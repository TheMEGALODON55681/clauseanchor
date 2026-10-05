import { test } from "node:test";
import assert from "node:assert/strict";
import { clampStep, flowReducer, initialFlow, maxReachableStep, nextBlocker, parseStep, suggestedParty, type FlowAction, type FlowState } from "./startFlow.ts";

const run = (...actions: FlowAction[]): FlowState => actions.reduce(flowReducer, initialFlow);

const UPLOAD: FlowAction[] = [{ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-done", seq: 1 }];
const PARSED: FlowAction = { type: "parse-done", seq: 1, parties: 2 };
const ROLE: FlowAction = { type: "set-role", role: "employer" };
const PARTY: FlowAction = { type: "set-party", party: "n1" };

test("a fresh flow has nothing chosen, the Indian law review on, and only step 1 in reach", () => {
  assert.equal(initialFlow.role, null);
  assert.equal(initialFlow.party, null);
  assert.equal(initialFlow.partyNone, false);
  assert.equal(initialFlow.india, true);
  assert.equal(initialFlow.upload.status, "idle");
  assert.equal(maxReachableStep(initialFlow), 1);
});

test("step 2 stays out of reach while the file is being checked or was refused", () => {
  assert.equal(maxReachableStep(run({ type: "upload-started", seq: 1, fileName: "a.pdf" })), 1);
  assert.equal(maxReachableStep(run({ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-failed", seq: 1, code: "scanned" })), 1);
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

test("a failed parse blocks step 3 until the file is uploaded again and read", () => {
  const failed = run(...UPLOAD, ROLE, PARTY, { type: "parse-failed", seq: 1 });
  assert.equal(failed.parse, "failed");
  assert.equal(maxReachableStep(failed), 2);
  const again = run(...UPLOAD, ROLE, PARTY, { type: "parse-failed", seq: 1 }, { type: "upload-started", seq: 2, fileName: "a.pdf" }, { type: "upload-done", seq: 2 }, { type: "parse-done", seq: 2, parties: 2 }, PARTY);
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
  assert.equal(flowReducer(replaced, { type: "parse-failed", seq: 1 }), replaced);
  assert.equal(flowReducer(replaced, { type: "upload-failed", seq: 1, code: "too_large" }), replaced);
  assert.equal(flowReducer(replaced, { type: "parse-done", seq: 2, parties: 2 }).parse, "done");
});

test("each upload refusal is kept as its code and keeps step 1 as the only reachable one", () => {
  for (const code of ["unsupported_type", "too_large", "scanned", "protected", "network"] as const) {
    const s = run({ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-failed", seq: 1, code });
    assert.deepEqual(s.upload, { status: "error", code, fileName: "a.pdf" });
    assert.equal(maxReachableStep(s), 1);
    assert.equal(s.parse, "idle");
  }
});

test("the party that fits the role is suggested, and nothing is when the fit is unknown", () => {
  assert.equal(suggestedParty("employer", 2), 0);
  assert.equal(suggestedParty("buyer", 2), 0);
  assert.equal(suggestedParty("licensee", 2), 0);
  assert.equal(suggestedParty("employee", 2), 1);
  assert.equal(suggestedParty("supplier", 2), 1);
  assert.equal(suggestedParty("licensor", 2), 1);
  assert.equal(suggestedParty("other", 2), null);
  assert.equal(suggestedParty(null, 2), null);
  assert.equal(suggestedParty("employee", 1), null, "a single party has no second one to suggest");
});

test("Next names what is missing on each step, in order", () => {
  assert.equal(nextBlocker(initialFlow, 1), "upload");
  assert.equal(nextBlocker(run({ type: "upload-started", seq: 1, fileName: "a.pdf" }), 1), "checking");
  assert.equal(nextBlocker(run({ type: "upload-started", seq: 1, fileName: "a.pdf" }, { type: "upload-failed", seq: 1, code: "scanned" }), 1), "upload");
  assert.equal(nextBlocker(run(...UPLOAD), 1), null);
  assert.equal(nextBlocker(run(...UPLOAD), 2), "reading", "parsing comes before the role");
  assert.equal(nextBlocker(run(...UPLOAD, { type: "parse-failed", seq: 1 }, ROLE, PARTY), 2), "read-failed");
  assert.equal(nextBlocker(run(...UPLOAD, PARSED), 2), "role");
  assert.equal(nextBlocker(run(...UPLOAD, PARSED, ROLE), 2), "party");
  assert.equal(nextBlocker(run(...UPLOAD, PARSED, ROLE, PARTY), 2), null);
  assert.equal(nextBlocker(run(...UPLOAD, PARSED, ROLE, { type: "set-party-none" }), 2), null);
  assert.equal(nextBlocker(initialFlow, 3), null, "the last step has no Next to block");
});
