import { useState } from "react";
import type { ReactNode } from "react";

export type InputState = "default" | "hover" | "focus" | "filled" | "error" | "disabled";

type TextInputProps = {
  state?: InputState;
  label?: string;
  placeholder?: string;
  value?: string;
  leadingIcon?: ReactNode;
  errorText?: string;
  id?: string;
};

export default function TextInput({
  state,
  label,
  placeholder = "Type here",
  value,
  leadingIcon,
  errorText = "Enter a valid value.",
  id = "text-input",
}: TextInputProps) {
  const [focused, setFocused] = useState(false);
  const resolved = state ?? (focused ? "focus" : "default");
  const disabled = resolved === "disabled";
  const error = resolved === "error";
  const filled = resolved === "filled";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 240 }}>
      {label && (
        <label htmlFor={id} style={{ fontSize: 14, fontWeight: 500, color: "var(--ink-secondary)" }}>
          {label}
        </label>
      )}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          minHeight: 44,
          background: "var(--paper-sunken)",
          border: `1px solid ${error ? "var(--status-unavailable-border)" : "var(--control-border)"}`,
          borderRadius: "var(--radius-sm)",
          padding: "0 12px",
          opacity: disabled ? 0.5 : 1,
          ...(resolved === "focus"
            ? { outline: "2px solid var(--focus-ring)", outlineOffset: 2 }
            : {}),
          ...(resolved === "hover" ? { borderColor: "var(--ink-tertiary)" } : {}),
        }}
      >
        {leadingIcon && <span style={{ color: "var(--ink-tertiary)", display: "inline-flex" }}>{leadingIcon}</span>}
        <input
          id={id}
          disabled={disabled}
          defaultValue={filled || value ? value ?? "Sample Traders Pvt. Ltd." : undefined}
          placeholder={placeholder}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className="focus:outline-none"
          aria-invalid={error || undefined}
          style={{
            flex: 1,
            border: "none",
            background: "transparent",
            outline: "none",
            fontFamily: "var(--font-sans)",
            fontSize: 15,
            color: "var(--ink-primary)",
            minWidth: 0,
          }}
        />
      </div>
      {error && (
        <span style={{ fontSize: 13, color: "var(--status-unavailable-fg)" }}>{errorText}</span>
      )}
    </div>
  );
}
