import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { CATALOGUE, GROUP_ORDER } from "./catalogue.ts";

/* The frontend lists the categories by the ids the API takes. Tanishq owns the file, and a start with an id that is not in it is a 422. */

const file = JSON.parse(readFileSync(new URL("../../../ml/configs/catalogue.json", import.meta.url), "utf8")) as {
  categories: { id: string; source: string }[];
};

test("the frontend catalogue holds exactly the ids of ml/configs/catalogue.json", () => {
  assert.deepEqual(CATALOGUE.map((c) => c.id).sort(), file.categories.map((c) => c.id).sort());
});

test("the five India extensions are the India-specific group, and no CUAD category is", () => {
  const india = new Set(file.categories.filter((c) => c.source === "india_extension").map((c) => c.id));
  for (const c of CATALOGUE) assert.equal(c.group === "India-specific", india.has(c.id), c.id);
});

test("every entry sits in one of the seven groups", () => {
  assert.equal(GROUP_ORDER.length, 7);
  for (const c of CATALOGUE) assert.ok(GROUP_ORDER.includes(c.group), c.id);
});
