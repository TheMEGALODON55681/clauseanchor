## Backend

The backend reads a PDF or DOCX contract and builds one canonical text with exact character offsets. Its code lives in `backend/`. Today it holds the PDF and DOCX parsers, the clause structure builder and a command-line tool. There is no server yet. The output format is in `docs/app/ParserContract.md`.

### Prerequisites

- Python 3.12. The project does not support 3.13 yet.
- Git Bash on Windows, or a POSIX shell on macOS or Linux.

### Install

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements-dev.txt
```

On macOS or Linux, activate with `source .venv/bin/activate`. `requirements.txt` pins the runtime packages, and `requirements-dev.txt` adds the pinned test and lint tools.

### Run

There is no server yet. To parse a file and print the result as JSON, from `backend/` with the virtual environment active:

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
