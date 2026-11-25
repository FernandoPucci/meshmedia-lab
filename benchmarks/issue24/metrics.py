"""Metric helpers for individual Issue #24 executions."""

from __future__ import annotations

import math
from typing import Any

from .fixtures import GrayPixels
from .strategies import DecodeSummary


def overhead_percent(wire_bytes: int, encoded_bytes: int) -> float:
    """Calculate overhead relative to codec bytes."""

    if encoded_bytes <= 0:
        raise ValueError("encoded_bytes must be positive")
    return ((wire_bytes - encoded_bytes) / encoded_bytes) * 100.0


def _pixel_bytes(pixels: GrayPixels) -> bytes:
    return bytes(pixel for row in pixels for pixel in row)


def quality_metrics(
    reference: GrayPixels,
    reconstructed: GrayPixels | None,
    *,
    expected_encoded: bytes,
    actual_encoded: bytes | None,
) -> dict[str, Any]:
    """Compare a reconstructed image to its exact grayscale reference."""

    encoded_equal = (
        actual_encoded is not None and actual_encoded == expected_encoded
    )
    if reconstructed is None:
        return {
            "encoded_byte_equal": encoded_equal,
            "pixel_byte_equal": None,
            "pixels_total": len(reference) * len(reference[0]),
            "pixels_different": None,
            "pixels_different_percent": None,
            "mse": None,
            "psnr_db": None,
            "psnr_infinite": False,
            "ssim": None,
            "ssim_available": False,
        }

    reference_bytes = _pixel_bytes(reference)
    reconstructed_bytes = _pixel_bytes(reconstructed)
    if len(reference_bytes) != len(reconstructed_bytes):
        raise ValueError("reference and reconstructed images have different sizes")

    differences = [
        actual - expected
        for expected, actual in zip(reference_bytes, reconstructed_bytes)
    ]
    different_count = sum(value != 0 for value in differences)
    squared_error = sum(value * value for value in differences)
    pixels_total = len(reference_bytes)
    mse = squared_error / pixels_total
    psnr = None if mse == 0 else 10.0 * math.log10((255 * 255) / mse)
    return {
        "encoded_byte_equal": encoded_equal,
        "pixel_byte_equal": reference_bytes == reconstructed_bytes,
        "pixels_total": pixels_total,
        "pixels_different": different_count,
        "pixels_different_percent": (different_count / pixels_total) * 100.0,
        "mse": mse,
        "psnr_db": psnr,
        "psnr_infinite": mse == 0,
        "ssim": None,
        "ssim_available": False,
    }


def decode_metrics(summary: DecodeSummary | None) -> dict[str, Any]:
    """Flatten block-level FEC diagnostics for a result record."""

    if summary is None:
        return {
            "blocks_total": 0,
            "blocks_decoded": 0,
            "blocks_recovered": 0,
            "blocks_failed": 0,
            "symbols_recovered": 0,
            "symbols_missing": 0,
            "symbols_invalid": 0,
            "decode_failure_reasons": [],
        }
    return {
        "blocks_total": summary.blocks_total,
        "blocks_decoded": summary.blocks_decoded,
        "blocks_recovered": summary.blocks_recovered,
        "blocks_failed": summary.blocks_failed,
        "symbols_recovered": summary.symbols_recovered,
        "symbols_missing": summary.symbols_missing,
        "symbols_invalid": summary.symbols_invalid,
        "decode_failure_reasons": list(summary.failure_reasons),
    }


def scenario_observations(
    *,
    units_sent: int,
    units_lost: int,
    corruption_events: int,
    units_corrupted: int,
    loss_rate: float,
    corruption_rate: float,
) -> dict[str, Any]:
    """Return requested and observed transport fault rates."""

    return {
        "loss_rate_requested": loss_rate,
        "loss_rate_observed": (
            units_lost / units_sent if units_sent else None
        ),
        "corruption_rate_requested": corruption_rate,
        "corruption_event_rate_observed": (
            corruption_events / units_sent if units_sent else None
        ),
        "corrupted_unit_rate_observed": (
            units_corrupted / units_sent if units_sent else None
        ),
    }
