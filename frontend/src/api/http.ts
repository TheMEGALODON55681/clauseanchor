import type { ApiClient } from "./client.ts";
import { NETWORK_MESSAGE, errorInfo } from "./errors.ts";
import { ApiError, type Analysis, type DocBlock, type DocNode, type Document, type Job, type NewAnalysis, type NewUpload, type ParseWarning, type Session } from "./types.ts";

/* The HTTP adapter. It follows docs/app/API.md and answers only for routes that exist. The base path is the one constant below,
   and the page and the API share one origin: the Vite dev server proxies it, and in production one server serves both. */

export const API_BASE = "/api/v1";

/** The upload limit of API.md section 3. The server decides; this only spares it, and the connection, a body it would refuse. */
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

/** The parser's output as the document read serves it (API.md section 11). Only the fields the adapter reads are named. */
type ParsedView = {
  source_text: string;
  text_sha256: string;
  page_count: number | null;
  blocks: { id: string; kind: string; start: number; end: number; page: number | null }[];
  nodes: { id: string; parent_id: string | null; kind: string; start: number; end: number; page: number | null; name_span?: { start: number; end: number } | null }[];
  warnings: ParseWarning[];
  coverage: { partial: boolean };
};
type DocumentView = {
  id: string;
  filename: string;
  status: Document["status"];
  expires_at: string;
  parsed: ParsedView | null;
};

/** RFC 5987 value for `filename*`: UTF-8, percent-encoded. encodeURIComponent leaves ' ( ) * alone and RFC 5987 does not. */
const encodeFilename = (name: string) => encodeURIComponent(name).replace(/['()*]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);

function toDocument(v: DocumentView): Document {
  const p = v.parsed;
  const blocks: DocBlock[] = (p?.blocks ?? []).map((b) => ({ id: b.id, kind: b.kind, start: b.start, end: b.end, page: b.page }));
  const nodes: DocNode[] = (p?.nodes ?? []).map((n) => ({
    id: n.id,
    parent_id: n.parent_id,
    kind: n.kind,
    start: n.start,
    end: n.end,
    page: n.page ?? null,
    // Only a party node has the key. A null span reads as the whole node text.
    ...(n.kind === "party" ? { name_span: n.name_span ?? null } : {}),
  }));
  return {
    id: v.id,
    filename: v.filename,
    status: v.status,
    source_text: p?.source_text ?? null,
    text_sha256: p?.text_sha256 ?? null,
    page_count: p?.page_count ?? null,
    blocks,
    nodes,
    warnings: p?.warnings ?? [],
    partial: p?.coverage.partial ?? false,
    expires_at: v.expires_at,
  };
}

/** A feature whose endpoint does not exist yet (Phase 3). The page shows its "not available" state and does not call this. */
const notAvailable = (): never => {
  throw new ApiError("not_available", "This is not available in this build yet.");
};

/** The error for an API code, with the words from the table. */
const apiError = (code: string, retryable = false) => {
  const info = errorInfo(code);
  return new ApiError(info.ui, info.message, code, retryable);
};

export function createHttpClient(doFetch: typeof fetch): ApiClient {
  /** One request. A failed fetch and a reply that is not the API's error envelope are network errors. */
  async function send(path: string, init: RequestInit & { token?: string } = {}): Promise<Response> {
    const { token, headers, ...rest } = init;
    const h = new Headers(headers);
    if (token) h.set("Authorization", `Bearer ${token}`);
    let res: Response;
    try {
      res = await doFetch(`${API_BASE}${path}`, { ...rest, headers: h });
    } catch {
      throw new ApiError("network", NETWORK_MESSAGE, null, true);
    }
    if (res.ok) return res;
    const body = (await res.json().catch(() => null)) as { error?: { code?: unknown; retryable?: unknown } } | null;
    const code = body?.error?.code;
    if (typeof code !== "string") throw new ApiError("network", NETWORK_MESSAGE, null, true);
    throw apiError(code, body?.error?.retryable === true);
  }

  const json = async <T>(path: string, init?: RequestInit & { token?: string }) => (await send(path, init)).json() as Promise<T>;
  const getJob = (token: string, jobId: string) => json<Job>(`/jobs/${jobId}`, { token });

  return {
    createSession: () => json<Session>("/sessions", { method: "POST" }),

    uploadDocument: (token, { file }) => {
      if (file.size > MAX_UPLOAD_BYTES) return Promise.reject(apiError("FILE_TOO_LARGE"));
      return json<NewUpload>("/documents", {
        method: "POST",
        token,
        headers: { "Content-Disposition": `attachment; filename*=UTF-8''${encodeFilename(file.name)}` },
        body: file,
      });
    },

    getDocument: async (token, documentId) => toDocument(await json<DocumentView>(`/documents/${documentId}`, { token })),

    startAnalysis: (token, documentId, options) =>
      json<NewAnalysis>(`/documents/${documentId}/analyses`, {
        method: "POST",
        token,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category_ids: options.category_ids, jurisdiction_scope: options.jurisdiction_scope }),
      }),

    getJob,

    getAnalysis: (token, analysisId) => json<Analysis>(`/analyses/${analysisId}`, { token }),

    // A cancel that arrives after the analysis ended is a 409. That is not a failure for the caller, who wants the job as it stands.
    cancelJob: async (token, jobId) => {
      try {
        return await json<Job>(`/jobs/${jobId}/cancel`, { method: "POST", token });
      } catch (e) {
        if (e instanceof ApiError && e.apiCode === "JOB_NOT_CANCELLABLE") return getJob(token, jobId);
        throw e;
      }
    },

    // A document the API no longer knows (404) is what a delete wants, so it counts as done. Any other failure, a 503 included,
    // leaves the document in the session, and the caller shows it and tries again.
    deleteDocument: async (token, documentId) => {
      try {
        await send(`/documents/${documentId}`, { method: "DELETE", token });
      } catch (e) {
        if (!(e instanceof ApiError && e.code === "not_found")) throw e;
      }
    },

    setParty: async () => notAvailable(),
    getManualReview: async () => notAvailable(),
    downloadReport: async () => notAvailable(),
    getEvaluations: async () => notAvailable(),
  };
}
