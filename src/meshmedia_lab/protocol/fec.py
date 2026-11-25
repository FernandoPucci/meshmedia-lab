"""Experimental FEC extension carried inside MM1 v1 packets.

The ordinary MM1 header and CRC are reused unchanged.  FEC-enabled packets
are selected explicitly with ``FLAG_FEC`` and carry a self-describing symbol
frame in their payload.  This keeps the legacy payload path byte-compatible
while making the experimental extension rejectable by an implementation that
does not understand it.
"""

import struct
from dataclasses import dataclass

from meshmedia_lab.fec import (
    FecBlockMetadata,
    FecConfig,
    FecDecoder,
    FecInputError,
    FecSymbol,
    FecTransmission,
    IncompleteBlockPolicy,
    PaddingPolicy,
    block_metadata_for_index,
    validate_symbol,
)
from meshmedia_lab.media import ImageMetadata

from .descriptor import DescriptorError, TransmissionDescriptor
from .packet import (
    FLAG_FEC,
    FLAG_FIRST_FRAGMENT,
    FLAG_INLINE_DESCRIPTOR,
    FLAG_LAST_FRAGMENT,
    Packet,
)

FEC_FRAME_MAGIC = b"FC"
FEC_FRAME_VERSION = 1
_FEC_FRAME_HEADER = struct.Struct("!2sBBHHHHHBBIHHIIH")
FEC_FRAME_HEADER_SIZE = _FEC_FRAME_HEADER.size

_PADDING_TO_BYTE = {
    PaddingPolicy.REJECT: 0,
    PaddingPolicy.ZERO_PAD: 1,
}
_BYTE_TO_PADDING = {value: key for key, value in _PADDING_TO_BYTE.items()}
_INCOMPLETE_TO_BYTE = {
    IncompleteBlockPolicy.REJECT: 0,
    IncompleteBlockPolicy.PAD_TO_K: 1,
}
_BYTE_TO_INCOMPLETE = {
    value: key for key, value in _INCOMPLETE_TO_BYTE.items()
}


class FecFrameError(ValueError):
    """Raised when an FEC symbol frame is malformed."""


class FecPacketizationError(ValueError):
    """Raised when FEC symbols cannot fit in MM1 packets."""


class FecReassemblyError(ValueError):
    """Raised when FEC packets cannot form a recoverable transmission."""


@dataclass(frozen=True, slots=True)
class FecSymbolFrame:
    """Self-describing wire representation of one FEC symbol."""

    config: FecConfig
    encoded_length: int
    total_blocks: int
    block_index: int
    metadata: FecBlockMetadata
    symbol: FecSymbol

    def __post_init__(self) -> None:
        if not isinstance(self.config, FecConfig):
            raise FecFrameError("config must be FecConfig")
        if type(self.encoded_length) is not int or self.encoded_length < 0:
            raise FecFrameError("encoded_length must be a non-negative integer")
        if type(self.total_blocks) is not int or self.total_blocks <= 0:
            raise FecFrameError("total_blocks must be a positive integer")
        if type(self.block_index) is not int or self.block_index < 0:
            raise FecFrameError("block_index must be a non-negative integer")
        if not isinstance(self.metadata, FecBlockMetadata):
            raise FecFrameError("metadata must be FecBlockMetadata")
        if not isinstance(self.symbol, FecSymbol):
            raise FecFrameError("symbol must be FecSymbol")

        try:
            expected_metadata = block_metadata_for_index(
                self.encoded_length,
                self.config,
                self.block_index,
                total_blocks=self.total_blocks,
            )
        except FecInputError as error:
            raise FecFrameError(str(error)) from error
        if self.metadata != expected_metadata:
            raise FecFrameError(
                "block metadata does not match encoded_length and block_index"
            )
        try:
            validate_symbol(self.symbol, self.config)
        except (FecInputError, ValueError) as error:
            raise FecFrameError(str(error)) from error

        for field_name, value, maximum in (
            ("encoded_length", self.encoded_length, 0xFFFFFFFF),
            ("total_blocks", self.total_blocks, 0xFFFF),
            ("block_index", self.block_index, 0xFFFF),
            ("original_length", self.metadata.original_length, 0xFFFFFFFF),
            ("padding_length", self.metadata.padding_length, 0xFFFFFFFF),
            ("symbol_index", self.symbol.index, 0xFFFF),
            ("symbol_size", self.config.symbol_size, 0xFFFF),
            ("data_symbols", self.config.data_symbols, 0xFFFF),
            ("repair_symbols", self.config.repair_symbols, 0xFFFF),
            ("block_symbols", self.config.block_symbols, 0xFFFF),
            ("interleaving_depth", self.config.interleaving_depth, 0xFFFF),
        ):
            if value > maximum:
                raise FecFrameError(f"{field_name} does not fit the FEC frame")

        if len(self.config.algorithm_id.encode("utf-8")) > 0xFF:
            raise FecFrameError("algorithm_id is too long for the FEC frame")

    def to_bytes(self) -> bytes:
        """Serialize one FEC frame, excluding the surrounding MM1 packet."""

        try:
            algorithm_id = self.config.algorithm_id.encode("ascii")
        except UnicodeEncodeError as error:
            raise FecFrameError("algorithm_id must contain ASCII characters") from error

        try:
            header = _FEC_FRAME_HEADER.pack(
                FEC_FRAME_MAGIC,
                FEC_FRAME_VERSION,
                len(algorithm_id),
                self.config.symbol_size,
                self.config.data_symbols,
                self.config.repair_symbols,
                self.config.block_symbols,
                self.config.interleaving_depth,
                _PADDING_TO_BYTE[self.config.padding_policy],
                _INCOMPLETE_TO_BYTE[self.config.incomplete_block_policy],
                self.encoded_length,
                self.total_blocks,
                self.block_index,
                self.metadata.original_length,
                self.metadata.padding_length,
                self.symbol.index,
            )
        except (KeyError, struct.error) as error:
            raise FecFrameError("invalid FEC frame fields") from error
        return header + algorithm_id + self.symbol.data

    @classmethod
    def from_bytes(cls, raw: bytes) -> "FecSymbolFrame":
        """Parse exactly one FEC frame."""

        raw = bytes(raw)
        if len(raw) < FEC_FRAME_HEADER_SIZE:
            raise FecFrameError("FEC frame is shorter than its header")

        (
            magic,
            version,
            algorithm_length,
            symbol_size,
            data_symbols,
            repair_symbols,
            block_symbols,
            interleaving_depth,
            padding_policy,
            incomplete_policy,
            encoded_length,
            total_blocks,
            block_index,
            original_length,
            padding_length,
            symbol_index,
        ) = _FEC_FRAME_HEADER.unpack(raw[:FEC_FRAME_HEADER_SIZE])

        if magic != FEC_FRAME_MAGIC:
            raise FecFrameError("invalid FEC frame magic")
        if version != FEC_FRAME_VERSION:
            raise FecFrameError("unsupported FEC frame version")
        try:
            algorithm_start = FEC_FRAME_HEADER_SIZE
            algorithm_end = algorithm_start + algorithm_length
            algorithm_id = raw[algorithm_start:algorithm_end].decode("ascii")
        except UnicodeDecodeError as error:
            raise FecFrameError("algorithm_id must contain ASCII characters") from error

        expected_size = FEC_FRAME_HEADER_SIZE + algorithm_length + symbol_size
        if len(raw) != expected_size:
            raise FecFrameError("FEC frame length does not match symbol_size")
        if padding_policy not in _BYTE_TO_PADDING:
            raise FecFrameError("unsupported FEC padding policy")
        if incomplete_policy not in _BYTE_TO_INCOMPLETE:
            raise FecFrameError("unsupported FEC incomplete-block policy")

        try:
            config = FecConfig(
                algorithm_id=algorithm_id,
                symbol_size=symbol_size,
                data_symbols=data_symbols,
                repair_symbols=repair_symbols,
                block_symbols=block_symbols,
                interleaving_depth=interleaving_depth,
                padding_policy=_BYTE_TO_PADDING[padding_policy],
                incomplete_block_policy=_BYTE_TO_INCOMPLETE[incomplete_policy],
            )
            metadata = FecBlockMetadata(
                original_length=original_length,
                padding_length=padding_length,
            )
            symbol = FecSymbol(
                index=symbol_index,
                data=raw[FEC_FRAME_HEADER_SIZE + algorithm_length :],
            )
            return cls(
                config=config,
                encoded_length=encoded_length,
                total_blocks=total_blocks,
                block_index=block_index,
                metadata=metadata,
                symbol=symbol,
            )
        except (FecInputError, ValueError) as error:
            raise FecFrameError(str(error)) from error


@dataclass(frozen=True, slots=True)
class FecPacketizer:
    """Turn a prepared FEC transmission into one-symbol MM1 packets."""

    max_payload_size: int = 64

    def __post_init__(self) -> None:
        if not 1 <= self.max_payload_size <= 0xFF:
            raise FecPacketizationError(
                "max_payload_size must be between 1 and 255"
            )

    def packetize(
        self,
        transmission: FecTransmission,
        *,
        image_id: int,
        metadata: ImageMetadata,
        descriptor: TransmissionDescriptor | None = None,
    ) -> tuple[Packet, ...]:
        if not isinstance(transmission, FecTransmission):
            raise FecPacketizationError("transmission must be FecTransmission")
        if not isinstance(metadata, ImageMetadata):
            raise FecPacketizationError("metadata must be ImageMetadata")
        if descriptor is not None:
            if descriptor.metadata != metadata:
                raise FecPacketizationError("descriptor and packet metadata differ")
            if descriptor.encoded_length != transmission.encoded_length:
                raise FecPacketizationError(
                    "descriptor length does not match FEC transmission"
                )

        total_packets = transmission.total_symbols
        if not 1 <= total_packets <= 0xFFFF:
            raise FecPacketizationError(
                "FEC transmission requires an invalid number of packets"
            )

        packets: list[Packet] = []
        sequence = 0
        for block in transmission.blocks:
            for symbol in block.symbols:
                frame = FecSymbolFrame(
                    config=transmission.config,
                    encoded_length=transmission.encoded_length,
                    total_blocks=transmission.total_blocks,
                    block_index=block.block_index,
                    metadata=block.metadata,
                    symbol=symbol,
                )
                payload = frame.to_bytes()
                if sequence == 0 and descriptor is not None:
                    payload = descriptor.to_bytes() + payload
                if len(payload) > self.max_payload_size:
                    raise FecPacketizationError(
                        "payload limit cannot fit the FEC symbol frame"
                    )

                flags = FLAG_FEC
                if descriptor is not None:
                    flags |= FLAG_INLINE_DESCRIPTOR
                if sequence == 0:
                    flags |= FLAG_FIRST_FRAGMENT
                if sequence == total_packets - 1:
                    flags |= FLAG_LAST_FRAGMENT
                packets.append(
                    Packet(
                        metadata=metadata,
                        image_id=image_id,
                        fragment_number=sequence,
                        total_fragments=total_packets,
                        payload=payload,
                        flags=flags,
                    )
                )
                sequence += 1
        return tuple(packets)


class FecReassembler:
    """Collect FEC symbol packets and recover the encoded byte stream."""

    def __init__(self) -> None:
        self._image_id: int | None = None
        self._total_fragments: int | None = None
        self._metadata: ImageMetadata | None = None
        self._config: FecConfig | None = None
        self._encoded_length: int | None = None
        self._total_blocks: int | None = None
        self._inline_descriptor = False
        self._descriptor: TransmissionDescriptor | None = None
        self._frames: dict[tuple[int, int], FecSymbolFrame] = {}
        self._fragment_frames: dict[int, tuple[int, int]] = {}
        self._rejected = False

    @property
    def rejected(self) -> bool:
        return self._rejected

    @property
    def metadata(self) -> ImageMetadata | None:
        return self._metadata

    @property
    def descriptor(self) -> TransmissionDescriptor | None:
        return self._descriptor

    @property
    def config(self) -> FecConfig | None:
        return self._config

    @property
    def expected_packets(self) -> int | None:
        return self._total_fragments

    @property
    def total_blocks(self) -> int | None:
        """Return the advertised number of FEC blocks, when known."""

        return self._total_blocks

    @property
    def received_symbols(self) -> int:
        return len(self._frames)

    @property
    def is_complete(self) -> bool:
        return (
            not self._rejected
            and self._total_fragments is not None
            and len(self._frames) == self._total_fragments
            and (not self._inline_descriptor or self._descriptor is not None)
        )

    @property
    def can_decode(self) -> bool:
        if self._rejected or self._config is None or self._total_blocks is None:
            return False
        if self._inline_descriptor and self._descriptor is None:
            return False
        return all(
            sum(1 for block_index, _ in self._frames if block_index == index)
            >= self._config.data_symbols
            for index in range(self._total_blocks)
        )

    @property
    def missing_symbols(self) -> tuple[tuple[int, int], ...]:
        if self._config is None or self._total_blocks is None:
            return ()
        return tuple(
            (block_index, symbol_index)
            for block_index in range(self._total_blocks)
            for symbol_index in range(self._config.block_symbols)
            if (block_index, symbol_index) not in self._frames
        )

    def add(self, packet: Packet) -> None:
        if self._rejected:
            raise FecReassemblyError("FEC transmission has been rejected")
        try:
            self._add(packet)
        except (FecFrameError, DescriptorError, FecInputError, FecReassemblyError):
            self._rejected = True
            self._frames.clear()
            raise

    def _add(self, packet: Packet) -> None:
        if not isinstance(packet, Packet):
            raise FecReassemblyError("value must be Packet")
        if not packet.flags & FLAG_FEC:
            raise FecReassemblyError("packet is not marked as FEC")

        inline_descriptor = bool(packet.flags & FLAG_INLINE_DESCRIPTOR)
        if self._image_id is None:
            self._image_id = packet.image_id
            self._total_fragments = packet.total_fragments
            self._metadata = packet.metadata
            self._inline_descriptor = inline_descriptor
        else:
            if packet.image_id != self._image_id:
                raise FecReassemblyError("packet belongs to another transmission")
            if packet.total_fragments != self._total_fragments:
                raise FecReassemblyError("packet has an inconsistent fragment count")
            if packet.metadata != self._metadata:
                raise FecReassemblyError("packet has inconsistent image metadata")
            if inline_descriptor != self._inline_descriptor:
                raise FecReassemblyError("packet has inconsistent descriptor mode")

        payload = packet.payload
        if inline_descriptor and packet.fragment_number == 0:
            descriptor, payload = TransmissionDescriptor.from_payload(payload)
            if descriptor.metadata != packet.metadata:
                raise FecReassemblyError("descriptor and packet metadata differ")
            if self._descriptor is not None and self._descriptor != descriptor:
                raise FecReassemblyError("duplicate descriptor has different contents")
            self._descriptor = descriptor

        frame = FecSymbolFrame.from_bytes(payload)
        if frame.config != self._config and self._config is not None:
            raise FecReassemblyError("packet has an inconsistent FEC configuration")
        if (
            self._encoded_length is not None
            and frame.encoded_length != self._encoded_length
        ):
            raise FecReassemblyError("packet has an inconsistent encoded length")
        if (
            self._total_blocks is not None
            and frame.total_blocks != self._total_blocks
        ):
            raise FecReassemblyError("packet has an inconsistent block count")

        expected_packets = frame.total_blocks * frame.config.block_symbols
        if packet.total_fragments != expected_packets:
            raise FecReassemblyError(
                "packet count does not match the FEC configuration"
            )
        expected_fragment = (
            frame.block_index * frame.config.block_symbols + frame.symbol.index
        )
        if packet.fragment_number != expected_fragment:
            raise FecReassemblyError(
                "fragment number does not match the FEC block and symbol index"
            )

        expected_flags = FLAG_FEC
        if self._inline_descriptor:
            expected_flags |= FLAG_INLINE_DESCRIPTOR
        if packet.fragment_number == 0:
            expected_flags |= FLAG_FIRST_FRAGMENT
        if packet.fragment_number == packet.total_fragments - 1:
            expected_flags |= FLAG_LAST_FRAGMENT
        if packet.flags != expected_flags:
            raise FecReassemblyError("invalid FEC fragment flags")

        if (
            self._descriptor is not None
            and self._descriptor.encoded_length != frame.encoded_length
        ):
            raise FecReassemblyError("descriptor and FEC encoded lengths differ")

        self._config = frame.config
        self._encoded_length = frame.encoded_length
        self._total_blocks = frame.total_blocks

        key = (frame.block_index, frame.symbol.index)
        previous_key = self._fragment_frames.get(packet.fragment_number)
        if previous_key is not None and previous_key != key:
            raise FecReassemblyError(
                "fragment number was reused for another FEC symbol"
            )
        previous = self._frames.get(key)
        if previous is not None:
            if previous != frame:
                raise FecReassemblyError(
                    "duplicate FEC symbol has different contents"
                )
            return

        self._fragment_frames[packet.fragment_number] = key
        self._frames[key] = frame

    def decode(self, decoder: FecDecoder) -> bytes:
        """Decode all blocks and return the original codec byte stream."""

        if self._rejected:
            raise FecReassemblyError("FEC transmission has been rejected")
        if self._config is None or self._total_blocks is None:
            raise FecReassemblyError("no FEC symbols have been received")
        if self._encoded_length is None:
            raise FecReassemblyError("FEC transmission has no encoded length")
        if not isinstance(decoder, FecDecoder):
            raise FecReassemblyError("decoder must implement FecDecoder")
        if not self.can_decode:
            missing = ", ".join(
                f"{block}:{symbol}" for block, symbol in self.missing_symbols
            )
            raise FecReassemblyError(
                f"insufficient symbols for FEC recovery; missing: {missing}"
            )

        source_blocks: list[bytes] = []
        for block_index in range(self._total_blocks):
            block_frames = tuple(
                frame
                for (candidate_block, _), frame in self._frames.items()
                if candidate_block == block_index
            )
            received = tuple(
                frame.symbol for frame in sorted(
                    block_frames,
                    key=lambda item: item.symbol.index,
                )
            )
            erasures = tuple(
                symbol_index
                for symbol_index in range(self._config.block_symbols)
                if (block_index, symbol_index) not in self._frames
            )
            metadata = block_metadata_for_index(
                self._encoded_length,
                self._config,
                block_index,
                total_blocks=self._total_blocks,
            )
            try:
                result = decoder.decode(
                    received,
                    erasures,
                    self._config,
                    metadata,
                )
            except ValueError as error:
                raise FecReassemblyError(
                    f"FEC decoder rejected block {block_index}: {error}"
                ) from error
            if not result.success or result.source_block is None:
                reason = result.reason.value if result.reason is not None else "unknown"
                raise FecReassemblyError(
                    f"FEC recovery failed for block {block_index}: {reason}"
                )
            source_blocks.append(result.source_block)

        source = b"".join(source_blocks)
        if len(source) != self._encoded_length:
            raise FecReassemblyError(
                "FEC recovery produced an unexpected encoded length"
            )
        return source


__all__ = [
    "FEC_FRAME_HEADER_SIZE",
    "FEC_FRAME_MAGIC",
    "FEC_FRAME_VERSION",
    "FecFrameError",
    "FecPacketizationError",
    "FecPacketizer",
    "FecReassembler",
    "FecReassemblyError",
    "FecSymbolFrame",
]
