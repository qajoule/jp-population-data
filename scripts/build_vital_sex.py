"""Build vital-statistics suicide counts and rates by age band and sex."""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VITAL_PATH = ROOT / "data" / "estat" / "vital_suicide_age_sex.csv"
POPULATION_PATH = ROOT / "data" / "estat" / "pop_total_single_age_annual.csv"
OUTPUT_PATH = ROOT / "data" / "derived" / "vital_suicide_by_age_sex_rate.csv"

RATE_YEARS = {
    1995,
    2000,
    2005,
    2010,
    *range(2013, 2025),
}
SEXES = ("男", "女", "総数")
POPULATION_SEX = {"男": "男", "女": "女", "総数": "男女計"}
BANDS = {
    "合計": ("総数",),
    "0-19歳": ("0～4歳", "5～9歳", "10～14歳", "15～19歳"),
    "20-29歳": ("20～24歳", "25～29歳"),
    "30-39歳": ("30～34歳", "35～39歳"),
    "40-49歳": ("40～44歳", "45～49歳"),
    "50-59歳": ("50～54歳", "55～59歳"),
    "60歳以上": (
        "60～64歳",
        "65～69歳",
        "70～74歳",
        "75～79歳",
        "80～84歳",
        "85～89歳",
        "90～94歳",
        "95～99歳",
        "100歳以上",
    ),
    "不詳": ("不詳",),
}
FIELDNAMES = [
    "series_id",
    "year",
    "sex",
    "age_band",
    "suicide_count",
    "suicide_count_source_age_classes",
    "suicide_count_zero_filled_source_age_classes",
    "population_persons",
    "population_source_age_classes",
    "population_unit_source",
    "population_basis",
    "denominator_scope",
    "rate_per_100k",
    "population_definition",
    "built_at",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV with a required header."""
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"Input has no header: {path}")
        return list(reader)


def dimension_values(label: str) -> set[str]:
    """Return e-Stat dimension values without matching dimension names."""
    values = set()
    for fragment in label.split("; "):
        _, separator, value = fragment.partition("=")
        if not separator:
            raise ValueError(f"Malformed dimension fragment: {fragment!r}")
        values.add(value)
    return values


def exact_age(label: str) -> int | None:
    """Return an age only for a single-age population label."""
    value = label.removesuffix("歳")
    return int(value) if value.isdigit() else None


def open_ended_age(label: str) -> int | None:
    """Return an age lower bound only for an open-ended population label."""
    value = label.removesuffix("歳以上")
    return int(value) if value.isdigit() and label.endswith("歳以上") else None


def count_value(row: dict[str, str]) -> tuple[int, bool]:
    """Return a count and whether a dash-flagged blank was filled with zero."""
    if row["value"]:
        return int(row["value"]), False
    if row["flag"] == "-":
        return 0, True
    raise ValueError(f"Vital count is blank without a dash flag: {row!r}")


def vital_counts(
    rows: list[dict[str, str]],
) -> tuple[list[int], dict[tuple[int, str, str], int], dict[tuple[int, str, str], tuple[str, ...]]]:
    """Aggregate the required age bands from all vital-statistics records."""
    indexed: dict[tuple[int, str, str], tuple[int, bool]] = {}
    for row in rows:
        key = (int(row["year"]), row["sex"], row["age"])
        if key in indexed:
            raise ValueError(f"Duplicate vital record: {row!r}")
        indexed[key] = count_value(row)

    years = sorted({year for year, _, _ in indexed})
    counts: dict[tuple[int, str, str], int] = {}
    zero_filled_ages: dict[tuple[int, str, str], tuple[str, ...]] = {}
    for year in years:
        for sex in SEXES:
            available = {age for item_year, item_sex, age in indexed if (item_year, item_sex) == (year, sex)}
            for band, source_ages in BANDS.items():
                missing = set(source_ages) - available
                if missing:
                    raise ValueError(f"Missing vital ages for {year} {sex} {band}: {sorted(missing)}")
                counts[(year, sex, band)] = sum(indexed[(year, sex, age)][0] for age in source_ages)
                zero_filled_ages[(year, sex, band)] = tuple(
                    age for age in source_ages if indexed[(year, sex, age)][1]
                )
    return years, counts, zero_filled_ages


def population_rows(rows: list[dict[str, str]]) -> dict[tuple[int, str, str], tuple[int, str]]:
    """Aggregate 1995-2024 total-population denominators by age band and sex."""
    selected: dict[tuple[int, str], dict[str, dict[str, str]]] = {}
    for row in rows:
        values = dimension_values(row["category"]) | dimension_values(row["subcategory"])
        sex = next((name for name, label in POPULATION_SEX.items() if label in values), None)
        if sex is None or "総人口" not in values:
            continue
        key = (int(row["year"]), sex)
        age_rows = selected.setdefault(key, {})
        if row["age"] in age_rows:
            raise ValueError(f"Duplicate population record: {row!r}")
        age_rows[row["age"]] = row

    result: dict[tuple[int, str, str], tuple[int, str]] = {}
    for year in RATE_YEARS:
        for sex in SEXES:
            try:
                by_age = selected[(year, sex)]
            except KeyError as error:
                raise ValueError(f"Missing population sex for {year} {sex}") from error
            if {row["unit"] for row in by_age.values()} != {"千人"}:
                raise ValueError(f"Unexpected population unit for {year} {sex}")
            singles = {exact_age(age): row for age, row in by_age.items() if exact_age(age) is not None}
            if len(singles) != len([age for age in by_age if exact_age(age) is not None]):
                raise ValueError(f"Duplicate single-age population for {year} {sex}")
            top = max(singles)
            end_age = f"{top + 1}歳以上"
            if end_age not in by_age:
                raise ValueError(f"Missing open-ended population for {year} {sex}: {end_age}")
            source_ages = {
                "合計": ("総数",),
                "0-19歳": tuple(f"{age}歳" for age in range(20)),
                "20-29歳": tuple(f"{age}歳" for age in range(20, 30)),
                "30-39歳": tuple(f"{age}歳" for age in range(30, 40)),
                "40-49歳": tuple(f"{age}歳" for age in range(40, 50)),
                "50-59歳": tuple(f"{age}歳" for age in range(50, 60)),
                "60歳以上": tuple(f"{age}歳" for age in range(60, top + 1)) + (end_age,),
                "不詳": ("総数",),
            }
            for band, ages in source_ages.items():
                missing = set(ages) - set(by_age)
                if missing:
                    raise ValueError(f"Missing population ages for {year} {sex} {band}: {sorted(missing)}")
                result[(year, sex, band)] = (
                    sum(int(by_age[age]["value"]) * 1_000 for age in ages),
                    "+".join(ages),
                )
    return result


def main() -> None:
    years, counts, zero_filled_ages = vital_counts(read_csv(VITAL_PATH))
    if len(years) != 25:
        raise ValueError(f"Expected 25 vital years, found {len(years)}")
    if set(years) != RATE_YEARS | {1950, 1955, 1960, 1965, 1970, 1975, 1980, 1985, 1990}:
        raise ValueError(f"Unexpected vital years: {years}")
    populations = population_rows(read_csv(POPULATION_PATH))
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    output_rows: list[dict[str, str]] = []
    for year in years:
        for sex in SEXES:
            for band, source_ages in BANDS.items():
                population = populations.get((year, sex, band))
                if population is None:
                    population_value = ""
                    population_source = ""
                    unit = ""
                    basis = ""
                    denominator_scope = "分母なし（1995年より前）"
                    rate = ""
                else:
                    population_value, population_source = population
                    unit = "千人"
                    basis = "確定値・各歳"
                    denominator_scope = "総人口（年齢不詳のため）" if band == "不詳" else band
                    rate_value = (Decimal(counts[(year, sex, band)]) / Decimal(population_value) * 100_000).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    rate = f"{rate_value:.2f}"
                output_rows.append(
                    {
                        "series_id": "vital_suicide_by_age_sex_rate",
                        "year": str(year),
                        "sex": sex,
                        "age_band": band,
                        "suicide_count": str(counts[(year, sex, band)]),
                        "suicide_count_source_age_classes": "+".join(source_ages),
                        "suicide_count_zero_filled_source_age_classes": "+".join(
                            zero_filled_ages[(year, sex, band)]
                        ),
                        "population_persons": str(population_value),
                        "population_source_age_classes": population_source,
                        "population_unit_source": unit,
                        "population_basis": basis,
                        "denominator_scope": denominator_scope,
                        "rate_per_100k": rate,
                        "population_definition": "人口動態統計（日本における日本人）",
                        "built_at": built_at,
                    }
                )
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
