import { Fragment } from "react";

/* A key cap or a combination of key caps. */
function Cap({ children }: { children: string }) {
  return (
    <kbd
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 12,
        lineHeight: "16px",
        color: "var(--ink-secondary)",
        background: "var(--paper-sheet)",
        border: "1px solid var(--rule-strong)",
        borderBottomWidth: 2,
        borderRadius: "var(--radius-sm)",
        padding: "1px 6px",
        minWidth: 20,
        textAlign: "center",
        display: "inline-block",
      }}
    >
      {children}
    </kbd>
  );
}

export default function KeyboardHint({ keys = ["J"] }: { keys?: string[] }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
      {keys.map((k, i) => (
        <Fragment key={k}>
          {i > 0 && <span style={{ fontSize: 12, color: "var(--ink-tertiary)" }}>+</span>}
          <Cap>{k}</Cap>
        </Fragment>
      ))}
    </span>
  );
}
