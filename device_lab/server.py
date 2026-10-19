"""Local TCP simulator: one request per connection, one shared device model."""

import argparse
import logging
import math
import socketserver

from device_lab.model import DeviceModel
from device_lab.protocol import MAX_LINE_BYTES, encode_response, process_line

logger = logging.getLogger(__name__)


class DeviceRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.connection.settimeout(self.server.request_timeout)
        try:
            try:
                raw = self.rfile.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    return
                if len(raw) > MAX_LINE_BYTES:
                    raise ValueError("Request line exceeds 4096 bytes")
                line = raw.decode("utf-8")
            except (ValueError, TimeoutError) as exc:
                response = encode_response(
                    {
                        "ok": False,
                        "error": {"code": "INVALID_REQUEST", "message": str(exc)},
                    }
                )
            else:
                response = process_line(line, self.server.model)
            self.wfile.write(response.encode("utf-8"))
        except OSError as exc:
            # A peer may leave before reading; the next connection still works.
            logger.warning("Connection from %s ended: %s", self.client_address, exc)


class DeviceServer(socketserver.TCPServer):
    """Serve requests serially on loopback; each server owns a fresh model."""

    # Permit a restart while previously accepted connections remain in TIME_WAIT.
    allow_reuse_address = True

    def __init__(self, port: int = 8765, *, request_timeout: float = 1.0) -> None:
        if not math.isfinite(request_timeout) or request_timeout <= 0:
            raise ValueError("request_timeout must be finite and positive")
        self.request_timeout = request_timeout
        self.model = DeviceModel()
        super().__init__(("127.0.0.1", port), DeviceRequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the simulated device on localhost")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--request-timeout", type=float, default=1.0)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        with DeviceServer(args.port, request_timeout=args.request_timeout) as server:
            logger.info("Simulated device listening on %s:%s", *server.server_address)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                logger.info("Simulated device stopped")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Cannot start simulated device: {exc}\n")


if __name__ == "__main__":
    main()
