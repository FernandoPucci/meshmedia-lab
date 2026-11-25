"""Standalone Reed-Solomon coding over ``GF(2^8)``.

The implementation is deliberately independent of MM1 packets, CRC and
transports.  It uses a systematic evaluation-code representation:

* the field polynomial is ``0x11D`` and the generator is ``0x02``;
* position ``i`` is evaluated at ``alpha ** i``;
* source symbols are the first ``k`` evaluations;
* repair symbols are the remaining ``n-k`` evaluations.

The concrete implementation accepts one-byte symbols and no interleaving.
Those restrictions are explicit because ``FecConfig`` is intentionally
algorithm-independent and permits configurations that Reed-Solomon does not
use in this experiment.
"""

from collections.abc import Iterable
from functools import cache
from typing import ClassVar

from .contract import (
    DecodeFailureReason,
    DecodeResult,
    EncodedBlock,
    FecBlockMetadata,
    FecConfig,
    FecConfigurationError,
    FecInputError,
    FecSymbol,
    IncompleteBlockPolicy,
    PaddingPolicy,
    prepare_source_symbols,
    validate_decode_inputs,
    validate_encoded_block,
)

REED_SOLOMON_ALGORITHM_ID = "reed_solomon"
GF256_PRIMITIVE_POLYNOMIAL = 0x11D
GF256_GENERATOR = 0x02
GF256_ORDER = 255


class _GF256:
    """Small table-based arithmetic implementation for ``GF(2^8)``."""

    _exp = [0] * (GF256_ORDER * 2)
    _log = [-1] * 256
    value = 1
    for exponent in range(GF256_ORDER):
        _exp[exponent] = value
        _log[value] = exponent
        value <<= 1
        if value & 0x100:
            value ^= GF256_PRIMITIVE_POLYNOMIAL
    for exponent in range(GF256_ORDER, GF256_ORDER * 2):
        _exp[exponent] = _exp[exponent - GF256_ORDER]
    exp = tuple(_exp)
    log = tuple(_log)
    _multiply_table: ClassVar[list[tuple[int, ...]]] = []
    for left in range(256):
        row = []
        for right in range(256):
            row.append(
                0
                if left == 0 or right == 0
                else exp[log[left] + log[right]]
            )
        _multiply_table.append(tuple(row))
    multiply_table = tuple(_multiply_table)

    @classmethod
    def add(cls, left: int, right: int) -> int:
        return left ^ right

    @classmethod
    def multiply(cls, left: int, right: int) -> int:
        return cls.multiply_table[left][right]

    @classmethod
    def inverse(cls, value: int) -> int:
        if value == 0:
            raise ZeroDivisionError("zero has no multiplicative inverse")
        return cls.exp[GF256_ORDER - cls.log[value]]

    @classmethod
    def power(cls, value: int, exponent: int) -> int:
        if exponent == 0:
            return 1
        if value == 0:
            return 0
        return cls.exp[(cls.log[value] * exponent) % GF256_ORDER]


def _trim_polynomial(polynomial: list[int]) -> list[int]:
    """Remove high zero coefficients while retaining the zero polynomial."""

    if not polynomial:
        return [0]
    last = len(polynomial) - 1
    while last > 0 and polynomial[last] == 0:
        last -= 1
    return polynomial[: last + 1]


def _polynomial_add(left: list[int], right: list[int]) -> list[int]:
    size = max(len(left), len(right))
    result = [0] * size
    for index in range(size):
        left_value = left[index] if index < len(left) else 0
        right_value = right[index] if index < len(right) else 0
        result[index] = _GF256.add(left_value, right_value)
    return _trim_polynomial(result)


def _polynomial_multiply(left: list[int], right: list[int]) -> list[int]:
    if left == [0] or right == [0]:
        return [0]
    result = [0] * (len(left) + len(right) - 1)
    for left_index, left_value in enumerate(left):
        if left_value == 0:
            continue
        for right_index, right_value in enumerate(right):
            if right_value:
                result[left_index + right_index] ^= _GF256.multiply(
                    left_value,
                    right_value,
                )
    return _trim_polynomial(result)


def _polynomial_evaluate(polynomial: list[int], value: int) -> int:
    result = 0
    for coefficient in reversed(polynomial):
        result = _GF256.multiply(result, value) ^ coefficient
    return result


def _polynomial_divide(
    dividend: list[int],
    divisor: list[int],
) -> tuple[list[int], list[int]]:
    """Return quotient and remainder using low-order-first coefficients."""

    divisor = _trim_polynomial(divisor)
    if divisor == [0]:
        raise ZeroDivisionError("cannot divide by the zero polynomial")

    dividend = _trim_polynomial(dividend)
    divisor_degree = len(divisor) - 1
    if len(dividend) <= divisor_degree:
        return [0], dividend

    remainder = dividend[:]
    quotient = [0] * (len(dividend) - divisor_degree)
    inverse_leading = _GF256.inverse(divisor[-1])

    for degree in range(len(dividend) - 1, divisor_degree - 1, -1):
        coefficient = _GF256.multiply(
            remainder[degree],
            inverse_leading,
        )
        quotient[degree - divisor_degree] = coefficient
        if coefficient == 0:
            continue
        for divisor_index, divisor_value in enumerate(divisor):
            remainder[degree - divisor_degree + divisor_index] ^= (
                _GF256.multiply(coefficient, divisor_value)
            )

    return _trim_polynomial(quotient), _trim_polynomial(
        remainder[:divisor_degree] or [0]
    )


def _interpolate(points: tuple[int, ...], values: tuple[int, ...]) -> list[int]:
    """Interpolate the unique polynomial through the supplied points."""

    polynomial = [0]
    for point_index, point in enumerate(points):
        basis = [1]
        denominator = 1
        for other_index, other_point in enumerate(points):
            if point_index == other_index:
                continue
            # In characteristic two, x - other_point == x + other_point.
            basis = _polynomial_multiply(basis, [other_point, 1])
            denominator = _GF256.multiply(
                denominator,
                point ^ other_point,
            )
        scale = _GF256.multiply(
            values[point_index],
            _GF256.inverse(denominator),
        )
        polynomial = _polynomial_add(
            polynomial,
            [
                _GF256.multiply(coefficient, scale)
                for coefficient in basis
            ],
        )
    return polynomial


def _solve_linear_system(
    matrix: list[list[int]],
    right_hand_side: list[int],
) -> list[int] | None:
    """Solve a possibly overdetermined linear system over ``GF(256)``."""

    if not matrix:
        return None
    column_count = len(matrix[0])
    if any(len(row) != column_count for row in matrix):
        raise ValueError("linear system rows have different lengths")
    if len(matrix) != len(right_hand_side):
        raise ValueError("linear system has mismatched right-hand side")

    augmented = [
        row[:] + [right_hand_side[row_index]]
        for row_index, row in enumerate(matrix)
    ]
    pivot_columns: list[int] = []
    pivot_row = 0

    for column in range(column_count):
        pivot = next(
            (
                row_index
                for row_index in range(pivot_row, len(augmented))
                if augmented[row_index][column] != 0
            ),
            None,
        )
        if pivot is None:
            continue

        augmented[pivot_row], augmented[pivot] = (
            augmented[pivot],
            augmented[pivot_row],
        )
        inverse = _GF256.inverse(augmented[pivot_row][column])
        for entry in range(column, column_count + 1):
            augmented[pivot_row][entry] = _GF256.multiply(
                augmented[pivot_row][entry],
                inverse,
            )

        for row_index in range(len(augmented)):
            if row_index == pivot_row:
                continue
            factor = augmented[row_index][column]
            if factor == 0:
                continue
            for entry in range(column, column_count + 1):
                augmented[row_index][entry] ^= _GF256.multiply(
                    factor,
                    augmented[pivot_row][entry],
                )

        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == len(augmented):
            break

    for row in augmented:
        if all(value == 0 for value in row[:column_count]) and row[-1] != 0:
            return None

    solution = [0] * column_count
    for row_index, column in enumerate(pivot_columns):
        solution[column] = augmented[row_index][-1]
    return solution


def _validate_rs_config(config: FecConfig) -> None:
    if not isinstance(config, FecConfig):
        raise FecConfigurationError("config must be FecConfig")
    if config.algorithm_id != REED_SOLOMON_ALGORITHM_ID:
        raise FecConfigurationError(
            f"algorithm_id must be {REED_SOLOMON_ALGORITHM_ID!r}"
        )
    if config.symbol_size != 1:
        raise FecConfigurationError(
            "Reed-Solomon requires symbol_size=1 for this implementation"
        )
    if config.block_symbols > GF256_ORDER:
        raise FecConfigurationError(
            f"block_symbols cannot exceed {GF256_ORDER} in GF(2^8)"
        )
    if config.interleaving_depth != 0:
        raise FecConfigurationError(
            "interleaving_depth must be zero for this implementation"
        )


def _validate_metadata(
    metadata: FecBlockMetadata,
    config: FecConfig,
) -> None:
    if not isinstance(metadata, FecBlockMetadata):
        raise FecInputError("metadata must be FecBlockMetadata")

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
    source_count = (
        0
        if metadata.original_length == 0
        else (
            metadata.original_length + config.symbol_size - 1
        )
        // config.symbol_size
    )
    if (
        config.incomplete_block_policy is IncompleteBlockPolicy.REJECT
        and source_count < config.data_symbols
    ):
        raise FecInputError(
            "metadata describes an incomplete block rejected by policy"
        )


def _evaluation_points(block_symbols: int) -> tuple[int, ...]:
    return tuple(_GF256.exp[index] for index in range(block_symbols))


@cache
def _evaluation_powers(
    block_symbols: int,
    maximum_power: int,
) -> tuple[tuple[int, ...], ...]:
    points = _evaluation_points(block_symbols)
    return tuple(
        tuple(
            _GF256.power(point, exponent)
            for exponent in range(maximum_power + 1)
        )
        for point in points
    )


@cache
def _systematic_coefficients(
    data_symbols: int,
    block_symbols: int,
) -> tuple[tuple[int, ...], ...]:
    """Return the fixed source-to-codeword transform for one configuration."""

    points = _evaluation_points(block_symbols)
    source_points = points[:data_symbols]
    basis_polynomials = []
    for source_index in range(data_symbols):
        values = [0] * data_symbols
        values[source_index] = 1
        basis_polynomials.append(
            _interpolate(source_points, tuple(values))
        )
    return tuple(
        tuple(
            _polynomial_evaluate(polynomial, point)
            for polynomial in basis_polynomials
        )
        for point in points
    )


def _codeword_values(
    source_values: tuple[int, ...],
    config: FecConfig,
) -> tuple[int, ...]:
    coefficients = _systematic_coefficients(
        config.data_symbols,
        config.block_symbols,
    )
    return tuple(_sum_gf_products(row, source_values) for row in coefficients)


def _sum_gf_products(
    coefficients: tuple[int, ...],
    values: tuple[int, ...],
) -> int:
    result = 0
    for coefficient, value in zip(coefficients, values):
        result ^= _GF256.multiply(coefficient, value)
    return result


def _recover_polynomial(
    received: tuple[FecSymbol, ...],
    config: FecConfig,
    missing_indices: tuple[int, ...],
) -> tuple[list[int], tuple[int, ...]] | None:
    """Use Berlekamp-Welch decoding for errors plus known erasures."""

    data_count = config.data_symbols
    redundancy = config.repair_symbols
    max_errors = (redundancy - len(missing_indices)) // 2
    if max_errors < 0:
        return None

    points = _evaluation_points(config.block_symbols)
    powers_by_index = _evaluation_powers(
        config.block_symbols,
        config.data_symbols + max_errors,
    )
    ordered_received = tuple(sorted(received, key=lambda symbol: symbol.index))

    for error_count in range(max_errors, -1, -1):
        q_degree_limit = data_count + error_count
        locator_unknowns = error_count
        matrix: list[list[int]] = []
        right_hand_side: list[int] = []

        for symbol in ordered_received:
            value = symbol.data[0]
            powers = powers_by_index[symbol.index]

            row = list(powers[:q_degree_limit])
            row.extend(
                _GF256.multiply(value, powers[index])
                for index in range(locator_unknowns)
            )
            matrix.append(row)
            right_hand_side.append(
                _GF256.multiply(value, powers[error_count])
            )

        solution = _solve_linear_system(matrix, right_hand_side)
        if solution is None:
            continue

        quotient_coefficients = solution[:q_degree_limit]
        locator_coefficients = solution[q_degree_limit:] + [1]
        polynomial, remainder = _polynomial_divide(
            quotient_coefficients,
            locator_coefficients,
        )
        if remainder != [0] or len(polynomial) > data_count:
            continue
        polynomial.extend([0] * (data_count - len(polynomial)))

        invalid_indices = tuple(
            symbol.index
            for symbol in ordered_received
            if _polynomial_evaluate(polynomial, points[symbol.index])
            != symbol.data[0]
        )
        if len(invalid_indices) > error_count:
            continue
        if any(
            _polynomial_evaluate(locator_coefficients, points[index]) != 0
            for index in invalid_indices
        ):
            continue
        return polynomial, invalid_indices

    return None


def _fast_decode(
    received: tuple[FecSymbol, ...],
    config: FecConfig,
    metadata: FecBlockMetadata,
    missing_indices: tuple[int, ...],
) -> DecodeResult | None:
    """Handle common erasure-only cases without solving a full system.

    The general decoder remains the authority for unknown errors.  When exactly
    ``k`` symbols are available, interpolation is the same zero-error
    Berlekamp-Welch solution.  When the complete codeword is available, a
    polynomial reconstructed from any ``k`` symbols is first verified against
    every received symbol before using the fast result.
    """

    received_by_index = {
        symbol.index: symbol.data[0] for symbol in received
    }
    source_indices = set(range(config.data_symbols))
    if (
        len(received) == config.data_symbols
        and source_indices.issubset(received_by_index)
    ):
        source_values = tuple(
            received_by_index[index] for index in range(config.data_symbols)
        )
        codeword = _codeword_values(source_values, config)
        return DecodeResult(
            source_block=bytes(source_values)[: metadata.original_length],
            recovered_symbols=tuple(
                FecSymbol(
                    index=index,
                    data=bytes((codeword[index],)),
                )
                for index in sorted(missing_indices)
            ),
            success=True,
            reason=None,
            missing_indices=missing_indices,
        )

    if len(received) >= config.data_symbols and missing_indices:
        points = _evaluation_points(config.block_symbols)
        ordered = tuple(sorted(received, key=lambda symbol: symbol.index))
        basis = ordered[: config.data_symbols]
        polynomial = _interpolate(
            tuple(points[symbol.index] for symbol in basis),
            tuple(symbol.data[0] for symbol in basis),
        )
        if all(
            _polynomial_evaluate(polynomial, points[symbol.index])
            == symbol.data[0]
            for symbol in ordered
        ):
            recovered_symbols = tuple(
                FecSymbol(
                    index=index,
                    data=bytes(
                        (_polynomial_evaluate(polynomial, points[index]),)
                    ),
                )
                for index in sorted(missing_indices)
            )
            padded_source = bytes(
                _polynomial_evaluate(polynomial, points[index])
                for index in range(config.data_symbols)
            )
            return DecodeResult(
                source_block=padded_source[: metadata.original_length],
                recovered_symbols=recovered_symbols,
                success=True,
                reason=None,
                missing_indices=missing_indices,
            )

    if len(received) == config.data_symbols:
        points = _evaluation_points(config.block_symbols)
        ordered = tuple(sorted(received, key=lambda symbol: symbol.index))
        polynomial = _interpolate(
            tuple(points[symbol.index] for symbol in ordered),
            tuple(symbol.data[0] for symbol in ordered),
        )
        padded_source = bytes(
            _polynomial_evaluate(polynomial, points[index])
            for index in range(config.data_symbols)
        )
        recovered_symbols = tuple(
            FecSymbol(
                index=index,
                data=bytes(
                    (_polynomial_evaluate(polynomial, points[index]),)
                ),
            )
            for index in sorted(missing_indices)
        )
        return DecodeResult(
            source_block=padded_source[: metadata.original_length],
            recovered_symbols=recovered_symbols,
            success=True,
            reason=None,
            missing_indices=missing_indices,
        )

    if not missing_indices and len(received) == config.block_symbols:
        ordered = tuple(sorted(received, key=lambda symbol: symbol.index))
        source_values = tuple(
            symbol.data[0]
            for symbol in ordered
            if symbol.index < config.data_symbols
        )
        expected = (
            _codeword_values(source_values, config)
            if len(source_values) == config.data_symbols
            else ()
        )
        if expected and all(
            expected[symbol.index] == symbol.data[0]
            for symbol in ordered
        ):
            return DecodeResult(
                source_block=bytes(source_values)[: metadata.original_length],
                recovered_symbols=(),
                success=True,
                reason=None,
            )

    return None


class ReedSolomonEncoder:
    """Encode one source block with systematic Reed-Solomon symbols."""

    def encode(self, source_block: bytes, config: FecConfig) -> EncodedBlock:
        _validate_rs_config(config)
        source_symbols, metadata = prepare_source_symbols(source_block, config)
        source_values = tuple(symbol.data[0] for symbol in source_symbols)
        codeword = _codeword_values(source_values, config)
        repair_symbols = tuple(
            FecSymbol(
                index=index,
                data=bytes((codeword[index],)),
            )
            for index in range(config.data_symbols, config.block_symbols)
        )
        block = EncodedBlock(source_symbols, repair_symbols, metadata)
        validate_encoded_block(block, config)
        return block


class ReedSolomonDecoder:
    """Decode source bytes and correct erasures or bounded unknown errors."""

    def decode(
        self,
        received_symbols: Iterable[FecSymbol],
        erasures: Iterable[int],
        config: FecConfig,
        metadata: FecBlockMetadata,
    ) -> DecodeResult:
        _validate_rs_config(config)
        received, _, missing_indices = validate_decode_inputs(
            received_symbols,
            erasures,
            config,
        )
        _validate_metadata(metadata, config)

        if (
            len(received) < config.data_symbols
            or len(missing_indices) > config.repair_symbols
        ):
            return DecodeResult(
                source_block=None,
                recovered_symbols=(),
                success=False,
                reason=DecodeFailureReason.INSUFFICIENT_SYMBOLS,
                missing_indices=missing_indices,
            )

        fast_result = _fast_decode(
            received,
            config,
            metadata,
            missing_indices,
        )
        if fast_result is not None:
            return fast_result

        recovered = _recover_polynomial(
            received,
            config,
            missing_indices,
        )
        if recovered is None:
            reason = (
                DecodeFailureReason.UNKNOWN_CORRUPTION
                if not missing_indices
                else DecodeFailureReason.RECOVERY_FAILED
            )
            return DecodeResult(
                source_block=None,
                recovered_symbols=(),
                success=False,
                reason=reason,
                missing_indices=missing_indices,
            )

        polynomial, invalid_indices = recovered
        points = _evaluation_points(config.block_symbols)
        reconstructed_indices = tuple(
            sorted(set(missing_indices).union(invalid_indices))
        )
        recovered_symbols = tuple(
            FecSymbol(
                index=index,
                data=bytes(
                    (
                        _polynomial_evaluate(polynomial, points[index]),
                    )
                ),
            )
            for index in reconstructed_indices
        )
        padded_source = bytes(
            _polynomial_evaluate(polynomial, points[index])
            for index in range(config.data_symbols)
        )
        return DecodeResult(
            source_block=padded_source[: metadata.original_length],
            recovered_symbols=recovered_symbols,
            success=True,
            reason=None,
            missing_indices=missing_indices,
            invalid_indices=invalid_indices,
        )


__all__ = [
    "GF256_GENERATOR",
    "GF256_PRIMITIVE_POLYNOMIAL",
    "REED_SOLOMON_ALGORITHM_ID",
    "ReedSolomonDecoder",
    "ReedSolomonEncoder",
]
