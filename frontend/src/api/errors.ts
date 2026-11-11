import type { ApiErrorCode } from "./types.ts";

/* One table from every API error code (API.md section 2, and the job errors under GET /api/v1/jobs/{job_id}) to the words the
   screen shows and to the UI code that decides where they show. http.test.ts reads API.md and fails when a code has no row. */

export const NETWORK_MESSAGE = "Could not reach the server. Check your connection and try again.";
const TROUBLE = "ClauseAnchor ran into a problem. Try again in a moment.";

type Info = { ui: ApiErrorCode; message: string };

export const ERROR_TABLE: Record<string, Info> = {
  // Request errors
  VALIDATION_ERROR: { ui: "other", message: TROUBLE },
  NOT_FOUND: { ui: "not_found", message: "This document is no longer available." },
  METHOD_NOT_ALLOWED: { ui: "other", message: TROUBLE },
  INTERNAL_ERROR: { ui: "other", message: TROUBLE },
  NOT_READY: { ui: "other", message: "The review engine is still starting. Try again in a minute." },
  CATALOGUE_UNAVAILABLE: { ui: "other", message: "The category list is not available right now. Try again in a moment." },
  SESSION_INVALID: { ui: "expired", message: "This session has ended." },
  SESSION_LIMIT: { ui: "other", message: "ClauseAnchor is full right now. A place opens when an earlier session ends, which can take up to an hour." },
  FILE_TOO_LARGE: { ui: "too_large", message: "This file is larger than 10 MB." },
  EMPTY_FILE: { ui: "other", message: "This file is empty." },
  UNSUPPORTED_TYPE: { ui: "unsupported_type", message: "This file type is not supported. Upload a PDF or DOCX." },
  DOCUMENT_LIMIT: { ui: "other", message: "This session holds the most documents it allows. Delete one, then upload again." },
  QUEUE_FULL: { ui: "other", message: "ClauseAnchor is reading other files right now. Try again in a minute." },
  DOCUMENT_NOT_PARSED: { ui: "other", message: "This document has not finished loading. Wait a moment, then try again." },
  SAMPLE_MODE_ONLY: { ui: "other", message: "This server reviews only its prepared sample contract, which is not available in this build yet." },
  ANALYSIS_IN_PROGRESS: { ui: "other", message: "A review is already running in this session. Wait for it to finish, or cancel it." },
  JOB_NOT_CANCELLABLE: { ui: "other", message: "This review has already ended." },
  ANALYSIS_QUEUE_FULL: { ui: "other", message: "Other reviews are waiting. Try again in a few minutes." },
  // Parse errors
  MALFORMED_FILE: { ui: "other", message: "This file could not be read. It may be damaged. Try the original file." },
  ENCRYPTED_PDF: { ui: "protected", message: "This file is password protected. Remove the password and upload again." },
  SCANNED_PDF: { ui: "scanned", message: "This PDF looks scanned. ClauseAnchor needs selectable text. Try the original digital file." },
  TOO_MANY_PAGES: { ui: "other", message: "This PDF has more than 100 pages." },
  TOO_MUCH_TEXT: { ui: "other", message: "This file is too large or complex to process" },
  ARCHIVE_TOO_LARGE: { ui: "other", message: "This Word file is too large once it is opened." },
  ARCHIVE_UNSAFE: { ui: "other", message: "This Word file has a structure that ClauseAnchor will not open." },
  TRACKED_CHANGES_PRESENT: { ui: "other", message: "This Word file has tracked changes. Accept all changes, save it, and upload it again." },
  NO_TEXT_FOUND: { ui: "other", message: "This file holds no text to read." },
  PARSE_TIMEOUT: { ui: "other", message: "Reading this file took too long, so ClauseAnchor stopped it." },
  PARSE_MEMORY_LIMIT: { ui: "other", message: "This file needs more memory to read than ClauseAnchor allows." },
  PARSE_FAILED: { ui: "other", message: "Reading this file failed." },
  // Analysis errors
  ANALYSIS_INVALID_RESULT: { ui: "other", message: "The result of the review failed its checks, so ClauseAnchor discarded it." },
  ANALYSIS_FAILED: { ui: "other", message: "The review stopped partway. Run it again to check the rest." },
};

/** The words and the UI code for an API code. A code that is not in the table gets the generic line. */
export function errorInfo(code: string | null | undefined): Info {
  return (code && ERROR_TABLE[code]) || { ui: "other", message: TROUBLE };
}
