/* What a judgment passage's authority status says, as the one phrase the card shows.
   The backend sends a free string, so a value not listed here still gets a phrase, and
   it never reads as a check that was made. The wording waits for the definition of the
   status (FrontendDesign.md 17.5, AP). */

export type Authority = "reviewed" | "not_reviewed" | "overruled" | "unknown";

export const AUTHORITY_PHRASE: Record<Authority, string> = {
  reviewed: "Checked against later judgments",
  not_reviewed: "Not checked against later judgments",
  overruled: "Overruled or modified by a later judgment",
  unknown: "Later judgments: status unknown",
};

export function authorityOf(status: string): Authority {
  return status === "reviewed" || status === "not_reviewed" || status === "overruled" ? status : "unknown";
}
