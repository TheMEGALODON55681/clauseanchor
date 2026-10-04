import { test } from "node:test";
import assert from "node:assert/strict";
import { revealOnce, type ObserverLike, type ObserverFactory } from "./reveal.ts";

type Entry = { isIntersecting: boolean };

/* A plain object stands in for the element and a fake for the observer,
   so the logic runs without a DOM. */
function setup() {
  const el = { dataset: {} as Record<string, string | undefined> };
  const log = { created: 0, observed: [] as unknown[], disconnects: 0 };
  let callback: (entries: Entry[]) => void = () => {};
  const observer: ObserverLike = {
    observe: (target) => void log.observed.push(target),
    disconnect: () => void log.disconnects++,
  };
  const factory: ObserverFactory = (cb) => {
    log.created++;
    callback = cb;
    return observer;
  };
  return { el, log, factory, fire: (...entries: Entry[]) => callback(entries) };
}

test("leaves the element visible when no observer can be made", () => {
  const { el } = setup();
  const stop = revealOnce(el, () => null, false);
  assert.equal(el.dataset.reveal, undefined);
  stop();
});

test("leaves the element visible and makes no observer under reduced motion", () => {
  const { el, log, factory } = setup();
  revealOnce(el, factory, true);
  assert.equal(el.dataset.reveal, undefined);
  assert.equal(log.created, 0);
});

test("marks the element pending once the observer exists and watches it", () => {
  const { el, log, factory } = setup();
  revealOnce(el, factory, false);
  assert.equal(el.dataset.reveal, "pending");
  assert.deepEqual(log.observed, [el]);
});

test("stays pending while the element is outside the viewport", () => {
  const { el, log, factory, fire } = setup();
  revealOnce(el, factory, false);
  fire({ isIntersecting: false });
  assert.equal(el.dataset.reveal, "pending");
  assert.equal(log.disconnects, 0);
});

test("marks the element shown on the first intersection and disconnects", () => {
  const { el, log, factory, fire } = setup();
  revealOnce(el, factory, false);
  fire({ isIntersecting: false }, { isIntersecting: true });
  assert.equal(el.dataset.reveal, "shown");
  assert.equal(log.disconnects, 1);
});

test("does not hide the element again after it was shown", () => {
  const { el, factory, fire } = setup();
  revealOnce(el, factory, false);
  fire({ isIntersecting: true });
  fire({ isIntersecting: false });
  assert.equal(el.dataset.reveal, "shown");
});

test("the stop function disconnects the observer", () => {
  const { el, log, factory } = setup();
  const stop = revealOnce(el, factory, false);
  stop();
  assert.equal(log.disconnects, 1);
});
