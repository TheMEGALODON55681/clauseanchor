# Candidate prototype package verification

Owner: Tanishq Arya. Execution and supplied-evidence review: October 31, 2026,
Asia/Calcutta. Release: `clauseanchor-candidate-prototype-v0`.

**Portable package creation and its isolated trained-model CPU smoke are
complete and reviewed.** The ML packaging checks are met ahead of November 6.
Live parser/API/UI integration and deployment remain unverified; the release
handoff remains due November 7. The October 29–November 7 window is unchanged.

Keep the tested ZIP, packaged source, `CandidateRelease.md` snapshot and generated
JSON unchanged. This separate record closes the package check without changing
the package's identity. No rebuild, model re-export, training, calibration,
decoder experiment or final evaluation rerun is required.

## Observed execution

Tanishq's **23 focused software tests passed in 76.350 seconds**. The builder
reported successful verification of the frozen export/final evidence and
publication of the portable archive. The CPU checker completed at
**13:56:32 IST on October 31**.

The checker reports import from the extracted package in an isolated subprocess,
actual checkpoint-000022 inference and no saved-prediction replay. Device was
explicitly **CPU**, batch size 1. Runtime: Python 3.12.14, NumPy 2.3.5,
Torch 2.9.1+cu126, Transformers 4.57.6, Tokenizers 0.22.2 and Safetensors 0.7.0.
The CUDA-capable Torch installation does not mean this smoke used the GPU.

Package loading took **25.81 seconds**. The full smoke call took **3.34 seconds**;
the simulated partial-context call 1.23 seconds and limited call 0.41 seconds.
These are one-run package-check timings, not total build time, application
latency, a throughput benchmark or evidence of time saved.

| Check | Completed/planned windows | Candidates | Observed behavior |
|---|---:|---:|---|
| Full raw-text call | 8/8 | 7 | Supported categories abstained; all five India categories unavailable |
| Simulated partial parser context | 3/3 | 2 | Abstained; search incomplete; parser and decoration warnings preserved |
| Explicit one-window limit | 1/3 | 1 | Abstained; full denominator and incomplete state retained |
| Zero-work limit | 0/3 | 0 | Unavailable, `window_limit_not_processed` |
| Whitespace-only source | 0/0 | 0 | Unavailable, `no_analyzable_text`; India extension unsupported |
| Cancellation before inference | No progress events | No result | `AnalysisCancelled` recorded |
| Cancellation after first window | 1/3 | No result | `AnalysisCancelled` recorded; no completed result returned |

The full call's eight windows are **2 Document Name + 3 Governing Law + 3 Cap on
Liability**. This correctly differs from the earlier adapter smoke's nine
windows because the authored input differs. Cap on Liability remains incomplete
because its question is truncated to the first 64 tokens. Completing all eight
planned windows does not make every requested category processing-complete.

All findings are model-origin `review_candidate` with null confidence and
unvalidated confidence band/calibration scope. All decision confidences are null.
No acceptance, absence, rules or retrieval output is added. The five India
extensions retain `unsupported_india_extension` with zero work.

## Supplied-evidence review

The reviewed inputs were the package receipt, CPU report and CPU report binding
manifest. The report's exact byte SHA-256 and length match that binding manifest;
all three agree on the outer release digest. The nested inference digest and
final-evaluation identity match the previously reviewed values.

The authored source was reconstructed from the delivered checker specification
and matches the report exactly: **4,368 Unicode code points**, with CRLF,
combining characters, an emoji and repeated wording. Its SHA-256 is
`3a27f94a8370a09b2e9e0f518fbf91ad6c1fdb2b64bedb9405fd7507aa1415de`.
The simulated decoration range is `[0, 34)`.

The unchanged core's strict deserializer/validator independently passed for
every returned result. The review checked all **10 exact source slices**, their
source/document identities, deterministic finding IDs, within-category
disjointness, candidate-only fields, category reasons, completeness/work counts,
progress sequences and cancellation records. The ten slices are **7 + 2 + 1
across separate calls**, not ten distinct correct clauses. No processed category
returned zero candidates in this particular smoke; the zero-candidate abstention
path remains covered by software tests rather than a new trained-model example.

Visible quality limitations persist: the raw call includes a punctuation-only
Governing Law candidate at `[4015, 4016)` and an overbroad candidate at
`[202, 1130)`. Exact offsets do not make these correct extractions. The raw-text
call also returns header text without a parser decoration context; the separate
partial-context call supplies that context. No new quality gate or filtering
rule is inferred from these examples. Frozen final evaluation remains the
quality evidence: full-test anchored precision 21.984%, recall 67.991%.

The large ZIP, outer release manifest and weights were not attached. Their
on-disk inventory/hash checks and actual model execution are reported by the
local builder/checker, not independently repeated here. The uploaded
`manifest.json` is the **CPU report binding**, not the outer release manifest.
This review establishes consistency of the supplied evidence and exact returned
source slices; it does not claim a fresh installation or live app test.

## Recorded identities

| Item | SHA-256 / size |
|---|---|
| Outer release manifest, canonical JSON, recorded by receipt | `29b4553786eb4e9f8cba8f6fb2244358406d101e460f77f3200542386ff84184` |
| ZIP bytes, recorded by receipt | `28d43542251d8b1800b2904f3c70e03840487188971ac0bf8bde8b3b93cbe758` |
| ZIP size | 509,869,238 bytes, approximately 486.25 MiB |
| Inference manifest, canonical JSON | `ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8` |
| Selected weights byte hash, retained from verified export | `cd508f9eb20d43047dcfbefe37be0c32ff17f14712ce09aa9f263fbb8320ab36` |
| Final-evaluation identity, canonical JSON | `0de0bbd440ebc2ba3797c84e82c18dd074ba9b6a42d36f055a849bd531946a7c` |
| Supplied package receipt bytes | `01698bd7142106e588fdd7dea168d79069062118c3d19e80ed68179be9c6bad8` |
| Supplied CPU report bytes | `4be34394e8c7f16b69d7859915fe9d4cdab8acf44b5765082da20c58eb84786d` |
| CPU report size | 29,417 bytes |
| Supplied CPU binding manifest bytes | `81dd22f185998f156ed424b4b191f006ca5a7f44723881f6316aff0d009c96b3` |

The receipt's `cpu_package_check: pending` is its creation-time state. The later
bound CPU report has `status: passed`; retain both unchanged. Use the **inference
manifest** digest for the analyzer/backend loader and the **outer release**
digest for the portable-package checker. They are different trust anchors.

## Current app boundary and remaining work

Remote main inspected October 31:
`49c2c17ff67bba942d9bb609cd8a2e7f08371c89`. Since the package's October 30 snapshot,
Aryan added document upload/parse jobs in `53f2ed1` and analyzer-backed jobs in
`49c2c17`. No ML/core/config file changed in those two commits.

Source inspection shows a real CPU analyzer factory with the external artifact
digest, `context_from_parsed_document` transport, source/result validation,
progress/cancellation forwarding and partial job states. Unresolved categories
do not count as resolved decisions. This updates the earlier snapshot's
"no analyzer route" observation: the code path now exists. It has not been
exercised with the selected artifact by this package smoke or this review.

The next integration check can use that actual parser/API path while keeping
Aryan's code ownership. Frontend highlighting/manual-review behavior and deploy
host loading remain separate checks. Do not mark these complete because a
factory or route exists. All catalogue entries remain `not_validated`; keep
neutral full-source manual review and null incomplete inventory/counts.

Finish available integration checks by **November 6**, then issue the release
handoff by **November 7** with any remaining live-app/deployment gap named.
No new decoder experiment, calibration procedure, source audit, workload study
or retraining branch is added. Candidate-only remains the release policy.

Keep the ZIP and generated evidence under
`data/processed/cuad/candidate_release_v0/`, outside Git. Commit the packaging
code/tests, original package instructions, this verification record and the
updated phase status. No artifact transfer, message to Aryan, push or deployment
has been performed by this review.
