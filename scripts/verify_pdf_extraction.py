"""Verify that the committed NPA CSV is reproducible from its source PDF.

This check establishes repeatability only.  It deliberately does not claim that
pdfplumber interpreted the PDF layout correctly.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PDF_NAME = "R7jisatsunojoukyou.pdf"
PDF_PATH = ROOT / PDF_NAME
MANIFEST_PATH = ROOT / "data/sources_manifest.csv"
COMMITTED_CSV = ROOT / "data/npa/npa_suicide_age_annual.csv"
EXTRACTOR = ROOT / "scripts/extract_npa_longtable.py"
EXCLUDED_COLUMN = "retrieved_at"
ROW_ID_COLUMNS = ("year", "age_class", "age_class_source")
MAX_DIFFERENCES = 5
PINNED_PDFPLUMBER = "0.11.10"
TEMP_DIRECTORY_ENV = "J_SHRINKING_PDF_EXTRACTION_TEMP_DIR"


@dataclass(frozen=True)
class Comparison:
    passed: bool
    rows: int
    cells: int
    differences: int
    details: tuple[str, ...]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return reader.fieldnames, list(reader)


def row_identity(row: dict[str, str], row_number: int) -> str:
    parts = [f"{column}={row[column]}" for column in ROW_ID_COLUMNS if column in row]
    return ",".join(parts) if parts else f"row_number={row_number}"


def compare_rows(
    left_headers: list[str], left_rows: list[dict[str, str]], right_headers: list[str], right_rows: list[dict[str, str]]
) -> Comparison:
    details: list[str] = []
    differences = 0
    compared_columns = [column for column in left_headers if column != EXCLUDED_COLUMN]
    if EXCLUDED_COLUMN not in left_headers or EXCLUDED_COLUMN not in right_headers:
        differences += 1
        details.append(f"missing_excluded_column column={EXCLUDED_COLUMN}")
    if left_headers != right_headers:
        differences += 1
        details.append(f"header left={left_headers!r} right={right_headers!r}")
    right_only = [column for column in right_headers if column not in left_headers]
    left_missing = [column for column in compared_columns if column not in right_headers]
    if right_only or left_missing:
        differences += 1
        details.append(f"unmatched_columns left_missing={left_missing!r} right_only={right_only!r}")
    rows = max(len(left_rows), len(right_rows))
    for index in range(rows):
        left = left_rows[index] if index < len(left_rows) else None
        right = right_rows[index] if index < len(right_rows) else None
        identity = row_identity(left or right or {}, index + 1)
        for column in compared_columns:
            left_value = left.get(column, "<missing>") if left else "<missing>"
            right_value = right.get(column, "<missing>") if right else "<missing>"
            if left_value != right_value:
                differences += 1
                if len(details) < MAX_DIFFERENCES:
                    details.append(
                        f"difference row={identity} column={column} left={left_value!r} right={right_value!r}"
                    )
    return Comparison(differences == 0, rows, rows * len(compared_columns), differences, tuple(details))


def compare_csv(left: Path, right: Path) -> Comparison:
    return compare_rows(*read_csv(left), *read_csv(right))


def print_comparison(label: str, result: Comparison) -> bool:
    passed = result.passed and result.cells > 0
    print(
        f"{label}: {'PASS' if passed else 'FAIL'} rows_compared={result.rows} "
        f"cells_compared={result.cells} differing_cells={result.differences}"
    )
    for detail in result.details:
        print(f"{label}_detail: {detail}")
    return passed


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_matches(expected: str, actual: str) -> bool:
    """Return whether the ledger identifies the exact document under test."""
    return expected == actual


def manifest_record() -> dict[str, str]:
    _, records = read_csv(MANIFEST_PATH)
    matches = [record for record in records if record.get("local_path") == PDF_NAME]
    if len(matches) != 1:
        raise ValueError(f"manifest PDF record count={len(matches)} local_path={PDF_NAME}")
    return matches[0]


def temporary_directory(prefix: str) -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix=prefix, dir=os.environ.get(TEMP_DIRECTORY_ENV))


def extract(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PDF_PATH, destination / PDF_NAME)
    (destination / "data/npa").mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [sys.executable, str(EXTRACTOR)], cwd=destination, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"extractor exit={completed.returncode} cwd={destination}\n"
            f"stdout={completed.stdout[-2000:]}\nstderr={completed.stderr[-2000:]}"
        )
    output = destination / "data/npa/npa_suicide_age_annual.csv"
    if not output.is_file():
        raise RuntimeError(f"extractor produced no CSV cwd={destination}")
    return output


def pdfplumber_version() -> str | None:
    if importlib.util.find_spec("pdfplumber") is None:
        return None
    try:
        return importlib.metadata.version("pdfplumber")
    except importlib.metadata.PackageNotFoundError:
        return "installed_but_distribution_version_unavailable"


def skipped_message(reason: str, required: str) -> str:
    return f"pdf_extraction: SKIPPED reason={reason} needed={required}"


def skipped(reason: str, required: str, label: str = "pdf_extraction") -> int:
    print(skipped_message(reason, required).replace("pdf_extraction", label, 1))
    return 0


def self_tests() -> bool:
    headers = ["year", "age_class", "value", EXCLUDED_COLUMN]
    original = [{"year": "2025", "age_class": "20-29歳", "value": "1", EXCLUDED_COLUMN: "a"}]
    changed = [{"year": "2025", "age_class": "20-29歳", "value": "2", EXCLUDED_COLUMN: "b"}]
    changed_result = compare_rows(headers, original, headers, changed)
    changed_passed = not changed_result.passed and changed_result.differences == 1
    print(f"self_test_changed_cell: {'PASS' if changed_passed else 'FAIL'} differing_cells={changed_result.differences}")
    expected_hash = hashlib.sha256(b"expected").hexdigest()
    actual_hash = hashlib.sha256(b"actual").hexdigest()
    hash_passed = not hash_matches(expected_hash, actual_hash)
    print(
        f"self_test_hash_mismatch: {'PASS' if hash_passed else 'FAIL'} "
        f"expected={expected_hash} actual={actual_hash} result=FAIL"
    )
    missing_exit = skipped(
        "PDF_absent", "source_url=https://example.invalid/source.pdf", label="self_test_missing_pdf_observed"
    )
    missing_passed = missing_exit == 0
    print(f"self_test_missing_pdf: {'PASS' if missing_passed else 'FAIL'} exit_code={missing_exit} status=SKIPPED")
    zero_passed = not all_comparisons_pass([])
    print(f"self_test_zero_file_run: {'PASS' if zero_passed else 'FAIL'} files_compared=0 status=FAIL")
    return changed_passed and hash_passed and missing_passed and zero_passed


def all_comparisons_pass(outcomes: list[bool]) -> bool:
    return bool(outcomes) and all(outcomes)


def main() -> int:
    print("limitation: SAME_PDF_SAME_OUTPUT only; this does not validate pdfplumber layout interpretation or PDF reading correctness")
    print(f"exclusion: column={EXCLUDED_COLUMN} reason=run_timestamp_not_data")
    self_tests_passed = self_tests()
    try:
        record = manifest_record()
    except (OSError, ValueError) as error:
        print(f"pdf_extraction: FAIL reason={error}")
        return 1
    if not PDF_PATH.is_file():
        return skipped("PDF_absent", f"source_url={record['source_url']}")
    version = pdfplumber_version()
    print(f"pdfplumber: measured={version or 'not_importable'} pinned={PINNED_PDFPLUMBER}")
    if version is None:
        return skipped("pdfplumber_not_importable", "interpreter=.venv/Scripts/python.exe requirements=requirements.txt")
    actual_hash = sha256(PDF_PATH)
    expected_hash = record["sha256"]
    print(f"pdf_sha256: expected={expected_hash} actual={actual_hash}")
    if not hash_matches(expected_hash, actual_hash):
        print("pdf_hash: FAIL reason=manifest_hash_mismatch")
        return 1
    outcomes: list[bool] = []
    try:
        with temporary_directory("verify_pdf_extraction_run_1_") as first_temporary, temporary_directory(
            "verify_pdf_extraction_run_2_"
        ) as second_temporary:
            run_1 = Path(first_temporary)
            run_2 = Path(second_temporary)
            print(f"working_directories: run_1={run_1} run_2={run_2}")
            first = extract(run_1)
            second = extract(run_2)
            outcomes.append(print_comparison("run_1_vs_run_2", compare_csv(first, second)))
            outcomes.append(print_comparison("run_1_vs_committed", compare_csv(first, COMMITTED_CSV)))
    except (OSError, RuntimeError, ValueError) as error:
        print(f"pdf_extraction: FAIL reason={error}")
        return 1
    return 0 if self_tests_passed and all_comparisons_pass(outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
