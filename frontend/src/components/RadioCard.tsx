import { useState } from "react";
import type { ReactNode } from "react";

export type RadioCardState = "unselected" | "hover" | "selected" | "focus" | "disabled";

type RadioCardProps = {
  title: string;
  description?: string;
  icon?: ReactNode;
  state?: RadioCardState;
  name?: string;
  onSelect?: () => void;
};

export default function RadioCard({
  title,
  description,
  icon,
  state,
  name = "radio-card",
  onSelect,
}: RadioCardProps) {
  const [hovered, setHovered] = useState(false);
  const resolved = state ?? (hovered ? "hover" : "unselected");
  const selected = resolved === "selected";
  const disabled = resolved === "disabled";

  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      name={name}
      disabled={disabled}
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="text-left focus:outline-none focus-visible:outline-none"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        width: "100%",
        minHeight: 44,
        background: "var(--paper-sheet)",
        border: `${selected ? 2 : 1}px solid ${selected ? "var(--anchor-600)" : "var(--rule-strong)"}`,
        borderLeftWidth: selected ? 4 : 1,
        borderLeftColor: selected ? "var(--anchor-600)" : "var(--rule-strong)",
        borderRadius: "var(--radius-md)",
        padding: selected ? "11px 13px" : "12px 14px",
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
        boxShadow: resolved === "hover" ? "var(--elevation-2)" : "none",
        ...(state === "focus" ? { outline: "2px solid var(--focus-ring)", outlineOffset: 2 } : {}),
      }}
      onFocus={(e) => {
        e.currentTarget.style.outline = "2px solid var(--focus-ring)";
        e.currentTarget.style.outlineOffset = "2px";
      }}
      onBlur={(e) => {
        if (state !== "focus") e.currentTarget.style.outline = "none";
      }}
    >
      {icon && (
        <span style={{ color: selected ? "var(--anchor-600)" : "var(--ink-tertiary)", marginTop: 1, display: "inline-flex" }}>
          {icon}
        </span>
      )}
      <span style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <span style={{ fontSize: 15, fontWeight: 500, color: "var(--ink-primary)" }}>{title}</span>
        {description && (
          <span style={{ fontSize: 13, lineHeight: "18px", color: "var(--ink-secondary)" }}>{description}</span>
        )}
      </span>
    </button>
  );
}
