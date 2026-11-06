import { test } from "node:test";
import assert from "node:assert/strict";
import { MAX_PARSE_RETRIES, canRetry, clampStep, flowReducer, initialFlow, maxReachableStep, nextBlocker, parseStep, partyName, suggestedParty, type FlowAction, type FlowError, type FlowState, type UploadErrorCode } from "./startFlow.ts";
import { buildOffsetIndex } from "./offsets.ts";
import type { DocNode } from "../api/types.ts";

const run = (...actions: FlowAction[]): FlowState => actions.reduce(flowReducer, initialFlow);
const err = (code: UploadErrorCode, over: Partial<FlowError> = {}): FlowError => ({ code, message: "Placeholder words.", apiCode: null, retryable: false, ...over });
const PARSE_ERR = err("other", { apiCode: "PARSE_FAILED", retryable: true });

const UPLOAD: FlowAction[] = [{ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-done", seq: 1 }];
const PARSED: FlowAction = { type: "parse-done", seq: 1, parties: 2 };
const ROLE: FlowAction = { type: "set-role", role: "employer" };
const PARTY: FlowAction = { type: "set-party", party: "n1" };

test("a fresh flow has nothing chosen, the India-specific switch off, and only step 1 in reach", () => {
  assert.equal(initialFlow.role, null);
  assert.equal(initialFlow.party, null);
  assert.equal(initialFlow.partyNone, false);
  assert.equal(initialFlow.india, false, "the user turns the switch on, as with the role and the categories");
  assert.equal(initialFlow.upload.status, "idle");
  assert.equal(maxReachableStep(initialFlow), 1);
});

test("step 2 stays out of reach while the file is being checked or was refused", () => {
  assert.equal(maxReachableStep(run({ type: "upload-started", seq: 1, fileName: "a.pdf" })), 1);
  assert.equal(maxReachableStep(run({ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-failed", seq: 1, error: err("scanned") })), 1);
});

test("an uploaded file opens step 2 while parsing is still running", () => {
  const s = run(...UPLOAD);
  assert.equal(s.parse, "running");
  assert.equal(maxReachableStep(s), 2);
});

test("step 3 needs parsing done, a role, and a party", () => {
  assert.equal(maxReachableStep(run(...UPLOAD, ROLE, PARTY)), 2, "parsing still running");
  assert.equal(maxReachableStep(run(...UPLOAD, PARSED, PARTY)), 2, "no role");
  assert.equal(maxReachableStep(run(...UPLOAD, PARSED, ROLE)), 2, "no party");
  assert.equal(maxReachableStep(run(...UPLOAD, PARSED, ROLE, PARTY)), 3);
});

test("None of these counts as the party decision", () => {
  const s = run(...UPLOAD, PARSED, ROLE, { type: "set-party-none" });
  assert.equal(s.party, null);
  assert.equal(maxReachableStep(s), 3);
});

test("choosing a party clears None of these, and the reverse", () => {
  const s = run({ type: "set-party-none" }, PARTY);
  assert.equal(s.partyNone, false);
  assert.equal(s.party, "n1");
  const t = run(PARTY, { type: "set-party-none" });
  assert.equal(t.party, null);
  assert.equal(t.partyNone, true);
});

test("a failed parse sends the user back to step 1 until the file is uploaded again and read", () => {
  const failed = run(...UPLOAD, ROLE, PARTY, { type: "parse-failed", seq: 1, error: PARSE_ERR });
  assert.equal(failed.parse, "failed");
  assert.equal(maxReachableStep(failed), 1, "the error shows beside the file, where it can be replaced");
  const again = run(...UPLOAD, ROLE, PARTY, { type: "parse-failed", seq: 1, error: PARSE_ERR }, { type: "upload-started", seq: 2, fileName: "a.pdf" }, { type: "upload-done", seq: 2 }, { type: "parse-done", seq: 2, parties: 2 }, PARTY);
  assert.equal(maxReachableStep(again), 3);
});

test("a contract with no named parties needs no party choice", () => {
  const s = run(...UPLOAD, ROLE, { type: "parse-done", seq: 1, parties: 0 });
  assert.equal(s.partyNone, true);
  assert.equal(maxReachableStep(s), 3);
});

test("a role is never preselected and choosing one does not choose a party", () => {
  const s = run(...UPLOAD, PARSED, ROLE);
  assert.equal(s.role, "employer");
  assert.equal(s.party, null);
  assert.equal(s.partyNone, false);
});

test("a forced step is corrected to the highest reachable one", () => {
  assert.equal(clampStep(initialFlow, parseStep("3")), 1);
  assert.equal(clampStep(run(...UPLOAD), parseStep("3")), 2);
  assert.equal(clampStep(run(...UPLOAD, PARSED, ROLE, PARTY), parseStep("3")), 3);
  assert.equal(clampStep(run(...UPLOAD, PARSED, ROLE, PARTY), parseStep("2")), 2, "a reachable step is left alone");
});

test("the step query value is read as 1, 2 or 3 and anything else is step 1", () => {
  assert.equal(parseStep("1"), 1);
  assert.equal(parseStep("2"), 2);
  assert.equal(parseStep("3"), 3);
  for (const raw of [null, "", "0", "4", "2.5", "abc", "02", "3 "]) assert.equal(parseStep(raw), 1, String(raw));
});

test("replacing the file resets the party and keeps the role and the scope", () => {
  const s = run(...UPLOAD, PARSED, ROLE, PARTY, { type: "set-india", on: false }, { type: "upload-started", seq: 2, fileName: "b.pdf" });
  assert.equal(s.party, null);
  assert.equal(s.partyNone, false);
  assert.equal(s.parse, "idle");
  assert.equal(s.role, "employer");
  assert.equal(s.india, false);
  assert.equal(clampStep(s, 3), 1, "nothing past step 1 is reachable until the new file is read");
});

test("None of these is forgotten when the file is replaced", () => {
  const s = run(...UPLOAD, PARSED, { type: "set-party-none" }, { type: "upload-started", seq: 2, fileName: "b.pdf" });
  assert.equal(s.partyNone, false);
});

test("a late result from a replaced file is ignored", () => {
  const replaced = run(...UPLOAD, { type: "upload-started", seq: 2, fileName: "b.pdf" }, { type: "upload-done", seq: 2 });
  assert.equal(flowReducer(replaced, { type: "parse-done", seq: 1, parties: 2 }), replaced);
  assert.equal(flowReducer(replaced, { type: "parse-failed", seq: 1, error: PARSE_ERR }), replaced);
  assert.equal(flowReducer(replaced, { type: "upload-failed", seq: 1, error: err("too_large") }), replaced);
  assert.equal(flowReducer(replaced, { type: "parse-done", seq: 2, parties: 2 }).parse, "done");
});

test("each upload refusal is kept as its code and keeps step 1 as the only reachable one", () => {
  for (const code of ["unsupported_type", "too_large", "scanned", "protected", "network"] as const) {
    const s = run({ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-failed", seq: 1, error: err(code) });
    assert.deepEqual(s.upload, { status: "error", error: err(code), fileName: "a.pdf" });
    assert.equal(maxReachableStep(s), 1);
    assert.equal(s.parse, "idle");
  }
});

test("the party that fits the role is suggested, and nothing is when the fit is unknown", () => {
  assert.equal(suggestedParty("employer", 2), 0);
  assert.equal(suggestedParty("buyer_customer", 2), 0);
  assert.equal(suggestedParty("licensee", 2), 0);
  assert.equal(suggestedParty("employee", 2), 1);
  assert.equal(suggestedParty("supplier_vendor", 2), 1);
  assert.equal(suggestedParty("licensor", 2), 1);
  assert.equal(suggestedParty("other", 2), null);
  assert.equal(suggestedParty(null, 2), null);
  assert.equal(suggestedParty("employee", 1), null, "a single party has no second one to suggest");
});

test("Next names what is missing on each step, in order", () => {
  assert.equal(nextBlocker(initialFlow, 1), "upload");
  assert.equal(nextBlocker(run({ type: "upload-started", seq: 1, fileName: "a.pdf" }), 1), "checking");
  assert.equal(nextBlocker(run({ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-failed", seq: 1, error: err("scanned") }), 1), "upload");
  assert.equal(nextBlocker(run(...UPLOAD), 1), null);
  assert.equal(nextBlocker(run(...UPLOAD), 2), "reading", "parsing comes before the role");
  assert.equal(nextBlocker(run(...UPLOAD, { type: "parse-failed", seq: 1, error: PARSE_ERR }, ROLE, PARTY), 2), "read-failed");
  assert.equal(nextBlocker(run(...UPLOAD, PARSED), 2), "role");
  assert.equal(nextBlocker(run(...UPLOAD, PARSED, ROLE), 2), "party");
  assert.equal(nextBlocker(run(...UPLOAD, PARSED, ROLE, PARTY), 2), null);
  assert.equal(nextBlocker(run(...UPLOAD, PARSED, ROLE, { type: "set-party-none" }), 2), null);
  assert.equal(nextBlocker(initialFlow, 3), "categories", "Start review waits for at least one category");
  assert.equal(nextBlocker(run({ type: "toggle-category", id: "cuad.governing_law" }), 3), null);
});

// The first character is outside the BMP: two UTF-16 units, one code point. The offsets only land if they are read as code points.
const AGREEMENT = "\u{1D538} This Agreement is made between ABC Technologies, Inc., a Delaware corporation, and Example Ltd.";
const NAME = "ABC Technologies, Inc.";
const NODE_START = [...AGREEMENT.slice(0, AGREEMENT.indexOf(NAME))].length;
const ABC: DocNode = {
  id: "n_party",
  parent_id: null,
  kind: "party",
  start: NODE_START,
  end: NODE_START + [...`${NAME}, a Delaware corporation`].length,
  page: 1,
  name_span: { start: NODE_START, end: NODE_START + [...NAME].length },
};

test("a party's name is its own name span, so a comma inside the name stays", () => {
  assert.equal(partyName(AGREEMENT, buildOffsetIndex(AGREEMENT), ABC), "ABC Technologies, Inc.");
});

test("a party node with no name span reads as its whole text and is never cut at a comma", () => {
  const { name_span: _unused, ...bare } = ABC;
  assert.equal(partyName(AGREEMENT, buildOffsetIndex(AGREEMENT), bare), "ABC Technologies, Inc., a Delaware corporation");
});

/* A form leaves a blank line where the name goes. The parser still finds a party node there, and the card must not offer a row of
   underscores as a name (4-C1 live run, defect 4). The fixtures are synthetic. The dashes are written as escapes. */
const blankParty = (name: string) => {
  const source = `Between ${name} and Example Ltd.`;
  const start = "Between ".length;
  const node: DocNode = { id: "n_blank", parent_id: null, kind: "party", start, end: start + [...name].length, page: null, name_span: { start, end: start + [...name].length } };
  return { source, node };
};

test("a party whose name is only underscores, dots, dashes or spaces reads as left blank in the document", () => {
  for (const blank of ["__________", "..........", "----------", "_ _ _ _ _", "\u2013\u2013\u2013\u2013", "\u2014\u2014\u2014", "\u2026\u2026", " . _ - ", "   "]) {
    const { source, node } = blankParty(blank);
    assert.equal(partyName(source, buildOffsetIndex(source), node), "Party name left blank in the document", JSON.stringify(blank));
  }
});

test("a blank is read from the node's own text when it has no name span", () => {
  const { source, node } = blankParty("__________");
  const { name_span: _unused, ...bare } = node;
  assert.equal(partyName(source, buildOffsetIndex(source), bare), "Party name left blank in the document");
});

test("a real name keeps its punctuation, and a name with one underscore or dot is not blank", () => {
  for (const name of ["Alpha Co.", "A_B Holdings", "A.B.C. Ltd.", "Example-Works Ltd"]) {
    const { source, node } = blankParty(name);
    assert.equal(partyName(source, buildOffsetIndex(source), node), name);
  }
});

test("categories start empty, toggle on and off, and survive a replaced file", () => {
  assert.deepEqual(initialFlow.categories, []);
  const on = run({ type: "toggle-category", id: "cuad.a" }, { type: "toggle-category", id: "in.b" });
  assert.deepEqual(on.categories, ["cuad.a", "in.b"]);
  assert.deepEqual(flowReducer(on, { type: "toggle-category", id: "cuad.a" }).categories, ["in.b"]);
  assert.deepEqual(flowReducer(on, { type: "set-categories", ids: [] }).categories, []);
  assert.deepEqual(flowReducer(on, { type: "set-categories", ids: ["x", "y", "z"] }).categories, ["x", "y", "z"]);
  const replaced = flowReducer(on, { type: "upload-started", seq: 1, fileName: "b.pdf" });
  assert.deepEqual(replaced.categories, ["cuad.a", "in.b"], "the choice does not belong to the file");
});

test("a failed parse keeps its error, and a new upload clears it", () => {
  const failed = run(...UPLOAD, { type: "parse-failed", seq: 1, error: err("scanned", { apiCode: "SCANNED_PDF" }) });
  assert.equal(failed.parse, "failed");
  assert.equal(failed.parseError?.apiCode, "SCANNED_PDF");
  const again = flowReducer(failed, { type: "upload-started", seq: 2, fileName: "b.pdf" });
  assert.equal(again.parseError, null);
});

test("a failed parse stops Next on step 1, so the file has to be replaced", () => {
  const s = run(...UPLOAD, { type: "parse-failed", seq: 1, error: err("scanned", { apiCode: "SCANNED_PDF" }) });
  assert.equal(nextBlocker(s, 1), "read-failed");
  assert.equal(maxReachableStep(s), 1);
});

test("only a retryable error can be tried again", () => {
  const scanned = run(...UPLOAD, { type: "parse-failed", seq: 1, error: err("scanned", { apiCode: "SCANNED_PDF" }) });
  assert.equal(canRetry(scanned), false);
  const network = run({ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-failed", seq: 1, error: err("network", { retryable: true }) });
  assert.equal(canRetry(network), true);
  assert.equal(canRetry(initialFlow), false, "nothing failed");
});

test("a file that crashes the parser is retried at most twice, then the card stops offering it", () => {
  assert.equal(MAX_PARSE_RETRIES, 2);
  let s = run(...UPLOAD, { type: "parse-failed", seq: 1, error: PARSE_ERR });
  for (let seq = 2; seq <= 1 + MAX_PARSE_RETRIES; seq++) {
    assert.equal(canRetry(s), true, "retry " + (seq - 1));
    const again: FlowAction[] = [{ type: "upload-started", seq, fileName: "a.pdf", retry: true }, { type: "upload-done", seq }, { type: "parse-failed", seq, error: PARSE_ERR }];
    s = again.reduce(flowReducer, s);
  }
  assert.equal(s.parseRetries, MAX_PARSE_RETRIES);
  assert.equal(canRetry(s), false);
});

test("a different file starts the retry count again", () => {
  const again = (seq: number): FlowAction[] => [{ type: "upload-started", seq, fileName: "a.pdf", retry: true }, { type: "upload-done", seq }, { type: "parse-failed", seq, error: PARSE_ERR }];
  const worn = run(...UPLOAD, { type: "parse-failed", seq: 1, error: PARSE_ERR }, ...again(2), ...again(3));
  assert.equal(worn.parseRetries, 2);
  assert.equal(flowReducer(worn, { type: "upload-started", seq: 4, fileName: "b.pdf" }).parseRetries, 0);
});

test("a retry after a failed upload does not use up the retries of a failed read", () => {
  let s = run({ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-failed", seq: 1, error: err("network", { retryable: true }) });
  s = flowReducer(s, { type: "upload-started", seq: 2, fileName: "a.pdf", retry: true });
  assert.equal(s.parseRetries, 0);
});

test("a network failure while uploading can be retried without limit", () => {
  let s = run({ type: "upload-started", seq: 1, fileName: "a.pdf" });
  for (let seq = 1; seq <= 5; seq++) {
    s = flowReducer(s, { type: "upload-failed", seq, error: err("network", { retryable: true }) });
    assert.equal(canRetry(s), true);
    s = flowReducer(s, { type: "upload-started", seq: seq + 1, fileName: "a.pdf", retry: true });
  }
});
