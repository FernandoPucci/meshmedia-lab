import tempfile
import unittest
from pathlib import Path

from benchmarks.issue24.report import write_reports
from benchmarks.issue24.runner import run_matrix


class Issue24RunnerTests(unittest.TestCase):
    def test_all_strategies_reconstruct_the_same_32_by_32_fixture_without_faults(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            records = run_matrix(
                Path(directory),
                fixtures=("TEST-01",),
                resolutions=((32, 32),),
                scenarios=("NO-FAIL",),
                repetitions=1,
            )
            write_reports(Path(directory), records)

        self.assertEqual(len(records), 7)
        self.assertTrue(
            all(record["reconstruction_integral"] for record in records)
        )
        message_counts = {
            record["strategy_id"]: record["messages_sent"]
            for record in records
        }
        self.assertEqual(message_counts["crc-only"], 8)
        self.assertEqual(message_counts["crc+rs-rs32-28-4"], 608)
        self.assertEqual(message_counts["crc+rs-rs32-24-8"], 704)
        self.assertEqual(message_counts["crc+rs-rs32-20-12"], 832)
        self.assertEqual(message_counts["rs-only-rs32-28-4"], 608)
        self.assertEqual(message_counts["rs-only-rs32-24-8"], 704)
        self.assertEqual(message_counts["rs-only-rs32-20-12"], 832)

    def test_corruption_is_rejected_by_crc_and_recoverable_by_stronger_rs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            records = run_matrix(
                Path(directory),
                fixtures=("TEST-01",),
                resolutions=((32, 32),),
                strategies=("crc-only", "crc+rs", "rs-only"),
                scenarios=("CORRUPT-04",),
                repetitions=1,
            )

        by_strategy = {record["strategy_id"]: record for record in records}
        crc_only = by_strategy["crc-only"]
        self.assertGreater(crc_only["messages_crc_rejected"], 0)
        self.assertFalse(crc_only["reconstruction_integral"])

        crc_rs = by_strategy["crc+rs-rs32-20-12"]
        self.assertGreater(crc_rs["messages_crc_rejected"], 0)
        self.assertTrue(crc_rs["reconstruction_integral"])

        rs_only = by_strategy["rs-only-rs32-20-12"]
        self.assertIsNone(rs_only["messages_crc_rejected"])
        self.assertGreater(rs_only["packets_corrupted"], 0)
