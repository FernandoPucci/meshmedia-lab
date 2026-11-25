import unittest

from benchmarks.issue24.config import Scenario
from benchmarks.issue24.faults import (
    DeterministicFaultChannel,
    WireUnit,
)


class Issue24FaultTests(unittest.TestCase):
    def test_corruption_only_changes_the_declared_content_range(self) -> None:
        unit = WireUnit(
            ordinal=0,
            raw=b"HEADER-CONTENT",
            content_offset=7,
            content_length=7,
            message_unit="test",
        )
        delivered, stats = DeterministicFaultChannel().transmit(
            (unit,),
            scenario=Scenario("CORRUPT", "corruption", 0.0, 1.0),
            seed=42,
        )

        self.assertEqual(len(delivered), 1)
        self.assertEqual(stats.units_corrupted, 1)
        changed = [
            index
            for index, (before, after) in enumerate(
                zip(unit.raw, delivered[0].raw)
            )
            if before != after
        ]
        self.assertEqual(len(changed), 1)
        self.assertIn(changed[0], range(7, 14))

    def test_same_seed_reuses_loss_and_corruption_decisions_by_ordinal(self) -> None:
        first_units = tuple(
            WireUnit(
                ordinal=index,
                raw=bytes((index, 0, 1, 2)),
                content_offset=1,
                content_length=3,
                message_unit="first",
            )
            for index in range(20)
        )
        second_units = tuple(
            WireUnit(
                ordinal=index,
                raw=bytes((255, index, 4, 5, 6)),
                content_offset=2,
                content_length=3,
                message_unit="second",
            )
            for index in range(20)
        )
        scenario = Scenario("MIX", "mixed", 0.25, 0.35)
        channel = DeterministicFaultChannel()
        _, first_stats = channel.transmit(
            first_units,
            scenario=scenario,
            seed=99,
        )
        _, second_stats = channel.transmit(
            second_units,
            scenario=scenario,
            seed=99,
        )

        self.assertEqual(first_stats.lost_ordinals, second_stats.lost_ordinals)
        self.assertEqual(
            first_stats.corruption_selected_ordinals,
            second_stats.corruption_selected_ordinals,
        )
        self.assertEqual(
            first_stats.corrupted_ordinals,
            second_stats.corrupted_ordinals,
        )
