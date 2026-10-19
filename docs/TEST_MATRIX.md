# Test Matrix: Device Validation Lab

The project currently has 16 independent, deterministic tests.
Each test starts with a fresh model; integration tests use a fresh localhost
server on an ephemeral port with guaranteed teardown. No sleeps or external
services are needed.

| ID | Phase | Level | Behavior to prove |
| --- | --- | --- | --- |
| U01 | 1 | Model | Initial status is READY, null error, zero resets; PING is PONG. |
| U02 | 1 | Model | READY returns fixed temperature and voltage. |
| U03 | 1 | Model | SENSOR_FAILURE enters FAULT; STATUS and PING work; metrics give DEVICE_NOT_READY. |
| U04 | 1 | Model | RESET clears FAULT and increments count, including a later reset. |
| U05 | 1 | Model | Unsupported fault leaves state and count unchanged. |
| U06 | 1 | Protocol | Valid request frames parse and responses are newline-terminated JSON. |
| U07 | 1 | Protocol | Invalid JSON returns INVALID_JSON without changing state. |
| U08 | 1 | Protocol | Missing/wrong/extra fields, non-object JSON, and missing newline return INVALID_REQUEST. |
| U09 | 1 | Protocol | Unknown command returns UNKNOWN_COMMAND; a later valid command succeeds. |
| I01 | 2 | TCP | Separate connections share server state. |
| I02 | 2 | TCP | Fault injection, metrics failure, reset and metrics recovery work end to end. |
| I03 | 2 | TCP | Invalid JSON and invalid command receive errors; the server keeps serving. |
| I04 | 2 | Client | Injected OS connection refusal and connect timeout raise distinct errors with endpoint context and preserve the cause. |
| I05 | 2 | Client/fixture | Read timeout is bounded; fixture shuts down and a later test starts clean. |
| I06 | 2 | Client/TCP | Malformed, truncated, invalid UTF-8, and invalid response envelopes raise ClientProtocolError. |
| I07 | Audit | TCP lifecycle | Server can restart immediately on the same port after a completed connection, with a fresh model. |

I01 also checks that a second line in one connection is not executed. I03
includes bad UTF-8, oversized frames, missing newline, and an idle peer.
I04 injects OS exceptions because non-listening bound ports behave differently
on macOS and Linux; it also verifies the configured connect timeout is passed
to the socket operation. I01-I03 and I05-I06 use real loopback sockets.
I05 tests a newly started server directly, so it does not depend on test order.

Phase 3 extends I01 with read-only smoke success, I02 with smoke failure in
FAULT and success after recovery, and I04 with smoke communication failures.
These assertions check the CLI return code and output without adding another
server lifecycle or relying on subprocess timing.

The final audit extends U07 and I03 to reject duplicate command fields without
mutating state. I06 also rejects duplicate response fields, nonstandard numeric
constants, and float overflow. I07 was added after reproducing a failed restart
caused by a closed connection's TIME_WAIT state.
U07 uses genuinely malformed nested JSON rather than assuming a particular
decoder recursion limit, which differs between Python 3.11 and 3.14.

The final audit checks test independence, timeouts, cleanup, logging, README
commands, and CI syntax. It adds a test only when it exposes a real gap.
