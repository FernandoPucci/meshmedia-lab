"""Reproducible CRC/FEC comparison harness for Issue #24."""

from .config import (
    FEC_VARIANTS,
    RESOLUTIONS,
    SCENARIOS,
    Scenario,
    derive_seed,
)

__all__ = [
    "FEC_VARIANTS",
    "RESOLUTIONS",
    "SCENARIOS",
    "Scenario",
    "derive_seed",
]
