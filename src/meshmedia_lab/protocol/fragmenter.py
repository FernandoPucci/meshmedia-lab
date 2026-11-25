"""Split an encoded image into protocol packets."""

from dataclasses import dataclass

from meshmedia_lab.media import ImageMetadata

from .descriptor import TransmissionDescriptor
from .packet import (
    FLAG_FIRST_FRAGMENT,
    FLAG_INLINE_DESCRIPTOR,
    FLAG_LAST_FRAGMENT,
    Packet,
    PacketError,
)


class FragmentationError(ValueError):
    """Raised when data cannot be divided into valid fragments."""


@dataclass(frozen=True, slots=True)
class Fragmenter:
    """Create fixed-size fragments for the local MVP."""

    max_payload_size: int = 64

    def __post_init__(self) -> None:
        if not 1 <= self.max_payload_size <= 0xFF:
            raise FragmentationError("max_payload_size must be between 1 and 255")

    def fragment(
        self,
        data: bytes,
        *,
        image_id: int,
        metadata: ImageMetadata,
        descriptor: TransmissionDescriptor | None = None,
    ) -> tuple[Packet, ...]:
        data = bytes(data)
        if descriptor is not None:
            if descriptor.metadata != metadata:
                raise FragmentationError("descriptor and packet metadata differ")
            if descriptor.encoded_length != len(data):
                raise FragmentationError("data length does not match descriptor")
            prefix = descriptor.to_bytes()
            if len(prefix) > self.max_payload_size:
                raise FragmentationError("payload limit cannot fit the descriptor")
            data = prefix + data
        total_fragments = max(1, (len(data) + self.max_payload_size - 1) // self.max_payload_size)
        if total_fragments > 0xFFFF:
            raise FragmentationError("encoded data requires too many fragments")

        packets = []
        for fragment_number, offset in enumerate(range(0, len(data), self.max_payload_size)):
            flags = FLAG_INLINE_DESCRIPTOR if descriptor is not None else 0
            if fragment_number == 0:
                flags |= FLAG_FIRST_FRAGMENT
            if fragment_number == total_fragments - 1:
                flags |= FLAG_LAST_FRAGMENT
            packets.append(
                Packet(
                    metadata=metadata,
                    image_id=image_id,
                    fragment_number=fragment_number,
                    total_fragments=total_fragments,
                    payload=data[offset : offset + self.max_payload_size],
                    flags=flags,
                )
            )

        if not packets:
            try:
                packets.append(
                    Packet(
                        metadata=metadata,
                        image_id=image_id,
                        fragment_number=0,
                        total_fragments=1,
                        payload=b"",
                        flags=FLAG_FIRST_FRAGMENT | FLAG_LAST_FRAGMENT,
                    )
                )
            except PacketError as error:
                raise FragmentationError(str(error)) from error
        return tuple(packets)
