import type { ReactNode } from "react";
import { DragHandleIcon } from "./icons";

export type DrawerState = "closed" | "peek" | "open";
export type DrawerSide = "bottom" | "left";

type MobileDrawerProps = {
  side?: DrawerSide;
  state?: DrawerState;
  title?: string;
  children?: ReactNode;
  /** Render inside a positioned frame for the gallery instead of fixed to viewport. */
  framed?: boolean;
  /** Override the panel size: height for bottom, width for left. */
  size?: number | string;
  /** Header controls, such as Peek, Open and Close. */
  actions?: ReactNode;
  /** Fixed to the viewport with a backdrop that closes on click. */
  onBackdrop?: () => void;
  fixed?: boolean;
};

export default function MobileDrawer({
  side = "bottom",
  state = "open",
  title = "Non-compete",
  children,
  framed = true,
  size,
  actions,
  onBackdrop,
  fixed = false,
}: MobileDrawerProps) {
  const bottom = side === "bottom";
  const height = bottom ? (size ?? (state === "peek" ? 140 : state === "open" ? 360 : 0)) : fixed ? "100%" : 480;
  const width = bottom ? (fixed ? "100%" : 320) : state === "closed" ? 0 : (size ?? 260);

  const panel = (
    <div
      role="dialog"
      aria-label={title}
      aria-modal={fixed && !bottom ? true : undefined}
      className="reduce-motion-safe"
      style={{
        position: "absolute",
        ...(bottom
          ? { left: 0, right: 0, bottom: 0, height, borderTopLeftRadius: 14, borderTopRightRadius: 14 }
          : { left: 0, top: 0, bottom: 0, width, borderTopRightRadius: 14, borderBottomRightRadius: 14 }),
        background: "var(--paper-sheet)",
        borderTop: bottom ? "1px solid var(--rule-default)" : "none",
        borderRight: bottom ? "none" : "1px solid var(--rule-default)",
        boxShadow: "var(--elevation-3)",
        overflow: "hidden",
        transition: "height 200ms ease-in-out, width 200ms ease-in-out",
        display: state === "closed" ? "none" : fixed ? "flex" : "block",
        flexDirection: "column",
      }}
    >
      {bottom && (
        <div style={{ display: "flex", justifyContent: "center", padding: "8px 0 4px", color: "var(--ink-tertiary)" }}>
          <DragHandleIcon size={20} />
        </div>
      )}
      {fixed ? (
        <>
          {(title || actions) && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: bottom ? "0 12px 8px 16px" : "12px 12px 8px 16px" }}>
              <div style={{ flex: 1, minWidth: 0, fontSize: 16, fontWeight: 600, color: "var(--ink-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title}</div>
              {actions}
            </div>
          )}
          <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>{children}</div>
        </>
      ) : (
      <div style={{ padding: bottom ? "0 16px 16px" : "16px" }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: "var(--ink-primary)", marginBottom: 8 }}>{title}</div>
        <div style={{ fontSize: 14, color: "var(--ink-secondary)" }}>
          {children ?? (state === "peek" ? "Drag up to read the full clause." : "The full clause detail appears here.")}
        </div>
      </div>
      )}
    </div>
  );

  if (fixed) {
    if (state === "closed") return null;
    return (
      <div style={{ position: "fixed", inset: 0, zIndex: 40, pointerEvents: bottom ? "none" : "auto" }}>
        {!bottom && <div aria-hidden onClick={onBackdrop} style={{ position: "absolute", inset: 0, background: "rgba(27,31,36,0.3)" }} />}
        <div style={{ pointerEvents: "auto" }}>{panel}</div>
      </div>
    );
  }

  if (!framed) return panel;

  return (
    <div
      style={{
        position: "relative",
        width: 320,
        height: 440,
        background: "var(--paper-base)",
        border: "1px solid var(--rule-default)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
      }}
    >
      {/* Faux screen backdrop */}
      <div style={{ position: "absolute", inset: 0, background: state === "closed" ? "transparent" : "rgba(27,31,36,0.25)" }} />
      {panel}
    </div>
  );
}
