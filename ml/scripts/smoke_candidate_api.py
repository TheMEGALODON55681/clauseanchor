"""Real local ASGI upload -> parser child -> analysis queue -> trained CPU model.

Only authored DOCX samples are used. No server port, training, model tuning,
fixture-answer replay, production session or frontend/deployment test.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import io
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
from xml.sax.saxutils import escape
from zipfile import ZIP_STORED, ZipFile, ZipInfo

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO/'ml'), str(REPO/'backend')]
from clauseanchor_core import from_dict, to_dict, validate_result
from clauseanchor_core.artifacts import canonical_sha256, file_spec, read_json, require, runtime_versions, verify_bundle, write_json

ROOT = 'data/processed/cuad/candidate_api_v0'
ARTIFACT = 'models/clauseanchor_candidate_v0'
ARTIFACT_PIN = 'ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8'
RELEASE_PIN = '29b4553786eb4e9f8cba8f6fb2244358406d101e460f77f3200542386ff84184'
CPU_REPORT_PIN = '4be34394e8c7f16b69d7859915fe9d4cdab8acf44b5765082da20c58eb84786d'
BACKEND_PIN = '183e3b1793ac1959dbdcc4423f411a69a8990051e0d4dd330b30340da4b2c58e'
API_PACKAGES = {'fastapi':'0.143.3', 'starlette':'1.8.0', 'httpx':'0.28.1', 'pydantic':'2.14.1',
                'lxml':'6.1.3', 'pdfminer.six':'20260107', 'pdfplumber':'0.11.10',
                'python-docx':'1.2.0', 'PyYAML':'6.0.3', 'uvicorn':'0.54.0'}
ENDED = {'succeeded', 'partial', 'cancelled', 'failed', 'timed_out'}
LAW = 'This Agreement shall be governed by the laws of the State of New York.'
HEADER = 'MAPLE API CHECK — HEADER'


def authored_docx(partial=False):
    """Deterministic minimal Word package, including a genuine header relationship."""
    w = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    package_rel = 'http://schemas.openxmlformats.org/package/2006/relationships'
    def paragraph(text):
        return '<w:p><w:r><w:t xml:space="preserve">'+escape(text)+'</w:t></w:r></w:p>'
    paragraphs = ['MAPLE AND CEDAR SERVICES AGREEMENT', 'Unicode marker: café, ₹500, e\u0301, 😊.',
        'This Agreement is entered into on 1 October 2026 between Maple Labs and Cedar Services.', LAW,
        *(['The supplier will deliver monthly service reports to the designated contact.']*50),
        'SCHEDULE A — separate occurrence', LAW,
        'The aggregate liability shall not exceed fees paid during the preceding twelve months.']
    chunk = '<w:altChunk r:id="rChunk"/>' if partial else ''
    contents = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    contents += '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    contents += '<Default Extension="xml" ContentType="application/xml"/>'
    contents += '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    contents += '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
    if partial: contents += '<Default Extension="html" ContentType="text/html"/>'
    parts = {'[Content_Types].xml': contents+'</Types>',
        '_rels/.rels': f'<Relationships xmlns="{package_rel}"><Relationship Id="rDoc" Type="{rel}/officeDocument" Target="word/document.xml"/></Relationships>',
        'word/document.xml': f'<w:document xmlns:w="{w}" xmlns:r="{rel}"><w:body>'+''.join(map(paragraph, paragraphs))+chunk+
            '<w:sectPr><w:headerReference w:type="default" r:id="rHeader"/></w:sectPr></w:body></w:document>',
        'word/header1.xml': f'<w:hdr xmlns:w="{w}">'+paragraph(HEADER)+'</w:hdr>',
        'word/_rels/document.xml.rels': f'<Relationships xmlns="{package_rel}"><Relationship Id="rHeader" Type="{rel}/header" Target="header1.xml"/>'+
            (f'<Relationship Id="rChunk" Type="{rel}/aFChunk" Target="omitted.html"/>' if partial else '')+'</Relationships>'}
    if partial: parts['word/omitted.html'] = '<html><body>Authored unsupported-content marker.</body></html>'
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w', compression=ZIP_STORED) as archive:
        for name, content in sorted(parts.items()):
            archive.writestr(ZipInfo(name, date_time=(1980,1,1,0,0,0)), content.encode('utf-8'))
    return buffer.getvalue()


def backend_hashes(repo):
    paths = sorted(p.relative_to(repo).as_posix() for p in (repo/'backend/app').rglob('*.py'))
    paths += ['backend/requirements.txt', 'backend/constraints.txt']
    return {n:hashlib.sha256((repo/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for n in paths}


def preflight(repo):
    files = backend_hashes(repo)
    require(canonical_sha256(files) == BACKEND_PIN,
            'Backend snapshot differs from reviewed 49c2c17. Preserve this run and report the mismatch; do not bypass the pin.')
    packages = {n:importlib.metadata.version(n) for n in API_PACKAGES}
    require(packages == API_PACKAGES, 'API/parser dependencies differ. Use the batch installation command with both constraint files.')
    inference_runtime = runtime_versions()
    verify_bundle(repo/ARTIFACT, ARTIFACT_PIN)
    release = repo/'data/processed/cuad/candidate_release_v0'
    receipt = read_json(release/'package/receipt.json')
    binding = read_json(release/'cpu_check/manifest.json')
    cpu = read_json(release/'cpu_check/report.json')
    require(receipt['release_manifest_sha256'] == binding['release_manifest_sha256'] == cpu['release_manifest_sha256'] == RELEASE_PIN
            and file_spec(release/'cpu_check/report.json') == binding['report']
            and binding['report']['sha256'] == CPU_REPORT_PIN and cpu['status'] == 'passed'
            and receipt['artifact_manifest_sha256'] == ARTIFACT_PIN, 'Reviewed package/CPU evidence differs.')
    return {'version':'candidate-api-v0', 'backend_sha256_lf':files, 'backend_snapshot_sha256':BACKEND_PIN,
        'artifact_manifest_sha256':ARTIFACT_PIN, 'release_manifest_sha256':RELEASE_PIN,
        'prior_cpu_report_byte_sha256':CPU_REPORT_PIN, 'api_packages':packages, 'inference_runtime':inference_runtime,
        'smoke_script_sha256_lf':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        'sample_sha256':{name:hashlib.sha256(authored_docx(partial)).hexdigest() for name,partial in [('complete',False),('partial',True)]}}


def check_progress(snapshots):
    active = [s for s in snapshots if s['total_units'] is not None]
    require(all(0 <= s['completed_units'] <= s['total_units'] for s in active), 'Invalid API progress bounds.')
    require(all(a['total_units'] == b['total_units'] and a['completed_units'] <= b['completed_units']
                for a,b in zip(active,active[1:])), 'API progress regressed or changed denominator.')


def check_analysis(parsed, document_id, ids, response, job, artifact_pin):
    """Validate exactly the categories returned by the API against its parser text."""
    require(response['document_id'] == document_id and response['text_sha256'] == parsed['text_sha256']
            and response['mode'] == 'real' and response['contract_version'] == '2.0'
            and response['artifact_manifest_sha256'] == artifact_pin, 'API result identity differs.')
    require(response['decision_coverage'] == {'resolved':0,'requested':len(ids)}, 'Unvalidated categories counted as resolved.')
    require([c['category_id'] for c in response['categories']] == list(ids), 'Category request/result mismatch.')
    core = from_dict({'contract_version':'2.0','doc_id':document_id,'text_sha256':parsed['text_sha256'],
        'artifact_manifest_sha256':artifact_pin,'mode':'real','categories':response['categories'],'warnings':response['warnings']})
    validate_result(core, parsed['source_text'])
    expected_complete = not parsed['coverage']['partial'] and all(c.search_complete for c in core.categories)
    require(response['processing_complete'] is expected_complete
            and response['status'] == job['status'] == ('succeeded' if expected_complete else 'partial'), 'App completeness/status differs.')
    require(job['error'] is None and job['completed_units'] == sum(c.windows_done for c in core.categories)
            and job['total_units'] == sum(c.windows_total for c in core.categories), 'Terminal API progress differs from result.')
    for cat in core.categories:
        require(cat.status in ('abstained','unavailable') and cat.decision_confidence is None, 'Automatic decision emitted.')
        require(cat.windows_done == cat.windows_total, 'Unexpected hidden work cap in completed API analysis.')
        if cat.category_id.startswith('in.'):
            require(cat.status == 'unavailable' and cat.reason_code == 'unsupported_india_extension' and not cat.search_complete,
                    'India inference was falsely available.')
        else:
            require(cat.status == 'abstained' and cat.windows_done > 0, 'Supported category did not run.')
            if parsed['coverage']['partial']:
                require(not cat.search_complete and cat.reason_code == 'processing_incomplete_unvalidated', 'Partial parser result became complete.')
        intervals = sorted((f.span.start,f.span.end) for f in cat.clauses)
        require(all(a[1] <= b[0] for a,b in zip(intervals,intervals[1:])), 'Overlapping frozen disjoint candidates.')
        for f in cat.clauses:
            require(f.status == 'review_candidate' and f.confidence is None and f.origin == 'model'
                    and f.confidence_band == f.calibration_scope == 'unvalidated'
                    and not f.rule_flags and not f.passages and f.retrieval_status == 'not_run', 'Candidate-only output changed at API.')
            require(f.id == canonical_sha256([parsed['text_sha256'], document_id, cat.category_id, f.span.start, f.span.end]),
                    'API finding ID changed.')
            require(not any(f.span.start < b and f.span.end > a for a,b in parsed['decorations']), 'Header decoration overlaps a finding.')
    if parsed['coverage']['partial']:
        require('parser_incomplete' in core.warnings and 'UNSUPPORTED_DOCX_FEATURE' in core.warnings, 'Partial parser warning lost at API.')
    require('decorations_masked_same_source_coordinates' in core.warnings, 'Header decoration transport missing.')
    return to_dict(core)


def run_probe(repo, artifact, digest, journal):
    """Use the unmodified app/factory/workers. Parameters enable explicit tiny-model unit tests."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.config import Settings
    from clauseanchor_core import CandidateOnlyAnalyzer
    from app.parsing.schema import from_json
    import app.main
    require(Path(app.main.__file__).resolve() == (repo/'backend/app/main.py').resolve(), 'Another backend shadows this checkout.')
    app = create_app(Settings(analyzer='real', artifacts_dir=artifact, artifacts_sha256=digest,
                              catalogue_path=repo/'ml/configs/catalogue.json', db_path=':memory:'))
    headers = None
    started = time.perf_counter()
    with TestClient(app) as client:
        def request(method, path, expected=200, **kwargs):
            answer = client.request(method, '/api/v1'+path, headers=headers, **kwargs)
            require(answer.status_code == expected, f'Unexpected HTTP {answer.status_code} at {method} {path}.')
            return None if expected == 204 else answer.json()
        def poll_job(job_id, snapshots, *, cancel_after_progress=False):
            deadline = time.monotonic()+180
            cancel_reply = None
            while True:
                current = request('GET', '/jobs/'+job_id)
                if not snapshots or current != snapshots[-1]:
                    snapshots.append(current)
                    print(f'analysis/parse job: {current["status"]}; {current["completed_units"]}/{current["total_units"]}', flush=True)
                if current['status'] in ENDED:
                    check_progress(snapshots)
                    return current, cancel_reply
                if cancel_after_progress and cancel_reply is None and current['status'] == 'running' and current['completed_units'] >= 1:
                    cancel_reply = request('POST', '/jobs/'+job_id+'/cancel', expected=202)
                require(time.monotonic() < deadline, 'API job wait exceeded 180 seconds; preserve evidence.')
                time.sleep(.02)
        try:
            print('Waiting for the actual backend analyzer to load on CPU...', flush=True)
            deadline = time.monotonic()+180
            while True:
                ready = client.get('/api/v1/ready')
                if ready.status_code == 200:
                    journal['ready'] = ready.json()
                    require(journal['ready']['ready'] is True and all(v == 'ok' for v in journal['ready']['checks'].values()),
                            'Readiness response is inconsistent.')
                    break
                require(ready.status_code == 503 and ready.json()['error']['details']['checks']['analyzer'] == 'loading',
                        'Backend readiness failed; inspect the local error instead of falling back to a stub.')
                require(time.monotonic() < deadline, 'Analyzer readiness exceeded 180 seconds.')
                time.sleep(.1)
            journal['startup_to_ready_seconds'] = time.perf_counter()-started
            require(type(app.state.analysis_queue.analyzer) is CandidateOnlyAnalyzer, 'Backend did not load the actual candidate analyzer.')
            require(app.state.analysis_queue.analyzer.device == 'cpu', 'Expected CPU app factory.')
            journal['actual_cpu_analyzer_loaded'] = True
            capabilities = request('GET','/capabilities')
            require(capabilities['mode'] == 'real' and len(capabilities['categories']) == 46
                    and all(c['support_status'] == 'not_validated' for c in capabilities['categories']), 'Capabilities claim validation or wrong mode.')
            journal['capabilities'] = capabilities
            # The bearer token remains only in memory; no headers/session response enter the report.
            headers = {'Authorization':'Bearer '+request('POST','/sessions',expected=201)['token']}
            journal['documents'] = {}
            for label, partial, ids in [('complete',False,('cuad.document_name','cuad.governing_law')),
                ('partial',True,('cuad.governing_law','cuad.cap_on_liability','in.arbitration'))]:
                upload = request('POST','/documents',expected=202, content=authored_docx(partial))
                item = journal['documents'][label] = {'upload':upload, 'parse_progress':[], 'analysis_progress':[]}
                parsed_job,_ = poll_job(upload['parse_job_id'], item['parse_progress'])
                require(parsed_job['status'] in ('succeeded','partial'), 'Real parser job failed.')
                document = request('GET','/documents/'+upload['document_id']); item['document'] = document
                parsed = document['parsed']; from_json(parsed)
                require(document['status'] == 'parsed' and parsed['coverage']['partial'] is partial, 'Unexpected parser completeness.')
                require(parsed['decorations'] and any(parsed['source_text'][a:b] == HEADER for a,b in parsed['decorations']), 'Real DOCX header was not preserved as decoration.')
                require('😊' in parsed['source_text'] and 'e\u0301' in parsed['source_text'] and parsed['source_text'].count(LAW) == 2,
                        'Authored Unicode/repeated occurrences changed during parse.')
                if partial:
                    require('UNSUPPORTED_DOCX_FEATURE' in [w['code'] for w in parsed['warnings']], 'Missing genuine unsupported-block warning.')
                began = time.perf_counter()
                request_body = {'category_ids':list(ids),'jurisdiction_scope':'india_review' if partial else 'unspecified'}
                response = request('POST','/documents/'+upload['document_id']+'/analyses',expected=202,json=request_body)
                item['analysis_request'] = request_body; item['analysis_ids'] = response
                final_job,_ = poll_job(response['job_id'], item['analysis_progress'])
                result = request('GET','/analyses/'+response['analysis_id'])
                item['analysis'] = result; item['analysis_wall_seconds'] = time.perf_counter()-began
                item['core_result'] = check_analysis(parsed,upload['document_id'],ids,result,final_job,digest)
                if partial:
                    require('question_truncated_first64:cuad.cap_on_liability' in result['warnings'], 'Query truncation warning lost.')

            # A broad request gives time to observe live progress before cancellation.
            # It is cancelled once, never completed as another evaluation/quality run.
            doc = journal['documents']['complete']['document']
            ids = [c['id'] for c in capabilities['categories'] if c['source'] == 'cuad']
            request_body = {'category_ids':ids,'jurisdiction_scope':'unspecified'}
            new = request('POST','/documents/'+doc['id']+'/analyses',expected=202,json=request_body)
            cancellation = journal['cancellation'] = {'request':request_body,'analysis_ids':new,'progress':[]}
            last,reply = poll_job(new['job_id'],cancellation['progress'],cancel_after_progress=True)
            cancellation['cancel_response'] = reply
            cancellation['analysis'] = request('GET','/analyses/'+new['analysis_id'])
            require(reply is not None and last['status'] == 'cancelled', 'Cancellation was not observed; preserve this result, do not claim a pass.')
            cancelled = cancellation['analysis']
            require(cancelled['status'] == 'cancelled' and cancelled['categories'] == [] and not cancelled['processing_complete']
                    and cancelled['artifact_manifest_sha256'] is None and cancelled['decision_coverage']['resolved'] == 0,
                    'Cancelled API request exposed a completed result.')
            require(last['total_units'] is not None and 0 < last['completed_units'] < last['total_units'], 'Cancellation did not stop unfinished inference.')
        finally:
            if headers is not None:
                deleted = client.delete('/api/v1/sessions/current',headers=headers)
                old_document = journal.get('documents',{}).get('complete',{}).get('upload',{}).get('document_id','missing')
                refused = client.get('/api/v1/documents/'+old_document,headers=headers)
                journal['session_cleanup'] = {'delete_status':deleted.status_code,'old_token_status':refused.status_code}
                require(deleted.status_code == 204 and refused.status_code == 401, 'Ephemeral smoke session did not close.')
    journal['candidate_slices_checked'] = sum(len(c['clauses']) for item in journal['documents'].values()
        for c in item['core_result']['categories'])
    require(journal['candidate_slices_checked'] > 0, 'Real API inference returned no slices; record incomplete rather than an offset-check pass.')


def run(repo):
    identity = preflight(repo)
    root = repo/ROOT; root.mkdir(parents=True,exist_ok=True)
    identity_path = root/'identity.json'
    if identity_path.exists():
        require(read_json(identity_path) == identity, 'API check identity changed; keep existing evidence for review.')
    else:
        require(not any(root.iterdir()), 'Nonempty API evidence directory lacks identity.')
        write_json(identity_path, identity)
    digest = canonical_sha256(identity)
    output = root/'results'
    if output.exists():
        manifest = read_json(output/'manifest.json'); report = read_json(output/'report.json')
        require(manifest['identity_sha256'] == digest and file_spec(output/'report.json') == manifest['report'], 'Cached API evidence differs.')
        require(report['status'] == 'passed', 'Existing incomplete/failed API report is preserved; review it before another attempt.')
        print('Verified existing API check; no inference repeated.',flush=True)
        return report
    journal = {}; error = None
    try:
        run_probe(repo,repo/ARTIFACT,ARTIFACT_PIN,journal)
    except (Exception,KeyboardInterrupt) as exc:
        error = exc
    completed = datetime.now(timezone(timedelta(hours=5,minutes=30)))
    report = {'version':'candidate-api-v0','identity_sha256':digest,'status':'passed' if error is None else 'incomplete_or_failed',
        'completed_at_ist':completed.isoformat(),'completed_by_integration_deadline':completed<=datetime.fromisoformat('2026-11-06T23:59:59+05:30'),
        'error_type':None if error is None else type(error).__name__, 'checks':journal,
        'transport':'local_ASGI_TestClient_actual_app_workers', 'live_parser_and_api_exercised':error is None,
        'selected_checkpoint_cpu_inference':any('core_result' in d for d in journal.get('documents',{}).values()),
        'frontend_verified':False,'pdf_path_verified':False,
        'network_server_or_deployment_verified':False,'quality_evaluation':False,'manual_review_implementation_changed':False}
    with TemporaryDirectory(prefix='.pending-api-',dir=root) as temporary:
        stage = Path(temporary)/'results';stage.mkdir()
        write_json(stage/'report.json',report)
        write_json(stage/'manifest.json',{'identity_sha256':digest,'report':file_spec(stage/'report.json')})
        require(not output.exists(),'Another report appeared; preserve it.')
        os.rename(stage,output)
    print(f'Report: {output/"report.json"}\nIdentity: {identity_path}',flush=True)
    if error is not None: raise error
    print(f'PASS: real DOCX parser/API/CPU path; {journal["candidate_slices_checked"]} exact candidate slices; '
          'partial states, progress, cancellation and session cleanup.',flush=True)
    print('Frontend, PDF and network/deployment checks remain unverified. No model-quality or time-saving claim.',flush=True)
    return report


if __name__ == '__main__':
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    run(REPO)
