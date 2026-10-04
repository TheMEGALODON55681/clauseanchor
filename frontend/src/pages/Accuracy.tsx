import { useEffect, useMemo, useState } from "react";
import { client } from "../api/client";
import type { EvaluationRow, Evaluations } from "../api/types";
import { CATEGORY_BY_ID } from "../api/catalogue";
import Tabs from "../components/Tabs";
import SegmentedFilter from "../components/SegmentedFilter";
import PerformanceTableRow from "../components/PerformanceTableRow";
import NoticeBanner from "../components/NoticeBanner";
import ErrorCard from "../components/ErrorCard";
import Skeleton from "../components/Skeleton";

type SortKey = "Category" | "Recall" | "Silent miss";

const COLS = ["Category", "Support", "Precision", "Recall", "Silent miss", "Abstention"];

const GLOSSARY: { term: string; text: string }[] = [
  { term: "Precision", text: "Of the clauses marked Found, the share that a lawyer also marked. Higher means fewer passages marked by mistake." },
  { term: "Recall", text: "Of the clauses a lawyer marked, the share the review also found. Higher means fewer clauses passed over." },
  { term: "Silent miss", text: "The share of real clauses that were neither found nor sent to Needs a lawyer. This is the number to watch: these are misses with no warning." },
  { term: "Abstention", text: "How often the review declined to decide and sent the category to Needs a lawyer instead." },
  { term: "Support", text: "How many labelled examples the numbers rest on. Under 10 is shown as insufficient." },
];

function sortRows(rows: EvaluationRow[], key: SortKey) {
  const label = (r: EvaluationRow) => CATEGORY_BY_ID[r.category_id]?.label ?? r.category_id;
  const num = (v: number | null, worst: number) => (v === null ? worst : v);
  return [...rows].sort((a, b) => {
    if (key === "Recall") return num(a.recall, 2) - num(b.recall, 2);
    if (key === "Silent miss") return num(b.silent_miss, -1) - num(a.silent_miss, -1);
    return label(a).localeCompare(label(b));
  });
}

export default function Accuracy() {
  const [data, setData] = useState<Evaluations | null>(null);
  const [failed, setFailed] = useState(false);
  const [tab, setTab] = useState("");
  const [sort, setSort] = useState<SortKey>("Category");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setFailed(false);
    client
      .getEvaluations()
      .then((d) => {
        if (!live) return;
        setData(d);
        setTab((t) => t || d.sets[0]?.label || "");
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [attempt]);

  const set = data?.sets.find((s) => s.label === tab) ?? data?.sets[0];
  const rows = useMemo(() => (set ? sortRows(set.rows, sort) : []), [set, sort]);
  const weak = rows.filter((r) => r.weak).length;

  return (
    <div className="mx-auto w-full max-w-[1120px] px-5 py-12 md:px-8 md:py-16">
      <title>Accuracy | ClauseAnchor</title>
      <p className="font-mono text-[12px] tracking-[0.08em] uppercase" style={{ color: "var(--ink-tertiary)" }}>§ Accuracy</p>
      <h1 className="mt-3 text-[32px] leading-[40px]" style={{ fontFamily: "var(--font-serif)", fontWeight: 500, color: "var(--ink-primary)" }}>
        How well each category is found
      </h1>
      <p className="mt-4 max-w-[68ch] text-[16px] leading-[26px]" style={{ color: "var(--ink-secondary)" }}>
        These numbers describe the listed categories only. They do not measure how much of a contract's risk is found.
      </p>
      <div className="mt-6 max-w-[760px]">
        <NoticeBanner variant="review-scope" />
      </div>

      {failed && (
        <div className="mt-8 max-w-[640px]">
          <ErrorCard message="The accuracy figures could not be loaded." code="ERR_NETWORK" onRetry={() => setAttempt((a) => a + 1)} />
        </div>
      )}

      {!failed && (
        <section className="mt-10" aria-labelledby="table-title">
          <h2 id="table-title" className="sr-only">Results by category</h2>
          <div className="flex flex-wrap items-end justify-between gap-4">
            {data ? <Tabs items={data.sets.map((s) => s.label)} value={set?.label} onChange={setTab} /> : <Skeleton />}
            <div className="flex items-center gap-3">
              <span className="text-[13px]" style={{ color: "var(--ink-tertiary)" }} id="sort-label">Sort by</span>
              <SegmentedFilter items={["Category", "Recall", "Silent miss"]} value={sort} onChange={(v) => setSort(v as SortKey)} />
            </div>
          </div>

          {data?.is_example && (
            <p
              className="mt-5 inline-flex items-center gap-2 font-mono text-[12px]"
              style={{ color: "var(--status-unvalidated-fg)", border: "1px dashed var(--status-unvalidated-border)", borderRadius: "var(--radius-sm)", padding: "4px 8px" }}
            >
              Example numbers for layout. Real results appear after evaluation.
            </p>
          )}

          {set && (
            <p className="mt-3 text-[13px]" style={{ color: "var(--ink-secondary)" }}>
              {rows.length} categories. {weak} marked with an ochre rule where recall or precision is low.
            </p>
          )}

          <div className="mt-4 overflow-x-auto" style={{ border: "1px solid var(--rule-default)", borderRadius: "var(--radius-md)", background: "var(--paper-sheet)" }}>
            <div className="min-w-[640px]" role="table" aria-label={`${set?.label ?? "Evaluation"} results`}>
              <div
                role="row"
                className="grid px-4 py-2 text-[12px] font-semibold"
                style={{ gridTemplateColumns: "minmax(140px, 1.6fr) repeat(5, minmax(72px, 1fr))", color: "var(--ink-tertiary)", borderBottom: "1px solid var(--rule-strong)", gap: 12 }}
              >
                {COLS.map((c) => (
                  <span role="columnheader" key={c}>{c}</span>
                ))}
              </div>
              {!data &&
                Array.from({ length: 6 }, (_, i) => (
                  <div key={i} className="px-4 py-3"><Skeleton /></div>
                ))}
              {rows.map((r) => (
                <PerformanceTableRow
                  key={r.category_id}
                  category={CATEGORY_BY_ID[r.category_id]?.label ?? r.category_id}
                  variant={r.recall === null ? "not-measured" : r.weak ? "weak" : "strong"}
                  metrics={{ support: r.support, precision: r.precision, recall: r.recall, silentMiss: r.silent_miss, abstention: r.abstention }}
                />
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="mt-14 max-w-[760px]" aria-labelledby="glossary-title">
        <h2 id="glossary-title" className="text-[22px]" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, color: "var(--ink-primary)" }}>
          What the columns mean
        </h2>
        <dl className="mt-4">
          {GLOSSARY.map((g) => (
            <div key={g.term} className="grid gap-1 py-3 md:grid-cols-[160px_1fr] md:gap-6" style={{ borderTop: "1px solid var(--rule-default)" }}>
              <dt className="text-[15px] font-semibold" style={{ color: "var(--ink-primary)" }}>{g.term}</dt>
              <dd className="text-[15px] leading-[24px]" style={{ color: "var(--ink-secondary)" }}>{g.text}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
