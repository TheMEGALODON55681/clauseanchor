import { useState } from "react";
import Button from "./Button";
import { IndexCardIcon, ExternalIcon } from "./icons";

export type Authority = "not-reviewed" | "reviewed" | "overruled";
export type JudgmentState = "collapsed" | "expanded" | "hover" | "focus" | "empty";

type JudgmentCardProps = {
  state?: JudgmentState;
  authority?: Authority;
  passage?: { caseName: string; court: string; year: number | null; citation: string; text: string; sourceUrl?: string };
};

const AUTHORITY: Record<Authority, { label: string; fg: string; bg: string; border: string }> = {
  "not-reviewed": {
    label: "Not yet reviewed",
    fg: "var(--polarity-neutral-fg)",
    bg: "var(--polarity-neutral-bg)",
    border: "var(--rule-default)",
  },
  reviewed: {
    label: "Reviewed as of Sep 2026",
    fg: "var(--status-found-fg)",
    bg: "var(--status-found-bg)",
    border: "var(--status-found-border)",
  },
  overruled: {
    label: "Later overruled or modified",
    fg: "var(--status-review-fg)",
    bg: "var(--status-review-bg)",
    border: "var(--status-review-border)",
  },
};

const PASSAGE =
  "A covenant which restrains a party from carrying on a lawful trade must be read narrowly, and the court will not enforce a restriction wider in area or duration than is necessary to protect a legitimate interest of the party in whose favour it is made.";
const EXTRA =
  " The burden of showing that the restriction is reasonable rests on the party seeking to enforce it, and any doubt is resolved in favour of the freedom to trade.";

export default function JudgmentCard({ state = "collapsed", authority = "reviewed", passage }: JudgmentCardProps) {
  const [expanded, setExpanded] = useState(state === "expanded");
  const isExpanded = state === "expanded" || expanded;
  const auth = AUTHORITY[authority];

  if (state === "empty") {
    return (
      <div
        className="font-sans"
        style={{
          background: "var(--paper-sheet)",
          border: "1px solid var(--rule-default)",
          borderRadius: "var(--radius-md)",
          padding: 16,
          color: "var(--ink-tertiary)",
          fontSize: 14,
        }}
      >
        <div className="flex items-center gap-2" style={{ color: "var(--ink-tertiary)" }}>
          <IndexCardIcon size={16} />
          <span>No verified case law found for this clause type yet.</span>
        </div>
      </div>
    );
  }

  const outline =
    state === "focus" ? { outline: "2px solid var(--focus-ring)", outlineOffset: 2 } : {};
  const hoverShadow = state === "hover" ? "var(--elevation-2)" : "var(--elevation-1)";

  return (
    <div
      className="font-sans"
      style={{
        position: "relative",
        background: "var(--paper-sheet)",
        borderRadius: "var(--radius-md)",
        borderLeft: "4px solid var(--evidence-fg)",
        border: "1px solid var(--rule-default)",
        borderLeftWidth: 4,
        borderLeftColor: "var(--evidence-fg)",
        boxShadow: hoverShadow,
        overflow: "hidden",
        ...outline,
      }}
    >
      <div style={{ padding: "14px 16px" }}>
        <div className="flex items-start gap-2">
          <span style={{ color: "var(--evidence-fg)", marginTop: 1 }}>
            <IndexCardIcon size={16} />
          </span>
          <div className="flex-1">
            {/* Case name: small caps citation style */}
            <div
              style={{
                fontFamily: "var(--font-serif)",
                fontWeight: 500,
                fontVariant: "small-caps",
                letterSpacing: "0.03em",
                fontSize: 14,
                color: "var(--ink-primary)",
              }}
            >
              {passage?.caseName ?? "Sample Traders Pvt. Ltd. v. Example Industries Ltd."}
            </div>
            <div style={{ fontSize: 13, color: "var(--ink-secondary)", marginTop: 2 }}>
              {passage ? `${passage.court}${passage.year ? `, ${passage.year}` : ""}` : "Supreme Court of India, 2019"}
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                color: "var(--ink-tertiary)",
                marginTop: 2,
              }}
            >
              {passage?.citation ?? "[Placeholder citation]"}
            </div>
          </div>
        </div>

        {/* Passage over faint ruled lines, wrapped in big quote marks */}
        <div
          className="ruled-lines"
          style={{
            marginTop: 12,
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            position: "relative",
          }}
        >
          <p
            style={{
              fontFamily: "var(--font-serif)",
              fontStyle: "italic",
              fontSize: 15,
              lineHeight: "26px",
              color: "var(--ink-primary)",
              display: "-webkit-box",
              WebkitBoxOrient: "vertical",
              WebkitLineClamp: isExpanded ? "unset" : 6,
              overflow: isExpanded ? "visible" : "hidden",
            }}
          >
            <span
              style={{ color: "var(--evidence-fg)", fontSize: 22, lineHeight: 0, verticalAlign: "-4px", marginRight: 2 }}
              aria-hidden
            >
              &#8220;
            </span>
            {passage ? passage.text : PASSAGE}
            {isExpanded && !passage && (
              <span style={{ color: "var(--ink-tertiary)" }}>{EXTRA}</span>
            )}
            <span
              style={{ color: "var(--evidence-fg)", fontSize: 22, lineHeight: 0, verticalAlign: "-4px", marginLeft: 2 }}
              aria-hidden
            >
              &#8221;
            </span>
          </p>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3" style={{ marginTop: 12, flexWrap: "wrap" }}>
          <span
            className="inline-flex items-center"
            style={{
              fontSize: 12,
              fontWeight: 500,
              color: auth.fg,
              background: auth.bg,
              border: `1px solid ${auth.border}`,
              borderRadius: "var(--radius-sm)",
              padding: "2px 8px",
            }}
          >
            {auth.label}
          </span>
          <div className="flex items-center gap-1">
            <Button variant="tertiary" size="s" onClick={() => setExpanded((v) => !v)}>
              {isExpanded ? "Hide passage" : "View full passage"}
            </Button>
            <Button
              variant="tertiary"
              size="s"
              icon="trailing"
              iconNode={<ExternalIcon size={14} />}
              onClick={passage?.sourceUrl ? () => window.open(passage.sourceUrl, "_blank", "noopener") : undefined}
            >
              Open source
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
