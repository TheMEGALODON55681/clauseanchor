import { useState } from "react";
import { SearchIcon, CloseIcon } from "./icons";

export type SearchState = "empty" | "typing" | "results" | "no-results";

export default function SearchField({
  state = "empty",
  placeholder = "Filter categories",
  value: controlled,
  onChange,
}: {
  state?: SearchState;
  placeholder?: string;
  value?: string;
  onChange?: (v: string) => void;
}) {
  const [internal, setInternal] = useState(
    state === "typing" || state === "results" ? "non" : state === "no-results" ? "zzz" : ""
  );
  const value = controlled ?? internal;
  const setValue = (v: string) => {
    setInternal(v);
    onChange?.(v);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, width: "100%" }}>
      <label
        className="focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-[var(--focus-ring)]"
        style={{
          cursor: "text",
          display: "flex",
          alignItems: "center",
          gap: 8,
          minHeight: 44,
          background: "var(--paper-sunken)",
          border: "1px solid var(--control-border)",
          borderRadius: "var(--radius-sm)",
          padding: "0 10px",
        }}
      >
        <span style={{ color: "var(--ink-tertiary)" }}><SearchIcon size={16} /></span>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          aria-label="Filter categories"
          style={{ flex: 1, border: "none", background: "transparent", outline: "none", fontSize: 14, color: "var(--ink-primary)", minWidth: 0 }}
        />
        {value && (
          <button
            type="button"
            aria-label="Reset filter"
            onClick={() => setValue("")}
            className="hit"
            style={{ display: "inline-flex", padding: 4, color: "var(--ink-tertiary)", background: "none", border: "none", cursor: "pointer" }}
          >
            <CloseIcon size={14} />
          </button>
        )}
      </label>
      {state === "no-results" && (
        <span style={{ fontSize: 13, color: "var(--ink-tertiary)" }}>No categories match "{value}".</span>
      )}
    </div>
  );
}
