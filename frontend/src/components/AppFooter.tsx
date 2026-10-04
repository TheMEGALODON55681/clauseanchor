import Link from "./Link";

export default function AppFooter({ sampleMode = false, creditsHref = "#" }: { sampleMode?: boolean; creditsHref?: string }) {
  return (
    <footer
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        padding: "20px",
        background: "var(--paper-sheet)",
        borderTop: "1px solid var(--rule-default)",
      }}
    >
      <p style={{ fontSize: 13, lineHeight: "20px", color: "var(--ink-secondary)", maxWidth: "72ch" }}>
        Not legal advice. ClauseAnchor points to text in your contract and in published judgments. It does not tell you what the law requires.
      </p>
      <p style={{ fontSize: 12, color: "var(--ink-tertiary)" }}>
        Case data: CUAD by The Atticus Project (CC BY 4.0), OpenNyaya, NyayaAnumana.{" "}
        {sampleMode && "Sample mode: showing a prepared example. "}
        <Link variant="inline" href={creditsHref}>Data sources and credits</Link>
      </p>
    </footer>
  );
}
