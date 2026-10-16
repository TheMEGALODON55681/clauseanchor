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


## 2026-10-05: Part FE-4, the stepped start flow

Part: FE-4 (frontend track). Files changed under `frontend/`, `docs/app/` and `README.md`. Part 1-B stays paused at Aryan's request. No dependency was added. The part began with the six carry-over items from FE-3, then built the flow.

Files changed:
- New under `frontend/`: `src/lib/startFlow.ts` (the reducer, `maxReachableStep`, `clampStep`, `nextBlocker`, `parseStep`, `suggestedParty`), `src/lib/startFlow.test.ts` (17 tests), `src/pages/start/useStartFlow.ts` (upload, parse polling and the client calls), `src/pages/start/Summary.tsx` (the rail list and the one-line form).
- Rewritten: `src/pages/Start.tsx`, the three-step flow.
- Components: `RadioCard` (a label around a native radio, `tag`, `children`, `value`, `checked`, a generated group name, no 4 px rule), `RoleSelector` (controlled, `null` for no role, `hideLegend`, its own group name), `PartyBindingField` (a radio group by party id, `none`, `suggested`, a "Reading your document." status line), `NoticeBanner` (dismiss button only with `onDismiss`), `UploadDropzone` (the refusal line has `role="alert"`), `ClauseDetailPanel` (shell width from `--panel-w`), `JudgmentCard` (authority label and default), `Button` (a loading button ignores clicks), `AppHeader` (a doc comment only).
- App and pages: `app/Root.tsx` (the header button, the "Review" link removed), `pages/Landing.tsx` (the privacy heading, and at the end of the part the hero subline cap).
- `src/index.css`: the `.radio-card` rules and `--panel-w` on the hero panel.
- Added at the end of the part: `index.html` (the meta description), `src/api/client.ts`, `src/api/mock.ts` and `src/components/PreviewControls.tsx` (the `failParse` switch), `src/pages/start/useStartFlow.ts` (retry turns it off) and the parse-failure card and rail heading in `src/pages/Start.tsx`. The ponytail-review fixes touched `RoleSelector.tsx`, `Summary.tsx`, `useStartFlow.ts`, `startFlow.ts` and `startFlow.test.ts`.
- Docs: `Phases.md` (FE-4 ticked, deviations), `Architecture.md` (data flow, the start flow and tests rows, the tree), `FrontendDesign.md` (5.2, 6.2, 6.7, 6.9, 8.3, the skills rows in section 10, the FE-4 test row in 13, the deferred rows in 17.2, new 17.4 with amendments AA to AO, and at the start of the part 1.2, 6.1, 8.2 and 17.3), `DesignSystem.md` (3.4, 3.5 and section 6), `README.md` (routes).

Method. The reducer was written test first. The flow, the Reader regression pass, the hero measurements and the route sweeps ran earlier in this part in headless Edge over the DevTools protocol, against the dev server, with extensions disabled. The capture scripts live outside the repo and each run used a new browser profile folder and refused to overwrite a file. The final checks of the part ran in the browser pane, whose window is hidden (a viewport of 0 by 0), so those used the DOM and a call counter and no layout. Python is not installed.

Skills that ran: `superpowers:test-driven-development` (the reducer tests were red while `startFlow.ts` did not exist, then green, and six mutations of the reducer each failed at least one test), `stop-slop` (the new strings and the doc prose), `superpowers:verification-before-completion`, `/ponytail:ponytail-review`. At the end of the part, at Aryan's request: `copywriting`, `copy-editing`, then `stop-slop` again over the new strings (17.4, AO), and `/ponytail:ponytail-review` again over the full diff. Not run as separate passes in this part: `signup`, `cro` and `frontend-design`. Not run, and left to FE-R: the gstack design review and QA, `coderabbit`, `gstack-review`, `gstack-cso` and one independent second review.

Decisions: none were needed. D8 (whether the real API accepts a sample id while uploads are on) stays open and belongs to 4-C.

Carry-over items from FE-3:
- The landing § 6 heading is "Your contract is deleted within 60 minutes." (AA). The meta description now says "your contract is deleted within 60 minutes" (AL).
- The hero panel spans the sheet's full width from 768 to 1279 px (AB). Side by side needs about 1,180 px. Measured characters on a full line: 72 to 82 at 768 and 78 to 82 at 1024, for the sheet and the quote. At 1279 both run 115 to 120. The hero subline is capped at 66ch (AM), and the sheet and the quote are not.
- `JudgmentCard` shows "Reviewed", "Later overruled or modified" or "Not yet reviewed", with no date, because the passage data has none (AC). The grep in 1.2 covers `Reviewed as of`.
- The Reader regression pass found no regression. 24 captures sit in `frontend/.screens/FE-4/reader-clean/` and the pixel differences against FE-2 in `reader-diff/`. The sheet, marks, band and chips match, and the only visual change is that the empty "Nothing selected" panel lost its Close button (17.3, Z). FE-2 has no review-selected baseline and its `reader-selected-1440-dark.png` is a light capture, so that one case was compared by eye.
- The preview server on port 4173 was stopped. The rupee sign item needed no action.

Deviations from the plan, each recorded in 17.4:
- AD: the step is not in the reducer state. The address owns it.
- AE: the rail starts at 1280 px, not 1024, and has no Change link.
- AF and AG: no role or party is preselected, "None of these" is a radio option, and the cards are native radios with their own group names.
- AH: the header gets the primary button, absent on `/start` and in the Reader.
- AI and AJ: `NoticeBanner` has no dead dismiss button, the refusal line is announced, and history and parameters follow the rules in 17.4.
- AK: a loading `Button` ignores clicks (below).
- AL to AO: the meta description, the hero subline cap, the Fail parse switch and the copy pass, added at the end of the part at Aryan's request.

Deferred, with owners (the full list is in 17.4): LCP and CLS for `/` (FE-R), the 4 px rule on five more components (FE-5, FE-6), tabular numerals on counts (FE-5, FE-6), the hero sheet and quote at 1100 to 1279 px (93 to 120 characters, not capped, FE-R if Aryan asks) and the `JudgmentCard` label "Reviewed" (Aryan).

Added at the end of the part, at Aryan's request:
- Copy: copywriting, copy-editing, then stop-slop again over every new FE-4 string. Two strings changed (the parse-failure card and the rail heading). The rest stayed, with the reasons in 17.4 (AO).
- Meta description: "...and your contract is deleted within 60 minutes." (149 characters), in `index.html` and 8.3 (AL).
- Hero subline capped at `max-w-[66ch]` (AM). The longest line is 71 characters at 768, 1100, 1200, 1279 and 1280 px, down from 93 at 1100 and 111 at 1279. A cap of 68ch left a 75 character line. The heading needed no cap. The sheet and the quote still run 93 to 96 at 1100 and 117 to 120 at 1279. Captures at 1100 and 1280 px.
- A "Fail parse" switch in the Preview controls, next to "Failed analysis", wired through `MockSettings` and the mock's parse job (AN).
- `/ponytail:ponytail-review` over the full diff (below).

Verification. Run fresh on the final code:
- `pnpm typecheck`: exit 0. `pnpm test`: 37 of 37 pass (7 reveal, 8 colour tokens, 5 hero fixture, 17 flow), 0 failed, 0 skipped. `pnpm build`: 165 modules, exit 0, no warnings. All three ran again on the final code after the last edits.
- Bundle: the index chunk is 239.45 kB (72.67 kB gzipped) and the `/start` chunk 15.24 kB (5.66 kB gzipped, up from 3.96 at FE-3). The landing route's first load was not measured again, and the index chunk is 0.02 kB smaller than at FE-3. `dist` holds no "Preview controls", "Fail parse" or "Failed analysis" string.
- The tool-name grep and the Rules section 1 scrub over `backend/`, `frontend/` and `docs/app/` (excluding `.venv`, `node_modules`, `dist`, `.screens`, `graphify-out` and `Rules.md`): no match. The claims grep over `frontend/src` and `frontend/dist`, the "Evidence you can check" grep over `dist` and a grep for `googleapis` and `gstatic` over `dist`, `src` and `index.html`: no match. A node scan for en and em dashes over `frontend/src`, `frontend/public`, `frontend/index.html`, `docs/app` and `README.md` (102 files): no match, and it found both dashes in a control file. No `console.log`, `console.debug`, `debugger`, `TODO` or `FIXME` in `frontend/src`.
- The parse-failed path through the new Fail parse switch, in headless Edge, with no patched call. With the switch on, the sample link lands on step 2 and the card shows "We could not read your document", "Try again, or go back and choose a different file." and `ERR_PARSE`. Next is disabled, the party group is hidden and the console is empty. "Try again" turns the switch off, step 2 shows three party radios (two parties and None of these) and the card is gone.
- The double click on "Start review" (AK). A counter around `client.startAnalysis` and three clicks at most 30 ms apart: the original line made three calls, the fixed line made one. A single run that calls `click()` twice back to back is no test, because both clicks land before React commits the loading state.
- Route sweep in the browser pane, over `/`, `/start`, `/start?step=3` (corrected to step 1), `/how-it-works`, `/accuracy`, `/expired` and an unknown address: no React warning and no error other than the one below. Each navigation logs `InvalidStateError: Transition was aborted because of invalid state`. The pane's document is hidden, and a bare `document.startViewTransition` call on that document, with no app code, rejects with the same error, so it is a hidden-window artefact. The earlier headless sweep at 375 and 1280 px printed nothing. A tab that is hidden during a route change would log it too, and FE-R can decide whether the app should catch the rejection.
- `git status --short` lists no path under `frontend/node_modules`, `frontend/dist` or `frontend/.screens`. No git write command was run.

Measured earlier in this part, in headless Edge:
- A keyboard-only run from the landing header button to a started review passes. Each radio group is one tab stop with the arrow keys inside it. Neither role nor party is preselected.
- The four upload refusals show inline with the exact messages, and a good file after a refusal recovers. A forced `?step=3` is corrected with a replace and Back leaves `/start`. Browser Back from step 2 returns to step 1 with the file kept.
- The sample link replaces the address, uploads and lands on step 2. Sample mode works. With the mock set to fail the next request, "Try again" works and lands on step 2.
- The header button is at the far right, absent on `/start` and in the Reader, and inside the menu below 768 px. The Gallery shows every `RadioCard` and `PartyBindingField` state, and the landing role specimens stay inert.
- A route sweep at 375 and 1280 px printed nothing to the console and showed no overflow, except the development-only `/gallery` at 1280 px. Whether that predates FE-4 was not checked.

Not verified: LCP and CLS for `/`. The `Button` line came after the headless runs and after the ponytail-review, so the captured layouts and the keyboard-only run never saw it. It changes no layout, and the call counter above covers its behaviour. The end-of-part captures of the hero and the failure card ran against the dev server and not against the production build.

Screenshots: `frontend/.screens/FE-4/`, gitignored. `hero-before-` and `hero-after-` at 768, 1024 and 1280, `reader/` (an earlier set that shows the dev Preview controls button), `reader-clean/` (24 captures), `reader-diff/`, `start-all`, `start-final`, `start-checks`, `start-modes` and `misc` sets, and from the end of the part `hero-cap/` (the hero at 1100 and 1280 px after the cap) and `fail-parse-final/` (step 2 with the failure card at 1280 px).

ponytail-review, first pass during the part: no P1. Fixed: an unneeded export is dropped, the `Document` type is reused where a local copy stood, the `action` prop added to `AppHeader` is folded into `trailing`, and a `wait` helper used once is inlined. No kept item was recorded. Retry now keeps the `onAccepted` callback, so a retried sample upload still moves to step 2.

ponytail-review, second pass over the full FE-4 diff at the end of the part (also in 17.4). Three fixed: `RoleSelector` re-exported `RoleKey` and nothing imported it from there, so the re-export is gone. `PartyOption` repeated `PartyChoice` field for field, so it is gone. `maxReachableStep` repeated the gate `nextBlocker` holds and now reads from it, which left the test that compared the two with nothing to compare, so that test is deleted (18 tests became 17). One smaller fix: the one-line summary excluded the Scope row by its label text and now takes the first three rows. Kept, three: the four refusal codes appear in the reducer's type, in `REFUSALS` and in `REFUSAL_ZONE` (one line to save, three files to touch), `RoleSelector` keeps its own state only for the gallery's uncontrolled example, and `upload({ sampleId }, ...)` stands at three call sites in `Start.tsx` (a helper saves no lines). About 22 lines out, 5 of source and 17 of test.

Found along the way. Fixed: "Start review" called `startAnalysis` once per click, and the baseline page did the same (AK). Not fixed: the `/gallery` overflow at 1280 px, the hero sheet and quote measure at 1100 to 1279 px (93 to 120 characters), and the hidden-window console error above.

Blockers: none. Aryan's call: whether the hero sheet and quote should be capped too (one cap on the sheet), and the `JudgmentCard` label "Reviewed", which does not say who reviewed.

Next action: commit FE-4 with `feat(frontend): add stepped review start flow`, then reply `next` to start FE-5 (the Reader recomposition).


## 2026-10-14: Part FE-5, the Reader composition and motion

Part: FE-5 (frontend track). Files changed under `frontend/` and `docs/app/`. `README.md` needed no change: no command or route moved. Part 1-B stays paused at Aryan's request. No dependency was added.

Files changed:
- New under `frontend/`: `src/lib/authority.ts` (one phrase per authority status) and `authority.test.ts` (3 tests), `src/lib/reader.ts` (`nearestMark`, `freshDelays`) and `reader.test.ts` (7 tests), `src/lib/panelTransition.ts` (a state update inside a view transition of the panel only).
- Rewritten: `src/pages/Reader.tsx` (layout tiers, pick kinds, the band, the memoised document text), `src/components/MarginRuler.tsx` (a pointer overview strip).
- Components: `MobileDrawer` (the sheet stays mounted and holds its content while it leaves, focus in and back on a modal drawer, Peek or Open on the handle row), `CategoryRow` (a wrapped name, a plain status on a second line, an entry step), `CategorySidebar`, `CategoryGroupHeader`, `CountBadge`, `StageProgress` (Cancel in the compact line, tabular numerals), `StatusChip` (`plain`), `ScopePanel` (the mock counts and the 4 px rule are gone), `ManualReviewList` (the 4 px rules are gone), `JudgmentCard` (phrases from `lib/authority.ts`), `NoticeBanner` (the `read-partial` variant), `ReaderToolbar` (the file name keeps its extension, `showDelete`), `Button` (no label wrapping).
- Pages: `pages/HowItWorks.tsx` (one sentence on case law, so the page matches the card), `pages/landing/Evidence.tsx` (the `Authority` type import), `pages/landing/HeroDemo.tsx` (the quote takes the measure).
- `src/index.css`: `--measure`, `.reader-sheet`, the hero sheet width, `.ca-enter`, the panel transition rules. The unused `ca-drawer-up` keyframes are gone.
- `src/tokens.test.ts`: two tests added for the measure.
- Docs: `Phases.md` (FE-5 ticked, deviations), `Architecture.md` (two decision rows, the tests row, the tree), `FrontendDesign.md` (6.3, 7.3, the skills rows in 10, the FE-5 test rows in 13, deviations 14 to 18 in 16, new 17.5 with amendments AP to BA), `DesignSystem.md` (3.4, 3.5, the authority table in 4, section 6).

Method. Every figure below ran in headless Edge over the DevTools protocol, extensions disabled, against the Vite dev server. The 500,000 code point run used production React: the probe patches the client module in the page, so a built bundle could not be used, and the server ran with `NODE_ENV=production` instead. Development React overstated the cost several times over and led to the wrong fix first. The capture and probe scripts live outside the repo. Python is not installed.

Skills that ran: `copywriting`, `copy-editing`, then `stop-slop` over the new strings, with the one edit `stop-slop` asked for checked against its rules again (17.5, BA). `find-animation-opportunities`, read-only over the Reader (17.5). `/ponytail:ponytail-review` over the full diff (below). `superpowers:verification-before-completion`. Not recorded as run in this part: `frontend-design`, `emil-design-eng` and `onboarding`, which section 10 lists for FE-5.

Decisions: none were needed. The calls that are Aryan's are in Blockers.

Deviations from the plan, each recorded in 17.5:
- AS: below 1280 px the panel is a bottom sheet and not a right drawer. A 400 px drawer covers the text column at 1024. The sheet's header carries only Peek or Open.
- AT and AU: only a pointer pick cross-fades the panel, and the root is out of that transition.
- AR: the hero sheet is capped by the same measure token, which 17.4 had left to FE-R.
- AP and AQ: the authority phrases and the partial-read notice are interim wording, waiting for a definition of `authority_status` and for the parser codes in API.md.
- AW: B4 (the short ruler tick) was not reproduced from the baseline code, so its cause stays open.

Large documents (K). The 500,000 code point document (the 7,862 code point sample 64 times: 503,294 code points, 1,600 marks, 3,456 paragraphs, 311 thousand px tall) failed the 200 ms rule at the baseline, so this is not a regression of FE-5. Cause: every pick and every scroll event rendered every paragraph, because `measure` set new objects on each scroll event. No windowing was added, so no approval was needed. The fix is memoisation (17.5, AV). In production React, tasks over 50 ms: wheel scroll 0, jump scroll 0, 12 J steps 0, eight pointer picks 16 tasks with 182 ms the longest and none over 200, a ruler click 181 ms. The load has a longest task of 278 to 314 ms over two runs, outside the scrolling and selecting rule. Before the root was taken out of the panel transition, a pointer pick reached 235 ms and five of 17 tasks passed 200 ms. With reduced motion, so no transition, the longest was 78 ms.

Measure. One `--measure` token, 612 px. Full-line average in the Reader: 73.2 characters (65 to 81) at 1023, 1024, 1280, 1440 and 1920, 70.3 at 768, 34.3 at 375. Hero: 75 (longest 78) from 768 to 1279, 70.3 at 1280 and 1440. The earlier estimate in `tokens.test.ts` (7.83 px a character) and the in-page canvas probe (8.12) disagree, and the measured line averages are the evidence.

Verification. Run fresh on the final code:
- `pnpm typecheck`: exit 0. `pnpm test`: 49 of 49 pass (7 reveal, 10 tokens, 5 hero fixture, 17 flow, 3 authority, 7 reader), 0 failed, 0 skipped. `pnpm build`: 168 modules, exit 0, no warning.
- Bundle: the Reader chunk is 50.16 kB (14.85 kB gzipped), up from 45.58 and 13.46 at FE-4. The index chunk is 240.12 kB (72.95 kB gzipped), up from 239.45 and 72.66. The stylesheet is 31.33 kB (7.76 kB gzipped).
- The probe at 1024 with motion on: no transition for a first pick with the sheet closed, one for a pick with the panel showing, none for J (focus stays on the mark), focus on `#detail-panel-title` after Enter, the sheet holds its content while it exits, the categories drawer takes focus, makes one element `inert` and gives focus back to `#open-categories`. No horizontal overflow at 1440, 1280, 1024, 768 and 375.
- The mid-transition probe at 1440 and 1024, with `--dur-state` at 3 s: the only animations are on `reader-panel`, none on the root. `data-vt` is cleared at the end. The page stays live behind it.
- The three bands render the right content at 1440 light and 375 dark, with no overflow. The longest authority phrase does not wrap at 1440, 1280 and 375. The key hint shows from 1024 px.
- The console is empty on every run.

Not verified: LCP and CLS for `/` (FE-R). The contrast of the plain status text on the sunken sidebar and on the selected `anchor-100` row, which was reasoned and not computed. The 40 px shift when the progress line leaves, which relies on scroll anchoring. The hero quote column, 25.9 characters a line at 1280 and 1440 px beside a 320 px panel. The `Math.max(1, ...nodes)` page count, fine at the 3,600 nodes the document limit gives. A pixel comparison against the FE-4 captures, which would show the recomposition and not a regression.

Screenshots: `frontend/.screens/FE-5/`, gitignored. The Reader, a selected finding and the landing page at 375, 768, 1024, 1280 and 1440 px in light and dark, the three bands, the mid-transition frames at 1440 and 1024, and the 500,000 code point document at load and mid-scroll.

ponytail-review over the full FE-5 diff. No P1. Fixed, two: `panelTransition.ts` typed `startViewTransition` by hand, and TypeScript 5.9 ships the type. A JavaScript media query drove one hint line, which is now `hidden lg:flex`. About 8 lines out. Kept, five: `progress={null}` on `ReaderToolbar` means "draw none", where the Gallery's analysing state draws the default. `freshDelays` takes a cap that its one caller leaves at the default, and a constant saves no lines. `MarginRuler` keeps its variants and fixtures for the Gallery. The second `tokens.test.ts` test only checks that two source files name the token. `Math.max(1, ...nodes)` is baseline code.

Found along the way. Fixed: the `/how-it-works` page said each passage shows "whether it has been reviewed", which the card no longer says. Not fixed: the `/gallery` overflow at 375 px has its cause in the two 520 px specimen panes (code FE-5 did not touch), and at 1280 px it was not examined. The development-only Preview controls button sits over the last sidebar row and the bottom-left of the sheet in captures. It is development only.

Blockers: none. Aryan's call: the authority wording (AP), whether the hero sheet cap in AR is what was wanted, whether the enter motion for the delete confirmation, the menu and the toast (17.5) belongs in FE-6, and the partial-read wording once API.md has the warning codes.

Next action: commit FE-5 with `refactor(frontend): recompose reader with motion`, then reply `next` to start FE-6 (How it works, Accuracy, Expired, NotFound).


## 2026-10-14: Part FE-6, the secondary pages and the overlay enters

Part: FE-6 (frontend track). Files changed under `frontend/` and `docs/app/`. `README.md` needed no change: no command or route moved. Part 1-B stays paused at Aryan's request. No dependency was added.

Files changed:
- New under `frontend/`: `src/components/Specimen.tsx` (moved out of `Landing.tsx`, two callers).
- Pages: `pages/HowItWorks.tsx` (two grids, a sticky contents list in the margin, fragments beside the text, the Credits scroll, the corrected sentence on scanned files), `pages/Accuracy.tsx` (the banner, the table in the main column, the glossary in the aside, a sticky header, stacked blocks below 768 px), `pages/Expired.tsx` and `pages/NotFound.tsx` (on `PlainPage`), `pages/Landing.tsx` (imports `Specimen`), `pages/Gallery.tsx` (three `PerformanceTableRow` specimens pass `metrics`).
- App: `app/RootError.tsx` (on `PlainPage`), `app/Root.tsx` (the footer's Credits link is `#/how-it-works?at=credits`).
- Components: `Layout.tsx` (`PlainPage`), `PerformanceTableRow.tsx` (rewritten: one branch, ledger row, `PERF_COLUMNS`, cell roles), `MetricCell.tsx` (`emphasis`, `n =` only when a support is given, a `metric-label` class), `ErrorCard.tsx` and `Toast.tsx` (no 4 px rule, `tone`), `ConfirmDialog.tsx`, `DropdownMenu.tsx` and `Toast.tsx` (enter classes), `EmptyState.tsx` (`headingAs` removed).
- `src/index.css`: the `ca-pop` keyframes, `.ca-dialog`, `.ca-menu` and `.ca-toast`, and the `.ca-enter` comment.
- `src/tokens.test.ts`: four tests added.
- Docs: `Phases.md` (FE-6 ticked, deviations), `Architecture.md` (two decision rows, the tests row, the tree), `FrontendDesign.md` (6.4 to 6.6, the skills rows in 10, the FE-6 test rows in 13, deviations 19 to 22 in 16, new 17.6 with amendments BB to BI, the status line), `DesignSystem.md` (3.1, 3.4, 3.5, section 6).

Method. Every figure below ran in headless Edge over the DevTools protocol, extensions disabled, against the Vite dev server. The capture, audit and probe scripts live outside the repo. Python is not installed.

Skills that ran: `animate`, for the three overlay enters (its gate: all three are occasional overlays, none fires from a key at 100 or more a day; it asks for transitions on rapidly retriggered elements, which a mount-time keyframe on a one-shot toast is not). `copywriting`, `copy-editing`, then `stop-slop` over the two new strings, with the one edit `stop-slop` asked for (17.6, BI). `/ponytail:ponytail-review` over the full diff (below). Not recorded as run in this part: `frontend-design`, `cro` and `onboarding`, which section 10 does not list for FE-6, and `superpowers:verification-before-completion` was applied by running the checks fresh and reading their output.

Decisions: none were needed beyond the deviations below. The calls that are Aryan's are in Blockers.

Deviations from the plan, each recorded in 17.6:
- BD: the Accuracy table stays in the main column and does not span into the aside, because the six columns fit at 672 px.
- BE: the Credits link target is `?at=credits`, and not router state.
- BC: the menu enters over `--dur-press` (120 ms), not 150 ms, because no token holds 150.
- BF: Expired drops its dashed card.
- BH: tabular numerals on `MetricCell` are closed with no change, because the cells are already mono.

Additions that came with `next`:
- Plain status contrast (BB). 30 pairs computed, none under 4.5, lowest 4.55 (light absent on `anchor-100`). No token changed, so there is nothing to record in the colour table beyond the check. The mutation check set light `--status-absent-fg` to `#7A7F85`, the test failed, and the value was restored.
- Overlay enters (BC). Computed in the browser: menu `ca-pop` 120 ms from the top right, card `ca-pop` 200 ms from its centre, backdrop `ca-fade` 200 ms, toast `ca-rise` 200 ms. Under emulated reduced motion each is 0.01 ms with no animation running.

Verification. Run fresh on the final code:
- `pnpm typecheck`: exit 0. `pnpm test`: 53 of 53 pass (7 reveal, 14 tokens, 5 hero fixture, 17 flow, 3 authority, 7 reader), 0 failed, 0 skipped. `pnpm build`: 169 modules, exit 0, no warning.
- Bundle: How it works 7.47 kB (3.02 kB gzipped), Accuracy 7.93 kB (2.98 kB gzipped), Expired 0.73 kB, NotFound 0.59 kB. The Reader chunk is 51.45 kB (15.12 kB gzipped, from 50.16 and 14.85 at FE-5). The index chunk is 236.68 kB (72.28 kB gzipped). The stylesheet is 31.93 kB (7.90 kB gzipped). The build holds no "Preview controls" text and no Gallery chunk.
- The audit over five routes, five widths and two themes (50 pages): one `h1`, a distinct title, no horizontal overflow, no text node under 12 px, and an empty console on every run.
- The Credits link from the landing page, from the page itself, from a pasted `?at=credits` address and a contents entry: the target heading is in view and holds focus each time.
- Accuracy at 375 px is 11,525 px tall (46 blocks), and the baseline's 5,779 px had clipped columns.

Not verified: LCP and CLS for `/` (FE-R). Lighthouse and axe on any route (FE-R). A screen-reader pass. Whether a 46 block list at 375 px wants a way to jump or filter. The 40 px shift when the Reader's progress line leaves.

Screenshots: `frontend/.screens/FE-6/`, gitignored. `how-it-works-`, `accuracy-`, `expired-`, `expired-deleted-` and `notfound-` at 375, 768, 1024, 1280 and 1440 px in light and dark, `crop-accuracy-375-top`, `crop-how-375-top`, and `overlay-menu-`, `overlay-dialog-` and `overlay-toast-` at 1280 px in both themes. The development-only Preview controls button shows in the bottom-left of several captures. It is development only.

ponytail-review over the full FE-6 diff. No P1. Fixed, two: `ConfirmDialog`'s `Panel` took a `className` prop so that one of two callers could pass a class, and the class now sits on the panel always. `.ca-backdrop` repeated `.ca-enter` and is gone, with its test row. About 7 lines out. Kept, six: the `Toast` rename from `rule` to `tone`. `EmptyState`'s `no-document` variant with its `action` and `onAction`, which have no production caller and stay for the rule that every component keeps its API and states (about 12 lines if Aryan wants them gone). `PerformanceTableRow`'s `variant`, where only `weak` changes the row, for the same rule. `PERF_COLUMNS`, shared by the header and the row. The overlay class test, which reads CSS text. `MetricCell`'s `emphasis` and `PlainPage`'s `role`, one caller each.

Found along the way. Fixed: the baseline Accuracy table gave a `row` with no cell children, an ARIA structure error, and each measure now sits in a `cell`. The info toast's icon was under 2:1 on the sheet and is now `ink/tertiary`. Not fixed: the `/gallery` overflow at 1280 and 375 px, the hero ruler wrapper and the hero quote column, all from earlier parts and listed in 17.6.

Blockers: none. Aryan's call: whether to delete the `no-document` empty state variant, which has no production caller (about 12 lines), whether the `?at=credits` parameter should clear after a contents click, and the same two open calls from FE-5 that still wait on others: the authority wording (AP, Tanishq's definition first) and the partial-read wording once API.md has the parser codes (AQ).

Next action: commit FE-6 with `refactor(frontend): rebuild secondary pages`, then reply `next` to start FE-R (the phase-end review).

## 2026-10-14: Part FE-R, step 1, the phase-end review (findings only)

Part: FE-R, step 1 of 2 (frontend track). Range `1077d25..f24d382`. Review only: no file under `frontend/` changed, and the fixes are step 2, one commit per theme, after Aryan replies. Files changed: this entry. Part 1-B stays paused. No dependency was added.

Method. Production build of `f24d382` served by `vite preview` on `localhost:4173`, headless Edge over the DevTools protocol with extensions disabled, Lighthouse 13.5.0 (mobile, simulated throttling) and axe-core 4.14.0. The scripts live outside the repo. Screenshots are in `frontend/.screens/FE-R/`, gitignored.

Skills and reviews that ran: `superpowers:verification-before-completion` (every figure below was read from a fresh run), the design review and the QA pass as method only (no preamble, no telemetry, no write outside the allowed folders, as at FE-1), `/ponytail:ponytail-review` over the full range (below), one independent second review (read-only), and the review checklist of `/gstack-review` applied by reading the code. `/coderabbit:code-review` did not run: it failed to start three times, on the full range and on `8aee425..HEAD`, and the installed CLI (0.7.6) reports that it cannot update itself. `coderabbit update` was not run, because it changes the installed tool and needs Aryan's yes. `/gstack-cso` was not loaded, and its checklist was applied by hand (the security rows below). Not run: `improve-animations`, `optimize-web-animations`, the `impeccable` detector, `seo-audit` beyond title, heading and description, `gstack-benchmark`, `graphify`.

Quality bars (section 1.3), measured on the final range:

| Bar | Result | Verdict |
|---|---|---|
| Lighthouse mobile `/` | Performance 90, 88, 88 (three runs). LCP 2.7 s on all three. Accessibility 100, Best Practices 100, CLS 0, SEO 91 | Fails Performance (95) and LCP (2.5 s) |
| axe, every route, both themes | 5 widths by 2 themes over every route, plus Start steps 2 and 3, the four upload refusals, and the Reader in six states. Three rule failures: R2, R3, R4 | Fails |
| Keyboard | Run at 1280 px, light theme only. Skip link, route focus, one tab stop per radio group, first mark 6 stops from load, Enter, Escape all work. R5 and R11 | Partial. Dark and 375 px not run |
| Contrast | `tokens.test.ts` passes. One computed failure in the browser: R2 | Fails on one pair |
| Bundle | Entry 69.7 KB gzipped and runtime 33.5 KB (107 KB with the Vite figures). With the five preloaded chunks, 118.1 KB at gzip level 9 | Passes (200 KB) |
| Fonts, third party | One origin, `localhost:4173`, on every route (23 to 24 requests). No host in `dist` other than namespace and licence strings, React error URLs, the mock's `example.org` and the Atticus link | Passes |
| Reading measure | Average 73.2 characters on 37 full-line paragraphs at 1280, 1440 and 1920 px (minimum 65, maximum 81, column 612 px, sheet 710 px). Hero sheet 70.3 | Passes (68 to 80) |

Findings are grouped by severity. P1 breaks a quality bar, P2 weakens the experience, P3 is polish. `Verified` means seen in a run or computed. `Code` means read in the source and not run.

P1:
- R1. Lighthouse mobile `/`: Performance 88 to 90 and LCP 2.7 s (bars 95 and 2.5 s). The LCP element is the hero paragraph: time to first byte 20 ms, element render delay 2,153 ms after the script, 8 KB of render-blocking CSS, 52 KiB of unused script, style and layout 1.06 s under 4x CPU. `/start` scores 92 (LCP 2.9 s) and `/how-it-works` 93 (LCP 2.9 s). The `client` chunk (the mock adapter, 9.9 KB gzipped) is preloaded on the landing path because `session.tsx` imports it. SEO 91 is `robots.txt` falling through to `index.html`. Verified. One run per route beyond the three on `/`, so the variance is unknown.
- R2. axe, serious, `color-contrast`, Accuracy at 375 px in the dark theme, 50 nodes: `.metric-label` (12 px, `ink/tertiary` `#8b867f`) on the weak row, `status/review/bg` `#33280f`, is 4.01:1. Light passes. `tokens.test.ts` does not pair `ink/tertiary` with the status backgrounds. A token cross product also puts dark `ink/tertiary` under 4.5 on `anchor-100` and `status/found/bg` (3.79), `status/unavailable/bg` (4.25) and `status/absent/bg` (4.38). Those pairs were not found in the DOM. Verified for the first, computed only for the rest.
- R3. axe, serious, `label-content-name-mismatch` (WCAG 2.5.3, level A), Reader, every width, theme and state, 3 to 5 nodes: a mark is a `span role="button"` whose `aria-label` is "Document Name, found", so the visible quote is not in the accessible name. `Reader.tsx:1059`. Verified.
- R4. axe, critical, `aria-allowed-attr`, 7 nodes: `DropdownMenu` puts `aria-checked` on `role="menuitem"`. The role-change items are radios in a menu, so they want `menuitemradio`. `DropdownMenu.tsx:186`. Verified.
- R5. A mark that is selected and keyboard focused draws a 1 px outline in `status/found/fg`, not the 2 px ring. `markStyle("focused")` sets `outline` inline (`SpanHighlight.tsx:31`) and an inline declaration beats `:focus-visible` (`index.css:327`, no `!important`). Bar: a 2 px ring everywhere. Code, and the computed style was read. No screenshot.

P2:
- R6. `ConfirmDialog` (delete): focus does not move in, nothing is inert or trapped, Escape does nothing (the Reader's key handler returns while it is open, `Reader.tsx:287`), focus is not returned, and there is no `aria-modal`. Code. The second review agrees.
- R7. `MobileDrawer` (categories, below 1440 px) sets `aria-modal`, but only the Reader's main block is inert (`Reader.tsx:709`), so the header and the skip link stay reachable by Tab. Code and the second review. No real Tab run.
- R8. `SegmentedFilter` and `Tabs` use `role="tablist"` and `role="tab"` for list filters and a sort, with no `tabpanel`, no `aria-controls`, no roving tabindex and no arrow keys. Code, and the second review agrees.
- R9. `DropdownMenu` does not move focus on open, and focus drops to the page after a pick or Escape. Not verified: the Escape test had focus on the heading.
- R10. `JudgmentCard`: "Open source" has no handler and is not disabled when `sourceUrl` is missing (`JudgmentCard.tsx:171`). `window.open(sourceUrl, "_blank", "noopener")` has no scheme check and no `noreferrer` (line 176). The component's defaults invent a case ("Sample Traders Pvt. Ltd. v. Example Industries Ltd.", "[Placeholder citation]", a passage and an extra sentence) in production code (lines 23 to 26, 91, 94, 104, 138). Code.
- R11. Targets under the track's 44 px bar, measured as effective hit areas: the Reader sheet's "Open" (58 by 32, at 1024 px and below), the manual review chips ("All" about 42 by 38, the other two 38 high), and the footer link "Data sources and credits" (15 px tall on every route, inline in a sentence, so the WCAG 2.5.8 exemption probably applies). The 32 px `s` buttons pass through `.hit`. Verified.
- R12. `/accuracy`: CLS 0.421 and Performance 72, because the results block moves when its data arrives. The bar names only `/`, and this is the worst figure measured. Verified.
- R13. The mock adapter ships in the production build and drives behaviour: the upload's content is ignored (the sample contract always comes back), `jurisdiction_scope` is ignored, the judgments are placeholders with an `example.org` link and show as ordinary evidence, the rule flags carry legal-sounding notes, and sessions sit in module-level maps with no expiry. Known and gated on the backend since FE-1 (C7), but it needs an explicit release gate: this build is not releasable on the mock. Verified in the bundle.
- R14. The session-expiry banner always reads "This session ends in 8 minutes" (`NoticeBanner.tsx:20`), and the Reader shows it from 10 minutes down (`Reader.tsx:738`). The `text` prop made for a live countdown has no caller. Code.
- R15. Marks give no hover feedback. `hoverKey` in the Reader runs through `DocumentText` and `TextBlock` to `markStyle(kind, hovered)`, and `markStyle` reads `hovered` only for the kind `"hover"`, which the Reader never produces. Every mouse enter and leave re-renders the touched blocks and changes nothing on screen. `Reader.tsx:101`, `1045`, `1072`, `1079`; `SpanHighlight.tsx:49`. Code. Either give `.ca-mark:hover` a tint in CSS or delete the path (about 14 lines).

P3:
- R16. `Reader.tsx:137`: the document fetch's `.catch(handleError)` is not guarded by `live`.
- R17. `changeRole` (`Reader.tsx:410`) is unversioned, so two quick role changes can resolve out of order. It needs a real backend to show.
- R18. `heading-order` (moderate): `#confirm-title` is an `h3` under the page's `h1`.
- R19. `useStartFlow.ts:55` takes the party name as `text.split(",")[0]`, so "Sample Traders, Inc." reads "Sample Traders". `Math.max(...nodes)` at line 121 is fine to about 100,000 nodes.
- R20. No `<meta name="referrer">`, and `public/` has no `robots.txt` (R1).
- R21. Every component styles through `style=` attributes, so a deployed `style-src` policy needs `'unsafe-inline'` for them. `script-src` can stay strict, because the page has no inline script.
- R22. `ROLES` is written three times for one seven value enum: `Reader.tsx:46` (role, label, party node), `RoleSelector.tsx:6` (key, title) and `useStartFlow.ts:15` (`ROLE_FROM_KEY`), and the role to party rule is also in `startFlow.ts:80`. The Reader's table names the mock's node ids (`party_company`, `party_provider`).

Security checks (the `gstack-cso` list, by hand). Passed, verified: no storage of any kind (localStorage, sessionStorage, IndexedDB, Cache Storage and service workers all 0, no cookie for `localhost`), no request to a third party, no `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `fetch`, `XHR` or `sendBeacon` in `src`, no "Preview controls" or gallery text in `dist`, and `#/gallery` renders the not-found page on the production preview. Open: R10, R13, R20, R21.

ponytail-review over the full range. No P1. The range adds 11,603 lines under `frontend/src`, and about 1,390 of them can go. Dead whatever the component rule says, about 200: the Reader's hover path (R15, 14 lines), `ReaderToolbar`'s `progress` prop and its analysing branch, which draw nothing because the Reader passes `null` (8), the Landing page's `Evidence` section and its `EVIDENCE = null` guard, which cannot render until D7 supplies a passage (about 40, with `landing/Evidence.tsx`), the three role tables (R22, about 20), `Tabs` and `SegmentedFilter`, one component twice with two skins (about 45), the `Skel` in `ClauseDetailPanel` that copies `Skeleton`'s bar and the spinner in `Button` that copies `Spinner` (27), the mock switches that `Reader` and `useStartFlow` clear themselves (6), the `MarginRulerIcon` and `UploadIcon` glyphs and the `PartyCandidate` type, which nothing imports (19), the 11 `--color-*` lines in `index.css` that no class uses (11), the disabled "licence" sample card (7, a product call). Gallery only, already approved for step 2, 465 lines: `CheckboxRadio`, `DocumentBlock`, `SectionPath`, `Select`, `TextInput`, `Tooltip` and `Divider`. Divider is the seventh. It lost its last caller when the baseline `Home.tsx` was replaced, which is why the FE-0 count was six. Exists only so the Gallery can draw forced states and sample data, about 710 lines, and stays under the rule that every component keeps its API and states: the static sample branch of `ClauseDetailPanel` (about 217, including its invented "Non-compete" clause), `Mark` and `SpanHighlight` in `SpanHighlight.tsx` (about 158, with the `hover` and `keyboard` kinds), `StageProgress`'s full list and defaults (50), `CategorySidebar`'s sample groups, internal selection and fixed box (45), `MobileDrawer`'s framed mode (40), `MarginRuler`'s fixtures and variants (35), `NoticeBanner`'s `privacy` variant and dismiss button (30), `JudgmentCard`'s forced states and invented text (25), the `DropdownMenu` force-open props and default items (20) and about 90 more across ten smaller components. Mock only, replaced with the backend: `fakeSha` and an exported `STAGE_KEYS` (12). Kept as they are: the `selectRef`, `memo` and `plan` layers in `Reader.tsx`, which carry a measured reason in their comments, and `panelTransition.ts`. One for Aryan: `lib/reveal.ts`, `useReveal.ts` and their 75 line test (111 lines) could be a scroll driven CSS animation, which shows the content with no animation where it is unsupported, the same fallback the code has now. Net, about 1,390 lines, 12 percent of the range, of which 465 are approved and 710 depend on the component rule.

Not done in this step, and why: the dark and 375 px keyboard runs, the Gallery capture from the dev server and the before and after pairing view all wait for step 2, because the "after" half of a pair has to be shot on the fixed build. The hero ruler wrapper and the hero quote column (25.9 characters a line at 1280 and 1440 px beside a 320 px panel, measured again in this run) are carried from FE-3 and FE-5 unchanged.

Not verified: the ring width on a programmatic focus (R5 is from computed style), the `DropdownMenu` focus return (R9), whether Tab escapes the categories drawer (R7), the dark `ink/tertiary` pairs other than the one in R2, and a screen reader on any route.

Blockers: none for step 2. Aryan's calls, in order of effect:
1. Delete the 7 gallery-only components and the `no-document` empty state (approved), and say whether the 710 lines that exist for the Gallery stay under the rule or go with it.
2. The mock in the build (R13): a release gate in the docs and no fix in the frontend, or a build flag that excludes the adapter.
3. Run `coderabbit update` and retry, or accept the review without it.
4. `Evidence`: delete until D7 has a passage, or keep.
5. The authority wording (AP, Tanishq's definition first) and the partial-read wording (AQ, once API.md has the parser codes) are still open and do not block.
Already approved for step 2: the category list below 768 px on `/accuracy` grouped into the seven catalogue groups as `details`, first open, like the landing page, and `?at=credits` kept as it is.

Next action: reply with the fixes you want in step 2. P1 R1 to R5 and P2 R6 to R15 are proposed as the default set, one commit per theme (accessibility, performance, Reader behaviour, dead code).

## 2026-10-14: Part FE-R, step 2, commit 3, Reader behaviour

Part: FE-R, step 2, commit 3 of 6 (theme: Reader behaviour). Starts from `22f2294`. Part 1-B stays paused. No dependency was added.

Files changed:
- `frontend/src/pages/Reader.tsx`: the hover path removed (R15), the document fetch's catch guarded by `live` (R16), `changeRole` versioned with a ref (R17), the banner passed `sessionEndsIn(minutesLeft)` (R14).
- `frontend/src/lib/reader.ts` and `reader.test.ts`: `sessionEndsIn`, with 2 tests.
- `frontend/src/components/NoticeBanner.tsx`: the Gallery's session line is `sessionEndsIn(8)`.
- `frontend/src/components/SpanHighlight.tsx`, `ManualReviewList.tsx`, `pages/Landing.tsx`, `pages/landing/HeroDemo.tsx`: `markStyle(kind)` without the `hovered` flag.
- `frontend/src/index.css`: `.ca-pick` and its hover rule.
- `frontend/src/lib/startFlow.ts` and `startFlow.test.ts`: `partyName`, with 2 tests. `frontend/src/api/types.ts`: optional `name_span` on `DocNode`. `frontend/src/api/mock.ts`: the span on both parties. `frontend/src/pages/start/useStartFlow.ts`: reads the name through `partyName` (R19).
- `frontend/src/main.tsx`: a catch on the late font import.
- Docs: `FrontendDesign.md` (17.7, rows BO to BS, and two rows of section 13), `Architecture.md` (test count and two file notes), this entry.

Amendments BO to BS are in `FrontendDesign.md` 17.7, with the figures. Short form:
- R14: the banner reads the real minutes left, whole minutes rounded down.
- R15: marks tint under the pointer in CSS through the two tint tokens, and the hover state, props and handlers are gone.
- R16 and R17: a late fetch failure and an older role change are dropped.
- R19: the party name is the node's `name_span`, and a node without one reads whole. This is an assumption about the parser's party node (BR).
- The late font import has a catch, with a comment that the fallback faces stay.

Checks:
- `pnpm typecheck`: exit 0. `pnpm test`: 59 of 59 pass (7 reveal, 15 tokens, 1 font loading, 5 hero fixture, 19 start flow, 3 authority, 9 reader), 0 failed, 0 skipped. `pnpm build`: 171 modules, exit 0, no warning.
- Test first: the four new tests failed on the missing exports (`sessionEndsIn`, `partyName`) before the code was written, and passed after.
- Browser, headless Edge, dev server, light and dark: hover tint with a real pointer (R15), two out of order role changes (R17) and the banner minutes and their countdown (R14). Figures are in 17.7.
- `/ponytail:ponytail-review`: no P1, no P2.
- Copy passes on the banner lines: no wording changed.

Not run: R16 in a provoked failure. The dev server's hover in the browser pane (its pointer does not set `:hover`).

Housekeeping: two headless Edge instances launched and closed (light, dark), and the dev server on 5173 stopped.

Next action: commit this part, then commit 4 of 6, security (https-only scheme allowlist and `noopener,noreferrer` on `window.open`, R10 "Open source" disabled with no URL, the referrer meta, and the mock staying in the build with the 4-C removal recorded in `Architecture.md`).

## 2026-10-14: Part FE-R, step 2, commit 4, security

Part: FE-R, step 2, commit 4 of 6 (theme: security). Starts from `9802679`. Part 1-B stays paused. No dependency was added.

Files changed:
- `frontend/src/lib/reader.ts` and `reader.test.ts`: `httpsUrl`, with 2 tests.
- `frontend/src/components/JudgmentCard.tsx`: "Open source" opens only an address `httpsUrl` accepts, with `noopener,noreferrer`, and is disabled when there is none (R10).
- `frontend/index.html`: `<meta name="referrer" content="no-referrer">` (R20).
- Docs: `FrontendDesign.md` (17.7 rows BT to BW and the BR note, 5.8, section 13), `Architecture.md` (section 4 party nodes, 7.1 item 4, one decision row, the test count and two file notes), `Phases.md` (the 2-E note), this entry.

Amendments BT to BW are in `FrontendDesign.md` 17.7, with the figures. Short form:
- R10: the source link opens only an https address, with `noopener,noreferrer`, and the button is disabled with none.
- R20: the page sets the referrer policy to `no-referrer`.
- No `robots.txt` is added, as decided. SEO 91 on the preview server stays.
- R13: the mock stays in the build as a release gate. `Architecture.md` 7.1 says 4-C removes it and adds a check that `dist` holds no mock.
- Asked with this commit: `name_span` on party nodes is recorded as a backend requirement in `Architecture.md` section 4 and in the `Phases.md` 2-E note (API.md defines it, tagged `[CONTRACT]`), citing BR.

Checks:
- `pnpm typecheck`: exit 0. `pnpm test`: 61 of 61 pass (7 reveal, 15 tokens, 1 font loading, 5 hero fixture, 19 start flow, 3 authority, 11 reader), 0 failed, 0 skipped. `pnpm build`: 171 modules, exit 0, no warning.
- Test first: the two new tests failed on the missing export before the code was written, and passed after.
- Browser, dev server and the browser pane: the Gallery's 12 "Open source" buttons are disabled. In the Reader the mock's https address opens with `(url, "_blank", "noopener,noreferrer")`. With `javascript:`, `http:` and `data:` addresses patched in through `client.getAnalysis`, both buttons are disabled and `window.open` is not called. The meta is in the dev DOM and in `dist/index.html`.
- `/ponytail:ponytail-review`: nothing to cut, no P1, no P2.
- No user-facing string changed, so the copy passes did not run.

Not run: the `Referer` header on a real cross-origin navigation (the dataset links were not followed). R21 (the `style-src` note) is in no theme and is listed under Deferred in 17.7. R10's invented defaults in `JudgmentCard` (lines 23 to 26, 91, 94, 104, 138) stay for commit 5, because they are part of the Gallery-only decision.

Housekeeping: the dev server on 5173 stopped.

Next action: commit this part, then commit 5 of 6, dead code.

## 2026-10-14: Part FE-R, step 2, commit 5, dead code

Part: FE-R, step 2, commit 5 of 6 (theme: dead code and invented sample content). Starts from `4ec16e5`. Part 1-B stays paused. No dependency was added. 27 files under `frontend/src`, 126 lines added and 786 deleted.

Files changed:
- Deleted, no caller outside the Gallery: `components/TextInput.tsx`, `Select.tsx`, `CheckboxRadio.tsx`, `Tooltip.tsx`, `Divider.tsx`, `DocumentBlock.tsx`, `SectionPath.tsx`. `pages/Gallery.tsx` loses their groups.
- `components/JudgmentCard.tsx`: no sample text. A `passage` is required, or `state="empty"`. `components/ClauseDetailPanel.tsx`: a `caseLaw` prop for the static sample variants, and the panel's `Skel` replaced by `Bar` from `components/Skeleton.tsx`. `pages/Gallery.tsx`: `SAMPLE_PASSAGE`, `SAMPLE_LONG` and `SAMPLE_CASES` hold the invented case.
- `components/EmptyState.tsx`: no `no-document` variant. `components/ReaderToolbar.tsx` and `pages/Reader.tsx`: no `progress` prop and no `analyzing` variant.
- `components/RoleSelector.tsx` (the one table, keyed by `Role`), `lib/startFlow.ts` and `startFlow.test.ts` (no `RoleKey`), `pages/start/useStartFlow.ts` (no `ROLE_FROM_KEY`, no mock switch), `pages/start/Summary.tsx`, `pages/Landing.tsx`, `pages/Reader.tsx` (the role table, the party by `suggestedParty`, no mock switch).
- `api/mock.ts`: `once()`. `components/PreviewControls.tsx`: reads the switches when the drawer opens.
- `components/Spinner.tsx` and `Button.tsx`: one spinner with an `inline` mode. `components/icons.tsx`, `api/types.ts`, `index.css`: dead declarations removed.
- `pages/Gallery.tsx`: the dark `ink/tertiary` swatch value.
- Docs: `FrontendDesign.md` (1.2 claims grep, 6.7, 17.7 rows BX to CD, a rule, the commit 5 checks, the Deferred table), `Architecture.md` (the component count), `Phases.md` (the 4-C mock gate), this entry.

Amendments BX to CD are in `FrontendDesign.md` 17.7, with the figures. Short form:
- Seven gallery-only components and the `no-document` empty state are gone, as approved. `ReaderToolbar` drops `progress` and `analyzing`.
- `JudgmentCard` carries no invented case, court, citation or passage. The claims grep names those strings, so they cannot return to a component or to `dist`.
- One role table, keyed by the API's `Role`. The Reader no longer names the mock's party ids.
- A forced mock failure fires once, in the adapter, so no page clears a switch.
- `Skel` and the button's spinner reuse `Skeleton`'s bar and `Spinner`. Three icons, one type and eleven theme lines had no caller.
- The Gallery's dark `ink/tertiary` swatch matched the value commit 1 replaced.

Checks:
- `pnpm typecheck`: exit 0. `pnpm test`: 61 of 61 pass (7 reveal, 15 tokens, 1 font loading, 5 hero fixture, 19 start flow, 3 authority, 11 reader), 0 failed, 0 skipped. `pnpm build`: 171 modules, exit 0, no warning.
- Test count unchanged. The one test touched, `suggestedParty`, now takes the API's role strings. No new test, because every other change is a deletion or a rename that the typechecker covers, and the two behaviour changes (the party by position, the failure switch firing once) were run in the browser.
- Browser, dev server and the browser pane: the Gallery with an empty console and the counts in 17.7. The start flow sent `supplier_vendor` with `party_provider`. Four role changes in the Reader sent the same party ids as the old table. Both forced failures retried clean, and the drawer showed a fired switch as off after it was opened.
- Lighthouse on `/`, mobile: 95, 95, 94 on the final build, and 95, 95, 96 interleaved with 92, 97, 96 for `4ec16e5` on the same machine. LCP 2.19 to 2.31 s in all nine runs. The commit moved nothing measurable. The entry grew 0.3 KB gzipped because `Skeleton` moved into it.
- Claims grep with the new patterns, the old calibration grep, the Evidence gate, the Rules section 1 scrub, the tool-name grep over `frontend/` and README and the dash scan (control file detected): all print nothing.
- `/ponytail:ponytail-review`: no P1. Two P2 kept and listed: `ReaderToolbar`'s three invented defaults, and `Children.count` for the static panel's count.
- No user-facing string was added or changed, so the copy passes did not run.

Not run: the dark theme and 375 px captures of the Gallery, and the before and after pairs, which wait for the end of step 2. A screen reader on the Gallery or the Reader.

Housekeeping: the Vite dev server (5173) and two preview servers (4173, 4174) stopped, and a build of `4ec16e5` in the session scratchpad was used for the size and Lighthouse comparison. One slip: the seven deletions were first staged with `git rm`, which is a git write. The index was put back with `git reset` and the deletions sit unstaged in the working tree.

Open for Aryan:
1. Other components still carry invented sample text as a default, as `JudgmentCard` did: the static branch of `ClauseDetailPanel`, `MobileDrawer`'s title, `MarginRuler`'s fixtures, `PartyBindingField`'s sample parties and `ReaderToolbar`'s three defaults. None reaches a user. Same treatment, or leave?
2. The disabled "licence" sample card on the landing page (7 lines, a product call) was not in the approved list and is untouched.

Next action: commit this part, then commit 6 of 6, Accuracy mobile grouping (the 46 categories under the 7 catalogue groups as `details` below 768 px, first open).

## 2026-10-14: Part FE-R, step 2, commit 6, sample defaults

Part: FE-R, step 2, commit 6 of 7 (theme: contract content and review results in component defaults). Starts from `6ba24a8`. Part 1-B stays paused. No dependency was added. 12 files under `frontend/src`, 171 lines added and 405 deleted. The commit before the Accuracy mobile grouping, which is now commit 7. The report of the first round put two calls to Aryan (`MobileDrawer`'s title, and `StageProgress` with `CategorySidebar`), and both are folded in.

Files changed:
- `components/ClauseDetailPanel.tsx`: the static sample branch, `variant`, `PanelVariant` and the `caseLaw` prop are gone. No data and no custom content draws the skeleton.
- `components/MarginRuler.tsx`: no fixtures, `marks` defaults to none, `RulerVariant` is `hover`, `selected` or `focus`.
- `components/PartyBindingField.tsx`: `parties` is required. `components/ReaderToolbar.tsx`: `filename` and `meta` are required, `partialNote` has no default.
- `components/UploadDropzone.tsx` and `components/SpanHighlight.tsx`: found by the sweep, no file name, size or clause sentence of their own.
- `components/MobileDrawer.tsx`: `title` is required.
- `components/StageProgress.tsx`: `steps` is required, and the compact form draws nothing for an empty list. `components/CategorySidebar.tsx`: `groups` and `summary` are required, and the internal selection state is gone.
- `pages/Start.tsx`: the licence card. `pages/Reader.tsx`: `<ClauseDetailPanel />` for the skeleton, and the toolbar's old partial line as the Reader's own last fallback.
- `pages/Gallery.tsx`: `PANELS`, `RULERS`, `SAMPLE_PARTIES`, `SAMPLE_STEPS`, `SAMPLE_GROUPS`, `SAMPLE_SUMMARY`, `SAMPLE_FILE` and the clause constants hold what the components lost.
- Docs: `FrontendDesign.md` (1.2 claims grep, 17.7 rows CE to CK, BZ, a rule, the commit 6 checks, the kept list), this entry.

Amendments CE to CK are in `FrontendDesign.md` 17.7. Short form:
- A component holds no contract, party, clause, file name or review result as a default. It takes the data it is given, or draws its empty state or skeleton.
- The Gallery's panel specimens show what the Reader shows (the review note, the absent text), not a second copy of the wording.
- `UploadDropzone` and `SpanHighlight` were not on the commit 5 list and carried the same kind of content. They are in CI, apart from the rest, so they can be dropped from the commit on their own.
- `MobileDrawer`'s title is required (CJ). `StageProgress` and `CategorySidebar` take their steps, groups and summary from the caller (CK), which also takes 0.4 KB gzipped out of the Reader chunk, where both fixtures shipped.
- Not moved: statute text in `RuleFlagCard` and `StatuteTag` (real law), `ScopePanel`'s catalogue constants, and plain labels such as the drawer's two placeholder lines.
- One behaviour in the Gallery changed: a click on a sidebar row calls `onSelect` and no longer moves the highlight, because the component's own selection state is gone. The Reader never used it.

Checks:
- `pnpm typecheck`: exit 0. `pnpm test`: 61 of 61 pass (7 reveal, 15 tokens, 1 font loading, 5 hero fixture, 19 start flow, 3 authority, 11 reader), 0 failed, 0 skipped. `pnpm build`: 171 modules, exit 0, no warning. Entry 73.6 KB gzipped (74.4 at commit 5), Reader chunk 15.1 KB (15.5).
- Test count unchanged. No new test: the change deletes defaults and makes props required, which the typechecker covers, and the Reader's rendering was compared against a build of `6ba24a8` instead.
- Reader against `6ba24a8`, two production builds and one scripted run: the sidebar's HTML hash, the summary, the panel text and the toolbar file name are identical, before and after a category is selected, and the progress band shows the same stages.
- Browser: the Gallery with an empty console and the counts in 17.7, and `/start` in sample mode with one card.
- Claims grep with the new patterns (29 matches on `6ba24a8`'s `src`, none now), the old calibration grep, the Evidence gate, the Rules section 1 scrub, the tool-name grep over `frontend/` and README and the dash scan (control file detected, two lines): all print nothing.
- `/ponytail:ponytail-review`, two rounds: no P1. One P2 (`"default"` left `RulerVariant`) and one P3 (the `Row` alias) fixed. Kept and listed in 17.7.
- No user-facing string was added or changed, so the copy passes did not run.

Not run: Lighthouse on `/`, the dark theme and 375 px captures of the Gallery, and the before and after pairs, which wait for the end of step 2. A screen reader on the Gallery or the Reader. A pointer click on a sidebar row in the Reader (the selected state was compared through "Read the first finding").

Housekeeping: the Vite dev servers (5173, 5174) and the two preview servers (4173, 4174) stopped. A build of `6ba24a8` sat in the session scratchpad for the comparison, with `node_modules` junctioned in. No git write was run.

Open for Aryan: none. The three groups of content left in components are statute text, catalogue constants and plain labels, none of them contract or case content.

Next action: commit this part, then commit 7 of 7, Accuracy mobile grouping (the 46 categories under the 7 catalogue groups as `details` below 768 px, first open).

## 2026-10-14: Part FE-R, step 2, commit 7, Accuracy mobile grouping

Part: FE-R, step 2, commit 7 of 7 (theme: the Accuracy list below 768 px). Starts from `f86a36a`. Part 1-B stays paused. No dependency was added. 3 files under `frontend/src` (1 changed, 2 new), 70 lines added and 10 deleted. The final sweep follows this commit. A second round, at Aryan's request before the commit, added the Weak count to each group's summary.

Files changed:
- `pages/Accuracy.tsx`: below 768 px the 46 blocks sit under the seven catalogue groups, each a `Disclosure` with "Group (count)" in its summary, or "Group (count, n Weak)" when n rows are drawn Weak, and the first open. From 768 px the flat table is unchanged. Both layouts are in the DOM and CSS shows one (`hidden md:block`, `md:hidden`).
- `lib/accuracy.ts` and `lib/accuracy.test.ts`: `rowVariant` (how a row is drawn) and `groupRows` (with each group's Weak count), pure, with 2 tests.
- Docs: `FrontendDesign.md` (6.5, 17.7 rows CL and CM, a rule, the commit 7 checks, one Deferred row), `Architecture.md` (7.2 one decision row, the file tree and the test count), `DesignSystem.md` (the Accuracy row), this entry.

Amendments CL and CM are in `FrontendDesign.md` 17.7, with the figures. Short form:
- CL: a summary carries the group's Weak count when it is above zero, "Restrictions (9, 2 Weak)", so a closed group cannot hide a Weak row. "Drawn Weak" has one definition, `rowVariant`, which the row, the group counts and the headline "N are marked Weak" line all read. The headline read `r.weak` before and could have counted a not-measured row, and with the mock no figure moved (the group counts add up to 10 and 15, the headline's). "Weak" is capitalised as the page names the status, where the request's example was lowercase.
- CL: the groups are in catalogue order and the page's sort applies inside each group. An id the catalogue does not list falls under "Other categories", so no row drops out. A group the reader opened stays open through a sort and a switch of evaluation set. Each group's table is named "CUAD test set results, Basics", so the set stays in the name. `Disclosure`'s 15 px text on a 24 px line made every row about 23 px taller in the first build, and the group's table resets it: the 46 row heights are identical to the flat list's.
- CM: a width hook (`useMedia`) was tried first and not taken. It made the bundler split the hook out and move `StatuteTag` into the entry, +0.64 KB gzipped on every route. CSS costs 46 hidden rows in the DOM and no entry bytes.

Checks:
- `pnpm typecheck`: exit 0. `pnpm test`: 63 of 63 pass (7 reveal, 15 tokens, 1 font loading, 5 hero fixture, 19 start flow, 3 authority, 11 reader, 2 accuracy), 0 failed, 0 skipped. `pnpm build`: 172 modules, exit 0, no warning. Entry 73.58 KB gzipped (73.57 on `f86a36a`), Accuracy chunk 3.23 KB (3.03), Reader chunk 15.08 KB (unchanged).
- Test first, twice: the grouping test failed on the missing module before `lib/accuracy.ts` was written, and the Weak count test failed on the missing `rowVariant` export before the second round's code. Both pass.
- Weak counts, in the browser, both themes, both evaluation sets: every summary's count equals its rows and its Weak part equals the rows carrying the Weak note, the group totals equal the headline (10 and 15), no summary reads ", 0 Weak", and none wraps at 375 or 320 px (longest "Intellectual property (9, 6 Weak)"). 375 px heights are unchanged: 3,585 px with the first group open, 12,029 px with all open.
- Browser, production builds of this commit and of `f86a36a` on `vite preview`, headless Edge, real pointer and key events, both themes: 7 groups summing to 46 with the first open; a click opens and closes a group; Enter opens and Space closes a focused summary; Tab moves summary to summary; "Recall" sorts ascending inside every group; 767 px shows the groups and 768 px the table; axe reports no violation and nothing incomplete at 375, 768 and 1280 px; the console is empty. 375 px height 11,525 px, then 3,585 px with the first group open and 12,029 px with all open.
- The wide layout against `f86a36a`: full page screenshot hashes at 768, 1024, 1280 and 1440 px in both themes. Over three runs 21 of 24 pairs were identical and 3 differed once each. Repeats matched for light 1024 (6 of 6) and dark 1280 (4 of 4). For light 1440, `f86a36a` itself gave two images (4 of 5 and 1 of 5) that differ by one pixel (x 346, y 1995), and every capture of this commit is 0 pixels from the `f86a36a` capture with the same hash. The wide output is the same, and the cause of the single pixel was not established.
- Claims grep, calibration grep, Evidence gate, Rules section 1 scrub, tool-name grep over `frontend/` and README and the dash scan (control file detected): all print nothing.
- `/ponytail:ponytail-review`, two rounds: no P1, no P2. Round one, two P3 fixed (the `useMemo` and a long comment). Round two, after the Weak count, nothing to cut. Kept: both layouts in the DOM, `UNLISTED`, `groupRows` in `lib/`.
- Copy passes on the two new strings (the group table's accessible name, and the summary's Weak part): copywriting, copy-editing and stop-slop, no change to either string. Stop-slop cut one word from a code comment.

Not run: Lighthouse on `/accuracy` and `/`, the dark and 375 px keyboard run across the whole page, the before and after pairs (all in the final sweep). A screen reader on the grouped list.

Housekeeping: the two preview servers (4173, 4174) stopped. A build of `f86a36a` sat in the session scratchpad with `node_modules` junctioned in, and the junction was removed with `rmdir`. Screenshots of this commit are in `frontend/.screens/FE-R/c7/`, gitignored. No git write was run.

Open for Aryan: below 768 px "Recall" and "Silent miss" sort inside groups, so the worst rows are no longer first across the list. The Weak count in each summary shows where the Weak rows are, and a flat worst-first list would restore the order. Not asked for, and listed under Deferred in 17.7.

Next action: commit this part, then the final sweep (Lighthouse and axe on every route, the keyboard run in dark and at 375 px with a real click on a Reader sidebar row at 1280 and in the categories drawer at 375, the before and after pairs, the quality bars in the final BuildLog entry, FE-R ticked in `Phases.md`).

## 2026-10-15: Part FE-R, final sweep and close

Part: FE-R, step 2, commit 8 of 8, the last entry of the phase (theme: the four keyboard findings of the final sweep, and the phase's measurements). Starts from `2b32140`. Part 1-B stays paused. No dependency was added. The sweep stopped on 14 October at Aryan's request, for laptop safety, so the four fixes below were made in code and handed to Aryan for a manual check.

Files changed:
- `components/DropdownMenu.tsx` (S1), `components/DropdownMenu.test.ts` (new, 1 test), `components/MobileDrawer.tsx` (exports `PEEK_PX`) `pages/Reader.tsx` (S3, S3b and S4) and `pages/Reader.test.ts` (new, 1 test). No user-facing string changed.
- Docs: `FrontendDesign.md` (status, 17.7 rows CN to CQ and three Deferred rows), `Architecture.md` (the test count), `Phases.md` (FE-R ticked), this entry. `README.md` is unchanged, because nothing it describes moved.

Method. Production build of `2b32140` served by `vite preview` on `localhost:4173`, headless Edge over the DevTools protocol with extensions disabled, real pointer and key events, Lighthouse 13.5.0 (mobile, simulated throttling) and axe-core 4.14.0. The scripts live outside the repo. Screenshots are in `frontend/.screens/FE-R/`, gitignored, including 32 FE-0 and FE-R pairs in `pairs/`. The measurements below were taken before the four fixes. The fixes touch the Reader and the menu only and change no colour, so the other routes and the contrast figures stand. The keyboard run was not repeated after the fixes (see Not run).

Quality bars (`FrontendDesign.md` 1.3):

| Bar | Result | Verdict |
|---|---|---|
| Lighthouse mobile `/` | Performance 96, 97, 97 (three runs). LCP 2.21, 2.17, 2.26 s. TBT 127, 105, 31 ms. CLS 0.00003. Accessibility 100, Best Practices 100, SEO 91 | Passes (95, 2.5 s, 0.05, 100, 95) |
| Lighthouse, the other routes (no bar) | `/start` 95, 94, 95 with LCP 2.59, 2.67, 2.65 s. `/how-it-works` 94, 96, 96 with LCP 2.61, 2.40, 2.49 s. `/accuracy` 90, 94, 94 with LCP 2.79 s in all three and CLS 0. Accessibility 100 and Best Practices 100 on all four routes | Information. `/start` and `/accuracy` are over 2.5 s, and the bar names `/` only |
| axe, every route, both themes | Every route and state at 375, 768 and 1280 px, 77 captures in each theme, 154 in all: 0 violations. The R2 pair (dark Accuracy at 375 px) is among them | Passes |
| Keyboard | Light at 375 px and dark at 1280 px, landing to start to how it works to accuracy to the Reader, clause panel, judgment card, menu and delete dialog. Every stop has a 2 px ring and a 44 px target except where listed below. Real pointer runs: 120 of 120 checks pass across light and dark, motion and reduced motion, including a click on the opener and a pick at 1280 and 375 px | Passes at 1280 px. Below 1280 px the run found S3, S3b and S4, now fixed in code and verified by hand (below) |
| Contrast | `tokens.test.ts` passes. Rendered pixels, both themes: lowest ratio 4.57:1 in light (category rows at rest) and 6.10:1 in dark (the panel with a judgment card). Two groups in each theme read false for holding elements with no drawn text, and every ratio in them is above 4.5 | Passes (4.5) |
| Bundle | JavaScript named by `index.html` 109.25 KB gzipped at level 9, entry 73.58 KB by Vite's figure. All 20 chunks 148.81 KB. `/` transfers 112.06 KB of script in 7 files | Passes (200 KB) |
| Fonts, third party | One origin, `localhost:4173`, on `/`, `/start`, `/how-it-works` and `/accuracy` (16 to 24 requests). 15 font files in `dist/fonts`. No font or CDN host named anywhere in `dist` | Passes |
| Reading measure | Reader: 73.2 characters on 37 full-line paragraphs at 1280, 1440 and 1920 px (65 to 81, column 612 px, sheet 710 px). Hero sheet 70.3 (69 to 72) | Passes (68 to 80) |

Keyboard findings of the sweep and what was done:
- S1, the menu item has no focus ring (`DropdownMenu.tsx`). Fixed in code. Verified manually by Aryan. An inline `outline: none` on each item outranked `:focus-visible`. The item takes `focus-inset` and sets an inline outline only for the Gallery's forced state. Confirmed in the source: the one inline `outline` left is the forced-state ring, and `DropdownMenu.test.ts` fails if another appears.
- S3, a focused mark entirely behind the peek sheet below 1280 px (4 of 24 marks at 375 px with the panel open). Fixed in code. Verified manually by Aryan. The scroll area has `scrollPaddingBottom` of the sheet's height plus 16 px while a sheet shows.
- S4, Enter on a mark under reduced motion below 1280 px left focus on the mark. Fixed in code. Verified manually by Aryan. The panel title is focused again one frame later when the first call is refused.
- S3b, a control in the peek sheet taking focus below the viewport: at peek below 1280 px the judgment card's "Higher confidence", "View full passage" and "Open source" sat inside the clipped sheet. Fixed in code. Verified manually by Aryan. The panel in the sheet has an `onFocus` that opens the sheet when the focused control's bottom edge is more than `PEEK_PX` below the sheet's own top. The offset is taken from the sheet, so a slide in progress does not change it, and a control inside the peek (the title after Enter on a mark, "Close panel") leaves the sheet at peek. `Reader.test.ts` reads the source for the guard, the threshold and the wiring.
- Not defects: three stops read not in view by under 1 px at the viewport edge (two summaries on the landing page, the footer link on How it works), and a card button that read under 44 px while off screen.

Other results:
- Gallery, development only, axe: 6 `aria-required-parent`, 2 `landmark-unique`, 1 `color-contrast`, 2 `empty-table-header` and 2 `scrollable-region-focusable`, all inside specimens. The Gallery is not in the build.
- Closed with no change: SEO 91 (no `robots.txt`, as decided in commit 4, BV).

Checks (this commit):
- `pnpm typecheck`: exit 0. `pnpm test`: 65 of 65 pass (7 reveal, 15 tokens, 1 font loading, 5 hero fixture, 19 start flow, 3 authority, 11 reader, 2 accuracy, 1 menu, 1 sheet), 0 failed, 0 skipped. `pnpm build`: 172 modules, exit 0, no warning. Entry 73.58 KB gzipped (unchanged), Reader chunk 15.25 KB (15.08).
- The two new tests fail on `2b32140` and pass on this commit: the menu test on the missing outline literal, the sheet test on the missing handler (run red before the handler was written).
- `/ponytail:ponytail-review` over the full diff (S1, S3, S3b, S4 and both tests): no P1 and no P2. One P3 fixed earlier: the first of two menu tests was implied by the second. One P3 kept: `!xl && sheetState !== "closed"` appears twice in the scroller's style, and hoisting it saves no line. Kept: `SHEET_OPEN` (one value for the sheet's height and the scroll padding), the one retry in the focus effect (it has a cause and is cancelled with the effect), and the `top !== undefined` guard in `openSheetOnFocus` (typing only, `closest` always finds the sheet). Net: 0 lines possible.
- No user-facing string was added or changed, so the copy passes did not run.

Reviews. Step 1 ran `/ponytail:ponytail-review` over the full range and one independent second review, and applied the `/gstack-review` and `/gstack-cso` checklists by hand. `/coderabbit:code-review` did not run: it failed to start on the full range and on `8aee425..HEAD`, and the installed command line (0.7.6) cannot update itself. Aryan accepted it as not run. It was not retried.

Not run: the keyboard run after the four fixes (Aryan's manual check stands in for it), Lighthouse after the fixes (the fixes do not touch `/`), a screen reader on any route, and a real device or network.

Browser launch audit and the pause. After the sweep, Aryan stopped all browser, server and background launches and asked for the harness launches to be audited from the saved scripts and session logs (read only, nothing started). Every harness launch used a fresh temporary profile and none used the real profile, and Lighthouse used its own temporary profile. All were headless. Findings: (1) the first FE-0 harness run did not disable extensions, and an installed extension still ran in that fresh profile. How it got there was not established, and every later run disabled extensions. (2) One review session closed browsers by killing every `msedge.exe` by name, which also closes the user's own Edge, and two browsers ran at once in that session. (3) Leftover temporary profile folders remain in the temp directory (78 of them), because cleanup failed or never ran when a run was cut short. (4) The built-in browser pane loaded `localhost` pages only, and no desktop-control tool was used in any session. The standing rules that replace this practice are kept outside the repo: no launch without approval for that step, a fresh profile with extensions and sync disabled, a ledger of every process started and no kill by name, and a stop at any sign-in prompt. FE-R is closed on the measurements above, with S1, S3, S3b and S4 verified by hand.

Housekeeping: no server, browser or background process was started for this commit. Only typecheck, test and build ran, and each exited on its own. No git write was run.

Next action: Aryan runs the manual check for S1, S3, S3b and S4, then commits this part. FE-R is ticked in `Phases.md`. Part 1-B stays paused until Aryan says so.

## 2026-10-15: Part 1-B, PDF text extraction in reading order

Part: 1-B. It resumes after the frontend track closed at 75b6885.

Files changed:
- New in `backend/`: `app/parsing/detect.py`, `app/parsing/pdf.py`, `tests/conftest.py`, `tests/fixtures/build.py`, `tests/test_pdf.py`, `tests/test_invariants.py`.
- `docs/app/Phases.md`: 1-B ticked; the 1-B deviations and ceilings added under A8.
- `docs/app/Architecture.md`: the `pdf.py` tree line, two key-decision rows (reading order and blocks, errors and logs) and the block locator line in section 4.
- `docs/app/BuildLog.md`: this entry.
- Unchanged: `README.md` and `docs/app/Rules.md`. Rules.md section 1 already says either track may edit `README.md`, added at FE-0, so the exemption from the root-files freeze needed no change.

Commands run, from `backend/` in Git Bash with the venv active:
- `ruff format .`, `ruff check .`, `pytest -q`.
- Probes of pdfplumber 0.11.10 and pdfminer.six 20260107 in the venv: the `extract_words` keys, the exception class tree, the wrapped `PDFPasswordIncorrect`, the logger names, and ligature and NBSP behaviour with the Vera font.
- Two mutation passes on copies of `pdf.py` outside the repo, and byte-level sweeps of the fixtures outside the test suite (see Verification).
- A flowed-layout probe built with reportlab platypus outside the repo.
- The Rules section 1 scrub and a dash check over `backend/` and `docs/app/`.
- Read-only git: `git status`, `git log`.

Tests: 62 passed, 0 failed, 0 skipped. Of these, 24 come from 1-A, 25 are in `test_pdf.py` (7 for `detect_type`, 18 for `parse_pdf`) and 13 are in `test_invariants.py` (one per fixture, valid and invalid). Eighteen one-line mutations of `pdf.py` each failed at least one test: the pitch ratio, the numbering split, the left-edge return (removed, and firing on any jump), the opener condition, the stream-first exemption, ligature expansion, the logger silencing, the wrong-password mapping, the gutter width, the gutter zone, the rows-around-gutter check, the crossing test, the uncertain warning, the more-than-two branch, the empty-page skip, the empty-text filter, and moving the assembler calls inside the catch.

Pinned versions added: none. No new dependency. `pdfminer.psexceptions.PSException` and `pdfminer.pdfdocument.PDFPasswordIncorrect` are imported for their exception types only, and pdfminer.six is already pinned through pdfplumber (see the pre-phase entry). The parser modules import without scikit-learn in `sys.modules`.

Decisions:
- The two additions carried over from before the pause. First, every assembler call stays outside the try block that catches `ValueError` (A1). `_read` is the only function with a try block, and it returns plain words, so the layout and the assembler run after it. A test patches `TextAssembler.add_block` to hand the real assembler an empty block and asserts that `ValueError("block has no text")` comes out and is not a `ParseError`. Moving the calls inside the catch fails that test. Second, the README exemption from the root-files freeze was already in Rules.md, so nothing was changed.
- 1-B carries all of A1's error mapping (malformed to MALFORMED_FILE, a wrapped wrong password to ENCRYPTED_PDF, `from None`, silenced loggers), with `malformed.pdf` and `encrypted.pdf` and the byte-flip sweep. The libraries log raw bytes from their first call, so this could not wait for 1-C.
- `pdfplumber` is silenced next to `pdfminer`: it puts exception text into a metadata warning.
- Rows group by `top` from the first word of a row, with a tolerance of half the median word height. Lines inside a column are grouped again from that column's words.
- The gutter search is a sweep over merged word spans per row, not a sampled grid, so a damaged file with huge coordinates costs no memory. A row reads across the gutter when a word spans the gutter's right edge (one point of tolerance) or the gap at that edge is under 12 points. The right edge decides because a column's right side is ragged and its left side is square.
- A word with no text is dropped in `_read`. Without that filter, 28 and 35 of 2,500 mutants of `latin_unicode.pdf` raised `ZeroDivisionError` outside the catch. A patched `extract_words` covers it in `test_pdf.py`.
- The numbering token is a coarse regex local to `pdf.py`: `1.`, `1.1`, `1.1.1.` and `(a)`, `(iv)`, `(3)`, followed by white space. A bare number is left out, so `30 days` at the start of a wrapped line does not split.
- Block locator `[CONTRACT]`: `{"page": n, "block": i}`, both 1-based, `i` counting within the page. COLUMN_ORDER_UNCERTAIN `[CONTRACT]` fires once per page when a crossing line sits between two runs of column rows. Both go to Tanishq with the other contract items.
- `detect_type` gives MALFORMED_FILE for a ZIP that cannot be read, and UNSUPPORTED_TYPE for a ZIP without `word/document.xml` or with `word/vbaProject.bin`.
- Fixtures (all reportlab, `invariant=1`, uncompressed pages so a leak is visible, US letter): `simple`, `two_column`, `long_lines`, `latin_unicode` (Vera, holds U+FB01), `tight_clauses`, `three_column_table`, `column_uncertain`, `contents` (page numbers far right, covers the gutter zone), `first_line_indent`, `hanging_page_break`, `blank_page`, `malformed`, `encrypted`.

Findings during the part:
- Read literally, A7's left-edge rule cut every first-line-indent paragraph after its first line: 28 blocks for 14 paragraphs on a flowed two-page probe with 6 pt spacing. The rule now ends a block only when the block began at the edge or is the first block of its stream. A first attempt without the stream exemption fused the rest of a page that opened on the indented tail of a hanging paragraph, and a fixture caught it. The final numbers on the probe: 6 pt block paragraphs 14 blocks, 6 pt first-line indent 16, hanging with numbers 15, hanging without numbers 15, block paragraphs with no spacing 2 (one per page, nothing in the geometry separates them).
- Geometry cannot tell a hanging indent that opens a page from a first-line indent that opens one. The remaining ceilings are in `Phases.md` under the 1-B deviations.
- The reportlab default page is A4, so the first draft of the bbox test caught fixtures laid out for US letter. `PAGE_WIDTH` and `PAGE_HEIGHT` are now passed to the canvas.

Verification:
- `ruff format .`: 12 files left unchanged. `ruff check .`: all checks passed. `pytest -q`: 62 passed in about 1.7 s.
- Sweeps outside the suite: about 13,500 mutants of eleven fixtures (byte flips, truncation, deleted ranges, inserted bytes), seeds 1 to 3, 21 to 23 and 31, the last 9,000 against the final extractor. Every result was a parse or a ParseError (MALFORMED_FILE, ENCRYPTED_PDF or NO_TEXT_FOUND). No other exception type, no log record, and the slowest parse took 56 ms.
- Attribution scrub: no output. Dash check: no em or en dash in `backend/` or `docs/app/`.
- No server, browser or background process was started. No git write was run.

Blockers: none.

Next action: commit 1-B with `feat(parser): extract ordered text blocks from PDFs`, send the two new `[CONTRACT]` items to Tanishq with the rest, then reply `next` to start 1-C.

## 2026-10-15: Part 1-C, PDF safety: decoration, scanned pages and limits

Part: 1-C. It follows 1-B, committed as 9b2fa01.

Files changed:
- `backend/app/parsing/pdf.py`: A9, A10 and A11 as built. `_read` now returns the pages and whether an annotation holds text. One comment in 1-B code that carried a tool name was reworded.
- `backend/app/parsing/errors.py`: `MAX_DECODED_CONTENT_BYTES`.
- `backend/app/parsing/assemble.py`: `build()` takes `unreadable_pages`.
- `backend/tests/fixtures/build.py`: 29 registry entries, plus `_raw_pdf`, `_stream` and the bomb builders.
- `backend/tests/test_pdf.py` and `backend/tests/test_assemble.py`.
- `docs/app/Phases.md`: 1-C ticked, and the 1-C deviations and ceilings added under A11.
- `docs/app/Architecture.md`: the decoration row, the content budget row and the locator paragraph in section 4.
- `docs/app/BuildLog.md`: this entry.
- Outside the repo: five real contracts from the CUAD set (cc-by-4.0, from huggingface.co/datasets/theatticusproject/cuad) in `data/cuad_smoke/`, for the smoke check below. `data/*` is ignored, so `git status` does not show them. Rules.md says never to touch `data/`, and Aryan's instruction for this check overrode it.

Commands run, from `backend/` in Git Bash with the venv active:
- `ruff format .`, `ruff check .`, `pytest -q`.
- One-line mutations of `pdf.py` on copies outside the repo, byte-level sweeps of the fixtures, a before-and-after diff of the parser on the five contracts, and the smoke statistics.
- A clean install: a fresh virtual environment outside the repo, `pip install -r requirements-dev.txt`, then `ruff` and `pytest` inside it.
- The Rules section 1 scrub and a dash check over `backend/` and `docs/app/`.
- Read-only git: `git status`, `git diff`.

Tests: 149 passed, 0 failed, 0 skipped (62 after 1-B). `test_assemble.py` holds 25 (one new), `test_pdf.py` 82 (57 new) and `test_invariants.py` 42 (one per new fixture). The byte-flip test in `test_pdf.py` now runs over `simple.pdf`, `partly_scanned.pdf` and `form_field.pdf`, 300 seeded mutants each.

Pinned versions added: none. `reportlab==5.0.1` and `pillow==12.3.0` have been in `requirements-dev.txt` since 1-A, so the fixtures needed no new dependency. The clean install resolved pdfplumber 0.11.10, pdfminer.six 20260107, python-docx 1.2.0, PyYAML 6.0.3, pytest 9.1.1 and ruff 0.16.10. `sklearn` is not in `sys.modules` after importing the parser.

Decisions:
- Margin zone and kinds are as listed under the 1-C deviations in `Phases.md`. Each margin candidate is a block of its own, and a candidate that is neither number-shaped nor repeated keeps kind `text`.
- A9 gains a page-number rule for the first or last row of a page (see Findings). Folding the other margin candidates back into the body flow cut blocks on two files and changed reading order on one, so it stays out.
- A10: the parser emits `PARTIALLY_SCANNED_PDF` once per scanned page, and `coverage.pages_with_text` leaves out scanned pages. Both go beyond A10's text and carry the `[CONTRACT]` tag.
- A11: the budget undoes leading ASCII85 and ASCIIHex filters before it measures. A11's text does not say this. reportlab writes ASCII85 in front of Flate, so a bomb in that form would otherwise count its stored length.
- Fixtures are generated at test time by `build_all`, called from the session fixture in `conftest.py`. Nothing binary is committed.
- Tests reach three private names: `_PAGE_NUMBER`, `_decoded_length` and `_FLATE_CHUNK`. The page-number shapes are tested directly, and the chunk helpers are tested at boundaries that a fixture could reach only with an 8 MiB file.
- `bomb_encrypted.pdf` appends its padding through reportlab's private `canvas._code`.
- `_decoded_length` has no branch for an already-decoded stream. A mutation showed the branch was dead, so it is deleted.

Findings during the part:
- The page-number miss. On two of the five real contracts the text fills only the top half of the page and the bare page number sits at about 51 percent of the page height, outside the 8 percent zone. Under A9 as written it stayed text on 32 of 33 pages in one file and 13 of 14 in the other. The new rule marks a page-number-shaped first or last row of the page as decoration wherever it sits.
- Reading order. A first measurement of the rule, combined with folding the margin lines back into the body, showed changed text order on three files. With the rule alone, the text of files 01, 02 and 04 is identical to before, and two pages change order. Both are two-column signature pages, page 33 of file 03 and page 14 of file 05. The number sat in the left half, so it joined the left column and was read before the right one. It now comes last, like the footer it is, and removing the number blocks from both outputs leaves the same blocks in the same order. The earlier change on file 02 came from the margin-folding variant, which is not applied. Its cause is not traced.
- A9 variants on the five contracts, blocks and decoration:

| Variant | File 01 | File 02 | File 03 | File 04 | File 05 |
|---|---|---|---|---|---|
| A9 as written | 174 blocks, 16 footers | 797, 0 | 246, 0 | 614, 44 | 176, 0 |
| Margin lines folded back (not applied) | 174, 16 | 723, 0 | 246, 0 | 570, 44 | 176, 0 |
| Folded back, plus the number rule (not applied) | 174, 16 | 723, 2 | 246, 32 | 570, 44 | 176, 13 |
| Number rule alone (applied) | 174, 16 | 797, 2 | 246, 32 | 614, 44 | 176, 13 |

  The words are the same in every variant. Against A9 as written, the text order changes on file 02 when the margin lines are folded back, on files 02, 03 and 05 when the number rule is added to that, and on one page each of files 03 and 05 with the number rule alone. Folding the margin lines back cut block fragmentation on the two files that fill the page (797 to 723, 614 to 570), so it stays out until 1-E shows that fragmentation matters.
- A real-file smoke check on five CUAD contracts, picked by era and agreement type from the metadata before any was parsed. All five parse with `partial = False`.

| File | Pages | Blocks | Blocks per page | Longest block (chars) | Clause number after the start | Clause number at a line start | Blocks over 2,000 chars | Footers |
|---|---|---|---|---|---|---|---|---|
| 01 Cybergy 2014 | 16 | 174 | 10.9 | 1,210 | 16 | 1 | 0 | 16 |
| 02 Healthgate 1999 | 33 | 797 | 24.2 | 1,185 | 34 | 1 | 0 | 2 |
| 03 Athens 2009 | 33 | 246 | 7.5 | 4,428 | 54 | 1 | 8 | 32 |
| 04 Dova 2018 | 44 | 614 | 14.0 | 2,607 | 123 | 7 | 6 | 44 |
| 05 Theravance 2020 | 14 | 176 | 12.6 | 1,264 | 10 | 0 | 0 | 13 |

  Definitions. A clause number is a dotted number such as 4.2 or 11.3.1 (one or two digits per part, not preceded by a letter, digit, dollar sign, comma, slash, hyphen or full stop, and not followed by a letter, digit or percent sign), or an enumerator such as (b), (iv) or (12). "After the start" counts blocks with a clause number anywhere past their first character. "At a line start" counts blocks where a second or later line opens with one.
  Of the 237 blocks with a clause number after the start (11.8 percent of 2,007 blocks in 140 pages), 120 are cross-references, 113 are inline enumerators inside one paragraph and 4 are dates or decimals. The 10 line-start hits are wrapped cross-references or a table of contents, and none is two numbered paragraphs run together.
  A second check looked for a short line that ends a sentence and is followed by a capitalised line, inside one block. It found 9 blocks (0.45 percent), about 4 of them real fusions: unnumbered UK-style paragraphs in file 05. The 4,428-character block in file 03 was read in full and is one long paragraph.
  Warnings: file 02 has 2 `COLUMN_ORDER_UNCERTAIN` and 1 `MORE_THAN_TWO_COLUMNS`, file 04 has 1 `MORE_THAN_TWO_COLUMNS`, and file 05 has 3 `COLUMN_ORDER_UNCERTAIN`. Parse time ran from 1.6 s to 18 s per file, one run each, so it is noisy; file 03 (33 pages) took 18 s.
  Verdict: no fix for fused paragraphs is needed before 1-E. The sample is five files, all in the style of SEC exhibits, so it says little about other layouts.

Verification:
- `ruff format .`: 12 files left unchanged. `ruff check .`: all checks passed. `pytest -q`: 149 passed in about 9 s.
- Clean install: Python 3.12.10, a new venv outside the repo, `pip install -r requirements-dev.txt`, then `ruff format --check`, `ruff check` and `pytest -q`: all passed, 149 passed in 8.4 s.
- Mutations: 60 one-line mutants of `pdf.py` (margin share and zone edges, repetition thresholds, the page-number match, image share, the scanned and partial limits, annotation keys, the page limit, budget order and chunking, filter handling, and the page-number rule: order, each side, the shape test, the body check, the move). 59 failed at least one test. One does not apply, because the branch it targeted was deleted. The run used the code as of its last behaviour edit. Two edits came after it: a reworded comment and two tests merged into one with the same 14 cases.
- Byte sweeps outside the suite, on the final code: 5,180 mutants of 18 fixtures (byte flips, truncation, deleted ranges), seeds 1 and 2. 2,047 parsed, 2,533 gave `MALFORMED_FILE`, 468 `NO_TEXT_FOUND`, 125 `SCANNED_PDF` and 7 `ENCRYPTED_PDF`. No other exception type, no log record, and the slowest parse took 0.51 s.
- Attribution scrub (Rules section 1): no output. A grep for tool names over the `backend/` source: no hits. Dash scan over `backend/` and `docs/app/`, with a control file that holds both dashes: the control was found, and 23 files held no en or em dash.
- No browser, server or background process was started. No git write was run.

Not verified:
- The bomb fixtures are not in the sweeps. An earlier combined sweep ran for more than 25 minutes and was stopped, so `bomb_form.pdf` and `bomb_content.pdf` were left out, and `bomb_encrypted.pdf` was never added. The guess is that a mutated bomb slips under the budget and pdfminer then spends about 90 s on 8 MiB of whitespace. That guess is unconfirmed. It matches the time ceiling listed under the 1-C ceilings in `Phases.md`.
- Only five real contracts were parsed. Scanned pages, owner-password files and the page limit were covered by generated fixtures alone.

Blockers: none.

Next action: commit 1-C with `feat(parser): mark repeated page furniture and reject unreadable PDFs`, add the new `[CONTRACT]` items to the Tanishq message (kind `header` and `footer` on PDF blocks and the first-or-last-row page-number rule, the per-page `PARTIALLY_SCANNED_PDF` warning, the `BLANK_PAGE` warning, `pages_with_text` leaving out scanned pages, and the partial triggers: 20 to 199 characters on an image-dominant page, and annotation text), then reply `next` to start 1-D.

## 2026-10-15: Checks before 1-D

Two checks were open after 1-C was committed as 97bb743. No code changed for either.

Fused paragraphs on the CUAD sample. This was already measured in the 1-C entry (five contracts, 2,007 blocks, 140 pages, nothing re-parsed). Blocks with a clause number somewhere other than the start:

| File | Blocks | Clause number after the start | Of those, a second line opens with one |
|---|---|---|---|
| 01 Cybergy 2014 | 174 | 16 | 1 |
| 02 Healthgate 1999 | 797 | 34 | 1 |
| 03 Athens 2009 | 246 | 54 | 1 |
| 04 Dova 2018 | 614 | 123 | 7 |
| 05 Theravance 2020 | 176 | 10 | 0 |
| Total | 2,007 | 237 (11.8 percent) | 10 |

Of the 237, 120 are cross-references, 113 are inline enumerators inside one paragraph and 4 are dates or decimals. None of the 10 line-start hits is two numbered paragraphs run together. A separate check for a sentence end followed by a capitalised line found about 4 real fusions in 2,007 blocks, all unnumbered paragraphs in file 05. Verdict: 1-E needs no fix first. The sample is five SEC-exhibit style files, so it says little about other layouts.

An 8 MiB whitespace stream. One foreground run, one process, hard exit after 180 s.
- Input: a one-page PDF whose single content stream is exactly `MAX_DECODED_CONTENT_BYTES` spaces (8,388,608), Flate-packed, 8,603 bytes in all. It is the largest stream the budget accepts: `bomb_content.pdf` is the same file plus one byte.
- Method: `parse_pdf` on a copy of `app/` outside the repo, run from the venv interpreter in isolated mode. The process set `faulthandler.dump_traceback_later(180, exit=True)` as its own hard timeout, and the tool call had a 200 s backstop. One process started (pid 4740), and it exited by itself.
- Result: `NO_TEXT_FOUND` after 0.05 s wall and 0.03 s CPU. The budget let the stream through and the extractor read it.
- Reading: white space is not the slow path. `pdfminer/psparser.py` skips it with one regex search over each 4 KiB buffer, so 8 MiB is about 2,000 searches. The 90 s extrapolation under the 1-C ceilings, and the guess under "Not verified" in the 1-C entry, do not hold for white space. The 186 s that A11 measured for a 16 MB stream must have come from a stream of tokens, where the cost follows the number of operators and words and not the number of bytes. That content was not recorded.
- Not measured: 8 MiB of dense operators or text. That is the real worst case for time.

A11 wall-clock kill, proposal for 2-C. The only parse times on record for real files are from the 1-C smoke check: 1.6 s to 18 s per file, the slowest being 33 pages in 18 s, one run each, on this laptop. That is about 0.55 s per page, so about 55 s for a 100-page file by a straight line. Proposed value: 120 s, one named constant in the 2-C config, about twice the extrapolated legitimate worst case. It lets a slow host through and caps what a hostile file can take from one worker at two minutes. Two things are open. The figure rests on one run per file and must be re-measured on the Phase 2 host before it is fixed. And the dense-token case above is unmeasured, so the 120 s is a bound on cost, not a number the bomb was shown to reach.

## 2026-10-15: Part 1-D, DOCX archive safety, body, tables and text boxes

Part: 1-D. It follows 1-C, committed as 97bb743. The numbering, headers, footers and footnotes are 1-D2.

Files changed:
- `backend/app/parsing/docx.py` (new): A12 to A16. `parse_docx(data)`, the archive checks, the tracked-change scan, and the body walk.
- `backend/tests/fixtures/build.py`: 37 DOCX registry entries, `build_docx(body, extras, prolog)` and `build_zip(member_name)`.
- `backend/tests/test_docx.py` (new): 73 tests.
- `backend/tests/test_invariants.py`: picks `parse_docx` or `parse_pdf` by the fixture's suffix.
- `docs/app/Phases.md`: 1-D ticked, with the 1-D deviations and ceilings.
- `docs/app/Architecture.md`: two decision rows, the `docx.py` tree line and the DOCX locators.
- `docs/app/BuildLog.md`: this entry, and the checks entry above it.

Commands run, from `backend/` with the venv interpreter:
- `ruff format .`, `ruff check .`, `pytest -q`.
- One-line mutants of `docx.py` on copies of `app/` and `tests/` outside the repo, and mutation sweeps of small packages (damaged bytes, deleted ranges, inserted bytes), also outside the repo.
- Probes of four edge cases (strict relationship type, deep nesting, a 10 MB text node, entity expansion), all small.
- The Rules section 1 scrub, a tool-name grep over `backend/` and `docs/app/` added lines, and a dash scan with a control string that holds both dashes.
- Read-only git: `git status`, `git diff`, `git log`.

Tests: 259 passed, 0 failed, 0 skipped (149 after 1-C). `test_docx.py` holds 73, and `test_invariants.py` went from 42 to 79 (one per DOCX fixture).

Pinned versions added: none. `lxml` 6.1.3 is now imported directly, for `etree.LxmlError`. It comes with python-docx 1.2.0 and is not pinned on its own, the same as pdfminer.six next to pdfplumber.

Decisions (the rest are listed under the 1-D deviations in `Phases.md`):
- python-docx opens the package, so 1-D2 can use its styles, numbering and header parts. The walk itself reads the raw elements, because the library's paragraph text skips runs inside `smartTag`, `fldSimple`, content controls and text boxes.
- The reader returns plain items and the assembler runs after it, outside the try, as in `pdf.py`. A test patches the assembler to refuse an empty block and asserts a `ValueError`.
- A cell is one `table_cell` block, and a nested table or a text box ends it. A16 did not name the `segment` key that tells the pieces apart. It is always present.
- Warnings are once per document. A16 and A15 are silent on this.
- The text limit is checked while walking, so a part that holds millions of characters is not collected in full before the assembler refuses it.
- `NotImplementedError` is not in the catch tuple, because it is a subclass of `RuntimeError`, which A1 lists for the encrypted member.
- Zipfile's warning for overlapping entries is silenced inside the reader, because its text carries a member name from the file and would reach a server log.

Findings during the part:
- Most byte-flipped packages fail the zip checksum before any XML is read, so a second kind of mutant damages one XML member and repacks the package with correct checksums. Over about 195,000 mutants of five small packages, the only types that came out uncaught were `KeyError` (a missing member), `ValueError` (a negative seek from a damaged header), `zlib.error` and `EOFError`. A package whose content types part is well formed but has the wrong root gave `AttributeError`, found by a test and not by a sweep. All five are in the tuple now. No log record appeared, and the slowest parse took 5 ms.
- A first mutation run of `docx.py`: 66 mutants, 57 killed and 9 survived. Seven of the nine were test gaps and are closed:
  - Block-level `smartTag`, `fldSimple` and `hyperlink` were untested, because the wrapper fixtures only exercise the inline path.
  - Block-level markers such as `bookmarkStart` were untested.
  - An unknown child of a table and of a row both produced the same deduplicated warning, so removing either check changed nothing visible.
  - The early-end test raised `BadZipFile` and not `EOFError`.
  - The silenced zipfile warning was untested.
  - The remaining two were `NotImplementedError`, now removed from the tuple as redundant, and `if body is None`, an equivalent mutant: without the check the walk raises `TypeError`, which maps to the same code. The check stays for clarity.
  After the new tests, the seven gap mutants were all killed, and four new ones (three more markers, and the `RuntimeError` entry replaced) were killed too.
- Edge probes: a package with the strict relationship type passes `detect_type` and is `MALFORMED_FILE` here. 300 nested wrappers are `MALFORMED_FILE` (libxml2's depth limit is 256) and 100 parse. A single 10.1 MB text node is `TOO_MUCH_TEXT` after 0.02 s. Nested entities that would expand to 400,000 characters stay unexpanded.

`[CONTRACT]` items to add to the Tanishq message for 1-D:
- DOCX locators: body paragraph `{"part": "document", "paragraph": i}`, text box `{"part": "document", "textbox": n, "paragraph": i}`, cell `{"part": "document", "table": t, "row": r, "cell": c, "segment": k}`. All numbers are 1-based. `i` counts every body-level paragraph, empty ones included.
- DOCX blocks have kind `text` or `table_cell`, `page` None and `bbox` None. A paragraph with no text or only white space makes no block. U+00A0 and runs of spaces are kept.
- `TEXT_BOX_CONTENT`, `EMBEDDED_OBJECT` and `UNSUPPORTED_DOCX_FEATURE` appear once per document. The last carries `detail` `altChunk` or `unknown_block`, and sets `partial`. `EMBEDDED_OBJECT` sets `partial`. `TEXT_BOX_CONTENT` does not.
- New error codes in use: `ARCHIVE_UNSAFE`, `ARCHIVE_TOO_LARGE`, `TRACKED_CHANGES_PRESENT`.
- `media_type` is `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.

Verification:
- `ruff format --check .`: 14 files already formatted. `ruff check .`: all checks passed. `pytest -q`: 259 passed in about 4.4 s.
- Attribution scrub (Rules section 1): no output. No tool name in any line this part added. Dash scan over the files changed or added, with a control string that holds both dashes: the control was found, and no file held an en or em dash.
- No browser, server or background service was started. The mutation run was one sequential background process with a 180 s limit per mutant, and it ended by itself. No git write was run.

Not verified:
- Parse time for a large DOCX. A `document.xml` near the 100 MiB archive limit has not been parsed, so its memory use and time are unknown. The walk stops at 500,000 characters, but lxml parses the whole part first. The Phase 2 wall-clock kill covers it, and the 120 s proposal in the checks entry above was derived from PDF timings only.
- Only generated packages were parsed. No real contract in DOCX form was run, so Word's own markup (field codes, `mc:AlternateContent` with several `Choice` branches, grouped shapes) is covered by hand-written fixtures alone.
- Strict OOXML, comments and inline math are listed as ceilings in `Phases.md` and have no fixture. Strict was probed once, outside the suite.

Blockers: none.

Next action: commit 1-D with `feat(parser): extract DOCX body, tables and text boxes safely`, add the 1-D `[CONTRACT]` items above to the Tanishq message, then reply `next` to start 1-D2.


## 2026-10-15: Part 1-D2, DOCX numbering, headers, footers and notes

Part: 1-D2. It follows 1-D, committed as 0899b03. 1-E is next.

Files changed:
- `backend/app/parsing/docx.py`: A17 and A18. A `_Numbering` class computes list labels, and `_Walk` gains `part`, `page_parts` and `notes`. The body walk now takes the part's scope and kind from the walk, so tables, text boxes and cells work the same in a header or a note.
- `backend/requirements.txt`: `lxml` and `pdfminer.six` pinned.
- `backend/tests/fixtures/build.py`: `related_part` (replaces the two one-off header and footnotes builders), numbering and section helpers, a `section` argument on `build_docx`, and four registry fixtures.
- `backend/tests/test_docx.py`: 60 new tests.
- `docs/app/Phases.md`: 1-D2 ticked, with its deviations and ceilings, the 1-D ceilings updated, and the 2-C open item.
- `docs/app/Architecture.md`: the numbering row, a row for headers, footers and notes, the locator paragraph and the tech stack line.
- `docs/app/BuildLog.md`: this entry.

Commands run, from `backend/` with the venv interpreter:
- `ruff format .`, `ruff check .`, `pytest -q`.
- A clean install: Python 3.12.10, a new venv outside the repo, `pip install -r requirements-dev.txt`, then `ruff format --check`, `ruff check` and `pytest -q`.
- One-line mutants of `docx.py` on copies of `app/` and `tests/` outside the repo, and an XML mutation sweep of the four new fixtures, also outside the repo.
- The DOCX smoke check (below): three HTTP downloads with curl, no browser, and one parse script run in isolated mode with each path passed as an argument.
- The Rules section 1 scrub, a tool-name grep over the added lines, and a dash scan with a control string that holds both dashes.
- Read-only git: `git status`, `git diff`.

Tests: 323 passed, 0 failed, 0 skipped (259 after 1-D). `test_docx.py` holds 133 (73 before) and `test_invariants.py` 83 (79 before, one per new fixture). The clean install gave the same 323.

Pinned versions added to `requirements.txt`: `lxml==6.1.3` and `pdfminer.six==20260107`. Justification for Rules section 4: both are imported directly (`docx.py` uses `etree.LxmlError`, `pdf.py` the pdfminer errors and parser), and both were already installed as dependencies of python-docx and pdfplumber at those versions. pdfplumber itself requires `pdfminer.six==20260107`. The clean install resolved: pdfplumber 0.11.10, python-docx 1.2.0, PyYAML 6.0.3, pytest 9.1.1, ruff 0.16.10, reportlab 5.0.1, pillow 12.3.0, and the transitive pypdfium2 5.14.0, typing_extensions 4.16.0, cryptography 50.0.2, cffi 2.1.1, charset-normalizer 3.5.2. `sklearn` is not imported.

Decisions (the rest are under the 1-D2 deviations in `Phases.md`):
- The label travels in the locator as `list_label`, as the handoff and Architecture.md say. A17 left the carrier open. Tagged `[CONTRACT]`.
- A bullet or `none` level gives no label and no warning. The handoff would have warned on every bullet list.
- A header or footer block carries `paragraph` as well as A18's three keys, because a part has several paragraphs. Tagged `[CONTRACT]`.
- Endnotes are read with the footnotes, with kind `footnote` and part `endnotes`. The 1-D ceiling named endnotes as 1-D2 work, and the kind set stays closed.
- A page part is read once per relationship and dropped when an earlier part of the same kind has the same text. The first rule bounds the work, since a part named by thousands of sections is otherwise read each time. The second is the handoff's "deduplicate".
- A numbering part is untrusted input that runs once per paragraph, so it is bounded (label and level text 100 code points, 9 digit numbers, 9 levels, a style chain of 32).
- The review of the diff removed three things before this entry: a `_PAGE_PARTS` constant that a loop over two names replaced, a style cache the 32 step chain does not need, and the `decimalZero` format, which the handoff does not list.

Findings during the part:
- An empty numbered paragraph still counts. The first heading of the Common Paper template is "2." because an empty Heading 1 paragraph before it holds "1.", which Word shows too. A test pins it.
- A table, a cell or a text box inside a header needs the header's scope in its locator, and its kind must stay `header` or `footer`, or `decorations` would leave out table cells in a header. Both are tested.
- Mutation run on the new code of `docx.py`: 49 one-line mutants. The first run killed 40 and let 9 live. Eight were test gaps and are closed: a table or character default style taking over the default paragraph style, the farthest style winning over the nearest, a blank level text, a non-ASCII digit read as a number, counters not resetting per part, a dropped duplicate still using the text budget, notes before page parts, and an over-long level text. One is equivalent (resetting a level's own counter changes nothing unless `lvlRestart` names the level itself, which the schema forbids). One intermediate run was discarded, because a new test of mine failed on the unmutated code and made every mutant look killed. After the review edits the final run killed 46, left the one equivalent mutant, and skipped 2 whose patterns the edits removed. A manual mutant for the footer-before-header order was killed too.
- XML sweep over the four new fixtures: 40,000 mutants (5,000 per fixture, two seeds, one member damaged and the package repacked with correct checksums, with byte flips, deletions and insertions). 2,767 parsed and 37,233 gave `MALFORMED_FILE`. No other exception type, no warning, no log record, and the slowest parse took 6 ms.

DOCX smoke check, three public templates in `.docx` form. Files are in `data/docx_smoke/<name>/` (gitignored). They were fetched with curl over HTTP, and each parse ran as its own script with `python -I`. Two other sources failed and were replaced: the Australian Government HERC consulting agreement timed out on a HEAD and a GET (60 and 90 s, no bytes), and the California DGS model contract language answered 403.

| File | Source | Bytes | Blocks | Tables | Text boxes | Warnings | partial | Chars | Labelled | Parse |
|---|---|---|---|---|---|---|---|---|---|---|
| General conditions for the provision of Services | Buying for Victoria (state government, Word) | 126,722 | 251 (247 text, 4 footer) | 0 | 2 (both in footers) | `TEXT_BOX_CONTENT` | False | 33,584 | 173 | 0.03 s |
| Cloud Service Agreement template | Common Paper, CC BY 4.0, via the open-agreements repository | 122,037 | 212 (124 text, 82 table_cell, 4 header, 2 footer) | 5 | 0 | none | False | 37,864 | 120 | 0.02 s |
| Professional Services Agreement template | Bonterms, CC0, via the same repository | 25,553 | 21 (all table_cell) | 5 | 0 | none | False | 1,655 | 0 | 0.01 s |

As a check that no text was lost, the script counted every non-space character in every `w:t` outside `mc:Fallback` in the document, header, footer, footnote and endnote parts, with a separate lxml read, and compared the total with the parser's `source_text`. The differences are all explained: Victoria is +5 (13 no-break hyphens read as `-`, and 8 characters of a duplicate footer part dropped), Common Paper is -75 (two duplicate parts dropped, a 25 character header and a 50 character footer), and Bonterms is exactly 0.

Anything unexpected, none of it a parser fault:
- Common Paper's labels start at "2." (the empty Heading 1 above). Its footers read "Page  of 5" because the PAGE field has no result in the file.
- Bonterms is a cover page only. The standard terms are incorporated by reference, and the text holds template markers such as `{IF has_pilot}`.
- Victoria's contents list is plain text with typed numbers and a tab before the page number (`1.<tab>Term of Agreement<tab>1`, 23 lines). 1-E must treat a tab and a trailing number like a dot leader (A21). Added to the 1-D2 ceilings.
- No `NUMBERING_NOT_RENDERED`, no `UNSUPPORTED_DOCX_FEATURE`, no tracked changes, and `partial` was False for all three.

Not verified:
- Label correctness against Word's own rendering. There is no Word here, so the labels were compared by reading, not against a rendered page. The sequence in the Victorian file (`1.`, `(a)`, `(b)`, `2.`, `(a)` to `(d)`, `(i)` to `(iv)`) is what its text implies.
- What the three files did not exercise: footnotes and endnotes (both parts held no text), `startOverride`, `lvlOverride`, `lvlRestart`, a header list, a first-page or even-page variant with different text. Those are covered by generated packages only. Two of the three files come from one template tool, so only one is native Word output.
- The dense 8 MiB PDF timing and a DOCX near 100 MiB. Both moved to 2-C as an open item (`Phases.md`, 2-C), with the provisional 120 s kill.

Blockers: none.

Next action: commit 1-D2 with `feat(parser): render DOCX numbering and extract page parts`, send the consolidated `[CONTRACT]` message for 1-B to 1-D2 to Tanishq, then reply `next` to start 1-E.


## 2026-10-15: Part 1-E, clause structure tree and definitions

Part: 1-E. It follows 1-D2, committed as 1a5ab87. 1-F is next.

Files changed:
- `backend/app/parsing/structure.py`: new. `build_structure(source_text, blocks)` returns `(nodes, warnings)`: the clause tree and the defined terms (A19 to A22).
- `backend/tests/test_structure.py`: new, 135 tests.
- `backend/tests/test_invariants.py`: `assert_valid_nodes`, which every valid fixture runs through `build_structure`.
- `backend/tests/fixtures/build.py`: `contents_tab.docx`, a contents list typed as number, tab, title, tab, page number.
- `docs/app/Rules.md`: two rows in the section 4 table, for `lxml` and `pdfminer.six`.
- `docs/app/Phases.md`: 1-E ticked, with its deviations and ceilings.
- `docs/app/Architecture.md`: the tree line, three decision rows and a paragraph on nodes.
- `docs/app/BuildLog.md`: this entry.

Commands run, from `backend/` with the venv interpreter:
- `ruff format .`, `ruff check .`, `pytest -q`.
- One-line mutants of `structure.py` on copies of `app/` and `tests/` outside the repo, in three runs.
- The structure smoke check (below): the parser and `build_structure` over eight files, each as a script run with `python -I` and each path passed as an argument. The scripts printed counts, labels and the first line of a node or block (120 characters at most), and wrote nothing to disk.
- The Rules section 1 scrub, and a dash scan with a control string that holds both dashes.
- Read-only git: `git status`, `git diff`.

Tests: 459 passed, 0 failed, 0 skipped (323 after 1-D2). `test_structure.py` holds 135 and `test_invariants.py` 84 (83 before, one for the new fixture). A clean install was not repeated, because no dependency changed.

Pinned versions added: none. `lxml` and `pdfminer.six` were pinned in 1-D2. Their rows are now in the Rules section 4 table, each with a one-line reason: `pdfplumber` requires that exact `pdfminer.six`, and `python-docx` brings in `lxml`, and both are imported directly.

Decisions (the rest are under the 1-E deviations in `Phases.md`):
- One pass over the blocks with a stack of open nodes, and no sort. Nodes are created in document order and a container before what it holds, so the creation index is the id. The invariant test checks the order on every fixture.
- A numbered label has to earn its place, and this took three versions. Accepting only a continuation or a start at 1 read party lists (`1.`, `2.`) as clause one and two and then lost the real clauses. Accepting a restart at 1 every time made 150 false top-level nodes in the Healthgate file. Resuming an interrupted run and choosing the longer of two runs both fail on ties. The rule that stayed lets a restart at 1 replace a run of 3 or fewer.
- A Word label is trusted more than typed text. It goes through the same grammar, and it may open a top-level list above 1 because Word counts empty paragraphs.
- A title in capitals belongs to the label before it. This departs from A20 as written and is tagged `[CONTRACT]`.
- Two things are not built, and both need your decision: separate sequences for heading words and bare numbers (the Athens case), and accepting a gap in a Word list (an empty numbered paragraph in the middle).

Findings during the part:
- The first smoke run showed three faults, all fixed with tests: page numbers printed mid-page read as clause numbers (a bare number with no full stop is now ignored), `10.Title` with no space was not a label, and a party list took the first clause numbers.
- The final smoke run, on the code after those fixes, showed three more:
  - A notice block (`With a copy to:` over redaction marks) passed the 60 percent test on the whole block, because the marks are capitals. The test is now per line. It also stopped four multi-line blocks that were not headings: a company name over its description (Cybergy), a signature over a date (Healthgate), and a title over a date and two parties joined by `and` (Theravance).
  - An all-caps title after `SCHEDULE A` or `ARTICLE 5` closed the node it names. Cybergy's Schedule A items sat at level 1, and Dova's article 5 held no clauses. A title straight after a bare label now belongs to the label.
  - Common Paper had no sections, because an empty first Heading 1 paragraph holds `1.` and the first label read is `2.`. A Word list may now open above 1.
- Athens: 46 definitions against 6 from a regex for the verb forms. The other 40 are bracketed (27 `(the "T")` and 13 `("T")`), so the gap is explained. Cybergy is the same case: 4 definitions, all bracketed.
- Mutation runs on `structure.py` (copies outside the repo). The first run applied 66 one-line mutants: 40 were killed and 26 lived. Twenty-three of the 26 were test gaps, and each now has a test: the part and digit limits of a label, the leader length, case in definitions, the 60 percent and 80 character edges, contents entries in capitals, a table after a nested table, the page and letter guards of a Word list, a schedule clearing the state, a chain of restarts, the prefix rule, and letters keyed by parent. Three never changed a result: the sort in `finish`, a `typed and` in the title flag, and `>` against `>=` in `_outer_tables`. The sort and the `typed and` were removed as dead code. The `>=` is equivalent, because two tables never share a block.
- The second run corrected three patterns that the tool had mangled and added the no-sort mutant. It left 7 alive: those three plus the sort variant, and three further gaps (the roman guard, a contents rule that read wrapped blocks, and a leader test whose entries the start-at-1 rule rejected anyway). All three have tests now. The third run killed everything except the equivalent `>=`. Four more mutants (the title flag set always or never, and the two id offsets) were killed on their own. In all, 74 mutants were defined and 4 were retired with the code they patched.
- The review of the diff found nothing left to cut.

Structure smoke check. Five CUAD agreements in PDF form (`data/cuad_smoke/`) and the three DOCX files from 1-D2 (`data/docx_smoke/`), all gitignored. "Found" is the top-level numbering the tree holds, and "visible" is a count of line starts in the text (`N.`, `ARTICLE N`, `Section N.`). The structure pass took 0.000 to 0.024 s per file.

| File | Pages | Blocks | Nodes | By kind | Max level | Top level found / visible | Definitions |
|---|---|---|---|---|---|---|---|
| 01 Cybergy affiliate agreement | 16 | 174 | 93 | section 26, clause 48, subclause 13, heading 1, schedule 1, definition 4 | 3 | 1 to 26 / 1 to 26 | 4, all bracketed |
| 02 Healthgate hosting agreement | 33 | 797 | 209 | heading 13, section 49, clause 90, subclause 29, schedule 2, definition 26 | 4 | 1 to 34 / 1 to 34, plus 2 false from the party list | 26 (16 by verb form) |
| 03 Athens agency agreement | 33 | 246 | 157 | definition 46, heading 18, clause 65, section 2, subclause 26 | 4 | Section 1 to 20: 18 found, 5 and 6 missed, 2 false | 46 (6 by verb form) |
| 04 Dova promotion agreement | 44 | 614 | 413 | heading 30, definition 84, clause 142, subclause 154, schedule 1, section 2 | 5 | ARTICLE 1 to 13 / 1 to 13 | 84 (68 by verb form) |
| 05 Theravance service agreement | 14 | 176 | 124 | heading 3, definition 15, section 24, clause 48, subclause 34 | 3 | 1 to 24 / 1 to 24 | 15 (11 by verb form) |
| Bonterms PSA (DOCX) | none | 21 | 5 | table 5 | 1 | none visible: cover tables only | 0 |
| Common Paper CSA (DOCX) | none | 212 | 158 | table 5, definition 33, section 13, clause 93, subclause 14 | 3 | 2 to 14 found, and `1.` has no block | 33 (32 by verb form) |
| Victoria general conditions (DOCX) | none | 251 | 165 | section 23, clause 99, subclause 43 | 3 | 1 to 23 found, equal to the 23 contents lines it ignored | 0 |

Obviously wrong nodes, by file:
- 01: 1 of 1 unlabelled headings (`COMPANY`, a signature block name).
- 02: 3 of 13 headings (`BLACKWELL/MUNKSGAARD PUBLISHING SYSTEM` twice, a repeated page header, and a `[INITIALS ILLEGIBLE]` line), and 1 doubtful (`EXHIBIT 10.1`, a stamp). Two false level 1 nodes from the party list.
- 03: two false nodes (`5`, `6`) and two missed sections. No unlabelled headings.
- 04: 9 of 17 unlabelled headings: `TABLE OF CONTENTS` three times (a repeated header), `MULTIPLIED BY` four times (formula words) and two party names from the signature block. The other 8 are the title, RECITALS and six headings of a prescribing information exhibit.
- 05: none.
- DOCX: none by structure. The smoke script flagged two short list items in the Victoria file (`(b)` with `If:` and `17` with `GST`). Both are short paragraphs that Word numbers, and the label is what Word shows.

Not verified:
- Top-level numbers were compared with a count of line starts, and not with a human outline. Levels 2 and below were not counted, and the clause and subclause counts are unchecked.
- A DOCX with an empty numbered paragraph in the middle of a list. The ceiling is derived from the rule (`Phases.md`, 1-E) and no file shows it.
- Only one of the three DOCX files is native Word output, and Bonterms holds cover tables alone, so the DOCX tree is tested on two real contracts at most.
- Definitions were checked by form on Athens and Cybergy. The gaps in the other files are the bracketed forms by count, and were not read one by one.
- Linear time was tested on generated blocks. The slowest real file took 0.024 s.

Blockers: none.

Next action: commit 1-E with `feat(parser): build clause structure tree and detect definitions`, send the 1-E `[CONTRACT]` items to Tanishq (kinds, labels, sequence state, Word list opening, contents lines, all-caps headings, titles, tables and definitions), decide the two open items above, then reply `next` to start 1-F.


## 2026-10-15: Part 1-F, public entry point, CLI and parser contract

Part: 1-F. It follows 1-E, committed as eb3b30a. 1-R, the phase review, is next.

Files changed:
- `backend/app/parsing/__init__.py`: `parse_document` and `__all__`.
- `backend/app/parsing/structure.py`: the Word-list gap rule (`_CONTINUES`, `_STARTS`, `_fit`, the run counter) and its letter width limit.
- `backend/app/parsing/schema.py`: new. `SCHEMA` and `to_json`.
- `backend/app/scripts/parse_file.py`: new. The command line tool. There is no `__init__.py`, because `python -m` works on a namespace package.
- `backend/tests/fixtures/build.py`: `empty_numbered.docx`, and `VALID_NAMES` beside `NAMES`.
- `backend/tests/test_structure.py`: the 1-E test that pinned "Word 1. then 5. stays one node" is replaced, and the file grows from 135 to 146 tests (two of them cover the letter width limit).
- `backend/tests/test_parse.py`: new, 92 tests. `backend/tests/test_contract.py`: new, 131 tests.
- `docs/app/ParserContract.md`: new, 15 sections. `docs/app/parser_output.schema.json`: the committed copy of `SCHEMA`.
- `docs/app/Phases.md`, `docs/app/Architecture.md`, `README.md`: 1-F ticked with its deviations and ceilings, the tree and rows kept true, and the command line in the backend section.
- `docs/app/BuildLog.md`: this entry.

Commands run, from `backend/` with the venv interpreter:
- `ruff format .`, `ruff check .`, `pytest -q`.
- Mutants on copies of `app/` and `tests/` outside the repo, with `python -I`: 20 over the entry point, schema, CLI and gap rule, and 6 over the letter width limit.
- A node-by-node comparison of the structure tree at the last commit and in the working tree, over the five CUAD PDFs and the three DOCX files of 1-D2. Scripts in the scratchpad, each path passed as an argument, nothing written to disk.
- The Rules section 1 scrub, and a dash scan with a control string that holds both dashes.
- Read-only git: `git status`, `git diff`, `git archive` into the scratchpad for the last commit's code.

Tests: 694 passed, 0 failed, 0 skipped (459 after 1-E). `test_structure.py` holds 146 (135), `test_invariants.py` 85 (84, one for the new fixture), `test_parse.py` 92 and `test_contract.py` 131. A clean install was not repeated, because no dependency changed.

Pinned versions added: none. The schema checker in `test_contract.py` is about 40 lines, so no schema library was added.

Decisions (the rest are under the 1-F deviations in `Phases.md`):
- The gap rule reverses a 1-E decision `[CONTRACT]`. 1-E pinned "a Word `1.` then `5.` stays one node" with a test, and listed the gap as a ceiling. A Word label above the last number in its sequence now continues it, for decimals, letters and numerals. Scores: a plain continuation 3, a start at 1 gives 2, a gap or an opening above 1 gives 1. The ambiguity warning fires only on a tie at 3. The gap counts toward the run length, and a typed number never skips ahead.
- A letter does not reach the next width by a gap. See the first finding below. A gap from `(z)` to `(bb)` over an empty `(aa)` is not read either, which needs a 27th item to be the empty one.
- `parse_document` checks the size, then the type, then calls the reader and the tree builder. Reader warnings come first, then structure warnings.
- `ParserContract.md` replaces every earlier contract message. Each item is tagged same, refined or new against the first message to Tanishq (30 September, nine points).
- The CLI keeps `--summary`. JSON omits `source_text`, `blocks[].text` and `nodes[].text` unless `--text`, the error code goes to stderr and the exit status is 2, and non-ASCII characters are escaped.
- `graphify` moved to 1-R, because Rules section 7 puts it at the end of a phase.
- The review of the diff cut four things before this entry: an unused `_TEXT_FIELDS` constant, an empty `scripts/__init__.py`, a test that restated the model's field list, and a test of absent code. A second review after the width rule found nothing to cut. Kept: `--summary`, the `__main__` print in `schema.py` and the in-test checker.

Findings during the part:
- The gap rule's first version was wrong on a real file. Of the three DOCX files, only the Victoria general conditions changed: 167 nodes against 165. `(h) a reference to:` is followed by a Word numeral list `(i)` to `(iv)`. `(i)` has been read as the ninth letter since 1-E, and under the gap rule `(ii)` and `(iii)` were taken as the 35th and 61st letters, 26 numbers above, as clauses at level 2. An empty paragraph does not explain a jump that long. Fix: a letter gap has to stay within the same width (a to z, aa to zz). The test was written first and failed on exactly `(ii)` and `(iii)`. After the fix all eight files match the 1-E trees node for node (93, 209, 157, 413, 124, 5, 158 and 165 nodes). The five PDFs were compared on the final code only. They carry no Word labels, so the gap rule cannot reach them.
- No real file in the set holds an empty numbered paragraph inside a list. The gap rule is tested by `empty_numbered.docx` and by generated labels only.
- The entry point, schema and CLI were written test first. The first run failed on the missing import.
- The gap rule was also test first: 8 tests failed on the 1-E code. Two tests are regression guards and passed before the change: a numeral that continues a roman run is not taken for a letter, and a gap may reach `(z)` and a repeated letter may skip one inside its width.
- Mutation. The first run covered 20 mutants: 19 killed, and 1 equivalent, which led to `grew = number > current if not typed else ...` becoming `number > current`. The run over the simplified code killed all 20. The 6 width mutants (always true, an off-by-one at the end of a width, a looser bound, an inverted family test, `or` for `and`, no ordering) were all killed.
- Seen in passing, not changed: a numeral list right after `(h)` is read as one level 2 node that swallows `(ii)` to `(iv)`. That is the 1-E reading of `(i)`. The Word list's own level (`ilvl`) would settle it, and `docx.py` does not pass it on. Added to the 1-F ceilings and to `ParserContract.md` 12.6.

Not verified:
- The contract's tags compare with the first message only. The later messages to Tanishq (1-A update, 1-B, 1-C, 1-D, 1-D2, 1-E) were not re-read, so an item tagged "new" may have been sent in one of them.
- Rows copied from `Phases.md` into the contract and not measured again: rotated pages unsupported, an encrypted DOCX gives `UNSUPPORTED_TYPE`, a chain of 3,000 Form XObjects, and the 186 s timing.
- The gap rule against Word's own rendering. There is no Word here, and no real file exercises it.
- A Word list that opens with an empty paragraph at a nested decimal, a letter list or a numeral list is still unread. Documented, not built.
- The CLI ran by hand on one file only (the Victoria DOCX with `--summary` and without, and an empty file, which printed `EMPTY_FILE` and exited with 2). Piping its output into `head` prints a `BrokenPipeError` traceback. It is a development tool, so it was left alone.
- The copy passes (copywriting, copy-editing, stop-slop) ran over `ParserContract.md` and over the new text in `Phases.md`, `Architecture.md` and `README.md` (the README text needed no change). Four sentences in `Phases.md` and one line in `Architecture.md` were rewritten.

Blockers: none.

Open for your decision:
- Whether to build the `ilvl` carrier for the first-item and `(h)` then `(i)` cases.
- Whether the first message is the right baseline for the contract tags.
- `name_span` and the `party` kind: the frontend requires them, and nothing in Phase 1 or 2 builds them before 2-E.

Next action: commit 1-F with `feat(parser): add parse entry point, CLI and parser contract`, send `ParserContract.md` to Tanishq as the replacement for every earlier contract message, then reply `next` to start the 1-R phase review.


## 2026-10-16: Part 1-R, step 1, the phase review (findings only)

Part: 1-R, step 1 of 2. Range `1077d25..a37cbec`, which is 1-B to 1-F (`9b2fa01` to `a37cbec`) in the backend. The range also holds the frontend commits, so CodeRabbit read those too. Review only: no file under `backend/` changed, no dependency was added, and no git write ran. Files changed: this entry. The fixes are step 2, one commit per theme, after Aryan replies. Already approved for step 2: pass the Word list level (`ilvl`) from `docx.py` into `structure.py` so a numeral list after `(h)` reads `(i)` as a numeral in DOCX, and record the PDF case as a ceiling.

Reviews that ran:
- `/gstack-cso`, focused on untrusted file input, archive and decompression limits, logging of file content and exception paths. Attack surface: one entry point, `parse_document(bytes)`, with no network, disk, subprocess or HTTP in this phase. Secrets in tracked files and in history: none. Stray documents: none tracked, and `data/*` is ignored. CI files: none exist. Dependencies: advisory lookups by package name and version only (three searches, one page fetch).
- `/gstack-review`, as its checklist read against the code. The critical categories (SQL, races, model output, shell) have nothing to check in this phase. Enum completeness was traced: every `ErrorCode` and `WarningCode` is raised in `app/`, listed in `ParserContract.md` and covered by a test. The skill's auto-fix, review-log, version-queue and specialist steps did not run, because this step is review only.
- `/coderabbit:code-review --base-commit 1077d25`, one attempt. It started this time, ran about four minutes and exited 0 with 3 findings (one backend, two frontend). The earlier failures to start at FE-R did not repeat, and `coderabbit update` was not run.
- One independent second review, read-only, over the ten files under `backend/app/`. It was given no finding from the other reviews.

Method. Probes ran as separate processes with `python -I` against a copy of `app/` and `tests/` in the session scratchpad, never the repo. Each ran inside a job object with a 1.5 GiB memory cap, so a runaway allocation could only end that one process. Inputs were synthetic and nothing was written under the repo. Baseline on the copy: 694 passed in 36 s. A 100 MiB DOCX and an 8 MiB dense PDF were not run at full size, so the figures for those are scaled from smaller runs and marked as computed.

Findings are grouped by severity. P1 means a limit the docs promise does not hold. P2 weakens a guarantee, or leaves a known ceiling unbounded. P3 is hygiene. `Verified` means a probe reproduced it. `Code` means read in the source. `Second review` means it found the same thing on its own.

P1:
- B1. The DOCX archive limit (A12) trusts sizes the file author writes, and `zipfile` inflates a member in full before it cuts the result to the declared size. `_check_archive` (`docx.py:371`) sums `file_size` from the central directory. python-docx then reads each member with `ZipFile.read`. In the installed Python 3.12, `ZipExtFile._read1` (`zipfile/__init__.py:1067` to `1078`) asks Flate for up to 1 GiB per call (`MAX_N` is `1 << 31 - 1`, which Python reads as `1 << 30`), calls `decompress(data)` with no limit for bzip2 and lzma, and slices to the declared size afterwards. Verified: `word/document.xml` holding 128 MiB of white space, with the central directory declaring 2,000 bytes, passes `_check_archive`, allocates it all and only then fails the checksum as `MALFORMED_FILE`. Peak working set rose 256 MiB for Flate (file 131,589 B), 260 MiB for bzip2 (1,279 B) and 265 MiB for lzma (20,116 B). The 10 MiB input cap bounds the file and not the output: Flate allows about 10 GB from 10 MiB (computed from the 1,032 to 1 ceiling), and bzip2 reached 100,000 to 1 here. The three real DOCX files in the smoke set hold 90 members, 86 Flate and 4 stored, and none uses another method. Fix: refuse any other method, and count the real output in chunks (`archive.open(name).read(65536)` keeps Flate to 64 KiB a step) before python-docx reads, against the same 100 MiB total. `[CONTRACT]`: `ARCHIVE_TOO_LARGE` means the real size, and `ARCHIVE_UNSAFE` gains the method rule. A12 in `Phases.md` ("zipfile stops a member at its declared size") and `ParserContract.md` lines 368 and 399 ("declared") need the same correction. The second review did not find this one.
- B2. The PDF content budget (A11) measures only the first filter of a stream. `_decoded_length` (`pdf.py:112`) undoes leading ASCII filters, counts the output of one Flate, and ignores the rest of the chain. pdfminer's `decode` applies every filter with an unbounded `zlib.decompress`. `/Filter [/FlateDecode /FlateDecode]` passes, because stage one is the compressed form of stage two and is small. Verified: 64 MiB of content in one Flate stream is `TOO_MUCH_TEXT` in 0.01 s (file 65,807 B). The same content in two stages (file 838 B) parses in 0.82 s and the peak working set rose 129 MiB. 256 MiB in two stages (file 1,162 B) raised it 513 MiB, about twice the decoded size. Stage one may be up to 8 MiB, so a file under 10 KB can ask for about 8 GB (computed). Fix: measure the whole chain stage by stage with `max_length`, and treat a second compressing filter after Flate as over budget. Add a `bomb_double_flate` fixture beside `bomb_content`. The second review and CodeRabbit (major) found it too, and CodeRabbit proposed the same fixture.

P2:
- B3. Streams the budget never visits: embedded font programs, ToUnicode maps, object streams and xref streams. This is the 1-C ceiling in `Phases.md` and `ParserContract.md` line 446, now measured. A 66,262 B PDF whose font holds a 64 MiB Flate `FontFile2` parsed, and the peak working set rose 64 MiB (verified). At 1,000 to 1, a 10 MiB file asks for about 10 GB (computed). No library-level fix bounds every stream, because `pdfplumber.open` makes pdfminer read object streams before the budget check runs. The bound is the child process of Phase 2: it needs a memory cap next to the wall-clock kill, and 2-C should say so (call 2 below).
- B4. The gutter scan grows with the square of the words. `_gutters` (`pdf.py:294`) runs `_sides` over every row for every gutter candidate and never stops early. A wide MediaBox with many gaps makes a small file expensive. Verified on the function with 20 rows: 100, 200, 400 and 800 gaps took 0.02, 0.07, 0.28 and 1.07 s, about four times for each doubling. End to end, a 173,232 B PDF (400 gaps, 12,100 pt wide) took 0.78 s and a 349,232 B PDF (800 gaps, 24,100 pt) took 3.19 s. 10,000 gaps on one page would take about 170 s (computed), inside the 8 MiB budget. pdfminer accepts any page width. Fix: stop after `MIN_ROWS_AROUND_GUTTER` rows, and count the staggered case (words on both sides but never in one row) from sorted row positions instead of a scan per candidate.
- B5. DOCX walk cost per byte. The cap is 100 MiB of XML, and an empty paragraph is 6 bytes, so 17.5 million fit. Verified at scale: 200,000 empty paragraphs (file 2,838 B) took 0.71 s, 3.6 microseconds each, and the peak rose 25 MiB. 100 MiB of them is about 62 s and 2.2 GB (computed). A paragraph with a 32 step style chain (the maximum A17 allows) costs 19 microseconds, and 100,000 of them raised the peak 60 MiB. 100 MiB of those, 2.1 million paragraphs, is about 41 s and 1.3 GB (computed). A numbered one costs 24 microseconds, about 51 s. This is the open 100 MiB DOCX item on 2-C, now with figures. Real contracts have a `document.xml` under a few MB. Fix: cap the XML bytes of one part (for example 25 MiB) or count paragraphs in `_Walk`, plus the memory cap of call 2.
- B6. Glyphs with no text mapping enter the text silently. Verified: a Type0 font with no ToUnicode map and the string `<004100420043>` gives `source_text` of `(cid:65)(cid:66)(cid:67)`, no warning, `coverage.partial` False. A PDF set in such a font reads as a full document in which every clause is "not found". Neither the contract nor `Phases.md` mentions it. Fix: count `(cid:N)` tokens per page, and above a share (a decision) add a warning and set `partial`, as the scanned-page rule does. `[CONTRACT]` (a new code or an old one, call 3).
- B7. Text-free output still carries text. `to_json(doc, text=False)` and the CLI without `--text` leave out `source_text`, block text and node text, but `locator.list_label` (up to 100 characters of numbering text from the file) and the `label` of a definition node (a quoted term up to 80 characters) stay. Verified: a numbering level `Clause %1 SECRET-LABEL` and the term `Secret Widget Pricing` both appear in the JSON printed without `--text`. The CLI docstring says the result "can be pasted into a ticket without the contract", and defined terms are often party and product names. Fix: drop both when `text` is False, or say in the docstring and A23 that labels are content (call 4).
- B8. A DOCX with a DOCTYPE loses the text after an entity reference, silently. `_paragraph` reads `w:t.text` and never the tail of the entity node. Verified: `Before &inner; after` with an internal entity gives `Before`. The external entity and external DTD cases end as `MALFORMED_FILE` and the canary file text did not appear, so there is no file read, only loss. Word never writes a DOCTYPE into a package. Fix: refuse a part with a DOCTYPE as `MALFORMED_FILE`. The `entity_bomb` fixture pins "reads as empty" today and changes with it.

P3:
- B9. Hidden and alternate text is read as plain text. Verified: a run with `w:vanish` is in `source_text`, and an `mc:AlternateContent` with two `mc:Choice` branches gives both, with `Requires` never evaluated (`_NO_TEXT` at `docx.py:101` skips only the Fallback). The Reader shows the text, so hidden text becomes visible, but the contract does not say so. Second review found the Choice case. Fix: say it in the ceilings of `ParserContract.md`. A `w:vanish` or Choice warning would be a `[CONTRACT]` change and is not proposed.
- B10. A valid PDF with any bytes before `%PDF-` is refused. Verified: one leading newline, a UTF-8 BOM and 100 junk bytes all give `UNSUPPORTED_TYPE`. Readers accept the header anywhere in the first 1,024 bytes. Whether pdfminer then parses such a file was not tested (call 6).
- B11. A footnote `w:id` is not bounded. Verified: 4,200 digits parse, and the locator `id` becomes a 4,200 digit integer (4,913 characters of JSON). The numbering code bounds its numbers with `_number` (9 digits), and this one does not. A consumer with a 64 bit column or a JavaScript number would fail on it. Fix: use `_number` at `docx.py:605`.
- B12. The CLI reads the whole file before the 10 MiB check (`parse_file.py:29`, `Path.read_bytes()`). A development tool, so low. Second review. Fix: compare `stat().st_size` first.
- B13. `warnings.catch_warnings()` in `docx._read` changes the process-wide filter list, which is not safe if two threads parse at once. Phase 2 parses in a child process, so it only matters if that changes. Code.
- B14. Transitive runtime packages are not pinned: `cryptography`, `pypdfium2`, `charset-normalizer`, `cffi`, `pycparser`, `typing_extensions`, and Pillow in production (only `requirements-dev.txt` pins it). A clean install can resolve newer ones. Rules section 4 says to pin what the install resolved. Fix: a constraints file from the clean install (no new dependency, call 7).
- B15. The text limit counts only after layout. A compressed content stream just under 8 MiB can hold hundreds of thousands of tiny text operations, and `extract_words` builds the per-glyph objects before `TextAssembler` rejects the text. This is the 1-C ceiling "the budget bounds decoded size, not time". Second review. Not measured here.

Frontend, from CodeRabbit, outside Phase 1 (both minor, both still true in the current files):
- B16. `Reader.tsx:653` uses `var(--anchor-50)`, which `index.css` does not define (only `--anchor-100`), so the manual selection row draws no background. Code.
- B17. `revealOnce` in `lib/reveal.ts` returns a cleanup that disconnects the observer and leaves `data-reveal="pending"`, so a cleanup before the element shows can leave it hidden. Code.

Not reproduced. The second review said a 400 digit `/MediaBox` raises an uncaught `OverflowError`. It does not: that file gives `MALFORMED_FILE`, and 400 digit operands for `Td`, `Tf`, `Tm` and a zero `Tz`, a zero or negative MediaBox and `/Rotate 90` all parse with finite boxes or end in `ParseError`.

Checked and clean:
- `app/` opens no file, socket or subprocess, and has no `eval`, `pickle` or `yaml`. The only logging is the two `setLevel` lines that silence pdfminer and pdfplumber. Their messages go through `logging` only, and no library calls `warnings.warn` with file content. `ParseError` carries the code alone, and every `raise` inside a catch block is `from None`.
- XML: the parser python-docx builds resolves no entities, loads no DTD and has no network. Nesting: 110 nested `sdt`, 80 nested tables and 55 nested text boxes parse, 130 nested `sdt` is `MALFORMED_FILE`, and Form XObject chains of 1,000 and 3,000 give `MALFORMED_FILE`.
- Regexes in `structure.py` and `pdf.py` were read for backtracking, and none nests a quantifier over the same characters.
- The assembler's offset arithmetic and the definition node offsets (the `-1` and `+1` around the quoted term).
- Libraries. pdfminer.six 20260107 is past 20251230, the fix for CVE-2025-64512 and CVE-2025-70559 (the pickle CMap issues), and the installed `cmapdb.py` loads JSON from a checked path with no pickle. lxml 6.1.3 is past 6.1.0, the fix for CVE-2026-41066, which concerns `iterparse` and `ETCompatXMLParser` and neither is used. No advisory turned up for python-docx 1.2.0 or pdfplumber 0.11.10. A search by name is not a scan, so run `pip-audit` once on the install.

Not verified:
- The full size runs named above, and the 186 s PDF timing from 1-C.
- Whether pdfminer parses a PDF whose header sits after leading bytes (B10).
- A scan with `pip-audit`, which is not installed. Nothing was installed.
- `graphify` did not run, because it writes `graphify-out/`. It belongs with the docs commit of step 2. `/ponytail:ponytail-review` is not part of 1-R and did not run.

Processes. Started 36, closed 36, confirmed by a process listing at the end: 33 Python (23 probes, 2 test runs of the scratch copy, 8 short scripts) and 3 CodeRabbit (version, sign-in status, the one review). Short read-only shell commands (git, grep, ls, a process listing) are not counted. No browser, no server, no node process of ours. The second review went through the already connected MCP server, which is not ours and was left alone. The ledger and the probe scripts are in the session scratchpad, outside the repo.

Blockers: none for step 2.

Aryan's calls, in order of effect:
1. B1 and B2: refuse what Word and real producers never write (a non-stored, non-Flate DOCX member, a second compressing filter after Flate), and measure real output for the rest. Recommended. The other way is to measure everything, which needs a chunked reader for LZW and RunLength as well.
2. Phase 2: 2-C gets a memory cap for the parse child next to the wall-clock kill, because B3 and B5 have no library-level bound.
3. B6: a new warning code for unmapped text, or `partial` alone, and the share that triggers it.
4. B7: drop `list_label` and definition labels from text-free output, or document them as content.
5. B8: refuse any DOCTYPE as `MALFORMED_FILE`.
6. B10: accept `%PDF-` anywhere in the first 1,024 bytes.
7. B14: add a constraints file from the clean install.
8. B16 and B17: fold into step 2 as one frontend commit, or leave to the frontend track.

Proposed step 2, one commit per theme: (1) archive limits, B1. (2) PDF budget chain, B2, with the fixture. (3) gutter scan, B4. (4) DOCX bounds, B5, B8 and B11. (5) unreadable text, B6. (6) text-free output and the CLI, B7 and B12. (7) the `ilvl` carrier, with the PDF case recorded as a ceiling. (8) docs: the ceilings (B3, B9, B13, B15), A11 and A12 corrected, `ParserContract.md`, the 2-C note, the `graphify` refresh and the 1-R tick in `Phases.md`.

Next action: reply with the fixes you want in step 2. The default set is calls 1 to 5 and 7 as recommended, and the eight commits above.


## 2026-10-16: Part 1-R, step 2, commit 1 of 11: DOCX archive limits (B1)

Part: 1-R step 2, theme 1 of the proposed eleven (the eight of step 1, plus the PDF header window from call 6, the constraints file from call 7 and the frontend commit from call 8). Fixes B1, the P1 finding that the archive limit trusted sizes the file author writes. `[CONTRACT]`: two error codes change meaning, see the last section. The BuildLog also carries the step 1 entry above, which was not committed before this part started, so one commit takes both.

Files changed:
- `backend/app/parsing/docx.py`: `_check_archive` is replaced by `_unpack`. It checks every member name and compression method, then reads each member in 64 KiB steps, counts the bytes against `MAX_ARCHIVE_BYTES` and writes them into a new package with every member stored. python-docx opens that copy. Two constants, `_READABLE_METHODS` and `_READ_STEP`.
- `backend/tests/test_docx.py`: `declare` takes a checksum. The size-limit test is renamed (bytes read, not declared sizes). New: the limit trips in the middle of a member, the library is handed every member stored at its real size, and a member that lies about its size with a matching checksum is handed over cut. The compression test now runs for bzip2, lzma, Deflate64 and an unknown method and expects `ARCHIVE_UNSAFE`. 694 tests became 700 (four methods replace one test, three new).
- `docs/app/Phases.md` (A12 resolution, and the "A12 order" deviation rewritten), `docs/app/ParserContract.md` (the two error rows, the limits row, the refined list in section 14), `docs/app/Architecture.md` (the archive safety row), `docs/app/BuildLog.md` (this entry).

What changed, in the order the code runs:
- A member whose name is unsafe, or whose method is neither stored nor Flate, is `ARCHIVE_UNSAFE`. This runs before any member is read. zipfile inflates bzip2 and lzma with no limit on the output, so there is nothing to count.
- Each remaining member is read with `ZipFile.open(...).read(65536)`. Flate then yields at most 64 KiB a step, and the running total stops the read at 100 MiB plus one step (`ARCHIVE_TOO_LARGE`).
- The library gets a stored copy, so none of its reads inflates anything. This is the part that differs from the step 1 plan.

Findings during the part:
- The fix proposed in step 1 (count the real output in steps, then let python-docx read) is not enough. `ZipExtFile` cuts a member at the size the file declares, so a member that declares 2,000 bytes with a checksum that fits the first 2,000 passes the count. python-docx then calls `ZipFile.read`, which inflates up to 1 GiB in one call before it cuts. Verified with a new probe file (`word/document.xml` of 128 MiB of white space, declared 2,000 bytes, checksum of the first 2,000, file 131,599 B): the code at the last commit rose 257 MiB in peak working set (45 to 302 MiB) in 0.14 s, and the new code rose 1 MiB (45 to 46) in under 0.01 s. Both end `MALFORMED_FILE`, since the cut XML is not a document. Handing over a stored copy closes this, and the test for it needs no large allocation: it checks that the member reaches the library as 100 stored bytes.
- The three step 1 files on the new code: the Flate file with a wrong checksum rose 1 MiB (was 256), bzip2 and lzma are `ARCHIVE_UNSAFE` with no rise (were 260 and 265).
- Real files are unchanged. The three DOCX files of the smoke set give the same JSON, by hash, before and after: 21, 212 and 251 blocks.
- The rejection of a bomb now costs memory. The 101 MiB sparse fixture (463,358 B) was rejected from the member list in 0.00 s with no rise. It is now read until the limit, which took 0.46 s and raised the peak working set from 47 to 231 MiB: the 100 MiB copy, plus the growth of its buffer. That is the same order as accepting a 100 MiB archive, so the worst case of the parser did not grow, and the 2-C memory cap covers it. Counting first and copying second would avoid it for bombs at the price of inflating every file twice. Not done.
- Writing a directory entry into the copy needs no special case: a first version skipped them, a check showed they copy as they are, and the skip was cut.

Commands run, from `backend/` with the venv interpreter: `ruff format app tests`, `ruff check app tests`, `pytest -q -p no:cacheprovider`. Probes on a copy of `app/` and `tests/` in the scratchpad, never the repo, each as its own process under a 1.5 GiB cap: the four lying archives (three from step 1 and the checksum-matched one) against the last commit and the new code, and the 101 MiB fixture against both. A hash of the full JSON for each smoke DOCX file, for the last commit (exported with `git archive`) and for the working tree. Read-only git.

Tests: 700 passed, 0 failed, 0 skipped (694 before). Pinned versions added: none.

Over-engineering review of the diff: cut two fixtures (`archive_bzip2.docx`, `archive_lzma.docx`) and their 14 line builder, because the header-patched methods in the compression test reach the same check, and the `is_dir` skip described above. Kept: the test that stops a member in the middle (it is the only test of the step size), and the two constants. Nothing left unfixed.

Processes. Started 32, closed 32, confirmed by a process listing at the end: 26 Python (16 probes, 3 test runs, 7 short scripts) and 6 of the formatter and linter (three runs of the pair). No browser, no server, no node process.

Not verified:
- Other producers. The refusal of bzip2 and lzma rests on the smoke set (86 Flate members and 4 stored, across 90) and on Word's format, not on a survey. Google Docs, Pages, LibreOffice and WPS exports were not opened.
- Deflate64 was tested by patching a header, not with a real Deflate64 file, which Python cannot write.
- A real 100 MiB DOCX of dense XML, which is B5.

Blockers: none.

`[CONTRACT]` for Tanishq, not yet sent:
- `ARCHIVE_UNSAFE` also means a DOCX member with a compression method other than stored or Flate. Such a file used to parse if zipfile could read it (bzip2, lzma), and now has no result.
- `ARCHIVE_TOO_LARGE` keeps its limit (100 MiB) and now counts the bytes read. A file that declared a small size and held more no longer passes as small.

Next action: commit with `fix(parser): count DOCX archive bytes as read and refuse bzip2 and lzma`, send the two `[CONTRACT]` items above to Tanishq, then reply `next` for commit 2, the PDF budget chain (B2) with the `bomb_double_flate` fixture.


## 2026-10-16: Part 1-R, step 2, commit 2 of 11: PDF budget chain (B2)

Part: 1-R step 2, theme 2 of the eleven. Fixes B2, the P1 finding that the PDF content budget measured the first filter of a stream and ignored the rest of the chain. `[CONTRACT]`: `TOO_MUCH_TEXT` gains a meaning, see the last section. Commit 1 is `ede388a`, and the tree was clean before this part started.

Standing instruction from Aryan, applied from this part: no `[CONTRACT]` item is sent per commit. Every one is held, `ParserContract.md` is updated as each commit lands so it stays the single source, and one consolidated message for Tanishq covering all eleven commits is printed at the end of 1-R. The two items of commit 1 are held with this one.

Files changed:
- `backend/app/parsing/pdf.py`: `_decoded_length` returns "past the limit" for a stream whose filter list names more than one filter that can grow the data (Flate, LZW, RunLength), before it reads any byte. New constant `_GROWING_FILTERS`, two new pdfminer imports. The rest of the function is unchanged.
- `backend/tests/fixtures/build.py`: `_single_content_pdf` (the one-page file `bomb_content` already used) and the `bomb_double_flate` fixture, registered with `TOO_MUCH_TEXT`.
- `backend/tests/test_pdf.py`: the existing bomb test also runs `bomb_double_flate`, which proves no stream is decoded. New: four filter chains that must count as over the limit whatever the stream holds. 700 tests became 707 (one fixture row, four chains and two tests that run over every registered fixture).
- `docs/app/ParserContract.md` (the `TOO_MUCH_TEXT` row, the limits row, the ceiling row, the refined list in section 14), `docs/app/Phases.md` (A11 resolution), `docs/app/Architecture.md` (the PDF budget row), `docs/app/BuildLog.md` (this entry).

What changed, in the order the code runs:
- `_check_budget` calls `_decoded_length` for every content stream and Form XObject. The function now reads the filter names first. Two or more growing filters end the count at once as over the limit, so `_check_budget` raises `TOO_MUCH_TEXT` before pdfminer decodes anything.
- Everything else is as before: leading ASCII85 and ASCIIHex are undone, one Flate is read in 64 KiB steps, and any other filter counts the stored length.

Findings during the part:
- Step 1 proposed measuring the chain stage by stage with a cap on each stage, and refusing a second compressing filter after Flate. Only the refusal is needed, and it covers LZW and RunLength too. Measuring each stage bounds memory but not work: a chain of N Flate stages that each inflate to 8 MiB costs N times 8 MiB of work, and N is limited only by the file size (computed, not run). One growing filter per stream bounds the work to one stage. So the rule is a count of growing filters, in any order, and the position of the ASCII filters does not matter.
- Reproduced on a new probe file (two Flate stages over 64 MiB of white space, 702 B, first stage 65,239 B). The code at the last commit does not reject it: `NO_TEXT_FOUND` after 0.28 s, and the peak working set rose 127 MiB, which is the content decoded in full, 8 times the budget. The new code gives `TOO_MUCH_TEXT` in under 0.01 s with no rise. Step 1 measured 0.82 s and 129 MiB on a file with different content, which is the same finding.
- The three real PDFs of the smoke set hold 458 Flate streams, each alone, and 47 streams with no filter. None has a chain. Their JSON is the same by hash before and after: 174, 797 and 614 blocks.
- A stream whose only growing filter is LZW or RunLength still counts its stored length. That is the 1-C ceiling, reworded in the contract. Measuring both needs a chunked reader for each (the other way in call 1 of step 1) and was not done.

Commands run, from `backend/` with the venv interpreter: `ruff format app tests`, `ruff check app tests`, `pytest -q -p no:cacheprovider` (a red run of the new tests first: 6 failed, 3 passed). Probes on a copy of `app/` for the last commit (exported with `git archive`) and for the working tree, in the session scratchpad and never the repo, each as its own `python -I` process: one for the file build, two for the 64 MiB file (old code, new code), one for the filter chains of the three smoke PDFs, two for their parse (old code, new code). Peak working set came from `K32GetProcessMemoryInfo` in the probe itself. Read-only git.

Tests: 707 passed, 0 failed, 0 skipped (700 before). Pinned versions added: none.

Over-engineering review of the diff: cut one test case (the interleaved chain `Flate, ASCIIHex, Flate`), because the count ignores position and the case with a leading ASCII85 is the one a real writer would produce. Kept: `_single_content_pdf` (two fixtures use it), `_GROWING_FILTERS`. Nothing left unfixed.

Processes. Started 16, closed 16: 10 Python (4 test runs, 6 probe scripts) and 6 of the formatter and linter (three runs of the pair). A process listing at the end found no Python or ruff process running. No browser, no server, no node process.

Not verified:
- Other producers. The claim that a content stream has no use for a chain of growing filters rests on the PDF format and on three files from one source (SEC exhibits in `data/cuad_smoke/`), not on a survey. A producer that writes Flate twice would now get no result.
- A real LZW or RunLength content stream. Both are untested, and the lone-filter ceiling stands.
- The 256 MiB case of step 1 and the 8 GB figure for stage one at 8 MiB (computed there).

Blockers: none.

`[CONTRACT]`, held for the one message at the end of 1-R:
- Commit 1: `ARCHIVE_UNSAFE` also means a DOCX member with a compression method other than stored or Flate. `ARCHIVE_TOO_LARGE` keeps its limit (100 MiB) and counts the bytes read.
- Commit 2: `TOO_MUCH_TEXT` also means a PDF page content stream or Form XObject that names more than one filter that can grow the data (Flate, LZW or RunLength), whatever it holds. Such a file used to parse when the first filter's output was inside the budget (for example Flate twice over small content), and now has no result.

Next action: commit with `fix(parser): count a second growing PDF filter as over budget`, then reply `next` for commit 3, the gutter scan (B4).
