"""UDP transport adapter used by the local TX/RX applications."""

from __future__ import annotations

import socket
from types import TracebackType


class UdpSender:
    """Send one protocol packet per UDP datagram."""

    def __init__(self, host: str, port: int) -> None:
        self.destination = (host, port)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, payload: bytes) -> int:
        raw = bytes(payload)
        sent = self._socket.sendto(raw, self.destination)
        if sent != len(raw):
            raise OSError(f"only {sent} of {len(raw)} bytes were sent")
        return sent

    def close(self) -> None:
        self._socket.close()

    def __enter__(self) -> UdpSender:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class UdpReceiver:
    """Receive protocol packets while preserving UDP message boundaries."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout: float | None = None,
        max_datagram_size: int = 65535,
    ) -> None:
        if max_datagram_size <= 0:
            raise ValueError("max_datagram_size must be positive")
        self.max_datagram_size = max_datagram_size
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((host, port))
        self._socket.settimeout(timeout)

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._socket.getsockname()
        return host, port

    def receive(self) -> tuple[bytes, tuple[str, int]]:
        return self._socket.recvfrom(self.max_datagram_size)

    def close(self) -> None:
        self._socket.close()

    def __enter__(self) -> UdpReceiver:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
