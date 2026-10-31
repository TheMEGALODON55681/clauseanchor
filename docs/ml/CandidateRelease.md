# Candidate prototype packaging and integration checks

Owner: Tanishq Arya. Prepared October 30, 2026, Asia/Calcutta.
Inspected main: `829ac165b7a8dbb53bfd74dc4e065819d1729dbd`, following Tanishq's
seven-file final-evaluation commit `93d2942`. Packaging/integration checks are
due **November 6**, release handoff **November 7**. The execution window remains
October 29–November 7. This is the extraction-focused research prototype.

**Status: packaging software prepared; Tanishq's real package build and CPU
check await execution and output review.** Live parser/API/UI integration is
unverified. A prepared checker or a unit-test result does not close those gates.

## Frozen behavior and measured limits

Release label: `clauseanchor-candidate-prototype-v0`; core package version stays
0.1.0, contract stays **2.0**. The selected weights, tokenizer, core files,
generation, disjoint decoder, catalogue and operating policy are unchanged.

- Findings are model-origin `review_candidate`, confidence null, band and scope
  unvalidated. Processed supported categories are `abstained` with reasons;
  unsupported/unprocessed categories are `unavailable`. No accepted findings,
  automatic absence, raw-score confidence or new core status is introduced.
- Full-test anchored candidate precision is **21.984%**, recall **67.991%**:
  8,174 suggestions, 1,797 matched gold, 6,377 false highlights and 846 misses.
  Sensitivity precision/recall is 21.712%/67.964%. Full-test mean false highlights
  per document is 62.52; 1,176 questions are processing-incomplete. These are
  noisy review suggestions, not automatic acceptance or a time-saving result.
- The separate authors-reference path's official AUPR is 43.635% full and
  44.024% sensitivity. These are not the deployed analyzer's accuracy. Official
  P@80R and P@90R remain zero under the unchanged evaluator. The final evaluation
  document shipped alongside this file records the full interpretation.
- All 46 catalogue entries remain `not_validated`; the five India categories,
  rules and retrieval are deferred. Zero candidates never establish absence.
  Preserve full text and neutral manual review; candidates do not contribute
  accepted coverage, and incomplete inventory/count remain null under the
  existing manual-review gate. No unfamiliar-clause classifier or new audit.

## Build and check on Tanishq's machine

Install this batch's files at their matching `ml/` and `docs/ml/` paths. From
the repository root in VS Code, use the existing environment without upgrades:

```powershell
conda activate clauseanchor
python -m unittest discover -s ml/tests -p "test_candidate_release.py"
python ml/scripts/package_candidate_release.py
python ml/scripts/check_candidate_release.py
```

Run each command only after the preceding command succeeds. Allow about 1.5 GB
of free disk for the ZIP and temporary extracted copy. No training checkpoint
load, model re-export, calibration, scoring or official-test inference occurs.

The **23 software tests** include archive damage/path checks, interrupted-build
publication, preservation of existing packages, status/cancellation checks and
an actual isolated subprocess with explicitly tiny random QA test weights.
They reuse the already prepared clean-backbone tokenizer assets. No selected
checkpoint quality claim comes from these tests.

The builder verifies the existing exported artifact and reviewed final
identity/report/curves against fixed hashes, and checks all 14 final producer
hashes. It packages matching files and verifies the ZIP before publishing it.
It does not load the model tensors, open CUAD examples or recalculate metrics.

The CPU checker verifies the archive, extracts to a temporary directory and
starts Python with `-I -B`, offline model loading and the extracted core at the
front of the import path. It checks the loaded module path, so an editable
checkout cannot silently substitute for the packaged source. Dependencies come
from the existing environment: this is a portable-source/weights check, not a
fresh dependency-installation test or a deployment benchmark.

The real packaged checkpoint runs on authored text with CRLF, Unicode, an emoji,
repeated wording and overflow windows. The checker exercises:

- Exact source slices and contract serialization; unvalidated/null-confidence
  findings; all planned windows and monotone progress.
- All five unsupported India categories and visible first-64 query truncation.
- A **simulated** partial parser context with header decoration masking and
  preserved warnings; offsets continue to refer to unchanged original text.
- An explicit one-window limit and zero-work limit, retaining the full planned
  denominator and honest abstained/unavailable states.
- Cancellation before inference and after one completed window, with no
  completed result returned; subsequent reuse of the same analyzer instance.
- Whitespace-only input staying unavailable. Any processed zero-candidate set
  must remain abstained; no particular extracted answer is required.

If no actual candidate slice is produced, the report is
`incomplete_no_candidate_slices`; do not turn that into a pass or absence claim.
This smoke tests software and packaging, not extraction accuracy.

Outputs, all outside Git:

```text
data/processed/cuad/candidate_release_v0/
  package/
    clauseanchor-candidate-prototype-v0.zip
    receipt.json
  cpu_check/
    report.json
    manifest.json
```

Return the command outputs plus **package/receipt.json**, **cpu_check/report.json**
and **cpu_check/manifest.json** for review. Do not upload the ZIP/weights.
The receipt retains its creation-time `cpu_package_check: pending`; the separate
CPU report is the bound check evidence. Do not manually edit either JSON.
This document is also a pre-build snapshot included in the immutable ZIP.
Record the later reviewed execution in the release handoff and phase status;
do not rebuild a tested package solely to replace this snapshot's status text.

If interrupted before publication, incomplete temporary output is not accepted
as a package or check. Repeating the same command verifies and reuses a complete
matching output. A completed CPU report prevents another inference run.
Changed inputs or damaged output fail instead of being silently overwritten.
Preserve a failed run and its terminal error for review; do not delete training
or final-evaluation records. The builder's archive is immutable once published.

## Package contents and independent hashes

The ZIP includes:

- Exact runtime `ml/clauseanchor_core/` files, `ml/pyproject.toml`, pinned
  inference requirements, the builder/checker source and the repository license.
- The complete `models/clauseanchor_candidate_v0/` export, including inference
  weights, tokenizer, provenance, decoder, prompts and catalogue.
- Frozen `evidence/identity.json`, `evidence/report.json` and
  `evidence/official_curves.json`; the identity embeds the closed operating policy.
- This document, `docs/ml/CUAD_FinalEvaluation.md`, and a release manifest with
  every payload's byte size and SHA-256.

Optimizer/scaler/RNG state, training data, feature arrays, raw question records,
full prediction dumps, backend/frontend code and dependency wheels are excluded.
The existing source/model provenance is retained; the repository license does
not replace upstream model/data provenance.

The **release manifest hash** and **ZIP byte hash** are printed/recorded in the
receipt after the build. They cannot be filled in before the actual package
exists. Keep the receipt alongside the ZIP and communicate its hashes separately
when transferring the package through the team's chosen channel.

The nested inference manifest's canonical SHA-256 remains:

```text
ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8
```

Weights byte SHA-256 remains:

```text
cd508f9eb20d43047dcfbefe37be0c32ff17f14712ce09aa9f263fbb8320ab36
```

The outer release hash covers packaging files and evidence; the nested artifact
hash is the `CandidateOnlyAnalyzer` loader argument. Do not interchange them.
Hash checks establish identity/integrity, not model quality or legal reliability.
No file transfer, message to Aryan, hosted download, deployment or release tag is
performed by these scripts.

## Recipient loading and the app boundary

Use Python 3.12. In a fresh CPU environment only, install the dependencies using
the same instructions as the verified analyzer export:

```powershell
python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r ml/requirements-inference.txt
```

Tanishq should keep his existing CUDA-enabled environment unchanged. Before
installing the core, extract the ZIP into a fresh directory and run its checker
with the outer hash from the independent receipt. Example, from that directory:

```powershell
python -I -B ml/scripts/check_candidate_release.py --bundle-root . --expected-release-sha256 <RELEASE_MANIFEST_SHA256> --output ../candidate-receiver-check
```

Replace the placeholder with the actual receipt value. The output directory
must be outside the extraction. A clean extraction is required: verification
rejects unexpected files, symlinks, duplicate ZIP paths and changed payloads.
Then install the matching core with `python -m pip install -e ml`. Installation
may create metadata in that directory; preserve the original ZIP and use a
fresh extraction for later immutable-package checks.

The app can load one serialized analyzer instance as follows:

```python
from clauseanchor_core import CandidateOnlyAnalyzer, context_from_parsed_document, to_dict

analyzer = CandidateOnlyAnalyzer(
    "models/clauseanchor_candidate_v0",
    expected_manifest_sha256="ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8",
    device="cpu", batch_size=1,
)
result = analyzer.analyze(
    parsed.source_text, doc_id=document_id, text_sha256=parsed.text_sha256,
    category_ids=("cuad.governing_law", "cuad.cap_on_liability", "in.arbitration"),
    context=context_from_parsed_document(parsed, jurisdiction_scope="india_review"),
    progress=on_progress, cancelled=is_cancelled,
)
payload = to_dict(result)
```

`parsed`, `document_id`, callbacks and API serialization are supplied by Aryan's
app. Preserve the exact source string, code-point/end-exclusive offsets and
source hash. Cancelled analysis raises `AnalysisCancelled`; do not return a
successful completed result. Serialize calls per instance; concurrent calls
raise a busy error. Category support and processing completeness remain distinct.

At inspected main `829ac16`, Aryan's backend now reads the ML catalogue. Its
existing code does not yet invoke `CandidateOnlyAnalyzer`. Catalogue loading
alone is not runtime integration, and no support label should be changed merely
to enable the analyzer. Tanishq's package does not add an HTTP route or alter
Aryan's parser/backend/frontend/deployment files.

Before claiming live integration, exercise a real parser output through the
analyzer and the app's source highlighting, progress, cancellation, incomplete
states and neutral manual review. That is a remaining app check, not a new ML
experiment or source-audit prerequisite. If unavailable by handoff, name it as
unverified and hand over the tested candidate package with this limitation.

## Prepared-batch verification

Assistant-side checks on October 30: all 23 new packaging/harness tests passed,
including the isolated tiny-random-model run; all 17 existing neutral manual-review
fixture tests also passed. The three newly committed final
producer files match the hashes recorded in the previously reviewed evaluation
identity; the other 11 were already checked and are unchanged by the new commits.
The Windows test-path fix is committed. No core/model/policy file is edited here.

The actual checkpoint is on Tanishq's machine, so the real portable ZIP, its
release digest, CPU timing and trained-weight check remain unmeasured until he
runs the commands and supplies their outputs. Do not mark packaging or live
integration complete from this prepared batch. Final evaluation remains closed;
no training, decoder experiment, calibration refit or test tuning follows.
