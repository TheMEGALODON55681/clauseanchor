import { useEffect, useState } from "react";
import { Outlet, useLocation, useMatch } from "react-router";
import AppHeader from "../components/AppHeader";
import AppFooter from "../components/AppFooter";
import Button from "../components/Button";
import Toast from "../components/Toast";
import Link from "../components/Link";
import { MoonIcon, SunIcon } from "../components/icons";
import { useTheme } from "./theme";
import { useSession } from "./session";
import { useMedia } from "../lib/useMedia";

const LINKS = [
  { label: "Review", href: "#/", path: "/" },
  { label: "How it works", href: "#/how-it-works", path: "/how-it-works" },
  { label: "Accuracy", href: "#/accuracy", path: "/accuracy" },
];

export default function Root() {
  const { theme, toggle } = useTheme();
  const { toasts, dismissToast, mock } = useSession();
  const location = useLocation();
  const inReader = !!useMatch("/review/:documentId");
  const wide = useMedia("(min-width: 768px)");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
    if (!inReader) window.scrollTo(0, 0);
  }, [location.pathname, inReader]);

  const themeButton = (
    <Button
      variant="secondary"
      size="s"
      icon="icon-only"
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      onClick={toggle}
      iconNode={theme === "dark" ? <SunIcon size={18} /> : <MoonIcon size={18} />}
    />
  );

  const sample = !!mock?.sampleMode;
  const links = LINKS.map((l) => ({
    label: l.label,
    href: l.href,
    current: l.path === "/" ? location.pathname === "/" || inReader : location.pathname === l.path,
  }));

  return (
    <div className={inReader ? "flex h-dvh flex-col overflow-hidden" : "flex min-h-dvh flex-col"} style={{ background: "var(--paper-base)" }}>
      <a
        href="#main"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main")?.focus();
        }}
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:px-3 focus:py-2"
        style={{ background: "var(--paper-sheet)", color: "var(--anchor-600)" }}
      >
        Skip to content
      </a>
      <div style={{ position: "relative", zIndex: 30 }}>
        <AppHeader
          variant={!wide ? "mobile" : sample ? "sample-mode" : "default"}
          links={links}
          homeHref="#/"
          trailing={themeButton}
          onMenu={() => setMenuOpen((v) => !v)}
        />
        {!wide && menuOpen && (
          <nav
            aria-label="Main"
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: "100%",
              background: "var(--paper-sheet)",
              borderBottom: "1px solid var(--rule-default)",
              boxShadow: "var(--elevation-2)",
              padding: "8px 20px 14px",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            {links.map((l) => (
              <span key={l.label} aria-current={l.current ? "page" : undefined} style={{ minHeight: 36, display: "flex", alignItems: "center" }}>
                <Link variant="standalone" href={l.href}>{l.label}</Link>
              </span>
            ))}
            <span style={{ fontSize: 13, color: "var(--ink-tertiary)" }}>Not legal advice</span>
          </nav>
        )}
      </div>

      <main id="main" tabIndex={-1} className={inReader ? "flex min-h-0 flex-1 flex-col focus:outline-none" : "flex-1 focus:outline-none"}>
        <Outlet />
      </main>

      {!inReader && <AppFooter sampleMode={sample} creditsHref="#/how-it-works" />}

      <div
        aria-live="polite"
        style={{ position: "fixed", right: 16, bottom: 16, left: 16, zIndex: 60, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, pointerEvents: "none" }}
      >
        {toasts.map((t) => (
          <div key={t.id} style={{ pointerEvents: "auto", maxWidth: "100%" }}>
            <Toast variant={t.variant} message={t.message} onDismiss={() => dismissToast(t.id)} />
          </div>
        ))}
      </div>
    </div>
  );
}
