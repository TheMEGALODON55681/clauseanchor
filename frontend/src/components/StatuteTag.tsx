import { useState } from "react";
import { SectionIcon } from "./icons";

export type StatuteTagState = "default" | "hover" | "focus";

type StatuteTagProps = {
  citation?: string;
  state?: StatuteTagState;
};

/* Section-sign glyph plus a statute citation, in citation style. */
export default function StatuteTag({
  citation = "Section 27, Indian Contract Act 1872",
  state,
}: StatuteTagProps) {
  const [hovered, setHovered] = useState(false);
  const resolved = state ?? (hovered ? "hover" : "default");
  return (
    <button
      type="button"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="focus:outline-none focus-visible:outline-none"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        minHeight: 28,
        color: "var(--statute-fg)",
        background: resolved === "hover" ? "var(--statute-bg)" : "transparent",
        border: "1px solid var(--statute-border)",
        borderRadius: "var(--radius-sm)",
        padding: "3px 8px",
        cursor: "pointer",
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
      <SectionIcon size={16} />
      <span
        style={{
          fontFamily: "var(--font-serif)",
          fontWeight: 500,
          fontVariant: "small-caps",
          letterSpacing: "0.03em",
          fontSize: 13,
        }}
      >
        {citation}
      </span>
    </button>
  );
}
