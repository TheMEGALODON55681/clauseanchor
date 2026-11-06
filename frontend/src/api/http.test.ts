import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHttpClient, API_BASE } from "./http.ts";
import { ERROR_TABLE, NETWORK_MESSAGE, errorInfo } from "./errors.ts";
import { ApiError } from "./types.ts";
import * as F from "./fixtures.ts";

/* The adapter is tested against a stubbed fetch and the synthetic responses in fixtures.ts. */

type Call = { url: string; method: string; headers: Headers; body: unknown };
type Reply = { status: number; body?: unknown } | "network" | "html";

function stub(routes: Record<string, Reply>) {
  const calls: Call[] = [];
  const fetchStub: typeof fetch = async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({ url, method, headers: new Headers(init?.headers), body: init?.body });
    const reply = routes[`${method} ${url}`];
    if (!reply) throw new Error(`unexpected request: ${method} ${url}`);
    if (reply === "network") throw new TypeError("fetch failed");
    if (reply === "html") return new Response("<html>Bad Gateway</html>", { status: 502, headers: { "Content-Type": "text/html" } });
    return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), { status: reply.status, headers: { "Content-Type": "application/json" } });
  };
  return { client: createHttpClient(fetchStub), calls };
}

const TOKEN = F.SESSION.token;
const DOC = F.UPLOAD.document_id;
const rejects = (p: Promise<unknown>, code: string, apiCode?: string) =>
  assert.rejects(p, (e: unknown) => e instanceof ApiError && e.code === code && (apiCode === undefined || e.apiCode === apiCode));

test("every route sits under one base path", async () => {
  assert.equal(API_BASE, "/api/v1");
  const { client, calls } = stub({
    [`POST ${API_BASE}/sessions`]: { status: 201, body: F.SESSION },
    [`GET ${API_BASE}/documents/${DOC}`]: { status: 200, body: F.DOCUMENT_PARSING },
  });
  await client.createSession();
  await client.getDocument(TOKEN, DOC);
  assert.ok(calls.every((c) => c.url.startsWith(`${API_BASE}/`)));
});

test("a session is made without a token, and every other call sends the token as a bearer", async () => {
  const { client, calls } = stub({
    [`POST ${API_BASE}/sessions`]: { status: 201, body: F.SESSION },
    [`GET ${API_BASE}/documents/${DOC}`]: { status: 200, body: F.DOCUMENT_PARSING },
    [`GET ${API_BASE}/jobs/j1`]: { status: 200, body: F.JOB_ANALYSIS_RUNNING },
    [`GET ${API_BASE}/analyses/a1`]: { status: 200, body: F.ANALYSIS },
    [`DELETE ${API_BASE}/documents/${DOC}`]: { status: 204 },
  });
  assert.deepEqual(await client.createSession(), F.SESSION);
  await client.getDocument(TOKEN, DOC);
  await client.getJob(TOKEN, "j1");
  await client.getAnalysis(TOKEN, "a1");
  await client.deleteDocument(TOKEN, DOC);
  assert.equal(calls[0].headers.get("Authorization"), null);
  for (const c of calls.slice(1)) assert.equal(c.headers.get("Authorization"), `Bearer ${TOKEN}`, c.url);
});

test("an upload is the raw file with the name in Content-Disposition filename*", async () => {
  const { client, calls } = stub({ [`POST ${API_BASE}/documents`]: { status: 202, body: F.UPLOAD } });
  const file = new File([new Uint8Array([37, 80, 68, 70])], "Master Services (v2) 100%'s.pdf", { type: "application/pdf" });
  const out = await client.uploadDocument(TOKEN, { file });
  assert.deepEqual(out, F.UPLOAD);
  const [call] = calls;
  assert.equal(call.body, file, "the body is the file itself, not a multipart form");
  assert.equal(call.headers.get("Content-Disposition"), "attachment; filename*=UTF-8''Master%20Services%20%28v2%29%20100%25%27s.pdf");
  assert.equal(call.headers.get("Authorization"), `Bearer ${TOKEN}`);
});

test("a name outside ASCII is percent-encoded as UTF-8", async () => {
  const { client, calls } = stub({ [`POST ${API_BASE}/documents`]: { status: 202, body: F.UPLOAD } });
  await client.uploadDocument(TOKEN, { file: new File(["x"], "सेवा.pdf") });
  assert.equal(calls[0].headers.get("Content-Disposition"), "attachment; filename*=UTF-8''%E0%A4%B8%E0%A5%87%E0%A4%B5%E0%A4%BE.pdf");
});

test("the document is read from parsed: text, hash, blocks, nodes and object warnings", async () => {
  const { client } = stub({ [`GET ${API_BASE}/documents/${DOC}`]: { status: 200, body: F.DOCUMENT_PARSED } });
  const d = await client.getDocument(TOKEN, DOC);
  assert.equal(d.status, "parsed");
  assert.equal(d.source_text, F.SOURCE_TEXT);
  assert.equal(d.text_sha256, "0".repeat(64));
  assert.equal(d.page_count, 2);
  assert.deepEqual(d.blocks.map((b) => [b.id, b.start, b.page]), [["b0001", F.BLOCK_STARTS[0], 1], ["b0002", F.BLOCK_STARTS[1], 1], ["b0003", F.BLOCK_STARTS[2], 1], ["b0004", F.BLOCK_STARTS[3], 2]]);
  assert.deepEqual(d.warnings, [{ code: "UNSUPPORTED_DOCX_FEATURE", page: null, detail: "altChunk" }]);
});

test("a node keeps page as a number or null, and name_span as an object, null or absent", async () => {
  const { client } = stub({
    [`GET ${API_BASE}/documents/${DOC}`]: { status: 200, body: F.DOCUMENT_PARSED },
    [`GET ${API_BASE}/documents/docx`]: { status: 200, body: F.DOCUMENT_DOCX },
  });
  const d = await client.getDocument(TOKEN, DOC);
  const [heading, party, bare, clause] = d.nodes;
  assert.equal(heading.page, 1);
  assert.ok(!("name_span" in heading), "only a party node has the key");
  assert.deepEqual(party.name_span, { start: F.BLOCK_STARTS[1], end: F.BLOCK_STARTS[1] + "Alpha Co.".length });
  assert.equal(bare.name_span, null, "a party the parser could not isolate keeps a null span");
  assert.ok(!("name_span" in clause));
  const w = await client.getDocument(TOKEN, "docx");
  assert.equal(w.page_count, null);
  assert.ok(w.nodes.every((n) => n.page === null), "a Word file has no pages");
});

test("coverage.partial sets partial, with or without a warning", async () => {
  const { client } = stub({
    [`GET ${API_BASE}/documents/${DOC}`]: { status: 200, body: { ...F.DOCUMENT_PARSED, parsed: { ...F.DOCUMENT_PARSED.parsed, warnings: [] } } },
    [`GET ${API_BASE}/documents/docx`]: { status: 200, body: F.DOCUMENT_DOCX },
  });
  assert.equal((await client.getDocument(TOKEN, DOC)).partial, true, "no warning, but the parser says text may be missing");
  assert.equal((await client.getDocument(TOKEN, "docx")).partial, false);
});

test("a document still parsing has no text and no partial notice", async () => {
  const { client } = stub({ [`GET ${API_BASE}/documents/${DOC}`]: { status: 200, body: F.DOCUMENT_PARSING } });
  const d = await client.getDocument(TOKEN, DOC);
  assert.equal(d.status, "parsing");
  assert.equal(d.source_text, null);
  assert.equal(d.partial, false);
  assert.deepEqual([d.blocks, d.nodes, d.warnings], [[], [], []]);
});

test("a job carries partial, timed_out and the new fields", async () => {
  const { client } = stub({
    [`GET ${API_BASE}/jobs/p`]: { status: 200, body: F.JOB_ANALYSIS_PARTIAL },
    [`GET ${API_BASE}/jobs/t`]: { status: 200, body: F.JOB_ANALYSIS_TIMED_OUT },
    [`GET ${API_BASE}/jobs/f`]: { status: 200, body: F.JOB_PARSE_FAILED },
  });
  const partial = await client.getJob(TOKEN, "p");
  assert.equal(partial.status, "partial");
  assert.deepEqual([partial.stage, partial.completed_units, partial.total_units, partial.analysis_id], ["inference", 12, 12, F.NEW_ANALYSIS.analysis_id]);
  assert.equal((await client.getJob(TOKEN, "t")).status, "timed_out");
  const failed = await client.getJob(TOKEN, "f");
  assert.equal(failed.kind, "parse");
  assert.equal(failed.document_id, DOC);
  assert.deepEqual(failed.error, { code: "SCANNED_PDF", message: "The PDF is scanned, so it holds no text to read.", retryable: false });
});

test("an analysis start sends category_ids and jurisdiction_scope as JSON and returns both ids", async () => {
  const { client, calls } = stub({ [`POST ${API_BASE}/documents/${DOC}/analyses`]: { status: 202, body: F.NEW_ANALYSIS } });
  const out = await client.startAnalysis(TOKEN, DOC, { category_ids: ["cuad.governing_law", "in.arbitration"], jurisdiction_scope: "india_review" });
  assert.deepEqual(out, F.NEW_ANALYSIS);
  assert.equal(calls[0].headers.get("Content-Type"), "application/json");
  assert.deepEqual(JSON.parse(String(calls[0].body)), { category_ids: ["cuad.governing_law", "in.arbitration"], jurisdiction_scope: "india_review" });
});

test("an analysis is read by its own id, and the server's fields pass through", async () => {
  const { client, calls } = stub({ [`GET ${API_BASE}/analyses/${F.NEW_ANALYSIS.analysis_id}`]: { status: 200, body: F.ANALYSIS } });
  const a = await client.getAnalysis(TOKEN, F.NEW_ANALYSIS.analysis_id);
  assert.equal(calls[0].url, `${API_BASE}/analyses/${F.NEW_ANALYSIS.analysis_id}`);
  assert.equal(a.status, "partial");
  assert.equal(a.processing_complete, false);
  assert.equal(a.contract_version, "2.0");
  assert.equal(a.finished_at, F.ANALYSIS.finished_at);
  const clause = a.categories[0].clauses[0];
  assert.equal(clause.origin, "model");
  assert.equal(clause.passages[0].judgment_text_sha256, "0".repeat(64));
  assert.equal(clause.passages[0].corpus_version, "placeholder-1");
  assert.ok(!("polarity" in clause), "polarity comes with the party binding, not before");
});

test("decision_coverage.resolved is the server's count, which holds found and absent only", async () => {
  const { client } = stub({ [`GET ${API_BASE}/analyses/a1`]: { status: 200, body: F.ANALYSIS } });
  const a = await client.getAnalysis(TOKEN, "a1");
  // The fixture holds one found, one abstained and one unavailable category. A count of every category that is not unavailable would give 2.
  assert.deepEqual(a.decision_coverage, { resolved: 1, requested: 3 });
});

test("a cancel returns the job, and a 409 on an ended job returns the job as it stands", async () => {
  const { client, calls } = stub({
    [`POST ${API_BASE}/jobs/j1/cancel`]: { status: 202, body: F.JOB_ANALYSIS_RUNNING },
    [`POST ${API_BASE}/jobs/j2/cancel`]: { status: 409, body: F.ERROR("JOB_NOT_CANCELLABLE") },
    [`GET ${API_BASE}/jobs/j2`]: { status: 200, body: F.JOB_ANALYSIS_ENDED },
  });
  assert.equal((await client.cancelJob(TOKEN, "j1")).status, "running");
  assert.equal((await client.cancelJob(TOKEN, "j2")).status, "succeeded");
  assert.deepEqual(calls.map((c) => `${c.method} ${c.url}`), [`POST ${API_BASE}/jobs/j1/cancel`, `POST ${API_BASE}/jobs/j2/cancel`, `GET ${API_BASE}/jobs/j2`]);
});

test("a delete sends DELETE to the document and takes the empty 204", async () => {
  const { client, calls } = stub({ [`DELETE ${API_BASE}/documents/${DOC}`]: { status: 204 } });
  await client.deleteDocument(TOKEN, DOC);
  assert.equal(calls[0].method, "DELETE");
});

/* A delete is done when the server says the document is gone: 204, or 404 because it went already. Any other reply, a 503 included,
   leaves the document in the session, so it is a failure the caller can show and retry (4-C1 live run, defect 2). */
test("a 404 on a delete means the document is already gone, and not a failure", async () => {
  const { client } = stub({ [`DELETE ${API_BASE}/documents/${DOC}`]: { status: 404, body: F.ERROR("NOT_FOUND") } });
  await client.deleteDocument(TOKEN, DOC);
});

test("a 503 on a delete is a failure that can be retried, with or without the error envelope", async () => {
  const bare = stub({ [`DELETE ${API_BASE}/documents/${DOC}`]: { status: 503 } });
  await assert.rejects(bare.client.deleteDocument(TOKEN, DOC), (e: unknown) => e instanceof ApiError && e.code === "network" && e.retryable);
  const wrapped = stub({ [`DELETE ${API_BASE}/documents/${DOC}`]: { status: 503, body: F.ERROR("NOT_READY", true) } });
  await assert.rejects(wrapped.client.deleteDocument(TOKEN, DOC), (e: unknown) => e instanceof ApiError && e.apiCode === "NOT_READY" && e.retryable);
  const down = stub({ [`DELETE ${API_BASE}/documents/${DOC}`]: "network" });
  await rejects(down.client.deleteDocument(TOKEN, DOC), "network");
});

test("a delete that finds the session gone is still the expired page", async () => {
  const { client } = stub({ [`DELETE ${API_BASE}/documents/${DOC}`]: { status: 401, body: F.ERROR("SESSION_INVALID") } });
  await rejects(client.deleteDocument(TOKEN, DOC), "expired", "SESSION_INVALID");
});

test("a bad token is the expired page, and an unknown id is not_found", async () => {
  const { client } = stub({
    [`GET ${API_BASE}/documents/a`]: { status: 401, body: F.ERROR("SESSION_INVALID") },
    [`GET ${API_BASE}/documents/b`]: { status: 404, body: F.ERROR("NOT_FOUND") },
  });
  await rejects(client.getDocument(TOKEN, "a"), "expired", "SESSION_INVALID");
  await rejects(client.getDocument(TOKEN, "b"), "not_found", "NOT_FOUND");
});

test("the upload refusals keep their own codes, and a retryable one says so", async () => {
  const f = new File(["x"], "a.pdf");
  const big = stub({ [`POST ${API_BASE}/documents`]: { status: 413, body: F.ERROR("FILE_TOO_LARGE") } });
  await rejects(big.client.uploadDocument(TOKEN, { file: f }), "too_large", "FILE_TOO_LARGE");
  const type = stub({ [`POST ${API_BASE}/documents`]: { status: 415, body: F.ERROR("UNSUPPORTED_TYPE") } });
  await rejects(type.client.uploadDocument(TOKEN, { file: f }), "unsupported_type", "UNSUPPORTED_TYPE");
  const full = stub({ [`POST ${API_BASE}/documents`]: { status: 429, body: F.ERROR("QUEUE_FULL", true) } });
  await assert.rejects(full.client.uploadDocument(TOKEN, { file: f }), (e: unknown) => e instanceof ApiError && e.retryable && e.apiCode === "QUEUE_FULL");
});

test("a file over 10 MiB is refused before it is sent", async () => {
  const { client, calls } = stub({});
  const big = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "big.pdf");
  await assert.rejects(client.uploadDocument(TOKEN, { file: big }), (e: unknown) => e instanceof ApiError && e.code === "too_large" && e.apiCode === "FILE_TOO_LARGE" && e.message === errorInfo("FILE_TOO_LARGE").message);
  assert.equal(calls.length, 0, "the server is the authority, and this only spares it a body it would refuse");
  const exact = stub({ [`POST ${API_BASE}/documents`]: { status: 202, body: F.UPLOAD } });
  await exact.client.uploadDocument(TOKEN, { file: new File([new Uint8Array(10 * 1024 * 1024)], "exact.pdf") });
  assert.equal(exact.calls.length, 1, "10 MiB itself is allowed");
});

test("a fetch that fails, or a reply that is not the error envelope, is a network error", async () => {
  const down = stub({ [`POST ${API_BASE}/sessions`]: "network", [`GET ${API_BASE}/jobs/j`]: "html" });
  await rejects(down.client.createSession(), "network");
  await assert.rejects(down.client.getJob(TOKEN, "j"), (e: unknown) => e instanceof ApiError && e.code === "network" && e.message === NETWORK_MESSAGE && e.retryable);
});

test("TOO_MUCH_TEXT reads as the agreed sentence", () => {
  assert.equal(errorInfo("TOO_MUCH_TEXT").message, "This file is too large or complex to process");
});

test("the parse errors that the dropzone words keep their codes", () => {
  assert.equal(errorInfo("SCANNED_PDF").ui, "scanned");
  assert.equal(errorInfo("ENCRYPTED_PDF").ui, "protected");
});

test("every error code in API.md has a UI message, so none falls through to the generic line", () => {
  const api = readFileSync(new URL("../../../docs/app/API.md", import.meta.url), "utf8");
  const between = (from: string, to: string) => api.slice(api.indexOf(from), api.indexOf(to));
  const codes = (text: string) => [...text.matchAll(/^\| `([A-Z][A-Z_]+)` \|/gm)].map((m) => m[1]);
  const http = codes(between("## 2. Error envelope", "## 3. Endpoints"));
  const jobs = codes(between("A job fails with one of these codes", "The parser's `EMPTY_FILE`"));
  assert.ok(http.length >= 17 && jobs.length >= 14, `read ${http.length} request codes and ${jobs.length} job codes`);
  for (const code of [...http, ...jobs]) assert.ok(ERROR_TABLE[code]?.message, `${code} has no message`);
  for (const code of Object.keys(ERROR_TABLE)) assert.ok([...http, ...jobs].includes(code), `${code} is in the table but not in API.md`);
});

test("the features with no endpoint refuse with not_available and make no request", async () => {
  const { client, calls } = stub({});
  await rejects(client.setParty(TOKEN, DOC, { role: "employer", party_node_id: "n0002" }), "not_available");
  await rejects(client.getManualReview(TOKEN, DOC), "not_available");
  await rejects(client.downloadReport(TOKEN, DOC), "not_available");
  await rejects(client.getEvaluations(), "not_available");
  assert.equal(calls.length, 0);
});

/* The fixtures against docs/app/openapi.json. The check reads keys and nothing else: every key a response schema declares must be
   present unless it is optional, no key may be undeclared, and nested objects and arrays are followed. `parsed` is an open object in
   the OpenAPI document, so it is checked against the parser's own schema, plus the `page` that the API adds to every node. */

type Schema = Record<string, any>;
const openapi = JSON.parse(readFileSync(new URL("../../../docs/app/openapi.json", import.meta.url), "utf8"));
const parserSchema = JSON.parse(readFileSync(new URL("../../../docs/app/parser_output.schema.json", import.meta.url), "utf8"));

function deref(s: Schema, root: Schema): Schema {
  if (!s.$ref) return s;
  const target = (s.$ref as string).replace(/^#\//, "").split("/").reduce((o: Schema, k) => o[k], root);
  return deref(target, root);
}

function conforms(value: unknown, schema: Schema, root: Schema, where: string, problems: string[], extra: string[] = []): void {
  let s = deref(schema, root);
  if (s.anyOf) {
    const options = s.anyOf.map((o: Schema) => deref(o, root));
    if (value === null) return void (options.some((o: Schema) => o.type === "null") || problems.push(`${where} is null`));
    s = options.find((o: Schema) => o.type !== "null") ?? s;
  }
  if (Array.isArray(s.type) && value === null && s.type.includes("null")) return;
  if (Array.isArray(value)) {
    if (s.items) value.forEach((v, i) => conforms(v, s.items, root, `${where}[${i}]`, problems, extra));
    return;
  }
  if (value === null || typeof value !== "object" || !s.properties) return;
  const have = Object.keys(value);
  const allowed = new Set([...Object.keys(s.properties), ...extra]);
  const isParty = (value as Record<string, unknown>).kind === "party";
  if (s.if) {
    // The parser's node schema: name_span is required on a party and forbidden on any other node.
    if (isParty) allowed.add("name_span");
    else allowed.delete("name_span");
  }
  for (const k of have) if (!allowed.has(k)) problems.push(`${where}.${k} is not declared`);
  const required = new Set<string>([...(s.required ?? []), ...(s.if && isParty ? s.then.required : [])]);
  for (const k of required) if (!have.includes(k)) problems.push(`${where}.${k} is missing`);
  for (const [k, sub] of Object.entries<Schema>(s.properties)) {
    if (k in value) conforms((value as Record<string, unknown>)[k], sub, root, `${where}.${k}`, problems, k === "nodes" ? ["page"] : []);
  }
}

test("every fixture has the keys of its response schema in docs/app/openapi.json", () => {
  const problems: string[] = [];
  for (const f of F.FIXTURES) {
    const where = `${f.method.toUpperCase()} ${f.path} ${f.status}`;
    const schema = openapi.paths[f.path]?.[f.method]?.responses?.[f.status]?.content?.["application/json"]?.schema;
    if (!schema) {
      problems.push(`${where}: the route has no JSON response with that status`);
      continue;
    }
    conforms(f.body, schema, openapi, where, problems);
    const parsed = (f.body as { parsed?: unknown } | null)?.parsed;
    if (parsed) conforms(parsed, parserSchema, parserSchema, `${where} parsed`, problems);
  }
  assert.deepEqual(problems, []);
});

test("the schema check fails on a fixture that has drifted", () => {
  const problems: string[] = [];
  const drifted = { ...F.JOB_PARSE_FAILED, progress: 0.5 } as Record<string, unknown>;
  delete drifted.stage;
  conforms(drifted, openapi.components.schemas.Job, openapi, "job", problems);
  assert.deepEqual(problems.sort(), ["job.progress is not declared", "job.stage is missing"]);
});
