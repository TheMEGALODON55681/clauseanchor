import { useState } from "react";
import type { StatusKind } from "./StatusChip";

export type RulerVariant =
  | "default"
  | "hover"
  | "grouped"
  | "selected"
  | "focus"
  | "empty";

export type RulerMark = Mark;
type Mark = {
  /** position 0..1 down the document */
  at: number;
  status: StatusKind;
  label: string;
  /** number of grouped findings collapsed into this mark */
  count?: number;
};

type MarginRulerProps = {
  variant?: RulerVariant;
  height?: number | string;
  marks?: Mark[];
  selected?: number | null;
  onSelect?: (index: number) => void;
  /** Viewport box, 0..1 from top, and its fractional height. */
  viewport?: { top: number; size: number };
  caption?: string;
};

const MARK_COLOR: Record<StatusKind, string> = {
  found: "var(--status-found-fg)",
  review: "var(--status-review-fg)",
  unvalidated: "var(--status-unvalidated-fg)",
  absent: "var(--status-absent-fg)",
  unavailable: "var(--status-unavailable-fg)",
};

const DEFAULT_MARKS: Mark[] = [
  { at: 0.08, status: "found", label: "Definitions, clause 1.2" },
  { at: 0.22, status: "review", label: "Indemnity, clause 7.1" },
  { at: 0.4, status: "found", label: "Confidentiality, clause 9.4" },
  { at: 0.58, status: "found", label: "Non-compete, clause 11.3" },
  { at: 0.74, status: "unvalidated", label: "Assignment, clause 14.2" },
  { at: 0.9, status: "found", label: "Governing law, clause 18.1" },
];

const GROUPED_MARKS: Mark[] = [
  { at: 0.2, status: "found", label: "3 findings near clause 7", count: 3 },
  { at: 0.55, status: "review", label: "2 findings near clause 11", count: 2 },
  { at: 0.85, status: "found", label: "Governing law, clause 18.1" },
];

export default function MarginRuler({
  variant = "default",
  height = 320,
  marks: marksProp,
  selected,
  onSelect,
  viewport,
  caption,
}: MarginRulerProps) {
  const [hovered, setHovered] = useState<number | null>(
    variant === "hover" ? 3 : null
  );
  const marks =
    marksProp ?? (variant === "empty" ? [] : variant === "grouped" ? GROUPED_MARKS : DEFAULT_MARKS);
  const selectedIndex = selected !== undefined ? selected : variant === "selected" ? 3 : null;

  return (
    <div className="inline-flex flex-col items-center gap-2 font-sans">
      <div
        role="group"
        aria-label="Where findings appear in the document"
        tabIndex={0}
        className="focus:outline-none focus-visible:outline-none"
        style={{
          position: "relative",
          width: 28,
          height,
          background: "var(--paper-base)",
          ...(variant === "focus"
            ? { outline: "2px solid var(--focus-ring)", outlineOffset: 2 }
            : {}),
        }}
        onFocus={(e) => {
          if (variant !== "focus")
            e.currentTarget.style.outline = "2px solid var(--focus-ring)";
          e.currentTarget.style.outlineOffset = "2px";
        }}
        onBlur={(e) => {
          if (variant !== "focus") e.currentTarget.style.outline = "none";
        }}
      >
        {/* Ledger rule */}
        <div
          style={{
            position: "absolute",
            left: 14,
            top: 0,
            bottom: 0,
            width: 1,
            background: "var(--rule-strong)",
          }}
        />
        {/* Tick marks every 10% */}
        {Array.from({ length: 11 }).map((_, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 10,
              top: `${(i / 10) * 100}%`,
              width: 5,
              height: 1,
              background: "var(--rule-default)",
            }}
          />
        ))}

        {/* Viewport position box */}
        <div
          style={{
            position: "absolute",
            left: 3,
            right: 3,
            top: viewport ? `${viewport.top * 100}%` : "48%",
            height: viewport ? `${Math.max(viewport.size * 100, 2)}%` : 56,
            borderRadius: 2,
            background: "color-mix(in srgb, var(--anchor-600) 10%, transparent)",
            border: "1px solid color-mix(in srgb, var(--anchor-600) 35%, transparent)",
          }}
          aria-hidden
        />

        {/* Finding marks */}
        {marks.map((m, i) => {
          const isHover = hovered === i;
          const isSelected = selectedIndex === i;
          return (
            <div
              key={i}
              role={onSelect ? "button" : undefined}
              tabIndex={onSelect ? 0 : undefined}
              aria-label={onSelect ? m.label : undefined}
              onClick={onSelect ? () => onSelect(i) : undefined}
              onKeyDown={
                onSelect
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(i);
                      }
                    }
                  : undefined
              }
              onFocus={() => setHovered(i)}
              onBlur={() => setHovered(null)}
              className={onSelect ? "focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]" : undefined}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => variant !== "hover" && setHovered(null)}
              style={{
                position: "absolute",
                left: isSelected ? 4 : 8,
                top: `calc(${m.at * 100}% - 1.5px)`,
                width: isSelected ? 20 : 12,
                height: 3,
                borderRadius: 1,
                background: MARK_COLOR[m.status],
                cursor: "pointer",
                boxShadow: isSelected
                  ? "0 0 0 1px var(--paper-sheet), 0 0 0 2px var(--anchor-600)"
                  : "none",
              }}
            >
              {m.count && m.count > 1 && (
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    left: 14,
                    top: -8,
                    fontFamily: "var(--font-mono)",
                    fontSize: 10,
                    color: "var(--ink-tertiary)",
                  }}
                >
                  {m.count}
                </span>
              )}
              {isHover && (
                <div
                  role="tooltip"
                  style={{
                    position: "absolute",
                    right: 20,
                    top: -8,
                    whiteSpace: "nowrap",
                    background: "var(--ink-primary)",
                    color: "var(--paper-sheet)",
                    fontSize: 12,
                    padding: "3px 8px",
                    borderRadius: "var(--radius-sm)",
                    zIndex: 2,
                  }}
                >
                  {m.label}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <p
        style={{
          maxWidth: 140,
          fontSize: 11,
          lineHeight: "15px",
          color: "var(--ink-tertiary)",
          textAlign: "center",
        }}
      >
        {caption ??
          (variant === "empty" || marks.length === 0
            ? "No findings yet."
            : "Mark size does not mean severity.")}
      </p>
    </div>
  );
}
