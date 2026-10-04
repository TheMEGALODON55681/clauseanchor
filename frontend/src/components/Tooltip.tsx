import { useState } from "react";
import type { ReactNode } from "react";

export type TooltipSide = "top" | "bottom" | "left" | "right";

type TooltipProps = {
  label: string;
  side?: TooltipSide;
  /** Force visibility for the gallery. */
  open?: boolean;
  children: ReactNode;
};

function pos(side: TooltipSide): React.CSSProperties {
  switch (side) {
    case "top":
      return { bottom: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)" };
    case "bottom":
      return { top: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)" };
    case "left":
      return { right: "calc(100% + 8px)", top: "50%", transform: "translateY(-50%)" };
    case "right":
      return { left: "calc(100% + 8px)", top: "50%", transform: "translateY(-50%)" };
  }
}

export default function Tooltip({ label, side = "top", open, children }: TooltipProps) {
  const [hovered, setHovered] = useState(false);
  const show = open ?? hovered;
  return (
    <span
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
    >
      {children}
      {show && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            ...pos(side),
            zIndex: 20,
            maxWidth: 280,
            width: "max-content",
            background: "var(--ink-primary)",
            color: "var(--paper-sheet)",
            fontFamily: "var(--font-sans)",
            fontSize: 12,
            lineHeight: "16px",
            padding: "5px 8px",
            borderRadius: "var(--radius-sm)",
            boxShadow: "var(--elevation-2)",
          }}
        >
          {label}
        </span>
      )}
    </span>
  );
}
