import Link from "./Link";

/* The paper and the rule run edge to edge. The text sits on the page width, so it shares a left edge with the header and the page. */
export default function AppFooter({ sampleMode = false, creditsHref = "#" }: { sampleMode?: boolean; creditsHref?: string }) {
  return (
    <footer className="app-footer" style={{ background: "var(--paper-sheet)", borderTop: "1px solid var(--rule-default)" }}>
      <div className="container-page flex flex-col gap-2 py-5">
        <p style={{ fontSize: 13, lineHeight: "20px", color: "var(--ink-secondary)", maxWidth: "72ch" }}>
          Not legal advice. ClauseAnchor points to text in your contract. It does not tell you what the law requires.
        </p>
        <p style={{ fontSize: 12, color: "var(--ink-tertiary)" }}>
          Clause data: CUAD by The Atticus Project (CC BY 4.0). Model: RoBERTa-base.{" "}
          {sampleMode && "Sample mode: showing a prepared example. "}
          <Link variant="inline" href={creditsHref}>Data sources and credits</Link>
        </p>
      </div>
    </footer>
  );
}
