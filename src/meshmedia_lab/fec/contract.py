"""Algorithm-independent contracts and value types for forward error correction.

This module deliberately contains no FEC algorithm.  It defines the data model,
generic validation rules and structural encoder/decoder protocols that future
algorithms can implement without depending on MM1 packets or transports.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, TypeAlias, runtime_checkable

BytesLike: TypeAlias = bytes | bytearray | memoryview


class FecError(ValueError):
    """Base class for invalid FEC configuration or contract data."""


class FecConfigurationError(FecError):
    """Raised when an FEC configuration is invalid."""


class FecInputError(FecError):
    """Raised when symbols, erasures or block data are invalid."""


class PaddingPolicy(Enum):
    """Policy used when a source block does not fill its configured capacity."""

    REJECT = "reject"
    ZERO_PAD = "zero_pad"


class IncompleteBlockPolicy(Enum):
    """Policy used when a source block contains fewer than ``k`` symbols."""

    REJECT = "reject"
    PAD_TO_K = "pad_to_k"


class DecodeFailureReason(Enum):
    """Stable categories for valid decode attempts that do not recover a block."""

    INSUFFICIENT_SYMBOLS = "insufficient_symbols"
    RECOVERY_FAILED = "recovery_failed"
    UNKNOWN_CORRUPTION = "unknown_corruption"


def _require_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise FecConfigurationError(f"{field_name} must be an integer")
    return value


def _coerce_bytes(value: object, field_name: str) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise FecInputError(f"{field_name} must be bytes-like")
    try:
        return bytes(value)
    except (TypeError, ValueError) as error:
        raise FecInputError(f"{field_name} must be bytes-like") from error


def _coerce_symbol_tuple(
    value: Iterable["FecSymbol"],
    field_name: str,
) -> tuple["FecSymbol", ...]:
    if isinstance(value, (str, bytes, bytearray, memoryview)):
        raise FecInputError(f"{field_name} must be an iterable of FecSymbol")
    try:
        symbols = tuple(value)
    except TypeError as error:
        raise FecInputError(
            f"{field_name} must be an iterable of FecSymbol"
        ) from error
    if any(not isinstance(symbol, FecSymbol) for symbol in symbols):
        raise FecInputError(f"{field_name} must contain only FecSymbol values")
    return symbols


def _coerce_index_tuple(
    value: Iterable[int],
    field_name: str,
) -> tuple[int, ...]:
    if isinstance(value, (str, bytes, bytearray, memoryview)):
        raise FecInputError(f"{field_name} must be an iterable of integers")
    try:
        indices = tuple(value)
    except TypeError as error:
        raise FecInputError(
            f"{field_name} must be an iterable of integers"
        ) from error
    for index in indices:
        if type(index) is not int:
            raise FecInputError(f"{field_name} must contain only integers")
        if index < 0:
            raise FecInputError(f"{field_name} cannot contain negative indices")
    if len(set(indices)) != len(indices):
        raise FecInputError(f"{field_name} cannot contain duplicate indices")
    return indices


def _ensure_unique_symbol_indices(
    symbols: Iterable["FecSymbol"],
    field_name: str,
) -> None:
    indices = tuple(symbol.index for symbol in symbols)
    if len(set(indices)) != len(indices):
        raise FecInputError(f"{field_name} cannot contain duplicate indices")


@dataclass(frozen=True, slots=True)
class FecConfig:
    """Immutable, algorithm-independent parameters for one FEC block."""

    algorithm_id: str
    symbol_size: int
    data_symbols: int
    repair_symbols: int
    block_symbols: int
    interleaving_depth: int
    padding_policy: PaddingPolicy
    incomplete_block_policy: IncompleteBlockPolicy

    def __post_init__(self) -> None:
        if type(self.algorithm_id) is not str or not self.algorithm_id.strip():
            raise FecConfigurationError("algorithm_id must be a non-empty string")

        values = (
            ("symbol_size", self.symbol_size),
            ("data_symbols", self.data_symbols),
            ("repair_symbols", self.repair_symbols),
            ("block_symbols", self.block_symbols),
            ("interleaving_depth", self.interleaving_depth),
        )
        for field_name, value in values:
            _require_int(value, field_name)

        if self.symbol_size <= 0:
            raise FecConfigurationError("symbol_size must be positive")
        if self.data_symbols <= 0:
            raise FecConfigurationError("data_symbols must be positive")
        if self.repair_symbols < 0:
            raise FecConfigurationError("repair_symbols cannot be negative")
        if self.block_symbols <= 0:
            raise FecConfigurationError("block_symbols must be positive")
        if self.interleaving_depth < 0:
            raise FecConfigurationError(
                "interleaving_depth cannot be negative"
            )
        if self.block_symbols != self.data_symbols + self.repair_symbols:
            raise FecConfigurationError(
                "block_symbols must equal data_symbols + repair_symbols"
            )
        if not isinstance(self.padding_policy, PaddingPolicy):
            raise FecConfigurationError("padding_policy is not supported")
        if not isinstance(
            self.incomplete_block_policy,
            IncompleteBlockPolicy,
        ):
            raise FecConfigurationError(
                "incomplete_block_policy is not supported"
            )

    @property
    def source_capacity(self) -> int:
        """Return the number of source bytes in one complete block."""

        return self.data_symbols * self.symbol_size


@dataclass(frozen=True, slots=True)
class FecBlockMetadata:
    """Local, non-wire metadata required to restore a source block."""

    original_length: int
    padding_length: int

    def __post_init__(self) -> None:
        for field_name, value in (
            ("original_length", self.original_length),
            ("padding_length", self.padding_length),
        ):
            if type(value) is not int:
                raise FecInputError(f"{field_name} must be an integer")
            if value < 0:
                raise FecInputError(f"{field_name} cannot be negative")

    @property
    def padded_length(self) -> int:
        """Return the source length after local padding."""

        return self.original_length + self.padding_length


@dataclass(frozen=True, slots=True)
class FecSymbol:
    """One fixed-position FEC symbol.

    The upper index bound and fixed byte length depend on :class:`FecConfig`
    and are checked by ``validate_symbol`` or the block validators.
    """

    index: int
    data: bytes

    def __post_init__(self) -> None:
        if type(self.index) is not int:
            raise FecInputError("symbol index must be an integer")
        if self.index < 0:
            raise FecInputError("symbol index cannot be negative")
        data = _coerce_bytes(self.data, "symbol data")
        if not data:
            raise FecInputError("symbol data cannot be empty")
        object.__setattr__(self, "data", data)


@dataclass(frozen=True, slots=True)
class EncodedBlock:
    """Origin and repair symbols plus metadata for one encoded block."""

    source_symbols: tuple[FecSymbol, ...]
    repair_symbols: tuple[FecSymbol, ...]
    metadata: FecBlockMetadata

    def __post_init__(self) -> None:
        source_symbols = _coerce_symbol_tuple(
            self.source_symbols,
            "source_symbols",
        )
        repair_symbols = _coerce_symbol_tuple(
            self.repair_symbols,
            "repair_symbols",
        )
        if not isinstance(self.metadata, FecBlockMetadata):
            raise FecInputError("metadata must be FecBlockMetadata")
        _ensure_unique_symbol_indices(source_symbols, "source_symbols")
        _ensure_unique_symbol_indices(repair_symbols, "repair_symbols")
        _ensure_unique_symbol_indices(
            source_symbols + repair_symbols,
            "encoded block symbols",
        )
        object.__setattr__(self, "source_symbols", source_symbols)
        object.__setattr__(self, "repair_symbols", repair_symbols)

    @property
    def original_length(self) -> int:
        """Return the unpadded source byte count."""

        return self.metadata.original_length

    @property
    def padding_length(self) -> int:
        """Return the number of locally added padding bytes."""

        return self.metadata.padding_length

    def validate(self, config: FecConfig) -> None:
        """Validate this block against its FEC configuration."""

        validate_encoded_block(self, config)


@dataclass(frozen=True, slots=True)
class DecodeResult:
    """Outcome of a valid decode attempt.

    A failed result never carries a complete ``source_block``. Recovered
    symbols may still be reported for diagnostics, but they are not a
    substitute for a successful source block.
    """

    source_block: bytes | None
    recovered_symbols: tuple[FecSymbol, ...]
    success: bool
    reason: DecodeFailureReason | None
    missing_indices: tuple[int, ...] = ()
    invalid_indices: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.source_block is not None:
            object.__setattr__(
                self,
                "source_block",
                _coerce_bytes(self.source_block, "source_block"),
            )
        recovered_symbols = _coerce_symbol_tuple(
            self.recovered_symbols,
            "recovered_symbols",
        )
        _ensure_unique_symbol_indices(
            recovered_symbols,
            "recovered_symbols",
        )
        missing_indices = _coerce_index_tuple(
            self.missing_indices,
            "missing_indices",
        )
        invalid_indices = _coerce_index_tuple(
            self.invalid_indices,
            "invalid_indices",
        )
        if type(self.success) is not bool:
            raise FecInputError("success must be a boolean")
        if self.reason is not None and not isinstance(
            self.reason,
            DecodeFailureReason,
        ):
            raise FecInputError("reason is not a supported decode failure")
        if self.success:
            if self.source_block is None:
                raise FecInputError(
                    "a successful decode must include source_block"
                )
            if self.reason is not None:
                raise FecInputError(
                    "a successful decode cannot include a failure reason"
                )
        else:
            if self.source_block is not None:
                raise FecInputError(
                    "a failed decode cannot include source_block"
                )
            if self.reason is None:
                raise FecInputError(
                    "a failed decode must include a failure reason"
                )
        object.__setattr__(self, "recovered_symbols", recovered_symbols)
        object.__setattr__(self, "missing_indices", missing_indices)
        object.__setattr__(self, "invalid_indices", invalid_indices)

    @property
    def recovered_indices(self) -> tuple[int, ...]:
        """Return the positions of symbols recovered by the decoder."""

        return tuple(symbol.index for symbol in self.recovered_symbols)

    @property
    def recovered_count(self) -> int:
        """Return the number of symbols reported as recovered."""

        return len(self.recovered_symbols)


def validate_symbol(
    symbol: FecSymbol,
    config: FecConfig,
    *,
    role: str | None = None,
) -> None:
    """Validate one symbol's position and size against ``config``.

    ``role`` may be ``"source"`` or ``"repair"`` when a caller is validating
    a field of ``EncodedBlock``.
    """

    if not isinstance(config, FecConfig):
        raise FecConfigurationError("config must be FecConfig")
    if not isinstance(symbol, FecSymbol):
        raise FecInputError("value must be FecSymbol")
    if not 0 <= symbol.index < config.block_symbols:
        raise FecInputError(
            f"symbol index must be between 0 and {config.block_symbols - 1}"
        )
    if len(symbol.data) != config.symbol_size:
        raise FecInputError(
            f"symbol {symbol.index} has {len(symbol.data)} bytes; "
            f"expected {config.symbol_size}"
        )
    if role == "source" and symbol.index >= config.data_symbols:
        raise FecInputError(
            f"source symbol index must be between 0 and "
            f"{config.data_symbols - 1}"
        )
    if role == "repair" and symbol.index < config.data_symbols:
        raise FecInputError(
            f"repair symbol index must be between {config.data_symbols} and "
            f"{config.block_symbols - 1}"
        )
    if role not in (None, "source", "repair"):
        raise FecInputError(f"unsupported symbol role: {role}")


def _source_symbol_count(byte_length: int, symbol_size: int) -> int:
    if byte_length == 0:
        return 0
    return (byte_length + symbol_size - 1) // symbol_size


def _validate_metadata(
    metadata: FecBlockMetadata,
    config: FecConfig,
) -> None:
    capacity = config.source_capacity
    if metadata.original_length > capacity:
        raise FecInputError(
            "original_length cannot exceed the configured source capacity"
        )
    if metadata.padded_length != capacity:
        raise FecInputError(
            "original_length plus padding_length must equal source capacity"
        )
    if (
        config.padding_policy is PaddingPolicy.REJECT
        and metadata.padding_length != 0
    ):
        raise FecInputError(
            "padding metadata conflicts with PaddingPolicy.REJECT"
        )
    if (
        config.incomplete_block_policy is IncompleteBlockPolicy.REJECT
        and _source_symbol_count(
            metadata.original_length,
            config.symbol_size,
        )
        < config.data_symbols
    ):
        raise FecInputError(
            "metadata describes an incomplete block rejected by policy"
        )


def validate_encoded_block(
    block: EncodedBlock,
    config: FecConfig,
) -> None:
    """Validate all structural invariants of an encoded block."""

    if not isinstance(block, EncodedBlock):
        raise FecInputError("block must be EncodedBlock")
    if not isinstance(config, FecConfig):
        raise FecConfigurationError("config must be FecConfig")
    if len(block.source_symbols) != config.data_symbols:
        raise FecInputError(
            "encoded block has an invalid number of source symbols"
        )
    if len(block.repair_symbols) != config.repair_symbols:
        raise FecInputError(
            "encoded block has an invalid number of repair symbols"
        )
    for symbol in block.source_symbols:
        validate_symbol(symbol, config, role="source")
    for symbol in block.repair_symbols:
        validate_symbol(symbol, config, role="repair")
    _validate_metadata(block.metadata, config)

    source_bytes = b"".join(
        symbol.data for symbol in sorted(block.source_symbols, key=lambda item: item.index)
    )
    padding = source_bytes[block.metadata.original_length :]
    if padding != bytes(block.metadata.padding_length):
        raise FecInputError("source symbol padding is not zero-filled")


def prepare_source_symbols(
    source_block: BytesLike,
    config: FecConfig,
) -> tuple[tuple[FecSymbol, ...], FecBlockMetadata]:
    """Split and pad one source block according to the generic policies.

    This helper performs no encoding or repair generation. It only creates the
    fixed-size source symbols and the local metadata that a concrete encoder
    can use.
    """

    if not isinstance(config, FecConfig):
        raise FecConfigurationError("config must be FecConfig")
    source = _coerce_bytes(source_block, "source_block")
    if len(source) > config.source_capacity:
        raise FecInputError(
            "source_block cannot exceed the configured source capacity"
        )

    source_count = _source_symbol_count(len(source), config.symbol_size)
    padding_length = config.source_capacity - len(source)
    if (
        padding_length > 0
        and config.padding_policy is PaddingPolicy.REJECT
    ):
        raise FecInputError(
            "source_block requires padding rejected by policy"
        )
    if (
        source_count < config.data_symbols
        and config.incomplete_block_policy
        is IncompleteBlockPolicy.REJECT
    ):
        raise FecInputError(
            "source_block contains fewer than data_symbols"
        )

    padded = source + bytes(padding_length)
    symbols = tuple(
        FecSymbol(
            index=index,
            data=padded[
                index * config.symbol_size : (index + 1) * config.symbol_size
            ],
        )
        for index in range(config.data_symbols)
    )
    metadata = FecBlockMetadata(
        original_length=len(source),
        padding_length=padding_length,
    )
    return symbols, metadata


def validate_decode_inputs(
    received_symbols: Iterable[FecSymbol],
    erasures: Iterable[int],
    config: FecConfig,
) -> tuple[tuple[FecSymbol, ...], tuple[int, ...], tuple[int, ...]]:
    """Validate decoder inputs and return normalized values.

    The third tuple contains every currently absent symbol index. The caller
    should list known missing or CRC-rejected positions in ``erasures``; an
    omitted position remains a missing symbol and can still lead to a valid
    insufficient-symbols result.
    """

    if not isinstance(config, FecConfig):
        raise FecConfigurationError("config must be FecConfig")
    received = _coerce_symbol_tuple(received_symbols, "received_symbols")
    erasure_indices = _coerce_index_tuple(erasures, "erasures")
    for symbol in received:
        validate_symbol(symbol, config)
    _ensure_unique_symbol_indices(received, "received_symbols")
    for index in erasure_indices:
        if index >= config.block_symbols:
            raise FecInputError(
                f"erasure index must be between 0 and "
                f"{config.block_symbols - 1}"
            )
    received_indices = {symbol.index for symbol in received}
    conflicting = received_indices.intersection(erasure_indices)
    if conflicting:
        conflict = min(conflicting)
        raise FecInputError(
            f"symbol index {conflict} cannot be both received and an erasure"
        )
    missing = tuple(
        index
        for index in range(config.block_symbols)
        if index not in received_indices
    )
    return received, erasure_indices, missing


@runtime_checkable
class FecEncoder(Protocol):
    """Structural contract for an algorithm-specific FEC encoder."""

    def encode(self, source_block: bytes, config: FecConfig) -> EncodedBlock:
        """Encode one source block without serializing MM1 packets or CRC."""


@runtime_checkable
class FecDecoder(Protocol):
    """Structural contract for an algorithm-specific FEC decoder."""

    def decode(
        self,
        received_symbols: Iterable[FecSymbol],
        erasures: Iterable[int],
        config: FecConfig,
        metadata: FecBlockMetadata,
    ) -> DecodeResult:
        """Decode valid symbols and known erasures into one source block."""


__all__ = [
    "BytesLike",
    "DecodeFailureReason",
    "DecodeResult",
    "EncodedBlock",
    "FecBlockMetadata",
    "FecConfig",
    "FecConfigurationError",
    "FecDecoder",
    "FecEncoder",
    "FecError",
    "FecInputError",
    "FecSymbol",
    "IncompleteBlockPolicy",
    "PaddingPolicy",
    "prepare_source_symbols",
    "validate_decode_inputs",
    "validate_encoded_block",
    "validate_symbol",
]
