import { PlainPage } from "../components/Layout";
import Link from "../components/Link";

/* A bad URL is not an expired session, and it is not an error in the product,
   so there is no warning colour. */
export default function NotFound() {
  return (
    <PlainPage title="We could not find that page.">
      <title>Page not found | ClauseAnchor</title>
      <p className="t-prose-lg">The link may be wrong or out of date.</p>
      <div className="flex flex-wrap gap-x-8 gap-y-2">
        <Link variant="standalone" href="#/start">Review a contract</Link>
        <Link variant="standalone" href="#/how-it-works">How it works</Link>
      </div>
    </PlainPage>
  );
}
