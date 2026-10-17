# Parser Contract

The exact output of the parser, for the analysis core and the annotation tool. This file replaces every earlier contract message. If it disagrees with one of them, this file is right.

`parser_version` is `1.0.0`. Code: `backend/app/parsing/`. The machine form of the output is `docs/app/parser_output.schema.json`, and a test keeps it equal to `app/parsing/schema.py`.

## 1. How to read this file

Entry point: `parse_document(data: bytes) -> ParsedDocument`. It either returns a document or raises `ParseError`, whose `code` is one of the error codes in section 9. A rejected file returns no document.

The **Since** column and the tags in the text compare each item with the first message (30 September, nine points) and with the original spec it refined (`Architecture.md` section 4 and the Phase 1 handoff). Every item tagged `refined` or `new` is a change since the first message.

| Tag | Meaning |
|---|---|
| same | Stated in the first message or the original spec, and not changed since |
| refined | Stated there, and since made more exact or changed |
| new | Not stated before |

Where the first message's nine points went:

| Point | Topic | Now in |
|---|---|---|
| 1 | Normalisation and the two PDF exceptions | 3.3 |
| 2 | Decorations and page numbers | 5 |
| 3 | `coverage.partial` | 6 |
| 4 | 8 MiB decode budget, `TOO_MUCH_TEXT` | 9 and 11 |
| 5 | Tracked changes | 9 |
| 6 | DOCX wrappers and text boxes | 3.4, 4.3 and 10 |
| 7 | DOCX locators | 4.3 |
| 8 | Structure levels | 7 |
| 9 | Node ranges across page breaks | 7.2 |

One item is not built yet: `name_span` on party nodes (section 8).

## 2. The document

```python
@dataclass(frozen=True, slots=True)
class ParsedDocument:
    source_text: str
    text_sha256: str          # sha256 of source_text.encode("utf-8"), lowercase hex
    parser_version: str       # "1.0.0"
    media_type: str           # "application/pdf" or the DOCX type below
    page_count: int | None    # None for DOCX
    blocks: tuple[Block, ...]
    nodes: tuple[StructureNode, ...]
    decorations: tuple[tuple[int, int], ...]
    warnings: tuple[ParseWarning, ...]
    coverage: Coverage
```

The DOCX media type is `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.

| Field | Meaning | Since |
|---|---|---|
| `source_text` | The one canonical text. Every offset points into it | same |
| `blocks` | Every text block in reading order (section 4) | same |
| `nodes` | The clause tree (section 7). Built after the blocks, from them alone | same |
| `decorations` | `[start, end]` of every header and footer block (section 5) | same |
| `warnings` | What the parser had to guess or could not read (section 10). Reader warnings first, then structure warnings | refined |
| `coverage` | Section 6 | same |

JSON form: `to_json` in `app/parsing/schema.py` turns a document into plain data with the same field names. Tuples become arrays and `bbox` is an array of four numbers or `null`. The command line `python -m app.scripts.parse_file FILE [--text] [--summary]` prints it. By default it leaves out `source_text`, `blocks[].text` and `nodes[].text`. It also leaves out every block's `locator.list_label` and sets the `label` of every `definition` node to `null`, because both hold words from the file (a numbering level can say anything, and a defined term is often a party or product name). The other node labels (`1.1`, `(a)`, `ARTICLE I`) follow a fixed grammar and stay. A result can then be shared without the contract. `--text` keeps all of it, and `to_json(doc, text=False)` does the same as the default. A file over 10 MiB is refused with `FILE_TOO_LARGE` before it is read. A rejected file prints its code to stderr and exits with status 2. Every offset is present either way. **new**

## 3. Text and offsets

### 3.1 Offsets

| Rule | Since |
|---|---|
| Offsets are Unicode code points into `source_text`, zero-based, `end` exclusive. `source_text[start:end]` is the text of any block, node or decoration | same |
| `text_sha256` is the SHA-256 of `source_text` encoded as UTF-8 | same |
| `source_text` has at most 500,000 code points, separators included | same |
| A lone surrogate makes the file `MALFORMED_FILE`, because the text cannot be hashed | new |

The assembler assigns offsets while it appends text and never searches for them afterwards. A browser consumer converts code points to UTF-16 itself.

### 3.2 Separators

| Between | Separator | Since |
|---|---|---|
| Lines inside a block | `\n` | same |
| Blocks | `\n` | same |
| A block and the first block of a later page (PDF) | `\n\n` | same |

A page that holds no block leaves no mark, so two empty pages do not add `\n\n` twice and a blank page adds none. A DOCX has no pages and no `\n\n`. Page boundaries are in `Block.page`, not in the text. **new**

Before a line is appended, trailing spaces and tabs are removed, and CRLF and CR become LF. No other character is touched: form feed, U+2028 and the like stay. **same**

### 3.3 No normalisation

Nothing is normalised: no NFC or NFKC, no dehyphenation (`agree-` then a newline then `ment` stays that way), no ligature expansion (U+FB01 stays one character), and smart quotes arrive as they are. If the core normalises, it maps its offsets back to this text. **same**

The readers change the text in three ways, and in no others:

| Effect | Since |
|---|---|
| PDF: a run of spaces becomes one space | same |
| PDF: U+00A0 arrives as U+0020 | same |
| DOCX: `w:noBreakHyphen` arrives as ASCII `-` | new |

DOCX keeps U+00A0 and runs of spaces. **same**

### 3.4 What the DOCX reader puts in the text

| Source | Becomes | Since |
|---|---|---|
| `w:t` | its text | same |
| `w:tab`, `w:ptab` | `\t` | new |
| `w:cr`, and `w:br` of type text wrapping | `\n` | new |
| `w:br` of type page or column | nothing, so the words on either side fuse | new |
| A field's result | its text. The field instruction (`w:instrText`) is not read | new |
| Text inside `sdt`, `smartTag`, `fldSimple`, `customXml` and `hyperlink` | its text, in document order | refined |
| Text inside a text box (outside `mc:Fallback`) | blocks right after the anchor paragraph (4.3) | refined |
| A paragraph with no text, or only white space | no block. It still counts in `paragraph` numbers | new |
| A Word list label (`1.`, `(a)`) | not in the text. It is in the block's `list_label` | new |
| Tracked changes in any part | the file is rejected (section 9) | same |

## 4. Blocks

```python
@dataclass(frozen=True, slots=True)
class Block:
    id: str                    # "b0001", "b0002" ... in reading order
    kind: str                  # text, table_cell, header, footer, footnote
    start: int
    end: int
    text: str                  # source_text[start:end]
    page: int | None           # 1-based for PDF, None for DOCX
    bbox: tuple[float, float, float, float] | None   # PDF only
    locator: Mapping[str, int | str]
```

Blocks come in increasing `start` order and never overlap. The text between two blocks is a separator and nothing else. A block is never empty.

### 4.1 Kinds

| Kind | Where | Since |
|---|---|---|
| `text` | PDF body text, DOCX body paragraph, text box paragraph in the body | same |
| `table_cell` | DOCX body table cell | same |
| `header`, `footer` | PDF margin line that is decoration. DOCX header and footer parts, tables and text boxes inside them included | refined |
| `footnote` | DOCX footnote and endnote paragraphs | same |

A PDF margin line that is not decoration has kind `text`.

### 4.2 Order

PDF, per page: the top margin lines (each its own block), the body blocks in reading order, then the bottom margin lines. One gutter gives bands: lines that cross it stand alone, and each run of column rows reads the left column and then the right. Two or more gutters keep row order. **new**

DOCX: the body in document order (tables row by row and cell by cell, a text box right after its anchor paragraph), then for each section its headers (default, first, even) and footers, then footnotes, then endnotes. **refined**

### 4.3 Locators and boxes

Every number is 1-based. `bbox` is `(x0, top, x1, bottom)` in points from the top left of the page. DOCX blocks have `page` and `bbox` set to `None`.

| Block | Locator | Since |
|---|---|---|
| PDF | `{"page": n, "block": i}`. `i` counts blocks within the page, margin lines included | refined |
| DOCX body paragraph | `{"part": "document", "paragraph": i}`. `i` counts every body-level paragraph, empty ones included | refined |
| DOCX text box paragraph | `{"part": "document", "textbox": n, "paragraph": i}`. `n` counts text boxes in preorder (an outer box before the box inside it), `i` the paragraphs of that box | refined |
| DOCX table cell | `{"part": "document", "table": t, "row": r, "cell": c, "segment": k}`. `t` is the preorder index across all tables, nested ones included. `k` counts the blocks of one cell | refined |
| Header or footer | `{"part": "header" or "footer", "section": s, "variant": "default" or "first" or "even", "paragraph": i}`. A table or text box inside adds the keys above, numbered from 1 within that part | refined |
| Footnote or endnote | `{"part": "footnotes" or "endnotes", "id": n, "paragraph": i}`. `n` is the note's `w:id`, a number of up to nine digits. A table or text box inside adds the keys above | refined |

`list_label` **new**: the locator of a numbered DOCX paragraph also holds `"list_label"`, the rendered label as text, such as `1.`, `1.1`, `(a)`, `(ii)` or `ARTICLE I`. The key is absent when the paragraph is not numbered, when its number cannot be worked out, and for bullets and `none` formats. It is never in `source_text`. The structure builder reads it (7.3).

Cells and merges **new**:

- A cell is one block of kind `table_cell`, its paragraphs joined with `\n`. An empty cell makes no block.
- A nested table or a text box ends the block. The text after it starts the next block of the same cell, with `segment` one higher. The key `segment` is always present.
- A merged cell is one cell and is not marked.
- A cell block that holds several paragraphs carries no `list_label`, and the reader raises `NUMBERING_NOT_RENDERED`.

Page parts **refined**: a header or footer part that several sections name is read once. A part whose text equals an earlier part of the same kind is dropped. Only the variants a section names are read. Word's separator and continuation notes are skipped.

## 5. Decorations

`decorations` lists `[start, end]` for every block of kind `header` or `footer`, in block order. The text stays in `source_text`, so offsets never shift. **same**

How to treat them: they are page furniture and not clause text. Mask them when you read the text of a node, a span or a window. A node that spans a page break contains the furniture of that break (7.2). Footnotes are not decorations. **refined**

PDF rules **refined**:

| Rule | Since |
|---|---|
| A line is a candidate when its vertical middle sits in the top or bottom 8 percent of the page | new |
| A page number is also a candidate when it is the first or last row of the page, wherever it sits. This catches a page whose text stops half way down | refined |
| A page-number-shaped candidate is decoration at any page count, a one-page file included. Shapes: `3`, `Page 3`, `Page 3 of 10`, `3/10`, `- 3 -`, one to three digits, a hyphen, en dash or em dash | refined |
| Any other candidate is decoration when the same line (compared in lowercase, each digit read as `#`) recurs in the same zone on at least 3 pages and at least half the pages, rounded up | new |
| A margin line that is neither number-shaped nor repeated keeps kind `text` | new |
| Each candidate is a block of its own, so furniture never fuses with body text | new |

DOCX: header and footer parts are always decoration. Their tables and text boxes are too. **new**

## 6. Coverage and partial

| Field | Meaning | Since |
|---|---|---|
| `pages_total` | PDF page count. None for DOCX | same |
| `pages_with_text` | Pages that hold at least one block, leaving out scanned pages (their only blocks are margin stamps). None for DOCX | new |
| `chars` | `len(source_text)` | same |
| `partial` | True when content may be missing from `source_text` | refined |

`partial` is True when:

| Condition | Warning | Since |
|---|---|---|
| A PDF page is scanned: image-dominant (images cover more than half the page) with fewer than 20 characters outside the margin zones | `PARTIALLY_SCANNED_PDF`, once per such page | refined |
| An image-dominant PDF page has 20 to 199 characters outside the margins (a searchable scan) | none | refined |
| A PDF Widget or FreeText annotation holds non-blank text (`/Contents` or `/V`) | none | refined |
| More than 25 percent of a PDF page's glyphs have no text mapping (10) | `UNMAPPED_GLYPHS`, once per such page | new |
| A DOCX paragraph holds an embedded object (`w:object`) | `EMBEDDED_OBJECT` | refined |
| A DOCX block-level child the reader does not know, `altChunk` included | `UNSUPPORTED_DOCX_FEATURE` | refined |

**Rule for the core:** when `partial` is True, never report "not found" for this file. Report "not checked". Text boxes do not set `partial`, because their text is read.

`partial = False` leaves cases open. Section 12 lists what the parser cannot see and does not mark.

## 7. Structure tree

```python
@dataclass(frozen=True, slots=True)
class StructureNode:
    id: str                 # "n0001", "n0002" ...
    parent_id: str | None
    kind: str               # heading, section, clause, subclause, schedule, definition, table
    label: str | None
    level: int              # 1-based
    start: int
    end: int
    text: str               # source_text[start:end]
```

The tree is built from block text and block offsets only. It reads blocks of kind `text` and `table_cell`. A header, footer or footnote block never opens a node and never extends one, and no definition is found in them. **new**

### 7.1 Fields

| Field | Rule | Since |
|---|---|---|
| `id` | Nodes come in order of `start`, then `level`, and the ids follow that order. A container comes before what it holds | same |
| `parent_id` | The node that holds this one, or None. A parent starts no later than its child, ends no earlier, and has a lower `level` | same |
| `kind` | Which label gets which kind is below | new |
| `label` | The label without its trailing full stop: `1`, `1.1`, `(a)`, `(ii)`, `ARTICLE I`, `Section 2.1`, `SCHEDULE 2`. A definition's label is its term without the quotes. An unnumbered heading and a table have None | new |
| `level` | 7.4 | refined |
| `start`, `end` | 7.2 | refined |

Kinds **new**:

| Kind | Given to |
|---|---|
| `section` | A bare decimal label at level 1 (`1.`) |
| `clause` | A bare decimal or letter label at level 2 (`1.1`) |
| `subclause` | A bare decimal, letter or numeral label at level 3 or deeper |
| `heading` | `ARTICLE`, `SECTION` and `CLAUSE` labels, a bare roman heading (`IV.`), and an unnumbered all-capitals line |
| `schedule` | `SCHEDULE`, `ANNEXURE`, `APPENDIX` and `EXHIBIT` followed by a number, a roman numeral or one capital letter |
| `definition` | A quoted defined term (7.7) |
| `table` | A DOCX table (7.8) |

### 7.2 Ranges

A node starts at the start of the block where its label sits, and ends at the end of the last body block it covers. A definition spans its quoted term with both quotes. **refined**

A node that spans a page break holds the header and footer text between its blocks, because those blocks sit between the body blocks. Mask the ranges in `decorations` when you read node text. Header, footer and footnote blocks never extend a node, so the furniture after the last body block is outside it. **same**

### 7.3 Which labels count

A label is read at the start of a block, or from the block's `list_label`, which wins over the typed text. **new**

| Form | Grammar | Since |
|---|---|---|
| Decimal | One to five parts of one to three digits: `1`, `1.1`, `1.1.1`. A full stop may follow. The title may run straight on (`10.Title`) | new |
| Heading word | `ARTICLE`, `SECTION` or `CLAUSE` plus a number or a roman numeral. `ARTICLE` takes a single number or a roman numeral | new |
| Schedule word | `SCHEDULE`, `ANNEXURE`, `APPENDIX` or `EXHIBIT` plus one to three digits, a roman numeral or one capital letter | new |
| Roman heading | `I.`, `IV.` and the like at the start of a block | new |
| Letter | `(a)` to `(z)`, then `(aa)`, `(bb)` and on, as Word numbers them | new |
| Numeral | `(i)`, `(ii)`, `(iv)` and the like | new |

A heading word with a lower case word after it on the same line is running text (`Section 3 of this Agreement`). A typed article, schedule or roman heading counts only when its first line has 80 characters or fewer. **new**

### 7.4 Acceptance and levels

A label becomes a node only when it continues its sequence or starts one. Otherwise it stays body text, so a number in running text, a cross reference or a stray line does not become a clause. **refined**

| Rule | Since |
|---|---|
| A label **continues** when it is one more than the last accepted number in its sequence. Decimals are sequenced by their prefix (`1.` and `2.` together, `1.1` and `1.2` together). Letters and numerals are sequenced by the node they sit under | refined |
| A label **starts** a sequence at 1, `(a)` or `(i)` | refined |
| A restart at 1 replaces a run of 3 or fewer (a party or recital list before the clauses). After a longer run it is body text (a list inside a clause) | new |
| A decimal under an open decimal of the same depth must carry that decimal's number. `2.1` after an open `1.` is body text | new |
| A schedule label clears every sequence, because a schedule numbers from 1 | new |
| A typed number never skips ahead. After `1.` and `2.`, a typed `4.` is body text | new |

Levels **refined**:

| Label | Level |
|---|---|
| Decimal | Its number of parts, plus 1 while a schedule is open |
| `ARTICLE`, roman heading | 1 |
| `SECTION`, `CLAUSE` with a decimal | Its number of parts |
| Schedule word | 1 |
| Letter | One below the nearest open decimal node, else one below the nearest open node that is not a letter or numeral, else 1 |
| Numeral | One below the nearest open letter, else one below the nearest open node that is not a numeral, else 1 |
| Unnumbered all-capitals line | 1. It closes every open node |
| Definition | One below the innermost open node, or below the table it sits in |
| Table | One below the innermost open node |

`(i)`, `(v)`, `(x)`, `(c)`, `(d)`, `(l)` and `(m)` can be a letter or a numeral. `(i)` is a letter when it continues the letters and a numeral when it starts a run under a letter. When both readings continue a sequence it is a letter, and the parser adds `NUMBERING_AMBIGUOUS` once per page. **new**

### 7.5 Word lists

| Rule | Since |
|---|---|
| A Word label goes through the same grammar as typed text and wins over it | new |
| **A Word list may open a top-level decimal above 1.** Word counts empty numbered paragraphs, and the reader leaves them out of the blocks. Typed numbers still open at 1. Only a top-level decimal may open high: `(c)`, `2.3`, `ARTICLE III` and `SCHEDULE 2` may not | new |
| **A Word label above the last number in its sequence continues it**, whatever its form (1-F). An empty numbered paragraph in the middle of a list leaves a gap in the blocks, and the rest of the list is read. It ranks below a plain continuation and below a start, so `(i)` after `(a)` and `(b)` is still a numeral. A letter does not reach the next width (`(aa)`, `(bb)`) by a gap, because that skips the rest of the alphabet: `(ii)` after `(i)` is not the 35th letter. The gap counts as part of the run | new |

### 7.6 Headings in capitals, titles and contents lines

| Rule | Since |
|---|---|
| **Capitals heading.** A block is an unnumbered heading when it has 80 characters or fewer, at least 3 letters, and every line is at least 60 percent capitals. The test is per line, so a mixed case line with redaction marks under it is not a heading. A heading opens at level 1 and closes every open node | new |
| **Title.** An all-capitals block straight after a block that is only a label (`ARTICLE 5`, `SCHEDULE A`, `1.`) is that label's title. It opens no heading, so the label's node stays open and keeps the clauses that follow. A title in title case is already part of the node | new |
| **Contents line.** A block is a contents entry, and ignored, when it holds a dot leader anywhere (four or more full stops, with or without a space between them, or an ellipsis character), or when it is one line and the text after its label ends in a space or a tab and one to three digits. A year has four digits, so a clause that ends in one is a clause. A capitals line goes through the same test before it becomes a heading | new |
| **Bare number.** A typed decimal whose first line is the number alone, with no full stop and no title, is ignored. It is a page number. `3.` with its full stop is a label | new |

### 7.7 Definitions

A defined term is a `definition` node that spans the quoted term with both quotes, sits one level below the innermost open node (or below the table), and has the term as its label. **new**

| Rule | Since |
|---|---|
| Quotes are straight or curly. The term has 1 to 80 characters and may wrap a line | new |
| Forms: `"T" means`, `shall mean`, `has the meaning`, `have the meaning`, `shall have the meaning`, `refers to`, and `(the "T")` or `("T")` | new |
| The label drops trailing `,`, `.` and `;` and collapses white space | new |
| An empty or space-padded term is not a definition, and neither is a quoted phrase with none of these forms around it | new |

### 7.8 Tables

Each outermost DOCX table is one `table` node, one level below its container. A nested table has no node. Labels and headings are not read inside a cell, so a table is a leaf for labels. A definition in a cell is a child of the table node. PDFs have no table nodes. **new**

## 8. Party nodes and `name_span`

**Status: required, not built.**

The frontend lists the parties of a contract and must never cut a name at a comma, so the parser decides where a name ends (`FrontendDesign.md` 17.7, BR). The requirement:

- `StructureNode.kind` gains the value `party`.
- Every node of kind `party` carries `name_span`: `{"start": int, "end": int}` in code points into `source_text`, in the same coordinates as the node's own `start` and `end`.
- `name_span` lies inside the node's range and covers the party's name alone (`ABC Technologies, Inc.`), not the defining phrase around it (`(the "Supplier")`).
- A party node with no span reads as its whole text.

Today `StructureNode` has no `party` kind and no `name_span` field, and the JSON Schema has neither. API.md defines the field on the document node and tags it `[CONTRACT]` (`Phases.md`, 2-E). The parser gains it first. Send back any change to the shape before then.

## 9. Errors

A rejected file raises `ParseError`. Its message is the code alone, so no document text leaks through it. The codes are the ones in `errors.py`, unchanged since the first message except that `PARTIALLY_SCANNED_PDF` moved to the warning list.

| Code | Raised when | Since |
|---|---|---|
| `EMPTY_FILE` | The input has no bytes | same |
| `FILE_TOO_LARGE` | The input is over 10 MiB | same |
| `UNSUPPORTED_TYPE` | The file is not a PDF (`%PDF-`) and not a ZIP that holds `word/document.xml`. A macro-enabled document (`word/vbaProject.bin`) and an encrypted DOCX end here too | refined |
| `MALFORMED_FILE` | A library could not read the file: a damaged PDF, an unreadable archive, a package python-docx cannot open (strict OOXML, a template), XML nested deeper than 256 levels, a lone surrogate in the text, a DOCX part that has a DOCTYPE, a footnote or endnote whose `w:id` is missing, signed or longer than nine digits | refined |
| `ENCRYPTED_PDF` | A PDF needs a password to open. An owner-password file that opens without one parses | refined |
| `SCANNED_PDF` | Every page that has content is scanned. A blank page does not count | refined |
| `TOO_MANY_PAGES` | A PDF has more than 100 pages. Checked before any text is read | same |
| `TOO_MUCH_TEXT` | The decoded page content passes 8 MiB (PDF), or a PDF content stream names more than one filter that can grow the data (Flate, LZW or RunLength), whatever it holds, or a DOCX holds more than 100,000 paragraphs, empty ones included, or the text passes 500,000 code points (PDF and DOCX) | refined |
| `ARCHIVE_TOO_LARGE` | The members of a DOCX archive inflate to more than 100 MiB. The parser counts the bytes it reads, and stops at the limit | refined |
| `ARCHIVE_UNSAFE` | A member name is absolute, has a drive letter or has a `..` segment, after backslashes become slashes. Or a member uses a compression method other than stored or Flate | refined |
| `TRACKED_CHANGES_PRESENT` | `ins`, `del`, `moveFrom` or `moveTo` appears in the document, a header, a footer, the footnotes or the endnotes, in any element position. The user accepts all changes and uploads again | refined |
| `NO_TEXT_FOUND` | The file parses and holds no text, such as an all-blank PDF | same |

## 10. Warnings

A warning is `ParseWarning(code, page, detail)`. `page` is a 1-based PDF page or None. `detail` is a short fixed string, never document text. The file is parsed. Reader warnings come first, in the order the reader met them (PDF pages in order), then the structure builder's.

| Code | When | `page` | `detail` | Sets `partial` | Since |
|---|---|---|---|---|---|
| `COLUMN_ORDER_UNCERTAIN` | A PDF line that crosses a gutter sits between two runs of column rows, so the order around it is a guess. A full-width title above the columns or a full-width line below them does not trigger it | the page, once per page | None | no | refined |
| `MORE_THAN_TWO_COLUMNS` | A PDF page has two or more gutters and keeps row order | the page | None | no | same |
| `BLANK_PAGE` | A PDF page holds neither text nor an image | the page | None | no | same |
| `PARTIALLY_SCANNED_PDF` | A PDF page is scanned and the file has other pages with content. It was an error code in the original spec | the page, once per scanned page | None | yes | refined |
| `UNMAPPED_GLYPHS` | More than 25 percent of a PDF page's glyphs have no text mapping, because the font carries no Unicode map. Each such glyph stays in `source_text` as `(cid:` and its number and `)`, for example `(cid:65)`, and counts as one glyph, not eight characters. The share is counted over all the page's words, margins included. A file whose every page is like this still parses | the page, once per page | None | yes | new |
| `NUMBERING_AMBIGUOUS` | A numeral that continues both as a letter and as a numeral (7.4) | the block's page, once per page | None | no | refined |
| `NUMBERING_NOT_RENDERED` | A DOCX list number could not be worked out: a missing or unreadable numbering definition, a number format other than decimal, letters and roman numerals, a value over a bound, or a cell block that joins several numbered paragraphs | None | None | no | refined |
| `TEXT_BOX_CONTENT` | A DOCX holds a text box outside `mc:Fallback`. Informational: the text is read | None | None | no | refined |
| `EMBEDDED_OBJECT` | A DOCX paragraph holds `w:object`. The object's content is not read | None | None | yes | refined |
| `UNSUPPORTED_DOCX_FEATURE` | A DOCX block-level child the reader does not know was skipped | None | `altChunk` or `unknown_block` | yes | refined |

`TEXT_BOX_CONTENT`, `EMBEDDED_OBJECT`, `NUMBERING_NOT_RENDERED` and each `UNSUPPORTED_DOCX_FEATURE` detail appear once per document.

## 11. Limits

| Limit | Value | Error | Since |
|---|---|---|---|
| Input size | 10 MiB | `FILE_TOO_LARGE` | same |
| PDF pages | 100 | `TOO_MANY_PAGES` | same |
| Decoded PDF page content, content streams and Form XObjects, each stream counted once | 8 MiB, decoded incrementally and aborted as soon as the total passes. A stream with more than one growing filter (for example Flate twice) counts as over the limit without being decoded | `TOO_MUCH_TEXT` | refined |
| Text | 500,000 code points | `TOO_MUCH_TEXT` | same |
| DOCX paragraphs, every part together, empty ones included | 100,000 | `TOO_MUCH_TEXT` | new |
| DOCX archive, total uncompressed size, counted as the members are read | 100 MiB | `ARCHIVE_TOO_LARGE` | refined |

The budget bounds size, not time. The API runs each parse in a child process with a wall-clock kill (Phase 2, part 2-C).

## 12. Ceilings: what the parser cannot see or fix

The first message listed no ceilings, so this whole section is new. The last column says whether anything in the output marks the case.

### 12.1 Content the parser does not read

| Case | Marked |
|---|---|
| Text drawn as vector outlines, and scanned content in a file that also has real text. There is no OCR | A scanned page: `PARTIALLY_SCANNED_PDF` and `partial`. Outlined text: no |
| PDF form fields and annotations. A Widget or FreeText annotation with text sets `partial`. Other annotation types, and a value held only on a parent field, are not checked | `partial` for the first kind only |
| DOCX inline math, chart text, SmartArt text and comments | No |
| DOCX block-level math (`m:oMathPara`) and other unknown block children | `UNSUPPORTED_DOCX_FEATURE` and `partial` |
| A DOCX part that no relationship reaches | No |
| DOCX symbol characters (`w:sym`) and footnote reference marks add nothing, so a note's text carries no marker back to its place in the body | No |
| A text box is read at its anchor paragraph, not by where it sits on the page | No |
| Rotated PDF pages are not supported. Reading order and block boundaries there are not reliable | No |

### 12.2 Text effects

| Case | Marked |
|---|---|
| A DOCX page or column break adds nothing, so the words on either side fuse (`before` and `after` become `beforeafter`) | No |
| `w:noBreakHyphen` becomes ASCII `-` | No (listed in 3.3) |
| PDF space runs collapse and U+00A0 becomes U+0020 | No (listed in 3.3) |
| Up to 25 percent of a PDF page's glyphs can have no text mapping. Each shows in `source_text` as `(cid:N)`, with no warning | No |

### 12.3 PDF reading order and blocks

| Case | Marked |
|---|---|
| **Fused unspaced paragraphs.** Paragraphs with no spacing, no numbering and no indent fuse into one block per page. Nothing in the geometry separates them. Offsets stay exact, so only the block and the node that starts in it are coarser | No |
| First-line indents with no paragraph spacing and no numbering put block boundaries one line late | No |
| A page that fills its margins breaks one paragraph into several blocks | No |
| A two-column table is read as two columns, because its geometry matches a two-column page. Tables with three or more columns read row by row | The second only: `MORE_THAN_TWO_COLUMNS` |
| Three or more columns of running text read across | `MORE_THAN_TWO_COLUMNS` |
| A bare number that is the first or last row of a page is decoration, even when it is a table cell or a list marker on its own line | No |
| A page number on a line with other text (`Agreement 12`) is decoration only when the line repeats on enough pages | No |
| Overlapping images count twice toward the image share | No |
| A file with a broken page tree and no pages reports `NO_TEXT_FOUND` | Yes, by the error |

### 12.4 Safety limits

| Case | Marked |
|---|---|
| Only Flate streams are measured, behind any leading ASCII85 or ASCIIHex filter. A stream whose only growing filter is LZW or RunLength counts its stored length. Font programs, ToUnicode maps and object streams are not budgeted | No |
| The budget bounds size and not time. A 16 KB file that decodes to 16 MB took 186 s. The Phase 2 child process kill is the real bound | No |
| A DOCX part is parsed in full before the paragraph limit applies, so a large part costs memory: a 12 MB part of empty paragraphs took 279 MiB, which is about 2.3 GB for a 100 MiB part (computed). The Phase 2 child process memory cap is the bound | No |
| An owner-password PDF parses. The parser does not enforce usage permissions | No |
| An encrypted DOCX reports `UNSUPPORTED_TYPE`, not `ENCRYPTED_PDF`, because it is not a ZIP | Yes, by the error |
| A chain of 3,000 nested Form XObjects makes pdfminer fail, and the file is `MALFORMED_FILE` | Yes, by the error |

### 12.5 DOCX numbering

| Case | Marked |
|---|---|
| Word's finer restart rules inside one list are not modelled: a level override with no start override, and a restart in the middle of a list. A label can be wrong | No |
| A level named only through a style whose numbering has no level reads as level 0 | No |
| A numbered list in a header continues the body's count, because the counters are shared | No |
| Formats other than decimal, letters and roman (ordinal, cardinal text, leading zero, non-Latin scripts) give no label | `NUMBERING_NOT_RENDERED` |

### 12.6 Structure tree

These are the cases where the tree is wrong or coarse and offsets are still exact. No warning marks any of them.

| Case | Effect |
|---|---|
| **Athens-style lists.** A numbered list inside a section that shares numbers with the section sequence takes them. In one agency agreement a definitions list `1.` to `6.` inside Section 4 took 5 and 6, so Sections 5 and 6 are missed and two false nodes `5` and `6` appear. A Part A and a Part B pair that restarts after a long run reads as a list inside the clause. Separate sequences for heading words and bare numbers would split these, and would then open the list items as level 1 nodes, which cuts Section 4 short. Not built, and open for measurement on the Indian contracts (`Phases.md`, 2-0A) | Missed and false sections |
| A short all-capitals line is a heading and closes open nodes. Seen: signature block names, formula words (`MULTIPLIED BY`), and a page header that was not marked as furniture | Nodes end early |
| A party list at the top of a document (`1.` and `2.`) opens two level 1 nodes. The clause sequence then replaces its run by restart, and the two nodes stay | Two false nodes |
| A Word list whose first item is an empty numbered paragraph is not read when it is a nested decimal (`1.1` empty, `1.2` first), a letter list or a numeral list. A top-level decimal list is read. A gap in the middle of any list is read (7.5) | A list is missed |
| A numeral list that opens right after `(h)` reads `(i)` as the ninth letter. Its other numerals stay inside that node. Seen in a state government services template (`(h) a reference to:` then `(i)` to `(iv)`) | One coarse node, wrong level |
| Numbers inside a table cell are not read, so a contract laid out as one large table has a `table` node and no clauses | No clauses |
| A contents page with neither a dot leader nor a trailing page number is read as clauses | False nodes |
| A definition in a form that is not listed (`X shall be construed as`) is not found, and a quoted term at the end of one block with its verb at the start of the next is missed | Missed definition |
| A typed list that opens above 1 is body text | A list is missed |

## 13. A worked example

The fixture is a six paragraph DOCX. Its `source_text` has 208 code points:

```text
SERVICES AGREEMENT
1. Definitions
1.1 In this Agreement the following words have these meanings.
(a) "Services" means the work described in Schedule 1.
2. Term
2.1 This Agreement starts on the Effective Date.
```

Blocks (`text` is `source_text[start:end]`):

| id | start | end | locator | text |
|---|---|---|---|---|
| `b0001` | 0 | 18 | `{"part": "document", "paragraph": 1}` | `SERVICES AGREEMENT` |
| `b0002` | 19 | 33 | `{"part": "document", "paragraph": 2}` | `1. Definitions` |
| `b0003` | 34 | 96 | `{"part": "document", "paragraph": 3}` | `1.1 In this Agreement ...` |
| `b0004` | 97 | 151 | `{"part": "document", "paragraph": 4}` | `(a) "Services" means ...` |
| `b0005` | 152 | 159 | `{"part": "document", "paragraph": 5}` | `2. Term` |
| `b0006` | 160 | 208 | `{"part": "document", "paragraph": 6}` | `2.1 This Agreement starts ...` |

Offsets 18 to 19 and 33 to 34 are the `\n` between blocks. Nodes:

| id | parent | kind | label | level | start | end | text |
|---|---|---|---|---|---|---|---|
| `n0001` | None | `heading` | None | 1 | 0 | 18 | `SERVICES AGREEMENT` |
| `n0002` | None | `section` | `1` | 1 | 19 | 151 | `1. Definitions` to the end of `(a)` |
| `n0003` | `n0002` | `clause` | `1.1` | 2 | 34 | 151 | `1.1 In this Agreement ...` to the end of `(a)` |
| `n0004` | `n0003` | `subclause` | `(a)` | 3 | 97 | 151 | `(a) "Services" means ...` |
| `n0005` | `n0004` | `definition` | `Services` | 4 | 101 | 111 | `"Services"` |
| `n0006` | None | `section` | `2` | 1 | 152 | 208 | `2. Term` and `2.1 ...` |
| `n0007` | `n0006` | `clause` | `2.1` | 2 | 160 | 208 | `2.1 This Agreement starts ...` |

`source_text[101:111]` is `"Services"` with both quotes, and the node's label is `Services`. There are no warnings, no decorations, and `coverage` is `pages_total: None, pages_with_text: None, chars: 208, partial: False`.

A PDF block, from a six page fixture with the header `ACME SERVICES AGREEMENT` and the footer `Page n of 6` on each page. The first page gives:

| id | kind | start | end | page | bbox | locator | text |
|---|---|---|---|---|---|---|---|
| `b0001` | `header` | 0 | 23 | 1 | `(72.0, 32.9, 205.5, 41.9)` | `{"page": 1, "block": 1}` | `ACME SERVICES AGREEMENT` |
| `b0002` | `text` | 24 | 95 | 1 | `(72.0, 91.3, 278.6, 130.3)` | `{"page": 1, "block": 2}` | `1. Clause 1 of the Agreement` and a second line |
| `b0003` | `footer` | 96 | 107 | 1 | `(250.0, 752.9, 296.0, 761.9)` | `{"page": 1, "block": 3}` | `Page 1 of 6` |

The first two entries of `decorations` are `[0, 23]` and `[96, 107]`. Page 2 starts after `\n\n` at offset 109.

## 14. Changes since the first message, at a glance

**New** (not stated before):

- Word list labels in the locator (`list_label`), and the cell, segment and merge rules (4.3).
- The page separator rule for pages with no block, the PDF block order and the unit of `bbox` (3.2, 4.2, 4.3).
- Decoration: the 8 percent margin zone, the repetition rule, a block of its own for each candidate, and DOCX header and footer parts (section 5).
- DOCX text rules for tabs, breaks, field results and empty paragraphs, the `noBreakHyphen` effect, and the lone surrogate error (3.1, 3.4).
- `coverage.pages_with_text` leaving out scanned pages (section 6).
- Structure: node kinds and label format, the run of 3, the prefix rule, schedules clearing sequences, typed numbers never skipping ahead, Word lists opening above 1, the gap rule of 1-F, capitals headings, titles, contents lines, bare numbers, definitions, tables, and header, footer and footnote blocks never read (section 7).
- The DOCX paragraph limit (section 11).
- The `UNMAPPED_GLYPHS` warning (sections 6 and 10).
- The ceilings (section 12), the command line and the schema (section 2). The text-free form also leaves out `list_label` and sets a definition's label to `null`.

**Refined** (stated before, now exact or changed):

- `warnings` order, and the meaning of `COLUMN_ORDER_UNCERTAIN`, `PARTIALLY_SCANNED_PDF` (an error code in the original spec), `NUMBERING_AMBIGUOUS`, `NUMBERING_NOT_RENDERED`, `TEXT_BOX_CONTENT`, `EMBEDDED_OBJECT` and `UNSUPPORTED_DOCX_FEATURE` (section 10).
- The meaning of `UNSUPPORTED_TYPE`, `MALFORMED_FILE`, `ENCRYPTED_PDF`, `SCANNED_PDF`, `TOO_MUCH_TEXT`, `ARCHIVE_TOO_LARGE`, `ARCHIVE_UNSAFE` and `TRACKED_CHANGES_PRESENT` (section 9), the PDF content budget (section 11), and the `id` of a footnote or endnote in the locator (4.3).
- The PDF locator and every DOCX locator (4.3), header, footer and endnote reading (4.3), and the page-number rule (section 5).
- The triggers of `partial` (section 6), DOCX wrappers and text boxes (3.4), structure levels, ranges and acceptance (7.2 and 7.4).

## 15. To agree

1. The separators and offsets in section 3, which the core reads without change.
2. How the core treats `decorations` (mask them) and `partial` (report "not checked", never "not found").
3. The shape of `name_span` in section 8, before the parser builds it.
4. Which ceilings in section 12 the core wants a warning for. Each one needs a signal the parser does not have today.
