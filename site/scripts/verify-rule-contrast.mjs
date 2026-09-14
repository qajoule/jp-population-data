import http from "node:http";
import { mkdtemp, rm } from "node:fs/promises";
import { createReadStream, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const distRoot = path.join(siteRoot, "dist");
const browserCandidates = process.platform === "win32"
  ? [process.env.SITE_BROWSER, "C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe", "C:/Program Files/Microsoft/Edge/Application/msedge.exe"]
  : [process.env.SITE_BROWSER, "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"];

function contentType(filePath) {
  return new Map([[".css", "text/css; charset=utf-8"], [".html", "text/html; charset=utf-8"], [".js", "text/javascript; charset=utf-8"], [".svg", "image/svg+xml"]]).get(path.extname(filePath)) ?? "application/octet-stream";
}

function startServer() {
  const server = http.createServer((request, response) => {
    const pathname = decodeURIComponent(new URL(request.url ?? "/", "http://localhost").pathname);
    const requested = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
    const filePath = path.resolve(distRoot, requested);
    if (!(filePath.startsWith(`${distRoot}${path.sep}`) || filePath === distRoot) || !existsSync(filePath)) return response.writeHead(404).end();
    response.writeHead(200, { "content-type": contentType(filePath) });
    createReadStream(filePath).pipe(response);
  });
  return new Promise((resolve, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", () => resolve(server)); });
}

async function json(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Chromium endpoint failed: ${response.status}`);
  return response.json();
}

async function browserStartupFailure(launch, reason) {
  const status = await Promise.race([
    launch.closed,
    new Promise((resolve) => setTimeout(() => resolve({ code: launch.browser.exitCode, signal: launch.browser.signalCode }), 0)),
  ]);
  const exitStatus = launch.spawnError
    ? "exit_code=unavailable signal=unavailable"
    : status.code !== null
    ? `exit_code=${status.code}`
    : status.signal !== null
      ? `signal=${status.signal}`
      : "exit_code=running signal=none";
  const stderr = launch.stderr || "(no stderr captured)";
  return `${reason}; binary=${launch.command}; ${exitStatus}; Chromium stderr:\n${stderr}`;
}

async function waitForDebugging(port, launch) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (launch.spawnError) throw new Error(await browserStartupFailure(launch, `Chromium could not start: ${launch.spawnError.message}`));
    if (launch.browser.exitCode !== null || launch.browser.signalCode !== null) throw new Error(await browserStartupFailure(launch, "Chromium exited before exposing its debugging endpoint"));
    try { return await json(`http://127.0.0.1:${port}/json/version`); } catch { await new Promise((resolve) => setTimeout(resolve, 50)); }
  }
  throw new Error(await browserStartupFailure(launch, "Chromium did not expose its debugging endpoint"));
}

async function cdp(webSocketDebuggerUrl) {
  const socket = new WebSocket(webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
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
      return new Promise((resolve, reject) => pending.set(id, (message) => message.error ? reject(new Error(message.error.message)) : resolve(message.result)));
    },
    close() { socket.close(); },
  };
}

const measureExpression = `(() => {
  const parseColor = (value) => {
    const match = value.match(/^rgba?\\(([^)]+)\\)$/);
    if (!match) return null;
    const [red, green, blue, alpha = 1] = match[1].split(',').map(Number);
    return [red, green, blue, alpha];
  };
  const composite = (foreground, background) => {
    const alpha = foreground[3] + background[3] * (1 - foreground[3]);
    if (!alpha) return [0, 0, 0, 0];
    return [0, 1, 2].map((channel) => (foreground[channel] * foreground[3] + background[channel] * background[3] * (1 - foreground[3])) / alpha).concat(alpha);
  };
  const paintedBackground = (element) => {
    const ancestors = [];
    for (let current = element; current; current = current.parentElement) ancestors.unshift(current);
    return ancestors.reduce((background, current) => composite(parseColor(getComputedStyle(current).backgroundColor) ?? [0, 0, 0, 0], background), [255, 255, 255, 1]).slice(0, 3);
  };
  const structural = [
    ["site-header", ".site-header", "borderBottomColor"],
    ["ledger-list", ".ledger-list", "borderTopColor"],
    ["mock-figure", ".mock-figure", "borderBottomColor"],
    ["mock-figure-heading", ".mock-figure h2", "borderBottomColor"],
  ].flatMap(([name, selector, property]) => [...document.querySelectorAll(selector)].map((element) => ({ name, color: parseColor(getComputedStyle(element)[property])?.slice(0, 3), background: paintedBackground(element) })));
  const gridlines = [...document.querySelectorAll(".plot svg [data-gridline]")].map((element) => ({ name: "gridline", color: parseColor(getComputedStyle(element).stroke)?.slice(0, 3), background: paintedBackground(element) }));
  return { structural, gridlines };
})()`;

function luminance([red, green, blue]) {
  return [red, green, blue].map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
  }).reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0);
}

function contrast(color, background) {
  if (!color || !background) throw new Error("Computed color was unavailable");
  const [first, second] = [luminance(color), luminance(background)].sort((left, right) => right - left);
  return (first + 0.05) / (second + 0.05);
}

function assertTheme(theme, observation) {
  const measured = observation.structural.length + observation.gridlines.length;
  if (!measured) throw new Error(`${theme}: measured=0`);
  if (!observation.structural.length) throw new Error(`${theme}: no structural rules were measured`);
  if (!observation.gridlines.length) throw new Error(`${theme}: no gridlines were measured`);
  const structural = observation.structural.map((item) => ({ ...item, contrast: contrast(item.color, item.background) }));
  const gridlines = observation.gridlines.map((item) => ({ ...item, contrast: contrast(item.color, item.background) }));
  const faintStructural = structural.find((item) => item.contrast < 3);
  if (faintStructural) throw new Error(`${theme}: ${faintStructural.name} contrast=${faintStructural.contrast.toFixed(2)} is below 3:1`);
  const strongGridline = gridlines.find((item) => item.contrast >= 3);
  if (strongGridline) throw new Error(`${theme}: gridline contrast=${strongGridline.contrast.toFixed(2)} is not below 3:1`);
  return { measured, structural, gridlines };
}

function browserCommand() {
  for (const candidate of browserCandidates.filter(Boolean)) {
    if (candidate.includes(path.sep) && !existsSync(candidate)) continue;
    return candidate;
  }
  throw new Error("No Chromium browser found. Set SITE_BROWSER to a Chromium executable.");
}

function browserArguments(debugPort, userDataDir) {
  return [
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${userDataDir}`,
    "about:blank",
  ];
}

function launchBrowser(command, args) {
  let browser;
  try {
    browser = spawn(command, args, { stdio: ["ignore", "ignore", "pipe"] });
  } catch (error) {
    return {
      browser: { exitCode: null, signalCode: null },
      command,
      stderr: "",
      spawnError: error,
      closed: Promise.resolve({ code: null, signal: null }),
    };
  }
  let stderr = "";
  let spawnError = null;
  browser.stderr?.setEncoding("utf8");
  browser.stderr?.on("data", (chunk) => { stderr += chunk; });
  browser.once("error", (error) => { spawnError = error; });
  const closed = new Promise((resolve) => {
    browser.once("close", (code, signal) => resolve({ code, signal }));
  });
  return {
    browser,
    command,
    get stderr() { return stderr.trim(); },
    get spawnError() { return spawnError; },
    closed,
  };
}

async function observe(page, url, theme) {
  await page.call("Emulation.setEmulatedMedia", { media: "", features: [{ name: "prefers-color-scheme", value: "light" }] });
  await page.call("Page.navigate", { url });
  await page.call("Runtime.evaluate", { expression: "new Promise((resolve) => { if (document.readyState === 'complete') resolve(); else addEventListener('load', resolve, { once: true }); })", awaitPromise: true, returnByValue: true });
  await page.call("Runtime.evaluate", { expression: `document.documentElement${theme === "dark" ? ".setAttribute('data-theme', 'dark')" : ".removeAttribute('data-theme')"}`, returnByValue: true });
  const { result } = await page.call("Runtime.evaluate", { expression: measureExpression, returnByValue: true });
  return result.value;
}

async function cleanupProfile(userDataDir, remove = rm) {
  try {
    await remove(userDataDir, { recursive: true, force: true });
  } catch (error) {
    console.warn(`rule_contrast: cleanup warning ${error instanceof Error ? error.message : String(error)}`);
  }
}

async function run() {
  if (!existsSync(path.join(distRoot, "index.html"))) throw new Error(`Built site is missing: ${distRoot}`);
  const server = await startServer();
  const address = server.address();
  const userDataDir = await mkdtemp(path.join(tmpdir(), "j-shrinking-rule-contrast-"));
  const debugPort = 9229 + Math.floor(Math.random() * 1000);
  let launch;
  try {
    const command = browserCommand();
    const args = browserArguments(debugPort, userDataDir);
    console.log(`rule_contrast: Chromium binary=${command} flags=${args.filter((argument) => argument.startsWith("--")).join(" ")}`);
    launch = launchBrowser(command, args);
    await waitForDebugging(debugPort, launch);
    const pages = await json(`http://127.0.0.1:${debugPort}/json/list`);
    const pageEntry = pages.find((entry) => entry.type === "page");
    if (!pageEntry?.webSocketDebuggerUrl) throw new Error("Chromium exposed no debuggable page");
    const page = await cdp(pageEntry.webSocketDebuggerUrl);
    try {
      let measured = 0;
      for (const theme of ["light", "dark"]) {
        const result = assertTheme(theme, await observe(page, `http://127.0.0.1:${address.port}/`, theme));
        measured += result.measured;
        const structuralMinimum = Math.min(...result.structural.map((item) => item.contrast));
        const gridlineMaximum = Math.max(...result.gridlines.map((item) => item.contrast));
        console.log(`rule_contrast: theme=${theme} path=${theme === "dark" ? "data-theme=dark" : "no-data-theme with prefers-color-scheme=light"} structural_min=${structuralMinimum.toFixed(2)} gridline_max=${gridlineMaximum.toFixed(2)} measured=${result.measured}`);
      }
      if (!measured) throw new Error("measured=0");
      console.log(`rule_contrast: PASS measured=${measured} prefers-color-scheme-dark=not-covered`);
    } finally { page.close(); }
  } finally {
    launch?.browser.kill?.();
    await new Promise((resolve) => server.close(resolve));
    await cleanupProfile(userDataDir);
  }
}

async function selfTestCleanupFailure() {
  let assertionsPassed = false;
  try {
    assertTheme("light", { structural: [{ name: "fixture", color: [0, 0, 0], background: [255, 255, 255] }], gridlines: [{ name: "gridline", color: [180, 180, 180], background: [255, 255, 255] }] });
    assertionsPassed = true;
  } finally {
    await cleanupProfile("fixture", async () => { throw new Error("EBUSY: fixture lockfile"); });
  }
  if (!assertionsPassed) throw new Error("cleanup self-test assertions did not pass");
  console.log("rule_contrast: self-test cleanup-failure PASS expected_exit=0");
}

async function selfTestAssertionFailure() {
  try {
    assertTheme("light", { structural: [{ name: "fixture", color: [100, 100, 100], background: [100, 100, 100] }], gridlines: [{ name: "gridline", color: [180, 180, 180], background: [255, 255, 255] }] });
  } finally {
    await cleanupProfile("fixture", async () => {});
  }
}

const selfTests = new Map([
  ["--self-test-structural-light", () => assertTheme("light", { structural: [{ name: "fixture", color: [100, 100, 100], background: [100, 100, 100] }], gridlines: [{ name: "gridline", color: [180, 180, 180], background: [255, 255, 255] }] })],
  ["--self-test-structural-dark", () => assertTheme("dark", { structural: [{ name: "fixture", color: [30, 30, 30], background: [30, 30, 30] }], gridlines: [{ name: "gridline", color: [60, 60, 60], background: [13, 13, 13] }] })],
  ["--self-test-gridline-light", () => assertTheme("light", { structural: [{ name: "fixture", color: [0, 0, 0], background: [255, 255, 255] }], gridlines: [{ name: "gridline", color: [0, 0, 0], background: [255, 255, 255] }] })],
  ["--self-test-gridline-dark", () => assertTheme("dark", { structural: [{ name: "fixture", color: [255, 255, 255], background: [13, 13, 13] }], gridlines: [{ name: "gridline", color: [255, 255, 255], background: [13, 13, 13] }] })],
  ["--self-test-measured-zero", () => assertTheme("light", { structural: [], gridlines: [] })],
  ["--self-test-no-structural-rules", () => assertTheme("light", { structural: [], gridlines: [{ name: "gridline", color: [180, 180, 180], background: [255, 255, 255] }] })],
  ["--self-test-no-gridlines", () => assertTheme("light", { structural: [{ name: "fixture", color: [0, 0, 0], background: [255, 255, 255] }], gridlines: [] })],
  ["--self-test-unavailable-color", () => assertTheme("light", { structural: [{ name: "fixture", color: null, background: [255, 255, 255] }], gridlines: [{ name: "gridline", color: [180, 180, 180], background: [255, 255, 255] }] })],
]);

const selfTest = process.argv.includes("--self-test-cleanup-failure")
  ? selfTestCleanupFailure
  : process.argv.includes("--self-test-assertion-failure")
    ? selfTestAssertionFailure
    : [...selfTests.entries()].find(([argument]) => process.argv.includes(argument))?.[1];
try {
  await (selfTest ?? run)();
} catch (error) {
  console.error(`rule_contrast: FAIL ${error.message}`);
  process.exitCode = 1;
}
