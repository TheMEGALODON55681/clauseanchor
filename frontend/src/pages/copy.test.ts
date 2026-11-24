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
const expired = read("./Expired.tsx");
const errors = read("../api/errors.ts");
const demoNotice = read("../components/DemoNotice.tsx");

const OVER_PROMISES = [/Indian judgment/i, /case law/i, /Indian law review/i, /Review under Indian law/i, /cite Indian statutes/i, /published judgments/i, /confidence band/i, /lists the measured/i];

test("the hero examples carry no statute note and no Section 27 text, and the panel shows Confidence not validated, as the Reader does", () => {
  assert.doesNotMatch(examples, /\bband\b|statute|Section 27|Indian Contract Act|India-specific review/i);
  assert.doesNotMatch(demo, /ruleFlags|RuleFlagCard|\.band|\.statute/);
  assert.match(demo, /confidence: "unvalidated"/);
  assert.doesNotMatch(demo, /confidence: "(?!unvalidated")/, "no other band");
});

/* 4-B.3, DU. The live build runs 41 categories. The five India-specific ones are listed as coming later (docs/ml/CategoryCatalogue.md),
   every finding is a review candidate, and the credits name what the build uses. */

test("the landing page and How it works say 41 categories run, and none says 46", () => {
  for (const src of [landing, how]) assert.doesNotMatch(src, /\b46\b/);
  assert.match(landing, /against 41 listed clause categories/);
  assert.match(landing, /Finds clauses in 41 listed categories/);
  assert.match(how, /title: "Looking for 41 kinds of clause"/);
  assert.match(landing, /come in a later build|coming later/);
});

test("no public page calls a finding Found, or says how confident the build is", () => {
  assert.doesNotMatch(landing, /status="found"|markStyle\("found"\)/);
  assert.doesNotMatch(landing, /how confident it is|When the evidence for a category is close/);
  assert.doesNotMatch(how, /When the evidence for a category is close/);
  assert.match(landing, /Marks every finding Needs a lawyer, and shows no score/);
});

test("the credits and the footer name what the build uses and nothing it does not", () => {
  for (const src of [how, footer, landing]) assert.doesNotMatch(src, /OpenNyaya|NyayaAnumana|InLegalBERT/);
  const credits = how.match(/id: "credits"[\s\S]*$/)?.[0] ?? "";
  assert.match(credits, /CUAD<\/strong> by The Atticus Project, licensed under CC BY 4\.0/);
  assert.match(credits, /RoBERTa-base/);
  assert.match(credits, /FacebookAI\/roberta-base/);
  assert.doesNotMatch(credits, /licen[cs]ed under (MIT|Apache)/i, "the repository states no licence for the base model");
  assert.match(footer, /Clause data: CUAD by The Atticus Project \(CC BY 4\.0\)\. Model: RoBERTa-base\./);
});

/* SA4: the Expired page says why a session can end early. No heartbeat and no pinger, because a request every few minutes keeps the
   replica awake and costs credit (docs/app/SystemAudit.md 4.3). */

test("the Expired page says the demo server sleeps after a few quiet minutes and clears its memory, and the deleted page does not", () => {
  assert.match(expired, /demo server sleeps/);
  assert.match(expired, /after a few quiet minutes/);
  assert.match(expired, /memory is cleared/);
  assert.match(expired, /Upload it again/);
  assert.match(expired, /can take a minute or more/);
  assert.doesNotMatch(expired, /heartbeat|ping/i);
  assert.match(expired, /The file, its text and the review were removed from the server\. Nothing was kept\./);
  assert.match(errors, /SESSION_INVALID: \{ ui: "expired", message: "[^"]*demo server sleeps[^"]*" \}/);
});

/* SA16 and the sample: one plain line near the call and near the dropzone, and a fictional agreement to download. */

test("the public demo line and the sample link are one component, used on the landing page and on Start", () => {
  assert.match(demoNotice, /This is a public demo\. Use a sample or a public contract, not a confidential one\./);
  assert.match(demoNotice, /href="\/samples\/fictional-services-agreement\.docx"/);
  assert.match(demoNotice, /\bdownload\b/);
  assert.match(demoNotice, /Download a fictional sample agreement/);
  assert.match(demoNotice, /\(DOCX, 5 KB\)/);
  for (const src of [landing, start]) {
    assert.match(src, /<DemoNotice \/>/);
    assert.doesNotMatch(src, /The sample contract is not available in this build yet\./);
  }
});

test("the sample agreement is a small DOCX in public/samples, so the build serves it as a plain file", () => {
  const file = readFileSync(new URL("../../public/samples/fictional-services-agreement.docx", import.meta.url));
  assert.equal(file.subarray(0, 2).toString("latin1"), "PK", "a DOCX is a zip file");
  assert.ok(file.length > 1000 && file.length < 10 * 1024, `${file.length} bytes`);
});

test("the landing page promises quoted text only, and says plainly what comes in a later build", () => {
  for (const re of OVER_PROMISES) assert.doesNotMatch(landing, re, String(re));
  assert.match(landing, /Every finding quotes your text\. In this build each one is marked Needs a lawyer\./);
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
