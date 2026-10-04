import { useState } from "react";
import { ChevronDownIcon, CheckIcon } from "./icons";

export type SelectState = "closed" | "open" | "focus" | "disabled";

type SelectProps = {
  state?: SelectState;
  label?: string;
  options?: string[];
  value?: string;
  id?: string;
};

export default function Select({
  state,
  label,
  options = ["Buyer or customer", "Supplier or vendor", "Employer", "Employee"],
  value,
  id = "select",
}: SelectProps) {
  const [open, setOpen] = useState(state === "open");
  const [selected, setSelected] = useState(value ?? options[0]);
  const isOpen = state === "open" || open;
  const disabled = state === "disabled";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 240, position: "relative" }}>
      {label && (
        <label htmlFor={id} style={{ fontSize: 14, fontWeight: 500, color: "var(--ink-secondary)" }}>
          {label}
        </label>
      )}
      <button
        id={id}
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          minHeight: 44,
          background: "var(--paper-sunken)",
          border: "1px solid var(--control-border)",
          borderRadius: "var(--radius-sm)",
          padding: "0 12px",
          fontSize: 15,
          color: "var(--ink-primary)",
          opacity: disabled ? 0.5 : 1,
          cursor: disabled ? "not-allowed" : "pointer",
          ...(state === "focus" ? { outline: "2px solid var(--focus-ring)", outlineOffset: 2 } : {}),
        }}
      >
        {selected}
        <ChevronDownIcon size={18} />
      </button>
      {isOpen && (
        <ul
          role="listbox"
          style={{
            position: "absolute",
            top: label ? 74 : 48,
            left: 0,
            right: 0,
            zIndex: 20,
            listStyle: "none",
            margin: 0,
            padding: 4,
            background: "var(--paper-sheet)",
            border: "1px solid var(--rule-default)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--elevation-2)",
          }}
        >
          {options.map((o) => (
            <li
              key={o}
              role="option"
              aria-selected={o === selected}
              onClick={() => {
                setSelected(o);
                setOpen(false);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
                minHeight: 36,
                padding: "0 8px",
                borderRadius: "var(--radius-sm)",
                fontSize: 14,
                color: "var(--ink-primary)",
                cursor: "pointer",
                background: o === selected ? "var(--anchor-100)" : "transparent",
              }}
            >
              {o}
              {o === selected && <span style={{ color: "var(--anchor-600)" }}><CheckIcon size={16} /></span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
