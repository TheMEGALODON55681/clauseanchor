import { useState } from "react";
import type { CSSProperties, ReactNode } from "react";

export type SpanKind =
  | "found"
  | "review"
  | "focused"
  | "overlap2"
  | "overlap3"
  | "hover"
  | "keyboard";

/* An inline mark: underline + faint tint, never a filled box.
   Text stays fully legible. */
export function markStyle(kind: SpanKind, hovered: boolean): CSSProperties {
  switch (kind) {
    case "found":
      return {
        background: "var(--mark-found-tint)",
        boxShadow: "inset 0 -2px 0 var(--mark-found-line)",
      };
    case "review":
      return {
        background: "var(--mark-review-tint)",
        borderBottom: "2px dashed var(--mark-review-line)",
      };
    case "focused":
      return {
        background: "var(--mark-focused-tint)",
        outline: "1px solid var(--status-found-fg)",
        borderRadius: 2,
      };
    case "overlap2":
      return {
        background: "var(--mark-found-tint)",
        boxShadow:
          "inset 0 -2px 0 var(--mark-found-line), inset 0 -6px 0 -2px var(--mark-review-line)",
      };
    case "overlap3":
      return {
        background: "var(--mark-found-tint)",
        boxShadow:
          "inset 0 -2px 0 var(--mark-found-line), inset 0 -6px 0 -2px var(--mark-review-line), inset 0 -10px 0 -4px var(--status-found-fg)",
      };
    case "hover":
      return {
        background: hovered ? "var(--mark-focused-tint)" : "var(--mark-found-tint)",
        boxShadow: "inset 0 -2px 0 var(--mark-found-line)",
        cursor: "pointer",
      };
    case "keyboard":
      return {
        background: "var(--mark-found-tint)",
        boxShadow: "inset 0 -2px 0 var(--mark-found-line)",
        outline: "2px solid var(--focus-ring)",
        outlineOffset: 2,
        borderRadius: 2,
      };
  }
}

function Mark({
  kind,
  children,
  bracket,
  marginMarker,
  tooltip,
}: {
  kind: SpanKind;
  children: ReactNode;
  bracket?: boolean;
  marginMarker?: string;
  tooltip?: string;
}) {
  const [hovered, setHovered] = useState(false);
  const showTip = tooltip && hovered;
  return (
    <span style={{ position: "relative" }}>
      {bracket && (
        <span
          aria-hidden
          style={{
            position: "absolute",
            left: -14,
            color: "var(--status-found-fg)",
            fontFamily: "var(--font-serif)",
          }}
        >
          &#10214;
        </span>
      )}
      <span
        tabIndex={kind === "keyboard" || kind === "hover" ? 0 : undefined}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          ...markStyle(kind, hovered),
          paddingBottom: 3,
          transition: "background 120ms ease-out",
        }}
      >
        {children}
      </span>
      {bracket && (
        <span
          aria-hidden
          style={{ color: "var(--status-found-fg)", fontFamily: "var(--font-serif)", marginLeft: 2 }}
        >
          &#10215;
        </span>
      )}
      {marginMarker && (
        <span
          aria-hidden
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: "var(--ink-tertiary)",
            verticalAlign: "super",
            marginLeft: 2,
          }}
        >
          {marginMarker}
        </span>
      )}
      {showTip && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            left: 0,
            top: "-1.9em",
            whiteSpace: "nowrap",
            background: "var(--ink-primary)",
            color: "var(--paper-sheet)",
            fontFamily: "var(--font-sans)",
            fontSize: 12,
            padding: "3px 8px",
            borderRadius: "var(--radius-sm)",
            zIndex: 2,
          }}
        >
          {tooltip}
        </span>
      )}
    </span>
  );
}

/** A paragraph of contract text with one demonstrated highlight kind. */
export default function SpanHighlight({ kind }: { kind: SpanKind }) {
  return (
    <p
      style={{
        fontFamily: "var(--font-serif)",
        fontSize: 17,
        lineHeight: "30px",
        color: "var(--ink-primary)",
        maxWidth: "72ch",
        marginLeft: 16,
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-serif)",
          fontWeight: 600,
          marginRight: 8,
        }}
      >
        11.3
      </span>
      During the Term and for a period of two (2) years thereafter, the Employee
      shall not,{" "}
      {kind === "found" && (
        <Mark kind="found">directly or indirectly, engage in any business that competes</Mark>
      )}
      {kind === "review" && (
        <Mark kind="review">directly or indirectly, engage in any business that competes</Mark>
      )}
      {kind === "focused" && (
        <Mark kind="focused" bracket>
          directly or indirectly, engage in any business that competes
        </Mark>
      )}
      {kind === "overlap2" && (
        <Mark kind="overlap2">directly or indirectly, engage in any business that competes</Mark>
      )}
      {kind === "overlap3" && (
        <Mark kind="overlap3" marginMarker="+2">
          directly or indirectly, engage in any business that competes
        </Mark>
      )}
      {kind === "hover" && (
        <Mark kind="hover" tooltip="Non-compete">
          directly or indirectly, engage in any business that competes
        </Mark>
      )}
      {kind === "keyboard" && (
        <Mark kind="keyboard">directly or indirectly, engage in any business that competes</Mark>
      )}{" "}
      with the Company within India.
    </p>
  );
}
