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
