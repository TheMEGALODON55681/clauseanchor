import { CheckIcon, MinusIcon } from "./icons";

export type ToggleState = "unchecked" | "checked" | "indeterminate" | "focus" | "disabled";

type ControlProps = {
  kind: "checkbox" | "radio";
  state?: ToggleState;
  label?: string;
};

/* 20px control, radius/sm for the checkbox. Icon + text, 44px hit area via padding. */
export default function CheckboxRadio({ kind, state = "unchecked", label }: ControlProps) {
  const checked = state === "checked";
  const indeterminate = state === "indeterminate" && kind === "checkbox";
  const active = checked || indeterminate;
  const disabled = state === "disabled";
  const radio = kind === "radio";

  return (
    <label
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        minHeight: 44,
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      <span
        aria-hidden
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 20,
          height: 20,
          borderRadius: radio ? 999 : "var(--radius-sm)",
          border: `1px solid ${active ? "var(--anchor-600)" : "var(--control-border)"}`,
          background: active && !radio ? "var(--anchor-600)" : "var(--paper-sheet)",
          color: "var(--paper-sheet)",
          ...(state === "focus" ? { outline: "2px solid var(--focus-ring)", outlineOffset: 2 } : {}),
        }}
      >
        {radio && checked && (
          <span style={{ width: 10, height: 10, borderRadius: 999, background: "var(--anchor-600)" }} />
        )}
        {!radio && checked && <CheckIcon size={14} />}
        {!radio && indeterminate && <MinusIcon size={14} />}
      </span>
      {label && <span style={{ fontSize: 15, color: "var(--ink-primary)" }}>{label}</span>}
    </label>
  );
}
