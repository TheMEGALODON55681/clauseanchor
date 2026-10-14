import { test } from "node:test";
import assert from "node:assert/strict";
import { AUTHORITY_PHRASE, authorityOf } from "./authority.ts";

test("each known status maps to its own fixed phrase", () => {
  assert.equal(AUTHORITY_PHRASE[authorityOf("reviewed")], "Checked against later judgments");
  assert.equal(AUTHORITY_PHRASE[authorityOf("not_reviewed")], "Not checked against later judgments");
  assert.equal(AUTHORITY_PHRASE[authorityOf("overruled")], "Overruled or modified by a later judgment");
});

test("a value the card does not know gets its own phrase and never reads as checked", () => {
  for (const s of ["", "superseded", "REVIEWED", "not-reviewed", "reviewed "]) {
    assert.equal(authorityOf(s), "unknown", s);
  }
  assert.equal(AUTHORITY_PHRASE.unknown, "Later judgments: status unknown");
});

test("no phrase is the bare word Reviewed, and no two phrases match", () => {
  const phrases = Object.values(AUTHORITY_PHRASE);
  assert.ok(phrases.every((p) => p !== "Reviewed" && p !== "Not yet reviewed"));
  assert.equal(new Set(phrases).size, phrases.length);
});
