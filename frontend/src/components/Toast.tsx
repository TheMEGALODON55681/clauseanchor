import { CheckIcon, InfoIcon, BrokenLinkIcon, CloseIcon } from "./icons";

export type ToastVariant = "success" | "info" | "error";

const CONFIG: Record<ToastVariant, { icon: React.ReactNode; tone: string; message: string }> = {
  success: { icon: <CheckIcon size={18} />, tone: "var(--anchor-600)", message: "Report downloaded" },
  info: { icon: <InfoIcon size={18} />, tone: "var(--ink-tertiary)", message: "Your role was updated" },
  error: { icon: <BrokenLinkIcon size={18} />, tone: "var(--status-unavailable-fg)", message: "Could not reach the server. Try again." },
};

export default function Toast({ variant = "success", message, onDismiss }: { variant?: ToastVariant; message?: string; onDismiss?: () => void }) {
  const c = CONFIG[variant];
  return (
    <div
      role="status"
      className="ca-toast"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        minWidth: 260,
        maxWidth: 380,
        background: "var(--paper-sheet)",
        border: "1px solid var(--rule-default)",
        borderRadius: "var(--radius-md)",
        boxShadow: "var(--elevation-2)",
        padding: "10px 12px",
      }}
    >
      <span style={{ color: c.tone, display: "inline-flex" }}>{c.icon}</span>
      <span style={{ flex: 1, fontSize: 14, color: "var(--ink-primary)" }}>{message ?? c.message}</span>
      <button
        type="button"
        className="hit"
        aria-label="Dismiss"
        onClick={onDismiss}
        style={{ display: "inline-flex", color: "var(--ink-tertiary)", background: "none", border: "none", cursor: "pointer" }}
      >
        <CloseIcon size={16} />
      </button>
    </div>
  );
}
