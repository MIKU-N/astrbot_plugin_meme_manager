import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const script = await readFile(
  new URL("../../pages/app/shared/ui.js", import.meta.url),
  "utf8",
);
const start = script.lastIndexOf(
  'for (const dialog of document.querySelectorAll(\'[role="dialog"]\')) {',
);
const setup = script.slice(
  start,
  script.indexOf("document.addEventListener(", start),
);

function preview() {
  const handlers = new Map();
  const mask = {
    addEventListener(type, handler, capture) {
      const listeners = handlers.get(type) || [];
      listeners.push({ handler, capture });
      handlers.set(type, listeners);
    },
  };
  const dialog = { parentElement: mask };
  const text = {};
  const button = {};
  vm.runInNewContext(setup, {
    document: { querySelectorAll: () => [dialog] },
    dialogObserver: { observe() {} },
  });
  let closed = false;
  mask.addEventListener("click", (event) => {
    if (event.target === mask || event.target === dialog) closed = true;
  });
  function dispatch(type, target, detail = 1) {
    const event = {
      target,
      detail,
      stopped: false,
      stopImmediatePropagation() {
        this.stopped = true;
      },
    };
    const listeners = [...(handlers.get(type) || [])].sort(
      (a, b) => Number(Boolean(b.capture)) - Number(Boolean(a.capture)),
    );
    for (const { handler } of listeners) {
      handler(event);
      if (event.stopped) break;
    }
    return event;
  }
  function gesture(down, up, click) {
    dispatch("pointerdown", down);
    dispatch("pointerup", up);
    return dispatch("click", click);
  }
  return { mask, dialog, text, button, dispatch, gesture, closed: () => closed };
}

test("selecting text and releasing on either preview backdrop keeps it open", () => {
  for (const backdrop of ["mask", "dialog"]) {
    const p = preview();
    p.gesture(p.text, p[backdrop], p[backdrop]);
    assert.equal(p.closed(), false, backdrop);
  }
});

test("pressing the backdrop and releasing inside the dialog keeps it open", () => {
  const p = preview();
  p.gesture(p.mask, p.text, p.mask);
  assert.equal(p.closed(), false);
});

test("ordinary clicks on either preview backdrop still dismiss it", () => {
  for (const backdrop of ["mask", "dialog"]) {
    const p = preview();
    p.gesture(p[backdrop], p[backdrop], p[backdrop]);
    assert.equal(p.closed(), true, backdrop);
  }
});

test("content buttons and keyboard or programmatic clicks are not intercepted", () => {
  const p = preview();
  assert.equal(p.gesture(p.button, p.button, p.button).stopped, false);
  assert.equal(p.dispatch("click", p.button, 0).stopped, false);
  assert.equal(p.dispatch("click", p.mask, 0).stopped, false);
  assert.equal(p.closed(), true);
});

test("a cancelled pointer cannot leave a backdrop dismissal armed", () => {
  const p = preview();
  p.dispatch("pointerdown", p.mask);
  p.dispatch("pointercancel", p.mask);
  p.dispatch("pointerup", p.mask);
  p.dispatch("click", p.mask);
  assert.equal(p.closed(), false);
  p.gesture(p.mask, p.mask, p.mask);
  assert.equal(p.closed(), true);
});
