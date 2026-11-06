/* The one data interface for the app. Components never import an adapter directly. */

import { createHttpClient } from "./http.ts";
import type { Analysis, Document, Evaluations, Job, ManualReview, NewAnalysis, NewUpload, Role, Session, UploadInput } from "./types.ts";

export type PartyBinding = { role: Role; party_node_id: string | null };
export type Scope = "india_review" | "unspecified";

export interface ApiClient {
  createSession(): Promise<Session>;
  uploadDocument(token: string, input: UploadInput): Promise<NewUpload>;
  getDocument(token: string, documentId: string): Promise<Document>;
  startAnalysis(token: string, documentId: string, options: { category_ids: string[]; jurisdiction_scope: Scope }): Promise<NewAnalysis>;
  getJob(token: string, jobId: string): Promise<Job>;
  getAnalysis(token: string, analysisId: string): Promise<Analysis>;
  cancelJob(token: string, jobId: string): Promise<Job>;
  deleteDocument(token: string, documentId: string): Promise<void>;
  /* The four below have no endpoint until Phase 3, and the adapter refuses them (`not_available`). A page shows its own
     "not available" state while the matching flag in `available` is false, and does not call them. */
  setParty(token: string, documentId: string, binding: PartyBinding): Promise<void>;
  getManualReview(token: string, documentId: string): Promise<ManualReview>;
  downloadReport(token: string, documentId: string): Promise<Blob>;
  getEvaluations(): Promise<Evaluations>;
}

/** What this build can do. Each flag turns true in the part that adds its endpoint (Phases.md, Phase 3), together with the matching method of the adapter. */
export const available: Record<"partyBinding" | "report" | "evaluations" | "manualReview" | "samples", boolean> = {
  partyBinding: false, // 3-A
  report: false, // 3-B
  evaluations: false, // 3-C
  samples: false, // 3-C
  manualReview: false, // 3-D
};

export const client: ApiClient = createHttpClient((...args) => fetch(...args));
