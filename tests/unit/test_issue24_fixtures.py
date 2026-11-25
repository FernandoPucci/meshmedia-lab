import tempfile
import unittest
from pathlib import Path

from benchmarks.issue24.fixtures import (
    GRAY_PALETTE,
    build_fixture,
    generate_reference_images,
)
from meshmedia_lab.codec.decoder import ImageDecoder
from meshmedia_lab.codec.encoder import ImageEncoder


class Issue24FixtureTests(unittest.TestCase):
    def test_fixtures_are_deterministic_and_use_the_grayscale_palette(self) -> None:
        for fixture_id in ("TEST-01", "TEST-02", "TEST-03"):
            first = build_fixture(fixture_id, 32, 32)
            second = build_fixture(fixture_id, 32, 32)

            with self.subTest(fixture=fixture_id):
                self.assertEqual(first, second)
                self.assertTrue(
                    all(
                        pixel in GRAY_PALETTE
                        for row in first.pixels
                        for pixel in row
                    )
                )

    def test_fixture_round_trip_is_byte_exact_without_channel_faults(self) -> None:
        for fixture_id in ("TEST-01", "TEST-02", "TEST-03"):
            fixture = build_fixture(fixture_id, 32, 32)
            encoded = ImageEncoder(width=32, height=32, levels=16).encode(
                fixture.pixels
            )
            reconstructed = ImageDecoder().decode(encoded)

            with self.subTest(fixture=fixture_id):
                self.assertEqual(reconstructed, fixture.pixels)

    def test_reference_manifest_contains_all_fixtures_and_resolutions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            entries = generate_reference_images(Path(directory))
            self.assertEqual(len(entries), 9)
            self.assertTrue(
                (Path(directory) / "manifest.json").exists()
            )
            self.assertEqual(
                {
                    (entry["fixture_id"], entry["resolution"])
                    for entry in entries
                },
                {
                    (fixture, resolution)
                    for fixture in ("TEST-01", "TEST-02", "TEST-03")
                    for resolution in ("32x32", "64x64", "128x128")
                },
            )
