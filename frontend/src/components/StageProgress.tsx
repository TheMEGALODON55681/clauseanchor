import Spinner from "./Spinner";
import Button from "./Button";
import { CheckIcon, PersonWithDocIcon, BrokenLinkIcon } from "./icons";

export type StepState = "pending" | "active" | "done" | "partial" | "failed";

export type Step = { label: string; state: StepState; detail?: string };

const DEFAULT_STEPS: Step[] = [
  { label: "Reading document", state: "done" },
  { label: "Finding clauses", state: "active", detail: "18 of 46 categories" },
  { label: "Checking confidence", state: "pending" },
  { label: "Indian law review", state: "pending" },
  { label: "Finding case law", state: "pending" },
  { label: "Final checks", state: "pending" },
];

function Marker({ state }: { state: StepState }) {
  if (state === "active") return <Spinner size={14} />;
  if (state === "done")
    return (
      <span style={{ color: "var(--status-found-fg)", display: "inline-flex" }}>
        <CheckIcon size={16} />
      </span>
    );
  if (state === "partial")
    return (
      <span style={{ color: "var(--status-review-fg)", display: "inline-flex" }}>
        <PersonWithDocIcon size={16} />
      </span>
    );
  if (state === "failed")
    return (
      <span style={{ color: "var(--status-unavailable-fg)", display: "inline-flex" }}>
        <BrokenLinkIcon size={16} />
      </span>
    );
  return (
    <span
      aria-hidden
      style={{ width: 14, height: 14, borderRadius: 999, border: "1.5px solid var(--rule-strong)", display: "inline-block" }}
    />
  );
}

export default function StageProgress({
  steps = DEFAULT_STEPS,
  compact = false,
  showCancel = true,
  onCancel,
}: {
  steps?: Step[];
  compact?: boolean;
  showCancel?: boolean;
  onCancel?: () => void;
}) {
  if (compact) {
    const active = steps.find((s) => s.state === "active") ?? steps[steps.length - 1];
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8 }} aria-live="polite">
        <Marker state={active.state} />
        <span style={{ fontSize: 13, color: "var(--ink-secondary)" }}>
          {active.label}
          {active.detail ? `: ${active.detail}` : ""}
        </span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 260 }} aria-live="polite">
      <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 2 }}>
        {steps.map((s) => {
          const muted = s.state === "pending";
          const color =
            s.state === "partial"
              ? "var(--status-review-fg)"
              : s.state === "failed"
              ? "var(--status-unavailable-fg)"
              : muted
              ? "var(--ink-tertiary)"
              : "var(--ink-primary)";
          return (
            <li key={s.label} style={{ display: "flex", alignItems: "center", gap: 10, minHeight: 28 }}>
              <Marker state={s.state} />
              <span style={{ fontSize: 14, color }}>{s.label}</span>
              {s.detail && (
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)" }}>
                  {s.detail}
                </span>
              )}
            </li>
          );
        })}
      </ol>
      {showCancel && (
        <div style={{ marginTop: 8 }}>
          <Button variant="secondary" size="s" onClick={onCancel}>Cancel</Button>
        </div>
      )}
    </div>
  );
}
