"""Small synchronous TCP client with explicit failures and no retries."""

import json
import math
import socket

from device_lab.protocol import MAX_LINE_BYTES, decode_json


class ClientError(Exception):
    """Base class for transport or response failures."""


class ClientConnectionError(ClientError):
    """Could not connect, send, or receive due to a socket error."""


class ClientTimeoutError(ClientError):
    """Connection or response exceeded the configured socket timeout."""


class ClientProtocolError(ClientError):
    """The peer returned a malformed response."""


class DeviceClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        *,
        connect_timeout: float = 1.0,
        read_timeout: float = 1.0,
    ) -> None:
        for name, value in (
            ("connect_timeout", connect_timeout),
            ("read_timeout", read_timeout),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        self.address = (host, port)
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

    def request(self, command: str, **fields: object) -> dict[str, object]:
        """Return the full response, including valid device error responses."""
        payload = (json.dumps({"command": command, **fields}, allow_nan=False) + "\n").encode()
        if len(payload) > MAX_LINE_BYTES:
            raise ValueError("Request line exceeds 4096 bytes")
        context = f"{command} at {self.address[0]}:{self.address[1]}"
        stage = "connecting"
        try:
            with socket.create_connection(self.address, timeout=self.connect_timeout) as connection:
                stage = "sending request or reading response"
                connection.settimeout(self.read_timeout)
                connection.sendall(payload)
                with connection.makefile("rb") as stream:
                    raw = stream.readline(MAX_LINE_BYTES + 1)
        except TimeoutError as exc:
            raise ClientTimeoutError(f"{context}: timed out while {stage}") from exc
        except OSError as exc:
            raise ClientConnectionError(f"{context}: {stage} failed: {exc}") from exc

        if not raw.endswith(b"\n") or len(raw) > MAX_LINE_BYTES:
            raise ClientProtocolError(f"{context}: expected a JSON line of at most 4096 bytes")
        try:
            response = decode_json(raw.decode("utf-8"))
        except (ValueError, RecursionError) as exc:
            raise ClientProtocolError(f"{context}: response is not valid UTF-8 JSON") from exc
        if not isinstance(response, dict) or type(response.get("ok")) is not bool:
            raise ClientProtocolError(f"{context}: response must contain a boolean ok field")
        if response["ok"]:
            valid = response.keys() == {"ok", "result"} and isinstance(response["result"], dict)
        else:
            error = response.get("error")
            valid = (
                response.keys() == {"ok", "error"}
                and isinstance(error, dict)
                and error.keys() == {"code", "message"}
                and all(isinstance(error[key], str) and error[key] for key in ("code", "message"))
            )
        if not valid:
            raise ClientProtocolError(f"{context}: invalid response envelope")
        return response
