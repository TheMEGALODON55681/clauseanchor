## Backend

The backend reads a PDF or DOCX contract and builds one canonical text with exact character offsets. Its code lives in `backend/`. Today it holds the PDF and DOCX parsers, the clause structure builder, a command-line tool and the start of the API: health, readiness and capabilities. The parser output format is in `docs/app/ParserContract.md`, and the API contract is in `docs/app/API.md`.

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

### Run the API

From `backend/` with the virtual environment active:

```bash
uvicorn app.main:create_app --factory
```

The API listens on `http://127.0.0.1:8000`, and `GET /api/v1/health` should answer `{"status":"ok"}`. `GET /api/v1/ready` and `GET /api/v1/capabilities` answer 503 until `backend/app/catalogue.json` exists. The category catalogue comes from Tanishq and is not committed yet. API.md section 5 gives its shape.

The API reads these environment variables once, at start, and does not read a `.env` file. Every one is optional.

| Variable | Default | Meaning |
|---|---|---|
| `CLAUSEANCHOR_ANALYZER` | `stub` | `stub` serves sample mode. `real` loads the trained analyzer |
| `CLAUSEANCHOR_ARTIFACTS_DIR` | none | The analyzer's artifacts directory. Required when the analyzer is `real` |
| `CLAUSEANCHOR_DB_PATH` | `:memory:` | The SQLite path. The default keeps session data off disk |
| `CLAUSEANCHOR_SESSION_TTL_MINUTES` | `60` | Session lifetime, from 1 to 60 |
| `CLAUSEANCHOR_PARSE_KILL_SECONDS` | `120` | Wall-clock limit for one parse. Provisional |
| `CLAUSEANCHOR_PARSE_QUEUE_LENGTH` | `2` | How many parses can wait |

A bad value stops the start and the message names the variable. `docs/app/API.md` section 4 has the details.

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
