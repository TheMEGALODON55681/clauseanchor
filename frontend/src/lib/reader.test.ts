import { test } from "node:test";
import assert from "node:assert/strict";
import { INDIA_NOTE, categoryStatus, freshDelays, httpsUrl, listRows, nearestMark, sessionEndsIn, unfinishedList } from "./reader.ts";
import { INDIA_IDS } from "../api/catalogue.ts";
import type { Category, Clause } from "../api/types.ts";

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

test("sessionEndsIn: with no report to download, the line does not tell the user to download one", () => {
  assert.equal(sessionEndsIn(10, false), "This session ends in 10 minutes.");
  assert.equal(sessionEndsIn(0.4, false), "This session ends in less than a minute.");
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

/* The category list of the Reader (4-C1 live run, defects 1 and 5). The synthetic categories hold no contract text. */

const cat = (category_id: string, status: Category["status"], clauses = 0, search_complete = true): Category => ({
  category_id,
  status,
  decision_confidence: null,
  reason_code: null,
  search_complete,
  windows_done: 1,
  windows_total: 1,
  unresolved_count: 0,
  clauses: Array.from({ length: clauses }, (_, i) => ({ id: `${category_id}-${i}`, status: "review_candidate", confidence_band: "unvalidated" }) as Clause),
});
const byId = (...cats: Category[]) => new Map(cats.map((c) => [c.category_id, c]));
const THREE = ["cuad.governing_law", "cuad.cap_on_liability", "cuad.termination_for_convenience"];

test("India-specific: five ids, all in the catalogue's India group", () => {
  assert.equal(INDIA_IDS.length, 5);
  assert.ok(INDIA_IDS.every((id) => id.startsWith("in.")));
});

test("listRows: with the switch on, the five India categories are Unavailable rows with a reason, while the review runs and after it ends", () => {
  const running = listRows(THREE, true, byId(), false);
  const ended = listRows(THREE, true, byId(cat(THREE[0], "abstained", 1), cat(THREE[1], "abstained", 1), cat(THREE[2], "abstained")), true);
  for (const rows of [running, ended]) {
    const india = rows.filter((r) => INDIA_IDS.includes(r.id));
    assert.equal(india.length, 5);
    for (const r of india) assert.deepEqual({ status: r.status, pending: r.pending, note: r.note, count: r.count }, { status: "unavailable", pending: false, note: INDIA_NOTE, count: undefined }, r.id);
  }
  assert.equal(INDIA_NOTE, "Not available in this build yet");
});

test("listRows: with the switch off only the categories asked for are listed, and with it on the India ids follow them, none twice", () => {
  assert.deepEqual(listRows(THREE, false, byId(), false).map((r) => r.id), THREE);
  assert.deepEqual(listRows(THREE, true, byId(), false).map((r) => r.id), [...THREE, ...INDIA_IDS]);
  assert.deepEqual(listRows([...THREE, "in.arbitration"], true, byId(), false).map((r) => r.id), [...THREE, "in.arbitration", ...INDIA_IDS.filter((id) => id !== "in.arbitration")]);
});

test("listRows: an India category the API returned as unavailable is one row with the same reason", () => {
  const rows = listRows([...THREE, "in.arbitration"], true, byId(cat("in.arbitration", "unavailable")), true);
  assert.equal(rows.filter((r) => r.id === "in.arbitration").length, 1);
  assert.equal(rows.find((r) => r.id === "in.arbitration")?.note, INDIA_NOTE);
  assert.equal(rows.length, 3 + 5);
});

test("listRows: other categories are pending until the review ends, then Unavailable if the API never returned them", () => {
  assert.deepEqual(listRows(THREE, false, byId(), false).map((r) => [r.status, r.pending]), [["absent", true], ["absent", true], ["absent", true]]);
  assert.deepEqual(listRows(THREE, false, byId(), true).map((r) => [r.status, r.pending, r.note]), [["unavailable", false, undefined], ["unavailable", false, undefined], ["unavailable", false, undefined]]);
});

test("listRows: a category that abstained with no passage shows a count of 0, like the rows beside it", () => {
  const rows = listRows(THREE, false, byId(cat(THREE[0], "abstained", 2), cat(THREE[1], "abstained", 9), cat(THREE[2], "abstained", 0)), true);
  assert.deepEqual(rows.map((r) => [r.status, r.count]), [["review", 2], ["review", 9], ["review", 0]]);
});

test("listRows: Not found and Unavailable rows carry no count", () => {
  const rows = listRows(THREE, false, byId(cat(THREE[0], "absent"), cat(THREE[1], "unavailable"), cat(THREE[2], "found", 1)), true);
  assert.deepEqual(rows.map((r) => [r.status, r.count]), [["absent", undefined], ["unavailable", undefined], ["unvalidated", 1]]);
});

test("categoryStatus: found with only unvalidated passages is Confidence not validated, and abstained is Needs a lawyer", () => {
  assert.equal(categoryStatus(cat("cuad.a", "found", 1)), "unvalidated");
  assert.equal(categoryStatus(cat("cuad.a", "abstained")), "review");
});

/* The list behind View list: the categories and the pages that were not finished. It is empty when nothing was left out, and the
   control is then not drawn. */

test("unfinishedList: empty when nothing was left out", () => {
  const rows = listRows(THREE, false, byId(cat(THREE[0], "found", 1), cat(THREE[1], "absent"), cat(THREE[2], "abstained", 1)), true);
  assert.deepEqual(unfinishedList(rows, byId(cat(THREE[0], "found", 1)), { partial: false, warnings: [] }), []);
  assert.deepEqual(unfinishedList([], byId(), null), []);
});

test("unfinishedList: names the India categories, the unavailable ones and the ones searched in part, each with its reason", () => {
  const cats = byId(cat(THREE[0], "abstained", 1, false), cat(THREE[1], "unavailable"), cat(THREE[2], "found", 1));
  const out = unfinishedList(listRows(THREE, true, cats, true), cats, { partial: false, warnings: [] });
  assert.deepEqual(out.slice(0, 2), [
    { label: "Governing Law", note: "Checked in part" },
    { label: "Cap on Liability", note: "Not checked" },
  ]);
  assert.deepEqual(out.slice(2).map((o) => o.note), Array(5).fill(INDIA_NOTE));
  assert.equal(out.length, 7);
});

test("unfinishedList: names the pages that could not be read, or the document when the file has no pages", () => {
  const warn = (code: string, page: number | null) => ({ code, page, detail: null });
  const pages = unfinishedList([], byId(), { partial: true, warnings: [warn("PARTIALLY_SCANNED_PDF", 4), warn("COLUMN_ORDER_UNCERTAIN", 2), warn("UNMAPPED_GLYPHS", 7), warn("PARTIALLY_SCANNED_PDF", 4)] });
  assert.deepEqual(pages, [
    { label: "Page 4", note: "Could not be read" },
    { label: "Page 7", note: "Could not be read" },
  ]);
  assert.deepEqual(unfinishedList([], byId(), { partial: true, warnings: [warn("EMBEDDED_OBJECT", null)] }), [{ label: "Part of the document", note: "Could not be read" }]);
  assert.deepEqual(unfinishedList([], byId(), { partial: false, warnings: [warn("PARTIALLY_SCANNED_PDF", 4)] }), [], "the parser's own flag decides");
});
