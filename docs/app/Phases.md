# Backend Phases

Aryan's tracks: the backend (`backend/`) and the frontend (`frontend/`), each with its own phases. One part at a time. Every part is committed and pushed on its own, using the suggested message (adjust wording if you like). The frontend track is the last section of this file.

Legend: `[ ]` not started, `[~]` in progress, `[x]` done and committed.

Phase mapping: Plan Phase 3 = app Phase 1, Plan Phase 4 = app Phase 2, Plan Phase 10 backend parts = app Phase 3, Plan Phase 12 = app Phase 4.

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

- [x] **0-A** Add backend rules, architecture and phase plan
  `docs(app): add backend rules, architecture and phase plan`
- [x] **0-B** Sync app docs with parser amendments and v1.1 decisions
  `docs: sync app docs with parser amendments and v1.1 decisions`

## Phase 1: Parser

Goal: turn a PDF or DOCX into one canonical text with exact offsets, a clause structure tree and honest warnings. No API yet. Depends on nothing from the ML track.

- [x] **1-A** Package scaffold and the parsed-document model
  `chore(backend): set up package, tooling and parsed document model`
- [x] **1-B** PDF text extraction in reading order
  `feat(parser): extract ordered text blocks from PDFs`
  Adds `detect.py` and `pdf.py` with the A1 error mapping, A6 to A8 and their fixtures. Deviations and ceilings are listed under the 1-B amendments below.
- [x] **1-C** PDF safety: decoration, scanned, encrypted, malformed, limits
  `feat(parser): mark repeated page furniture and reject unreadable PDFs`
  Adds decoration, the scanned and partial checks, the page limit and the content budget to `pdf.py`, with A9 to A11 and their fixtures. Deviations and ceilings are listed under the 1-C amendments below.
- [x] **1-D** DOCX archive safety, body, tables and text boxes
  `feat(parser): extract DOCX body, tables and text boxes safely`
  Adds `docx.py` with A12 to A16 and their fixtures. Deviations and ceilings are listed under the 1-D amendments below.
- [x] **1-D2** DOCX numbering, headers, footers and footnotes
  `feat(parser): render DOCX numbering and extract page parts`
  Adds list labels, headers, footers, footnotes and endnotes to `docx.py` with A17, A18 and their fixtures. Deviations and ceilings are listed under the 1-D2 amendments below.
- [x] **1-E** Clause structure tree and definitions
  `feat(parser): build clause structure tree and detect definitions`
  Adds `structure.py` with A19 to A22 and the `contents_tab.docx` fixture. Deviations and ceilings are listed under the 1-E amendments below.
- [x] **1-F** Public entry point, CLI and parser contract
  `feat(parser): add parse entry point, CLI and parser contract`
  Adds `parse_document`, `schema.py`, `scripts/parse_file.py` and `ParserContract.md` with A23 and A24, and closes the Word-list gap that 1-E left open. Deviations and ceilings are listed under the 1-F amendments below.
- [ ] **1-R** Phase review: `/gstack-cso`, `/coderabbit:code-review`, `/gstack-review`; fixes as separate commits

**Sync with Tanishq:** send the `[CONTRACT]` items below before 1-B and apply his changes before 1-F. After 1-F, share `docs/app/ParserContract.md` and agree separators, offsets and warnings.

### Spec amendments (Phase 1)

Agreed in the spec review before 1-A. Each item amends the Phase 1 handoff where the two disagree; the handoff file stays unchanged. `[CONTRACT]` marks a change to parser output: fields, separators, offsets, codes, locators or the meaning of a warning. Those items go to Tanishq.

1-D is now two parts, **1-D** and **1-D2**. 1-E and 1-F keep their ids.

#### Every part

- **A1 Errors.** Each parser catches one closed tuple of library exceptions. PDF: the pdfplumber and pdfminer error types, plus TypeError, ValueError, AttributeError, AssertionError, KeyError and IndexError. DOCX: BadZipFile, lxml and python-docx package errors, the encrypted-member RuntimeError and NotImplementedError. Every hit maps to MALFORMED_FILE, except a wrapped PDFPasswordIncorrect, which maps to ENCRYPTED_PDF. Always `raise ParseError(code) from None`, and silence the `pdfminer` logger, because it logs raw document bytes. One test runs a seeded byte-flip sweep over a small PDF with a log handler attached. Each mutant must give a valid parse or a ParseError, never another exception type, and no exception text or log record may contain document text.
- **A2 pytest.** Set `pythonpath = ["."]` in pyproject. Without it `import app` fails under plain `pytest`. Done in 1-A.
- **A3 Attribution scrub.** Run `grep -rniE "<pattern>" backend/ docs/app/ --exclude-dir=.venv --exclude-dir=graphify-out --exclude=Rules.md`. The command as written always matches `Rules.md` and scans `.venv`. Add `graphify-out/` to `backend/.gitignore`. Done: the scrub command in 0-B, the ignore line in 1-A.
- **A4 Fixture registry.** `tests/fixtures/build.py` exposes `build_all(dir)`, which returns `{name: (path, expected error code or None)}`. `test_invariants.py` and the 1-F tests read it, so invalid fixtures are expected to raise instead of being skipped. Reportlab fixtures use `invariant=1`. Tests for `detect.py` live in `test_pdf.py`.

#### 1-A

- **A5 Assembler.** Remove `mark_decoration`. `build()` derives `decorations` from the header and footer blocks and sets `coverage.pages_total` from `page_count`. `add_block` refuses a block with no text (callers skip empty paragraphs and cells) and enforces the 500,000 code point limit as it appends. `build()` only computes the hash and raises NO_TEXT_FOUND, and it maps the UnicodeEncodeError from a lone surrogate to MALFORMED_FILE. Extra tests: bare CR, `new_page` twice, exactly 500,000 and 500,001 code points, whitespace-only text. Done in 1-A.

1-A also carries the A10 resolution's code-list change: `PARTIALLY_SCANNED_PDF` is a `WarningCode` in `errors.py`. The scanned-page checks land in 1-C.

Deviations from the 1-A spec, with reasons:
- `pyproject.toml` sets `version = "0.1.0"`. A `[project]` table needs a version, and the handoff names none.
- `build()` takes `media_type`, `page_count`, `warnings` and `partial`, and returns `nodes=()`. 1-F attaches the structure tree with `dataclasses.replace`, because the tree needs the finished `source_text`. `coverage.pages_with_text` counts the distinct pages that hold a block (`None` for DOCX); 1-C may refine it for scanned pages.
- `add_block` raises `ValueError` for a block with no text. An empty block is a caller bug, so it gets no file error code. A1 puts `ValueError` in the PDF catch tuple, so 1-B keeps assembler calls outside the try block that wraps pdfplumber. Otherwise a caller bug would surface as `MALFORMED_FILE`.
- `MAX_DECODED_CONTENT_BYTES` (A11) waits for 1-C, the first part that reads it.

#### 1-B

- **A6 Text fidelity [CONTRACT].** Call `extract_words(expand_ligatures=False)`; the default rewrites U+FB01 to `fi`. Runs of spaces collapse to one and NBSP arrives as U+0020 in PDFs, and the contract says so. `latin_unicode.pdf` embeds the Vera font that ships with reportlab and asserts that U+FB01 survives. Only DOCX asserts NBSP.
- **A7 Block splitting.** Compare the pitch (top to top) with the median pitch and split above 1.3 times, held in one named constant. A line that starts with a numbering token also starts a new block, matched by a coarse regex local to `pdf.py`. The left-edge rule applies only to a return to a column's left edge, never to an indent. New fixture: `tight_clauses.pdf` (hanging indents, 6 pt paragraph spacing).
- **A8 Columns.** Assign words to columns first, then group lines. A full-width line crosses the gutter. New fixtures: a 3-column table page (covers MORE_THAN_TWO_COLUMNS and shows that a table page keeps top-to-bottom order) and a page for COLUMN_ORDER_UNCERTAIN.

Deviations from the 1-B spec, with reasons. Done in 1-B:
- 1-B carries all of A1's error mapping for the PDF reader, with the fixtures `malformed.pdf` (the first 60 percent of `simple.pdf`) and `encrypted.pdf` (a user password). The libraries log raw document bytes from their first call, so the silenced loggers and the closed catch tuple cannot wait. The byte-flip sweep is one test in `test_pdf.py` (300 seeded mutants, a log handler attached). 1-C keeps decoration, scanned pages, the owner-only encrypted file, the page limit and the content budget.
- The `pdfplumber` logger is silenced next to `pdfminer`. pdfplumber puts exception text into a warning about unreadable metadata.
- The reader function is the only place library errors are caught. It returns plain words, and every assembler call runs after it. A test patches the assembler to refuse an empty block and asserts a `ValueError` comes out, not a file error code.
- A word with no text is dropped. A damaged ToUnicode map can produce one, and it reached layout as a division by zero in 28 to 35 of 2,500 mutants of the embedded-font fixture.
- A7 clarified: a return to the left edge ends a block only when the block began at the edge, or is the first block of its stream. Read literally, a first-line indent returned to the edge on its second line and cut every paragraph after its first line (28 blocks for 14 paragraphs in a flowed test page). The first block of a stream is exempt because it may open on the tail of a hanging paragraph from the page before.
- A8 gutter, in numbers: a strip at least 12 points wide that at most 40 percent of the rows touch, with words on both sides in at least two rows, whose right edge lies in the middle 60 percent of the page. A row reads across the gutter when a word spans its right edge or the gap there is under 12 points. Two or more gutters keep row order and add MORE_THAN_TWO_COLUMNS. A page with one gutter is read in bands: lines that cross it stand alone, and each run of column rows gives the left column, then the right.
  Resolution (16 October 2026, 1-R): the first version tested every row at every strip, so the cost grew with the square of the words. The rows are now counted per strip from their sorted positions, in time that grows with the words. The result is the same, and no `[CONTRACT]` item changes.
- COLUMN_ORDER_UNCERTAIN `[CONTRACT]` means a line that crosses the gutter sits between two runs of column rows, so the order around it is a guess. One warning per page. A full-width title above the columns or a full-width line below them does not trigger it.
- Block locator `[CONTRACT]`: `{"page": n, "block": i}`, with both numbers 1-based and `i` counting blocks within the page.
- `detect_type` returns `"pdf"` for `%PDF-`, `"docx"` for a ZIP that holds `word/document.xml` and no `word/vbaProject.bin`, and `UNSUPPORTED_TYPE` for everything else. A ZIP that cannot be read gives MALFORMED_FILE.
- `blank_page.pdf` (text, blank, text) is in the registry. 1-C adds the BLANK_PAGE warning to it (done).

Known ceilings of 1-B, none of them silent:
- Paragraphs with no spacing, no numbering and no indent fuse into one block per page. Nothing in the geometry separates them.
- First-line indents with no paragraph spacing and no numbering put block boundaries one line late: the next paragraph's indented first line joins the block above, and that paragraph's second line starts a new block. With 6 pt spacing the boundaries are right, except that a page opening on a paragraph start cuts it after its first line (16 blocks for 14 paragraphs on the two-page probe: one paragraph crosses the page break and one is cut).
- A two-column table is read as two columns, because its geometry matches a two-column page. Tables with three or more columns read row by row.
- `pdf.pages` builds every page object before 1-C adds the 100-page check and the incremental count (A11). Closed in 1-C.
- A mutated file with a broken page tree and no pages reports NO_TEXT_FOUND.

#### 1-C

- **A9 Decoration [CONTRACT].** Classify margin-zone lines before building blocks and give each candidate its own block. A page-number-shaped line in the margin zone counts as decoration at any page count. Other lines keep the repetition rule. Fixtures: 1-page and 2-page documents, a header on 2 of 3 pages (not decoration), a body line inside the zone.
- **A10 Scanned and partial [CONTRACT].** Count characters outside the margin zones. An image-dominant page with fewer than 20 of them is scanned. One with fewer than 200 sets `coverage.partial = True`, because a searchable scan (full-page image, large real text layer) must stay usable. Widget and FreeText annotations with content also set `partial = True`. Fixtures: a scanned page with a Bates stamp, an all-blank PDF (NO_TEXT_FOUND) and an owner-only encrypted PDF (parses).
  Resolution (17 October 2026, 1-R) `[CONTRACT]`: a font with no text mapping puts `(cid:N)` into the text, and nothing said so. A page where more than 25 percent of the glyphs are such tokens (each token counts once, whatever its length) gets `UNMAPPED_GLYPHS` and sets `partial`. The text is kept as it is, and `pages_with_text` still counts the page. Fixtures: `unmapped_all`, `unmapped_page_two`.
  Resolution (2 October 2026) `[CONTRACT]`: only `SCANNED_PDF` rejects a file, when every page with content is scanned. If only some pages are scanned, the parser sets `coverage.partial = True`, adds a `PARTIALLY_SCANNED_PDF` warning and parses the rest, so `PARTIALLY_SCANNED_PDF` moves from the error list to the warning list. The under-200 partial rule stays. The `partly_scanned.pdf` fixture now expects a parse with the warning. Reason: executed contracts often end in a scanned signature page. The code lists in `errors.py` follow this from 1-A.
- **A11 Content budget [CONTRACT].** Before extracting a page, decode its content streams and any Form XObjects incrementally, with Flate read through `zlib.decompressobj` in `max_length` chunks. Stop as soon as the running total passes `MAX_DECODED_CONTENT_BYTES` (8 MiB, kept with the other limits in `errors.py`) and raise TOO_MUCH_TEXT. Never decode a stream fully and measure afterwards. Count pages with `islice(PDFPage.create_pages(doc), 101)` instead of building every Page object. Fixtures: two 16 KB PDFs that decode past the budget, one in the page content and one in a Form XObject. Known ceiling: only Flate is measured. A 16 KB PDF that decodes to 16 MB took 186 s in `extract_words`, so Phase 2 must also add a child-process wall-clock kill.
  Resolution (16 October 2026, 1-R) `[CONTRACT]`: the budget measured the first filter only, and pdfminer inflates every stage in full, so `/Filter [/FlateDecode /FlateDecode]` passed. A stream that names more than one filter that can grow the data (Flate, LZW or RunLength) now counts as over the limit without being decoded (`TOO_MUCH_TEXT`), whatever it holds. A content stream has no use for such a chain (the three real PDFs of the smoke set use one Flate filter or none), and the rule also bounds the work to one growing stage. A stream whose only growing filter is LZW or RunLength still counts its stored length. Fixture: `bomb_double_flate`.

Deviations from the 1-C spec, with reasons. Done in 1-C:
- A9 widened `[CONTRACT]`: a page-number-shaped line that is the first or last row of the page is decoration wherever it sits, not only inside the margin zone. Without the rule, a page whose text stops halfway down kept its number as text (32 of 33 pages in one real contract, 13 of 14 in another), and on a two-column page the number joined the left column and was read before the right one. Folding the other margin candidates back into the body flow cut blocks on two files but changed reading order on one, so each candidate keeps its own block.
- Margin zone: a line whose vertical middle sits in the top or bottom 8 percent of the page. A line there leaves the column and gutter logic and becomes a block of its own. A page lists its top margin lines first, then its body blocks, then its bottom margin lines.
- A candidate has kind `header` or `footer` when it is page-number-shaped: `3`, `Page 3`, `Page 3 of 10`, `3/10` or `- 3 -`, with one to three digits and a hyphen, en dash or em dash. It has that kind too when the same line recurs in its zone (compared in lowercase, each digit read as `#`) on at least 3 pages and at least half the pages, rounded up. Otherwise its kind is `text`. The 7-page fixtures pin the rounding: 3 of 7 is text, 4 of 7 is decoration.
- Image share is the sum of the image boxes clipped to the page, over the page area, capped at 1. Above 0.5 is image-dominant.
- The parser emits `PARTIALLY_SCANNED_PDF` `[CONTRACT]` once per scanned page and sets `page`. A10 does not say how many. A page with neither text nor an image gets `BLANK_PAGE`. "Every page with content is scanned" counts only pages with text or an image.
- `coverage.pages_with_text` `[CONTRACT]` leaves out scanned pages, because their only blocks are margin stamps. `build()` takes `unreadable_pages` for this.
- Annotations: a Widget or FreeText annotation whose own `/Contents` or `/V` holds non-blank text sets `partial = True`. A blank field does not.
- The budget undoes leading ASCII85 and ASCIIHex filters before it measures a Flate stream. A11 says only Flate is measured, but reportlab writes ASCII85 in front of Flate, and without this step a bomb in that form counted its stored length. For an encrypted file it deciphers each stream first (`bomb_encrypted.pdf`).
- The budget counts each distinct stream once per document, keyed by object id, and walks nested Form XObjects with a work list, so a form that names itself ends. The page count comes from `islice(PDFPage.create_pages(doc), 101)` before any text is read.
- `MAX_DECODED_CONTENT_BYTES` is in `errors.py`, next to the other limits.
- Fixtures: `header_footer`, `page_number_one_page`, `furniture_two_pages`, `header_two_of_three`, `header_three_of_seven`, `header_four_of_seven`, `body_in_margin`, `page_numbers_off_margin`, `two_column_page_number`, `scanned`, `scanned_stamp`, `partly_scanned`, `scan_19_chars`, `scan_20_chars`, `scan_199_chars`, `scan_200_chars`, `scanned_most_of_page`, `image_mostly_off_page`, `all_blank`, `owner_only`, `form_field`, `free_text`, `plain_annotations`, `hundred_pages`, `too_many_pages`, `bomb_content`, `bomb_form`, `bomb_encrypted`, `form_cycle`. All are generated at test time with reportlab or raw bytes, and nothing binary is committed.

Known ceilings of 1-C, none of them silent:
- Only Flate, behind any leading ASCII filter, is measured. LZW and RunLength streams count their stored length, which understates them.
- A form drawn many times counts once. Font programs, ToUnicode maps and object streams are not budgeted.
- The budget bounds decoded size, not time. A11 measured 186 s for a 16 MB stream. An 8 MiB stream of white space, the largest the budget accepts, parsed in 0.05 s (BuildLog, "Checks before 1-D"), so the cost follows the number of tokens and not the number of bytes. 8 MiB of dense operators or text has not been measured. The Phase 2 wall-clock kill is the real bound.
- A form chain 3,000 deep makes pdfminer fail, and the file is rejected as `MALFORMED_FILE` with no leak.
- Annotation values held only on a parent field are not seen, and annotation types other than Widget and FreeText are not checked for text.
- Overlapping images count twice toward the image share.
- A bare number that is the first or last row of a page is decoration even when it is a table cell or a list marker on its own line.
- A page number printed on a line with other text, such as `Agreement 12`, is decoration only when the line repeats on enough pages.
- A margin line that is neither number-shaped nor repeated stays text, and a page that fills the margins breaks one paragraph into several blocks.

#### 1-D

- **A12 Archive.** Convert backslashes to slashes, then reject any member with an absolute path, a drive letter or a `..` segment (ARCHIVE_UNSAFE). Reject a total uncompressed size over 100 MiB (ARCHIVE_TOO_LARGE). One `build_zip(member_name)` fixture builder covers slash, backslash and drive-letter names. Other fixtures: a 101 MiB sparse archive and a corrupt zip (MALFORMED_FILE).
  Resolution (16 October 2026, 1-R) `[CONTRACT]`: the declared sizes bound nothing. zipfile inflates a Flate member in one call of up to 1 GiB, and a bzip2 or lzma member with no limit, before it cuts the result to the size the file declares. The parser now refuses a member that is not stored or Flate (`ARCHIVE_UNSAFE`) and reads every member in 64 KiB steps against the 100 MiB limit (`ARCHIVE_TOO_LARGE`), so the limit counts bytes read. python-docx receives a stored copy of the package.
- **A13 Tracked changes [CONTRACT].** Match `ins`, `del`, `moveFrom` and `moveTo` by namespace URI in every text part under `word/`: document, headers, footers, footnotes and endnotes.
- **A14 No silent loss [CONTRACT].** The body walk recurses through `sdt` and `sdtContent`, `smartTag`, `fldSimple`, `customXml` and `hyperlink`. An `altChunk` or any unknown block-level child raises UNSUPPORTED_DOCX_FEATURE and sets `partial = True`. One fixture per wrapper asserts that its text appears.
  Resolution (2 October 2026): an unknown block-level child, including `altChunk`, is skipped. The parser adds an `UNSUPPORTED_DOCX_FEATURE` warning and sets `coverage.partial = True`; it does not raise. Reason: a raised error leaves no result to mark partial. The code stays in the warning list.
- **A15 Text boxes [CONTRACT].** Extract every `w:txbxContent` outside `mc:Fallback`. Its paragraphs become `kind="text"` blocks directly after the anchor paragraph, with locator `{"part": "document", "textbox": n, "paragraph": i}`. Headers, footers and footnotes follow the same rule. TEXT_BOX_CONTENT stays as an informational warning and `partial` stays False. Embedded objects keep EMBEDDED_OBJECT with `partial = True`. Two tests: a document with `mc:AlternateContent` and a document with bare VML each yield the text exactly once. The `[CONTRACT]` tag covers the changed warning meaning and the new locator keys; block kinds do not change.
- **A16 Cells and paragraphs [CONTRACT].** Walk a cell's children in XML order and flush the text before and after a nested table as separate blocks. `"table"` in a locator is the preorder index across all tables. Body paragraphs use `{"part": "document", "paragraph": i}`.

Deviations from the 1-D spec, with reasons. Done in 1-D:
- `parse_docx(data)` is the entry point. It does not call `detect_type`, which 1-F puts in front of both parsers. The package is opened with python-docx, so a file python-docx cannot open (a strict OOXML package, a template, a missing relationship) is `MALFORMED_FILE`.
- A12 order: the member names and methods are checked first, then each member is read in 64 KiB steps and counted. zipfile stops a member at its declared size, so a member that understates its size is cut short and fails its checksum (`MALFORMED_FILE`), and one whose checksum fits the cut data is handed on cut. Nothing is extracted to disk. The overlapping and duplicate entry warnings that zipfile raises are silenced, because their text carries a member name from the file.
- A1 tuple for DOCX is larger than the spec's list: `zlib.error`, `EOFError`, `KeyError`, `ValueError` and `AttributeError` each came out of a mutation sweep as an uncaught type. `TypeError`, `AssertionError` and `IndexError` follow the PDF reader's tuple. The walk and the archive checks sit inside the try, the assembler calls outside it, as in `pdf.py`.
- Locators `[CONTRACT]`. A body paragraph is `{"part": "document", "paragraph": i}`, with `i` counting every body-level paragraph from 1, empty ones included, so the number stays the paragraph's place in the file. A text box paragraph is `{"part": "document", "textbox": n, "paragraph": i}`. `n` numbers text boxes from 1 across the document in preorder (an outer box before the box inside it), and `i` counts the paragraphs of that box. A table cell is `{"part": "document", "table": t, "row": r, "cell": c, "segment": k}`. `t` is the preorder index across all tables, and `r` and `c` count rows and cells from 1 (a merged cell is one cell). `k` is not named in A16: it counts the blocks of one cell from 1, because a nested table or a text box ends one block and the text after it starts the next. The key is always present.
- A cell is one block of kind `table_cell`, its paragraphs joined with a newline. An empty cell makes no block. A text box anchored in a cell is read as a nested table is: the cell text so far, anchor paragraph included, is flushed, then the box's blocks, then the rest of the cell as the next segment.
- A paragraph with no text, or only white space (a lone U+00A0 included), makes no block and still counts in `paragraph`. Characters are never altered, so U+00A0 and runs of spaces stay.
- Run text follows the library's rules: `w:t`, `w:tab`, `w:ptab` (tab), `w:cr` and a `w:br` of type text wrapping (newline), `w:noBreakHyphen` (`-`). A page or column `w:br` adds nothing, which is A24's fused-words ceiling. Field instructions (`w:instrText`) are not read, field results are.
- A14 as built. At block level the walk sees through `sdt`, `customXml`, `smartTag`, `fldSimple` and `hyperlink`, also between table rows and between cells. A child that is not a paragraph, a table, one of those wrappers or a property or range marker is skipped, with `UNSUPPORTED_DOCX_FEATURE` and `partial`. `detail` is `altChunk` or `unknown_block`.
- A15 as built: a `w:object` anywhere in a paragraph gives `EMBEDDED_OBJECT` and `partial`. `TEXT_BOX_CONTENT`, `EMBEDDED_OBJECT` and each `UNSUPPORTED_DOCX_FEATURE` detail are emitted once per document `[CONTRACT]`.
- A13 as built: the tracked-change check covers the parts of type document, header, footer, footnotes and endnotes that the package relationships reach, matched by namespace and local name, in any element position. That includes `w:ins` inside `w:rPr`, which marks an inserted paragraph.
- The walk stops with `TOO_MUCH_TEXT` as soon as the text passes 500,000 characters, before the assembler runs.
  Resolution (16 October 2026, 1-R) `[CONTRACT]`, three bounds. The walk also stops with `TOO_MUCH_TEXT` at the 100,001st paragraph of the whole file, empty ones included (`MAX_DOCX_PARAGRAPHS`): the text limit counts only text, and an empty paragraph is 6 bytes, so the 100 MiB archive limit allowed 17 million of them. A part with a DOCTYPE is `MALFORMED_FILE`: lxml keeps each entity reference as a node and the text after it was dropped without a sign, and Word never writes one. A note `w:id` that is missing, signed or longer than nine digits is `MALFORMED_FILE`, the bound `_number` already puts on the numbering ids.
- `media_type` is `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
- Fixtures: `simple`, `zip_dotdot`, `zip_backslash`, `zip_drive_letter`, `zip_absolute`, `zip_dots_in_name`, `archive_too_large` (101 MiB sparse), `corrupt_zip`, `tracked_insert`, `tracked_delete`, `tracked_move_from`, `tracked_move_to`, `tracked_other_prefix`, `tracked_paragraph_mark`, `tracked_in_header`, `tracked_in_footnotes`, `foreign_ins`, `wrap_sdt`, `wrap_sdt_inline`, `wrap_smart_tag`, `wrap_fld_simple`, `wrap_custom_xml`, `wrap_hyperlink`, `wrap_sdt_row`, `wrap_sdt_cell`, `alt_chunk`, `unknown_block`, `textbox_alternate_content`, `textbox_vml`, `textbox_nested`, `textbox_in_cell`, `embedded_object`, `tables`, `nested_table`, `run_content`, `empty_paragraphs` and `entity_bomb`. All are generated at test time from raw XML, and nothing binary is committed. `build_zip(member_name)` builds the archive fixtures and sets the member name after the entry is made, because `ZipInfo` rewrites a backslash on Windows.

Known ceilings of 1-D. The first two bullets are silent: the file parses and nothing says text was left out.
- Inline math, chart text and SmartArt text are not read and raise no warning. A block-level `m:oMathPara` is skipped with `UNSUPPORTED_DOCX_FEATURE`.
- Comments are not read and raise no warning. Symbol characters (`w:sym`) and footnote reference marks add nothing.
- Headers, footers, footnotes and endnotes were not read in 1-D, and 1-D2 reads them. They were already searched for tracked changes.
- A part that no relationship reaches is neither searched for tracked changes nor read.
- A strict OOXML package, which `detect_type` accepts, is rejected here as `MALFORMED_FILE`.
- XML nested deeper than 256 levels is `MALFORMED_FILE`.
- A text box is read at its anchor paragraph, not by where it sits on the page.
- Merged cells are not marked. List numbering was not rendered in 1-D, and 1-D2 does it.

#### 1-D2

- **A17 Numbering.** Resolve `numPr` through the paragraph style and its `basedOn` chain. Honour `numId` 0, `start`, `startOverride`, `lvlOverride` and composite `lvlText` such as `%1.%2`. Anything unresolved gives NUMBERING_NOT_RENDERED once per document. Fixture: `List Number` paragraphs, which carry no direct `numPr`.
- **A18 Page parts [CONTRACT].** Read the three header and three footer variants per section (default, first page, even page), deduplicated. Locators: `{"part": "header" or "footer", "section": s, "variant": "default" or "first" or "even"}`. Footnotes use `{"part": "footnotes", "id": n, "paragraph": i}`.

Deviations from the 1-D2 spec, with reasons. Done in 1-D2:
- Label carrier `[CONTRACT]`. A17 does not say where the label goes. The handoff and `Architecture.md` say the block locator, so a numbered paragraph's locator gains `"list_label"`: the level's text with each `%n` replaced by that level's counter, such as `1.`, `1.1`, `(a)` or `ARTICLE I`. The key is absent when the paragraph is not numbered, when its number is not rendered, and for formats with no number. The label is never in `source_text`.
- A label sits on a body paragraph, a text box paragraph, or a cell block of one paragraph. A cell block that joins several paragraphs gets no label and raises `NUMBERING_NOT_RENDERED`, because one block has no single paragraph to hold it.
- Counters. Every numbered paragraph advances its counter, empty ones included, in document order. A text box paragraph counts after its anchor. Headers, footers and notes use the same counters as the body.
- Resolution. `numId` and `ilvl` each come from the paragraph's own `numPr`, then the style chain, nearest style first (32 steps at most). A paragraph with no `pStyle` takes the default paragraph style. `numId` 0 switches numbering off. Nums that share an abstractNum share counters, except a num with a `startOverride`, which counts on its own. A `lvlOverride` with a `lvl` replaces that level. `lvlRestart` and `isLgl` are honoured. An absent `start` is 0, as the schema says.
- Formats: `decimal`, `lowerLetter`, `upperLetter`, `lowerRoman` and `upperRoman`, the handoff's set. Letters repeat past z (aa, bb) up to 780, and roman numerals stop at 3999. `bullet` and `none` have no number, so they give no label and no warning. The handoff says "anything else" warns, which would have warned on every bullet list. Every other format gives no label and `NUMBERING_NOT_RENDERED`.
- Bounds. A level's text and a rendered label are at most 100 code points, a number attribute at most 9 digits, a level index below 9. A numbering part can otherwise make the parser build a long label for every paragraph.
- Page part locators `[CONTRACT]`. A18 names three keys. A part holds several paragraphs, so the blocks would share one locator. Header and footer blocks also carry `paragraph`, and `table`, `row`, `cell`, `segment` or `textbox` as the body does. Tables and text boxes are numbered from 1 within each header, footer or note, and not across the file.
- Page parts are read after the body: for each section in order, the headers (default, first, even), then the footers. Only references a section names are read, because a section with none shows the previous section's part, which is read where it was named. A part named twice is read once, and a part with the same kind and text as an earlier one is dropped. Blocks have kind `header` or `footer`, table cells and text boxes too, so `decorations` covers them. `titlePg` and `evenAndOddHeaders` are not consulted.
- Notes `[CONTRACT]`. Footnotes then endnotes follow the page parts. Both have kind `footnote`, and the locator's `part` (`footnotes` or `endnotes`) tells them apart, so the kind set does not change. `separator`, `continuationSeparator` and `continuationNotice` notes are skipped by type.
- `lxml` and `pdfminer.six` are pinned in `requirements.txt` at the versions that were already resolved, because both are imported directly.
- Fixtures: `list_number_style`, `numbering_levels`, `header_footer` and `notes` are in the registry. The other cases (styles, overrides, restarts, formats, cells, text boxes, hostile numbering, limits) are built inline in `test_docx.py`.

Known ceilings of 1-D2, none of them silent unless noted:
- Word's finer restart rules inside one num are not modelled: a `lvlOverride` with no `startOverride`, and a restart in the middle of a list. Nums of one abstractNum simply share counters. This one is silent when a real file depends on it, and a label can be wrong.
- A level that names a style through `pStyle` is not followed when the style's `numPr` has no `ilvl`. The level defaults to 0.
- A header list continues the body's count, because the counters are shared.
- Other formats (ordinal, cardinal text, decimal with leading zero, scripts other than Latin) give no label and a warning.
- A footnote reference mark adds nothing to the body (a 1-D ceiling), so a note's text carries no marker back to its place.
- A DOCX table of contents is plain text with typed numbers and a tab before the page number (`1.<tab>Term of Agreement<tab>1`). 1-E must treat the tab and trailing number like a dot leader (A21). Done in 1-E, with `contents_tab.docx`.

#### 1-E

- **A19 Interface.** `build_structure` returns `(nodes, warnings)`.
- **A20 Levels [CONTRACT].** A decimal label's level is its number of parts, plus 1 while a schedule is open. ARTICLE and roman-numbered headings are level 1. Numeric SECTION and CLAUSE headings use their part count. All three have kind `heading`. An unnumbered all-caps heading is level 1; it closes open nodes, and that is a known ceiling. `(a)` with no open decimal node sits one level below the nearest open node, or at level 1 when none is open. Definition and table nodes are leaves one level below their container.
- **A21 Numbering acceptance [CONTRACT].** A label counts only when it continues its previous sibling's sequence or starts one at 1, a or i. Other leading integers and roman tokens stay body text. Lines with dot leaders or a trailing page number (table of contents) are ignored. The same rule settles `(i)`, `(v)`, `(x)`, `(c)`, `(d)`, `(l)` and `(m)`. NUMBERING_AMBIGUOUS fires only when both readings continue a sequence.
- **A22 Node ranges [CONTRACT].** A node ends at the end of the last body block it covers. A PDF node that spans a page break contains the interleaved header and footer text, so consumers mask the ranges in `decorations`.

Deviations from A19 to A22, with reasons. Done in 1-E:
- Kinds `[CONTRACT]`. A20 sets levels and gives `heading` to ARTICLE, roman, SECTION and CLAUSE labels. It names no kind for the rest. A numbered label takes its kind from its level: 1 is `section`, 2 is `clause`, 3 and deeper are `subclause`. ARTICLE, SECTION, CLAUSE and bare roman labels are `heading`, and so is an unnumbered all-caps line. SCHEDULE, ANNEXURE, APPENDIX and EXHIBIT labels are `schedule`.
- Labels `[CONTRACT]`. `label` holds the label without its trailing full stop: `1`, `1.1`, `(a)`, `(ii)`, `ARTICLE I`, `Section 2.1`, `SCHEDULE 2`. A decimal has one to five parts of one to three digits, and may run into its title (`10.Title`). Letters run `(a)` to `(z)`, then `(aa)` and `(bb)`, as Word numbers them. A Word `list_label` is read with the same grammar and wins over the typed text. A definition's label is its quoted term without the quotes.
- Sequence state `[CONTRACT]`. A21 says a label "continues its previous sibling's sequence or starts one at 1, a or i". The parser keeps the last number and the run length of each sequence: decimals by their prefix, letters and numerals by the node they sit under. A number continues a run when it is one more. A restart at 1 replaces a run of 3 or fewer (a party or recital list before the clauses) and is body text after a longer run (a list inside a clause). A decimal under an open decimal of the same depth must carry that decimal's number, so `2.1` after an open `1.` stays body text. A schedule label clears every sequence, because a schedule numbers from 1.
- Word lists may open above 1 `[CONTRACT]`. The first top-level decimal read from `list_label` may be any number, because Word counts the empty paragraphs that the reader leaves out of the blocks. Typed numbers still open at 1. Without this rule every section of the Common Paper template (`2.` to `14.`) was rejected.
- Letters and numerals. A letter sits one level below the nearest open decimal, else one level below the nearest open node that is not a letter or a numeral, else at level 1. A numeral sits one level below the nearest open letter. `(i)` is a letter when it continues the letters, and a numeral when it starts a run under a letter. When both continue it is a letter, and NUMBERING_AMBIGUOUS fires once per page.
- Heading words. A heading word with a lower case word after it on the same line is running text (`Section 3 of this Agreement`). A typed ARTICLE, schedule or roman heading counts only when its first line has 80 characters or fewer.
- Contents lines `[CONTRACT]`. A21 names dot leaders and a trailing page number. A block is a contents entry when it holds a dot leader anywhere (four or more full stops, with or without a space between them, or an ellipsis character), or when it is one line and the text after its label ends in a space or a tab and one to three digits. A year has four digits, so a clause that ends in one is a clause. `ARTICLE 1` is not an entry, because the test reads what follows the label. An all-caps line goes through the same test before it becomes a heading.
- Bare numbers. A typed decimal whose first line is the number alone, with no full stop and no title, is ignored. 1-C does not mark a page number printed mid-page as furniture, and the number equals the next clause number on the page that opens that clause. `3.` with its full stop is still a label.
- All-caps headings `[CONTRACT]`. A20 does not define the test. A block is a heading when it has 80 characters or fewer, at least 3 letters, and every line at least 60 percent capitals. The test runs per line, so a mixed case line with redaction marks under it is not a heading. A heading opens at level 1 and closes every open node, as A20 says.
- Titles `[CONTRACT]`. An all-caps block straight after a block that is only a label (`ARTICLE 5`, `SCHEDULE A`, `1.`) is that label's title. It opens no heading, so the label's node stays open and keeps the clauses that follow. Read literally, A20 would close the node on its own title and leave it holding its label alone. A title in title case was already part of the node.
- Tables `[CONTRACT]`. Each outermost table is one `table` node, one level below its container, and a nested table has no node. Labels and headings are not read inside a cell. A definition in a cell is a child of the table node, so a table is a leaf for labels only.
- Definitions `[CONTRACT]`. The node spans the quoted term with both quotes and sits one level below the innermost open node, or below the table. A term has up to 80 characters and may wrap a line. Forms: `"T" means`, `shall mean`, `has the meaning`, `have the meaning`, `shall have the meaning`, `refers to`, and `(the "T")` or `("T")`, in straight or curly quotes. The label drops trailing `,`, `.` and `;` and collapses white space. An empty or space-padded term is not a definition, and neither is a quoted phrase with none of these forms around it.
- Ranges. A node ends at the end of the last body block it covers (A22). Header, footer and footnote blocks never open a node and never extend one, so a node that spans a page break holds the furniture inside it and not after it.
- Ids. Nodes are created in document order, a container before what it holds, so `n0001`, `n0002` and on follow start, then level. The invariant test checks the order on every fixture.

Known ceilings of 1-E, none of them silent unless noted:
- A numbered list that shares numbers with the section sequence takes them. In the Athens agency agreement a definitions list `1.` to `6.` inside Section 4 took 5 and 6, so Sections 5 and 6 are missed and two false `5` and `6` nodes appear. A Part A and Part B pair that restarts after a long run reads as a list inside the clause. Keying the sequences by label style (a heading word against a bare number) would split the two, and would then open the list items as level 1 nodes, which cuts Section 4 short. Not built.
- A short all-caps line is a heading and closes open nodes (A20's ceiling). Seen: signature block names (`COMPANY`), formula words (`MULTIPLIED BY`, four times in Dova), and a page header that 1-C did not mark as furniture (`TABLE OF CONTENTS` three times in Dova, `BLACKWELL/MUNKSGAARD PUBLISHING SYSTEM` twice in Healthgate).
- A party list at the top of a document (`1.` and `2.`) opens two level 1 nodes. The clause sequence then replaces its run by restart, and the two nodes stay (Healthgate).
- An empty numbered paragraph after the first one breaks that Word list's run, because the reader drops the empty block and the next label is one number too high. This follows from the rule and no real file in the smoke set shows it. Accepting any larger number from a Word list would fix it. Closed in 1-F (see the 1-F amendments).
- Letters and numerals from a Word list still open at `(a)` and `(i)`. A list whose first items were empty paragraphs is not read, because a lenient start for letters would make `(i)` a letter.
- Numbers inside a table cell are not read, so a contract laid out as one large table has a `table` node and no clauses (the Bonterms cover tables).
- A contents page with neither a dot leader nor a trailing number would be read as clauses. None was seen.
- A definition in a form that is not listed (`X shall be construed as`) is not found, and a quoted term at the end of one block with its verb at the start of the next is missed.
- `ParserContract.md` and A24 belong to 1-F. Done in 1-F.

#### 1-F

- **A23 CLI.** Default output omits every text field (`source_text`, `blocks[].text`, `nodes[].text`); `--text` includes them. A ParseError exits with status 2.
  Resolution (17 October 2026, 1-R) `[CONTRACT]`: two more fields hold the file's own words, a block's `locator.list_label` (up to 100 characters of numbering text) and the `label` of a definition node (the quoted term, up to 80). The default output and `to_json(doc, text=False)` now leave out the first and set the second to `null`. Other node labels follow the label grammar and stay. The CLI also compares the file size with the 10 MiB limit before it reads the file, and prints `FILE_TOO_LARGE` for a larger one.
- **A24 Contract ceilings.** `ParserContract.md` lists what the parser cannot see or fix: outlined vector text and form fields; `partial = True` means the core must never report "not found"; only Flate is budgeted; owner-only encrypted PDFs parse; an encrypted DOCX reports UNSUPPORTED_TYPE; a page-break `w:br` fuses neighbouring words; `w:noBreakHyphen` becomes ASCII `-`; rotated pages are unsupported.

Deviations from the 1-F spec, with reasons. Done in 1-F:
- Word-list gap `[CONTRACT]`. 1-E left a gap open: the reader drops an empty numbered paragraph, so the label after it is one number too high, and the rest of that list was read as body text. A Word label above the last number in its sequence now continues it, for decimals, letters and numerals alike. It ranks below a plain continuation and below a start at 1, so `(i)` after `(a)` and `(b)` is still a numeral. A letter does not reach a repeated letter (`(aa)`, `(bb)`) by a gap: Word letters run a to z, then aa to zz, so `(ii)` after `(i)` would be the 35th letter and needs 26 empty paragraphs. The first version allowed it, and the Victoria file showed `(ii)` and `(iii)` taken as clauses. The gap counts toward the run length, so `1`, `2`, `4`, `5` is a run of four and a restart at 1 after it is still a list inside a clause. A typed number never skips ahead. Tests for the new rule replace a 1-E test that pinned the old one (a Word `1.` followed by `5.` stays one node). Fixture: `empty_numbered.docx`, with an empty paragraph at the top level, inside a nested decimal list and inside a letter list.
- `parse_document` checks the size, then `detect_type` (which raises `EMPTY_FILE` and `UNSUPPORTED_TYPE`), then dispatches to the reader, then builds the tree and attaches it with `dataclasses.replace`. The structure builder's warnings follow the reader's. The public names are `parse_document`, `ParsedDocument`, `ParseError`, `ErrorCode` and `WarningCode`, as the handoff lists.
- `schema.py` holds the JSON Schema and `to_json`, the function that turns a document into the plain data the schema describes. The schema is written by hand, with the enums read from the model (block kinds, node kinds, warning codes). The checker that tests it against every parsed fixture is about 40 lines in `test_contract.py`, so no schema library was added. `docs/app/parser_output.schema.json` is the committed copy, and a test keeps it equal to `SCHEMA`.
- The CLI keeps the handoff's `--summary`. The error code goes to stderr, so stdout holds only JSON. The CLI escapes non-ASCII characters in the JSON, because the Windows console cannot print every character a contract holds. A usage error from `argparse` also exits with status 2, which A23 gives to `ParseError`. The tool is for development, so it does not tell the two apart.
- `VALID_NAMES` joined `NAMES` in `tests/fixtures/build.py`, so the schema test can run over the files that parse without skipping the rest.
- The root README's backend section no longer says the readers are still to come, and shows the command line.
- The handoff asks 1-F to run `graphify` against `Architecture.md`. Rules section 7 puts it at the end of the phase, so it moves to 1-R.

Known ceilings of 1-F, none of them silent unless noted:
- The schema describes shape only. `test_invariants.py` checks that offsets slice back to their text and that nodes nest inside their parents.
- The gap rule trusts a Word number. A Word list that jumps for another reason (a restart that Word's own rules would have applied, which 1-D2 does not model) reads as one run. Two readings that both only skip ahead (`(x)` as a letter or a numeral) keep the first, which is the letter.
- A Word list whose first item is an empty numbered paragraph is still not read when it is a nested decimal (`1.1` empty, `1.2` first), a letter list or a numeral list. Only a top-level decimal list may open high.
- A numeral list that opens right after `(h)` reads `(i)` as the ninth letter, because a continuation outranks a start. Its other numerals stay inside that node, one level too high. This is the 1-E reading of `(i)`, seen in the Victoria general conditions (`(h) a reference to:` then `(i)` to `(iv)`) and not changed by the gap rule. Telling the two apart needs the Word list's own level, which `docx.py` knows and does not pass on.
  Resolution (17 October 2026, 1-R) `[CONTRACT]`: `docx.py` now passes the level on. The locator of a numbered DOCX paragraph gains `"list_level"` (the `w:ilvl`, 0 to 8), present exactly when `list_label` is. When a Word label reads as both a letter and a numeral and a letter is open, a deeper level than that letter makes it a numeral and the same level makes it the next letter; a shallower level keeps both readings. On the Victoria file `(h)` now holds `(i)` to `(iv)` as level 3 children (165 nodes became 168), and no other node moved. Fixtures: `numeral_after_h.docx` and `letter_after_h.docx`. Ceiling: a PDF block, and a DOCX list that is typed, have no level, so the PDF case is unchanged and `(i)` after `(h)` is still read as the ninth letter there. A Word list whose letters and numerals share one level in different lists is also not told apart; the number format (`lowerLetter` or `lowerRoman`) would settle it, and is not passed on.
- `name_span` and the `party` kind are not built. `ParserContract.md` section 8 records the requirement, and no part of Phase 1 or 2 builds it yet. 2-E defines the API field on top of it.

#### Process

- Commit 0-A before 1-A starts.
- The Tanishq message lists every `[CONTRACT]` item. Work continues without waiting for a reply, and his changes land before 1-F.
- One independent second review runs at phase end, next to the other phase-end reviews. No per-part run.
- The correctness review at 1-R is `/coderabbit:code-review` with `--base-commit <commit before 1-A>`. `/coderabbit:review` does not exist (see BuildLog, 0-B).

## Phase 2: API skeleton

Depends on: Phase 1. Part 2-D also needs `ml/clauseanchor_core` at contract version 2.0 on `main`. If it is not there, 2-A to 2-C still go ahead and 2-D waits.

Parse jobs run in a child process with a wall-clock kill (Phase 1 amendment A11). Plan this into 2-C.

Parts 2-0A and 2-0B hold the annotation work from plan v1.1 Phase 3. Both need only the parser, so they come first. Aryan annotates contracts 001 to 025 of the Indian set, and that set gates Tanishq's evaluation. The 0 ids keep the 2-A to 2-D references stable.

- [ ] **2-0A** Annotation guidelines
  `docs(docs): add annotation guidelines for the Indian contract set`
  Writes `docs/app/AnnotationGuidelines.md`. It covers the label set (core v2.0 categories, multi-span), span boundary rules, overlap rules, offsets as code points into the parser's `source_text`, worked examples, and every topic plan v1.1 section 4.3 lists: inclusion and exclusion, complete operative spans, overlapping categories, multiple occurrences, cross-references, schedules, definitions, negation, amended provisions, missing clauses, illegible text and disagreement resolution. It separates `absent` from `unassessable` and never labels stamp payment, enforceability or a case outcome from contract text.
  Measure on the Indian contracts (a Phase 1 ceiling, listed under the 1-E ceilings and in `ParserContract.md` 12.6): the Athens-style list. A numbered list inside a section that shares numbers with the section sequence takes those numbers. In the Athens agency agreement a definitions list `1.` to `6.` inside Section 4 took 5 and 6, so Sections 5 and 6 were missed and two false nodes appeared. While annotating contracts 001 to 025, count the files where a numbered list sits inside a section and the section tree comes out wrong (missed or false sections), and note the numbering style of each (typed numbers, a heading word such as `Section 5`, or a Word list). The count decides whether to key the sequences by label style, which would split the two but would open the list items as level 1 nodes unless the rule says more.
- [ ] **2-0B** Offline annotation tool
  `feat(annotator): add offline annotation tool`
  Builds `backend/tools/annotator/`. It runs locally with no network, loads parser output, lets the annotator select spans and exports JSONL with code-point offsets checked against the parser's `source_text` (plan v1.1 section 4.3). `[CONTRACT]` The export schema must match what Tanishq's `ml/` code consumes; agree it with him before this part starts. Needs Phase 1 complete. Any new dependency needs Aryan's approval at the start of the part.
- [ ] **2-A** FastAPI app, config, error envelope, health, readiness, capabilities
  `feat(api): add app with health, readiness and capabilities`
  Capabilities include the scope notice, the catalogue version and every category's support status (plan v1.1).
- [ ] **2-B** RAM store with TTL, SQLite metadata, expiring sessions
  `feat(store): add in-memory document store and expiring sessions`
- [ ] **2-C** Upload validation, parse jobs, document read and delete
  `feat(api): add document upload with validation and parse jobs`
  Open item from Phase 1: time the dense case. An 8 MiB Flate stream of operators and text is the largest stream `MAX_DECODED_CONTENT_BYTES` accepts, and it has not been measured (8 MiB of white space took 0.05 s, BuildLog "Checks before 1-D"). Neither has a DOCX whose `document.xml` approaches 100 MiB, which lxml parses whole before the 500,000 character stop. Measure both on the Phase 2 host. Until then the wall-clock kill is provisionally 120 s, one named constant in the 2-C config. That figure is about twice 0.55 s per page for 100 pages, from one run per file in the 1-C smoke check, so it bounds cost and is not a number a bomb was shown to reach. Re-measure before fixing it.
- [ ] **2-D** Analysis jobs through the core analyzer (stub), progress, cancel, partial results
  `feat(jobs): run analysis jobs through the core analyzer`
  The analysis response carries the scope notice and reports processing completion and decision coverage as separate fields. Cancelled, timed-out or partially parsed work is reported as incomplete, never as absent. No safety or risk-score field (plan v1.1).
- [ ] **2-E** OpenAPI export and API.md
  `docs(api): export OpenAPI schema and document endpoints`
  The frontend mock uses names that plan section 9 does not have: `scope_notice`, `catalogue_version`, `processing_complete`, `decision_coverage {resolved, requested}`, `ReviewUnit`, `ManualReview` and `getManualReview`. 2-E fixes the final names in API.md. The frontend adapter follows API.md, and plan section 9 copies from API.md, not the other way round.
  Party nodes carry a `name_span` (`FrontendDesign.md` 17.7, BR). API.md must define it on a document node of kind `party`, tagged `[CONTRACT]`: `{start, end}` in code points into `source_text`, the same coordinates as the node's own `start` and `end`, inside that range and covering the party's name alone ("ABC Technologies, Inc."), so the frontend never cuts a name at a comma. The parser's output gains the field first (`Architecture.md` section 4). The mock sets it today, and the frontend reads a node with no span as its whole text.
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
  The UI string for `TOO_MUCH_TEXT` is "This file is too large or complex to process". No backend part maps error codes to UI messages, so this first frontend integration part checks that the UI shows it.
  The swap to the HTTP adapter removes the mock adapter and the sample contract, and the part checks that `dist` holds no mock: no `mock-*` chunk, no sample contract text and no `example.org`. The build is not releasable on the mock until then (`Architecture.md` 7.1, `FrontendDesign.md` 17.7 BW).
- [ ] **4-R** Phase review, then root docs and README merge (coordinated with Tanishq)

---

## Frontend track

The frontend track edits `frontend/`, `docs/app/` and `README.md`, never `backend/`, so it runs beside the backend without collisions. The app runs on the mock adapter in `src/api/client.ts` until the backend API exists. The one-line swap to an HTTP adapter happens at 4-C, and the adapter follows API.md (2-E fixes the final type names).

Phase 4 has no frontend parts of its own, so no FE part maps onto it. 4-C is the first run of the real client, and it checks the `TOO_MUCH_TEXT` message in the UI.

Part ids and commit messages are suggestions, like the backend parts. Every part ends with `/ponytail:ponytail-review` and stops for review.

- [x] **FE-0** Import the baseline frontend
  `chore(frontend): import baseline frontend`
  The delivered frontend runs inside the repo as received. Only build config, the HTML shell and package metadata changed. No UI change.
- [x] **FE-1** Design direction (docs only)
  `docs(frontend): add frontend design direction`
  Audit of every route at every width and theme, the final information architecture, section-by-section composition, type, spacing and motion tokens, copy plan, trust and conversion map, skills table and dependency requests. Includes the font self-hosting proposal: the fonts load from Google, which contradicts the privacy promise. Written to `FrontendDesign.md`, then reviewed with the plan design review (amendments A to L in its section 17.1). Stops for review before any UI code changes: FE-2 starts after decisions D1 to D6 in section 15 are answered. Deviations from the brief are listed in section 16 of that file.
- [x] **FE-2** Foundations
  `feat(frontend): add motion tokens, layout primitives and 404 route`
  Motion and type tokens, the colour changes, layout primitives, the reveal hook (tests first), route transitions and titles, `NotFound` and error pages, the dev-only gallery and preview controls, the favicon and 44 px hit areas, and self-hosted fonts. Scope and acceptance: `FrontendDesign.md` section 14. Decisions D1 to D13 and the amendments are in section 17.2 of that file.
  Deviations: the layout primitives are one file, `components/Layout.tsx`, not a `layout/` folder. The baseline `Link` never navigated and was fixed. The fonts are the Latin subset. The ink-in keyframes wait for FE-3, the header restructure for FE-4, the footer Credits link for FE-6, and the Reader items (squeezed category names, the ruler, drawer focus) for FE-5. The full list with owners is in `FrontendDesign.md` 17.2.
- [x] **FE-3** Landing
  `feat(frontend): rebuild landing with live hero demo`
  The landing page at `/`: the hero with its live demo (three examples from a typed fixture that a test checks against the sample contract), the problem, three steps beside real component fragments, the lawyer section, the 46 categories, privacy, questions and a closing call to action. The Evidence section is built and stays out of the build until a verified passage exists (D7). The ink-in, the Latin-extended fonts and the `Button` link form land here. Scope and acceptance: `FrontendDesign.md` section 14. Amendments U to Z are in 17.3.
  Deviations: an interim `/start` page ships here, the baseline form moved out of `Home`, so the buttons have a destination, and FE-4 rebuilds it. The hero ruler is hidden below 640 px. LCP is not measured in this part, because the capture run was blocked, so it moves to the FE-R measurements unless it is rerun first. The heading "Nothing is kept after your session" was open for Aryan to confirm and became "Your contract is deleted within 60 minutes." at the start of FE-4 (17.4, AA).
- [x] **FE-4** The `/start` stepped flow
  `feat(frontend): add stepped review start flow`
  `/start` is three steps, one decision each: upload the contract, say which side you are, confirm the scope. The step lives in `?step=`. The flow state is a pure reducer written test first (17 tests). Role and party are native radio groups with nothing preselected, and "None of these" is the last party option. The four upload refusals show inline. The header gains the primary "Review a contract" button, hidden on `/start` and in the Reader. The summary rail shows from 1280 px. Scope and acceptance: `FrontendDesign.md` section 14. Amendments AA to AO are in 17.4.
  Deviations: the step is not in the reducer state, because a copy there and a copy in the address raced on browser Back (AD). The rail starts at 1280 px and has no Change link (AE). The carry-over fixes from FE-3 landed here: the privacy heading, the hero panel at full width from 768 to 1279 px, and the judgment card's authority label (AA to AC). A loading `Button` now ignores clicks, after "Start review" called the analysis once per click (AK). The end of the part added the meta description wording, a 66ch cap on the hero subline, a Fail parse switch in the Preview controls, the copy passes and a second ponytail-review (AL to AO). Still open: LCP and CLS for `/` (FE-R), and whether the hero sheet and quote get a cap too (Aryan).
- [x] **FE-5** Reader composition and motion
  `refactor(frontend): recompose reader with motion`
  The Reader sits on one 710 px sheet whose text column is the `--measure` token, 612 px, and a full line averages 73 characters from 1024 to 1920 px. The category list is docked from 1440 px, a 64 px rail from 1280, and below that the panel is a bottom sheet and the list a left drawer. A pointer pick cross-fades the panel, a J or K step does not. The margin ruler is a strip you can click. A band above the sheet carries progress with Cancel, a partial-read notice or the zero-findings line. A 500,000 code point document scrolls and picks with no main-thread task over 200 ms, by memoisation and no windowing. Scope and acceptance: `FrontendDesign.md` section 14. Amendments AP to BA are in 17.5.
  Deviations: the panel is a bottom sheet below 1280 px and not a right drawer (AS). Only a pointer pick cross-fades (AT), and the root is out of that transition (AU). The sheet header carries only Peek or Open (AS). The judgment card's words are interim and wait for a definition of `authority_status` (AP), and so does the partial-read notice for the parser codes (AQ). The hero sheet is capped by the same measure token (AR). Still open: LCP and CLS for `/` (FE-R), the authority wording (Tanishq, Aryan), the 4 px rule on three components (FE-6).
- [x] **FE-6** How it works, Accuracy, Expired, NotFound
  `refactor(frontend): rebuild secondary pages`
  How it works, Accuracy, Expired and NotFound sit on the margin grid. How it works has a sticky contents list in the margin and real components beside the text, and the footer's Credits link opens the Credits section. Accuracy shows an example banner under the notice, a sticky header from 768 px and a stacked block per category below it. Expired and NotFound share one plain page. The delete confirmation, the menu and the toast enter with the existing motion tokens, and the plain status text is contrast tested on the sunken and selected rows (53 tests).
  Deviations: the Accuracy table stays in the main column and the aside holds the glossary (BD). The Credits link target is `?at=credits` and not router state (BE). The menu enters over `--dur-press`, 120 ms and not 150 (BC). Expired drops its dashed card (BF). Closed with no change: tabular numerals on metric cells, which are already mono (BH). Still open: LCP and CLS for `/` (FE-R), the authority wording (Tanishq, then Aryan) and the parser warning codes (2-E).
- [x] **FE-R** Phase-end review
  `fix(frontend): close keyboard findings from the final sweep` is the last of eight step 2 commits. Step 1 reviewed `1077d25..f24d382` (R1 to R22) and every P1 is fixed. The quality bars are measured, in the BuildLog entry of 2026-10-15: `/` scores 96 to 97 with an LCP of 2.17 to 2.26 s, axe reports no violation in 154 captures, and the keyboard run found four defects (S1, S3, S3b, S4), fixed in code. Open and listed in `FrontendDesign.md` 17.7: LCP over 2.5 s on `/start` and `/accuracy`, the mock in the build (4-C) and the authority wording. `/coderabbit:code-review` did not run and Aryan accepted it as not run.

Standing constraints, the checks every FE part runs and the quality bars: `docs/app/FrontendDesign.md`, section 1.
