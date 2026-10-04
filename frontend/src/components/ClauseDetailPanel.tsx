import type { ReactNode } from "react";
import StatusChip, { type StatusKind } from "./StatusChip";
import PolarityBadge, { type PolarityKind } from "./PolarityBadge";
import ConfidenceBand, { type ConfidenceVariant } from "./ConfidenceBand";
import JudgmentCard from "./JudgmentCard";
import RuleFlagCard from "./RuleFlagCard";
import Button from "./Button";
import { CloseIcon } from "./icons";

export type PanelVariant =
  | "found"
  | "review"
  | "absent"
  | "unavailable"
  | "loading";

/** Live data for the reader. When omitted, the gallery sample renders. */
export type PanelData = {
  title: string;
  status: StatusKind;
  sectionPath?: string | null;
  offsets?: { start: number; end: number } | null;
  quote?: string;
  polarity?: PolarityKind;
  confidence?: ConfidenceVariant;
  reviewNote?: string;
  ruleFlags?: ReactNode;
  caseLaw?: ReactNode;
  caseLawCount?: number;
  emptyTitle?: string;
  emptyBody?: string;
  onRetry?: () => void;
  /** Pager for categories with more than one span. */
  pager?: ReactNode;
};

type ClauseDetailPanelProps = {
  variant?: PanelVariant;
  data?: PanelData;
  onClose?: () => void;
  /** Fill the parent instead of the fixed 400px card. */
  fill?: boolean;
  /** Replace the body with custom content inside the same shell. */
  custom?: { title: string; content: ReactNode };
};

const STATUS_FOR: Record<Exclude<PanelVariant, "loading">, StatusKind> = {
  found: "found",
  review: "review",
  absent: "absent",
  unavailable: "unavailable",
};

const CONFIDENCE_FOR: Record<"found" | "review", ConfidenceVariant> = {
  found: "higher",
  review: "review",
};

const CLAUSE_TEXT =
  "During the Term and for a period of two (2) years thereafter, the Employee shall not, directly or indirectly, engage in any business that competes with the Company within India.";

function Shell({ children, fill = false }: { children: ReactNode; fill?: boolean }) {
  return (
    <div
      className="font-sans flex flex-col"
      style={
        fill
          ? { width: "100%", minHeight: "100%", background: "var(--paper-base)" }
          : {
              width: 400,
              maxWidth: "100%",
              background: "var(--paper-base)",
              border: "1px solid var(--rule-default)",
              borderRadius: "var(--radius-lg)",
              boxShadow: "var(--elevation-2)",
              overflow: "hidden",
            }
      }
    >
      {children}
    </div>
  );
}

function Skel({ w, h = 12 }: { w: number | string; h?: number }) {
  return (
    <div
      className="shimmer"
      style={{
        width: w,
        height: h,
        borderRadius: 3,
        background: "var(--paper-sunken)",
      }}
    />
  );
}

function PanelHeader({ title, chip, onClose }: { title: string; chip?: ReactNode; onClose?: () => void }) {
  return (
    <div
      className="flex items-start justify-between gap-3"
      style={{ padding: "16px 20px", borderBottom: "1px solid var(--rule-default)" }}
    >
      <div className="flex flex-col gap-2" style={{ minWidth: 0 }}>
        <h2
          id="detail-panel-title"
          tabIndex={-1}
          className="focus:outline-none"
          style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 22, lineHeight: "30px", color: "var(--ink-primary)" }}
        >
          {title}
        </h2>
        {chip}
      </div>
      <Button variant="secondary" size="s" icon="icon-only" aria-label="Close panel" onClick={onClose} iconNode={<CloseIcon size={18} />} />
    </div>
  );
}

export default function ClauseDetailPanel({ variant = "found", data, onClose, fill = false, custom }: ClauseDetailPanelProps) {
  if (custom) {
    return (
      <Shell fill={fill}>
        <PanelHeader title={custom.title} onClose={onClose} />
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>{custom.content}</div>
      </Shell>
    );
  }
  if (data) return <LivePanel data={data} onClose={onClose} fill={fill} />;
  if (variant === "loading") {
    return (
      <Shell fill={fill}>
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
          <Skel w={180} h={20} />
          <Skel w={120} />
          <Skel w="100%" h={72} />
          <div className="flex gap-2">
            <Skel w={110} h={24} />
            <Skel w={120} h={24} />
          </div>
          <Skel w="100%" h={90} />
        </div>
      </Shell>
    );
  }

  const status = STATUS_FOR[variant];
  const found = variant === "found" || variant === "review";

  return (
    <Shell>
      {/* Header */}
      <div
        className="flex items-start justify-between gap-3"
        style={{ padding: "16px 20px", borderBottom: "1px solid var(--rule-default)" }}
      >
        <div className="flex flex-col gap-2">
          <h3
            style={{
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: 22,
              lineHeight: "30px",
              color: "var(--ink-primary)",
            }}
          >
            Non-compete
          </h3>
          <StatusChip status={status} size="s" />
        </div>
        <Button variant="secondary" size="s" icon="icon-only" aria-label="Close panel" iconNode={<CloseIcon size={18} />} />
      </div>

      <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Review notice */}
        {variant === "review" && (
          <div
            style={{
              borderLeft: "4px solid var(--status-review-fg)",
              background: "var(--status-review-bg)",
              borderRadius: "var(--radius-md)",
              padding: "10px 12px",
              fontSize: 13,
              lineHeight: "20px",
              color: "var(--status-review-fg)",
            }}
          >
            ClauseAnchor could not confirm this clause with enough confidence. A lawyer should read it.
          </div>
        )}

        {/* Breadcrumb + offset */}
        <div className="flex items-center justify-between gap-2">
          <span
            style={{
              fontFamily: "var(--font-serif)",
              fontWeight: 600,
              fontSize: 14,
              color: "var(--ink-secondary)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            Clause 11 › 11.3 › (b)
          </span>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--ink-tertiary)",
            }}
          >
            chars 4210 to 4488
          </span>
        </div>

        {found ? (
          <>
            {/* Quoted clause */}
            <div>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--ink-tertiary)",
                  marginBottom: 6,
                }}
              >
                From your contract
              </div>
              <div
                style={{
                  position: "relative",
                  background: "var(--paper-sheet)",
                  border: "1px solid var(--rule-default)",
                  borderRadius: "var(--radius-md)",
                  padding: "14px 22px",
                }}
              >
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    left: 6,
                    top: 10,
                    color: "var(--status-found-fg)",
                    fontFamily: "var(--font-serif)",
                  }}
                >
                  &#10214;
                </span>
                <p
                  style={{
                    fontFamily: "var(--font-serif)",
                    fontSize: 17,
                    lineHeight: "30px",
                    color: "var(--ink-primary)",
                  }}
                >
                  {CLAUSE_TEXT}
                </p>
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    right: 6,
                    bottom: 10,
                    color: "var(--status-found-fg)",
                    fontFamily: "var(--font-serif)",
                  }}
                >
                  &#10215;
                </span>
              </div>
            </div>

            {/* Polarity + confidence */}
            <div className="flex flex-wrap items-center gap-3">
              <PolarityBadge polarity="exposure" />
              <ConfidenceBand variant={CONFIDENCE_FOR[variant as "found" | "review"]} size="full" />
            </div>

            {/* Rule flag (wired to the RuleFlagCard component) */}
            <RuleFlagCard variant={variant === "review" ? "verify" : "standard"} />

            {/* Case law */}
            <div>
              <div
                className="flex items-center gap-2"
                style={{ fontSize: 15, fontWeight: 600, color: "var(--ink-primary)", marginBottom: 10 }}
              >
                Case law
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                    color: "var(--ink-tertiary)",
                    fontWeight: 400,
                  }}
                >
                  2
                </span>
              </div>
              <div className="flex flex-col gap-3">
                <JudgmentCard authority="reviewed" />
                <JudgmentCard authority="overruled" />
              </div>
            </div>
          </>
        ) : (
          <div
            style={{
              background: "var(--paper-sheet)",
              border: "1px solid var(--rule-default)",
              borderRadius: "var(--radius-md)",
              padding: 16,
            }}
          >
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--ink-primary)" }}>
              {variant === "absent"
                ? "No clause found at the validated threshold"
                : "This part of the review did not finish"}
            </p>
            <p style={{ fontSize: 13, lineHeight: "20px", color: "var(--ink-secondary)", marginTop: 8 }}>
              {variant === "absent"
                ? "ClauseAnchor did not locate a non-compete clause with validated confidence. This does not mean the contract has none, only that none was confirmed here."
                : "Processing did not complete for this category. This is a technical issue, not a legal finding."}
            </p>
            {variant === "unavailable" && (
              <div style={{ marginTop: 12 }}>
                <Button variant="secondary" size="s">
                  Try again
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Footer note */}
        <p style={{ fontSize: 13, lineHeight: "20px", color: "var(--ink-tertiary)", borderTop: "1px solid var(--rule-default)", paddingTop: 12 }}>
          ClauseAnchor quotes text. It does not decide what the law requires.
        </p>
      </div>
    </Shell>
  );
}

const eyebrow = {
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: "0.08em",
  textTransform: "uppercase" as const,
  color: "var(--ink-tertiary)",
  marginBottom: 6,
};

function LivePanel({ data, onClose, fill }: { data: PanelData; onClose?: () => void; fill: boolean }) {
  const hasQuote = !!data.quote;
  return (
    <Shell fill={fill}>
      <PanelHeader title={data.title} chip={<StatusChip status={data.status} size="s" />} onClose={onClose} />
      <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
        {data.reviewNote && (
          <div
            style={{
              borderLeft: "4px solid var(--status-review-fg)",
              background: "var(--status-review-bg)",
              borderRadius: "var(--radius-md)",
              padding: "10px 12px",
              fontSize: 13,
              lineHeight: "20px",
              color: "var(--status-review-fg)",
            }}
          >
            {data.reviewNote}
          </div>
        )}

        {(data.sectionPath || data.offsets) && (
          <div className="flex items-center justify-between gap-2" style={{ flexWrap: "wrap" }}>
            <span style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 14, color: "var(--ink-secondary)", fontVariantNumeric: "tabular-nums" }}>
              {data.sectionPath ?? ""}
            </span>
            {data.offsets && (
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)" }}>
                chars {data.offsets.start} to {data.offsets.end}
              </span>
            )}
          </div>
        )}

        {data.pager}

        {hasQuote ? (
          <>
            <div>
              <div style={eyebrow}>From your contract</div>
              <div
                style={{
                  position: "relative",
                  background: "var(--paper-sheet)",
                  border: "1px solid var(--rule-default)",
                  borderRadius: "var(--radius-md)",
                  padding: "14px 22px",
                }}
              >
                <span aria-hidden style={{ position: "absolute", left: 6, top: 10, color: "var(--status-found-fg)", fontFamily: "var(--font-serif)" }}>
                  &#10214;
                </span>
                <blockquote style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: "30px", color: "var(--ink-primary)", whiteSpace: "pre-wrap" }}>
                  {data.quote}
                </blockquote>
                <span aria-hidden style={{ position: "absolute", right: 6, bottom: 10, color: "var(--status-found-fg)", fontFamily: "var(--font-serif)" }}>
                  &#10215;
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {data.polarity && <PolarityBadge polarity={data.polarity} />}
              {data.confidence && <ConfidenceBand variant={data.confidence} size="full" />}
            </div>

            {data.ruleFlags}

            <div>
              <h3 className="flex items-center gap-2" style={{ fontSize: 15, fontWeight: 600, color: "var(--ink-primary)", marginBottom: 10 }}>
                Case law
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)", fontWeight: 400 }}>
                  {data.caseLawCount ?? 0}
                </span>
              </h3>
              <div className="flex flex-col gap-3">{data.caseLaw ?? <JudgmentCard state="empty" />}</div>
            </div>
          </>
        ) : (
          <div style={{ background: "var(--paper-sheet)", border: "1px solid var(--rule-default)", borderRadius: "var(--radius-md)", padding: 16 }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--ink-primary)" }}>{data.emptyTitle}</p>
            <p style={{ fontSize: 13, lineHeight: "20px", color: "var(--ink-secondary)", marginTop: 8 }}>{data.emptyBody}</p>
            {data.onRetry && (
              <div style={{ marginTop: 12 }}>
                <Button variant="secondary" size="s" onClick={data.onRetry}>
                  Try again
                </Button>
              </div>
            )}
          </div>
        )}

        <p style={{ fontSize: 13, lineHeight: "20px", color: "var(--ink-tertiary)", borderTop: "1px solid var(--rule-default)", paddingTop: 12 }}>
          ClauseAnchor quotes text. It does not decide what the law requires.
        </p>
      </div>
    </Shell>
  );
}
