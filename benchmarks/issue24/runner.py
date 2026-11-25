"""Execution engine for the reproducible Issue #24 matrix."""

from __future__ import annotations

import csv
import json
import platform
import subprocess
import time
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from meshmedia_lab import __version__ as software_version
from meshmedia_lab.codec.encoder import ImageEncoder

from .config import (
    FEC_VARIANTS,
    RESOLUTIONS,
    SCENARIOS,
    Scenario,
    StrategyName,
    derive_seed,
    strategy_id,
    trace_seed,
)
from .faults import DeterministicFaultChannel
from .fixtures import (
    Fixture,
    build_fixture,
    generate_reference_images,
    save_gray_pixels,
)
from .metrics import (
    decode_metrics,
    overhead_percent,
    quality_metrics,
    scenario_observations,
)
from .strategies import (
    PreparedTransmission,
    StrategyOutcome,
    prepare_transmission,
    receive,
)

FIXTURE_IDS = ("TEST-01", "TEST-02", "TEST-03")
STRATEGIES: tuple[StrategyName, ...] = (
    "crc-only",
    "crc+rs",
    "rs-only",
)
SddRevision = "0.8.0-draft"


def _git_commit(source_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def _scenario(scenario_id: str) -> Scenario:
    for scenario in SCENARIOS:
        if scenario.scenario_id == scenario_id:
            return scenario
    raise ValueError(f"unknown scenario: {scenario_id}")


def _resolution_label(resolution: tuple[int, int]) -> str:
    return f"{resolution[0]}x{resolution[1]}"


def _run_id(
    fixture_id: str,
    resolution: tuple[int, int],
    strategy: StrategyName,
    fec_variant: tuple[int, int] | None,
    scenario_id: str,
    repetition: int,
) -> str:
    variant = strategy_id(strategy, fec_variant)
    return (
        f"{fixture_id.lower()}-{_resolution_label(resolution)}-"
        f"{variant.replace('+', '-')}-{scenario_id.lower()}-r{repetition:02d}"
    )


def _block_details(summary) -> list[dict[str, object]]:
    if summary is None:
        return []
    return [
        {
            "block_index": result.block_index,
            "success": result.success,
            "recovered_symbols": result.recovered_symbols,
            "missing_symbols": result.missing_symbols,
            "invalid_symbols": result.invalid_symbols,
            "reason": result.reason,
        }
        for result in summary.block_results
    ]


def _prepared_metrics(prepared: PreparedTransmission) -> dict[str, object]:
    return {
        "source_bytes": prepared.encoded_bytes,
        "reference_pixel_bytes": (
            prepared.encoded.width * prepared.encoded.height
        ),
        "encoded_bytes": prepared.encoded_bytes,
        "padded_source_bytes": prepared.padded_source_bytes,
        "padding_bytes": prepared.padding_bytes,
        "repair_bytes": prepared.repair_bytes,
        "fec_frame_bytes": prepared.fec_frame_bytes,
        "payload_bytes": prepared.payload_bytes,
        "header_bytes": prepared.header_bytes,
        "crc_bytes": prepared.crc_bytes,
        "wire_bytes": prepared.wire_bytes,
        "bytes_transmitted": prepared.wire_bytes,
        "overhead_bytes": prepared.wire_bytes - prepared.encoded_bytes,
        "overhead_percent": overhead_percent(
            prepared.wire_bytes,
            prepared.encoded_bytes,
        ),
        "messages_sent": len(prepared.units),
        "packets_sent": len(prepared.units),
        "message_unit": prepared.message_unit,
        "total_blocks": prepared.total_blocks,
    }


def _outcome_metrics(
    prepared: PreparedTransmission,
    outcome: StrategyOutcome,
    *,
    delivered_count: int,
    lost_count: int,
    corrupted_count: int,
    corruption_events: int,
) -> dict[str, object]:
    final_decode = decode_metrics(outcome.final_decode)
    first_decode = decode_metrics(outcome.first_decode)
    metrics = {
        "messages_received": outcome.messages_received,
        "messages_delivered": delivered_count,
        "messages_validated": outcome.messages_validated,
        "messages_crc_rejected": outcome.messages_crc_rejected,
        "messages_used_to_conclude": outcome.messages_used_to_conclude,
        "completion_message_index": outcome.completion_message_index,
        "messages_after_completion": (
            len(prepared.units) - outcome.completion_message_index
            if outcome.completion_message_index is not None
            else None
        ),
        "packets_received": outcome.messages_received,
        "packets_lost": lost_count,
        "packets_corrupted": corrupted_count,
        "corruption_events": corruption_events,
        "packets_crc_rejected": outcome.messages_crc_rejected,
        "reconstruction_available": (
            outcome.reconstructed_encoded is not None
        ),
        "decoder_concluded": outcome.first_decode is not None
        if prepared.strategy != "crc-only"
        else outcome.completion_message_index is not None,
        "failure_reason": outcome.failure_reason,
        "final_decode": final_decode,
        "first_decode": first_decode,
        "final_block_details": _block_details(outcome.final_decode),
        "first_block_details": _block_details(outcome.first_decode),
    }
    metrics.update(
        {
            "blocks_total": final_decode["blocks_total"],
            "blocks_decoded": final_decode["blocks_decoded"],
            "blocks_recovered": final_decode["blocks_recovered"],
            "blocks_failed": final_decode["blocks_failed"],
            "symbols_recovered": final_decode["symbols_recovered"],
            "symbols_missing": final_decode["symbols_missing"],
            "symbols_invalid": final_decode["symbols_invalid"],
            "decode_failure_reasons": final_decode[
                "decode_failure_reasons"
            ],
        }
    )
    return metrics


def execute_one(
    *,
    fixture: Fixture,
    resolution: tuple[int, int],
    strategy: StrategyName,
    fec_variant: tuple[int, int] | None,
    scenario: Scenario,
    repetition: int,
    output_directory: Path,
    source_root: Path = Path("."),
    repository_commit: str | None = None,
) -> dict[str, object]:
    """Execute and persist one matrix cell."""

    width, height = resolution
    run_id = _run_id(
        fixture.fixture_id,
        resolution,
        strategy,
        fec_variant,
        scenario.scenario_id,
        repetition,
    )
    seed = trace_seed(
        fixture.fixture_id,
        resolution,
        scenario.scenario_id,
        repetition,
    )
    image_id = derive_seed("issue24-image", run_id) % 0x10000
    started_at = datetime.now(timezone.utc).isoformat()
    total_start = time.perf_counter_ns()

    encode_start = time.perf_counter_ns()
    encoded = ImageEncoder(width=width, height=height, levels=16).encode(
        fixture.pixels
    )
    encode_time_ns = time.perf_counter_ns() - encode_start

    prepare_start = time.perf_counter_ns()
    prepared = prepare_transmission(
        fixture.pixels,
        width=width,
        height=height,
        strategy=strategy,
        fec_variant=fec_variant,
        image_id=image_id,
        encoded_image=encoded,
    )
    prepare_time_ns = time.perf_counter_ns() - prepare_start

    channel_start = time.perf_counter_ns()
    delivered, fault_stats = DeterministicFaultChannel().transmit(
        prepared.units,
        scenario=scenario,
        seed=seed,
    )
    channel_time_ns = time.perf_counter_ns() - channel_start

    decode_start = time.perf_counter_ns()
    outcome = receive(prepared, delivered)
    decode_time_ns = time.perf_counter_ns() - decode_start
    total_time_ns = time.perf_counter_ns() - total_start

    quality = quality_metrics(
        fixture.pixels,
        outcome.reconstructed_pixels,
        expected_encoded=encoded.data,
        actual_encoded=outcome.reconstructed_encoded,
    )
    reconstruction_integral = (
        quality["encoded_byte_equal"] is True
        and quality["pixel_byte_equal"] is True
    )

    received_image_path: str | None = None
    if outcome.reconstructed_pixels is not None:
        relative_path = Path("results") / "images" / f"{run_id}-received.png"
        save_gray_pixels(
            outcome.reconstructed_pixels,
            output_directory / relative_path,
        )
        received_image_path = relative_path.as_posix()

    reference_path = (
        Path("reference")
        / fixture.fixture_id
        / f"{width}x{height}.png"
    )
    record: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "environment": "local-simulation",
        "software_version": software_version,
        "protocol_version": 1,
        "sdd_revision": SddRevision,
        "repository_commit": repository_commit,
        "python_version": platform.python_version(),
        "started_at_utc": started_at,
        "fixture_id": fixture.fixture_id,
        "fixture_description": fixture.description,
        "fixture_seed": fixture.seed,
        "fixture_source_path": fixture.source_path,
        "reference_path": reference_path.as_posix(),
        "width": width,
        "height": height,
        "resolution": _resolution_label(resolution),
        "codec": "grayscale",
        "codec_id": 0x01,
        "levels": 16,
        "payload_limit": 64,
        "transmission_mode": "legacy",
        "strategy": strategy,
        "strategy_id": prepared.strategy_id,
        "message_unit": prepared.message_unit,
        "fec_algorithm": (
            "reed_solomon" if fec_variant is not None else "none"
        ),
        "fec_data_symbols": (
            fec_variant[0] if fec_variant is not None else None
        ),
        "fec_repair_symbols": (
            fec_variant[1] if fec_variant is not None else None
        ),
        "fec_symbol_size": 1 if fec_variant is not None else None,
        "fec_interleaving_depth": 0 if fec_variant is not None else None,
        "scenario_id": scenario.scenario_id,
        "scenario_kind": scenario.kind,
        "loss_rate_requested": scenario.loss_rate,
        "corruption_rate_requested": scenario.corruption_rate,
        "seed": seed,
        "repetition": repetition,
        "image_id": image_id,
        "reconstruction_integral": reconstruction_integral,
        "reconstruction_success": outcome.reconstructed_encoded is not None,
        "equality_byte_to_byte": quality["encoded_byte_equal"],
        "received_image_path": received_image_path,
        "encode_time_ns": encode_time_ns,
        "fec_prepare_time_ns": prepare_time_ns,
        "channel_time_ns": channel_time_ns,
        "decode_time_ns": decode_time_ns,
        "total_time_ns": total_time_ns,
    }
    record.update(_prepared_metrics(prepared))
    record.update(
        scenario_observations(
            units_sent=fault_stats.units_sent,
            units_lost=fault_stats.units_lost,
            corruption_events=fault_stats.corruption_events,
            units_corrupted=fault_stats.units_corrupted,
            loss_rate=scenario.loss_rate,
            corruption_rate=scenario.corruption_rate,
        )
    )
    record.update(
        _outcome_metrics(
            prepared,
            outcome,
            delivered_count=fault_stats.units_delivered,
            lost_count=fault_stats.units_lost,
            corrupted_count=fault_stats.units_corrupted,
            corruption_events=fault_stats.corruption_events,
        )
    )
    record["corrupted_bytes"] = fault_stats.corrupted_bytes
    record["lost_ordinals"] = list(fault_stats.lost_ordinals)
    record["corrupted_ordinals"] = list(fault_stats.corrupted_ordinals)
    record["quality"] = quality
    record["historical_baseline"] = (
        {
            "source": "docs/experiment-matrix.md#12-resultados-locais-registrados",
            "comparable": (
                strategy == "crc-only"
                and scenario.scenario_id == "NO-FAIL"
                and fixture.fixture_id == "TEST-03"
                and resolution in ((32, 32), (64, 64))
            ),
        }
    )

    raw_path = output_directory / "results" / "raw" / f"{run_id}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return record


def iter_cases(
    *,
    fixtures: Iterable[str] = FIXTURE_IDS,
    resolutions: Iterable[tuple[int, int]] = RESOLUTIONS,
    strategies: Iterable[StrategyName] = STRATEGIES,
    scenarios: Iterable[str] = tuple(
        scenario.scenario_id for scenario in SCENARIOS
    ),
    repetitions: int = 10,
):
    """Yield the complete or filtered experiment matrix."""

    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    scenario_values = tuple(_scenario(value) for value in scenarios)
    for fixture_id in fixtures:
        for resolution in resolutions:
            for strategy in strategies:
                variants = (None,) if strategy == "crc-only" else FEC_VARIANTS
                for fec_variant in variants:
                    for scenario in scenario_values:
                        for repetition in range(1, repetitions + 1):
                            yield (
                                fixture_id,
                                resolution,
                                strategy,
                                fec_variant,
                                scenario,
                                repetition,
                            )


_WORKER_FIXTURE_CACHE: dict[tuple[str, int, int, str], Fixture] = {}


def _execute_case_in_worker(
    case: tuple[
        str,
        tuple[int, int],
        StrategyName,
        tuple[int, int] | None,
        Scenario,
        int,
        Path,
        Path,
        str | None,
    ],
) -> dict[str, object]:
    (
        fixture_id,
        resolution,
        strategy,
        fec_variant,
        scenario,
        repetition,
        output_directory,
        source_root,
        repository_commit,
    ) = case
    key = (
        fixture_id,
        resolution[0],
        resolution[1],
        str(source_root),
    )
    fixture = _WORKER_FIXTURE_CACHE.get(key)
    if fixture is None:
        fixture = build_fixture(
            fixture_id,
            resolution[0],
            resolution[1],
            source_root=source_root,
        )
        _WORKER_FIXTURE_CACHE[key] = fixture
    return execute_one(
        fixture=fixture,
        resolution=resolution,
        strategy=strategy,
        fec_variant=fec_variant,
        scenario=scenario,
        repetition=repetition,
        output_directory=output_directory,
        source_root=source_root,
        repository_commit=repository_commit,
    )


def _load_raw_records(output_directory: Path) -> list[dict[str, object]]:
    raw_directory = output_directory / "results" / "raw"
    records: list[dict[str, object]] = []
    for path in sorted(raw_directory.glob("*.json")):
        if path.name == "results.jsonl":
            continue
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def write_result_indexes(output_directory: Path) -> list[dict[str, object]]:
    """Write deterministic JSONL and CSV indexes for all raw records."""

    records = _load_raw_records(output_directory)
    records.sort(key=lambda record: str(record["run_id"]))
    raw_directory = output_directory / "results" / "raw"
    raw_directory.mkdir(parents=True, exist_ok=True)
    with (raw_directory / "results.jsonl").open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    summary_directory = output_directory / "results" / "summary"
    summary_directory.mkdir(parents=True, exist_ok=True)
    summary_path = summary_directory / "results.csv"
    columns = (
        "run_id",
        "fixture_id",
        "resolution",
        "strategy_id",
        "scenario_id",
        "repetition",
        "seed",
        "messages_sent",
        "messages_received",
        "messages_validated",
        "messages_used_to_conclude",
        "packets_lost",
        "packets_corrupted",
        "messages_crc_rejected",
        "symbols_recovered",
        "blocks_recovered",
        "blocks_failed",
        "reconstruction_integral",
        "pixels_different",
        "psnr_db",
        "wire_bytes",
        "overhead_percent",
        "encode_time_ns",
        "decode_time_ns",
        "total_time_ns",
        "failure_reason",
    )
    with summary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for record in records:
            quality = record.get("quality", {})
            final_decode = record.get("final_decode", {})
            row = {
                column: record.get(column)
                for column in columns
            }
            row["symbols_recovered"] = final_decode.get(
                "symbols_recovered",
                record.get("symbols_recovered"),
            )
            row["blocks_recovered"] = final_decode.get(
                "blocks_recovered",
                record.get("blocks_recovered"),
            )
            row["blocks_failed"] = final_decode.get(
                "blocks_failed",
                record.get("blocks_failed"),
            )
            row["pixels_different"] = quality.get("pixels_different")
            row["psnr_db"] = quality.get("psnr_db")
            writer.writerow(row)
    return records


def run_matrix(
    output_directory: Path,
    *,
    source_root: Path = Path("."),
    fixtures: Iterable[str] = FIXTURE_IDS,
    resolutions: Iterable[tuple[int, int]] = RESOLUTIONS,
    strategies: Iterable[StrategyName] = STRATEGIES,
    scenarios: Iterable[str] = tuple(
        scenario.scenario_id for scenario in SCENARIOS
    ),
    repetitions: int = 10,
    workers: int = 1,
    resume: bool = False,
) -> list[dict[str, object]]:
    """Run a selected matrix slice and refresh its indexes."""

    output_directory.mkdir(parents=True, exist_ok=True)
    generate_reference_images(
        output_directory / "reference",
        source_root=source_root,
    )
    if workers <= 0:
        raise ValueError("workers must be positive")
    repository_commit = _git_commit(source_root)
    cases = tuple(
        iter_cases(
            fixtures=fixtures,
            resolutions=resolutions,
            strategies=strategies,
            scenarios=scenarios,
            repetitions=repetitions,
        )
    )
    if resume:
        raw_directory = output_directory / "results" / "raw"
        cases = tuple(
            case
            for case in cases
            if not (
                raw_directory
                / f"{_run_id(case[0], case[1], case[2], case[3], case[4].scenario_id, case[5])}.json"
            ).exists()
        )
    if workers > 1:
        worker_cases = tuple(
            (
                fixture_id,
                resolution,
                strategy,
                fec_variant,
                scenario,
                repetition,
                output_directory,
                source_root,
                repository_commit,
            )
            for (
                fixture_id,
                resolution,
                strategy,
                fec_variant,
                scenario,
                repetition,
            ) in cases
        )
        with ProcessPoolExecutor(max_workers=workers) as executor:
            for _ in executor.map(_execute_case_in_worker, worker_cases):
                pass
        return write_result_indexes(output_directory)

    fixture_cache: dict[tuple[str, int, int], Fixture] = {}
    for (
        fixture_id,
        resolution,
        strategy,
        fec_variant,
        scenario,
        repetition,
    ) in cases:
        key = (fixture_id, resolution[0], resolution[1])
        fixture = fixture_cache.get(key)
        if fixture is None:
            fixture = build_fixture(
                fixture_id,
                resolution[0],
                resolution[1],
                source_root=source_root,
            )
            fixture_cache[key] = fixture
        execute_one(
            fixture=fixture,
            resolution=resolution,
            strategy=strategy,
            fec_variant=fec_variant,
            scenario=scenario,
            repetition=repetition,
            output_directory=output_directory,
            source_root=source_root,
            repository_commit=repository_commit,
        )
    return write_result_indexes(output_directory)
