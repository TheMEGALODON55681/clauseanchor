/* Quiet single-arc stroke. Motion removed under reduced-motion. `inline` is for inside a button: it takes the
   text colour and is hidden from assistive technology, because the button carries aria-busy. */
export default function Spinner({ size = 20, inline = false }: { size?: number; inline?: boolean }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin"
      {...(inline ? { "aria-hidden": true } : { role: "status", "aria-label": "Loading" })}
    >
      <circle cx="12" cy="12" r="9" stroke={inline ? "currentColor" : "var(--rule-strong)"} strokeWidth="2.5" opacity={inline ? 0.25 : 0.4} />
      <path d="M12 3a9 9 0 0 1 9 9" stroke={inline ? "currentColor" : "var(--anchor-600)"} strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
