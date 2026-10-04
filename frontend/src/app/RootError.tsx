import Button from "../components/Button";

/* Shown when a page fails to load or render. The router's own developer error
   screen never reaches a visitor. No error text is shown, because it could carry contract text. */
export default function RootError() {
  return (
    <div role="alert" className="mx-auto flex w-full max-w-[560px] flex-col gap-4 px-5 py-20 md:py-28">
      <title>Page could not load | ClauseAnchor</title>
      <h1 style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 30, lineHeight: "38px", letterSpacing: "-0.005em", color: "var(--ink-primary)" }}>
        This page could not load.
      </h1>
      <p style={{ fontSize: 16, lineHeight: "26px", color: "var(--ink-secondary)" }}>Reload to try again. Reloading ends your session.</p>
      <div>
        <Button variant="primary" onClick={() => window.location.reload()}>Reload</Button>
      </div>
    </div>
  );
}
