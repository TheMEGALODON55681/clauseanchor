# README claims

Every number and checkable claim in `README.md`, with the file or the run it comes from. Written for 4-B.5 on 25 November 2026. The README keeps no figure that is not in this file.

How each row was checked. **Copied**: the figure is the same string in the source file, matched by a script. **Read**: the value was read from the file or its code. **Counted**: counted with a command, given below. **Run**: measured in a run of this part, given in the second half.


## Evaluation

| Claim | Source | Checked |
|---|---|---|
| Full test: 102 contracts, 99 families, 2,643 gold spans; 8,174 candidates; precision 21.984%, recall 67.991%, exact-match recall 56.300%, micro F1 33.225%, macro F1 35.226% | `docs/ml/CUAD_FinalEvaluation.md` | Copied |
| Known-overlap slice: 93 contracts, 2,441 gold spans, 7,641 candidates; 21.712%, 67.964%, 55.961%, 32.910%, 34.962% | `docs/ml/CUAD_FinalEvaluation.md` | Copied |
| 95% intervals: precision 19.618% to 24.766%, recall 65.581% to 70.329%, exact-match recall 53.750% to 58.877%, from a 2,000-replicate bootstrap | `docs/ml/CUAD_FinalEvaluation.md` | Copied |
| 6,377 false candidates; 62.52 a contract, 198.25 at the 95th percentile, 597 at worst | `docs/ml/CUAD_FinalEvaluation.md` | Copied |
| 1,176 of 4,182 questions processing-incomplete (1,122 cut to 64 tokens, 68 boundary flags, 14 both); 2,242 with no candidate, 36 of them with a gold span; 16 of 41 categories with sparse support | `docs/ml/CUAD_FinalEvaluation.md` | Copied |
| Official path: AUPR 43.635% and 42.586%, P@80R 0.000% and 31.131%, a difference of 1.049 points | `docs/ml/CUAD_FinalEvaluation.md` | Copied |
| Out-of-fold Brier 0.103406 and ECE 0.040156 | `docs/ml/ReleaseHandoff.md` | Copied |

## Limits

| Claim | Source | Checked |
|---|---|---|
| Session 60 minutes; parse kill 120 s; parse queue 2; parse memory cap 1,536 MiB | `backend/app/config.py` | Read |
| 25 sessions, 5 documents each, 4 uploads in flight, 2 analyses waiting, an analysis limit of 1,800 s (30 minutes) | `backend/app/config.py` | Read |
| 10 MiB upload, 100 PDF pages, 500,000 characters; the upload checks run in the order token, size, empty body, type | `docs/app/API.md` | Read |
| Memory cap default 1536 MiB in the settings table | `docs/app/API.md` | Read |

## Hosting

| Claim | Source | Checked |
|---|---|---|
| Central India, 2 vCPU, 4 GiB, 0 to 1 replicas | `deploy/azure-containerapp.yaml` | Read |
| One uvicorn worker, Python 3.12, PyTorch 2.9.1 from the CPU index | `Dockerfile` | Read |
| Image 1672 MiB, peak memory 1025 MiB of 4096 with the file cache included | docs/app/Phases.md (4-B.3) | Copied |
| A first visit after idle takes 1 to 3 minutes (reported, not measured) | `docs/app/Deploy.md` | Copied |

## CI

| Claim | Source | Checked |
|---|---|---|
| The image workflow starts by hand or on a v* tag, checks the model SHA-256, builds, starts a 4 GiB and 2 CPU container, runs the smoke test and publishes only after every step passed. It is the only workflow file | `.github/workflows/image.yml` | Read |

## Versions

| Claim | Source | Checked |
|---|---|---|
| FastAPI 0.143.3, uvicorn 0.54.0, Pydantic 2.14.1, pdfplumber 0.11.10, pdfminer.six 20260107, python-docx 1.2.0, lxml 6.1.3 | `backend/constraints.txt` | Read |
| pytest 9.1.1, httpx 0.28.1, ruff 0.16.10 | `backend/constraints.txt` | Read |
| PyTorch 2.9.1, Transformers 4.57.6 | `ml/requirements-inference.txt` | Read |
| React 19.2.4, TypeScript 5.9.3, Vite 8.0.5, Tailwind CSS 4.2.2, react-router 8.4.0 | `frontend/pnpm-lock.yaml` | Read |
| Node 22.18 or later | `frontend/package.json` | Read |

## Tests

| Claim | Source | Checked |
|---|---|---|
| Backend 1788 passed and 27 skipped, frontend 179 passed, run on 25 November 2026 before any change in this part | `the two baseline runs of this part` | Run |
| 1-R: backend 769 and frontend 68 | docs/app/BuildLog.md (1-R) | Copied |
| 4-B.4: frontend 170 to 179, backend 1,788 passed and 27 skipped | docs/app/Phases.md (4-B.4) | Copied |
| 4-B.3: frontend 136 to 170, backend 1,787 to 1,788. 4-B.2: backend 1785 to 1787, frontend 135 to 136 | docs/app/Phases.md (4-B.3, 4-B.2) | Copied |

## Accessibility

| Claim | Source | Checked |
|---|---|---|
| axe: 154 captures with no violation in the frontend review | `docs/app/BuildLog.md` | Copied |
| axe: 110 runs with no violation, and some results that need review, recorded in 17.9 | `docs/app/FrontendDesign.md` | Copied |

## Partial result

| Claim | Source | Checked |
|---|---|---|
| The toolbar line and the scope band count categories checked in part, categories not checked and pages not read, and View list names each | `frontend/src/lib/reader.ts` | Read |
| A question longer than 64 tokens is cut, the API follows the core's wording, and the fix belongs to the core | docs/app/Phases.md (4-B.4) | Read |

## Decisions

| Claim | Source | Checked |
|---|---|---|
| A raw request body, because a multipart parser writes a temporary file once a part passes 1 MiB | `docs/app/API.md` | Read |

## Roadmap

| Claim | Source | Checked |
|---|---|---|
| 4-B, 4-B.1 to 4-B.4 and 4-C1 are ticked. 3-A, 4-A, 4-C and 4-R are open | `docs/app/Phases.md` | Read |

## Carried

| Claim | Source | Checked |
|---|---|---|
| The model bundle is about 486 MiB (509,869,238 bytes) | `docs/ml/ReleaseHandoff.md` | Copied |
| Contract text at 68 to 80 characters a line, text never under 12 px, hit areas at least 44 px | `docs/app/DesignSystem.md` | Read |
| A 16 KB file can decode to 16 MB (the reason for the parse child) | `docs/app/Architecture.md` | Read |
| The one-origin decision is R17 in 4-C1 and Architecture section 8.1 | docs/app/Phases.md, docs/app/Architecture.md | Read |

## Counted

| Claim | How it was counted |
|---|---|
| 46 categories, 41 from CUAD and 5 India extensions | `ml/configs/catalogue.json` holds 46 entries, 41 with an id that starts `cuad.` and 5 with `in.` |
| Twelve font files | `git ls-files frontend/public/fonts` lists 12 `.woff2` files (and 3 license texts) |
| 17,298 lines of Python in 84 source files, 19,356 in 66 test files | Physical lines, blank lines included, of the git-tracked `.py` files. A test file is one under `backend/tests/` or `ml/tests/`. Everything else is source |
| 9,668 lines of TypeScript in 88 source files, 1,810 in 17 test files | The same count over git-tracked `.ts` and `.tsx` files. A test file is one that ends `.test.ts` or `.test.tsx` |
| Frontend counts for 4-C1 (133) and 4-B (135) | `docs/app/Phases.md`, the 4-C1 and 4-B entries |

## Run in 4-B.5

| Claim | Value | Where it was measured |
|---|---|---|
| Review on the live app, 25 November 2026 | 24 categories, finished after 47 s, status partial | `capture.mjs --session`, log of the run |
| Toolbar line | Partial result. 6 categories were checked in part. View list has the details. | the Reader, read from the page and in `reader-*.png` |
| View list | Exclusivity, No-Solicit of Employees, Change of Control, Cap on Liability, Uncapped Liability, Post-Termination Services, each Checked in part | the Reader, read from the page and in `partial-*.png` |
| Selected passages | Non-Compete, characters 3124 to 3336 (passage 1 of 2). Governing Law, characters 5804 to 5852 | the Reader; the same offsets as the 24 November shots |
| Deletes | The document and the session both answered 204. Console errors: 0 | the run log |
| Demo frames | 78 frames in 11 scenes. The progress run is 58 captures over 46 s, about one every 800 ms, played at 14 frames a second, so about 11 times faster | the run log and `encode_gif.py` |
| `demo.gif` | 1200 by 804, 6,873,654 bytes, 29.2 s, 128 colours, 6 blend frames between scenes, loops to its first frame | the encoder's report |
| `gauntlet.gif` | 1200 by 720, 1,054,146 bytes, 19.2 s at 14 frames a second, 255 colours | the encoder's report |
| `docs/assets/readme/` | 21 files, 14,970,625 bytes, none over 7 MB | `stat` over the folder |

The upload refusals, from `curl` against `POST /api/v1/documents` on 25 November 2026 (22 calls, all documents and the session deleted with 204):

| File | Bytes | Reply |
|---|---:|---|
| `empty.bin` | 0 | 400 `EMPTY_FILE`, "The file is empty." |
| `photo.pdf` (PNG data, sent as `application/pdf`) | 72 | 415 `UNSUPPORTED_TYPE`, "The file is not a PDF or a DOCX." |
| `oversize.pdf` (a PDF header, then zeros) | 10,485,761 | 413 `FILE_TOO_LARGE`, "The file is larger than 10 MiB." |
| `encrypted.pdf` | 2,852 | 202, then the job failed `ENCRYPTED_PDF`, "The PDF needs a password to open." |
| `scanned.pdf` | 2,301 | 202, then the job failed `SCANNED_PDF`, "The PDF is scanned, so it holds no text to read." |
| `tracked_insert.docx` | 1,130 | 202, then the job failed `TRACKED_CHANGES_PRESENT`, "The document has tracked changes. Accept all changes and upload it again." |
| `demo-services-agreement.docx` | 4,768 | 202, then the job succeeded |

The raw replies and the scripts sit in `.handoff/readme_demo/`, which git ignores.

## Not claimed

The README names no weak category, because the per-category breakdown is outside git. It states no time-saving figure and no latency figure, because none was measured. The cold start is a reported range, and the README says so.
