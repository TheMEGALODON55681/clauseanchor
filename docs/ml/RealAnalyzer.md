# Candidate-only real analyzer v0

Prepared 2026-10-28, Tanishq Arya. Batch target: **October 30, Asia/Calcutta**.
Base repository: `f4b6500ff78f2bef7022cd837870ad04b64adc94`, with no newer remote
main at initial inspection. Tanishq completed the local export and real CPU
smoke on October 28; the supplied output/JSON review passed below. Parser-to-core
app integration remains pending.

## Batch exit condition

Completed on October 28: focused Windows tests, local checkpoint export and
real CPU smoke; supplied outputs reviewed. The artifact hashes below come from
Tanishq's exporter receipt. The assistant verified the supplied report's source,
contract and bindings, but did not independently read the local weight file.
Software tests use tiny random weights/test logits, explicitly separate from
the real smoke. No training, dev_select diagnostics, source audit, calibration,
test evaluation or decoder experiment was rerun by this batch.

Assistant-side verification on October 28: all **442 ML software tests passed**
in 9.689 seconds, with no skips, using Python 3.12.14 and pinned dependencies
(CPU Torch 2.9.1). This includes 32 new adapter/export/parity tests. The actual
selected training weights were unavailable here; no trained-weight smoke or
model-quality evaluation is claimed from those tests.

## Reviewed local evidence — October 28

Tanishq's focused Windows run: **32 tests passed in 11.751 seconds**. Exporter
reported verified checkpoint hashes and a successful inference-only export.
The real CPU smoke completed **9/9 windows**, emitted **5 review candidates**,
and checked cancellation. Load: **24.35 seconds**; inference: **3.97 seconds**.
These are one-run timings on this smoke input, not a general runtime benchmark.

Runtime: Python 3.12.14; NumPy 2.3.5; Torch 2.9.1+cu126; Transformers 4.57.6;
tokenizers 0.22.2; safetensors 0.7.0. Device was explicitly CPU, batch size 1;
the installed CUDA-capable Torch build does not mean this run used the GPU.

| Identity | Actual SHA-256 |
|---|---|
| Manifest, canonical JSON (loader argument) | `ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8` |
| Manifest file bytes | `753c533ed622eba6a9278a79c9ad55082621ed9e51bda9926441e3f3f4ffc88e` |
| Exported QA weight file bytes | `cd508f9eb20d43047dcfbefe37be0c32ff17f14712ce09aa9f263fbb8320ab36` |
| Exact smoke source UTF-8 | `85c90f397ae46ed7eb1f6408a42ac009ba3b0c6ad17373a23e57e099f653ceff` |
| Supplied export receipt bytes | `7f0245ee1817616c5143f438a6193352c3870157e973ef571defc3b0c5cbf5dd` |
| Supplied smoke report bytes | `b8cd21f029a4c29e8d85ca3ab27145aa8348bf79d5941aa919b473fe3b448d4d` |

The receipt, report and nested result agree on the canonical artifact identity.
The report's source equals the authored smoke input exactly, including CRLF,
Unicode and repeated text. The existing contract validator passed independently
on the uploaded result. All five source slices and deterministic finding IDs
were checked; all confidences and decision confidences are null. Every finding
is a model-origin review candidate with unvalidated band/scope, empty rule flags
and passages, and retrieval not run.

| Requested category | State | Windows | Candidates | Search complete |
|---|---|---|---|---|
| Document Name | abstained | 3/3 | 1 | true |
| Governing Law | abstained | 3/3 | 3 | true |
| Cap on Liability | abstained | 3/3 | 1 | false |
| India Arbitration | unavailable | 0/0 | 0 | false |

Cap-on-liability is incomplete because the original question was truncated to
its first 64 tokens, as the frozen generation policy specifies. Its warning and
`processing_incomplete_unvalidated` reason are correct even though all windows
ran. India arbitration remains `unsupported_india_extension`. The overall
request must therefore not be presented as fully processed; completed neutral
manual-review inventory/count remain null under the existing app gate.

The five candidates are not five established correct clauses. In particular,
governing-law output `[4058,4059)` is only a period, and `[162,410)` includes the
law sentence plus two service-report sentences. The separate law occurrence at
`[4273,4343)` is preserved at its own offsets. These are visible quality/boundary
limitations, not an offset or serialization failure. No accuracy percentage or
new filtering rule is inferred from this smoke. The candidate-only adapter
batch is accepted; decoder freeze, calibration, policy, final evaluation and
actual parser/app integration remain on their fixed dates.

No test rerun or model re-export is required for this evidence-only Markdown
update. Keep generated reports/weights outside Git and retain the original
files unchanged. Do not run the completed smoke again just to update this log.

## Install and run on Tanishq's Windows machine

Place the supplied files at their identical paths under:
`C:\Users\Asus\OneDrive\Desktop\ClauseANchor\clauseanchor`.
The files change only `ml/` and `docs/ml/`. The restored `Phases.md` receives a
dated scope update, not another repair. Frozen training/diagnostic producers,
catalogue, question mapping, schema and teammate files are unchanged.

From VS Code's terminal at that repository root:

```powershell
conda activate clauseanchor
python -m unittest discover -s ml/tests -p "test_candidate_analyzer.py"
python ml/scripts/export_candidate_analyzer.py
python ml/scripts/smoke_candidate_analyzer.py --device cpu
```

Run each command only after the preceding one succeeds. The existing editable
core install and pinned environment suffice; no package upgrade is requested.
The focused tests require the already prepared local tokenizer assets. The
export can take time to hash the original checkpoint; CPU load/export may need
several GB of RAM, and about 500 MB of additional disk for inference weights.
It does not instantiate or initialize the pristine backbone as the final model.

Share the terminal output and these small JSON files for review:

- `data/processed/cuad/candidate_adapter_v0/export_receipt.json`
- `data/processed/cuad/candidate_adapter_v0/smoke-cpu.json`

Do not upload the weights or stage generated artifacts. If a command fails,
preserve its output and stop this batch. A missing local checkpoint is a file
availability issue, never an instruction to retrain. If smoke returns zero
candidates, it records `incomplete_no_candidate_slices`: inference ran but the
source-slice check was not exercised. That is neither absence nor a quality
result. Existing smoke reports are preserved; a justified repeat needs a new
`--report data/processed/cuad/candidate_adapter_v0/smoke-cpu-r2.json` path.

## Artifact identity and transfer

The exporter reads `data/processed/cuad/clean_training_v1`, verifies the complete
latest-to-selected checkpoint chain and every recorded file hash, and requires
`checkpoint-000022`. It checks the saved decoder-validation identity against the
previously verified canonical SHA-256
`f47f3b426894fca493d8e963148b024630c05167bf5a5dde7ecfb1114d1a16e7` and requires
the identical checkpoint binding. This is metadata verification, not another
experiment or report replay. It also verifies the pinned tokenizer/config,
category prompts, original producer files and the AMP execution binding.

`torch.load(..., weights_only=True)` reads the verified original checkpoint.
Strict state-dict loading and finite-weight checks precede an inference-only
safetensors export. Optimizer, scaler, RNG and training progress remain in the
original directory and are not part of the runtime weight file.

Output directory: **`models/clauseanchor_candidate_v0/`** (ignored by Git).
It contains:

| File | Purpose |
|---|---|
| `model.safetensors`, `config.json` | Selected QA weights and exact model configuration |
| `tokenizer/` | Five verified source files, including tokenizer model-type metadata |
| `catalogue.json`, `category_questions.json` | Exact stable category IDs, original questions and unchanged validation labels |
| `decoder.json` | Existing generation, disjoint selection, score definition and parser transport settings |
| `requirements-inference.txt`, `training_source.json` | Runtime requirements and pinned source identity |
| `provenance.json` | Original checkpoint hashes/bindings, producer identities, export runtime and source revision |
| `manifest.json` | Byte SHA-256/size for all payloads, LF-normalized core code hashes, required versions |

The receipt distinguishes **canonical JSON manifest SHA-256** from the manifest
file's byte SHA-256. `expected_manifest_sha256` takes the canonical value only.
The loader checks that independently supplied value, every file, the inventory,
runtime versions, category binding and installed core code before loading any
weights. Unexpected files, tokenizer overrides, altered code or changed policies
fail. It operates offline and never downloads substitute weights. Hashes verify
identity/integrity, not quality, provenance ownership or legal reliability.

The local export and smoke output have been reviewed. Tanishq can now provide
Aryan the entire artifact directory by
their chosen file-transfer method and the separately recorded canonical digest.
There is no hosted download URL yet; this batch does not upload weights or send
Aryan a message. Aryan also needs the matching `ml/clauseanchor_core/` package.
An unchanged export rerun verifies the saved receipt; it never overwrites a
different bundle. Interrupted publication without a receipt fails explicitly;
preserve/move the incomplete bundle before re-exporting from the original source.

## Loading for Aryan

Use Python 3.12. On a fresh CPU environment, install the CPU Torch build first,
then the matching inference dependencies and core. Keep Tanishq's existing CUDA
installation unchanged. Commands for that **fresh CPU environment only**:

```powershell
python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r ml/requirements-inference.txt
python -m pip install -e ml
```

```python
from clauseanchor_core import (
    CandidateOnlyAnalyzer, AnalysisContext, context_from_parsed_document,
    text_digest, to_dict,
)

analyzer = CandidateOnlyAnalyzer(
    "models/clauseanchor_candidate_v0",
    expected_manifest_sha256="ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8",
    device="cpu", batch_size=1,
)

# parsed is the existing ParsedDocument; never clean/reflow source_text here.
result = analyzer.analyze(
    parsed.source_text,
    doc_id=document_id,
    text_sha256=parsed.text_sha256,
    category_ids=("cuad.governing_law", "cuad.cap_on_liability", "in.arbitration"),
    context=context_from_parsed_document(parsed, jurisdiction_scope="india_review"),
    progress=on_progress,
    cancelled=is_cancelled,
)
core_payload = to_dict(result)
```

For raw text without a parser, pass the exact source and `text_digest(source)`
with `AnalysisContext()`. The backend still owns its HTTP adapter, party polarity,
job state, missing-page metadata, full reader and neutral manual-review display.
Loading this class does not install an app endpoint or bypass capability gates.
`inference_category_ids` lists 41 experimental question capabilities;
`category_ids` lists all 46 known IDs. **All catalogue rows stay not_validated.**
Aryan must expose a clearly experimental candidate-only route, rather than mark
the catalogue validated to enable real mode. This app integration is still pending.

## Output and processing semantics

- `mode=real`. Every model finding is `review_candidate`, `origin=model`,
  `confidence=null`, `confidence_band=unvalidated`,
  `calibration_scope=unvalidated`. No raw margin is exposed as probability.
- Processed categories are `abstained`, `decision_confidence=null`, with a
  reason and exact `unresolved_count`. Zero candidates still means abstention.
  This class cannot emit accepted findings, `found`, `absent` or `unassessable`.
- India extensions are `unavailable / unsupported_india_extension`, with no
  windows and `search_complete=false`. Unknown IDs are rejected. Empty or
  decoration-only text is `unavailable / no_analyzable_text`.
- Rule flags and judgment passages remain empty; `retrieval_status=not_run`.
  Rules/retrieval and India validation remain deferred.
- All spans use end-exclusive Python Unicode code-point offsets and the original
  source digest. `source[start:end] == span.text` is checked by the existing
  validator. CRLF, Unicode and repeated occurrences are preserved. The browser
  must convert code-point offsets to UTF-16; do not search for matching wording.
- `windows_total` is the full planned window count, never the permitted prefix.
  Default work has no document/window/output cap beyond the frozen generator.
  An explicit `max_windows_per_category=N` constructor limit retains candidates
  already generated and makes unfinished work incomplete; zero work is unavailable.
- Parser partial coverage, truncated question text, selected boundary-review
  candidates and omitted decoration-crossing candidates set `search_complete=false`
  with warnings. Otherwise completeness means the declared window procedure ran,
  not that all legally relevant clauses were discovered. Top-20 start/end and
  per-window pruning, 256-token spans and greedy selection remain limitations.
- Parser warning codes are retained. Informational warnings alone do not imply
  omitted text; `coverage.partial` drives parser completeness.
- Progress events count completed inference windows over all requested supported
  questions. Unsupported/empty searches have zero windows. Cancellation is checked
  before tokenization, between batches/categories and before return. It raises
  `AnalysisCancelled`; it cannot interrupt an in-flight model operation or return
  a partial snapshot through the unchanged protocol. A model/loading failure is
  an exception, never a successful empty result. Backend jobs must retain an
  incomplete/error/cancelled state and full source access, not report absence.
- Serialize jobs per analyzer instance. Concurrent calls fail with a busy error;
  cancellation does not wait behind an in-process lock. The app owns scheduling.

## Parser decoration transport without changing contract 2.0

`context_from_parsed_document()` copies ordinary parser nodes and appends one core
`StructureNode(kind="decoration", parent_id=None, start=..., end=...)` for each
`parsed.decorations` range. It also maps warning codes and `coverage.partial`.
This uses the existing unconstrained `kind: str` field; no dataclass/schema field
is added. The app must use this bridge or implement that exact convention.
Omitting decoration metadata cannot be detected reliably by the core.

For model input only, non-whitespace characters inside these explicit ranges
become one space per source code point; whitespace/line breaks stay intact.
Canonical source text and hash are never modified. Candidates intersecting a
decoration range are omitted, not silently split, concatenated or relocated;
omissions are reported as incomplete boundary coverage. Plain source text without
decorations follows the existing tokenizer/decoder exactly. Footnotes and
schedules are not decoration. This transport choice is an integration safeguard,
not the optional decoder-quality experiment, and has no measured quality claim.

## Decoder and release boundary

Runtime copies of `FeatureTokenizer`, `window_count`, `window_candidates` and
`exact_candidates` preserve the frozen producer logic; AST and behavioral parity
tests compare them with those unchanged files. Disjoint selection retains the
existing exact deduplication/tie order, strict margin >0 and suppression of any
positive overlap, with touching intervals allowed. No original top-50 cap and
no new threshold or decoder variant is introduced.

CPU uses FP32/SDPA; CUDA explicitly uses FP16 autocast/SDPA, as in development
validation. Numerical equality across devices/batch sizes is not claimed. The
smoke source is fixed; the report records device, batch size, exact runtime,
source hash and artifact hash. Runtime is descriptive on that host, not a latency
guarantee. The selected-weight CUDA smoke is optional after the CPU output review.

The one-experiment gate and fixed October 29–November 7 execution window remain
in [Phases.md](Phases.md). Freeze by October 31; calibration assessment November 2;
policy November 4; final evaluation November 5; integration checks November 6;
release November 7. If quality fails, preserve this honestly labelled research
prototype. Neutral manual review in [ScopeFixtures.md](ScopeFixtures.md) stays:
review candidates never contribute accepted coverage; incomplete inventory/count
are null; zero highlights does not establish absence, harmlessness or importance.
