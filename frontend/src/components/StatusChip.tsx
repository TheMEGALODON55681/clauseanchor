import type { CSSProperties, ReactNode } from "react";
import {
  AnchorIcon,
  PersonWithDocIcon,
  DashedCircleIcon,
  EmptyBracketIcon,
  BrokenLinkIcon,
} from "./icons";

export type StatusKind =
  | "found"
  | "review"
  | "unvalidated"
  | "absent"
  | "unavailable";
export type ChipSize = "s" | "m";

type StatusChipProps = {
  status: StatusKind;
  size?: ChipSize;
};

const CONFIG: Record<
  StatusKind,
  { label: string; icon: (p: { size: number }) => ReactNode; style: CSSProperties }
> = {
  found: {
    label: "Found",
    icon: ({ size }) => <AnchorIcon size={size} />,
    style: {
      color: "var(--status-found-fg)",
      background: "var(--status-found-bg)",
      border: "1px solid var(--status-found-border)",
    },
  },
  review: {
    label: "Needs a lawyer",
    icon: ({ size }) => <PersonWithDocIcon size={size} />,
    style: {
      color: "var(--status-review-fg)",
      background: "var(--status-review-bg)",
      border: "1px solid var(--status-review-border)",
    },
  },
  unvalidated: {
    label: "Confidence not validated",
    icon: ({ size }) => <DashedCircleIcon size={size} />,
    style: {
      color: "var(--status-unvalidated-fg)",
      background: "transparent",
      border: "1px dashed var(--status-unvalidated-border)",
    },
  },
  absent: {
    label: "Not found",
    icon: ({ size }) => <EmptyBracketIcon size={size} />,
    style: {
      color: "var(--status-absent-fg)",
      background: "var(--status-absent-bg)",
      border: "1px solid var(--status-absent-border)",
    },
  },
  unavailable: {
    label: "Unavailable",
    icon: ({ size }) => <BrokenLinkIcon size={size} />,
    style: {
      color: "var(--status-unavailable-fg)",
      background: "var(--status-unavailable-bg)",
      border: "1px solid var(--status-unavailable-border)",
    },
  },
};

export default function StatusChip({ status, size = "m" }: StatusChipProps) {
  const cfg = CONFIG[status];
  const iconSize = size === "s" ? 14 : 16;
  return (
    <span
      className="inline-flex items-center gap-1.5 font-sans font-medium whitespace-nowrap"
      style={{
        ...cfg.style,
        borderRadius: "var(--radius-sm)",
        paddingInline: size === "s" ? 6 : 8,
        paddingBlock: size === "s" ? 2 : 4,
        fontSize: size === "s" ? 12 : 14,
        letterSpacing: size === "s" ? "0.02em" : 0,
        lineHeight: 1.2,
      }}
    >
      {cfg.icon({ size: iconSize })}
      {cfg.label}
    </span>
  );
}
