import { useState } from "react";
import StatusChip, { type StatusKind } from "./StatusChip";
import CountBadge from "./CountBadge";
import { ChevronIcon } from "./icons";

export type CategoryRowState = "default" | "hover" | "selected" | "focus";

type CategoryRowProps = {
  name: string;
  status: StatusKind;
  count?: number;
  state?: CategoryRowState;
  onClick?: () => void;
};

const RULE_COLOR: Record<StatusKind, string> = {
  found: "var(--status-found-fg)",
  review: "var(--status-review-fg)",
  unvalidated: "var(--status-unvalidated-fg)",
  absent: "var(--status-absent-fg)",
  unavailable: "var(--status-unavailable-fg)",
};

export default function CategoryRow({ name, status, count, state, onClick }: CategoryRowProps) {
  const [hovered, setHovered] = useState(false);
  const resolved = state ?? (hovered ? "hover" : "default");
  const selected = resolved === "selected";

  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-current={selected || undefined}
      className="text-left focus:outline-none focus-visible:outline-none"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        width: "100%",
        minHeight: 44,
        padding: "8px 12px",
        background: selected ? "var(--paper-sheet)" : resolved === "hover" ? "var(--paper-sheet)" : "transparent",
        border: "none",
        borderLeft: `4px solid ${selected ? RULE_COLOR[status] : "transparent"}`,
        cursor: "pointer",
        ...(state === "focus" ? { outline: "2px solid var(--focus-ring)", outlineOffset: -2 } : {}),
      }}
      onFocus={(e) => {
        e.currentTarget.style.outline = "2px solid var(--focus-ring)";
        e.currentTarget.style.outlineOffset = "-2px";
      }}
      onBlur={(e) => {
        if (state !== "focus") e.currentTarget.style.outline = "none";
      }}
    >
      <span style={{ flex: 1, minWidth: 0, fontSize: 14, color: "var(--ink-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {name}
      </span>
      {count && count > 0 ? <CountBadge count={count} /> : null}
      <StatusChip status={status} size="s" />
      <span style={{ color: "var(--ink-tertiary)" }}>
        <ChevronIcon size={16} />
      </span>
    </button>
  );
}
