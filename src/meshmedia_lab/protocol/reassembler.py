"""Collect packet fragments and rebuild the encoded payload."""

from .packet import Packet
from meshmedia_lab.media import ImageMetadata


class ReassemblyError(ValueError):
    """Raised when fragments cannot belong to the same transmission."""


class Reassembler:
    """Reassemble packets independently of their arrival order."""

    def __init__(self) -> None:
        self._image_id: int | None = None
        self._total_fragments: int | None = None
        self._metadata: ImageMetadata | None = None
        self._fragments: dict[int, bytes] = {}

    @property
    def is_complete(self) -> bool:
        return (
            self._total_fragments is not None
            and len(self._fragments) == self._total_fragments
        )

    @property
    def missing_fragments(self) -> tuple[int, ...]:
        if self._total_fragments is None:
            return ()
        return tuple(
            number
            for number in range(self._total_fragments)
            if number not in self._fragments
        )

    @property
    def metadata(self) -> ImageMetadata | None:
        return self._metadata

    def add(self, packet: Packet) -> None:
        if self._image_id is None:
            self._image_id = packet.image_id
            self._total_fragments = packet.total_fragments
            self._metadata = packet.metadata
        elif packet.image_id != self._image_id:
            raise ReassemblyError("packet belongs to another image")
        elif packet.total_fragments != self._total_fragments:
            raise ReassemblyError("packet has an inconsistent fragment count")
        elif packet.metadata != self._metadata:
            raise ReassemblyError("packet has inconsistent image metadata")

        previous = self._fragments.get(packet.fragment_number)
        if previous is not None and previous != packet.payload:
            raise ReassemblyError("duplicate fragment has different payload")
        self._fragments[packet.fragment_number] = packet.payload

    def assemble(self) -> bytes:
        if not self.is_complete:
            missing = ", ".join(str(number) for number in self.missing_fragments)
            raise ReassemblyError(f"missing fragments: {missing}")
        return b"".join(self._fragments[number] for number in range(self._total_fragments or 0))
