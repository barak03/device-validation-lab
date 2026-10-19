"""Parse one JSON request line and format one JSON response line."""

import json
import math

from device_lab.model import DeviceError, DeviceModel


class ProtocolError(Exception):
    """A request failed validation with a stable protocol error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


COMMANDS = {"PING", "STATUS", "READ_METRICS", "INJECT_FAULT", "RESET"}
MAX_LINE_BYTES = 4096


def decode_json(document: str) -> object:
    """Reject ambiguous object keys and numbers that cannot be represented finitely."""

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    def finite_number(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number")
        return number

    return json.loads(
        document,
        object_pairs_hook=unique_object,
        parse_constant=finite_number,
        parse_float=finite_number,
    )


def parse_request(line: str) -> dict[str, str]:
    """Validate one newline-terminated request and return its fields."""
    if not isinstance(line, str) or not line.endswith("\n") or line.count("\n") != 1:
        raise ProtocolError("INVALID_REQUEST", "Expected one newline-terminated request")

    try:
        request = decode_json(line[:-1])
    except (ValueError, RecursionError) as exc:
        raise ProtocolError("INVALID_JSON", "Request is not valid JSON") from exc

    if not isinstance(request, dict):
        raise ProtocolError("INVALID_REQUEST", "Request must be a JSON object")

    command = request.get("command")
    if not isinstance(command, str) or not command:
        raise ProtocolError("INVALID_REQUEST", "command must be a nonempty string")
    if command not in COMMANDS:
        raise ProtocolError("UNKNOWN_COMMAND", "Command is not supported")

    expected_fields = {"command", "fault_code"} if command == "INJECT_FAULT" else {"command"}
    if request.keys() != expected_fields:
        raise ProtocolError("INVALID_REQUEST", "Request fields do not match command")
    if command == "INJECT_FAULT":
        fault_code = request["fault_code"]
        if not isinstance(fault_code, str) or not fault_code:
            raise ProtocolError("INVALID_REQUEST", "fault_code must be a nonempty string")

    return request


def encode_response(response: dict[str, object]) -> str:
    """Return compact JSON followed by exactly one line feed."""
    return json.dumps(response, separators=(",", ":"), allow_nan=False) + "\n"


def process_line(line: str, model: DeviceModel) -> str:
    """Apply a validated request and turn expected failures into responses."""
    try:
        request = parse_request(line)
        command = request["command"]
        if command == "PING":
            result = model.ping()
        elif command == "STATUS":
            result = model.status()
        elif command == "READ_METRICS":
            result = model.read_metrics()
        elif command == "INJECT_FAULT":
            result = model.inject_fault(request["fault_code"])
        else:
            result = model.reset()
    except (ProtocolError, DeviceError) as exc:
        return encode_response(
            {
                "ok": False,
                "error": {"code": exc.code, "message": str(exc)},
            }
        )
    return encode_response({"ok": True, "result": result})
