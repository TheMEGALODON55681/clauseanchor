import { useEffect, useRef, useState } from "react";
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
  const trigger = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const live = () => [...(list.current?.querySelectorAll<HTMLElement>('[role^="menuitem"]:not([aria-disabled])') ?? [])];

  /* Opening moves focus into the menu: the checked item, else the first. */
  useEffect(() => {
    if (!isOpen) return;
    const els = live();
    (els.find((el) => el.getAttribute("aria-checked") === "true") ?? els[0])?.focus();
  }, [isOpen]);

  /* Closing gives focus back to the trigger first, so a pick that opens a dialog hands that dialog the trigger. */
  const close = () => {
    setIsOpen(false);
    trigger.current?.focus();
  };
  const pick = (it: MenuItem) => {
    if (it.disabled) return;
    close();
    it.onSelect?.();
  };

  return (
    <div
      style={{ position: "relative", display: "inline-block" }}
      onKeyDown={(e) => {
        if (e.key === "Escape" && show) {
          // The menu takes the key, so the Reader does not also close its detail panel.
          e.stopPropagation();
          close();
          return;
        }
        if (e.key === "ArrowDown" && !show) {
          e.preventDefault();
          setIsOpen(true);
          return;
        }
        if (!show) return;
        const els = live();
        const at = els.indexOf(document.activeElement as HTMLElement);
        const to = e.key === "ArrowDown" ? at + 1 : e.key === "ArrowUp" ? (at < 0 ? -1 : at - 1) : e.key === "Home" ? 0 : e.key === "End" ? els.length - 1 : null;
        if (to === null || !els.length) return;
        e.preventDefault();
        els[(to + els.length) % els.length].focus();
      }}
      onBlur={(e) => {
        if (open === undefined && !e.currentTarget.contains(e.relatedTarget as Node | null)) setIsOpen(false);
      }}
    >
      <button
        ref={trigger}
        type="button"
        aria-haspopup="menu"
        aria-expanded={show}
        aria-label={label}
        onClick={() => setIsOpen((v) => !v)}
        className="hit"
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
      >
        <DotsIcon size={18} />
      </button>
      {show && (
        <ul
          ref={list}
          role="menu"
          className="ca-menu"
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
              role={it.checked === undefined ? "menuitem" : "menuitemradio"}
              aria-disabled={it.disabled || undefined}
              tabIndex={it.disabled ? -1 : 0}
              aria-checked={it.checked}
              className="focus-inset"
              onClick={() => pick(it)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  pick(it);
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
                // Only the gallery's forced state draws its own ring. An inline `none` would beat :focus-visible and hide a real one.
                ...(focusIndex === i ? { outline: "2px solid var(--focus-ring)", outlineOffset: -2 } : null),
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
