import { useState } from "react";

export type SwitchState = "off" | "on" | "focus" | "disabled";

type SwitchProps = {
  state?: SwitchState;
  label?: string;
  description?: string;
  checked?: boolean;
  onChange?: (v: boolean) => void;
};

export default function Switch({ state, label, description, checked, onChange }: SwitchProps) {
  const [on, setOn] = useState(state === "on");
  const isOn = state === "on" || (state === undefined && (checked ?? on));
  const disabled = state === "disabled";

  return (
    <label style={{ display: "flex", alignItems: "flex-start", gap: 12, minHeight: 44, opacity: disabled ? 0.5 : 1, cursor: disabled ? "not-allowed" : "pointer" }}>
      <button
        type="button"
        role="switch"
        aria-checked={isOn}
        disabled={disabled}
        onClick={() => {
          setOn(!isOn);
          onChange?.(!isOn);
        }}
        className="focus:outline-none focus-visible:outline-none reduce-motion-safe"
        style={{
          flexShrink: 0,
          marginTop: 2,
          width: 40,
          height: 24,
          borderRadius: 999,
          border: "1px solid var(--rule-strong)",
          background: isOn ? "var(--anchor-600)" : "var(--paper-sunken)",
          position: "relative",
          transition: "background 120ms ease-out",
          cursor: disabled ? "not-allowed" : "pointer",
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
        <span
          className="reduce-motion-safe"
          style={{
            position: "absolute",
            top: 2,
            left: isOn ? 18 : 2,
            width: 18,
            height: 18,
            borderRadius: 999,
            background: "var(--paper-sheet)",
            boxShadow: "0 1px 2px rgba(0,0,0,0.2)",
            transition: "left 120ms ease-out",
          }}
        />
      </button>
      {(label || description) && (
        <span style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {label && <span style={{ fontSize: 15, fontWeight: 500, color: "var(--ink-primary)" }}>{label}</span>}
          {description && <span style={{ fontSize: 13, lineHeight: "18px", color: "var(--ink-secondary)" }}>{description}</span>}
        </span>
      )}
    </label>
  );
}
