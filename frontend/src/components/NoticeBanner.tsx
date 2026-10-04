import type { ReactNode } from "react";
import Button from "./Button";
import { InfoIcon, AnchorIcon, PersonWithDocIcon, CloseIcon } from "./icons";

export type NoticeVariant = "legal-scope" | "privacy" | "sample-mode" | "session-expiry" | "review-scope";

type NoticeBannerProps = {
  variant: NoticeVariant;
  onDismiss?: () => void;
  /** Override the fixed text, used for live countdowns. */
  text?: string;
  onAction?: () => void;
};

const FIXED: Record<NoticeVariant, string> = {
  "legal-scope":
    "Not legal advice. ClauseAnchor points to text in your contract and in published judgments. It does not tell you what the law requires.",
  privacy: "Your contract is processed in memory and deleted within 60 minutes.",
  "sample-mode": "Sample mode: showing a prepared example. Uploads are turned off.",
  "session-expiry": "This session ends in 8 minutes. Download your report before it closes.",
  "review-scope":
    "This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment.",
};

function config(variant: NoticeVariant, onAction?: () => void): {
  rule: string;
  bg: string;
  fg: string;
  icon: ReactNode;
  dismissible: boolean;
  action?: ReactNode;
} {
  switch (variant) {
    case "legal-scope":
      return {
        rule: "var(--anchor-600)",
        bg: "var(--anchor-100)",
        fg: "var(--anchor-700)",
        icon: <AnchorIcon size={18} />,
        dismissible: false,
      };
    case "privacy":
      return {
        rule: "var(--rule-strong)",
        bg: "var(--paper-sunken)",
        fg: "var(--ink-secondary)",
        icon: <InfoIcon size={18} />,
        dismissible: true,
      };
    case "sample-mode":
      return {
        rule: "var(--status-review-fg)",
        bg: "var(--status-review-bg)",
        fg: "var(--status-review-fg)",
        icon: <PersonWithDocIcon size={18} />,
        dismissible: false,
      };
    case "review-scope":
      return {
        rule: "var(--anchor-600)",
        bg: "var(--paper-sheet)",
        fg: "var(--anchor-600)",
        icon: <InfoIcon size={18} />,
        dismissible: false,
      };
    case "session-expiry":
      return {
        rule: "var(--rule-strong)",
        bg: "var(--paper-sunken)",
        fg: "var(--ink-secondary)",
        icon: <InfoIcon size={18} />,
        dismissible: false,
        action: (
          <Button variant="primary" size="s" onClick={onAction}>
            Download report
          </Button>
        ),
      };
  }
}

export default function NoticeBanner({ variant, onDismiss, text, onAction }: NoticeBannerProps) {
  const c = config(variant, onAction);
  return (
    <div
      role="note"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        background: c.bg,
        border: "1px solid var(--rule-default)",
        borderLeftWidth: 4,
        borderLeftColor: c.rule,
        borderRadius: "var(--radius-md)",
        padding: "12px 14px",
      }}
    >
      <span style={{ color: c.fg, marginTop: 1, display: "inline-flex" }}>{c.icon}</span>
      <p style={{ flex: 1, fontSize: 14, lineHeight: "20px", color: "var(--ink-primary)" }}>
        {text ?? FIXED[variant]}
      </p>
      {c.action}
      {c.dismissible && (
        <button
          type="button"
          aria-label="Dismiss notice"
          onClick={onDismiss}
          className="focus:outline-none focus-visible:outline-none"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 24,
            height: 24,
            color: "var(--ink-tertiary)",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            borderRadius: "var(--radius-sm)",
          }}
          onFocus={(e) => {
            e.currentTarget.style.outline = "2px solid var(--focus-ring)";
            e.currentTarget.style.outlineOffset = "2px";
          }}
          onBlur={(e) => (e.currentTarget.style.outline = "none")}
        >
          <CloseIcon size={16} />
        </button>
      )}
    </div>
  );
}
