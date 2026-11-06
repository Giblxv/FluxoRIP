// Synthetic regression contract for decorative transition suppression.
// No DOM, network, printer, ICC or proprietary assets required.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const css = readFileSync(new URL("./cmyk-cartoon.css", import.meta.url), "utf8");
const media = css.lastIndexOf("@media (prefers-reduced-motion: reduce)");
assert.ok(media >= 0, "reduced-motion rule missing");
const reduced = css.slice(media);
const manual = reduced.indexOf("html.motion-off .top-tab");
assert.ok(manual > 0, "manual motion-off rule missing");
const blocks = [reduced.slice(0, manual), reduced.slice(manual)];
for (const [i, block] of blocks.entries()) {
  for (const selector of [".top-tab", ".action", "#primary-btn", ".metric", ".panel", ".task-card", "#toast", ".motion-switch"]) {
    assert.ok(block.includes(selector), `missing selector ${selector} in mode ${i}`);
  }
  assert.match(block, /animation:\s*none\s*!important/);
  assert.match(block, /transition:\s*none\s*!important/);
  assert.match(block, /scroll-behavior:\s*auto\s*!important/);
}
assert.match(css, /:focus-visible\s*\{[^}]*outline:/s, "keyboard focus must remain visible");
console.log("PASS: system and manual reduced-motion suppress decorative transitions");
