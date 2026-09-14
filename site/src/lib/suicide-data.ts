import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export const SUICIDE_AGE_CSV_PATH = "data/derived/suicide_by_age_rate.csv";
export const VITAL_SUICIDE_CSV_PATH = "data/derived/vital_suicide_by_age_sex_rate.csv";

const AGE_COLUMNS = [
  "series_id", "year", "age_band", "suicide_count", "suicide_count_source",
  "population_persons", "population_source_age_classes", "population_unit_source",
  "population_basis", "denominator_scope", "rate_per_100k", "built_at",
] as const;
const VITAL_COLUMNS = [
  "series_id", "year", "sex", "age_band", "suicide_count", "suicide_count_source_age_classes",
  "suicide_count_zero_filled_source_age_classes", "population_persons", "population_source_age_classes",
  "population_unit_source", "population_basis", "denominator_scope", "rate_per_100k",
  "population_definition", "built_at",
] as const;

export type SuicideAgeRecord = Record<(typeof AGE_COLUMNS)[number], string>;
export type VitalSuicideRecord = Record<(typeof VITAL_COLUMNS)[number], string>;

function readRows<T extends readonly string[]>(path: string, columns: T): Record<T[number], string>[] {
  const lines = readFileSync(resolve(process.cwd(), "..", path), "utf8").trimEnd().split("\n");
  const header = lines.shift()?.replace(/^\uFEFF/, "").split(",");
  if (!header || header.join(",") !== columns.join(",")) throw new Error(`${path}: 列名または列順が要件と一致しません`);
  return lines.map((line, i) => {
    const values = line.replace(/\r$/, "").split(",");
    if (values.length !== columns.length) throw new Error(`${path}: ${i + 2}行目の列数が不一致です`);
    return Object.fromEntries(columns.map((column, j) => [column, values[j]])) as Record<T[number], string>;
  });
}

export const suicideAgeRecords = readRows(SUICIDE_AGE_CSV_PATH, AGE_COLUMNS) as SuicideAgeRecord[];
export const vitalSuicideRecords = readRows(VITAL_SUICIDE_CSV_PATH, VITAL_COLUMNS) as VitalSuicideRecord[];

export const suicideAgeBands = ["合計", "0-19歳", "20-29歳", "30-39歳", "40-49歳", "50-59歳", "60歳以上"] as const;
export const vitalAgeBands = ["0-19歳", "20-29歳", "30-39歳", "40-49歳", "50-59歳", "60歳以上"] as const;
export const rateYears = [1995, 2000, 2005, 2010, ...Array.from({ length: 12 }, (_, i) => 2013 + i)] as const;

export const vitalRateRecords = vitalSuicideRecords.filter(
  (record) => rateYears.includes(Number(record.year) as (typeof rateYears)[number]) &&
    vitalAgeBands.includes(record.age_band as (typeof vitalAgeBands)[number]) && record.rate_per_100k !== "",
);
