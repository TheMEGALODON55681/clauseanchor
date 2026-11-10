# ClauseAnchor: notes for Claude

Reviews Indian contracts (PDF/DOCX) against a fixed catalogue of 46 clause categories and marks review candidates in the text. It never writes legal text and never gives a score, verdict or "safe" claim.

## Map
- `backend/` FastAPI API, Python 3.12 only. `app/parsing/` turns a file into one canonical `source_text` with code-point offsets; `app/services/` holds the RAM store, the parse queue (one capped child process per parse) and the analysis queue; `app/api/` routes, auth, errors.
- `ml/clauseanchor_core/` Tanishq's analysis core: `StubAnalyzer` (sample mode) and `CandidateOnlyAnalyzer` (real model, loads torch in its constructor). `ml/scripts/` is CUAD training and evaluation, not used by the API.
- `frontend/` React 19 + Vite 8 + Tailwind 4 + react-router 8, hash router, talks to `/api/v1` on the same origin.
- `docs/app/` is the source of truth: `Architecture.md`, `API.md`, `ParserContract.md`, `Rules.md`, `Phases.md`, `BuildLog.md`. `graphify-out/GRAPH_REPORT.md` is a repo map; read it before sweeping many files.

## Commands
- Backend: `cd backend && pip install -r requirements-dev.txt -c constraints.txt`, then `ruff check . && ruff format --check . && python -m pytest -q`
- Frontend: `cd frontend && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test && pnpm build && pnpm check:dist`
- Run locally: `cd backend && uvicorn app.main:create_app --factory` and `cd frontend && pnpm dev` (proxies `/api` to 127.0.0.1:8000)
- ML tests need local assets that are not in git (the clean backbone and the external CUAD baseline); without them about 70 tests error.

## Rules that tests enforce
- No contract text, file name or exception text in any log or error body (Rules.md section 5). Error messages are fixed per code.
- Nothing user-provided touches disk; documents live in RAM for at most 60 minutes.
- Docs are tested: a new error code, env variable, limit or route must be added to `docs/app/API.md`, and `docs/app/openapi.json` regenerated with `python -m app.scripts.export_openapi`.
- No field named for a score, verdict, percentage, risk or safety in the API.
- Offsets are Unicode code points, end exclusive; the frontend converts with `lib/offsets.ts`.

## Do not
- Test against the deployed Azure app: it runs on a limited free grant. Use stub mode locally or the fake core in tests.
- Commit model weights; they come from the `model-v0` release asset.
