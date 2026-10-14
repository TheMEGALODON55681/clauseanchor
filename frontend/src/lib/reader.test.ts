import { test } from "node:test";
import assert from "node:assert/strict";
import { freshDelays, httpsUrl, nearestMark, sessionEndsIn } from "./reader.ts";

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

test("sessionEndsIn: names the whole minutes left, rounded down so it never promises more time than there is", () => {
  assert.equal(sessionEndsIn(10), "This session ends in 10 minutes. Download your report before it closes.");
  assert.match(sessionEndsIn(8.99), /ends in 8 minutes\./);
  assert.match(sessionEndsIn(2.2), /ends in 2 minutes\./);
});

test("sessionEndsIn: one minute is singular, and under a minute says so", () => {
  assert.match(sessionEndsIn(1.9), /ends in 1 minute\./);
  assert.match(sessionEndsIn(0.4), /ends in less than a minute\./);
  assert.match(sessionEndsIn(-3), /ends in less than a minute\./, "a clock that ran past the expiry still reads sensibly");
});

test("httpsUrl: an https address comes back normalised, so the string opened is the string checked", () => {
  assert.equal(httpsUrl("https://example.org/a b"), "https://example.org/a%20b");
  assert.equal(httpsUrl("  https://example.org/x"), "https://example.org/x");
});

test("httpsUrl: every other scheme, a relative path and a missing value give undefined", () => {
  for (const bad of ["http://example.org", "javascript:alert(1)", "data:text/html,x", "ftp://example.org", "//example.org", "/judgment/1", "", undefined]) {
    assert.equal(httpsUrl(bad), undefined, String(bad));
  }
});
