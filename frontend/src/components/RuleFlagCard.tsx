import Button from "./Button";
import StatuteTag from "./StatuteTag";
import { SectionIcon, ExternalIcon } from "./icons";

export type RuleFlagVariant = "standard" | "verify" | "applicability-unclear";

type RuleFlagCardProps = {
  variant?: RuleFlagVariant;
  citation?: string;
  note?: string;
};

const NOTE: Record<RuleFlagVariant, string> = {
  standard: "Restraint-of-trade review: Section 27, Indian Contract Act 1872.",
  verify: "Liquidated damages review: Section 74, Indian Contract Act 1872.",
  "applicability-unclear": "Governing law may not be Indian law.",
};

export default function RuleFlagCard({ variant = "standard", citation, note }: RuleFlagCardProps) {
  const unclear = variant === "applicability-unclear";
  return (
    <div
      style={{
        background: "var(--statute-bg)",
        border: "1px solid var(--statute-border)",
        borderLeftWidth: 4,
        borderLeftColor: "var(--statute-fg)",
        borderRadius: "var(--radius-md)",
        padding: "12px 14px",
      }}
    >
      <div className="flex items-center gap-2" style={{ color: "var(--statute-fg)" }}>
        <SectionIcon size={18} />
        <span style={{ fontWeight: 600, fontSize: 14 }}>Review under Indian law</span>
        {variant === "verify" && (
          <span
            style={{
              marginLeft: "auto",
              fontSize: 12,
              fontWeight: 500,
              color: "var(--status-review-fg)",
              background: "var(--status-review-bg)",
              border: "1px solid var(--status-review-border)",
              borderRadius: "var(--radius-sm)",
              padding: "1px 6px",
            }}
          >
            Verify with counsel
          </span>
        )}
      </div>

      <p style={{ fontSize: 13, lineHeight: "20px", color: "var(--ink-secondary)", marginTop: 6 }}>
        {note ?? NOTE[variant]}
      </p>

      {!unclear && (
        <div style={{ marginTop: 8 }}>
          <StatuteTag citation={citation ?? (variant === "verify" ? "Section 74, Indian Contract Act 1872" : "Section 27, Indian Contract Act 1872")} />
        </div>
      )}

      <div style={{ marginTop: 8 }}>
        <Button variant="tertiary" size="s" icon="trailing" iconNode={<ExternalIcon size={14} />}>
          Read the section
        </Button>
      </div>
    </div>
  );
}
