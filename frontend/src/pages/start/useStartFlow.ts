import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { client } from "../../api/client";
import { SAMPLE_FILENAME } from "../../api/contract";
import { ApiError, type Document, type Role, type UploadInput } from "../../api/types";
import { useSession } from "../../app/session";
import type { PartyChoice } from "../../components/PartyBindingField";
import { buildOffsetIndex, sliceCp } from "../../lib/offsets";
import { flowReducer, initialFlow, type RoleKey, type UploadErrorCode } from "../../lib/startFlow";

/* The side effects of the /start flow: the upload, the parse polling and the calls to
   `client`. The reducer in lib/startFlow.ts holds the state and this hook reports to it.
   Each upload takes a new `seq`, so an answer for a replaced file changes nothing. */

const ROLE_FROM_KEY: Record<RoleKey, Role> = {
  buyer: "buyer_customer",
  supplier: "supplier_vendor",
  employer: "employer",
  employee: "employee",
  licensor: "licensor",
  licensee: "licensee",
  other: "other",
};

const REFUSALS: UploadErrorCode[] = ["unsupported_type", "too_large", "scanned", "protected"];

const formatSize = (bytes: number) => (bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);

export function useStartFlow() {
  const navigate = useNavigate();
  const { ensureToken, setDoc, mock, setMock } = useSession();
  const [flow, dispatch] = useReducer(flowReducer, initialFlow);
  const [docId, setDocId] = useState<string | null>(null);
  const [doc, setDocument] = useState<Document | null>(null);
  const [size, setSize] = useState("");
  const [starting, setStarting] = useState(false);
  const [startFailed, setStartFailed] = useState(false);
  const seq = useRef(0);
  const last = useRef<{ input: UploadInput; onAccepted?: () => void } | null>(null);
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
        return { id: n.id, name: text.split(",")[0], quote: `“${text}”`, start: n.start, end: n.end };
      });
  }, [doc]);

  /** `onAccepted` runs as soon as the upload is accepted, while parsing goes on. The sample link uses it to move to step 2. */
  const upload = useCallback(
    async (input: UploadInput, onAccepted?: () => void) => {
      const mine = ++seq.current;
      last.current = { input, onAccepted };
      setDocId(null);
      setDocument(null);
      setSize("file" in input ? formatSize(input.file.size) : "");
      dispatch({ type: "upload-started", seq: mine, fileName: "file" in input ? input.file.name : input.sampleId === "secondment" ? SAMPLE_FILENAME : `${input.sampleId}.pdf` });
      let uploaded = false;
      try {
        const token = await ensureToken();
        const { document, job } = await client.uploadDocument(token, input);
        if (!alive.current || mine !== seq.current) return;
        uploaded = true;
        setDocId(document.id);
        setDoc(document.id, { parseJobId: job.id });
        dispatch({ type: "upload-done", seq: mine });
        onAccepted?.();
        for (;;) {
          const j = await client.getJob(token, job.id);
          if (!alive.current || mine !== seq.current) return;
          if (j.status === "succeeded") break;
          if (j.status === "failed" || j.status === "cancelled") throw new ApiError("network", "Reading the document did not finish.");
          await new Promise((r) => setTimeout(r, 450));
        }
        const parsed = await client.getDocument(token, document.id);
        if (!alive.current || mine !== seq.current) return;
        setDocument(parsed);
        dispatch({ type: "parse-done", seq: mine, parties: parsed.nodes.filter((n) => n.kind === "party").length });
      } catch (e) {
        if (uploaded) dispatch({ type: "parse-failed", seq: mine });
        else dispatch({ type: "upload-failed", seq: mine, code: REFUSALS.find((c) => e instanceof ApiError && e.code === c) ?? "network" });
      }
    },
    [ensureToken, setDoc],
  );

  /** Uploads the same file or sample again, after a failed upload or a failed parse. A forced parse failure in the mock is cleared first, as the reader does for a failed analysis. */
  const retry = useCallback(() => {
    if (flow.parse === "failed" && mock?.failParse) setMock({ failParse: false });
    if (last.current) void upload(last.current.input, last.current.onAccepted);
  }, [upload, flow.parse, mock?.failParse, setMock]);

  const start = useCallback(async () => {
    if (!docId || flow.role === null) return;
    setStarting(true);
    setStartFailed(false);
    try {
      const token = await ensureToken();
      const role = ROLE_FROM_KEY[flow.role];
      const partyNodeId = flow.partyNone ? null : flow.party;
      await client.setParty(token, docId, { role, party_node_id: partyNodeId });
      const job = await client.startAnalysis(token, docId, { jurisdiction_scope: flow.india ? "india_review" : "unspecified" });
      setDoc(docId, { analysisJobId: job.id, role, partyNodeId });
      navigate(`/review/${docId}`, { viewTransition: true });
    } catch {
      setStarting(false);
      setStartFailed(true);
    }
  }, [docId, flow.role, flow.party, flow.partyNone, flow.india, ensureToken, setDoc, navigate]);

  const pages = doc ? Math.max(...doc.nodes.map((n) => n.page), 1) : 0;
  const fileMeta = [size, pages ? `${pages} ${pages === 1 ? "page" : "pages"}` : ""].filter(Boolean).join(", ");

  return { flow, dispatch, parties, fileMeta, upload, retry, start, starting, startFailed };
}
