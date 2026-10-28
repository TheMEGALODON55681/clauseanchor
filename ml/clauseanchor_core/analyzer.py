"""Candidate-only trained-model adapter. No calibration, acceptance or absence."""

from itertools import islice
from pathlib import Path
from threading import Lock

from .artifacts import canonical_sha256, require, runtime_versions, verify_bundle
from .contract import (
    CONTRACT_VERSION, AnalysisCancelled, AnalysisContext, AnalysisResult,
    CategoryResult, ClauseFinding, ProgressEvent, Span, StructureNode,
    text_digest, validate_result,
)


def context_from_parsed_document(parsed, *, jurisdiction_scope="unspecified"):
    """Duck-typed parser bridge; keeps app imports out of the installable core.

    Existing structure nodes carry decoration ranges as kind='decoration'.
    The original ParsedDocument and its canonical source text remain untouched.
    """
    require(parsed.text_sha256 == text_digest(parsed.source_text), "Parser source hash mismatch.")
    nodes = [StructureNode(n.id, n.parent_id, n.kind, n.start, n.end) for n in parsed.nodes]
    used = {n.id for n in nodes}
    for index, (start, end) in enumerate(parsed.decorations):
        name = f"clauseanchor.decoration.{index}"
        require(name not in used, "Decoration node ID collision.")
        nodes.append(StructureNode(name, None, "decoration", start, end))
    context = AnalysisContext(jurisdiction_scope=jurisdiction_scope,
                              parser_complete=not parsed.coverage.partial,
                              structure_nodes=nodes, warnings=[w.code for w in parsed.warnings])
    _source_view(parsed.source_text, context)
    return context


def _source_view(source, context):
    require(context.jurisdiction_scope in ("unspecified", "india_review"), "Unknown jurisdiction scope.")
    require(type(context.parser_complete) is bool and all(isinstance(w, str) for w in context.warnings),
            "Invalid parser completeness/warnings.")
    ids, ranges = set(), []
    for node in context.structure_nodes:
        require(node.id and node.id not in ids and type(node.start) is int and type(node.end) is int
                and 0 <= node.start < node.end <= len(source), "Invalid/duplicate structure node.")
        ids.add(node.id)
        if node.kind == "decoration":
            ranges.append((node.start, node.end))
    chars = list(source) if ranges else None
    for start, end in ranges:
        for i in range(start, end):
            if not chars[i].isspace():
                chars[i] = " "
    return ("".join(chars) if chars is not None else source), ranges


class CandidateOnlyAnalyzer:
    """One offline model instance; serialize calls per instance (tokenizer state).

    max_windows_per_category is an explicit optional work limit, never hidden
    truncation. None processes all planned windows. Exceptions do not return a
    successful result; cancellation raises AnalysisCancelled, as in the protocol.
    """

    def __init__(self, artifact_dir, *, expected_manifest_sha256, device="cpu",
                 batch_size=1, max_windows_per_category=None):
        require(type(batch_size) is int and batch_size > 0, "Invalid batch_size.")
        require(max_windows_per_category is None or (type(max_windows_per_category) is int
                and max_windows_per_category >= 0), "Invalid work limit.")
        root = Path(artifact_dir)
        manifest, catalogue, questions = verify_bundle(root, expected_manifest_sha256)
        self.runtime = runtime_versions()
        from ._inference import FeatureTokenizer, TorchBackend
        self._tokenizer = FeatureTokenizer(root / "tokenizer")
        self._backend = TorchBackend(root, device)
        self._manifest = manifest
        self._manifest_sha256 = expected_manifest_sha256
        self._questions = questions
        self.category_ids = tuple(row["id"] for row in catalogue["categories"])
        self.inference_category_ids = tuple(questions)
        self.batch_size = batch_size
        self.max_windows_per_category = max_windows_per_category
        self.device = device
        self._lock = Lock()

    def analyze(self, document_text, *, doc_id, text_sha256, category_ids,
                context: AnalysisContext, progress=None, cancelled=None):
        # Do not queue a request behind an uncancellable in-process lock.
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("Analyzer is busy; serialize jobs or use a separate worker instance.")
        try:
            return self._analyze(document_text, doc_id, text_sha256, category_ids, context, progress, cancelled)
        finally:
            self._lock.release()

    def _analyze(self, source, doc_id, digest, category_ids, context, progress, cancelled):
        from ._inference import disjoint_candidates, window_candidates, window_count
        import numpy as np

        def check_cancelled():
            if cancelled and cancelled():
                raise AnalysisCancelled("Analysis cancelled by caller; no completed result returned.")

        require(isinstance(source, str) and isinstance(doc_id, str) and doc_id, "Invalid source/doc_id.")
        require(digest == text_digest(source), "Caller text hash mismatch.")
        require(category_ids and all(isinstance(c, str) and c for c in category_ids)
                and len(set(category_ids)) == len(category_ids), "Request unique, nonempty category IDs.")
        require(all(c in self.category_ids for c in category_ids), "Unknown catalogue category.")
        check_cancelled()
        view, decorations = _source_view(source, context)
        warnings = [*context.warnings, "experimental_candidate_only_unvalidated",
                    "bounded_candidate_generation_not_exhaustive", "rules_and_retrieval_not_run"]
        if not context.parser_complete:
            warnings.append("parser_incomplete")
        if decorations:
            warnings.append("decorations_masked_same_source_coordinates")
        # Whitespace-only input is unavailable; do not call it an absent document.
        active = [c for c in category_ids if c in self._questions and view.strip()]
        raw, offsets = self._tokenizer.context(view) if active else (None, None)
        totals, truncated = {}, {}
        for cat in active:
            query, original_length = self._tokenizer.question(self._questions[cat])
            totals[cat] = window_count(len(raw.ids), len(query.ids))
            truncated[cat] = original_length > 64
        total, done, results = sum(totals.values()), 0, []
        check_cancelled()
        if progress:
            progress(ProgressEvent("inference", 0, total))
        for cat in category_ids:
            check_cancelled()
            if cat not in active:
                reason = "unsupported_india_extension" if cat not in self._questions else "no_analyzable_text"
                results.append(CategoryResult(cat, "unavailable", None, reason, False, 0, 0, 0))
                continue
            n = totals[cat]
            limit = n if self.max_windows_per_category is None else min(n, self.max_windows_per_category)
            windows = iter(self._tokenizer.windows(raw, offsets, self._questions[cat]))
            candidates, completed = [], 0
            while completed < limit:
                check_cancelled()
                rows = list(islice(windows, min(self.batch_size, limit - completed)))
                require(bool(rows), "Tokenizer returned fewer windows than planned.")
                starts, ends = self._backend.predict([r[1] for r in rows])
                require(starts.shape == ends.shape == (len(rows), 512), "Invalid inference batch shape.")
                for j, (_, encoding, _) in enumerate(rows):
                    row = completed + j
                    seq = np.array([-1 if s is None else s for s in encoding.sequence_ids])
                    candidates.extend(window_candidates(starts[j], ends[j], seq,
                        np.asarray(encoding.offsets), view, row, row > 0, row < n - 1))
                completed += len(rows)
                done += len(rows)
                if progress:
                    progress(ProgressEvent("inference", done, total))
                check_cancelled()
            # Filter decoration-crossing intervals without splitting/merging or relocating.
            crossing = [c for c in candidates if c["margin"] > 0 and any(
                c["start"] < b and c["end"] > a for a, b in decorations)]
            clean = [c for c in candidates if not any(c["start"] < b and c["end"] > a
                                                     for a, b in decorations)]
            selected = disjoint_candidates(clean)
            boundary = any(c["boundary_review"] for c in selected)
            issues = []
            if completed < n:
                issues.append("window_limit")
            if truncated[cat]:
                issues.append("question_truncated_first64")
            if boundary:
                issues.append("boundary_review")
            if crossing:
                issues.append("decoration_crossing_candidate_omitted")
            warnings.extend(f"{issue}:{cat}" for issue in issues)
            clauses = [ClauseFinding(
                id=canonical_sha256([digest, doc_id, cat, c["start"], c["end"]]), category_id=cat,
                span=Span(doc_id, digest, c["start"], c["end"], source[c["start"]:c["end"]]),
                status="review_candidate", confidence=None, confidence_band="unvalidated",
                calibration_scope="unvalidated", origin="model") for c in selected]
            complete = context.parser_complete and not issues
            reason = ("unvalidated_model" if complete else "processing_incomplete_unvalidated")
            if completed == 0:
                reason = "window_limit_not_processed"
            results.append(CategoryResult(cat, "abstained" if completed else "unavailable", None,
                                          reason, complete, completed, n, len(clauses), clauses))
        check_cancelled()
        result = AnalysisResult(CONTRACT_VERSION, doc_id, digest, self._manifest_sha256,
                                "real", results, list(dict.fromkeys(warnings)))
        validate_result(result, source)
        return result
