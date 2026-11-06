// Synthetic, dependency-free tab-navigation smoke test; no printer or API calls.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const code = readFileSync(new URL("./cmyk-navigation.js", import.meta.url), "utf8");

function makeApp() {
  let keyHandler = null;
  let observerCallback = null;
  const state = { active: 0, focused: 0, press: [], scroll: [], prevented: 0,
                  reduced: false, motionOff: false };
  let document;

  const tabs = ["projects", "queue", "history"].map((name, index) => {
    const tab = {
      name,
      disabled: false,
      hidden: false,
      tabIndex: null,
      getAttribute(attr) {
        return attr === "aria-selected" && state.active === index ? "true" : "false";
      },
      focus() {
        document.activeElement = this;
        state.focused = index;
      },
      click() {
        state.active = index;
        state.press.push(name);
        observerCallback?.([{attributeName: "aria-selected"}]);
      },
      scrollIntoView(options) { state.scroll.push(options); }
    };
    return tab;
  });
  const nav = {
    addEventListener(name, handler) {
      assert.equal(name, "keydown");
      keyHandler = handler;
    },
    querySelectorAll() { return tabs; }
  };
  document = {
    activeElement: tabs[0],
    documentElement: { classList: {contains(name) {
      assert.equal(name, "motion-off");
      return state.motionOff;
    }}},
    querySelector(selector) {
      assert.equal(selector, ".top-navigation[role='tablist']");
      return nav;
    }
  };
  class FakeMutationObserver {
    constructor(callback) { observerCallback = callback; }
    observe(target, options) {
      assert.equal(target, nav);
      assert.deepEqual(options.attributeFilter, ["aria-selected", "class"]);
    }
  }
  runInNewContext(code, {
    document, window: {matchMedia() { return {matches:state.reduced}; }},
    MutationObserver: FakeMutationObserver
  }, {timeout: 1000});
  return {
    tabs, state,
    key(key, extras = {}) {
      const event = {
        key, altKey: false, ctrlKey: false, metaKey: false,
        preventDefault() {state.prevented += 1;}, ...extras
      };
      keyHandler(event);
      return event;
    }
  };
}

{
  const app = makeApp();
  assert.deepEqual(app.tabs.map(t => t.tabIndex), [0,-1,-1]);
  app.key("ArrowRight");
  assert.equal(app.state.active, 1);
  assert.deepEqual(app.tabs.map(t => t.tabIndex), [-1,0,-1]);
  assert.deepEqual(app.state.press, ["queue"]);
  assert.equal(app.state.prevented, 1);
  assert.equal(app.state.scroll.at(-1).behavior, "smooth");
  app.key("End");
  assert.equal(app.state.active, 2);
  app.key("ArrowRight"); // wraps
  assert.equal(app.state.active, 0);
  app.key("ArrowLeft"); // reverse wraps
  assert.equal(app.state.active, 2);
  app.key("Home");
  assert.equal(app.state.active, 0);
  const count = app.state.press.length;
  app.key("ArrowRight", {ctrlKey:true});
  assert.equal(app.state.press.length, count);
  app.key("Escape");
  assert.equal(app.state.press.length, count);
  app.state.reduced = true;
  app.key("ArrowRight");
  assert.equal(app.state.scroll.at(-1).behavior, "auto");
  app.state.reduced = false;
  app.state.motionOff = true;
  app.key("ArrowRight");
  assert.equal(app.state.scroll.at(-1).behavior, "auto");
}
{
  const app = makeApp();
  app.tabs[1].disabled = true;
  app.key("ArrowRight");
  assert.equal(app.state.active, 2, "must skip disabled tab");
}
console.log("PASS: CMYK keyboard tabs, wrap, Home/End, disabled and reduced motion");
