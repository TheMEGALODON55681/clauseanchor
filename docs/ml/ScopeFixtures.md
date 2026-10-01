# Scope fixture handoff: Plan 1.1, sections 10.7 and 11.3

Status: development fixture pack prepared; application integration pending.

This pack supplies all eight required scenario families, expanded into 16 deterministic cases. It contains original synthetic contract text, exact source spans, simulated category scope, parser/job metadata and frozen expected results. It does not contain a trained model or establish legal correctness. The existing core interface remains version 2.0. The fixture envelope has its own version, 1.0.

## Start here in VS Code

Keep using the existing `clauseanchor` Conda environment with Python 3.12.14. No new environment or dependencies are required. Open the repository folder, pull using VS Code Source Control, and use its integrated PowerShell terminal. The prompt should start with `(clauseanchor)` and end at your repository root.

After adding this pack, run these commands **separately**, waiting for each to finish:

```powershell
python .\ml\scripts\check_scope_fixtures.py
```

Expected final summary: `PASS: 8 scope families; 16 cases; exact spans and reference expectations.` An incomplete case prints `manual_review_count=None`; JSON stores this as `null`. That is intentional, not a failure.

```powershell
python .\ml\scripts\check_contract.py
```

Expected: the original contract 2.0 check passes, with four category states and two exact spans.

```powershell
python -m unittest discover -s .\ml\tests -v
```

Expected for this repository baseline: `Ran 43 tests` followed by `OK`. This comprises the original 26 tests and 17 new tests. One new test checks all 16 frozen cases as subtests; cases and test-method counts are different quantities. If a teammate adds tests later, the total can increase.

The pack is additive: stage its 14 new files under `ml/` and `docs/ml/` after local checks pass. Do not stage the downloaded ZIP, extracted installer or an environment folder. Use a commit such as `Add scope fixtures for Plan 1.1 manual review`, then push through VS Code. The installer never commits or pushes.

## What a fixture teaches us

A fixture is an example with a predetermined answer. Here we prescribe the analyzer's output, then verify how the application must expose it. This makes development independent of training quality.

In case 1 the source contains two paragraphs:

```text
Liability is limited to the fees paid under this agreement.

The supplier may substitute blue packaging with green packaging.
```

The first paragraph occupies `[0, 59)` and has an accepted fixture finding. The second occupies `[61, 125)` and has no accepted finding. Positions 59 and 60 are newline characters. The selected simulated catalogue contains only `cuad.cap_on_liability`, so packaging is explicitly outside this fixture's catalogue. That statement makes no claim about its legal importance.

Expected: the category is `found`; the first paragraph is fully highlighted; the second appears under `Text without accepted findings`; both remain readable. Finding the first clause does not assess the rest of the agreement.

`[start, end)` includes the start character and stops before the end character. Offsets count Unicode code points, as Python string slicing does. They are not bytes or JavaScript UTF-16 indexes. Always check `source[start:end] == span.text` in Python. In JavaScript the equivalent validation is `Array.from(source).slice(start, end).join('')`. Repeated wording must be located by the supplied offsets, not by searching for the first occurrence.

## Files and scenario coverage

The JSON files below are under `ml/fixtures/scope/`. Each contains one family and a `cases` array. The source lives in each case's `document.text`; there is no separate text file to keep synchronized. JSON escapes preserve source newlines. Decode UTF-8 and hash the exact decoded source string encoded as UTF-8, without trimming or normalization.

| Family file | Cases | Main expected behaviour |
|---|---:|---|
| `01_supported_and_outside.json` | 1 | Supported clause plus outside-catalogue material; one manual-review item. |
| `02_outside_only.json` | 1 | Illustrative category absence; one manual-review item; no all-clear. |
| `03_mixed_paragraph.json` | 1 | Whole mixed paragraph remains; review candidate does not add accepted coverage. |
| `04_broad_span.json` | 1 | Whole paragraph accepted, including outside-catalogue text; zero items still means no safety verdict. |
| `05_distant_clauses.json` | 1 | Main limit and distant exception remain reachable with intervening definitions and schedules; no interaction-assessment claim. |
| `06_incomplete.json` | 5 | Parser omission, unfinished search, cancellation, truncated candidate search and boundary-coverage failure suppress completed inventory. |
| `07_positions.json` | 4 | Emoji, second repeated occurrence, overlapping findings, nested nodes, substantive gaps, invalid-node fallback, whitespace and union across categories. |
| `08_proposed_category.json` | 2 | Proposed category is distinguishable while unselected; requesting it produces `unavailable`, not validated support. |

Family 6 intentionally includes a job labelled `completed` with an unfinished category search. This checks that an outer job flag cannot override the category-level gate. The cancellation case contains available text and `core_result: null`, representing cancellation before a result was returned. Do not fabricate a core result for it.

`artifact.json` identifies the self-authored recipe and baseline. Each non-null core result's `artifact_manifest_sha256` is the SHA-256 of that file's bytes. It is a fixture identity, not a trained-model manifest. `manifest.json` separately pins the bytes of the eight family files and artifact file. It detects accidental edits; it is not a digital signature.

## Fixture envelope 1.0

This is a development interchange format, not an HTTP response schema. Do not add its fields to `AnalysisResult` or alter the exported core schema.

| Field | Meaning and consumer |
|---|---|
| `fixture_format_version` | Top-level family format version, `1.0`. |
| `family`, `title`, `cases` | Required plan scenario, readable title and its explicit variants. |
| `cases[].id`, `purpose` | Stable case ID and why it exists. |
| `document` | Immutable canonical `text`, `doc_id` and SHA-256 of UTF-8 text. |
| `catalogue` | Versioned simulated support catalogue. `simulated: true` is mandatory. |
| `requested_category_ids` | Ordered selection; non-null core results contain exactly these categories. |
| `parser` | Completion flag, minimal structure nodes and unavailable source-region descriptions. |
| `job` | Processing status, unfinished stages, truncation flag and boundary-coverage flag. These are application test inputs. |
| `core_result` | Existing core 2.0 result in `stub` mode, or null for the cancellation case. |
| `anchors` | Exact passages for human/context checks, including outside-catalogue material and distant clauses. These are annotations, not model findings. |
| `expected.category_states` | Expected core states; an empty object means no result was returned. |
| `expected.navigation` | Frozen units, accepted/candidate IDs, coverage labels, manual-review inventory and unavailable regions. |
| `expected.presentation` | Required disclosure, context access, category/support display, sample labels and report expectations. |

Every span uses the existing `{doc_id, text_sha256, start, end, text}` shape. Parser nodes use `{id, parent_id, kind, start, end}`. In the intentionally invalid-node case, the app must fall back to exact paragraphs; the core result and its finding spans are still valid.

Support and decision are separate. `supported` is a **simulated fixture support state**, not a claim that a production model is validated. `proposed_unvalidated` means the category lacks decision support. A selected proposed category is `unavailable` with reason `category_not_validated`. Proposed categories must not be silently added to the existing stub's supported IDs.

All fixture confidences are null; findings carry `origin: fixture`, `confidence_band: unvalidated` and `calibration_scope: unvalidated`. Preserve sample-only labels. The `proposal.algorithmic_price_change` identifier exists only for this test catalogue; it does not expand the production taxonomy.

## Navigation rules to implement in the app

1. Validate document identity and exact spans. Consider only accepted findings in requested categories. Review candidates keep their own entry point and uncertain styling.
2. Validate parser ranges and hierarchy. Select non-overlapping leaves once; do not also display nested parent ranges as separate inventory units. Add exact gap units for substantive source text outside leaves. Use exact paragraphs when structure is missing or invalid. Whitespace-only units need no card, but remain in the full reader.
3. Gate completed navigation on complete parsing and all requested searches, valid source identity, a completed job, no unfinished stage, no truncation and complete boundary coverage. An unavailable selected category fails this gate. A complete search can still contain uncertain review candidates; uncertainty and unfinished processing are separate.
4. For an eligible unit, use the union of accepted intervals across requested categories. No intersection gives `none`; some gives `partial`; the entire original interval gives `full`. Leading/trailing separators count. Overlaps do not double-count coverage; adjacent intervals can jointly cover a unit.
5. `none` includes the exact unit under `Text without accepted findings`. `partial` includes the entire unit with its existing highlights and `Partly highlighted` label. `full` remains in the full reader and is never labelled cleared or fully assessed.
6. If processing is incomplete, show `Processing incomplete`, retain manual reading of available text and identify unavailable regions. Inventory and count are **null**, not empty/zero. Missing page content has a locator and reason, not invented offsets into available text.

Unit IDs in `expected` identify this fixture's units. An application may use different internal IDs; its test adapter should map them to exact `[start, end)` ranges before comparing. Preserve the specified semantic labels and counts. Sort display units by source position; accepted/candidate ID order in the reference follows core result order. UI ordering can be normalized when asserting membership.

Always show the fixed notice at upload, results and in the report:

> This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment.

The manual-review explanation is:

> These passages have no accepted finding, or are only partly highlighted, for the selected categories. This does not establish whether they are harmless or harmful. Read them with the surrounding agreement.

Keep full text, headings, definitions, neighbouring clauses and schedules reachable. Use neutral styling. No overall safety score, automatic red risk label, complete-risk-coverage claim or inference that interactions have been assessed is permitted. The report includes selected scope/support, parsing/processing limitations and the manual-review count only when computed. Zero is not a safety verdict. Manual-review items follow the existing transient session/deletion policy; no new retention is introduced.

## Aryan's adapter and acceptance work

Use these cases through a test-only adapter. Load `document`, parser/job metadata and the fixed `core_result` into the application boundary. Map `mode=stub` to the existing API's sample mode. Do not enable fixture selection for arbitrary uploaded documents and do not route these cases through `StubAnalyzer.analyze()`; that analyzer correctly accepts only its original fixed sample and rejects partial parser inputs.

The reference checker has `load_families()`, `observe(case)` and `verify_case(case)`. It is a small development oracle under `ml/scripts/`, deliberately outside `clauseanchor_core`. The frozen `expected` snapshots are the handoff. Application tests must exercise Aryan's implementation against those expectations; calling this reference implementation as the application under test would not establish integration correctness.

For every case, app-side tests should verify:

- Exact highlights, source positions, eligible inventory units and counts, with no double-counted parents or missing substantive gaps.
- Distinct category/support/processing states, including null confidence and cancellation without an invented core result.
- Both distant anchors can be opened with surrounding context; filtered navigation still reaches the full source.
- Review candidates remain separate and do not count as accepted coverage.
- The fixed notice, selected catalogue/version/support and appropriate limitations appear in the browser and exported report, including the zero-item and incomplete cases.
- Sample mode refers only to the fixed sample; clearing a session clears its manual-review items using the existing no-retention flow.

Record observed browser/backend/report outcomes and unresolved failures by case ID. This pack validates data and reference mechanics on Linux; it does not execute the production backend, browser, PDF export, real PDF/DOCX parser or deletion flow. Real-model examples must still be audited before release, separately from the frozen CUAD and Indian evaluation sets. Never use this synthetic suite as measured model performance.

## How to change a fixture later

Review the source, spans and expected behaviour together. Do not regenerate expected snapshots automatically from an app implementation merely to make tests pass. Bump the fixture revision when changing meaning; recalculate source hashes and span positions after source edits, and update the byte manifest after any JSON edit. Existing `ml/.gitattributes` already pins JSON files to LF. Re-run the checker, original contract check and tests.

Keep fixture requirements recorded before Phase 3-D begins. Aryan should add 3-D and its dependency to the app phase plan. In `docs/ml/Phases.md`, the original Phase 1 row still needs to reflect the successful Windows installation while keeping application integration pending. This additive pack does not overwrite either teammate's tracking files.
