# Candidate prototype: local parser/API integration check

Updated October 31, 2026, Asia/Calcutta. Owner: Tanishq Arya. **Trained Windows
DOCX/parser/API/CPU check completed and supplied evidence reviewed.** Remaining
integration checks stay due November 6; release handoff November 7.
The October 29–November 7 window is unchanged.

## Verified starting point

Main was inspected at `b6f22bfd9052770231da7ce7cd90cf6c0e267cca`, including
Tanishq's six-file packaging commit `4e137e9`. Aryan's real analyzer factory,
upload, parser subprocess and analysis jobs are present; their last relevant
commit is `49c2c17ff67bba942d9bb609cd8a2e7f08371c89`.

The selected checkpoint remains `checkpoint-000022`. Training, the one decoder
experiment, failed calibration assessment, policy decision, frozen evaluation
and isolated portable-package CPU check are closed. See
[CandidateReleaseVerification.md](CandidateReleaseVerification.md) for the last
verified results. This batch changes only `ml/` and `docs/ml/`.

## What this check exercises

`ml/scripts/smoke_candidate_api.py` loads the actual FastAPI app with its real CPU
analyzer, in-memory session store, parser subprocess and analysis worker. Requests
use local ASGI `TestClient`; no listening network server or browser is started.
It generates two deterministic, authored DOCX documents in memory and sends them
through the upload API. It does not use CUAD examples or fixture answer replay.

1. Complete DOCX: document-name and governing-law analysis, Unicode source,
   repeated text, a real header decoration, exact candidate offsets and IDs.
2. Partial DOCX: a real unsupported `altChunk` block causes parser partial
   coverage. Governing law, cap on liability and the India arbitration extension
   check partial-state/warning transport, query truncation and unavailability.
3. Cancellation: another request on the parsed complete document requests all
   41 CUAD categories, then cancels after observed inference progress. This
   checks interrupted work, not all-category extraction quality.
4. Session deletion: deletion succeeds and the old bearer token is rejected.

All returned candidates must remain `review_candidate`, model-origin, null
confidence and unvalidated. Supported categories abstain; unsupported India
categories are unavailable with a reason. Decision coverage remains zero. API
processing completeness must match parser coverage and category searches; a
complete parse can still produce a partial analysis. Zero candidates never
establish absence. At least one candidate slice must actually be checked before
the overall run passes. Neutral manual-review implementation is unchanged.

This is a local DOCX parser/API/model integration check. It does **not** verify
frontend rendering/highlight selection, the PDF path, a network server, deployment,
privacy beyond the observed session deletion behavior, extraction accuracy or
time savings. Those limits must remain explicit in the release handoff.

## Pinned evidence

| Item | SHA-256 |
|---|---|
| Inference manifest, canonical JSON | `ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8` |
| Portable release manifest, canonical JSON | `29b4553786eb4e9f8cba8f6fb2244358406d101e460f77f3200542386ff84184` |
| Reviewed package CPU report, file bytes | `4be34394e8c7f16b69d7859915fe9d4cdab8acf44b5765082da20c58eb84786d` |
| Backend snapshot, canonical map of LF-normalized file hashes | `183e3b1793ac1959dbdcc4423f411a69a8990051e0d4dd330b30340da4b2c58e` |

Preflight verifies every inference-artifact file and frozen core source hash,
the earlier package receipt/report binding, the backend snapshot, Python 3.12
and required package versions. Backend hashes cover `backend/app/**/*.py`,
`backend/requirements.txt` and `backend/constraints.txt`; CRLF/LF differences are
ignored. Other source changes are not silently accepted. No model, ZIP or
evaluation rebuild is needed. The original verified export is used at
`models/clauseanchor_candidate_v0`.

## Install these four files

Copy the delivered files into their matching paths under the repository:

- `ml/scripts/smoke_candidate_api.py`
- `ml/tests/test_candidate_api.py`
- `docs/ml/CandidateAPIIntegration.md`
- `docs/ml/Phases.md`

These are the commands used for the completed check, retained for loading and
reproduction. **Tanishq does not need to rerun them.** Use the existing conda
environment. From VS Code's PowerShell terminal:

```powershell
conda activate clauseanchor
Set-Location "C:\Users\Asus\OneDrive\Desktop\ClauseANchor\clauseanchor\backend"
python -m pip install -r requirements.txt -c constraints.txt -c ../ml/requirements-inference.txt httpx==0.28.1
Set-Location ..
python -m unittest discover -s ml/tests -p "test_candidate_api.py"
python ml/scripts/smoke_candidate_api.py
```

Run the smoke only if installation and tests succeed. The two constraint files
retain the existing inference pins and CUDA Torch build while adding Aryan's
API/parser dependencies. The tests reuse the existing clean-backbone tokenizer
files and construct tiny random QA weights solely for software verification.
The smoke CLI accepts only the pinned trained export; it cannot select that test
model or fall back to a stub. A Starlette warning about its pinned HTTPX transport
is a deprecation notice, not a test failure; do not change dependencies for it.

## Output and review

The script prints parser/analysis progress and writes:

```text
data/processed/cuad/candidate_api_v0/identity.json
data/processed/cuad/candidate_api_v0/results/report.json
data/processed/cuad/candidate_api_v0/results/manifest.json
```

The identity records source/artifact/dependency hashes. The report contains only
these authored documents, parsed canonical text, API results, observed progress,
timings and session-cleanup status codes. The bearer token is never saved.
Timings are observations from this check, not a throughput benchmark.

The supplied terminal output and all three JSON files have now been reviewed as
recorded below. Keep generated evidence outside Git. Commit the smoke script,
its tests, this measured record and the updated `Phases.md` together. Preserve
the generated JSON and tested script unchanged; this documentation update does
not require another run.

A completed report is checked and reused without repeating inference. A failed
or incomplete report is preserved and blocks an automatic rerun. If a pin fails,
send the error; do not delete evidence, bypass the check or rebuild the package.
If VS Code closes before any final report exists, the same command can restart
this small smoke; it is not training or evaluation collection. Preserve any
existing identity. No deadline is extended by a restart.

## Verification before delivery

Assistant-side: 18 focused tests passed using the real app, real DOCX parser
subprocess and tiny random CPU weights. They cover source/offset corruption,
candidate-only semantics, partial coverage, cancellation, token-free reporting,
backend newline handling and evidence preservation/reuse. Dependency consistency
also passed. That Linux software run used random weights; the separate trained
Windows evidence is recorded below. Aryan owns frontend and deployment work.

## Trained Windows result and evidence review

The run completed **October 31 at 14:28:33 IST**, before the November 6 deadline.
Tanishq's 18 focused tests passed in **7.208 seconds**. Dependency installation
succeeded with the prescribed pins; the identity retains Python 3.12.14 and
Torch 2.9.1+cu126 while the actual app analyzer uses CPU. The pinned `certifi`
version replacing a newer installed version is an expected constraint result.

Startup to API readiness took **17.47 seconds**, including app startup and model
loading. This is not an isolated weight-load measurement. The two analysis times
below include API submission/polling and are not throughput estimates.

| Request | Observed windows | Candidates | API result | Processing complete | Resolved decisions | Analysis wall time |
|---|---:|---:|---|---|---|---:|
| Complete DOCX: document name, governing law | 4/4 | 5 | succeeded | true | 0/2 | 1.86 s |
| Partial DOCX: governing law, cap on liability, India arbitration | 5/5 | 5 | partial | false | 0/3 | 2.01 s |
| Cancellation on 41 CUAD categories | 2/105 | No result returned | cancelled | false | 0/41 | Not assessed |

Both parser jobs finished successfully. The second parsed document nevertheless
correctly retained `coverage.partial=true` and `UNSUPPORTED_DOCX_FEATURE` for its
unsupported `altChunk`; parse-job success does not mean complete source coverage.
The two extracted source strings are identical because the unsupported block is
omitted, but their completeness metadata differs. Both have 4,294 Python Unicode
code points, parser version `1.1.0`, and source SHA-256:

`dd8eb9ce6573b32dbcd910ec6c512bd451ec61ad81a6f99c36903674d8f4e8a1`

The review independently verified all ten returned source slices, their IDs,
null/unvalidated candidate fields, parser block/node slices, header exclusion,
request/result/job identities, progress denominators and saved core/API equality.
The supported categories abstain and count as unresolved even when processing is
complete. In the partial call, cap-on-liability query truncation remains visible;
India arbitration is unavailable with `unsupported_india_extension` and 0/0
windows. All 46 capability entries remain `not_validated`.

Cancellation was requested after observing 1/105 windows and became terminal at
2/105: another in-flight window completed before cancellation took effect. The
cancelled analysis has no categories or artifact-result digest, false processing
completeness and zero resolved decisions. Session deletion returned 204; the old
token then received 401. No bearer token or authorization headers are present in
the report.

Ten exact slices means five candidates in each of two calls, **not ten correct
or distinct clauses**. Governing law includes the unrelated service-report
sentence at `[229,305)` and a newline at `[228,229)` in both calls. Repeated law
sentences retain their separate source positions. Preserve these noisy outputs
and the frozen decoder; this check supplies no new accuracy or calibration claim.
No processed supported category returned zero candidates in these two calls;
empty-output semantics remain covered by the software tests, not this smoke.

### Evidence bindings

| Evidence | SHA-256 |
|---|---|
| Identity, canonical JSON | `f78bf85742ac054597264565acd9bee0ff1ff268aba189f1021f7bbcba853406` |
| Report, file bytes (119,296 bytes) | `7ae189413ac2bfa8a273ff39f2e39422f5979b2613bb9d7850917b071e93efc8` |
| Results manifest, file bytes | `272d8aa0e2348851cb14ec820009da083ac6ba30b913f10c23e001721a159633` |
| Smoke script, LF-normalized bytes | `92511270e6c65b1ad99294df12334b9d1c60bc700a3a2cb4d3746203310011d6` |

The identity/report/manifest bindings match. The recorded backend file hashes
and smoke-script hash match the inspected sources; artifact, package and prior
CPU-report pins match the already reviewed release evidence. Authored DOCX byte
hashes also reproduce when Windows ZIP creator metadata is retained. Linux ZIP
creator metadata alone changes archive byte hashes; no source or script fix is
needed.

Review used the supplied source strings, API results and identity/manifest files.
The selected weights were not supplied here and inference was not rerun; local
preflight and the user's trained execution provide that execution evidence.
The frozen package, model, decoder, backend and manual-review implementation are
unchanged. Local ASGI DOCX/parser/API/CPU integration is now checked. Frontend
highlight rendering, PDF integration, a listening network server and deployment
remain unverified; do not describe this as complete app or deployment validation.
