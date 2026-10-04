import type { ReactNode } from "react";
import Link from "../components/Link";
import NoticeBanner from "../components/NoticeBanner";

const SECTIONS: { id: string; title: string; body: ReactNode }[] = [
  {
    id: "reading",
    title: "Reading the contract",
    body: (
      <>
        <p>
          Your file is turned into plain text once, when you upload it. Every finding afterwards points back into that exact text by character position, so the passage you see highlighted is the passage that was read. Nothing is paraphrased into the document.
        </p>
        <p>Scanned images and password-protected files are refused at upload, because there is no reliable text to point to.</p>
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
          If a provision is not on the list, it is not checked. Unhighlighted text means only that no listed category was confirmed there. The Manual review list in the reader collects those passages so you can read them yourself.
        </p>
      </>
    ),
  },
  {
    id: "confidence",
    title: "Saying how sure it is",
    body: (
      <>
        <p>
          A clause is marked Found only when its evidence clears a threshold that was tested against labelled contracts. When the evidence is close, the category goes to Needs a lawyer instead of being guessed. A few categories have too few labelled examples to test, so their findings carry the note Confidence not validated.
        </p>
        <p>The Accuracy page lists the measured numbers for each category, including how often a real clause is missed without a warning.</p>
      </>
    ),
  },
  {
    id: "law",
    title: "Indian law review and case law",
    body: (
      <>
        <p>
          With Indian law review on, some clauses get a short note citing the statute that a court would look at, for example Section 27 of the Indian Contract Act 1872 for restraints of trade. These notes describe what to check. They do not predict an outcome.
        </p>
        <p>
          Case law passages are quoted word for word from published judgments, with the court, year and citation. Each shows whether it has been reviewed and whether it was later overruled or modified. If no verified passage exists, the panel says so.
        </p>
      </>
    ),
  },
  {
    id: "role",
    title: "Reading from your side",
    body: (
      <p>
        You choose your role and which named party you are. Each finding is then labelled Burden on you, Benefits you, Both ways or No direction. Change your role from the reader menu and the labels update. If no party is chosen, the label reads Party unclear.
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
        <li><strong>NyayaAnumana</strong>. Indian case corpus used for passage retrieval.</li>
        <li><strong>InLegalBERT</strong>. Language model pretrained on Indian legal text.</li>
      </ul>
    ),
  },
];

export default function HowItWorks() {
  return (
    <div className="mx-auto w-full max-w-[1120px] px-5 py-12 md:px-8 md:py-16">
      <title>How it works | ClauseAnchor</title>
      <div className="grid gap-10 lg:grid-cols-[220px_1fr]">
        <nav aria-label="On this page" className="lg:sticky lg:top-8 lg:self-start">
          <p className="font-mono text-[12px] tracking-[0.08em] uppercase" style={{ color: "var(--ink-tertiary)" }}>On this page</p>
          <ol className="mt-3 flex flex-col">
            {SECTIONS.map((s, i) => (
              <li key={s.id} className="text-[14px]">
                <a
                  href={`#/how-it-works`}
                  onClick={(e) => {
                    e.preventDefault();
                    document.getElementById(s.id)?.scrollIntoView({ block: "start" });
                    document.getElementById(`${s.id}-h`)?.focus({ preventScroll: true });
                  }}
                  className="inline-block py-[13px] hover:underline"
                  style={{ color: "var(--ink-secondary)" }}
                >
                  <span className="font-mono text-[12px]" style={{ color: "var(--ink-tertiary)" }}>{i + 1}.</span> {s.title}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <article className="max-w-[74ch]" style={{ fontFamily: "var(--font-serif)", color: "var(--ink-primary)" }}>
          <h1 className="text-[36px] leading-[44px]" style={{ fontWeight: 500 }}>How it works</h1>
          <p className="mt-4 text-[19px] leading-[32px]" style={{ color: "var(--ink-secondary)" }}>
            A plain account of what happens to your contract, what the marks in the reader mean, and where the limits are.
          </p>
          <div className="mt-6 font-sans">
            <NoticeBanner variant="legal-scope" />
          </div>
          {SECTIONS.map((s) => (
            <section key={s.id} id={s.id} className="mt-12" aria-labelledby={`${s.id}-h`}>
              <h2 id={`${s.id}-h`} tabIndex={-1} className="flex items-baseline gap-3 text-[24px] leading-[32px]" style={{ fontWeight: 600 }}>
                <span aria-hidden style={{ color: "var(--anchor-600)" }}>§</span>
                {s.title}
              </h2>
              <div className="mt-4 flex flex-col gap-4 text-[18px] leading-[30px]" style={{ color: "var(--ink-secondary)" }}>
                {s.body}
              </div>
            </section>
          ))}
        </article>
      </div>
    </div>
  );
}
