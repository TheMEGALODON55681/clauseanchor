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
