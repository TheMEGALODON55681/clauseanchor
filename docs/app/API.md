# API

The contract for the HTTP API. This file governs: the frontend adapter follows it, and plan section 9 copies it (`Phases.md`, D1). Each part adds its endpoints here. Part 2-A adds health, readiness and capabilities, and part 2-B adds sessions.

`[CONTRACT]` marks a shape Tanishq has to agree to.

---

## 1. Conventions

- **Base path.** Every route sits under `/api/v1`, `/api/v1/openapi.json` included. The interactive docs pages are off, because they load scripts from a CDN.
- **Format.** JSON in UTF-8.
- **Declared fields only.** Each response has a Pydantic model, and a field the model does not declare cannot leave the API.
- **No verdicts.** No response carries a safety score, a risk score, a verdict or a completeness figure (`Phases.md`, Review scope).
- **Scope notice.** `GET /api/v1/capabilities` carries it. Each analysis response will too (2-D).
- **Sessions.** Health, readiness and capabilities are public. Every other route takes the bearer token from `POST /api/v1/sessions` (section 7).
- **No caching.** Every response carries `Cache-Control: no-store`, errors included.

## 2. Error envelope

Every error response has this body, with the status code in the table below:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "No such resource.",
    "request_id": "0b0f6c1e-3a3e-4a52-9c3c-2f1d3a5f7a10",
    "retryable": false,
    "details": {}
  }
}
```

| Field | Type | Meaning |
|---|---|---|
| `code` | string | A fixed machine code from the table below |
| `message` | string | A fixed sentence for the code. It never holds request input, document text or exception text |
| `request_id` | string | A new UUID for each error response |
| `retryable` | boolean | Whether the same request can succeed later |
| `details` | object | Safe, fixed fields for the code. `{}` unless the table says otherwise |

| Code | Status | Retryable | When |
|---|---|---|---|
| `VALIDATION_ERROR` | 422 | no | A path, query or body value fails validation. FastAPI's own 422 body repeats the submitted input, so the envelope replaces it and names no field |
| `NOT_FOUND` | 404 | no | No route matches |
| `METHOD_NOT_ALLOWED` | 405 | no | The route exists but not for this method. The `Allow` header lists the methods that work |
| `INTERNAL_ERROR` | 500 | no | An unhandled exception. The body has no exception text, and the server logs only the exception class name |
| `NOT_READY` | 503 | yes | `GET /api/v1/ready` found a failed check. `details.checks` lists the results |
| `CATALOGUE_UNAVAILABLE` | 503 | no | `GET /api/v1/capabilities` has no usable catalogue |
| `SESSION_INVALID` | 401 | no | The bearer token is missing, malformed, unknown or expired. The reply carries `WWW-Authenticate: Bearer` and never repeats the token (section 7) |
| `SESSION_LIMIT` | 429 | yes | `POST /api/v1/sessions` found `MAX_SESSIONS` live sessions (section 8) |

Later parts add codes for uploads (413, 415), queues (429) and parse errors.

## 3. Endpoints

### `GET /api/v1/health`

Liveness only. It checks no dependency, so it answers 200 while the catalogue is missing.

```json
{ "status": "ok" }
```

### `GET /api/v1/ready`

Readiness of the analyzer setting, the catalogue, the session store and the database.

200 when every check passes:

```json
{ "ready": true, "checks": { "analyzer": "ok", "catalogue": "ok", "store": "ok", "database": "ok" } }
```

503 `NOT_READY` otherwise, with the same `checks` object under `details`:

```json
{ "error": { "code": "NOT_READY", "message": "The service is not ready.", "request_id": "0b0f6c1e-3a3e-4a52-9c3c-2f1d3a5f7a10", "retryable": true, "details": { "checks": { "analyzer": "ok", "catalogue": "missing", "store": "ok", "database": "ok" } } } }
```

| Check | Value | Meaning |
|---|---|---|
| `analyzer` | `ok` | The analyzer is `stub`, or it is `real` and `CLAUSEANCHOR_ARTIFACTS_DIR` names a directory that exists |
| | `artifacts_missing` | The analyzer is `real` and that directory does not exist. The API never falls back to the stub |
| `catalogue` | `ok` | The catalogue loaded at start |
| | `missing` | No readable catalogue file |
| | `invalid` | The file breaks the shape in section 5 |
| `store` | `ok` | The expiry sweep is running |
| | `sweep_stopped` | The sweep is not running. Expired sessions would stay in memory until a request found them |
| `database` | `ok` | SQLite answers a query |
| | `unavailable` | It does not |

The `analyzer` check looks at the directory and no more. Artifact manifest checks come with 4-A.

### `GET /api/v1/capabilities`

The review scope, the mode and the category catalogue. The field names follow the frontend mock, and 2-E may rename them.

```json
{
  "scope_notice": "This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment.",
  "mode": "sample",
  "catalogue_version": "example-1",
  "categories": [
    { "id": "example.category_a", "display_name": "Example A", "source": "cuad", "support_status": "example_status" }
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `scope_notice` | string | The fixed text of `Phases.md`, Review scope. It is one constant in `app/services/scope.py`, never generated |
| `mode` | `sample` or `real` | Comes from `CLAUSEANCHOR_ANALYZER`: `stub` gives `sample`, `real` gives `real` |
| `catalogue_version` | string | The catalogue file's `catalogue_version` |
| `categories` | array | Every catalogue row, in file order, with the four fields of section 5 |

A category can be listed without validated support. `support_status` says which case applies.

503 `CATALOGUE_UNAVAILABLE` when the catalogue is missing or invalid.

### `POST /api/v1/sessions`

Starts an anonymous session. Send no body. The API ignores one.

201:

```json
{ "token": "Qk3v0x...43 characters in all", "expires_at": "2026-10-18T11:00:00Z" }
```

| Field | Type | Meaning |
|---|---|---|
| `token` | string | The bearer token: 32 random bytes as 43 characters of URL-safe text. This reply is the only place the API shows it. The server keeps a SHA-256 hash of it and nothing else, so a lost token cannot be recovered. Start a new session |
| `expires_at` | string | ISO-8601 UTC, in whole seconds. It is the creation time plus `CLAUSEANCHOR_SESSION_TTL_MINUTES` and never moves. No request extends it, polling included |

At `expires_at` the session stops working, and the API deletes it with its documents and jobs from memory and from SQLite. A sweep every `SWEEP_INTERVAL_SECONDS` seconds finds the sessions that no request touches.

429 `SESSION_LIMIT` when `MAX_SESSIONS` sessions are alive. An expired session does not count.

### `DELETE /api/v1/sessions/current`

Ends the session named by the bearer token at once and deletes its documents and jobs from memory and from SQLite.

204 with no body. 401 `SESSION_INVALID` for a bad token. A second delete with the same token gets 401, because the session is gone.

## 4. Configuration

The API reads the process environment once, at start. It does not read a `.env` file. A bad value stops the start with a message that names the variable and never shows its value.

| Variable | Default | Meaning |
|---|---|---|
| `CLAUSEANCHOR_ANALYZER` | `stub` | `stub` or `real`. The stub serves sample mode, and `real` loads Tanishq's artifacts (4-A) |
| `CLAUSEANCHOR_ARTIFACTS_DIR` | none | The artifacts directory. Required when the analyzer is `real` and ignored otherwise |
| `CLAUSEANCHOR_DB_PATH` | `:memory:` | The SQLite path. The default writes nothing to disk. A file path works too, and its three tables are emptied at every start (D4). An upload's file name never reaches SQLite. A path the API cannot open stops the start |
| `CLAUSEANCHOR_SESSION_TTL_MINUTES` | `60` | Session lifetime. A whole number from 1 to 60, because the promise to users is deletion within 60 minutes |
| `CLAUSEANCHOR_PARSE_KILL_SECONDS` | `120` | Wall-clock limit for one parse. Provisional: 2-C times the dense cases and fixes it |
| `CLAUSEANCHOR_PARSE_QUEUE_LENGTH` | `2` | How many parses can wait (plan 9.3) |

The three numbers must be whole numbers of at least 1. The parser's own limits (file size, page count, text length) are not settings. They stay in the parser. The limits in section 8 are constants and not settings.

## 5. Catalogue `[CONTRACT]`

Tanishq owns the categories: 41 CUAD categories plus 5 India extensions, 46 in all. The API loads them from one JSON file, `backend/app/catalogue.json`, through `load_catalogue` in `app/services/scope.py`. The API reads the file once, at start, so a new file needs a restart.

```json
{
  "catalogue_version": "example-1",
  "categories": [
    { "id": "example.category_a", "display_name": "Example A", "source": "cuad", "support_status": "example_status" },
    { "id": "example.category_b", "display_name": "Example B", "source": "india_extension", "support_status": "example_status" }
  ]
}
```

The ids above are placeholders. The API invents no id.

| Field | Rule |
|---|---|
| `catalogue_version` | Non-empty text |
| `categories` | A non-empty array. Ids are unique |
| `id` | Non-empty text. The stable id of the category. The API passes it through unchanged |
| `display_name` | Non-empty text |
| `source` | `cuad` or `india_extension` |
| `support_status` | Non-empty text. Tanishq fixes the vocabulary and the API passes it through |

Each row has exactly these four fields, and the top level has exactly the two keys above. An extra or missing key makes the file `invalid`.

The API reports two failure states and never guesses. With no file, `/ready` says `catalogue: missing` and `/capabilities` answers 503. With a broken file, `/ready` says `catalogue: invalid` and `/capabilities` answers 503. No real catalogue is committed yet. The change that adds it also adds a test for the count of 41 and 5.

## 6. Differences from plan section 9

This file governs, and the plan will copy it.

- Health and readiness sit at `/api/v1/health` and `/api/v1/ready`. The plan has `/healthz` and `/readyz` outside the base path. The readiness body is `{ready, checks}`, where the plan has `{ready, mode, artifact_manifest_sha256}`.
- `Capabilities` has `scope_notice`, `mode`, `catalogue_version` and `categories`. The plan's also lists `contract_version`, upload limits, `upload_enabled` and `artifact_ready`. The parts that own those values add them.
- A category has four fields. The plan's `CategorySpec` adds `description`.
- The error envelope keeps the five fields of plan 9.1's `Error`. `details` is `{}` except on `NOT_READY`.
- `POST /api/v1/sessions` returns `token` and `expires_at`. The plan's `Session` adds `session_id`, which the frontend has no use for, so the API does not show it.
- The plan says "401 invalid capability" and 410 for an expired document or job. Here every bad token is one 401, `SESSION_INVALID` (section 7). A document lives and dies with its session (D5), so after expiry a request fails the bearer check before it reaches a document route, and 410 does not occur.
- Readiness adds `store` and `database` to the checks.

## 7. Bearer token

A route that needs a session reads `Authorization: Bearer <token>`. The scheme name is not case sensitive. The API hashes the token with SHA-256 and looks up the hash, so the stored value is not a credential.

Every bad token gets the same reply: 401, `SESSION_INVALID` and `WWW-Authenticate: Bearer`. That covers a missing header, another scheme, an empty token, a token that was never issued and a token whose session expired or ended. The reply never repeats the token. Routes use one dependency for the check, `require_session` in `app/api/auth.py`.

One code covers unknown and expired, for two reasons. The frontend mock raises one `expired` error for any token it does not know. The Reader sends that error and `not_found` to the same Expired page, which takes its wording from the address (`?reason=`). And the server cannot tell the two apart: it deletes an expired session the first time it sees it, and from then on the token looks unknown.

## 8. Limits

These three are constants in `app/config.py`, not settings. Plan 9.2 names a 429 for the session limit and gives no number, and neither plan section gives a document limit, so the values are proposals for Aryan to confirm.

| Constant | Value | Meaning |
|---|---|---|
| `MAX_SESSIONS` | 25 | Live sessions at once. Past it, `POST /api/v1/sessions` answers 429 `SESSION_LIMIT`. Expired sessions do not count |
| `MAX_DOCUMENTS_PER_SESSION` | 5 | Documents one session can hold. The store enforces it. The upload route (2-C) answers 429, the plan's status for its limits, and picks the code |
| `SWEEP_INTERVAL_SECONDS` | 30 | How often the sweep runs. Every lookup checks the time, so an expired session is unreachable at once. The sweep sets how long its data stays in memory after that |
