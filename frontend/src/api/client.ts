/* The one data interface for the app. Components never import the mock directly.
   To connect the FastAPI backend, replace `mockAdapter` below with an HTTP adapter. */

import type { Analysis, Document, Evaluations, Job, ManualReview, Role, Session, UploadInput } from "./types";
import { mockAdapter, settings } from "./mock";

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
  failNextRequest: boolean;
  shortSession: boolean;
};

export const client: ApiClient = mockAdapter;

/** Null once a real adapter is connected. */
export const mockSettings: MockSettings | null = settings;
