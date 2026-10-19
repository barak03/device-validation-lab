"""Offline TCP checks using loopback sockets and explicit resource cleanup."""

import errno
import json
import socket
import socketserver
from time import monotonic

import pytest

from device_lab.client import (
    ClientConnectionError,
    ClientProtocolError,
    ClientTimeoutError,
    DeviceClient,
)
from device_lab.server import DeviceServer
from device_lab.smoke import main as smoke_main


def test_connections_share_state_and_process_only_one_line(device_server, client, capsys) -> None:
    assert device_server.server_address[0] == "127.0.0.1"
    assert client.request("STATUS")["result"]["reset_count"] == 0
    assert client.request("X" * 4000)["error"]["code"] == "UNKNOWN_COMMAND"
    assert (
        client.request("INJECT_FAULT", fault_code="X" * 4000)["error"]["code"]
        == "UNSUPPORTED_FAULT"
    )
    assert client.request("RESET")["result"]["reset_count"] == 1
    assert client.request("STATUS")["result"]["reset_count"] == 1

    assert smoke_main(["--port", str(device_server.server_address[1])]) == 0
    output = capsys.readouterr()
    assert "Smoke check passed (simulated device)." in output.out
    assert output.err == ""
    assert client.request("STATUS")["result"]["reset_count"] == 1

    with socket.create_connection(device_server.server_address, timeout=1) as connection:
        connection.sendall(b'{"command":"PING"}\n{"command":"RESET"}\n')
        with connection.makefile("rb") as stream:
            assert json.loads(stream.readline()) == {
                "ok": True,
                "result": {"reply": "PONG"},
            }
            assert stream.read() == b""
    assert client.request("STATUS")["result"]["reset_count"] == 1


def test_fault_injection_and_reset_recovery(client, capsys) -> None:
    assert client.request("READ_METRICS")["result"] == {
        "temperature_c": 22.5,
        "voltage_v": 3.3,
    }
    fault = {"state": "FAULT", "error_code": "SENSOR_FAILURE", "reset_count": 0}
    assert client.request("INJECT_FAULT", fault_code="SENSOR_FAILURE")["result"] == fault
    assert client.request("READ_METRICS")["error"]["code"] == "DEVICE_NOT_READY"
    assert client.request("PING")["result"] == {"reply": "PONG"}
    assert (
        client.request("INJECT_FAULT", fault_code="OTHER")["error"]["code"] == "UNSUPPORTED_FAULT"
    )
    assert client.request("STATUS")["result"] == fault
    assert smoke_main(["--port", str(client.address[1])]) == 1
    assert "FAIL: STATUS:" in capsys.readouterr().err
    assert client.request("STATUS")["result"] == fault
    assert client.request("RESET")["result"] == {
        "state": "READY",
        "error_code": None,
        "reset_count": 1,
    }
    assert client.request("READ_METRICS")["ok"] is True
    assert smoke_main(["--port", str(client.address[1])]) == 0
    assert "Smoke check passed" in capsys.readouterr().out


def test_malformed_requests_do_not_break_server(device_server, client) -> None:
    cases = (
        (b"{bad}\n", "INVALID_JSON"),
        (b'{"command":"PING","command":"RESET"}\n', "INVALID_JSON"),
        (b'{"command":"MISSING"}\n', "UNKNOWN_COMMAND"),
        (b'{"command":false}\n', "INVALID_REQUEST"),
        (b"\xff\n", "INVALID_REQUEST"),
        (b'{"command":"RESET"}', "INVALID_REQUEST"),
        (b"x" * 4096 + b"\n", "INVALID_REQUEST"),
    )
    for payload, code in cases:
        with socket.create_connection(device_server.server_address, timeout=1) as connection:
            connection.sendall(payload)
            connection.shutdown(socket.SHUT_WR)
            with connection.makefile("rb") as stream:
                response = json.loads(stream.readline())
                assert response["ok"] is False
                assert response["error"]["code"] == code
        assert client.request("PING")["ok"] is True
    # An incomplete request gets a timeout error instead of holding the server forever.
    with socket.create_connection(device_server.server_address, timeout=1) as connection:
        connection.sendall(b'{"command":"RESET"}')
        with connection.makefile("rb") as stream:
            assert json.loads(stream.readline())["error"]["code"] == "INVALID_REQUEST"
    assert client.request("STATUS")["result"]["reset_count"] == 0


def test_refused_connection_and_connect_timeout_have_context(monkeypatch, capsys) -> None:
    # A bound, non-listening port times out on macOS but refuses on Linux.
    # Inject the OS failures so both branches are deterministic on either OS.
    failures = (
        (
            ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused"),
            ClientConnectionError,
        ),
        (TimeoutError("timed out"), ClientTimeoutError),
    )
    for failure, expected_error in failures:

        def fail_connection(address, *, timeout, failure=failure):
            assert address == ("127.0.0.1", 8765)
            assert timeout == 0.2
            raise failure

        monkeypatch.setattr(socket, "create_connection", fail_connection)
        client = DeviceClient(connect_timeout=0.2)
        with pytest.raises(expected_error, match="PING at 127.0.0.1:8765:.*connecting") as error:
            client.request("PING")
        assert error.value.__cause__ is failure
        assert smoke_main(["--timeout", "0.2"]) == 1
        output = capsys.readouterr()
        assert "FAIL: PING at 127.0.0.1:8765:" in output.err
        assert output.out == ""


def test_read_timeout_cleanup_and_fresh_server(run_server) -> None:
    # The kernel accepts the connection; this peer intentionally sends no response.
    with socket.socket() as silent_peer:
        silent_peer.bind(("127.0.0.1", 0))
        silent_peer.listen(1)
        client = DeviceClient(*silent_peer.getsockname(), read_timeout=0.05)
        start = monotonic()
        with pytest.raises(ClientTimeoutError, match="reading response"):
            client.request("PING")
        assert monotonic() - start < 2, "Read timeout was not bounded"

    with run_server(DeviceServer(port=0)) as first:
        client = DeviceClient(*first.server_address)
        client.request("INJECT_FAULT", fault_code="SENSOR_FAILURE")
        client.request("RESET")
    assert first.socket.fileno() == -1
    with run_server(DeviceServer(port=0)) as second:
        client = DeviceClient(*second.server_address)
        assert client.request("STATUS")["result"] == {
            "state": "READY",
            "error_code": None,
            "reset_count": 0,
        }
    assert second.socket.fileno() == -1


def test_client_rejects_malformed_responses(run_server) -> None:
    class BadResponseHandler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            self.connection.settimeout(1)
            self.rfile.readline(4096)
            self.wfile.write(self.server.response)

    with run_server(socketserver.TCPServer(("127.0.0.1", 0), BadResponseHandler)) as peer:
        client = DeviceClient(*peer.server_address)
        for response in (
            b"",
            b"not-json\n",
            b"\xff\n",
            b"{}\n",
            b'{"ok":true}\n',
            b'{"ok":false,"error":{}}\n',
            b'{"ok":true,"result":{}}',
            b'{"ok":true,"result":{"temperature_c":NaN}}\n',
            b'{"ok":true,"result":{"voltage_v":Infinity}}\n',
            b'{"ok":true,"result":{"voltage_v":-Infinity}}\n',
            b'{"ok":true,"result":{"voltage_v":1e999}}\n',
            b'{"ok":false,"ok":true,"result":{}}\n',
            b'{"ok":true,"result":{"reply":"WRONG","reply":"PONG"}}\n',
        ):
            peer.response = response
            with pytest.raises(ClientProtocolError, match="PING at 127.0.0.1"):
                client.request("PING")


def test_server_restarts_on_same_port(run_server) -> None:
    with run_server(DeviceServer(port=0)) as first:
        address = first.server_address
        # Read through EOF so the server actively closes the accepted socket.
        with socket.create_connection(address, timeout=1) as connection:
            connection.sendall(b'{"command":"RESET"}\n')
            with connection.makefile("rb") as stream:
                assert json.loads(stream.read())["result"]["reset_count"] == 1
    assert first.socket.fileno() == -1

    with run_server(DeviceServer(port=address[1])) as restarted:
        client = DeviceClient(*restarted.server_address)
        assert client.request("STATUS")["result"] == {
            "state": "READY",
            "error_code": None,
            "reset_count": 0,
        }
    assert restarted.socket.fileno() == -1
