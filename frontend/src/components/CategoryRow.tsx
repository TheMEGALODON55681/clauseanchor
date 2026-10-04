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
      className="text-left focus-inset"
      style={{
        position: "relative",
        display: "flex",
        alignItems: "center",
        gap: 10,
        width: "100%",
        minHeight: 44,
        padding: "8px 12px 8px 16px",
        background: selected ? "var(--anchor-100)" : resolved === "hover" ? "var(--paper-sheet)" : "transparent",
        border: "none",
        cursor: "pointer",
        ...(state === "focus" ? { outline: "2px solid var(--focus-ring)", outlineOffset: -2 } : {}),
      }}
    >
      {/* Out of flow, so an unselected row keeps all of its width for the name. */}
      <span aria-hidden style={{ position: "absolute", left: 4, top: "50%", transform: "translateY(-50%)", fontFamily: "var(--font-serif)", color: "var(--anchor-600)", visibility: selected ? "visible" : "hidden" }}>
        &#10214;
      </span>
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
