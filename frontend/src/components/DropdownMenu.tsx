import { useState } from "react";
import type { ReactNode } from "react";
import { DotsIcon, DownloadIcon, BracketPairIcon } from "./icons";

export type MenuItem = { label: string; icon?: ReactNode; disabled?: boolean; onSelect?: () => void; checked?: boolean };

type DropdownMenuProps = {
  items?: MenuItem[];
  /** Force-open for the gallery. */
  open?: boolean;
  focusIndex?: number;
  label?: string;
};

const DEFAULT_ITEMS: MenuItem[] = [
  { label: "Download PDF report", icon: <DownloadIcon size={16} /> },
  { label: "Copy offsets", icon: <BracketPairIcon size={16} /> },
  { label: "Print view", disabled: true },
];

export default function DropdownMenu({ items = DEFAULT_ITEMS, open, focusIndex, label = "Report actions" }: DropdownMenuProps) {
  const [isOpen, setIsOpen] = useState(open ?? false);
  const show = open ?? isOpen;

  return (
    <div
      style={{ position: "relative", display: "inline-block" }}
      onKeyDown={(e) => {
        if (e.key === "Escape") setIsOpen(false);
      }}
      onBlur={(e) => {
        if (open === undefined && !e.currentTarget.contains(e.relatedTarget as Node | null)) setIsOpen(false);
      }}
    >
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={show}
        aria-label={label}
        onClick={() => setIsOpen((v) => !v)}
        className="focus:outline-none focus-visible:outline-none"
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 40,
          height: 40,
          background: "var(--paper-sheet)",
          border: "1px solid var(--rule-strong)",
          borderRadius: "var(--radius-md)",
          color: "var(--ink-secondary)",
          cursor: "pointer",
        }}
        onFocus={(e) => {
          e.currentTarget.style.outline = "2px solid var(--focus-ring)";
          e.currentTarget.style.outlineOffset = "2px";
        }}
        onBlur={(e) => (e.currentTarget.style.outline = "none")}
      >
        <DotsIcon size={18} />
      </button>
      {show && (
        <ul
          role="menu"
          style={{
            position: "absolute",
            top: 44,
            right: 0,
            zIndex: 20,
            minWidth: 220,
            listStyle: "none",
            margin: 0,
            padding: 4,
            background: "var(--paper-sheet)",
            border: "1px solid var(--rule-default)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--elevation-2)",
          }}
        >
          {items.map((it, i) => (
            <li
              key={it.label}
              role="menuitem"
              aria-disabled={it.disabled || undefined}
              tabIndex={it.disabled ? -1 : 0}
              aria-checked={it.checked}
              onClick={() => {
                if (it.disabled) return;
                it.onSelect?.();
                setIsOpen(false);
              }}
              onKeyDown={(e) => {
                if ((e.key === "Enter" || e.key === " ") && !it.disabled) {
                  e.preventDefault();
                  it.onSelect?.();
                  setIsOpen(false);
                }
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                minHeight: 40,
                padding: "0 10px",
                borderRadius: "var(--radius-sm)",
                fontSize: 14,
                color: it.disabled ? "var(--ink-tertiary)" : "var(--ink-primary)",
                background: focusIndex === i ? "var(--anchor-100)" : "transparent",
                opacity: it.disabled ? 0.6 : 1,
                cursor: it.disabled ? "not-allowed" : "pointer",
                outline: focusIndex === i ? "2px solid var(--focus-ring)" : "none",
                outlineOffset: -2,
              }}
            >
              {it.icon && <span style={{ color: "var(--ink-tertiary)", display: "inline-flex" }}>{it.icon}</span>}
              {it.label}
              {it.checked && <span aria-hidden style={{ marginLeft: "auto", color: "var(--anchor-600)" }}>&#10003;</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
