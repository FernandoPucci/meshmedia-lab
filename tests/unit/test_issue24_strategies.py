import unittest

from benchmarks.issue24.fixtures import build_fixture
from benchmarks.issue24.strategies import prepare_transmission


class Issue24StrategyPreparationTests(unittest.TestCase):
    def test_crc_only_message_counts_match_the_codec_sizes(self) -> None:
        expected = {
            (32, 32): (512, 8, 680),
            (64, 64): (2048, 32, 2720),
            (128, 128): (8192, 128, 10880),
        }
        for resolution, values in expected.items():
            width, height = resolution
            prepared = prepare_transmission(
                build_fixture("TEST-01", width, height).pixels,
                width=width,
                height=height,
                strategy="crc-only",
                fec_variant=None,
            )
            with self.subTest(resolution=resolution):
                self.assertEqual(
                    (
                        prepared.encoded_bytes,
                        len(prepared.units),
                        prepared.wire_bytes,
                    ),
                    values,
                )

    def test_fec_message_counts_are_one_per_transmitted_symbol(self) -> None:
        expected = {
            (28, 4): 608,
            (24, 8): 704,
            (20, 12): 832,
        }
        fixture = build_fixture("TEST-01", 32, 32)
        for fec_variant, message_count in expected.items():
            prepared = prepare_transmission(
                fixture.pixels,
                width=32,
                height=32,
                strategy="crc+rs",
                fec_variant=fec_variant,
            )
            with self.subTest(fec_variant=fec_variant):
                self.assertEqual(len(prepared.units), message_count)
                self.assertEqual(
                    prepared.message_unit,
                    "mm1",
                )
