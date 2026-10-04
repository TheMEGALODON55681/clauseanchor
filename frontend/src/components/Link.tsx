import type { CSSProperties, ReactNode } from "react";
import { Link as RouterLink } from "react-router";
import { ExternalIcon } from "./icons";

export type LinkVariant = "inline" | "standalone" | "external" | "visited";

type LinkProps = {
  variant?: LinkVariant;
  /** "#/path" goes through the router with a view transition. "#" is a placeholder. */
  href?: string;
  children: ReactNode;
};

/* A link inside a sentence takes the prose style, with a tertiary visited colour.
   Navigation and external links keep the anchor colour and get a 44 px hit area. */
export default function Link({ variant = "inline", href = "#", children }: LinkProps) {
  const prose = variant === "inline" || variant === "visited";
  const className = prose ? "link-prose" : "hit";
  const style: CSSProperties = prose
    ? variant === "visited"
      ? { color: "var(--ink-tertiary)" }
      : {}
    : {
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        color: "var(--anchor-600)",
        textDecoration: "underline",
        textDecorationThickness: 1,
        textUnderlineOffset: "0.2em",
        fontSize: 14,
        borderRadius: 2,
      };
  const external = variant === "external";
  if (href.startsWith("#/")) {
    return (
      <RouterLink to={href.slice(1)} viewTransition className={className} style={style}>
        {children}
      </RouterLink>
    );
  }
  return (
    <a
      href={href}
      onClick={href === "#" ? (e) => e.preventDefault() : undefined}
      target={external ? "_blank" : undefined}
      rel={external ? "noreferrer" : undefined}
      className={className}
      style={style}
    >
      {children}
      {external && <ExternalIcon size={14} />}
    </a>
  );
}
