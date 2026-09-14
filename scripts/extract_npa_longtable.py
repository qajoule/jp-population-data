"""Extract NPA table 4-12, preserving PDF merged-cell meanings."""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pdfplumber

PDF_PATH = Path("R7jisatsunojoukyou.pdf")
OUTPUT_PATH = Path("data/npa/npa_suicide_age_annual.csv")
PAGE_INDEX = 31
SOURCE_PAGE = PAGE_INDEX + 1
SOURCE_FIGURE = "図表４－12"
SERIES_ID = "npa_suicide_age_annual"
AGE_HEADERS = ["～９歳", "10～19歳", "20～29歳", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70～79歳", "80歳～"]
TRAILING_HEADERS = ["不詳", "合計"]
YEAR_PATTERN = re.compile(r"^(昭和|平成|令和)(元|[0-9０-９]+)年$")
NUMBER_PATTERN = re.compile(r"^[0-9][0-9,]*$")
FIELDS = [
    "series_id", "source_pdf", "source_page", "source_figure", "year", "region", "sex", "age_class", "age_class_source", "value", "flag", "retrieved_at",
]
HEADER_TOP_MIN = 67.0
HEADER_TOP_MAX = 82.0
EDGE_TOLERANCE = 1.0
ROW_TOLERANCE = 1.0


@dataclass(frozen=True)
class VerticalRule:
    """One PDF vertical rule, including its observed y extent."""

    x: float
    segments: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class Cell:
    """A physical table cell and the age headers it covers."""

    left: float
    right: float
    headers: tuple[str, ...]

    @property
    def age_class_source(self) -> str:
        return "|".join(self.headers)

    @property
    def age_class(self) -> str:
        if self.headers == ("～９歳", "10～19歳"):
            return "～19歳"
        if self.headers == ("60～69歳", "70～79歳", "80歳～"):
            return "60歳～"
        if len(self.headers) != 1:
            raise ValueError(f"unsupported merged age cell: {self.headers}")
        return self.headers[0]


def era_to_year(label: str) -> int:
    """Convert a Japanese era year printed in the table to Gregorian year."""
    match = YEAR_PATTERN.fullmatch(label)
    if match is None:
        raise ValueError(f"unrecognized year label: {label}")
    era, number = match.groups()
    digits = str.maketrans("０１２３４５６７８９", "0123456789")
    year_in_era = 1 if number == "元" else int(number.translate(digits))
    return {"昭和": 1925, "平成": 1988, "令和": 2018}[era] + year_in_era


def vertical_rules(page: pdfplumber.page.Page) -> list[VerticalRule]:
    """Coalesce paired stroke edges into physical vertical table rules."""
    candidates = sorted((edge for edge in page.edges if edge.get("orientation") == "v" and 130.0 <= float(edge["x0"]) <= 505.0), key=lambda edge: float(edge["x0"]))
    groups: list[list[dict[str, object]]] = []
    for edge in candidates:
        if not groups or float(edge["x0"]) - float(groups[-1][-1]["x0"]) > EDGE_TOLERANCE:
            groups.append([edge])
        else:
            groups[-1].append(edge)
    return [
        VerticalRule(
            sum(float(edge["x0"]) for edge in group) / len(group),
            tuple((float(edge["top"]), float(edge["bottom"])) for edge in group),
        )
        for group in groups
    ]


def header_grid_rules(rules: list[VerticalRule]) -> list[VerticalRule]:
    """Select the table grid rules visible in the age-header band."""
    grid = [
        rule
        for rule in rules
        if any(top <= HEADER_TOP_MAX and bottom >= HEADER_TOP_MIN for top, bottom in rule.segments)
    ]
    if len(grid) != len(AGE_HEADERS) + len(TRAILING_HEADERS) + 1:
        raise ValueError(f"unexpected header grid-rule count: {len(grid)}")
    return grid


def rule_reaches_row(rule: VerticalRule, row_top: float) -> bool:
    """Whether a vertical boundary exists at the observed table-row top."""
    return any(
        top <= row_top + ROW_TOLERANCE and bottom >= row_top - ROW_TOLERANCE
        for top, bottom in rule.segments
    )


def cells_for_row(grid: list[VerticalRule], row_top: float) -> list[Cell]:
    """Build cells from vertical-rule continuity at this row, without year rules."""
    cells: list[Cell] = []
    start = 0
    for boundary_index in range(1, len(AGE_HEADERS)):
        if rule_reaches_row(grid[boundary_index], row_top):
            cells.append(Cell(grid[start].x, grid[boundary_index].x, tuple(AGE_HEADERS[start:boundary_index])))
            start = boundary_index
    cells.append(Cell(grid[start].x, grid[len(AGE_HEADERS)].x, tuple(AGE_HEADERS[start:])))
    for index, header in enumerate(TRAILING_HEADERS, start=len(AGE_HEADERS)):
        cells.append(Cell(grid[index].x, grid[index + 1].x, (header,)))
    return cells


def cell_for_x(cells: list[Cell], center: float) -> Cell | None:
    for cell in cells:
        if cell.left <= center < cell.right:
            return cell
    return None


def extract_rows() -> tuple[list[tuple[int, list[tuple[Cell, int]]]], list[VerticalRule]]:
    """Read values from cells defined by the page's vertical rules."""
    with pdfplumber.open(PDF_PATH) as pdf:
        page = pdf.pages[PAGE_INDEX]
        words = page.extract_words()
        rules = vertical_rules(page)
    grid = header_grid_rules(rules)
    year_words = [word for word in words if float(word["x0"]) < 140.0 and YEAR_PATTERN.fullmatch(word["text"])]
    rows: list[tuple[int, list[tuple[Cell, int]]]] = []
    for year_word in year_words:
        row_top = float(year_word["top"])
        cells = cells_for_row(grid, row_top)
        values: dict[Cell, int] = {}
        for word in words:
            if abs(float(word["top"]) - row_top) > ROW_TOLERANCE or not NUMBER_PATTERN.fullmatch(word["text"]):
                continue
            cell = cell_for_x(cells, (float(word["x0"]) + float(word["x1"])) / 2)
            if cell is None:
                continue
            if cell in values:
                raise ValueError(f"duplicate numeric cell for {year_word['text']}: {cell.age_class_source}")
            values[cell] = int(word["text"].replace(",", ""))
        missing = [cell.age_class_source for cell in cells if cell not in values]
        if missing:
            raise ValueError(f"numeric cell not read for {year_word['text']}: {missing}")
        rows.append((era_to_year(year_word["text"]), [(cell, values[cell]) for cell in cells]))
    return rows, grid


def validate(rows: list[tuple[int, list[tuple[Cell, int]]]]) -> None:
    """Require a continuous annual series and exact within-year arithmetic."""
    years = [year for year, _ in rows]
    if len(years) != len(set(years)) or not years:
        raise ValueError("duplicate or missing table rows")
    missing_years = [year for year in range(min(years), max(years) + 1) if year not in years]
    if missing_years:
        raise ValueError(f"missing years: {missing_years}")
    failures = []
    for year, cells in rows:
        values = {cell.age_class: value for cell, value in cells}
        total = values.pop("合計")
        if sum(values.values()) != total:
            failures.append((year, sum(values.values()), total))
    if failures:
        raise ValueError(f"total reconciliation failed: {failures}")


def write_csv(rows: list[tuple[int, list[tuple[Cell, int]]]]) -> Counter[str]:
    """Write only source cells that carry a parsed value."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")
    flags: Counter[str] = Counter()
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for year, cells in rows:
            for cell, value in cells:
                writer.writerow({"series_id": SERIES_ID, "source_pdf": PDF_PATH.name, "source_page": SOURCE_PAGE, "source_figure": SOURCE_FIGURE, "year": year, "region": "全国", "sex": "総数", "age_class": cell.age_class, "age_class_source": cell.age_class_source, "value": value, "flag": "", "retrieved_at": retrieved_at})
    return flags


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not PDF_PATH.is_file():
        raise FileNotFoundError(PDF_PATH)
    rows, grid = extract_rows()
    validate(rows)
    flags = write_csv(rows)
    print(f"header grid x: {[round(rule.x, 1) for rule in grid]}")
    print(f"rows: {len(rows)} years, {sum(len(cells) for _, cells in rows)} CSV rows")
    print(f"years: {min(year for year, _ in rows)}-{max(year for year, _ in rows)}")
    print(f"flags: {dict(flags)}")
    print("total reconciliation: passed for all years")


if __name__ == "__main__":
    main()
