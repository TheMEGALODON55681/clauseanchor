"""Regenerate self-authored fixture data and the wire schema."""

from pathlib import Path
import json

from clauseanchor_core import (
    CONTRACT_VERSION, AnalysisResult, CategoryResult, ClauseFinding, Span,
    result_json_schema, text_digest, to_json, validate_result,
)


def main():
    directory = Path(__file__).resolve().parents[1] / "fixtures"
    directory.mkdir(exist_ok=True)
    parts = [
        "SOFTWARE TEST FIXTURE - NOT A LEGAL AGREEMENT\n",
        "Parties: Alpha and Beta. Unicode marker: \U0001f4cc\n",
        "Alpha may pay at most ten units for Task A.\n",
        "Alpha may pay at most twenty units for Task B.\n",
        "The review process is not specified in this fixture.\n",
    ]
    source = "".join(parts)
    digest = text_digest(source)
    start_a = len(parts[0]) + len(parts[1])
    start_b = start_a + len(parts[2])
    ranges = [(start_a, start_a + len(parts[2]) - 1),
              (start_b, start_b + len(parts[3]) - 1)]
    findings = [ClauseFinding(
        id=f"fixture-cap-{i}", category_id="cuad.cap_on_liability",
        span=Span("fixture-document", digest, start, end, source[start:end]),
        status="accepted", confidence=None, confidence_band="unvalidated",
        calibration_scope="unvalidated", origin="fixture",
    ) for i, (start, end) in enumerate(ranges, 1)]
    result = AnalysisResult(
        contract_version=CONTRACT_VERSION, doc_id="fixture-document", text_sha256=digest,
        artifact_manifest_sha256=text_digest("clauseanchor-phase1-fixture-v1"), mode="stub",
        categories=[
            CategoryResult("cuad.cap_on_liability", "found", None, None, True, 1, 1, 0, findings),
            CategoryResult("cuad.non_compete", "absent", None, "FIXTURE_ONLY", True, 1, 1, 0),
            CategoryResult("in.arbitration", "abstained", None, "UNVALIDATED_CATEGORY", True, 1, 1, 0),
            CategoryResult("in.seat_venue", "unavailable", None, "NOT_IMPLEMENTED", False, 0, 1, 0),
        ],
        warnings=["FIXTURE_ONLY_NO_MODEL_INFERENCE", "CONFIDENCE_NOT_MEASURED"],
    )
    validate_result(result, source)
    (directory / "sample_contract.txt").write_bytes(source.encode("utf-8"))
    (directory / "sample_analysis.json").write_bytes((to_json(result) + "\n").encode("utf-8"))
    (directory / "contract.schema.json").write_bytes((json.dumps(
        result_json_schema(), indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print("Generated exact-text fixture, sample analysis and JSON Schema.")


if __name__ == "__main__":
    main()
