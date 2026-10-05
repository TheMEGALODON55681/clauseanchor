import { useId } from "react";
import type { ReactNode } from "react";
import { CheckIcon } from "./icons";

export type RadioCardState = "unselected" | "hover" | "selected" | "focus" | "disabled";

type RadioCardProps = {
  title: string;
  description?: string;
  icon?: ReactNode;
  /** A short label after the title. */
  tag?: string;
  /** Extra content under the description, such as a quote. */
  children?: ReactNode;
  /** Force a visual state, used by the gallery and the landing specimens. Interactive by default. */
  state?: RadioCardState;
  /** The group. Cards with the same name are one group, so give each group its own. A lone card gets its own. */
  name?: string;
  value?: string;
  checked?: boolean;
  onSelect?: () => void;
};

/* A choice card on a native radio input, so the arrow keys and the single tab stop of a
   group come from the browser. The look is in index.css (.radio-card). */
export default function RadioCard({ title, description, icon, tag, children, state, name, value, checked = false, onSelect }: RadioCardProps) {
  const id = useId();
  return (
    <label className="radio-card" data-state={state}>
      <input
        type="radio"
        className="sr-only"
        name={name ?? id}
        value={value}
        checked={state ? state === "selected" : checked}
        disabled={state === "disabled"}
        onChange={() => onSelect?.()}
        aria-labelledby={`${id}-title`}
        aria-describedby={description || children ? `${id}-body` : undefined}
      />
      {icon && <span className="radio-card-icon">{icon}</span>}
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="flex flex-wrap items-center gap-2">
          <span id={`${id}-title`} className="text-[15px] font-medium" style={{ color: "var(--ink-primary)" }}>{title}</span>
          {tag && <span className="radio-card-tag">{tag}</span>}
        </span>
        {(description || children) && (
          <span id={`${id}-body`} className="flex flex-col gap-1">
            {description && <span className="text-[13px] leading-[18px]" style={{ color: "var(--ink-secondary)" }}>{description}</span>}
            {children}
          </span>
        )}
      </span>
      <span aria-hidden className="radio-card-check">
        <CheckIcon size={18} />
      </span>
    </label>
  );
}
