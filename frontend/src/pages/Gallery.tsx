import { useState } from "react";
import type { ReactNode } from "react";
import { AnchorIcon } from "../components/icons";
import Button from "../components/Button";
import StatusChip, { type StatusKind, type ChipSize } from "../components/StatusChip";
import PolarityBadge, { type PolarityKind } from "../components/PolarityBadge";
import ConfidenceBand from "../components/ConfidenceBand";
import JudgmentCard from "../components/JudgmentCard";
import MarginRuler from "../components/MarginRuler";
import SpanHighlight from "../components/SpanHighlight";
import ClauseDetailPanel from "../components/ClauseDetailPanel";

// Atoms
import TextInput from "../components/TextInput";
import Select from "../components/Select";
import RadioCard from "../components/RadioCard";
import CheckboxRadio from "../components/CheckboxRadio";
import Switch from "../components/Switch";
import StatuteTag from "../components/StatuteTag";
import CountBadge from "../components/CountBadge";
import Tooltip from "../components/Tooltip";
import LinkAtom from "../components/Link";
import KeyboardHint from "../components/KeyboardHint";
import DividerAtom from "../components/Divider";
import Spinner from "../components/Spinner";
import OffsetTag from "../components/OffsetTag";
import Skeleton from "../components/Skeleton";

// Molecules
import UploadDropzone from "../components/UploadDropzone";
import RoleSelector from "../components/RoleSelector";
import PartyBindingField from "../components/PartyBindingField";
import NoticeBanner from "../components/NoticeBanner";
import CategoryRow from "../components/CategoryRow";
import CategoryGroupHeader from "../components/CategoryGroupHeader";
import StageProgress from "../components/StageProgress";
import RuleFlagCard from "../components/RuleFlagCard";
import SearchField from "../components/SearchField";
import Tabs from "../components/Tabs";
import SegmentedFilter from "../components/SegmentedFilter";
import Toast from "../components/Toast";
import ConfirmDialog from "../components/ConfirmDialog";
import EmptyState from "../components/EmptyState";
import ErrorCard from "../components/ErrorCard";
import MetricCell from "../components/MetricCell";
import DropdownMenu from "../components/DropdownMenu";
import SectionPath from "../components/SectionPath";

// Organisms
import CategorySidebar from "../components/CategorySidebar";
import ReaderToolbar from "../components/ReaderToolbar";
import DocumentBlock from "../components/DocumentBlock";
import PerformanceTableRow from "../components/PerformanceTableRow";
import AppHeader from "../components/AppHeader";
import AppFooter from "../components/AppFooter";
import MobileDrawer from "../components/MobileDrawer";
import Disclosure from "../components/Disclosure";
import { Section } from "../components/Layout";
import { useReveal } from "../lib/useReveal";
import { AnchorLogomark, Wordmark, HorizontalLockup, Favicon } from "../components/BrandMark";

type Mode = "light" | "dark";

/* WCAG relative-luminance contrast ratio between two hex colors. */
function contrast(a: string, b: string): number {
  const lum = (hex: string) => {
    const c = hex.replace("#", "");
    const rgb = [0, 2, 4].map((i) => parseInt(c.slice(i, i + 2), 16) / 255);
    const lin = rgb.map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
  };
  const l1 = lum(a);
  const l2 = lum(b);
  const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

// -- Foundations reference data (both modes) --------------------------------

const CORE: { token: string; light: string; dark: string; on: [string, string] }[] = [
  { token: "paper/base", light: "#F6F3EC", dark: "#131619", on: ["#1B1F24", "#ECE7DD"] },
  { token: "paper/sheet", light: "#FFFDF8", dark: "#1A1E22", on: ["#1B1F24", "#ECE7DD"] },
  { token: "paper/sunken", light: "#EFEBE2", dark: "#0F1214", on: ["#1B1F24", "#ECE7DD"] },
  { token: "ink/primary", light: "#1B1F24", dark: "#ECE7DD", on: ["#F6F3EC", "#131619"] },
  { token: "ink/secondary", light: "#4E545B", dark: "#B4AEA3", on: ["#F6F3EC", "#131619"] },
  { token: "ink/tertiary", light: "#646970", dark: "#8B867F", on: ["#F6F3EC", "#131619"] },
  { token: "control/border", light: "#85817A", dark: "#6A6E72", on: ["#F6F3EC", "#131619"] },
  { token: "anchor/600", light: "#0F4C5C", dark: "#6FB8C8", on: ["#FFFDF8", "#131619"] },
  { token: "anchor/700", light: "#0A3945", dark: "#8FCBD8", on: ["#FFFDF8", "#131619"] },
];

const SPACING = [
  ["space/1", 4], ["space/2", 8], ["space/3", 12], ["space/4", 16],
  ["space/6", 24], ["space/8", 32], ["space/12", 48], ["space/16", 64],
] as const;

const TYPE_SPECIMENS: { style: string; family: string; note: string; el: ReactNode }[] = [
  {
    style: "display/md",
    family: "Source Serif 4 600",
    note: "30 / 38",
    el: <span style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 30, lineHeight: "38px" }}>Section titles read as print</span>,
  },
  {
    style: "heading/lg",
    family: "IBM Plex Sans 600",
    note: "22 / 30",
    el: <span style={{ fontWeight: 600, fontSize: 22, lineHeight: "30px" }}>Panel titles</span>,
  },
  {
    style: "body/md",
    family: "IBM Plex Sans 400",
    note: "15 / 24",
    el: <span style={{ fontSize: 15, lineHeight: "24px" }}>Default UI text sits quietly on the page.</span>,
  },
  {
    style: "document/body",
    family: "Source Serif 4 400",
    note: "17 / 30",
    el: <span style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: "30px" }}>Contract reading text, generous and calm.</span>,
  },
  {
    style: "citation",
    family: "Source Serif 4 500 small caps",
    note: "13 / 20",
    el: <span style={{ fontFamily: "var(--font-serif)", fontWeight: 500, fontVariant: "small-caps", letterSpacing: "0.03em", fontSize: 13 }}>Sample Traders Pvt. Ltd. v. Example Industries Ltd.</span>,
  },
  {
    style: "mono/sm",
    family: "IBM Plex Mono 400",
    note: "12 / 18",
    el: <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>chars 4210 to 4488</span>,
  },
];

// -- Small layout helpers ---------------------------------------------------

function SectionTitle({ children, sub, id }: { children: ReactNode; sub?: string; id?: string }) {
  return (
    <div id={id} style={{ marginBottom: 20, scrollMarginTop: 80 }}>
      <h2
        style={{
          fontFamily: "var(--font-serif)",
          fontWeight: 600,
          fontSize: 30,
          lineHeight: "38px",
          letterSpacing: "-0.005em",
          color: "var(--ink-primary)",
        }}
      >
        {children}
      </h2>
      {sub && (
        <p style={{ fontSize: 14, color: "var(--ink-secondary)", marginTop: 4, maxWidth: "60ch" }}>{sub}</p>
      )}
    </div>
  );
}

function Group({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--ink-tertiary)",
          marginBottom: 12,
        }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}

function Cell({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-start" }}>
      <div style={{ display: "flex", alignItems: "center", minHeight: 48 }}>{children}</div>
      <span style={{ fontSize: 12, color: "var(--ink-tertiary)", fontFamily: "var(--font-mono)" }}>{caption}</span>
    </div>
  );
}

function Divider() {
  return <div style={{ height: 1, background: "var(--rule-default)", margin: "40px 0" }} />;
}

/* A block component shown with its state name underneath. */
function Labeled({ label, children, width }: { label: string; children: ReactNode; width?: number | string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, width }}>
      <div style={{ display: "flex", alignItems: "center", minHeight: 44 }}>{children}</div>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-tertiary)" }}>{label}</span>
    </div>
  );
}

/* Wrapping row for a set of labeled states. */
function Row({ children }: { children: ReactNode }) {
  return <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>{children}</div>;
}

// -- The library shown once per mode ---------------------------------------

function Library({ mode }: { mode: Mode }) {
  const statuses: StatusKind[] = ["found", "review", "unvalidated", "absent", "unavailable"];
  const polarities: PolarityKind[] = ["exposure", "protection", "mixed", "neutral", "unresolved"];
  // Section ids live on the light column only so anchors stay unique across both columns.
  const sid = (name: string) => (mode === "light" ? name : undefined);

  return (
    <div>
      {/* Foundations */}
      <SectionTitle id={sid("foundations")} sub="Every component references variables, never raw hex. Contrast ratios measured against the appropriate ground.">
        Foundations
      </SectionTitle>

      <Group label="Color · core">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {CORE.map((c) => {
            const swatch = mode === "light" ? c.light : c.dark;
            const on = mode === "light" ? c.on[0] : c.on[1];
            const ratio = contrast(swatch, on);
            return (
              <div
                key={c.token}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  border: "1px solid var(--rule-default)",
                  borderRadius: "var(--radius-sm)",
                  padding: 8,
                  background: "var(--paper-sheet)",
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "var(--radius-sm)",
                    background: swatch,
                    border: "1px solid var(--rule-strong)",
                    flexShrink: 0,
                  }}
                />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-primary)" }}>{c.token}</div>
                  <div style={{ fontSize: 11, color: "var(--ink-tertiary)" }}>
                    {swatch} · {ratio.toFixed(1)}:1 {ratio >= 4.5 ? "AA" : ratio >= 3 ? "AA lg" : ""}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </Group>

      <Group label="Typography">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {TYPE_SPECIMENS.map((t) => (
            <div key={t.style} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <div style={{ color: "var(--ink-primary)" }}>{t.el}</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-tertiary)" }}>
                {t.style} · {t.family} · {t.note}
              </div>
            </div>
          ))}
        </div>
      </Group>

      <Group label="Spacing · 4px base">
        <div style={{ display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap" }}>
          {SPACING.map(([name, v]) => (
            <div key={name} style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "center" }}>
              <div style={{ width: v, height: v, background: "var(--anchor-600)", borderRadius: 2 }} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-tertiary)" }}>{v}</span>
            </div>
          ))}
        </div>
      </Group>

      <Group label="Radius & elevation">
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {(["sm", "md", "lg"] as const).map((r) => (
            <Cell key={r} caption={`radius/${r}`}>
              <div style={{ width: 56, height: 40, background: "var(--paper-sheet)", border: "1px solid var(--rule-strong)", borderRadius: `var(--radius-${r})` }} />
            </Cell>
          ))}
          {([1, 2, 3] as const).map((e) => (
            <Cell key={e} caption={`elevation/${e}`}>
              <div style={{ width: 56, height: 40, background: "var(--paper-sheet)", borderRadius: "var(--radius-md)", boxShadow: `var(--elevation-${e})` }} />
            </Cell>
          ))}
        </div>
      </Group>

      <Divider />

      {/* Buttons */}
      <SectionTitle sub="Rectangular with a 2px ink-stamp bottom edge. On press the edge lifts and the button shifts down 1px.">
        Button
      </SectionTitle>

      <Group label="Variants · size M">
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
          <Cell caption="primary"><Button variant="primary">Start review</Button></Cell>
          <Cell caption="secondary"><Button variant="secondary">Choose file</Button></Cell>
          <Cell caption="tertiary"><Button variant="tertiary">View full passage</Button></Cell>
          <Cell caption="destructive"><Button variant="destructive">Delete document</Button></Cell>
          <Cell caption="ghost-on-dark">
            <span style={{ background: "var(--ink-primary)", padding: 8, borderRadius: "var(--radius-md)" }}>
              <Button variant="ghost-on-dark">Dismiss</Button>
            </span>
          </Cell>
        </div>
      </Group>

      <Group label="States · primary">
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
          {(["default", "hover", "pressed", "focus", "disabled", "loading"] as const).map((st) => (
            <Cell key={st} caption={st}>
              <Button variant="primary" state={st}>Start review</Button>
            </Cell>
          ))}
        </div>
      </Group>

      <Group label="Sizes & icons">
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
          <Cell caption="S"><Button size="s">Small</Button></Cell>
          <Cell caption="M"><Button size="m">Medium</Button></Cell>
          <Cell caption="L"><Button size="l">Large</Button></Cell>
          <Cell caption="leading icon">
            <Button variant="secondary" icon="leading" iconNode={<AnchorIcon size={18} />}>Upload contract</Button>
          </Cell>
          <Cell caption="icon-only">
            <Button variant="secondary" icon="icon-only" aria-label="Upload contract" iconNode={<AnchorIcon size={18} />} />
          </Cell>
        </div>
      </Group>

      <Divider />

      {/* Chips & badges */}
      <SectionTitle sub="Status is never color-only: every one carries an icon and a text label.">
        Status chip & polarity badge
      </SectionTitle>

      <Group label="Status chip · size M">
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {statuses.map((s) => (
            <StatusChip key={s} status={s} size="m" />
          ))}
        </div>
      </Group>
      <Group label="Status chip · size S">
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {statuses.map((s) => (
            <StatusChip key={s} status={s} size={"s" as ChipSize} />
          ))}
        </div>
      </Group>
      <Group label="Polarity badge">
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {polarities.map((p) => (
            <PolarityBadge key={p} polarity={p} />
          ))}
        </div>
      </Group>

      <Divider />

      {/* Signature components */}
      <SectionTitle sub="The pieces that make ClauseAnchor feel like a careful reader's marginalia.">
        Signature components
      </SectionTitle>

      <Group label="Confidence band · a measurement range, never a bare percentage">
        <div style={{ display: "flex", gap: 28, flexWrap: "wrap" }}>
          <Cell caption="higher, with a calibration scope"><ConfidenceBand variant="higher" size="full" calibration="category" /></Cell>
          <Cell caption="review, with a calibration scope"><ConfidenceBand variant="review" size="full" calibration="pooled" /></Cell>
          <Cell caption="higher, label only (no calibration in the data)"><ConfidenceBand variant="higher" size="full" /></Cell>
          <Cell caption="unvalidated"><ConfidenceBand variant="unvalidated" size="full" /></Cell>
        </div>
      </Group>

      <Group label="Span highlight · underline + faint tint, text stays legible">
        <div style={{ display: "flex", flexDirection: "column", gap: 14, background: "var(--paper-sheet)", border: "1px solid var(--rule-default)", borderRadius: "var(--radius-md)", padding: "16px 16px 16px 24px" }}>
          {(["found", "review", "focused", "overlap2", "overlap3", "hover", "keyboard"] as const).map((k) => (
            <div key={k}>
              <SpanHighlight kind={k} />
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-tertiary)", marginTop: 2, marginLeft: 16 }}>{k}</div>
            </div>
          ))}
        </div>
      </Group>

      <Group label="Margin ruler · a ledger margin, not a heatmap">
        <div style={{ display: "flex", gap: 32, alignItems: "flex-start", flexWrap: "wrap" }}>
          {(["default", "hover", "grouped", "selected", "empty"] as const).map((v) => (
            <div key={v} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <MarginRuler variant={v} height={260} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-tertiary)" }}>{v}</span>
            </div>
          ))}
        </div>
      </Group>

      <Group label="Judgment card · a library index card">
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16, maxWidth: 460 }}>
          <div>
            <JudgmentCard state="collapsed" authority="reviewed" />
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-tertiary)", marginTop: 4 }}>collapsed · reviewed</div>
          </div>
          <div>
            <JudgmentCard state="expanded" authority="overruled" />
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-tertiary)", marginTop: 4 }}>expanded · later overruled</div>
          </div>
          <div>
            <JudgmentCard state="empty" />
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-tertiary)", marginTop: 4 }}>no evidence</div>
          </div>
        </div>
      </Group>

      <Group label="Clause detail panel · the organism these atoms assemble into">
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
          {(["found", "review", "absent", "loading"] as const).map((v) => (
            <div key={v} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <ClauseDetailPanel variant={v} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-tertiary)" }}>{v}</span>
            </div>
          ))}
        </div>
      </Group>

      <Divider />

      {/* ============================= ATOMS ============================= */}
      <SectionTitle id={sid("atoms")} sub="Single-purpose parts. Every interactive one carries a visible 2px focus ring and a 44px touch target.">
        02 Atoms
      </SectionTitle>

      <Group label="Text input">
        <Row>
          {(["default", "hover", "focus", "filled", "error", "disabled"] as const).map((st) => (
            <Labeled key={st} label={st} width={220}>
              <TextInput state={st} label="Party name" placeholder="Enter a party name" />
            </Labeled>
          ))}
        </Row>
      </Group>

      <Group label="Select">
        <Row>
          {(["closed", "open", "focus", "disabled"] as const).map((st) => (
            <Labeled key={st} label={st} width={220}>
              <Select state={st} label="Your role" />
            </Labeled>
          ))}
        </Row>
      </Group>

      <Group label="Radio card">
        <Row>
          {(["unselected", "hover", "selected", "focus", "disabled"] as const).map((st) => (
            <Labeled key={st} label={st} width={220}>
              <RadioCard state={st} title="Buyer" description="You are receiving goods or services." />
            </Labeled>
          ))}
        </Row>
      </Group>

      <Group label="Checkbox & radio">
        <Row>
          {(["unchecked", "checked", "indeterminate", "focus", "disabled"] as const).map((st) => (
            <Labeled key={`c-${st}`} label={`checkbox: ${st}`}>
              <CheckboxRadio kind="checkbox" state={st} label="Include case law" />
            </Labeled>
          ))}
          {(["unchecked", "checked", "focus", "disabled"] as const).map((st) => (
            <Labeled key={`r-${st}`} label={`radio: ${st}`}>
              <CheckboxRadio kind="radio" state={st} label="Sample mode" />
            </Labeled>
          ))}
        </Row>
      </Group>

      <Group label="Switch">
        <Row>
          {(["off", "on", "focus", "disabled"] as const).map((st) => (
            <Labeled key={st} label={st}>
              <Switch state={st} label="Show low-confidence findings" />
            </Labeled>
          ))}
        </Row>
      </Group>

      <Group label="Statute tag · count badge · offset tag">
        <Row>
          {(["default", "hover", "focus"] as const).map((st) => (
            <Labeled key={st} label={`statute: ${st}`}>
              <StatuteTag state={st} />
            </Labeled>
          ))}
          <Labeled label="count: neutral"><CountBadge count={3} tone="neutral" /></Labeled>
          <Labeled label="count: anchor"><CountBadge count={12} tone="anchor" /></Labeled>
          <Labeled label="offset tag"><OffsetTag start={4210} end={4488} /></Labeled>
        </Row>
      </Group>

      <Group label="Tooltip · four sides">
        <div style={{ display: "flex", gap: 44, flexWrap: "wrap", padding: "20px 8px" }}>
          {(["top", "bottom", "left", "right"] as const).map((side) => (
            <Labeled key={side} label={side}>
              <Tooltip side={side} label="Character offsets in the source text" open>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-secondary)", border: "1px dashed var(--rule-strong)", padding: "4px 8px", borderRadius: 4 }}>
                  hover
                </span>
              </Tooltip>
            </Labeled>
          ))}
        </div>
      </Group>

      <Group label="Link · keyboard hint · spinner">
        <Row>
          <Labeled label="inline"><LinkAtom variant="inline">read the clause</LinkAtom></Labeled>
          <Labeled label="standalone"><LinkAtom variant="standalone">View full passage</LinkAtom></Labeled>
          <Labeled label="external"><LinkAtom variant="external">Indian Contract Act 1872</LinkAtom></Labeled>
          <Labeled label="visited"><LinkAtom variant="visited">Section 27</LinkAtom></Labeled>
          <Labeled label="keyboard hint"><KeyboardHint keys={["J"]} /></Labeled>
          <Labeled label="keys: g then n"><KeyboardHint keys={["G", "N"]} /></Labeled>
          {([14, 20, 32] as const).map((s) => (
            <Labeled key={s} label={`spinner ${s}`}><Spinner size={s} /></Labeled>
          ))}
        </Row>
      </Group>

      <Group label="Divider · horizontal / vertical / labelled">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ width: 260 }}><DividerAtom /></div>
          <div style={{ height: 40, display: "flex", alignItems: "center" }}>
            <span style={{ fontSize: 13, color: "var(--ink-secondary)" }}>before</span>
            <DividerAtom orientation="vertical" />
            <span style={{ fontSize: 13, color: "var(--ink-secondary)" }}>after</span>
          </div>
          <div style={{ width: 260 }}><DividerAtom label="Money and liability" /></div>
        </div>
      </Group>

      <Group label="Skeleton · reduced-motion aware">
        <Row>
          <Labeled label="line" width={220}><Skeleton variant="line" /></Labeled>
          <Labeled label="block" width={220}><Skeleton variant="block" /></Labeled>
          <Labeled label="paragraph" width={260}><Skeleton variant="paragraph" /></Labeled>
        </Row>
      </Group>

      <Divider />

      {/* ============================ MOLECULES ============================ */}
      <SectionTitle id={sid("molecules")} sub="Atoms combined into the recurring building blocks of each screen.">
        03 Molecules
      </SectionTitle>

      <Group label="Notice banner · fixed phrases, verbatim">
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 460 }}>
          {(["legal-scope", "privacy", "sample-mode", "session-expiry"] as const).map((v) => (
            <Labeled key={v} label={v}><NoticeBanner variant={v} /></Labeled>
          ))}
        </div>
      </Group>

      <Group label="Upload dropzone · states and the four error messages">
        <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 460 }}>
          {(["idle", "hover", "drag-over", "validating", "uploaded", "error-type", "error-size", "error-scanned", "error-protected"] as const).map((st) => (
            <Labeled key={st} label={st} width="100%"><UploadDropzone state={st} /></Labeled>
          ))}
        </div>
      </Group>

      <Group label="Role selector">
        <div style={{ maxWidth: 460 }}><RoleSelector /></div>
      </Group>

      <Group label="Party binding field">
        <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 460 }}>
          {(["loading", "choices", "selected", "unresolved"] as const).map((st) => (
            <Labeled key={st} label={st} width="100%"><PartyBindingField state={st} /></Labeled>
          ))}
        </div>
      </Group>

      <Group label="Category group header · category row">
        <div style={{ maxWidth: 320, border: "1px solid var(--rule-default)", borderRadius: "var(--radius-md)", overflow: "hidden", background: "var(--paper-sunken)" }}>
          <CategoryGroupHeader label="Restrictions" summary="2 found, 1 needs a lawyer" />
          <CategoryRow name="Non-Compete" status="found" count={1} state="selected" />
          <CategoryRow name="Exclusivity" status="review" />
          <CategoryRow name="Price Restrictions" status="absent" />
          <CategoryGroupHeader label="Money and liability" summary="2 found, 1 not validated" collapsed />
        </div>
      </Group>

      <Group label="Stage progress · full and compact, no percentage bar">
        <div style={{ display: "flex", gap: 32, flexWrap: "wrap", alignItems: "flex-start" }}>
          <Labeled label="full" width={280}><StageProgress /></Labeled>
          <Labeled label="compact"><StageProgress compact /></Labeled>
        </div>
      </Group>

      <Group label="Rule flag card">
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 460 }}>
          {(["standard", "verify", "applicability-unclear"] as const).map((v) => (
            <Labeled key={v} label={v} width="100%"><RuleFlagCard variant={v} /></Labeled>
          ))}
        </div>
      </Group>

      <Group label="Search field">
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 320 }}>
          {(["empty", "typing", "results", "no-results"] as const).map((st) => (
            <Labeled key={st} label={st} width="100%"><SearchField state={st} /></Labeled>
          ))}
        </div>
      </Group>

      <Group label="Tabs · segmented filter · section path">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Labeled label="tabs"><Tabs items={["Findings", "Case law", "Accuracy"]} value="Findings" disabledItems={["Accuracy"]} /></Labeled>
          <Labeled label="segmented filter"><SegmentedFilter /></Labeled>
          <Labeled label="section path"><SectionPath /></Labeled>
        </div>
      </Group>

      <Group label="Toast · success / info / error">
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 380 }}>
          <Labeled label="success" width="100%"><Toast variant="success" /></Labeled>
          <Labeled label="info" width="100%"><Toast variant="info" /></Labeled>
          <Labeled label="error" width="100%"><Toast variant="error" /></Labeled>
        </div>
      </Group>

      <Group label="Metric cell">
        <Row>
          <Labeled label="value + n"><MetricCell variant="value" label="Precision" value="0.89" support={42} /></Labeled>
          <Labeled label="not measured"><MetricCell variant="not-measured" label="Recall" /></Labeled>
          <Labeled label="insufficient"><MetricCell variant="insufficient" label="Silent miss" /></Labeled>
        </Row>
      </Group>

      <Group label="Dropdown menu">
        <Labeled label="open"><DropdownMenu open focusIndex={0} /></Labeled>
      </Group>

      <Group label="Confirm dialog · empty state · error card">
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
          <Labeled label="confirm dialog" width={360}><ConfirmDialog inline /></Labeled>
          {(["no-document", "no-findings", "no-evidence"] as const).map((v) => (
            <Labeled key={v} label={`empty: ${v}`} width={280}><EmptyState variant={v} /></Labeled>
          ))}
          <Labeled label="error card" width={360}><ErrorCard /></Labeled>
        </div>
      </Group>

      <Divider />

      {/* ============================ ORGANISMS ============================ */}
      <SectionTitle id={sid("organisms")} sub="Whole regions of a screen, assembled from the molecules above.">
        04 Organisms
      </SectionTitle>

      <Group label="Brand mark">
        <Row>
          <Labeled label="logomark"><AnchorLogomark size={40} /></Labeled>
          <Labeled label="wordmark"><Wordmark /></Labeled>
          <Labeled label="horizontal lockup"><HorizontalLockup /></Labeled>
          <Labeled label="favicon 32"><Favicon size={32} /></Labeled>
          <Labeled label="favicon 16"><Favicon size={16} /></Labeled>
        </Row>
      </Group>

      <Group label="App header">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {(["default", "sample-mode", "mobile"] as const).map((v) => (
            <Labeled key={v} label={v} width="100%"><AppHeader variant={v} /></Labeled>
          ))}
        </div>
      </Group>

      <Group label="Reader toolbar">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {(["analyzing", "complete", "partial", "sample-mode"] as const).map((v) => (
            <Labeled key={v} label={v} width="100%"><ReaderToolbar variant={v} /></Labeled>
          ))}
        </div>
      </Group>

      <Group label="Category sidebar · 280px">
        <Row>
          {(["loading", "populated", "filtered-empty"] as const).map((st) => (
            <Labeled key={st} label={st}><CategorySidebar state={st} /></Labeled>
          ))}
        </Row>
      </Group>

      <Group label="Document block · the contract rendered as paper">
        <div style={{ display: "flex", flexDirection: "column", gap: 16, background: "var(--paper-sheet)", border: "1px solid var(--rule-default)", borderRadius: "var(--radius-md)", padding: 20, maxWidth: 640 }}>
          <DocumentBlock variant="heading" number="11" />
          <DocumentBlock variant="clause" number="11.3" />
          <DocumentBlock variant="sub-clause" number="(b)" />
          <DocumentBlock variant="definition" />
          <DocumentBlock variant="table" />
          <DocumentBlock variant="page-break" />
          <DocumentBlock variant="header-footer" />
        </div>
      </Group>

      <Group label="Performance table row">
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 640 }}>
          <Labeled label="strong" width="100%"><PerformanceTableRow category="Non-Compete" variant="strong" /></Labeled>
          <Labeled label="weak" width="100%"><PerformanceTableRow category="Exclusivity" variant="weak" /></Labeled>
          <Labeled label="not measured" width="100%"><PerformanceTableRow category="Insurance" variant="not-measured" /></Labeled>
        </div>
      </Group>

      <Group label="Mobile drawer · bottom sheet and left drawer">
        <Row>
          <Labeled label="bottom · peek"><MobileDrawer side="bottom" state="peek" /></Labeled>
          <Labeled label="bottom · open"><MobileDrawer side="bottom" state="open" /></Labeled>
          <Labeled label="left · open"><MobileDrawer side="left" state="open" /></Labeled>
          <Labeled label="closed"><MobileDrawer side="bottom" state="closed" /></Labeled>
        </Row>
      </Group>

      <Group label="App footer">
        <Labeled label="default" width="100%"><AppFooter /></Labeled>
      </Group>

      <Divider />

      {/* ========================= STATUS GALLERY ========================= */}
      <SectionTitle id={sid("status-gallery")} sub="One clause carried through all five statuses and all five polarities. Status is always icon plus text; polarity never stands alone.">
        05 Status gallery
      </SectionTitle>

      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{ padding: 8, textAlign: "left", color: "var(--ink-tertiary)", fontWeight: 600, fontFamily: "var(--font-mono)", fontSize: 11 }} />
              {polarities.map((p) => (
                <th key={p} style={{ padding: 8, textAlign: "left" }}>
                  <PolarityBadge polarity={p} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {statuses.map((s) => (
              <tr key={s}>
                <th style={{ padding: 8, textAlign: "left", verticalAlign: "top" }}>
                  <StatusChip status={s} size="s" />
                </th>
                {polarities.map((p) => (
                  <td
                    key={p}
                    style={{
                      padding: 8,
                      border: "1px solid var(--rule-default)",
                      background: "var(--paper-sheet)",
                      verticalAlign: "top",
                    }}
                  >
                    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 150 }}>
                      <span style={{ fontFamily: "var(--font-serif)", fontSize: 14, fontWeight: 600, color: "var(--ink-primary)" }}>
                        Non-compete
                      </span>
                      <StatusChip status={s} size="s" />
                      <PolarityBadge polarity={p} />
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-tertiary)" }}>
                        chars 4210 to 4488
                      </span>
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Divider />

      {/* ============================== VOICE ============================== */}
      <SectionTitle id={sid("voice")} sub="ClauseAnchor points to text. It never tells you what the law requires. The words safe, risky, void, clear and danger never appear in the interface.">
        06 Voice
      </SectionTitle>

      <Group label="Microcopy · say this, not that">
        <div style={{ display: "flex", flexDirection: "column", border: "1px solid var(--rule-default)", borderRadius: "var(--radius-md)", overflow: "hidden", maxWidth: 560 }}>
          {[
            ["Confirmed with confidence", "This clause is safe"],
            ["Needs a lawyer to read it", "This clause is risky"],
            ["Not confirmed at the validated threshold", "This clause is clear"],
            ["Points to Section 27, Indian Contract Act 1872", "This clause is void"],
            ["This is a technical issue, not a legal finding", "Something dangerous happened"],
          ].map(([good, bad], i) => (
            <div
              key={good}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                borderTop: i === 0 ? "none" : "1px solid var(--rule-default)",
              }}
            >
              <div style={{ padding: "10px 12px", fontSize: 13, color: "var(--ink-primary)", borderRight: "1px solid var(--rule-default)" }}>
                {good}
              </div>
              <div style={{ padding: "10px 12px", fontSize: 13, color: "var(--ink-tertiary)", textDecoration: "line-through" }}>
                {bad}
              </div>
            </div>
          ))}
        </div>
      </Group>

      <Group label="Fixed phrases · used verbatim wherever they appear">
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 560 }}>
          {[
            "ClauseAnchor points to text in your contract and in published judgments. It does not tell you what the law requires.",
            "Your contract is processed in memory and deleted within 60 minutes.",
            "ClauseAnchor could not confirm this clause with enough confidence. A lawyer should read it.",
            "This does not mean the contract has none, only that none was confirmed here.",
          ].map((phrase) => (
            <p
              key={phrase}
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: 15,
                lineHeight: "24px",
                color: "var(--ink-secondary)",
                borderLeft: "1px solid var(--rule-strong)",
                paddingLeft: 12,
              }}
            >
              {phrase}
            </p>
          ))}
        </div>
      </Group>
    </div>
  );
}

function ModeColumn({ mode }: { mode: Mode }) {
  return (
    <div
      className={mode === "dark" ? "dark" : "light"}
      style={{
        background: "var(--paper-base)",
        color: "var(--ink-primary)",
        padding: "32px 32px 80px",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--rule-default)",
      }}
    >
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--ink-tertiary)",
          marginBottom: 28,
          paddingBottom: 8,
          borderBottom: "1px solid var(--rule-default)",
        }}
      >
        {mode} mode
      </div>
      <Library mode={mode} />
    </div>
  );
}

export default function Gallery() {
  return (
    <div style={{ minHeight: "100vh", background: "var(--paper-base)" }}>
      {/* App header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "18px 32px",
          borderBottom: "1px solid var(--rule-default)",
          background: "var(--paper-sheet)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ color: "var(--anchor-600)" }}>
            <AnchorIcon size={26} />
          </span>
          <span style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 22, letterSpacing: "-0.01em", color: "var(--ink-primary)" }}>
            ClauseAnchor
          </span>
          <span style={{ fontSize: 13, color: "var(--ink-tertiary)", marginLeft: 8 }}>
            Component library · Marginalia v1.0
          </span>
        </div>
        <span style={{ fontSize: 13, color: "var(--ink-tertiary)" }}>Precise. Calm. Accountable.</span>
      </header>

      {/* Sticky table of contents */}
      <nav
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          display: "flex",
          flexWrap: "wrap",
          gap: 4,
          padding: "10px 32px",
          background: "var(--paper-sheet)",
          borderBottom: "1px solid var(--rule-default)",
        }}
      >
        {[
          ["Foundations", "foundations"],
          ["Atoms", "atoms"],
          ["Molecules", "molecules"],
          ["Organisms", "organisms"],
          ["Status gallery", "status-gallery"],
          ["Voice", "voice"],
          ["Layout and motion", "layout"],
        ].map(([label, id]) => (
          <a
            key={id}
            href={`#${id}`}
            onClick={(e) => {
              e.preventDefault();
              document.getElementById(id)?.scrollIntoView();
            }}
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: "var(--ink-secondary)",
              textDecoration: "none",
              padding: "6px 10px",
              borderRadius: "var(--radius-sm)",
              minHeight: 44,
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            {label}
          </a>
        ))}
      </nav>

      <main
        style={{
          maxWidth: 1600,
          margin: "0 auto",
          padding: 24,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(520px, 1fr))",
          gap: 24,
          alignItems: "start",
        }}
      >
        <ModeColumn mode="light" />
        <ModeColumn mode="dark" />
      </main>

      <LayoutAndMotion />

      <footer style={{ padding: "24px 32px", borderTop: "1px solid var(--rule-default)", color: "var(--ink-tertiary)", fontSize: 13 }}>
        Not legal advice. ClauseAnchor points to text in your contract and in published judgments. It does not tell you what the law requires.
      </footer>
    </div>
  );
}

/* The layout primitives, type tokens, motion tokens, reveal hook and disclosure at full
   page width. The margin grid follows the viewport, so it cannot sit in a half-width column. */
function LayoutAndMotion() {
  const [on, setOn] = useState(false);
  const reveal = useReveal<HTMLDivElement>();
  const durations = [
    ["--dur-press", "120 ms, hover and press"],
    ["--dur-state", "200 ms, a state change"],
    ["--dur-panel", "320 ms, panels, drawers, reveals"],
    ["--dur-ink", "400 ms, the ink-in sweep"],
  ] as const;
  return (
    <div id="layout" style={{ borderTop: "1px solid var(--rule-default)" }}>
      <Section
        labelledBy="layout-type"
        mark="§ 1"
        aside={
          <div style={{ border: "1px dashed var(--control-border)", borderRadius: "var(--radius-md)", padding: 16, background: "var(--paper-sheet)" }}>
            <p className="t-marginal-note">The aside column holds the component that a section explains.</p>
          </div>
        }
      >
        <div className="flow">
          <h2 id="layout-type" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 30, lineHeight: "38px" }}>Layout and type</h2>
          <p className="t-prose-lg">
            Margin, main and aside from 1280 px. Margin and main from 1024 px, with the aside under the main column. One column below.
          </p>
          <p className="t-display-xl" data-specimen="display-xl">Display, one idea per heading</p>
          <p className="t-overline" data-specimen="overline" style={{ color: "var(--ink-secondary)" }}>Overline, 12 px</p>
          <p className="t-marginal-note" data-specimen="marginal-note">A short note that sits in the margin.</p>
        </div>
      </Section>

      <Section labelledBy="layout-flow" mark="§ 2">
        <div className="flow" data-specimen="flow">
          <h2 id="layout-flow" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 24, lineHeight: "32px" }}>Heading spacing</h2>
          <p className="t-prose-lg">A heading is closer to what it introduces than to what precedes it.</p>
          <h2 style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 24, lineHeight: "32px" }}>A second heading</h2>
          <p className="t-prose-lg">Forty-eight pixels above, sixteen below.</p>
          <h3 style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 19, lineHeight: "28px" }}>A third-level heading</h3>
          <p className="t-prose-lg">Thirty-two above, twelve below.</p>
        </div>
      </Section>

      <Section labelledBy="layout-motion" mark="§ 3">
        <div className="flow">
          <h2 id="layout-motion" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 24, lineHeight: "32px" }}>Motion tokens</h2>
          <div>
            <Button variant="secondary" size="s" onClick={() => setOn((v) => !v)}>{on ? "Reset" : "Play"}</Button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {durations.map(([token, note]) => (
              <div key={token} style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, width: 240, color: "var(--ink-secondary)" }}>{token}: {note}</span>
                <span
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 2,
                    background: "var(--anchor-600)",
                    transform: on ? "translateX(160px)" : "none",
                    transition: `transform var(${token}) var(--ease-out)`,
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      </Section>

      <div style={{ height: 480 }} aria-hidden />

      <Section labelledBy="layout-reveal" mark="§ 4">
        <div className="flow">
          <h2 id="layout-reveal" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 24, lineHeight: "32px" }}>Scroll reveal and disclosure</h2>
          <div ref={reveal} data-specimen="reveal" style={{ border: "1px solid var(--rule-default)", borderRadius: "var(--radius-md)", background: "var(--paper-sheet)", padding: 16 }}>
            <p className="t-marginal-note">This block rose into view once. It rises at most 12 px, and it never hides under reduced motion.</p>
          </div>
          <div>
            <Disclosure summary="Is this legal advice?" open>
              No. ClauseAnchor points to text in your contract and in published judgments. It does not tell you what the law requires.
            </Disclosure>
            <Disclosure summary="What happens to my file?">
              Your contract is processed in memory and deleted within 60 minutes.
            </Disclosure>
          </div>
        </div>
      </Section>
    </div>
  );
}
