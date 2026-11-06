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

/* A switch that adds five unavailable categories lists them whenever it is on: the Reader reads the scope from the analysis. */

test("the Reader lists the India-specific rows from the analysis's own scope", () => {
  assert.match(source, /analysis\?\.jurisdiction_scope === "india_review"/);
  assert.match(source, /listRows\(/);
});
