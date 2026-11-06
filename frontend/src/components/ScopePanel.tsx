import { useId, useState } from "react";
import type { Unfinished } from "../lib/reader";
import Button from "./Button";
import { InfoIcon, PersonWithDocIcon } from "./icons";

export type ScopeVariant = "complete" | "processing-incomplete" | "sample-mode";

type ScopePanelProps = {
  variant?: ScopeVariant;
  categoryCount?: number;
  catalogueVersion?: string;
  /** The categories and pages that were not finished. View list is drawn only when there is something in it. */
  unfinished?: Unfinished[];
};

const SCOPE_TEXT =
  "This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment.";

/* Compact scope card pinned to the top of the category sidebar. Never a verdict. */
export default function ScopePanel({
  variant = "complete",
  categoryCount = 46,
  catalogueVersion = "cat-2026.09-r1.1",
  unfinished = [],
}: ScopePanelProps) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  return (
    <section
      aria-label="Review scope"
      style={{
        background: "var(--paper-sheet)",
        border: "1px solid var(--rule-default)",
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
        {unfinished.length > 0 && (
          <Button variant="tertiary" size="s" aria-expanded={open} aria-controls={listId} onClick={() => setOpen((o) => !o)}>
            {open ? "Hide list" : "View list"}
          </Button>
        )}
      </div>
      {unfinished.length > 0 && (
        <div id={listId} hidden={!open}>
          <p style={{ fontSize: 12, lineHeight: "17px", fontWeight: 600, color: "var(--ink-primary)" }}>Not finished</p>
          <ul style={{ listStyle: "none", margin: "4px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 4 }}>
            {unfinished.map((u) => (
              <li key={u.label} style={{ fontSize: 12, lineHeight: "17px", color: "var(--ink-secondary)", overflowWrap: "anywhere" }}>
                <span style={{ color: "var(--ink-primary)" }}>{u.label}</span>: {u.note}
              </li>
            ))}
          </ul>
        </div>
      )}
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
    </section>
  );
}
