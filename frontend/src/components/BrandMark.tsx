type MarkProps = { size?: number; className?: string };

/* Logomark: a bracket pair ⟦ ⟧ that resolves into an anchor.
   Single weight, works at 16px and 64px, uses anchor/600 (mode-aware). */
export function AnchorLogomark({ size = 32 }: MarkProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" role="img" aria-label="ClauseAnchor logo">
      <g stroke="var(--anchor-600)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none">
        {/* Bracket pair */}
        <path d="M9 5H6v22h3" />
        <path d="M23 5h3v22h-3" />
        {/* Anchor inside */}
        <circle cx="16" cy="8.5" r="2" />
        <path d="M16 10.5V24" />
        <path d="M12 13h8" />
        <path d="M9.5 18c0 4 2.9 6.5 6.5 6.5s6.5-2.5 6.5-6.5" />
      </g>
    </svg>
  );
}

export function Wordmark({ size = 22 }: { size?: number }) {
  return (
    <span
      style={{
        fontFamily: "var(--font-serif)",
        fontWeight: 600,
        fontSize: size,
        letterSpacing: "-0.01em",
        color: "var(--ink-primary)",
      }}
    >
      ClauseAnchor
    </span>
  );
}

export function HorizontalLockup({ size = 28 }: { size?: number }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <AnchorLogomark size={size} />
      <Wordmark size={size * 0.8} />
    </span>
  );
}

/* Favicon renders identical mark at 16 and 32. */
export function Favicon({ size = 32 }: { size?: 16 | 32 }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size,
        background: "var(--paper-sheet)",
        border: "1px solid var(--rule-default)",
        borderRadius: 4,
      }}
    >
      <AnchorLogomark size={size - 6} />
    </span>
  );
}

export default HorizontalLockup;
