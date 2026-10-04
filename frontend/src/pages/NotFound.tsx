import Link from "../components/Link";

/* A bad URL is not an expired session, and it is not an error in the product,
   so there is no warning colour. */
export default function NotFound() {
  return (
    <div className="mx-auto flex w-full max-w-[560px] flex-col gap-4 px-5 py-20 md:py-28">
      <title>Page not found | ClauseAnchor</title>
      <h1 style={{ fontFamily: "var(--font-serif)", fontWeight: 600, fontSize: 30, lineHeight: "38px", letterSpacing: "-0.005em", color: "var(--ink-primary)" }}>
        We could not find that page.
      </h1>
      <p style={{ fontSize: 16, lineHeight: "26px", color: "var(--ink-secondary)" }}>The link may be wrong or out of date.</p>
      <div className="flex flex-wrap gap-x-8 gap-y-2">
        <Link variant="standalone" href="#/">Review a contract</Link>
        <Link variant="standalone" href="#/how-it-works">How it works</Link>
      </div>
    </div>
  );
}
