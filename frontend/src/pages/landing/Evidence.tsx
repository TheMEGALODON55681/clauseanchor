import JudgmentCard, { type Authority } from "../../components/JudgmentCard";
import { Section } from "../../components/Layout";
import { useReveal } from "../../lib/useReveal";

/* One verbatim passage from the corpus the product serves. Landing.tsx holds
   the passage and renders this section only when it is set. */
export type EvidencePassage = {
  caseName: string;
  court: string;
  year: number;
  citation: string;
  /** Verbatim. Never paraphrased. */
  text: string;
  sourceUrl: string;
  authority: Authority;
};

export default function Evidence({ passage, mark }: { passage: EvidencePassage; mark: string }) {
  const card = useReveal<HTMLDivElement>();
  return (
    <Section
      id="evidence"
      labelledBy="evidence-title"
      mark={mark}
      aside={
        <div ref={card}>
          <JudgmentCard authority={passage.authority} passage={passage} />
        </div>
      }
    >
      <h2 id="evidence-title" className="t-display-md">Evidence you can check.</h2>
      <p className="t-prose-lg mt-4">
        Case law appears as a quoted passage with its court, year and citation, so you can look it up yourself. Nothing is paraphrased.
      </p>
    </Section>
  );
}
