import { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { useNavigate, useParams } from "react-router";
import { client } from "../api/client";
import { ApiError, type Analysis, type Category, type Clause, type Document, type Job, type ManualReview, type Role } from "../api/types";
import { CATALOGUE, CATALOGUE_VERSION, CATEGORY_BY_ID, GROUP_ORDER } from "../api/catalogue";
import { buildOffsetIndex, sliceCp, toUtf16, type OffsetIndex } from "../lib/offsets";
import { authorityOf } from "../lib/authority";
import { freshDelays } from "../lib/reader";
import { panelTransition } from "../lib/panelTransition";
import { useMedia, useReducedMotion } from "../lib/useMedia";
import { useSession } from "../app/session";
import ReaderToolbar, { type ToolbarVariant } from "../components/ReaderToolbar";
import StageProgress, { type Step, type StepState } from "../components/StageProgress";
import CategorySidebar, { type SidebarGroup, type SidebarRow } from "../components/CategorySidebar";
import ClauseDetailPanel, { REVIEW_CANDIDATE_NOTE, type PanelData } from "../components/ClauseDetailPanel";
import MarginRuler, { type RulerMark } from "../components/MarginRuler";
import ScopePanel from "../components/ScopePanel";
import ManualReviewList, { type ManualItem } from "../components/ManualReviewList";
import NoticeBanner from "../components/NoticeBanner";
import ErrorCard from "../components/ErrorCard";
import ConfirmDialog from "../components/ConfirmDialog";
import DropdownMenu, { type MenuItem } from "../components/DropdownMenu";
import MobileDrawer from "../components/MobileDrawer";
import RuleFlagCard from "../components/RuleFlagCard";
import JudgmentCard from "../components/JudgmentCard";
import KeyboardHint from "../components/KeyboardHint";
import CountBadge from "../components/CountBadge";
import Button from "../components/Button";
import Skeleton from "../components/Skeleton";
import { markStyle, type SpanKind } from "../components/SpanHighlight";
import type { StatusKind } from "../components/StatusChip";
import { ChevronIcon, EmptyBracketIcon, ListIcon, PilcrowIcon, TrashIcon } from "../components/icons";

const POLL_MS = 700;

const STAGES: { key: string; label: string }[] = [
  { key: "reading", label: "Reading document" },
  { key: "finding_clauses", label: "Finding clauses" },
  { key: "checking_confidence", label: "Checking confidence" },
  { key: "law_review", label: "Indian law review" },
  { key: "case_law", label: "Finding case law" },
  { key: "final_checks", label: "Final checks" },
];

const ROLES: { role: Role; label: string; party: "party_company" | "party_provider" | null }[] = [
  { role: "buyer_customer", label: "Buyer or customer", party: "party_company" },
  { role: "supplier_vendor", label: "Supplier or vendor", party: "party_provider" },
  { role: "employer", label: "Employer", party: "party_company" },
  { role: "employee", label: "Employee", party: "party_provider" },
  { role: "licensor", label: "Licensor", party: "party_provider" },
  { role: "licensee", label: "Licensee", party: "party_company" },
  { role: "other", label: "Other", party: null },
];

const TERMINAL = new Set(["succeeded", "partial", "failed", "cancelled"]);

type Finding = { clause: Clause; categoryId: string; s16: number; e16: number; kind: SpanKind; status: StatusKind };
type Selection = { type: "category"; id: string; clause: number } | { type: "manual" } | null;
/* How a finding was chosen. A click cross-fades the panel and scrolls smoothly. A step with J or K is
   instant and keeps focus on the mark. Enter on a mark is instant and moves focus to the panel. */
type Pick = "pointer" | "step" | "activate";

function labelOf(id: string) {
  return CATEGORY_BY_ID[id]?.label ?? id;
}

function clauseStatus(c: Clause): StatusKind {
  if (c.status === "review_candidate") return "review";
  return c.confidence_band === "unvalidated" ? "unvalidated" : "found";
}

function categoryStatus(c: Category): StatusKind {
  if (c.status === "found") return c.clauses.some((k) => k.status === "accepted" && k.confidence_band !== "unvalidated") ? "found" : "unvalidated";
  if (c.status === "abstained") return "review";
  return c.status;
}

function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}

export default function Reader() {
  const { documentId = "" } = useParams();
  const navigate = useNavigate();
  const { token, docs, setDoc, forgetDoc, toast, mock, setMock } = useSession();
  const meta = docs[documentId];
  const reduced = useReducedMotion();
  const wide = useMedia("(min-width: 1440px)");
  const xl = useMedia("(min-width: 1280px)");
  const md = useMedia("(min-width: 768px)");

  const [doc, setDocument] = useState<Document | null>(null);
  const [index, setIndex] = useState<OffsetIndex | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [manual, setManual] = useState<ManualReview | null>(null);
  const [netError, setNetError] = useState(false);
  const [pollKey, setPollKey] = useState(0);
  const [selection, setSelection] = useState<Selection>(null);
  const [hoverKey, setHoverKey] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sheet, setSheet] = useState<"closed" | "peek" | "open">("closed");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const scroller = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const panelFocus = useRef(false);
  const seen = useRef(new Set<string>());

  const goExpired = useCallback(() => navigate("/expired?reason=expired", { replace: true, viewTransition: true }), [navigate]);

  const handleError = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && (e.code === "not_found" || e.code === "expired")) goExpired();
      else setNetError(true);
    },
    [goExpired]
  );

  /* Contract text is fetched once and kept in memory only. */
  useEffect(() => {
    if (!token || !meta?.analysisJobId) {
      goExpired();
      return;
    }
    let live = true;
    client
      .getDocument(token, documentId)
      .then((d) => {
        if (!live) return;
        setDocument(d);
        setIndex(buildOffsetIndex(d.source_text ?? ""));
      })
      .catch(handleError);
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, token]);

  /* Poll the job and the analysis until the job reaches a terminal state. */
  useEffect(() => {
    if (!token || !meta?.analysisJobId) return;
    const jobId = meta.analysisJobId;
    let live = true;
    let timer = 0;
    const tick = async () => {
      try {
        const [j, a] = await Promise.all([client.getJob(token, jobId), client.getAnalysis(token, documentId)]);
        if (!live) return;
        setNetError(false);
        setJob(j);
        setAnalysis(a);
        if (TERMINAL.has(j.status)) {
          const m = await client.getManualReview(token, documentId);
          if (live) setManual(m);
          return;
        }
        timer = window.setTimeout(tick, POLL_MS);
      } catch (e) {
        if (live) handleError(e);
      }
    };
    void tick();
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, token, meta?.analysisJobId, pollKey]);

  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 30000);
    return () => window.clearInterval(t);
  }, []);

  const text = doc?.source_text ?? "";
  const finished = !!job && TERMINAL.has(job.status);
  const catMap = useMemo(() => new Map((analysis?.categories ?? []).map((c) => [c.category_id, c])), [analysis]);

  const findings: Finding[] = useMemo(() => {
    if (!index) return [];
    const out: Finding[] = [];
    for (const c of analysis?.categories ?? []) {
      for (const k of c.clauses) {
        const status = clauseStatus(k);
        out.push({
          clause: k,
          categoryId: c.category_id,
          s16: toUtf16(index, k.span.start),
          e16: toUtf16(index, k.span.end),
          kind: status === "review" ? "review" : "found",
          status,
        });
      }
    }
    return out.sort((a, b) => a.s16 - b.s16 || b.e16 - a.e16);
  }, [analysis, index]);

  const selectedFinding = useMemo(() => {
    if (selection?.type !== "category") return null;
    const cat = catMap.get(selection.id);
    const clause = cat?.clauses[selection.clause];
    return clause ? findings.find((f) => f.clause.id === clause.id) ?? null : null;
  }, [selection, catMap, findings]);

  const reveal = useCallback(
    (el: HTMLElement | null, opts: { smooth?: boolean; focus?: boolean } = {}) => {
      if (!el) return;
      el.scrollIntoView({ block: "center", behavior: opts.smooth && !reduced ? "smooth" : "auto" });
      if (opts.focus) el.focus({ preventScroll: true });
    },
    [reduced]
  );

  /* Only a pointer choice cross-fades the panel, and only while a panel is on screen. */
  const choose = useCallback(
    (next: Selection, how: Pick) => {
      panelTransition(
        () => {
          setSelection(next);
          setSheet((s) => (s === "open" ? s : "peek"));
          setSidebarOpen(false);
        },
        how === "pointer" && !reduced && (xl || sheet !== "closed")
      );
      if (how === "activate") panelFocus.current = true;
    },
    [reduced, xl, sheet]
  );

  const selectCategory = useCallback(
    (id: string, clause = 0, how: Pick = "pointer") => {
      choose({ type: "category", id, clause }, how);
      const k = catMap.get(id)?.clauses[clause];
      if (k) reveal(document.getElementById(`f-${k.id}`), { smooth: how === "pointer" });
    },
    [catMap, choose, reveal]
  );

  const selectFinding = useCallback(
    (f: Finding, how: Pick) => {
      const cat = catMap.get(f.categoryId);
      const idx = cat ? cat.clauses.findIndex((c) => c.id === f.clause.id) : 0;
      choose({ type: "category", id: f.categoryId, clause: Math.max(0, idx) }, how);
      reveal(document.getElementById(`f-${f.clause.id}`), { smooth: how === "pointer", focus: how === "step" });
    },
    [catMap, choose, reveal]
  );

  /* One identity for the life of the page, so the text blocks that a pick does not touch are not rendered again. */
  const selectRef = useRef(selectFinding);
  selectRef.current = selectFinding;
  const pickFinding = useCallback((f: Finding, how: Pick) => selectRef.current(f, how), []);

  const openManual = useCallback(() => {
    choose({ type: "manual" }, "pointer");
    setSheet("open");
  }, [choose]);

  /* After an Enter on a mark the panel title takes focus, once the panel has rendered. */
  useEffect(() => {
    if (!panelFocus.current) return;
    panelFocus.current = false;
    document.getElementById("detail-panel-title")?.focus({ preventScroll: true });
  }, [selection, sheet]);

  /* A reload ends the session and the text with it, so the browser asks first. It shows its own prompt. */
  const open = !!meta;
  useEffect(() => {
    if (!open) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [open]);

  /* Reader keys: J and K step through findings, Escape closes the detail. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "Escape") {
        if (confirmDelete) return;
        setSelection(null);
        setSheet("closed");
        setSidebarOpen(false);
        return;
      }
      const k = e.key.toLowerCase();
      if ((k === "j" || k === "k") && findings.length) {
        e.preventDefault();
        const cur = selectedFinding ? findings.indexOf(selectedFinding) : -1;
        const next = k === "j" ? (cur + 1) % findings.length : cur <= 0 ? findings.length - 1 : cur - 1;
        selectFinding(findings[next], "step");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [findings, selectedFinding, selectFinding, confirmDelete]);

  /* Margin ruler positions come from the rendered marks, so they follow wrapping. */
  const [marks, setMarks] = useState<(RulerMark & { id: string })[]>([]);
  const [viewport, setViewport] = useState({ top: 0, size: 1, h: 480 });
  const measure = useCallback(() => {
    const sc = scroller.current;
    if (!sc) return;
    const total = sc.scrollHeight || 1;
    const base = sc.getBoundingClientRect().top - sc.scrollTop;
    const seen = new Set<string>();
    const next: (RulerMark & { id: string })[] = [];
    for (const f of findings) {
      if (seen.has(f.categoryId)) continue;
      const el = document.getElementById(`f-${f.clause.id}`);
      if (!el) continue;
      seen.add(f.categoryId);
      const at = (el.getBoundingClientRect().top - base) / total;
      next.push({ id: f.clause.id, at: Math.min(0.99, Math.max(0.01, at)), status: f.status, label: labelOf(f.categoryId) });
    }
    // A scroll event changes the viewport box and almost never the marks. Equal values keep the old state, so React skips the render.
    setMarks((prev) => (prev.length === next.length && prev.every((m, i) => m.id === next[i].id && m.at === next[i].at && m.status === next[i].status) ? prev : next));
    const top = sc.scrollTop / total;
    const size = Math.min(1, sc.clientHeight / total);
    const h = Math.max(160, sc.clientHeight - 48);
    setViewport((v) => (v.top === top && v.size === size && v.h === h ? v : { top, size, h }));
  }, [findings]);

  /* The strip follows the pane: a resize, a panel opening or the text reflowing all re-measure it. */
  useLayoutEffect(() => {
    measure();
    const ro = new ResizeObserver(measure);
    if (scroller.current) ro.observe(scroller.current);
    if (content.current) ro.observe(content.current);
    return () => ro.disconnect();
  }, [measure]);

  /* Rows that resolve while the review runs enter with a short stagger. A finished or reopened review draws every row at once. */
  const fresh = useMemo(() => (finished ? new Map<string, number>() : freshDelays(seen.current, catMap.keys())), [catMap, finished]);
  useEffect(() => {
    catMap.forEach((_, id) => seen.current.add(id));
  }, [catMap]);

  /* Sidebar groups, with skeleton rows for categories still being checked. */
  const groups: SidebarGroup[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    return GROUP_ORDER.map((g) => {
      const rows: SidebarRow[] = CATALOGUE.filter((c) => c.group === g).map((c) => {
        const cat = catMap.get(c.id);
        if (!cat) return { id: c.id, name: c.label, status: finished ? "unavailable" : "absent", pending: !finished };
        const status = categoryStatus(cat);
        return { id: c.id, name: c.label, status, count: cat.clauses.length || undefined, enterStep: fresh.get(c.id) };
      });
      const shown = rows.filter((r) => {
        if (q && !r.name.toLowerCase().includes(q)) return false;
        if (filter === "Found") return r.status === "found" || r.status === "unvalidated";
        if (filter === "Needs a lawyer") return r.status === "review";
        if (filter === "Not found") return r.status === "absent" && !r.pending;
        return true;
      });
      const f = rows.filter((r) => !r.pending && (r.status === "found" || r.status === "unvalidated")).length;
      const rv = rows.filter((r) => !r.pending && r.status === "review").length;
      const parts = [`${f} found`];
      if (rv) parts.push(`${rv} ${rv === 1 ? "needs" : "need"} a lawyer`);
      const pend = rows.filter((r) => r.pending).length;
      if (pend) parts.push(`${pend} in progress`);
      return { label: g, summary: parts.join(", "), rows: shown };
    }).filter((g) => g.rows.length > 0);
  }, [catMap, query, filter, finished, fresh]);

  const counts = useMemo(() => {
    const c = { found: 0, review: 0, absent: 0, unvalidated: 0, unavailable: 0 };
    for (const cat of analysis?.categories ?? []) c[categoryStatus(cat)]++;
    return c;
  }, [analysis]);
  const summary = `${CATALOGUE.length} categories: ${counts.found} found, ${counts.review} need a lawyer, ${counts.absent} not found, ${counts.unvalidated} not validated${counts.unavailable ? `, ${counts.unavailable} unavailable` : ""}`;

  const unavailableNames = (analysis?.categories ?? []).filter((c) => c.status === "unavailable").map((c) => labelOf(c.category_id));

  /* Manual review items, with partial highlights mapped into each preview. */
  const manualItems: ManualItem[] = useMemo(() => {
    if (!manual || !index) return [];
    return manual.units
      .filter((u) => u.overlap !== "full")
      .map((u) => {
        const a16 = toUtf16(index, u.start);
        const b16 = toUtf16(index, u.end);
        const m: [number, number][] = findings
          .filter((f) => f.e16 > a16 && f.s16 < b16)
          .map((f) => [Math.max(0, f.s16 - a16), Math.min(b16, f.e16) - a16]);
        return {
          id: u.id,
          sectionPath: u.section_path,
          text: sliceCp(text, index, u.start, u.end),
          start: u.start,
          end: u.end,
          variant: u.unavailable ? "unavailable" : u.overlap === "partial" ? "partial" : "none",
          marks: m,
        };
      });
  }, [manual, index, findings, text]);

  const sectionFor = useCallback(
    (cp: number) => manual?.units.find((u) => cp >= u.start && cp < u.end)?.section_path ?? null,
    [manual]
  );

  async function changeRole(r: (typeof ROLES)[number]) {
    if (!token) return;
    try {
      const party = r.party ?? meta?.partyNodeId ?? null;
      await client.setParty(token, documentId, { role: r.role, party_node_id: party });
      setDoc(documentId, { role: r.role, partyNodeId: party });
      setAnalysis(await client.getAnalysis(token, documentId));
      toast("success", "Your role was updated");
    } catch (e) {
      handleError(e);
    }
  }

  async function download() {
    if (!token) return;
    try {
      const blob = await client.downloadReport(token, documentId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(doc?.filename ?? "contract").replace(/\.[a-z]+$/i, "")}-review.pdf`;
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast("success", "Report downloaded");
    } catch {
      toast("error", "The report could not be downloaded. Try again.");
    }
  }

  async function remove() {
    if (!token) return;
    try {
      await client.deleteDocument(token, documentId);
      forgetDoc(documentId);
      navigate("/expired?reason=deleted", { replace: true, viewTransition: true });
    } catch {
      setConfirmDelete(false);
      toast("error", "The contract could not be deleted. Try again.");
    }
  }

  async function cancel() {
    if (!token || !meta?.analysisJobId) return;
    try {
      await client.cancelJob(token, meta.analysisJobId);
      setPollKey((k) => k + 1);
    } catch (e) {
      handleError(e);
    }
  }

  async function retryAnalysis() {
    if (!token) return;
    if (mock?.failAnalysis) setMock({ failAnalysis: false });
    try {
      const j = await client.startAnalysis(token, documentId, { jurisdiction_scope: analysis?.jurisdiction_scope ?? "india_review" });
      setManual(null);
      setDoc(documentId, { analysisJobId: j.id });
      setPollKey((k) => k + 1);
    } catch (e) {
      handleError(e);
    }
  }

  /* The band above the sheet: progress while the review runs, then a notice that stays. A partial read
     never shows the zero-findings line, because nothing found in text that was not read is no finding. */
  const parserWarning = !!doc && doc.warnings.length > 0;
  const noFindings = !!index && finished && job?.status === "succeeded" && !!analysis?.processing_complete && findings.length === 0 && !parserWarning;

  /* Detail panel content for the current selection. */
  const panel: ReactNode = (() => {
    const fill = !xl;
    if (selection?.type === "manual") {
      return (
        <ClauseDetailPanel
          fill={fill}
          onClose={() => setSelection(null)}
          custom={{
            title: "Manual review",
            content: (
              <ManualReviewList
                state={!manual ? "loading" : manual.status === "processing_incomplete" ? "processing-incomplete" : manualItems.length ? "populated" : "empty"}
                items={manualItems}
                onGo={(id) => {
                  setSheet("peek");
                  reveal(document.getElementById(`unit-${id}`), { smooth: true, focus: true });
                }}
                onReadFull={() => scroller.current?.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" })}
              />
            ),
          }}
        />
      );
    }
    if (selection?.type === "category") {
      const cat = catMap.get(selection.id);
      const title = labelOf(selection.id);
      if (!cat) {
        if (finished) {
          return <ClauseDetailPanel fill={fill} onClose={() => setSelection(null)} data={{ title, status: "unavailable", emptyTitle: "This part of the review did not finish", emptyBody: "This category was not reached before the review stopped." }} />;
        }
        return <ClauseDetailPanel variant="loading" fill={fill} onClose={() => setSelection(null)} />;
      }
      const clause = cat.clauses[selection.clause] ?? cat.clauses[0];
      let data: PanelData;
      if (cat.status === "unavailable") {
        data = {
          title,
          status: "unavailable",
          emptyTitle: "This part of the review did not finish",
          emptyBody: "Some passages for this category were not checked. Read the agreement for it yourself, or ask a lawyer.",
          onRetry: finished ? retryAnalysis : undefined,
        };
      } else if (cat.status === "absent") {
        data = { title, status: "absent", emptyTitle: "No clause found at the validated threshold", emptyBody: "This category was checked. Nothing was confirmed here." };
      } else if (!clause) {
        data = {
          title,
          status: "review",
          emptyTitle: "Needs a lawyer",
          emptyBody: "The review could not settle whether this clause is in the agreement. There is no single passage to point to. Ask a lawyer to read for it.",
        };
      } else {
        const status = clauseStatus(clause);
        const quote = index ? sliceCp(text, index, clause.span.start, clause.span.end) : clause.span.text;
        data = {
          title,
          status,
          sectionPath: sectionFor(clause.span.start),
          offsets: { start: clause.span.start, end: clause.span.end },
          quote,
          polarity: clause.polarity,
          confidence: clause.confidence_band,
          calibration: clause.calibration_scope === "category" || clause.calibration_scope === "pooled" ? clause.calibration_scope : undefined,
          reviewNote: clause.status === "review_candidate" ? REVIEW_CANDIDATE_NOTE : undefined,
          ruleFlags: clause.rule_flags.length ? (
            <div className="flex flex-col gap-2">
              {clause.rule_flags.map((f) => (
                <RuleFlagCard key={f.rule_id} variant={f.scope_status === "verify" ? "verify" : "standard"} citation={f.statute_citations.join("; ")} note={f.note} />
              ))}
            </div>
          ) : undefined,
          caseLaw: (
            <div className="flex flex-col gap-2">
              {clause.passages.length ? (
                clause.passages.map((p) => (
                  <JudgmentCard
                    key={p.id}
                    authority={authorityOf(p.authority_status)}
                    passage={{ caseName: p.case_name, court: p.court, year: p.year, citation: p.citation, text: p.text, sourceUrl: p.source_url }}
                  />
                ))
              ) : (
                <JudgmentCard state="empty" />
              )}
            </div>
          ),
          caseLawCount: clause.passages.length,
          pager:
            cat.clauses.length > 1 ? (
              <Pager
                index={selection.clause}
                total={cat.clauses.length}
                onGo={(i) => selectCategory(cat.category_id, i)}
              />
            ) : undefined,
        };
      }
      return <ClauseDetailPanel key={clause?.id ?? selection.id} fill={fill} data={data} onClose={() => { setSelection(null); setSheet("closed"); }} />;
    }
    return (
      <ClauseDetailPanel
        fill={fill}
        custom={{
          title: "Nothing selected",
          content: (
            <div className="flex flex-col gap-3 text-[14px] leading-[22px]" style={{ color: "var(--ink-secondary)" }}>
              <p>Choose a highlighted passage or a category to see the exact wording, which side it favours, and any case law.</p>
              {noFindings ? (
                <div>
                  <Button variant="secondary" size="s" onClick={openManual}>
                    Open the manual review list
                  </Button>
                </div>
              ) : findings.length > 0 ? (
                <div>
                  <Button variant="secondary" size="s" onClick={() => selectFinding(findings[0], "activate")}>
                    Read the first finding
                  </Button>
                </div>
              ) : null}
              <p className="flex flex-wrap items-center gap-2">
                <KeyboardHint keys={["J"]} /> next finding <KeyboardHint keys={["K"]} /> previous <KeyboardHint keys={["Esc"]} /> close
              </p>
            </div>
          ),
        }}
      />
    );
  })();

  const sidebar = (
    <CategorySidebar
      fill
      state={!analysis ? "loading" : groups.length ? "populated" : "filtered-empty"}
      groups={groups}
      summary={analysis ? summary : "Checking categories"}
      selected={selection?.type === "category" ? selection.id : null}
      onSelect={(r) => r.id && selectCategory(r.id)}
      query={query}
      onQuery={setQuery}
      filter={filter}
      onFilter={setFilter}
      top={
        <ScopePanel
          variant={analysis?.mode === "sample" ? "sample-mode" : finished && analysis && !analysis.processing_complete ? "processing-incomplete" : "complete"}
          categoryCount={CATALOGUE.length}
          catalogueVersion={analysis?.catalogue_version ?? CATALOGUE_VERSION}
          limitations={unavailableNames.length ? [`Unavailable: ${unavailableNames.join(", ")}`] : []}
          onViewList={() => setFilter("All")}
        />
      }
      footer={
        <button
          type="button"
          onClick={openManual}
          aria-pressed={selection?.type === "manual"}
          className="flex w-full items-center gap-2 text-left"
          style={{
            minHeight: 44,
            padding: "8px 12px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--rule-default)",
            background: selection?.type === "manual" ? "var(--anchor-50)" : "var(--paper-sheet)",
            color: "var(--ink-primary)",
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          <PilcrowIcon size={16} />
          <span className="flex-1">Manual review</span>
          {manual ? <CountBadge count={manualItems.length} /> : <span className="font-mono text-[12px]" style={{ color: "var(--ink-tertiary)" }}>after review</span>}
        </button>
      }
    />
  );

  /* Steps for the compact progress readout. */
  const steps: Step[] = STAGES.map((s, i) => {
    const cur = job?.stage ? STAGES.findIndex((x) => x.key === job.stage) : job && TERMINAL.has(job.status) ? STAGES.length : 0;
    let state: StepState = i < cur ? "done" : i === cur ? "active" : "pending";
    if (job?.status === "failed" && i === cur) state = "failed";
    const detail =
      i === cur && job?.total_units
        ? s.key === "finding_clauses"
          ? `${analysis?.categories.length ?? 0} of ${CATALOGUE.length} categories`
          : `${job.completed_units} of ${job.total_units}`
        : undefined;
    return { label: s.label, state, detail };
  });

  const variant: ToolbarVariant = !finished
    ? "analyzing"
    : job?.status === "partial" || job?.status === "cancelled" || job?.status === "failed"
      ? "partial"
      : analysis?.mode === "sample"
        ? "sample-mode"
        : "complete";

  const partialNote =
    job?.status === "cancelled"
      ? "You stopped the review. Categories not reached are listed as Unavailable."
      : job?.status === "failed"
        ? "The review stopped early. Categories not reached are listed as Unavailable."
        : unavailableNames.length
          ? `Partial result. Not finished: ${unavailableNames.join(", ")}.`
          : undefined;

  const roleItems: MenuItem[] = ROLES.map((r) => ({ label: r.label, checked: meta?.role === r.role, onSelect: () => void changeRole(r) }));
  // On a phone Delete leaves the toolbar, so Download report keeps its line, and joins the role list.
  if (!md) roleItems.push({ label: "Delete document", icon: <TrashIcon size={16} />, onSelect: () => setConfirmDelete(true) });
  const pages = doc ? Math.max(1, ...doc.nodes.map((n) => n.page)) : 0;
  const minutesLeft = doc ? (new Date(doc.expires_at).getTime() - now) / 60000 : Infinity;

  /* The bottom sheet stays mounted, so it can slide out. While it leaves it still holds the panel it showed. */
  const held = useRef<{ node: ReactNode; title: string; open: boolean } | null>(null);
  // A ref written in render is harmless to repeat. A state copy would cost a second render per pick.
  if (selection) held.current = { node: panel, title: selection.type === "manual" ? "Manual review" : labelOf(selection.id), open: sheet === "open" };
  const sheetBody = held.current ?? { node: panel, title: "Detail", open: false };
  const sheetState = selection && sheet !== "closed" ? sheet : "closed";

  if (!token || !meta) return null;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <title>Review | ClauseAnchor</title>
      <h1 className="sr-only">Contract review</h1>

      {/* The page is inert while the categories drawer is open, so Tab stays inside the drawer. */}
      <div className="flex min-h-0 flex-1 flex-col" inert={sidebarOpen}>
        <ReaderToolbar
          variant={variant}
          filename={doc?.filename ?? "Loading"}
          meta={doc ? `${plural(pages, "page", "pages")}, ${CATALOGUE.length} categories` : ""}
          progress={null}
          partialNote={partialNote}
          showDelete={md}
          leading={
            !xl ? (
              <Button
                id="open-categories"
                variant="secondary"
                size="s"
                icon="icon-only"
                iconNode={<ListIcon size={16} />}
                aria-label="Show categories"
                aria-expanded={sidebarOpen}
                onClick={() => setSidebarOpen(true)}
              />
            ) : undefined
          }
          menu={<DropdownMenu label={md ? "Change your role" : "More actions"} items={roleItems} />}
          onDownload={download}
          onDelete={() => setConfirmDelete(true)}
        />

        {(minutesLeft <= 10 || netError || job?.status === "failed") && (
          <div className="flex flex-col gap-2 px-4 py-3" style={{ borderBottom: "1px solid var(--rule-default)", background: "var(--paper-base)" }}>
            {minutesLeft <= 10 && <NoticeBanner variant="session-expiry" onAction={download} />}
            {netError && (
              <ErrorCard
                message="Could not reach the server. Your contract is still open here."
                code="ERR_NETWORK"
                onRetry={() => {
                  setNetError(false);
                  setPollKey((k) => k + 1);
                }}
              />
            )}
            {job?.status === "failed" && (
              <ErrorCard
                title="The analysis did not finish"
                message="The review stopped partway. Findings already checked are shown. Run it again to check the rest."
                code="ANALYSIS_FAILED"
                onRetry={retryAnalysis}
              />
            )}
          </div>
        )}

        <div className="flex min-h-0 flex-1">
          {/* From 1440 the category list is docked. From 1280 a 64 px rail opens it as a drawer. */}
          {wide && (
            <div className="w-[264px] shrink-0 overflow-hidden" style={{ borderRight: "1px solid var(--rule-default)" }}>
              {sidebar}
            </div>
          )}
          {xl && !wide && (
            <nav aria-label="Reader" className="flex w-16 shrink-0 flex-col items-stretch pt-3" style={{ borderRight: "1px solid var(--rule-default)", background: "var(--paper-sunken)" }}>
              <button
                id="open-categories"
                type="button"
                aria-expanded={sidebarOpen}
                onClick={() => setSidebarOpen(true)}
                className="focus-inset flex min-h-[56px] flex-col items-center justify-center gap-1 py-2"
                style={{ color: "var(--ink-secondary)", background: "transparent", border: "none", cursor: "pointer" }}
              >
                <ListIcon size={20} />
                <span style={{ fontSize: 12, lineHeight: "16px" }}>Categories</span>
              </button>
            </nav>
          )}

          <div
            ref={scroller}
            onScroll={measure}
            className="scroll-pane min-w-0 flex-1 overflow-y-auto"
            style={{ background: "var(--paper-sunken)", paddingBottom: !xl && sheetState !== "closed" ? 160 : 0 }}
          >
            <div ref={content} className="mx-auto flex w-full flex-col items-center px-3 py-6 md:px-4 md:py-10">
              {/* Above the sheet. The progress band goes when the review ends, and scroll anchoring keeps the text still. */}
              {(!finished || parserWarning || noFindings) && (
                <div className="mb-3 flex w-full justify-center gap-3">
                  <div className="reader-sheet flex min-w-0 flex-col gap-2">
                    {!finished && (
                      <div
                        className="flex min-h-[44px] items-center px-3"
                        style={{ background: "var(--paper-sheet)", border: "1px solid var(--rule-default)", borderRadius: "var(--radius-md)" }}
                      >
                        <StageProgress compact steps={steps} onCancel={cancel} />
                      </div>
                    )}
                    {parserWarning && <NoticeBanner variant="read-partial" />}
                    {noFindings && (
                      <p className="flex items-center gap-2 px-1 text-[14px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
                        <EmptyBracketIcon size={16} />
                        {CATALOGUE.length} categories reviewed. No clause found at the validated threshold.
                      </p>
                    )}
                  </div>
                  {/* The width of the margin ruler beside the sheet, so the band and the sheet share a left edge. */}
                  {md && <div aria-hidden className="w-7 shrink-0" />}
                </div>
              )}

              <div className="flex w-full justify-center gap-3">
                <article
                  aria-label="Contract text"
                  className="reader-sheet min-w-0"
                  style={{
                    background: "var(--paper-sheet)",
                    border: "1px solid var(--rule-default)",
                    borderRadius: "var(--radius-sm)",
                    boxShadow: "var(--elevation-1)",
                    padding: md ? "56px 48px" : "28px 20px",
                  }}
                >
                  <div style={{ maxWidth: "var(--measure)", marginInline: "auto" }}>
                    {doc && index ? (
                      <DocumentText
                        doc={doc}
                        index={index}
                        findings={findings}
                        inkSteps={fresh}
                        selectedId={selectedFinding?.clause.id ?? null}
                        hoverId={hoverKey}
                        onHover={setHoverKey}
                        onPick={pickFinding}
                      />
                    ) : (
                      <div className="flex flex-col gap-4" aria-busy="true">
                        <span className="sr-only">Loading the contract</span>
                        {Array.from({ length: 8 }, (_, i) => (
                          <Skeleton key={i} />
                        ))}
                      </div>
                    )}
                  </div>
                </article>
                {md && (
                  <div className="sticky top-6 shrink-0 self-start" style={{ height: viewport.h }}>
                    <MarginRuler
                      height="100%"
                      marks={marks}
                      selected={selectedFinding ? marks.findIndex((m) => m.label === labelOf(selectedFinding.categoryId)) : null}
                      viewport={viewport}
                      caption="Findings"
                      onSelect={(i) => {
                        const f = findings.find((x) => x.clause.id === marks[i]?.id);
                        if (f) selectFinding(f, "pointer");
                      }}
                    />
                  </div>
                )}
              </div>

              <p className="mt-4 hidden flex-wrap items-center justify-center gap-2 text-[13px] lg:flex" style={{ color: "var(--ink-tertiary)" }}>
                <KeyboardHint keys={["J"]} /> next finding <KeyboardHint keys={["K"]} /> previous <KeyboardHint keys={["Esc"]} /> close
              </p>
            </div>
          </div>

          {xl && (
            <div
              className="scroll-pane shrink-0 overflow-y-auto"
              style={{ width: wide ? 384 : 360, borderLeft: "1px solid var(--rule-default)", background: "var(--paper-base)" }}
            >
              <div className="reader-panel">{panel}</div>
            </div>
          )}
        </div>
      </div>

      {!wide && (
        <MobileDrawer
          fixed
          framed={false}
          side="left"
          state={sidebarOpen ? "open" : "closed"}
          title="Categories"
          size={Math.min(320, typeof window === "undefined" ? 320 : window.innerWidth - 40)}
          onBackdrop={() => setSidebarOpen(false)}
          actions={<Button variant="tertiary" size="s" onClick={() => setSidebarOpen(false)}>Close</Button>}
        >
          {sidebar}
        </MobileDrawer>
      )}

      {!xl && (
        <MobileDrawer
          fixed
          framed={false}
          side="bottom"
          state={sheetState}
          title={sheetBody.title}
          size="78dvh"
          actions={
            <Button variant="tertiary" size="s" onClick={() => setSheet(sheet === "peek" ? "open" : "peek")}>
              {sheetBody.open ? "Peek" : "Open"}
            </Button>
          }
        >
          <div className="reader-panel">{sheetBody.node}</div>
        </MobileDrawer>
      )}

      {confirmDelete && (
        <ConfirmDialog
          title="Delete this contract?"
          body="The contract, its text and this review are removed from the server now. This cannot be undone."
          confirmLabel="Delete contract"
          cancelLabel="Keep it"
          onConfirm={remove}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </div>
  );
}

function Pager({ index, total, onGo }: { index: number; total: number; onGo: (i: number) => void }) {
  return (
    <div className="flex items-center gap-2" style={{ fontSize: 13, color: "var(--ink-secondary)" }}>
      <Button variant="tertiary" size="s" state={index === 0 ? "disabled" : undefined} onClick={() => onGo(index - 1)} aria-label="Previous passage">
        <span style={{ display: "inline-flex", transform: "rotate(180deg)" }}><ChevronIcon size={16} /></span>
      </Button>
      <span className="font-mono">
        Passage {index + 1} of {total}
      </span>
      <Button variant="tertiary" size="s" state={index >= total - 1 ? "disabled" : undefined} onClick={() => onGo(index + 1)} aria-label="Next passage">
        <ChevronIcon size={16} />
      </Button>
    </div>
  );
}

type TextBlockProps = {
  blk: { id: string; kind: string; a: number; b: number };
  bi: number;
  text: string;
  /** The findings that touch this block. */
  inside: Finding[];
  /** The findings whose first piece of text is in this block. Their id sits on that piece. */
  first: Set<string>;
  inkSteps: Map<string, number>;
  /** Null unless the selected or hovered finding touches this block, so no other block is rendered again. */
  selectedId: string | null;
  hoverId: string | null;
  onHover: (id: string | null) => void;
  onPick: (f: Finding, how: Pick) => void;
};

/* Contract text as escaped text nodes, split at every finding boundary so overlaps stack. */
const DocumentText = memo(function DocumentText({
  doc,
  index,
  findings,
  inkSteps,
  selectedId,
  hoverId,
  onHover,
  onPick,
}: {
  doc: Document;
  index: OffsetIndex;
  findings: Finding[];
  /** Stagger steps for categories that resolved while the review ran, keyed by category id. */
  inkSteps: Map<string, number>;
  selectedId: string | null;
  hoverId: string | null;
  onHover: (id: string | null) => void;
  onPick: (f: Finding, how: Pick) => void;
}) {
  const text = doc.source_text ?? "";
  const blocks = useMemo(
    () =>
      doc.nodes
        .filter((n) => n.kind !== "party")
        .sort((a, b) => a.start - b.start)
        .map((n) => ({ id: n.id.replace(/^n_/, ""), kind: n.kind, a: toUtf16(index, n.start), b: toUtf16(index, n.end) })),
    [doc, index]
  );
  /* Which findings touch each block, worked out once per set of findings. A selection or a hover then renders
     only the blocks it touches, not every paragraph of a long contract. */
  const plan = useMemo(() => {
    const seen = new Set<string>();
    return blocks.map((blk, bi) => {
      const inside = findings.filter((f) => f.e16 > blk.a && f.s16 < blk.b);
      const first = new Set<string>();
      for (const f of inside) {
        if (f.s16 >= blk.a && !seen.has(f.clause.id)) {
          seen.add(f.clause.id);
          first.add(f.clause.id);
        }
      }
      return { blk, bi, inside, first };
    });
  }, [blocks, findings]);

  return (
    <div style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: "30px", color: "var(--ink-primary)" }}>
      {plan.map((p) => (
        <TextBlock
          key={p.blk.id}
          {...p}
          text={text}
          inkSteps={inkSteps}
          selectedId={p.inside.some((f) => f.clause.id === selectedId) ? selectedId : null}
          hoverId={p.inside.some((f) => f.clause.id === hoverId) ? hoverId : null}
          onHover={onHover}
          onPick={onPick}
        />
      ))}
    </div>
  );
});

const TextBlock = memo(function TextBlock({ blk, bi, text, inside, first, inkSteps, selectedId, hoverId, onHover, onPick }: TextBlockProps) {
  const cuts = new Set<number>([blk.a, blk.b]);
  for (const f of inside) {
    cuts.add(Math.max(blk.a, f.s16));
    cuts.add(Math.min(blk.b, f.e16));
  }
  const pts = [...cuts].sort((x, y) => x - y);
  const nodes: ReactNode[] = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    const piece = text.slice(a, b);
    const active = inside.filter((f) => f.s16 <= a && f.e16 >= b);
    if (!active.length) {
      nodes.push(<span key={a}>{piece}</span>);
      continue;
    }
    const sel = active.find((f) => f.clause.id === selectedId);
    const hovered = active.some((f) => f.clause.id === hoverId);
    const kind: SpanKind = sel ? "focused" : active.length >= 3 ? "overlap3" : active.length === 2 ? "overlap2" : active[0].kind;
    /* The innermost finding owns clicks on stacked text. */
    const owner = [...active].sort((x, y) => x.e16 - x.s16 - (y.e16 - y.s16))[0];
    const starts = active.filter((f) => f.s16 === a && first.has(f.clause.id));
    const anchor = starts[0];
    const openBracket = sel && sel.s16 === a;
    const closeBracket = sel && sel.e16 === b;
    nodes.push(
      <span key={a}>
        {starts.slice(1).map((f) => (
          <span key={f.clause.id} id={`f-${f.clause.id}`} tabIndex={-1} />
        ))}
        {openBracket && <Bracket>⟦</Bracket>}
        <span
          id={anchor ? `f-${anchor.clause.id}` : undefined}
          tabIndex={anchor ? 0 : undefined}
          role={anchor ? "button" : undefined}
          aria-label={anchor ? `${labelOf(anchor.categoryId)}, ${anchor.status === "review" ? "needs a lawyer" : "found"}${active.length > 1 ? `, overlaps ${active.length - 1} other` : ""}` : undefined}
          aria-pressed={anchor ? !!sel : undefined}
          onClick={() => onPick(owner, "pointer")}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onPick(anchor ?? owner, "activate");
            }
          }}
          onMouseEnter={() => onHover(owner.clause.id)}
          onMouseLeave={() => onHover(null)}
          // One finding on its own text inks in when it first draws. The class stays when it is selected, so a
          // selection never replays the sweep.
          className={active.length === 1 ? "ca-mark ca-ink cursor-pointer" : "ca-mark cursor-pointer"}
          style={
            {
              ...markStyle(kind, hovered && !sel),
              borderRadius: 1,
              "--ink-delay": `calc(${inkSteps.get(active[0].categoryId) ?? 0} * var(--stagger))`,
            } as CSSProperties
          }
        >
          {piece}
        </span>
        {closeBracket && <Bracket>⟧</Bracket>}
      </span>
    );
  }
  const heading = blk.kind === "heading" || bi === 0;
  return (
    <p
      id={`unit-${blk.id}`}
      tabIndex={-1}
      style={{
        whiteSpace: "pre-wrap",
        overflowWrap: "anywhere",
        margin: heading ? "28px 0 10px" : "0 0 16px",
        fontWeight: heading ? 600 : 400,
        fontSize: bi === 0 ? 22 : heading ? 18 : undefined,
        textAlign: bi === 0 ? "center" : undefined,
        letterSpacing: bi === 0 ? "0.04em" : undefined,
        marginTop: bi === 0 ? 0 : undefined,
      }}
    >
      {nodes}
    </p>
  );
});

function Bracket({ children }: { children: ReactNode }) {
  return (
    <span aria-hidden className="font-mono" style={{ color: "var(--anchor-600)", fontWeight: 600, fontSize: "0.9em", padding: "0 1px" }}>
      {children}
    </span>
  );
}
