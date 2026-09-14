import http from "node:http";
import { mkdtemp, rm } from "node:fs/promises";
import { createReadStream, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

// Test both sides of the two responsive layout transitions in the specification.
const widths = [375, 400, 401, 560, 561, 683, 684, 1024];
const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const distRoot = path.join(siteRoot, "dist");
const browserCandidates = process.platform === "win32"
  ? [
      process.env.SITE_BROWSER,
      "C:/Program Files/Google/Chrome/Application/chrome.exe",
      "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
      "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    ]
  : [process.env.SITE_BROWSER, "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"];

function contentType(filePath) {
  return new Map([
    [".css", "text/css; charset=utf-8"], [".html", "text/html; charset=utf-8"],
    [".js", "text/javascript; charset=utf-8"], [".svg", "image/svg+xml"],
  ]).get(path.extname(filePath)) ?? "application/octet-stream";
}

function safeFilePath(requestUrl) {
  const pathname = decodeURIComponent(new URL(requestUrl, "http://localhost").pathname);
  const requested = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const filePath = path.resolve(distRoot, requested);
  return filePath.startsWith(`${distRoot}${path.sep}`) || filePath === distRoot ? filePath : null;
}

function startServer() {
  const server = http.createServer((request, response) => {
    const filePath = safeFilePath(request.url ?? "/");
    if (!filePath || !existsSync(filePath)) {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, { "content-type": contentType(filePath) });
    createReadStream(filePath).pipe(response);
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

async function json(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Chromium endpoint failed: ${response.status}`);
  return response.json();
}

async function waitForDebugging(port, browser) {
  const endpoint = `http://127.0.0.1:${port}/json/version`;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (browser.exitCode !== null) throw new Error(`Chromium exited before starting (code ${browser.exitCode})`);
    try { return await json(endpoint); } catch { await new Promise((resolve) => setTimeout(resolve, 50)); }
  }
  throw new Error("Chromium did not expose its debugging endpoint");
}

async function cdp(webSocketDebuggerUrl) {
  const socket = new WebSocket(webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  let nextId = 1;
  const pending = new Map();
  socket.addEventListener("message", ({ data }) => {
    const message = JSON.parse(data);
    const resolve = pending.get(message.id);
    if (resolve) { pending.delete(message.id); resolve(message); }
  });
  return {
    call(method, params = {}) {
      const id = nextId++;
      socket.send(JSON.stringify({ id, method, params }));
      return new Promise((resolve, reject) => {
        pending.set(id, (message) => message.error ? reject(new Error(message.error.message)) : resolve(message.result));
      });
    },
    close() { socket.close(); },
  };
}

const overflowExpression = `(() => {
  const documentWidth = document.documentElement.clientWidth;
  const documentScrollWidth = document.documentElement.scrollWidth;
  const isContainedByHorizontalOverflow = (element) => {
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
      if (["auto", "scroll", "hidden", "clip"].includes(getComputedStyle(parent).overflowX)) return true;
    }
    return false;
  };
  const offenders = [...document.querySelectorAll('*')].map((element) => {
    const rect = element.getBoundingClientRect();
    return { tag: element.tagName.toLowerCase(), id: element.id, className: typeof element.className === 'string' ? element.className : '', right: rect.right, width: rect.width, contained: isContainedByHorizontalOverflow(element) };
  }).filter((item) => item.right > documentWidth + 0.5 && !item.contained).sort((a, b) => b.right - a.right);
  const plots = [...document.querySelectorAll('.plot')].map((plot, index) => {
    const svg = plot.querySelector('svg');
    const plotRect = plot.getBoundingClientRect();
    const svgWidth = svg?.getBoundingClientRect().width ?? 0;
    const mustScroll = documentWidth < svgWidth - 0.5;
    const leftGap = plotRect.left;
    const rightGap = documentWidth - plotRect.right;
    return { index, id: plot.id, className: plot.className, left: plotRect.left, plotWidth: plotRect.width, leftGap, rightGap, svgWidth, scrollWidth: plot.scrollWidth, clientWidth: plot.clientWidth, overflowX: getComputedStyle(plot).overflowX, mustScroll };
  });
  const expectsNumberColumn = documentWidth >= 684;
  const numberColumnOutliers = [...document.querySelectorAll('.mock-figure')].map((figure, index) => {
    const style = getComputedStyle(figure);
    const labelStyle = getComputedStyle(figure, '::before');
    const firstColumn = Number.parseFloat(style.gridTemplateColumns.split(' ')[0]);
    const hasExpectedColumn = style.display === 'grid' && Math.abs(firstColumn - 58) <= 0.5;
    const hasNoColumn = style.display === 'block' && labelStyle.display === 'block';
    return { index, display: style.display, firstColumn, labelDisplay: labelStyle.display, expected: expectsNumberColumn ? '58px grid column' : 'no column with label above heading', valid: expectsNumberColumn ? hasExpectedColumn : hasNoColumn };
  }).filter((figure) => !figure.valid);
  const plotAlignmentReference = plots[0] ?? null;
  const plotAlignmentOutliers = plotAlignmentReference === null ? [{ reason: "no .plot elements were measured" }] : plots.filter((plot) => Math.abs(plot.left - plotAlignmentReference.left) > 0.5 || Math.abs(plot.plotWidth - plotAlignmentReference.plotWidth) > 0.5);
  const plotCenteringOutliers = plots.filter((plot) => Math.abs(plot.leftGap - plot.rightGap) > 0.5);
  const plotFailure = plots.find((plot) => plot.mustScroll && (!["auto", "scroll"].includes(plot.overflowX) || plot.scrollWidth <= plot.clientWidth + 0.5));
  return { documentWidth, documentScrollWidth, pageOverflow: documentScrollWidth > documentWidth + 0.5, offender: offenders[0] ?? null, plotFailure, numberColumnOutliers, plotAlignmentReference, plotAlignmentOutliers, plotCenteringOutliers };
})()`;

function formatPlot(plot) {
  const name = plot.id ? `#${plot.id}` : `[${plot.index}]`;
  return `.plot${name} left=${plot.left.toFixed(1)} width=${plot.plotWidth.toFixed(1)} left_gap=${plot.leftGap.toFixed(1)} right_gap=${plot.rightGap.toFixed(1)}`;
}

function assertObservation(width, observation) {
  if (!observation || typeof observation !== "object") throw new Error(`No layout observation was returned at ${width}px`);
  if (!Array.isArray(observation.plotAlignmentOutliers)) throw new Error(`Layout observation omitted plot alignment data at ${width}px`);
  if (!Array.isArray(observation.plotCenteringOutliers)) throw new Error(`Layout observation omitted plot centering data at ${width}px`);
  if (!Array.isArray(observation.numberColumnOutliers)) throw new Error(`Layout observation omitted number-column data at ${width}px`);
  if (observation.numberColumnOutliers.length) {
    const outliers = observation.numberColumnOutliers.map((figure) => `[${figure.index}] display=${figure.display} first_column=${Number.isNaN(figure.firstColumn) ? 'none' : `${figure.firstColumn}px`} label_display=${figure.labelDisplay} expected=${figure.expected}`).join('; ');
    throw new Error(`Number-column mismatch at ${width}px: ${outliers}`);
  }
  if (observation.plotAlignmentOutliers.length) {
    const reference = observation.plotAlignmentReference ? formatPlot(observation.plotAlignmentReference) : "none";
    const outliers = observation.plotAlignmentOutliers.map((plot) => plot.reason ?? formatPlot(plot)).join("; ");
    throw new Error(`Chart geometry mismatch at ${width}px: reference ${reference}; outliers ${outliers}`);
  }
  if (observation.plotCenteringOutliers.length) {
    const outliers = observation.plotCenteringOutliers.map(formatPlot).join("; ");
    throw new Error(`Chart centering mismatch at ${width}px: ${outliers}`);
  }
  if (observation.plotFailure) {
    const plot = observation.plotFailure;
    throw new Error(`Chart scroll container failed at ${width}px: .plot${plot.id ? `#${plot.id}` : `[${plot.index}]`} svg_width=${plot.svgWidth.toFixed(1)} plot_width=${plot.plotWidth.toFixed(1)} scroll_width=${plot.scrollWidth} client_width=${plot.clientWidth} overflow_x=${plot.overflowX}`);
  }
  if (observation.offender) {
    const offender = observation.offender;
    throw new Error(`Horizontal overflow at ${width}px: ${offender.tag}${offender.id ? `#${offender.id}` : ""}${offender.className ? `.${offender.className.trim().replaceAll(/\\s+/g, ".")}` : ""} right=${offender.right.toFixed(1)} document_width=${observation.documentWidth}`);
  }
  if (observation.pageOverflow) throw new Error(`Horizontal page overflow at ${width}px: scroll_width=${observation.documentScrollWidth} document_width=${observation.documentWidth}; no element-level offender was identified`);
}

function browserCommand() {
  for (const candidate of browserCandidates.filter(Boolean)) {
    if (candidate.includes(path.sep) && !existsSync(candidate)) continue;
    return candidate;
  }
  throw new Error("No Chromium browser found. Set SITE_BROWSER to a Chromium executable.");
}

async function run() {
  if (!existsSync(path.join(distRoot, "index.html"))) throw new Error(`Built site is missing: ${distRoot}`);
  const server = await startServer();
  const address = server.address();
  const userDataDir = await mkdtemp(path.join(tmpdir(), "j-shrinking-layout-"));
  const debugPort = 9229 + Math.floor(Math.random() * 1000);
  let browser;
  try {
    browser = spawn(browserCommand(), ["--headless=new", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${userDataDir}`, "about:blank"], { stdio: "ignore" });
    await waitForDebugging(debugPort, browser);
    const pages = await json(`http://127.0.0.1:${debugPort}/json/list`);
    const pageEntry = pages.find((entry) => entry.type === "page");
    if (!pageEntry?.webSocketDebuggerUrl) throw new Error("Chromium exposed no debuggable page");
    const page = await cdp(pageEntry.webSocketDebuggerUrl);
    try {
      let measuredWidths = 0;
      for (const width of widths) {
        await page.call("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: true });
        await page.call("Page.navigate", { url: `http://127.0.0.1:${address.port}/` });
        await page.call("Runtime.evaluate", { expression: "new Promise((resolve) => { if (document.readyState === 'complete') resolve(); else addEventListener('load', resolve, { once: true }); })", awaitPromise: true, returnByValue: true });
        await page.call("Runtime.evaluate", { expression: "document.fonts.ready", awaitPromise: true, returnByValue: true });
        const { result } = await page.call("Runtime.evaluate", { expression: overflowExpression, returnByValue: true });
        const observation = result.value;
        assertObservation(width, observation);
        measuredWidths += 1;
        console.log(`width=${width} document_width=${observation.documentWidth} scroll_width=${observation.documentScrollWidth} offender=${observation.offender ? observation.offender.tag : "none"}`);
      }
      if (measuredWidths !== widths.length) throw new Error(`Measured ${measuredWidths} of ${widths.length} required widths`);
      console.log(`responsive_layout: PASS widths=${widths.join(",")} measured=${measuredWidths}`);
    } finally { page.close(); }
  } finally {
    browser?.kill();
    await new Promise((resolve) => server.close(resolve));
    try {
      await rm(userDataDir, { recursive: true, force: true });
    } catch (error) {
      console.warn(`responsive_layout: cleanup warning ${error instanceof Error ? error.message : String(error)}`);
    }
  }
}

let verification;
if (process.argv.includes("--self-test-plot-scroll")) {
  verification = () => assertObservation(390, {
    plotAlignmentReference: { index: 0, id: "fixture", left: 0, plotWidth: 390 },
    plotAlignmentOutliers: [],
    plotCenteringOutliers: [],
    numberColumnOutliers: [],
    plotFailure: { index: 0, id: "fixture", svgWidth: 620, plotWidth: 390, scrollWidth: 390, clientWidth: 390, overflowX: "visible" },
  });
} else if (process.argv.includes("--self-test-plot-alignment")) {
  verification = () => assertObservation(390, {
    plotAlignmentReference: { index: 0, id: "reference", left: 0, plotWidth: 390, leftGap: 0, rightGap: 0 },
    plotAlignmentOutliers: [{ index: 1, id: "outlier", left: 58, plotWidth: 332, leftGap: 58, rightGap: 0 }],
    plotCenteringOutliers: [],
    numberColumnOutliers: [],
    plotFailure: null,
  });
} else if (process.argv.includes("--self-test-plot-centering")) {
  verification = () => assertObservation(390, {
    plotAlignmentReference: { index: 0, id: "reference", left: 0, plotWidth: 390, leftGap: 0, rightGap: 0 },
    plotAlignmentOutliers: [],
    plotCenteringOutliers: [{ index: 0, id: "off-centre", left: 58, plotWidth: 332, leftGap: 58, rightGap: 0 }],
    plotFailure: null,
    numberColumnOutliers: [],
  });
} else if (process.argv.includes("--self-test-number-column")) {
  verification = () => assertObservation(684, {
    plotAlignmentReference: { index: 0, id: "reference", left: 32, plotWidth: 1040, leftGap: 32, rightGap: 32 },
    plotAlignmentOutliers: [],
    plotCenteringOutliers: [],
    plotFailure: null,
    numberColumnOutliers: [{ index: 0, display: "grid", firstColumn: 57, labelDisplay: "block", expected: "58px grid column" }],
  });
} else {
  verification = run;
}

try {
  await verification();
} catch (error) {
  console.error(`responsive_layout: FAIL ${error.message}`);
  process.exitCode = 1;
}
