/* The one data interface for the app. Components never import the mock directly.
   To connect the FastAPI backend, replace `adapter` below with an HTTP adapter. */

import type { Analysis, Document, Evaluations, Job, ManualReview, Role, Session, UploadInput } from "./types";

export type PartyBinding = { role: Role; party_node_id: string | null };

export interface ApiClient {
  createSession(): Promise<Session>;
  uploadDocument(token: string, input: UploadInput): Promise<{ document: Document; job: Job }>;
  getDocument(token: string, documentId: string): Promise<Document>;
  setParty(token: string, documentId: string, binding: PartyBinding): Promise<void>;
  startAnalysis(token: string, documentId: string, options: { jurisdiction_scope: "india_review" | "unspecified" }): Promise<Job>;
  getJob(token: string, jobId: string): Promise<Job>;
  getAnalysis(token: string, documentId: string): Promise<Analysis>;
  getManualReview(token: string, documentId: string): Promise<ManualReview>;
  cancelJob(token: string, jobId: string): Promise<void>;
  deleteDocument(token: string, documentId: string): Promise<void>;
  downloadReport(token: string, documentId: string): Promise<Blob>;
  getEvaluations(): Promise<Evaluations>;
}

/** Switches available only while the mock adapter is in use. */
export type MockSettings = {
  sampleMode: boolean;
  partialRun: boolean;
  failAnalysis: boolean;
  failParse: boolean;
  failNextRequest: boolean;
  shortSession: boolean;
};

/* The switches the mock reads. They sit here, and not in the mock, so the shell can read them without loading it. */
export const settings: MockSettings = {
  sampleMode: false,
  partialRun: false,
  failAnalysis: false,
  failParse: false,
  failNextRequest: false,
  shortSession: false,
};

/* The adapter loads on the first call, so the landing page does not carry it. */
const adapter = () => import("./mock").then((m) => m.mockAdapter);

export const client: ApiClient = {
  createSession: async () => (await adapter()).createSession(),
  uploadDocument: async (...a) => (await adapter()).uploadDocument(...a),
  getDocument: async (...a) => (await adapter()).getDocument(...a),
  setParty: async (...a) => (await adapter()).setParty(...a),
  startAnalysis: async (...a) => (await adapter()).startAnalysis(...a),
  getJob: async (...a) => (await adapter()).getJob(...a),
  getAnalysis: async (...a) => (await adapter()).getAnalysis(...a),
  getManualReview: async (...a) => (await adapter()).getManualReview(...a),
  cancelJob: async (...a) => (await adapter()).cancelJob(...a),
  deleteDocument: async (...a) => (await adapter()).deleteDocument(...a),
  downloadReport: async (...a) => (await adapter()).downloadReport(...a),
  getEvaluations: async () => (await adapter()).getEvaluations(),
};

/** Null once a real adapter is connected. */
export const mockSettings: MockSettings | null = settings;
