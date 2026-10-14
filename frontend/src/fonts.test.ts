import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";

/* The sheet that paints the page declares only the Latin faces index.html preloads. The rest
   wait for fonts-late.css, which src/main.tsx loads after first paint. A Latin face added to
   index.css puts its file back on the path to the first screen (FrontendDesign.md 17.7). */

const read = (p: string) => readFileSync(new URL(p, import.meta.url), "utf8");
const files = (css: string) => [...css.matchAll(/url\('\/fonts\/([^']+)'\)/g)].map((m) => m[1]);
const latin = (names: string[]) => names.filter((f) => f.endsWith(".woff2") && !f.includes("latin-ext")).sort();

test("index.css declares the preloaded Latin faces, fonts-late.css the other Latin files once each", () => {
  const preloaded = [...read("../index.html").matchAll(/rel="preload" href="\/fonts\/([^"]+)"/g)].map((m) => m[1]).sort();
  const early = latin(files(read("./index.css")));
  const late = latin(files(read("./fonts-late.css")));
  assert.equal(preloaded.length, 2);
  assert.deepEqual(early, preloaded);
  assert.deepEqual([...early, ...late].sort(), latin(readdirSync(new URL("../public/fonts", import.meta.url))));
});
