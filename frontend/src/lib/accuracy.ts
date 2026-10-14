import { CATEGORY_BY_ID, GROUP_ORDER } from "../api/catalogue.ts";
import type { EvaluationRow } from "../api/types.ts";

/* Where a row goes when its id is not in the catalogue, so a list on a phone never drops one. */
export const UNLISTED = "Other categories";

/* How a row is drawn. A row with no recall was not measured, whatever its weak flag says. */
export const rowVariant = (r: EvaluationRow) => (r.recall === null ? "not-measured" : r.weak ? "weak" : "strong");

/* The rows under the catalogue's seven groups, in catalogue order, each with its count of rows
   drawn Weak. Rows keep the order they came in, so the page's sort applies inside each group.
   A group with no row is left out. */
export function groupRows(rows: EvaluationRow[]) {
  const groupOf = (r: EvaluationRow) => CATEGORY_BY_ID[r.category_id]?.group ?? UNLISTED;
  return [...GROUP_ORDER, UNLISTED]
    .map((group) => {
      const inGroup = rows.filter((r) => groupOf(r) === group);
      return { group, rows: inGroup, weak: inGroup.filter((r) => rowVariant(r) === "weak").length };
    })
    .filter((g) => g.rows.length > 0);
}
