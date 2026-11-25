import unittest

from benchmarks.issue24.viewer import (
    _format_state,
    _html_document,
    _strategy_spec,
)


class Issue24ViewerTests(unittest.TestCase):
    def test_strategy_id_preserves_the_rs_configuration(self) -> None:
        self.assertEqual(
            _strategy_spec("crc+rs-rs32-24-8"),
            ("crc+rs", (24, 8)),
        )
        self.assertEqual(
            _strategy_spec("rs-only-rs32-20-12"),
            ("rs-only", (20, 12)),
        )
        self.assertEqual(_strategy_spec("crc-only"), ("crc-only", None))

    def test_failure_state_does_not_claim_a_reconstruction(self) -> None:
        state = _format_state(
            {
                "reconstruction_integral": False,
                "reconstruction_available": False,
                "failure_reason": "incomplete_transmission",
            }
        )
        self.assertIn("FALHA", state)
        self.assertIn("incomplete_transmission", state)

    def test_web_viewer_contains_pixelated_side_by_side_controls(self) -> None:
        document = _html_document([])

        self.assertIn("image-rendering:pixelated", document)
        self.assertIn("EXECUTAR EXPERIMENTO", document)
        self.assertIn("/api/run", document)
