"""Binary packet representation for the first protocol iteration."""

import struct
from dataclasses import dataclass

from meshmedia_lab.media import ImageMetadata

from .crc import crc16

MAGIC = b"MM"
FLAG_FIRST_FRAGMENT = 0x01
FLAG_LAST_FRAGMENT = 0x02
_HEADER = struct.Struct("!2sBBBBHHHHHHB")
_CRC = struct.Struct("!H")


class PacketError(ValueError):
    """Raised when a packet is malformed or fails integrity validation."""


@dataclass(frozen=True, slots=True)
class Packet:
    """One fragment and its minimal routing metadata."""

    metadata: ImageMetadata
    image_id: int
    fragment_number: int
    total_fragments: int
    payload: bytes
    flags: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", bytes(self.payload))
        if not 0 <= self.image_id <= 0xFFFF:
            raise PacketError("image_id must fit in 2 bytes")
        if not 0 <= self.fragment_number <= 0xFFFF:
            raise PacketError("fragment_number must fit in 2 bytes")
        if not 1 <= self.total_fragments <= 0xFFFF:
            raise PacketError("total_fragments must fit in 2 bytes")
        if self.fragment_number >= self.total_fragments:
            raise PacketError("fragment_number must be smaller than total_fragments")
        if not 0 <= self.flags <= 0xFF:
            raise PacketError("flags must fit in 1 byte")
        if len(self.payload) > 0xFF:
            raise PacketError("payload cannot exceed 255 bytes")

    def to_bytes(self) -> bytes:
        header = _HEADER.pack(
            MAGIC,
            self.metadata.version,
            self.metadata.media_type,
            self.metadata.codec,
            self.flags,
            self.image_id,
            self.fragment_number,
            self.total_fragments,
            self.metadata.width,
            self.metadata.height,
            self.metadata.levels,
            len(self.payload),
        )
        body = header + self.payload
        return body + _CRC.pack(crc16(body))

    @classmethod
    def from_bytes(cls, raw: bytes) -> "Packet":
        raw = bytes(raw)
        minimum_size = _HEADER.size + _CRC.size
        if len(raw) < minimum_size:
            raise PacketError("packet is shorter than its header and CRC")

        (
            magic,
            version,
            media_type,
            codec,
            flags,
            image_id,
            fragment_number,
            total_fragments,
            width,
            height,
            levels,
            payload_length,
        ) = _HEADER.unpack(raw[: _HEADER.size])
        if magic != MAGIC:
            raise PacketError("invalid packet magic")

        expected_size = _HEADER.size + payload_length + _CRC.size
        if len(raw) != expected_size:
            raise PacketError("packet length does not match its payload length")

        body = raw[:-_CRC.size]
        received_crc = _CRC.unpack(raw[-_CRC.size :])[0]
        if crc16(body) != received_crc:
            raise PacketError("packet CRC does not match")

        try:
            metadata = ImageMetadata(
                width=width,
                height=height,
                levels=levels,
                version=version,
                media_type=media_type,
                codec=codec,
            )
        except ValueError as error:
            raise PacketError("invalid image metadata") from error

        return cls(
            metadata=metadata,
            image_id=image_id,
            fragment_number=fragment_number,
            total_fragments=total_fragments,
            payload=raw[_HEADER.size : -_CRC.size],
            flags=flags,
        )
