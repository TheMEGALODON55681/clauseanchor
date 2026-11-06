/* Types mirror the backend API contract exactly. Offsets are Unicode code points. */

export type Span = {
  doc_id: string;
  text_sha256: string;
  start: number;
  end: number;
  text: string;
};

export type Status = "found" | "absent" | "abstained" | "unavailable";
export type ConfidenceBand = "higher" | "review" | "unvalidated";
export type Role =
  | "buyer_customer"
  | "supplier_vendor"
  | "employer"
  | "employee"
  | "licensor"
  | "licensee"
  | "other";
export type JobStatus = "queued" | "running" | "succeeded" | "partial" | "failed" | "cancelled" | "timed_out";

export type RuleFlag = {
  rule_id: string;
  version: string;
  label_key: string;
  note: string;
  statute_citations: string[];
  authority_ids: string[];
  evidence_spans: Span[];
  scope_status: string;
};

export type Passage = {
  id: string;
  judgment_id: string;
  case_name: string;
  court: string;
  year: number | null;
  citation: string;
  source_url: string;
  start: number;
  end: number;
  text: string;
  judgment_text_sha256: string;
  corpus_version: string;
  authority_status: string;
  provenance_status: string;
  rank: number;
};

export type Clause = {
  id: string;
  category_id: string;
  span: Span;
  status: "accepted" | "review_candidate";
  confidence: number | null;
  confidence_band: ConfidenceBand;
  calibration_scope: string;
  /** The core's own word for what produced the finding. Polarity is not here: it comes with the party binding (3-A). */
  origin: "model" | "fixture";
  rule_flags: RuleFlag[];
  passages: Passage[];
  retrieval_status: string;
};

export type Category = {
  category_id: string;
  status: Status;
  decision_confidence: number | null;
  reason_code: string | null;
  search_complete: boolean;
  windows_done: number;
  windows_total: number;
  unresolved_count: number;
  clauses: Clause[];
};

export type Analysis = {
  id: string;
  document_id: string;
  text_sha256: string;
  contract_version: string;
  artifact_manifest_sha256: string | null;
  status: JobStatus;
  mode: "real" | "sample";
  jurisdiction_scope: "india_review" | "unspecified";
  categories: Category[];
  warnings: string[];
  created_at: string;
  finished_at: string | null;
  scope_notice: string;
  catalogue_version: string;
  processing_complete: boolean;
  /** The server counts `found` and `absent` only (API.md section 10). The adapter passes it through. */
  decision_coverage: { resolved: number; requested: number };
};

export type ReviewUnit = {
  id: string;
  start: number;
  end: number;
  section_path: string | null;
  overlap: "none" | "partial" | "full";
  unavailable: boolean;
};

export type ManualReview = {
  status: "complete" | "processing_incomplete";
  units: ReviewUnit[];
};

export type JobError = { code: string; message: string; retryable: boolean };

export type Job = {
  id: string;
  kind: "parse" | "analysis";
  document_id: string;
  analysis_id: string | null;
  status: JobStatus;
  stage: string | null;
  completed_units: number;
  total_units: number | null;
  error: JobError | null;
};

export type NewAnalysis = { analysis_id: string; job_id: string };

export type DocNode = {
  id: string;
  parent_id: string | null;
  kind: string;
  start: number;
  end: number;
  /** A PDF page, 1-based. Null for a Word file, which has no pages. */
  page: number | null;
  /** A party node only: the code point span of the party's name inside `start` to `end`. Null when the parser could not isolate the name. */
  name_span?: { start: number; end: number } | null;
};

/** A text block of the parser, in reading order. The blocks do not overlap and cover the text, so the Reader draws them. A node nests inside others and does not. */
export type DocBlock = { id: string; kind: string; start: number; end: number; page: number | null };

/** What the parser had to guess or could not read. `detail` is null or one of two fixed words. */
export type ParseWarning = { code: string; page: number | null; detail: string | null };

export type Document = {
  id: string;
  filename: string;
  status: "parsing" | "parsed" | "failed";
  source_text: string | null;
  text_sha256: string | null;
  /** Null for a Word file. */
  page_count: number | null;
  blocks: DocBlock[];
  nodes: DocNode[];
  warnings: ParseWarning[];
  /** `parsed.coverage.partial`: text may be missing. It can be true with no warning. */
  partial: boolean;
  expires_at: string;
};

export type Session = { token: string; expires_at: string };

export type UploadInput = { file: File };

export type NewUpload = { document_id: string; parse_job_id: string; expires_at: string };

export type EvaluationRow = {
  category_id: string;
  support: number;
  precision: number | null;
  recall: number | null;
  silent_miss: number | null;
  abstention: number | null;
  weak: boolean;
};

export type Evaluations = {
  is_example: boolean;
  sets: { id: "cuad" | "indian"; label: string; rows: EvaluationRow[] }[];
};

/* `network`, `not_found` and `expired` send the Reader to the Expired page or the retry card. The next four have their own words in the upload
   zone. `not_available` is a feature with no endpoint yet. `other` is any other error the API sent. */
export type ApiErrorCode = "network" | "not_found" | "expired" | "unsupported_type" | "too_large" | "scanned" | "protected" | "not_available" | "other";

export class ApiError extends Error {
  code: ApiErrorCode;
  /** The API's own code (API.md section 2), or null when the error never reached the API. */
  apiCode: string | null;
  /** Whether the same request can succeed later, as the API says. */
  retryable: boolean;
  constructor(code: ApiErrorCode, message: string, apiCode: string | null = null, retryable = false) {
    super(message);
    this.code = code;
    this.apiCode = apiCode;
    this.retryable = retryable;
  }
}
