import MetricCell from "./MetricCell";

export type PerfVariant = "strong" | "weak" | "not-measured";

type PerformanceTableRowProps = {
  category?: string;
  variant?: PerfVariant;
  metrics?: { support: number; precision: number | null; recall: number | null; silentMiss: number | null; abstention: number | null };
};

/* One row for the accuracy page. Weak rows carry an ochre left rule and label. */
export default function PerformanceTableRow({
  category = "Non-Compete",
  variant = "strong",
  metrics,
}: PerformanceTableRowProps) {
  if (metrics) {
    const weakRow = variant === "weak";
    const cell = (label: string, v: number | null) =>
      v === null ? (
        <MetricCell variant="not-measured" label={label} />
      ) : (
        <MetricCell variant={metrics.support < 10 ? "insufficient" : "value"} label={label} value={v.toFixed(2)} support={metrics.support} />
      );
    return (
      <div
        role="row"
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(140px, 1.6fr) repeat(5, minmax(72px, 1fr))",
          gap: 12,
          alignItems: "center",
          padding: "12px 14px",
          background: "var(--paper-sheet)",
          border: "1px solid var(--rule-default)",
          borderLeftWidth: 4,
          borderLeftColor: weakRow ? "var(--status-review-fg)" : "var(--rule-default)",
          borderRadius: "var(--radius-md)",
        }}
      >
        <div role="rowheader" style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ fontSize: 14, fontWeight: 500, color: "var(--ink-primary)" }}>{category}</span>
          {weakRow && (
            <span style={{ fontSize: 12, color: "var(--status-review-fg)" }}>Weak: read these findings with extra care</span>
          )}
        </div>
        <MetricCell variant="value" label="Support" value={String(metrics.support)} support={metrics.support} />
        {cell("Precision", metrics.precision)}
        {cell("Recall", metrics.recall)}
        {cell("Silent miss", metrics.silentMiss)}
        {cell("Abstention", metrics.abstention)}
      </div>
    );
  }
  const weak = variant === "weak";
  const notMeasured = variant === "not-measured";
  const metric = notMeasured ? "not-measured" : "value";

  return (
    <div
      role="row"
      style={{
        display: "grid",
        gridTemplateColumns: "1.6fr repeat(5, 1fr)",
        gap: 12,
        alignItems: "center",
        padding: "12px 14px",
        background: "var(--paper-sheet)",
        border: "1px solid var(--rule-default)",
        borderLeftWidth: 4,
        borderLeftColor: weak ? "var(--status-review-fg)" : "var(--rule-default)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <span style={{ fontSize: 14, fontWeight: 500, color: "var(--ink-primary)" }}>{category}</span>
        {weak && (
          <span style={{ fontSize: 12, color: "var(--status-review-fg)" }}>
            Weak: read these findings with extra care
          </span>
        )}
      </div>
      <MetricCell variant={notMeasured ? "not-measured" : "value"} label="Support" value="42" support={42} />
      <MetricCell variant={metric} label="Precision" value={weak ? "0.58" : "0.89"} support={42} />
      <MetricCell variant={metric} label="Recall" value={weak ? "0.41" : "0.82"} support={42} />
      <MetricCell variant={weak ? "value" : metric} label="Silent miss" value={weak ? "0.34" : "0.07"} support={42} />
      <MetricCell variant={notMeasured ? "not-measured" : "value"} label="Abstention" value="0.12" support={42} />
    </div>
  );
}
