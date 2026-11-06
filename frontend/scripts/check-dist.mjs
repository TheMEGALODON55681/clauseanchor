// Run after `pnpm build`: node scripts/check-dist.mjs
// The build must hold no mock adapter and no sample contract (Architecture.md 7.1, Phases.md 4-C): no mock or contract chunk,
// no example.org, and none of the sample contract's text except the three paragraphs that the landing demo quotes.
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { SAMPLE_CONTRACT } from "../src/api/contract.ts";
import { HERO_EXAMPLES } from "../src/pages/landing/heroExamples.ts";

const dist = resolve(import.meta.dirname, "../dist");
const files = (dir) => readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? files(join(dir, e.name)) : [join(dir, e.name)]));
const all = files(dist);
const text = all.filter((f) => /\.(js|css|html|svg|json|txt)$/.test(f)).map((f) => ({ name: relative(dist, f), body: readFileSync(f, "utf8") }));
const problems = [];

for (const f of all) if (/[\\/](mock|contract)-[^\\/]*\.js$/.test(f)) problems.push(`chunk ${relative(dist, f)} holds the mock adapter or the sample contract`);
for (const t of text) if (t.body.includes("example.org")) problems.push(`${t.name} holds example.org`);

// A probe is the longest run of one line of the contract that has no quote, backslash or non-ASCII character, so minifier escaping cannot hide it.
const probes = SAMPLE_CONTRACT.split("\n")
  .map((line) => (line.match(/[\x20-\x7e]+/g) ?? []).flatMap((run) => run.split(/["'\\]/)).sort((a, b) => b.length - a.length)[0] ?? "")
  .filter((p) => p.length >= 30);
const quoted = HERO_EXAMPLES.map((e) => e.excerpt);
let found = 0;
let landing = 0;
for (const probe of probes) {
  const hits = text.filter((t) => t.body.includes(probe));
  if (!hits.length) continue;
  found++;
  if (quoted.some((q) => q.includes(probe))) landing++;
  else problems.push(`sample contract text in ${hits.map((h) => h.name).join(", ")}: ${probe.slice(0, 50)}...`);
}

console.log(`dist: ${all.length} files, ${probes.length} lines of the sample contract probed, ${found} found (${landing} of them in the landing demo's three quoted paragraphs)`);
if (problems.length) {
  console.error(problems.map((p) => `FAIL ${p}`).join("\n"));
  process.exit(1);
}
console.log("dist check passed: no mock or contract chunk, no example.org, no sample contract text outside the landing demo");
