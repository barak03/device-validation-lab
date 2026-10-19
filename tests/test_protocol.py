"""Unit tests for JSON-line parsing, responses, and dispatch."""

import json

from device_lab.model import DeviceModel
from device_lab.protocol import parse_request, process_line


def response_for(line: str, model: DeviceModel) -> dict[str, object]:
    response_line = process_line(line, model)
    assert response_line.endswith("\n")
    assert response_line.count("\n") == 1
    return json.loads(response_line)


def test_valid_request_and_response_frames() -> None:
    model = DeviceModel()

    assert parse_request('{"command":"INJECT_FAULT","fault_code":"SENSOR_FAILURE"}\n') == {
        "command": "INJECT_FAULT",
        "fault_code": "SENSOR_FAILURE",
    }
    assert response_for('{"command":"PING"}\n', model) == {
        "ok": True,
        "result": {"reply": "PONG"},
    }
    assert response_for('{"command":"STATUS"}\n', model)["result"] == model.status()
    assert response_for('{"command":"READ_METRICS"}\n', model)["result"] == model.read_metrics()
    assert response_for('{"command":"RESET"}\n', model)["result"] == model.status()


def test_invalid_json_returns_error_without_mutation() -> None:
    model = DeviceModel()
    before = model.status()

    for line in (
        '{"command":\n',
        "[" * 1500 + "\n",  # Invalid even when a decoder supports this nesting depth.
        '{"command":"PING","command":"RESET"}\n',
        '{"command":"INJECT_FAULT","fault_code":NaN}\n',
    ):
        response = response_for(line, model)
        assert response["ok"] is False
        assert response["error"]["code"] == "INVALID_JSON"
        assert model.status() == before


def test_invalid_request_shapes_return_error_without_mutation() -> None:
    model = DeviceModel()
    invalid_lines = (
        "[]\n",
        "{}\n",
        '{"command":42}\n',
        '{"command":"PING","extra":1}\n',
        '{"command":"INJECT_FAULT"}\n',
        '{"command":"INJECT_FAULT","fault_code":false}\n',
        '{"command":"PING"}',
        '{"command":"PING"}\n{"command":"RESET"}\n',
    )

    for line in invalid_lines:
        response = response_for(line, model)
        assert response["error"]["code"] == "INVALID_REQUEST"
        assert model.status() == {"state": "READY", "error_code": None, "reset_count": 0}


def test_unknown_command_and_later_valid_command() -> None:
    model = DeviceModel()

    response = response_for('{"command":"REBOOT"}\n', model)

    assert response["error"]["code"] == "UNKNOWN_COMMAND"
    assert response_for('{"command":"PING"}\n', model)["result"] == {"reply": "PONG"}
    assert model.status()["reset_count"] == 0
