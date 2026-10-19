"""In-memory behavior of the simulated device."""


class DeviceError(Exception):
    """A device operation failed with a stable protocol error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DeviceModel:
    """Hold device state independently of transport and request parsing."""

    def __init__(self) -> None:
        self.state = "READY"
        self.error_code: str | None = None
        self.reset_count = 0

    def ping(self) -> dict[str, str]:
        return {"reply": "PONG"}

    def status(self) -> dict[str, str | int | None]:
        return {
            "state": self.state,
            "error_code": self.error_code,
            "reset_count": self.reset_count,
        }

    def read_metrics(self) -> dict[str, float]:
        if self.state != "READY":
            raise DeviceError("DEVICE_NOT_READY", "Device is in FAULT state")
        return {"temperature_c": 22.5, "voltage_v": 3.3}

    def inject_fault(self, fault_code: str) -> dict[str, str | int | None]:
        if fault_code != "SENSOR_FAILURE":
            raise DeviceError("UNSUPPORTED_FAULT", "Only SENSOR_FAILURE is supported")
        self.state = "FAULT"
        self.error_code = fault_code
        return self.status()

    def reset(self) -> dict[str, str | int | None]:
        self.state = "READY"
        self.error_code = None
        self.reset_count += 1
        return self.status()
