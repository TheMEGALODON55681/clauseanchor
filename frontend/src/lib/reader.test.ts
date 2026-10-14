import { test } from "node:test";
import assert from "node:assert/strict";
import { freshDelays, nearestMark } from "./reader.ts";

test("nearestMark: a click on a tick picks it", () => {
  assert.equal(nearestMark([0.1, 0.5, 0.9], 0.5, 500), 1);
});

test("nearestMark: between two ticks the closer one wins, and a tie takes the first", () => {
  // Two ticks 10 px apart on a 200 px strip.
  assert.equal(nearestMark([0.5, 0.55], 0.51, 200), 0);
  assert.equal(nearestMark([0.5, 0.55], 0.54, 200), 1);
  assert.equal(nearestMark([0.5, 0.55], 0.525, 200), 0);
});

test("nearestMark: a click farther than the reach from every tick picks none", () => {
  // 0.05 of 500 px is 25 px, past the 12 px reach.
  assert.equal(nearestMark([0.1, 0.5], 0.3, 500), -1);
  assert.equal(nearestMark([0.5], 0.5 + 12 / 500, 500), 0);
  assert.equal(nearestMark([0.5], 0.5 + 13 / 500, 500), -1);
});

test("nearestMark: no ticks and a zero-height strip pick none", () => {
  assert.equal(nearestMark([], 0.5, 500), -1);
  assert.equal(nearestMark([0.5], 0.5, 0), -1);
});

test("freshDelays: nothing new gives no delays", () => {
  assert.equal(freshDelays(new Set(["a", "b"]), ["a", "b"]).size, 0);
});

test("freshDelays: new ids step 0, 1, 2 in order and known ids are skipped", () => {
  const d = freshDelays(new Set(["a"]), ["a", "b", "c", "d"]);
  assert.deepEqual([...d], [["b", 0], ["c", 1], ["d", 2]]);
});

test("freshDelays: the stagger stops at the cap, so later rows share the last step", () => {
  const ids = Array.from({ length: 10 }, (_, i) => `r${i}`);
  const d = freshDelays(new Set(), ids, 6);
  assert.deepEqual([...d.values()], [0, 1, 2, 3, 4, 5, 5, 5, 5, 5]);
});
