# Protocol: Device Validation Lab

This project simulates a device. The protocol is local, plain TCP with UTF-8
JSON Lines. One connection carries exactly one request line and one response
line. A line ends with `\n`; the server closes the connection after replying.
Device state persists across connections until reset or server shutdown.

The server binds only to `127.0.0.1` and processes connections serially. Only
the first request line in a connection is processed. Lines are limited to
4096 bytes including the line feed. Invalid UTF-8, oversized requests, and
requests that stall before the line feed receive `INVALID_REQUEST` when the
peer is still connected. An empty connection closes without a response.

The default server socket timeout is 1 second. `DeviceClient` defaults to
1 second for connecting and 1 second for sending/reading. These are socket
inactivity timeouts, not a total wall-clock deadline for a peer that keeps
sending bytes. All timeout values must be finite and positive. There are no
retries. A timeout cannot prove whether a state-changing request was executed;
reconnect and inspect `STATUS` before deciding whether to send it again.

## Request

A request is a JSON object. `command` is a required, case-sensitive string.
No fields beyond those listed below are accepted.

| Command | Exact request shape | Meaning |
| --- | --- | --- |
| `PING` | `{"command":"PING"}` | Check that the device responds, in any state. |
| `STATUS` | `{"command":"STATUS"}` | Read state, error code and reset count. |
| `READ_METRICS` | `{"command":"READ_METRICS"}` | Read fixed sample values in READY. |
| `INJECT_FAULT` | `{"command":"INJECT_FAULT","fault_code":"SENSOR_FAILURE"}` | Enter FAULT. |
| `RESET` | `{"command":"RESET"}` | Enter READY, clear error and increment reset count. |

`fault_code` must be a nonempty string. `SENSOR_FAILURE` is the only supported
value. Another nonempty string produces `UNSUPPORTED_FAULT` without changing
the device. JSON must be valid, contain one object, and end with one line feed.
Requests and responses reject duplicate object keys, `NaN`, `Infinity`, and
numbers too large to represent as finite Python floats. These rules also
apply to nested objects so decoding cannot silently replace an earlier field.

## Response

Every response is a JSON object followed by `\n`. Success has exactly the
keys `ok` and `result`; errors have exactly `ok` and `error`.

```json
{"ok":true,"result":{"reply":"PONG"}}
{"ok":true,"result":{"state":"READY","error_code":null,"reset_count":0}}
{"ok":true,"result":{"temperature_c":22.5,"voltage_v":3.3}}
{"ok":false,"error":{"code":"DEVICE_NOT_READY","message":"Device is in FAULT state"}}
```

`PING` returns `reply: "PONG"`. `STATUS`, `INJECT_FAULT`, and `RESET` return the
same status fields: `state` (`READY` or `FAULT`), `error_code` (a string or
`null`), and `reset_count` (an integer). `READ_METRICS` returns fixed sample
values `temperature_c: 22.5` and `voltage_v: 3.3` only in READY.

Error responses contain a stable `code` and a readable `message`. Consumers
should branch on `code`, not the text of `message`.

| Error code | Condition |
| --- | --- |
| `INVALID_JSON` | Invalid JSON, duplicate keys, non-finite numbers, or nesting/numbers beyond decoder limits. |
| `INVALID_REQUEST` | Invalid UTF-8, oversized/stalled line, missing line feed, non-object JSON, missing/wrong fields, or extra fields. |
| `UNKNOWN_COMMAND` | A syntactically valid command name is not supported. |
| `UNSUPPORTED_FAULT` | A nonempty fault code other than `SENSOR_FAILURE`. |
| `DEVICE_NOT_READY` | `READ_METRICS` while in FAULT. |

Malformed requests and domain errors return one error response and do not
change device state. The protocol has no request ID, retries, authentication,
or compatibility version; these are outside the project's scope.

## Python client

`DeviceClient.request(command, **fields)` opens and closes a connection for
each call and returns the full response envelope. Device errors such as
`DEVICE_NOT_READY` are ordinary responses. Transport failures instead raise
`ClientConnectionError`, `ClientTimeoutError`, or `ClientProtocolError` (all
subclasses of `ClientError`) with command and endpoint context. Malformed,
truncated, oversized, or incorrectly shaped responses raise
`ClientProtocolError`.
