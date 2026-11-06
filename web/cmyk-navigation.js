/* Fluxo RIP — keyboard navigation for the real tablist.
   Visual CMYK motion is CSS-only; this module does not change machine state. */
(() => {
  "use strict";
  const nav = document.querySelector(".top-navigation[role='tablist']");
  if (!nav) return;

  const buttons = () => Array.from(nav.querySelectorAll("button.top-tab[role='tab']"));
  // CSS-hidden and aria-hidden tabs must not become keyboard tab stops.
  const isAvailable = tab => !tab.disabled && !tab.hidden &&
    tab.getAttribute("aria-hidden") !== "true" &&
    (typeof tab.getClientRects !== "function" || tab.getClientRects().length > 0);

  const activeIndex = (tabs) => {
    const selected = tabs.findIndex(tab => tab.getAttribute("aria-selected") === "true");
    return selected < 0 ? 0 : selected;
  };

  function syncRovingFocus() {
    const tabs = buttons();
    const selected = activeIndex(tabs);
    const current = tabs[selected] && isAvailable(tabs[selected])
      ? selected : tabs.findIndex(isAvailable);
    tabs.forEach((tab, index) => {
      tab.tabIndex = index === current ? 0 : -1;
    });
  }

  // A mouse click should not strand keyboard users on a tab with tabindex=-1.
  nav.addEventListener("click", event => {
    if (event.target.closest("button.top-tab[role='tab']")) {
      // The application click handler may update aria-selected after this listener.
      queueMicrotask(syncRovingFocus);
    }
  });

  nav.addEventListener("keydown", event => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
    if (!keys.includes(event.key)) return;
    const tabs = buttons().filter(isAvailable);
    if (!tabs.length) return;
    if (!tabs.includes(document.activeElement)) return;
    const index = tabs.indexOf(document.activeElement);
    const nextIndex =
      event.key === "Home" ? 0 :
      event.key === "End" ? tabs.length - 1 :
      (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    const next = tabs[nextIndex];
    event.preventDefault();
    next.focus();
    // Reuse the app's existing click handler; do not implement another router.
    next.click();
    const reduced = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    next.scrollIntoView?.({
      block: "nearest",
      inline: "nearest",
      behavior: reduced || document.documentElement.classList.contains("motion-off")
        ? "auto" : "smooth",
    });
    syncRovingFocus();
  });

  const observer = new MutationObserver(mutations => {
    if (mutations.some(mutation =>
        mutation.attributeName === "aria-selected" || mutation.attributeName === "class")) {
      syncRovingFocus();
    }
  });
  observer.observe(nav, {subtree: true, attributes: true, attributeFilter: ["aria-selected", "aria-hidden", "class", "hidden", "disabled", "style"]});
  syncRovingFocus();
})();
