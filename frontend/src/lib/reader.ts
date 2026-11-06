/* Pure helpers for the Reader. All are tested without a DOM (reader.test.ts). */

import { CATEGORY_BY_ID, INDIA_IDS } from "../api/catalogue.ts";
import type { Category, Document } from "../api/types.ts";
import type { StatusKind } from "../components/StatusChip.tsx";

/** Which tick a click at `y` means. `ats` are tick positions and `y` a click, both 0 to 1 down
 *  the strip, and `stripPx` is the strip's height. The nearest tick wins, so neighbours never
 *  share a hit area. A click more than `reachPx` from every tick means none, and gives -1. */
export function nearestMark(ats: number[], y: number, stripPx: number, reachPx = 12): number {
  if (stripPx <= 0) return -1;
  let best = -1;
  let bestPx = Infinity;
  ats.forEach((at, i) => {
    const px = Math.abs(at - y) * stripPx;
    if (px < bestPx) {
      best = i;
      bestPx = px;
    }
  });
  // The epsilon is for float error: 0.524 - 0.5 times 500 is 12.000000000000014.
  return bestPx <= reachPx + 1e-6 ? best : -1;
}

/** Stagger steps for rows that are new since the last render. Each new id gets the next step, and
 *  steps stop at `cap - 1`, so a burst of rows never waits longer than the cap allows. */
export function freshDelays(seen: ReadonlySet<string>, ids: Iterable<string>, cap = 6): Map<string, number> {
  const out = new Map<string, number>();
  for (const id of ids) if (!seen.has(id)) out.set(id, Math.min(out.size, cap - 1));
  return out;
}

/** The session banner's line for `minutesLeft`. Whole minutes, rounded down, so it never promises more time than there is. */
export function sessionEndsIn(minutesLeft: number, report = true): string {
  const m = Math.floor(minutesLeft);
  const when = m < 1 ? "less than a minute" : `${m} ${m === 1 ? "minute" : "minutes"}`;
  return `This session ends in ${when}.${report ? " Download your report before it closes." : ""}`;
}

/** `raw` as a normalised https address, or undefined for anything else (http, javascript:, data:,
 *  a relative path, nothing). A source link is quoted from a judgment record, so it is checked
 *  before the page opens it, and the string returned is the string that was checked. */
export function httpsUrl(raw: string | undefined): string | undefined {
  try {
    const u = new URL(raw ?? "");
    return u.protocol === "https:" ? u.href : undefined;
  } catch {
    return undefined;
  }
}

/** Why an India-specific row is Unavailable. The core has no model for the five yet (docs/ml/RealAnalyzer.md). */
export const INDIA_NOTE = "Not available in this build yet";

/** The status a row shows for a category the API returned. */
export function categoryStatus(c: Category): StatusKind {
  if (c.status === "found") return c.clauses.some((k) => k.status === "accepted" && k.confidence_band !== "unvalidated") ? "found" : "unvalidated";
  if (c.status === "abstained") return "review";
  return c.status;
}

export type ListRow = { id: string; status: StatusKind; pending: boolean; count?: number; note?: string };

/** One row for each category the Reader lists: the ones asked for, then the five India-specific ones when the switch is on (the API
 *  answers only the ids it was sent, API.md section 6, and the switch adds none). An India-specific category is Unavailable with its
 *  reason from the start, whether the API returned it or not. Any other category is pending until the review ends, and Unavailable if
 *  the API never returned it. */
export function listRows(requested: readonly string[], india: boolean, byId: ReadonlyMap<string, Category>, finished: boolean): ListRow[] {
  const ids = india ? [...requested, ...INDIA_IDS.filter((id) => !requested.includes(id))] : requested;
  return ids.map((id): ListRow => {
    const cat = byId.get(id);
    if (INDIA_IDS.includes(id) && (!cat || cat.status === "unavailable")) return { id, status: "unavailable", pending: false, note: INDIA_NOTE };
    if (!cat) return { id, status: finished ? "unavailable" : "absent", pending: !finished };
    const status = categoryStatus(cat);
    // A count of 0 is a fact for a category that abstained with no passage. Not found and Unavailable have nothing to count.
    return { id, status, pending: false, count: status === "absent" || status === "unavailable" ? undefined : cat.clauses.length };
  });
}

export type Unfinished = { label: string; note: string };

/** The page warnings that set `partial` and name a page (ParserContract.md section 10). */
const UNREAD_PAGE = new Set(["PARTIALLY_SCANNED_PDF", "UNMAPPED_GLYPHS"]);

/** What View list shows: the categories and the pages that were not finished, each with a short reason. Empty when nothing was left out. */
export function unfinishedList(rows: readonly ListRow[], byId: ReadonlyMap<string, Category>, doc: Pick<Document, "partial" | "warnings"> | null): Unfinished[] {
  const out: Unfinished[] = [];
  for (const r of rows) {
    const note = r.note ?? (r.pending ? null : r.status === "unavailable" ? "Not checked" : byId.get(r.id)?.search_complete === false ? "Checked in part" : null);
    if (note) out.push({ label: CATEGORY_BY_ID[r.id]?.label ?? r.id, note });
  }
  if (doc?.partial) {
    const pages = [...new Set(doc.warnings.filter((w) => w.page !== null && UNREAD_PAGE.has(w.code)).map((w) => w.page as number))].sort((a, b) => a - b);
    if (pages.length) for (const p of pages) out.push({ label: `Page ${p}`, note: "Could not be read" });
    else out.push({ label: "Part of the document", note: "Could not be read" });
  }
  return out;
}
