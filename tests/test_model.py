"""Unit tests for device state transitions."""

import pytest

from device_lab.model import DeviceError, DeviceModel


def test_initial_status_and_ping() -> None:
    model = DeviceModel()

    assert model.status() == {"state": "READY", "error_code": None, "reset_count": 0}
    assert model.ping() == {"reply": "PONG"}


def test_ready_metrics_are_fixed() -> None:
    assert DeviceModel().read_metrics() == {"temperature_c": 22.5, "voltage_v": 3.3}


def test_fault_blocks_metrics_but_not_status_or_ping() -> None:
    model = DeviceModel()

    assert model.inject_fault("SENSOR_FAILURE") == {
        "state": "FAULT",
        "error_code": "SENSOR_FAILURE",
        "reset_count": 0,
    }
    assert model.ping() == {"reply": "PONG"}
    assert model.status()["state"] == "FAULT"
    with pytest.raises(DeviceError) as error:
        model.read_metrics()
    assert error.value.code == "DEVICE_NOT_READY"


def test_reset_recovers_and_counts_each_reset() -> None:
    model = DeviceModel()
    model.inject_fault("SENSOR_FAILURE")

    assert model.reset() == {"state": "READY", "error_code": None, "reset_count": 1}
    assert model.read_metrics()["voltage_v"] == 3.3
    assert model.reset()["reset_count"] == 2


def test_unsupported_fault_does_not_change_state() -> None:
    model = DeviceModel()
    for state in ("READY", "FAULT"):
        if state == "FAULT":
            model.inject_fault("SENSOR_FAILURE")
        before = model.status()
        with pytest.raises(DeviceError) as error:
            model.inject_fault("UNKNOWN_FAULT")
        assert error.value.code == "UNSUPPORTED_FAULT"
        assert model.status() == before
