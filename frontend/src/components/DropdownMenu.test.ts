import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

/* A menu item's inline style outranks the :focus-visible rule, so an inline `outline: none` hid the ring on a
   keyboard-focused item. The only inline outline allowed is the gallery's forced-state ring. */

const source = readFileSync(new URL("./DropdownMenu.tsx", import.meta.url), "utf8");

test("a menu item draws no inline outline except the forced-state ring, and takes the shared inset ring", () => {
  const inline = [...source.matchAll(/\boutline:\s*"([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(inline, ["2px solid var(--focus-ring)"]);
  assert.match(source, /className="focus-inset"/);
});
