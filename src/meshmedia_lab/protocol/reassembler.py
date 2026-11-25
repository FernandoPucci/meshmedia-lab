"""Collect packet fragments and rebuild the encoded payload."""

from meshmedia_lab.media import ImageMetadata

from .descriptor import DescriptorError, TransmissionDescriptor, expected_encoded_length
from .packet import (
    FLAG_FIRST_FRAGMENT,
    FLAG_INLINE_DESCRIPTOR,
    FLAG_LAST_FRAGMENT,
    Packet,
)


class ReassemblyError(ValueError):
    """Raised when fragments cannot belong to the same transmission."""


class Reassembler:
    """Reassemble packets independently of their arrival order."""

    def __init__(self) -> None:
        self._image_id: int | None = None
        self._total_fragments: int | None = None
        self._metadata: ImageMetadata | None = None
        self._fragments: dict[int, bytes] = {}
        self._inline_descriptor = False
        self._descriptor: TransmissionDescriptor | None = None
        self._data_size = 0
        self._rejected = False

    @property
    def is_complete(self) -> bool:
        return (
            not self._rejected
            and self._total_fragments is not None
            and len(self._fragments) == self._total_fragments
            and (not self._inline_descriptor or self._descriptor is not None)
        )

    @property
    def missing_fragments(self) -> tuple[int, ...]:
        if self._rejected or self._total_fragments is None:
            return ()
        return tuple(
            number
            for number in range(self._total_fragments)
            if number not in self._fragments
        )

    @property
    def metadata(self) -> ImageMetadata | None:
        return self._descriptor.metadata if self._descriptor else self._metadata

    @property
    def descriptor(self) -> TransmissionDescriptor | None:
        return self._descriptor

    @property
    def rejected(self) -> bool:
        """Whether an extended transmission failed irreversibly."""

        return self._rejected

    def add(self, packet: Packet) -> None:
        if self._rejected:
            raise ReassemblyError("transmission has been rejected")
        if self._image_id is not None and packet.image_id != self._image_id:
            raise ReassemblyError("packet belongs to another image")
        try:
            self._add(packet)
        except (DescriptorError, ReassemblyError) as error:
            if self._inline_descriptor or packet.flags & FLAG_INLINE_DESCRIPTOR:
                self._rejected = True
                self._fragments.clear()
                self._descriptor = None
                self._data_size = 0
            raise ReassemblyError(str(error)) from error

    def _add(self, packet: Packet) -> None:
        inline = bool(packet.flags & FLAG_INLINE_DESCRIPTOR)
        if self._image_id is None:
            self._image_id = packet.image_id
            self._total_fragments = packet.total_fragments
            self._metadata = packet.metadata
            self._inline_descriptor = inline
        elif packet.total_fragments != self._total_fragments:
            raise ReassemblyError("packet has an inconsistent fragment count")
        elif packet.metadata != self._metadata:
            raise ReassemblyError("packet has inconsistent image metadata")
        elif inline != self._inline_descriptor:
            raise ReassemblyError("packet has inconsistent descriptor mode")

        payload = packet.payload
        descriptor = self._descriptor
        if inline:
            expected_size = expected_encoded_length(packet.metadata)
            expected_flags = FLAG_INLINE_DESCRIPTOR
            if packet.fragment_number == 0:
                expected_flags |= FLAG_FIRST_FRAGMENT
            if packet.fragment_number == packet.total_fragments - 1:
                expected_flags |= FLAG_LAST_FRAGMENT
            if packet.flags != expected_flags:
                raise ReassemblyError("invalid extended fragment flags")
            if packet.total_fragments > expected_size + 1:
                raise ReassemblyError("fragment count exceeds encoded length bound")
            if packet.fragment_number == 0:
                descriptor, payload = TransmissionDescriptor.from_payload(payload)
                if descriptor.metadata != packet.metadata:
                    raise ReassemblyError("descriptor and packet metadata differ")
                if self._descriptor is not None and descriptor != self._descriptor:
                    raise ReassemblyError("duplicate descriptor has different contents")
            elif not payload:
                raise ReassemblyError("extended data fragments cannot be empty")

        previous = self._fragments.get(packet.fragment_number)
        if previous is not None:
            if previous != payload:
                raise ReassemblyError("duplicate fragment has different payload")
            return
        new_size = self._data_size + len(payload)
        if inline:
            if new_size > expected_size:
                raise ReassemblyError("data exceeds descriptor encoded length")
            if len(self._fragments) + 1 == packet.total_fragments:
                if new_size != expected_size:
                    raise ReassemblyError("data is shorter than descriptor encoded length")
        self._descriptor = descriptor
        self._data_size = new_size
        self._fragments[packet.fragment_number] = payload

    def assemble(self) -> bytes:
        if self._rejected:
            raise ReassemblyError("transmission has been rejected")
        if not self.is_complete:
            missing = ", ".join(str(number) for number in self.missing_fragments)
            raise ReassemblyError(f"missing fragments: {missing}")
        return b"".join(self._fragments[number] for number in range(self._total_fragments or 0))
