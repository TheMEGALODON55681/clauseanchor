export type SpinnerSize = 14 | 20 | 32;

/* Quiet single-arc stroke. Motion removed under reduced-motion. */
export default function Spinner({ size = 20 }: { size?: SpinnerSize }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin"
      role="status"
      aria-label="Loading"
    >
      <circle cx="12" cy="12" r="9" stroke="var(--rule-strong)" strokeWidth="2.5" opacity="0.4" />
      <path
        d="M12 3a9 9 0 0 1 9 9"
        stroke="var(--anchor-600)"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
