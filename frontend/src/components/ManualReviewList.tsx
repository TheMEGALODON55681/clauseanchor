import { useState } from "react";
import Button from "./Button";
import SegmentedFilter from "./SegmentedFilter";
import OffsetTag from "./OffsetTag";
import Skeleton from "./Skeleton";
import { markStyle } from "./SpanHighlight";
import { BrokenLinkIcon, PilcrowIcon } from "./icons";

export type ManualItemVariant = "none" | "partial" | "unavailable";

export type ManualItem = {
  id: string;
  sectionPath: string | null;
  /** Passage text, already sliced with code point offsets. */
  text: string;
  start: number;
  end: number;
  variant: ManualItemVariant;
  /** Highlighted ranges inside `text`, as UTF-16 indexes into the preview. */
  marks?: [number, number][];
};

export type ManualListState = "loading" | "populated" | "empty" | "processing-incomplete";

const EXPLANATION =
  "These passages have no accepted finding, or are only partly highlighted, for the selected categories. This does not establish whether they are harmless or harmful. Read them with the surrounding agreement.";

function Preview({ text, marks = [] }: { text: string; marks?: [number, number][] }) {
  const parts: { t: string; m: boolean }[] = [];
  let cursor = 0;
  for (const [a, b] of [...marks].sort((x, y) => x[0] - y[0])) {
    if (a > cursor) parts.push({ t: text.slice(cursor, a), m: false });
    if (b > Math.max(a, cursor)) parts.push({ t: text.slice(Math.max(a, cursor), b), m: true });
    cursor = Math.max(cursor, b);
  }
  if (cursor < text.length) parts.push({ t: text.slice(cursor), m: false });
  return (
    <p
      style={{
        fontFamily: "var(--font-serif)",
        fontSize: 15,
        lineHeight: "24px",
        color: "var(--ink-primary)",
        whiteSpace: "pre-wrap",
        display: "-webkit-box",
        WebkitBoxOrient: "vertical",
        WebkitLineClamp: 3,
        overflow: "hidden",
      }}
    >
      {parts.map((p, i) => (p.m ? <span key={i} style={markStyle("found", false)}>{p.t}</span> : <span key={i}>{p.t}</span>))}
    </p>
  );
}

export function ManualReviewItem({ item, onGo }: { item: ManualItem; onGo?: (id: string) => void }) {
  const unavailable = item.variant === "unavailable";
  return (
    <article
      style={{
        background: unavailable ? "var(--status-unavailable-bg)" : "var(--paper-sheet)",
        border: `1px solid ${unavailable ? "var(--status-unavailable-border)" : "var(--rule-default)"}`,
        borderLeftWidth: 4,
        borderLeftColor: unavailable ? "var(--status-unavailable-fg)" : "var(--rule-strong)",
        borderRadius: "var(--radius-md)",
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 13, color: "var(--ink-secondary)" }}>
          {item.sectionPath ?? "Unnumbered text"}
        </span>
        {item.variant === "partial" && (
          <span
            style={{
              fontSize: 12,
              fontWeight: 500,
              color: "var(--ink-secondary)",
              background: "var(--paper-sunken)",
              border: "1px solid var(--rule-default)",
              borderRadius: "var(--radius-sm)",
              padding: "1px 6px",
            }}
          >
            Partly highlighted
          </span>
        )}
      </div>
      {unavailable ? (
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14, color: "var(--status-unavailable-fg)" }}>
          <BrokenLinkIcon size={16} />
          This part of the document could not be read
        </div>
      ) : (
        <Preview text={item.text} marks={item.marks} />
      )}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <OffsetTag start={item.start} end={item.end} />
        <Button variant="tertiary" size="s" onClick={() => onGo?.(item.id)}>
          Go to passage
        </Button>
      </div>
    </article>
  );
}

export default function ManualReviewList({
  state = "populated",
  items = [],
  onGo,
  onReadFull,
}: {
  state?: ManualListState;
  items?: ManualItem[];
  onGo?: (id: string) => void;
  onReadFull?: () => void;
}) {
  const [filter, setFilter] = useState("All");
  const shown = items.filter((i) =>
    filter === "No findings" ? i.variant !== "partial" : filter === "Partly highlighted" ? i.variant === "partial" : true
  );

  return (
    <section aria-labelledby="manual-review-title" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--ink-tertiary)" }}>
        <PilcrowIcon size={18} />
        <h3 id="manual-review-title" style={{ fontSize: 16, fontWeight: 600, color: "var(--ink-primary)" }}>
          Text without accepted findings
        </h3>
      </div>
      <p style={{ fontSize: 13, lineHeight: "20px", color: "var(--ink-secondary)" }}>{EXPLANATION}</p>

      {state === "processing-incomplete" ? (
        <div
          style={{
            background: "var(--status-review-bg)",
            border: "1px solid var(--status-review-border)",
            borderLeftWidth: 4,
            borderLeftColor: "var(--status-review-fg)",
            borderRadius: "var(--radius-md)",
            padding: "12px 14px",
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <p style={{ fontSize: 14, lineHeight: "20px", color: "var(--ink-primary)" }}>
            Processing incomplete. Until every category is finished, ClauseAnchor cannot list the text it did not cover. Read the full document in the meantime.
          </p>
          <div>
            <Button variant="secondary" size="s" onClick={onReadFull}>
              Read the full document
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div style={{ overflowX: "auto" }}>
            <SegmentedFilter items={["All", "No findings", "Partly highlighted"]} value={filter} onChange={setFilter} />
          </div>
          {state === "loading" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Skeleton variant="block" />
              <Skeleton variant="block" />
            </div>
          )}
          {state === "empty" || (state === "populated" && shown.length === 0) ? (
            <p
              style={{
                fontSize: 14,
                lineHeight: "20px",
                color: "var(--ink-secondary)",
                border: "1px dashed var(--rule-strong)",
                borderRadius: "var(--radius-md)",
                padding: 14,
              }}
            >
              No passages without findings for the selected categories. This is a count, not a safety verdict.
            </p>
          ) : null}
          {state === "populated" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }} role="list">
              {shown.map((i) => (
                <div role="listitem" key={i.id}>
                  <ManualReviewItem item={i} onGo={onGo} />
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
