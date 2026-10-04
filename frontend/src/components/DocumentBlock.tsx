import type { ReactNode } from "react";

export type BlockVariant =
  | "heading"
  | "clause"
  | "sub-clause"
  | "definition"
  | "table"
  | "page-break"
  | "header-footer";

type DocumentBlockProps = {
  variant: BlockVariant;
  number?: string;
  children?: ReactNode;
};

const bodyStyle: React.CSSProperties = {
  fontFamily: "var(--font-serif)",
  fontSize: 17,
  lineHeight: "30px",
  color: "var(--ink-primary)",
  maxWidth: "74ch",
};

/* Clause number hangs in the left margin; body reads as paper. */
function Hang({ number, children, indent = 0 }: { number?: string; children: ReactNode; indent?: number }) {
  return (
    <div style={{ display: "flex", gap: 12, paddingLeft: indent }}>
      <span
        style={{
          fontFamily: "var(--font-serif)",
          fontWeight: 600,
          fontSize: 17,
          lineHeight: "30px",
          fontVariantNumeric: "tabular-nums",
          minWidth: 40,
          textAlign: "right",
          color: "var(--ink-secondary)",
          flexShrink: 0,
        }}
      >
        {number}
      </span>
      <p style={bodyStyle}>{children}</p>
    </div>
  );
}

export default function DocumentBlock({ variant, number, children }: DocumentBlockProps) {
  switch (variant) {
    case "heading":
      return (
        <h3 style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 22, lineHeight: "30px", color: "var(--ink-primary)", marginBottom: 4 }}>
          {number ? `${number} ` : ""}
          {children ?? "Restrictive Covenants"}
        </h3>
      );
    case "clause":
      return <Hang number={number ?? "11.3"}>{children ?? "During the Term and for a period of two (2) years thereafter, the Employee shall not engage in any business that competes with the Company within India."}</Hang>;
    case "sub-clause":
      return <Hang number={number ?? "(b)"} indent={40}>{children ?? "solicit or attempt to solicit any employee of the Company to leave their employment."}</Hang>;
    case "definition":
      return (
        <p style={bodyStyle}>
          <strong style={{ fontWeight: 600 }}>"Confidential Information"</strong>{" "}
          {children ?? "means any information disclosed by one party to the other that is marked confidential or would reasonably be understood to be confidential."}
        </p>
      );
    case "table":
      return (
        <table style={{ borderCollapse: "collapse", fontFamily: "var(--font-serif)", fontSize: 15, color: "var(--ink-primary)", width: "100%", maxWidth: 520 }}>
          <tbody>
            {[
              ["Renewal term", "12 months"],
              ["Notice period", "60 days"],
              ["Governing law", "India"],
            ].map((r) => (
              <tr key={r[0]}>
                <td style={{ border: "1px solid var(--rule-default)", padding: "6px 10px", fontWeight: 600 }}>{r[0]}</td>
                <td style={{ border: "1px solid var(--rule-default)", padding: "6px 10px" }}>{r[1]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    case "page-break":
      return (
        <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "8px 0" }}>
          <span style={{ flex: 1, height: 1, background: "var(--rule-default)" }} />
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)" }}>Page 4</span>
          <span style={{ flex: 1, height: 1, background: "var(--rule-default)" }} />
        </div>
      );
    case "header-footer":
      return (
        <div style={{ fontFamily: "var(--font-serif)", fontSize: 13, fontStyle: "italic", color: "var(--ink-tertiary)" }}>
          {children ?? "Sample Traders Pvt. Ltd. and Example Industries Ltd., Confidential"}
          <span style={{ fontFamily: "var(--font-mono)", fontStyle: "normal", fontSize: 12, marginLeft: 8 }}>Repeated page header</span>
        </div>
      );
  }
}
