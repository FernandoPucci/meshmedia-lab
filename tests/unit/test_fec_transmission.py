import unittest

from meshmedia_lab.fec import (
    EncodedBlock,
    FecConfig,
    FecEncoder,
    FecInputError,
    FecSymbol,
    FecTransmission,
    IncompleteBlockPolicy,
    PaddingPolicy,
    ReedSolomonEncoder,
    prepare_fec_transmission,
    prepare_source_symbols,
)


def make_config(
    *,
    data_symbols: int = 4,
    repair_symbols: int = 3,
    padding_policy: PaddingPolicy = PaddingPolicy.ZERO_PAD,
    incomplete_block_policy: IncompleteBlockPolicy = (
        IncompleteBlockPolicy.PAD_TO_K
    ),
) -> FecConfig:
    return FecConfig(
        algorithm_id="reed_solomon",
        symbol_size=1,
        data_symbols=data_symbols,
        repair_symbols=repair_symbols,
        block_symbols=data_symbols + repair_symbols,
        interleaving_depth=0,
        padding_policy=padding_policy,
        incomplete_block_policy=incomplete_block_policy,
    )


class RecordingEncoder:
    def __init__(self) -> None:
        self.blocks: list[bytes] = []

    def encode(self, source_block: bytes, config: FecConfig) -> EncodedBlock:
        self.blocks.append(source_block)
        source_symbols, metadata = prepare_source_symbols(source_block, config)
        repair_symbols = tuple(
            FecSymbol(
                index=config.data_symbols + offset,
                data=bytes((offset + 1,)),
            )
            for offset in range(config.repair_symbols)
        )
        block = EncodedBlock(source_symbols, repair_symbols, metadata)
        block.validate(config)
        return block


class FecTransmissionPreparationTests(unittest.TestCase):
    def test_prepares_multiple_ordered_blocks_and_preserves_padding(self) -> None:
        transmission = prepare_fec_transmission(
            b"abcdefghij",
            make_config(),
            ReedSolomonEncoder(),
        )

        self.assertIsInstance(transmission, FecTransmission)
        self.assertEqual(transmission.encoded_length, 10)
        self.assertEqual(transmission.total_blocks, 3)
        self.assertEqual(transmission.total_symbols, 21)
        self.assertEqual(transmission.repair_symbol_count, 9)
        self.assertEqual(
            tuple(block.block_index for block in transmission.blocks),
            (0, 1, 2),
        )
        self.assertEqual(
            tuple(block.metadata.original_length for block in transmission.blocks),
            (4, 4, 2),
        )
        self.assertEqual(
            tuple(block.metadata.padding_length for block in transmission.blocks),
            (0, 0, 2),
        )
        self.assertEqual(
            tuple(symbol.data for symbol in transmission.blocks[2].source_symbols),
            (b"i", b"j", b"\x00", b"\x00"),
        )

    def test_encoder_is_called_through_the_abstract_contract(self) -> None:
        encoder = RecordingEncoder()
        self.assertIsInstance(encoder, FecEncoder)

        transmission = prepare_fec_transmission(
            b"abcdef",
            make_config(),
            encoder,
        )

        self.assertEqual(encoder.blocks, [b"abcd", b"ef"])
        self.assertEqual(transmission.blocks[0].source_symbols[0].data, b"a")
        self.assertEqual(transmission.blocks[1].metadata.original_length, 2)

    def test_reject_policies_are_applied_by_the_existing_contract(self) -> None:
        config = make_config(
            padding_policy=PaddingPolicy.REJECT,
            incomplete_block_policy=IncompleteBlockPolicy.REJECT,
        )

        prepare_fec_transmission(b"abcd", config, ReedSolomonEncoder())
        with self.assertRaises(FecInputError):
            prepare_fec_transmission(b"abc", config, ReedSolomonEncoder())

    def test_invalid_encoder_result_is_rejected(self) -> None:
        class InvalidEncoder:
            def encode(self, source_block: bytes, config: FecConfig):
                return object()

        with self.assertRaises(FecInputError):
            prepare_fec_transmission(
                b"abcd",
                make_config(),
                InvalidEncoder(),  # type: ignore[arg-type]
            )

    def test_invalid_configuration_fails_before_block_preparation(self) -> None:
        with self.assertRaises(ValueError):
            FecConfig(
                algorithm_id="reed_solomon",
                symbol_size=1,
                data_symbols=4,
                repair_symbols=3,
                block_symbols=6,
                interleaving_depth=0,
                padding_policy=PaddingPolicy.ZERO_PAD,
                incomplete_block_policy=IncompleteBlockPolicy.PAD_TO_K,
            )


if __name__ == "__main__":
    unittest.main()
