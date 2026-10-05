import { ROLES } from "../../components/RoleSelector";
import type { FlowState } from "../../lib/startFlow";
import type { PartyChoice } from "../../components/PartyBindingField";

/* What the user has decided so far. The rail beside the form shows the list from 1280 px,
   and below that the page shows one line above the buttons. A value that is not decided
   yet is left out of the line and named in the list. */

type Row = { label: string; value: string | null; note?: string };

function rowsOf(flow: FlowState, fileMeta: string, parties: PartyChoice[]): Row[] {
  const file = flow.upload.status === "uploaded" ? flow.upload.fileName : null;
  const role = ROLES.find((r) => r.key === flow.role)?.title ?? null;
  const party = flow.partyNone ? "None of these" : (parties.find((p) => p.id === flow.party)?.name ?? null);
  return [
    { label: "File", value: file, note: file ? fileMeta : undefined },
    { label: "Role", value: role },
    { label: "Party", value: party },
    { label: "Scope", value: flow.india ? "Indian law review on" : "Indian law review off" },
  ];
}

export default function Summary({ flow, fileMeta, parties, variant }: { flow: FlowState; fileMeta: string; parties: PartyChoice[]; variant: "list" | "line" }) {
  const rows = rowsOf(flow, fileMeta, parties);
  if (variant === "line") {
    const chosen = rows.slice(0, 3).map((r) => r.value).filter(Boolean);
    return chosen.length ? <p className="text-[13px] leading-[20px]" style={{ color: "var(--ink-secondary)", overflowWrap: "anywhere" }}>{chosen.join(" · ")}</p> : null;
  }
  return (
    <dl className="flex flex-col gap-4 text-[14px] leading-[20px]">
      {rows.map((r) => (
        <div key={r.label}>
          <dt className="t-overline" style={{ color: "var(--ink-tertiary)" }}>{r.label}</dt>
          <dd className="mt-1" style={{ color: r.value ? "var(--ink-primary)" : "var(--ink-tertiary)", overflowWrap: "anywhere" }}>
            {r.value ?? "Not chosen yet"}
            {r.note && <span className="block text-[13px] tabular-nums" style={{ color: "var(--ink-secondary)" }}>{r.note}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}
