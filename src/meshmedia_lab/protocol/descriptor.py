"""Strict, transport-independent Transmission Descriptor v1 (ADR 0004)."""

import struct
from dataclasses import dataclass

from meshmedia_lab.media import (
    CODEC_GRAYSCALE_PACKED,
    CODEC_RGB332,
    MEDIA_TYPE_IMAGE,
    PROTOCOL_VERSION,
    ImageMetadata,
)

DESCRIPTOR_MARKER = b"TD"
DESCRIPTOR_VERSION = 1
_BODY = struct.Struct("!BBBBHHHIBB")
DESCRIPTOR_BODY_SIZE = _BODY.size
DESCRIPTOR_PREFIX_SIZE = 3 + DESCRIPTOR_BODY_SIZE


class DescriptorError(ValueError):
    """Raised for unsupported or inconsistent descriptor data."""


def expected_encoded_length(metadata: ImageMetadata) -> int:
    """Validate the current descriptor codec contract before allocating data."""

    if not isinstance(metadata, ImageMetadata):
        raise DescriptorError("metadata must be ImageMetadata")
    for field in ("version", "media_type", "codec", "width", "height", "levels"):
        if type(getattr(metadata, field)) is not int:
            raise DescriptorError(f"{field} must be an integer")
    if metadata.version != PROTOCOL_VERSION:
        raise DescriptorError("unsupported MM1 protocol version")
    if metadata.media_type != MEDIA_TYPE_IMAGE:
        raise DescriptorError("unsupported descriptor media type")
    if metadata.codec == CODEC_GRAYSCALE_PACKED:
        if not 1 <= metadata.width <= 128 or not 1 <= metadata.height <= 128:
            raise DescriptorError("grayscale dimensions must be between 1 and 128")
        if metadata.levels not in (2, 4, 8, 16, 256):
            raise DescriptorError("unsupported grayscale levels")
        bits = metadata.width * metadata.height * (metadata.levels.bit_length() - 1)
        return (bits + 7) // 8
    if metadata.codec == CODEC_RGB332:
        if not 1 <= metadata.width <= 64 or not 1 <= metadata.height <= 64:
            raise DescriptorError("RGB332 dimensions must be between 1 and 64")
        if metadata.levels != 0:
            raise DescriptorError("RGB332 descriptor requires levels=0")
        return metadata.width * metadata.height
    raise DescriptorError("unsupported descriptor codec")


@dataclass(frozen=True, slots=True)
class TransmissionDescriptor:
    """Complete image contract; only NONE compression and empty extras in v1."""

    metadata: ImageMetadata
    encoded_length: int
    version: int = DESCRIPTOR_VERSION
    flags: int = 0
    compression_id: int = 0
    codec_parameters: bytes = b""

    def __post_init__(self) -> None:
        for field in ("version", "flags", "compression_id", "encoded_length"):
            if type(getattr(self, field)) is not int:
                raise DescriptorError(f"{field} must be an integer")
        if self.version != DESCRIPTOR_VERSION:
            raise DescriptorError("unsupported descriptor version")
        if self.flags != 0:
            raise DescriptorError("unsupported descriptor flags")
        if self.compression_id != 0:
            raise DescriptorError("unsupported descriptor compression")
        if not isinstance(self.codec_parameters, bytes) or self.codec_parameters:
            raise DescriptorError("descriptor v1 requires empty codec parameters")
        if self.encoded_length != expected_encoded_length(self.metadata):
            raise DescriptorError("encoded length does not match codec metadata")

    def to_bytes(self) -> bytes:
        """Serialize the complete 19-byte prefix (not a packet or CRC)."""

        body = _BODY.pack(
            self.version,
            self.flags,
            self.metadata.media_type,
            self.metadata.codec,
            self.metadata.width,
            self.metadata.height,
            self.metadata.levels,
            self.encoded_length,
            self.compression_id,
            len(self.codec_parameters),
        )
        return DESCRIPTOR_MARKER + bytes((len(body),)) + body

    @classmethod
    def from_bytes(cls, raw: bytes) -> "TransmissionDescriptor":
        """Parse exactly one prefix; trailing image data is not accepted here."""

        descriptor, data = cls.from_payload(raw)
        if data:
            raise DescriptorError("unexpected bytes after descriptor")
        return descriptor

    @classmethod
    def from_payload(cls, payload: bytes) -> tuple["TransmissionDescriptor", bytes]:
        """Parse a fragment-zero payload, returning descriptor and image bytes."""

        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise DescriptorError("descriptor payload must be bytes-like")
        size = payload.nbytes if isinstance(payload, memoryview) else len(payload)
        if not 3 <= size <= 255:
            raise DescriptorError("invalid descriptor payload size")
        payload = bytes(payload)
        if payload[:2] != DESCRIPTOR_MARKER:
            raise DescriptorError("invalid descriptor marker")
        length = payload[2]
        if length != DESCRIPTOR_BODY_SIZE:
            raise DescriptorError("descriptor body length must be 16")
        if len(payload) < 3 + length:
            raise DescriptorError("truncated descriptor body")
        (
            version, flags, media_type, codec, width, height, levels,
            encoded_length, compression_id, parameters_length,
        ) = _BODY.unpack(payload[3:DESCRIPTOR_PREFIX_SIZE])
        if parameters_length != 0:
            raise DescriptorError("descriptor v1 requires empty codec parameters")
        try:
            metadata = ImageMetadata(
                width=width,
                height=height,
                levels=levels,
                media_type=media_type,
                codec=codec,
            )
        except ValueError as error:
            raise DescriptorError(f"invalid descriptor metadata: {error}") from error
        descriptor = cls(
            metadata=metadata,
            encoded_length=encoded_length,
            version=version,
            flags=flags,
            compression_id=compression_id,
        )
        return descriptor, payload[DESCRIPTOR_PREFIX_SIZE:]
