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

## 2026-10-01: Plan revision 1.1 adopted (review scope)

Part: none (planning change, no code).

Files changed:
- `docs/app/Phases.md`: new "Review scope" section; scope requirements added to 2-A, 2-D, 3-B and 4-C; new part 3-D (manual-review navigation).
- `docs/app/Architecture.md`: request flow step 8, three key-decision rows, two planned modules (`scope.py`, `review_units.py`).

Decision: adopt the team plan's revision 1.1 in full, including the manual-review navigation (plan section 10.7). 3-D is built last in Phase 3 so it cannot delay the demo path. Phase 1 is unaffected: parser blocks already provide the exact, non-overlapping units 3-D needs.

Dependencies: Tanishq supplies the eight scope fixtures (plan section 11.3) before 3-D starts.

Next action: unchanged. Continue Phase 1 from the current part.

## 2026-10-02: Part 0-B, docs/app sync

Part: 0-B (docs only: no code, no new dependencies, nothing outside `docs/app/`).

Files changed:
- `docs/app/Rules.md`: section 1 scrub command replaced with the A3 version; section 7 correctness-review row names `/coderabbit:code-review`; the four `/ponytail-review` invocations now read `/ponytail:ponytail-review`; the commit scope list gains `annotator`.
- `docs/app/Architecture.md`: the fixes listed below.
- `docs/app/Phases.md`: phase mapping line; 0-A ticked and 0-B added; parts 2-0A and 2-0B; name note on 2-E; `TOO_MUCH_TEXT` UI string on 4-C; the 1-R line and the Process list name the right review skill; resolution notes under A10 and A14.
- `docs/app/BuildLog.md`: this entry.

Commands run: the Rules section 7 skill listing; `coderabbit --version` (0.7.6) and `coderabbit review --help`; the corrected section 1 scrub over `backend/` and `docs/app/` (rerun after the late changes below); a read of the installed ponytail plugin manifest, skill folder and command folder.

Tests: none (docs only). The scrub printed nothing and grep exited 1, its no-match status. Run without `--exclude=Rules.md`, it matches only the three lines of Rules.md that hold the pattern text, so the exclude does what A3 says. No em or en dash in `docs/app/`.

Correctness-review skill: `coderabbit:code-review`. The plugin ships two entries, the skill `coderabbit:code-review` and the command `coderabbit:coderabbit-review`. Both run `coderabbit review --agent` on the local repository and open no PR. The skill documents `--base-commit` for a commit range, which is what a phase-scoped review needs. The command documents only `--base <branch>`. Rules section 7 and the 1-R line use `--base-commit <commit before the phase started>`. The skill text still shows `-t committed`; CLI 0.7.6 lists `--committed` and `--uncommitted` instead, so the docs avoid both.

Architecture.md fixes (each against the amendment that drives it):
- Request flow step 3: "worker thread" became a child process with a wall-clock kill (A11).
- Key decisions, Text normalisation: "None in the parser" became no Unicode normalisation plus three extractor effects: PDF space runs collapse, PDF U+00A0 arrives as U+0020 (A6), DOCX `w:noBreakHyphen` becomes `-` (A24).
- Key decisions, Scanned or partly scanned PDFs: "Rejected in v1" became the A10 rule with its two thresholds (20 and 200), then the 2 October change: only `SCANNED_PDF` rejects, and a partly scanned file parses as partial with a `PARTIALLY_SCANNED_PDF` warning.
- Key decisions, Worker model: "One process" became one API process plus a child process per parse job (A11).
- Key decisions, new rows: PDF content budget with the 8 MiB incremental abort (A11), DOCX tracked changes rejected with `TRACKED_CHANGES_PRESENT` (A13), DOCX text boxes extracted outside `mc:Fallback` (A15), DOCX embedded objects as partial (A15), DOCX unknown block content skipped with a warning and `partial` (A14, resolved 2 October).
- Section 4 separators: "Nothing else changes" became the A6 rule (PDF space runs and U+00A0; DOCX keeps U+00A0).
- Folder tree: `.gitignore` gains `graphify-out` (A3); `errors.py` also holds the limits (A11); `pdf.py` gains the content budget and `docx.py` gains text boxes and the tracked-change check; `documents.py` notes the child process; `tools/annotator/` added as planned (2-0B).
- Checked and left alone: the DOCX numbering row already says labels live on `StructureNode.label` and stay out of `source_text` (A17).

Decisions:
- A10 gives the two thresholds but not what happens to a scanned page. The first draft of the Architecture row took the outcome from the Phase 1 handoff; the resolution below replaces it.
- 2-0A uses the `docs` commit scope and 2-0B uses `annotator`. `annotator` was not in the Rules list, so it was added there.
- `TOO_MUCH_TEXT` UI string: no part in this file maps error codes to UI messages, so the note sits on 4-C, the first part that runs the real frontend against the backend.
- 0-A was already committed, so it is ticked. 0-B is ticked as part of this change.
- WorkSplit.md is not in the repo, so the contract-section line was not added. Datasets.md is untouched.

Resolutions added before the commit (2 October 2026):
- A14: an unknown DOCX block is a warning, not an error. The parser skips it, records `UNSUPPORTED_DOCX_FEATURE` in warnings and sets `coverage.partial`. A raised error leaves no result to mark partial. Written into a new Architecture.md DOCX row and a resolution note under A14 in Phases.md.
- A10, tagged `[CONTRACT]`: only `SCANNED_PDF` rejects, when every page with content is scanned (the handoff's "pages with content" wording; blank pages do not count). A partly scanned file parses with `coverage.partial = True` and a `PARTIALLY_SCANNED_PDF` warning, so that code moves from the error list to the warning list. The under-200 partial rule stays. Reason: executed contracts often end in a scanned signature page. Updated the Architecture.md scanned row and added a note under A10 in Phases.md. The handoff's `partly_scanned.pdf` fixture now expects a parse. This goes to Tanishq with the other `[CONTRACT]` items.
- 2-0B exports JSONL (plan v1.1 section 4.3), with code-point offsets checked against the parser's `source_text`, as that section requires for an offline tool. 2-0A covers every guideline topic that section lists.
- Commit scopes: 2-0A `docs`, 2-0B `annotator`; `annotator` added to the Rules.md scope list.
- Review skill invocation: `/ponytail:ponytail-review`. Evidence: the installed plugin is `ponytail` 4.8.4 (manifest name `ponytail`), its skill folder is `skills/ponytail-review` with `name: ponytail-review`, no user-level skill of that name exists, its `commands/` folder holds `.toml` files, not slash-command markdown, and the session's skill registry lists `ponytail:ponytail-review`. The skill was read, not run. Phases.md and BuildLog.md held no `/ponytail-review` invocation. The report label `ponytail-review:` in the Rules.md part report template is a field name, not an invocation, and stays.

Blockers: none.

Next action: commit 0-B with `docs: sync app docs with parser amendments and v1.1 decisions`, then start Phase 1 at 1-A.

## 2026-10-03: Part 1-A, package scaffold and parsed-document model

Part: 1-A.

Files changed:
- New in `backend/`: `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `.env.example`, `app/__init__.py` and `app/parsing/__init__.py` (both empty), `app/parsing/model.py`, `app/parsing/errors.py`, `app/parsing/assemble.py`, `tests/test_assemble.py`.
- `docs/app/Phases.md`: 1-A ticked; A2, A3 and A5 marked done; the A10 code-list change noted; 1-A deviations recorded.
- `docs/app/BuildLog.md`: this entry.
- Root `README.md`: new backend section (prerequisites, install, run, test), at the request of the 1-A prompt.
- `docs/app/Architecture.md`: unchanged. Its tree lines, key-decision rows and section 4 already match the scaffold.

Commands run, from `backend/` in Git Bash:
- `python -m venv .venv`, `source .venv/Scripts/activate`, `pip install -r requirements-dev.txt` with unpinned names, then `pip freeze` to copy the resolved versions into both files.
- `ruff format --check .`, `ruff check .`, `pytest -q`.
- Clean install check: a fresh venv outside the repo, `pip install --no-cache-dir -r requirements-dev.txt` from the pinned files, then the same three checks and an import smoke run that builds a one-block document.
- A mutation pass on a copy of `assemble.py` outside the repo (see Tests).
- The Rules section 1 scrub and a dash check over `backend/` and `docs/app/`.
- Read-only git: `git status`, `git log`, and one `git branch -a`.

Tests: 24 passed, 0 failed, 0 skipped, with `pytest -q` from `backend/`. Ten one-line mutations of `assemble.py` each failed at least one test: the limit comparison, CR conversion, the page separator, tab stripping, the whitespace check, the decoration kinds, `from None`, the page-break reset, the page count and the empty-block guard.

Pinned versions, Python 3.12.10:
- Runtime: pdfplumber 0.11.10, python-docx 1.2.0, PyYAML 6.0.3.
- Dev: pytest 9.1.1, ruff 0.16.10, reportlab 5.0.1, pillow 12.3.0.
- Transitive, recorded here and left unpinned: pdfminer.six 20260107, lxml 6.1.3, pypdfium2 5.13.0, cryptography 50.0.2, cffi 2.1.1, pycparser 3.0, charset-normalizer 3.5.2, typing_extensions 4.16.0, pluggy 1.6.0, iniconfig 2.3.0, packaging 26.3, Pygments 2.21.0, colorama 0.4.6.
- Against the pre-phase scratch install, ruff moved from 0.16.9 to 0.16.10 and cryptography from 50.0.1 to 50.0.2.
- `pip list` shows no scikit-learn and no PyMuPDF. Every compiled package imports on this machine.

Decisions:
- Applied amendments: A2 (`pythonpath`), A3 (the `graphify-out/` ignore line), A5 (assembler) and the A10 code-list change.
- The codes are `StrEnum` classes with explicit values. `ParseError` hands only the code to `Exception`, so `str(error)` prints the code and nothing else.
- `new_page()` sets a flag. Two calls in a row give one page separator, and a call before the first block adds nothing.
- `add_block` converts CRLF and CR to LF inside each line, then splits and strips trailing spaces and tabs, so a space before a CR goes too. It avoids `str.splitlines`, which also splits on form feed, U+2028 and other characters the canonical text must keep.
- The 500,000 limit counts separators, and `add_block` checks it before appending.
- `build()` encodes the text before the whitespace check, so a lone surrogate gives MALFORMED_FILE.
- Only direct dependencies carry pins, as decided before the phase.
- The over-engineering review raised six findings, none blocking. Two applied: the block field test compares whole `Block` values, and the invariant helper drops a decoration-bounds loop that repeated the block check. Four kept: the three limits no 1-A code reads and the full code lists, which the 1-A spec asks for; the `warnings` and `partial` parameters of `build()`, which fill required fields; and the `PARSER_VERSION` constant, a contract value.

Deviations: listed under the 1-A amendments in Phases.md (project version, the `build()` signature, `ValueError` for an empty block, the root README section, the A11 limit deferred to 1-C).

Verification:
- Clean venv install from the pinned files: works.
- `ruff format --check .`: 6 files already formatted. `ruff check .`: all checks passed. 1-A sets up no type checker.
- `pytest -q`: 24 passed.
- Smoke check (1-A has no server or CLI): `python -c "import app.parsing.assemble"` exits 0, and a one-block build returns parser version 1.0.0.
- Attribution scrub: no output. Dash check: no em or en dash in `backend/` or `docs/app/`.

Core interface: `ml/clauseanchor_core` sits on main at contract version 2.0, with `StubAnalyzer` and the sample fixtures, since d9e4c6a. The scope fixtures arrived in 19f386c. Nothing in `backend/` imports from `ml/`. The 2-D dependency is met.

Blockers: none.

Next action: commit 1-A with `chore(backend): set up package, tooling and parsed document model`, send the updated contract message to Tanishq, then reply `next` to start 1-B.


## 2026-10-04: Part FE-0, baseline frontend import

Part: FE-0 (frontend track). Only `frontend/`, `docs/app/` and `README.md` changed. Part 1-B stays paused at Aryan's request.

Files changed:
- New `frontend/`: `package.json`, `pnpm-lock.yaml`, `tsconfig.json`, `vite.config.ts`, `index.html`, `.gitignore` and `src/` (72 files).
- New `docs/app/DesignSystem.md`.
- `docs/app/Rules.md`: README exempted from the root-file freeze (root config stays frozen), `frontend` added to the commit scopes, section 1 scrub extended to `frontend/` with the `node_modules`, `dist` and `.screens` excludes.
- `docs/app/Phases.md`: Frontend track section with FE-0 ticked, 1-B marked paused, 1-A README deviation note removed.
- `docs/app/Architecture.md`: new section 7 (frontend data flow, key decisions, folder tree); section 6 renamed "Backend tech stack".
- `README.md`: new Frontend section.
- `docs/app/BuildLog.md`: this entry.

Copied, as imported from the design export: `src/` without `src/imports/` (50 components plus `icons.tsx`, 6 pages, `api/`, `app/`, `lib/`, `main.tsx`, `App.tsx`, `index.css`, `vite-env.d.ts`), `index.html`, `package.json`, `pnpm-lock.yaml`, `tsconfig.json`, `vite.config.ts`. A diff against the source shows `src/`, the lockfile and `tsconfig.json` unchanged.

Excluded, because they are authoring-tool scaffolding and not project source: the tool's hidden config folder (preview and deploy scripts), `plans/` (a working note), `AGENTS.md` and the one-line file that points to it, `src/imports/` (the component brief and prompt notes; the brief's sections 1 to 4 and 9 became `DesignSystem.md`), `.gitattributes`, `.mise.toml` (it pinned Node 22 and pnpm 10.34.3) and the export's own `.gitignore`.

Allowed edits, nothing else:
- `vite.config.ts`: dropped the four authoring-tool plugins, the `site.json` import, the `base` environment lookup and the `server` and `preview` blocks. It keeps `react()`, `tailwindcss()` and the `@` alias, and is 13 lines on Vite defaults (port 5173).
- `index.html`: replaced the comment slots with `lang="en"`, `<title>ClauseAnchor</title>` and a meta description: "Know which clauses to ask a lawyer about. Every finding quotes your contract or a published judgment, and nothing is stored after your session." (143 characters).
- `package.json`: name set to `clauseanchor-frontend`, `"typecheck": "tsc --noEmit"` added. Every dependency and version is unchanged.
- `frontend/.gitignore`: `node_modules/`, `dist/`, `.vite/`, `*.tsbuildinfo`, `*.log`, `.env*`, `.screens/`.
- Type fixes: none. `pnpm typecheck` passed on the first run.

Environment: Node v24.16.0 and pnpm 11.20.0 were installed. The export pinned Node 22 and pnpm 10.34.3. The install, typecheck and build ran on the installed versions only, so the README's "22 or later" and "10 or later" rest on the pin and not on a run.

Resolved versions (lockfile, unchanged): react 19.2.4, react-dom 19.2.4, react-router 8.4.0, tailwindcss 4.2.2, @tailwindcss/vite 4.2.2, vite 8.0.5, @vitejs/plugin-react 6.0.1, typescript 5.9.3, @types/node 22.19.17, @types/react 19.2.14, @types/react-dom 19.2.3, oxfmt 0.2.0. No dependency was added.

Commands run, from `frontend/` in Git Bash:
- `pnpm install --frozen-lockfile`, `pnpm typecheck`, `pnpm build`, `pnpm dev`.
- A screenshot and console script in headless Edge over the DevTools protocol. It lives outside the repo and adds no dependency. The first run picked up a browser extension that made requests to a third-party host, so the record is the second run, with extensions disabled.
- Read-only git: `git status`, `git check-ignore`.

Skills that ran: copywriting (meta description), copy-editing and stop-slop (README and docs prose), `/ponytail:ponytail-review`.

Verification:
- `pnpm install --frozen-lockfile`: works, 46 packages, the lockfile passed the supply-chain policy check.
- `pnpm typecheck`: exit 0, no errors.
- `pnpm build`: 160 modules, no warnings. `dist/` holds `index.html` 0.58 kB, CSS 19.34 kB (5.28 kB gzipped) and one JS file of 491.26 kB (143.37 kB gzipped). The initial route is under the 200 KB bar.
- App Control: no native binary (Tailwind oxide, lightningcss, rolldown) was blocked.
- Dev server: Vite 8.0.5 on port 5173. Seven views rendered: `/`, `/how-it-works`, `/accuracy`, `/expired`, `/gallery`, an unknown path (the catch-all shows Expired) and `/review/:documentId`, reached by uploading a file on the mock adapter. The console showed one entry in the whole run: a 404 for `/favicon.ico`. No React warnings.
- Screenshots: 70 images, seven views at 375, 768, 1024, 1280 and 1440 px in light and dark, in `frontend/.screens/FE-0/` as `<view>-<theme>-<width>.png` (views: `home`, `how-it-works`, `accuracy`, `expired`, `gallery`, `unknown-route`, `reader`). The folder is gitignored.
- Tool-name grep over `frontend/`, the Rules section 1 scrub over `backend/`, `frontend/` and `docs/app/`, and the dash check over `frontend/src`, `docs/app` and `README.md`: no output, no match.
- `git status --short -uall` lists no path under `frontend/node_modules`, `frontend/dist` or `frontend/.screens`.

ponytail-review: no P1. Four P2, all baseline items the brief says to keep:
- The `@` alias has no use in `src/`. Dead config in `vite.config.ts` and in `tsconfig.json` (`baseUrl`, `paths`). Kept because the brief names the alias. FE-2 decides.
- `oxfmt` and the `format` script: nothing calls them. Kept because every dependency stays. FE-R decides.
- CheckboxRadio, DocumentBlock, SectionPath, Select, TextInput and Tooltip (444 lines) are imported only by the gallery. Kept because component APIs stay. TextInput, Select and CheckboxRadio are likely needed by the `/start` flow in FE-4. FE-R removes what is still unused.
- The Phases.md standing constraints and quality bars repeat the brief. Kept because the brief sits outside the repo. FE-1 moves the quality bars into FrontendDesign.md and Phases.md will point there.

Decisions:
- The export was zipped in Downloads, not unzipped at the folder the brief names. I extracted that zip to the named folder, outside the repo, and copied from there.
- No favicon was added. `index.html` edits were limited to the three listed, and a favicon is design work. It costs one 404 per cold load. FE-2 should add one from the brand mark.
- `DesignSystem.md` keeps section 4 byte for byte (checked with a diff). Accessibility moved from section 9 to section 5. Tooling instructions (variables, pages, file organisation) were dropped. A note in 3.4 records the Google Fonts import.
- Phase 4 has no frontend parts, so no FE part maps onto it. The adapter swap stays at 4-C.

Baseline observations for the FE-1 audit, with no change made:
- The fonts load from Google Fonts through a CSS import in `index.css`, a third-party request that contradicts the privacy promise.
- `/gallery` scrolls horizontally at 1280 px.
- Expired, the gallery and the reader have no `<h1>`.
- The reader at 375 px puts "Download report" and "Delete document" on two-line buttons.

Blockers: none.

Next action: commit FE-0 with `chore(frontend): import baseline frontend`, then reply `next` to start FE-1 (design direction, docs only).


## 2026-10-04: Part FE-1, frontend design direction

Part: FE-1 (frontend track), docs only. Only `docs/app/` changed. No file under `frontend/` changed. Part 1-B stays paused at Aryan's request.

Files changed:
- New `docs/app/FrontendDesign.md`: the audit, principles, information architecture, layout and tokens, page compositions, motion, copy plan, trust map, skills table, dependency requests, accessibility plan, test plan, part scopes, 13 open decisions, 13 deviations and the design-review amendments (17.1).
- `docs/app/Phases.md`: FE-1 ticked. The standing constraints and quality bars moved to `FrontendDesign.md` section 1, and the file keeps one pointer line. The FE-1 and FE-2 entries say what moved. Decisions D1 to D6 gate FE-2.
- `docs/app/Architecture.md`: the fonts row points at the self-hosting proposal, and section 7.3 lists the files the FE parts plan to add, marked planned. The tree itself is unchanged.
- `docs/app/DesignSystem.md`: a note that the new tokens and colour changes land in FE-2, and the fonts note points at the proposal.
- `docs/app/BuildLog.md`: this entry.

Method. The audit ran against the production build served by `pnpm preview`, driven through a headless Edge over the DevTools protocol with extensions disabled, at 375 and 1280 px in the light theme (contrast pairs in both themes). The scripts live outside the repo and add no dependency. The 70 FE-0 screenshots and the 16 state screenshots in `frontend/.screens/FE-1/` are the visual record. No new screenshot was taken at the end of FE-1, because no route changed.

Skills that ran: `ui-ux-pro-max` (search only, nothing written), `frontend-design`, `cro`, `marketing-psychology`, `site-architecture`, `signup`, `onboarding`, `impeccable` (detector only, read-only), `copywriting`, `copy-editing`, `stop-slop`, `/ponytail:ponytail-review`. `gstack-design-consultation` and `gstack-plan-design-review` ran as method only. Their start-up routine (update check, telemetry, artifact sync), the design-file output, the generated mockups, the review log and the outside voices were skipped, because they write outside `frontend/`, `docs/app/` and `README.md`. Not run, and listed in `FrontendDesign.md` section 10 for later parts: `design-taste-frontend`, `emil-design-eng`, `animate`, `tailwindcss`.

Plan design review ratings, before and after the amendments (the "after" column assumes Aryan approves them):

| Pass | Before | After | What was missing |
|---|---|---|---|
| 1 Information architecture | 8 | 9 | No first-viewport hierarchy or fold budget, no journey diagram, no rule for a Reader URL without a session |
| 2 Interaction states | 5 | 9 | No states for the root error, a page without JavaScript, the start steps, zero findings or a long filename |
| 3 Journey and emotional arc | 6 | 9 | No scene-by-scene arc, no reload protection, a landing promise (the report) that nothing confirms |
| 4 AI slop risk | 7 | 9 | Three jobs in one section, a legal line repeated three times, content hidden behind animation timing, unthemed browser surfaces, an indistinguishable visited link |
| 5 Design system alignment | 8 | 9 | New patterns without a definition, and the edits owed to `DesignSystem.md` unlisted |
| 6 Responsive and accessibility | 7 | 9 | A three-column grid that leaves an 80 px aside at 1024, no forced-colours path, no landing layout per viewport |
| 7 Unresolved decisions | n/a | 13 open, 0 hidden | See `FrontendDesign.md` section 15 |

Overall design completeness: 7 of 10 before, 9 of 10 after. The missing point is visual proof. No mockup was generated, so the composition is specified and not yet seen. FE-3 is the first time it is drawn.

Findings that matter most (the full list is in `FrontendDesign.md` sections 2 and 17):
- The reader's contract column holds about 47 characters a line at 1280 and 50 at 1024, against a target of 68 to 80. The proposal is a 64 px category rail from 1280 to 1439.
- The Google Fonts import breaks the privacy promise on every route. Self-hosting is proposed, with option B (vendored files, no dependency) recommended.
- Seven contrast pairs fail AA, and the form borders fail the 3:1 non-text bar. Every fix keeps its hue and is verified.
- 13 of 21 controls on the mobile home are under 44 px.
- Four routes have no `h1`, the page title never changes, and an unknown URL renders the "session expired" page.
- The landing page has no call to action in the hero, and the mock counts and placeholder judgments must stay off it.
- Review amendment I: a three-column margin grid at 1024 would leave an aside about 80 px wide, so it starts at 1280.

Correction made during FE-1. The first audit pass reported the reader measure as 35, 54 and 54 characters at 1280, 1440 and 1920. That count divided the text length by the number of wrapped lines, which overstates the line count when inline marks and short last lines are present. A second run measured the real text width and the average glyph width (7.83 px per character for the 17 px serif) and gives a capacity of 47, 67 and 75. A direct count of the full lines over 13 paragraphs gives an average of 44.3, 65.9 and 73.7, so capacity by width runs 1 to 3 characters high and is a fair quick estimate. The 1280 proposal changed with it: the first plan sized the sheet for a 74 character line using the wrong glyph width and would have produced about 88. Section 2.4 states both methods, and FE-5 accepts on the full-line average.

Checked in FE-1: the CUAD facts (510 contracts, 41 categories, more than 13,000 annotations, CC BY 4.0) against the dataset page and the paper abstract; the 46 categories as 41 plus 5; contrast ratios by the WCAG luminance formula (70 pairs, and the new values re-run); the focus ring ratios; and that `node --test` with type stripping runs a `.ts` file that imports `lib/offsets.ts` on this machine (Node 24.16).

Not checked: Lighthouse and axe (FE-R, they need approval to download); how React Router 8.4.0 handles view transitions (the general docs were read, the pinned version was not); the font file names and sizes (read from registry and CDN metadata, nothing downloaded); any screen reader. The 1280 reader layout figures are estimates until FE-5 measures them. The Reader's behaviour on a 500,000 code point document is unmeasured.

Decisions: none were made. `FrontendDesign.md` section 15 lists 13 open decisions with a recommendation each. D1 to D6 gate FE-2: hero data source, play once with Next example, font self-hosting and the download, the test runner, the narrowed margin rule and the colour changes. D7 (a verified judgment quote for the landing page, from a corpus id Tanishq supplies) gates FE-3.

Verification:
- `pnpm install --frozen-lockfile`: works. `pnpm typecheck`: exit 0. `pnpm build`: 160 modules, JavaScript 491.26 kB (143.37 kB gzipped), CSS 19.34 kB (5.28 kB gzipped), identical to FE-0.
- Rules section 1 scrub over `backend/`, `frontend/` and `docs/app/`, the tool-name grep over `frontend/`, and the dash check over `frontend/src`, `docs/app` and `README.md`: no output, no match.
- `git status --short` lists only the four modified docs files and the new `FrontendDesign.md`.
- The preview server on port 4173 and every headless Edge process were stopped.

ponytail-review: no P1. Eleven P2 and P3 items, all fixed in this part:
- `FrontendDesign.md` section 0: a table that repeated the headings. Cut to two sentences.
- Section 2.2: a table that repeated the old ratios in 5.4. Cut to one sentence.
- `space/24` and `space/32` as CSS tokens: Tailwind derives `py-24` and `py-32` from `--spacing`. The tokens are gone, and the names stay in `DesignSystem.md` only.
- `--w-form`: one use. Replaced by an inline `max-w-[640px]`.
- `--dur-step`: a cap and not a token. Now one rule in 7.2.
- A "Replay" button next to "Next example": removed, and the examples wrap.
- A new `src/content/` folder for one fixture: the fixture moves to `pages/landing/`.
- A Manual review button in the reader rail: the drawer already holds the list. The rail has one button.
- A sentence about fixing the gallery's overflow: removed, because the gallery no longer ships.
- The ratings table: moved here, because it records the review and is not part of the spec.
- The FE-2 line in `Phases.md`: shortened, with a pointer to the acceptance table.

Kept on purpose: the skills table and the banned list (the brief requires both), the deviations list (it overlaps the decisions but is the sign-off record), the split of the reveal logic from its hook (the test runner has no DOM), and `control-border` as its own token (`rule/strong` still draws dividers). The spec went from 921 to 891 lines.

Blockers: none for FE-1. D7 blocks the landing Evidence section at FE-3, and the section is omitted until a verified quote exists.

Next action: review `FrontendDesign.md` and answer D1 to D6. Commit with `docs(frontend): add frontend design direction`, then reply `next` to start FE-2.


## 2026-10-04: Part FE-2, foundations

Part: FE-2 (frontend track). Files changed under `frontend/`, `docs/app/` and `README.md`. Part 1-B stays paused at Aryan's request. No dependency was added.

Files changed:
- New under `frontend/`: `public/favicon.svg`, `public/fonts/` (seven woff2 files and three OFL licence texts), `src/lib/reveal.ts`, `src/lib/reveal.test.ts`, `src/lib/useReveal.ts`, `src/tokens.test.ts`, `src/components/Layout.tsx`, `src/components/Disclosure.tsx`, `src/components/PreviewControls.tsx`, `src/pages/NotFound.tsx`, `src/app/RootError.tsx`.
- `frontend/index.html`, `package.json` (a `test` script and an `engines` field), `src/index.css` (rewritten: own-origin fonts with metric-matched fallbacks, the colour changes, motion and width tokens, one global focus rule, `.hit`, layout and type classes, reveal CSS, one reduced-motion block, forced-colours marks, themed selection and scrollbars), `src/app/routes.tsx` (lazy pages, error boundaries, `/gallery` in development only), `src/app/Root.tsx` (focus to the heading on a path change, menu id and Escape, dev-only preview controls).
- Components, mechanical: per-component focus code removed from 14 components in favour of the global rule, `.hit` added where a visual size is under 44 px, `control-border` swapped in on eight form controls, and 11 and 10 px text raised to 12 px.
- Components, specific: `Link` (router link for `#/` addresses), `AppHeader`, `Button`, `MobileDrawer` (rewritten, stays mounted, slides on `transform`), `CategoryRow` (tint and bracket mark instead of the side stripe), `CategoryGroupHeader` (44 px), `ClauseDetailPanel` (two 4 px stripes replaced by a 1 px box), `ConfidenceBand`, `DropdownMenu`, `EmptyState` (`headingAs`), `SearchField` (the label wraps the field, so the whole box focuses the input), `SpanHighlight` (`ca-mark`), `Switch` (the knob moves on `transform`), `Spinner`, `icons`.
- Pages: `Home` (mock panel removed, view transitions on navigation), `Reader` (title, a visually hidden `h1`, scroll panes, `ca-mark`), `Accuracy` and `HowItWorks` (titles), `Expired` (title, `h1`), `Gallery` (colour swatches corrected, a new "Layout and motion" section, a working contents bar).
- Docs: `DesignSystem.md` (3.1, 3.2, 3.4, 3.5 and 5 updated, new section 6), `FrontendDesign.md` (5.2 and 5.4 marked, section 15 pointer, new 17.2 with D1 to D13, amendments N to T and the deferred list), `Phases.md` (FE-2 ticked, deviations), `Architecture.md` (tree, routing, fonts, motion and test rows), `README.md` (Node 22.18, `pnpm test`, routes, fonts).

Method. Browser checks ran against the production build from `pnpm preview` (port 4173) and the dev server (port 5173), driven through a headless Edge over the DevTools protocol with extensions disabled. The scripts live outside the repo and add no dependency.

Skills that ran: `superpowers:test-driven-development` (the reveal core, red then green), `tailwindcss` and `animate` (run late, as a check of the finished tokens and motion against their rules, so they changed nothing), `superpowers:verification-before-completion`, `copywriting`, `copy-editing` and `stop-slop` (in that order, over the docs and the few user-facing strings: the error page, the not-found page and the noscript line), `/ponytail:ponytail-review`. Not run, and left to the parts that need them: `design-taste-frontend` and `emil-design-eng`. The gstack design review and QA, `coderabbit`, `gstack-review`, `gstack-cso` and one independent second review run at FE-R, as the plan says.

Decisions: D1 to D13 are answered in `FrontendDesign.md` 17.2. D8 to D13 follow their recommendations, because none adds a dependency, changes a fixed phrase or moves a route:
- D8 follows the mock for the sample id. D9 uses CUAD facts only. D10 picks hero heading A. D11 picks the 64 px Reader rail. D12 keeps the report out of the landing copy. D13 shows both landing buttons.
- D2 is signed off with its WCAG 2.2.2 reasoning (17.2). D7 holds the Evidence section back until Aryan sends a verified passage from Tanishq.

Deviations from the plan, each recorded in 17.2:
- N: the three layout primitives are one file, `components/Layout.tsx`, not a `layout/` folder.
- O: a baseline bug. The `Link` atom called `preventDefault` on every click, so no internal link in the header, footer or page body navigated. It now goes through the router with a view transition.
- P: the fixed `MobileDrawer` stays mounted. Focus does not move into a drawer or back out (FE-5). The bottom sheet has no exit animation, because the Reader unmounts it (FE-5).
- Q, R: hit areas fixed beyond the plan's list, and the bracket mark moved out of the row's flow, after the first screenshot pass showed it squeezing every category name by about 16 px, and the row keeps the baseline's 16 px left edge so it lines up with the in-progress rows.
- S: the fonts are the Latin subset. The rupee sign U+20B9, the bracket marks and non-Latin scripts fall back to a system font. Contracts in India contain the rupee sign, so a Latin-extended subset is worth adding. The three OFL licence texts were fetched with the seven files, a small step beyond the seven files D3 named.
- T: the How it works contents links grew block padding to reach 44 px, a visible spacing change that FE-6 redoes.

Deferred, with owners (the full table is in 17.2): the ink-in keyframes (FE-3), the header restructure (FE-4), the footer Credits link (FE-6), the 4 px rule on seven more components (FE-4 to FE-6), the squeezed category names and the 12 by 3 px ruler ticks (FE-5), drawer focus management (FE-5) and tabular numerals on counts (FE-4, FE-6).

Versions on this machine: Node v24.16.0, pnpm 11.20.0. The README still says pnpm 10 or later, which holds. `engines` is `^22.18.0 || >=23.6.0`. 22.18.0 is the version where type stripping is on by default, checked in the Node docs. 23.6.0 is from memory and unchecked, and `engines` is only a hint.

Verification (all run on the final build, fresh):
- `pnpm install --frozen-lockfile`: up to date. `pnpm typecheck`: exit 0. `pnpm test`: 15 of 15 pass (7 reveal, 8 colour tokens), 0 failed, 0 skipped. `pnpm build`: 154 modules, no warnings.
- Bundle: the index chunk is 215.68 kB (67.57 kB gzipped). The landing route loads six script files, 118.4 kB gzipped in all, and 7.1 kB of CSS. FE-1 measured one 491.26 kB file (143.37 kB gzipped) for every route, so the landing route is 25 kB lighter and Reader code no longer loads with it. The five fonts the landing page uses add 138 kB.
- `dist` holds no "Preview controls" string, no Gallery chunk and no `googleapis` or `gstatic` reference.
- Six routes at 375 and 1280 px (home, how it works, accuracy, expired, expired with `reason=deleted`, not found): zero console output, zero third-party hosts, one `h1` each, a title of the form "How it works | ClauseAnchor" (Home keeps "ClauseAnchor"), no horizontal overflow.
- After a header link click focus lands on the `h1`. The mobile menu sets `aria-expanded`, closes on Escape and returns focus to its button. A blocked lazy chunk shows "This page could not load." inside the shell. Every focus ring computes to 2 px solid with a 2 px offset. Reduced motion leaves 0 running animations. A click on a header link calls `document.startViewTransition` once.
- Hit areas, counting the 44 px `::after`: every interactive element on the six routes passes. In the Reader at 375, 1280 and 1440 px, and with each drawer and the sheet open at 1024, 768 and 375 px, every control passes except the ruler's 12 by 3 px ticks at 768 px and wider (deferred to FE-5). The first Reader pass found the menu trigger (40 px), the group headers (36 px), the filter field (an input 21 px high inside a 44 px box) and the confidence button (20 px). All four are fixed, and the filter's 14 px reset button was fixed with the field. The one overlap the audit reported at 375 px, the header's theme button against the open drawer's Close, is a false positive: the audit ignores stacking, and a click on Close reaches Close.
- Reader drawers: the categories drawer moves from `translateX(-320px)` to 0 and back, and is hidden and `aria-hidden` when closed. The bottom sheet peeks 168 px at 375 and 768, opens to its full 78 percent height and closes. No console output at any width.
- Performance, indicative only, headless Edge on localhost with no throttling: LCP 112 to 332 ms and CLS 0 on `/` at 375 px over four runs. The quality-bar measurements (Lighthouse and axe) run at FE-R.
- Dev server: Preview controls appear and Home has no mock panel. The margin grid is 144, 672 and 320 px at 1280 and 1440, 144 and 784 px at 1024 with the aside stacked, and one 343 px column at 375. The long-form flow gives an `h2` 48 px above and 16 below, an `h3` 32 above and 12 below. A reveal goes from `opacity 0` and 12 px down to shown on scroll. A disclosure summary is 44 px. The Reader sets its title and `h1` and moves focus there, with no console output. The Gallery contents bar scrolls to its sections.
- Small items checked by hand: the Switch knob moves on `transform`; clicking the edge of the filter field focuses the input and the box takes a 2 px ring; jumping to a contents link on How it works leaves the heading 80 px from the top.
- The tool-name grep over `frontend/`, the Rules section 1 scrub over `backend/`, `frontend/` and `docs/app/`, and a scan of `frontend/src`, `frontend/index.html`, `frontend/public`, `docs/app` and `README.md` for en and em dashes: no output, no match. No `console.log`, `debugger`, `TODO` or `FIXME` in `frontend/src`.
- `git status --short` lists no path under `frontend/node_modules`, `frontend/dist` or `frontend/.screens`.
- No git write command was run.

Screenshots: 98 files in `frontend/.screens/FE-2/`, gitignored. Naming is `<route>-<width>-<theme>.png` for `home`, `how-it-works`, `accuracy`, `expired` and `not-found`, full page, at 375, 768, 1024, 1280 and 1440 in light and dark. The Reader has `reader-`, `reader-selected-` (a finding open) at every width and theme, `reader-drawer-` at 375, 768 and 1024, and `reader-sheet-peek-` and `reader-sheet-open-` at 375 and 768, all light. `gallery-layout-` and `gallery-layout-b-` show the new Gallery section, from the dev server. `search-focus-1440-light.png` shows the filter field's ring. The before set is in `frontend/.screens/FE-0/` and `FE-1/`.

ponytail-review: no P1. Two P2 fixed, five P2 kept:
- Fixed: the `ca-drawer-left` keyframe and its ternary in `MobileDrawer` (the side drawer is always mounted, so the mount animation could not play). Fixed: an unused `className` prop on `Container`.
- Kept: `Disclosure`, `useReveal` and the Gallery's layout section have no production consumer until FE-3, and the part's scope names them. `--stagger` and `--dur-ink` are unused until FE-3. `Container` and `MarginGrid` are exported and used only inside `Layout.tsx` until FE-3. `NotFound` and `RootError` repeat a three-line `h1` style, two callers, and FE-6 recomposes both. `HydrateFallback: () => null` appears on two routes, which a shared constant would save one line on.

Found along the way, not fixed, and added to the deferred table in `FrontendDesign.md` 17.2: the confidence popover in `ConfidenceBand` states "Calibrated on 214 examples from 48 contracts", a number with no cited source, in a component the Reader shows. FE-5 should replace it with a figure from the evaluation or remove the line.

Blockers: none.

Next action: commit FE-2 with `feat(frontend): add motion tokens, layout primitives and 404 route`, then reply `next` to start FE-3 (landing, with the live hero demo).


## 2026-10-05: Part FE-3, landing with the live hero

Part: FE-3 (frontend track). Files changed under `frontend/`, `docs/app/` and `README.md`. Part 1-B stays paused at Aryan's request. No dependency was added.

Files changed:
- New under `frontend/`: `public/fonts/` (five Latin-extended woff2 files, 135,184 bytes in all), `src/pages/Landing.tsx`, `src/pages/Start.tsx` (the old `Home.tsx`, moved), `src/pages/landing/HeroDemo.tsx`, `src/pages/landing/heroExamples.ts`, `src/pages/landing/heroExamples.test.ts`, `src/pages/landing/Evidence.tsx`.
- Removed: `src/pages/Home.tsx` (it lives on as `Start.tsx`, with the marketing hero taken out).
- `src/index.css`: five Latin-extended `@font-face` rules, `.t-display-md`, the `ca-ink`, `ca-fade` and `ca-rise` keyframes, the `.hero-demo` rules and a zero animation delay in the reduced-motion block.
- Components: `SpanHighlight` (found and review marks as two background layers), `ConfidenceBand` (optional `calibration`, no hard-coded figure), `ClauseDetailPanel` (`titleAs`, Close and Case law only with their data, an exported review note), `StatuteTag` (a label), `RuleFlagCard` (no dead button), `MarginRuler` (`viewport={false}`, `caption=""`, tab stop only with `onSelect`), `Button` (`to`), `Layout` (`SectionFrame`), `RoleSelector` (exports its role list), `Gallery` (band cells show scope or label only).
- Pages and app: `Reader` (passes the calibration scope, uses the shared review note), `app/routes.tsx` (`/` is the landing page, `/start` loads on demand), `app/Root.tsx` (the header "Review" link points to `/start`), `NotFound` and `Expired` ("Review a contract" goes to `/start`).
- Docs: `Phases.md` (FE-3 ticked, deviations), `Architecture.md` (tree, routing, fonts, data flow and test rows), `FrontendDesign.md` (1.2 gains two checks, the skills table, the deferred list in 17.2, new 17.3 with amendments U to Z), `DesignSystem.md` (3.3, 3.4, the type table, the motion table, section 6), `README.md` (routes).

Method. Page structure, the Reader and the hit areas were checked in the browser pane against the production build from `pnpm preview` (port 4173). Layouts were read from headless Edge captures over the DevTools protocol, extensions disabled. The capture script wrote the landing, `/start` and hero captures and stopped before its Reader and LCP stages. Rerunning it was blocked in this session, so those stages did not run, and Python is not installed. Scripts live outside the repo.

Skills that ran: `superpowers:test-driven-development` (the hero fixture test, red then green, and a mutation check showing the astral-character test fails on UTF-16 slicing), `animate`, `copywriting`, `copy-editing` and `stop-slop` (in that order, over the new strings and the doc prose), `cro`, `frontend-design`, `design-taste-frontend`, `emil-design-eng` and `ui-ux-pro-max` (the rule list only), `superpowers:verification-before-completion`, `/ponytail:ponytail-review`. Not run, and left to the parts that need them: the gstack design review and QA, `coderabbit`, `gstack-review`, `gstack-cso` and one independent second review run at FE-R.

Decisions: D1, D2, D8, D9, D10 and D13 are built as recorded in 17.2. D7 holds: the Evidence section is built and renders only when `EVIDENCE` in `Landing.tsx` is set, and it is `null`.

Deviations from the plan, each recorded in 17.3:
- U: an interim `/start` ships now, because the landing buttons need a destination. FE-4 replaces it.
- V: the hero ruler is hidden below 640 px.
- W: the mark is two background layers so the ink-in can sweep it. The Reader gets the same mark and adopts the sweep in FE-5.
- X: five Latin-extended font files, so the rupee sign renders in Source Serif 4. None of the three hero excerpts contains a rupee sign. The probe and the Reader at clause 2.2 do.
- Y: `ConfidenceBand` shows calibration only when the data gives it, and the hard-coded "214 examples from 48 contracts" line is gone.
- Z: shared components lose the controls that did nothing (the "Read the section" button, the statute tag as a button, a Close button with no handler).

Deferred, with owners (the full table is in 17.2 and 17.3): LCP and CLS for `/` (FE-R), the header primary button (FE-4), the footer Credits link (FE-6), the 4 px rule on seven more components (FE-4 to FE-6), the squeezed category names and the 12 by 3 px ruler ticks (FE-5), tabular numerals on counts (FE-4, FE-6), the Reader's confidence popover keeping its open state across selections (FE-5) and `--stagger`, still unused (FE-5).

Verification. Run fresh on the final build:
- `pnpm install --frozen-lockfile`: already up to date. `pnpm typecheck`: exit 0. `pnpm test`: 20 of 20 pass (7 reveal, 8 colour tokens, 5 hero fixture), 0 failed, 0 skipped. `pnpm build`: 162 modules, exit 0, no warnings.
- Bundle: the index chunk is 239.47 kB (72.61 kB gzipped), the `/start` chunk 3.96 kB gzipped and the Reader chunk 13.46 kB gzipped. The landing route loads six script files, 121.4 kB gzipped in all, 7.3 kB of CSS and five fonts at 136.6 kB. That is 22 kB under the FE-0 figure of 143 kB.
- `dist` holds no `googleapis` or `gstatic` reference. With `EVIDENCE` set to `null`, `dist` holds none of "Evidence you can check", "evidence-title", "look it up yourself" or "EvidencePassage". The calibration grep prints nothing over `frontend/src` and `frontend/dist`.
- The tool-name grep, the Rules section 1 scrub over `backend/`, `frontend/` and `docs/app/`, and a node scan for en and em dashes over `frontend/src`, `frontend/public`, `frontend/index.html`, `docs/app` and `README.md`: no output, no match. The scan was checked against a file that holds both dashes, and it found both. No `console.log`, `debugger`, `TODO` or `FIXME` in `frontend/src`.
- `git status --short` lists no path under `frontend/node_modules`, `frontend/dist` or `frontend/.screens`. No git write command was run.

Measured earlier in this part, on the build before the last copy edits, the removal of the two dead buttons and the link alignment fix. Those edits can change where text wraps and move the Accuracy link 16 px, and nothing else in layout or motion:

- With a fake passage the Evidence section rendered after § 2 and the later marks ran to § 7. The constant went back to `null`, the file matched its backup byte for byte, and the rebuilt bundle had the same file hash.
- Landing page: one `h1`, no skipped heading level, 26 controls with names, no horizontal overflow, no text under 12 px, no console output, one host. Two targets are under 44 px and both are links inside running text, which WCAG 2.5.8 exempts.
- Hero: the privacy line ends at 619 px at 375 by 667 and the primary button starts at 455 px. At 1280 by 720 the sheet and panel start at 550 px and the excerpt shows. The run is still until 600 ms, inks in 600 to 1000, ticks 1000 to 1200 and rises 1200 to 1520 ms. Hover or focus pauses it, "Next example" is not frozen by its own hover, and reduced motion draws the final state at once.
- Reader after the shared changes: 22 found marks and 3 review marks draw with the two-layer background (2 px underline, tint, repeating dash on review marks). The band label opens "Calibration: category-specific" on Non-Compete and "Calibration: pooled" on the review finding. Case law keeps its section and its empty state. Close panel is present and no "Read the section" button shows.
- Fonts: the rupee sign rendered in the Source Serif 4 web font on a probe in the hero paragraph and on the Reader at clause 2.2. With the Latin-extended files blocked it fell to Georgia.

Not verified: LCP and CLS for `/`. The browser pane records no paint while its window is hidden, and the capture script could not be rerun. The Reader was not captured at five widths, so its marks and band were checked by structure and computed style, not by eye. The headless captures predate the last copy edits, the removal of the dead buttons and a 16 px alignment fix on the "See the Accuracy page" link. The dev server was not started in this part.

Screenshots: 30 files in `frontend/.screens/FE-3/`, gitignored. They are `home-` and `start-<width>-<theme>.png` at 375, 768, 1024, 1280 and 1440 in light and dark, five `hero-seq-` frames at 1280, `hero-example-2` and `-3`, `hero-fold-` at 1280 (dark) and 375 (light) and `hero-reduced-motion`.

ponytail-review: no P1. Three P2 fixed, four kept:
- Fixed: the `onClick` prop and button branch of `StatuteTag` and the `onRead` prop and button of `RuleFlagCard`, which nothing passed, so both are gone. Fixed: `UploadFragment` and the `SAMPLE` constant, each used once, are inlined. Fixed: the local `Fragment` component shared a name with React's, and is now `Specimen`.
- Kept: `Evidence.tsx` and its constant are unrendered code, by request (D7). `--stagger` has no user until FE-5. The five Latin-extended `@font-face` rules repeat one `unicode-range`, because CSS cannot take a variable there. `MarginRuler` has two switches (`viewport={false}` and `caption=""`) for one caller, the hero, which is smaller than a variant prop.

Found along the way, not fixed: the heading "Nothing is kept after your session" sits above a body that says the contract is deleted within 60 minutes (8.2 wording, open for Aryan, listed in 17.3). In the browser pane, a click on "Start review" changed the address to the review route and the page stayed on the form until a second route change. It did not happen in headless Edge, and the pane's window was hidden, so it looks like throttling. It has not been reproduced in a visible browser. A full-page capture drops the finished ruler tick unless animations are off, while a viewport capture and a DOM probe both show it painted. That is treated as a capture artefact and its cause is not isolated.

Blockers: none. The LCP gap and the capture rerun need Aryan's call (17.3).

Next action: commit FE-3 with `feat(frontend): rebuild landing with live hero demo`, then reply `next` to start FE-4 (the `/start` stepped flow, reducer test first).
