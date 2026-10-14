import { useEffect, useMemo, useState } from "react";
import { client } from "../api/client";
import type { EvaluationRow, Evaluations } from "../api/types";
import { CATEGORY_BY_ID } from "../api/catalogue";
import Tabs from "../components/Tabs";
import SegmentedFilter from "../components/SegmentedFilter";
import { Container, MarginGrid } from "../components/Layout";
import PerformanceTableRow, { PERF_COLUMNS } from "../components/PerformanceTableRow";
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
    <div className="pb-16 md:pb-24">
      <title>Accuracy | ClauseAnchor</title>

      <section aria-labelledby="accuracy-title" className="pb-10 pt-8 md:pt-12 lg:pt-16">
        <Container>
          <MarginGrid>
            <h1 id="accuracy-title" className="t-display-md">How well each category is found</h1>
            <p className="t-prose-lg mt-4">These numbers describe the listed categories only. They do not measure how much of a contract's risk is found.</p>
            <div className="mt-6">
              <NoticeBanner variant="review-scope" />
            </div>
          </MarginGrid>
        </Container>
      </section>

      <Container>
        <MarginGrid
          aside={
            <section aria-labelledby="glossary-title" className="xl:sticky xl:top-8">
              <h2 id="glossary-title" className="font-serif text-[22px] font-semibold leading-[30px]" style={{ color: "var(--ink-primary)" }}>
                What the columns mean
              </h2>
              <dl className="mt-3">
                {GLOSSARY.map((g) => (
                  <div key={g.term} className="py-3" style={{ borderTop: "1px solid var(--rule-default)" }}>
                    <dt className="text-[14px] font-semibold leading-[21px]" style={{ color: "var(--ink-primary)" }}>{g.term}</dt>
                    <dd className="mt-1 text-[14px] leading-[21px]" style={{ color: "var(--ink-secondary)" }}>{g.text}</dd>
                  </div>
                ))}
              </dl>
            </section>
          }
        >
          {failed ? (
            <div className="max-w-[640px]">
              <ErrorCard message="The accuracy figures could not be loaded." code="ERR_NETWORK" onRetry={() => setAttempt((a) => a + 1)} />
            </div>
          ) : (
            <section aria-labelledby="table-title">
              <h2 id="table-title" className="sr-only">Results by category</h2>
              {!data && (
                /* A screen tall, so the glossary and the footer are below the fold before and after the data lands, and nothing in view moves. */
                <div className="min-h-dvh" aria-hidden>
                  {Array.from({ length: 6 }, (_, i) => (
                    <div key={i} className="px-3 py-3"><Skeleton /></div>
                  ))}
                </div>
              )}
              {data && (
                <>
                  <div className="flex flex-wrap items-end justify-between gap-4">
                    <Tabs label="Evaluation set" items={data.sets.map((s) => s.label)} value={set?.label} onChange={setTab} />
                    <div className="flex items-center gap-3">
                      <span className="text-[13px]" style={{ color: "var(--ink-tertiary)" }}>Sort by</span>
                      <SegmentedFilter label="Sort by" items={["Category", "Recall", "Silent miss"]} value={sort} onChange={(v) => setSort(v as SortKey)} />
                    </div>
                  </div>

                  {data.is_example && (
                    <p
                      role="note"
                      className="mt-4 text-[15px] leading-[22px]"
                      style={{ color: "var(--ink-primary)", background: "var(--paper-sheet)", border: "1px dashed var(--status-unvalidated-border)", borderRadius: "var(--radius-sm)", padding: "12px 16px" }}
                    >
                      Example numbers for layout. Real results appear after evaluation.
                    </p>
                  )}

                  {set && (
                    <p className="mt-4 text-[14px] leading-[21px]" style={{ color: "var(--ink-secondary)" }}>
                      {rows.length} categories. {weak} are marked Weak because their recall or precision is low.
                    </p>
                  )}

                  <div className="mt-4" role="table" aria-label={`${set?.label ?? "Evaluation"} results`}>
                    <div
                      role="row"
                      className={`z-10 hidden gap-3 border-b px-3 py-2 text-[12px] font-semibold md:sticky md:top-0 md:grid ${PERF_COLUMNS}`}
                      style={{ color: "var(--ink-secondary)", background: "var(--paper-base)", borderColor: "var(--rule-strong)" }}
                    >
                      {COLS.map((c) => (
                        <span role="columnheader" key={c}>{c}</span>
                      ))}
                    </div>
                    {rows.map((r) => (
                      <PerformanceTableRow
                        key={r.category_id}
                        category={CATEGORY_BY_ID[r.category_id]?.label ?? r.category_id}
                        variant={r.recall === null ? "not-measured" : r.weak ? "weak" : "strong"}
                        metrics={{ support: r.support, precision: r.precision, recall: r.recall, silentMiss: r.silent_miss, abstention: r.abstention }}
                      />
                    ))}
                  </div>
                </>
              )}
            </section>
          )}
        </MarginGrid>
      </Container>
    </div>
  );
}
