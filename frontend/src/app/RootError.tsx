import Button from "../components/Button";
import { PlainPage } from "../components/Layout";

/* Shown when a page fails to load or render. The router's own developer error
   screen never reaches a visitor. No error text is shown, because it could carry contract text. */
export default function RootError() {
  return (
    <PlainPage title="This page could not load." role="alert">
      <title>Page could not load | ClauseAnchor</title>
      <p className="t-prose-lg">Reload to try again. Reloading ends your session.</p>
      <div>
        <Button variant="primary" onClick={() => window.location.reload()}>Reload</Button>
      </div>
    </PlainPage>
  );
}
