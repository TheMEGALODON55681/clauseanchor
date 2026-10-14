import { test } from "node:test";
import assert from "node:assert/strict";
import { groupRows, rowVariant, UNLISTED } from "./accuracy.ts";
import type { EvaluationRow } from "../api/types.ts";

const row = (category_id: string): EvaluationRow => ({ category_id, support: 20, precision: 0.8, recall: 0.8, silent_miss: 0.1, abstention: 0.1, weak: false });

test("groupRows: catalogue order, input order inside a group, no empty group, an unknown id last", () => {
  const out = groupRows([row("governing_law"), row("arbitration"), row("parties"), row("not_in_catalogue"), row("non_compete")]);
  assert.deepEqual(out.map((g) => g.group), ["Basics", "Restrictions", "India-specific", UNLISTED]);
  assert.deepEqual(out[0].rows.map((r) => r.category_id), ["governing_law", "parties"]);
  assert.deepEqual(out[3].rows.map((r) => r.category_id), ["not_in_catalogue"]);
  assert.deepEqual(groupRows([]), []);
});

test("groupRows: weak counts only the rows drawn as Weak, and rowVariant says which those are", () => {
  const weak = (id: string, over: Partial<EvaluationRow> = {}) => ({ ...row(id), weak: true, ...over });
  const out = groupRows([weak("parties"), row("governing_law"), weak("non_compete"), weak("exclusivity"), weak("arbitration", { recall: null })]);
  assert.deepEqual(out.map((g) => [g.group, g.rows.length, g.weak]), [["Basics", 2, 1], ["Restrictions", 2, 2], ["India-specific", 1, 0]]);
  assert.equal(rowVariant(weak("parties")), "weak");
  assert.equal(rowVariant(row("parties")), "strong");
  assert.equal(rowVariant(weak("parties", { recall: null })), "not-measured");
});
