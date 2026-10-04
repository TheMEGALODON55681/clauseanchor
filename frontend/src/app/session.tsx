import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { client, mockSettings, type MockSettings } from "../api/client";
import type { Role } from "../api/types";
import type { ToastVariant } from "../components/Toast";

/* Session token, contract metadata and job ids live in React memory only.
   Nothing is written to localStorage, sessionStorage or IndexedDB. */

export type DocMeta = { parseJobId: string | null; analysisJobId: string | null; role: Role; partyNodeId: string | null };
export type ToastMsg = { id: number; variant: ToastVariant; message: string };

type SessionValue = {
  ensureToken: () => Promise<string>;
  token: string | null;
  docs: Record<string, DocMeta>;
  setDoc: (id: string, patch: Partial<DocMeta>) => void;
  forgetDoc: (id: string) => void;
  toasts: ToastMsg[];
  toast: (variant: ToastVariant, message: string) => void;
  dismissToast: (id: number) => void;
  mock: MockSettings | null;
  setMock: (patch: Partial<MockSettings>) => void;
};

const BLANK_DOC: DocMeta = { parseJobId: null, analysisJobId: null, role: "employer", partyNodeId: null };

const Ctx = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const pending = useRef<Promise<string> | null>(null);
  const [docs, setDocs] = useState<Record<string, DocMeta>>({});
  const [toasts, setToasts] = useState<ToastMsg[]>([]);
  const [mock, setMockState] = useState<MockSettings | null>(mockSettings ? { ...mockSettings } : null);

  const ensureToken = useCallback(async () => {
    if (token) return token;
    if (!pending.current) {
      pending.current = client.createSession().then((s) => {
        setToken(s.token);
        return s.token;
      });
      pending.current.catch(() => (pending.current = null));
    }
    return pending.current;
  }, [token]);

  const setDoc = useCallback((id: string, patch: Partial<DocMeta>) => {
    setDocs((d) => ({
      ...d,
      [id]: { ...(d[id] ?? BLANK_DOC), ...patch },
    }));
  }, []);

  const forgetDoc = useCallback((id: string) => {
    setDocs((d) => {
      const next = { ...d };
      delete next[id];
      return next;
    });
  }, []);

  const toast = useCallback((variant: ToastVariant, message: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-2), { id, variant, message }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);

  const dismissToast = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);

  const setMock = useCallback((patch: Partial<MockSettings>) => {
    if (!mockSettings) return;
    Object.assign(mockSettings, patch);
    setMockState({ ...mockSettings });
  }, []);

  const value = useMemo(
    () => ({ ensureToken, token, docs, setDoc, forgetDoc, toasts, toast, dismissToast, mock, setMock }),
    [ensureToken, token, docs, setDoc, forgetDoc, toasts, toast, dismissToast, mock, setMock]
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): SessionValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession must be used inside SessionProvider");
  return v;
}
