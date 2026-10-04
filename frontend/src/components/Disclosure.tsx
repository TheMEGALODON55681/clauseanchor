import type { ReactNode } from "react";
import { ChevronDownIcon } from "./icons";

/* A native details element: the browser supplies the keyboard behaviour and
   the state. The summary row is 44 px high and the ring comes from index.css. */
export default function Disclosure({ summary, open, children }: { summary: string; open?: boolean; children: ReactNode }) {
  return (
    <details className="disclosure" open={open}>
      <summary>
        <span style={{ fontSize: 16, fontWeight: 500 }}>{summary}</span>
        <ChevronDownIcon size={18} />
      </summary>
      <div style={{ padding: "12px 0 16px", fontSize: 15, lineHeight: "24px", color: "var(--ink-secondary)" }}>{children}</div>
    </details>
  );
}
