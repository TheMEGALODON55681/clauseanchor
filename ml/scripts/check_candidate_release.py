"""Verify the portable release in an isolated subprocess and run a CPU smoke.

This exercises trained weights from the extracted ZIP, never saved predictions.
Parser contexts are simulated; this does not claim live parser/API/UI integration.
"""
import argparse
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_candidate_release import (
    ARTIFACT, ARTIFACT_PIN, ROOT, VERSION, ZIP_NAME, canonical_sha256, file_spec,
    read_json, require, verify_tree, verify_zip, write_json,
)


def smoke_source():
    header = 'MAPLE SERVICES — REPEATED HEADER\r\n'
    law = 'This Agreement shall be governed by the laws of the State of New York.'
    return (header + 'MAPLE AND CEDAR SERVICES AGREEMENT\r\n'
            'Unicode offset marker: café, ₹500, e\u0301, 😊.\r\n'
            'This Agreement is entered into on 1 October 2026 between Maple Labs and Cedar Services.\r\n'
            + law + '\r\n'
            + 'The supplier will deliver monthly service reports to the designated contact.\r\n' * 50
            + 'SCHEDULE A — separate occurrence\r\n' + law + '\r\n'
            'The aggregate liability shall not exceed fees paid during the preceding twelve months.\r\n'), len(header)


def exercise(analyzer):
    """Behavior checks shared by the real CPU run and explicit test doubles."""
    from clauseanchor_core import (
        AnalysisCancelled, AnalysisContext, context_from_parsed_document,
        from_dict, text_digest, to_dict, validate_result,
    )
    source, header_end = smoke_source()
    cases = {}
    india = tuple(c for c in analyzer.category_ids if c.startswith('in.'))
    require(len(india) == 5, 'Expected all five unsupported India categories.')

    def invoke(label, *, text=source, categories=('cuad.governing_law',), context=None, cancel=None):
        events = []
        def progress(event):
            events.append({'stage': event.stage, 'completed_units': event.completed_units, 'total_units': event.total_units})
            print(f'{label}: {event.completed_units}/{event.total_units} windows', flush=True)
        started = time.perf_counter()
        result = analyzer.analyze(text, doc_id='package-smoke-'+label, text_sha256=text_digest(text),
            category_ids=categories, context=context or AnalysisContext(), progress=progress,
            cancelled=(lambda: cancel(events)) if cancel else None)
        elapsed = time.perf_counter()-started
        validate_result(result, text)
        require(from_dict(to_dict(result)) == result, 'Contract round trip differs.')
        require(result.mode == 'real' and result.artifact_manifest_sha256 == ARTIFACT_PIN, 'Wrong runtime artifact.')
        require(tuple(c.category_id for c in result.categories) == categories, 'Requested category order differs.')
        require(all(c.status in ('abstained', 'unavailable') and c.decision_confidence is None for c in result.categories),
                'Automatic decision emitted.')
        findings = [f for c in result.categories for f in c.clauses]
        require(all(f.status == 'review_candidate' and f.confidence is None and f.origin == 'model'
                    and f.confidence_band == f.calibration_scope == 'unvalidated'
                    and not f.rule_flags and not f.passages and f.retrieval_status == 'not_run' for f in findings),
                'Candidate-only semantics differ.')
        require(events and events[0]['completed_units'] == 0
                and all(e['stage'] == 'inference' for e in events)
                and all(a['total_units'] == b['total_units'] and a['completed_units'] <= b['completed_units']
                        for a, b in zip(events, events[1:])), 'Invalid progress sequence.')
        require(events[-1]['completed_units'] == sum(c.windows_done for c in result.categories)
                and events[-1]['total_units'] == sum(c.windows_total for c in result.categories), 'Progress/result mismatch.')
        cases[label] = {'seconds': elapsed, 'source_sha256': text_digest(text), 'result': to_dict(result),
                        'events': events, 'candidate_count': len(findings)}
        return result

    full = invoke('full', categories=('cuad.document_name', 'cuad.governing_law', 'cuad.cap_on_liability', *india))
    require(all(c.windows_done == c.windows_total and c.windows_total > 1 for c in full.categories[:3]),
            'All overflow windows must run.')
    require(all(c.status == 'unavailable' and c.reason_code == 'unsupported_india_extension'
                and c.windows_done == c.windows_total == 0 and not c.search_complete for c in full.categories[3:]),
            'Unsupported categories must remain unavailable.')
    cap = full.categories[2]
    require(not cap.search_complete and 'question_truncated_first64:cuad.cap_on_liability' in full.warnings,
            'Frozen query truncation must remain visible.')

    # This is explicitly a simulated parser transport, not a real parse.
    parsed = SimpleNamespace(source_text=source, text_sha256=text_digest(source), nodes=(),
        decorations=((0, header_end),), coverage=SimpleNamespace(partial=True),
        warnings=(SimpleNamespace(code='PARTIALLY_SCANNED_PDF'),))
    context = context_from_parsed_document(parsed, jurisdiction_scope='india_review')
    require(not context.parser_complete and len(context.structure_nodes) == 1
            and context.structure_nodes[0].kind == 'decoration', 'Parser context bridge differs.')
    partial = invoke('simulated_parser_partial', context=context)
    require(all(not c.search_complete and c.reason_code == 'processing_incomplete_unvalidated' for c in partial.categories)
            and all(w in partial.warnings for w in ('PARTIALLY_SCANNED_PDF', 'parser_incomplete',
                                                   'decorations_masked_same_source_coordinates')),
            'Partial parse/decoration warning lost.')
    require(all(f.span.start >= header_end for c in partial.categories for f in c.clauses), 'Decoration-crossing finding returned.')

    try:
        analyzer.max_windows_per_category = 1
        limited = invoke('window_limited')
        c = limited.categories[0]
        require(c.status == 'abstained' and c.windows_done == 1 < c.windows_total and not c.search_complete
                and 'window_limit:cuad.governing_law' in limited.warnings, 'Work limit concealed.')
    finally:
        analyzer.max_windows_per_category = None

    cancellations = {}
    for label, immediate in [('before_inference', True), ('after_first_window', False)]:
        events = []
        started = time.perf_counter()
        try:
            analyzer.analyze(source, doc_id='package-cancel-'+label, text_sha256=text_digest(source),
                category_ids=('cuad.governing_law',), context=AnalysisContext(),
                progress=lambda e: events.append({'stage': e.stage, 'completed_units': e.completed_units, 'total_units': e.total_units}),
                cancelled=lambda: immediate or any(e['completed_units'] >= 1 for e in events))
        except AnalysisCancelled:
            pass
        else:
            raise ValueError('Cancellation returned a successful result.')
        require(not events if immediate else bool(events) and 0 < events[-1]['completed_units'] < events[-1]['total_units'],
                'Cancellation timing differs.')
        cancellations[label] = {'raised_AnalysisCancelled': True, 'completed_result_returned': False,
                                'seconds': time.perf_counter()-started, 'events': events}

    # Reuse after cancellation also verifies that the instance lock was released.
    try:
        analyzer.max_windows_per_category = 0
        zero = invoke('not_processed').categories[0]
        require(zero.status == 'unavailable' and zero.reason_code == 'window_limit_not_processed'
                and zero.windows_done == 0 < zero.windows_total and not zero.clauses and not zero.search_complete,
                'Unprocessed category mislabeled.')
    finally:
        analyzer.max_windows_per_category = None
    empty = invoke('empty_source', text=' \r\n', categories=('cuad.governing_law', india[0]))
    require(all(c.status == 'unavailable' and not c.search_complete and not c.clauses for c in empty.categories)
            and empty.categories[0].reason_code == 'no_analyzable_text', 'Empty source interpreted as absence.')
    count = sum(c['candidate_count'] for c in cases.values())
    return {'source_text': source, 'source_sha256': text_digest(source), 'decoration_range': [0, header_end],
            'empty_source_text': ' \r\n', 'cases': cases, 'cancellation': cancellations,
            'exact_source_slices_checked': count, 'zero_processed_candidate_sets': sum(
                cat['windows_done'] > 0 and not cat['clauses'] for c in cases.values() for cat in c['result']['categories'])}


def cached_check(output, release_digest):
    manifest = read_json(output/'manifest.json')
    require(manifest['release_manifest_sha256'] == release_digest
            and file_spec(output/'report.json') == manifest['report'], 'Cached CPU report damaged or belongs to another release.')
    report = read_json(output/'report.json')
    require(report['release_manifest_sha256'] == release_digest and report['device'] == 'cpu', 'Cached CPU identity differs.')
    return report


def check_bundle(root, digest, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    require(not output.is_relative_to(root), 'Write check evidence outside the immutable extracted bundle.')
    verify_tree(root, digest)
    if output.exists():
        return cached_check(output, digest)
    sys.path.insert(0, str(root/'ml'))
    import clauseanchor_core
    require(Path(clauseanchor_core.__file__).resolve() == root/'ml/clauseanchor_core/__init__.py',
            'Editable checkout shadowed the extracted core.')
    print('Loading packaged checkpoint-000022 on CPU...', flush=True)
    started = time.perf_counter()
    analyzer = clauseanchor_core.CandidateOnlyAnalyzer(root/ARTIFACT,
        expected_manifest_sha256=ARTIFACT_PIN, device='cpu', batch_size=1, max_windows_per_category=None)
    load_seconds = time.perf_counter()-started
    checks = exercise(analyzer)
    completed = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    report = {'version': VERSION, 'release_manifest_sha256': digest, 'artifact_manifest_sha256': ARTIFACT_PIN,
        'status': 'passed' if checks['exact_source_slices_checked'] else 'incomplete_no_candidate_slices',
        'completed_at_ist': completed.isoformat(),
        'completed_by_packaging_deadline': completed <= datetime.fromisoformat('2026-11-06T23:59:59+05:30'),
        'device': 'cpu', 'batch_size': 1, 'runtime': analyzer.runtime, 'load_seconds': load_seconds,
        'core_imported_from_extracted_bundle': True, 'trained_weight_inference': True,
        'saved_predictions_replayed': False, 'simulated_parser_context_only': True,
        'live_parser_tested': False, 'backend_api_tested': False, 'frontend_tested': False,
        'manual_review_implementation_changed': False, 'quality_evaluation': False, 'checks': checks}
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.pending-cpu-', dir=output.parent) as temporary:
        stage = Path(temporary)/'cpu_check'
        stage.mkdir()
        write_json(stage/'report.json', report)
        write_json(stage/'manifest.json', {'release_manifest_sha256': digest, 'report': file_spec(stage/'report.json')})
        require(not output.exists(), 'Another CPU report appeared; preserve it.')
        os.rename(stage, output)
    return report


def run(repo):
    repo = Path(repo).resolve()
    root = repo/ROOT
    package = root/'package'
    receipt = read_json(package/'receipt.json')
    digest = receipt['release_manifest_sha256']
    require(file_spec(package/ZIP_NAME) == receipt['archive'], 'Package ZIP hash differs from receipt.')
    output = root/'cpu_check'
    with TemporaryDirectory(prefix='clauseanchor-release-') as temporary:
        extracted = Path(temporary)/'bundle'
        extracted.mkdir()
        print('Verifying and extracting the portable ZIP...', flush=True)
        verify_zip(package/ZIP_NAME, digest, extracted)
        if output.exists():
            report = cached_check(output, digest)
            print('Verified existing CPU report; no inference repeated.', flush=True)
        else:
            env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1')
            # -I removes cwd/PYTHONPATH/user-site imports; -B keeps the extracted inventory immutable.
            subprocess.run([sys.executable, '-I', '-B', str(extracted/'ml/scripts/check_candidate_release.py'),
                '--bundle-root', str(extracted), '--expected-release-sha256', digest, '--output', str(output)],
                cwd=temporary, env=env, check=True)
            report = cached_check(output, digest)
    require(report['status'] == 'passed', 'CPU run has no candidate slices; keep the incomplete report, do not claim absence.')
    print(f'PASS: extracted-package CPU checks. Load {report["load_seconds"]:.2f}s; '
          f'{report["checks"]["exact_source_slices_checked"]} source slices checked.', flush=True)
    print(f'Report: {output/"report.json"}\nReceipt: {package/"receipt.json"}', flush=True)
    print('Live parser/API/UI integration remains unverified. No quality or time-saving claim.', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-root', type=Path)
    parser.add_argument('--expected-release-sha256')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.bundle_root is None:
        require(args.expected_release_sha256 is None and args.output is None, 'Bundle options must be supplied together.')
        run(Path(__file__).resolve().parents[2])
    else:
        require(args.expected_release_sha256 and args.output, 'Supply the independently recorded release digest and external output path.')
        result = check_bundle(args.bundle_root, args.expected_release_sha256, args.output)
        require(result['status'] == 'passed', 'No candidate slices; CPU smoke is incomplete, never absence.')
