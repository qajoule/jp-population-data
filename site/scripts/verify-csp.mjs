import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { contentSecurityPolicy } from "../src/csp-policy.mjs";

const root = new URL("../", import.meta.url);
const distIndex = new URL("dist/index.html", root);
const distHeaders = new URL("dist/_headers", root);
const publicHeaders = new URL("public/_headers", root);

function parsePolicy(policy) {
  return new Map(policy.split(";").map((directive) => directive.trim()).filter(Boolean).map((directive) => {
    const [name, ...sources] = directive.split(/\s+/);
    return [name, new Set(sources)];
  }));
}

function extractMetaPolicy(html) {
  const meta = [...html.matchAll(/<meta\b([^>]*)>/gi)].find((match) => attribute(match[1], "http-equiv")?.toLowerCase() === "content-security-policy");
  return meta && attribute(meta[1], "content");
}

function extractHeaderPolicy(headers) {
  return headers.match(/^\s*Content-Security-Policy:\s*(.+)$/im)?.[1].trim();
}

function policyMatchesSharedSource(headers) {
  return extractHeaderPolicy(headers) === contentSecurityPolicy;
}

function elements(html, tag) {
  return [...html.matchAll(new RegExp(`<${tag}\\b([^>]*)>([\\s\\S]*?)<\\/${tag}>`, "gi"))];
}

function attribute(attributes, name) {
  return attributes.match(new RegExp(`\\b${name}="([^"]*)"`, "i"))?.[1]
    ?? attributes.match(new RegExp(`\\b${name}='([^']*)'`, "i"))?.[1];
}

function sha256(value) {
  return `sha256-${createHash("sha256").update(value).digest("base64")}`;
}

function contentMatchesHash(content, hash) {
  const match = /^sha(256|384|512)-/.exec(hash);
  return match && hash === `sha${match[1]}-${createHash(`sha${match[1]}`).update(content).digest("base64")}`;
}

function resourceAllowed(source, policy) {
  return source.startsWith("/") && policy.has("'self'");
}

function hashes(policy, directive) {
  return [...(policy?.get(directive) ?? [])]
    .filter((source) => /^'sha(256|384|512)-/.test(source))
    .map((source) => source.slice(1, -1));
}

function validate(html, headers, sourceHeaders = headers) {
  const failures = [];
  const metaPolicy = extractMetaPolicy(html);
  const headerPolicy = extractHeaderPolicy(headers);
  const meta = metaPolicy && parsePolicy(metaPolicy);
  const header = headerPolicy && parsePolicy(headerPolicy);
  const scripts = elements(html, "script");
  const inlineScripts = scripts.filter((script) => !attribute(script[1], "src"));
  const styles = elements(html, "style");
  const stylesheets = [...html.matchAll(/<link\b([^>]*)>/gi)].filter((match) => attribute(match[1], "rel")?.toLowerCase() === "stylesheet");

  if (!metaPolicy || !headerPolicy) failures.push("policy_presence");
  if (metaPolicy !== contentSecurityPolicy || !policyMatchesSharedSource(headers) || !policyMatchesSharedSource(sourceHeaders)) failures.push("shared_policy");
  if (!meta?.get("default-src")?.has("'none'") || !header?.get("default-src")?.has("'none'")) failures.push("default_src_none");
  if (!meta?.get("connect-src")?.has("'none'") || !header?.get("connect-src")?.has("'none'")) failures.push("connect_src_none");

  const directiveNames = new Set([...(meta?.keys() ?? []), ...(header?.keys() ?? [])]);
  const disagreements = [...directiveNames].filter((name) => {
    const left = meta?.get(name) ?? new Set();
    const right = header?.get(name) ?? new Set();
    return left.size !== right.size || [...left].some((source) => !right.has(source));
  });
  if (directiveNames.size === 0 || disagreements.length > 0) failures.push("policy_agreement");

  const scriptPolicy = meta?.get("script-src") ?? new Set();
  const stylePolicy = meta?.get("style-src") ?? new Set();
  const blockedScripts = scripts.filter((script) => {
    const src = attribute(script[1], "src");
    return src ? !resourceAllowed(src, scriptPolicy) : !scriptPolicy.has(`'${sha256(script[2])}'`);
  });
  const blockedStyles = styles.filter((style) => !stylePolicy.has(`'${sha256(style[2])}'`));
  const blockedStylesheets = stylesheets.filter((stylesheet) => !resourceAllowed(attribute(stylesheet[1], "href") ?? "", stylePolicy));
  if (scripts.length === 0 || styles.length + stylesheets.length === 0 || blockedScripts.length > 0 || blockedStyles.length > 0 || blockedStylesheets.length > 0) failures.push("resource_authorization");

  const inlineContents = {
    "script-src": inlineScripts.map((script) => script[2]),
    "style-src": styles.map((style) => style[2]),
  };
  const unmatchedHashes = [
    ["meta", meta],
    ["header", header],
  ].flatMap(([layer, policy]) => ["script-src", "style-src"].flatMap((directive) =>
    hashes(policy, directive)
      .filter((hash) => !inlineContents[directive].some((content) => contentMatchesHash(content, hash)))
      .map((hash) => ({ layer, directive, hash })),
  ));
  if (unmatchedHashes.length > 0) failures.push("hash_matches_inline_content");

  return {
    failures,
    measurements: {
      documents: 1,
      directives: directiveNames.size,
      scripts: scripts.length,
      inlineScripts: inlineScripts.length,
      inlineStyles: styles.length,
      stylesheets: stylesheets.length,
      scriptHashes: new Set([...hashes(meta, "script-src"), ...hashes(header, "script-src")]).size,
      styleHashes: new Set([...hashes(meta, "style-src"), ...hashes(header, "style-src")]).size,
      blockedScripts: blockedScripts.length,
      blockedInlineStyles: blockedStyles.length,
      blockedStylesheets: blockedStylesheets.length,
      disagreements: disagreements.length,
    },
    unmatchedHashes,
  };
}

function report(result, label) {
  const { measurements } = result;
  console.log(`${label}: documents=${measurements.documents} directives=${measurements.directives} scripts=${measurements.scripts} inline_scripts=${measurements.inlineScripts} inline_styles=${measurements.inlineStyles} stylesheets=${measurements.stylesheets}`);
  console.log(`${label}: script_src_hashes=${measurements.scriptHashes} style_src_hashes=${measurements.styleHashes}`);
  console.log(`${label}: blocked_scripts=${measurements.blockedScripts} blocked_inline_styles=${measurements.blockedInlineStyles} blocked_stylesheets=${measurements.blockedStylesheets} disagreements=${measurements.disagreements}`);
  for (const { layer, directive, hash } of result.unmatchedHashes) console.log(`${label}: unmatched_hash layer=${layer} directive=${directive} hash=${hash}`);
  if (measurements.inlineScripts === 0 && measurements.inlineStyles === 0 && measurements.scriptHashes === 0 && measurements.styleHashes === 0) console.log(`${label}: expected_zero_inline_content_and_hashes`);
  if (result.failures.length > 0) console.log(`${label}: failed_assertions=${result.failures.join(",")}`);
  console.log(`${label}: ${result.failures.length === 0 ? "PASS" : `FAIL ${result.failures.join(",")}`}`);
}

function fixture(policy, body = '<script src="/app.js"></script><link rel="stylesheet" href="/app.css">') {
  return {
    html: `<meta http-equiv="content-security-policy" content="${policy}">${body}`,
    headers: `/*\n  Content-Security-Policy: ${policy}\n`,
  };
}

function selfTest() {
  const policy = "default-src 'none'; connect-src 'none'; script-src 'self'; style-src 'self'";
  const cases = [
    ["policy_presence", { html: "", headers: "" }],
    ["shared_policy", fixture(policy)],
    ["connect_src_none", fixture(policy.replace("connect-src 'none'", "connect-src 'self'"))],
    ["policy_agreement", { ...fixture(policy), headers: fixture(policy.replace("default-src 'none'; ", "")).headers }],
    ["resource_authorization", fixture(policy, '<script src="https://example.invalid/app.js"></script><style>body{color:red}</style>')],
    ["zero_denominator", fixture(policy, "")],
    ["hash_matches_inline_content", fixture(`${policy}; script-src 'self' 'sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='`)],
  ];
  let failed = false;
  for (const [name, input] of cases) {
    const result = validate(input.html, input.headers);
    const observed = result.failures.includes(name) || (name === "zero_denominator" && result.failures.includes("resource_authorization"));
    console.log(`self_test_${name}: ${observed ? "EXPECTED_FAIL" : "FAIL"}`);
    failed ||= !observed;
  }
  if (failed) throw new Error("CSP self-test did not fail every assertion intentionally");
}

const isSelfTest = process.argv.includes("--self-test");
if (isSelfTest) {
  selfTest();
} else {
  const [html, headers, sourceHeaders] = await Promise.all([readFile(distIndex, "utf8"), readFile(distHeaders, "utf8"), readFile(publicHeaders, "utf8")]);
  const result = validate(html, headers, sourceHeaders);
  report(result, "csp");
  if (result.failures.length > 0) process.exitCode = 1;
  selfTest();
}

export { validate };
