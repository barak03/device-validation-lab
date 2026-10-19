"""Read-only smoke check against a running simulated device."""

import argparse
import json
import math
import sys
from collections.abc import Sequence

from device_lab.client import ClientError, DeviceClient


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a running simulated device")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be finite and positive")
    client = DeviceClient(port=args.port, connect_timeout=args.timeout, read_timeout=args.timeout)
    checks = (
        ("PING", {"reply": "PONG"}),
        ("STATUS", None),
        ("READ_METRICS", {"temperature_c": 22.5, "voltage_v": 3.3}),
    )
    try:
        for command, expected in checks:
            response = client.request(command)
            if not response["ok"]:
                raise ValueError(f"{command}: {response['error']['code']}")
            result = response["result"]
            if command == "STATUS":
                if (
                    result.get("state") != "READY"
                    or result.get("error_code") is not None
                    or "error_code" not in result
                    or type(result.get("reset_count")) is not int
                    or result["reset_count"] < 0
                ):
                    raise ValueError(
                        f"STATUS: expected READY with no error and a reset count; got {result}"
                    )
            elif result != expected:
                raise ValueError(f"{command}: expected {expected}; got {result}")
            print(f"PASS {command}: {json.dumps(result, sort_keys=True)}")
    except (ClientError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("Smoke check passed (simulated device).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
