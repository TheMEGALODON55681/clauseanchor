# ClauseAnchor candidate prototype v0: release handoff

Owner: Tanishq Arya. Prepared October 31, 2026, Asia/Calcutta.
Inspected source: `06d615cc39104b547130cf6b79a57413ac624373`, including the
committed trained DOCX/parser/API integration check. Aryan owns the parser,
backend, frontend and deployment; Tanishq owns `ml/` and `docs/ml/`.

**Release decision: the frozen, uncalibrated candidate-only extraction research
prototype.** ML implementation, final evaluation, portable-package CPU checks
and local DOCX/parser/API/CPU integration are completed and reviewed. This
handoff is prepared; artifact transfer and recipient verification have not been
confirmed. Full application/deployment validation is not claimed.

The execution window remains **October 29–November 7, 2026 IST**. Available joint
integration checks remain due November 6; release handoff November 7. This does
not complete the original rules/retrieval/India-validation programme.

## 1. Frozen release and behavior

| Component | Identity or decision |
|---|---|
| Release | `clauseanchor-candidate-prototype-v0` |
| Package / contract | `clauseanchor-core` 0.1.0 / contract 2.0 |
| Trained model | Clean-split RoBERTa QA, selected `checkpoint-000022`; inference-only export |
| Decoder | Positive-margin `disjoint_full`; no global candidate cap |
| One decoder experiment | Failed: +1 matched gold against required +19; closed October 29 |
| Calibration | Failed the predeclared bin-gap check; unvalidated; closed October 29 |
| Operating policy | Retain candidate-only v0; automatic acceptance and absence disabled |
| Final evaluation | Completed and reviewed October 30; no post-test tuning |
| Support | 41 CUAD categories can produce candidates; all 46 catalogue entries `not_validated`; five India extensions unavailable |

Calibration OOF Brier 0.103406 and ECE 0.040156 do not override the failed
assessment or justify probabilities. There is no second decoder experiment,
calibrator, retraining branch or additional source-audit prerequisite.

Real findings remain `review_candidate`, `origin=model`, `confidence=null`, with
confidence band and calibration scope `unvalidated`. Supported processed
categories abstain; unsupported/unprocessed categories are unavailable with
reasons and honest work counts. Do not introduce `unassessable`, accepted findings
with null confidence, raw-score probabilities or absence inferred from zero
candidates. Rule flags/passages remain empty and retrieval status is `not_run`.

## 2. Artifact and companion records

The existing archive is on Tanishq's machine at this repository-relative path:

```text
data/processed/cuad/candidate_release_v0/package/clauseanchor-candidate-prototype-v0.zip
```

Hand over the unchanged ZIP and receipt through the team's chosen file-transfer
channel. The source repository does not contain trained weights. No hosted
download URL, transfer receipt, message, upload, release tag or deployment is
claimed by this document. Weights and generated evidence stay outside Git.

Preserve these companion paths, since each report/manifest has a different role:

```text
data/processed/cuad/candidate_release_v0/package/receipt.json
data/processed/cuad/candidate_release_v0/cpu_check/report.json
data/processed/cuad/candidate_release_v0/cpu_check/manifest.json
data/processed/cuad/candidate_api_v0/identity.json
data/processed/cuad/candidate_api_v0/results/report.json
data/processed/cuad/candidate_api_v0/results/manifest.json
```

Supply this document, [package verification](CandidateReleaseVerification.md),
[API verification](CandidateAPIIntegration.md) and
[final evaluation](CUAD_FinalEvaluation.md) alongside the archive or through the
source checkout. These are companion records, not new ZIP payloads.

The ZIP already includes runtime source, inference requirements, model/tokenizer
export, decoder/prompts/catalogue, provenance, checker, license and frozen final
identity/report/official curves. It excludes datasets, optimizer state, caches,
backend/frontend and dependency wheels. Retain the included license and upstream
provenance; this handoff makes no new distribution-permission claim.

The packaged `CandidateRelease.md` is intentionally a pre-build snapshot. Its
pending status and old "no analyzer route" observation are historical; later
verification records supply the measured outcomes. The receipt's creation-time
`cpu_package_check: pending` similarly coexists with the later bound CPU report's
`status: passed`. **Do not edit the tested ZIP, packaged snapshots or generated
JSON, or rebuild the archive solely to update wording.**

### Independent identities

| Item | SHA-256 |
|---|---|
| ZIP bytes; size 509,869,238 bytes (about 486.25 MiB) | `28d43542251d8b1800b2904f3c70e03840487188971ac0bf8bde8b3b93cbe758` |
| Outer release manifest, canonical JSON | `29b4553786eb4e9f8cba8f6fb2244358406d101e460f77f3200542386ff84184` |
| Inference manifest, canonical JSON | `ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8` |
| Selected inference weights, bytes | `cd508f9eb20d43047dcfbefe37be0c32ff17f14712ce09aa9f263fbb8320ab36` |
| Final-evaluation identity, canonical JSON | `0de0bbd440ebc2ba3797c84e82c18dd074ba9b6a42d36f055a849bd531946a7c` |
| Package CPU report, bytes | `4be34394e8c7f16b69d7859915fe9d4cdab8acf44b5765082da20c58eb84786d` |
| Local API identity, canonical JSON | `f78bf85742ac054597264565acd9bee0ff1ff268aba189f1021f7bbcba853406` |
| Local API report, bytes | `7ae189413ac2bfa8a273ff39f2e39422f5979b2613bb9d7850917b071e93efc8` |

Use the ZIP byte hash for transfer, the **outer** digest for the package checker
and the **inference** digest for the analyzer/backend. Hashing an indented JSON
file's bytes does not produce its canonical JSON digest. Identity checks do not
establish extraction quality.

## 3. Recipient verification and loading

These steps are for a new receiving machine. Tanishq's completed model/package/API
runs do not need repeating. From the folder containing the received ZIP, compare
size and SHA-256 with section 2:

```powershell
Get-Item .\clauseanchor-candidate-prototype-v0.zip | Select-Object Length
Get-FileHash .\clauseanchor-candidate-prototype-v0.zip -Algorithm SHA256
```

Stop on a mismatch and request an intact copy. With a matching archive, extract
into a new directory; keep companion documents outside that extraction:

```powershell
Expand-Archive -LiteralPath .\clauseanchor-candidate-prototype-v0.zip -DestinationPath .\candidate-release
Set-Location .\candidate-release
```

Use Python 3.12. For a fresh CPU-only conda environment, without replacing
Tanishq's existing CUDA environment:

```powershell
conda create -n clauseanchor_candidate_cpu python=3.12.14 pip -y
conda activate clauseanchor_candidate_cpu
python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r ml/requirements-inference.txt
```

Pins: NumPy 2.3.5, Torch 2.9.1, Transformers 4.57.6, Tokenizers 0.22.2 and
Safetensors 0.7.0. Dependency installation needs package access; model artifacts
load locally. Fresh recipient installation is an instruction, not an already
verified outcome.

Before installing the core, verify the untouched extraction and run its CPU
check. Write output outside the extraction:

```powershell
python -I -B ml/scripts/check_candidate_release.py --bundle-root . --expected-release-sha256 29b4553786eb4e9f8cba8f6fb2244358406d101e460f77f3200542386ff84184 --output ../candidate-receiver-check
```

This checks every payload and executes packaged trained weights on authored
text. It is a new receiving-host check, not a model experiment. Preserve the
report/binding manifest; report failures without rewriting the archive. After
success, standalone users can install the verified core:

```powershell
python -m pip install -e ml
```

Installation may add metadata; use a fresh extraction for later immutable-package
checks. Keep the original ZIP. From the extracted root, load as follows:

```python
from clauseanchor_core import CandidateOnlyAnalyzer

analyzer = CandidateOnlyAnalyzer(
    "models/clauseanchor_candidate_v0",
    expected_manifest_sha256="ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8",
    device="cpu", batch_size=1,
)
```

For Aryan's backend, use the inspected source checkout or a subsequently reviewed
revision. Its requirements install the checkout's core, which the artifact loader
checks against the frozen manifest. API/parser dependency commands are in
[CandidateAPIIntegration.md](CandidateAPIIntegration.md). Set:

| Environment variable | Value |
|---|---|
| `CLAUSEANCHOR_ANALYZER` | `real` |
| `CLAUSEANCHOR_ARTIFACTS_DIR` | Absolute path to the verified extraction's `models/clauseanchor_candidate_v0` directory |
| `CLAUSEANCHOR_ARTIFACTS_SHA256` | `ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8` |
| `CLAUSEANCHOR_DB_PATH` | `:memory:` |

The existing `app.main:create_app` factory loads one CPU analyzer, batch 1, and
serializes analysis jobs. `/api/v1/ready` reports loading/ok/failed; failure never
falls back to the stub. Capabilities retain real mode and `not_validated` support.
These settings are not a deployment recipe or proof of a tested network server.

Pass immutable parser source/hash and
`context_from_parsed_document(parsed, jurisdiction_scope=...)` to `analyze()`;
forward progress/cancellation. See [RealAnalyzer.md](RealAnalyzer.md) and
[Interface.md](Interface.md) for full call semantics. Offsets count Python Unicode
code points, with exclusive ends. JavaScript must map them to UTF-16 positions or
validate with `Array.from(source).slice(start, end).join('')`. Never normalize the
source or search for the first matching occurrence to position a highlight.

## 4. Measured quality and execution limits

Actual frozen-analyzer evaluation uses one-to-one anchored matching at character
IoU >=0.5 on CUAD text. These are candidate metrics, not accepted-finding
precision or arbitrary-upload/India quality:

| Slice | Documents | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| Full official test | 102 | 1,797 | 6,377 | 846 | 21.984% | 67.991% |
| Known-overlap sensitivity | 93 | 1,659 | 5,982 | 782 | 21.712% | 67.964% |

Full test returned 8,174 candidates, with 1,488 exact matches and 62.52 false
highlights per document on average. There were 1,176 processing-incomplete
questions and 2,242 zero-candidate questions, including 36 with gold. Sixteen of
41 measured categories have sparse support; none becomes validated. Accepted
precision is undefined because the accepted set is empty. No absence accuracy
is claimed.

The separate authors-reference path gives clean-checkpoint official AUPR 43.635%
versus 42.586% for the released reference. Clean P@80R/P@90R are zero under the
unchanged evaluator; released P@80R is 31.131%. These are different computations
from the deployed disjoint analyzer and do not establish overall superiority.
[CUAD_FinalEvaluation.md](CUAD_FinalEvaluation.md) records sensitivity, intervals,
training-exposure differences and the lookup-grid endpoint explanation. No result
selects a new model, cutoff or decoder.

| Reviewed Windows check | Observation |
|---|---|
| Isolated package, October 31 13:56 IST | CPU load 25.81 s; full authored call 3.34 s, 8/8 windows; 10 exact slices across full/partial/limited calls |
| Actual local DOCX/parser/API, October 31 14:28 IST | Startup to readiness 17.47 s; complete call 4/4 windows, 5 candidates, 1.86 s; partial call 5/5 windows, 5 candidates, 2.01 s |
| API cancellation | Requested at 1/105; terminal at 2/105; no completed result |
| API session cleanup | Delete 204; old token rejected with 401 |

API times include submission/polling; startup and isolated model load measure
different operations. These are single-run observations, not benchmarks or
measured time savings. Evaluation used the frozen GPU path; CPU checks establish
operation/source integrity, not a new CPU accuracy measurement. Exact source
slices can still be wrong suggestions: the API smoke retains a newline and an
unrelated service-report sentence as governing-law candidates.

Supplied reports, bindings and source slices were reviewed. The large ZIP/weights
were not uploaded to the assistant; their on-disk checks and execution are
evidenced by Tanishq's local tools. No trained inference was rerun during review.

## 5. Remaining ownership and release boundary

| Item | Status / owner |
|---|---|
| Export, contract, evaluation, portable-package CPU check | Complete/reviewed; Tanishq |
| Real DOCX/parser/API/model path, partial states, cancellation | Checked via local ASGI TestClient using Aryan's unchanged app |
| Browser highlights, navigation and neutral manual-review presentation | Unverified; Aryan |
| PDF upload through real model/API and resulting presentation | Unverified; Aryan |
| Listening network server and target-host loading/deployment | Unverified; Aryan |
| ZIP transfer and recipient hash/load acknowledgement | Not confirmed; Tanishq supplies artifact, Aryan records receipt/check |
| Rules, verified judgment corpus/retrieval, India-category validation | Deferred beyond this release; no later completion date promised |

Preserve full-source access and neutral manual review from
[ScopeFixtures.md](ScopeFixtures.md). Only accepted findings contribute accepted
coverage; review candidates stay separate. Incomplete work keeps manual inventory
and count null rather than zero. Unhighlighted text, zero candidates and zero
manual-review items never establish absence, harmlessness or complete review.
No unfamiliar-clause classifier, new importance audit, formal workload study or
safety score is added.

By November 6, record available app checks with source revision and actual
outcome, particularly Unicode/repeated-text highlights and incomplete states.
If unavailable, retain those explicit gaps in the November 7 handoff. They do
not justify another ML experiment or declaring the original ML scope complete.

## 6. Closing this handoff

This batch changes only `docs/ml/ReleaseHandoff.md` and `docs/ml/Phases.md`.
No inference, test suite, training, evaluation or archive rebuild is required.
Before transferring, Tanishq can verify the existing ZIP from the repository root:

```powershell
Get-FileHash -LiteralPath "data/processed/cuad/candidate_release_v0/package/clauseanchor-candidate-prototype-v0.zip" -Algorithm SHA256
```

Compare with section 2, then commit the two documentation files after review.
Transfer the unchanged archive/receipt and companion records through the team's
chosen channel, recording actual recipient acknowledgement/check when available.
Until then the status is **handoff prepared; transfer/recipient verification
pending**, not delivered or deployed. No automated message or transfer is
authorized by this document.
