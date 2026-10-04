/* Traceability tag, e.g. "chars 4210 to 4488". Monospace. */
export default function OffsetTag({ start = 4210, end = 4488 }: { start?: number; end?: number }) {
  return (
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 12,
        lineHeight: "18px",
        color: "var(--ink-tertiary)",
        background: "var(--paper-sunken)",
        border: "1px solid var(--rule-default)",
        borderRadius: "var(--radius-sm)",
        padding: "1px 6px",
        whiteSpace: "nowrap",
      }}
    >
      chars {start} to {end}
    </span>
  );
}
