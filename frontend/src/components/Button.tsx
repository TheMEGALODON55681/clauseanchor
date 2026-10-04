import { useState } from "react";
import type { CSSProperties, ReactNode } from "react";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "tertiary"
  | "destructive"
  | "ghost-on-dark";
export type ButtonSize = "s" | "m" | "l";
export type ButtonState =
  | "default"
  | "hover"
  | "pressed"
  | "focus"
  | "disabled"
  | "loading";
export type ButtonIcon = "none" | "leading" | "trailing" | "icon-only";

type ButtonProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ButtonIcon;
  /** Force a visual state, used by the gallery. Interactive by default. */
  state?: ButtonState;
  iconNode?: ReactNode;
  children?: ReactNode;
  onClick?: () => void;
  id?: string;
  "aria-label"?: string;
  "aria-expanded"?: boolean;
  "aria-controls"?: string;
};

const SIZES: Record<ButtonSize, { h: number; px: number; font: number; icon: number }> = {
  s: { h: 32, px: 12, font: 13, icon: 16 },
  m: { h: 40, px: 16, font: 14, icon: 18 },
  l: { h: 48, px: 20, font: 15, icon: 20 },
};

function Spinner({ size = 14 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin"
      aria-hidden
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.25" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

/** Ink-stamp styling per variant + resolved visual state. */
function styleFor(variant: ButtonVariant, state: ButtonState): CSSProperties {
  const pressed = state === "pressed";
  const hover = state === "hover";
  const disabled = state === "disabled";

  const base: CSSProperties = {
    borderRadius: "var(--radius-md)",
    fontWeight: 500,
    transition: "transform var(--dur-press) var(--ease-out), background var(--dur-press) var(--ease-out)",
    transform: pressed ? "translateY(1px)" : "translateY(0)",
    opacity: disabled ? 0.45 : 1,
    cursor: disabled ? "not-allowed" : "pointer",
  };

  switch (variant) {
    case "primary":
      return {
        ...base,
        background: hover || pressed ? "var(--anchor-700)" : "var(--anchor-600)",
        color: "var(--paper-sheet)",
        border: "1px solid transparent",
        boxShadow: pressed ? "none" : "0 2px 0 0 var(--anchor-700)",
      };
    case "secondary":
      return {
        ...base,
        background: hover ? "var(--paper-sunken)" : "var(--paper-sheet)",
        color: "var(--ink-primary)",
        border: "1px solid var(--rule-strong)",
        boxShadow: pressed ? "none" : "0 2px 0 0 var(--rule-strong)",
      };
    case "destructive":
      return {
        ...base,
        background: hover ? "var(--status-unavailable-bg)" : "var(--paper-sheet)",
        color: "var(--status-unavailable-fg)",
        border: "1px solid var(--status-unavailable-border)",
        boxShadow: pressed ? "none" : "0 2px 0 0 var(--status-unavailable-border)",
      };
    case "ghost-on-dark":
      return {
        ...base,
        background: hover || pressed ? "rgba(255,255,255,0.12)" : "transparent",
        color: "var(--paper-sheet)",
        border: "1px solid rgba(255,255,255,0.35)",
        boxShadow: "none",
      };
    case "tertiary":
    default:
      return {
        ...base,
        background: "transparent",
        color: "var(--anchor-600)",
        border: "1px solid transparent",
        boxShadow: "none",
        textDecoration: hover ? "underline" : "none",
        textUnderlineOffset: 3,
      };
  }
}

export default function Button({
  variant = "primary",
  size = "m",
  icon = "none",
  state,
  iconNode,
  children,
  onClick,
  ...rest
}: ButtonProps) {
  const [hovered, setHovered] = useState(false);
  const [active, setActive] = useState(false);

  // Resolve the visual state: forced prop wins, else derive from pointer.
  const resolved: ButtonState =
    state ?? (active ? "pressed" : hovered ? "hover" : "default");
  const disabled = state === "disabled";
  const loading = state === "loading";
  const s = SIZES[size];
  const iconOnly = icon === "icon-only";

  const css = styleFor(variant, resolved);

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setActive(false);
      }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
      aria-busy={loading || undefined}
      className="hit inline-flex items-center justify-center gap-2 font-sans select-none"
      style={{
        ...css,
        minHeight: s.h,
        minWidth: iconOnly ? s.h : 44,
        height: s.h,
        paddingInline: iconOnly ? 0 : s.px,
        width: iconOnly ? s.h : undefined,
        fontSize: s.font,
        ...(state === "focus"
          ? { outline: "2px solid var(--focus-ring)", outlineOffset: 2 }
          : {}),
      }}
      {...rest}
    >
      {loading && <Spinner size={s.icon - 2} />}
      {!loading && (icon === "leading" || iconOnly) && (
        <span style={{ display: "inline-flex" }}>{iconNode}</span>
      )}
      {!iconOnly && <span>{children}</span>}
      {!loading && icon === "trailing" && (
        <span style={{ display: "inline-flex" }}>{iconNode}</span>
      )}
    </button>
  );
}
