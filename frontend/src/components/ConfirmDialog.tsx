import Button from "./Button";

type ConfirmDialogProps = {
  title?: string;
  body?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Static render for the gallery, no overlay. */
  inline?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
};

function Panel({ title, body, confirmLabel, cancelLabel, onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <div
      role="alertdialog"
      aria-labelledby="confirm-title"
      style={{
        width: 400,
        maxWidth: "100%",
        background: "var(--paper-base)",
        border: "1px solid var(--rule-default)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--elevation-3)",
        padding: 20,
      }}
    >
      <h3 id="confirm-title" style={{ fontSize: 18, fontWeight: 600, color: "var(--ink-primary)" }}>
        {title}
      </h3>
      <p style={{ fontSize: 14, lineHeight: "20px", color: "var(--ink-secondary)", marginTop: 8 }}>{body}</p>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
        <Button variant="secondary" onClick={onCancel}>{cancelLabel}</Button>
        <Button variant="destructive" onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </div>
  );
}

export default function ConfirmDialog({
  title = "Delete document?",
  body = "This removes your contract and results now.",
  confirmLabel = "Delete document",
  cancelLabel = "Keep it",
  inline = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const panel = (
    <Panel
      title={title}
      body={body}
      confirmLabel={confirmLabel}
      cancelLabel={cancelLabel}
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
  if (inline) return panel;
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(27,31,36,0.35)",
        padding: 16,
      }}
    >
      {panel}
    </div>
  );
}
