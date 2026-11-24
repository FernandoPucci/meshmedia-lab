"""Local UDP framing for the isolated RGB332 experiment.

This format is deliberately separate from MM1 v1. It is only a localhost
test harness and must not be treated as a protocol packet.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from meshmedia_lab.codec.rgb332 import MAX_RGB332_HEIGHT, MAX_RGB332_WIDTH

MAGIC = b"R332"
VERSION = 1
_HEADER = struct.Struct("!4sBHHHHHB")


class Rgb332DatagramError(ValueError):
    """Raised when a local RGB332 datagram is invalid."""


@dataclass(frozen=True, slots=True)
class Rgb332Datagram:
    """One fragment in the local, non-MM1 RGB332 test harness."""

    image_id: int
    fragment_number: int
    total_fragments: int
    width: int
    height: int
    payload: bytes

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", bytes(self.payload))
        if not 0 <= self.image_id <= 0xFFFF:
            raise Rgb332DatagramError("image_id must fit in 2 bytes")
        if not 0 <= self.fragment_number <= 0xFFFF:
            raise Rgb332DatagramError("fragment_number must fit in 2 bytes")
        if not 1 <= self.total_fragments <= 0xFFFF:
            raise Rgb332DatagramError("total_fragments must fit in 2 bytes")
        if self.fragment_number >= self.total_fragments:
            raise Rgb332DatagramError(
                "fragment_number must be smaller than total_fragments"
            )
        if not 1 <= self.width <= MAX_RGB332_WIDTH:
            raise Rgb332DatagramError(
                f"width must be between 1 and {MAX_RGB332_WIDTH}"
            )
        if not 1 <= self.height <= MAX_RGB332_HEIGHT:
            raise Rgb332DatagramError(
                f"height must be between 1 and {MAX_RGB332_HEIGHT}"
            )
        if len(self.payload) > 0xFF:
            raise Rgb332DatagramError("payload cannot exceed 255 bytes")

    def to_bytes(self) -> bytes:
        header = _HEADER.pack(
            MAGIC,
            VERSION,
            self.image_id,
            self.fragment_number,
            self.total_fragments,
            self.width,
            self.height,
            len(self.payload),
        )
        return header + self.payload

    @classmethod
    def from_bytes(cls, raw: bytes) -> "Rgb332Datagram":
        raw = bytes(raw)
        if len(raw) < _HEADER.size:
            raise Rgb332DatagramError("datagram is shorter than its header")

        (
            magic,
            version,
            image_id,
            fragment_number,
            total_fragments,
            width,
            height,
            payload_length,
        ) = _HEADER.unpack(raw[: _HEADER.size])
        if magic != MAGIC:
            raise Rgb332DatagramError("invalid RGB332 datagram magic")
        if version != VERSION:
            raise Rgb332DatagramError("unsupported RGB332 datagram version")

        expected_size = _HEADER.size + payload_length
        if len(raw) != expected_size:
            raise Rgb332DatagramError("datagram length does not match its payload")

        return cls(
            image_id=image_id,
            fragment_number=fragment_number,
            total_fragments=total_fragments,
            width=width,
            height=height,
            payload=raw[_HEADER.size :],
        )


def fragment_data(
    data: bytes,
    *,
    image_id: int,
    width: int,
    height: int,
    payload_size: int = 64,
) -> tuple[Rgb332Datagram, ...]:
    """Split RGB332 bytes into local datagrams without using MM1."""

    if not 1 <= payload_size <= 0xFF:
        raise Rgb332DatagramError("payload_size must be between 1 and 255")
    data = bytes(data)
    total_fragments = max(1, (len(data) + payload_size - 1) // payload_size)
    if total_fragments > 0xFFFF:
        raise Rgb332DatagramError("data requires too many fragments")

    return tuple(
        Rgb332Datagram(
            image_id=image_id,
            fragment_number=fragment_number,
            total_fragments=total_fragments,
            width=width,
            height=height,
            payload=data[offset : offset + payload_size],
        )
        for fragment_number, offset in enumerate(
            range(0, len(data), payload_size)
        )
    ) or (
        Rgb332Datagram(
            image_id=image_id,
            fragment_number=0,
            total_fragments=1,
            width=width,
            height=height,
            payload=b"",
        ),
    )


__all__ = [
    "MAGIC",
    "VERSION",
    "Rgb332Datagram",
    "Rgb332DatagramError",
    "fragment_data",
]
