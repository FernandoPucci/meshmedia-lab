"""Configuration and deterministic identifiers for the Issue #24 matrix."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from meshmedia_lab.fec import (
    FecConfig,
    IncompleteBlockPolicy,
    PaddingPolicy,
)

StrategyName = Literal["crc-only", "crc+rs", "rs-only"]
ScenarioKind = Literal["none", "loss", "corruption", "mixed"]

RESOLUTIONS: tuple[tuple[int, int], ...] = (
    (32, 32),
    (64, 64),
    (128, 128),
)

FEC_VARIANTS: tuple[tuple[int, int], ...] = (
    (28, 4),
    (24, 8),
    (20, 12),
)

FIXTURE_SEEDS: dict[str, int] = {
    "TEST-01": 24001,
    "TEST-02": 24002,
    "TEST-03": 24003,
}


@dataclass(frozen=True, slots=True)
class Scenario:
    """One deterministic channel condition in the experiment matrix."""

    scenario_id: str
    kind: ScenarioKind
    loss_rate: float
    corruption_rate: float


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("NO-FAIL", "none", 0.0, 0.0),
    Scenario("LOSS-01", "loss", 0.01, 0.0),
    Scenario("LOSS-02", "loss", 0.05, 0.0),
    Scenario("LOSS-03", "loss", 0.10, 0.0),
    Scenario("LOSS-04", "loss", 0.20, 0.0),
    Scenario("LOSS-05", "loss", 0.30, 0.0),
    Scenario("CORRUPT-01", "corruption", 0.0, 0.01),
    Scenario("CORRUPT-02", "corruption", 0.0, 0.05),
    Scenario("CORRUPT-03", "corruption", 0.0, 0.10),
    Scenario("CORRUPT-04", "corruption", 0.0, 0.20),
    Scenario("MIX-01", "mixed", 0.01, 0.01),
    Scenario("MIX-02", "mixed", 0.05, 0.05),
    Scenario("MIX-03", "mixed", 0.10, 0.05),
    Scenario("MIX-04", "mixed", 0.10, 0.10),
    Scenario("MIX-05", "mixed", 0.20, 0.10),
)


def derive_seed(*parts: object) -> int:
    """Derive a stable 64-bit seed without using Python's randomized hash."""

    material = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:8], "big")


def fixture_seed(fixture_id: str) -> int:
    """Return the fixed seed assigned to one fixture."""

    try:
        return FIXTURE_SEEDS[fixture_id]
    except KeyError as error:
        raise ValueError(f"unknown fixture: {fixture_id}") from error


def trace_seed(
    fixture_id: str,
    resolution: tuple[int, int],
    scenario_id: str,
    repetition: int,
) -> int:
    """Return the seed shared by all strategies in one matrix cell."""

    width, height = resolution
    return derive_seed(
        "meshmedia-lab",
        "issue-24",
        fixture_id,
        f"{width}x{height}",
        scenario_id,
        repetition,
    )


def fec_config(data_symbols: int, repair_symbols: int) -> FecConfig:
    """Build one of the approved Reed-Solomon experiment configurations."""

    return FecConfig(
        algorithm_id="reed_solomon",
        symbol_size=1,
        data_symbols=data_symbols,
        repair_symbols=repair_symbols,
        block_symbols=data_symbols + repair_symbols,
        interleaving_depth=0,
        padding_policy=PaddingPolicy.ZERO_PAD,
        incomplete_block_policy=IncompleteBlockPolicy.PAD_TO_K,
    )


def strategy_id(strategy: StrategyName, fec: tuple[int, int] | None) -> str:
    """Return the stable identifier recorded in result artifacts."""

    if strategy == "crc-only":
        return "crc-only"
    if fec is None:
        raise ValueError(f"{strategy} requires an FEC variant")
    data_symbols, repair_symbols = fec
    return f"{strategy}-rs32-{data_symbols}-{repair_symbols}"
