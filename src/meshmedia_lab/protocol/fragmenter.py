"""Split an encoded image into protocol packets."""

from dataclasses import dataclass

from .packet import Packet, PacketError


class FragmentationError(ValueError):
    """Raised when data cannot be divided into valid fragments."""


@dataclass(frozen=True, slots=True)
class Fragmenter:
    """Create fixed-size fragments for the local MVP."""

    max_payload_size: int = 64

    def __post_init__(self) -> None:
        if not 1 <= self.max_payload_size <= 0xFF:
            raise FragmentationError("max_payload_size must be between 1 and 255")

    def fragment(self, data: bytes, *, image_id: int) -> tuple[Packet, ...]:
        data = bytes(data)
        total_fragments = max(1, (len(data) + self.max_payload_size - 1) // self.max_payload_size)
        if total_fragments > 0xFFFF:
            raise FragmentationError("encoded data requires too many fragments")

        packets = []
        for fragment_number, offset in enumerate(range(0, len(data), self.max_payload_size)):
            packets.append(
                Packet(
                    image_id=image_id,
                    fragment_number=fragment_number,
                    total_fragments=total_fragments,
                    payload=data[offset : offset + self.max_payload_size],
                )
            )

        if not packets:
            try:
                packets.append(
                    Packet(
                        image_id=image_id,
                        fragment_number=0,
                        total_fragments=1,
                        payload=b"",
                    )
                )
            except PacketError as error:
                raise FragmentationError(str(error)) from error
        return tuple(packets)
