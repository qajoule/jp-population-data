import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export const AGE_STRUCTURE_CSV_PATH = "data/derived/aging_age_structure.csv";
export const VITAL_CHANGE_CSV_PATH = "data/derived/aging_vital_change.csv";

const AGE_COLUMNS = [
  "series_id", "year", "reference_date", "observation_basis", "observation_schedule",
  "population_definition", "population_definition_source", "age_band", "population_persons",
  "population_share_percent", "age_band_source", "population_unit_source", "source_series_id",
  "source_stats_data_id", "built_at",
] as const;
const VITAL_COLUMNS = [
  "series_id", "year", "reference_date", "population_definition", "population_definition_source",
  "births_persons", "births_source", "deaths_persons", "deaths_source", "natural_change_persons",
  "total_fertility_rate", "total_fertility_rate_source", "unit_source", "source_births_stats_data_id",
  "source_deaths_stats_data_id", "built_at",
] as const;

export type AgingAgeRecord = Record<(typeof AGE_COLUMNS)[number], string>;
export type AgingVitalRecord = Record<(typeof VITAL_COLUMNS)[number], string>;

function readRows<T extends readonly string[]>(path: string, columns: T, expectedRows: number, allowEmpty: boolean): Record<T[number], string>[] {
  const file = resolve(process.cwd(), "..", path);
  const lines = readFileSync(file, "utf8").trimEnd().split("\n");
  const header = lines.shift()?.replace(/^\uFEFF/, "").split(",");
  if (!header || header.join(",") !== columns.join(",")) throw new Error(`${path}: 列名または列順が要件と一致しません`);
  if (lines.length !== expectedRows) throw new Error(`${path}: データ行数が不正です: ${lines.length}`);
  return lines.map((line, index) => {
    const values = line.replace(/\r$/, "").split(",");
    if (values.length !== columns.length || (!allowEmpty && values.some((value) => value === ""))) {
      throw new Error(`${path}: ${index + 2}行目の列数または空セルが不正です`);
    }
    return Object.fromEntries(columns.map((column, i) => [column, values[i]])) as Record<T[number], string>;
  });
}

export const agingAgeRecords = readRows(AGE_STRUCTURE_CSV_PATH, AGE_COLUMNS, 228, false) as AgingAgeRecord[];
export const agingVitalRecords = readRows(VITAL_CHANGE_CSV_PATH, VITAL_COLUMNS, 123, true) as AgingVitalRecord[];

const BASIS_PRIORITY = ["確定値・各歳", "概算値・5歳階級", "国勢調査・年齢3区分"] as const;

/** 年ごとに実在する basis の優先順位で、年齢帯ごとに一行だけ選ぶ。 */
export const selectedAgeStructureRecords = Array.from(
  agingAgeRecords.reduce((byYear, record) => {
    const rows = byYear.get(record.year) ?? [];
    rows.push(record);
    byYear.set(record.year, rows);
    return byYear;
  }, new Map<string, AgingAgeRecord[]>()).entries(),
).flatMap(([, rows]) => {
  const basis = BASIS_PRIORITY.find((candidate) => rows.some((row) => row.observation_basis === candidate));
  if (!basis) throw new Error(`${AGE_STRUCTURE_CSV_PATH}: 選択可能な observation_basis がありません`);
  return rows.filter((row) => row.observation_basis === basis);
}).sort((a, b) => Number(a.year) - Number(b.year) || a.age_band.localeCompare(b.age_band));

const selectedAgeYears = Array.from(new Map(
  selectedAgeStructureRecords.map((record) => [record.year, record]),
).values()).sort((a, b) => Number(a.year) - Number(b.year));

export const ageStructureAnnotations = (["observation_basis", "observation_schedule"] as const).flatMap((field) =>
  selectedAgeYears.flatMap((record, index) => {
    const previous = selectedAgeYears[index - 1];
    return !previous || record[field] === previous[field]
      ? []
      : [{ kind: `${field}_change`, year: record.year, previous: previous[field], current: record[field] }];
  }),
);
