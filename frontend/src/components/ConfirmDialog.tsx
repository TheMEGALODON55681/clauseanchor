import { useEffect, useRef } from "react";
import Button from "./Button";
import { trapTab } from "../lib/focusTrap";

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

function Panel({ title, body, confirmLabel, cancelLabel, onConfirm, onCancel, modal }: ConfirmDialogProps & { modal: boolean }) {
  return (
    <div
      role="alertdialog"
      className="ca-dialog"
      aria-modal={modal || undefined}
      aria-labelledby="confirm-title"
      aria-describedby="confirm-body"
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
      <h2 id="confirm-title" style={{ fontSize: 18, fontWeight: 600, color: "var(--ink-primary)" }}>
        {title}
      </h2>
      <p id="confirm-body" style={{ fontSize: 14, lineHeight: "20px", color: "var(--ink-secondary)", marginTop: 8 }}>{body}</p>
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
  const overlay = useRef<HTMLDivElement>(null);

  /* A modal takes focus when it opens, on the safe choice (the first button, Cancel), and gives it
     back to what had it when it closes. A confirmed delete leaves the page, so the opener is gone and
     nothing is focused. */
  useEffect(() => {
    if (inline) return;
    const back = document.activeElement;
    overlay.current?.querySelector<HTMLElement>("button")?.focus();
    return () => {
      if (back instanceof HTMLElement && back.isConnected) back.focus();
    };
  }, [inline]);

  const panel = (
    <Panel
      title={title}
      body={body}
      confirmLabel={confirmLabel}
      cancelLabel={cancelLabel}
      onConfirm={onConfirm}
      onCancel={onCancel}
      modal={!inline}
    />
  );
  if (inline) return panel;
  return (
    <div
      ref={overlay}
      // Focusable so a click on the backdrop keeps focus, and the keys, inside the dialog.
      tabIndex={-1}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          onCancel?.();
        } else trapTab(e, overlay.current);
      }}
      className="ca-enter"
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
