import Button from "./Button";
import { InfoIcon, PersonWithDocIcon } from "./icons";

export type ScopeVariant = "complete" | "processing-incomplete" | "sample-mode";

type ScopePanelProps = {
  variant?: ScopeVariant;
  categoryCount?: number;
  catalogueVersion?: string;
  support?: { validated: number; pooled: number; notValidated: number };
  limitations?: string[];
  onViewList?: () => void;
};

const SCOPE_TEXT =
  "This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment.";

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, fontSize: 12, color: "var(--ink-secondary)" }}>
      <span>{label}</span>
      <span style={{ fontFamily: "var(--font-mono)", color: "var(--ink-primary)" }}>{value}</span>
    </div>
  );
}

/* Compact scope card pinned to the top of the category sidebar. Never a verdict. */
export default function ScopePanel({
  variant = "complete",
  categoryCount = 46,
  catalogueVersion = "cat-2026.09-r1.1",
  support = { validated: 27, pooled: 14, notValidated: 5 },
  limitations = [],
  onViewList,
}: ScopePanelProps) {
  return (
    <section
      aria-label="Review scope"
      style={{
        background: "var(--paper-sheet)",
        border: "1px solid var(--rule-default)",
        borderLeftWidth: 4,
        borderLeftColor: "var(--anchor-600)",
        borderRadius: "var(--radius-md)",
        padding: "10px 12px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--anchor-600)" }}>
        <InfoIcon size={16} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-primary)" }}>Review scope</span>
        <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)" }}>
          {catalogueVersion}
        </span>
      </div>
      <p style={{ fontSize: 12, lineHeight: "17px", color: "var(--ink-secondary)" }}>{SCOPE_TEXT}</p>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <span style={{ fontSize: 12, color: "var(--ink-primary)" }}>
          <span style={{ fontFamily: "var(--font-mono)" }}>{categoryCount}</span> categories reviewed
        </span>
        <Button variant="tertiary" size="s" onClick={onViewList}>
          View list
        </Button>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Row label="Validated" value={support.validated} />
        <Row label="Pooled" value={support.pooled} />
        <Row label="Not validated" value={support.notValidated} />
      </div>

      {variant === "processing-incomplete" && (
        <div
          style={{
            display: "flex",
            gap: 6,
            alignItems: "flex-start",
            fontSize: 12,
            lineHeight: "17px",
            color: "var(--status-review-fg)",
            background: "var(--status-review-bg)",
            border: "1px solid var(--status-review-border)",
            borderRadius: "var(--radius-sm)",
            padding: "6px 8px",
          }}
        >
          <span style={{ display: "inline-flex", marginTop: 1 }}><PersonWithDocIcon size={14} /></span>
          Processing incomplete: some categories or pages were not finished
        </div>
      )}
      {variant === "sample-mode" && (
        <div style={{ fontSize: 12, color: "var(--status-review-fg)" }}>Sample mode: showing a prepared example.</div>
      )}
      {limitations.map((l) => (
        <div
          key={l}
          style={{ fontSize: 12, lineHeight: "17px", color: "var(--ink-secondary)", borderTop: "1px solid var(--rule-default)", paddingTop: 6 }}
        >
          {l}
        </div>
      ))}
    </section>
  );
}
