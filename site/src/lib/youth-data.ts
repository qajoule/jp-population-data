import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export const CSV_PATH = "data/derived/youth_suicide_rate.csv";

const EXPECTED_COLUMNS = [
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
] as const;

export type YouthRecord = Record<(typeof EXPECTED_COLUMNS)[number], string>;

function failValidation(message: string): never {
  throw new Error(`${CSV_PATH}: ${message}`);
}

function parseCsv(): YouthRecord[] {
  const csvPath = resolve(process.cwd(), "..", CSV_PATH);
  const lines = readFileSync(csvPath, "utf8").trimEnd().split("\n");
  const header = lines.shift()?.replace(/^\uFEFF/, "").split(",");

  if (!header || header.join(",") !== EXPECTED_COLUMNS.join(",")) {
    failValidation("列名または列順が要件と一致しません");
  }
  if (lines.length !== 31) {
    failValidation(`データ行数は31行である必要があります: ${lines.length}`);
  }

  const records = lines.map((line, index) => {
    const values = line.replace(/\r$/, "").split(",");
    if (values.length !== EXPECTED_COLUMNS.length || values.some((value) => value === "")) {
      failValidation(`${index + 2}行目に空セルまたは列数不一致があります`);
    }
    return Object.fromEntries(EXPECTED_COLUMNS.map((column, columnIndex) => [column, values[columnIndex]])) as YouthRecord;
  });

  records.forEach((record, index) => {
    if (record.year !== String(1995 + index)) {
      failValidation("年が1995年から2025年まで連続していません");
    }
  });

  return records;
}

export const youthRecords = parseCsv();

export function firstChange(column: keyof YouthRecord) {
  const changedRecord = youthRecords.find((record, index) => index > 0 && record[column] !== youthRecords[index - 1][column]);
  if (!changedRecord) {
    failValidation(`${column} の区分変化がありません`);
  }
  return changedRecord;
}
