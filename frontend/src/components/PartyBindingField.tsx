import { useId, useState } from "react";
import OffsetTag from "./OffsetTag";
import RadioCard from "./RadioCard";
import Skeleton from "./Skeleton";

export type PartyBindingState = "loading" | "choices" | "selected" | "unresolved";

export type PartyChoice = { id: string; name: string; quote: string; start: number; end: number };

const PARTIES: PartyChoice[] = [
  { id: "p1", name: "Sample Traders Pvt. Ltd.", quote: "“Sample Traders Pvt. Ltd., a company incorporated under the Companies Act”", start: 120, end: 210 },
  { id: "p2", name: "Example Industries Ltd.", quote: "“Example Industries Ltd., having its registered office at New Delhi”", start: 240, end: 322 },
];

const UNCLEAR = "We will mark party-specific clauses as Party unclear.";

/* The party the user is, as a radio group with "None of these" as its last option. Nothing
   is chosen until the user chooses: a wrong party flips Burden and Benefit on every finding.
   The party that fits the role best is listed first and carries the tag "Suggested". */
export default function PartyBindingField({
  state = "choices",
  parties = PARTIES,
  value,
  none = false,
  suggested = null,
  onChange,
  onNone,
}: {
  state?: PartyBindingState;
  parties?: PartyChoice[];
  /** The id of the chosen party. Controlled when given (null means no party yet). */
  value?: string | null;
  none?: boolean;
  /** The id of the party to tag "Suggested". */
  suggested?: string | null;
  onChange?: (id: string) => void;
  onNone?: () => void;
}) {
  const label = useId();
  const [internal, setInternal] = useState<string | null>(state === "selected" ? PARTIES[0].id : null);
  const selected = value !== undefined ? value : internal;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div id={label} style={{ fontSize: 15, fontWeight: 500, color: "var(--ink-primary)" }}>
        Which party are you?
      </div>

      {state === "loading" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <p role="status" style={{ fontSize: 14, color: "var(--ink-secondary)" }}>Reading your document.</p>
          <Skeleton variant="line" />
          <Skeleton variant="line" />
        </div>
      )}

      {state === "unresolved" && (
        <div
          style={{
            background: "var(--paper-sunken)",
            border: "1px solid var(--rule-default)",
            borderRadius: "var(--radius-md)",
            padding: "12px 14px",
            fontSize: 14,
            color: "var(--ink-secondary)",
          }}
        >
          {UNCLEAR}
        </div>
      )}

      {(state === "choices" || state === "selected") && (
        <div role="radiogroup" aria-labelledby={label} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {parties.map((p) => (
            <RadioCard
              key={p.id}
              name={label}
              value={p.id}
              title={p.name}
              tag={p.id === suggested ? "Suggested" : undefined}
              checked={!none && selected === p.id}
              onSelect={() => {
                setInternal(p.id);
                onChange?.(p.id);
              }}
            >
              <span style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", fontSize: 14, color: "var(--ink-secondary)" }}>{p.quote}</span>
              <OffsetTag start={p.start} end={p.end} />
            </RadioCard>
          ))}
          <RadioCard name={label} value="none" title="None of these" checked={none} onSelect={() => onNone?.()} />
          {none && <p style={{ fontSize: 13, color: "var(--ink-secondary)" }}>{UNCLEAR}</p>}
        </div>
      )}
    </div>
  );
}
