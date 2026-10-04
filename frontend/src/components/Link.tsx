import type { ReactNode } from "react";
import { ExternalIcon } from "./icons";

export type LinkVariant = "inline" | "standalone" | "external" | "visited";

type LinkProps = {
  variant?: LinkVariant;
  href?: string;
  children: ReactNode;
};

export default function Link({ variant = "inline", href = "#", children }: LinkProps) {
  const visited = variant === "visited";
  return (
    <a
      href={href}
      onClick={(e) => e.preventDefault()}
      target={variant === "external" ? "_blank" : undefined}
      rel={variant === "external" ? "noreferrer" : undefined}
      className="focus:outline-none focus-visible:outline-none"
      style={{
        display: variant === "standalone" || variant === "external" ? "inline-flex" : "inline",
        alignItems: "center",
        gap: 4,
        color: visited ? "var(--anchor-700)" : "var(--anchor-600)",
        textDecoration: "underline",
        textUnderlineOffset: 2,
        fontSize: 14,
        borderRadius: 2,
      }}
      onFocus={(e) => {
        e.currentTarget.style.outline = "2px solid var(--focus-ring)";
        e.currentTarget.style.outlineOffset = "2px";
      }}
      onBlur={(e) => (e.currentTarget.style.outline = "none")}
    >
      {children}
      {variant === "external" && <ExternalIcon size={14} />}
    </a>
  );
}
