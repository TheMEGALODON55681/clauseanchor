import { Fragment } from "react";

/* Breadcrumb using document numbers, e.g. "Clause 11 > 11.3 > (b)". */
export default function SectionPath({ parts = ["Clause 11", "11.3", "(b)"] }: { parts?: string[] }) {
  return (
    <nav aria-label="Section path" style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 6 }}>
      {parts.map((p, i) => (
        <Fragment key={p}>
          {i > 0 && <span aria-hidden style={{ color: "var(--ink-tertiary)", fontSize: 13 }}>&rsaquo;</span>}
          <span
            style={{
              fontFamily: "var(--font-serif)",
              fontWeight: 600,
              fontSize: 14,
              fontVariantNumeric: "tabular-nums",
              color: i === parts.length - 1 ? "var(--ink-primary)" : "var(--ink-secondary)",
            }}
          >
            {p}
          </span>
        </Fragment>
      ))}
    </nav>
  );
}
