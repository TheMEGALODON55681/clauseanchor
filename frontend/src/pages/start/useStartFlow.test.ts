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

/* SA3, "start over": the app has no start-over control, so the case it has is a new upload while the session still holds a document
   from an earlier visit. That review is abandoned, so its text goes before the new file is sent. Merely opening /start deletes nothing. */

test("a new upload deletes the documents of an earlier review before it uploads, and forgets them", () => {
  assert.match(source, /const docsRef = useRef\(docs\)/);
  const sweep = upload.match(/for \(const id of Object\.keys\(docsRef\.current\)\)[^\n]*\n[^\n]*\n[^\n]*\n/)?.[0] ?? "";
  assert.match(sweep, /id !== replaced/);
  assert.match(sweep, /await client\.deleteDocument\(token, id\)/);
  assert.match(sweep, /forgetDoc\(id\)/);
  assert.ok(upload.indexOf("Object.keys(docsRef.current)") < upload.indexOf("client.uploadDocument"), "before the upload");
  assert.ok(upload.indexOf("Object.keys(docsRef.current)") > upload.indexOf("ensureToken()"), "after the token exists");
});

test("a replaced document is forgotten once its delete has worked, so no stale entry holds the session open", () => {
  assert.match(upload, /await client\.deleteDocument\(token, replaced\);\s*forgetDoc\(replaced\);\s*\}/);
});

test("the replaced document stays current until its delete has succeeded", () => {
  assert.doesNotMatch(upload.split("try {")[0], /current\.current = null/, "cleared before the delete ran");
  assert.match(upload, /await client\.deleteDocument\(token, replaced\);\s*forgetDoc\(replaced\);\s*\}\s*current\.current = null;/);
});
