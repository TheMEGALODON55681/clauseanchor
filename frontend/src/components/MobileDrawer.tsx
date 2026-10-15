import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { DragHandleIcon } from "./icons";
import { trapTab } from "../lib/focusTrap";

export type DrawerState = "closed" | "peek" | "open";
export type DrawerSide = "bottom" | "left";

type MobileDrawerProps = {
  side?: DrawerSide;
  state?: DrawerState;
  title: string;
  children?: ReactNode;
  /** Render inside a positioned frame for the gallery instead of fixed to viewport. */
  framed?: boolean;
  /** The open size: height for bottom, width for left. */
  size?: number | string;
  /** Header controls, such as Peek, Open and Close. */
  actions?: ReactNode;
  /** Fixed to the viewport. A left drawer is modal: it has a backdrop that closes on click, takes focus on open and gives it back on close. */
  onBackdrop?: () => void;
  fixed?: boolean;
};

/* How much of a peeking bottom sheet shows. The Reader pads its scroll area by it. */
export const PEEK_PX = 168;

export default function MobileDrawer({
  side = "bottom",
  state = "open",
  title,
  children,
  framed = true,
  size,
  actions,
  onBackdrop,
  fixed = false,
}: MobileDrawerProps) {
  const bottom = side === "bottom";
  const closed = state === "closed";
  const modal = fixed && !bottom;
  const dialog = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLElement | null>(null);

  /* Focus. A modal drawer takes focus when it opens. Either kind gives it back to what was focused
     before when it closes, if focus is still inside it or has been dropped. */
  useEffect(() => {
    if (!fixed) return;
    if (!closed) {
      opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      if (modal) dialog.current?.focus({ preventScroll: true });
      return;
    }
    const back = opener.current;
    opener.current = null;
    const now = document.activeElement;
    if (back?.isConnected && (!now || now === document.body || dialog.current?.contains(now))) back.focus({ preventScroll: true });
  }, [closed, fixed, modal]);

  /* The fixed drawer stays mounted and slides on transform only, so it can animate out, and it
     leaves faster than it arrives. The gallery frame shows static states. */
  const slide = bottom
    ? { open: "translateY(0)", peek: `translateY(calc(100% - ${PEEK_PX}px))`, closed: "translateY(100%)" }
    : { open: "translateX(0)", peek: "translateX(0)", closed: "translateX(-100%)" };
  const fixedStyle = {
    ...(bottom
      ? { left: 0, right: 0, marginInline: "auto", width: "min(100%, 720px)", bottom: 0, height: size ?? "78dvh", borderTopLeftRadius: 14, borderTopRightRadius: 14 }
      : { left: 0, top: 0, bottom: 0, width: size ?? 260, borderTopRightRadius: 14, borderBottomRightRadius: 14 }),
    transform: slide[state],
    visibility: closed ? ("hidden" as const) : ("visible" as const),
    // Visibility waits for the slide-out, and does not transition on open: the reduced-motion rule gives every
    // transition 0.01 ms, which would leave the drawer hidden when it takes focus.
    transition: closed
      ? "transform var(--dur-state) var(--ease-exit), visibility 0s linear var(--dur-state)"
      : "transform var(--dur-panel) var(--ease-out)",
    display: "flex",
    flexDirection: "column" as const,
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
      ref={dialog}
      role="dialog"
      aria-label={title}
      aria-modal={modal ? true : undefined}
      aria-hidden={fixed && closed ? true : undefined}
      tabIndex={modal ? -1 : undefined}
      onKeyDown={modal && !closed ? (e) => trapTab(e, dialog.current) : undefined}
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
        <div
          style={{
            position: "relative",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "8px 0 4px",
            // Tall enough to hold the controls' 44 px hit area, which the sheet's overflow would clip.
            minHeight: fixed && actions ? 44 : undefined,
            color: "var(--ink-tertiary)",
          }}
        >
          <DragHandleIcon size={20} />
          {/* A bottom sheet holds a panel that already heads itself, so its title is only the dialog name and its controls share the handle row. */}
          {fixed && actions && <div style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)" }}>{actions}</div>}
        </div>
      )}
      {fixed ? (
        <>
          {!bottom && (title || actions) && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 12px 8px 16px" }}>
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
              transition: `opacity var(--${closed ? "dur-state" : "dur-panel"}) ${closed ? "var(--ease-exit)" : "var(--ease-out)"}`,
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
