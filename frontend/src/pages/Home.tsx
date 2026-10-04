import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router";
import { client } from "../api/client";
import { ApiError, type Document, type Role } from "../api/types";
import { buildOffsetIndex, sliceCp } from "../lib/offsets";
import { useSession } from "../app/session";
import Button from "../components/Button";
import NoticeBanner from "../components/NoticeBanner";
import UploadDropzone, { type DropzoneState } from "../components/UploadDropzone";
import RoleSelector, { type RoleKey } from "../components/RoleSelector";
import Switch from "../components/Switch";
import PartyBindingField, { type PartyChoice } from "../components/PartyBindingField";
import RadioCard from "../components/RadioCard";
import ErrorCard from "../components/ErrorCard";
import { BracketPairIcon, CheckIcon, CloseIcon, FileIcon, PilcrowIcon, SectionIcon } from "../components/icons";

const ROLE_FROM_KEY: Record<RoleKey, Role> = {
  buyer: "buyer_customer",
  supplier: "supplier_vendor",
  employer: "employer",
  employee: "employee",
  licensor: "licensor",
  licensee: "licensee",
  other: "other",
};

/* Which party a role usually maps to in a two-party agreement: first or second named. */
const DEFAULT_PARTY_INDEX: Partial<Record<RoleKey, number>> = { buyer: 0, employer: 0, licensee: 0, supplier: 1, employee: 1, licensor: 1 };

const STEPS: { icon: ReactNode; title: string; line: string }[] = [
  { icon: <SectionIcon size={20} />, title: "Upload", line: "A PDF or DOCX with selectable text." },
  { icon: <PilcrowIcon size={20} />, title: "Tell us your side", line: "Your role decides how each clause reads for you." },
  { icon: <BracketPairIcon size={20} />, title: "Read the marked-up contract", line: "Every finding points to exact text you can check." },
];

const DOES = [
  "Finds clauses in 46 listed categories",
  "Quotes your contract word for word, with character offsets",
  "Shows passages from published Indian judgments",
  "Shows how confident it is, and when it is not",
];
const DOES_NOT = [
  "Give legal advice",
  "Predict how a court will decide",
  "Write replacement clauses",
  "Store your contract after the session",
];

const SAMPLES = [
  { id: "secondment", title: "Services and secondment agreement", description: "Two Indian companies, 14 clauses, about 1,300 words." },
  { id: "licence", title: "Software licence agreement", description: "Being prepared. Not available yet.", disabled: true },
];

function formatSize(bytes: number) {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export default function Home() {
  const navigate = useNavigate();
  const { ensureToken, setDoc, mock } = useSession();
  const sample = !!mock?.sampleMode;
  const fileInput = useRef<HTMLInputElement>(null);

  const [zone, setZone] = useState<DropzoneState>("idle");
  const [fileName, setFileName] = useState("");
  const [fileMeta, setFileMeta] = useState("");
  const [networkError, setNetworkError] = useState<null | (() => void)>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [doc, setDocument] = useState<Document | null>(null);
  const [roleKey, setRoleKey] = useState<RoleKey>("employee");
  const [india, setIndia] = useState(true);
  const [party, setParty] = useState<string | null>(null);
  const [partyTouched, setPartyTouched] = useState(false);
  const [partyNone, setPartyNone] = useState(false);
  const [starting, setStarting] = useState(false);
  const [sampleChoice, setSampleChoice] = useState<string | null>(null);

  const parties: (PartyChoice & { nodeId: string })[] = useMemo(() => {
    if (!doc?.source_text) return [];
    const index = buildOffsetIndex(doc.source_text);
    return doc.nodes
      .filter((n) => n.kind === "party")
      .map((n) => {
        const text = sliceCp(doc.source_text ?? "", index, n.start, n.end);
        return { nodeId: n.id, name: text.split(",")[0], quote: `“${text}”`, start: n.start, end: n.end };
      });
  }, [doc]);

  /* Pick the usual party for the role until the user chooses one. */
  useEffect(() => {
    if (partyTouched || parties.length === 0) return;
    const i = DEFAULT_PARTY_INDEX[roleKey];
    setParty(i === undefined ? null : parties[i]?.name ?? null);
    setPartyNone(false);
  }, [roleKey, parties, partyTouched]);

  async function pollParse(token: string, id: string, jobId: string) {
    for (;;) {
      const job = await client.getJob(token, jobId);
      if (job.status === "succeeded") break;
      if (job.status === "failed" || job.status === "cancelled") throw new ApiError("network", "Reading the document did not finish.");
      await new Promise((r) => setTimeout(r, 450));
    }
    setDocument(await client.getDocument(token, id));
  }

  async function upload(input: { file: File } | { sampleId: string }) {
    setNetworkError(null);
    setDocument(null);
    setDocId(null);
    setPartyTouched(false);
    setPartyNone(false);
    if ("file" in input) {
      setFileName(input.file.name);
      setFileMeta(formatSize(input.file.size));
      setZone("validating");
    }
    try {
      const token = await ensureToken();
      const { document, job } = await client.uploadDocument(token, input);
      setDocId(document.id);
      setDoc(document.id, { parseJobId: job.id });
      if ("file" in input) setZone("uploaded");
      await pollParse(token, document.id, job.id);
    } catch (e) {
      const code = e instanceof ApiError ? e.code : "network";
      const map: Partial<Record<string, DropzoneState>> = {
        unsupported_type: "error-type",
        too_large: "error-size",
        scanned: "error-scanned",
        protected: "error-protected",
      };
      const z = map[code];
      if (z) setZone(z);
      else {
        setZone("idle");
        setNetworkError(() => () => upload(input));
      }
    }
  }

  function onFiles(files: FileList | null) {
    const f = files?.[0];
    if (f) void upload({ file: f });
  }

  async function start() {
    if (!docId) return;
    setStarting(true);
    setNetworkError(null);
    try {
      const token = await ensureToken();
      const role = ROLE_FROM_KEY[roleKey];
      const chosen = partyNone ? null : parties.find((p) => p.name === party)?.nodeId ?? null;
      await client.setParty(token, docId, { role, party_node_id: chosen });
      const job = await client.startAnalysis(token, docId, { jurisdiction_scope: india ? "india_review" : "unspecified" });
      setDoc(docId, { analysisJobId: job.id, role, partyNodeId: chosen });
      navigate(`/review/${docId}`, { viewTransition: true });
    } catch {
      setStarting(false);
      setNetworkError(() => start);
    }
  }

  const parsing = !!docId && !doc;
  const ready = !!doc && doc.status === "parsed";

  return (
    <div>
      {/* Hero */}
      <section className="mx-auto w-full max-w-[1120px] px-5 pb-10 pt-12 md:px-8 md:pt-20">
        <p className="font-mono text-[12px] tracking-[0.08em] uppercase" style={{ color: "var(--ink-tertiary)" }}>
          § Contract review, India
        </p>
        <h1
          className="mt-4 max-w-[20ch] text-[32px] leading-[40px] md:text-[44px] md:leading-[54px]"
          style={{ fontFamily: "var(--font-serif)", fontWeight: 500, color: "var(--ink-primary)", letterSpacing: "-0.01em" }}
        >
          Read your contract with a careful second pair of eyes.
        </h1>
        <p className="mt-5 max-w-[62ch] text-[17px] leading-[28px]" style={{ color: "var(--ink-secondary)" }}>
          ClauseAnchor points to the clauses that matter, shows real Indian case law about them, and tells you when a lawyer should look.
        </p>

        <ol className="mt-10 grid gap-0 md:grid-cols-3" style={{ borderTop: "1px solid var(--rule-strong)" }}>
          {STEPS.map((s, i) => (
            <li
              key={s.title}
              className="flex gap-3 py-5 md:px-5 md:first:pl-0"
              style={{ borderBottom: "1px solid var(--rule-default)", borderLeft: i > 0 ? undefined : undefined }}
            >
              <span className="font-mono text-[12px]" style={{ color: "var(--ink-tertiary)", paddingTop: 3 }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <span style={{ color: "var(--anchor-600)", paddingTop: 1 }}>{s.icon}</span>
              <span className="flex flex-col gap-1">
                <span className="text-[15px] font-semibold" style={{ color: "var(--ink-primary)" }}>{s.title}</span>
                <span className="text-[14px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>{s.line}</span>
              </span>
            </li>
          ))}
        </ol>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <ScopeCard title="What it does" items={DOES} kind="does" />
          <ScopeCard title="What it does not do" items={DOES_NOT} kind="not" />
        </div>
      </section>

      {/* Flow */}
      <section aria-labelledby="start-title" style={{ background: "var(--paper-sunken)", borderTop: "1px solid var(--rule-default)", borderBottom: "1px solid var(--rule-default)" }}>
        <div className="mx-auto flex w-full max-w-[640px] flex-col gap-6 px-5 py-12">
          <h2 id="start-title" className="text-[24px] leading-[32px]" style={{ fontFamily: "var(--font-serif)", fontWeight: 600, color: "var(--ink-primary)" }}>
            Start a review
          </h2>
          <NoticeBanner variant="review-scope" />

          {networkError && (
            <ErrorCard message="Could not reach the server. Check your connection and try again." code="ERR_NETWORK" onRetry={networkError} />
          )}

          {sample ? (
            <div className="flex flex-col gap-3">
              <NoticeBanner variant="sample-mode" />
              <h3 className="text-[18px] font-semibold" style={{ color: "var(--ink-primary)" }}>Try a sample contract</h3>
              <div role="radiogroup" aria-label="Sample contracts" className="flex flex-col gap-3">
                {SAMPLES.map((s) => (
                  <RadioCard
                    key={s.id}
                    title={s.title}
                    description={s.description}
                    icon={<FileIcon size={18} />}
                    state={s.disabled ? "disabled" : sampleChoice === s.id ? "selected" : "unselected"}
                    name="sample"
                    onSelect={() => {
                      if (s.disabled) return;
                      setSampleChoice(s.id);
                      void upload({ sampleId: s.id });
                    }}
                  />
                ))}
              </div>
            </div>
          ) : (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                if (zone !== "validating") setZone("drag-over");
              }}
              onDragLeave={() => zone === "drag-over" && setZone(docId ? "uploaded" : "idle")}
              onDrop={(e) => {
                e.preventDefault();
                onFiles(e.dataTransfer.files);
              }}
            >
              <UploadDropzone
                state={zone}
                fileName={fileName}
                fileMeta={doc ? `${fileMeta}, ${Math.max(...doc.nodes.map((n) => n.page), 1)} pages` : fileMeta}
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
                  onFiles(e.target.files);
                  e.target.value = "";
                }}
              />
            </div>
          )}

          <RoleSelector value={roleKey} onChange={setRoleKey} />

          <Switch
            checked={india}
            onChange={setIndia}
            label="Review under Indian law"
            description="Adds review flags that cite Indian statutes and passages from Indian judgments. Turn off if the contract is under another country's law."
          />

          {(parsing || ready) && (
            <div aria-live="polite">
              <PartyBindingField
                state={parsing ? "loading" : partyNone || parties.length === 0 ? "unresolved" : "choices"}
                parties={parties}
                value={party}
                onChange={(n) => {
                  setParty(n);
                  setPartyTouched(true);
                  setPartyNone(false);
                }}
                onNone={() => {
                  setPartyNone(true);
                  setPartyTouched(true);
                }}
              />
              {partyNone && (
                <div className="mt-2">
                  <Button variant="tertiary" size="s" onClick={() => setPartyNone(false)}>
                    Choose a party after all
                  </Button>
                </div>
              )}
            </div>
          )}

          <div className="flex flex-col gap-2">
            <div>
              <Button variant="primary" size="l" state={!ready ? "disabled" : starting ? "loading" : undefined} onClick={start}>
                Start review
              </Button>
            </div>
            <p className="text-[13px]" style={{ color: "var(--ink-tertiary)" }} aria-live="polite">
              {ready
                ? "Your contract is ready. The review takes about a minute on real documents."
                : parsing
                  ? "Reading your document."
                  : sample
                    ? "Choose a sample contract to begin."
                    : "Upload a contract to begin."}
            </p>
          </div>

          <NoticeBanner variant="legal-scope" />
          <NoticeBanner variant="privacy" />
        </div>
      </section>

    </div>
  );
}

function ScopeCard({ title, items, kind }: { title: string; items: string[]; kind: "does" | "not" }) {
  return (
    <div style={{ background: "var(--paper-sheet)", border: "1px solid var(--rule-default)", borderRadius: "var(--radius-lg)", padding: "18px 20px" }}>
      <h2 className="text-[16px] font-semibold" style={{ color: "var(--ink-primary)" }}>{title}</h2>
      <ul className="mt-3 flex flex-col gap-2">
        {items.map((i) => (
          <li key={i} className="flex items-start gap-2 text-[14px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
            <span style={{ color: kind === "does" ? "var(--anchor-600)" : "var(--ink-tertiary)", paddingTop: 1 }}>
              {kind === "does" ? <CheckIcon size={16} /> : <CloseIcon size={16} />}
            </span>
            {i}
          </li>
        ))}
      </ul>
    </div>
  );
}
