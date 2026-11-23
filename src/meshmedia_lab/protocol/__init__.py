"""Packet format and reliability primitives."""

from .crc import crc16
from .fragmenter import Fragmenter
from .packet import (
    FLAG_FIRST_FRAGMENT,
    FLAG_LAST_FRAGMENT,
    Packet,
    PacketError,
)
from .reassembler import Reassembler, ReassemblyError

__all__ = [
    "Fragmenter",
    "FLAG_FIRST_FRAGMENT",
    "FLAG_LAST_FRAGMENT",
    "Packet",
    "PacketError",
    "Reassembler",
    "ReassemblyError",
    "crc16",
]
