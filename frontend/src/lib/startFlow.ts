/* The state of the /start flow as a pure reducer. It holds no side effect: the
   upload, the polling and the client calls live in pages/start/useStartFlow.ts and
   report back with actions. Every action that answers a request carries the `seq`
   of the upload it belongs to, so a late answer for a replaced file is dropped.
   The current step is not part of the state. It lives in the address (`?step=`),
   and `clampStep` says which step the state allows. */

export type RoleKey = "buyer" | "supplier" | "employer" | "employee" | "licensor" | "licensee" | "other";
export type Step = 1 | 2 | 3;
export type UploadErrorCode = "unsupported_type" | "too_large" | "scanned" | "protected" | "network";

export type UploadState =
  | { status: "idle" }
  | { status: "validating"; fileName: string }
  | { status: "uploaded"; fileName: string }
  | { status: "error"; code: UploadErrorCode; fileName: string };

export type ParseState = "idle" | "running" | "done" | "failed";

export type FlowState = {
  seq: number;
  upload: UploadState;
  parse: ParseState;
  role: RoleKey | null;
  /** The id of the chosen party. Never set by the flow itself. */
  party: string | null;
  partyNone: boolean;
  india: boolean;
};

export type FlowAction =
  | { type: "upload-started"; seq: number; fileName: string }
  | { type: "upload-done"; seq: number }
  | { type: "upload-failed"; seq: number; code: UploadErrorCode }
  | { type: "parse-done"; seq: number; parties: number }
  | { type: "parse-failed"; seq: number }
  | { type: "set-role"; role: RoleKey }
  | { type: "set-party"; party: string }
  | { type: "set-party-none" }
  | { type: "set-india"; on: boolean };

export const initialFlow: FlowState = {
  seq: 0,
  upload: { status: "idle" },
  parse: "idle",
  role: null,
  party: null,
  partyNone: false,
  india: true,
};

/** 1 until a file is uploaded, 2 until step 2 is complete, then 3. A step is reachable when nothing blocks Next on the one before it. */
export function maxReachableStep(s: FlowState): Step {
  return nextBlocker(s, 1) ? 1 : nextBlocker(s, 2) ? 2 : 3;
}

/** The step to show for a requested one: never past what the state allows. */
export function clampStep(s: FlowState, requested: Step): Step {
  return Math.min(requested, maxReachableStep(s)) as Step;
}

export type Blocker = "upload" | "checking" | "reading" | "read-failed" | "role" | "party";

/** What stops Next on this step, or null when it can move. */
export function nextBlocker(s: FlowState, step: Step): Blocker | null {
  if (step === 1) return s.upload.status === "uploaded" ? null : s.upload.status === "validating" ? "checking" : "upload";
  if (step === 3) return null;
  if (s.parse === "running") return "reading";
  if (s.parse === "failed") return "read-failed";
  if (s.role === null) return "role";
  return s.party !== null || s.partyNone ? null : "party";
}

/** Reads the `step` query value. Anything but 1, 2 or 3 is step 1. */
export function parseStep(raw: string | null): Step {
  return raw === "2" ? 2 : raw === "3" ? 3 : 1;
}

/* Which party a role usually is in a two-party agreement, by position: first or second named. */
const SUGGESTED_INDEX: Partial<Record<RoleKey, number>> = { buyer: 0, employer: 0, licensee: 0, supplier: 1, employee: 1, licensor: 1 };

/** The index of the party to list first and mark "Suggested", or null when the fit is unknown. */
export function suggestedParty(role: RoleKey | null, count: number): number | null {
  const i = role === null ? undefined : SUGGESTED_INDEX[role];
  return i !== undefined && i < count ? i : null;
}

export function flowReducer(s: FlowState, a: FlowAction): FlowState {
  switch (a.type) {
    case "upload-started":
      // A new file keeps the role and the scope and drops everything that came from the old one.
      return { ...s, seq: a.seq, upload: { status: "validating", fileName: a.fileName }, parse: "idle", party: null, partyNone: false };
    case "upload-done":
      if (a.seq !== s.seq || s.upload.status !== "validating") return s;
      return { ...s, upload: { status: "uploaded", fileName: s.upload.fileName }, parse: "running" };
    case "upload-failed":
      if (a.seq !== s.seq || s.upload.status !== "validating") return s;
      return { ...s, upload: { status: "error", code: a.code, fileName: s.upload.fileName }, parse: "idle" };
    case "parse-done":
      if (a.seq !== s.seq || s.parse !== "running") return s;
      // With no party to choose from, "None of these" is the only possible answer.
      return { ...s, parse: "done", partyNone: s.partyNone || a.parties === 0 };
    case "parse-failed":
      return a.seq === s.seq && s.parse === "running" ? { ...s, parse: "failed" } : s;
    case "set-role":
      return { ...s, role: a.role };
    case "set-party":
      return { ...s, party: a.party, partyNone: false };
    case "set-party-none":
      return { ...s, party: null, partyNone: true };
    case "set-india":
      return { ...s, india: a.on };
  }
}
