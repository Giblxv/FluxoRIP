// Structural accessibility smoke test; no browser, backend, or printer required.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const read = path => readFileSync(new URL(path, import.meta.url), "utf8");
const html = read("./management.html");
const app = read("./app.js");
const pages = ["projects", "art", "prints", "queue", "history",
               "printers", "stations", "scanner", "files"];
const tablist = html.match(/<div class="top-navigation" role="tablist"[\s\S]*?<\/div>/)?.[0];
assert.ok(tablist, "primary tablist must exist");
for (const page of pages) {
  const match = tablist.match(new RegExp('<button[^>]*data-page="' + page + '"[^>]*>'));
  assert.ok(match, "missing tab " + page);
  assert.match(match[0], new RegExp('id="tab-' + page + '"'));
  assert.match(match[0], /aria-controls="view"/);
  assert.match(match[0], /role="tab"/);
}
assert.equal((html.match(/role="tabpanel"/g) || []).length, 1,
  "only one dynamic workspace panel should be present");
assert.match(html, /id="view"[^>]*role="tabpanel"[^>]*aria-labelledby="tab-projects"[^>]*tabindex="0"/);
assert.match(app, /root\.setAttribute\('aria-labelledby', 'tab-'\+state\.page\)/,
  "render must update the panel label whenever its active section changes");
assert.match(app, /btn\.setAttribute\('aria-selected',String\(btn\.dataset\.page===state\.page\)\)/,
  "render must keep selected tab synchronized");
console.log("PASS: tab-to-panel associations and dynamic active-section label");
