import { useState } from "react";

type TabsProps = {
  items: string[];
  value?: string;
  onChange?: (v: string) => void;
  disabledItems?: string[];
};

export default function Tabs({ items, value, onChange, disabledItems = [] }: TabsProps) {
  const [internal, setInternal] = useState(value ?? items[0]);
  const active = value ?? internal;

  return (
    <div role="tablist" style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--rule-default)" }}>
      {items.map((it) => {
        const isActive = it === active;
        const disabled = disabledItems.includes(it);
        return (
          <button
            key={it}
            role="tab"
            aria-selected={isActive}
            disabled={disabled}
            onClick={() => {
              setInternal(it);
              onChange?.(it);
            }}
            className="focus:outline-none focus-visible:outline-none"
            style={{
              minHeight: 44,
              padding: "0 12px",
              background: "transparent",
              border: "none",
              borderBottom: `2px solid ${isActive ? "var(--anchor-600)" : "transparent"}`,
              marginBottom: -1,
              fontSize: 14,
              fontWeight: 500,
              color: disabled ? "var(--ink-tertiary)" : isActive ? "var(--anchor-600)" : "var(--ink-secondary)",
              cursor: disabled ? "not-allowed" : "pointer",
              opacity: disabled ? 0.5 : 1,
            }}
            onFocus={(e) => {
              e.currentTarget.style.outline = "2px solid var(--focus-ring)";
              e.currentTarget.style.outlineOffset = "-2px";
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
