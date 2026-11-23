"""Replaceable byte transport interfaces."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol


class TransportAdapter(Protocol):
    """Minimal interface required by the transmitter."""

    def send(self, payload: bytes) -> None:
        """Send one encoded packet."""


@dataclass
class InMemoryTransport:
    """Transport substitute for local tests and experiments."""

    _payloads: list[bytes] = field(default_factory=list)

    def send(self, payload: bytes) -> None:
        self._payloads.append(bytes(payload))

    def drain(self) -> tuple[bytes, ...]:
        payloads = tuple(self._payloads)
        self._payloads.clear()
        return payloads

    def extend(self, payloads: Iterable[bytes]) -> None:
        for payload in payloads:
            self.send(payload)
