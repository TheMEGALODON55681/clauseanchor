import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

/* This build returns no statute notes and no judgment passages, and it scores nothing. The public copy and the hero examples must
   not promise them (4-C1 live run, defect 7). These are source-level checks, like Reader.test.ts. */

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
const landing = read("./Landing.tsx");
const how = read("./HowItWorks.tsx");
const start = read("./Start.tsx");
const summary = read("./start/Summary.tsx");
const demo = read("./landing/HeroDemo.tsx");
const examples = read("./landing/heroExamples.ts");
const footer = read("../components/AppFooter.tsx");
const notice = read("../components/NoticeBanner.tsx");

const OVER_PROMISES = [/Indian judgment/i, /case law/i, /Indian law review/i, /Review under Indian law/i, /cite Indian statutes/i, /published judgments/i, /confidence band/i, /lists the measured/i];

test("the hero examples carry no confidence badge, no statute note and no Section 27 text", () => {
  assert.doesNotMatch(examples, /\bband\b|statute|Section 27|Indian Contract Act|India-specific review/i);
  assert.doesNotMatch(demo, /confidence:|ruleFlags|RuleFlagCard|\.band|\.statute/);
});

test("the landing page promises quoted text only, and says plainly what comes in a later build", () => {
  for (const re of OVER_PROMISES) assert.doesNotMatch(landing, re, String(re));
  assert.match(landing, /Every finding quotes your text\. Where it is unsure, it says Needs a lawyer\./);
  const faq = landing.match(/\["Which law does it cover\?", "([^"]*)"\]/)?.[1] ?? "";
  assert.match(faq, /later build/);
  const does = landing.match(/const DOES = \[([\s\S]*?)\];/)?.[1] ?? "";
  assert.match(does, /later build/);
});

test("How it works says that statute notes and judgment passages come in a later build", () => {
  const section = how.match(/id: "law"[\s\S]*?id: "role"/)?.[0] ?? "";
  assert.ok(section.length > 100, "the India section was found");
  for (const re of OVER_PROMISES) assert.doesNotMatch(section, re, String(re));
  assert.doesNotMatch(section, /StatuteTag|Section 27/);
  assert.match(section, /later build/);
  assert.doesNotMatch(how, /used for passage retrieval/);
});

test("the legal sentence, in the footer, the notice and the FAQ, points only to the contract", () => {
  for (const src of [footer, notice, landing]) {
    assert.match(src, /ClauseAnchor points to text in your contract\. It does not tell you what the law requires\./);
  }
});

test("How it works says confidence is not validated in this build and is measured in a later one", () => {
  const section = how.match(/id: "confidence"[\s\S]*?id: "law"/)?.[0] ?? "";
  assert.ok(section.length > 100, "the confidence section was found");
  assert.match(section, /This build does not validate its confidence yet\./);
  assert.match(section, /Confidence not validated/);
  assert.match(section, /later build/);
  assert.doesNotMatch(section, /threshold|clears|tested against/i);
  assert.doesNotMatch(section, /status="found"/);
});

test("the switch and the summary line are named for the categories, not for a law", () => {
  assert.match(start, /label="Include India-specific categories"/);
  assert.match(summary, /"India-specific categories on" : "India-specific categories off"/);
  for (const re of [/Review under Indian law/, /Indian law review/]) {
    assert.doesNotMatch(start, re);
    assert.doesNotMatch(summary, re);
  }
});

test("the Reader's empty panel does not promise case law", () => {
  assert.doesNotMatch(read("./Reader.tsx"), /and any case law/);
});
