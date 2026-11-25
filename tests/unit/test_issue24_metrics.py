import unittest

from benchmarks.issue24.fixtures import build_fixture
from benchmarks.issue24.metrics import overhead_percent, quality_metrics


class Issue24MetricTests(unittest.TestCase):
    def test_overhead_uses_codec_bytes_as_the_denominator(self) -> None:
        self.assertEqual(overhead_percent(680, 512), 32.8125)

    def test_perfect_reconstruction_has_zero_pixel_difference(self) -> None:
        fixture = build_fixture("TEST-01", 32, 32)
        result = quality_metrics(
            fixture.pixels,
            fixture.pixels,
            expected_encoded=b"source",
            actual_encoded=b"source",
        )

        self.assertTrue(result["encoded_byte_equal"])
        self.assertTrue(result["pixel_byte_equal"])
        self.assertEqual(result["pixels_different"], 0)
        self.assertTrue(result["psnr_infinite"])

    def test_missing_reconstruction_does_not_create_a_fake_image(self) -> None:
        fixture = build_fixture("TEST-02", 32, 32)
        result = quality_metrics(
            fixture.pixels,
            None,
            expected_encoded=b"source",
            actual_encoded=None,
        )

        self.assertIsNone(result["pixels_different"])
        self.assertIsNone(result["psnr_db"])
        self.assertIsNone(result["pixel_byte_equal"])
