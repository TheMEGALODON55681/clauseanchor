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
      className="text-left focus-inset"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        width: "100%",
        minHeight: 44,
        padding: "6px 12px",
        background: "transparent",
        border: "none",
        cursor: "pointer",
      }}
    >
      <span style={{ color: "var(--ink-tertiary)" }}>
        <ChevronIcon size={14} open={isOpen} />
      </span>
      <span className="t-overline" style={{ color: "var(--ink-secondary)" }}>
        {label}
      </span>
      {summary && (
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--ink-tertiary)" }}>{summary}</span>
      )}
    </button>
  );
}
