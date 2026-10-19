# Project Spec: Device Validation Lab

## Elevator pitch
A small Python device simulator and automated validation harness. A locally running virtual device accepts JSON commands over plain TCP. Pytest exercises expected behavior, fault injection, recovery, error handling and connection failures. GitHub Actions runs the suite in CI.

**Important:** This is a simulated device. Do not present it as validating physical hardware or production equipment.

## Why this project exists
Show the actual engineering skills used in automation/R&D work: designing concise checks, separating production and test code, validating state transitions, debugging communications failures, handling error responses and running reproducible CI. It intentionally avoids duplicating a pre-existing REST API test framework.

## Intended audience
An interviewer for Python Automation Engineer, SDET, Software Automation Engineer, or QA Infrastructure roles.

## System overview

```text
Pytest / smoke CLI
        |
        v
 DeviceClient (TCP, JSON lines, timeout)
        |
        v
 Local TCP server (127.0.0.1 only)
        |
        v
 DeviceModel: READY <-> FAULT
        |
        v
 Fixed sample metrics and structured error codes
```

## Stack and cost
- Python 3.11+ (free)
- Python standard library: `socket`, `socketserver`, `json`, `threading`, `argparse`, `logging` as needed
- pytest for tests (open source)
- Ruff for linting (open source)
- GitHub repository (public) and standard GitHub Actions runner (free for public repositories, subject to GitHub's current terms)
- No paid tools or accounts, no external API keys, no database, no cloud, no real hardware.
- Codex access itself depends on the user's own OpenAI plan and usage limits; it is not a dependency of the running project.

## MVP requirements
1. Device starts in READY state with `error_code = null` and `reset_count = 0`.
2. `PING` returns `PONG` regardless of state.
3. `STATUS` returns current state, current error code, and reset count.
4. `READ_METRICS` in READY returns static sample temperature and voltage; in FAULT it returns a structured `DEVICE_NOT_READY` error.
5. `INJECT_FAULT` with `SENSOR_FAILURE` changes state to FAULT. Unsupported fault codes return a structured error without changing state.
6. `RESET` changes state to READY, clears the error code, and increments `reset_count`.
7. Invalid JSON, unknown commands, and invalid request shapes do not crash the server; they return consistent error responses.
8. The server supports one JSON line request and one JSON line response per connection. State survives between connections.
9. A small client sets connection/read timeouts and raises understandable errors if the server is absent or unresponsive.
10. Pytest fixture runs simulator bound to `127.0.0.1` on a dynamically chosen available port and cleans up after each test.
11. Roughly 12-15 targeted unit and integration tests, all deterministic and offline.
12. GitHub Actions lints and tests on pushes and pull requests on a standard runner.
13. README documents setup, usage, limitations, project structure, and troubleshooting.

## Explicitly out of scope
- Real serial, USB, CAN, SSH, physical sensors, or physical device support
- Authentication, encryption, production security hardening, remote access
- An HTTP or REST wrapper, web dashboard, frontend
- Databases, queues, containers, Kubernetes or cloud deployments
- Performance/load testing or flaky-test statistical analysis
- AI features, LLM APIs, paid CI add-ons, code generation at runtime
- Sophisticated concurrency or asynchronous architecture

## Quality bar
A reviewer should understand the code within 15 minutes. Prefer clear failure messages, deterministic behavior and proper resource cleanup to more technology names. It must be easy to intentionally break a state transition, observe a failure and find why.
