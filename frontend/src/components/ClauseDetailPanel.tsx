import type { ReactNode } from "react";
import StatusChip, { type StatusKind } from "./StatusChip";
import PolarityBadge, { type PolarityKind } from "./PolarityBadge";
import ConfidenceBand, { type CalibrationScope, type ConfidenceVariant } from "./ConfidenceBand";
import JudgmentCard from "./JudgmentCard";
import Button from "./Button";
import { Bar } from "./Skeleton";
import { CloseIcon } from "./icons";

/** What the panel shows. With no data and no custom content it draws its skeleton. */
export type PanelData = {
  title: string;
  status: StatusKind;
  sectionPath?: string | null;
  offsets?: { start: number; end: number } | null;
  quote?: string;
  polarity?: PolarityKind;
  confidence?: ConfidenceVariant;
  calibration?: CalibrationScope;
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

/** The note on a passage that may be the clause but missed the validated threshold. */
export const REVIEW_CANDIDATE_NOTE =
  "This passage may be the clause, but the evidence did not reach the validated threshold. A lawyer should read it with the surrounding text.";

type ClauseDetailPanelProps = {
  data?: PanelData;
  onClose?: () => void;
  /** Fill the parent instead of the fixed 400px card. */
  fill?: boolean;
  /** Replace the body with custom content inside the same shell. */
  custom?: { title: string; content: ReactNode };
  /** The title is a heading in the reader. A page that only shows the panel as an example sets "p". */
  titleAs?: "h2" | "p";
};

function Shell({ children, fill = false }: { children: ReactNode; fill?: boolean }) {
  return (
    <div
      className="font-sans flex flex-col"
      style={
        fill
          ? { width: "100%", minHeight: "100%", background: "var(--paper-base)" }
          : {
              width: "var(--panel-w, 400px)",
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

function PanelHeader({ title, chip, onClose, titleAs = "h2" }: { title: string; chip?: ReactNode; onClose?: () => void; titleAs?: "h2" | "p" }) {
  const Title = titleAs;
  return (
    <div
      className="flex items-start justify-between gap-3"
      style={{ padding: "16px 20px", borderBottom: "1px solid var(--rule-default)" }}
    >
      <div className="flex flex-col gap-2" style={{ minWidth: 0 }}>
        <Title
          {...(titleAs === "h2" ? { id: "detail-panel-title", tabIndex: -1 } : {})}
          style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 22, lineHeight: "30px", color: "var(--ink-primary)" }}
        >
          {title}
        </Title>
        {chip}
      </div>
      {onClose && <Button variant="secondary" size="s" icon="icon-only" aria-label="Close panel" onClick={onClose} iconNode={<CloseIcon size={18} />} />}
    </div>
  );
}

export default function ClauseDetailPanel({ data, onClose, fill = false, custom, titleAs }: ClauseDetailPanelProps) {
  if (custom) {
    return (
      <Shell fill={fill}>
        <PanelHeader title={custom.title} onClose={onClose} />
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>{custom.content}</div>
      </Shell>
    );
  }
  if (data) return <LivePanel data={data} onClose={onClose} fill={fill} titleAs={titleAs} />;
  return (
    <Shell fill={fill}>
      <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
        <Bar w={180} h={20} />
        <Bar w={120} />
        <Bar w="100%" h={72} />
        <div className="flex gap-2">
          <Bar w={110} h={24} />
          <Bar w={120} h={24} />
        </div>
        <Bar w="100%" h={90} />
      </div>
    </Shell>
  );
}

const eyebrow = {
  fontSize: 12,
  fontWeight: 600,
  letterSpacing: "0.08em",
  textTransform: "uppercase" as const,
  color: "var(--ink-tertiary)",
  marginBottom: 6,
};

function LivePanel({ data, onClose, fill, titleAs }: { data: PanelData; onClose?: () => void; fill: boolean; titleAs?: "h2" | "p" }) {
  const hasQuote = !!data.quote;
  /* A panel with no case law data leaves the section out. An empty list would claim a search that never ran. */
  const hasCaseLaw = data.caseLaw !== undefined || data.caseLawCount !== undefined;
  return (
    <Shell fill={fill}>
      <PanelHeader title={data.title} chip={<StatusChip status={data.status} size="s" />} onClose={onClose} titleAs={titleAs} />
      <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
        {data.reviewNote && (
          <div
            style={{
              border: "1px solid var(--status-review-border)",
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
              {data.confidence && <ConfidenceBand variant={data.confidence} size="full" calibration={data.calibration} />}
            </div>

            {data.ruleFlags}

            {hasCaseLaw && (
              <div>
                <h3 className="flex items-center gap-2" style={{ fontSize: 15, fontWeight: 600, color: "var(--ink-primary)", marginBottom: 10 }}>
                  Case law
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)", fontWeight: 400 }}>
                    {data.caseLawCount ?? 0}
                  </span>
                </h3>
                <div className="flex flex-col gap-3">{data.caseLaw ?? <JudgmentCard state="empty" />}</div>
              </div>
            )}
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
