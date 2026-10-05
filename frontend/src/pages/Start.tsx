import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { useSession } from "../app/session";
import Button from "../components/Button";
import ErrorCard from "../components/ErrorCard";
import { FileIcon } from "../components/icons";
import { Container, MarginGrid } from "../components/Layout";
import NoticeBanner from "../components/NoticeBanner";
import PartyBindingField from "../components/PartyBindingField";
import RadioCard from "../components/RadioCard";
import RoleSelector from "../components/RoleSelector";
import Switch from "../components/Switch";
import UploadDropzone, { type DropzoneState } from "../components/UploadDropzone";
import { clampStep, nextBlocker, parseStep, suggestedParty, type Blocker, type Step, type UploadState } from "../lib/startFlow";
import Summary from "./start/Summary";
import { useStartFlow } from "./start/useStartFlow";

/* The /start flow: three steps, one decision each. The step lives in `?step=` and
   `clampStep` says how far the state allows. The rules are in lib/startFlow.ts and the
   upload and polling in pages/start/useStartFlow.ts. This file is the page. */

const STEP_TITLES = ["Upload the contract", "Say which side you are", "Confirm the scope"] as const;

const SAMPLES = [
  { id: "secondment", title: "Services and secondment agreement", description: "Two Indian companies, 14 clauses, about 1,300 words." },
  { id: "licence", title: "Software licence agreement", description: "Being prepared. Not available yet.", disabled: true },
];

const BLOCKED: Record<Blocker, string | null> = {
  upload: "Upload a contract to begin.",
  checking: "Checking your file.",
  reading: "Still reading your document.",
  "read-failed": null,
  role: "Choose your role to continue.",
  party: "Choose a party, or None of these, to continue.",
};

const REFUSAL_ZONE: Record<string, DropzoneState> = {
  unsupported_type: "error-type",
  too_large: "error-size",
  scanned: "error-scanned",
  protected: "error-protected",
};

function zoneOf(u: UploadState, dragging: boolean): DropzoneState {
  if (u.status === "validating" || u.status === "uploaded") return u.status;
  if (u.status === "error") return REFUSAL_ZONE[u.code] ?? "idle";
  return dragging ? "drag-over" : "idle";
}

export default function Start() {
  const { mock } = useSession();
  const sampleMode = !!mock?.sampleMode;
  const { flow, dispatch, parties, fileMeta, upload, retry, start, starting, startFailed } = useStartFlow();
  const [params, setParams] = useSearchParams();
  const urlStep = parseStep(params.get("step"));
  const step = clampStep(flow, urlStep);
  const heading = useRef<HTMLHeadingElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const shownStep = useRef(step);
  const sampleStarted = useRef(false);
  const [dragging, setDragging] = useState(false);
  const [sampleChoice, setSampleChoice] = useState<string | null>(null);

  // Whole objects and not updater functions: the setter keeps the parameters of the render it came from, and a callback that outlives its render would put the sample parameter back.
  const goTo = (s: Step) => setParams({ step: String(s) });

  // A link to a step that is out of reach is corrected with a replace, so Back does not trap the user.
  useEffect(() => {
    if (step !== urlStep) setParams({ step: String(step) }, { replace: true });
  }, [step, urlStep, setParams]);

  // A change of step moves focus to the new step heading and does not scroll.
  useEffect(() => {
    if (shownStep.current === step) return;
    shownStep.current = step;
    heading.current?.focus({ preventScroll: true });
  }, [step]);

  /* "Try the sample contract" links here with ?sample=secondment. Read it once and drop it, so a reload does not upload again. */
  useEffect(() => {
    const id = params.get("sample");
    if (!id || sampleStarted.current) return;
    sampleStarted.current = true;
    setParams({}, { replace: true });
    if (SAMPLES.some((x) => x.id === id && !x.disabled)) void upload({ sampleId: id }, () => goTo(2));
  }, []);

  const blocker = nextBlocker(flow, step);
  const hint = blocker ? (blocker === "upload" && sampleMode ? "Choose a sample contract to begin." : BLOCKED[blocker]) : null;
  const upErr = flow.upload.status === "error" ? flow.upload.code : null;
  const suggested = suggestedParty(flow.role, parties.length);
  const ordered = suggested === null ? parties : [parties[suggested], ...parties.filter((_, i) => i !== suggested)];
  const partyState = flow.parse === "running" ? "loading" : parties.length === 0 ? "unresolved" : "choices";
  const summary = <Summary flow={flow} fileMeta={fileMeta} parties={parties} variant="list" />;

  return (
    <div className="py-12 md:py-16 lg:py-20">
      <title>Review a contract | ClauseAnchor</title>
      <Container>
        <MarginGrid
          margin={
            <div>
              <p className="t-overline tabular-nums" style={{ color: "var(--ink-secondary)" }}>
                Step {step} of 3
              </p>
              <ol className="mt-3 hidden flex-col gap-2 text-[14px] leading-[20px] lg:flex">
                {STEP_TITLES.map((t, i) => (
                  <li key={t} aria-current={i + 1 === step ? "step" : undefined} style={{ color: i + 1 === step ? "var(--ink-primary)" : "var(--ink-secondary)", fontWeight: i + 1 === step ? 600 : 400 }}>
                    {t}
                  </li>
                ))}
              </ol>
            </div>
          }
          aside={
            <aside aria-label="Your choices" className="hidden xl:block">
              <p className="t-overline mb-4" style={{ color: "var(--ink-secondary)" }}>Your choices</p>
              {summary}
            </aside>
          }
        >
          <div className="flex max-w-[640px] flex-col gap-8">
            <h1 className="t-display-md">Review a contract</h1>

            <section aria-labelledby="step-title" className="flex flex-col gap-6">
              <h2 id="step-title" ref={heading} tabIndex={-1} className="text-[22px] font-semibold leading-[30px]" style={{ fontFamily: "var(--font-serif)", color: "var(--ink-primary)" }}>
                {STEP_TITLES[step - 1]}
              </h2>

              {step === 1 && (
                <>
                  {sampleMode ? (
                    <div role="radiogroup" aria-label="Sample contracts" className="flex flex-col gap-3">
                      <NoticeBanner variant="sample-mode" />
                      {SAMPLES.map((s) => (
                        <RadioCard
                          key={s.id}
                          name="sample"
                          value={s.id}
                          title={s.title}
                          description={s.description}
                          icon={<FileIcon size={18} />}
                          state={s.disabled ? "disabled" : undefined}
                          checked={sampleChoice === s.id}
                          onSelect={() => {
                            setSampleChoice(s.id);
                            void upload({ sampleId: s.id }, () => goTo(2));
                          }}
                        />
                      ))}
                    </div>
                  ) : (
                    <>
                      <div
                        onDragOver={(e) => {
                          e.preventDefault();
                          setDragging(true);
                        }}
                        onDragLeave={() => setDragging(false)}
                        onDrop={(e) => {
                          e.preventDefault();
                          setDragging(false);
                          const file = e.dataTransfer.files[0];
                          if (file && flow.upload.status !== "validating") void upload({ file });
                        }}
                      >
                        <UploadDropzone
                          state={zoneOf(flow.upload, dragging)}
                          fileName={flow.upload.status === "idle" ? "" : flow.upload.fileName}
                          fileMeta={fileMeta}
                          onChoose={() => fileInput.current?.click()}
                          onReplace={() => fileInput.current?.click()}
                        />
                        <input
                          ref={fileInput}
                          type="file"
                          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                          className="sr-only"
                          tabIndex={-1}
                          aria-label="Choose a contract file"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) void upload({ file });
                            e.target.value = "";
                          }}
                        />
                      </div>
                      {upErr === "network" && <ErrorCard message="Could not reach the server. Check your connection and try again." code="ERR_NETWORK" onRetry={retry} />}
                      <p className="text-[13px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
                        Your contract is processed in memory and deleted within 60 minutes.
                      </p>
                      <div>
                        <Button variant="secondary" onClick={() => void upload({ sampleId: "secondment" }, () => goTo(2))}>
                          Try the sample contract
                        </Button>
                      </div>
                    </>
                  )}
                </>
              )}

              {step === 2 && (
                <>
                  <RoleSelector value={flow.role} hideLegend onChange={(role) => dispatch({ type: "set-role", role })} />
                  {flow.parse === "failed" ? (
                    <ErrorCard title="We could not read your document" message="Try again, or go back and choose a different file." code="ERR_PARSE" onRetry={retry} />
                  ) : (
                    <PartyBindingField
                      state={partyState}
                      parties={ordered}
                      value={flow.party}
                      none={flow.partyNone}
                      suggested={suggested === null ? null : parties[suggested].id}
                      onChange={(party) => dispatch({ type: "set-party", party })}
                      onNone={() => dispatch({ type: "set-party-none" })}
                    />
                  )}
                </>
              )}

              {step === 3 && (
                <>
                  <Switch
                    checked={flow.india}
                    onChange={(on) => dispatch({ type: "set-india", on })}
                    label="Review under Indian law"
                    description="Adds review flags that cite Indian statutes and passages from Indian judgments. Turn off if the contract is under another country's law."
                  />
                  <NoticeBanner variant="review-scope" />
                  <NoticeBanner variant="legal-scope" />
                  <div className="xl:hidden">{summary}</div>
                </>
              )}
            </section>

            {startFailed && <ErrorCard message="Could not reach the server. Check your connection and try again." code="ERR_NETWORK" onRetry={() => void start()} />}

            <div className="flex flex-col gap-3">
              {step < 3 && (
                <div className="xl:hidden">
                  <Summary flow={flow} fileMeta={fileMeta} parties={parties} variant="line" />
                </div>
              )}
              <div className="flex flex-wrap items-center gap-3">
                {step > 1 && (
                  <Button variant="secondary" size="l" onClick={() => goTo((step - 1) as Step)}>
                    Back
                  </Button>
                )}
                {step < 3 ? (
                  <Button size="l" state={blocker ? "disabled" : undefined} onClick={() => goTo((step + 1) as Step)}>
                    Next
                  </Button>
                ) : (
                  <Button size="l" state={starting ? "loading" : undefined} onClick={() => void start()}>
                    Start review
                  </Button>
                )}
              </div>
              <p aria-live="polite" className="min-h-[20px] text-[13px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
                {hint}
              </p>
            </div>
          </div>
        </MarginGrid>
      </Container>
    </div>
  );
}
