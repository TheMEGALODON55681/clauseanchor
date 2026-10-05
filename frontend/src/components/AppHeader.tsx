import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router";
import { HorizontalLockup } from "./BrandMark";
import Link from "./Link";
import Button from "./Button";
import { DotsIcon } from "./icons";

export type HeaderVariant = "default" | "sample-mode" | "mobile";

type NavLink = { label: string; href: string; current?: boolean };

const DEFAULT_LINKS: NavLink[] = [
  { label: "Review", href: "#" },
  { label: "How it works", href: "#" },
  { label: "Accuracy", href: "#" },
];

export default function AppHeader({
  variant = "default",
  links = DEFAULT_LINKS,
  homeHref,
  trailing,
  onMenu,
  menuOpen = false,
  menuId,
}: {
  variant?: HeaderVariant;
  links?: NavLink[];
  homeHref?: string;
  /** Extra controls at the far right, such as the theme toggle and the primary action. */
  trailing?: ReactNode;
  onMenu?: () => void;
  /** Mobile menu state, for the expanded state of its button. */
  menuOpen?: boolean;
  menuId?: string;
}) {
  const mobile = variant === "mobile";
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        padding: "12px 20px",
        background: "var(--paper-sheet)",
        borderBottom: "1px solid var(--rule-default)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {homeHref ? (
          <RouterLink to={homeHref.slice(1)} viewTransition aria-label="ClauseAnchor home" className="hit rounded" style={{ display: "inline-flex" }}>
            <HorizontalLockup size={26} />
          </RouterLink>
        ) : (
          <HorizontalLockup size={26} />
        )}
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

      {mobile ? (
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {trailing}
          <Button id="menu-button" variant="secondary" size="s" icon="icon-only" aria-label={menuOpen ? "Close menu" : "Open menu"} aria-expanded={menuOpen} aria-controls={menuId} onClick={onMenu} iconNode={<DotsIcon size={18} />} />
        </div>
      ) : (
        <nav aria-label="Main" style={{ display: "flex", alignItems: "center", gap: 18 }}>
          {links.map((l) => (
            <span key={l.label} aria-current={l.current ? "page" : undefined} style={l.current ? { boxShadow: "inset 0 -2px 0 var(--anchor-600)" } : undefined}>
              <Link variant="standalone" href={l.href}>{l.label}</Link>
            </span>
          ))}
          <span style={{ fontSize: 13, color: "var(--ink-tertiary)" }}>Not legal advice</span>
          {trailing}
        </nav>
      )}
    </header>
  );
}
