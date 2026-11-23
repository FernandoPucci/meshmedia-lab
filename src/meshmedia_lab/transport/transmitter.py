"""Transmit protocol packets through an adapter."""

from collections.abc import Iterable

from meshmedia_lab.protocol.packet import Packet

from .adapter import TransportAdapter


class Transmitter:
    """Serialize packets and hand them to the selected transport."""

    def __init__(self, adapter: TransportAdapter) -> None:
        self.adapter = adapter

    def transmit(self, packets: Iterable[Packet]) -> int:
        count = 0
        for packet in packets:
            self.adapter.send(packet.to_bytes())
            count += 1
        return count
