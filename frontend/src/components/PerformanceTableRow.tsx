import MetricCell from "./MetricCell";

export type PerfVariant = "strong" | "weak" | "not-measured";

/* Six columns from 768 px. Below that the name and the support take a line each and the four
   measures sit two by two, so no cell clips and no text drops under 12 px. The header row of the
   page uses the same columns. */
export const PERF_COLUMNS = "md:grid-cols-[minmax(140px,1.6fr)_repeat(5,minmax(72px,1fr))]";

type PerformanceTableRowProps = {
  category: string;
  variant?: PerfVariant;
  metrics: { support: number; precision: number | null; recall: number | null; silentMiss: number | null; abstention: number | null };
};

/* One row for the accuracy page. A weak row takes the ochre tint and a label. A value that
   was not measured says so and never shows a zero. */
export default function PerformanceTableRow({ category, variant = "strong", metrics }: PerformanceTableRowProps) {
  const weak = variant === "weak";
  const measure = (label: string, v: number | null, emphasis = false) => (
    <div role="cell">
      {v === null ? (
        <MetricCell variant="not-measured" label={label} />
      ) : (
        <MetricCell variant={metrics.support < 10 ? "insufficient" : "value"} label={label} value={v.toFixed(2)} emphasis={emphasis} />
      )}
    </div>
  );
  return (
    <div
      role="row"
      className={`grid grid-cols-2 items-start gap-3 border-b px-3 py-3 md:items-center md:[&_.metric-label]:sr-only ${PERF_COLUMNS}`}
      style={{ borderColor: "var(--rule-default)", background: weak ? "var(--status-review-bg)" : "var(--paper-sheet)" }}
    >
      <div role="rowheader" className="col-span-2 flex flex-col gap-0.5 md:col-span-1">
        <span style={{ fontSize: 14, fontWeight: 500, color: "var(--ink-primary)" }}>{category}</span>
        {weak && <span style={{ fontSize: 12, color: "var(--status-review-fg)" }}>Weak: read these findings with extra care</span>}
      </div>
      <div role="cell" className="col-span-2 md:col-span-1">
        <MetricCell variant="value" label="Support" value={String(metrics.support)} />
      </div>
      {measure("Precision", metrics.precision)}
      {measure("Recall", metrics.recall)}
      {measure("Silent miss", metrics.silentMiss, true)}
      {measure("Abstention", metrics.abstention)}
    </div>
  );
}
