import type { ReactNode } from "react";
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
}: {
  variant?: HeaderVariant;
  links?: NavLink[];
  homeHref?: string;
  /** Extra controls, such as the theme toggle. */
  trailing?: ReactNode;
  onMenu?: () => void;
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
          <a href={homeHref} aria-label="ClauseAnchor home" className="rounded focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]" style={{ display: "inline-flex" }}>
            <HorizontalLockup size={26} />
          </a>
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
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {trailing}
          <Button variant="secondary" size="s" icon="icon-only" aria-label="Open menu" onClick={onMenu} iconNode={<DotsIcon size={18} />} />
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
