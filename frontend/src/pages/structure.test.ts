import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

/* 4-B.3 (FrontendDesign.md 17.9): the page structure (DN to DT) and the state motion (DZ). These are source-level checks, like
   copy.test.ts and Reader.test.ts: the numbers (padding, gaps, heights) are measured in a browser and recorded in 17.9. */

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
const layout = read("../components/Layout.tsx");
const css = read("../index.css");
const landing = read("./Landing.tsx");
const hero = read("./landing/HeroDemo.tsx");
const header = read("../components/AppHeader.tsx");
const footer = read("../components/AppFooter.tsx");
const root = read("../app/Root.tsx");
const start = read("./Start.tsx");
const dropzone = read("../components/UploadDropzone.tsx");
const reader = read("./Reader.tsx");
const confidenceBand = read("../components/ConfidenceBand.tsx");

/** One rule of index.css, from its selector to the closing brace. */
const rule = (selector: string) => css.match(new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{[^}]*\\}`))?.[0] ?? "";

/* DN. One padding for every section left the content of a short section floating in a 256 px band. A section that holds one heading and
   a short block takes 48 and 64 px, and the rest take 64, 80 and 96. Every value is on the 4 px scale. */

test("SectionFrame takes compact: 48 and 64 px for a short section, 64, 80 and 96 for the rest", () => {
  assert.match(layout, /compact\?: boolean/);
  assert.match(layout, /compact \? "py-12 md:py-16" : "py-16 md:py-20 lg:py-24"/);
  assert.doesNotMatch(layout, /md:py-24 lg:py-32/);
});

test("the short landing sections are compact, and the long ones are not", () => {
  for (const id of ["problem", "privacy", "questions", "start"]) assert.match(landing, new RegExp(`<Section(Frame)?\\s+compact\\s+id="${id}"`), id);
  for (const id of ["how", "lawyer", "categories"]) assert.match(landing, new RegExp(`<Section(Frame)?\\s+id="${id}"`), id);
});

/* DO. § 1 is one paragraph and a source note, so most of its aside was empty. The aside holds a ledger of the three CUAD figures the
   paragraph already states, set as ruled rows and hidden from assistive technology like the other specimens. */

test("the § 1 aside is a ledger of the three CUAD figures with the source note under it", () => {
  assert.match(landing, /\["41", "kinds of clause"\]/);
  assert.match(landing, /\["510", "commercial contracts"\]/);
  assert.match(landing, /\["13,000\+", "annotations"\]/);
  assert.match(landing, /<dl[^>]*>/);
  assert.match(landing, /<Specimen>\s*<Ledger \/>\s*<\/Specimen>/);
  assert.match(landing, /Source: CUAD v1, The Atticus Project\. Licence CC BY 4\.0\./);
  const figures = landing.match(/with more than 13,000 annotations/);
  assert.ok(figures, "the paragraph states the same figures in words");
});

/* DP. A step's text, number and visual share one midline from 1280 px, and each step is a ruled row. */

test("each step is a ruled row centred on its visual from 1280 px", () => {
  assert.match(layout, /center\?: boolean/);
  assert.match(layout, /margin-grid-center/);
  assert.match(css, /@media \(min-width: 1280px\)\s*\{\s*\.margin-grid-center \{ align-items: center; \}/);
  const steps = landing.match(/<ol[^>]*>[\s\S]*?<\/ol>/)?.[0] ?? "";
  assert.match(steps, /border-t/);
  assert.match(steps, /<MarginGrid center /);
  assert.doesNotMatch(steps, /gap-12/);
});

/* DQ. The headline block, the example control, the sheet, its caption and the panel are one grid. The panel sits in the aside from the
   headline's top from 1280 px. Reading order is headline, control, sheet, caption, panel. */

test("the hero is one grid: headline block, example control, sheet, caption, panel", () => {
  assert.match(landing, /<HeroDemo>\s*<h1 id="hero-title"/);
  assert.doesNotMatch(landing, /<div className="mt-10 md:mt-14">\s*<HeroDemo \/>/);
  const order = ["hero-head", "hero-control", "hero-sheet", "hero-caption", "hero-panel-cell"].map((c) => hero.indexOf(c));
  assert.ok(order.every((n) => n > -1), `every cell is drawn ${order}`);
  assert.deepEqual([...order].sort((a, b) => a - b), order, "in reading order");
  assert.match(css, /\.hero-grid \{/);
  assert.doesNotMatch(hero, /<MarginGrid/);
});

/* The panel (777 px at 1280) is taller than the three rows beside it. It spans a fourth row that takes the leftover height, so the rows
   of the headline block, the control and the sheet keep their own heights and the gaps between them stay as set. */

test("from 1280 the panel spans a fourth row that takes the extra height, and the caption stays at the top of its row", () => {
  const wide = css.match(/@media \(min-width: 1280px\) \{\s*(?:\/\*[\s\S]*?\*\/\s*)?\.hero-grid \{[\s\S]*?\n  \}\n/)?.[0] ?? "";
  assert.ok(wide.length > 100, "the 1280 hero block was found");
  assert.match(wide, /grid-template-rows: auto auto auto 1fr/);
  assert.match(wide, /\.hero-panel-cell \{[^}]*grid-row: 1 \/ span 4/);
  assert.match(css, /\.hero-grid > \.hero-caption \{[^}]*align-self: start/);
});

test("the example control is a row above the sheet: the label in secondary ink at the left, Next example in size M at the right", () => {
  const control = hero.match(/className="hero-control[\s\S]*?<\/div>\s*\n/)?.[0] ?? "";
  assert.match(control, /Example \{i \+ 1\} of \{HERO_EXAMPLES\.length\}/);
  assert.match(control, /color: "var\(--ink-secondary\)"/);
  assert.doesNotMatch(control, /ink-tertiary/);
  assert.match(control, /<Button variant="secondary" size="m"/);
  assert.match(control, /Next example/);
});

/* DR. The sizes next to the headings come up to body/md (15 on 24) and label/md (14 on 20). Nothing leaves the scale. */

test("the hero lines, the figure caption and the Start notes use sizes on the type scale, none at 13 px", () => {
  assert.match(landing, /<p className="mt-4 text-\[15px\] leading-\[24px\]"[^>]*>\{PRIVACY_LINE\}<\/p>/);
  assert.match(hero, /<figcaption className="mt-3 text-\[14px\] leading-\[20px\]"/);
  for (const src of [landing, hero, start]) assert.doesNotMatch(src, /text-\[13px\]/);
  assert.match(start, /<p className="text-\[15px\] leading-\[24px\]"[^>]*>\s*Your contract is processed in memory/);
});

/* DS. The header and the footer take the page width, so the logo, the page and the footer text share a left edge at 1920 and 2560 px.
   The section rules stay full width. The Reader keeps its full-width panes. */

test("the header and the footer sit on the page width, and the Reader's header does not", () => {
  assert.match(header, /contained\?: boolean/);
  assert.match(header, /contained \? "container-page [^"]*" : /);
  assert.match(footer, /className="container-page/);
  assert.match(root, /contained=\{!inReader\}/);
});

/* DT. Step 1: one notes block under the dropzone, in 15 px lines, so a visitor reads the privacy line, the public-demo line and the
   sample link as one thing. */

test("Start step 1 holds one notes block: the privacy line, then the public-demo line and the sample link", () => {
  const notes = start.match(/\{\/\* Notes block[\s\S]*?<DemoNotice \/>[\s\S]*?<\/div>/)?.[0] ?? "";
  assert.ok(notes.length > 100, "the notes block was found");
  assert.ok(notes.indexOf("Your contract is processed in memory") < notes.indexOf("<DemoNotice />"));
  assert.match(start, /<div className="flex flex-col gap-4">\s*<div\s+onDragOver/);
});

/* The band in the hero's 320 px panel. A flex row counts its items' set widths in its minimum width, so the 160 px track never gave way
   and the label ran past the card edge. The row wraps instead: the label drops under the track when the two do not fit, and a panel
   wide enough for both (the Reader's 400 px) keeps one line. */

test("the confidence band's row wraps, so the label is never cut off in a narrow panel", () => {
  const row = confidenceBand.match(/<div className="(flex [^"]*)">\s*\{track\}/)?.[1] ?? "";
  assert.match(row, /\bflex-wrap\b/);
  assert.match(row, /\bgap-y-1\b/);
  assert.match(confidenceBand, /flexShrink: 0,\s*whiteSpace: "nowrap"/, "the label itself still never breaks");
});

/* DZ. Motion explains a change of state, and only that. The rules are in DesignSystem.md 3.5 and 6. */

test("there is one reduced-motion block, and the new motions are inside what it covers", () => {
  assert.equal(css.match(/@media \(prefers-reduced-motion/g)?.length, 1);
  const reduced = css.match(/@media \(prefers-reduced-motion: reduce\) \{[\s\S]*?\n\}\n/)?.[0] ?? "";
  assert.match(reduced, /animation-duration: 0\.01ms !important/);
  assert.match(reduced, /transition-duration: 0\.01ms !important/);
});

test("a new step in the start flow fades in and rises 8 px over the state duration, once per change", () => {
  assert.match(start, /<div key=\{step\} className="ca-step/);
  assert.match(css, /@keyframes ca-step-in \{\s*from \{ opacity: 0; transform: translateY\(8px\); \}\s*\}/);
  assert.match(rule(".ca-step"), /animation: ca-step-in var\(--dur-state\) var\(--ease-out\) backwards/);
  // The step heading stays outside the keyed block, so focus keeps its element across a change.
  assert.ok(start.indexOf('id="step-title"') < start.indexOf("<div key={step}"));
});

test("the dropzone grows by 1 percent while a file is over it, and the accepted file's icon pops in", () => {
  assert.match(dropzone, /transform: tone === "drag" \? "scale\(1\.01\)" : "none"/);
  assert.match(dropzone, /transition: "transform var\(--dur-press\) var\(--ease-out\)"/);
  assert.match(dropzone, /<span className="ca-accept"/);
  assert.match(rule(".ca-accept"), /--pop-from: 0\.9/);
  assert.match(rule(".ca-accept"), /animation: ca-pop var\(--dur-state\) var\(--ease-out\) backwards/);
});

test("the review band draws the work done as a bar that scales from the left, and the bar says nothing to assistive technology", () => {
  assert.match(reader, /<span aria-hidden className="ca-bar"/);
  assert.match(reader, /"--fill": Math\.min\(1, job\.completed_units \/ job\.total_units\)/);
  const bar = rule(".ca-bar");
  assert.match(bar, /transform: scaleX\(var\(--fill, 0\)\)/);
  assert.match(bar, /transform-origin: left/);
  assert.match(bar, /transition: transform var\(--dur-state\) var\(--ease-out\)/);
});

test("the new motions animate transform and opacity only", () => {
  const blocks = [rule(".ca-step"), rule(".ca-accept"), rule(".ca-bar"), css.match(/@keyframes ca-step-in \{[\s\S]*?\n\}/)?.[0] ?? ""];
  for (const b of blocks) {
    assert.ok(b.length > 20, "the block was found");
    assert.doesNotMatch(b, /(transition|animation)[^;]*\b(width|height|top|left|right|bottom|margin|padding|background|border|color)\b/);
  }
});
