## Backend

The backend reads a PDF or DOCX contract and builds one canonical text with exact character offsets. Its code lives in `backend/`. Today it holds the PDF and DOCX parsers, the clause structure builder, a command-line tool and the API: health, readiness, capabilities, sessions, uploads, parse jobs and analyses. The parser output format is in `docs/app/ParserContract.md`, and the API contract is in `docs/app/API.md`.

### Prerequisites

- Python 3.12. The project does not support 3.13 yet.
- Git Bash on Windows, or a POSIX shell on macOS or Linux.

### Install

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements-dev.txt -c constraints.txt
```

On macOS or Linux, activate with `source .venv/bin/activate`. `requirements.txt` pins the runtime packages, and `requirements-dev.txt` adds the pinned test and lint tools. `constraints.txt` pins everything those two pull in. For a runtime-only install, use `requirements.txt` in place of `requirements-dev.txt`.

`requirements.txt` also installs Tanishq's analysis core from `../ml` in editable mode, so run `pip` from `backend/`. The core needs no other package. It pulls in no torch, transformers or numpy, and neither does the API in its default mode.

### Run the API

From `backend/` with the virtual environment active:

```bash
uvicorn app.main:create_app --factory
```

The API listens on `http://127.0.0.1:8000`, and `GET /api/v1/health` should answer `{"status":"ok"}`. `GET /api/v1/capabilities` lists the 46 categories from `ml/configs/catalogue.json`, which Tanishq maintains and the API reads in place at start. If that file is missing or broken, `GET /api/v1/ready` names the problem and `GET /api/v1/capabilities` answers 503. API.md section 5 gives the file's shape.

`POST /api/v1/sessions` starts a session and returns a bearer token once. A session lasts 60 minutes, or less if `CLAUSEANCHOR_SESSION_TTL_MINUTES` says so, and `DELETE /api/v1/sessions/current` ends it sooner. Sessions and the documents they hold live in memory only, so stopping the API deletes them all. `GET /api/v1/ready` also checks the session store and the database.

`POST /api/v1/documents` takes one PDF or DOCX of up to 10 MiB as the raw request body, not as multipart. It answers 202 with a document id and a parse job id. The file name travels in `Content-Disposition` as `filename*`.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents -H "Authorization: Bearer $TOKEN" -H "Content-Disposition: attachment; filename*=UTF-8''contract.pdf" --data-binary @contract.pdf
```

Poll `GET /api/v1/jobs/{job_id}` until the job has succeeded or failed. Then `GET /api/v1/documents/{document_id}` returns the parsed text, and `DELETE /api/v1/documents/{document_id}` removes the document at once. The API parses each file in a child process with a time limit and a memory cap, so a bad file cannot take the server down. The file and its text stay in memory and are never written to disk. `docs/app/API.md` has the request and reply shapes, and section 9 describes the child process.

Once a document has parsed, `POST /api/v1/documents/{document_id}/analyses` queues an analysis. The body names the categories and the jurisdiction scope, and the reply is 202 with an analysis id and a job id.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents/$DOCUMENT_ID/analyses -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"category_ids": ["cuad.governing_law"], "jurisdiction_scope": "unspecified"}'
```

Poll the job, which now reports progress. Then `GET /api/v1/analyses/{analysis_id}` returns the result, and `POST /api/v1/jobs/{job_id}/cancel` stops an analysis that is waiting or running. The result carries the scope notice, and it holds no verdict and no risk score. `processing_complete` says whether the run left anything out, and `decision_coverage` says how many categories reached a decision. API.md section 10 defines both.

The default analyzer is the stub, which serves sample mode. It reads only the core's own sample contract, so it answers 409 for an uploaded file, and the route that opens the sample document comes with part 3-C. Real mode runs Tanishq's candidate-only analyzer on CPU, and the section "Real mode" below walks through it.

The API reads these environment variables once, at start, and does not read a `.env` file. Every one is optional.

| Variable | Default | Meaning |
|---|---|---|
| `CLAUSEANCHOR_ANALYZER` | `stub` | `stub` serves sample mode. `real` loads the candidate-only analyzer |
| `CLAUSEANCHOR_ARTIFACTS_DIR` | none | The analyzer's artifacts directory. Required when the analyzer is `real` |
| `CLAUSEANCHOR_ARTIFACTS_SHA256` | none | The digest of the artifact manifest, 64 lowercase hexadecimal digits. Required when the analyzer is `real` |
| `CLAUSEANCHOR_DB_PATH` | `:memory:` | The SQLite path for session metadata. The default writes nothing to disk. A file path is emptied at every start |
| `CLAUSEANCHOR_SESSION_TTL_MINUTES` | `60` | Session lifetime, from 1 to 60 |
| `CLAUSEANCHOR_PARSE_KILL_SECONDS` | `120` | Wall-clock limit for one parse |
| `CLAUSEANCHOR_PARSE_QUEUE_LENGTH` | `2` | How many parses can wait while one runs |
| `CLAUSEANCHOR_PARSE_MEMORY_MIB` | `1536` | Memory cap for the process that parses one file, in MiB |

A bad value stops the start and the message names the variable. `docs/app/API.md` section 4 has the details.

### Real mode

Real mode runs the candidate-only analyzer with Tanishq's v0 bundle. It has run behind the API on this laptop (`docs/app/Phases.md`, 2-D.1). Every finding is a `review_candidate` with a null confidence, all 46 categories stay `not_validated`, and the five India categories come back `unavailable`.

1. **Check the bundle.** Take `clauseanchor-candidate-prototype-v0.zip` from Tanishq, compare its size and SHA-256 with `docs/ml/ReleaseHandoff.md` section 2, and extract it into a new folder outside the repository. Nothing from it belongs in Git.
2. **Make an environment for it.** Use Python 3.12 and a virtual environment of its own, apart from `backend/.venv`, because torch is large and the tests do not need it. Install in this order, with `backend/` as the working directory:

   ```bash
   pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
   pip install -r ../ml/requirements-inference.txt
   pip install -r requirements.txt -c constraints.txt
   ```

   The last command installs the runtime packages and `../ml` as an editable install. The inference pins and `constraints.txt` do not conflict, and `pip check` is clean.
3. **Run the receiver check.** Use the command in `docs/ml/ReleaseHandoff.md` section 3, from inside the extraction, with its output outside it. It checks every file in the bundle and runs the trained model on authored text. It took about a minute here.
4. **Set the variables and start the API** from `backend/`:

   ```bash
   export CLAUSEANCHOR_ANALYZER=real
   export CLAUSEANCHOR_ARTIFACTS_DIR=/path/to/extraction/models/clauseanchor_candidate_v0
   export CLAUSEANCHOR_ARTIFACTS_SHA256=<the inference digest in ReleaseHandoff.md section 2>
   uvicorn app.main:create_app --factory
   ```

   Use the inference manifest's digest, which differs from the ZIP's. `GET /api/v1/ready` reports the analyzer as `loading`, then `ok`. If the bundle does not match the digest, it reports `failed`, and the API does not fall back to the stub.

The run on this laptop (torch's default 8 threads, 15.7 GiB of RAM) used `TestClient`, so real mode has not run under `uvicorn` yet. The API reached `ok` after 42.6 s on the first run and 6.2 s on the second. The process peaked at 1,281 MiB while loading and settled near 950 MiB. A 33-page contract with all 41 CUAD categories plans 2,185 windows of 0.37 to 0.51 s each, so it would take 804 to 1,123 s, inside the 30-minute analysis limit.

### Parse a file

To parse a file and print the result as JSON, from `backend/` with the virtual environment active:

```bash
python -m app.scripts.parse_file CONTRACT.pdf
```

The JSON leaves out the contract text unless you add `--text`. Add `--summary` for a count of blocks, nodes and warnings instead. A file the parser rejects prints its error code and exits with status 2.

### Test

From `backend/`, with the virtual environment active:

```bash
ruff format --check .
ruff check .
pytest
```

## Frontend

The frontend is a React app that shows a contract, marks findings in the margin and quotes the passages behind them. Its code lives in `frontend/`. It runs on mock data until the backend API is connected.

### Prerequisites

- Node 22.18 or later. The tests use the type stripping that ships on by default from that version.
- pnpm 10 or later. If it is missing, run `npm install -g pnpm@10`.

### Install

From the repository root:

```bash
cd frontend
pnpm install --frozen-lockfile
```

### Develop

```bash
pnpm dev
```

Open http://localhost:5173. In development the app adds a Preview controls drawer (the mock adapter's switches and a component gallery at `#/gallery`). A production build contains neither.

### Build and check

```bash
pnpm typecheck
pnpm test
pnpm build
```

`pnpm test` runs the unit tests with Node's built-in runner. `pnpm build` writes the production files to `frontend/dist/`.

### Routes

The app uses hash routes, so it runs on any static host: `#/` (landing), `#/start` (a three-step flow: upload the contract, choose your role and party, confirm the scope and start the review), `#/review/:documentId`, `#/how-it-works`, `#/accuracy`, `#/expired`. Any other address shows a page-not-found screen. Fonts are served from `frontend/public/fonts/`, so no page requests a third-party host.
