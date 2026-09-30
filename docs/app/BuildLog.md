# Build Log

Project memory for the backend. Append new entries at the bottom; never rewrite history.

## 2026-09-30: Pre-phase, Phase 1 spec review

Part: none (before 1-A).

Files changed:
- `docs/app/Phases.md`: 1-D split into 1-D and 1-D2, Spec amendments section, Phase 2 dependency line.
- `docs/app/BuildLog.md`: created. Part 1-A appends its own entry.

Commands run: none in the repo. Library behaviour was measured in a scratch virtual environment outside the repo: `pip install pdfplumber python-docx pyyaml pytest ruff reportlab pillow`, then probe scripts against generated PDFs and DOCX parts.

Tests: none yet.

Versions resolved in the scratch install (1-A pins what its own install resolves): pdfplumber 0.11.10, pdfminer.six 20260107, python-docx 1.2.0, PyYAML 6.0.3, pytest 9.1.1, ruff 0.16.9, reportlab 5.0.1, pillow 12.3.0. Transitive: lxml 6.1.3, pypdfium2 5.13.0, cryptography 50.0.1. No scikit-learn, no PyMuPDF. Every compiled package loads on this machine. `pdfminer` and `lxml` are imported directly for their exception types; both are already pinned by pdfplumber and python-docx, so they get no separate pin.

Measured behaviour behind the amendments:
- pdfplumber wraps pdfminer errors in `PdfminerException` (the cause is `args[0]`). It also raises `MalformedPDFException` and a bare `TypeError`: about 4 percent of 400 byte-flipped mutants escaped a `PdfminerException`-only catch.
- pdfminer exception text and log records contain raw document bytes.
- `extract_words` rewrites U+FB01 to `fi` by default and splits on NBSP; `page.chars` keeps both.
- A 16 KB PDF that decodes to 16 MB took 186 s in `extract_words`, about 11.6 s per decoded MB.
- python-docx `paragraph.text` drops `fldSimple`, inline `sdt`, `smartTag` and `moveTo`/`moveFrom` content, and `doc.paragraphs` skips a body-level `sdt`. The `List Number` style carries `numPr`; the paragraph does not.
- `pytest` cannot import `app` without `pythonpath = ["."]`.

Decisions:
- Adopt amendments A1 to A24 (see Phases.md). The over-engineering review removed a second limit check in `build()`, the `page_count` equality test, a separate table fixture, `flush_cache`, a member-count cap, the encrypted-member fixture, the `"seg"` locator key, custom missing-file handling and a separate privacy test.
- Both A10 thresholds stay (20 and 200). A searchable scan has a full-page image and a large real text layer, and one threshold would mark every searchable scan partial.
- Text boxes are extracted instead of skipped (A15).
- The content budget decodes incrementally and aborts at the limit (A11).
- 1-D splits into 1-D and 1-D2.

Blockers: none.

Next action: commit 0-A together with these two doc changes, send the Tanishq message, then reply `go` to start 1-A.
