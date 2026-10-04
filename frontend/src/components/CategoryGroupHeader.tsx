import { useState } from "react";
import { ChevronIcon } from "./icons";

type CategoryGroupHeaderProps = {
  label: string;
  summary?: string;
  collapsed?: boolean;
  onToggle?: () => void;
};

export default function CategoryGroupHeader({
  label,
  summary,
  collapsed,
  onToggle,
}: CategoryGroupHeaderProps) {
  const [open, setOpen] = useState(!collapsed);
  const isOpen = collapsed === undefined ? open : !collapsed;

  return (
    <button
      type="button"
      onClick={() => {
        setOpen((v) => !v);
        onToggle?.();
      }}
      aria-expanded={isOpen}
      className="text-left focus:outline-none focus-visible:outline-none"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        width: "100%",
        minHeight: 36,
        padding: "6px 12px",
        background: "transparent",
        border: "none",
        cursor: "pointer",
      }}
      onFocus={(e) => {
        e.currentTarget.style.outline = "2px solid var(--focus-ring)";
        e.currentTarget.style.outlineOffset = "-2px";
      }}
      onBlur={(e) => (e.currentTarget.style.outline = "none")}
    >
      <span style={{ color: "var(--ink-tertiary)" }}>
        <ChevronIcon size={14} open={isOpen} />
      </span>
      <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-secondary)" }}>
        {label}
      </span>
      {summary && (
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--ink-tertiary)" }}>{summary}</span>
      )}
    </button>
  );
}
