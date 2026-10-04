import { useSession } from "../app/session";
import Link from "./Link";
import Switch from "./Switch";

/* Development only. A floating drawer for the mock adapter's switches and the gallery link.
   Root loads it behind import.meta.env.DEV, so a production build holds none of it. */
export default function PreviewControls() {
  const { mock, setMock } = useSession();
  if (!mock) return null;
  return (
    <details className="fixed bottom-4 left-4 z-50 max-w-[calc(100vw-32px)]">
      <summary
        className="flex min-h-[44px] cursor-pointer items-center rounded-md px-3 text-[13px] font-medium"
        style={{ background: "var(--paper-sheet)", border: "1px solid var(--control-border)", color: "var(--ink-primary)", boxShadow: "var(--elevation-2)" }}
      >
        Preview controls
      </summary>
      <div
        className="mt-2 flex w-[320px] max-w-full flex-col gap-1 rounded-lg p-4"
        style={{ background: "var(--paper-sheet)", border: "1px solid var(--rule-default)", boxShadow: "var(--elevation-3)" }}
      >
        <p className="text-[13px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
          These switches exist only while the app runs on mock data in development.
        </p>
        <Switch checked={mock.sampleMode} onChange={(v) => setMock({ sampleMode: v })} label="Sample mode" description="Uploads off, prepared example only." />
        <Switch checked={mock.partialRun} onChange={(v) => setMock({ partialRun: v })} label="Partial run" description="Some categories finish as Unavailable." />
        <Switch checked={mock.failAnalysis} onChange={(v) => setMock({ failAnalysis: v })} label="Failed analysis" description="The review stops partway." />
        <Switch checked={mock.shortSession} onChange={(v) => setMock({ shortSession: v })} label="Short session" description="Expires in 9 minutes, shows the notice." />
        <Switch checked={mock.failNextRequest} onChange={(v) => setMock({ failNextRequest: v })} label="Fail next request" description="One network error, then normal." />
        <p className="mt-2 text-[13px] leading-[20px]" style={{ color: "var(--ink-secondary)" }}>
          Name a file with "scanned" or "protected" to see those upload errors. <Link href="#/gallery">Open the component gallery</Link>
        </p>
      </div>
    </details>
  );
}
