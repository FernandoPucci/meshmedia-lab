"""Preparation of encoded image bytes for FEC transmission.

This module coordinates the algorithm-independent FEC contract with a byte
stream produced by an image codec.  It deliberately does not know about MM1
packets, CRCs or transports.
"""

from dataclasses import dataclass
from typing import TypeAlias

from .contract import (
    BytesLike,
    EncodedBlock,
    FecBlockMetadata,
    FecConfig,
    FecEncoder,
    FecInputError,
    IncompleteBlockPolicy,
    PaddingPolicy,
)

FecBlockSequence: TypeAlias = tuple["FecTransmissionBlock", ...]


def _coerce_source_bytes(source_data: BytesLike) -> bytes:
    if not isinstance(source_data, (bytes, bytearray, memoryview)):
        raise FecInputError("source_data must be bytes-like")
    try:
        return bytes(source_data)
    except (TypeError, ValueError) as error:
        raise FecInputError("source_data must be bytes-like") from error


def fec_block_count(encoded_length: int, config: FecConfig) -> int:
    """Return the number of FEC blocks needed for an encoded byte stream."""

    if not isinstance(config, FecConfig):
        raise FecInputError("config must be FecConfig")
    if type(encoded_length) is not int:
        raise FecInputError("encoded_length must be an integer")
    if encoded_length < 0:
        raise FecInputError("encoded_length cannot be negative")
    capacity = config.source_capacity
    return max(1, (encoded_length + capacity - 1) // capacity)


def block_metadata_for_index(
    encoded_length: int,
    config: FecConfig,
    block_index: int,
    *,
    total_blocks: int | None = None,
) -> FecBlockMetadata:
    """Derive the local metadata for one position in a transmission.

    The total encoded length and the fixed source capacity make the final
    block's original and padding lengths deterministic.  The same derivation
    is used by TX and RX; no contract type is duplicated or serialized here.
    """

    if type(block_index) is not int:
        raise FecInputError("block_index must be an integer")
    if block_index < 0:
        raise FecInputError("block_index cannot be negative")

    expected_blocks = fec_block_count(encoded_length, config)
    if total_blocks is not None:
        if type(total_blocks) is not int:
            raise FecInputError("total_blocks must be an integer")
        if total_blocks != expected_blocks:
            raise FecInputError("total_blocks does not match encoded_length")
    if block_index >= expected_blocks:
        raise FecInputError("block_index is outside the transmission")

    capacity = config.source_capacity
    original_length = min(
        capacity,
        max(0, encoded_length - block_index * capacity),
    )
    padding_length = capacity - original_length

    if (
        padding_length > 0
        and config.padding_policy is PaddingPolicy.REJECT
    ):
        raise FecInputError("transmission requires padding rejected by policy")

    source_count = (
        0
        if original_length == 0
        else (original_length + config.symbol_size - 1) // config.symbol_size
    )
    if (
        source_count < config.data_symbols
        and config.incomplete_block_policy is IncompleteBlockPolicy.REJECT
    ):
        raise FecInputError(
            "transmission contains an incomplete block rejected by policy"
        )

    return FecBlockMetadata(
        original_length=original_length,
        padding_length=padding_length,
    )


@dataclass(frozen=True, slots=True)
class FecTransmissionBlock:
    """One ordered FEC block in a transmission."""

    block_index: int
    total_blocks: int
    encoded_block: EncodedBlock

    def __post_init__(self) -> None:
        if type(self.block_index) is not int or self.block_index < 0:
            raise FecInputError("block_index must be a non-negative integer")
        if type(self.total_blocks) is not int or self.total_blocks <= 0:
            raise FecInputError("total_blocks must be a positive integer")
        if self.block_index >= self.total_blocks:
            raise FecInputError("block_index must be smaller than total_blocks")
        if not isinstance(self.encoded_block, EncodedBlock):
            raise FecInputError("encoded_block must be EncodedBlock")

    @property
    def metadata(self) -> FecBlockMetadata:
        """Return the local metadata of the wrapped encoded block."""

        return self.encoded_block.metadata

    @property
    def source_symbols(self):
        """Return source symbols without introducing a second symbol type."""

        return self.encoded_block.source_symbols

    @property
    def repair_symbols(self):
        """Return repair symbols without introducing a second symbol type."""

        return self.encoded_block.repair_symbols

    @property
    def symbols(self):
        """Return all symbols in their deterministic codeword order."""

        return tuple(
            sorted(
                self.source_symbols + self.repair_symbols,
                key=lambda symbol: symbol.index,
            )
        )


@dataclass(frozen=True, slots=True)
class FecTransmission:
    """Structured FEC preparation result for one encoded image stream."""

    encoded_length: int
    config: FecConfig
    blocks: FecBlockSequence

    def __post_init__(self) -> None:
        if type(self.encoded_length) is not int:
            raise FecInputError("encoded_length must be an integer")
        if self.encoded_length < 0:
            raise FecInputError("encoded_length cannot be negative")
        if not isinstance(self.config, FecConfig):
            raise FecInputError("config must be FecConfig")

        blocks = tuple(self.blocks)
        expected_blocks = fec_block_count(self.encoded_length, self.config)
        if len(blocks) != expected_blocks:
            raise FecInputError("blocks do not match encoded_length")

        for index, block in enumerate(blocks):
            if not isinstance(block, FecTransmissionBlock):
                raise FecInputError("blocks must contain FecTransmissionBlock values")
            if block.block_index != index or block.total_blocks != expected_blocks:
                raise FecInputError("blocks must be contiguous and ordered")
            block.encoded_block.validate(self.config)
            expected_metadata = block_metadata_for_index(
                self.encoded_length,
                self.config,
                index,
                total_blocks=expected_blocks,
            )
            if block.metadata != expected_metadata:
                raise FecInputError(
                    "block metadata does not match encoded_length and block index"
                )

        if sum(block.metadata.original_length for block in blocks) != self.encoded_length:
            raise FecInputError("block metadata does not preserve encoded_length")

        object.__setattr__(self, "blocks", blocks)

    @property
    def total_blocks(self) -> int:
        """Return the number of source blocks."""

        return len(self.blocks)

    @property
    def total_symbols(self) -> int:
        """Return source plus repair symbols across all blocks."""

        return self.total_blocks * self.config.block_symbols

    @property
    def repair_symbol_count(self) -> int:
        """Return the number of repair symbols produced for the stream."""

        return self.total_blocks * self.config.repair_symbols


def prepare_fec_transmission(
    source_data: BytesLike,
    config: FecConfig,
    encoder: FecEncoder,
) -> FecTransmission:
    """Partition codec bytes and encode every block through ``FecEncoder``."""

    if not isinstance(config, FecConfig):
        raise FecInputError("config must be FecConfig")
    if not isinstance(encoder, FecEncoder):
        raise FecInputError("encoder must implement FecEncoder")

    source = _coerce_source_bytes(source_data)
    capacity = config.source_capacity
    total_blocks = fec_block_count(len(source), config)
    blocks: list[FecTransmissionBlock] = []

    for block_index in range(total_blocks):
        offset = block_index * capacity
        source_block = source[offset : offset + capacity]
        encoded_block = encoder.encode(source_block, config)
        if not isinstance(encoded_block, EncodedBlock):
            raise FecInputError("FecEncoder.encode must return EncodedBlock")
        encoded_block.validate(config)
        blocks.append(
            FecTransmissionBlock(
                block_index=block_index,
                total_blocks=total_blocks,
                encoded_block=encoded_block,
            )
        )

    return FecTransmission(
        encoded_length=len(source),
        config=config,
        blocks=tuple(blocks),
    )


__all__ = [
    "FecTransmission",
    "FecTransmissionBlock",
    "block_metadata_for_index",
    "fec_block_count",
    "prepare_fec_transmission",
]
