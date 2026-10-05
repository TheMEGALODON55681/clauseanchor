import { SectionIcon } from "./icons";

export type StatuteTagState = "default" | "hover" | "focus";

type StatuteTagProps = {
  citation?: string;
  /** Forces a visual state, used by the gallery. The tag is a label, not a control. */
  state?: StatuteTagState;
};

/* Section-sign glyph plus a statute citation, in citation style. */
export default function StatuteTag({
  citation = "Section 27, Indian Contract Act 1872",
  state,
}: StatuteTagProps) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        minHeight: 28,
        color: "var(--statute-fg)",
        background: state === "hover" ? "var(--statute-bg)" : "transparent",
        border: "1px solid var(--statute-border)",
        borderRadius: "var(--radius-sm)",
        padding: "3px 8px",
        ...(state === "focus" ? { outline: "2px solid var(--focus-ring)", outlineOffset: 2 } : {}),
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
    </span>
  );
}
