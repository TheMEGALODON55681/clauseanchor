import type { ReactNode } from "react";

type DividerProps = {
  orientation?: "horizontal" | "vertical";
  label?: ReactNode;
};

export default function Divider({ orientation = "horizontal", label }: DividerProps) {
  if (orientation === "vertical") {
    return (
      <span
        aria-hidden
        style={{ display: "inline-block", width: 1, alignSelf: "stretch", minHeight: 20, background: "var(--rule-default)" }}
      />
    );
  }
  if (label) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ flex: 1, height: 1, background: "var(--rule-default)" }} />
        <span className="t-overline" style={{ color: "var(--ink-tertiary)" }}>
          {label}
        </span>
        <span style={{ flex: 1, height: 1, background: "var(--rule-default)" }} />
      </div>
    );
  }
  return <div style={{ height: 1, background: "var(--rule-default)", width: "100%" }} />;
}
