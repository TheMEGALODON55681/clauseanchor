import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

/* The four client methods with no endpoint until Phase 3 refuse every call. A page that calls one must check the matching flag in
   `available` first, so the user sees the "not available" state and not a failed request. */

const GUARD: Record<string, string> = { setParty: "partyBinding", downloadReport: "report", getManualReview: "manualReview", getEvaluations: "evaluations" };
const src = fileURLToPath(new URL("..", import.meta.url));
const files = (dir: string): string[] => readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? files(join(dir, e.name)) : [join(dir, e.name)]));
const code = files(src).filter((f) => /\.tsx?$/.test(f) && !/\.test\.ts$/.test(f) && !/[\\/]api[\\/](http|client|fixtures)\.ts$/.test(f));

test("every call to a method with no endpoint sits in a file that checks its flag", () => {
  let calls = 0;
  for (const f of code) {
    const text = readFileSync(f, "utf8");
    for (const [method, flag] of Object.entries(GUARD)) {
      if (!text.includes(`client.${method}(`)) continue;
      calls++;
      assert.ok(text.includes(`available.${flag}`), `${f} calls client.${method}() and never reads available.${flag}`);
    }
  }
  assert.ok(calls >= 4, `found ${calls} calls; the scan lost its files`);
});
