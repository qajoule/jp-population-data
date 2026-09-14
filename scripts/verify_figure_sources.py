"""Verify that source attribution rendered in the built page matches its records."""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site/dist/index.html"
FIGURE_SOURCES = ROOT / "data/figure_sources.json"
ESTAT_META = ROOT / "data/estat/_meta.csv"
SOURCES_DOCUMENT = ROOT / "docs/SOURCES.md"
NPA_DOCUMENT = ROOT / "docs/NPA_SUICIDE_SOURCE_RESULT.md"
ATTRIBUTION_ITEM = re.compile(r"「(?P<title>[^」]+)」（(?P<organization>[^）]+)）")


@dataclass
class Figure:
    figure_id: str


@dataclass
class Section:
    figures: list[Figure] = field(default_factory=list)
    attributions: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)


class PageParser(HTMLParser):
    """Collect figures, section attribution, and source-block links from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[Section] = []
        self.external_urls: list[str] = []
        self.non_source_urls: list[str] = []
        self.figure_ids_outside_sections: list[str] = []
        self._current_section: Section | None = None
        self._source_depth = 0
        self._attribution_depth = 0
        self._attribution_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "section" and "mock-figure" in classes:
            self._current_section = Section()
            self.sections.append(self._current_section)
        figure_id = attributes.get("data-figure-id")
        if figure_id:
            if self._current_section is None:
                self.figure_ids_outside_sections.append(figure_id)
            else:
                self._current_section.figures.append(Figure(figure_id))
        if tag == "details" and "chart-sources" in classes and self._current_section:
            self._source_depth += 1
        if self._source_depth and tag == "p" and "chart-attribution" in classes:
            self._attribution_depth += 1
            self._attribution_parts = []
        href = attributes.get("href")
        if href and href.startswith(("https://", "http://")):
            self.external_urls.append(href)
            if self._source_depth and self._current_section:
                self._current_section.urls.append(href)
            else:
                self.non_source_urls.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self._attribution_depth:
            if self._current_section is not None:
                self._current_section.attributions.append("".join(self._attribution_parts))
            self._attribution_depth -= 1
        if tag == "details" and self._source_depth:
            self._source_depth -= 1
        if tag == "section" and self._current_section is not None:
            self._current_section = None

    def handle_data(self, data: str) -> None:
        if self._attribution_depth:
            self._attribution_parts.append(data)


def parse_page(text: str) -> PageParser:
    parser = PageParser()
    parser.feed(text)
    parser.close()
    return parser


def read_meta_titles() -> set[str]:
    with ESTAT_META.open(encoding="utf-8", newline="") as source:
        return {row["table_title"] for row in csv.DictReader(source) if row["table_title"]}


def npa_titles() -> set[str]:
    text = NPA_DOCUMENT.read_text(encoding="utf-8")
    return set(re.findall(r"\| 2025 \| ([^|]+) \| \[PDF\]", text))


def attribution_items(attribution: str) -> list[tuple[str, str]]:
    return [(match["title"], match["organization"]) for match in ATTRIBUTION_ITEM.finditer(attribution)]


def report(label: str, checked: int, mismatches: list[str], *, nonzero: bool = True) -> bool:
    passed = not mismatches and (checked > 0 if nonzero else True)
    print(
        f"{label}: {'PASS' if passed else 'FAIL'} "
        f"checked={checked} mismatches={len(mismatches)}"
    )
    for mismatch in mismatches:
        print(f"{label}_detail: {mismatch}")
    return passed


def check_urls_in_sources(urls: list[str], sources_text: str) -> list[str]:
    return [f"url={url!r} reason=not_literal_in_docs/SOURCES.md" for url in urls if url not in sources_text]


def check_titles(sections: list[Section], estat_titles: set[str], police_titles: set[str]) -> tuple[int, list[str]]:
    mismatches: list[str] = []
    checked = 0
    for section in sections:
        for attribution in section.attributions:
            for title, organization in attribution_items(attribution):
                checked += 1
                titles = police_titles if organization == "警察庁" else estat_titles
                if title not in titles:
                    normalized_match = next(
                        (
                            candidate
                            for candidate in titles
                            if unicodedata.normalize("NFKC", candidate)
                            == unicodedata.normalize("NFKC", title)
                        ),
                        None,
                    )
                    detail = f"section_figures={[figure.figure_id for figure in section.figures]!r} title={title!r}"
                    if normalized_match:
                        detail += f" normalized_only_record={normalized_match!r}"
                    detail += " reason=not_literal_in_authoritative_record"
                    mismatches.append(detail)
    return checked, mismatches


def check_organizations(sections: list[Section], records: dict[str, object]) -> tuple[int, list[str]]:
    checked = 0
    mismatches: list[str] = []
    for section in sections:
        figure_ids = [figure.figure_id for figure in section.figures if figure.figure_id in records]
        organizations = {
            item["source_organization"]
            for figure_id in figure_ids
            for item in records[figure_id]["primary_inputs"]  # type: ignore[index]
        }
        for attribution in section.attributions:
            for _, organization in attribution_items(attribution):
                checked += 1
                if organization not in organizations:
                    mismatches.append(
                        f"section_figures={figure_ids!r} attribution_organization={organization!r} "
                        f"recorded_organizations={sorted(organizations)!r}"
                    )
    return checked, mismatches


def check_section_attributions(parser: PageParser) -> list[str]:
    mismatches: list[str] = []
    seen_figure_ids: set[str] = set()
    for index, section in enumerate(parser.sections, start=1):
        figure_ids = [figure.figure_id for figure in section.figures]
        if len(section.attributions) != 1:
            mismatches.append(
                f"section={index} figures={figure_ids!r} attributions={len(section.attributions)} "
                "reason=section_must_have_exactly_one_attribution"
            )
        duplicate_ids = sorted(set(figure_ids) & seen_figure_ids)
        if duplicate_ids:
            mismatches.append(f"section={index} duplicate_figure_ids={duplicate_ids!r}")
        seen_figure_ids.update(figure_ids)
    if parser.figure_ids_outside_sections:
        mismatches.append(f"figure_ids_outside_sections={parser.figure_ids_outside_sections!r}")
    return mismatches


def check_figure_urls(sections: list[Section], records: dict[str, object]) -> tuple[int, list[str]]:
    checked = 0
    mismatches: list[str] = []
    for section in sections:
        figure_ids = [figure.figure_id for figure in section.figures if figure.figure_id in records]
        expected = {
            item["source_url"]
            for figure_id in figure_ids
            for item in records[figure_id]["primary_inputs"]  # type: ignore[index]
        }
        for url in section.urls:
            checked += 1
            if url not in expected:
                mismatches.append(f"section_figures={figure_ids!r} url={url!r} reason=not_in_figure_primary_inputs")
    return checked, mismatches


def self_tests() -> bool:
    source_url = "https://example.invalid/source"
    non_source_url = "https://example.invalid/non-source"
    title = "表題７"
    section = Section([Figure("figure")], [f"「{title}」（省庁）を加工して作成"], [source_url])
    records = {"figure": {"primary_inputs": [{"source_organization": "別の省庁", "source_url": "https://example.invalid/other"}]}}
    source_parser = parse_page(
        '<section class="mock-figure"><svg data-figure-id="figure"></svg>'
        f'<details class="chart-sources"><a href="{source_url}">source</a></details></section>'
        f'<a href="{non_source_url}">non-source</a>'
    )
    source_failure = (
        bool(check_urls_in_sources(source_parser.sections[0].urls, ""))
        and source_parser.non_source_urls == [non_source_url]
    )
    _, title_failure = check_titles([section], {"表題7"}, set())
    _, organization_failure = check_organizations([section], records)
    _, url_failure = check_figure_urls([section], records)
    no_attribution_parser = parse_page('<section class="mock-figure"><svg data-figure-id="figure"></svg></section>')
    no_attribution_failure = bool(check_section_attributions(no_attribution_parser))
    two_attributions_parser = parse_page(
        '<section class="mock-figure"><svg data-figure-id="figure"></svg>'
        '<details class="chart-sources"><p class="chart-attribution">a</p>'
        '<p class="chart-attribution">b</p></details></section>'
    )
    two_attributions_failure = bool(check_section_attributions(two_attributions_parser))
    results = {
        "self_test_source_url": source_failure,
        "self_test_title_width": bool(title_failure),
        "self_test_organization": bool(organization_failure),
        "self_test_figure_url": bool(url_failure),
        "self_test_figure_set": no_attribution_failure,
        "self_test_figure_without_attribution": no_attribution_failure,
        "self_test_section_with_two_attributions": two_attributions_failure,
    }
    for label, passed in results.items():
        print(f"{label}: {'PASS' if passed else 'FAIL'} deliberately_injected_mismatch=1")
    return all(results.values())


def main() -> int:
    parser = parse_page(PAGE.read_text(encoding="utf-8"))
    records = json.loads(FIGURE_SOURCES.read_text(encoding="utf-8"))
    sources_text = SOURCES_DOCUMENT.read_text(encoding="utf-8")
    source_urls = [url for section in parser.sections for url in section.urls]
    non_source_urls = sorted(set(parser.non_source_urls))
    figure_count = sum(len(section.figures) for section in parser.sections)
    print(
        f"page: path={PAGE.relative_to(ROOT)} sections={len(parser.sections)} "
        f"figures={figure_count} source_urls={len(source_urls)} "
        f"non_source_urls={len(non_source_urls)}"
    )
    for url in non_source_urls:
        print(f"non_source_url: url={url!r}")

    title_count, title_mismatches = check_titles(parser.sections, read_meta_titles(), npa_titles())
    organization_count, organization_mismatches = check_organizations(parser.sections, records)
    figure_url_count, figure_url_mismatches = check_figure_urls(parser.sections, records)
    attribution_mismatches = check_section_attributions(parser)
    outcomes = [
        report("source_urls_in_sources", len(source_urls), check_urls_in_sources(source_urls, sources_text)),
        report("attribution_titles", title_count, title_mismatches),
        report("attribution_organizations", organization_count, organization_mismatches),
        report("section_attribution_coverage", len(parser.sections), attribution_mismatches),
        report("figure_source_urls", figure_url_count, figure_url_mismatches),
    ]
    self_test_passed = self_tests()
    mismatch_count = sum(len(items) for items in (title_mismatches, organization_mismatches, figure_url_mismatches, attribution_mismatches, check_urls_in_sources(source_urls, sources_text)))
    print(
        f"summary: sections_checked={len(parser.sections)} figures_checked={figure_count} "
        f"source_urls_checked={len(source_urls)} non_source_urls_listed={len(non_source_urls)} "
        f"titles_checked={title_count} mismatches={mismatch_count}"
    )
    return 0 if all(outcomes) and self_test_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
