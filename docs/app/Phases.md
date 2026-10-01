# Backend Phases

Aryan's track: `backend/` only. One phase at a time. Every part is committed and pushed on its own, using the suggested message (adjust wording if you like).

Legend: `[ ]` not started, `[~]` in progress, `[x]` done and committed.

---

## Review scope (plan v1.1, applies to Phases 2 to 4)

Adopted on 1 October 2026 from the team plan, revision 1.1 (sections 2.5, 10.7 and 11.3). ClauseAnchor reviews a fixed list of clause categories. It does not detect every risk in a contract, and nothing the backend returns may suggest that it does.

- **Fixed scope notice.** The capabilities response, every analysis response and the PDF report carry this exact text: "This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment." It is a constant in one place, not generated.
- **Banned outputs.** No overall safety verdict, risk score, safety percentage or "risk completeness" figure in any field, endpoint or report. An `absent` decision for one category is never rolled up into a statement about the whole contract.
- **Three separate measures, never merged:** processing completion (which inputs and windows were processed), decision coverage (how many requested category decisions resolved) and highlight extent (which source ranges have accepted findings). None of them is "how much of the risk was found".
- **Catalogue.** 41 CUAD categories plus 5 India extensions, with a catalogue version. Being listed in the catalogue is separate from validated support; each category reports its support status.
- **Full text always available.** Text without an accepted finding stays readable through the API. The backend never filters it out.
- **Ownership.** Tanishq supplies the scope fixtures (plan section 11.3: exact text, spans, category scope and expected states) and keeps the category backlog (`docs/ml/CategoryBacklog.md`). The app track renders and tests them.


## Phase 0: Docs

- [ ] **0-A** Add backend rules, architecture and phase plan
  `docs(app): add backend rules, architecture and phase plan`

## Phase 1: Parser

Goal: turn a PDF or DOCX into one canonical text with exact offsets, a clause structure tree and honest warnings. No API yet. Depends on nothing from the ML track.

- [ ] **1-A** Package scaffold and the parsed-document model
  `chore(backend): set up package, tooling and parsed document model`
- [ ] **1-B** PDF text extraction in reading order
  `feat(parser): extract ordered text blocks from PDFs`
- [ ] **1-C** PDF safety: decoration, scanned, encrypted, malformed, limits
  `feat(parser): mark repeated page furniture and reject unreadable PDFs`
- [ ] **1-D** DOCX archive safety, body, tables and text boxes
  `feat(parser): extract DOCX body, tables and text boxes safely`
- [ ] **1-D2** DOCX numbering, headers, footers and footnotes
  `feat(parser): render DOCX numbering and extract page parts`
- [ ] **1-E** Clause structure tree and definitions
  `feat(parser): build clause structure tree and detect definitions`
- [ ] **1-F** Public entry point, CLI and parser contract
  `feat(parser): add parse entry point, CLI and parser contract`
- [ ] **1-R** Phase review: `/gstack-cso`, `/coderabbit:review`, `/gstack-review`; fixes as separate commits

**Sync with Tanishq:** send the `[CONTRACT]` items below before 1-B and apply his changes before 1-F. After 1-F, share `docs/app/ParserContract.md` and agree separators, offsets and warnings.

### Spec amendments (Phase 1)

Agreed in the spec review before 1-A. Each item amends the Phase 1 handoff where the two disagree; the handoff file stays unchanged. `[CONTRACT]` marks a change to parser output: fields, separators, offsets, codes, locators or the meaning of a warning. Those items go to Tanishq.

1-D is now two parts, **1-D** and **1-D2**. 1-E and 1-F keep their ids.

#### Every part

- **A1 Errors.** Each parser catches one closed tuple of library exceptions. PDF: the pdfplumber and pdfminer error types, plus TypeError, ValueError, AttributeError, AssertionError, KeyError and IndexError. DOCX: BadZipFile, lxml and python-docx package errors, the encrypted-member RuntimeError and NotImplementedError. Every hit maps to MALFORMED_FILE, except a wrapped PDFPasswordIncorrect, which maps to ENCRYPTED_PDF. Always `raise ParseError(code) from None`, and silence the `pdfminer` logger, because it logs raw document bytes. One test runs a seeded byte-flip sweep over a small PDF with a log handler attached. Each mutant must give a valid parse or a ParseError, never another exception type, and no exception text or log record may contain document text.
- **A2 pytest.** Set `pythonpath = ["."]` in pyproject. Without it `import app` fails under plain `pytest`.
- **A3 Attribution scrub.** Run `grep -rniE "<pattern>" backend/ docs/app/ --exclude-dir=.venv --exclude-dir=graphify-out --exclude=Rules.md`. The command as written always matches `Rules.md` and scans `.venv`. Add `graphify-out/` to `backend/.gitignore`.
- **A4 Fixture registry.** `tests/fixtures/build.py` exposes `build_all(dir)`, which returns `{name: (path, expected error code or None)}`. `test_invariants.py` and the 1-F tests read it, so invalid fixtures are expected to raise instead of being skipped. Reportlab fixtures use `invariant=1`. Tests for `detect.py` live in `test_pdf.py`.

#### 1-A

- **A5 Assembler.** Remove `mark_decoration`. `build()` derives `decorations` from the header and footer blocks and sets `coverage.pages_total` from `page_count`. `add_block` refuses a block with no text (callers skip empty paragraphs and cells) and enforces the 500,000 code point limit as it appends. `build()` only computes the hash and raises NO_TEXT_FOUND, and it maps the UnicodeEncodeError from a lone surrogate to MALFORMED_FILE. Extra tests: bare CR, `new_page` twice, exactly 500,000 and 500,001 code points, whitespace-only text.

#### 1-B

- **A6 Text fidelity [CONTRACT].** Call `extract_words(expand_ligatures=False)`; the default rewrites U+FB01 to `fi`. Runs of spaces collapse to one and NBSP arrives as U+0020 in PDFs, and the contract says so. `latin_unicode.pdf` embeds the Vera font that ships with reportlab and asserts that U+FB01 survives. Only DOCX asserts NBSP.
- **A7 Block splitting.** Compare the pitch (top to top) with the median pitch and split above 1.3 times, held in one named constant. A line that starts with a numbering token also starts a new block, matched by a coarse regex local to `pdf.py`. The left-edge rule applies only to a return to a column's left edge, never to an indent. New fixture: `tight_clauses.pdf` (hanging indents, 6 pt paragraph spacing).
- **A8 Columns.** Assign words to columns first, then group lines. A full-width line crosses the gutter. New fixtures: a 3-column table page (covers MORE_THAN_TWO_COLUMNS and shows that a table page keeps top-to-bottom order) and a page for COLUMN_ORDER_UNCERTAIN.

#### 1-C

- **A9 Decoration [CONTRACT].** Classify margin-zone lines before building blocks and give each candidate its own block. A page-number-shaped line in the margin zone counts as decoration at any page count. Other lines keep the repetition rule. Fixtures: 1-page and 2-page documents, a header on 2 of 3 pages (not decoration), a body line inside the zone.
- **A10 Scanned and partial [CONTRACT].** Count characters outside the margin zones. An image-dominant page with fewer than 20 of them is scanned. One with fewer than 200 sets `coverage.partial = True`, because a searchable scan (full-page image, large real text layer) must stay usable. Widget and FreeText annotations with content also set `partial = True`. Fixtures: a scanned page with a Bates stamp, an all-blank PDF (NO_TEXT_FOUND) and an owner-only encrypted PDF (parses).
- **A11 Content budget [CONTRACT].** Before extracting a page, decode its content streams and any Form XObjects incrementally, with Flate read through `zlib.decompressobj` in `max_length` chunks. Stop as soon as the running total passes `MAX_DECODED_CONTENT_BYTES` (8 MiB, kept with the other limits in `errors.py`) and raise TOO_MUCH_TEXT. Never decode a stream fully and measure afterwards. Count pages with `islice(PDFPage.create_pages(doc), 101)` instead of building every Page object. Fixtures: two 16 KB PDFs that decode past the budget, one in the page content and one in a Form XObject. Known ceiling: only Flate is measured. A 16 KB PDF that decodes to 16 MB took 186 s in `extract_words`, so Phase 2 must also add a child-process wall-clock kill.

#### 1-D

- **A12 Archive.** Convert backslashes to slashes, then reject any member with an absolute path, a drive letter or a `..` segment (ARCHIVE_UNSAFE). Reject a total uncompressed size over 100 MiB (ARCHIVE_TOO_LARGE). One `build_zip(member_name)` fixture builder covers slash, backslash and drive-letter names. Other fixtures: a 101 MiB sparse archive and a corrupt zip (MALFORMED_FILE).
- **A13 Tracked changes [CONTRACT].** Match `ins`, `del`, `moveFrom` and `moveTo` by namespace URI in every text part under `word/`: document, headers, footers, footnotes and endnotes.
- **A14 No silent loss [CONTRACT].** The body walk recurses through `sdt` and `sdtContent`, `smartTag`, `fldSimple`, `customXml` and `hyperlink`. An `altChunk` or any unknown block-level child raises UNSUPPORTED_DOCX_FEATURE and sets `partial = True`. One fixture per wrapper asserts that its text appears.
- **A15 Text boxes [CONTRACT].** Extract every `w:txbxContent` outside `mc:Fallback`. Its paragraphs become `kind="text"` blocks directly after the anchor paragraph, with locator `{"part": "document", "textbox": n, "paragraph": i}`. Headers, footers and footnotes follow the same rule. TEXT_BOX_CONTENT stays as an informational warning and `partial` stays False. Embedded objects keep EMBEDDED_OBJECT with `partial = True`. Two tests: a document with `mc:AlternateContent` and a document with bare VML each yield the text exactly once. The `[CONTRACT]` tag covers the changed warning meaning and the new locator keys; block kinds do not change.
- **A16 Cells and paragraphs [CONTRACT].** Walk a cell's children in XML order and flush the text before and after a nested table as separate blocks. `"table"` in a locator is the preorder index across all tables. Body paragraphs use `{"part": "document", "paragraph": i}`.

#### 1-D2

- **A17 Numbering.** Resolve `numPr` through the paragraph style and its `basedOn` chain. Honour `numId` 0, `start`, `startOverride`, `lvlOverride` and composite `lvlText` such as `%1.%2`. Anything unresolved gives NUMBERING_NOT_RENDERED once per document. Fixture: `List Number` paragraphs, which carry no direct `numPr`.
- **A18 Page parts [CONTRACT].** Read the three header and three footer variants per section (default, first page, even page), deduplicated. Locators: `{"part": "header" or "footer", "section": s, "variant": "default" or "first" or "even"}`. Footnotes use `{"part": "footnotes", "id": n, "paragraph": i}`.

#### 1-E

- **A19 Interface.** `build_structure` returns `(nodes, warnings)`.
- **A20 Levels [CONTRACT].** A decimal label's level is its number of parts, plus 1 while a schedule is open. ARTICLE and roman-numbered headings are level 1. Numeric SECTION and CLAUSE headings use their part count. All three have kind `heading`. An unnumbered all-caps heading is level 1; it closes open nodes, and that is a known ceiling. `(a)` with no open decimal node sits one level below the nearest open node, or at level 1 when none is open. Definition and table nodes are leaves one level below their container.
- **A21 Numbering acceptance [CONTRACT].** A label counts only when it continues its previous sibling's sequence or starts one at 1, a or i. Other leading integers and roman tokens stay body text. Lines with dot leaders or a trailing page number (table of contents) are ignored. The same rule settles `(i)`, `(v)`, `(x)`, `(c)`, `(d)`, `(l)` and `(m)`. NUMBERING_AMBIGUOUS fires only when both readings continue a sequence.
- **A22 Node ranges [CONTRACT].** A node ends at the end of the last body block it covers. A PDF node that spans a page break contains the interleaved header and footer text, so consumers mask the ranges in `decorations`.

#### 1-F

- **A23 CLI.** Default output omits every text field (`source_text`, `blocks[].text`, `nodes[].text`); `--text` includes them. A ParseError exits with status 2.
- **A24 Contract ceilings.** `ParserContract.md` lists what the parser cannot see or fix: outlined vector text and form fields; `partial = True` means the core must never report "not found"; only Flate is budgeted; owner-only encrypted PDFs parse; an encrypted DOCX reports UNSUPPORTED_TYPE; a page-break `w:br` fuses neighbouring words; `w:noBreakHyphen` becomes ASCII `-`; rotated pages are unsupported.

#### Process

- Commit 0-A before 1-A starts.
- The Tanishq message lists every `[CONTRACT]` item. Work continues without waiting for a reply, and his changes land before 1-F.
- One independent second review runs at phase end, next to the other phase-end reviews. No per-part run.
- Confirm the exact skill name for the correctness review at 1-R: `/coderabbit:review` does not exist as written.

## Phase 2: API skeleton

Depends on: Phase 1. Part 2-D also needs `ml/clauseanchor_core` at contract version 2.0 on `main`. If it is not there, 2-A to 2-C still go ahead and 2-D waits.

Parse jobs run in a child process with a wall-clock kill (Phase 1 amendment A11). Plan this into 2-C.

- [ ] **2-A** FastAPI app, config, error envelope, health, readiness, capabilities
  `feat(api): add app with health, readiness and capabilities`
  Capabilities include the scope notice, the catalogue version and every category's support status (plan v1.1).
- [ ] **2-B** RAM store with TTL, SQLite metadata, expiring sessions
  `feat(store): add in-memory document store and expiring sessions`
- [ ] **2-C** Upload validation, parse jobs, document read and delete
  `feat(api): add document upload with validation and parse jobs`
- [ ] **2-D** Analysis jobs through the core analyzer (stub), progress, cancel, partial results
  `feat(jobs): run analysis jobs through the core analyzer`
  The analysis response carries the scope notice and reports processing completion and decision coverage as separate fields. Cancelled, timed-out or partially parsed work is reported as incomplete, never as absent. No safety or risk-score field (plan v1.1).
- [ ] **2-E** OpenAPI export and API.md
  `docs(api): export OpenAPI schema and document endpoints`
- [ ] **2-R** Phase review

## Phase 3: Polarity, reports, remaining endpoints

- [ ] **3-A** 46-category polarity policy and party binding endpoint
  `feat(polarity): add party binding and clause polarity`
- [ ] **3-B** PDF review report
  `feat(report): generate PDF review reports`
  The report includes the scope notice, the selected categories with their support status, any parsing or processing limitations, and the manual-review item count once 3-D exists. A count of zero is printed as a count, never as a verdict (plan v1.1).
- [ ] **3-C** Evaluations and sample-mode endpoints
  `feat(api): add evaluations and sample-mode endpoints`
- [ ] **3-D** Manual-review navigation (plan v1.1 section 10.7)
  `feat(api): add manual-review navigation for text without findings`
  Built last in Phase 3. From the parser blocks and the accepted spans, compute non-overlapping display units (plus gap units for substantive text no block covers) and label each one by its overlap with the union of accepted intervals: none ("Text without accepted findings"), partial ("Partly highlighted") or full. Mechanical labels only, never "cleared" or "assessed". Only enabled when every requested category search finished and nothing was cut short (no parser omission, unfinished stage, truncated candidate search or boundary failure); otherwise the response says "Processing incomplete". Missing pages are listed as unavailable, not as unmatched text. Transient, same TTL and deletion rules as the source text. Needs Tanishq's scope fixtures (plan section 11.3) before it starts.
- [ ] **3-R** Phase review

## Phase 4: Integration and run

Needs: the frontend on the real client, and Tanishq's real analyzer and artifacts.

- [ ] **4-A** Real analyzer switch with artifact manifest checks
  `feat(api): load real analyzer from verified artifacts`
- [ ] **4-B** Local run script and Dockerfile
  `build(backend): add local run script and Dockerfile`
- [ ] **4-C** End-to-end check on a public contract, CPU benchmark
  `test(backend): add end-to-end review check and CPU benchmark`
  Also run all eight scope cases from plan section 11.3 through the full application, first with fixture findings, then with the real model, and record expected against observed behaviour in BuildLog.md.
- [ ] **4-R** Phase review, then root docs and README merge (coordinated with Tanishq)
