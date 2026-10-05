import type { ReactNode } from "react";
import { CATALOGUE, GROUP_ORDER } from "../api/catalogue";
import Button from "../components/Button";
import Disclosure from "../components/Disclosure";
import { Container, MarginGrid, Section, SectionFrame } from "../components/Layout";
import OffsetTag from "../components/OffsetTag";
import RadioCard from "../components/RadioCard";
import { ROLES } from "../components/RoleSelector";
import { markStyle } from "../components/SpanHighlight";
import StatusChip from "../components/StatusChip";
import UploadDropzone from "../components/UploadDropzone";
import { useReveal } from "../lib/useReveal";
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
  "Finds clauses in 46 listed categories",
  "Quotes your contract word for word and shows where each quote sits",
  "Shows passages from published Indian judgments where it has them",
  "Shows how confident it is, and says so when it is unsure",
];
const DOES_NOT = [
  "Give legal advice",
  "Predict how a court will decide",
  "Write replacement clauses",
  "Promise that nothing was missed",
];

const QUESTIONS: [string, string][] = [
  ["Is this legal advice?", "No. ClauseAnchor points to text in your contract and in published judgments. It does not tell you what the law requires."],
  ["What happens to my file?", "Your contract is processed in memory and deleted within 60 minutes. Choose Delete document in the reader to remove it sooner."],
  ["What if it misses something?", "It can. This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment."],
  ["Which files work?", "PDF or DOCX with selectable text, up to 10 MB and 100 pages. A file that is scanned throughout, or password protected, is refused."],
  ["Which law does it cover?", "Indian law review adds notes that cite Indian statutes and passages from Indian judgments. Turn it off for a contract under another country's law."],
];

const GROUPS = GROUP_ORDER.map((group) => ({ group, names: CATALOGUE.filter((c) => c.group === group).map((c) => c.label) }));

/* A real component shown as a specimen. It takes no input and is hidden from assistive
   technology, because the step beside it says the same thing in words. It rises into view once. */
function Specimen({ children }: { children: ReactNode }) {
  const ref = useReveal<HTMLDivElement>();
  return (
    <div ref={ref} inert aria-hidden className="max-w-[400px]">
      {children}
    </div>
  );
}

function RoleFragment() {
  const pick = (key: string) => ROLES.find((r) => r.key === key)!;
  return (
    <div className="flex flex-col gap-3">
      {(["buyer", "supplier"] as const).map((key) => (
        <RadioCard key={key} title={pick(key).title} description={pick(key).desc} icon={pick(key).icon} state={key === "supplier" ? "selected" : "unselected"} />
      ))}
    </div>
  );
}

function FindingFragment() {
  const e = HERO_EXAMPLES[1];
  return (
    <div className="flex flex-col gap-3 p-4" style={{ background: "var(--paper-sheet)", border: "1px solid var(--rule-default)", borderRadius: "var(--radius-lg)" }}>
      <p style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: "30px", color: "var(--ink-primary)" }}>
        <mark className="ca-mark" style={{ ...markStyle("found", false), color: "inherit", paddingBottom: 3 }}>{e.quote}</mark>
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <StatusChip status="found" size="s" />
        <OffsetTag start={e.start} end={e.end} />
      </div>
    </div>
  );
}

const STEPS: { title: string; body: string; fragment: ReactNode }[] = [
  { title: "Upload the contract", body: "Upload a PDF or DOCX with selectable text, up to 10 MB and 100 pages.", fragment: <UploadDropzone state="idle" /> },
  { title: "Say which side you are", body: "Pick your role and the party you are. That decides whether a clause reads as a burden or a benefit for you.", fragment: <RoleFragment /> },
  { title: "Check each finding", body: "Every finding points to exact text. Select one to see the quoted wording, the confidence band and any case law.", fragment: <FindingFragment /> },
];

function Mark({ children }: { children: string }) {
  return <span aria-hidden className="t-section-mark">{children}</span>;
}

function Ctas() {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <Button to="/start" size="l">Review a contract</Button>
      <Button to="/start?sample=secondment" variant="secondary" size="l">Try the sample contract</Button>
    </div>
  );
}

export default function Landing() {
  // The § marks count only the sections that render, in order.
  let n = 0;
  const mark = () => `§ ${++n}`;

  return (
    <div>
      <title>ClauseAnchor | Know which clauses to ask a lawyer about</title>

      <section aria-labelledby="hero-title" className="pb-16 pt-8 md:pb-24 md:pt-12 lg:pt-16">
        <Container>
          <MarginGrid>
            <h1 id="hero-title" className="t-display-xl" style={{ color: "var(--ink-primary)" }}>
              Know which clauses to ask a lawyer about.
            </h1>
            <p className="mt-4 max-w-[66ch] font-serif text-[17px] leading-[28px] md:text-[19px] md:leading-[32px]" style={{ color: "var(--ink-secondary)" }}>
              ClauseAnchor checks your contract against 46 listed clause categories and marks each match in the margin. Every finding quotes your text, and some add a passage from a published Indian judgment. Where it is unsure, it says Needs a lawyer.
            </p>
            <div className="mt-6">
              <Ctas />
            </div>
            <p className="mt-4 text-[14px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>{PRIVACY_LINE}</p>
          </MarginGrid>
          <div className="mt-10 md:mt-14">
            <HeroDemo />
          </div>
        </Container>
      </section>

      <Section
        id="problem"
        labelledBy="problem-title"
        mark={mark()}
        aside={<p className="t-marginal-note">Source: CUAD v1, The Atticus Project. Licence CC BY 4.0.</p>}
      >
        <h2 id="problem-title" className="t-display-md">Contracts run long. The clause types worth asking about are a known list.</h2>
        <p className="t-prose-lg mt-4">
          The Contract Understanding Atticus Dataset labels 41 kinds of clause across 510 commercial contracts, with more than 13,000 annotations. ClauseAnchor starts from those 41 and adds five for Indian agreements.{" "}
          <a className="link-prose" href="https://www.atticusprojectai.org/cuad/" target="_blank" rel="noreferrer">Read about the dataset</a>.
        </p>
      </Section>

      <SectionFrame id="how" labelledBy="how-title">
        <MarginGrid margin={<Mark>{mark()}</Mark>}>
          <h2 id="how-title" className="t-display-md">Three steps. Every finding can be checked.</h2>
        </MarginGrid>
        <ol className="mt-12 flex flex-col gap-12">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <MarginGrid margin={<Mark>{String(i + 1)}</Mark>} aside={<Specimen>{s.fragment}</Specimen>}>
                <h3 className="font-sans text-[18px] font-semibold leading-[26px]" style={{ color: "var(--ink-primary)" }}>{s.title}</h3>
                <p className="t-prose-lg mt-2">{s.body}</p>
              </MarginGrid>
            </li>
          ))}
        </ol>
        <div className="mt-12">
          <MarginGrid>
            <Button to="/start" size="l">Review a contract</Button>
          </MarginGrid>
        </div>
      </SectionFrame>

      {EVIDENCE && <Evidence passage={EVIDENCE} mark={mark()} />}

      <Section id="lawyer" labelledBy="lawyer-title" mark={mark()}>
        <h2 id="lawyer-title" className="t-display-md">Built to tell you when to call a lawyer.</h2>
        <p className="t-prose-lg mt-4">
          When the evidence for a category is close, ClauseAnchor does not guess. It marks the category Needs a lawyer and shows you the text it found. Take the marked clauses and their quoted evidence to a lawyer, and start the conversation at the clause.
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
        <h2 id="categories-title" className="t-display-md">46 clause categories, in seven groups.</h2>
        <p className="t-prose-lg mt-4">
          From basics such as governing law to India-specific clauses such as stamping and registration. A category that is not on the list is not checked.
        </p>
        <div className="mt-8">
          {GROUPS.map((g, i) => (
            <Disclosure key={g.group} summary={`${g.group} (${g.names.length})`} open={i === 0}>
              <ul className="gap-x-8 sm:columns-2">
                {g.names.map((name) => <li key={name} className="py-0.5">{name}</li>)}
              </ul>
            </Disclosure>
          ))}
        </div>
      </Section>

      <Section id="privacy" labelledBy="privacy-title" mark={mark()}>
        <h2 id="privacy-title" className="t-display-md">Your contract is deleted within 60 minutes.</h2>
        <p className="t-prose-lg mt-4">
          {PRIVACY_LINE} Reloading the page ends your session, and nothing is written to your browser's storage. The Accuracy page lists the measured figures for each category once the evaluation is complete. Until then it shows labelled example numbers.
        </p>
        <p className="-ml-4 mt-4">
          <Button to="/accuracy" variant="tertiary">See the Accuracy page</Button>
        </p>
      </Section>

      <Section id="questions" labelledBy="questions-title" mark={mark()}>
        <h2 id="questions-title" className="t-display-md">Questions before you upload.</h2>
        <div className="mt-8">
          {QUESTIONS.map(([q, a]) => (
            <Disclosure key={q} summary={q}>{a}</Disclosure>
          ))}
        </div>
      </Section>

      <SectionFrame id="start" labelledBy="start-title">
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
