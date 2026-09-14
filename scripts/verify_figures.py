"""Acceptance check for the fifteen static figures in FIGURES_BRIEF.md."""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import os
import re
import shutil
import tempfile
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGURES = {
    "age-structure-persons": ("人口（人）", ["0-14歳", "15-64歳", "65歳以上"]),
    "age-structure-share": ("構成比（%）", ["0-14歳", "15-64歳", "65歳以上"]),
    "vital-counts": ("人数（人）", ["出生", "死亡", "自然増減"]),
    "total-fertility-rate": ("合計特殊出生率", ["単一"]),
    "suicide-count-by-age": ("自殺者数（人）", ["合計", "0-19歳", "20-29歳", "30-39歳", "40-49歳", "50-59歳", "60歳以上"]),
    "suicide-rate-by-age": ("自殺死亡率（人口 10 万対）", ["合計", "0-19歳", "20-29歳", "30-39歳", "40-49歳", "50-59歳", "60歳以上"]),
    "youth-suicide-count": ("自殺者数（人）", ["0-19歳"]),
    "youth-population": ("人口（人）", ["0-19歳"]),
    "youth-suicide-rate": ("自殺死亡率（人口 10 万対）", ["0-19歳"]),
    "vital-suicide-rate-0-19": ("自殺死亡率（人口 10 万対）", ["男", "女"]),
    "vital-suicide-rate-20-29": ("自殺死亡率（人口 10 万対）", ["男", "女"]),
    "vital-suicide-rate-30-39": ("自殺死亡率（人口 10 万対）", ["男", "女"]),
    "vital-suicide-rate-40-49": ("自殺死亡率（人口 10 万対）", ["男", "女"]),
    "vital-suicide-rate-50-59": ("自殺死亡率（人口 10 万対）", ["男", "女"]),
    "vital-suicide-rate-60-plus": ("自殺死亡率（人口 10 万対）", ["男", "女"]),
}
AGE_BANDS = {"0-14歳", "15-64歳", "65歳以上"}
SUICIDE_BANDS = {"合計", "0-19歳", "20-29歳", "30-39歳", "40-49歳", "50-59歳", "60歳以上"}
VITAL_BANDS = {"0-19歳", "20-29歳", "30-39歳", "40-49歳", "50-59歳", "60歳以上"}
METRIC_COLUMNS = {
    "population_persons": "population_persons", "population_share_percent": "population_share_percent",
    "birth_count": "births_persons", "death_count": "deaths_persons",
    "natural_change": "natural_change_persons", "total_fertility_rate": "total_fertility_rate",
    "suicide_count": "suicide_count", "rate_per_100k": "rate_per_100k",
}
METRIC_ATTRS = {metric: f"data-csv-{metric.replace('_', '-')}" for metric in METRIC_COLUMNS}
NUMERIC_ATTRS = set(METRIC_ATTRS.values())


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    attr_counts: dict[str, int] = field(default_factory=dict)
    parent: Node | None = None
    children: list[Node] = field(default_factory=list)
    data: list[str] = field(default_factory=list)

    def descendants(self) -> list[Node]:
        found: list[Node] = []
        for child in self.children:
            found.append(child)
            found.extend(child.descendants())
        return found

    def text(self) -> str:
        return "".join(self.data) + "".join(child.text() for child in self.children)


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        counts: dict[str, int] = defaultdict(int)
        for key, _ in attrs:
            counts[key] += 1
        node = Node(tag, {key: value or "" for key, value in attrs}, dict(counts), self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in {"circle", "line", "path", "rect", "meta", "link", "input", "br"}:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in {"circle", "line", "path", "rect", "meta", "link", "input", "br"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        self.stack[-1].data.append(data)


@dataclass(frozen=True)
class Config:
    dist: Path
    csvs: dict[str, Path]


@dataclass(frozen=True)
class ConditionResult:
    passed: bool
    denominator: int
    detail: str


def config() -> Config:
    def path(name: str, default: Path) -> Path:
        return Path(os.environ.get(name, default))
    return Config(path("FIGURES_DIST", ROOT / "site" / "dist"), {
        "aging": path("FIGURES_AGING", ROOT / "data/derived/aging_age_structure.csv"),
        "vital": path("FIGURES_VITAL", ROOT / "data/derived/aging_vital_change.csv"),
        "suicide": path("FIGURES_SUICIDE", ROOT / "data/derived/suicide_by_age_rate.csv"),
        "youth": path("FIGURES_YOUTH", ROOT / "data/derived/youth_suicide_rate.csv"),
        "sex": path("FIGURES_SEX", ROOT / "data/derived/vital_suicide_by_age_sex_rate.csv"),
    })


def decimal(value: str | None) -> Decimal:
    if value is None or value == "":
        raise ValueError("missing decimal")
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"invalid decimal: {value}") from error


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def pages(dist: Path) -> list[Node]:
    roots: list[Node] = []
    for path in sorted(dist.rglob("*.html")):
        parser = Parser()
        parser.feed(path.read_text(encoding="utf-8"))
        roots.append(parser.root)
    return roots


def figures(nodes: list[Node]) -> list[Node]:
    return [
        node for root in nodes for node in [root, *root.descendants()]
        if node.tag == "svg" and "data-figure-id" in node.attrs
    ]


def all_nodes(nodes: list[Node]) -> list[Node]:
    return [node for root in nodes for node in [root, *root.descendants()]]


def has_svg_ancestor(node: Node) -> bool:
    current = node.parent
    while current is not None:
        if current.tag == "svg":
            return True
        current = current.parent
    return False


def points(figure: Node) -> list[Node]:
    return [node for node in figure.descendants() if node.tag == "circle"]


def report(number: int, passed: bool, denominator: int, detail: str) -> ConditionResult:
    del number
    return ConditionResult(passed, denominator, detail)


def print_condition_result(
    number: int,
    result: ConditionResult | None = None,
    error: Exception | None = None,
) -> bool:
    if error is not None:
        print(
            f"condition_{number}: FAIL denominator=0 is not judgeable "
            f"{type(error).__name__}: {error}"
        )
        return False
    if result is None:
        raise ValueError("condition result is required when no exception was raised")
    passed = result.passed and result.denominator > 0
    detail = result.detail
    if result.denominator == 0:
        detail = f"is not judgeable {detail}".strip()
    print(
        f"condition_{number}: {'PASS' if passed else 'FAIL'} "
        f"denominator={result.denominator} {detail}"
    )
    return passed


def execute_condition(number: int, check: Callable[[], ConditionResult]) -> bool:
    try:
        return print_condition_result(number, result=check())
    except Exception as error:  # noqa: BLE001
        return print_condition_result(number, error=error)


def figure_map(figs: list[Node]) -> dict[str, Node]:
    return {figure.attrs["data-figure-id"]: figure for figure in figs}


def metric_for(figure_id: str) -> str:
    return {
        "age-structure-persons": "population_persons", "age-structure-share": "population_share_percent",
        "vital-counts": "", "total-fertility-rate": "total_fertility_rate",
        "suicide-count-by-age": "suicide_count", "suicide-rate-by-age": "rate_per_100k",
        "youth-suicide-count": "suicide_count", "youth-population": "population_persons",
        "youth-suicide-rate": "rate_per_100k",
        "vital-suicide-rate-0-19": "rate_per_100k", "vital-suicide-rate-20-29": "rate_per_100k",
        "vital-suicide-rate-30-39": "rate_per_100k", "vital-suicide-rate-40-49": "rate_per_100k",
        "vital-suicide-rate-50-59": "rate_per_100k", "vital-suicide-rate-60-plus": "rate_per_100k",
    }[figure_id]


def c1(figs: list[Node], nodes: list[Node]) -> ConditionResult:
    by_id = defaultdict(list)
    for figure in figs:
        by_id[figure.attrs["data-figure-id"]].append(figure)
    failures = 0
    details: list[str] = []
    for figure_id, (label, _) in FIGURES.items():
        current = by_id.get(figure_id, [])
        if len(current) != 1:
            failures += 2
            details.append(
                f"figure_id={figure_id} violated=svg_identity count={len(current)}"
            )
            continue
        for axis, expected in (("x", "年"), ("y", label)):
            axes = [node for node in current[0].descendants() if node.attrs.get("data-axis") == axis]
            valid = [
                node for node in axes
                if any(child.attrs.get("data-tick-value") is not None for child in node.descendants())
                and any(
                    child.tag == "text"
                    and child.attrs.get("data-axis-label") == expected
                    and child.text().strip() == expected
                    for child in node.descendants()
                )
            ]
            if not valid:
                failures += 1
                details.append(
                    f"figure_id={figure_id} value={axis} violated=axis_contract"
                )
    for figure_id, value in by_id.items():
        if figure_id not in FIGURES:
            failures += len(value)
            details.append(
                f"figure_id={figure_id} violated=unexpected_svg_identity count={len(value)}"
            )
    for node in nodes:
        if "data-axis-label" in node.attrs and node.tag != "text":
            failures += 1
            details.append(
                f"value={node.attrs['data-axis-label']} "
                f"violated=axis_label_not_text tag={node.tag}"
            )
        if node.tag != "svg" and "data-figure-id" in node.attrs:
            failures += 1
            details.append(
                "value=" + node.attrs["data-figure-id"]
                + f" violated=non_svg_figure_identity tag={node.tag}"
            )
        if "data-figure-id" in node.attrs and "data-figure-ref" in node.attrs:
            failures += 1
            details.append(
                "value=" + node.attrs["data-figure-id"]
                + f" violated=identity_and_reference tag={node.tag}"
            )
    return report(1, failures == 0, 30, "\n".join([f"invalid_axes={failures}", *details]))


def colour_literals(node: Node) -> set[str]:
    values: set[str] = set()
    current: Node | None = node
    while current is not None:
        for attribute in ("stroke", "fill", "color", "data-series-color"):
            if current.attrs.get(attribute):
                values.add(current.attrs[attribute])
        current = current.parent
    return values


def c2(figs: list[Node], nodes: list[Node]) -> ConditionResult:
    by_id = figure_map(figs)
    failures = 0
    details: list[str] = []
    for figure_id, (_, series) in FIGURES.items():
        figure = by_id.get(figure_id)
        if figure is None:
            failures += len(series)
            continue
        for name in series:
            metric = metric_for(figure_id)
            selected = [point for point in points(figure) if ((point.attrs.get("data-csv-age-band") == name and point.attrs.get("data-csv-metric") == metric) or (point.attrs.get("data-csv-sex") == name and point.attrs.get("data-csv-metric") == metric) or (figure_id == "vital-counts" and {"出生": "birth_count", "死亡": "death_count", "自然増減": "natural_change"}[name] == point.attrs.get("data-csv-metric")) or (name == "単一" and point.attrs.get("data-csv-metric") == "total_fertility_rate"))]
            if not selected:
                failures += 1
                details.append(f"figure_id={figure_id} value={name!r} violated=missing_series")
                continue
            if len(series) <= 1:
                continue
            expected = series_key(figure, selected[0])
            legends = [
                node for node in nodes
                if not has_svg_ancestor(node)
                and node.attrs.get("data-figure-ref") == figure_id
                and node.attrs.get("data-series-label") == name
                and series_key(figure, node) == expected
            ]
            mark_colours = set().union(*(colour_literals(point) for point in selected))
            valid_legends = [
                legend for legend in legends
                if mark_colours.intersection(
                    set().union(*(colour_literals(swatch) for swatch in [legend, *legend.descendants()]))
                )
            ]
            failures += int(len(valid_legends) != 1)
            if len(valid_legends) != 1:
                details.append(
                    f"figure_id={figure_id} value={name!r} "
                    f"violated=legend_contract_or_colour matches={len(valid_legends)}"
                )
    return report(2, failures == 0, 39 + 35, "\n".join([f"missing_series_or_labels={failures}", *details]))


def row_key(point: Node) -> tuple[str, str, str, str, str]:
    return (
        point.attrs.get("data-csv-series-id", ""),
        point.attrs.get("data-csv-year", ""),
        point.attrs.get("data-csv-age-band", ""),
        point.attrs.get("data-csv-sex", ""),
        point.attrs.get("data-csv-population-definition", ""),
    )


def c3(figs: list[Node], rows: dict[str, list[dict[str, str]]]) -> ConditionResult:
    all_rows = [row for group in rows.values() for row in group]
    index: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in all_rows:
        index[(
            row.get("series_id", ""),
            row.get("year", ""),
            row.get("age_band", ""),
            row.get("sex", ""),
            row.get("population_definition", ""),
        )].append(row)
    failures = 0
    details: list[str] = []
    selected = [point for figure in figs for point in points(figure)]
    for figure in figs:
        for point in points(figure):
            metric = point.attrs.get("data-csv-metric")
            matches = index[row_key(point)]
            column = METRIC_COLUMNS.get(metric or "")
            if len(matches) != 1 or column is None:
                failures += 1
                continue
            row = matches[0]
            required = {"data-csv-series-id": "series_id", "data-csv-year": "year", METRIC_ATTRS[metric]: column}
            for attribute, source in required.items():
                if attribute not in point.attrs:
                    failures += 1
                elif attribute in NUMERIC_ATTRS:
                    try:
                        matches_value = decimal(point.attrs[attribute]) == decimal(row[source])
                    except ValueError as error:
                        failures += 1
                        details.append(
                            "condition_3_detail: "
                            f"figure_id={figure.attrs['data-figure-id']} element={point.tag} "
                            f"attribute={attribute} svg_value={point.attrs[attribute]!r} "
                            f"csv_value={row[source]!r} violated=decimal_parse "
                            f"{type(error).__name__}: {error}"
                        )
                    else:
                        failures += int(not matches_value)
                else:
                    failures += int(point.attrs.get(attribute) != row[source])
            pairs = [("age_band", "data-csv-age-band"), ("sex", "data-csv-sex")]
            if row["series_id"] == "aging_age_structure":
                pairs += [("observation_basis", "data-csv-observation-basis"), ("observation_schedule", "data-csv-observation-schedule"), ("population_definition", "data-csv-population-definition")]
            if row["series_id"] == "youth_suicide_rate_0_19":
                pairs.append(("population_basis", "data-csv-population-basis"))
                if metric == "suicide_count": pairs.append(("suicide_count_source", "data-csv-suicide-count-source"))
            if row["series_id"] == "npa_suicide_by_age_rate":
                pairs.append(("population_basis", "data-csv-population-basis"))
                if metric == "rate_per_100k": pairs += [("population_source_age_classes", "data-csv-population-source-age-classes"), ("denominator_scope", "data-csv-denominator-scope")]
            if row["series_id"] == "vital_suicide_by_age_sex_rate":
                pairs += [("suicide_count_source_age_classes", "data-csv-suicide-count-source-age-classes"), ("population_source_age_classes", "data-csv-population-source-age-classes"), ("denominator_scope", "data-csv-denominator-scope")]
            for source, attribute in pairs:
                if row.get(source):
                    failures += int(point.attrs.get(attribute) != row[source])
    return report(3, bool(selected) and failures == 0, len(selected), "\n".join([f"attribute_or_row_failures={failures}", *details]))


def point_value(point: Node) -> Decimal:
    metric = point.attrs.get("data-csv-metric", "")
    return decimal(point.attrs.get(METRIC_ATTRS.get(metric, "")))


def c4(figs: list[Node]) -> ConditionResult:
    failures = 0
    denominator = 0
    for figure in figs:
        current = points(figure)
        denominator += len(current)
        try:
            minimum = decimal(figure.attrs.get("data-y-scale-domain-min")); maximum = decimal(figure.attrs.get("data-y-scale-domain-max"))
            top = decimal(figure.attrs.get("data-y-scale-pixel-top")); bottom = decimal(figure.attrs.get("data-y-scale-pixel-bottom"))
            if not minimum < maximum or not top < bottom or not current:
                failures += max(1, len(current)); continue
            for point in current:
                expected = bottom + (point_value(point) - minimum) / (maximum - minimum) * (top - bottom)
                failures += int(abs(decimal(point.attrs.get("cy")) - expected) > Decimal("0.01"))
        except (KeyError, ValueError):
            failures += max(1, len(current))
    return report(4, len(figs) == 15 and denominator > 0 and failures == 0, denominator, f"scale_or_coordinate_failures={failures}")


def c5(figs: list[Node]) -> ConditionResult:
    by_id = figure_map(figs); failures = 0
    for figure_id in ("age-structure-persons", "vital-counts", "suicide-count-by-age", "youth-suicide-count", "youth-population"):
        figure = by_id.get(figure_id)
        try:
            failures += int(figure is None or not (decimal(figure.attrs.get("data-y-scale-domain-min")) <= 0 <= decimal(figure.attrs.get("data-y-scale-domain-max"))))
        except ValueError:
            failures += 1
    return report(5, failures == 0, 5, f"domains_not_including_zero={failures}")


def selected_aging(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    priority = {"確定値・各歳": 0, "概算値・5歳階級": 1, "国勢調査・年齢3区分": 2}
    result = []
    for year in sorted({row["year"] for row in rows}, key=int):
        for band in AGE_BANDS:
            choices = [row for row in rows if row["year"] == year and row["age_band"] == band and row["population_definition"] == "総人口" and not (int(year) >= 1995 and row["observation_basis"] == "国勢調査・年齢3区分")]
            if choices:
                result.append(min(choices, key=lambda row: priority[row["observation_basis"]]))
    return result


def c6(
    figs: list[Node], rows: dict[str, list[dict[str, str]]], nodes: list[Node]
) -> ConditionResult:
    expected = selected_aging(rows["aging"]); expected_keys = {(row["year"], row["age_band"]) for row in expected}
    expected_changes: list[tuple[str, str, str, str]] = []
    base = sorted((row for row in expected if row["age_band"] == "0-14歳"), key=lambda row: int(row["year"]))
    for previous, current in pairwise(base):
        for column, kind in (("observation_basis", "observation_basis_change"), ("observation_schedule", "observation_schedule_change")):
            if previous[column] != current[column]: expected_changes.append((kind, current["year"], previous[column], current[column]))
    failures = 0
    details: list[str] = []
    for figure_id in ("age-structure-persons", "age-structure-share"):
        figure = figure_map(figs).get(figure_id); current = [] if figure is None else [point for point in points(figure) if point.attrs.get("data-csv-series-id") == "aging_age_structure"]
        actual = {(point.attrs.get("data-csv-year"), point.attrs.get("data-csv-age-band")) for point in current}
        failures += len(actual ^ expected_keys) + (len(current) - len(actual))
        metric = metric_for(figure_id); expected_by_key = {(row["year"], row["age_band"]): row for row in expected}
        for point in current:
            row = expected_by_key.get((point.attrs.get("data-csv-year"), point.attrs.get("data-csv-age-band")))
            failures += int(row is None or point.attrs.get(METRIC_ATTRS[metric]) != row[METRIC_COLUMNS[metric]])
        failures += sum(point.attrs.get("data-csv-year", "") >= "1995" and point.attrs.get("data-csv-observation-basis") == "国勢調査・年齢3区分" for point in current)
        for kind, year, before, after in expected_changes:
            notes = [
                node for node in nodes
                if not has_svg_ancestor(node)
                and node.attrs.get("data-figure-ref") == figure_id
                and node.attrs.get("data-annotation-kind") == kind
                and node.attrs.get("data-annotation-year") == year
                and before in node.text() and after in node.text()
            ]
            rules = [
                node for node in ([] if figure is None else figure.descendants())
                if node.tag == "line"
                and node.attrs.get("data-annotation-kind") == kind
                and node.attrs.get("data-annotation-year") == year
            ]
            failures += int(len(notes) != 1 or len(rules) != 1)
            if len(notes) != 1 or len(rules) != 1:
                details.append(
                    f"figure_id={figure_id} value={kind}:{year} "
                    f"violated=note_or_rule_pair notes={len(notes)} rules={len(rules)}"
                )
    return report(6, failures == 0, 2 * len(expected_keys) + 4 * len(expected_changes), "\n".join([f"selection_or_annotation_failures={failures}", *details]))


def c7(figs: list[Node], rows: dict[str, list[dict[str, str]]]) -> ConditionResult:
    expected = {(row["year"], row["total_fertility_rate"]) for row in rows["vital"] if row["total_fertility_rate"]}
    figure = figure_map(figs).get("total-fertility-rate")
    current = [] if figure is None else [point for point in points(figure) if point.attrs.get("data-csv-metric") == "total_fertility_rate"]
    actual = {(point.attrs.get("data-csv-year", ""), point.attrs.get("data-csv-total-fertility-rate", "")) for point in current}
    failures = len(actual ^ expected) + sum(point.attrs.get("data-csv-year", "9999") <= "1946" for point in current)
    return report(7, failures == 0, len(expected), f"missing_extra_or_pre_1947={failures}")


def c10(figs: list[Node]) -> ConditionResult:
    ticks = [
        node
        for figure in figs
        for axis in figure.descendants()
        if axis.attrs.get("data-axis") == "x"
        and any(
            label.tag == "text" and label.attrs.get("data-axis-label") == "年"
            for label in axis.descendants()
        )
        for node in axis.descendants()
        if "data-tick-value" in node.attrs
    ]
    failures = sum(
        node.attrs.get("data-tick-value") != node.text().strip()
        or re.fullmatch(r"[0-9]{4}", node.attrs.get("data-tick-value", "")) is None
        for node in ticks
    )
    return report(10, bool(ticks) and failures == 0, len(ticks), f"invalid_year_ticks={failures}")


def series_key(figure: Node, node: Node) -> tuple[str, str, str, str]:
    return (
        figure.attrs.get("data-figure-id", ""),
        node.attrs.get("data-csv-metric", ""),
        node.attrs.get("data-csv-age-band", ""),
        node.attrs.get("data-csv-sex", ""),
    )


TRANSLATE = re.compile(
    r"translate\(\s*([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))"
    r"(?:(?:\s*,\s*|\s+)([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)))?\s*\)"
)
EM_BASELINE = re.compile(r"[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)em")


def svg_coordinate(node: Node, coordinate: int) -> Decimal:
    attribute = ("x", "y")[coordinate]
    value = node.attrs.get(attribute)
    # Observable Plot places tick labels with a translate transform and uses an
    # em-valued text baseline adjustment. Tick placement is encoded in the
    # translate transform, while the baseline offset is shared presentation
    # within an axis and does not affect adjacent-tick spacing.
    position = Decimal(0) if value is None or EM_BASELINE.fullmatch(value) else decimal(value)
    current: Node | None = node
    while current is not None:
        for match in TRANSLATE.finditer(current.attrs.get("transform", "")):
            position += decimal(match.group(coordinate + 1) or "0")
        current = current.parent
    return position


def c13(figs: list[Node]) -> ConditionResult:
    endpoint_failures = 0
    pair_failures = 0
    denominator = 0
    for figure in figs:
        x_axes = [
            axis for axis in figure.descendants()
            if axis.attrs.get("data-axis") == "x"
        ]
        y_axes = [
            axis for axis in figure.descendants()
            if axis.attrs.get("data-axis") == "y"
        ]
        figure_years = [point.attrs.get("data-csv-year", "") for point in points(figure)]
        if not figure_years:
            endpoint_failures += 1
        else:
            minimum, maximum = min(figure_years), max(figure_years)
            x_ticks = [
                tick for axis in x_axes for tick in axis.descendants()
                if "data-tick-value" in tick.attrs and tick.text().strip()
            ]
            endpoint_failures += int(
                not any(tick.attrs["data-tick-value"] == minimum for tick in x_ticks)
            )
            endpoint_failures += int(
                not any(tick.attrs["data-tick-value"] == maximum for tick in x_ticks)
            )
        for axes, coordinate, minimum_gap in ((x_axes, 0, Decimal(30)), (y_axes, 1, Decimal(14))):
            ticks = [
                tick for axis in axes for tick in axis.descendants()
                if "data-tick-value" in tick.attrs and tick.text().strip()
            ]
            denominator += max(0, len(ticks) - 1)
            coordinates: list[Decimal | None] = []
            for tick in ticks:
                try:
                    coordinates.append(svg_coordinate(tick, coordinate))
                except ValueError:
                    coordinates.append(None)
            coordinates.sort(key=lambda value: (value is None, value or Decimal(0)))
            for first, second in pairwise(coordinates):
                if first is None or second is None:
                    pair_failures += 1
                else:
                    pair_failures += int(second - first < minimum_gap)
    return report(
        13,
        denominator > 0 and endpoint_failures == 0 and pair_failures == 0,
        denominator,
        f"endpoint_failures={endpoint_failures} tick_pair_failures={pair_failures}",
    )


def visible_texts(figure: Node) -> list[Node]:
    return [
        node for node in figure.descendants()
        if node.tag == "text" and node.text().strip() and has_svg_ancestor(node)
    ]


def truncated_text(node: Node, limit: int = 80) -> str:
    text = node.text().strip()
    return text if len(text) <= limit else f"{text[:limit]}..."


def c14(figs: list[Node]) -> ConditionResult:
    failures = 0
    denominator = 0
    details: list[str] = []
    for figure in figs:
        figure_id = figure.attrs.get("data-figure-id", "missing")
        visible = visible_texts(figure)
        denominator += len(visible)
        svgs = [
            node for node in [figure, *figure.descendants()]
            if node.tag == "svg"
        ]
        if len(svgs) != 1:
            failures += 1
            details.append(f"figure_id={figure_id} violated=viewBox svg_count={len(svgs)}")
            continue
        try:
            parts = svgs[0].attrs.get("viewbox", "").split()
            if len(parts) != 4 or parts[:2] != ["0", "0"]:
                raise ValueError("invalid viewBox")
            width, height = decimal(parts[2]), decimal(parts[3])
            if width <= 0 or height <= 0:
                raise ValueError("non-positive viewBox")
        except ValueError:
            failures += 1
            details.append(f"figure_id={figure_id} violated=viewBox")
            continue
        for node in visible:
            try:
                permitted = (
                    "data-axis-label" in node.attrs or "data-tick-value" in node.attrs
                )
                font_size: Decimal | None = None
                current: Node | None = node
                while current is not None:
                    if "font-size" in current.attrs:
                        font_size = decimal(current.attrs["font-size"])
                        break
                    current = current.parent
                font_size = Decimal(10) if font_size is None else font_size
                text_width = font_size * sum(
                    Decimal("0.6") if ord(character) <= 0x7F else Decimal(1)
                    for character in node.text().strip()
                )
                x, y = svg_coordinate(node, 0), svg_coordinate(node, 1)
                anchor = node.attrs.get("text-anchor", "start")
                valid_x = {
                    "start": x + text_width + 4 <= width,
                    "end": x - text_width - 4 >= 0,
                    "middle": x - text_width / 2 - 4 >= 0 and x + text_width / 2 + 4 <= width,
                }.get(anchor, False)
                violated: list[str] = []
                if font_size <= 0:
                    violated.append("font_size")
                if not permitted:
                    violated.append("not_axis_or_tick")
                if anchor == "start" and x + text_width + 4 > width:
                    violated.append("right")
                elif anchor == "end" and x - text_width - 4 < 0:
                    violated.append("left")
                elif anchor == "middle":
                    if x - text_width / 2 - 4 < 0:
                        violated.append("left")
                    if x + text_width / 2 + 4 > width:
                        violated.append("right")
                elif anchor not in {"start", "end", "middle"}:
                    violated.append("anchor")
                if not 0 <= y <= height:
                    violated.append("y")
                if violated:
                    details.append(
                        "condition_14_detail: "
                        f"figure_id={figure_id} text={truncated_text(node)!r} "
                        f"anchor={anchor} width={text_width} x={x} y={y} "
                        f"violated={','.join(violated)}"
                    )
                failures += int(
                    not permitted or font_size <= 0 or not valid_x or not (0 <= y <= height)
                )
            except ValueError:
                failures += 1
                details.append(
                    "condition_14_detail: "
                    f"figure_id={figure_id} text={truncated_text(node)!r} "
                    "anchor=unresolved width=unresolved x=unresolved y=unresolved "
                    "violated=parse"
                )
    detail = "\n".join([f"text_fit_failures={failures}", *details])
    return report(14, denominator > 0 and failures == 0, denominator, detail)


X_DOMAINS = {
    "age-structure-persons": ("1920", "2025"), "age-structure-share": ("1920", "2025"),
    "vital-counts": ("1899", "2024"), "total-fertility-rate": ("1899", "2024"),
    "suicide-count-by-age": ("1995", "2025"), "suicide-rate-by-age": ("1995", "2025"),
    "youth-suicide-count": ("1995", "2025"), "youth-population": ("1995", "2025"),
    "youth-suicide-rate": ("1995", "2025"),
    "vital-suicide-rate-0-19": ("1995", "2024"), "vital-suicide-rate-20-29": ("1995", "2024"),
    "vital-suicide-rate-30-39": ("1995", "2024"), "vital-suicide-rate-40-49": ("1995", "2024"),
    "vital-suicide-rate-50-59": ("1995", "2024"), "vital-suicide-rate-60-plus": ("1995", "2024"),
}


def c15(
    figs: list[Node], rows: dict[str, list[dict[str, str]]], nodes: list[Node]
) -> ConditionResult:
    by_id = figure_map(figs)
    failures = 0
    details: list[str] = []
    for identifier, (minimum, maximum) in X_DOMAINS.items():
        figure = by_id.get(identifier)
        if figure is None:
            failures += 2
            details.append(f"figure_id={identifier} value=missing violated=domain_attributes")
            continue
        failures += int(figure.attr_counts.get("data-x-scale-domain-min") != 1 or figure.attrs.get("data-x-scale-domain-min") != minimum)
        failures += int(figure.attr_counts.get("data-x-scale-domain-max") != 1 or figure.attrs.get("data-x-scale-domain-max") != maximum)
        if identifier.startswith("vital-suicide-rate-"):
            suffix = identifier.removeprefix("vital-suicide-rate-")
            band = "60歳以上" if suffix == "60-plus" else f"{suffix}歳"
            source = [row for row in rows["sex"] if row["age_band"] == band and row["rate_per_100k"]]
        elif identifier.startswith("age-structure-"):
            source = selected_aging(rows["aging"])
        else:
            source_name = {"vital": "vital", "suicide": "suicide", "youth": "youth"}.get(
                "vital" if identifier in {"vital-counts", "total-fertility-rate"} else
                "suicide" if identifier.startswith("suicide-") else "youth"
            )
            source = rows[source_name]
        metrics = (
            ("birth_count", "death_count", "natural_change")
            if identifier == "vital-counts"
            else (metric_for(identifier),)
        )
        columns = [METRIC_COLUMNS[metric] for metric in metrics]
        observed = [
            row["year"]
            for row in source
            if any(row.get(column, "") for column in columns)
        ]
        if not observed:
            failures += 1
            continue
        first = min(observed)
        annotations = [
            node for node in nodes
            if not has_svg_ancestor(node)
            and node.attrs.get("data-figure-ref") == identifier
            and node.attrs.get("data-annotation-kind") == "source_data_start"
        ]
        rules = [
            node for node in figure.descendants()
            if node.tag == "line"
            and node.attrs.get("data-annotation-kind") == "source_data_start"
        ]
        expected_text = f"元データは {first} 年から"
        if first > minimum:
            invalid = (
                len(annotations) != 1
                or len(rules) != 1
                or annotations[0].attrs.get("data-annotation-year") != first
                or rules[0].attrs.get("data-annotation-year") != first
                or annotations[0].text().strip() != expected_text
            )
            failures += int(invalid)
            if invalid:
                details.append(
                    f"figure_id={identifier} value=source_data_start:{first} "
                    f"violated=note_or_rule_pair notes={len(annotations)} rules={len(rules)}"
                )
        else:
            invalid = bool(annotations) or bool(rules)
            failures += int(invalid)
            if invalid:
                details.append(
                    f"figure_id={identifier} value=source_data_start "
                    f"violated=unexpected_note_or_rule notes={len(annotations)} rules={len(rules)}"
                )
    return report(15, failures == 0, 60, "\n".join([f"domain_or_start_annotation_failures={failures}", *details]))


def run(conf: Config) -> int:
    try:
        rows = {name: load(path) for name, path in conf.csvs.items()}; nodes = pages(conf.dist)
        if not nodes: print("precondition: FAIL denominator=0 built_html_files=0"); return 1
    except Exception as error:  # noqa: BLE001
        print(f"precondition: FAIL denominator=0 {type(error).__name__}: {error}"); return 1
    figs = figures(nodes)
    results = []
    all_html_nodes = all_nodes(nodes)
    for number, check in ((1, lambda: c1(figs, all_html_nodes)), (2, lambda: c2(figs, all_html_nodes)), (3, lambda: c3(figs, rows)), (4, lambda: c4(figs)), (5, lambda: c5(figs)), (6, lambda: c6(figs, rows, all_html_nodes)), (7, lambda: c7(figs, rows)), (10, lambda: c10(figs)), (13, lambda: c13(figs)), (14, lambda: c14(figs)), (15, lambda: c15(figs, rows, all_html_nodes))):
        results.append(execute_condition(number, check))
    return 0 if all(results) else 1


def fixture_html(rows: dict[str, list[dict[str, str]]]) -> str:
    aging = selected_aging(rows["aging"]); suicide = [row for row in rows["suicide"] if row["age_band"] in SUICIDE_BANDS]
    sex = [row for row in rows["sex"] if row["rate_per_100k"] and row["age_band"] in VITAL_BANDS]

    def series_colour(metric: str, age_band: str = "", sex: str = "") -> str:
        return {
            "0-14歳": "#2a78d6", "15-64歳": "#eb6834", "65歳以上": "#008300",
            "0-19歳": "#2a78d6", "20-29歳": "#eb6834", "30-39歳": "#1baf7a",
            "40-49歳": "#eda100", "50-59歳": "#e87ba4", "60歳以上": "#008300",
            "男": "#2a78d6", "女": "#e87ba4",
            "birth_count": "#2a78d6", "death_count": "#eb6834",
            "natural_change": "#1baf7a",
        }.get(age_band or sex or metric, "#000000")

    def circle(row: dict[str, str], metric: str, minimum: Decimal, maximum: Decimal) -> str:
        value = decimal(row[METRIC_COLUMNS[metric]]); cy = Decimal(100) + (value - minimum) / (maximum - minimum) * Decimal(-100)
        attrs = {"data-csv-series-id": row["series_id"], "data-csv-year": row["year"], "data-csv-metric": metric, METRIC_ATTRS[metric]: row[METRIC_COLUMNS[metric]], "cx": row["year"], "cy": str(cy)}
        for source, attribute in (("age_band", "data-csv-age-band"), ("sex", "data-csv-sex"), ("observation_basis", "data-csv-observation-basis"), ("observation_schedule", "data-csv-observation-schedule"), ("population_definition", "data-csv-population-definition"), ("suicide_count_source", "data-csv-suicide-count-source"), ("population_basis", "data-csv-population-basis"), ("suicide_count_source_age_classes", "data-csv-suicide-count-source-age-classes"), ("population_source_age_classes", "data-csv-population-source-age-classes"), ("denominator_scope", "data-csv-denominator-scope")):
            if row.get(source): attrs[attribute] = row[source]
        attrs["stroke"] = series_colour(metric, row.get("age_band", ""), row.get("sex", ""))
        return "<circle " + " ".join(f'{key}="{value}"' for key, value in attrs.items()) + "/>"
    def label_specs(identifier: str, metrics: list[str], source: list[dict[str, str]]) -> list[tuple[str, str, str, str, Decimal]]:
        if len(FIGURES[identifier][1]) <= 1:
            return []
        names = FIGURES[identifier][1]
        metric_by_name = {"出生": "birth_count", "死亡": "death_count", "自然増減": "natural_change"}
        result = []
        for name in names:
            metric = metric_by_name.get(name, metrics[0])
            candidates = [row for row in source if metric in metrics and row.get(METRIC_COLUMNS[metric], "") and (name in {"出生", "死亡", "自然増減"} or row.get("age_band") == name)]
            if candidates:
                row = max(candidates, key=lambda candidate: int(candidate["year"]))
                result.append((name, metric, row.get("age_band", ""), row.get("sex", ""), decimal(row[METRIC_COLUMNS[metric]])))
        return result
    def figure(identifier: str, body: str, minimum: Decimal, maximum: Decimal, labels: list[tuple[str, str, str, str, Decimal]], years: list[str], annotations: list[tuple[str, str, str]] | None = None) -> str:
        label = FIGURES[identifier][0]
        labels_html = ""; series_lines = ""
        for name, metric, band, sex, _ in labels:
            age_attribute = f' data-csv-age-band="{band}"' if band else ""
            sex_attribute = f' data-csv-sex="{sex}"' if sex else ""
            colour = series_colour(metric, band, sex)
            labels_html += (
                f'<li data-figure-ref="{identifier}" data-series-label="{name}" '
                f'data-csv-metric="{metric}"{age_attribute}{sex_attribute}>'
                f'<span class="series-swatch" data-series-color="{colour}" '
                f'aria-hidden="true"></span>{name}</li>'
            )
            series_lines += f'<line stroke="{colour}"/>'
        first_year, last_year = min(years), max(years)
        domain_minimum, domain_maximum = X_DOMAINS[identifier]
        notes = ""; rules = ""
        for kind, year, text in annotations or []:
            notes += f'<p data-figure-ref="{identifier}" data-annotation-kind="{kind}" data-annotation-year="{year}">{text}</p>'
            rules += f'<line data-annotation-kind="{kind}" data-annotation-year="{year}"/>'
        if first_year > domain_minimum:
            notes += f'<p data-figure-ref="{identifier}" data-annotation-kind="source_data_start" data-annotation-year="{first_year}">元データは {first_year} 年から</p>'
            rules += f'<line data-annotation-kind="source_data_start" data-annotation-year="{first_year}"/>'
        return f'<section><figure><svg data-figure-id="{identifier}" data-y-scale-domain-min="{minimum}" data-y-scale-domain-max="{maximum}" data-y-scale-pixel-top="0" data-y-scale-pixel-bottom="100" data-x-scale-pixel-left="0" data-x-scale-pixel-right="100" data-x-scale-domain-min="{domain_minimum}" data-x-scale-domain-max="{domain_maximum}" viewBox="0 0 960 420"><g data-axis="x" transform="translate(10, 20)"><text data-axis-label="年" data-axis-label-visible="yes" x="0" y="5">年</text><text data-tick-value="{first_year}" transform="translate(0, 0)" y="0.71em">{first_year}</text><text data-tick-value="{last_year}" transform="translate(30, 0)" y="0.71em">{last_year}</text></g><g data-axis="y" transform="translate(5 10)"><text data-axis-label="{label}" data-axis-label-visible="yes" x="10" y="10">{label}</text><text data-tick-value="0" transform="translate(0, 0)" x="0" y="0.32em">0</text><text data-tick-value="1" transform="translate(0, 14)" x="0" y="0.32em">1</text></g>{body}{series_lines}{rules}</svg></figure>{labels_html}{notes}</section>'
    pieces = []
    for identifier, metric, source in (("age-structure-persons", "population_persons", aging), ("age-structure-share", "population_share_percent", aging), ("vital-counts", "birth_count", rows["vital"]), ("total-fertility-rate", "total_fertility_rate", [row for row in rows["vital"] if row["total_fertility_rate"]]), ("suicide-count-by-age", "suicide_count", suicide), ("suicide-rate-by-age", "rate_per_100k", suicide), ("youth-suicide-count", "suicide_count", rows["youth"]), ("youth-population", "population_persons", rows["youth"]), ("youth-suicide-rate", "rate_per_100k", rows["youth"])):
        metrics = [metric] if identifier != "vital-counts" else ["birth_count", "death_count", "natural_change"]
        values = [decimal(row[METRIC_COLUMNS[current]]) for current in metrics for row in source if row.get(METRIC_COLUMNS[current], "")]
        minimum, maximum = min(Decimal(0), min(values)), max(values)
        body = "".join(circle(row, current, minimum, maximum) for current in metrics for row in source if row.get(METRIC_COLUMNS[current], ""))
        annotations: list[tuple[str, str, str]] = []
        if identifier.startswith("age-structure"):
            base = sorted((row for row in aging if row["age_band"] == "0-14歳"), key=lambda row: int(row["year"]))
            for prior, current in pairwise(base):
                for column, kind in (("observation_basis", "observation_basis_change"), ("observation_schedule", "observation_schedule_change")):
                    if prior[column] != current[column]:
                        annotations.append((kind, current["year"], f'{prior[column]} {current[column]}'))
        pieces.append(figure(identifier, body, minimum, maximum, label_specs(identifier, metrics, source), sorted({row["year"] for row in source}), annotations))
    for suffix, band in (("0-19", "0-19歳"), ("20-29", "20-29歳"), ("30-39", "30-39歳"), ("40-49", "40-49歳"), ("50-59", "50-59歳"), ("60-plus", "60歳以上")):
        identifier = f"vital-suicide-rate-{suffix}"
        selected = [row for row in sex if row["age_band"] == band]
        values = [decimal(row["rate_per_100k"]) for row in selected]
        labels = [(name, "rate_per_100k", band, name, decimal(max((row for row in selected if row["sex"] == name), key=lambda row: int(row["year"]))["rate_per_100k"])) for name in ("男", "女")]
        pieces.append(figure(identifier, "".join(circle(row, "rate_per_100k", Decimal(0), max(values)) for row in selected), Decimal(0), max(values), labels, sorted({row["year"] for row in selected})))
    return "<html><body>" + "".join(pieces) + "</body></html>"


def run_fixtures() -> int:
    temporary = Path(tempfile.mkdtemp(prefix="verify-figures-")); outcomes = []
    try:
        rows = {name: load(path) for name, path in config().csvs.items()}
        for condition in (1, 2, 3, 4, 5, 6, 7, 10, 13, 14, 15):
            labels = ("pass", "attribute_fail", "visible_text_fail") if condition == 1 else ("pass", "fail")
            for label in labels:
                root = temporary / f"condition-{condition}-{label}"; dist = root / "dist"; dist.mkdir(parents=True)
                html = fixture_html(rows)
                if label == "attribute_fail":
                    html = html.replace('data-axis-label="年"', 'data-axis-label="wrong"', 1)
                elif label == "visible_text_fail":
                    html = html.replace('data-axis-label-visible="yes" x="0" y="5">年</text>', 'data-axis-label-visible="yes" x="0" y="5">wrong</text>', 1)
                elif label == "fail":
                    replacements = {1: ('data-figure-id="age-structure-persons"', 'data-figure-id="bad"'), 2: ('data-figure-ref="age-structure-persons"', 'data-figure-ref="bad"'), 3: ('data-csv-year="1920"', 'data-csv-year="x"'), 4: ('cy="', 'cy="999'), 5: ('data-y-scale-domain-min="0"', 'data-y-scale-domain-min="1"'), 6: ('data-annotation-kind="observation_basis_change"', 'data-annotation-kind="bad"'), 7: ('data-csv-metric="total_fertility_rate"', 'data-csv-metric="total_fertility_rate" data-csv-year="1899"'), 10: ('data-tick-value="1995" transform="translate(0, 0)" y="0.71em">1995</text>', 'data-tick-value="1,995" transform="translate(0, 0)" y="0.71em">1,995</text>'), 13: ('transform="translate(30, 0)"', 'transform="translate(29, 0)"'), 14: ('viewBox="0 0 960 420"', 'viewBox="0 0 20 420"'), 15: ('data-x-scale-domain-min="1920"', 'data-x-scale-domain-min="1919"')}[condition]
                    html = html.replace(*replacements, 1)
                (dist / "index.html").write_text(html, encoding="utf-8")
                previous = os.environ.get("FIGURES_DIST"); os.environ["FIGURES_DIST"] = str(dist)
                output = io.StringIO()
                with contextlib.redirect_stdout(output): run(config())
                if previous is None: os.environ.pop("FIGURES_DIST", None)
                else: os.environ["FIGURES_DIST"] = previous
                captured = output.getvalue()
                print(captured, end="")
                line = next((item for item in captured.splitlines() if item.startswith(f"condition_{condition}:")), "")
                expected = "PASS" if label == "pass" else "FAIL"; denominator = next((item.split("=", 1)[1] for item in line.split() if item.startswith("denominator=")), "unknown")
                passed = f"condition_{condition}: {expected}" in line
                print(f"fixture_condition_{condition}_{label}: {'PASS' if passed else 'FAIL'} denominator={denominator}")
                outcomes.append(passed)
    finally:
        shutil.rmtree(temporary)
    return 0 if all(outcomes) else 1


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--fixture", action="store_true")
    arguments = parser.parse_args()
    return run_fixtures() if arguments.fixture else run(config())


if __name__ == "__main__":
    raise SystemExit(main())
