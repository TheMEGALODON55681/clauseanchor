export type MetricVariant = "value" | "not-measured" | "insufficient";

type MetricCellProps = {
  variant?: MetricVariant;
  value?: string;
  support?: number;
  label?: string;
  /** The measure that matters most, set a step heavier. */
  emphasis?: boolean;
};

/* Never shows 0 for missing data. */
export default function MetricCell({ variant = "value", value = "0.71", support, label, emphasis }: MetricCellProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 88 }}>
      {label && (
        <span className="metric-label" style={{ fontSize: 12, letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--ink-tertiary)" }}>
          {label}
        </span>
      )}
      {variant === "value" && (
        <>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: emphasis ? 500 : 400, color: "var(--ink-primary)" }}>{value}</span>
          {support !== undefined && <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)" }}>n = {support}</span>}
        </>
      )}
      {variant === "not-measured" && (
        <span style={{ fontSize: 13, color: "var(--ink-tertiary)" }}>Not measured</span>
      )}
      {variant === "insufficient" && (
        <span style={{ fontSize: 13, color: "var(--ink-tertiary)" }}>Insufficient data</span>
      )}
    </div>
  );
}
