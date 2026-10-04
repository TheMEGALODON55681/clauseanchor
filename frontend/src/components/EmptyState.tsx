import type { ReactNode } from "react";
import Button from "./Button";
import { FileIcon, EmptyBracketIcon, IndexCardIcon } from "./icons";

export type EmptyVariant = "no-document" | "no-findings" | "no-evidence";

const CONFIG: Record<EmptyVariant, { icon: ReactNode; heading: string; line: string; action?: string }> = {
  "no-document": {
    icon: <FileIcon size={28} />,
    heading: "No contract loaded",
    line: "Upload a contract to begin the review.",
    action: "Upload a contract",
  },
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

export default function EmptyState({
  variant,
  heading,
  line,
  onAction,
  headingAs: Heading = "div",
}: {
  variant: EmptyVariant;
  heading?: string;
  line?: string;
  onAction?: () => void;
  headingAs?: "h1" | "h2" | "div";
}) {
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
      <Heading style={{ fontSize: 16, fontWeight: 600, color: "var(--ink-primary)" }}>{c.heading}</Heading>
      <p style={{ fontSize: 14, color: "var(--ink-secondary)", maxWidth: 360 }}>{c.line}</p>
      {c.action && (
        <div style={{ marginTop: 8 }}>
          <Button variant="primary" onClick={onAction}>{c.action}</Button>
        </div>
      )}
    </div>
  );
}
