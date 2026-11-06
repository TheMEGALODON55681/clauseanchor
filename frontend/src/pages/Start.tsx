import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { available } from "../api/client";
import Button from "../components/Button";
import CategoryPicker from "../components/CategoryPicker";
import ErrorCard from "../components/ErrorCard";
import { Container, MarginGrid } from "../components/Layout";
import NoticeBanner from "../components/NoticeBanner";
import PartyBindingField from "../components/PartyBindingField";
import RoleSelector from "../components/RoleSelector";
import Switch from "../components/Switch";
import UploadDropzone, { type DropzoneState } from "../components/UploadDropzone";
import { canRetry, clampStep, nextBlocker, parseStep, suggestedParty, type Blocker, type FlowError, type FlowState, type Step } from "../lib/startFlow";
import Summary from "./start/Summary";
import { useStartFlow } from "./start/useStartFlow";

/* The /start flow: three steps, one decision each. The step lives in `?step=` and
   `clampStep` says how far the state allows. The rules are in lib/startFlow.ts and the
   upload and polling in pages/start/useStartFlow.ts. This file is the page. */

const STEP_TITLES = ["Upload the contract", "Say which side you are", "Confirm the scope"] as const;

const BLOCKED: Record<Blocker, string | null> = {
  upload: "Upload a contract to begin.",
  checking: "Checking your file.",
  reading: "Still reading your document.",
  "read-failed": null,
  role: "Choose your role to continue.",
  party: "Choose a party, or None of these, to continue.",
  categories: "Choose at least one category to start the review.",
};

const ZONES: Partial<Record<FlowError["code"], DropzoneState>> = {
  unsupported_type: "error-type",
  too_large: "error-size",
  scanned: "error-scanned",
  protected: "error-protected",
};

/** The error on screen: a refused upload, or a file that was taken and could not be read. */
const failureOf = (f: FlowState): FlowError | null => (f.upload.status === "error" ? f.upload.error : f.parse === "failed" ? f.parseError : null);

/* A failure the user can try again shows as a card with Try again, and the zone stays as it was. Any other failure is the zone itself, with the sentence in it. */
function zoneOf(f: FlowState, dragging: boolean, retryable: boolean): DropzoneState {
  const e = failureOf(f);
  if (e && !retryable) return ZONES[e.code] ?? "error-other";
  if (f.upload.status === "validating" || f.upload.status === "uploaded") return f.upload.status;
  return dragging ? "drag-over" : "idle";
}

export default function Start() {
  const { flow, dispatch, parties, fileMeta, upload, retry, start, starting, startError } = useStartFlow();
  const [params, setParams] = useSearchParams();
  const urlStep = parseStep(params.get("step"));
  const step = clampStep(flow, urlStep);
  const heading = useRef<HTMLHeadingElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const shownStep = useRef(step);
  const [dragging, setDragging] = useState(false);

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

  const blocker = nextBlocker(flow, step);
  const hint = blocker ? BLOCKED[blocker] : null;
  const failure = failureOf(flow);
  const retryable = canRetry(flow);
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
                      state={zoneOf(flow, dragging, retryable)}
                      fileName={flow.upload.status === "idle" ? "" : flow.upload.fileName}
                      fileMeta={fileMeta}
                      message={failure?.message}
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
                  {failure && retryable && <ErrorCard message={failure.message} code={failure.apiCode ?? "ERR_NETWORK"} onRetry={retry} />}
                  <p className="text-[13px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
                    Your contract is processed in memory and deleted within 60 minutes.
                  </p>
                  {/* The prepared sample needs the sample endpoint of 3-C. */}
                  {!available.samples && (
                    <p className="text-[13px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
                      The sample contract is not available in this build yet.
                    </p>
                  )}
                </>
              )}

              {step === 2 && (
                <>
                  {!available.partyBinding && <NoticeBanner variant="not-available" text="This build does not use your side yet. Findings carry no burden or benefit label." />}
                  <RoleSelector value={flow.role} hideLegend hint={available.partyBinding ? undefined : null} onChange={(role) => dispatch({ type: "set-role", role })} />
                  <PartyBindingField
                    state={partyState}
                    parties={ordered}
                    value={flow.party}
                    none={flow.partyNone}
                    suggested={suggested === null ? null : parties[suggested].id}
                    onChange={(party) => dispatch({ type: "set-party", party })}
                    onNone={() => dispatch({ type: "set-party-none" })}
                  />
                </>
              )}

              {step === 3 && (
                <>
                  <CategoryPicker selected={flow.categories} onToggle={(id) => dispatch({ type: "toggle-category", id })} onSet={(ids) => dispatch({ type: "set-categories", ids })} />
                  <Switch
                    checked={flow.india}
                    onChange={(on) => dispatch({ type: "set-india", on })}
                    label="Include India-specific categories"
                    description="Adds the five India-specific categories. In this build they show as not yet available."
                  />
                  <NoticeBanner variant="review-scope" />
                  <NoticeBanner variant="legal-scope" />
                  <div className="xl:hidden">{summary}</div>
                </>
              )}
            </section>

            {startError && <ErrorCard message={startError.message} code={startError.apiCode ?? "ERR_NETWORK"} onRetry={startError.retryable ? () => void start() : undefined} />}

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
                  <Button size="l" state={starting ? "loading" : blocker ? "disabled" : undefined} onClick={() => void start()}>
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
