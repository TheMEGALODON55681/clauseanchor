import type { ReactNode } from "react";
import { CATALOGUE, GROUP_ORDER } from "../api/catalogue";
import Button from "../components/Button";
import DemoNotice from "../components/DemoNotice";
import Disclosure from "../components/Disclosure";
import { Container, MarginGrid, Section, SectionFrame } from "../components/Layout";
import OffsetTag from "../components/OffsetTag";
import RadioCard from "../components/RadioCard";
import { ROLES } from "../components/RoleSelector";
import Specimen from "../components/Specimen";
import { markStyle } from "../components/SpanHighlight";
import StatusChip from "../components/StatusChip";
import UploadDropzone from "../components/UploadDropzone";
import Evidence, { type EvidencePassage } from "./landing/Evidence";
import HeroDemo from "./landing/HeroDemo";
import { HERO_EXAMPLES } from "./landing/heroExamples";

/* The landing page. Copy and section order follow docs/app/FrontendDesign.md 6.1 and 8. */

/* The Evidence section needs one verbatim passage from the corpus the product
   serves (decision D7). Until a verified one is set here the section is not
   rendered, the § marks renumber and nothing about it is in the build. */
const EVIDENCE: EvidencePassage | null = null;

const PRIVACY_LINE = "Your contract is processed in memory and deleted within 60 minutes.";

const DOES = [
  "Finds clauses in 41 listed categories",
  "Quotes your contract word for word and shows where each quote sits",
  "Adds statute notes and judgment passages in a later build",
  "Marks every finding Needs a lawyer, and shows no score",
];
const DOES_NOT = [
  "Give legal advice",
  "Predict how a court will decide",
  "Write replacement clauses",
  "Promise that nothing was missed",
];

const QUESTIONS: [string, string][] = [
  ["Is this legal advice?", "No. ClauseAnchor points to text in your contract. It does not tell you what the law requires."],
  ["What happens to my file?", "Your contract is processed in memory and deleted within 60 minutes. Choose Delete document in the reader to remove it sooner."],
  ["What if it misses something?", "It can. This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment."],
  ["Which files work?", "PDF or DOCX with selectable text, up to 10 MB and 100 pages. A file that is scanned throughout, or password protected, is refused."],
  ["Which law does it cover?", "ClauseAnchor finds listed clause categories and does not apply any country's law. The five India-specific categories show as not available in this build yet. Statute notes and judgment passages come in a later build."],
];

/* The India-specific group is listed and does not run in this build (docs/ml/CategoryCatalogue.md), so its summary says so. */
const GROUPS = GROUP_ORDER.map((group) => {
  const rows = CATALOGUE.filter((c) => c.group === group);
  return { group, names: rows.map((c) => c.label), later: rows.every((c) => c.id.startsWith("in.")) };
});

/* The three CUAD figures that § 1 states in words, set as a ruled ledger in the aside. The paragraph carries the same facts, so the
   ledger is a specimen: hidden from assistive technology, and it rises into view once. */
const LEDGER: [string, string][] = [
  ["41", "kinds of clause"],
  ["510", "commercial contracts"],
  ["13,000+", "annotations"],
];

function Ledger() {
  return (
    <dl className="m-0">
      {LEDGER.map(([figure, label]) => (
        <div key={label} className="flex items-baseline gap-4 border-t py-3 last:border-b" style={{ borderColor: "var(--rule-default)" }}>
          <dt className="t-section-mark min-w-[6rem]">{figure}</dt>
          <dd className="t-marginal-note m-0">{label}</dd>
        </div>
      ))}
    </dl>
  );
}

function RoleFragment() {
  const pick = (role: string) => ROLES.find((r) => r.role === role)!;
  return (
    <div className="flex flex-col gap-3">
      {(["buyer_customer", "supplier_vendor"] as const).map((role) => (
        <RadioCard key={role} title={pick(role).title} description={pick(role).desc} icon={pick(role).icon} state={role === "supplier_vendor" ? "selected" : "unselected"} />
      ))}
    </div>
  );
}

function FindingFragment() {
  const e = HERO_EXAMPLES[1];
  return (
    <div className="flex flex-col gap-3 p-4" style={{ background: "var(--paper-sheet)", border: "1px solid var(--rule-default)", borderRadius: "var(--radius-lg)" }}>
      <p style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: "30px", color: "var(--ink-primary)" }}>
        <mark className="ca-mark" style={{ ...markStyle(e.status), color: "inherit", paddingBottom: 3 }}>{e.quote}</mark>
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <StatusChip status={e.status} size="s" />
        <OffsetTag start={e.start} end={e.end} />
      </div>
    </div>
  );
}

const STEPS: { title: string; body: string; fragment: ReactNode }[] = [
  { title: "Upload the contract", body: "Upload a PDF or DOCX with selectable text, up to 10 MB and 100 pages.", fragment: <UploadDropzone state="idle" /> },
  { title: "Say which side you are", body: "Pick your role and the party you are. This build does not use your choice yet, so findings carry no burden or benefit label.", fragment: <RoleFragment /> },
  { title: "Check each finding", body: "Every finding points to exact text. Select one to see the quoted wording and where it sits in your contract. Statute notes and judgment passages come in a later build.", fragment: <FindingFragment /> },
];

function Mark({ children }: { children: string }) {
  return <span aria-hidden className="t-section-mark">{children}</span>;
}

function Ctas() {
  return (
    <>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button to="/start" size="l">Review a contract</Button>
      </div>
      {/* The built-in sample needs the sample endpoint of 3-C. Until then a fictional agreement is a plain download. */}
      <div className="mt-3">
        <DemoNotice />
      </div>
    </>
  );
}

export default function Landing() {
  // The § marks count only the sections that render, in order.
  let n = 0;
  const mark = () => `§ ${++n}`;

  return (
    <div>
      <title>ClauseAnchor | Know which clauses to ask a lawyer about</title>

      <section aria-labelledby="hero-title" className="pb-12 pt-8 md:pb-16 md:pt-12 lg:pt-16">
        <Container>
          <HeroDemo>
            <h1 id="hero-title" className="t-display-xl" style={{ color: "var(--ink-primary)" }}>
              Know which clauses to ask a lawyer about.
            </h1>
            <p className="mt-4 max-w-[66ch] font-serif text-[17px] leading-[28px] md:text-[19px] md:leading-[32px]" style={{ color: "var(--ink-secondary)" }}>
              ClauseAnchor checks your contract against 41 listed clause categories and marks each match in the margin. Every finding quotes your text. In this build each one is marked Needs a lawyer.
            </p>
            <div className="mt-6">
              <Ctas />
            </div>
            <p className="mt-4 text-[15px] leading-[24px]" style={{ color: "var(--ink-secondary)" }}>{PRIVACY_LINE}</p>
          </HeroDemo>
        </Container>
      </section>

      <Section
        compact
        id="problem"
        labelledBy="problem-title"
        mark={mark()}
        aside={
          <>
            <Specimen>
              <Ledger />
            </Specimen>
            <p className="t-marginal-note mt-4">Source: CUAD v1, The Atticus Project. Licence CC BY 4.0.</p>
          </>
        }
      >
        <h2 id="problem-title" className="t-display-md">Contracts run long. The clause types worth asking about are a known list.</h2>
        <p className="t-prose-lg mt-4">
          The Contract Understanding Atticus Dataset labels 41 kinds of clause across 510 commercial contracts, with more than 13,000 annotations. ClauseAnchor checks those 41. The five India-specific categories it also lists come in a later build.{" "}
          <a className="link-prose" href="https://www.atticusprojectai.org/cuad/" target="_blank" rel="noreferrer">Read about the dataset</a>.
        </p>
      </Section>

      <SectionFrame id="how" labelledBy="how-title">
        <MarginGrid margin={<Mark>{mark()}</Mark>}>
          <h2 id="how-title" className="t-display-md">Three steps. Every finding can be checked.</h2>
        </MarginGrid>
        {/* Ruled rows: from 1280px a step's number, text and visual share one midline, so the row's own padding is the only space around them. */}
        <ol className="mt-6">
          {STEPS.map((s, i) => (
            <li key={s.title} className="border-t py-8 last:border-b" style={{ borderColor: "var(--rule-default)" }}>
              <MarginGrid center margin={<Mark>{String(i + 1)}</Mark>} aside={<Specimen>{s.fragment}</Specimen>}>
                <h3 className="font-sans text-[18px] font-semibold leading-[26px]" style={{ color: "var(--ink-primary)" }}>{s.title}</h3>
                <p className="t-prose-lg mt-2">{s.body}</p>
              </MarginGrid>
            </li>
          ))}
        </ol>
        <div className="mt-8">
          <MarginGrid>
            <Button to="/start" size="l">Review a contract</Button>
          </MarginGrid>
        </div>
      </SectionFrame>

      {EVIDENCE && <Evidence passage={EVIDENCE} mark={mark()} />}

      <Section id="lawyer" labelledBy="lawyer-title" mark={mark()}>
        <h2 id="lawyer-title" className="t-display-md">Built to tell you when to call a lawyer.</h2>
        <p className="t-prose-lg mt-4">
          ClauseAnchor does not guess. In this build it marks every match Needs a lawyer and shows you the text it found. Take the marked clauses and their quoted evidence to a lawyer, and start the conversation at the clause.
        </p>
        <div className="mt-8 grid gap-8 md:grid-cols-2 md:gap-0">
          <div className="md:pr-8">
            <h3 className="font-sans text-[15px] font-semibold leading-[22px]" style={{ color: "var(--ink-primary)" }}>What it does</h3>
            <ul className="mt-3 flex flex-col gap-2 text-[15px] leading-[24px]" style={{ color: "var(--ink-secondary)" }}>
              {DOES.map((t) => <li key={t}>{t}</li>)}
            </ul>
          </div>
          <div className="md:border-l md:pl-8" style={{ borderColor: "var(--rule-default)" }}>
            <h3 className="font-sans text-[15px] font-semibold leading-[22px]" style={{ color: "var(--ink-primary)" }}>What it does not do</h3>
            <ul className="mt-3 flex flex-col gap-2 text-[15px] leading-[24px]" style={{ color: "var(--ink-secondary)" }}>
              {DOES_NOT.map((t) => <li key={t}>{t}</li>)}
            </ul>
          </div>
        </div>
        <div className="mt-8 flex flex-wrap items-center gap-x-3 gap-y-2 border-t pt-6" style={{ borderColor: "var(--rule-default)" }}>
          <StatusChip status="review" />
          <p className="text-[15px] leading-[24px]" style={{ color: "var(--ink-secondary)" }}>The text it found stays on screen, and a person makes the call.</p>
        </div>
      </Section>

      <Section id="categories" labelledBy="categories-title" mark={mark()}>
        <h2 id="categories-title" className="t-display-md">41 clause categories run in this build.</h2>
        <p className="t-prose-lg mt-4">
          From basics such as governing law to restrictions and liability. The five India-specific categories, such as stamping and registration, are listed and come in a later build. A category that is not on the list is not checked.
        </p>
        <div className="mt-8">
          {GROUPS.map((g, i) => (
            <Disclosure key={g.group} summary={`${g.group} (${g.names.length}${g.later ? ", coming later" : ""})`} open={i === 0}>
              <ul className="gap-x-8 sm:columns-2">
                {g.names.map((name) => <li key={name} className="py-0.5">{name}</li>)}
              </ul>
            </Disclosure>
          ))}
        </div>
      </Section>

      <Section compact id="privacy" labelledBy="privacy-title" mark={mark()}>
        <h2 id="privacy-title" className="t-display-md">Your contract is deleted within 60 minutes.</h2>
        <p className="t-prose-lg mt-4">
          {PRIVACY_LINE} Reloading the page ends your session, and nothing is written to your browser's storage. The Accuracy page will list the measured figures for each category in a later build.
        </p>
        <p className="-ml-4 mt-4">
          <Button to="/accuracy" variant="tertiary">See the Accuracy page</Button>
        </p>
      </Section>

      <Section compact id="questions" labelledBy="questions-title" mark={mark()}>
        <h2 id="questions-title" className="t-display-md">Questions before you upload.</h2>
        <div className="mt-8">
          {QUESTIONS.map(([q, a]) => (
            <Disclosure key={q} summary={q}>{a}</Disclosure>
          ))}
        </div>
      </Section>

      <SectionFrame compact id="start" labelledBy="start-title">
        <MarginGrid>
          <h2 id="start-title" className="t-display-md">Start with the contract in front of you.</h2>
          <div className="mt-6">
            <Ctas />
          </div>
        </MarginGrid>
      </SectionFrame>
    </div>
  );
}
