import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseHTML } from 'linkedom';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const builtPage = path.join(siteRoot, 'dist', 'index.html');

function keyOf(figureId, element) {
  return [
    figureId,
    element.getAttribute('data-csv-year') ?? '',
    element.getAttribute('data-csv-series-label') ?? '',
    element.getAttribute('data-csv-metric') ?? '',
  ].join('|');
}

function describeKey(figureId, element) {
  return `figure=${figureId} year=${element.getAttribute('data-csv-year') ?? ''} series-label=${element.getAttribute('data-csv-series-label') ?? ''} metric=${element.getAttribute('data-csv-metric') ?? ''}`;
}

function checkPage(html) {
  const { document } = parseHTML(html);
  let compared = 0;
  const mismatches = [];
  const tables = [...document.querySelectorAll('table[data-figure-table]')];
  tables.forEach((table) => {
    const figureId = table.getAttribute('data-figure-table') ?? 'unknown';
    const svg = table.closest('figure')?.querySelector('svg[data-figure-id]');
    if (!svg) throw new Error(`Figure table has no sibling SVG: ${figureId}`);
    const circles = new Map();
    svg.querySelectorAll('circle[data-csv-value]').forEach((circle) => {
      const key = keyOf(figureId, circle);
      const matches = circles.get(key) ?? [];
      matches.push(circle);
      circles.set(key, matches);
    });
    table.querySelectorAll('td[data-csv-value]').forEach((cell) => {
      const matches = circles.get(keyOf(figureId, cell)) ?? [];
      if (matches.length !== 1) {
        mismatches.push({ figureId, key: describeKey(figureId, cell), tableValue: cell.getAttribute('data-csv-value'), circleValue: matches.length === 0 ? 'missing circle' : `ambiguous circles=${matches.length}` });
        return;
      }
      const [circle] = matches;
      compared += 1;
      const tableValue = cell.getAttribute('data-csv-value');
      const circleValue = circle.getAttribute('data-csv-value');
      if (tableValue !== circleValue) mismatches.push({ figureId, key: describeKey(figureId, cell), tableValue, circleValue });
    });
  });
  if (tables.length === 0) throw new Error('Compared zero figures');
  if (mismatches.length) throw new Error(mismatches.map((item) => `${item.key} table=${item.tableValue} circle=${item.circleValue}`).join('\n'));
  if (compared === 0) throw new Error('Compared zero table cells');
  return { compared, figures: tables.length };
}

async function run() {
  if (process.argv.includes('--self-test')) {
    const mismatchFixture = '<figure><svg data-figure-id="fixture"><circle data-csv-series-id="a" data-csv-series-label="series a" data-csv-year="2020" data-csv-metric="rate_per_100k" data-csv-value="1.2" /></svg><table data-figure-table="fixture"><td data-csv-series-id="a" data-csv-series-label="series a" data-csv-year="2020" data-csv-metric="rate_per_100k" data-csv-value="9.9">9.9</td></table></figure>';
    const ambiguityFixture = '<figure><svg data-figure-id="fixture"><circle data-csv-series-id="shared" data-csv-series-label="series a" data-csv-year="2020" data-csv-metric="count" data-csv-value="1" /><circle data-csv-series-id="shared" data-csv-series-label="series a" data-csv-year="2020" data-csv-metric="count" data-csv-value="1" /></svg><table data-figure-table="fixture"><td data-csv-series-id="shared" data-csv-series-label="series a" data-csv-year="2020" data-csv-metric="count" data-csv-value="1">1</td></table></figure>';
    const fixtures = [
      ['intentional mismatch', mismatchFixture, 'table=9.9 circle=1.2'],
      ['ambiguous key', ambiguityFixture, 'ambiguous circles=2'],
    ];
    for (const [name, fixture, expectedMessage] of fixtures) {
      try {
        checkPage(fixture);
      } catch (error) {
        if (error.message.includes(expectedMessage)) continue;
        throw new Error(`Self-test detected ${name}, but reported an unexpected failure: ${error.message}`);
      }
      throw new Error(`Self-test did not detect the ${name}`);
    }
    console.log('figure_table_values: PASS self-test detected intentional mismatch and ambiguous key');
    return;
  }
  const { compared, figures } = checkPage(await readFile(builtPage, 'utf8'));
  console.log(`figure_table_values: PASS compared=${compared} figures=${figures}`);
}

run().catch((error) => { console.error(`figure_table_values: FAIL ${error.message}`); process.exitCode = 1; });
