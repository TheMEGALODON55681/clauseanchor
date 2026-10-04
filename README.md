## Backend

The backend reads a PDF or DOCX contract and builds one canonical text with exact character offsets. Its code lives in `backend/`. Today it holds the parsed-document model and the text assembler. The PDF and DOCX readers land next.

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

The backend has no server or command-line tool yet. To check your install, import the package:

```bash
python -c "import app.parsing.assemble"
```

A silent exit means the install works.

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

The app uses hash routes, so it runs on any static host: `#/` (landing and upload), `#/review/:documentId`, `#/how-it-works`, `#/accuracy`, `#/expired`. Any other address shows a page-not-found screen. Fonts are served from `frontend/public/fonts/`, so no page requests a third-party host.
