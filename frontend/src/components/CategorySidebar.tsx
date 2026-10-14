import { useState } from "react";
import type { ReactNode } from "react";
import SearchField from "./SearchField";
import SegmentedFilter from "./SegmentedFilter";
import CategoryGroupHeader from "./CategoryGroupHeader";
import CategoryRow from "./CategoryRow";
import Skeleton from "./Skeleton";
import EmptyState from "./EmptyState";
import type { StatusKind } from "./StatusChip";

export type SidebarState = "loading" | "populated" | "filtered-empty";

export type SidebarRow = { id?: string; name: string; status: StatusKind; count?: number; pending?: boolean; enterStep?: number };
export type SidebarGroup = { label: string; summary: string; rows: SidebarRow[] };

export default function CategorySidebar({
  state = "populated",
  groups,
  summary,
  selected,
  onSelect,
  query,
  onQuery,
  filter,
  onFilter,
  top,
  footer,
  fill = false,
}: {
  state?: SidebarState;
  groups: SidebarGroup[];
  summary: string;
  selected?: string | null;
  onSelect?: (row: SidebarRow) => void;
  query?: string;
  onQuery?: (v: string) => void;
  filter?: string;
  onFilter?: (v: string) => void;
  /** Pinned above the filters, such as the scope panel. */
  top?: ReactNode;
  /** Below the category groups, such as the manual review entry. */
  footer?: ReactNode;
  fill?: boolean;
}) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  return (
    <aside
      style={{
        width: fill ? "100%" : 280,
        maxWidth: "100%",
        background: "var(--paper-sunken)",
        borderRight: "1px solid var(--rule-default)",
        display: "flex",
        flexDirection: "column",
        height: fill ? "100%" : 560,
      }}
    >
      {top && <div style={{ padding: "12px 12px 0" }}>{top}</div>}
      <div style={{ padding: "14px 12px 10px", display: "flex", flexDirection: "column", gap: 10 }}>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--ink-primary)" }}>Clauses reviewed</h2>
          <p style={{ fontSize: 12, color: "var(--ink-tertiary)", marginTop: 2, fontVariantNumeric: "tabular-nums" }} aria-live="polite">
            {summary}
          </p>
        </div>
        <SearchField state={state === "filtered-empty" && query === undefined ? "no-results" : "empty"} value={query} onChange={onQuery} />
        <div style={{ overflowX: "auto", maxWidth: "100%" }}>
          <SegmentedFilter label="Filter categories" value={filter} onChange={onFilter} />
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", paddingBottom: 12 }}>
        {state === "loading" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14, padding: "8px 12px" }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} variant="line" />
            ))}
          </div>
        )}

        {state === "filtered-empty" && (
          <div style={{ padding: 12 }}>
            <EmptyState
              variant="no-findings"
              heading={query !== undefined ? "No categories match this filter" : undefined}
              line={query !== undefined ? "The document text is unchanged. Reset the filter to see every category." : undefined}
            />
          </div>
        )}

        {state === "populated" &&
          groups.map((g) => (
            <div key={g.label} style={{ marginBottom: 4 }}>
              <CategoryGroupHeader
                label={g.label}
                summary={g.summary}
                collapsed={!!collapsed[g.label]}
                onToggle={() => setCollapsed((c) => ({ ...c, [g.label]: !c[g.label] }))}
              />
              {!collapsed[g.label] &&
                g.rows.map((r) =>
                  r.pending ? (
                    <div key={r.id ?? r.name} style={{ display: "flex", alignItems: "center", gap: 10, minHeight: 44, padding: "8px 16px" }}>
                      <span style={{ flex: 1, minWidth: 0, fontSize: 14, color: "var(--ink-tertiary)", overflowWrap: "anywhere" }}>{r.name}</span>
                      <span style={{ width: 72, overflow: "hidden" }} aria-label="Still checking">
                        <Skeleton variant="line" />
                      </span>
                    </div>
                  ) : (
                    <CategoryRow
                      key={r.id ?? r.name}
                      name={r.name}
                      status={r.status}
                      count={r.count}
                      enterStep={r.enterStep}
                      state={selected === (r.id ?? r.name) ? "selected" : undefined}
                      onClick={() => onSelect?.(r)}
                    />
                  )
                )}
            </div>
          ))}
        {footer}
      </div>
    </aside>
  );
}
