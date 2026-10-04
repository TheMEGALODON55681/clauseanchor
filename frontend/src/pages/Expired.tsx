import { useNavigate, useSearchParams } from "react-router";
import EmptyState from "../components/EmptyState";

export default function Expired() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const deleted = params.get("reason") === "deleted";
  return (
    <div className="mx-auto flex w-full max-w-[560px] flex-col items-center px-5 py-20 md:py-28">
      <EmptyState
        variant="no-document"
        heading={deleted ? "Your contract has been deleted." : "This session has ended"}
        line={
          deleted
            ? "The file, its text and the review were removed from the server. Nothing was kept."
            : "Sessions end after a set time, or when the page is reloaded. Your contract was not kept. Upload it again to start a new review."
        }
        onAction={() => navigate("/")}
      />
    </div>
  );
}
