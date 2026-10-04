import type { CSSProperties, ReactNode } from "react";
import {
  ExposureIcon,
  ProtectionIcon,
  MixedIcon,
  NeutralIcon,
  UnresolvedIcon,
} from "./icons";

export type PolarityKind =
  | "exposure"
  | "protection"
  | "mixed"
  | "neutral"
  | "unresolved";

type PolarityBadgeProps = {
  polarity: PolarityKind;
};

const CONFIG: Record<
  PolarityKind,
  { label: string; icon: (p: { size: number }) => ReactNode; style: CSSProperties }
> = {
  exposure: {
    label: "Burden on you",
    icon: ({ size }) => <ExposureIcon size={size} />,
    style: { color: "var(--polarity-exposure-fg)", background: "var(--polarity-exposure-bg)" },
  },
  protection: {
    label: "Benefits you",
    icon: ({ size }) => <ProtectionIcon size={size} />,
    style: { color: "var(--polarity-protection-fg)", background: "var(--polarity-protection-bg)" },
  },
  mixed: {
    label: "Both ways",
    icon: ({ size }) => <MixedIcon size={size} />,
    style: { color: "var(--polarity-mixed-fg)", background: "var(--polarity-mixed-bg)" },
  },
  neutral: {
    label: "No direction",
    icon: ({ size }) => <NeutralIcon size={size} />,
    style: { color: "var(--polarity-neutral-fg)", background: "var(--polarity-neutral-bg)" },
  },
  unresolved: {
    label: "Party unclear",
    icon: ({ size }) => <UnresolvedIcon size={size} />,
    style: {
      color: "var(--polarity-unresolved-fg)",
      background: "transparent",
      border: "1px dotted var(--polarity-unresolved-fg)",
    },
  },
};

export default function PolarityBadge({ polarity }: PolarityBadgeProps) {
  const cfg = CONFIG[polarity];
  return (
    <span
      className="inline-flex items-center gap-1.5 font-sans font-medium whitespace-nowrap"
      style={{
        ...cfg.style,
        borderRadius: "var(--radius-sm)",
        paddingInline: 8,
        paddingBlock: 4,
        fontSize: 14,
        lineHeight: 1.2,
      }}
    >
      {cfg.icon({ size: 16 })}
      {cfg.label}
    </span>
  );
}
