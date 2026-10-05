import { useState } from "react";
import Button from "../../components/Button";
import ClauseDetailPanel, { REVIEW_CANDIDATE_NOTE, type PanelData } from "../../components/ClauseDetailPanel";
import { MarginGrid } from "../../components/Layout";
import MarginRuler from "../../components/MarginRuler";
import RuleFlagCard from "../../components/RuleFlagCard";
import { markStyle } from "../../components/SpanHighlight";
import { HERO_EXAMPLES, splitExcerpt, type HeroExample } from "./heroExamples";

/* The live demo: a short excerpt of the sample contract where a finding inks in,
   the ruler marks it and the clause panel opens beside it. It plays once per
   example (index.css, .hero-demo) and "Next example" remounts it with a new key.
   Everything here is the final state, and the CSS keyframes only add the start. */

const STATUS_WORD = { found: "Found", review: "Needs a lawyer" } as const;

/* Only what is verified: the quote with its offsets, the category, the status,
   the direction, the confidence band as a word and the statute note. No decimal
   and no case law, because neither is real data yet. */
function panelData(e: HeroExample): PanelData {
  return {
    title: e.category,
    status: e.status,
    sectionPath: e.sectionPath,
    offsets: { start: e.start, end: e.end },
    quote: e.quote,
    polarity: e.polarity,
    confidence: e.band,
    reviewNote: e.status === "review" ? REVIEW_CANDIDATE_NOTE : undefined,
    ruleFlags: e.statute && <RuleFlagCard citation={e.statute.citation} note={e.statute.note} />,
  };
}

export default function HeroDemo() {
  const [i, setI] = useState(0);
  const e = HERO_EXAMPLES[i];
  const { before, mark, after } = splitExcerpt(e);
  // The tick sits at the finding's midpoint by character count. Exact line geometry would need measuring the text.
  const at = ((e.start + e.end) / 2 - e.excerptStart) / [...e.excerpt].length;

  return (
    <div className="hero-demo">
      <MarginGrid
        margin={
          <div className="flex flex-col items-start gap-3">
            <p className="t-overline" style={{ color: "var(--ink-tertiary)" }}>
              Example {i + 1} of {HERO_EXAMPLES.length}
            </p>
            <p className="t-marginal-note">{e.caption}</p>
            <Button variant="secondary" size="s" onClick={() => setI((i + 1) % HERO_EXAMPLES.length)}>
              Next example
            </Button>
            <p className="sr-only" aria-live="polite">
              Example {i + 1} of {HERO_EXAMPLES.length}: {e.category}, {STATUS_WORD[e.status]}
            </p>
          </div>
        }
        aside={
          <div key={i} role="group" aria-label="Finding detail" className="hero-panel">
            <ClauseDetailPanel titleAs="p" data={panelData(e)} />
          </div>
        }
      >
        <figure key={i} className="hero-sheet m-0">
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
            <p style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: "30px", color: "var(--ink-primary)" }}>
              {before}
              <span className="sr-only">
                Finding, {STATUS_WORD[e.status]}: {e.category}.{" "}
              </span>
              <mark
                className="ca-mark ca-ink"
                style={{ ...markStyle(e.status, false), color: "inherit", paddingBottom: 3 }}
              >
                {mark}
              </mark>
              {after}
            </p>
          </div>
          <figcaption className="mt-3 text-[13px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
            Sample contract, fictional parties. Reading as the Provider.
          </figcaption>
        </figure>
      </MarginGrid>
    </div>
  );
}
