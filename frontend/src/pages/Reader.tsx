import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate, useParams } from "react-router";
import { client } from "../api/client";
import { ApiError, type Analysis, type Category, type Clause, type Document, type Job, type ManualReview, type Role } from "../api/types";
import { CATALOGUE, CATALOGUE_VERSION, CATEGORY_BY_ID, GROUP_ORDER } from "../api/catalogue";
import { buildOffsetIndex, sliceCp, toUtf16, type OffsetIndex } from "../lib/offsets";
import { useMedia, useReducedMotion } from "../lib/useMedia";
import { useSession } from "../app/session";
import ReaderToolbar, { type ToolbarVariant } from "../components/ReaderToolbar";
import StageProgress, { type Step, type StepState } from "../components/StageProgress";
import CategorySidebar, { type SidebarGroup, type SidebarRow } from "../components/CategorySidebar";
import ClauseDetailPanel, { type PanelData } from "../components/ClauseDetailPanel";
import MarginRuler, { type RulerMark } from "../components/MarginRuler";
import ScopePanel from "../components/ScopePanel";
import ManualReviewList, { type ManualItem } from "../components/ManualReviewList";
import NoticeBanner from "../components/NoticeBanner";
import ErrorCard from "../components/ErrorCard";
import ConfirmDialog from "../components/ConfirmDialog";
import DropdownMenu, { type MenuItem } from "../components/DropdownMenu";
import MobileDrawer from "../components/MobileDrawer";
import RuleFlagCard from "../components/RuleFlagCard";
import JudgmentCard, { type Authority } from "../components/JudgmentCard";
import KeyboardHint from "../components/KeyboardHint";
import CountBadge from "../components/CountBadge";
import Button from "../components/Button";
import Skeleton from "../components/Skeleton";
import { markStyle, type SpanKind } from "../components/SpanHighlight";
import type { StatusKind } from "../components/StatusChip";
import { ChevronIcon, ListIcon, PilcrowIcon } from "../components/icons";

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

function authorityOf(s: string): Authority {
  return s === "overruled" ? "overruled" : s === "reviewed" ? "reviewed" : "not-reviewed";
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
  const xl = useMedia("(min-width: 1280px)");
  const lg = useMedia("(min-width: 1024px)");
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
  const sheetRef = useRef<HTMLDivElement>(null);

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

  const scrollToEl = useCallback(
    (el: HTMLElement | null, focus = false) => {
      if (!el) return;
      el.scrollIntoView({ block: "center", behavior: reduced ? "auto" : "smooth" });
      if (focus) el.focus({ preventScroll: true });
    },
    [reduced]
  );

  const selectCategory = useCallback(
    (id: string, clause = 0, scroll = true) => {
      setSelection({ type: "category", id, clause });
      setSheet((s) => (s === "open" ? s : "peek"));
      setSidebarOpen(false);
      const k = catMap.get(id)?.clauses[clause];
      if (scroll && k) scrollToEl(document.getElementById(`f-${k.id}`));
    },
    [catMap, scrollToEl]
  );

  const selectFinding = useCallback(
    (f: Finding, focus: boolean) => {
      const cat = catMap.get(f.categoryId);
      const idx = cat ? cat.clauses.findIndex((c) => c.id === f.clause.id) : 0;
      setSelection({ type: "category", id: f.categoryId, clause: Math.max(0, idx) });
      setSheet((s) => (s === "open" ? s : "peek"));
      scrollToEl(document.getElementById(`f-${f.clause.id}`), focus);
    },
    [catMap, scrollToEl]
  );

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
        selectFinding(findings[next], true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [findings, selectedFinding, selectFinding, confirmDelete]);

  /* Margin ruler positions come from the rendered marks, so they follow wrapping. */
  const [marks, setMarks] = useState<(RulerMark & { id: string })[]>([]);
  const [viewport, setViewport] = useState({ top: 0, size: 1 });
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
    setMarks(next);
    setViewport({ top: sc.scrollTop / total, size: Math.min(1, sc.clientHeight / total) });
  }, [findings]);

  useLayoutEffect(() => {
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [measure, md, lg, xl]);

  /* Sidebar groups, with skeleton rows for categories still being checked. */
  const groups: SidebarGroup[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    return GROUP_ORDER.map((g) => {
      const rows: SidebarRow[] = CATALOGUE.filter((c) => c.group === g).map((c) => {
        const cat = catMap.get(c.id);
        if (!cat) return { id: c.id, name: c.label, status: finished ? "unavailable" : "absent", pending: !finished };
        const status = categoryStatus(cat);
        return { id: c.id, name: c.label, status, count: cat.clauses.length || undefined };
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
  }, [catMap, query, filter, finished]);

  const counts = useMemo(() => {
    const c = { found: 0, review: 0, absent: 0, unvalidated: 0, unavailable: 0 };
    for (const cat of analysis?.categories ?? []) c[categoryStatus(cat)]++;
    return c;
  }, [analysis]);
  const summary = `${CATALOGUE.length} categories: ${counts.found} found, ${counts.review} need a lawyer, ${counts.absent} not found, ${counts.unvalidated} not validated${counts.unavailable ? `, ${counts.unavailable} unavailable` : ""}`;

  const unavailableNames = (analysis?.categories ?? []).filter((c) => c.status === "unavailable").map((c) => labelOf(c.category_id));
  const support = useMemo(() => {
    const s = { validated: 0, pooled: 0, notValidated: 0 };
    for (const c of CATALOGUE) {
      if (c.support === "validated") s.validated++;
      else if (c.support === "pooled") s.pooled++;
      else s.notValidated++;
    }
    return s;
  }, []);

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

  /* Detail panel content for the current selection. */
  const panel: ReactNode = (() => {
    const fill = !lg;
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
                  scrollToEl(document.getElementById(`unit-${id}`), true);
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
          reviewNote:
            clause.status === "review_candidate"
              ? "This passage may be the clause, but the evidence did not reach the validated threshold. A lawyer should read it with the surrounding text."
              : undefined,
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
      return <ClauseDetailPanel fill={fill} data={data} onClose={() => { setSelection(null); setSheet("closed"); }} />;
    }
    return (
      <ClauseDetailPanel
        fill={fill}
        custom={{
          title: "Nothing selected",
          content: (
            <div className="flex flex-col gap-3 text-[14px] leading-[22px]" style={{ color: "var(--ink-secondary)" }}>
              <p>Choose a highlighted passage or a category to see the exact wording, which side it favours, and any case law.</p>
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
          support={support}
          limitations={unavailableNames.length ? [`Unavailable: ${unavailableNames.join(", ")}`] : []}
          onViewList={() => setFilter("All")}
        />
      }
      footer={
        <button
          type="button"
          onClick={() => {
            setSelection({ type: "manual" });
            setSheet("open");
            setSidebarOpen(false);
          }}
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
  const pages = doc ? Math.max(1, ...doc.nodes.map((n) => n.page)) : 0;
  const minutesLeft = doc ? (new Date(doc.expires_at).getTime() - now) / 60000 : Infinity;

  if (!token || !meta) return null;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <title>Review | ClauseAnchor</title>
      <h1 className="sr-only">Contract review</h1>
      <ReaderToolbar
        variant={variant}
        filename={doc?.filename ?? "Loading"}
        meta={doc ? `${plural(pages, "page", "pages")}, ${CATALOGUE.length} categories` : ""}
        progress={!finished ? <StageProgress compact steps={steps} onCancel={cancel} /> : undefined}
        partialNote={partialNote}
        leading={
          !xl ? (
            <Button variant="secondary" size="s" icon="icon-only" iconNode={<ListIcon size={16} />} aria-label="Show categories" onClick={() => setSidebarOpen(true)} />
          ) : undefined
        }
        menu={<DropdownMenu label="Change your role" items={roleItems} />}
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
        {xl && (
          <div className="w-[280px] shrink-0 overflow-hidden" style={{ borderRight: "1px solid var(--rule-default)" }}>
            {sidebar}
          </div>
        )}

        <div
          ref={scroller}
          onScroll={measure}
          className="scroll-pane min-w-0 flex-1 overflow-y-auto"
          style={{ background: "var(--paper-sunken)", paddingBottom: !lg && sheet !== "closed" ? 160 : 0 }}
        >
          <div className="mx-auto flex w-full max-w-[820px] gap-3 px-3 py-6 md:px-6 md:py-10">
            <article
              aria-label="Contract text"
              className="min-w-0 flex-1"
              style={{
                maxWidth: 760,
                background: "var(--paper-sheet)",
                border: "1px solid var(--rule-default)",
                borderRadius: "var(--radius-sm)",
                boxShadow: "var(--elevation-1)",
                padding: md ? "56px 64px" : "28px 20px",
              }}
            >
              {doc && index ? (
                <DocumentText
                  doc={doc}
                  index={index}
                  findings={findings}
                  selectedId={selectedFinding?.clause.id ?? null}
                  hoverId={hoverKey}
                  onHover={setHoverKey}
                  onPick={(f) => selectFinding(f, false)}
                />
              ) : (
                <div className="flex flex-col gap-4" aria-busy="true">
                  <span className="sr-only">Loading the contract</span>
                  {Array.from({ length: 8 }, (_, i) => (
                    <Skeleton key={i} />
                  ))}
                </div>
              )}
            </article>
            {md && (
              <div className="sticky top-6 shrink-0 self-start" style={{ height: "calc(100dvh - 220px)" }}>
                <MarginRuler
                  height="100%"
                  marks={marks}
                  selected={selectedFinding ? marks.findIndex((m) => m.label === labelOf(selectedFinding.categoryId)) : null}
                  viewport={viewport}
                  caption="Findings"
                  onSelect={(i) => {
                    const f = findings.find((x) => x.clause.id === marks[i]?.id);
                    if (f) selectFinding(f, true);
                  }}
                />
              </div>
            )}
          </div>
        </div>

        {lg && (
          <div className="scroll-pane w-[400px] shrink-0 overflow-y-auto" style={{ borderLeft: "1px solid var(--rule-default)", background: "var(--paper-base)" }}>
            {panel}
          </div>
        )}
      </div>

      {!xl && (
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

      {!lg && selection && sheet !== "closed" && (
        <div ref={sheetRef}>
          <MobileDrawer
            fixed
            framed={false}
            side="bottom"
            state={sheet}
            title={selection.type === "manual" ? "Manual review" : labelOf(selection.id)}
            size="78dvh"
            actions={
              <div className="flex gap-1">
                <Button variant="tertiary" size="s" onClick={() => setSheet(sheet === "peek" ? "open" : "peek")}>
                  {sheet === "peek" ? "Open" : "Peek"}
                </Button>
                <Button variant="tertiary" size="s" onClick={() => { setSheet("closed"); setSelection(null); }}>
                  Close
                </Button>
              </div>
            }
          >
            {panel}
          </MobileDrawer>
        </div>
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

/* Contract text as escaped text nodes, split at every finding boundary so overlaps stack. */
function DocumentText({
  doc,
  index,
  findings,
  selectedId,
  hoverId,
  onHover,
  onPick,
}: {
  doc: Document;
  index: OffsetIndex;
  findings: Finding[];
  selectedId: string | null;
  hoverId: string | null;
  onHover: (id: string | null) => void;
  onPick: (f: Finding) => void;
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
  const firstSeen = new Set<string>();

  return (
    <div style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: "30px", color: "var(--ink-primary)" }}>
      {blocks.map((blk, bi) => {
        const inside = findings.filter((f) => f.e16 > blk.a && f.s16 < blk.b);
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
          const starts = active.filter((f) => f.s16 === a && !firstSeen.has(f.clause.id));
          starts.forEach((f) => firstSeen.add(f.clause.id));
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
                onClick={() => onPick(owner)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onPick(anchor ?? owner);
                  }
                }}
                onMouseEnter={() => onHover(owner.clause.id)}
                onMouseLeave={() => onHover(null)}
                className="ca-mark cursor-pointer"
                style={{ ...markStyle(kind, hovered && !sel), borderRadius: 1 }}
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
            key={blk.id}
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
      })}
    </div>
  );
}

function Bracket({ children }: { children: ReactNode }) {
  return (
    <span aria-hidden className="font-mono" style={{ color: "var(--anchor-600)", fontWeight: 600, fontSize: "0.9em", padding: "0 1px" }}>
      {children}
    </span>
  );
}
