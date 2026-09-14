"""Rebuild tracked derived artefacts in isolation and compare their contents."""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_COLUMN = "built_at"
SEEDS = ("137", "941")
BUILDERS = (
    ("build_aging_series.py", (
        "data/derived/aging_age_structure.csv",
        "data/derived/aging_vital_change.csv",
        "docs/AGING_SERIES_RESULT.md",
    )),
    ("build_suicide_by_age.py", ("data/derived/suicide_by_age_rate.csv",)),
    ("build_vital_sex.py", ("data/derived/vital_suicide_by_age_sex_rate.csv",)),
    ("build_youth_rate.py", ("data/derived/youth_suicide_rate.csv",)),
)
COPIED_BUILDERS = (
    "build_aging_series.py",
    "build_suicide_by_age.py",
    "build_vital_sex.py",
    "build_youth_rate.py",
)
EXPECTED_OUTPUTS = frozenset(
    output for _, outputs in BUILDERS for output in outputs
)
NOT_COMPARED_OUTPUTS = {
    "docs/AGING_SERIES_RESULT.md": (
        "generated_work_log_numbers_covered_by_verify_aging_series.py"
    ),
}
COMPARED_OUTPUTS = EXPECTED_OUTPUTS - NOT_COMPARED_OUTPUTS.keys()
PRIMARY_INPUTS = (
    "data/estat/_meta.csv",
    "data/estat/pop_age3_longterm.csv",
    "data/estat/pop_total_5y_2025.csv",
    "data/estat/pop_total_single_age_annual.csv",
    "data/estat/vital_births_rates.csv",
    "data/estat/vital_deaths_rates.csv",
    "data/estat/vital_suicide_age_sex.csv",
    "data/npa/npa_suicide_age_annual.csv",
)
ROW_ID_COLUMNS = ("series_id", "year", "sex", "age_band")
MAX_DIFFERENCES = 5
TEMP_DIRECTORY_ENV = "J_SHRINKING_REDERIVATION_TEMP_DIR"


@dataclass(frozen=True)
class Comparison:
    passed: bool
    rows: int
    cells: int
    differences: int
    details: tuple[str, ...]


class BuildFailure(RuntimeError):
    """A copied builder could not produce its required output."""


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return reader.fieldnames, list(reader)


@contextmanager
def temporary_directory(prefix: str):
    """Create an isolated directory without Windows' restrictive tempfile ACL."""
    parent = Path(os.environ.get(TEMP_DIRECTORY_ENV, tempfile.gettempdir()))
    path = parent / f"{prefix}{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


def row_identity(row: dict[str, str], row_number: int) -> str:
    parts = [f"{column}={row[column]}" for column in ROW_ID_COLUMNS if column in row]
    return ",".join(parts) if parts else f"row_number={row_number}"


def compare_csv(left: Path, right: Path) -> Comparison:
    left_headers, left_rows = read_csv(left)
    right_headers, right_rows = read_csv(right)
    details: list[str] = []
    differences = 0
    if left_headers != right_headers:
        differences += 1
        details.append(f"header committed={left_headers!r} rebuilt={right_headers!r}")
    columns = [column for column in left_headers if column != EXCLUDED_COLUMN]
    if EXCLUDED_COLUMN not in left_headers:
        differences += 1
        details.append(f"missing_excluded_column column={EXCLUDED_COLUMN}")
    if any(column != EXCLUDED_COLUMN and column not in right_headers for column in left_headers):
        differences += 1
        details.append("rebuilt_header_is_missing_a_compared_column")
    rows = max(len(left_rows), len(right_rows))
    for index in range(rows):
        committed = left_rows[index] if index < len(left_rows) else None
        rebuilt = right_rows[index] if index < len(right_rows) else None
        identity = row_identity(committed or rebuilt or {}, index + 1)
        for column in columns:
            committed_value = committed.get(column, "<missing>") if committed else "<missing>"
            rebuilt_value = rebuilt.get(column, "<missing>") if rebuilt else "<missing>"
            if committed_value != rebuilt_value:
                differences += 1
                if len(details) < MAX_DIFFERENCES:
                    details.append(
                        "difference "
                        f"row={identity} column={column} "
                        f"committed={committed_value!r} rebuilt={rebuilt_value!r}"
                    )
    return Comparison(
        passed=differences == 0,
        rows=rows,
        cells=rows * len(columns),
        differences=differences,
        details=tuple(details),
    )


def files_in_tree(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


def copy_tree(destination: Path, builders_to_copy: tuple[str, ...] = COPIED_BUILDERS) -> set[str]:
    scripts_destination = destination / "scripts"
    scripts_destination.mkdir(parents=True, exist_ok=True)
    for builder in builders_to_copy:
        source = ROOT / "scripts" / builder
        if not source.is_file():
            raise BuildFailure(f"Committed builder is missing: scripts/{builder}")
        shutil.copy2(source, scripts_destination / builder)
    print(
        f"copied_builders: rebuild={destination.name} count={len(builders_to_copy)} "
        f"files={','.join(builders_to_copy)}"
    )
    for relative_name in PRIMARY_INPUTS:
        source = ROOT / relative_name
        if not source.is_file():
            raise BuildFailure(f"Committed primary input is missing: {relative_name}")
        target = destination / relative_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for output in EXPECTED_OUTPUTS:
        (destination / output).parent.mkdir(parents=True, exist_ok=True)
    return files_in_tree(destination)


def clean_environment(seed: str) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() != "ESTAT_APP_ID"
    }
    environment["PYTHONHASHSEED"] = seed
    return environment


def report_produced_files(destination: Path, copied_files: set[str]) -> bool:
    produced_files = files_in_tree(destination) - copied_files
    unexpected = sorted(produced_files - EXPECTED_OUTPUTS)
    missing = sorted(EXPECTED_OUTPUTS - produced_files)
    if not produced_files:
        print(f"produced_files: FAIL rebuild={destination.name} count=0 reason=no_files_produced")
        return False
    if not unexpected and not missing:
        print(f"produced_files: PASS rebuild={destination.name} count={len(produced_files)}")
        return True
    print(f"produced_files: FAIL rebuild={destination.name} count={len(produced_files)}")
    for path in unexpected:
        print(f"produced_files_detail: rebuild={destination.name} unexpected={path}")
    for path in missing:
        print(f"produced_files_detail: rebuild={destination.name} missing={path}")
    return False


def run_build(
    destination: Path, seed: str, builders_to_copy: tuple[str, ...] = COPIED_BUILDERS
) -> bool:
    copied_files = copy_tree(destination, builders_to_copy)
    environment = clean_environment(seed)
    for builder, outputs in BUILDERS:
        command = [sys.executable, str(destination / "scripts" / builder)]
        completed = subprocess.run(
            command, text=True, capture_output=True, env=environment, check=False
        )
        if completed.returncode != 0:
            raise BuildFailure(
                f"builder={builder} seed={seed} exit={completed.returncode}\n"
                f"stdout={completed.stdout[-2000:]}\nstderr={completed.stderr[-2000:]}"
            )
        for output in outputs:
            if not (destination / output).is_file():
                raise BuildFailure(f"builder={builder} seed={seed} did not create {output}")
    return report_produced_files(destination, copied_files)


def print_comparison(label: str, filename: str, result: Comparison) -> bool:
    passed = result.passed and result.cells > 0
    print(
        f"{label}: {'PASS' if passed else 'FAIL'} file={filename} "
        f"rows_compared={result.rows} cells_compared={result.cells} "
        f"differing_cells={result.differences}"
    )
    for detail in result.details:
        print(f"{label}_detail: file={filename} {detail}")
    return passed


def self_tests() -> bool:
    changed_passed = False
    missing_passed = False
    missing_builder_passed = False
    changed_differences = 0
    failure_detail = ""
    try:
        with temporary_directory("verify_rederivation_selftest_") as temporary:
            temporary_root = Path(temporary)
            committed_path = temporary_root / "committed.csv"
            rebuilt_path = temporary_root / "rebuilt.csv"
            for path, value in ((committed_path, "original"), (rebuilt_path, "changed")):
                with path.open("w", encoding="utf-8", newline="") as destination:
                    writer = csv.DictWriter(destination, fieldnames=["series_id", "value", "built_at"])
                    writer.writeheader()
                    writer.writerow({"series_id": "test", "value": value, "built_at": "timestamp"})
            changed = compare_csv(committed_path, rebuilt_path)
            changed_differences = changed.differences
            changed_passed = not changed.passed and changed.differences == 1
            try:
                read_csv(temporary_root / "missing.csv")
            except FileNotFoundError:
                missing_passed = True
            missing_builder = COPIED_BUILDERS[-1]
            incomplete_builders = COPIED_BUILDERS[:-1]
            try:
                run_build(temporary_root / "missing_builder", SEEDS[0], incomplete_builders)
            except BuildFailure as error:
                missing_builder_passed = f"builder={missing_builder}" in str(error)
    except OSError as error:
        failure_detail = f" reason={error}"
    print(
        f"self_test_changed_cell: {'PASS' if changed_passed else 'FAIL'} "
        f"differing_cells={changed_differences}{failure_detail}"
    )
    print(f"self_test_missing_file: {'PASS' if missing_passed else 'FAIL'}{failure_detail}")
    print(
        f"self_test_missing_builder: {'PASS' if missing_builder_passed else 'FAIL'} "
        f"removed={COPIED_BUILDERS[-1]}"
    )
    zero_passed = not all_comparisons_pass([])
    print(f"self_test_zero_file_run: {'PASS' if zero_passed else 'FAIL'} files_compared=0")
    return changed_passed and missing_passed and missing_builder_passed and zero_passed


def all_comparisons_pass(results: list[bool]) -> bool:
    return bool(results) and all(results)


def main() -> int:
    print(f"exclusion: column={EXCLUDED_COLUMN} reason=run_timestamp_not_data")
    print("environment: ESTAT_APP_ID=unset for every builder subprocess")
    print(f"hash_seeds: rebuild_1={SEEDS[0]} rebuild_2={SEEDS[1]}")
    print("coverage: compared_artefacts=5 not_covered=2")
    print(
        "coverage_detail: foreign_employment.csv=NOT_COVERED "
        "reason=inputs_under_data/mhlw_are_not_tracked"
    )
    for filename, reason in NOT_COMPARED_OUTPUTS.items():
        print(f"coverage_detail: {filename}=NOT_COMPARED reason={reason}")
    outcomes: list[bool] = []
    try:
        with temporary_directory("verify_rederivation_") as temporary:
            temporary_root = Path(temporary)
            first = temporary_root / "rebuild_1"
            second = temporary_root / "rebuild_2"
            outcomes.append(run_build(first, SEEDS[0]))
            outcomes.append(run_build(second, SEEDS[1]))
            for filename in sorted(COMPARED_OUTPUTS):
                committed = ROOT / filename
                rebuilt_first = first / filename
                rebuilt_second = second / filename
                outcomes.append(
                    print_comparison(
                        "committed_vs_rebuild_1",
                        filename,
                        compare_csv(committed, rebuilt_first),
                    )
                )
                outcomes.append(
                    print_comparison(
                        "rebuild_1_vs_rebuild_2",
                        filename,
                        compare_csv(rebuilt_first, rebuilt_second),
                    )
                )
    except (BuildFailure, OSError, ValueError) as error:
        print(f"rederivation: FAIL reason={error}")
        outcomes.append(False)
    self_test_passed = self_tests()
    print("files_compared: denominator=5 covered=5 not_covered=2")
    return 0 if all_comparisons_pass(outcomes) and self_test_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
