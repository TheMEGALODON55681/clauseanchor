import { useSearchParams } from "react-router";
import Button from "../components/Button";
import { PlainPage } from "../components/Layout";

export default function Expired() {
  const deleted = useSearchParams()[0].get("reason") === "deleted";
  return (
    <PlainPage title={deleted ? "Your contract has been deleted." : "This session has ended"}>
      <title>Session ended | ClauseAnchor</title>
      {deleted ? (
        <p className="t-prose-lg">The file, its text and the review were removed from the server. Nothing was kept.</p>
      ) : (
        <>
          {/* SA4: the page says why. Nothing polls to hold the server awake, because that costs credit. */}
          <p className="t-prose-lg">
            A session ends after a set time, when the page is reloaded, or when the demo server sleeps. The demo server sleeps after a few quiet minutes and its memory is cleared, so your contract was not kept. Upload it again to start a new review.
          </p>
          <p className="text-[15px] leading-[24px]" style={{ color: "var(--ink-secondary)" }}>
            If the page is slow to answer, the server is waking up. That can take a minute or more.
          </p>
        </>
      )}
      <div>
        <Button to="/start" size="l">Review a contract</Button>
      </div>
    </PlainPage>
  );
}
