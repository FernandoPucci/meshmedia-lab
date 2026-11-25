"""Deterministic, content-targeted channel faults for Issue #24."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .config import Scenario


@dataclass(frozen=True, slots=True)
class WireUnit:
    """One transmitted unit and the byte range considered content."""

    ordinal: int
    raw: bytes
    content_offset: int
    content_length: int
    message_unit: str
    block_index: int | None = None
    symbol_index: int | None = None

    def __post_init__(self) -> None:
        raw = bytes(self.raw)
        object.__setattr__(self, "raw", raw)
        if self.ordinal < 0:
            raise ValueError("wire unit ordinal must be non-negative")
        if self.content_offset < 0 or self.content_length <= 0:
            raise ValueError("wire unit content range must be positive")
        if self.content_offset + self.content_length > len(raw):
            raise ValueError("wire unit content range exceeds raw bytes")
        if not self.message_unit:
            raise ValueError("wire unit message_unit cannot be empty")


@dataclass(frozen=True, slots=True)
class DeliveredUnit:
    """One unit delivered after the deterministic channel transformation."""

    unit: WireUnit
    raw: bytes
    corrupted: bool


@dataclass(frozen=True, slots=True)
class FaultStats:
    """Observed channel counters for one transmission."""

    units_sent: int
    units_lost: int
    units_delivered: int
    corruption_events: int
    units_corrupted: int
    corrupted_bytes: int
    lost_ordinals: tuple[int, ...]
    corruption_selected_ordinals: tuple[int, ...]
    corrupted_ordinals: tuple[int, ...]


def _fraction(seed: int, ordinal: int, stream: str) -> float:
    material = f"{seed}|{ordinal}|{stream}".encode("ascii")
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


class DeterministicFaultChannel:
    """Apply the same index-based fault sequence to every strategy."""

    def transmit(
        self,
        units: tuple[WireUnit, ...],
        *,
        scenario: Scenario,
        seed: int,
    ) -> tuple[tuple[DeliveredUnit, ...], FaultStats]:
        delivered: list[DeliveredUnit] = []
        lost_ordinals: list[int] = []
        corruption_selected_ordinals: list[int] = []
        corrupted_ordinals: list[int] = []
        corrupted_bytes = 0

        for unit in units:
            lost = _fraction(seed, unit.ordinal, "loss") < scenario.loss_rate
            corruption_selected = (
                _fraction(seed, unit.ordinal, "corruption")
                < scenario.corruption_rate
            )
            if corruption_selected:
                corruption_selected_ordinals.append(unit.ordinal)
            if lost:
                lost_ordinals.append(unit.ordinal)
                continue

            raw = unit.raw
            corrupted = False
            if corruption_selected:
                raw = self._corrupt_content(unit, seed)
                corrupted = True
                corrupted_ordinals.append(unit.ordinal)
                corrupted_bytes += 1
            delivered.append(
                DeliveredUnit(
                    unit=unit,
                    raw=raw,
                    corrupted=corrupted,
                )
            )

        return (
            tuple(delivered),
            FaultStats(
                units_sent=len(units),
                units_lost=len(lost_ordinals),
                units_delivered=len(delivered),
                corruption_events=len(corruption_selected_ordinals),
                units_corrupted=len(corrupted_ordinals),
                corrupted_bytes=corrupted_bytes,
                lost_ordinals=tuple(lost_ordinals),
                corruption_selected_ordinals=tuple(
                    corruption_selected_ordinals
                ),
                corrupted_ordinals=tuple(corrupted_ordinals),
            ),
        )

    @staticmethod
    def _corrupt_content(unit: WireUnit, seed: int) -> bytes:
        byte_selector = int(
            _fraction(seed, unit.ordinal, "corruption-byte")
            * unit.content_length
        )
        byte_selector = min(unit.content_length - 1, byte_selector)
        bit_selector = int(
            _fraction(seed, unit.ordinal, "corruption-bit") * 8
        )
        bit_selector = min(7, bit_selector)
        offset = unit.content_offset + byte_selector
        corrupted = bytearray(unit.raw)
        corrupted[offset] ^= 1 << bit_selector
        return bytes(corrupted)
