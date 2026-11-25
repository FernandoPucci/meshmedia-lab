"""CLI for the reproducible Issue #24 experiment matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmarks.issue24.config import (
    RESOLUTIONS,
    SCENARIOS,
)
from benchmarks.issue24.report import write_reports
from benchmarks.issue24.runner import (
    FIXTURE_IDS,
    STRATEGIES,
    iter_cases,
    run_matrix,
)


def _resolution(value: str) -> tuple[int, int]:
    parts = value.lower().split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            "resolution must use WIDTHxHEIGHT"
        )
    try:
        result = (int(parts[0]), int(parts[1]))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "resolution dimensions must be integers"
        ) from error
    if result not in RESOLUTIONS:
        raise argparse.ArgumentTypeError(
            "resolution must be 32x32, 64x64 or 128x128"
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the MeshMedia Lab Issue #24 comparison",
    )
    parser.add_argument(
        "--output-dir",
        default="experiments/issue-24",
        help="directory for references, results and reports",
    )
    parser.add_argument(
        "--source-root",
        default=".",
        help="repository root containing test-images/",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        choices=FIXTURE_IDS,
        help="fixture filter; repeat to select more than one",
    )
    parser.add_argument(
        "--resolution",
        action="append",
        type=_resolution,
        help="resolution filter; repeat to select more than one",
    )
    parser.add_argument(
        "--strategy",
        action="append",
        choices=STRATEGIES,
        help="strategy filter; repeat to select more than one",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        choices=tuple(scenario.scenario_id for scenario in SCENARIOS),
        help="scenario filter; repeat to select more than one",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=10,
        help="repetitions per selected cell",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="parallel worker processes; 1 keeps sequential execution",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="skip raw JSON files already generated for selected cells",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the selected execution count without running",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fixtures = tuple(args.fixture or FIXTURE_IDS)
    resolutions = tuple(args.resolution or RESOLUTIONS)
    strategies = tuple(args.strategy or STRATEGIES)
    scenarios = tuple(
        args.scenario
        or (scenario.scenario_id for scenario in SCENARIOS)
    )
    cases = tuple(
        iter_cases(
            fixtures=fixtures,
            resolutions=resolutions,
            strategies=strategies,
            scenarios=scenarios,
            repetitions=args.repetitions,
        )
    )
    print(f"selected_cases={len(cases)}")
    if args.dry_run:
        return 0

    output_directory = Path(args.output_dir)
    records = run_matrix(
        output_directory,
        source_root=Path(args.source_root),
        fixtures=fixtures,
        resolutions=resolutions,
        strategies=strategies,
        scenarios=scenarios,
        repetitions=args.repetitions,
        workers=args.workers,
        resume=args.resume,
    )
    summary = write_reports(output_directory, records)
    print(f"records_available={summary['record_count']}")
    print(
        "reconstruction_success_rate="
        f"{summary['reconstruction_success_rate']}"
    )
    print(f"output_directory={output_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
