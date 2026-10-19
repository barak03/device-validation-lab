# Device Validation Lab

A small Python device simulator and automated validation harness for an SDET
or Python automation portfolio. This is a **simulated device** with fixed sample
metrics. It does not validate physical hardware or production equipment.

The project demonstrates state transitions, TCP/JSON communication, fault
injection and recovery, negative testing, explicit timeouts, and test cleanup.
The runtime uses only Python's standard library. Development tools are pytest
and Ruff; no API keys, accounts, external devices, or external services are
needed to run locally.

## How it works

```text
pytest / smoke CLI -> DeviceClient -> localhost TCP server -> DeviceModel
                                                               READY <-> FAULT
```

Each connection sends one UTF-8 JSON line and receives one JSON line. The
server processes connections serially and keeps device state between them.
`SENSOR_FAILURE` moves the model to FAULT. `RESET` returns it to READY, clears
the error, and increments the reset count. PING and STATUS work in both states.

## Setup

Use Python 3.11 or newer. From the project directory, on macOS or Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

On Windows PowerShell, create the environment with `py -3 -m venv .venv` and
activate it with `.venv\Scripts\Activate.ps1`. Run commands from this directory
so Python can find `device_lab`. Installing dependencies requires internet;
running the project and its tests afterward uses only localhost.

## Run the simulator and smoke check

In the first terminal, with the environment activated:

```sh
python -m device_lab.server --port 8765
```

Expected startup message:

```text
INFO: Simulated device listening on 127.0.0.1:8765
```

In a second terminal, activate the same environment and run:

```sh
python -m device_lab.smoke --port 8765
```

Expected output for a fresh server:

```text
PASS PING: {"reply": "PONG"}
PASS STATUS: {"error_code": null, "reset_count": 0, "state": "READY"}
PASS READ_METRICS: {"temperature_c": 22.5, "voltage_v": 3.3}
Smoke check passed (simulated device).
```

Smoke checks are read-only. They exit with code 0 on success, 1 on a failed
check or communication error, and 2 for invalid CLI arguments. They require
READY and do not silently reset a faulted device. Stop the server with Ctrl+C.
Use `--help` on either module to inspect its options.

## Try a fault and recovery

With the server still running, start `python` in the second terminal:

```python
from device_lab.client import DeviceClient

client = DeviceClient()
print(client.request("INJECT_FAULT", fault_code="SENSOR_FAILURE"))
print(client.request("READ_METRICS"))  # ok=False, DEVICE_NOT_READY
print(client.request("RESET"))  # READY, error cleared, reset_count=1
print(client.request("READ_METRICS"))  # ok=True, fixed sample metrics
```

Each call opens a new connection. A valid device error is returned as an
`ok: false` response. Connection, timeout, and malformed-response failures
raise `ClientError` subclasses instead. See the [protocol](docs/PROTOCOL.md)
for all request and response shapes.

To observe a failing smoke check, inject the fault and run the smoke command
before RESET. It prints `FAIL` to stderr and exits 1. Reset the device and run
it again to see recovery.

## Tests and lint

```sh
python -m pytest -q
ruff check .
ruff format --check .
```

The suite currently contains 16 tests: nine model/protocol tests and seven
transport/client tests. Expected pytest summary: `16 passed` (timing varies).
Tests start their own servers on `127.0.0.1` using OS-assigned ports. Each
fixture closes its socket and joins its thread, including on test failure.
You do not need a separately running server, and tests do not share its state.

The connection-refusal and connect-timeout cases inject OS exceptions for
consistent macOS/Linux behavior. Other transport tests use real loopback TCP,
including a peer that does not respond to exercise the read timeout. Smoke
success, FAULT failure, and communication failure are checked in these same
tests. The [test matrix](docs/TEST_MATRIX.md) maps cases to requirements.

The [GitHub Actions workflow](.github/workflows/ci.yml) is configured to run
these checks on push and pull request, using Python 3.11 on `ubuntu-latest`.
It uses the official [checkout](https://github.com/actions/checkout/releases)
and [setup-python](https://github.com/actions/setup-python/releases) actions.
It starts running once this project is pushed to a GitHub repository with
Actions enabled; local verification does not establish a successful CI run.

## Project structure

```text
device_lab/
  model.py         In-memory READY/FAULT state machine
  protocol.py      JSON-line parsing, dispatch, and responses
  server.py        Local TCP server and server CLI
  client.py        Timeouts, socket cleanup, and response validation
  smoke.py         Read-only smoke CLI
tests/
  conftest.py      Temporary server fixtures
  test_model.py    State transitions and domain errors
  test_protocol.py  Request validation and response framing
  test_integration.py  Transport, client failures, and smoke behavior
docs/              Specification, protocol, test matrix, phase plan
.github/workflows/ci.yml
pyproject.toml      Python metadata, pytest and Ruff configuration
requirements-dev.txt  Tested pytest and Ruff versions
```

## Limits and troubleshooting

- **Connection failed:** start the server and use the same port in both
  terminals. The server always binds to `127.0.0.1`.
- **Port already in use:** stop your earlier simulator or choose another port,
  for example `--port 8766`, for both server and smoke.
- **Smoke reports FAULT:** inspect STATUS, then issue RESET when you want to
  clear the fault. Every RESET increments the count, including in READY.
- **Timeout:** default connect and socket read/write timeouts are 1 second.
  Smoke accepts `--timeout 2`; the server accepts `--request-timeout 2`.
  These limit inactivity, not total elapsed time if a peer keeps sending.
  No operation is retried; after an uncertain state-changing request, inspect
  STATUS before deciding whether to send it again.
- **Import/dependency error:** activate `.venv`, install `requirements-dev.txt`,
  and run from the project root. No editable package installation is required.
- **Socket permission error:** the integration tests require local socket
  binding. Restricted execution environments must permit localhost sockets.

The protocol limits lines to 4096 bytes. State is kept only in memory and a
server restart creates a fresh model. This is a serial educational simulator,
with no authentication, encryption, real device transport, performance goals,
or production reliability claims. It has no Docker, database, cloud runtime,
or web interface.
