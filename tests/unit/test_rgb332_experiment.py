import unittest

from benchmarks.rgb332_experiment import _mm1_cost


class Rgb332ExperimentTests(unittest.TestCase):
    def test_mm1_cost_matches_32_by_32_rgb332(self) -> None:
        self.assertEqual(
            _mm1_cost(1024, 64),
            {
                "encoded_bytes": 1024,
                "fragment_count": 16,
                "header_bytes": 304,
                "crc_bytes": 32,
                "overhead_bytes": 336,
                "wire_bytes": 1360,
            },
        )

    def test_mm1_cost_matches_64_by_64_rgb332(self) -> None:
        self.assertEqual(
            _mm1_cost(4096, 64),
            {
                "encoded_bytes": 4096,
                "fragment_count": 64,
                "header_bytes": 1216,
                "crc_bytes": 128,
                "overhead_bytes": 1344,
                "wire_bytes": 5440,
            },
        )
