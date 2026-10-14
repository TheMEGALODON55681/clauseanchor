import Button from "./Button";
import StageProgress from "./StageProgress";
import DropdownMenu from "./DropdownMenu";
import type { ReactNode } from "react";
import { FileIcon, TrashIcon, DownloadIcon } from "./icons";

export type ToolbarVariant = "analyzing" | "complete" | "partial" | "sample-mode";

/* A long name truncates at the end of the base and keeps its extension. */
function FileName({ name }: { name: string }) {
  const dot = name.lastIndexOf(".");
  const [base, ext] = dot > 0 ? [name.slice(0, dot), name.slice(dot)] : [name, ""];
  return (
    <span title={name} style={{ display: "flex", minWidth: 0, maxWidth: 320, fontSize: 14, fontWeight: 500, color: "var(--ink-primary)" }}>
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{base}</span>
      <span style={{ whiteSpace: "nowrap" }}>{ext}</span>
    </span>
  );
}

export default function ReaderToolbar({
  variant = "complete",
  filename = "employment-agreement.pdf",
  meta = "8 pages",
  progress,
  partialNote = "Some categories could not be finished. They are listed as Unavailable.",
  menu,
  leading,
  showDelete = true,
  onDownload,
  onDelete,
}: {
  variant?: ToolbarVariant;
  filename?: string;
  meta?: string;
  /** Live progress node shown while analyzing. */
  progress?: ReactNode;
  partialNote?: string;
  /** Overflow menu override. */
  menu?: ReactNode;
  /** Slot before the filename, for the drawer toggle. */
  leading?: ReactNode;
  /** False leaves Delete to the menu, which is where it sits on a phone. */
  showDelete?: boolean;
  onDownload?: () => void;
  onDelete?: () => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        flexWrap: "wrap",
        padding: "10px 16px",
        background: "var(--paper-sheet)",
        borderBottom: "1px solid var(--rule-default)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0, flex: "0 1 auto" }}>
        {leading}
        <span style={{ color: "var(--ink-tertiary)", display: "inline-flex" }}><FileIcon size={18} /></span>
        <FileName name={filename} />
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)", whiteSpace: "nowrap" }}>{meta}</span>
        {variant === "sample-mode" && (
          <span
            style={{
              fontSize: 12,
              fontWeight: 500,
              color: "var(--status-review-fg)",
              background: "var(--status-review-bg)",
              border: "1px solid var(--status-review-border)",
              borderRadius: "var(--radius-sm)",
              padding: "2px 8px",
            }}
          >
            Sample
          </span>
        )}
      </div>

      {variant === "analyzing" && progress !== null && (
        <div style={{ flex: 1, minWidth: 200 }}>
          {progress ?? <StageProgress compact />}
        </div>
      )}

      {variant === "partial" && (
        <span style={{ flex: 1, minWidth: 200, fontSize: 13, color: "var(--status-review-fg)" }}>
          {partialNote}
        </span>
      )}

      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
        <Button variant="primary" size="s" icon="leading" iconNode={<DownloadIcon size={16} />} onClick={onDownload}>
          Download report
        </Button>
        {menu ?? <DropdownMenu />}
        {showDelete && (
          <Button variant="destructive" size="s" icon="leading" iconNode={<TrashIcon size={16} />} onClick={onDelete}>
            Delete document
          </Button>
        )}
      </div>
    </div>
  );
}
