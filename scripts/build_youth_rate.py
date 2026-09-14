"""Build the annual 0-19 youth suicide rate series from repository inputs."""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUICIDE_PATH = ROOT / "data" / "npa" / "npa_suicide_age_annual.csv"
SINGLE_AGE_PATH = ROOT / "data" / "estat" / "pop_total_single_age_annual.csv"
FIVE_YEAR_PATH = ROOT / "data" / "estat" / "pop_total_5y_2025.csv"
OUTPUT_PATH = ROOT / "data" / "derived" / "youth_suicide_rate.csv"

FIELDNAMES = [
    "series_id",
    "year",
    "age_band",
    "suicide_count",
    "suicide_count_source",
    "population_persons",
    "population_unit_source",
    "population_basis",
    "rate_per_100k",
    "built_at",
]
UNIT_MULTIPLIERS = {"千人": Decimal(1000), "万人": Decimal(10000)}


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV, rejecting missing input files and headers."""
    if not path.is_file():
        raise ValueError(f"Input file is missing: {path}")
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"Input CSV has no header: {path}")
        return list(reader)


def dimension_values(label: str) -> dict[str, str]:
    """Split an e-Stat composite label and retain only dimension values."""
    values: dict[str, str] = {}
    for fragment in label.split("; "):
        if "=" not in fragment:
            raise ValueError(f"Malformed dimension fragment: {fragment!r}")
        key, value = fragment.split("=", 1)
        values[key] = value
    return values


def is_total_population_combined(row: dict[str, str]) -> bool:
    """Match total population and combined sex through dimension values only."""
    category = dimension_values(row["category"])
    subcategory = dimension_values(row["subcategory"])
    values = set(category.values()) | set(subcategory.values())
    return "総人口" in values and "男女計" in values


def persons_from_row(row: dict[str, str]) -> int:
    """Convert one population row to an integral count of persons."""
    unit = row["unit"]
    if unit not in UNIT_MULTIPLIERS:
        raise ValueError(f"Unsupported population unit: {unit!r}")
    persons = Decimal(row["value"]) * UNIT_MULTIPLIERS[unit]
    if persons != persons.to_integral_value():
        raise ValueError(f"Population is not integral after conversion: {row!r}")
    return int(persons)


def single_age_number(label: str) -> int | None:
    """Return the integer for labels representing exactly one age."""
    value = label.removesuffix("歳")
    return int(value) if value.isdigit() else None


def suicide_counts(rows: list[dict[str, str]]) -> dict[int, tuple[int, str]]:
    """Build 0-19 counts from age_class labels, including merged-cell labels."""
    result: dict[int, tuple[int, str]] = {}
    by_year: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        if row["region"] == "全国" and row["sex"] == "総数":
            by_year.setdefault(int(row["year"]), []).append(row)

    for year in range(1995, 2026):
        age_rows = {row["age_class"]: row for row in by_year.get(year, [])}
        if "～19歳" in age_rows:
            result[year] = (int(age_rows["～19歳"]["value"]), "～19歳")
            continue
        required = ("～９歳", "10～19歳")
        if all(age_class in age_rows for age_class in required):
            count = sum(int(age_rows[age_class]["value"]) for age_class in required)
            result[year] = (count, "～９歳+10～19歳")
            continue
        present = ", ".join(sorted(age_rows))
        raise ValueError(f"No 0-19 suicide source for {year}; age_class values: {present}")
    return result


def single_age_populations(rows: list[dict[str, str]]) -> dict[int, tuple[int, str, str]]:
    """Sum ages 0 through 19 for each annual single-age population record."""
    selected = [row for row in rows if is_total_population_combined(row)]
    result: dict[int, tuple[int, str, str]] = {}
    for year in range(1995, 2025):
        age_rows = [
            row
            for row in selected
            if int(row["year"]) == year and single_age_number(row["age"]) is not None
        ]
        by_age = {single_age_number(row["age"]): row for row in age_rows}
        required = set(range(20))
        if set(by_age) & required != required:
            missing = sorted(required - set(by_age))
            raise ValueError(f"Missing ages for {year}: {missing}")
        if len(age_rows) != len(by_age):
            raise ValueError(f"Duplicate single-age population rows for {year}")
        units = {by_age[age]["unit"] for age in required}
        if len(units) != 1:
            raise ValueError(f"Multiple units in single-age population for {year}: {units}")
        unit = units.pop()
        population = sum(persons_from_row(by_age[age]) for age in required)
        result[year] = (population, unit, "確定値・各歳")
    return result


def five_year_population(rows: list[dict[str, str]]) -> tuple[int, str, str]:
    """Sum the four 0-19 five-year age bands from the 2025 estimate."""
    selected = [row for row in rows if is_total_population_combined(row)]
    required = ("0～4歳", "5～9歳", "10～14歳", "15～19歳")
    target_rows = [
        row for row in selected if row["year"] == "2025" and row["age"] in required
    ]
    by_age = {row["age"]: row for row in target_rows}
    if not all(age in by_age for age in required):
        missing = [age for age in required if age not in by_age]
        raise ValueError(f"Missing 2025 five-year age bands: {missing}")
    if len(target_rows) != len(by_age):
        raise ValueError("Duplicate 2025 five-year population rows")
    units = {by_age[age]["unit"] for age in required}
    if len(units) != 1:
        raise ValueError(f"Multiple units in 2025 five-year population: {units}")
    unit = units.pop()
    population = sum(persons_from_row(by_age[age]) for age in required)
    return population, unit, "概算値・5歳階級"


def main() -> None:
    suicide = suicide_counts(read_csv(SUICIDE_PATH))
    populations = single_age_populations(read_csv(SINGLE_AGE_PATH))
    populations[2025] = five_year_population(read_csv(FIVE_YEAR_PATH))
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    output_rows: list[dict[str, str]] = []
    for year in range(1995, 2026):
        count, count_source = suicide[year]
        population, unit, basis = populations[year]
        rate = (Decimal(count) / Decimal(population) * Decimal(100000)).quantize(
            Decimal("0.01")
        )
        output_rows.append(
            {
                "series_id": "youth_suicide_rate_0_19",
                "year": str(year),
                "age_band": "0-19歳",
                "suicide_count": str(count),
                "suicide_count_source": count_source,
                "population_persons": str(population),
                "population_unit_source": unit,
                "population_basis": basis,
                "rate_per_100k": f"{rate:.2f}",
                "built_at": built_at,
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
