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
export type Polarity = "exposure" | "protection" | "mixed" | "neutral" | "unresolved";
export type Role =
  | "buyer_customer"
  | "supplier_vendor"
  | "employer"
  | "employee"
  | "licensor"
  | "licensee"
  | "other";
export type JobStatus = "queued" | "running" | "succeeded" | "partial" | "failed" | "cancelled";

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
  polarity: Polarity;
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
  status: JobStatus;
  mode: "real" | "sample";
  jurisdiction_scope: "india_review" | "unspecified";
  categories: Category[];
  warnings: string[];
  created_at: string;
  scope_notice: string;
  catalogue_version: string;
  processing_complete: boolean;
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

export type Job = {
  id: string;
  kind: "parse" | "analysis";
  status: JobStatus;
  stage: string | null;
  completed_units: number;
  total_units: number | null;
};

export type DocNode = {
  id: string;
  parent_id: string | null;
  kind: string;
  start: number;
  end: number;
  page: number;
};

export type Document = {
  id: string;
  filename: string;
  status: string;
  source_text: string | null;
  text_sha256: string | null;
  nodes: DocNode[];
  warnings: string[];
  expires_at: string;
};

export type Session = { token: string; expires_at: string };

export type PartyCandidate = { name: string; start: number; end: number; text: string };

export type UploadInput = { file: File } | { sampleId: string };

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

export type ApiErrorCode =
  | "network"
  | "not_found"
  | "expired"
  | "unsupported_type"
  | "too_large"
  | "scanned"
  | "protected"
  | "uploads_disabled";

export class ApiError extends Error {
  code: ApiErrorCode;
  constructor(code: ApiErrorCode, message: string) {
    super(message);
    this.code = code;
  }
}
