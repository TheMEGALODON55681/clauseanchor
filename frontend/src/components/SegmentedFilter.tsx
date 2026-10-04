import { useState } from "react";

/* Paper-tab look. Selected segment lifts onto a sheet. */
export default function SegmentedFilter({
  items = ["All", "Found", "Needs a lawyer", "Not found"],
  value,
  onChange,
}: {
  items?: string[];
  value?: string;
  onChange?: (v: string) => void;
}) {
  const [internal, setInternal] = useState(value ?? items[0]);
  const active = value ?? internal;
  return (
    <div
      role="tablist"
      style={{
        display: "inline-flex",
        gap: 2,
        padding: 2,
        background: "var(--paper-sunken)",
        border: "1px solid var(--rule-default)",
        borderRadius: "var(--radius-md)",
      }}
    >
      {items.map((it) => {
        const isActive = it === active;
        return (
          <button
            key={it}
            role="tab"
            aria-selected={isActive}
            onClick={() => {
              setInternal(it);
              onChange?.(it);
            }}
            className="focus:outline-none focus-visible:outline-none"
            style={{
              minHeight: 32,
              padding: "0 10px",
              borderRadius: "var(--radius-sm)",
              border: isActive ? "1px solid var(--rule-default)" : "1px solid transparent",
              background: isActive ? "var(--paper-sheet)" : "transparent",
              boxShadow: isActive ? "var(--elevation-1)" : "none",
              fontSize: 13,
              fontWeight: 500,
              color: isActive ? "var(--ink-primary)" : "var(--ink-secondary)",
              cursor: "pointer",
            }}
            onFocus={(e) => {
              e.currentTarget.style.outline = "2px solid var(--focus-ring)";
              e.currentTarget.style.outlineOffset = "2px";
            }}
            onBlur={(e) => (e.currentTarget.style.outline = "none")}
          >
            {it}
          </button>
        );
      })}
    </div>
  );
}
