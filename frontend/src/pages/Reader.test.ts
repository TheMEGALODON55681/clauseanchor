import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

/* At peek the bottom sheet shows only its top PEEK_PX and clips the rest, so a control focused below that line is
   out of sight and focus cannot scroll to it. Focus entering the sheet's content there opens the sheet. */

const source = readFileSync(new URL("./Reader.tsx", import.meta.url), "utf8");

test("focus on a control below the peek line opens the sheet", () => {
  const handler = source.match(/const openSheetOnFocus = [\s\S]*?\n  \};/)?.[0] ?? "";
  assert.match(handler, /sheetState !== "peek"/);
  assert.match(handler, /> PEEK_PX/);
  assert.match(handler, /setSheet\("open"\)/);
  assert.match(source, /<div className="reader-panel" onFocus=\{openSheetOnFocus\}>\{sheetBody\.node\}<\/div>/);
});

/* A delete that meets a session that ended leaves for the Expired page (API.md section 2: 401 SESSION_INVALID). A document that is
   already gone counts as deleted, because the adapter takes the 404. Any other failure, a 503 included, leaves the document in place
   and says so in words the user can act on, and the document is forgotten only after a delete succeeded. */

test("a delete that finds the session gone goes to the Expired page, and any other failure is a message", () => {
  const remove = source.match(/async function remove\(\) \{[\s\S]*?\n  \}/)?.[0] ?? "";
  assert.match(remove, /e\.code === "expired"/);
  assert.doesNotMatch(remove, /not_found/);
  assert.match(remove, /handleError\(e\)/);
  assert.match(remove, /toast\("error", "The contract could not be deleted\. Try again\."\)/);
  assert.ok(remove.indexOf("await client.deleteDocument") < remove.indexOf("forgetDoc(documentId)"), "forgotten only after the delete succeeded");
});

/* SA3: deleting the last document leaves the session with nothing to keep, so it ends on the server and frees its slot. A delete that
   leaves another document does not. A failed end is ignored, because the sweep ends the session anyway. The Reader's own effect sends
   a visitor with no token to the Expired page, so it must stand down while the Reader is the one leaving. */

test("deleting the last document ends the session, after the document is forgotten, and a failed end is ignored", () => {
  const remove = source.match(/async function remove\(\) \{[\s\S]*?\n  \}/)?.[0] ?? "";
  assert.match(remove, /Object\.keys\(docs\)\.some\(\(id\) => id !== documentId\)/);
  assert.match(remove, /client\.endSession\(token\)\.catch\(\(\) => undefined\)/);
  assert.ok(remove.indexOf("forgetDoc(documentId)") < remove.indexOf("client.endSession"), "forgotten first");
  assert.ok(remove.indexOf("client.endSession") < remove.indexOf('navigate("/expired?reason=deleted"'), "ended before it leaves");
});

test("the effect that sends a visitor with no token to Expired stands down while the Reader leaves", () => {
  assert.match(source, /const leaving = useRef\(false\)/);
  const effect = source.match(/Contract text is fetched once[\s\S]*?goExpired\(\);\n      return;\n    \}/)?.[0] ?? "";
  assert.match(effect, /if \(leaving\.current\) return;/);
  assert.ok(effect.indexOf("leaving.current") < effect.indexOf("goExpired()"), "checked before it sends anyone away");
});

/* 4-B.3, DV. This build runs no case law retrieval, so a panel that prints "Case law 0" and "No verified case law found" claims a search
   that never ran (the panel's own comment says so). The section is drawn only for a clause that carries a passage. */

test("the panel draws a case law section only when the clause carries a passage", () => {
  assert.match(source, /caseLaw: clause\.passages\.length \? \(/);
  assert.match(source, /caseLawCount: clause\.passages\.length \|\| undefined/);
  assert.doesNotMatch(source, /<JudgmentCard state="empty" \/>/);
});

/* View list opens the categories and pages that were not finished, and is not drawn when there is nothing to show. */

const scope = readFileSync(new URL("../components/ScopePanel.tsx", import.meta.url), "utf8");

test("View list is drawn only with a list behind it, and it opens that list", () => {
  assert.doesNotMatch(scope, /onViewList/, "no control without a handler");
  assert.match(scope, /unfinished\.length > 0 &&/);
  assert.match(scope, /aria-expanded=\{open\}/);
  assert.match(scope, /aria-controls=/);
  assert.doesNotMatch(source, /onViewList/);
  assert.match(source, /unfinished=\{unfinished\}/);
});

/* 4-B.4: the toolbar and the Review scope band take their words from what the API returned (reader.test.ts), so neither holds a fixed
   sentence that claims Unavailable rows, and the two lines for a cancelled, timed out or failed review stay as they were. */

test("the toolbar note and the scope band are built from the list of what was left out", () => {
  assert.match(source, /partialLine\(unfinished\)/);
  assert.match(scope, /incompleteBand\(unfinished\)/);
  assert.doesNotMatch(source, /Some categories could not be finished/);
  assert.doesNotMatch(scope, /some categories or pages were not finished/);
  assert.doesNotMatch(source, /Partial result\. Not finished/);
});

test("a cancelled, timed out or failed review keeps its own line", () => {
  assert.match(source, /"You stopped the review\. Categories not reached are listed as Unavailable\."/);
  assert.match(source, /"The review took too long, so ClauseAnchor stopped it\. Categories not reached show as Unavailable\."/);
  assert.match(source, /"The review stopped early\. Categories not reached are listed as Unavailable\."/);
});

/* A switch that adds five unavailable categories lists them whenever it is on: the Reader reads the scope from the analysis. */

test("the Reader lists the India-specific rows from the analysis's own scope", () => {
  assert.match(source, /analysis\?\.jurisdiction_scope === "india_review"/);
  assert.match(source, /listRows\(/);
});
