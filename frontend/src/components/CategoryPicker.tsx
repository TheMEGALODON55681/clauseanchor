import { CATALOGUE, GROUP_ORDER } from "../api/catalogue";
import Button from "./Button";
import Disclosure from "./Disclosure";

/* The categories to check, as native checkboxes under the seven catalogue groups. Each group is a native details element with its
   own count, the first one open. Nothing is chosen until the user chooses, as with the role. The ids are the API's. */
export default function CategoryPicker({
  selected,
  onToggle,
  onSet,
}: {
  selected: string[];
  onToggle: (id: string) => void;
  onSet: (ids: string[]) => void;
}) {
  const chosen = new Set(selected);
  return (
    <fieldset style={{ border: "none", padding: 0, margin: 0, minWidth: 0 }}>
      <legend style={{ fontSize: 18, fontWeight: 600, color: "var(--ink-primary)", marginBottom: 4 }}>Categories to check</legend>
      <p style={{ fontSize: 13, color: "var(--ink-secondary)", marginBottom: 10 }}>
        More categories take longer. Choose the ones you need.
      </p>
      <div className="flex flex-wrap items-center gap-2" style={{ marginBottom: 4 }}>
        <p aria-live="polite" className="tabular-nums" style={{ fontSize: 14, color: "var(--ink-primary)", marginRight: 8 }}>
          {selected.length} of {CATALOGUE.length} selected
        </p>
        <Button variant="secondary" size="s" onClick={() => onSet(CATALOGUE.map((c) => c.id))}>
          Select all
        </Button>
        <Button variant="secondary" size="s" onClick={() => onSet([])}>
          Clear
        </Button>
      </div>
      {GROUP_ORDER.map((group, i) => {
        const rows = CATALOGUE.filter((c) => c.group === group);
        const n = rows.filter((c) => chosen.has(c.id)).length;
        return (
          <Disclosure key={group} summary={n ? `${group}, ${n} of ${rows.length} selected` : group} open={i === 0}>
            <div className="flex flex-col" style={{ marginTop: -4 }}>
              {rows.map((c) => (
                <label key={c.id} className="flex min-h-[44px] cursor-pointer items-center gap-3 py-1" style={{ color: "var(--ink-primary)", fontSize: 15, lineHeight: "22px" }}>
                  <input
                    type="checkbox"
                    checked={chosen.has(c.id)}
                    onChange={() => onToggle(c.id)}
                    style={{ width: 20, height: 20, flexShrink: 0, accentColor: "var(--anchor-600)" }}
                  />
                  <span>{c.label}</span>
                </label>
              ))}
            </div>
          </Disclosure>
        );
      })}
    </fieldset>
  );
}
