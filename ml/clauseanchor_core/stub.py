"""A fixture-bound analyzer. It does not perform model inference."""

from dataclasses import replace
import json
from pathlib import Path

from .contract import (
    AnalysisCancelled, AnalysisContext, AnalysisResult, ProgressEvent,
    text_digest, validate_result,
)
from .serialization import from_dict


def read_exact_text(path: Path) -> str:
    # Binary decoding retains the exact newline characters used for offsets.
    return path.read_bytes().decode("utf-8")


class StubAnalyzer:
    def __init__(self, fixture_dir: str | Path):
        directory = Path(fixture_dir)
        self.source_text = read_exact_text(directory / "sample_contract.txt")
        self._result = from_dict(json.loads(
            (directory / "sample_analysis.json").read_text(encoding="utf-8")
        ))
        validate_result(self._result, self.source_text)

    @property
    def category_ids(self) -> tuple[str, ...]:
        return tuple(item.category_id for item in self._result.categories)

    def analyze(
        self, document_text: str, *, doc_id: str, text_sha256: str,
        category_ids: tuple[str, ...], context: AnalysisContext,
        progress=None, cancelled=None,
    ) -> AnalysisResult:
        if not doc_id:
            raise ValueError("doc_id must be nonempty.")
        if text_sha256 != text_digest(document_text):
            raise ValueError("Caller text hash mismatch.")
        if document_text != self.source_text:
            raise ValueError("This stub accepts only its exact fixture text.")
        if not context.parser_complete or context.warnings:
            raise ValueError("This Phase 1 stub supports only complete clean fixture input.")
        if context.jurisdiction_scope not in ("india_review", "unspecified"):
            raise ValueError("Unknown jurisdiction scope.")
        if not category_ids or len(set(category_ids)) != len(category_ids):
            raise ValueError("Request unique, nonempty category IDs.")
        known = {item.category_id: item for item in self._result.categories}
        if any(item not in known for item in category_ids):
            raise ValueError("Requested category is not available in this fixture.")
        output = []
        for index, category_id in enumerate(category_ids):
            if cancelled and cancelled():
                raise AnalysisCancelled("Analysis cancelled by caller.")
            original = known[category_id]
            clauses = []
            for item in original.clauses:
                span = replace(item.span, doc_id=doc_id)
                flags = [replace(flag, evidence_spans=[
                    replace(evidence, doc_id=doc_id) for evidence in flag.evidence_spans
                ]) for flag in item.rule_flags]
                clauses.append(replace(item, span=span, rule_flags=flags))
            output.append(replace(original, clauses=clauses))
            if progress:
                progress(ProgressEvent("fixture", index + 1, len(category_ids)))
        result = replace(self._result, doc_id=doc_id, categories=output)
        validate_result(result, document_text)
        return result
