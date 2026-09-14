"""Build annual suicide counts, populations, and rates for required age bands."""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NPA_PATH = ROOT / "data" / "npa" / "npa_suicide_age_annual.csv"
SINGLE_AGE_PATH = ROOT / "data" / "estat" / "pop_total_single_age_annual.csv"
FIVE_YEAR_PATH = ROOT / "data" / "estat" / "pop_total_5y_2025.csv"
OUTPUT_PATH = ROOT / "data" / "derived" / "suicide_by_age_rate.csv"

FIELDNAMES = [
    "series_id",
    "year",
    "age_band",
    "suicide_count",
    "suicide_count_source",
    "population_persons",
    "population_source_age_classes",
    "population_unit_source",
    "population_basis",
    "denominator_scope",
    "rate_per_100k",
    "built_at",
]
UNIT_MULTIPLIERS = {"人": 1, "千人": 1_000, "万人": 10_000}
BANDS = (
    ("合計", ("合計",)),
    ("0-19歳", ("～19歳",), ("～９歳", "10～19歳")),
    ("20-29歳", ("20～29歳",)),
    ("30-39歳", ("30～39歳",)),
    ("40-49歳", ("40～49歳",)),
    ("50-59歳", ("50～59歳",)),
    ("60歳以上", ("60歳～",), ("60～69歳", "70～79歳", "80歳～")),
    ("不詳", ("不詳",)),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV and reject missing files or headers."""
    if not path.is_file():
        raise ValueError(f"Input file is missing: {path}")
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"Input CSV has no header: {path}")
        return list(reader)


def dimension_values(label: str) -> set[str]:
    """Return values, rather than dimension names, from an e-Stat label."""
    values = set()
    for fragment in label.split("; "):
        _, separator, value = fragment.partition("=")
        if not separator:
            raise ValueError(f"Malformed dimension fragment: {fragment!r}")
        values.add(value)
    return values


def is_total_population_combined(row: dict[str, str]) -> bool:
    """Match total population and combined sex through dimension values only."""
    values = dimension_values(row["category"]) | dimension_values(row["subcategory"])
    return "総人口" in values and "男女計" in values


def population_basis(row: dict[str, str]) -> str:
    """Derive the population basis from the input definition."""
    definition = row["source_population_definition"]
    if "確定値" in definition and "各歳" in definition:
        return "確定値・各歳"
    if "概算値" in definition and "5歳階級" in definition:
        return "概算値・5歳階級"
    raise ValueError(f"Unsupported population definition: {definition!r}")


def persons(row: dict[str, str]) -> int:
    """Convert a population input value to persons."""
    try:
        multiplier = UNIT_MULTIPLIERS[row["unit"]]
    except KeyError as error:
        raise ValueError(f"Unsupported population unit: {row['unit']!r}") from error
    value = Decimal(row["value"]) * multiplier
    if value != value.to_integral_value():
        raise ValueError(f"Population is not integral after conversion: {row!r}")
    return int(value)


def exact_age(label: str) -> int | None:
    """Return an age only when the label denotes exactly one age."""
    value = label.removesuffix("歳")
    return int(value) if value.isdigit() else None


def open_ended_age(label: str) -> int | None:
    """Return the lower bound of an open-ended age label."""
    suffix = "歳以上"
    if not label.endswith(suffix):
        return None
    value = label.removesuffix(suffix)
    return int(value) if value.isdigit() else None


def age_band_lower_bound(label: str) -> int | None:
    """Return the lower bound for a closed or open-ended age-band label."""
    lower_bound = label.split("～", 1)[0]
    value = lower_bound.removesuffix("歳以上").removesuffix("歳")
    return int(value) if value.isdigit() else None


def suicide_counts(rows: list[dict[str, str]]) -> dict[tuple[int, str], tuple[int, str]]:
    """Aggregate each required NPA band, preserving its input labels."""
    by_year: dict[int, dict[str, dict[str, str]]] = {}
    for row in rows:
        if row["region"] == "全国" and row["sex"] == "総数":
            year_rows = by_year.setdefault(int(row["year"]), {})
            if row["age_class"] in year_rows:
                raise ValueError(f"Duplicate NPA age class: {row!r}")
            year_rows[row["age_class"]] = row

    result: dict[tuple[int, str], tuple[int, str]] = {}
    for year in range(1995, 2026):
        classes = by_year.get(year, {})
        for definition in BANDS:
            band, *alternatives = definition
            source = next(
                (candidate for candidate in alternatives if all(item in classes for item in candidate)),
                None,
            )
            if source is None:
                raise ValueError(f"Missing NPA source for {year} {band}: {sorted(classes)}")
            result[(year, band)] = (
                sum(int(classes[item]["value"]) for item in source),
                "+".join(source),
            )
    return result


def annual_populations(rows: list[dict[str, str]]) -> dict[tuple[int, str], tuple[int, str, str, str]]:
    """Build 1995-2024 populations by summing exact-age records."""
    selected = [row for row in rows if is_total_population_combined(row)]
    result: dict[tuple[int, str], tuple[int, str, str, str]] = {}
    for year in range(1995, 2025):
        age_rows = [row for row in selected if int(row["year"]) == year]
        by_age = {exact_age(row["age"]): row for row in age_rows if exact_age(row["age"]) is not None}
        if len(by_age) != len([row for row in age_rows if exact_age(row["age"]) is not None]):
            raise ValueError(f"Duplicate exact-age population rows for {year}")
        metadata = {(row["unit"], population_basis(row)) for row in by_age.values()}
        if len(metadata) != 1:
            raise ValueError(f"Population unit or basis is not unique for {year}")
        unit, basis = metadata.pop()
        total_rows = [row for row in age_rows if row["age"] == "総数"]
        if len(total_rows) != 1:
            raise ValueError(f"Total population is not unique for {year}: {len(total_rows)}")
        ranges = {
            "0-19歳": range(20),
            "20-29歳": range(20, 30),
            "30-39歳": range(30, 40),
            "40-49歳": range(40, 50),
            "50-59歳": range(50, 60),
            "60歳以上": range(60, max(by_age) + 1),
        }
        open_ended_rows = {
            open_ended_age(row["age"]): row
            for row in age_rows
            if open_ended_age(row["age"]) is not None
        }
        if len(open_ended_rows) != len(
            [row for row in age_rows if open_ended_age(row["age"]) is not None]
        ):
            raise ValueError(f"Duplicate open-ended population rows for {year}")
        for band, ages in ranges.items():
            if not all(age in by_age for age in ages):
                raise ValueError(f"Missing population ages for {year} {band}")
            source_rows = [by_age[age] for age in ages]
            if band == "60歳以上":
                top_age = max(by_age) + 1
                try:
                    source_rows.append(open_ended_rows[top_age])
                except KeyError as error:
                    raise ValueError(
                        f"Missing open-ended population age {top_age}歳以上 for {year}"
                    ) from error
            result[(year, band)] = (
                sum(persons(row) for row in source_rows),
                "+".join(row["age"] for row in source_rows),
                unit,
                basis,
            )
        total = persons(total_rows[0])
        for band in ("合計", "不詳"):
            result[(year, band)] = (total, "総数", unit, basis)
    return result


def five_year_populations(rows: list[dict[str, str]]) -> dict[tuple[int, str], tuple[int, str, str, str]]:
    """Build 2025 populations from its five-year age-band estimate."""
    selected = [row for row in rows if is_total_population_combined(row) and row["year"] == "2025"]
    by_age = {row["age"]: row for row in selected}
    if len(by_age) != len(selected):
        raise ValueError("Duplicate 2025 five-year population rows")
    metadata = {(row["unit"], population_basis(row)) for row in selected}
    if len(metadata) != 1:
        raise ValueError("2025 population unit or basis is not unique")
    unit, basis = metadata.pop()
    ranges = {
        "0-19歳": ("0～4歳", "5～9歳", "10～14歳", "15～19歳"),
        "20-29歳": ("20～24歳", "25～29歳"),
        "30-39歳": ("30～34歳", "35～39歳"),
        "40-49歳": ("40～44歳", "45～49歳"),
        "50-59歳": ("50～54歳", "55～59歳"),
    }
    result: dict[tuple[int, str], tuple[int, str, str, str]] = {}
    for band, ages in ranges.items():
        if not all(age in by_age for age in ages):
            raise ValueError(f"Missing 2025 population ages for {band}")
        result[(2025, band)] = (sum(persons(by_age[age]) for age in ages), "+".join(ages), unit, basis)
    senior_ages = tuple(
        age for age in by_age if (lower_bound := age_band_lower_bound(age)) is not None and lower_bound >= 60
    )
    if not senior_ages:
        raise ValueError("Missing 2025 population ages for 60歳以上")
    result[(2025, "60歳以上")] = (sum(persons(by_age[age]) for age in senior_ages), "+".join(senior_ages), unit, basis)
    total_rows = [row for row in selected if row["age"] == "総数"]
    if len(total_rows) != 1:
        raise ValueError(f"2025 total population is not unique: {len(total_rows)}")
    total = persons(total_rows[0])
    for band in ("合計", "不詳"):
        result[(2025, band)] = (total, "総数", unit, basis)
    return result


def main() -> None:
    counts = suicide_counts(read_csv(NPA_PATH))
    populations = annual_populations(read_csv(SINGLE_AGE_PATH))
    populations.update(five_year_populations(read_csv(FIVE_YEAR_PATH)))
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    output_rows: list[dict[str, str]] = []
    for year in range(1995, 2026):
        for definition in BANDS:
            band = definition[0]
            count, count_source = counts[(year, band)]
            population, population_source, unit, basis = populations[(year, band)]
            denominator_scope = "総人口（年齢不詳のため）" if band == "不詳" else band
            rate = (Decimal(count) / Decimal(population) * 100_000).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            output_rows.append(
                {
                    "series_id": "npa_suicide_by_age_rate",
                    "year": str(year),
                    "age_band": band,
                    "suicide_count": str(count),
                    "suicide_count_source": count_source,
                    "population_persons": str(population),
                    "population_source_age_classes": population_source,
                    "population_unit_source": unit,
                    "population_basis": basis,
                    "denominator_scope": denominator_scope,
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
