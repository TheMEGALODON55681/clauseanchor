import type { ReactNode } from "react";

/* ClauseAnchor custom glyphs.
   Outline style, 1.5px stroke, rounded caps + joins, on a 20px grid.
   currentColor everywhere so each icon inherits the semantic text color. */

type IconProps = {
  size?: number;
  className?: string;
  strokeWidth?: number;
  title?: string;
};

function Svg({
  size = 20,
  className,
  strokeWidth = 1.5,
  title,
  children,
}: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role={title ? "img" : "presentation"}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

/* Brand mark + "found": an anchor. */
export function AnchorIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="10" cy="4" r="1.75" />
      <path d="M10 5.75V17" />
      <path d="M6 9h8" />
      <path d="M4 11.5c0 3 2.6 5.5 6 5.5s6-2.5 6-5.5" />
      <path d="M4 11.5l1.5.6M16 11.5l-1.5.6" />
    </Svg>
  );
}

/* Statutory flag: the section sign. */
export function SectionIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12.5 6.2c-.4-1.1-1.4-1.8-2.7-1.8-1.6 0-2.7.9-2.7 2.2 0 1.2.9 1.8 2.7 2.3 1.9.5 2.9 1.2 2.9 2.6 0 1.4-1.2 2.3-2.9 2.3-1.4 0-2.5-.7-2.9-1.9" />
    </Svg>
  );
}

/* Clause: a pilcrow. */
export function PilcrowIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M13.5 4H8.5a3 3 0 0 0 0 6h2" />
      <path d="M11 4v12" />
      <path d="M13.5 4v12" />
    </Svg>
  );
}

/* Span: a bracket pair ⟦ ⟧. */
export function BracketPairIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 4H5v12h3" />
      <path d="M7 4v12" />
      <path d="M12 4h3v12h-3" />
      <path d="M13 4v12" />
    </Svg>
  );
}

/* Empty bracket pair: "not found". */
export function EmptyBracketIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 4H5.5v12H8" />
      <path d="M12 4h2.5v12H12" />
    </Svg>
  );
}

/* Case evidence: an index card. */
export function IndexCardIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="5" width="14" height="10" rx="1.5" />
      <path d="M3 8h14" />
      <path d="M6 11h6M6 13h4" />
    </Svg>
  );
}

/* Risk strip: a margin ruler. */
export function MarginRulerIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M7 3v14" />
      <path d="M7 5h3M7 8h2M7 11h3M7 14h2" />
      <rect x="11.5" y="7.5" width="3.5" height="5" rx="0.5" />
    </Svg>
  );
}

/* "Needs a lawyer": a person raising a hand with a document.
   Reads as "ask a professional", never as an error. */
export function PersonWithDocIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="7.5" cy="6" r="2" />
      <path d="M4 16v-1.5A3.5 3.5 0 0 1 7.5 11c1 0 1.9.4 2.5 1" />
      <rect x="11" y="4" width="5" height="7" rx="0.8" />
      <path d="M12.5 6.5h2M12.5 8.5h2" />
    </Svg>
  );
}

/* Unvalidated: a dashed circle. */
export function DashedCircleIcon({ size = 20, className, strokeWidth = 1.5, title }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeDasharray="2.2 2.6"
      className={className}
      role={title ? "img" : "presentation"}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      {title ? <title>{title}</title> : null}
      <circle cx="10" cy="10" r="6" />
    </svg>
  );
}

/* Unavailable: a broken link (operational failure only). */
export function BrokenLinkIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8.5 11.5l-1.4 1.4a2.5 2.5 0 0 1-3.5-3.5l1.9-1.9" />
      <path d="M11.5 8.5l1.4-1.4a2.5 2.5 0 0 1 3.5 3.5l-1.9 1.9" />
      <path d="M8 5V3M5 8H3M12 17v-2M17 12h2" />
    </Svg>
  );
}

/* Polarity: exposure, arrow landing inside a bracket (burden). */
export function ExposureIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 6H4v8h1M15 6h1v8h-1" />
      <path d="M10 4v8" />
      <path d="M7.5 9.5L10 12l2.5-2.5" />
    </Svg>
  );
}

/* Polarity: protection, arrow leaving a bracket (benefit). */
export function ProtectionIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 6H4v8h1M15 6h1v8h-1" />
      <path d="M10 16V8" />
      <path d="M7.5 10.5L10 8l2.5 2.5" />
    </Svg>
  );
}

/* Polarity: mixed, two-way vertical arrow. */
export function MixedIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10 4v12" />
      <path d="M7 7l3-3 3 3" />
      <path d="M7 13l3 3 3-3" />
    </Svg>
  );
}

/* Polarity: neutral, short horizontal line. */
export function NeutralIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 10h8" />
    </Svg>
  );
}

/* Polarity: unresolved, question mark in a dotted circle. */
export function UnresolvedIcon({ size = 20, className, strokeWidth = 1.5, title }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role={title ? "img" : "presentation"}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      {title ? <title>{title}</title> : null}
      <circle cx="10" cy="10" r="6.5" strokeDasharray="2.2 2.6" />
      <path d="M8.4 8.2a1.7 1.7 0 0 1 3.2.6c0 1.1-1.6 1.4-1.6 2.4" />
      <path d="M10 13.4h.01" />
    </svg>
  );
}

export function ChevronIcon({ open = false, ...props }: IconProps & { open?: boolean }) {
  return (
    <Svg {...props} className={`${props.className ?? ""} transition-transform ${open ? "rotate-90" : ""}`}>
      <path d="M8 5l5 5-5 5" />
    </Svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 6l8 8M14 6l-8 8" />
    </Svg>
  );
}

export function ExternalIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 5H5v10h10v-3" />
      <path d="M12 4h4v4" />
      <path d="M16 4l-6 6" />
    </Svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 10.5l3.2 3.2L15 6.5" />
    </Svg>
  );
}

export function MinusIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 10h10" />
    </Svg>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="9" cy="9" r="5" />
      <path d="M13 13l3 3" />
    </Svg>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 8l5 5 5-5" />
    </Svg>
  );
}

export function InfoIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="10" cy="10" r="6.5" />
      <path d="M10 9v4" />
      <path d="M10 6.6h.01" />
    </Svg>
  );
}

export function UploadIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10 13V4" />
      <path d="M6.5 7.5L10 4l3.5 3.5" />
      <path d="M4 14v2h12v-2" />
    </Svg>
  );
}

export function FileIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 3h5l3 3v11H6z" />
      <path d="M11 3v3h3" />
    </Svg>
  );
}

export function TrashIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 6h12" />
      <path d="M8 6V4h4v2" />
      <path d="M6 6l.7 10h6.6L14 6" />
    </Svg>
  );
}

export function DotsIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="5" cy="10" r="1" />
      <circle cx="10" cy="10" r="1" />
      <circle cx="15" cy="10" r="1" />
    </Svg>
  );
}

export function DownloadIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10 4v9" />
      <path d="M6.5 9.5L10 13l3.5-3.5" />
      <path d="M4 15v1h12v-1" />
    </Svg>
  );
}

export function DragHandleIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 8h8M6 12h8" />
    </Svg>
  );
}

/* Theme toggle: sun and moon. */
export function SunIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="10" cy="10" r="3.25" />
      <path d="M10 2.5v1.75M10 15.75v1.75M2.5 10h1.75M15.75 10h1.75M4.7 4.7l1.2 1.2M14.1 14.1l1.2 1.2M4.7 15.3l1.2-1.2M14.1 5.9l1.2-1.2" />
    </Svg>
  );
}

export function MoonIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M15.5 12.4A6 6 0 0 1 7.6 4.5a6 6 0 1 0 7.9 7.9Z" />
    </Svg>
  );
}

/* Drawer toggle: three ledger lines. */
export function ListIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 6h12M4 10h12M4 14h8" />
    </Svg>
  );
}
