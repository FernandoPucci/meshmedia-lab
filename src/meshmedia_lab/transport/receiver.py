"""Receive and validate protocol packets."""

from collections.abc import Iterable

from meshmedia_lab.protocol.packet import Packet


class Receiver:
    """Convert raw transport payloads into validated packets."""

    def receive(self, payload: bytes) -> Packet:
        return Packet.from_bytes(payload)

    def receive_many(self, payloads: Iterable[bytes]) -> tuple[Packet, ...]:
        return tuple(self.receive(payload) for payload in payloads)
