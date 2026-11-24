import { useState } from "react";
import type { ReactNode } from "react";
import Button from "../../components/Button";
import ClauseDetailPanel, { REVIEW_CANDIDATE_NOTE, type PanelData } from "../../components/ClauseDetailPanel";
import MarginRuler from "../../components/MarginRuler";
import { markStyle } from "../../components/SpanHighlight";
import { HERO_EXAMPLES, splitExcerpt, type HeroExample } from "./heroExamples";

/* The first screen as one composition: the headline block (the children), the example control, a short excerpt of the sample contract
   where a finding inks in, the ruler tick and the clause panel. They share one grid (index.css). From 1280px the panel sits in the
   aside beside the headline block and the sheet. It plays once per example and "Next example" remounts the sheet and the panel with
   a new key. Everything here is the final state, and the CSS keyframes only add the start. */

/* What this build serves, drawn the way the Reader draws a review candidate: the quote with its offsets, the category, Needs a lawyer and
   Confidence not validated. No score, no statute note and no case law, because none is real data yet. */
function panelData(e: HeroExample): PanelData {
  return {
    title: e.category,
    status: e.status,
    sectionPath: e.sectionPath,
    offsets: { start: e.start, end: e.end },
    quote: e.quote,
    confidence: "unvalidated",
    reviewNote: REVIEW_CANDIDATE_NOTE,
  };
}

export default function HeroDemo({ children }: { children: ReactNode }) {
  const [i, setI] = useState(0);
  const e = HERO_EXAMPLES[i];
  const { before, mark, after } = splitExcerpt(e);
  // The tick sits at the finding's midpoint by character count. Exact line geometry would need measuring the text.
  const at = ((e.start + e.end) / 2 - e.excerptStart) / [...e.excerpt].length;

  return (
    <div className="hero-demo hero-grid">
      <div className="hero-head">{children}</div>

      <div className="hero-control flex items-center justify-between gap-4">
        <p className="t-overline" style={{ color: "var(--ink-secondary)" }}>
          Example {i + 1} of {HERO_EXAMPLES.length}
        </p>
        <Button variant="secondary" size="m" onClick={() => setI((i + 1) % HERO_EXAMPLES.length)}>
          Next example
        </Button>
        <p className="sr-only" aria-live="polite">
          Example {i + 1} of {HERO_EXAMPLES.length}: {e.category}, Needs a lawyer
        </p>
      </div>

      <figure key={i} className="hero-sheet hero-sheet-cell m-0">
        <div
          className="flex gap-3 px-4 py-5 sm:px-6"
          style={{ background: "var(--paper-sheet)", border: "1px solid var(--rule-default)", borderRadius: "var(--radius-lg)" }}
        >
          <div aria-hidden className="hidden sm:flex [&>div]:flex-1">
            <MarginRuler
              height="100%"
              viewport={false}
              caption=""
              marks={[{ at, status: e.status, label: e.category }]}
            />
          </div>
          <p style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: "30px", color: "var(--ink-primary)", maxWidth: "var(--measure)", minWidth: 0 }}>
            {before}
            <span className="sr-only">
              Finding, Needs a lawyer: {e.category}.{" "}
            </span>
            <mark
              className="ca-mark ca-ink"
              style={{ ...markStyle(e.status), color: "inherit", paddingBottom: 3 }}
            >
              {mark}
            </mark>
            {after}
          </p>
        </div>
        <figcaption className="mt-3 text-[14px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
          Sample contract, fictional parties.
        </figcaption>
      </figure>

      <p className="hero-caption t-marginal-note">{e.caption}</p>

      <div key={i} role="group" aria-label="Finding detail" className="hero-panel hero-panel-cell">
        <ClauseDetailPanel titleAs="p" data={panelData(e)} />
      </div>
    </div>
  );
}
