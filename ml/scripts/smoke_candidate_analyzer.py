"""Run checkpoint-000022 on newly supplied text, never replay fixture answers.

Fixed authored source, not CUAD, with CRLF, Unicode, repeated wording and
overflow windows. It tests software integration, not extraction quality.
"""

import argparse
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clauseanchor_core import (
    AnalysisCancelled, AnalysisContext, CandidateOnlyAnalyzer, from_dict,
    text_digest, to_dict, validate_result,
)
from clauseanchor_core.artifacts import read_json, require, write_json

DEFAULT_ARTIFACT = "models/clauseanchor_candidate_v0"
REPORT_DIR = "data/processed/cuad/candidate_adapter_v0"


def smoke_text():
    clause = "This Agreement shall be governed by the laws of the State of New York."
    return ("NIMBUS AND CEDAR SERVICES AGREEMENT\r\n"
            "Review marker: café, ₹500, e\u0301, 😊.\r\n"
            "This Agreement is entered into on 1 October 2026 between Nimbus Labs and Cedar Services.\r\n"
            + clause + "\r\n"
            + "The supplier will deliver monthly service reports to the customer's designated contact.\r\n" * 45
            + "SCHEDULE A — separate occurrence\r\n" + clause + "\r\n"
            "The aggregate liability of either party shall not exceed the fees paid during the preceding twelve months.\r\n")


def run(repo, artifact_dir, digest, device, batch_size, report_path):
    source = smoke_text()
    require(source != (repo / "ml/fixtures/sample_contract.txt").read_bytes().decode("utf-8"), "Smoke source is a fixture.")
    require(not report_path.exists(), "Smoke report already exists; preserve it and use --report with a new filename.")
    started = time.perf_counter()
    analyzer = CandidateOnlyAnalyzer(artifact_dir, expected_manifest_sha256=digest,
                                     device=device, batch_size=batch_size)
    loaded = time.perf_counter()
    events = []

    def progress(event):
        events.append(event)
        print(f"{event.stage}: {event.completed_units}/{event.total_units} windows", flush=True)

    args = dict(doc_id="nonfixture-analyzer-smoke-v0", text_sha256=text_digest(source),
                category_ids=("cuad.document_name", "cuad.governing_law", "cuad.cap_on_liability", "in.arbitration"),
                context=AnalysisContext())
    result = analyzer.analyze(source, **args, progress=progress)
    ended = time.perf_counter()
    validate_result(result, source)
    require(from_dict(to_dict(result)) == result, "Contract serialization differs.")
    require(result.mode == "real" and result.artifact_manifest_sha256 == digest, "Incorrect real artifact identity.")
    require(all(c.status in ("abstained", "unavailable") for c in result.categories), "Unexpected automatic decision.")
    require(result.categories[-1].status == "unavailable" and not result.categories[-1].search_complete,
            "India extension must be unavailable.")
    require(all(c.windows_done == c.windows_total and c.windows_done > 1 for c in result.categories[:-1]),
            "Expected all overflow windows to run.")
    findings = [f for c in result.categories for f in c.clauses]
    require(all(f.status == "review_candidate" and f.origin == "model" and f.confidence is None
                and f.confidence_band == f.calibration_scope == "unvalidated"
                and not f.rule_flags and not f.passages and f.retrieval_status == "not_run" for f in findings),
            "Candidate-only invariants failed.")
    require(events and events[0].completed_units == 0
            and events[-1].completed_units == events[-1].total_units
            and all(a.total_units == b.total_units and a.completed_units <= b.completed_units
                    for a, b in zip(events, events[1:])), "Invalid progress.")
    try:
        analyzer.analyze(source, **args, cancelled=lambda: True)
    except AnalysisCancelled:
        cancellation = True
    else:
        raise ValueError("Cancellation did not stop inference.")
    # No required answer/category/boundary: this is not a hidden quality test.
    # Zero findings is valid abstention, but cannot exercise actual source slices.
    report = {"status": "passed" if findings else "incomplete_no_candidate_slices",
              "checkpoint": "checkpoint-000022", "artifact_manifest_sha256": digest,
              "source_text": source, "source_sha256": text_digest(source), "non_fixture": True,
              "device": device, "batch_size": batch_size, "runtime": analyzer.runtime,
              "load_seconds": loaded - started, "inference_seconds": ended - loaded,
              "candidate_count": len(findings), "exact_source_slices_checked": len(findings),
              "cancellation_checked": cancellation, "result": to_dict(result),
              "quality_evaluation": False, "parser_to_core_integration_test": False}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(report_path, report)
    print(f"Report: {report_path}")
    print(f"Load {report['load_seconds']:.2f}s; inference {report['inference_seconds']:.2f}s; candidates {len(findings)}")
    require(bool(findings), "Inference ran but returned zero candidates; slice smoke is incomplete, not evidence of absence.")
    print("PASS: real non-fixture inference, exact source slices, contract 2.0, overflow, unsupported category and cancellation.")
    print("No extraction-accuracy, calibration, parser integration or time-saving claim.")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT)
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--report")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    artifact = Path(args.artifact_dir)
    artifact = artifact if artifact.is_absolute() else repo / artifact
    digest = args.expected_manifest_sha256
    if digest is None:
        receipt = read_json(repo / REPORT_DIR / "export_receipt.json")
        require(artifact.resolve() == (repo / receipt["artifact_directory"]).resolve(),
                "Supply the expected hash for a different artifact directory.")
        digest = receipt["manifest_canonical_sha256"]
    report = Path(args.report) if args.report else Path(REPORT_DIR) / f"smoke-{args.device}.json"
    run(repo, artifact, digest, args.device, args.batch_size, report if report.is_absolute() else repo / report)


if __name__ == "__main__":
    main()
