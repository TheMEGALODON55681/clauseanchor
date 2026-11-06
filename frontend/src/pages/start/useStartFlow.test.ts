import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

/* A replaced upload is deleted first. A delete the server did not carry out leaves the old document in the session, so it must not
   read as done: the new upload waits, the error shows with Try again, and the old document stays the current one until a delete
   succeeds or the document reads 404 (4-C1 live run, defect 2). */

const source = readFileSync(new URL("./useStartFlow.ts", import.meta.url), "utf8");
const upload = source.match(/const upload = useCallback\([\s\S]*?\n  \);/)?.[0] ?? "";

test("a failed delete of the replaced upload is not swallowed", () => {
  const del = upload.match(/if \(replaced\)[^\n]*\n[^\n]*/)?.[0] ?? "";
  assert.match(del, /await client\.deleteDocument\(token, replaced\)/);
  assert.doesNotMatch(del, /\.catch\(/);
});

test("the replaced document stays current until its delete has succeeded", () => {
  assert.doesNotMatch(upload.split("try {")[0], /current\.current = null/, "cleared before the delete ran");
  assert.match(upload, /await client\.deleteDocument\(token, replaced\);\s*current\.current = null;/);
});
