import { useEffect } from "react";
import type { ReactNode } from "react";
import { useLocation } from "react-router";
import { Container, MarginGrid } from "../components/Layout";
import Link from "../components/Link";
import NoticeBanner from "../components/NoticeBanner";
import Specimen from "../components/Specimen";
import StatusChip from "../components/StatusChip";


/* `fragment` is a real component that shows what the text describes. It sits in the aside from
   1280 px and under the text below that. */
const SECTIONS: { id: string; title: string; body: ReactNode; fragment?: ReactNode }[] = [
  {
    id: "reading",
    title: "Reading the contract",
    body: (
      <>
        <p>
          Your file is turned into plain text once, when you upload it. Every finding afterwards points back into that exact text by character position, so the passage you see highlighted is the passage that was read. Nothing is paraphrased into the document.
        </p>
        <p>
          ClauseAnchor refuses a file at upload if it is scanned throughout or password protected, because there is no reliable text to point to. If only some pages are scanned, ClauseAnchor reads the rest and tells you in the reader that it could not read part of the document.
        </p>
      </>
    ),
  },
  {
    id: "categories",
    title: "Looking for 46 kinds of clause",
    body: (
      <>
        <p>
          The review checks a fixed list of clause categories: 41 drawn from the CUAD research dataset and five added for Indian agreements, such as stamping and registration. Each category is searched across the whole document in overlapping windows.
        </p>
        <p>
          If a provision is not on the list, it is not checked. Unhighlighted text means only that no listed category was confirmed there. A Manual review list that collects those passages is not available in this build yet, so read the full text yourself.
        </p>
      </>
    ),
  },
  {
    id: "confidence",
    fragment: (
      <div className="flex flex-col items-start gap-2">
        <StatusChip status="review" />
        <StatusChip status="unvalidated" />
      </div>
    ),
    title: "Saying how sure it is",
    body: (
      <>
        <p>
          This build does not validate its confidence yet. Every finding carries the note Confidence not validated and shows no score, so read each marked passage yourself. A later build will measure how often the marks are right, against labelled contracts.
        </p>
        <p>
          When the evidence for a category is close, ClauseAnchor marks the category Needs a lawyer instead of guessing. The Accuracy page will list the measured numbers for each category, including how often a real clause is missed without a warning. It is not available in this build yet.
        </p>
      </>
    ),
  },
  {
    id: "law",
    title: "India-specific categories",
    body: (
      <>
        <p>
          The India-specific switch adds five categories for Indian agreements, such as stamping and registration. In this build they show as not available yet.
        </p>
        <p>Statute notes and judgment passages come in a later build.</p>
      </>
    ),
  },
  {
    id: "role",
    title: "Reading from your side",
    body: (
      <p>
        You choose your role and which named party you are. This build does not use your choice yet, so findings carry no burden or benefit label.
      </p>
    ),
  },
  {
    id: "limits",
    title: "What it will not do",
    body: (
      <p>
        ClauseAnchor does not give legal advice, does not rate a contract, and does not write replacement wording. It is a reading aid. For anything you intend to sign or enforce, speak to a lawyer qualified in the relevant jurisdiction.
      </p>
    ),
  },
  {
    id: "privacy",
    title: "Privacy",
    body: (
      <>
        <p>
          Your contract and its text are held in server memory for the length of your session and are deleted when it ends, or sooner if you choose Delete in the reader. They are not used to train anything and are not shared.
        </p>
        <p>This browser keeps the contract only in page memory. Nothing is written to local storage. Reloading the page ends the session.</p>
      </>
    ),
  },
  {
    id: "credits",
    title: "Credits",
    body: (
      <ul className="flex flex-col gap-3">
        <li>
          <strong>CUAD</strong> by The Atticus Project, licensed under CC BY 4.0. Category definitions and labelled examples.{" "}
          <Link variant="external" href="https://www.atticusprojectai.org/cuad">atticusprojectai.org</Link>
        </li>
        <li><strong>OpenNyaya</strong>. Indian judgment texts and structure.</li>
        <li><strong>NyayaAnumana</strong>. Indian case corpus, for passage retrieval in a later build.</li>
        <li><strong>InLegalBERT</strong>. Language model pretrained on Indian legal text.</li>
      </ul>
    ),
  },
];

/* The page keeps its hash route, so a section cannot be a fragment. The contents links and the
   footer's Credits link (?at=credits) scroll to a heading and move focus to it. */
function goTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ block: "start" });
  document.getElementById(`${id}-h`)?.focus({ preventScroll: true });
}

export default function HowItWorks() {
  const { key, search } = useLocation();
  const at = new URLSearchParams(search).get("at");
  useEffect(() => {
    if (!at) return;
    // Root resets scroll and focus after the page mounts, so wait one frame.
    const frame = requestAnimationFrame(() => goTo(at));
    return () => cancelAnimationFrame(frame);
  }, [at, key]);

  return (
    <div className="pb-16 md:pb-24">
      <title>How it works | ClauseAnchor</title>

      <section aria-labelledby="how-title" className="pb-10 pt-8 md:pt-12 lg:pt-16">
        <Container>
          <MarginGrid>
            <h1 id="how-title" className="t-display-md">How it works</h1>
            <p className="t-prose-lg mt-4">A plain account of what happens to your contract, what the marks in the reader mean, and where the limits are.</p>
            <div className="mt-6">
              <NoticeBanner variant="legal-scope" />
            </div>
          </MarginGrid>
        </Container>
      </section>

      <Container>
        <MarginGrid
          margin={
            <nav aria-label="On this page" className="lg:sticky lg:top-8">
              <p className="t-overline" style={{ color: "var(--ink-tertiary)" }}>On this page</p>
              <ol className="mt-2 flex flex-col">
                {SECTIONS.map((s, i) => (
                  <li key={s.id}>
                    <a
                      href="#/how-it-works"
                      onClick={(e) => {
                        e.preventDefault();
                        goTo(s.id);
                      }}
                      className="flex min-h-11 items-center gap-2 py-1 text-[14px] leading-[20px] hover:underline"
                      style={{ color: "var(--ink-secondary)" }}
                    >
                      <span aria-hidden className="shrink-0 whitespace-nowrap font-serif tabular-nums" style={{ color: "var(--anchor-600)" }}>§ {i + 1}</span>
                      {s.title}
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
          }
        >
          {SECTIONS.map((s, i) => (
            <section
              key={s.id}
              id={s.id}
              aria-labelledby={`${s.id}-h`}
              className="relative mt-10 border-t pt-10 first:mt-0 first:border-t-0 first:pt-0"
              style={{ borderColor: "var(--rule-default)" }}
            >
              <div className="flex items-baseline gap-3">
                <span aria-hidden className="t-section-mark">§ {i + 1}</span>
                <h2 id={`${s.id}-h`} tabIndex={-1} className="font-serif text-[24px] font-semibold leading-[32px]" style={{ color: "var(--ink-primary)" }}>
                  {s.title}
                </h2>
              </div>
              <div className="t-prose-lg mt-4 flex flex-col gap-4">{s.body}</div>
              {s.fragment && (
                <div className="mt-6 xl:absolute xl:left-full xl:top-10 xl:ml-8 xl:mt-0 xl:w-[320px]">
                  <Specimen>{s.fragment}</Specimen>
                </div>
              )}
            </section>
          ))}
        </MarginGrid>
      </Container>
    </div>
  );
}
