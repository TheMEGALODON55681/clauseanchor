from dataclasses import replace
import json
from pathlib import Path
import unittest

from clauseanchor_core import (
    AnalysisCancelled, AnalysisContext, Span, StubAnalyzer, from_dict,
    result_json_schema, text_digest, to_dict, to_json, validate_result,
)
from clauseanchor_core.contract import validate_span


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = StubAnalyzer(FIXTURES)
        self.source = self.analyzer.source_text
        self.result = self.call()

    def call(self, **overrides):
        args = dict(doc_id="test-document", text_sha256=text_digest(self.source),
                    category_ids=self.analyzer.category_ids, context=AnalysisContext())
        args.update(overrides)
        return self.analyzer.analyze(self.source, **args)

    def category(self, index, **changes):
        categories = list(self.result.categories)
        categories[index] = replace(categories[index], **changes)
        return replace(self.result, categories=categories)

    def test_four_distinct_states(self):
        self.assertEqual([c.status for c in self.result.categories],
                         ["found", "absent", "abstained", "unavailable"])

    def test_multiple_exact_spans_and_caller_document_id(self):
        findings = self.result.categories[0].clauses
        self.assertEqual(len(findings), 2)
        self.assertLess(findings[0].span.end, findings[1].span.start)
        for finding in findings:
            self.assertEqual(finding.span.doc_id, "test-document")
            self.assertEqual(self.source[finding.span.start:finding.span.end], finding.span.text)

    def test_fixture_cannot_claim_measured_confidence(self):
        self.assertEqual(self.result.mode, "stub")
        self.assertTrue(all(f.confidence is None and f.origin == "fixture"
                            for c in self.result.categories for f in c.clauses))

    def test_json_round_trip(self):
        self.assertEqual(from_dict(json.loads(to_json(self.result))), self.result)

    def test_wrong_input_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.call(text_sha256="0" * 64)

    def test_different_text_with_correct_hash_rejected(self):
        changed = self.source + "extra"
        with self.assertRaisesRegex(ValueError, "exact fixture"):
            self.analyzer.analyze(changed, doc_id="test", text_sha256=text_digest(changed),
                                  category_ids=self.analyzer.category_ids, context=AnalysisContext())

    def test_crlf_conversion_rejected(self):
        changed = self.source.replace("\n", "\r\n")
        with self.assertRaisesRegex(ValueError, "exact fixture"):
            self.analyzer.analyze(changed, doc_id="test", text_sha256=text_digest(changed),
                                  category_ids=self.analyzer.category_ids, context=AnalysisContext())

    def test_wrong_span_text_rejected(self):
        span = self.result.categories[0].clauses[0].span
        with self.assertRaisesRegex(ValueError, "exact source slice"):
            validate_span(replace(span, text="invented"), self.source, self.result.doc_id)

    def test_unicode_offsets_are_code_points(self):
        span = self.result.categories[0].clauses[0].span
        utf16_start = len(self.source[:span.start].encode("utf-16-le")) // 2
        self.assertEqual(utf16_start, span.start + 1)
        with self.assertRaises(ValueError):
            validate_span(replace(span, start=utf16_start), self.source, self.result.doc_id)

    def test_repeated_text_keeps_second_position(self):
        source = "same / same"
        span = Span("repeat", text_digest(source), 7, 11, "same")
        validate_span(span, source, "repeat")
        self.assertNotEqual(span.start, source.find(span.text))

    def test_absent_cannot_be_incomplete(self):
        with self.assertRaisesRegex(ValueError, "complete search"):
            validate_result(self.category(1, search_complete=False), self.source)

    def test_found_requires_accepted_occurrence(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            validate_result(self.category(0, clauses=[]), self.source)

    def test_unavailable_cannot_claim_complete_search(self):
        with self.assertRaises(ValueError):
            validate_result(self.category(3, search_complete=True, windows_done=1), self.source)

    def test_abstention_requires_reason(self):
        with self.assertRaisesRegex(ValueError, "reason code"):
            validate_result(self.category(2, reason_code=None), self.source)

    def test_unknown_json_field_rejected(self):
        data = to_dict(self.result)
        data["unknown"] = 1
        with self.assertRaises(ValueError):
            from_dict(data)

    def test_missing_json_field_rejected(self):
        data = to_dict(self.result)
        del data["mode"]
        with self.assertRaises(ValueError):
            from_dict(data)

    def test_boolean_is_not_an_offset(self):
        data = to_dict(self.result)
        data["categories"][0]["clauses"][0]["span"]["start"] = True
        with self.assertRaises(ValueError):
            from_dict(data)

    def test_nonfinite_confidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_result(self.category(1, decision_confidence=float("nan")), self.source)

    def test_unknown_and_duplicate_categories_rejected(self):
        for ids in [("unknown",), (self.analyzer.category_ids[0],) * 2, ()]:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.call(category_ids=ids)

    def test_subset_order_and_progress(self):
        events = []
        ids = self.analyzer.category_ids[::-1][:2]
        result = self.call(category_ids=ids, progress=events.append)
        self.assertEqual(tuple(c.category_id for c in result.categories), ids)
        self.assertEqual([(e.completed_units, e.total_units) for e in events], [(1, 2), (2, 2)])

    def test_cancellation_between_categories(self):
        events = []
        with self.assertRaises(AnalysisCancelled):
            self.call(progress=events.append, cancelled=lambda: len(events) >= 1)
        self.assertEqual(len(events), 1)

    def test_partial_parser_input_rejected_by_stub(self):
        with self.assertRaises(ValueError):
            self.call(context=AnalysisContext(parser_complete=False))

    def test_wrong_contract_version_rejected(self):
        with self.assertRaises(ValueError):
            validate_result(replace(self.result, contract_version="1.0"), self.source)

    def test_real_mode_cannot_relabel_fixture(self):
        with self.assertRaisesRegex(ValueError, "provenance"):
            validate_result(replace(self.result, mode="real"), self.source)

    def test_real_accepted_requires_validated_confidence(self):
        category = self.result.categories[0]
        clauses = [replace(f, origin="model") for f in category.clauses]
        result = replace(self.result, mode="real", categories=[replace(category, clauses=clauses)])
        with self.assertRaisesRegex(ValueError, "validated confidence"):
            validate_result(result, self.source)

    def test_exported_schema_matches_source(self):
        schema = json.loads((FIXTURES / "contract.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema, result_json_schema())


if __name__ == "__main__":
    unittest.main()
