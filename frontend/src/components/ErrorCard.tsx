import Button from "./Button";
import { BrokenLinkIcon } from "./icons";

export default function ErrorCard({
  message = "Could not reach the server.",
  code = "ERR_NETWORK_TIMEOUT",
  title = "Something did not complete",
  onRetry,
}: {
  message?: string;
  code?: string;
  title?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      style={{
        background: "var(--status-unavailable-bg)",
        border: "1px solid var(--status-unavailable-border)",
        borderLeftWidth: 4,
        borderLeftColor: "var(--status-unavailable-fg)",
        borderRadius: "var(--radius-md)",
        padding: 16,
        maxWidth: 420,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--status-unavailable-fg)" }}>
        <BrokenLinkIcon size={18} />
        <span style={{ fontSize: 15, fontWeight: 600 }}>{title}</span>
      </div>
      <p style={{ fontSize: 14, lineHeight: "20px", color: "var(--ink-secondary)", marginTop: 8 }}>{message}</p>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-tertiary)", marginTop: 6 }}>{code}</div>
      <div style={{ marginTop: 12 }}>
        <Button variant="primary" size="s" onClick={onRetry}>Try again</Button>
      </div>
    </div>
  );
}
