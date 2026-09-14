"""Regression checks for calculations in the six derived CSV artifacts."""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
FILES = {
    "aging": "aging_age_structure.csv",
    "vital": "aging_vital_change.csv",
    "employment": "foreign_employment.csv",
    "suicide": "suicide_by_age_rate.csv",
    "vital_sex": "vital_suicide_by_age_sex_rate.csv",
    "youth": "youth_suicide_rate.csv",
}
SITE_HEADERS = {
    "aging": [
        "series_id", "year", "reference_date", "observation_basis", "observation_schedule",
        "population_definition", "population_definition_source", "age_band", "population_persons",
        "population_share_percent", "age_band_source", "population_unit_source", "source_series_id",
        "source_stats_data_id", "built_at",
    ],
    "vital": [
        "series_id", "year", "reference_date", "population_definition", "population_definition_source",
        "births_persons", "births_source", "deaths_persons", "deaths_source", "natural_change_persons",
        "total_fertility_rate", "total_fertility_rate_source", "unit_source", "source_births_stats_data_id",
        "source_deaths_stats_data_id", "built_at",
    ],
    "suicide": [
        "series_id", "year", "age_band", "suicide_count", "suicide_count_source",
        "population_persons", "population_source_age_classes", "population_unit_source",
        "population_basis", "denominator_scope", "rate_per_100k", "built_at",
    ],
    "vital_sex": [
        "series_id", "year", "sex", "age_band", "suicide_count", "suicide_count_source_age_classes",
        "suicide_count_zero_filled_source_age_classes", "population_persons", "population_source_age_classes",
        "population_unit_source", "population_basis", "denominator_scope", "rate_per_100k",
        "population_definition", "built_at",
    ],
    "youth": [
        "series_id", "year", "age_band", "suicide_count", "suicide_count_source",
        "population_persons", "population_unit_source", "population_basis", "rate_per_100k", "built_at",
    ],
}


@dataclass(frozen=True)
class Result:
    passed: bool
    denominator: int
    detail: str


def load(name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (DERIVED / FILES[name]).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def number(row: dict[str, str], column: str) -> Decimal:
    return Decimal(row[column])


def rate_check(rows: list[dict[str, str]]) -> Result:
    applicable = [row for row in rows if row.get("population_persons") and row.get("rate_per_100k")]
    mismatches = sum(
        (number(row, "suicide_count") / number(row, "population_persons") * 100_000).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ) != number(row, "rate_per_100k")
        for row in applicable
    )
    return Result(mismatches == 0, len(applicable), f"rate_mismatches={mismatches}")


def c1(data: dict[str, list[dict[str, str]]]) -> Result:
    results = [rate_check(data[name]) for name in ("suicide", "youth", "vital_sex")]
    return Result(
        all(result.passed for result in results),
        sum(result.denominator for result in results),
        " ".join(
            f"{name}={result.denominator},mismatches={result.detail.rsplit('=', 1)[1]}"
            for name, result in zip(("suicide", "youth", "vital_sex"), results, strict=True)
        ),
    )


def c2(data: dict[str, list[dict[str, str]]]) -> Result:
    rows = data["vital"]
    mismatches = sum(
        number(row, "births_persons") - number(row, "deaths_persons")
        != number(row, "natural_change_persons")
        for row in rows
    )
    return Result(mismatches == 0, len(rows), f"natural_change_mismatches={mismatches}")


def c3(data: dict[str, list[dict[str, str]]]) -> Result:
    source = {row["year"]: row for row in data["suicide"] if row["age_band"] == "0-19歳"}
    target = {row["year"]: row for row in data["youth"]}
    years = sorted(set(source) | set(target), key=int)
    mismatches = sum(
        year not in source or year not in target
        or source[year]["suicide_count"] != target[year]["suicide_count"]
        or source[year]["population_persons"] != target[year]["population_persons"]
        for year in years
    )
    return Result(mismatches == 0, len(years), f"cross_csv_mismatches={mismatches}")


def record_age_unknown(data: dict[str, list[dict[str, str]]]) -> None:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in data["aging"]:
        if row["population_definition"] == "総人口":
            grouped[(row["year"], row["observation_basis"])].append(row)
    records = []
    for (year, basis), rows in sorted(grouped.items(), key=lambda item: int(item[0][0])):
        if len(rows) != 3:
            continue
        total = sum(int(row["population_persons"]) for row in rows)
        denominators = [
            Decimal(row["population_persons"]) * 100 / Decimal(row["population_share_percent"])
            for row in rows
        ]
        official = int(sum(denominators) / len(denominators)).__round__()
        records.append((year, basis, total, official, official - total))
    below = sum(
        sum(Decimal(row["population_share_percent"]) for row in rows) < 100
        for rows in grouped.values()
        if len(rows) == 3
    )
    print(f"record_age_unknown: denominator={len(records)} share_sum_below_100_percent={below}")
    for year, basis, total, official, difference in records:
        print(f"record_age_unknown_detail: year={year} basis={basis} bands_total={total} share_denominator={official} difference={difference}")


def c4(data: dict[str, list[dict[str, str]]]) -> Result:
    rows = [row for row in data["vital_sex"] if row["denominator_scope"] == "分母なし（1995年より前）"]
    bad = sum(bool(row["population_persons"] or row["rate_per_100k"]) for row in rows)
    return Result(bad == 0, len(rows), f"nonblank_denominatorless_rows={bad}")


def c5(data: dict[str, list[dict[str, str]]]) -> Result:
    applicable = ["aging", "suicide", "vital_sex", "youth"]
    failures = 0
    detail = []
    for name in applicable:
        groups: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in data[name]:
            groups[(row["series_id"], row["year"])].add(row["age_band"])
        by_series: dict[str, set[frozenset[str]]] = defaultdict(set)
        for (series_id, _), bands in groups.items():
            by_series[series_id].add(frozenset(bands))
        inconsistent = any(len(bands) != 1 for bands in by_series.values())
        failures += inconsistent
        detail.append(f"{name}_series={len(by_series)},inconsistent={int(inconsistent)}")
    return Result(failures == 0, len(applicable), " ".join(detail))


def c6(headers: dict[str, list[str]]) -> Result:
    failures = sum(headers[name] != expected for name, expected in SITE_HEADERS.items())
    return Result(failures == 0, len(SITE_HEADERS), f"header_mismatches={failures}")


def c7(data: dict[str, list[dict[str, str]]]) -> Result:
    failures = 0
    detail = []
    for name, rows in data.items():
        values = {row["built_at"] for row in rows}
        failures += int(len(values) != 1)
        detail.append(f"{name}={len(values)}")
    return Result(failures == 0, len(data), f"distinct_built_at={' '.join(detail)}")


def c8(data: dict[str, list[dict[str, str]]]) -> Result:
    rows = data["vital_sex"]
    counts = Counter(row["sex"] for row in rows)
    values = set(counts.values())
    return Result(len(counts) == 3 and len(values) == 1, sum(counts.values()), f"sex_counts={dict(sorted(counts.items()))}")


def c9(data: dict[str, list[dict[str, str]]]) -> Result:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in data["aging"]:
        groups[(row["year"], row["population_definition"])].append(row)
    mismatches = 0
    for rows in groups.values():
        people = sorted(rows, key=lambda row: int(row["population_persons"]))
        shares = sorted(rows, key=lambda row: Decimal(row["population_share_percent"]))
        mismatches += int([row["age_band"] for row in people] != [row["age_band"] for row in shares])
    return Result(mismatches == 0, len(groups), f"population_share_ordering_mismatches={mismatches}")


def record_candidates(data: dict[str, list[dict[str, str]]]) -> None:
    for name, rows in data.items():
        years = sorted({int(row["year"]) for row in rows})
        missing = sum(current - previous - 1 for previous, current in pairwise(years))
        print(f"candidate_year_continuity: file={FILES[name]} denominator={len(years)} missing_years={missing}")


def print_result(number: int, result: Result) -> bool:
    passed = result.passed and result.denominator > 0
    print(f"condition_{number}: {'PASS' if passed else 'FAIL'} denominator={result.denominator} {result.detail}")
    return passed


def main() -> int:
    headers_and_data = {name: load(name) for name in FILES}
    headers = {name: value[0] for name, value in headers_and_data.items()}
    data = {name: value[1] for name, value in headers_and_data.items()}
    checks = (c1(data), c2(data), c3(data), c4(data), c5(data), c6(headers), c7(data), c8(data), c9(data))
    outcomes = [print_result(number, result) for number, result in enumerate(checks, start=1)]
    record_age_unknown(data)
    record_candidates(data)
    return 0 if all(outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
