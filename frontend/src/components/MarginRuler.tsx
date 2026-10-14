import { useRef, useState } from "react";
import type { StatusKind } from "./StatusChip";
import { nearestMark } from "../lib/reader";

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
  /** A number is the strip's height in px. A string is the height of the whole ruler, and the strip takes what the caption leaves. */
  height?: number | string;
  marks?: Mark[];
  selected?: number | null;
  /** Makes the strip a pointer overview: a click picks the nearest tick. Keyboard users reach every finding through the marks in the text and the category list. */
  onSelect?: (index: number) => void;
  /** Viewport box, 0..1 from top, and its fractional height. False draws none. */
  viewport?: { top: number; size: number } | false;
  /** An empty string draws no caption. */
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

/* The strip is a ledger rule with a tick for each finding. With onSelect it is a pointer
   overview: the nearest tick within 12 px of a click is picked, so neighbouring ticks never
   share a hit area, and the click zone is 44 px wide around the 28 px strip. */
export default function MarginRuler({
  variant = "default",
  height = 320,
  marks: marksProp,
  selected,
  onSelect,
  viewport,
  caption,
}: MarginRulerProps) {
  const [hovered, setHovered] = useState<number | null>(variant === "hover" ? 3 : null);
  const strip = useRef<HTMLDivElement>(null);
  const marks = marksProp ?? (variant === "empty" ? [] : variant === "grouped" ? GROUPED_MARKS : DEFAULT_MARKS);
  const selectedIndex = selected !== undefined ? selected : variant === "selected" ? 3 : null;
  const fill = typeof height === "string";

  const under = (clientY: number) => {
    const r = strip.current?.getBoundingClientRect();
    return r && r.height > 0 ? nearestMark(marks.map((m) => m.at), (clientY - r.top) / r.height, r.height) : -1;
  };

  return (
    <div className="flex flex-col items-center gap-2 font-sans" style={{ height: fill ? height : undefined }} aria-hidden>
      <div
        style={{ margin: "0 -8px", padding: "0 8px", flex: fill ? "1 1 0" : undefined, minHeight: 0, cursor: onSelect ? "pointer" : undefined }}
        onClick={onSelect ? (e) => {
          const i = under(e.clientY);
          if (i >= 0) onSelect(i);
        } : undefined}
        onMouseMove={onSelect ? (e) => {
          const i = under(e.clientY);
          setHovered(i >= 0 ? i : null);
        } : undefined}
        onMouseLeave={onSelect ? () => setHovered(null) : undefined}
      >
        <div
          ref={strip}
          style={{
            position: "relative",
            width: 28,
            height: fill ? "100%" : height,
            background: "var(--paper-base)",
            ...(variant === "focus" ? { outline: "2px solid var(--focus-ring)", outlineOffset: 2 } : {}),
          }}
        >
          {/* Ledger rule */}
          <div style={{ position: "absolute", left: 14, top: 0, bottom: 0, width: 1, background: "var(--rule-strong)" }} />
          {/* Tick marks every 10% */}
          {Array.from({ length: 11 }).map((_, i) => (
            <div key={i} style={{ position: "absolute", left: 10, top: `${(i / 10) * 100}%`, width: 5, height: 1, background: "var(--rule-default)" }} />
          ))}

          {/* Viewport position box */}
          {viewport !== false && (
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
            />
          )}

          {/* Finding ticks */}
          {marks.map((m, i) => {
            const isSelected = selectedIndex === i;
            return (
              <div
                key={i}
                data-ruler-mark
                style={{
                  position: "absolute",
                  left: isSelected ? 3 : 6,
                  top: `calc(${m.at * 100}% - 1.5px)`,
                  width: isSelected ? 22 : 16,
                  height: 3,
                  borderRadius: 1,
                  background: MARK_COLOR[m.status],
                  boxShadow: isSelected ? "0 0 0 1px var(--paper-sheet), 0 0 0 2px var(--anchor-600)" : "none",
                }}
              >
                {m.count && m.count > 1 && (
                  <span style={{ position: "absolute", left: 24, top: -8, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)" }}>
                    {m.count}
                  </span>
                )}
                {hovered === i && (
                  <div
                    style={{
                      position: "absolute",
                      right: 26,
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
      </div>
      {caption !== "" && (
        // The caption is as wide as the strip and its words spill evenly to both sides, so it never widens the column.
        <p style={{ width: 28, display: "flex", justifyContent: "center", whiteSpace: "nowrap", fontSize: 12, lineHeight: "15px", color: "var(--ink-tertiary)" }}>
          {caption ?? (variant === "empty" || marks.length === 0 ? "No findings yet." : "Mark size does not mean severity.")}
        </p>
      )}
    </div>
  );
}
