import unittest
from dataclasses import FrozenInstanceError, replace

from meshmedia_lab.fec import (
    DecodeFailureReason,
    DecodeResult,
    EncodedBlock,
    FecBlockMetadata,
    FecConfig,
    FecConfigurationError,
    FecDecoder,
    FecEncoder,
    FecInputError,
    FecSymbol,
    IncompleteBlockPolicy,
    PaddingPolicy,
    prepare_source_symbols,
    validate_decode_inputs,
    validate_encoded_block,
    validate_symbol,
)


def make_config(
    *,
    padding_policy: PaddingPolicy = PaddingPolicy.ZERO_PAD,
    incomplete_block_policy: IncompleteBlockPolicy = (
        IncompleteBlockPolicy.PAD_TO_K
    ),
) -> FecConfig:
    return FecConfig(
        algorithm_id="fake",
        symbol_size=2,
        data_symbols=2,
        repair_symbols=1,
        block_symbols=3,
        interleaving_depth=0,
        padding_policy=padding_policy,
        incomplete_block_policy=incomplete_block_policy,
    )


class FakeFecEncoder:
    """Deterministic contract fake; it does not implement mathematical FEC."""

    def encode(self, source_block: bytes, config: FecConfig) -> EncodedBlock:
        source_symbols, metadata = prepare_source_symbols(source_block, config)
        repair_symbols = tuple(
            FecSymbol(
                index=config.data_symbols + offset,
                data=bytes((offset + 1,)) * config.symbol_size,
            )
            for offset in range(config.repair_symbols)
        )
        block = EncodedBlock(source_symbols, repair_symbols, metadata)
        validate_encoded_block(block, config)
        return block


class FakeFecDecoder:
    """Contract fake that only succeeds when all source symbols are present."""

    def decode(
        self,
        received_symbols,
        erasures,
        config: FecConfig,
        metadata: FecBlockMetadata,
    ) -> DecodeResult:
        received, _, missing = validate_decode_inputs(
            received_symbols,
            erasures,
            config,
        )
        if metadata.padded_length != config.source_capacity:
            raise FecInputError("metadata does not match source capacity")

        by_index = {symbol.index: symbol for symbol in received}
        if len(received) < config.data_symbols:
            return DecodeResult(
                source_block=None,
                recovered_symbols=(),
                success=False,
                reason=DecodeFailureReason.INSUFFICIENT_SYMBOLS,
                missing_indices=missing,
            )
        if any(index not in by_index for index in range(config.data_symbols)):
            return DecodeResult(
                source_block=None,
                recovered_symbols=(),
                success=False,
                reason=DecodeFailureReason.RECOVERY_FAILED,
                missing_indices=missing,
            )

        padded_source = b"".join(
            by_index[index].data for index in range(config.data_symbols)
        )
        return DecodeResult(
            source_block=padded_source[: metadata.original_length],
            recovered_symbols=(),
            success=True,
            reason=None,
            missing_indices=missing,
        )


class FecConfigurationTests(unittest.TestCase):
    def test_valid_configuration_is_immutable_and_exposes_capacity(self) -> None:
        config = make_config()

        self.assertEqual(config.source_capacity, 4)
        with self.assertRaises(FrozenInstanceError):
            config.symbol_size = 4  # type: ignore[misc]

    def test_invalid_configuration_values_are_rejected(self) -> None:
        base = {
            "algorithm_id": "fake",
            "symbol_size": 2,
            "data_symbols": 2,
            "repair_symbols": 1,
            "block_symbols": 3,
            "interleaving_depth": 0,
            "padding_policy": PaddingPolicy.ZERO_PAD,
            "incomplete_block_policy": IncompleteBlockPolicy.PAD_TO_K,
        }
        invalid = (
            ("algorithm_id", ""),
            ("algorithm_id", "   "),
            ("algorithm_id", None),
            ("symbol_size", 0),
            ("symbol_size", -1),
            ("symbol_size", True),
            ("data_symbols", 0),
            ("data_symbols", -1),
            ("data_symbols", True),
            ("repair_symbols", -1),
            ("repair_symbols", True),
            ("block_symbols", 0),
            ("block_symbols", -1),
            ("block_symbols", 4),
            ("block_symbols", True),
            ("interleaving_depth", -1),
            ("interleaving_depth", True),
            ("padding_policy", "zero_pad"),
            ("incomplete_block_policy", "pad_to_k"),
        )
        for field_name, value in invalid:
            with (
                self.subTest(field_name=field_name, value=value),
                self.assertRaises(FecConfigurationError),
            ):
                FecConfig(**{**base, field_name: value})

    def test_zero_repair_symbols_are_valid(self) -> None:
        config = replace(
            make_config(),
            repair_symbols=0,
            block_symbols=2,
        )

        self.assertEqual(config.repair_symbols, 0)
        self.assertEqual(config.block_symbols, config.data_symbols)


class FecValueTests(unittest.TestCase):
    def test_symbol_rejects_negative_and_empty_data(self) -> None:
        with self.assertRaises(FecInputError):
            FecSymbol(-1, b"x")
        with self.assertRaises(FecInputError):
            FecSymbol(0, b"")

    def test_symbol_length_and_role_are_validated_against_config(self) -> None:
        config = make_config()
        source = FecSymbol(0, b"ab")
        repair = FecSymbol(2, b"cd")

        validate_symbol(source, config, role="source")
        validate_symbol(repair, config, role="repair")
        with self.assertRaises(FecInputError):
            validate_symbol(FecSymbol(0, b"a"), config)
        with self.assertRaises(FecInputError):
            validate_symbol(FecSymbol(2, b"cd"), config, role="source")
        with self.assertRaises(FecInputError):
            validate_symbol(FecSymbol(0, b"ab"), config, role="repair")
        with self.assertRaises(FecInputError):
            validate_symbol(FecSymbol(3, b"cd"), config)

    def test_encoded_block_validates_symbol_ranges_counts_and_metadata(self) -> None:
        config = make_config()
        source_symbols, metadata = prepare_source_symbols(b"abc", config)
        valid = EncodedBlock(
            source_symbols=source_symbols,
            repair_symbols=(FecSymbol(2, b"xy"),),
            metadata=metadata,
        )
        valid.validate(config)

        with self.assertRaises(FecInputError):
            validate_encoded_block(
                EncodedBlock(
                    source_symbols=source_symbols,
                    repair_symbols=(),
                    metadata=metadata,
                ),
                config,
            )

        with self.assertRaises(FecInputError):
            validate_encoded_block(
                EncodedBlock(
                    source_symbols=source_symbols,
                    repair_symbols=(FecSymbol(0, b"xy"),),
                    metadata=metadata,
                ),
                config,
            )

        with self.assertRaises(FecInputError):
            validate_encoded_block(
                EncodedBlock(
                    source_symbols=source_symbols,
                    repair_symbols=(FecSymbol(2, b"xy"),),
                    metadata=FecBlockMetadata(2, 2),
                ),
                config,
            )

    def test_padding_and_incomplete_block_policies_are_applied(self) -> None:
        config = make_config()
        symbols, metadata = prepare_source_symbols(b"abc", config)
        self.assertEqual(tuple(symbol.data for symbol in symbols), (b"ab", b"c\0"))
        self.assertEqual(metadata, FecBlockMetadata(3, 1))

        reject_incomplete = make_config(
            incomplete_block_policy=IncompleteBlockPolicy.REJECT,
        )
        with self.assertRaises(FecInputError):
            prepare_source_symbols(b"a", reject_incomplete)

        reject_padding = make_config(
            padding_policy=PaddingPolicy.REJECT,
            incomplete_block_policy=IncompleteBlockPolicy.REJECT,
        )
        prepare_source_symbols(b"abcd", reject_padding)
        with self.assertRaises(FecInputError):
            prepare_source_symbols(b"abc", reject_padding)
        with self.assertRaises(FecInputError):
            prepare_source_symbols(b"abcde", config)


class FecDecoderInputTests(unittest.TestCase):
    def test_valid_erasures_are_normalized_and_missing_indices_reported(self) -> None:
        config = make_config()
        received = (FecSymbol(0, b"ab"), FecSymbol(2, b"cd"))

        normalized, erasures, missing = validate_decode_inputs(
            received,
            (1,),
            config,
        )

        self.assertEqual(normalized, received)
        self.assertEqual(erasures, (1,))
        self.assertEqual(missing, (1,))

    def test_invalid_duplicate_conflicting_and_out_of_range_inputs_fail(self) -> None:
        config = make_config()
        symbol = FecSymbol(0, b"ab")
        cases = (
            ((symbol, symbol), ()),
            ((symbol,), (0,)),
            ((symbol,), (1, 1)),
            ((symbol,), (3,)),
            ((FecSymbol(3, b"ab"),), ()),
        )
        for received, erasures in cases:
            with (
                self.subTest(received=received, erasures=erasures),
                self.assertRaises(FecInputError),
            ):
                validate_decode_inputs(received, erasures, config)

    def test_decode_result_does_not_expose_partial_data_as_success(self) -> None:
        with self.assertRaises(FecInputError):
            DecodeResult(
                source_block=None,
                recovered_symbols=(),
                success=True,
                reason=None,
            )
        with self.assertRaises(FecInputError):
            DecodeResult(
                source_block=b"partial",
                recovered_symbols=(),
                success=False,
                reason=DecodeFailureReason.INSUFFICIENT_SYMBOLS,
            )
        with self.assertRaises(FecInputError):
            DecodeResult(
                source_block=None,
                recovered_symbols=(),
                success=False,
                reason=None,
            )


class FecContractFakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = make_config()
        self.encoder = FakeFecEncoder()
        self.decoder = FakeFecDecoder()

    def test_fake_implements_separate_structural_protocols(self) -> None:
        self.assertIsInstance(self.encoder, FecEncoder)
        self.assertIsInstance(self.decoder, FecDecoder)

    def test_encode_and_decode_preserve_original_length_and_padding(self) -> None:
        encoded = self.encoder.encode(b"abc", self.config)

        self.assertEqual(encoded.original_length, 3)
        self.assertEqual(encoded.padding_length, 1)
        result = self.decoder.decode(
            encoded.source_symbols + encoded.repair_symbols,
            (),
            self.config,
            encoded.metadata,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.source_block, b"abc")
        self.assertEqual(result.recovered_count, 0)
        self.assertEqual(result.recovered_indices, ())

    def test_valid_erasure_can_be_reported_without_claiming_recovery(self) -> None:
        encoded = self.encoder.encode(b"abc", self.config)
        result = self.decoder.decode(
            (encoded.source_symbols[0], encoded.repair_symbols[0]),
            (1,),
            self.config,
            encoded.metadata,
        )

        self.assertFalse(result.success)
        self.assertIsNone(result.source_block)
        self.assertEqual(result.reason, DecodeFailureReason.RECOVERY_FAILED)
        self.assertEqual(result.missing_indices, (1,))

    def test_insufficient_symbols_return_a_typed_failure(self) -> None:
        encoded = self.encoder.encode(b"abcd", self.config)
        result = self.decoder.decode(
            (encoded.source_symbols[0],),
            (1, 2),
            self.config,
            encoded.metadata,
        )

        self.assertFalse(result.success)
        self.assertIsNone(result.source_block)
        self.assertEqual(
            result.reason,
            DecodeFailureReason.INSUFFICIENT_SYMBOLS,
        )
