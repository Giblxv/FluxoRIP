// Synthetic, dependency-free tab-navigation smoke test; no printer or API calls.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const code = readFileSync(new URL("./cmyk-navigation.js", import.meta.url), "utf8");

function makeApp() {
  let keyHandler = null;
  let clickHandler = null;
  let observerCallback = null;
  const state = { active: 0, focused: 0, press: [], scroll: [], prevented: 0,
                  reduced: false, motionOff: false };
  let document;

  const tabs = ["projects", "queue", "history"].map((name, index) => {
    const tab = {
      name,
      disabled: false,
      hidden: false,
      cssHidden: false,
      ariaHidden: false,
      getClientRects() { return this.cssHidden ? [] : [{}]; },
      tabIndex: null,
      getAttribute(attr) {
        if (attr === "aria-hidden") return this.ariaHidden ? "true" : null;
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
      if (name === "keydown") keyHandler = handler;
      else if (name === "click") clickHandler = handler;
      else assert.fail("Unexpected listener: " + name);
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
      assert.equal(options.attributeFilter.join(","), "aria-selected,aria-hidden,class,hidden,disabled,style");
    }
  }
  runInNewContext(code, {
    document, window: {matchMedia() { return {matches:state.reduced}; }},
    MutationObserver: FakeMutationObserver,
    queueMicrotask(callback) { callback(); }
  }, {timeout: 1000});
  return {
    tabs, state,
    simulateClick(index) {
      state.active = index;
      clickHandler({target:{closest(selector) {
        assert.equal(selector, "button.top-tab[role='tab']");
        return tabs[index];
      }}});
    },
    syncSelection() { observerCallback?.([{attributeName: "aria-selected"}]); },
    mutateAttribute(name) { observerCallback?.([{attributeName: name}]); },
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
{
  const app = makeApp();
  app.tabs[0].disabled = true;
  app.syncSelection();
  assert.deepEqual(app.tabs.map(t => t.tabIndex), [-1,0,-1],
    "disabled selected tab cannot be keyboard tab stop");
  app.tabs[0].disabled = false;
  app.tabs[0].hidden = true;
  app.syncSelection();
  assert.deepEqual(app.tabs.map(t => t.tabIndex), [-1,0,-1],
    "hidden selected tab cannot be keyboard tab stop");
}
{
  const app = makeApp();
  app.simulateClick(2);
  assert.deepEqual(app.tabs.map(t => t.tabIndex), [-1,-1,0],
    "mouse activation must update the keyboard tab stop");
}
{
  const app = makeApp();
  app.tabs[0].cssHidden = true;
  app.syncSelection();
  assert.deepEqual(app.tabs.map(t => t.tabIndex), [-1,0,-1],
    "CSS-hidden selected tab must not trap keyboard focus");
  app.tabs[0].cssHidden = false;
  app.tabs[0].ariaHidden = true;
  app.syncSelection();
  assert.deepEqual(app.tabs.map(t => t.tabIndex), [-1,0,-1],
    "aria-hidden selected tab must not be keyboard tab stop");
  app.tabs[0].ariaHidden = false;
  app.tabs[1].cssHidden = true;
  app.tabs[0].focus();
  app.syncSelection();
  app.key("ArrowRight");
  assert.equal(app.state.active, 2, "arrow navigation must skip CSS-hidden tab");
  app.tabs[1].cssHidden = false;
  app.tabs[1].ariaHidden = true;
  app.tabs[0].focus();
  app.key("ArrowRight");
  assert.equal(app.state.active, 2, "arrow navigation must skip aria-hidden tab");
}
{
  const app = makeApp();
  const expected = [-1,0,-1];
  const cases = [
    ["hidden", tab => { tab.hidden = true; }],
    ["disabled", tab => { tab.disabled = true; }],
    ["aria-hidden", tab => { tab.ariaHidden = true; }],
    ["style", tab => { tab.cssHidden = true; }],
    ["class", tab => { tab.cssHidden = true; }]
  ];
  for (const [attribute, change] of cases) {
    const trial = makeApp();
    change(trial.tabs[0]);
    trial.mutateAttribute(attribute);
    assert.deepEqual(trial.tabs.map(t => t.tabIndex), expected,
      attribute + " mutation must move tab stop away from unavailable tab");
    // Re-enable the tab and verify it becomes reachable again.
    trial.tabs[0].hidden = false;
    trial.tabs[0].disabled = false;
    trial.tabs[0].ariaHidden = false;
    trial.tabs[0].cssHidden = false;
    trial.mutateAttribute(attribute);
    assert.deepEqual(trial.tabs.map(t => t.tabIndex), [0,-1,-1],
      attribute + " restoration must recover selected tab stop");
  }
  app.tabs.forEach(tab => { tab.disabled = true; });
  app.mutateAttribute("disabled");
  assert.deepEqual(app.tabs.map(t => t.tabIndex), [-1,-1,-1],
    "all unavailable tabs must be removed from keyboard tab order");
}
console.log("PASS: CMYK keyboard tabs, wrap, Home/End, disabled and reduced motion");
