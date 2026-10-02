# Backend Architecture

The backend takes an uploaded contract, turns it into one canonical text with exact character offsets, runs the analysis core on that text, applies the user's side of the deal, and serves results to the frontend. It never generates legal text.

This file describes the target design. Sections marked **(planned)** do not exist yet. Update this file whenever the code changes shape.

---

## 1. Request flow

```mermaid
flowchart TD
    U[Browser: upload + role] --> S[Session check]
    S --> V[Upload validation: type, size, zip safety]
    V --> P[Parser: canonical text + offsets + structure]
    P --> M[(RAM store: text, nodes, results)]
    P --> A[Analysis job: core Analyzer]
    A --> K[Party binding + polarity]
    K --> M
    M --> R[Results API]
    M --> F[PDF report]
    D[(SQLite: metadata only)] --- S
    D --- A
```

1. The browser creates an anonymous session and gets a bearer token (Phase 2).
2. It uploads one PDF or DOCX with the user's role and review scope.
3. The upload is validated by magic bytes, size and archive safety, then parsed in a child process that a wall-clock timer can kill (planned, Phase 2).
4. The parser returns a `ParsedDocument`: canonical `source_text`, its SHA-256, text blocks with source locators, a structure tree and warnings. The uploaded bytes are dropped.
5. The analysis job passes `source_text` and an `AnalysisContext` to the core `Analyzer` from `ml/clauseanchor_core` and gets back category decisions with spans.
6. The backend applies polarity from the user's role and party binding. The core never sees the user's side.
7. Everything text-bearing lives in RAM with a 60-minute TTL. SQLite holds only metadata (ids, statuses, counts, offsets).
8. Every capabilities response, analysis response and report carries the fixed scope notice (Phases.md, "Review scope"). After a complete analysis, the manual-review endpoint (planned, Phase 3) labels each display unit by its overlap with accepted findings, so text without findings is easy to reach.

## 2. Key decisions

| Decision | Choice | Reason |
|---|---|---|
| PDF library | **pdfplumber** (MIT) | PyMuPDF is AGPL, which conflicts with the repo's MIT licence and the hosted demo |
| Offset unit | Unicode code points, `end` exclusive | Matches Python slicing; the frontend converts to UTF-16 |
| Canonical text | Built once, never changed after offsets are assigned | Every highlight, report line and rule flag points into the same string |
| Text normalisation | No Unicode normalisation, dehyphenation or ligature expansion. Three extractor effects remain: PDF runs of spaces collapse to one space, PDF U+00A0 arrives as U+0020, and DOCX `w:noBreakHyphen` becomes ASCII `-` | Keeps `source_text` faithful to the file. Model-side normalisation belongs to the core, which maps its own offsets back. ParserContract.md lists the three effects |
| DOCX auto-numbering | Rendered as `StructureNode.label`, **not** inserted into `source_text` | `source_text` stays literal file text; the UI shows labels from nodes |
| Headers, footers, page numbers | Kept in `source_text`, marked as decoration ranges | Deleting them would shift offsets and hide content |
| Scanned or partly scanned PDFs | Count characters outside the margin zones. An image-dominant page with fewer than 20 is scanned. When every page with content is scanned, the file is rejected with `SCANNED_PDF`. When only some pages are scanned, the file parses with `coverage.partial = True` and a `PARTIALLY_SCANNED_PDF` warning. An image-dominant page with fewer than 200 also sets `coverage.partial = True`. Widget and FreeText annotations with content set `partial` too | Executed contracts often end in a scanned signature page, so rejecting them would turn away usable files. Margin text such as a Bates stamp does not make a scan readable. A searchable scan (full-page image, large real text layer) must stay usable. `partial` tells the core never to report "not found" for this file |
| PDF content budget | Page content streams and Form XObjects decode incrementally. Decoding aborts at 8 MiB (`MAX_DECODED_CONTENT_BYTES`) with `TOO_MUCH_TEXT` | A 16 KB file can decode to 16 MB and take minutes to extract, so the check must run while decoding. Only Flate streams are measured; the child-process kill (Worker model) covers the rest |
| DOCX tracked changes | `ins`, `del`, `moveFrom` and `moveTo` in any text part under `word/` are rejected with `TRACKED_CHANGES_PRESENT` | The parser cannot tell which version is the contract. The user accepts all changes and uploads again |
| DOCX text boxes | Every `w:txbxContent` outside `mc:Fallback` is extracted as text blocks right after its anchor paragraph. `TEXT_BOX_CONTENT` is an informational warning and `partial` stays False | Contract text can sit in a text box. Reading the Fallback copy as well would duplicate it |
| DOCX embedded objects | `EMBEDDED_OBJECT` warning and `coverage.partial = True` | The object's content is not extracted, so the core must not report "not found" for this file |
| DOCX unknown block content | The body walk recurses through `sdt`, `smartTag`, `fldSimple`, `customXml` and `hyperlink`. An unknown block-level child, including `altChunk`, is skipped with an `UNSUPPORTED_DOCX_FEATURE` warning and `coverage.partial = True` | Text inside a wrapper must not vanish. A raised error would leave no result to mark partial, so an unknown block is a warning |
| Database | SQLite only, `create_all()` | Nothing durable is stored; no migrations tool needed |
| Worker model | One API process, one bounded analysis worker, one executor thread. Each parse job runs in a child process with a wall-clock kill (planned, part 2-C) | Fits a laptop and a free host; no Redis or Celery. The kill stops a parse that the content budget cannot bound |
| User content storage | RAM only, 60-minute absolute TTL | Matches the synopsis promise; nothing on disk |
| Review scope | Fixed category catalogue, a fixed scope notice on every result, no safety score or overall verdict anywhere | The system checks listed categories only. A highlight-free passage is not a safe passage, and the output must never imply it is |
| Completeness | Processing completion, decision coverage and highlight extent are separate fields | Each answers a different question; merging them would read as "share of risk found", which nothing measures |
| Manual-review navigation | Derived in the backend from parser blocks and accepted spans; no new core field | Parser blocks are already exact, non-overlapping units, so the core interface (v2.0) stays unchanged |

## 3. Folder structure

```text
backend/
  pyproject.toml            # package metadata, ruff and pytest config
  requirements.txt          # pinned runtime dependencies
  requirements-dev.txt      # pinned test and lint dependencies
  .env.example              # config names only, no secrets
  .gitignore                # .venv, caches, local db, graphify-out
  app/
    __init__.py
    parsing/                # Phase 1
      __init__.py           # public: parse_document, ParsedDocument, ParseError
      model.py              # dataclasses: ParsedDocument, Block, StructureNode, ParseWarning, Coverage
      assemble.py           # TextAssembler: builds source_text and assigns offsets while appending
      errors.py             # ParseError, the fixed error/warning code lists and the limits
      detect.py             # file type detection by magic bytes
      pdf.py                # pdfplumber extraction: words to lines to blocks, columns, decoration, scanned checks, content budget
      docx.py               # python-docx extraction: body order, tables, text boxes, headers, footers, footnotes, numbering, tracked-change check
      structure.py          # numbering stack, headings, schedules, definitions
      schema.py             # exports ParserContract JSON Schema
    scripts/
      parse_file.py         # CLI: parse a local file and print JSON (dev only)
    main.py                 # (planned, Phase 2) FastAPI app
    config.py               # (planned, Phase 2)
    db.py, models.py        # (planned, Phase 2) SQLite metadata
    schemas.py              # (planned, Phase 2) Pydantic DTOs
    api/routes.py           # (planned, Phase 2)
    services/               # (planned, Phase 2 and 3)
      memory_store.py       # RAM-only content with TTL
      sessions.py           # capability tokens
      jobs.py               # bounded queue, progress, cancel
      documents.py          # upload validation, parse jobs (child process, wall-clock kill)
      analysis.py           # core adapter and result validation
      polarity.py           # (Phase 3) party binding and polarity
      report.py             # (Phase 3) ReportLab report
      review_units.py       # (Phase 3) manual-review display units and overlap labels
      scope.py              # (Phase 2) scope notice constant and category catalogue with support status
    policies/polarity.yaml  # (planned, Phase 3) 46 category policies
  tools/
    annotator/              # (planned, 2-0B) offline annotation tool: runs locally, no network
  tests/
    conftest.py             # session-scoped fixture generation into a temp dir
    fixtures/build.py       # generates PDF and DOCX fixtures with reportlab and python-docx
    test_assemble.py
    test_pdf.py
    test_docx.py
    test_structure.py
    test_invariants.py      # offset invariant over every fixture
```

Fixtures are generated at test time, so no binary files are committed.

## 4. Parser output (summary; the full contract lives in ParserContract.md)

```python
@dataclass(frozen=True, slots=True)
class ParsedDocument:
    source_text: str
    text_sha256: str             # sha256 of source_text.encode("utf-8"), lowercase hex
    parser_version: str          # "1.0.0"
    media_type: str              # "application/pdf" or the DOCX mime type
    page_count: int | None       # None for DOCX
    blocks: tuple[Block, ...]    # every text block, in reading order
    nodes: tuple[StructureNode, ...]
    decorations: tuple[tuple[int, int], ...]   # repeated headers, footers, page numbers
    warnings: tuple[ParseWarning, ...]
    coverage: Coverage
```

Separators: lines inside a block join with `"\n"`, blocks join with `"\n"`, pages join with `"\n\n"`. Trailing spaces and tabs are stripped from each line before it is appended. CRLF and CR become LF. In PDF text, runs of spaces collapse to one space and U+00A0 becomes U+0020. DOCX text keeps U+00A0.

## 5. Interface to the core (planned, Phase 2)

The backend imports only public names from `clauseanchor_core`: `CONTRACT_VERSION`, the result dataclasses, `Analyzer` and `StubAnalyzer`. It never imports training, extraction or retrieval internals. Contract version **2.0** (multi-span findings) must be present before the analysis part of Phase 2 starts. The switch is `CLAUSEANCHOR_ANALYZER=stub|real`; a real run with missing artifacts fails readiness instead of falling back to the stub.

## 6. Tech stack

Python 3.12, pdfplumber, python-docx, FastAPI, Pydantic v2, SQLAlchemy 2 on SQLite, ReportLab, PyYAML, pytest, httpx, ruff.
