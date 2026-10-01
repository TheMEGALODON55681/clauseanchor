# Scope fixture build log

## 2026-10-01: development handoff prepared

- Goal: fulfil Plan 1.1 section 11.3 with exact text, source spans, category scope and expected mechanical states for the section 10.7 feature.
- Starting remote main: `52bb951`; includes ML starter `d9e4c6a` and app planning `e64cbc7`.
- Added eight scenario families with 16 cases, a versioned fixture identity and checksum manifest, reference checker, 17 regression tests and handoff documentation.
- Scope coverage: all eight required families, plus explicit variants for four incomplete causes, boundary failure, invalid parser-node fallback, whitespace boundaries, union across selected categories and proposed-category selection.
- Sources: original synthetic development text. No customer documents or frozen CUAD/Indian evaluation data used. Support states and findings are simulated; no measured confidences.
- Verification environment: Python 3.12.14 on Linux. No new dependency installation needed. Repository source was selected with `PYTHONPATH=ml` for isolated verification.
- Commands: `python ml/scripts/check_scope_fixtures.py`, `python ml/scripts/check_contract.py`, `python -m unittest discover -s ml/tests -v`.
- Observed: scope checker passed all 16 cases; original contract checker passed; all 43 tests passed, comprising 26 existing and 17 new tests.
- Regression checks include corrupted text/source identity, incorrect UTF-16 offsets, forged confidence, altered expectations, unsafe absence on partial parsing, candidate exclusion, selected-category scope, incomplete gates, hierarchy fallback, byte-manifest tampering and duplicate JSON keys.
- No existing repository file was modified. Core 2.0, the original sample analyzer and its tests remain unchanged. No commit or push was performed.
- Pending: run the bundle on Tanishq's Windows/VS Code environment; commit and push through VS Code; app-side backend/browser/report and actual parser integration; real-model audit before release.
- Unresolved failures: none in the executed fixture checks. App-side cases have not been executed, so their outcome is unverified.

## 2026-10-01: Windows verification

- Environment: Windows, VS Code, Conda environment `clauseanchor`.
- Scope checker: PASS for 8 families and 16 cases.
- Unit tests: all 43 tests reported ok; runtime 0.242 seconds.
- Failures observed: none in the scope checker or unit tests.
- Backend, browser and report integration: pending.
- Next action: commit and push the fixture pack for Aryan's Phase 3-D work.

## App integration entry: fill when Phase 3-D is exercised

Record application commit and environment; case IDs exercised; expected versus observed backend state, browser highlights/navigation and report output; session deletion result; failures; and the next corrective action. Keep any real-model audit separate from deterministic fixture outcomes.
