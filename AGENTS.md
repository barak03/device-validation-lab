# Codex Instructions: Device Validation Lab

You are implementing a SMALL, credible, personal Python Software Automation/SDET portfolio project. Read `docs/PROJECT_SPEC.md`, `docs/PROTOCOL.md`, `docs/TEST_MATRIX.md`, and `docs/IMPLEMENTATION_PLAN.md` before coding.

## Goals
- Build an honest, interview-defensible project demonstrating Python, stateful test automation, TCP/JSON diagnostics, pytest fixtures, negative testing, and free CI.
- Make the simulated system under test intentionally simple. Engineering quality should live primarily in the test harness and reliable test execution.
- Prefer readable, idiomatic Python 3.11+ over abstractions, patterns, and frameworks that are not needed.
- Work in phases. **Do not advance to the next phase without the user's next explicit instruction.**

## Non-negotiable constraints
- 100% free technical stack; no paid APIs, cloud accounts, hosted databases, external devices, credentials, or secrets.
- Run locally, offline after Python dev dependencies are installed; CI uses only GitHub-hosted standard `ubuntu-latest` for a public repository.
- Python standard library for the TCP simulator and transport. Only pytest and Ruff as development dependencies. Do not add FastAPI, Flask, Requests, Redis, Docker, Celery, external services, or a web frontend.
- No real hardware integration or unverified claims about Dell, CEVA, or employer code. This is a synthetic educational demo and must always be labeled as such.
- Do not add speculative capabilities, excessive layers, generic frameworks, factories, plugins, or unnecessary classes.
- Bind the simulator to 127.0.0.1 by default. Never use 0.0.0.0 as default.
- No sleep-based test synchronization or arbitrary waits. Use ephemeral ports and deterministic pytest fixtures with guaranteed teardown.
- Add proper connect/read timeouts and explicit, small error types. Do not silently retry failures.
- One JSON request per TCP connection, terminated by `\n`, and one JSON response, terminated by `\n`. Server state persists across connections until reset/shutdown.
- Keep messages and errors consistent with `docs/PROTOCOL.md`. A malformed request must not crash the server.
- Avoid committing environment files, `.venv`, secrets, caches, or test reports.

## Code and tests
- Root package: `device_lab/`. Tests: `tests/`.
- `device_lab/model.py`: small in-memory state machine, no networking.
- `device_lab/protocol.py`: JSON-line parsing, schema validation, response helper(s).
- `device_lab/server.py`: stdlib TCP server and a CLI entry point.
- `device_lab/client.py`: Python client with timeouts, clear exceptions, contextual errors.
- `device_lab/smoke.py`: tiny CLI smoke check.
- `tests/conftest.py`: server fixture on port 0, fresh model per test, clean shutdown.
- Keep pytest tests independent, deterministic, and offline. No test ordering assumptions.
- Add type hints to public methods and concise docstrings for non-obvious behavior.
- Use Ruff for lint. Do not suppress warnings globally.
- Make logs helpful but small and avoid unnecessary logging in successful tests.
- Prefer subprocess-independent integration tests (start a server in a test fixture thread); provide a CLI that can launch the server manually.

## Expected delivery after each phase
1. Briefly list added/changed files.
2. Explain why any implementation differed from the spec.
3. Show the exact lint and test commands run and their real results. Do not pretend execution succeeded.
4. Identify any unfinished work or limitations.
5. Stop. Do not proceed to the next phase or publish to GitHub.

## Definition of done (final phase)
- `python -m pytest -q` passes locally, with no network services.
- `ruff check .` passes.
- A beginner-readable README explains the simulated nature of the project and how to run it.
- The GitHub Actions CI runs lint and tests on push/PR using a standard runner.
- There are around 12-15 meaningful, independent tests, not dozens of superficial assertions.
- Basic protocol failures, device FAULT, RESET recovery, and client timeouts are covered.
- User can describe the system in under two minutes and reproduce a failing test.
