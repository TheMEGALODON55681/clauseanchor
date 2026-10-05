import { useState } from "react";
import RadioCard from "./RadioCard";
import { PersonWithDocIcon, PilcrowIcon, BracketPairIcon, IndexCardIcon, AnchorIcon, SectionIcon, NeutralIcon } from "./icons";

export const ROLES: { key: string; title: string; desc: string; icon: React.ReactNode }[] = [
  { key: "buyer", title: "Buyer or customer", desc: "You are receiving goods or services.", icon: <AnchorIcon size={18} /> },
  { key: "supplier", title: "Supplier or vendor", desc: "You are providing goods or services.", icon: <IndexCardIcon size={18} /> },
  { key: "employer", title: "Employer", desc: "You are engaging a person to work.", icon: <SectionIcon size={18} /> },
  { key: "employee", title: "Employee", desc: "You are the person being engaged.", icon: <PersonWithDocIcon size={18} /> },
  { key: "licensor", title: "Licensor", desc: "You are granting rights to use something.", icon: <BracketPairIcon size={18} /> },
  { key: "licensee", title: "Licensee", desc: "You are receiving rights to use something.", icon: <PilcrowIcon size={18} /> },
  { key: "other", title: "Other", desc: "Some other role in this contract.", icon: <NeutralIcon size={18} /> },
];

export type RoleKey = "buyer" | "supplier" | "employer" | "employee" | "licensor" | "licensee" | "other";

export default function RoleSelector({ value, onChange }: { value?: RoleKey; onChange?: (v: RoleKey) => void }) {
  const [internal, setInternal] = useState<string>("employee");
  const selected = value ?? internal;
  const setSelected = (k: string) => {
    setInternal(k);
    onChange?.(k as RoleKey);
  };
  return (
    <fieldset style={{ border: "none", padding: 0, margin: 0 }}>
      <legend style={{ fontSize: 18, fontWeight: 600, color: "var(--ink-primary)", marginBottom: 4 }}>
        Who are you in this contract?
      </legend>
      <p style={{ fontSize: 13, color: "var(--ink-secondary)", marginBottom: 14 }}>
        This decides whether a clause reads as a burden or a benefit for you.
      </p>
      <div
        role="radiogroup"
        aria-label="Your role in this contract"
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}
      >
        {ROLES.map((r) => (
          <RadioCard
            key={r.key}
            title={r.title}
            description={r.desc}
            icon={r.icon}
            state={selected === r.key ? "selected" : "unselected"}
            onSelect={() => setSelected(r.key)}
          />
        ))}
      </div>
    </fieldset>
  );
}
