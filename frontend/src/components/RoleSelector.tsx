import { useId, useState } from "react";
import RadioCard from "./RadioCard";
import type { RoleKey } from "../lib/startFlow";
import { PersonWithDocIcon, PilcrowIcon, BracketPairIcon, IndexCardIcon, AnchorIcon, SectionIcon, NeutralIcon } from "./icons";

export const ROLES: { key: RoleKey; title: string; desc: string; icon: React.ReactNode }[] = [
  { key: "buyer", title: "Buyer or customer", desc: "You are receiving goods or services.", icon: <AnchorIcon size={18} /> },
  { key: "supplier", title: "Supplier or vendor", desc: "You are providing goods or services.", icon: <IndexCardIcon size={18} /> },
  { key: "employer", title: "Employer", desc: "You are engaging a person to work.", icon: <SectionIcon size={18} /> },
  { key: "employee", title: "Employee", desc: "You are the person being engaged.", icon: <PersonWithDocIcon size={18} /> },
  { key: "licensor", title: "Licensor", desc: "You are granting rights to use something.", icon: <BracketPairIcon size={18} /> },
  { key: "licensee", title: "Licensee", desc: "You are receiving rights to use something.", icon: <PilcrowIcon size={18} /> },
  { key: "other", title: "Other", desc: "Some other role in this contract.", icon: <NeutralIcon size={18} /> },
];

/** Controlled when `value` is given (null means no role yet). Without it the gallery example keeps its own choice. */
export default function RoleSelector({ value, onChange, hideLegend = false }: { value?: RoleKey | null; onChange?: (v: RoleKey) => void; hideLegend?: boolean }) {
  const group = useId();
  const [internal, setInternal] = useState<RoleKey | null>("employee");
  const selected = value !== undefined ? value : internal;
  const choose = (k: RoleKey) => {
    setInternal(k);
    onChange?.(k);
  };
  return (
    <fieldset style={{ border: "none", padding: 0, margin: 0 }}>
      <legend className={hideLegend ? "sr-only" : undefined} style={{ fontSize: 18, fontWeight: 600, color: "var(--ink-primary)", marginBottom: 4 }}>
        Who are you in this contract?
      </legend>
      <p style={{ fontSize: 13, color: "var(--ink-secondary)", marginBottom: 14 }}>
        This decides whether a clause reads as a burden or a benefit for you.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
        {ROLES.map((r) => (
          <RadioCard key={r.key} name={group} value={r.key} title={r.title} description={r.desc} icon={r.icon} checked={selected === r.key} onSelect={() => choose(r.key)} />
        ))}
      </div>
    </fieldset>
  );
}
