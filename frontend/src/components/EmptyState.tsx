import type { ReactNode } from "react";
import { EmptyBracketIcon, IndexCardIcon } from "./icons";

export type EmptyVariant = "no-findings" | "no-evidence";

const CONFIG: Record<EmptyVariant, { icon: ReactNode; heading: string; line: string }> = {
  "no-findings": {
    icon: <EmptyBracketIcon size={28} />,
    heading: "No clause found at the validated threshold",
    line: "This category was checked. Nothing was confirmed here.",
  },
  "no-evidence": {
    icon: <IndexCardIcon size={28} />,
    heading: "No case law yet",
    line: "No verified case law found for this clause type yet.",
  },
};

export default function EmptyState({ variant, heading, line }: { variant: EmptyVariant; heading?: string; line?: string }) {
  const c = { ...CONFIG[variant], ...(heading ? { heading } : {}), ...(line ? { line } : {}) };
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        gap: 8,
        padding: "32px 24px",
        border: "1px dashed var(--rule-strong)",
        borderRadius: "var(--radius-lg)",
        background: "var(--paper-sheet)",
      }}
    >
      <span style={{ color: "var(--ink-tertiary)" }}>{c.icon}</span>
      <div style={{ fontSize: 16, fontWeight: 600, color: "var(--ink-primary)" }}>{c.heading}</div>
      <p style={{ fontSize: 14, color: "var(--ink-secondary)", maxWidth: 360 }}>{c.line}</p>
    </div>
  );
}
