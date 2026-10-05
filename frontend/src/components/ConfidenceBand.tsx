import { useState } from "react";

export type ConfidenceVariant = "higher" | "review" | "unvalidated";
export type BandSize = "compact" | "full";
/** How the band was calibrated, when the data says so. */
export type CalibrationScope = "category" | "pooled";

type ConfidenceBandProps = {
  variant: ConfidenceVariant;
  size?: BandSize;
  /** Calibration detail. Without it the band shows only its label, because the label is all the data gives. */
  calibration?: CalibrationScope;
};

const TRACK_W = 160;

const CONFIG: Record<
  ConfidenceVariant,
  { label: string; segment: { left: number; width: number } | null; color: string }
> = {
  // A shaded range, not a point, like a tolerance band on a technical drawing.
  higher: { label: "Higher confidence", segment: { left: 66, width: 30 }, color: "var(--anchor-600)" },
  review: { label: "Needs a lawyer", segment: { left: 34, width: 34 }, color: "var(--status-review-fg)" },
  unvalidated: { label: "Confidence not validated", segment: null, color: "var(--status-unvalidated-fg)" },
};

export default function ConfidenceBand({ variant, size = "compact", calibration }: ConfidenceBandProps) {
  const [open, setOpen] = useState(false);
  const cfg = CONFIG[variant];
  const trackWidth = size === "compact" ? 120 : TRACK_W;
  const labelStyle = {
    fontSize: size === "compact" ? 12 : 13,
    fontWeight: 500,
    color: cfg.color,
    // The track gives way in a narrow panel, never the label.
    flexShrink: 0,
    whiteSpace: "nowrap",
  } as const;

  const track = (
    <div
      aria-hidden
      style={{
        position: "relative",
        width: trackWidth,
        minWidth: 64,
        height: 8,
        borderRadius: 2,
        background: "var(--paper-sunken)",
        ...(cfg.segment
          ? {}
          : {
              background: "transparent",
              border: "1px dashed var(--status-unvalidated-border)",
            }),
      }}
    >
      {cfg.segment && (
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: `${cfg.segment.left}%`,
            width: `${cfg.segment.width}%`,
            borderRadius: 2,
            background: cfg.color,
            opacity: variant === "review" ? 0.85 : 1,
          }}
        />
      )}
    </div>
  );

  return (
    <div className="font-sans inline-flex flex-col gap-2">
      <div className="flex items-center gap-3">
        {track}
        {calibration ? (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="text-left hit"
            style={{
              ...labelStyle,
              textDecoration: "underline",
              textUnderlineOffset: 3,
              textDecorationStyle: variant === "unvalidated" ? "dashed" : "solid",
            }}
            aria-expanded={open}
          >
            {cfg.label}
          </button>
        ) : (
          <span style={labelStyle}>{cfg.label}</span>
        )}
      </div>

      {calibration && open && (
        <div
          style={{
            width: size === "compact" ? 240 : 300,
            padding: 12,
            borderRadius: "var(--radius-md)",
            background: "var(--paper-sheet)",
            border: "1px solid var(--rule-default)",
            boxShadow: "var(--elevation-2)",
          }}
        >
          <p style={{ fontSize: 13, color: "var(--ink-primary)" }}>
            Calibration: {calibration === "pooled" ? "pooled" : "category-specific"}
          </p>
        </div>
      )}
    </div>
  );
}
