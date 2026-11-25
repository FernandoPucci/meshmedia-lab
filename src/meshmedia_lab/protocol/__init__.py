"""Packet format and reliability primitives."""

from .crc import crc16
from .descriptor import DescriptorError, TransmissionDescriptor
from .fec import (
    FEC_FRAME_HEADER_SIZE,
    FEC_FRAME_MAGIC,
    FEC_FRAME_VERSION,
    FecFrameError,
    FecPacketizationError,
    FecPacketizer,
    FecReassembler,
    FecReassemblyError,
    FecSymbolFrame,
)
from .fragmenter import Fragmenter
from .packet import (
    FLAG_FEC,
    FLAG_FIRST_FRAGMENT,
    FLAG_INLINE_DESCRIPTOR,
    FLAG_LAST_FRAGMENT,
    Packet,
    PacketError,
)
from .reassembler import Reassembler, ReassemblyError

__all__ = [
    "FEC_FRAME_HEADER_SIZE",
    "FEC_FRAME_MAGIC",
    "FEC_FRAME_VERSION",
    "FLAG_FEC",
    "FLAG_FIRST_FRAGMENT",
    "FLAG_INLINE_DESCRIPTOR",
    "FLAG_LAST_FRAGMENT",
    "DescriptorError",
    "FecFrameError",
    "FecPacketizationError",
    "FecPacketizer",
    "FecReassembler",
    "FecReassemblyError",
    "FecSymbolFrame",
    "Fragmenter",
    "Packet",
    "PacketError",
    "Reassembler",
    "ReassemblyError",
    "TransmissionDescriptor",
    "crc16",
]
