// Static UX guardrails: checks touch target, focus and reduced-motion contracts.
// No browser, API, printer or proprietary sample files are needed.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const css = readFileSync(new URL("./cmyk-cartoon.css", import.meta.url), "utf8");
const html = readFileSync(new URL("./index.html", import.meta.url), "utf8");
assert.match(html, /\/static\/cmyk-cartoon\.css\?v=\d+/);
assert.match(css, /@media\s*\(pointer:\s*coarse\)/);
const coarse = css.slice(css.indexOf("@media (pointer: coarse)"));
assert.match(coarse, /\.top-tab\s*\{[^}]*min-height:\s*44px/s);
assert.match(coarse, /\.fleet-item\s*\{[^}]*min-height:\s*48px/s);
assert.match(coarse, /\.action,\s*\.mini-btn[^}]*min-height:\s*44px/s);
assert.match(css, /:focus-visible\s*\{\s*outline:\s*3px solid var\(--cartoon-y\)/);
assert.match(css, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
assert.match(css, /html\.motion-off/);
assert.match(css, /\.task-card\.dragging\s*\{[^}]*animation:\s*none\s*!important/s);
const touchStart = css.indexOf("@media (pointer: coarse)");
const touchEnd = css.indexOf("/* Focus must remain visible", touchStart);
const touchRules = css.slice(touchStart, touchEnd);
assert.match(touchRules,
  /\.top-tab:active:not\(:disabled\)[^{}]*\.action\.primary:active:not\(:disabled\),\s*#primary-btn:active:not\(:disabled\)\s*\{\s*transform:\s*none;/s,
  "touch press states must not move or shrink controls");
console.log("PASS: CMYK touch targets, keyboard focus, reduced motion, drag stability");
