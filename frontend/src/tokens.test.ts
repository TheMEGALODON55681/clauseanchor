import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

/* Reads the real token file, so a later edit that drops a pair below the bar
   fails here. The pairs are the colour changes in FrontendDesign.md 5.4. */

const css = readFileSync(new URL("./index.css", import.meta.url), "utf8");

function block(selector: RegExp): Record<string, string> {
  const m = css.match(selector);
  assert.ok(m, `block not found: ${selector}`);
  const vars: Record<string, string> = {};
  for (const [, name, value] of m[1].matchAll(/--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) vars[name] = value.toLowerCase();
  return vars;
}

const light = block(/:root,\s*\.light\s*\{([\s\S]*?)\n\}/);
const dark = block(/\.dark\s*\{([\s\S]*?)\n\}/);

function luminance(hex: string): number {
  const channel = (i: number) => {
    const v = parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(0) + 0.7152 * channel(1) + 0.0722 * channel(2);
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

type Pair = { fg: string; bg: string; min: number };

function check(theme: Record<string, string>, label: string, pairs: Pair[]) {
  for (const { fg, bg, min } of pairs) {
    assert.ok(theme[fg], `${label}: missing --${fg}`);
    assert.ok(theme[bg], `${label}: missing --${bg}`);
    const r = ratio(theme[fg], theme[bg]);
    assert.ok(r >= min, `${label}: --${fg} on --${bg} is ${r.toFixed(2)}, needs ${min}`);
  }
}

const surfaces = ["paper-base", "paper-sheet", "paper-sunken"];
const on = (fg: string, bgs: string[], min: number): Pair[] => bgs.map((bg) => ({ fg, bg, min }));

test("light: tertiary ink reaches 4.5 on every surface", () => {
  check(light, "light", on("ink-tertiary", surfaces, 4.5));
});

test("dark: tertiary ink reaches 4.5 on every surface", () => {
  check(dark, "dark", on("ink-tertiary", surfaces, 4.5));
});

/* Tertiary ink also sits on tinted fills: the selected row, a status chip, a metric on a weak row.
   Every token whose name ends in -bg, plus anchor-100, is a fill that text can land on. */
test("tertiary ink reaches 4.5 on every tinted fill in both themes", () => {
  for (const [label, theme] of [["light", light], ["dark", dark]] as const) {
    const fills = Object.keys(theme).filter((k) => k.endsWith("-bg") || k === "anchor-100");
    assert.ok(fills.length >= 9, `${label}: found ${fills.length} fills`);
    check(theme, label, on("ink-tertiary", fills, 4.5));
  }
});

test("light: absent, neutral and unresolved text reach 4.5 on their chips", () => {
  check(light, "light", [
    ...on("status-absent-fg", ["status-absent-bg", "paper-sheet"], 4.5),
    ...on("polarity-neutral-fg", ["polarity-neutral-bg", "paper-sheet"], 4.5),
    ...on("polarity-unresolved-fg", ["paper-sheet"], 4.5),
  ]);
});

test("light: the three grey texts stay one value", () => {
  assert.equal(light["status-absent-fg"], light["polarity-neutral-fg"]);
  assert.equal(light["status-absent-fg"], light["polarity-unresolved-fg"]);
});

test("light: control borders reach 3 on every surface", () => {
  check(light, "light", on("control-border", surfaces, 3));
});

test("dark: control borders reach 3 on every surface", () => {
  check(dark, "dark", on("control-border", surfaces, 3));
});

test("the unvalidated chip border reaches 3 on the sheet in both themes", () => {
  check(light, "light", on("status-unvalidated-border", ["paper-sheet"], 3));
  check(dark, "dark", on("status-unvalidated-border", ["paper-sheet"], 3));
});

test("the focus ring reaches 3 on every surface in both themes", () => {
  check(light, "light", on("focus-ring", surfaces, 3));
  check(dark, "dark", on("focus-ring", surfaces, 3));
});

/* A plain status (icon and words, no fill) sits straight on its row: the sunken sidebar, the
   selected row's anchor-100 tint and the hovered row's sheet (CategoryRow, StatusChip plain). */
const rowSurfaces = ["paper-sunken", "anchor-100", "paper-sheet"];
const plainStatus = ["found", "review", "unvalidated", "absent", "unavailable"].map((s) => `status-${s}-fg`);

test("light: plain status text reaches 4.5 on the sunken, selected and hovered rows", () => {
  for (const fg of plainStatus) check(light, "light", on(fg, rowSurfaces, 4.5));
});

test("dark: plain status text reaches 4.5 on the sunken, selected and hovered rows", () => {
  for (const fg of plainStatus) check(dark, "dark", on(fg, rowSurfaces, 4.5));
});

/* The reading measure (DesignSystem.md 3.4) is one token. The Reader sheet and the hero
   sheet both read it, so the two pages set the same line. Source Serif 4 at 17 px averages
   7.83 px a character, and a ragged full line fills about 93 percent of its column
   (measured in FE-5), so 68 to 80 characters is a column of 572 to 673 px. */
test("one --measure token holds a column that sets a 68 to 80 character line", () => {
  const m = css.match(/--measure:\s*(\d+)px;/);
  assert.ok(m, "--measure is defined in px");
  const px = Number(m[1]);
  assert.ok(px >= 572 && px <= 673, `--measure is ${px}px, needs 572 to 673`);
});

test("the Reader and the hero sheet both set their text column from --measure", () => {
  for (const file of ["pages/Reader.tsx", "pages/landing/HeroDemo.tsx"]) {
    const src = readFileSync(new URL(`./${file}`, import.meta.url), "utf8");
    assert.ok(src.includes("var(--measure)"), `${file} reads var(--measure)`);
  }
});

/* The overlay enters (FrontendDesign.md 17.6) take their time from the motion tokens, so none can
   drift to a raw value. The one reduced-motion rule zeroes every animation, which is the only
   guard they have, so a change that drops it from `*` fails here. */
test("overlay enter classes read the motion tokens and the components use them", () => {
  const uses: Record<string, string> = {
    ".ca-dialog": "components/ConfirmDialog.tsx",
    ".ca-menu": "components/DropdownMenu.tsx",
    ".ca-toast": "components/Toast.tsx",
  };
  for (const [selector, file] of Object.entries(uses)) {
    const m = css.match(new RegExp(`${selector.replace(".", "\.")} \{([^}]*)\}`));
    assert.ok(m, `${selector} is defined`);
    assert.match(m[1], /animation:[^;]*var\(--dur-[a-z]+\)[^;]*var\(--ease-out\)/, `${selector} reads a --dur token and --ease-out`);
    const src = readFileSync(new URL(`./${file}`, import.meta.url), "utf8");
    assert.ok(src.includes(selector.slice(1)), `${file} uses ${selector}`);
  }
});

test("one reduced-motion rule zeroes the duration and delay of every animation", () => {
  const m = css.match(/@media \(prefers-reduced-motion: reduce\) \{\s*\*,[^{]*\{([^}]*)\}/);
  assert.ok(m, "the rule selects *");
  assert.match(m[1], /animation-duration:\s*0\.01ms !important/);
  assert.match(m[1], /animation-delay:\s*0ms !important/);
});
