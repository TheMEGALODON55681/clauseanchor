/* The state of the /start flow as a pure reducer. It holds no side effect: the
   upload, the polling and the client calls live in pages/start/useStartFlow.ts and
   report back with actions. Every action that answers a request carries the `seq`
   of the upload it belongs to, so a late answer for a replaced file is dropped.
   The current step is not part of the state. It lives in the address (`?step=`),
   and `clampStep` says which step the state allows. */

import type { DocNode, Role } from "../api/types.ts";
import { sliceCp, type OffsetIndex } from "./offsets.ts";

export type Step = 1 | 2 | 3;
export type UploadErrorCode = "unsupported_type" | "too_large" | "scanned" | "protected" | "network" | "other";

/** Why an upload or a read failed. `code` picks the words in the upload zone, `message` is the sentence for the screen, and `apiCode` is the API's own code. */
export type FlowError = { code: UploadErrorCode; message: string; apiCode: string | null; retryable: boolean };

/** A file that crashes the parser crashes it again, so the card offers a retry of PARSE_FAILED twice and then stops (2-R, R28). */
export const MAX_PARSE_RETRIES = 2;

export type UploadState =
  | { status: "idle" }
  | { status: "validating"; fileName: string }
  | { status: "uploaded"; fileName: string }
  | { status: "error"; error: FlowError; fileName: string };

export type ParseState = "idle" | "running" | "done" | "failed";

export type FlowState = {
  seq: number;
  upload: UploadState;
  parse: ParseState;
  parseError: FlowError | null;
  /** How many times the same file was uploaded again after a failed read. */
  parseRetries: number;
  role: Role | null;
  /** The id of the chosen party. Never set by the flow itself. */
  party: string | null;
  partyNone: boolean;
  india: boolean;
  /** The ids of the categories to check, in the order they were chosen. */
  categories: string[];
};

export type FlowAction =
  | { type: "upload-started"; seq: number; fileName: string; retry?: boolean }
  | { type: "upload-done"; seq: number }
  | { type: "upload-failed"; seq: number; error: FlowError }
  | { type: "parse-done"; seq: number; parties: number }
  | { type: "parse-failed"; seq: number; error: FlowError }
  | { type: "set-role"; role: Role }
  | { type: "set-party"; party: string }
  | { type: "set-party-none" }
  | { type: "set-india"; on: boolean }
  | { type: "toggle-category"; id: string }
  | { type: "set-categories"; ids: string[] };

export const initialFlow: FlowState = {
  seq: 0,
  upload: { status: "idle" },
  parse: "idle",
  parseError: null,
  parseRetries: 0,
  role: null,
  party: null,
  partyNone: false,
  india: false,
  categories: [],
};

/** 1 until a file is uploaded, 2 until step 2 is complete, then 3. A step is reachable when nothing blocks Next on the one before it. */
export function maxReachableStep(s: FlowState): Step {
  return nextBlocker(s, 1) ? 1 : nextBlocker(s, 2) ? 2 : 3;
}

/** The step to show for a requested one: never past what the state allows. */
export function clampStep(s: FlowState, requested: Step): Step {
  return Math.min(requested, maxReachableStep(s)) as Step;
}

export type Blocker = "upload" | "checking" | "reading" | "read-failed" | "role" | "party" | "categories";

/** What stops Next on this step, or null when it can move. */
export function nextBlocker(s: FlowState, step: Step): Blocker | null {
  if (step === 1) return s.upload.status === "uploaded" ? (s.parse === "failed" ? "read-failed" : null) : s.upload.status === "validating" ? "checking" : "upload";
  if (step === 3) return s.categories.length ? null : "categories";
  if (s.parse === "running") return "reading";
  if (s.parse === "failed") return "read-failed";
  if (s.role === null) return "role";
  return s.party !== null || s.partyNone ? null : "party";
}

/** Whether the card for the error on screen may offer Try again. A read that failed for a reason the file will repeat is not offered again. */
export function canRetry(s: FlowState): boolean {
  const e = s.upload.status === "error" ? s.upload.error : s.parse === "failed" ? s.parseError : null;
  if (!e?.retryable) return false;
  return e.apiCode !== "PARSE_FAILED" || s.parseRetries < MAX_PARSE_RETRIES;
}

/** Reads the `step` query value. Anything but 1, 2 or 3 is step 1. */
export function parseStep(raw: string | null): Step {
  return raw === "2" ? 2 : raw === "3" ? 3 : 1;
}

/* Which party a role usually is in a two-party agreement, by position: first or second named. */
const SUGGESTED_INDEX: Partial<Record<Role, number>> = { buyer_customer: 0, employer: 0, licensee: 0, supplier_vendor: 1, employee: 1, licensor: 1 };

/** The index of the party to list first and mark "Suggested", or null when the fit is unknown. */
export function suggestedParty(role: Role | null, count: number): number | null {
  const i = role === null ? undefined : SUGGESTED_INDEX[role];
  return i !== undefined && i < count ? i : null;
}

/** What the card says for a party whose name is a blank line in the file. */
export const BLANK_PARTY = "Party name left blank in the document";

/* Underscores, dots, hyphens, the Unicode dashes (U+2010 to U+2015, U+2212), the ellipsis and spaces: the ways a form leaves a name blank. */
const BLANK = /^[\s_.\-\u2010-\u2015\u2212\u2026]*$/u;

/** What a party card calls the party: the node's own name span, or the node's whole text when it has none.
 *  It is never cut at a comma, because "ABC Technologies, Inc." is one name. A name that is only a blank line reads as left blank. */
export function partyName(source: string, index: OffsetIndex, node: DocNode): string {
  const { start, end } = node.name_span ?? node;
  const name = sliceCp(source, index, start, end);
  return BLANK.test(name) ? BLANK_PARTY : name;
}

export function flowReducer(s: FlowState, a: FlowAction): FlowState {
  switch (a.type) {
    case "upload-started":
      // A new file keeps the role and the scope and drops everything that came from the old one.
      return { ...s, seq: a.seq, upload: { status: "validating", fileName: a.fileName }, parse: "idle", parseError: null, parseRetries: !a.retry ? 0 : s.parse === "failed" ? s.parseRetries + 1 : s.parseRetries, party: null, partyNone: false };
    case "upload-done":
      if (a.seq !== s.seq || s.upload.status !== "validating") return s;
      return { ...s, upload: { status: "uploaded", fileName: s.upload.fileName }, parse: "running" };
    case "upload-failed":
      if (a.seq !== s.seq || s.upload.status !== "validating") return s;
      return { ...s, upload: { status: "error", error: a.error, fileName: s.upload.fileName }, parse: "idle" };
    case "parse-done":
      if (a.seq !== s.seq || s.parse !== "running") return s;
      // With no party to choose from, "None of these" is the only possible answer.
      return { ...s, parse: "done", partyNone: s.partyNone || a.parties === 0 };
    case "parse-failed":
      return a.seq === s.seq && s.parse === "running" ? { ...s, parse: "failed", parseError: a.error } : s;
    case "set-role":
      return { ...s, role: a.role };
    case "set-party":
      return { ...s, party: a.party, partyNone: false };
    case "set-party-none":
      return { ...s, party: null, partyNone: true };
    case "set-india":
      return { ...s, india: a.on };
    case "toggle-category":
      return { ...s, categories: s.categories.includes(a.id) ? s.categories.filter((x) => x !== a.id) : [...s.categories, a.id] };
    case "set-categories":
      return { ...s, categories: a.ids };
  }
}
