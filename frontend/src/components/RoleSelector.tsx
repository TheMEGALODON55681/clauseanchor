import { useId, useState } from "react";
import RadioCard from "./RadioCard";
import type { Role } from "../api/types";
import { PersonWithDocIcon, PilcrowIcon, BracketPairIcon, IndexCardIcon, AnchorIcon, SectionIcon, NeutralIcon } from "./icons";

/** The one table of roles, keyed by the API's `Role`. The reader's menu, the summary and the landing page read it too. */
export const ROLES: { role: Role; title: string; desc: string; icon: React.ReactNode }[] = [
  { role: "buyer_customer", title: "Buyer or customer", desc: "You are receiving goods or services.", icon: <AnchorIcon size={18} /> },
  { role: "supplier_vendor", title: "Supplier or vendor", desc: "You are providing goods or services.", icon: <IndexCardIcon size={18} /> },
  { role: "employer", title: "Employer", desc: "You are engaging a person to work.", icon: <SectionIcon size={18} /> },
  { role: "employee", title: "Employee", desc: "You are the person being engaged.", icon: <PersonWithDocIcon size={18} /> },
  { role: "licensor", title: "Licensor", desc: "You are granting rights to use something.", icon: <BracketPairIcon size={18} /> },
  { role: "licensee", title: "Licensee", desc: "You are receiving rights to use something.", icon: <PilcrowIcon size={18} /> },
  { role: "other", title: "Other", desc: "Some other role in this contract.", icon: <NeutralIcon size={18} /> },
];

/** Controlled when `value` is given (null means no role yet). Without it the gallery example keeps its own choice. */
export default function RoleSelector({ value, onChange, hideLegend = false }: { value?: Role | null; onChange?: (v: Role) => void; hideLegend?: boolean }) {
  const group = useId();
  const [internal, setInternal] = useState<Role | null>("employee");
  const selected = value !== undefined ? value : internal;
  const choose = (k: Role) => {
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
          <RadioCard key={r.role} name={group} value={r.role} title={r.title} description={r.desc} icon={r.icon} checked={selected === r.role} onSelect={() => choose(r.role)} />
        ))}
      </div>
    </fieldset>
  );
}
