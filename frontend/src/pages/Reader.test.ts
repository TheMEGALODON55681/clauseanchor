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
