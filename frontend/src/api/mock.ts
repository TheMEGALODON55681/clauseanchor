/* Mock adapter. Simulates the backend in memory so the UI can be built and
   reviewed before the real API exists. Swap it for the HTTP adapter in client.ts. */

import type { ApiClient, MockSettings } from "./client";
import { CATALOGUE } from "./catalogue";
import { SAMPLE_CONTRACT, SAMPLE_FILENAME } from "./contract";
import {
  ApiError,
  type Analysis,
  type Category,
  type Clause,
  type DocNode,
  type Document,
  type Evaluations,
  type Job,
  type JobStatus,
  type ManualReview,
  type Passage,
  type Polarity,
  type ReviewUnit,
  type Role,
  type RuleFlag,
  type Session,
  type Span,
} from "./types";
import { buildOffsetIndex, sliceCp, toCodePoint } from "../lib/offsets";

/* ------------------------------------------------------------------ */
/* Settings                                                            */
/* ------------------------------------------------------------------ */

export const settings: MockSettings = {
  sampleMode: false,
  partialRun: false,
  failAnalysis: false,
  failNextRequest: false,
  shortSession: false,
};

/* ------------------------------------------------------------------ */
/* Text, hashing and spans                                             */
/* ------------------------------------------------------------------ */

const TEXT = SAMPLE_CONTRACT;
const INDEX = buildOffsetIndex(TEXT);

function fakeSha(text: string): string {
  let h1 = 0x811c9dc5;
  let h2 = 0x01000193;
  for (let i = 0; i < text.length; i++) {
    h1 = Math.imul(h1 ^ text.charCodeAt(i), 16777619) >>> 0;
    h2 = Math.imul(h2 + text.charCodeAt(i), 2246822507) >>> 0;
  }
  return (h1.toString(16) + h2.toString(16)).padEnd(64, "0").slice(0, 64);
}

const SHA = fakeSha(TEXT);
const TEMPLATE_DOC = "doc_template";

/** Locate a snippet ONCE at load and store code point offsets. */
function locate(snippet: string): { start: number; end: number } {
  const u16 = TEXT.indexOf(snippet);
  if (u16 < 0) throw new Error(`Mock span not found: ${snippet.slice(0, 40)}`);
  const start = toCodePoint(INDEX, u16);
  const end = toCodePoint(INDEX, u16 + snippet.length);
  if (sliceCp(TEXT, INDEX, start, end) !== snippet) throw new Error("Mock span offsets do not round-trip");
  return { start, end };
}

function makeSpan(snippet: string, docId = TEMPLATE_DOC): Span {
  const { start, end } = locate(snippet);
  return { doc_id: docId, text_sha256: SHA, start, end, text: snippet };
}

/* ------------------------------------------------------------------ */
/* Findings                                                            */
/* ------------------------------------------------------------------ */

type Favours = "company" | "provider" | "mutual" | "neutral";

type Finding = {
  category_id: string;
  snippet: string;
  kind: "accepted" | "review_candidate";
  band: "higher" | "review" | "unvalidated";
  confidence: number | null;
  favours: Favours;
  flags?: RuleFlag[];
  passages?: Omit<Passage, "id" | "rank">[];
};

const FLAG_S27: RuleFlag = {
  rule_id: "IN-ICA-27",
  version: "1.0",
  label_key: "restraint_of_trade",
  note: "Restraint-of-trade review: Section 27, Indian Contract Act 1872. Post-termination restraints are reviewed closely.",
  statute_citations: ["Section 27, Indian Contract Act 1872"],
  authority_ids: ["auth_s27_1"],
  evidence_spans: [],
  scope_status: "applies",
};

const FLAG_S74: RuleFlag = {
  rule_id: "IN-ICA-74",
  version: "1.0",
  label_key: "liquidated_damages",
  note: "Liquidated damages review: Section 74, Indian Contract Act 1872. Courts look at reasonable compensation up to the stated amount.",
  statute_citations: ["Section 74, Indian Contract Act 1872"],
  authority_ids: ["auth_s74_1"],
  evidence_spans: [],
  scope_status: "applies",
};

const FLAG_STAMP: RuleFlag = {
  rule_id: "IN-STAMP-ARB",
  version: "1.0",
  label_key: "stamp_review",
  note: "Stamping review: whether this agreement is duly stamped can affect how its arbitration clause is acted on. Verify with counsel.",
  statute_citations: ["Indian Stamp Act 1899"],
  authority_ids: ["auth_stamp_1"],
  evidence_spans: [],
  scope_status: "verify",
};

function passage(
  judgment: string,
  caseName: string,
  court: string,
  year: number | null,
  text: string,
  authority: "reviewed" | "not_reviewed" | "overruled",
): Omit<Passage, "id" | "rank"> {
  return {
    judgment_id: judgment,
    case_name: caseName,
    court,
    year,
    citation: "[Placeholder citation]",
    source_url: "https://example.org/placeholder-judgment",
    start: 0,
    end: text.length,
    text,
    authority_status: authority,
    provenance_status: "placeholder",
  };
}

const FINDINGS: Finding[] = [
  { category_id: "document_name", snippet: "SERVICES AND SECONDMENT AGREEMENT", kind: "accepted", band: "higher", confidence: 0.97, favours: "neutral" },
  {
    category_id: "parties",
    snippet: "Sample Traders Pvt. Ltd., a company incorporated under the Companies Act, 2013",
    kind: "accepted",
    band: "higher",
    confidence: 0.95,
    favours: "neutral",
  },
  { category_id: "agreement_date", snippet: "made at New Delhi on 4 March 2026", kind: "accepted", band: "higher", confidence: 0.93, favours: "neutral" },
  { category_id: "effective_date", snippet: "This Agreement shall come into force on 1 April 2026", kind: "accepted", band: "higher", confidence: 0.92, favours: "neutral" },
  { category_id: "expiration_date", snippet: "expiring on 31 March 2028", kind: "accepted", band: "unvalidated", confidence: null, favours: "neutral" },
  {
    category_id: "renewal_term",
    snippet: "this Agreement shall automatically renew for successive periods of one (1) year each",
    kind: "accepted",
    band: "higher",
    confidence: 0.9,
    favours: "neutral",
  },
  {
    category_id: "notice_period_renewal",
    snippet: "unless either Party gives the other written notice of non-renewal at least ninety (90) days before the end of the then current term",
    kind: "accepted",
    band: "higher",
    confidence: 0.88,
    favours: "mutual",
  },
  {
    category_id: "governing_law",
    snippet: "This Agreement shall be governed by and construed in accordance with the laws of India.",
    kind: "accepted",
    band: "higher",
    confidence: 0.96,
    favours: "neutral",
  },
  {
    category_id: "non_compete",
    snippet:
      "During the term of this Agreement and for a period of two (2) years after its termination or expiry, the Provider shall not, directly or indirectly, provide warehouse management or logistics services to any business that competes with the Company anywhere in India.",
    kind: "accepted",
    band: "higher",
    confidence: 0.94,
    favours: "company",
    flags: [FLAG_S27],
    passages: [
      passage(
        "j_001",
        "Placeholder Logistics Ltd. v. Sample Carriers",
        "Supreme Court of India",
        2019,
        "A covenant which restrains a party from carrying on a lawful trade after the contract has ended must be read narrowly, and the court will not enforce a restriction wider in area or duration than is necessary.",
        "reviewed",
      ),
      passage(
        "j_002",
        "Example Freight v. Illustrative Stores",
        "High Court of Delhi",
        2016,
        "A restraint operating during the term of the agreement stands on a different footing from one that operates after the agreement has come to an end.",
        "overruled",
      ),
    ],
  },
  {
    category_id: "competitive_restriction_exception",
    snippet:
      "The restriction in Clause 4.1 shall not apply to services that the Provider was already providing to an existing client on the Effective Date",
    kind: "review_candidate",
    band: "review",
    confidence: 0.52,
    favours: "provider",
  },
  {
    category_id: "no_solicit_employees",
    snippet:
      "neither Party shall solicit, recruit or employ any employee of the other Party who was involved in the Services, without the prior written consent of that other Party",
    kind: "accepted",
    band: "higher",
    confidence: 0.91,
    favours: "mutual",
    passages: [
      passage(
        "j_003",
        "Specimen Tech v. Placeholder Staffing",
        "High Court of Bombay",
        2021,
        "A promise not to solicit the employees of the other party is examined separately from a promise not to compete, and is read with the purpose it serves.",
        "not_reviewed",
      ),
    ],
  },
  {
    category_id: "ip_ownership_assignment",
    snippet:
      "The Provider hereby assigns to the Company, absolutely and without further payment, all present and future intellectual property rights in the Work Product.",
    kind: "accepted",
    band: "higher",
    confidence: 0.93,
    favours: "company",
  },
  {
    category_id: "liquidated_damages",
    snippet:
      "the Provider shall pay the Company, as liquidated damages and not as a penalty, an amount equal to five percent (5%) of the monthly fee for each week of delay, subject to a maximum of twenty percent (20%) of the monthly fee",
    kind: "accepted",
    band: "higher",
    confidence: 0.92,
    favours: "company",
    flags: [FLAG_S74],
    passages: [
      passage(
        "j_004",
        "Illustrative Builders v. Sample Housing Board",
        "Supreme Court of India",
        2015,
        "Where a sum is named in the contract as payable on breach, the party complaining of the breach is entitled to reasonable compensation not exceeding the amount so named.",
        "reviewed",
      ),
    ],
  },
  {
    category_id: "cap_on_liability",
    snippet:
      "the total liability of each Party under or in connection with this Agreement shall not exceed the total fees paid by the Company in the twelve (12) months before the event giving rise to the claim",
    kind: "accepted",
    band: "higher",
    confidence: 0.9,
    favours: "mutual",
  },
  {
    category_id: "cap_on_liability",
    snippet: "Neither Party shall be liable for any indirect or consequential loss, or for loss of profits",
    kind: "accepted",
    band: "higher",
    confidence: 0.87,
    favours: "mutual",
  },
  {
    category_id: "uncapped_liability",
    snippet:
      "Nothing in this Agreement limits either Party's liability for breach of Clause 6 (Confidentiality and Data Protection), for fraud, or for death or personal injury caused by negligence, and such liability shall be unlimited.",
    kind: "accepted",
    band: "higher",
    confidence: 0.89,
    favours: "mutual",
  },
  {
    category_id: "termination_for_convenience",
    snippet:
      "The Company may terminate this Agreement for convenience at any time by giving the Provider not less than sixty (60) days' written notice.",
    kind: "accepted",
    band: "higher",
    confidence: 0.95,
    favours: "company",
  },
  {
    category_id: "audit_rights",
    snippet:
      "The Company, or an independent auditor appointed by it, may on reasonable notice inspect and audit the Provider's records relating to the Services and the fees charged",
    kind: "accepted",
    band: "unvalidated",
    confidence: null,
    favours: "company",
  },
  {
    category_id: "stamping_registration",
    snippet: "The stamp duty payable on this Agreement and any counterpart shall be borne by the Provider.",
    kind: "review_candidate",
    band: "review",
    confidence: 0.48,
    favours: "company",
    flags: [FLAG_STAMP],
  },
  {
    category_id: "dispute_escalation",
    snippet: "shall first be referred to the senior management of each Party, who shall meet within fifteen (15) days to attempt to resolve it",
    kind: "review_candidate",
    band: "review",
    confidence: 0.55,
    favours: "neutral",
  },
  {
    category_id: "arbitration",
    snippet:
      "it shall be finally resolved by arbitration under the Arbitration and Conciliation Act, 1996, by a sole arbitrator appointed by mutual agreement. The seat and venue of arbitration shall be New Delhi",
    kind: "accepted",
    band: "higher",
    confidence: 0.94,
    favours: "neutral",
    flags: [FLAG_STAMP],
    passages: [
      passage(
        "j_005",
        "Sample Infra v. Placeholder Power Co.",
        "Supreme Court of India",
        2023,
        "The question of whether an instrument is sufficiently stamped is to be considered with care, and the parties may be directed to address it before the tribunal.",
        "reviewed",
      ),
    ],
  },
  {
    /* Overlaps the arbitration span on purpose: stacked underlines. */
    category_id: "seat_and_venue",
    snippet: "The seat and venue of arbitration shall be New Delhi",
    kind: "accepted",
    band: "higher",
    confidence: 0.9,
    favours: "neutral",
  },
  {
    category_id: "jurisdiction_forum",
    snippet: "the courts at New Delhi shall have exclusive jurisdiction over all matters arising out of this Agreement",
    kind: "accepted",
    band: "higher",
    confidence: 0.91,
    favours: "neutral",
  },
  {
    category_id: "anti_assignment",
    snippet: "Neither Party may assign or transfer its rights under this Agreement without the prior written consent of the other Party.",
    kind: "accepted",
    band: "higher",
    confidence: 0.9,
    favours: "mutual",
  },
  {
    category_id: "insurance",
    snippet: "The Provider shall maintain adequate insurance with a reputable insurer to cover its liabilities under this Agreement.",
    kind: "accepted",
    band: "unvalidated",
    confidence: null,
    favours: "company",
  },
];

/* Pre-compute spans once at load. Throws if any snippet does not round-trip. */
const LOCATED = FINDINGS.map((f) => ({ ...f, span: makeSpan(f.snippet) }));

/** Abstained with no candidate span. */
const ABSTAIN_NO_CANDIDATE = new Set(["non_disparagement"]);
const ALWAYS_UNAVAILABLE = new Set(["source_code_escrow"]);
const PARTIAL_UNAVAILABLE = new Set(["license_grant", "warranty_duration", "change_of_control"]);

/* ------------------------------------------------------------------ */
/* Document structure                                                  */
/* ------------------------------------------------------------------ */

type Para = { start: number; end: number; text: string };

const PARAS: Para[] = (() => {
  const out: Para[] = [];
  const re = /[^\n](?:[\s\S]*?)(?=\n\n|$)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(TEXT))) {
    const start = toCodePoint(INDEX, m.index);
    const end = toCodePoint(INDEX, m.index + m[0].length);
    out.push({ start, end, text: m[0] });
  }
  return out;
})();

function sectionPathFor(text: string, lastClause: string | null): { path: string | null; clause: string | null } {
  const heading = /^(\d+)\.\s+[A-Z][A-Z ,-]+$/.exec(text);
  if (heading) return { path: `Clause ${heading[1]}`, clause: heading[1] };
  const sub = /^(\d+)\.(\d+)/.exec(text);
  if (sub) return { path: `Clause ${sub[1]} › ${sub[1]}.${sub[2]}`, clause: sub[1] };
  if (lastClause === null) return { path: "Preamble", clause: null };
  return { path: text.startsWith("IN WITNESS") || text.startsWith("For ") ? "Signatures" : `Clause ${lastClause}`, clause: lastClause };
}

const UNITS_BASE: { id: string; start: number; end: number; section_path: string | null; kind: string }[] = (() => {
  let clause: string | null = null;
  return PARAS.map((p, i) => {
    const r = sectionPathFor(p.text, clause);
    clause = r.clause;
    const kind = /^\d+\.\s/.test(p.text) ? "heading" : /^\d+\.\d+/.test(p.text) ? "clause" : "paragraph";
    return { id: `u${i + 1}`, start: p.start, end: p.end, section_path: r.path, kind };
  });
})();

function buildNodes(): DocNode[] {
  const pages = 5;
  const per = INDEX.cpLength / pages;
  const nodes: DocNode[] = UNITS_BASE.map((u) => ({
    id: `n_${u.id}`,
    parent_id: null,
    kind: u.kind,
    start: u.start,
    end: u.end,
    page: Math.min(pages, Math.floor(u.start / per) + 1),
  }));
  const company = locate("Sample Traders Pvt. Ltd., a company incorporated under the Companies Act, 2013, having its registered office at 14 Example Road");
  const provider = locate("Example Industries Ltd., a company incorporated under the Companies Act, 2013, having its registered office at Plot 7");
  nodes.push({ id: "party_company", parent_id: null, kind: "party", ...company, page: 1 });
  nodes.push({ id: "party_provider", parent_id: null, kind: "party", ...provider, page: 1 });
  return nodes;
}

/* ------------------------------------------------------------------ */
/* In-memory store                                                     */
/* ------------------------------------------------------------------ */

type StoredDoc = {
  doc: Document;
  parseJob: Job & { startedAt: number };
  role: Role;
  party: "party_company" | "party_provider" | null;
  analysisJob: (Job & { startedAt: number; frozenAt: number | null; partial: boolean; fail: boolean }) | null;
  analysisId: string | null;
  createdAt: string;
};

const sessions = new Map<string, Session>();
const docs = new Map<string, StoredDoc>();
const jobsToDoc = new Map<string, string>();
let seq = 0;
const id = (p: string) => `${p}_${Date.now().toString(36)}${(++seq).toString(36)}`;

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

async function gate(token: string | null, ms = 260) {
  await wait(ms + Math.random() * 180);
  if (settings.failNextRequest) {
    settings.failNextRequest = false;
    throw new ApiError("network", "Could not reach the server. Check your connection and try again.");
  }
  if (token !== null) {
    const s = sessions.get(token);
    if (!s) throw new ApiError("expired", "This session has ended.");
  }
}

function getStored(docId: string): StoredDoc {
  const d = docs.get(docId);
  if (!d) throw new ApiError("not_found", "This document is no longer available.");
  return d;
}

/* ------------------------------------------------------------------ */
/* Job timeline: parsing about 2s, analysis about 12s in six stages    */
/* ------------------------------------------------------------------ */

const PARSE_MS = 2000;
export const STAGE_KEYS = ["reading", "finding_clauses", "checking_confidence", "law_review", "case_law", "final_checks"] as const;
const STAGE_BOUNDS = [0, 1200, 8000, 9000, 10000, 11200, 12000];
const ANALYSIS_MS = STAGE_BOUNDS[STAGE_BOUNDS.length - 1];
const FAIL_AT = 5200;
const TOTAL_PASSAGES = LOCATED.reduce((n, f) => n + (f.passages?.length ?? 0), 0);
const STAGE_UNITS = [5, CATALOGUE.length, CATALOGUE.length, 3, TOTAL_PASSAGES, 1];

function analysisElapsed(s: StoredDoc): number {
  const j = s.analysisJob;
  if (!j) return 0;
  const now = j.frozenAt ?? Date.now();
  return Math.min(now - j.startedAt, j.fail ? FAIL_AT : ANALYSIS_MS);
}

function categoriesDone(elapsed: number): number {
  if (elapsed < STAGE_BOUNDS[1]) return 0;
  if (elapsed >= STAGE_BOUNDS[2]) return CATALOGUE.length;
  return Math.floor(((elapsed - STAGE_BOUNDS[1]) / (STAGE_BOUNDS[2] - STAGE_BOUNDS[1])) * CATALOGUE.length);
}

function refreshAnalysisJob(s: StoredDoc) {
  const j = s.analysisJob;
  if (!j) return;
  if (j.status === "cancelled") return;
  const elapsed = analysisElapsed(s);
  if (j.fail && elapsed >= FAIL_AT) {
    j.status = "failed";
    return;
  }
  if (elapsed >= ANALYSIS_MS) {
    j.status = j.partial ? "partial" : "succeeded";
    j.stage = null;
    j.completed_units = j.total_units ?? 0;
    return;
  }
  let stage = 0;
  while (stage < STAGE_KEYS.length - 1 && elapsed >= STAGE_BOUNDS[stage + 1]) stage++;
  const frac = (elapsed - STAGE_BOUNDS[stage]) / (STAGE_BOUNDS[stage + 1] - STAGE_BOUNDS[stage]);
  j.status = "running";
  j.stage = STAGE_KEYS[stage];
  j.total_units = STAGE_UNITS[stage];
  j.completed_units = Math.floor(frac * STAGE_UNITS[stage]);
}

/* ------------------------------------------------------------------ */
/* Polarity follows the bound party, so a role change needs no re-run  */
/* ------------------------------------------------------------------ */

function polarityFor(favours: Favours, party: StoredDoc["party"]): Polarity {
  if (favours === "neutral") return "neutral";
  if (favours === "mutual") return "mixed";
  if (party === null) return "unresolved";
  const mine = party === "party_company" ? "company" : "provider";
  return favours === mine ? "protection" : "exposure";
}

function buildCategories(s: StoredDoc): Category[] {
  const j = s.analysisJob;
  if (!j) return [];
  const done = categoriesDone(analysisElapsed(s));
  const docId = s.doc.id;
  return CATALOGUE.slice(0, done).map((cat): Category => {
    const unavailable = ALWAYS_UNAVAILABLE.has(cat.id) || (j.partial && PARTIAL_UNAVAILABLE.has(cat.id));
    if (unavailable) {
      return {
        category_id: cat.id,
        status: "unavailable",
        decision_confidence: null,
        reason_code: "processing_timeout",
        search_complete: false,
        windows_done: 3,
        windows_total: 8,
        unresolved_count: 5,
        clauses: [],
      };
    }
    const found = LOCATED.filter((f) => f.category_id === cat.id);
    const clauses: Clause[] = found.map((f, i) => ({
      id: `${cat.id}_${i + 1}`,
      category_id: cat.id,
      span: { ...f.span, doc_id: docId },
      status: f.kind,
      confidence: f.confidence,
      confidence_band: f.band,
      calibration_scope: cat.support === "not_validated" ? "none" : cat.support === "pooled" ? "pooled" : "category",
      polarity: polarityFor(f.favours, s.party),
      rule_flags: (f.flags ?? []).map((fl) => ({ ...fl, evidence_spans: [{ ...f.span, doc_id: docId }] })),
      passages: (f.passages ?? []).map((p, k) => ({ ...p, id: `${cat.id}_p${k + 1}`, rank: k + 1 })),
      retrieval_status: f.passages?.length ? "complete" : "no_verified_passages",
    }));
    const accepted = clauses.some((c) => c.status === "accepted");
    const abstained = ABSTAIN_NO_CANDIDATE.has(cat.id) || (!accepted && clauses.length > 0);
    return {
      category_id: cat.id,
      status: accepted ? "found" : abstained ? "abstained" : "absent",
      decision_confidence: accepted ? Math.max(...clauses.map((c) => c.confidence ?? 0)) || null : abstained ? 0.5 : 0.93,
      reason_code: abstained ? (clauses.length ? "below_threshold" : "conflicting_windows") : null,
      search_complete: true,
      windows_done: 8,
      windows_total: 8,
      unresolved_count: 0,
      clauses,
    };
  });
}

/* ------------------------------------------------------------------ */
/* Evaluations: example numbers for layout only                        */
/* ------------------------------------------------------------------ */

function exampleRows(seed: number) {
  return CATALOGUE.map((c, i) => {
    const r = Math.abs(Math.sin((i + 1) * seed));
    if (c.support === "not_validated" || (seed > 2 && i % 5 === 3)) {
      return { category_id: c.id, support: Math.round(r * 8), precision: null, recall: null, silent_miss: null, abstention: null, weak: false };
    }
    const recall = 0.35 + r * 0.6;
    const precision = 0.5 + Math.abs(Math.cos((i + 2) * seed)) * 0.45;
    const support = 12 + Math.round(r * 140);
    return {
      category_id: c.id,
      support,
      precision: Math.round(precision * 100) / 100,
      recall: Math.round(recall * 100) / 100,
      silent_miss: Math.round((1 - recall) * 0.7 * 100) / 100,
      abstention: Math.round(r * 0.2 * 100) / 100,
      weak: recall < 0.55 || precision < 0.6,
    };
  });
}

/* ------------------------------------------------------------------ */
/* Adapter                                                             */
/* ------------------------------------------------------------------ */

function newDocument(filename: string): StoredDoc {
  const docId = id("doc");
  const ttl = settings.shortSession ? 9 * 60_000 : 60 * 60_000;
  const parseJob = { id: id("job"), kind: "parse" as const, status: "running" as JobStatus, stage: "reading", completed_units: 0, total_units: 5, startedAt: Date.now() };
  const stored: StoredDoc = {
    doc: {
      id: docId,
      filename,
      status: "parsing",
      source_text: null,
      text_sha256: null,
      nodes: [],
      warnings: [],
      expires_at: new Date(Date.now() + ttl).toISOString(),
    },
    parseJob,
    role: "employer",
    party: null,
    analysisJob: null,
    analysisId: null,
    createdAt: new Date().toISOString(),
  };
  docs.set(docId, stored);
  jobsToDoc.set(parseJob.id, docId);
  return stored;
}

function refreshParse(s: StoredDoc) {
  const j = s.parseJob;
  const elapsed = Date.now() - j.startedAt;
  if (elapsed >= PARSE_MS) {
    j.status = "succeeded";
    j.stage = null;
    j.completed_units = 5;
    if (s.doc.status === "parsing") {
      s.doc.status = "parsed";
      s.doc.source_text = TEXT;
      s.doc.text_sha256 = SHA;
      s.doc.nodes = buildNodes();
    }
  } else {
    j.completed_units = Math.floor((elapsed / PARSE_MS) * 5);
  }
}

const strip = <T extends { startedAt: number }>(j: T): Job => {
  const { id: jid, kind, status, stage, completed_units, total_units } = j as unknown as Job & { startedAt: number };
  return { id: jid, kind, status, stage, completed_units, total_units };
};

export const mockAdapter: ApiClient = {
  async createSession() {
    await gate(null, 120);
    const s: Session = { token: id("tok"), expires_at: new Date(Date.now() + 60 * 60_000).toISOString() };
    sessions.set(s.token, s);
    return s;
  },

  async uploadDocument(token, input) {
    await gate(token, 500);
    if ("file" in input) {
      if (settings.sampleMode) throw new ApiError("uploads_disabled", "Sample mode: showing a prepared example. Uploads are turned off.");
      const { file } = input;
      const name = file.name.toLowerCase();
      if (!/\.(pdf|docx)$/.test(name)) throw new ApiError("unsupported_type", "This file type is not supported. Upload a PDF or DOCX.");
      if (file.size > 10 * 1024 * 1024) throw new ApiError("too_large", "This file is larger than 10 MB.");
      if (name.includes("scanned")) throw new ApiError("scanned", "This PDF looks scanned.");
      if (name.includes("protected")) throw new ApiError("protected", "This file is password protected.");
      const s = newDocument(file.name);
      return { document: { ...s.doc }, job: strip(s.parseJob) };
    }
    const s = newDocument(input.sampleId === "secondment" ? SAMPLE_FILENAME : `${input.sampleId}.pdf`);
    return { document: { ...s.doc }, job: strip(s.parseJob) };
  },

  async getDocument(token, docId) {
    await gate(token, 120);
    const s = getStored(docId);
    refreshParse(s);
    return { ...s.doc, nodes: [...s.doc.nodes] };
  },

  async setParty(token, docId, binding) {
    await gate(token, 200);
    const s = getStored(docId);
    s.role = binding.role;
    s.party = binding.party_node_id === "party_company" || binding.party_node_id === "party_provider" ? binding.party_node_id : null;
  },

  async startAnalysis(token, docId) {
    await gate(token, 300);
    const s = getStored(docId);
    const job = {
      id: id("job"),
      kind: "analysis" as const,
      status: "queued" as JobStatus,
      stage: null,
      completed_units: 0,
      total_units: null,
      startedAt: Date.now(),
      frozenAt: null,
      partial: settings.partialRun,
      fail: settings.failAnalysis,
    };
    s.analysisJob = job;
    s.analysisId = id("an");
    jobsToDoc.set(job.id, docId);
    return strip(job);
  },

  async getJob(token, jobId) {
    await gate(token, 100);
    const docId = jobsToDoc.get(jobId);
    if (!docId) throw new ApiError("not_found", "This job is no longer available.");
    const s = getStored(docId);
    if (s.parseJob.id === jobId) {
      refreshParse(s);
      return strip(s.parseJob);
    }
    refreshAnalysisJob(s);
    if (!s.analysisJob) throw new ApiError("not_found", "This job is no longer available.");
    return strip(s.analysisJob);
  },

  async getAnalysis(token, docId) {
    await gate(token, 140);
    const s = getStored(docId);
    if (!s.analysisJob || !s.analysisId) throw new ApiError("not_found", "No review has been started for this document.");
    refreshAnalysisJob(s);
    const categories = buildCategories(s);
    const finished = s.analysisJob.status === "succeeded" || s.analysisJob.status === "partial";
    const unavailable = categories.filter((c) => c.status === "unavailable").length;
    const analysis: Analysis = {
      id: s.analysisId,
      document_id: docId,
      text_sha256: SHA,
      status: s.analysisJob.status,
      mode: settings.sampleMode ? "sample" : "real",
      jurisdiction_scope: "india_review",
      categories,
      warnings: s.analysisJob.partial && finished ? ["Some categories could not be finished."] : [],
      created_at: s.createdAt,
      scope_notice:
        "This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment.",
      catalogue_version: "cat-2026.09-r1.1",
      processing_complete: finished && !s.analysisJob.partial,
      decision_coverage: { resolved: categories.length - unavailable, requested: CATALOGUE.length },
    };
    return analysis;
  },

  async getManualReview(token, docId) {
    await gate(token, 160);
    const s = getStored(docId);
    if (!s.analysisJob) throw new ApiError("not_found", "No review has been started for this document.");
    refreshAnalysisJob(s);
    const finished = s.analysisJob.status === "succeeded";
    if (!finished) return { status: "processing_incomplete", units: [] } satisfies ManualReview;
    const accepted = buildCategories(s)
      .flatMap((c) => c.clauses)
      .filter((c) => c.status === "accepted")
      .map((c) => [c.span.start, c.span.end] as const);
    const units: ReviewUnit[] = UNITS_BASE.map((u) => {
      let covered = 0;
      const ranges = accepted
        .map(([a, b]) => [Math.max(a, u.start), Math.min(b, u.end)] as const)
        .filter(([a, b]) => b > a)
        .sort((x, y) => x[0] - y[0]);
      let cursor = u.start;
      for (const [a, b] of ranges) {
        const from = Math.max(a, cursor);
        if (b > from) covered += b - from;
        cursor = Math.max(cursor, b);
      }
      const len = u.end - u.start;
      const overlap: ReviewUnit["overlap"] = covered === 0 ? "none" : covered >= len ? "full" : "partial";
      return { id: u.id, start: u.start, end: u.end, section_path: u.section_path, overlap, unavailable: false };
    });
    return { status: "complete", units };
  },

  async cancelJob(token, jobId) {
    await gate(token, 150);
    const docId = jobsToDoc.get(jobId);
    if (!docId) return;
    const s = getStored(docId);
    if (s.analysisJob && s.analysisJob.id === jobId && s.analysisJob.status === "running") {
      s.analysisJob.frozenAt = Date.now();
      s.analysisJob.status = "cancelled";
    }
  },

  async deleteDocument(token, docId) {
    await gate(token, 300);
    docs.delete(docId);
  },

  async downloadReport(token, docId) {
    await gate(token, 700);
    const s = getStored(docId);
    return new Blob([`ClauseAnchor report for ${s.doc.filename}. Not legal advice.`], { type: "text/plain" });
  },

  async getEvaluations() {
    await gate(null, 300);
    const result: Evaluations = {
      is_example: true,
      sets: [
        { id: "cuad", label: "CUAD test set", rows: exampleRows(1.7) },
        { id: "indian", label: "Indian contracts", rows: exampleRows(3.1) },
      ],
    };
    return result;
  },
};
