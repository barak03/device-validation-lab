"""Bound sockets make startup deterministic; every server is joined at teardown."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from socketserver import TCPServer
from threading import Thread

import pytest

from device_lab.client import DeviceClient
from device_lab.server import DeviceServer


@pytest.fixture
def run_server() -> Callable[[TCPServer], AbstractContextManager[TCPServer]]:
    @contextmanager
    def run(server: TCPServer) -> Iterator[TCPServer]:
        # TCPServer binds and listens during construction, before the thread starts.
        with server:
            thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
            thread.start()
            try:
                yield server
            finally:
                server.shutdown()
                thread.join(timeout=2)
                assert not thread.is_alive(), "Simulator thread did not stop"

    return run


@pytest.fixture
def device_server(run_server) -> Iterator[DeviceServer]:
    with run_server(DeviceServer(port=0, request_timeout=0.1)) as server:
        yield server


@pytest.fixture
def client(device_server: DeviceServer) -> DeviceClient:
    return DeviceClient(*device_server.server_address, connect_timeout=1, read_timeout=1)
