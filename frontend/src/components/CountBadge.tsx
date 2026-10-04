/* The only pill shape allowed in the system. */
export default function CountBadge({ count = 1, tone = "neutral" }: { count?: number; tone?: "neutral" | "anchor" }) {
  const label = count > 99 ? "99+" : String(count);
  const anchor = tone === "anchor";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth: 18,
        height: 18,
        paddingInline: 5,
        borderRadius: 999,
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        lineHeight: 1,
        color: anchor ? "var(--paper-sheet)" : "var(--ink-secondary)",
        background: anchor ? "var(--anchor-600)" : "var(--paper-sunken)",
        border: anchor ? "1px solid transparent" : "1px solid var(--rule-default)",
      }}
      aria-label={`${label} findings`}
    >
      {label}
    </span>
  );
}
