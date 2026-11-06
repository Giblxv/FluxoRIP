// Synthetic contract: forced-colors remains usable when gradients and shadows vanish.
// No browser, backend, printer, proprietary samples or external packages required.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const css = readFileSync(new URL("./cmyk-cartoon.css", import.meta.url), "utf8");
const start = css.indexOf("@media (forced-colors: active)");
assert.ok(start >= 0, "Windows high-contrast media query must exist");
const forced = css.slice(start);
for (const selector of [
  ".top-tab.active", ".top-tab.active::after",
  ".action.primary", ".page-header .eyebrow::before",
  ".lane.drag-over", "#toast:not(:empty)", ":focus-visible"
]) {
  assert.ok(forced.includes(selector), "missing forced-color state: " + selector);
}
for (const token of ["Highlight", "CanvasText", "ButtonFace", "ButtonText"]) {
  assert.ok(forced.includes(token), "must use system color: " + token);
}
assert.match(forced, /\.top-tab\.active::after\s*\{\s*display:\s*none\s*!important/);
assert.match(forced, /\.top-tab\.active\s*\{[^}]*border-bottom:\s*3px solid Highlight/s);
assert.match(forced, /:focus-visible\s*\{[^}]*outline:\s*3px solid Highlight/s);
assert.match(forced, /\.action\.primary::before, #primary-btn::before\s*\{\s*display:\s*none/s);
console.log("PASS: Windows forced-colors state and focus CSS contract");
