import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { available, client } from "../../api/client";
import { errorInfo } from "../../api/errors";
import { ApiError, type Document, type Job, type UploadInput } from "../../api/types";
import { useSession } from "../../app/session";
import type { PartyChoice } from "../../components/PartyBindingField";
import { buildOffsetIndex, sliceCp } from "../../lib/offsets";
import { flowReducer, initialFlow, partyName, type FlowError, type UploadErrorCode } from "../../lib/startFlow";

/* The side effects of the /start flow: the upload, the parse polling and the calls to
   `client`. The reducer in lib/startFlow.ts holds the state and this hook reports to it.
   Each upload takes a new `seq`, so an answer for a replaced file changes nothing. */

const CODES: UploadErrorCode[] = ["unsupported_type", "too_large", "scanned", "protected", "network"];

const formatSize = (bytes: number) => (bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);

/** What the screen shows for a failed request. */
function flowError(e: unknown): FlowError {
  if (!(e instanceof ApiError)) return { code: "network", message: errorInfo(null).message, apiCode: null, retryable: true };
  const code = CODES.find((c) => c === e.code) ?? "other";
  return { code, message: e.message, apiCode: e.apiCode, retryable: e.retryable };
}

/** What the screen shows for a parse job that failed. The words come from our table and not from the server's sentence. */
function jobError(job: Job): FlowError {
  const apiCode = job.error?.code ?? null;
  const info = errorInfo(apiCode);
  return { code: CODES.find((c) => c === info.ui) ?? "other", message: info.message, apiCode, retryable: job.error?.retryable ?? false };
}

/** The session is gone, or the document is: both end on the Expired page. */
const isGone = (e: unknown) => e instanceof ApiError && (e.code === "expired" || e.code === "not_found");

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function useStartFlow() {
  const navigate = useNavigate();
  const { ensureToken, endSession, setDoc } = useSession();
  const [flow, dispatch] = useReducer(flowReducer, initialFlow);
  const [docId, setDocId] = useState<string | null>(null);
  const [doc, setDocument] = useState<Document | null>(null);
  const [size, setSize] = useState("");
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<FlowError | null>(null);
  const seq = useRef(0);
  const last = useRef<UploadInput | null>(null);
  const current = useRef<string | null>(null);
  const alive = useRef(true);

  // Leaving the page ends any polling still running. A flag and not a counter, so StrictMode's test unmount in development does not drop an upload that has just started.
  useEffect(() => {
    alive.current = true;
    return () => void (alive.current = false);
  }, []);

  const parties = useMemo<PartyChoice[]>(() => {
    if (!doc?.source_text) return [];
    const index = buildOffsetIndex(doc.source_text);
    return doc.nodes
      .filter((n) => n.kind === "party")
      .map((n) => {
        const text = sliceCp(doc.source_text ?? "", index, n.start, n.end);
        return { id: n.id, name: partyName(doc.source_text ?? "", index, n), quote: `“${text}”`, start: n.start, end: n.end };
      });
  }, [doc]);

  const gone = useCallback(() => {
    endSession();
    navigate("/expired?reason=expired", { replace: true, viewTransition: true });
  }, [endSession, navigate]);

  const upload = useCallback(
    async (input: UploadInput, retry = false) => {
      const mine = ++seq.current;
      last.current = input;
      // A replaced upload is deleted first, so a session keeps one document and the slot is free for the next (API.md section 8).
      // The old one stays current until that delete has worked, so a delete that fails (a 503, say) shows its error and Try again deletes it again.
      const replaced = current.current;
      setDocId(null);
      setDocument(null);
      setSize(formatSize(input.file.size));
      dispatch({ type: "upload-started", seq: mine, fileName: input.file.name, retry });
      let uploaded = false;
      try {
        const token = await ensureToken();
        if (replaced) await client.deleteDocument(token, replaced);
        current.current = null;
        const { document_id, parse_job_id } = await client.uploadDocument(token, input);
        if (mine !== seq.current) {
          // The user chose another file while this one was on its way. Nothing refers to it, so it goes.
          void client.deleteDocument(token, document_id).catch(() => undefined);
          return;
        }
        if (!alive.current) return;
        uploaded = true;
        current.current = document_id;
        setDocId(document_id);
        setDoc(document_id, { parseJobId: parse_job_id });
        dispatch({ type: "upload-done", seq: mine });
        for (;;) {
          const j = await client.getJob(token, parse_job_id);
          if (!alive.current || mine !== seq.current) return;
          if (j.status === "succeeded") break;
          if (j.status === "failed" || j.status === "cancelled" || j.status === "timed_out") {
            dispatch({ type: "parse-failed", seq: mine, error: jobError(j) });
            return;
          }
          await sleep(450);
        }
        const parsed = await client.getDocument(token, document_id);
        if (!alive.current || mine !== seq.current) return;
        setDocument(parsed);
        dispatch({ type: "parse-done", seq: mine, parties: parsed.nodes.filter((n) => n.kind === "party").length });
      } catch (e) {
        if (!alive.current || mine !== seq.current) return;
        if (isGone(e)) return gone();
        dispatch({ type: uploaded ? "parse-failed" : "upload-failed", seq: mine, error: flowError(e) });
      }
    },
    [ensureToken, setDoc, gone],
  );

  /** Uploads the same file again, after a failed upload or a failed read. */
  const retry = useCallback(() => {
    if (last.current) void upload(last.current, true);
  }, [upload]);

  const start = useCallback(async () => {
    if (!docId || flow.role === null || flow.categories.length === 0) return;
    setStarting(true);
    setStartError(null);
    try {
      const token = await ensureToken();
      const role = flow.role;
      const partyNodeId = flow.partyNone ? null : flow.party;
      // The binding has no endpoint until 3-A. The step stays, and until then it sends nothing.
      if (available.partyBinding) await client.setParty(token, docId, { role, party_node_id: partyNodeId });
      const started = await client.startAnalysis(token, docId, { category_ids: flow.categories, jurisdiction_scope: flow.india ? "india_review" : "unspecified" });
      setDoc(docId, { analysisJobId: started.job_id, analysisId: started.analysis_id, categoryIds: flow.categories, role, partyNodeId });
      navigate(`/review/${docId}`, { viewTransition: true });
    } catch (e) {
      setStarting(false);
      if (isGone(e)) return gone();
      setStartError(flowError(e));
    }
  }, [docId, flow.role, flow.party, flow.partyNone, flow.india, flow.categories, ensureToken, setDoc, navigate, gone]);

  const pages = doc?.page_count ?? 0;
  const fileMeta = [size, pages ? `${pages} ${pages === 1 ? "page" : "pages"}` : ""].filter(Boolean).join(", ");

  return { flow, dispatch, parties, fileMeta, upload, retry, start, starting, startError };
}
