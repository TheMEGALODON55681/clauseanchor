/* Synthetic API responses for the adapter tests. They hold no contract text: every string is a
   made-up placeholder. Each fixture names the route and status it answers, so
   http.test.ts can check its keys against that route's schema in docs/app/openapi.json and the
   fixtures cannot drift from the real API. Only tests import this file. */

export type Fixture = { path: string; method: "get" | "post" | "delete"; status: string; body: unknown };

const DOC_ID = "3b0f6c1e-3a3e-4a52-9c3c-2f1d3a5f7a10";
const PARSE_JOB_ID = "7d2f9a44-8f0e-4c1b-b1a5-5e6a9c0d1e22";
const ANALYSIS_ID = "5a1c0e2b-7d3f-4b6e-9a10-2c8d4e6f8a31";
const ANALYSIS_JOB_ID = "9c4e1f20-6b7a-4d8e-8f01-3a5b7c9d1e42";
const SHA = "0".repeat(64);
const EXPIRES = "2026-11-04T12:00:00Z";

/* ASCII only, so a UTF-16 index and a code point offset agree. */
export const SOURCE_TEXT = "TEST HEADING\nAlpha Co. is the first party.\nThe second paragraph is a placeholder.\n\nA later page holds one more placeholder.";
const at = (s: string) => SOURCE_TEXT.indexOf(s);
export const BLOCK_STARTS = ["TEST HEADING", "Alpha Co. is the first party.", "The second paragraph is a placeholder.", "A later page holds one more placeholder."].map(at);

const block = (id: string, n: number, text: string, page: number) => ({
  id,
  kind: "text",
  start: BLOCK_STARTS[n],
  end: BLOCK_STARTS[n] + text.length,
  text,
  page,
  bbox: null,
  locator: { page, block: n + 1 },
});

const node = (id: string, parent: string | null, kind: string, label: string | null, level: number, n: number, text: string, page: number | null) => ({
  id,
  parent_id: parent,
  kind,
  label,
  level,
  start: BLOCK_STARTS[n],
  end: BLOCK_STARTS[n] + text.length,
  text,
  page,
});

const PARSED = {
  source_text: SOURCE_TEXT,
  text_sha256: SHA,
  parser_version: "1.4.0",
  media_type: "application/pdf",
  page_count: 2,
  blocks: [
    block("b0001", 0, "TEST HEADING", 1),
    block("b0002", 1, "Alpha Co. is the first party.", 1),
    block("b0003", 2, "The second paragraph is a placeholder.", 1),
    block("b0004", 3, "A later page holds one more placeholder.", 2),
  ],
  nodes: [
    node("n0001", null, "heading", null, 1, 0, "TEST HEADING", 1),
    // A party node with a name span, and one the parser could not isolate.
    { ...node("n0002", null, "party", null, 1, 1, "Alpha Co. is the first party.", 1), name_span: { start: BLOCK_STARTS[1], end: BLOCK_STARTS[1] + "Alpha Co.".length } },
    { ...node("n0003", null, "party", null, 1, 2, "The second paragraph is a placeholder.", 1), name_span: null },
    node("n0004", null, "clause", "1", 1, 3, "A later page holds one more placeholder.", 2),
  ],
  decorations: [],
  warnings: [{ code: "UNSUPPORTED_DOCX_FEATURE", page: null, detail: "altChunk" }],
  coverage: { pages_total: 2, pages_with_text: 2, chars: SOURCE_TEXT.length, partial: true },
};

/** The same document as a Word file: no pages, so every `page` is null. */
export const PARSED_DOCX = {
  ...PARSED,
  media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  page_count: null,
  blocks: PARSED.blocks.map((b) => ({ ...b, page: null, locator: { part: "document", paragraph: 1 } })),
  nodes: PARSED.nodes.map((n) => ({ ...n, page: null })),
  warnings: [],
  coverage: { pages_total: null, pages_with_text: null, chars: SOURCE_TEXT.length, partial: false },
};

export const SESSION = { token: "t".repeat(43), expires_at: EXPIRES };
export const UPLOAD = { document_id: DOC_ID, parse_job_id: PARSE_JOB_ID, expires_at: EXPIRES };

const documentView = (parsed: Record<string, unknown> | null, status: string) => ({
  id: DOC_ID,
  filename: "placeholder.pdf",
  status,
  media_type: "application/pdf",
  byte_count: 1234,
  expires_at: EXPIRES,
  parsed,
});
export const DOCUMENT_PARSING = documentView(null, "parsing");
export const DOCUMENT_PARSED = documentView(PARSED, "parsed");
export const DOCUMENT_DOCX = { ...documentView(PARSED_DOCX, "parsed"), filename: "placeholder.docx", media_type: PARSED_DOCX.media_type };

const job = (over: Record<string, unknown>) => ({
  id: PARSE_JOB_ID,
  kind: "parse",
  document_id: DOC_ID,
  analysis_id: null,
  status: "running",
  stage: null,
  completed_units: 0,
  total_units: null,
  error: null,
  ...over,
});
export const JOB_PARSE_FAILED = job({ status: "failed", error: { code: "SCANNED_PDF", message: "The PDF is scanned, so it holds no text to read.", retryable: false } });
export const JOB_ANALYSIS_RUNNING = job({ id: ANALYSIS_JOB_ID, kind: "analysis", analysis_id: ANALYSIS_ID, status: "running", stage: "inference", completed_units: 3, total_units: 12 });
export const JOB_ANALYSIS_PARTIAL = { ...JOB_ANALYSIS_RUNNING, status: "partial", completed_units: 12 };
export const JOB_ANALYSIS_TIMED_OUT = { ...JOB_ANALYSIS_RUNNING, status: "timed_out" };
export const JOB_ANALYSIS_ENDED = { ...JOB_ANALYSIS_RUNNING, status: "succeeded", completed_units: 12 };

export const NEW_ANALYSIS = { analysis_id: ANALYSIS_ID, job_id: ANALYSIS_JOB_ID };

const span = (text: string) => ({ doc_id: DOC_ID, text_sha256: SHA, start: at(text), end: at(text) + text.length, text });

const category = (id: string, status: string, over: Record<string, unknown> = {}) => ({
  category_id: id,
  status,
  decision_confidence: null,
  reason_code: null,
  search_complete: true,
  windows_done: 1,
  windows_total: 1,
  unresolved_count: 0,
  clauses: [],
  ...over,
});

const PASSAGE = {
  id: "p1",
  judgment_id: "j1",
  case_name: "Placeholder v. Placeholder",
  court: "Placeholder Court",
  year: null,
  citation: "[placeholder]",
  source_url: "https://example.invalid/placeholder",
  start: 0,
  end: 10,
  text: "Placeholder.",
  judgment_text_sha256: SHA,
  corpus_version: "placeholder-1",
  authority_status: "reviewed",
  provenance_status: "verified",
  rank: 1,
};

/* One found, one abstained and one unavailable category. Only `found` is resolved, so decision_coverage reads 1 of 3. */
export const ANALYSIS = {
  id: ANALYSIS_ID,
  document_id: DOC_ID,
  text_sha256: SHA,
  contract_version: "2.0",
  artifact_manifest_sha256: SHA,
  status: "partial",
  mode: "real",
  jurisdiction_scope: "india_review",
  created_at: EXPIRES,
  finished_at: EXPIRES,
  scope_notice: "Placeholder scope notice.",
  catalogue_version: "1.0.0",
  processing_complete: false,
  decision_coverage: { resolved: 1, requested: 3 },
  categories: [
    category("cuad.alpha", "found", {
      decision_confidence: 0.9,
      clauses: [
        {
          id: "c1",
          category_id: "cuad.alpha",
          span: span("The second paragraph is a placeholder."),
          status: "review_candidate",
          confidence: null,
          confidence_band: "unvalidated",
          calibration_scope: "unvalidated",
          origin: "model",
          rule_flags: [
            {
              rule_id: "r1",
              version: "1",
              label_key: "placeholder",
              note: "Placeholder note.",
              statute_citations: [],
              authority_ids: [],
              evidence_spans: [span("TEST HEADING")],
              scope_status: "applies",
            },
          ],
          passages: [PASSAGE],
          retrieval_status: "complete",
        },
      ],
    }),
    category("cuad.beta", "abstained", { reason_code: "below_threshold" }),
    category("in.gamma", "unavailable", { search_complete: false, windows_done: 0, windows_total: 2, unresolved_count: 2, reason_code: "not_supported" }),
  ],
  warnings: ["CONFIDENCE_NOT_MEASURED"],
};

export const ERROR = (code: string, retryable = false) => ({ error: { code, message: "Fixed placeholder sentence.", request_id: "0b0f6c1e-3a3e-4a52-9c3c-2f1d3a5f7a10", retryable, details: {} } });

export const FIXTURES: Fixture[] = [
  { path: "/api/v1/sessions", method: "post", status: "201", body: SESSION },
  { path: "/api/v1/sessions", method: "post", status: "429", body: ERROR("SESSION_LIMIT", true) },
  { path: "/api/v1/documents", method: "post", status: "202", body: UPLOAD },
  { path: "/api/v1/documents", method: "post", status: "413", body: ERROR("FILE_TOO_LARGE") },
  { path: "/api/v1/documents", method: "post", status: "415", body: ERROR("UNSUPPORTED_TYPE") },
  { path: "/api/v1/documents", method: "post", status: "429", body: ERROR("QUEUE_FULL", true) },
  { path: "/api/v1/documents/{document_id}", method: "get", status: "200", body: DOCUMENT_PARSING },
  { path: "/api/v1/documents/{document_id}", method: "get", status: "200", body: DOCUMENT_PARSED },
  { path: "/api/v1/documents/{document_id}", method: "get", status: "200", body: DOCUMENT_DOCX },
  { path: "/api/v1/documents/{document_id}", method: "get", status: "404", body: ERROR("NOT_FOUND") },
  { path: "/api/v1/documents/{document_id}", method: "get", status: "401", body: ERROR("SESSION_INVALID") },
  { path: "/api/v1/jobs/{job_id}", method: "get", status: "200", body: JOB_PARSE_FAILED },
  { path: "/api/v1/jobs/{job_id}", method: "get", status: "200", body: JOB_ANALYSIS_RUNNING },
  { path: "/api/v1/jobs/{job_id}", method: "get", status: "200", body: JOB_ANALYSIS_PARTIAL },
  { path: "/api/v1/jobs/{job_id}", method: "get", status: "200", body: JOB_ANALYSIS_TIMED_OUT },
  { path: "/api/v1/jobs/{job_id}/cancel", method: "post", status: "202", body: JOB_ANALYSIS_RUNNING },
  { path: "/api/v1/jobs/{job_id}/cancel", method: "post", status: "409", body: ERROR("JOB_NOT_CANCELLABLE") },
  { path: "/api/v1/documents/{document_id}/analyses", method: "post", status: "202", body: NEW_ANALYSIS },
  { path: "/api/v1/documents/{document_id}/analyses", method: "post", status: "409", body: ERROR("SAMPLE_MODE_ONLY") },
  { path: "/api/v1/documents/{document_id}/analyses", method: "post", status: "429", body: ERROR("ANALYSIS_QUEUE_FULL", true) },
  { path: "/api/v1/analyses/{analysis_id}", method: "get", status: "200", body: ANALYSIS },
  { path: "/api/v1/analyses/{analysis_id}", method: "get", status: "404", body: ERROR("NOT_FOUND") },
];
