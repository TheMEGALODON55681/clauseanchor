import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

/* SA3: a page that is really leaving ends its session on the server, so the slot is free for the next visitor.
   The token lives in React state, so the handler reads it through a ref. A page that goes into the back-forward cache
   may come back with its token, so it does not end anything. */

const source = readFileSync(new URL("./session.tsx", import.meta.url), "utf8");

test("pagehide ends the session with a keepalive request, from a token ref", () => {
  assert.match(source, /addEventListener\("pagehide"/);
  assert.match(source, /removeEventListener\("pagehide"/);
  const handler = source.match(/const onHide = [\s\S]*?\n    \};/)?.[0] ?? "";
  assert.match(handler, /client\.endSession\(tokenRef\.current, \{ keepalive: true \}\)/);
  assert.match(handler, /\.catch\(/, "a failed request on the way out is not an error anyone can act on");
});

test("a page that enters the back-forward cache does not end the session", () => {
  const handler = source.match(/const onHide = [\s\S]*?\n    \};/)?.[0] ?? "";
  assert.match(handler, /e\.persisted/);
  assert.ok(handler.indexOf("e.persisted") < handler.indexOf("client.endSession"), "checked first");
});
