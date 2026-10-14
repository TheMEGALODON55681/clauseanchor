import { useSearchParams } from "react-router";
import Button from "../components/Button";
import { PlainPage } from "../components/Layout";

export default function Expired() {
  const deleted = useSearchParams()[0].get("reason") === "deleted";
  return (
    <PlainPage title={deleted ? "Your contract has been deleted." : "This session has ended"}>
      <title>Session ended | ClauseAnchor</title>
      <p className="t-prose-lg">
        {deleted
          ? "The file, its text and the review were removed from the server. Nothing was kept."
          : "Sessions end after a set time, or when the page is reloaded. Your contract was not kept. Upload it again to start a new review."}
      </p>
      <div>
        <Button to="/start" size="l">Review a contract</Button>
      </div>
    </PlainPage>
  );
}
