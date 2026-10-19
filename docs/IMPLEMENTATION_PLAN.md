# Implementation Plan: Device Validation Lab

Work in small phases. This plan is derived from `PROJECT_SPEC.md` and
`PROTOCOL.md`; it is the project's execution checklist. Keep the simulated
device simple and the validation behavior easy to explain in an interview.

## Phase 1: model and protocol

- Create a minimal Python 3.11+ project with `device_lab/` and `tests/`.
- Implement an in-memory `DeviceModel` without sockets. Its public methods
  cover PING, STATUS, READ_METRICS, INJECT_FAULT, and RESET.
- Implement JSON-line request parsing, strict request shape validation,
  consistent success/error responses, and a small dispatcher in
  `device_lab/protocol.py`.
- Add unit tests U01-U09 from `TEST_MATRIX.md`.
- Run the tests and available lint check, and report actual results.

Stop after Phase 1 for review of state transitions and failure responses.
Phase 1 excludes TCP, integration fixtures, CI, Docker, and extras.

## Phase 2: TCP simulator and automation harness

- Add a localhost-only server using the standard library. It handles one
  request and one response per connection, while preserving model state.
- Add a small `DeviceClient` with explicit connect/read timeouts and clear
  connection/protocol errors; no silent retries.
- Add a pytest fixture using `127.0.0.1`, port 0, a fresh model per test, and
  guaranteed server shutdown without sleep-based synchronization.
- Add tests I01-I06 and run lint plus all tests.

Stop after Phase 2. Do not add CI, Docker, GUI, or extra libraries here.

### Inspect Phase 2 locally

Run from the project root with the development dependencies installed:

```sh
./.venv/bin/python -m pytest -q
./.venv/bin/ruff check .
./.venv/bin/python -m device_lab.server --port 8765
```

In another terminal, from the same directory:

```sh
./.venv/bin/python -c 'from device_lab.client import DeviceClient; print(DeviceClient().request("STATUS"))'
```

The expected initial response is
`{'ok': True, 'result': {'state': 'READY', 'error_code': None, 'reset_count': 0}}`.
Stop the server with Ctrl+C. Tests manage their own temporary localhost
servers and do not require a separately running server. A sandbox that blocks
local socket binding must allow loopback sockets for the TCP tests to run.

## Phase 3: usability and CI

- Add a tiny smoke CLI, a beginner-readable English README, a minimal Ruff
  configuration, and GitHub Actions lint/test on push and pull request using
  `ubuntu-latest`.
- Include a short example of expected command output and explain that this
  is a simulated device, not physical hardware validation.
- Run all available local checks and document any limitation.

The smoke CLI checks PING, STATUS, and READ_METRICS against a running server
without changing device state. See `README.md` for setup, usage, sample output,
and troubleshooting. Development dependencies are recorded in
`requirements-dev.txt`. CI performs lint, format checking, and pytest on
Python 3.11; its hosted result is only available after a future push to GitHub.

## Final audit

Review as an SDET hiring manager and maintainer. Identify up to five real
defects or risks, demonstrate them when possible, apply only justified fixes,
and rerun lint and the full suite. Do not add features beyond the spec.
Do not commit or publish without a separate user instruction.

### Audit completed locally: 2026-10-19

Phases 1-3 and the final local audit are complete. Four findings were reproduced
before their fixes:

1. **Ambiguous commands could change state.** A request containing both
   `"command":"PING"` and `"command":"RESET"` executed RESET because the JSON
   decoder silently retained the last value. Duplicate object keys are now
   rejected with `INVALID_JSON`, without mutation; the client rejects duplicate
   response keys as well.
2. **Invalid numeric responses were accepted.** The client accepted `NaN` as a
   successful metric value. Shared JSON decoding now rejects NaN, infinities,
   and float overflow with `ClientProtocolError` on responses.
3. **A stopped server could not immediately restart on the same port.** A
   completed connection left the port in TIME_WAIT and the next bind raised
   `Address already in use`. Address reuse now permits a new server to bind
   after shutdown. A dedicated test also confirms the new model starts fresh.
4. **One test depended on the Python decoder implementation.** It assumed a
   deeply nested but valid array would always fail JSON parsing. Python 3.14
   parsed it successfully, producing the correct request-shape error instead.
   The test now supplies genuinely invalid JSON so its expected error is stable.

Verification performed on macOS:

- `./.venv/bin/python -m pytest -q -W error`: 16 passed on Python 3.11.9.
- Created a temporary environment with `python3 -m venv`, installed
  `requirements-dev.txt`, and ran `python -m pytest -q -W error`: 16 passed on
  Python 3.14.3. Warnings were treated as failures in both runs.
- `ruff check .` and `ruff format --check .`: passed with Ruff 0.17.1.
- `python -m pip check`: no broken requirements in the project environment.
- Started the server and smoke CLI in separate processes using Python 3.14.
  Checked exact README output, failure in FAULT, successful RESET recovery,
  startup/shutdown logs, Ctrl+C cleanup, and immediate restart on the same port.
- Parsed the CI YAML and verified its events, read permission, runner, job
  timeout, and install/lint/format/test commands.

The GitHub-hosted workflow has not run. Linux and Windows execution have not
been verified locally. The documented serial-server and inactivity-timeout
limits remain intentional. No commit or publication was performed.

For an interview, be ready to explain the READY/FAULT transitions and rejection
of invalid commands, why each test owns its server and ephemeral port, and how
timeouts and JSON framing distinguish device errors from transport failures.
