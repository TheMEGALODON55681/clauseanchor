# Core interface, version 2.0

This document defines the Phase 1 Python core boundary. It is not the complete HTTP API. The app owns document parsing, jobs, sessions, party binding, polarity and reports.

## Call

```python
from pathlib import Path
from clauseanchor_core import AnalysisContext, StubAnalyzer, text_digest, to_dict

analyzer = StubAnalyzer(Path("ml/fixtures"))
source_text = analyzer.source_text
result = analyzer.analyze(
    source_text,
    doc_id="integration-example",
    text_sha256=text_digest(source_text),
    category_ids=analyzer.category_ids,
    context=AnalysisContext(),
)
payload = to_dict(result)
```

The call also accepts `progress(event)` and `cancelled() -> bool`. Cancellation is checked between categories in the stub and will be checked between batches in real inference. `AnalysisCancelled` signals a stopped call.

`AnalyzerProtocol` defines this signature for the later real analyzer. Constructor options for real model artifacts will be added separately, without changing the call signature unless a reviewed contract revision is necessary.

## Shapes and invariants

`ml/fixtures/contract.schema.json` describes the serialized core result shape. `contract.py` defines the dataclasses. `from_dict()` rejects missing or extra fields and incorrect JSON types. `validate_result(result, source_text)` checks offsets and important cross-field invariants. Use both when accepting serialized results. JSON Schema alone cannot prove that a span is an exact source slice.

The core result has `contract_version`, `doc_id`, `text_sha256`, `artifact_manifest_sha256`, `mode`, `categories`, and `warnings`. Every field is serialized, including nulls and empty arrays. Each category contains an array of clauses; several clauses may share a category.

| Status | Meaning |
|---|---|
| found | At least one accepted occurrence; other occurrences may remain unresolved. |
| absent | Complete eligible search plus a validated absence decision in real mode. |
| abstained | No supported final decision; provide a reason. |
| unavailable | Required processing or capability did not run; provide a reason. |

Each span is `{doc_id, text_sha256, start, end, text}`. The invariant is `source_text[start:end] == text`. Offsets count Python Unicode code points and `end` is exclusive. `text_sha256` hashes the exact source string encoded as UTF-8. Repeated wording is identified by its supplied offsets, never by `find()`.

Confidence is either a measured probability or null. Null means not validated, not zero. The fixture's accepted and absent states are illustrative exceptions allowed only in stub mode. Real accepted findings require a confidence value and a validated calibration scope. Real absence requires complete search and a calibrated category decision. Policy support, provenance against artifact manifests, and retrieval corpus verification are additional Phase 6-8 responsibilities, not proven by this Phase 1 validator.

`rule_flags`, `passages` and `retrieval_status` reserve the later integration fields. Passage lengths and basic metadata are checked here. Exact comparison with the canonical judgment text will occur in the retrieval layer.

## App adapter

The backend wraps this result in its HTTP `Analysis` object: it adds analysis ID, job status, timestamps, jurisdiction and party binding; it maps core `doc_id` to the document ID and core `mode=stub` to API `mode=sample`. Do not copy the core object directly into the HTTP response without this adapter.

The backend adds `polarity` and `actor_evidence` to its clause DTO. The ML core does not decide which party is helped or harmed. `StructureNode` is a minimal core input; the parser's full nodes also contain page and source-locator metadata.

JavaScript indexes strings using UTF-16 units. Before highlighting, map code-point offsets to UTF-16 positions or validate with `Array.from(sourceText).slice(start, end).join('')`. The fixture includes an emoji before the spans to expose this mismatch.

The stub supports four fixture category IDs only, not the full 46-category catalogue. It rejects arbitrary uploaded text, mismatched hashes, unknown categories, partial parsing and warnings. The real analyzer must represent partial work explicitly rather than adopt the stub's limited fixture-only behavior.

The fixture artifact hash identifies the fixed sample revision; it is not a trained-model manifest. Production manifests will hash the exact versioned model, tokenizer, policy, rules and corpus references.

## Integration acceptance

Run the contract checker and unit tests. Then Aryan should verify both sample spans highlight exactly, all four states display distinctly, null confidence displays as unvalidated, and arbitrary uploads are disabled in sample mode. Agree the field names and adapter before training work changes the package.
