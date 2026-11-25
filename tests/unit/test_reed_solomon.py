import itertools
import unittest

from meshmedia_lab.fec import (
    DecodeFailureReason,
    DecodeResult,
    FecBlockMetadata,
    FecConfig,
    FecConfigurationError,
    FecDecoder,
    FecEncoder,
    FecInputError,
    FecSymbol,
    IncompleteBlockPolicy,
    PaddingPolicy,
    ReedSolomonDecoder,
    ReedSolomonEncoder,
)


def make_config(
    data_symbols: int = 4,
    repair_symbols: int = 3,
    *,
    algorithm_id: str = "reed_solomon",
    symbol_size: int = 1,
    interleaving_depth: int = 0,
    padding_policy: PaddingPolicy = PaddingPolicy.ZERO_PAD,
    incomplete_block_policy: IncompleteBlockPolicy = (
        IncompleteBlockPolicy.PAD_TO_K
    ),
) -> FecConfig:
    return FecConfig(
        algorithm_id=algorithm_id,
        symbol_size=symbol_size,
        data_symbols=data_symbols,
        repair_symbols=repair_symbols,
        block_symbols=data_symbols + repair_symbols,
        interleaving_depth=interleaving_depth,
        padding_policy=padding_policy,
        incomplete_block_policy=incomplete_block_policy,
    )


def alter_symbol(symbol: FecSymbol, mask: int = 0x55) -> FecSymbol:
    return FecSymbol(symbol.index, bytes((symbol.data[0] ^ mask,)))


class ReedSolomonEncodingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.encoder = ReedSolomonEncoder()
        self.decoder = ReedSolomonDecoder()

    def test_concrete_classes_implement_the_fec_protocols(self) -> None:
        self.assertIsInstance(self.encoder, FecEncoder)
        self.assertIsInstance(self.decoder, FecDecoder)

    def test_independent_systematic_reference_vector(self) -> None:
        """Vector calculated independently using the documented convention."""

        config = make_config(data_symbols=4, repair_symbols=3)
        block = self.encoder.encode(b"\x01\x02\x03\x04", config)

        self.assertEqual(
            tuple(symbol.data for symbol in block.source_symbols),
            (b"\x01", b"\x02", b"\x03", b"\x04"),
        )
        self.assertEqual(
            tuple(symbol.data for symbol in block.repair_symbols),
            (b"\xd6", b"\x36", b"\xe2"),
        )

    def test_experimental_configurations_have_expected_symbols(self) -> None:
        for data_symbols, repair_symbols in ((28, 4), (24, 8), (20, 12)):
            with self.subTest(
                data_symbols=data_symbols,
                repair_symbols=repair_symbols,
            ):
                config = make_config(data_symbols, repair_symbols)
                block = self.encoder.encode(
                    bytes(range(data_symbols)),
                    config,
                )

                self.assertEqual(len(block.source_symbols), data_symbols)
                self.assertEqual(len(block.repair_symbols), repair_symbols)
                self.assertEqual(
                    tuple(symbol.index for symbol in block.source_symbols),
                    tuple(range(data_symbols)),
                )
                self.assertEqual(
                    tuple(symbol.index for symbol in block.repair_symbols),
                    tuple(range(data_symbols, data_symbols + repair_symbols)),
                )
                self.assertTrue(
                    all(
                        len(symbol.data) == 1
                        for symbol in (
                            block.source_symbols + block.repair_symbols
                        )
                    )
                )
                block.validate(config)

    def test_experimental_configurations_recover_at_erasure_limit(self) -> None:
        for data_symbols, repair_symbols in ((28, 4), (24, 8), (20, 12)):
            with self.subTest(
                data_symbols=data_symbols,
                repair_symbols=repair_symbols,
            ):
                config = make_config(data_symbols, repair_symbols)
                source = bytes(range(data_symbols))
                block = self.encoder.encode(source, config)
                erasures = tuple(range(repair_symbols))
                received = tuple(
                    symbol
                    for symbol in block.source_symbols + block.repair_symbols
                    if symbol.index not in erasures
                )
                result = ReedSolomonDecoder().decode(
                    received,
                    erasures,
                    config,
                    block.metadata,
                )

                self.assertTrue(result.success)
                self.assertEqual(result.source_block, source)
                self.assertEqual(result.recovered_indices, erasures)

    def test_padding_preserves_original_length(self) -> None:
        config = make_config(data_symbols=4, repair_symbols=3)
        block = self.encoder.encode(b"\x01\x02\x03", config)

        self.assertEqual(block.metadata, FecBlockMetadata(3, 1))
        self.assertEqual(
            tuple(symbol.data for symbol in block.source_symbols),
            (b"\x01", b"\x02", b"\x03", b"\x00"),
        )
        result = self.decoder.decode(
            block.source_symbols + block.repair_symbols,
            (),
            config,
            block.metadata,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.source_block, b"\x01\x02\x03")

    def test_reject_padding_and_incomplete_blocks(self) -> None:
        config = make_config(
            padding_policy=PaddingPolicy.REJECT,
            incomplete_block_policy=IncompleteBlockPolicy.REJECT,
        )

        self.encoder.encode(b"\x01\x02\x03\x04", config)
        with self.assertRaises(FecInputError):
            self.encoder.encode(b"\x01\x02\x03", config)

    def test_invalid_algorithm_specific_configurations_are_rejected(self) -> None:
        cases = (
            make_config(symbol_size=2),
            make_config(interleaving_depth=1),
            make_config(algorithm_id="fake"),
            make_config(data_symbols=200, repair_symbols=56),
        )
        for config in cases:
            with self.subTest(
                config=config
            ), self.assertRaises(FecConfigurationError):
                self.encoder.encode(b"\x00" * config.source_capacity, config)


class ReedSolomonDecodingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.encoder = ReedSolomonEncoder()
        self.decoder = ReedSolomonDecoder()
        self.config = make_config()
        block = self.encoder.encode(b"\x01\x02\x03\x04", self.config)
        self.all_symbols = block.source_symbols + block.repair_symbols
        self.metadata = block.metadata

    def decode(
        self,
        symbols: list[FecSymbol] | tuple[FecSymbol, ...],
        erasures: tuple[int, ...] = (),
    ) -> DecodeResult:
        return self.decoder.decode(
            symbols,
            erasures,
            self.config,
            self.metadata,
        )

    def test_decodes_without_losses(self) -> None:
        result = self.decode(self.all_symbols)

        self.assertTrue(result.success)
        self.assertEqual(result.source_block, b"\x01\x02\x03\x04")
        self.assertEqual(result.recovered_indices, ())
        self.assertEqual(result.invalid_indices, ())

    def test_recovers_every_single_erasure(self) -> None:
        for erased_index in range(self.config.block_symbols):
            with self.subTest(erased_index=erased_index):
                received = tuple(
                    symbol
                    for symbol in self.all_symbols
                    if symbol.index != erased_index
                )
                result = self.decode(received, (erased_index,))

                self.assertTrue(result.success)
                self.assertEqual(result.source_block, b"\x01\x02\x03\x04")
                self.assertEqual(result.recovered_indices, (erased_index,))

    def test_recovers_any_set_at_the_erasure_limit(self) -> None:
        for erased_indices in itertools.combinations(
            range(self.config.block_symbols),
            self.config.repair_symbols,
        ):
            with self.subTest(erased_indices=erased_indices):
                received = tuple(
                    symbol
                    for symbol in self.all_symbols
                    if symbol.index not in erased_indices
                )
                result = self.decode(received, erased_indices)

                self.assertTrue(result.success)
                self.assertEqual(result.source_block, b"\x01\x02\x03\x04")
                self.assertEqual(
                    result.recovered_indices,
                    erased_indices,
                )

    def test_fails_when_erasures_exceed_the_limit(self) -> None:
        erased_indices = (0, 1, 2, 3)
        received = tuple(
            symbol
            for symbol in self.all_symbols
            if symbol.index not in erased_indices
        )
        result = self.decode(received, erased_indices)

        self.assertFalse(result.success)
        self.assertIsNone(result.source_block)
        self.assertEqual(result.reason, DecodeFailureReason.INSUFFICIENT_SYMBOLS)
        self.assertEqual(result.missing_indices, erased_indices)

    def test_corrects_one_unknown_error_at_every_position(self) -> None:
        for error_index in range(self.config.block_symbols):
            with self.subTest(error_index=error_index):
                received = list(self.all_symbols)
                received[error_index] = alter_symbol(
                    received[error_index],
                )
                result = self.decode(received)

                self.assertTrue(result.success)
                self.assertEqual(result.source_block, b"\x01\x02\x03\x04")
                self.assertEqual(result.invalid_indices, (error_index,))
                self.assertEqual(result.recovered_indices, (error_index,))

    def test_corrects_errors_and_erasures_at_the_combined_limit(self) -> None:
        erased_indices = (0,)
        error_index = 1
        received = [
            alter_symbol(symbol)
            if symbol.index == error_index
            else symbol
            for symbol in self.all_symbols
            if symbol.index not in erased_indices
        ]
        result = self.decode(received, erased_indices)

        self.assertTrue(result.success)
        self.assertEqual(result.source_block, b"\x01\x02\x03\x04")
        self.assertEqual(result.invalid_indices, (error_index,))
        self.assertEqual(result.recovered_indices, (0, error_index))

    def test_fails_when_unknown_errors_exceed_the_limit(self) -> None:
        received = list(self.all_symbols)
        received[0] = alter_symbol(received[0], 0x11)
        received[1] = alter_symbol(received[1], 0x22)
        result = self.decode(received)

        self.assertFalse(result.success)
        self.assertIsNone(result.source_block)
        self.assertEqual(result.reason, DecodeFailureReason.UNKNOWN_CORRUPTION)

    def test_rejects_duplicate_and_invalid_decoder_inputs(self) -> None:
        with self.assertRaises(FecInputError):
            self.decode((self.all_symbols[0], self.all_symbols[0]))
        with self.assertRaises(FecInputError):
            self.decode((FecSymbol(0, b"\x00\x01"),))
        with self.assertRaises(FecInputError):
            self.decode((FecSymbol(self.config.block_symbols, b"\x00"),))
        with self.assertRaises(FecInputError):
            self.decode((self.all_symbols[0],), (0,))
        with self.assertRaises(FecInputError):
            self.decode((self.all_symbols[0],), (self.config.block_symbols,))

    def test_invalid_metadata_is_rejected_without_partial_data(self) -> None:
        with self.assertRaises(FecInputError):
            self.decoder.decode(
                self.all_symbols,
                (),
                self.config,
                FecBlockMetadata(3, 0),
            )

    def test_fails_without_returning_partial_source_when_too_few_symbols(
        self,
    ) -> None:
        received = self.all_symbols[: self.config.data_symbols - 1]
        result = self.decode(received, (4, 5, 6))

        self.assertFalse(result.success)
        self.assertIsNone(result.source_block)
        self.assertEqual(result.reason, DecodeFailureReason.INSUFFICIENT_SYMBOLS)


if __name__ == "__main__":
    unittest.main()
