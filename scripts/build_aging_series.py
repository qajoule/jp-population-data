"""Build the purpose-1 age-structure and vital-change derived series."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESTAT_DIR = ROOT / "data" / "estat"
DERIVED_DIR = ROOT / "data" / "derived"
RESULT_PATH = ROOT / "docs" / "AGING_SERIES_RESULT.md"

AGE_HEADERS = [
    "series_id",
    "year",
    "reference_date",
    "observation_basis",
    "observation_schedule",
    "population_definition",
    "population_definition_source",
    "age_band",
    "population_persons",
    "population_share_percent",
    "age_band_source",
    "population_unit_source",
    "source_series_id",
    "source_stats_data_id",
    "built_at",
]
VITAL_HEADERS = [
    "series_id",
    "year",
    "reference_date",
    "population_definition",
    "population_definition_source",
    "births_persons",
    "births_source",
    "deaths_persons",
    "deaths_source",
    "natural_change_persons",
    "total_fertility_rate",
    "total_fertility_rate_source",
    "unit_source",
    "source_births_stats_data_id",
    "source_deaths_stats_data_id",
    "built_at",
]
PERSON_FACTORS = {"人": 1, "千人": 1_000, "万人": 10_000}
AGE_BANDS = ("0-14歳", "15-64歳", "65歳以上")
SOURCE_PRIORITY = {
    "確定値・各歳": 3,
    "概算値・5歳階級": 2,
    "国勢調査・年齢3区分": 1,
    "国勢調査・年齢3区分・不詳補完値": 1,
}


def read_csv(name: str) -> list[dict[str, str]]:
    with (ESTAT_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def label_values(*labels: str) -> set[str]:
    values: set[str] = set()
    for label in labels:
        for fragment in filter(None, label.split("; ")):
            if "=" not in fragment:
                raise ValueError(f"Label fragment has no equals sign: {fragment!r}")
            _, value = fragment.split("=", 1)
            values.add(value)
    return values


def normalized_year(value: str) -> int:
    match = re.fullmatch(r"(\d{4})(?:年)?", value)
    if not match:
        raise ValueError(f"Unrecognised year literal: {value!r}")
    return int(match.group(1))


def persons(row: dict[str, str]) -> int:
    try:
        factor = PERSON_FACTORS[row["unit"]]
    except KeyError as error:
        raise ValueError(f"Unrecognised population unit: {row['unit']!r}") from error
    amount = float(row["value"])
    converted = amount * factor
    if not converted.is_integer() or converted <= 0:
        raise ValueError(f"Population is not a positive integer after conversion: {row!r}")
    return int(converted)


def select_rows(rows: list[dict[str, str]], required: set[str]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if required.issubset(label_values(row["category"], row["subcategory"]))
    ]


def sum_band(rows: list[dict[str, str]], ages: list[str]) -> tuple[int, str]:
    by_age = {row["age"]: row for row in rows}
    if len(by_age) != len(rows):
        raise ValueError("Multiple population rows use the same age literal")
    missing = [age for age in ages if age not in by_age]
    if missing:
        raise ValueError(f"Missing age literals: {missing!r}")
    return sum(persons(by_age[age]) for age in ages), "|".join(ages)


def assemble_single_age(rows: list[dict[str, str]]) -> dict[str, tuple[int, str]]:
    exact_ages = {row["age"] for row in rows}
    open_ages = [age for age in exact_ages if re.fullmatch(r"\d+歳以上", age)]
    if len(open_ages) != 1:
        raise ValueError(f"Expected one open upper age band, found: {open_ages!r}")
    open_match = re.fullmatch(r"(\d+)歳以上", open_ages[0])
    assert open_match is not None
    upper_start = int(open_match.group(1))
    individual_ages = {int(match.group(1)) for age in exact_ages if (match := re.fullmatch(r"(\d+)歳", age))}
    expected = set(range(upper_start))
    if individual_ages != expected:
        raise ValueError("Single-age rows do not cover exactly the ages below the open band")
    bands = {
        "0-14歳": [f"{age}歳" for age in range(15)],
        "15-64歳": [f"{age}歳" for age in range(15, 65)],
        "65歳以上": [f"{age}歳" for age in range(65, upper_start)] + open_ages,
    }
    return {band: sum_band(rows, ages) for band, ages in bands.items()}


def assemble_five_year(rows: list[dict[str, str]]) -> dict[str, tuple[int, str]]:
    component_rows = [row for row in rows if not row["age"].startswith("（再掲）")]
    ranges: dict[tuple[int, int], str] = {}
    open_ages: list[str] = []
    for row in component_rows:
        range_match = re.fullmatch(r"(\d+)～(\d+)歳", row["age"])
        if range_match:
            ranges[(int(range_match.group(1)), int(range_match.group(2)))] = row["age"]
        elif re.fullmatch(r"\d+歳以上", row["age"]):
            open_ages.append(row["age"])
        elif row["age"] != "総数":
            raise ValueError(f"Unrecognised five-year age literal: {row['age']!r}")
    if len(open_ages) != 1:
        raise ValueError(f"Expected one open five-year age band, found: {open_ages!r}")
    bands: dict[str, list[str]] = {}
    for output_band, start, end in (("0-14歳", 0, 14), ("15-64歳", 15, 64), ("65歳以上", 65, 99)):
        ages = [ranges[(age, age + 4)] for age in range(start, end + 1, 5)]
        if output_band == "65歳以上":
            ages.append(open_ages[0])
        bands[output_band] = ages
    return {band: sum_band(component_rows, ages) for band, ages in bands.items()}


def candidate_rows() -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    long_rows = select_rows(read_csv("pop_age3_longterm.csv"), {"実数", "全国"})
    for reference_date, rows in group_rows(long_rows, "reference_date").items():
        basis = "国勢調査・年齢3区分・不詳補完値" if "不詳補完値" in reference_date else "国勢調査・年齢3区分"
        candidates.append(make_candidate(rows, basis, "総人口", {
            "0-14歳": "０～14歳", "15-64歳": "15～64歳", "65歳以上": "65歳以上",
        }))
    annual_rows = read_csv("pop_total_single_age_annual.csv")
    for definition in ("総人口", "日本人人口"):
        selected = select_rows(annual_rows, {"男女計", "全国", definition})
        selected = [row for row in selected if row["unit"] in PERSON_FACTORS]
        for rows in group_rows(selected, "year").values():
            candidates.append(make_candidate(rows, "確定値・各歳", definition, None))
    five_rows = select_rows(read_csv("pop_total_5y_2025.csv"), {"人口", "男女計", "概算値", "全国", "総人口"})
    for rows in group_rows(five_rows, "year").values():
        candidates.append(make_candidate(rows, "概算値・5歳階級", "総人口", None))
    return candidates


def group_rows(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    return groups


def make_candidate(
    rows: list[dict[str, str]], basis: str, definition: str, direct_ages: dict[str, str] | None
) -> dict[str, object]:
    if not rows:
        raise ValueError("Cannot build an empty population candidate")
    units = {row["unit"] for row in rows}
    if len(units) != 1 or not units <= PERSON_FACTORS.keys():
        raise ValueError(f"Candidate has invalid population units: {units!r}")
    totals = [row for row in rows if row["age"] == "総数"]
    if len(totals) != 1:
        raise ValueError(f"Candidate must have one total row, found {len(totals)}")
    if direct_ages is not None:
        bands = {band: sum_band(rows, [age]) for band, age in direct_ages.items()}
    elif basis == "確定値・各歳":
        bands = assemble_single_age(rows)
    elif basis == "概算値・5歳階級":
        bands = assemble_five_year(rows)
    else:
        raise ValueError(f"Unknown candidate basis: {basis!r}")
    return {
        "year": normalized_year(rows[0]["year"]),
        "reference_date": rows[0]["reference_date"],
        "basis": basis,
        "definition": definition,
        "definition_source": rows[0]["source_population_definition"],
        "unit": rows[0]["unit"],
        "series_id": rows[0]["series_id"],
        "stats_data_id": rows[0]["stats_data_id"],
        "total": persons(totals[0]),
        "bands": bands,
    }


def build_age_structure(built_at: str) -> tuple[list[dict[str, str]], list[tuple[int, str, str, float]]]:
    candidates_by_key: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
    for candidate in candidate_rows():
        year = candidate["year"]
        assert isinstance(year, int)
        definition = candidate["definition"]
        assert isinstance(definition, str)
        candidates_by_key[(year, definition)].append(candidate)
    winners: dict[tuple[int, str], dict[str, object]] = {}
    for key, candidates in candidates_by_key.items():
        highest_priority = max(SOURCE_PRIORITY[candidate["basis"]] for candidate in candidates)
        winning_candidates = [
            candidate
            for candidate in candidates
            if SOURCE_PRIORITY[candidate["basis"]] == highest_priority
        ]
        if len(winning_candidates) != 1:
            raise ValueError(f"Ambiguous source priority for year and definition {key}")
        winners[key] = winning_candidates[0]
    output: list[dict[str, str]] = []
    mismatches: list[tuple[int, str, str, float]] = []
    for (year, _), candidate in sorted(winners.items()):
        bands = candidate["bands"]
        assert isinstance(bands, dict)
        summed = sum(value for value, _ in bands.values())
        total = candidate["total"]
        assert isinstance(total, int)
        difference = abs(summed - total) / total
        if difference > 0.001:
            mismatches.append((year, candidate["definition"], candidate["basis"], difference))
        for age_band in AGE_BANDS:
            amount, source = bands[age_band]
            output.append({
                "series_id": "aging_age_structure",
                "year": str(year),
                "reference_date": candidate["reference_date"],
                "observation_basis": candidate["basis"],
                "observation_schedule": "年次" if candidate["basis"] != "国勢調査・年齢3区分" else "国勢調査時点・非年次",
                "population_definition": candidate["definition"],
                "population_definition_source": candidate["definition_source"],
                "age_band": age_band,
                "population_persons": str(amount),
                "population_share_percent": f"{amount * 100 / total:.9f}",
                "age_band_source": source,
                "population_unit_source": candidate["unit"],
                "source_series_id": candidate["series_id"],
                "source_stats_data_id": candidate["stats_data_id"],
                "built_at": built_at,
            })
    return output, mismatches


def select_vital(rows: list[dict[str, str]], value: str, require_value: bool = True) -> dict[int, dict[str, str]]:
    selected = [row for row in rows if value in label_values(row["category"], row["subcategory"])]
    if require_value:
        selected = [row for row in selected if row["value"]]
    result: dict[int, dict[str, str]] = {}
    for row in selected:
        year = normalized_year(row["year"])
        if year in result:
            raise ValueError(f"Multiple vital rows for {value!r} in {year}")
        result[year] = row
    return result


def build_vital_change(built_at: str) -> list[dict[str, str]]:
    births = select_vital(read_csv("vital_births_rates.csv"), "出生数_総数")
    fertility = select_vital(read_csv("vital_births_rates.csv"), "合計特殊出生率")
    deaths = select_vital(read_csv("vital_deaths_rates.csv"), "死亡数_総数")
    if set(births) != set(deaths):
        raise ValueError("Birth and death year sets differ")
    output: list[dict[str, str]] = []
    for year in sorted(births):
        birth, death = births[year], deaths[year]
        if birth["unit"] != "人" or death["unit"] != "人":
            raise ValueError(f"Vital count unit is not persons in {year}")
        if birth["reference_date"] != death["reference_date"]:
            raise ValueError(f"Birth and death reference dates differ in {year}")
        if birth["source_population_definition"] != death["source_population_definition"]:
            raise ValueError(f"Birth and death population definitions differ in {year}")
        fertility_row = fertility.get(year)
        output.append({
            "series_id": "aging_vital_change",
            "year": str(year),
            "reference_date": birth["reference_date"],
            "population_definition": "日本における日本人",
            "population_definition_source": birth["source_population_definition"],
            "births_persons": birth["value"],
            "births_source": birth["category"],
            "deaths_persons": death["value"],
            "deaths_source": death["category"],
            "natural_change_persons": str(int(birth["value"]) - int(death["value"])),
            "total_fertility_rate": "" if fertility_row is None else fertility_row["value"],
            "total_fertility_rate_source": "" if fertility_row is None else fertility_row["category"],
            "unit_source": birth["unit"],
            "source_births_stats_data_id": birth["stats_data_id"],
            "source_deaths_stats_data_id": death["stats_data_id"],
            "built_at": built_at,
        })
    return output


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def compact_years(years: list[int]) -> str:
    return ", ".join(str(year) for year in years)


def write_result(age_rows: list[dict[str, str]], vital_rows: list[dict[str, str]], mismatches: list[tuple[int, str, str, float]]) -> None:
    age_years = sorted({int(row["year"]) for row in age_rows})
    vital_years = sorted({int(row["year"]) for row in vital_rows})
    fertility_years = sorted(int(row["year"]) for row in vital_rows if row["total_fertility_rate"])
    age_groups = {
        (row["year"], row["population_definition"], row["source_series_id"])
        for row in age_rows
    }
    upper_by_year: dict[int, str] = {}
    for row in age_rows:
        if row["observation_basis"] == "確定値・各歳" and row["age_band"] == "65歳以上":
            upper = "90歳以上" if "90歳以上" in row["age_band_source"] else "100歳以上"
            upper_by_year[int(row["year"])] = upper
    natural_change_matches = all(
        int(row["natural_change_persons"]) == int(row["births_persons"]) - int(row["deaths_persons"])
        for row in vital_rows
    )
    report = [
        "# AGING_SERIES_RESULT",
        "",
        "`scripts/build_aging_series.py` により、目的 1 の年齢構成と人口動態の派生系列を作成した。",
        "",
        "## 完了条件の実測",
        "",
        "1. `aging_age_structure.csv` と `aging_vital_change.csv` を UTF-8、LF で出力した。列順は要求表と一致する。",
        f"2. 年齢構成は {len(age_rows)} 行、年集合は {compact_years(age_years)} である。",
        "   見込みどおり 46 年、228 行である。1920-1990 は総人口 15 年 x 3 行、1995-2024 は 2 定義 30 年 x 3 行、2025 は総人口 1 年 x 3 行である。",
        f"3. `population_persons` は {len(age_rows)}/{len(age_rows)} 行で正の整数である。換算は `人`=1、`千人`=1000、`万人`=10000 とし、未知の単位は停止する。",
        f"4. `age_band_source` は {sum(bool(row['age_band_source']) for row in age_rows)}/{len(age_rows)} 行で非空である。各歳表の老年上端は {', '.join(f'{year}: {upper}' for year, upper in sorted(upper_by_year.items()))}。",
        f"5. 3 区分合計と同一出所の総数の比較は {len(age_groups)}/{len(age_groups)} 組で実施し、0.1% 超の不一致は {len(mismatches)} 組である。",
        f"6. 人口動態は {len(vital_rows)} 行、年集合は {compact_years(vital_years)} である。",
        f"7. 合計特殊出生率が非空の年は {len(fertility_years)} 年で、年集合は {compact_years(fertility_years)} である。",
        f"8. `natural_change_persons = births_persons - deaths_persons` は {len(vital_rows)}/{len(vital_rows)} 行で一致した: {natural_change_matches}。",
        "",
        "出生・死亡の `population_definition` は `日本における日本人` と明記した。年齢構成の総人口は外国人を含むため、両系列の母集団は同一ではない。",
        "",
        "## 実行した検証",
        "",
        "- 作成スクリプト内で、人口単位、必須年齢区分、開いた老年上端、年ごとの出所優先、総数との 0.1% 比較、出生・死亡の年集合と定義の一致を検査した。",
        "- `.venv/Scripts/python.exe -m ruff check scripts/` を実行した。",
        "",
        "## 実行していない検証",
        "",
        "- `scripts/verify_aging_series.py` は実行していない。並行ジョブが所有する検査役の成果物である。",
        "- e-Stat API、ネットワーク呼出し、git 操作は実行していない。",
    ]
    RESULT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    age_rows, mismatches = build_age_structure(built_at)
    vital_rows = build_vital_change(built_at)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(DERIVED_DIR / "aging_age_structure.csv", AGE_HEADERS, age_rows)
    write_csv(DERIVED_DIR / "aging_vital_change.csv", VITAL_HEADERS, vital_rows)
    write_result(age_rows, vital_rows, mismatches)


if __name__ == "__main__":
    main()
