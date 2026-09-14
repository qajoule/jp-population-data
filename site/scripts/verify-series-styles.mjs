import fs from "node:fs";

const source = fs.readFileSync(new URL("../src/lib/figures.ts", import.meta.url), "utf8");
const styles = new Set([...source.matchAll(/^  "([^"]+)": \{ sourceColor:/gm)].map(([, name]) => name));
const declaration = source.match(/export const renderedSeriesByFigure = \{([\s\S]*?)\n\} as const;/);

if (!declaration) throw new Error("renderedSeriesByFigure が見つかりません");

const figureEntries = [...declaration[1].matchAll(/^  "[^"]+": \[([^\]]*)\],?$/gm)];
const renderedSeries = new Set(
  figureEntries.flatMap(([, entries]) => [...entries.matchAll(/"([^"]+)"/g)].map(([, name]) => name)),
);
const missing = [...renderedSeries].filter((name) => !styles.has(name));

console.log(`seriesStyles coverage: ${renderedSeries.size - missing.length}/${renderedSeries.size} distinct series across ${figureEntries.length} figures`);
if (missing.length) {
  console.error(`missing seriesStyles entries: ${missing.join(", ")}`);
  process.exitCode = 1;
}
