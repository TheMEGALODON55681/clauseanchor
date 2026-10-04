import Button from "./Button";
import Spinner from "./Spinner";
import { AnchorIcon, FileIcon, InfoIcon } from "./icons";

export type DropzoneState =
  | "idle"
  | "hover"
  | "drag-over"
  | "validating"
  | "uploaded"
  | "error-type"
  | "error-size"
  | "error-scanned"
  | "error-protected";

const ERROR_MESSAGE: Record<string, string> = {
  "error-type": "This file type is not supported. Upload a PDF or DOCX.",
  "error-size": "This file is larger than 10 MB.",
  "error-scanned":
    "This PDF looks scanned. ClauseAnchor needs selectable text. Try the original digital file.",
  "error-protected": "This file is password protected. Remove the password and upload again.",
};

export default function UploadDropzone({
  state = "idle",
  fileName = "employment-agreement.pdf",
  fileMeta,
  onChoose,
  onReplace,
}: {
  state?: DropzoneState;
  fileName?: string;
  fileMeta?: string;
  onChoose?: () => void;
  onReplace?: () => void;
}) {
  const isError = state.startsWith("error");
  const dragOver = state === "drag-over";

  if (state === "validating") {
    return (
      <Shell tone="idle">
        <Spinner size={20} />
        <div style={{ marginTop: 8, fontSize: 15, color: "var(--ink-primary)" }}>Checking your file</div>
        <div style={{ fontSize: 13, color: "var(--ink-secondary)" }}>{fileName}{fileMeta ? `, ${fileMeta}` : ""}</div>
      </Shell>
    );
  }

  if (state === "uploaded") {
    return (
      <Shell tone="idle">
        <span style={{ color: "var(--anchor-600)" }}><FileIcon size={28} /></span>
        <div style={{ marginTop: 8, fontSize: 15, fontWeight: 500, color: "var(--ink-primary)", overflowWrap: "anywhere" }}>
          {fileName}
        </div>
        <div style={{ fontSize: 13, color: "var(--ink-secondary)" }}>{fileMeta ?? "1.2 MB, 8 pages"}</div>
        <div style={{ marginTop: 12 }}>
          <Button variant="tertiary" size="s" onClick={onReplace}>Replace</Button>
        </div>
      </Shell>
    );
  }

  return (
    <Shell tone={dragOver ? "drag" : isError ? "error" : "idle"}>
      <span style={{ color: isError ? "var(--status-unavailable-fg)" : "var(--anchor-600)" }}>
        {isError ? <InfoIcon size={28} /> : <AnchorIcon size={28} />}
      </span>
      <div style={{ marginTop: 10, fontSize: 18, fontWeight: 600, color: "var(--ink-primary)" }}>
        {dragOver ? "Release to upload" : isError ? "That file did not work" : "Drop your contract here"}
      </div>
      {isError ? (
        <p style={{ marginTop: 4, fontSize: 14, lineHeight: "20px", color: "var(--status-unavailable-fg)", maxWidth: 380 }}>
          {ERROR_MESSAGE[state]}
        </p>
      ) : (
        <p style={{ marginTop: 4, fontSize: 14, color: "var(--ink-secondary)" }}>
          PDF or DOCX, up to 10 MB and 100 pages
        </p>
      )}
      <div style={{ marginTop: 14 }}>
        <Button variant="secondary" onClick={onChoose}>{isError ? "Choose another file" : "Choose file"}</Button>
      </div>
    </Shell>
  );
}

function Shell({ tone, children }: { tone: "idle" | "drag" | "error"; children: React.ReactNode }) {
  const border =
    tone === "drag"
      ? "2px solid var(--anchor-600)"
      : tone === "error"
      ? "2px dashed var(--status-unavailable-border)"
      : "2px dashed var(--rule-strong)";
  const bg = tone === "drag" ? "var(--anchor-100)" : "var(--paper-sheet)";
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        border,
        background: bg,
        borderRadius: "var(--radius-lg)",
        padding: "40px 24px",
        minHeight: 220,
        justifyContent: "center",
        width: "100%",
      }}
    >
      {children}
    </div>
  );
}
