import { test } from "node:test";
import assert from "node:assert/strict";
import { SAMPLE_CONTRACT } from "../../api/contract.ts";
import { buildOffsetIndex, sliceCp } from "../../lib/offsets.ts";
import { HERO_EXAMPLES, splitExcerpt } from "./heroExamples.ts";

const index = buildOffsetIndex(SAMPLE_CONTRACT);

test("three examples show two findings and one abstention, in that order", () => {
  assert.deepEqual(
    HERO_EXAMPLES.map((e) => [e.category, e.status]),
    [
      ["Non-Compete", "found"],
      ["Notice Period to Terminate Renewal", "found"],
      ["Competitive Restriction Exception", "review"],
    ],
  );
});

test("each finding's offsets slice the sample contract to its quote", () => {
  for (const e of HERO_EXAMPLES) assert.equal(sliceCp(SAMPLE_CONTRACT, index, e.start, e.end), e.quote, e.category);
});

test("each excerpt appears verbatim in the sample contract at its offset", () => {
  for (const e of HERO_EXAMPLES) {
    const end = e.excerptStart + [...e.excerpt].length;
    assert.equal(sliceCp(SAMPLE_CONTRACT, index, e.excerptStart, end), e.excerpt, e.category);
    assert.ok(!e.excerpt.includes("\n"), `${e.category}: one paragraph per excerpt`);
  }
});

test("each finding lies inside its excerpt, and the three parts rebuild the excerpt", () => {
  for (const e of HERO_EXAMPLES) {
    const { before, mark, after } = splitExcerpt(e);
    assert.equal(mark, e.quote, e.category);
    assert.equal(before + mark + after, e.excerpt, e.category);
  }
});

test("splitExcerpt counts code points, not UTF-16 units", () => {
  // The emoji is two UTF-16 units and one code point, so "found" starts at code point 4 of the excerpt.
  const excerpt = "A \u{1F600} found it";
  const parts = splitExcerpt({ excerpt, excerptStart: 100, start: 104, end: 109 });
  assert.deepEqual(parts, { before: "A \u{1F600} ", mark: "found", after: " it" });
});
