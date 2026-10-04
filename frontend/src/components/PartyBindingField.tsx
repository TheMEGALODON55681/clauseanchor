import { useState } from "react";
import OffsetTag from "./OffsetTag";
import Skeleton from "./Skeleton";
import Button from "./Button";
import { CheckIcon } from "./icons";

export type PartyBindingState = "loading" | "choices" | "selected" | "unresolved";

const PARTIES = [
  { name: "Sample Traders Pvt. Ltd.", quote: "“Sample Traders Pvt. Ltd., a company incorporated under the Companies Act”", start: 120, end: 210 },
  { name: "Example Industries Ltd.", quote: "“Example Industries Ltd., having its registered office at New Delhi”", start: 240, end: 322 },
];

export type PartyChoice = { name: string; quote: string; start: number; end: number };

export default function PartyBindingField({
  state = "choices",
  parties = PARTIES,
  value,
  onChange,
  onNone,
}: {
  state?: PartyBindingState;
  parties?: PartyChoice[];
  value?: string | null;
  onChange?: (name: string) => void;
  onNone?: () => void;
}) {
  const [internal, setInternal] = useState<string | null>(state === "selected" ? PARTIES[0].name : null);
  const selected = value !== undefined ? value : internal;
  const setSelected = (n: string) => {
    setInternal(n);
    onChange?.(n);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ fontSize: 15, fontWeight: 500, color: "var(--ink-primary)" }}>
        Which party are you?
      </div>

      {state === "loading" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Skeleton variant="line" />
          <Skeleton variant="line" />
        </div>
      )}

      {state === "unresolved" && (
        <div
          style={{
            background: "var(--paper-sunken)",
            border: "1px solid var(--rule-default)",
            borderLeftWidth: 4,
            borderLeftColor: "var(--rule-strong)",
            borderRadius: "var(--radius-md)",
            padding: "12px 14px",
            fontSize: 14,
            color: "var(--ink-secondary)",
          }}
        >
          We will mark party-specific clauses as Party unclear.
        </div>
      )}

      {(state === "choices" || state === "selected") && (
        <>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {parties.map((p) => {
              const isSel = (state === "selected" ? selected : selected) === p.name;
              return (
                <button
                  key={p.name}
                  type="button"
                  aria-pressed={isSel}
                  onClick={() => setSelected(p.name)}
                  className="text-left focus:outline-none focus-visible:outline-none"
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                    minHeight: 44,
                    background: "var(--paper-sheet)",
                    border: `${isSel ? 2 : 1}px solid ${isSel ? "var(--anchor-600)" : "var(--rule-strong)"}`,
                    borderRadius: "var(--radius-md)",
                    padding: isSel ? "9px 11px" : "10px 12px",
                    cursor: "pointer",
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.outline = "2px solid var(--focus-ring)";
                    e.currentTarget.style.outlineOffset = "2px";
                  }}
                  onBlur={(e) => (e.currentTarget.style.outline = "none")}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 15, fontWeight: 500, color: "var(--ink-primary)" }}>{p.name}</span>
                    {isSel && <span style={{ color: "var(--anchor-600)" }}><CheckIcon size={16} /></span>}
                  </span>
                  <span style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", fontSize: 14, color: "var(--ink-secondary)" }}>
                    {p.quote}
                  </span>
                  <OffsetTag start={p.start} end={p.end} />
                </button>
              );
            })}
          </div>
          <Button variant="tertiary" size="s" onClick={onNone}>None of these</Button>
        </>
      )}
    </div>
  );
}
