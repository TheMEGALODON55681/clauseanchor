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
  /** The open size: height for bottom, width for left. */
  size?: number | string;
  /** Header controls, such as Peek, Open and Close. */
  actions?: ReactNode;
  /** Fixed to the viewport with a backdrop that closes on click. */
  onBackdrop?: () => void;
  fixed?: boolean;
};

/* How much of a peeking bottom sheet shows. */
const PEEK_PX = 168;

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
  const closed = state === "closed";

  /* The fixed drawer stays mounted and slides on transform only, so it can animate out.
     The gallery frame shows static states. */
  const slide = bottom
    ? { open: "translateY(0)", peek: `translateY(calc(100% - ${PEEK_PX}px))`, closed: "translateY(100%)" }
    : { open: "translateX(0)", peek: "translateX(0)", closed: "translateX(-100%)" };
  const fixedStyle = {
    ...(bottom
      ? { left: 0, right: 0, bottom: 0, height: size ?? "78dvh", borderTopLeftRadius: 14, borderTopRightRadius: 14 }
      : { left: 0, top: 0, bottom: 0, width: size ?? 260, borderTopRightRadius: 14, borderBottomRightRadius: 14 }),
    transform: slide[state],
    visibility: closed ? ("hidden" as const) : ("visible" as const),
    transition: `transform var(--dur-panel) ${closed ? "var(--ease-exit)" : "var(--ease-out)"}, visibility 0s linear ${closed ? "var(--dur-panel)" : "0s"}`,
    display: "flex",
    flexDirection: "column" as const,
    animation: bottom ? "ca-drawer-up var(--dur-panel) var(--ease-out)" : undefined,
  };
  const framedHeight = bottom ? (size ?? (state === "peek" ? 140 : state === "open" ? 360 : 0)) : 480;
  const framedWidth = bottom ? 320 : closed ? 0 : (size ?? 260);
  const framedStyle = {
    ...(bottom
      ? { left: 0, right: 0, bottom: 0, height: framedHeight, borderTopLeftRadius: 14, borderTopRightRadius: 14 }
      : { left: 0, top: 0, bottom: 0, width: framedWidth, borderTopRightRadius: 14, borderBottomRightRadius: 14 }),
    display: closed ? "none" : "block",
  };

  const panel = (
    <div
      role="dialog"
      aria-label={title}
      aria-modal={fixed && !bottom ? true : undefined}
      aria-hidden={fixed && closed ? true : undefined}
      style={{
        position: "absolute",
        ...(fixed ? fixedStyle : framedStyle),
        background: "var(--paper-sheet)",
        borderTop: bottom ? "1px solid var(--rule-default)" : "none",
        borderRight: bottom ? "none" : "1px solid var(--rule-default)",
        boxShadow: "var(--elevation-3)",
        overflow: "hidden",
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
    return (
      <div style={{ position: "fixed", inset: 0, zIndex: 40, pointerEvents: "none" }}>
        {!bottom && (
          <div
            aria-hidden
            onClick={onBackdrop}
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(27,31,36,0.3)",
              opacity: closed ? 0 : 1,
              pointerEvents: closed ? "none" : "auto",
              transition: `opacity var(--dur-panel) ${closed ? "var(--ease-exit)" : "var(--ease-out)"}`,
            }}
          />
        )}
        <div style={{ pointerEvents: closed ? "none" : "auto" }}>{panel}</div>
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
      <div style={{ position: "absolute", inset: 0, background: closed ? "transparent" : "rgba(27,31,36,0.25)" }} />
      {panel}
    </div>
  );
}
