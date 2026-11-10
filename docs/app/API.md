# API

The contract for the HTTP API. This file governs: the frontend adapter follows it, and plan section 9 copies it (`Phases.md`, D1). Each part adds its endpoints here. Part 2-A adds health, readiness and capabilities, part 2-B adds sessions, part 2-C adds documents and parse jobs, and part 2-D adds analyses and cancel. Part 2-E fixes the final names, defines the document fields and the party binding shape, and exports the OpenAPI schema (sections 11 to 14).

`[CONTRACT]` marks a shape Tanishq has to agree to.

---

## 1. Conventions

- **Base path.** Every route sits under `/api/v1`, `/api/v1/openapi.json` included. The interactive docs pages are off, because they load scripts from a CDN.
- **Format.** JSON in UTF-8.
- **Declared fields only.** Each response has a Pydantic model, and a field the model does not declare cannot leave the API.
- **No verdicts.** No response carries a safety score, a risk score, a verdict or a completeness figure (`Phases.md`, Review scope).
- **Scope notice.** `GET /api/v1/capabilities` and every analysis response carry it.
- **Sessions.** Health, readiness and capabilities are public. Every other route takes the bearer token from `POST /api/v1/sessions` (section 7).
- **No caching.** Every response carries `Cache-Control: no-store`, errors included. The one exception is the frontend's hashed build files under `/assets/`, when the API serves the frontend (section 4): they carry `public, max-age=31536000, immutable`, because their names change with their content. `index.html` keeps `no-store`.
- **OpenAPI.** The app serves its OpenAPI document at `/api/v1/openapi.json`, and `docs/app/openapi.json` is the committed copy (section 14).

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
| `request_id` | string | A new UUID for each request. Every reply, error or not, carries the same value in its `X-Request-ID` header, and the log line of a crash names it as `request_id=`, so a reported id finds its line in the log (R27). It holds nothing from the request |
| `retryable` | boolean | Whether the same request can succeed later |
| `details` | object | Safe, fixed fields for the code. `{}` unless the table says otherwise |

| Code | Status | Retryable | When |
|---|---|---|---|
| `VALIDATION_ERROR` | 422 | no | A path, query or body value fails validation. For an analysis request that includes a body over 64 KiB, a list over 100 ids, an id over 64 characters, an unknown or repeated category id, and in sample mode an id the sample does not hold. FastAPI's own 422 body repeats the submitted input, so the envelope replaces it and names no field |
| `NOT_FOUND` | 404 | no | No route matches, or the id is unknown or belongs to another session |
| `METHOD_NOT_ALLOWED` | 405 | no | The route exists but not for this method. The `Allow` header lists the methods that work |
| `INTERNAL_ERROR` | 500 | no | An unhandled exception. The body has no exception text, and the server logs only the exception class name |
| `NOT_READY` | 503 | yes | `GET /api/v1/ready` found a failed check, and `details.checks` lists the results. An analysis start gets it too while the analyzer is `loading` or `failed`, with `details.checks.analyzer` alone |
| `CATALOGUE_UNAVAILABLE` | 503 | no | `GET /api/v1/capabilities` or an analysis start finds no usable catalogue |
| `SESSION_INVALID` | 401 | no | The bearer token is missing, malformed, unknown or expired. The reply carries `WWW-Authenticate: Bearer` and never repeats the token (section 7) |
| `SESSION_LIMIT` | 429 | yes | `POST /api/v1/sessions` found `MAX_SESSIONS` live sessions (section 8) |
| `FILE_TOO_LARGE` | 413 | no | The upload is over 10 MiB, by its `Content-Length` header or by the bytes that arrive |
| `EMPTY_FILE` | 400 | no | The upload has no bytes |
| `UNSUPPORTED_TYPE` | 415 | no | The bytes are not a PDF and not a DOCX. The check reads the bytes and ignores the `Content-Type` header |
| `DOCUMENT_LIMIT` | 429 | no | The session already holds `MAX_DOCUMENTS_PER_SESSION` documents (section 8). Delete one, then upload again |
| `QUEUE_FULL` | 429 | yes | `CLAUSEANCHOR_PARSE_QUEUE_LENGTH` parses are already waiting (section 9), or `MAX_UPLOADS_IN_FLIGHT` uploads are already arriving (section 8) |
| `DOCUMENT_NOT_PARSED` | 409 | no | An analysis was started on a document whose parse is still running or failed. Read the parse job first |
| `SAMPLE_MODE_ONLY` | 409 | no | The analyzer is the stub, and the document is not the prepared sample (section 10) |
| `ANALYSIS_IN_PROGRESS` | 409 | yes | The session already has an analysis waiting or running (section 10) |
| `JOB_NOT_CANCELLABLE` | 409 | no | The job is a parse, or an analysis that has ended |
| `ANALYSIS_QUEUE_FULL` | 429 | yes | `ANALYSIS_QUEUE_LENGTH` analyses are already waiting (section 8) |

A file the parser cannot read is not an HTTP error. The upload succeeds, and the parse job fails with a code of its own (the job errors table under `GET /api/v1/jobs/{job_id}`). An analysis that fails does the same, with one of the two analysis codes in that table.

## 3. Endpoints

### `GET /api/v1/health`

Liveness only. It checks no dependency, so it answers 200 while the catalogue is missing.

```json
{ "status": "ok" }
```

### `GET /api/v1/ready`

Readiness of the analyzer, the catalogue, the session store and the database.

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
| `analyzer` | `ok` | The analyzer loaded |
| | `loading` | The analyzer is still loading. The real model took 43 s on its first run and 6 s on the second (2-D.1), and the stub takes a few milliseconds. The app answers every other route meanwhile |
| | `failed` | The load raised, for example a missing directory or a manifest that does not match `CLAUSEANCHOR_ARTIFACTS_SHA256`. The API never falls back to the stub, and the log holds the exception class and nothing else |
| `catalogue` | `ok` | The catalogue loaded at start |
| | `missing` | No readable catalogue file |
| | `invalid` | The file breaks the shape in section 5 |
| `store` | `ok` | The expiry sweep is running |
| | `sweep_stopped` | The sweep is not running. Expired sessions would stay in memory until a request found them |
| `database` | `ok` | SQLite answers a query |
| | `unavailable` | It does not |

The core checks the artifact manifest and every file hash while it loads (`CandidateOnlyAnalyzer`), so `ok` means the bundle matched the digest. It says nothing about quality. A failed load does not retry, and a fixed bundle needs a restart.

### `GET /api/v1/capabilities`

The review scope, the mode and the category catalogue. `scope_notice` and `catalogue_version` are the frontend mock's names, and they are final (section 6).

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

204 with no body. 401 `SESSION_INVALID` for a bad token. A second delete with the same token gets 401, because the session is gone. A parse that is still running loses its child (section 9).

### `POST /api/v1/documents`

Uploads one file and queues its parse. The body is the raw file, not multipart: a multipart parser moves a file part to a temporary file once it passes 1 MiB, and an upload never touches disk (`Rules.md` section 5, `Phases.md` D3). The upload carries the file and nothing else. The role goes with the party binding, and the scope goes with the analysis request (`Phases.md` D1).

| Header | Rule |
|---|---|
| `Authorization` | `Bearer <token>` (section 7). The API checks it before it reads the body |
| `Content-Length` | Optional. A value over 10 MiB gets 413 before the API reads a byte |
| `Content-Disposition` | Optional. `attachment; filename*=UTF-8''NAME` names the file |
| `Content-Type` | Ignored. The type comes from the bytes |

The name comes from `filename*` (RFC 5987) alone. A plain `filename=` has no defined encoding, so the API does not read it. It decodes the value as UTF-8, keeps the text after the last `/` or `\`, removes every Unicode "other" character (controls such as NUL and U+0085, format characters such as U+202E and U+200B, private use and unassigned code points) and the line and paragraph separators U+2028 and U+2029, cuts the result to 255 characters and trims it. Letters, marks, symbols and ordinary spaces stay. The format characters include the zero-width joiners and directional marks that some Indic, Persian and Arabic names use, so a name loses them. A name that is missing, is not valid UTF-8 or has nothing left (empty, or only dots) becomes `document.pdf` or `document.docx`, to match the detected type. The name is for display. It lives in RAM and never reaches SQLite.

The API runs these checks in order and stops at the first that fails:

1. The bearer token: 401 `SESSION_INVALID`. A session that ends while the body arrives gets the same reply.
2. `MAX_UPLOADS_IN_FLIGHT` uploads are already arriving: 429 `QUEUE_FULL`, before the API reads a byte. An upload keeps its place until it gets its reply, whatever the reply.
3. A `Content-Length` over 10 MiB: 413 `FILE_TOO_LARGE`.
4. The size of the body: the API counts the bytes as they arrive and stops at 10 MiB plus one byte with the same 413, so a body with no `Content-Length`, or a false one, is bounded too.
5. An empty body: 400 `EMPTY_FILE`.
6. The type, read from the bytes: a PDF header in the first 1,024 bytes, or a ZIP that holds `word/document.xml`. Anything else is 415 `UNSUPPORTED_TYPE`. A ZIP that cannot be read passes as a DOCX and fails its parse job with `MALFORMED_FILE`.
7. The session already holds `MAX_DOCUMENTS_PER_SESSION` documents: 429 `DOCUMENT_LIMIT`.
8. `CLAUSEANCHOR_PARSE_QUEUE_LENGTH` parses are already waiting: 429 `QUEUE_FULL`. The API keeps nothing of the upload.

202:

```json
{
  "document_id": "3b0f6c1e-3a3e-4a52-9c3c-2f1d3a5f7a10",
  "parse_job_id": "7d2f9a44-8f0e-4c1b-b1a5-5e6a9c0d1e22",
  "expires_at": "2026-10-18T11:00:00Z"
}
```

| Field | Type | Meaning |
|---|---|---|
| `document_id` | string | The id for `GET` and `DELETE /api/v1/documents/{document_id}` |
| `parse_job_id` | string | The id for `GET /api/v1/jobs/{job_id}` |
| `expires_at` | string | ISO-8601 UTC, in whole seconds. It is the session's `expires_at`, because a document lives and dies with its session (`Phases.md` D5) |

The reply comes before the parse runs. Poll the job until it has `succeeded` or `failed`, then read the document.

### `GET /api/v1/documents/{document_id}`

The document's metadata and, once the parse has succeeded, the full parser output.

```json
{
  "id": "3b0f6c1e-3a3e-4a52-9c3c-2f1d3a5f7a10",
  "filename": "services-agreement.pdf",
  "status": "parsed",
  "media_type": "application/pdf",
  "byte_count": 48213,
  "expires_at": "2026-10-18T11:00:00Z",
  "parsed": { "source_text": "...", "text_sha256": "...", "nodes": [], "...": "..." }
}
```

| Field | Type | Meaning |
|---|---|---|
| `id` | string | The document id |
| `filename` | string | The cleaned name from the upload, or `document.pdf` or `document.docx` |
| `status` | string | `parsing` while the parse job waits or runs, `parsed` once it has succeeded, `failed` once it has failed. The job holds the code |
| `media_type` | string | `application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, from the bytes |
| `byte_count` | integer | The size of the upload in bytes |
| `expires_at` | string | The session's `expires_at` |
| `parsed` | object or `null` | `null` unless `status` is `parsed`. Then it holds the parser's full output, the form `to_json` writes with text (`ParserContract.md` section 2, `parser_output.schema.json`). The full text is always included. Every node also has a `page`, which the API adds (section 11). Its `nodes` can hold nodes of kind `party`, each with a `name_span`, and its `warnings` are objects, not strings. `coverage.partial` says whether text may be missing (all in section 11) |

404 `NOT_FOUND` for an unknown id and for another session's document alike, so an id tells a stranger nothing. 401 `SESSION_INVALID` for a bad token, an expired session included.

### `DELETE /api/v1/documents/{document_id}`

Deletes the document and its jobs from memory and from SQLite. A parse that is still running loses its child first, and the reply waits up to 5 s for the child to exit. The delete frees a slot under `MAX_DOCUMENTS_PER_SESSION`, so a client that replaces its upload deletes the old one first.

204 with no body. 404 `NOT_FOUND` for an unknown id, another session's document, or a second delete. 401 `SESSION_INVALID` for a bad token.

### `GET /api/v1/jobs/{job_id}`

The state of a parse job or an analysis job.

```json
{
  "id": "7d2f9a44-8f0e-4c1b-b1a5-5e6a9c0d1e22",
  "kind": "parse",
  "document_id": "3b0f6c1e-3a3e-4a52-9c3c-2f1d3a5f7a10",
  "analysis_id": null,
  "status": "failed",
  "stage": null,
  "completed_units": 0,
  "total_units": null,
  "error": { "code": "SCANNED_PDF", "message": "The PDF is scanned, so it holds no text to read.", "retryable": false }
}
```

| Field | Type | Meaning |
|---|---|---|
| `id` | string | The job id |
| `kind` | string | `parse` or `analysis` |
| `document_id` | string | The document the job reads |
| `analysis_id` | string or `null` | The id for `GET /api/v1/analyses/{analysis_id}`. `null` for a parse |
| `status` | string | `queued` while the job waits and `running` while it works. A parse then ends as `succeeded` or `failed`. An analysis ends as `succeeded` (a complete run), `partial` (it finished with a result that is not complete, section 10), `failed`, `cancelled` or `timed_out` |
| `stage` | string or `null` | The core's own word for what an analysis is doing, from its last progress event (the stub says `fixture`, the real model `inference`). `null` for a parse and before the first event |
| `completed_units` | integer | Units the core has finished. `0` for a parse |
| `total_units` | integer or `null` | Units the core plans to do, from its progress events. For the real model a unit is one window of one category, so the total is known after tokenizing. `null` for a parse and before the first event. It is a count of work done and never a percentage of risk found |
| `error` | object or `null` | `null` unless `status` is `failed`. Then `code`, a fixed `message` and `retryable`, as in the table below |

A job fails with one of these codes. They are not HTTP errors, and the reply to the poll is 200. The first nine are the parser's own (`ParserContract.md` section 9). The next three are API codes, for a parse child that was ended or that failed. The last two belong to analyses. A message never holds request input, document text or exception text.

| Code | Retryable | When |
|---|---|---|
| `MALFORMED_FILE` | no | A library could not read the file: a damaged PDF or DOCX, or a ZIP that is not a package |
| `ENCRYPTED_PDF` | no | The PDF needs a password to open |
| `SCANNED_PDF` | no | Every page with content is scanned, so there is no text to read |
| `TOO_MANY_PAGES` | no | The PDF has more than 100 pages |
| `TOO_MUCH_TEXT` | no | The file holds more than the API processes: 8 MiB of decoded PDF page content, 100,000 DOCX paragraphs or 500,000 characters (the parser's limits), or more than `MAX_BLOCKS_AND_NODES` blocks and nodes (section 8) |
| `ARCHIVE_TOO_LARGE` | no | The DOCX package expands to more than 100 MiB |
| `ARCHIVE_UNSAFE` | no | A member of the DOCX package has an unsafe name or an unsupported compression method |
| `TRACKED_CHANGES_PRESENT` | no | The DOCX has tracked changes. Accept all changes and upload it again |
| `NO_TEXT_FOUND` | no | The file parses and holds no text |
| `PARSE_TIMEOUT` | no | The child ran for `CLAUSEANCHOR_PARSE_KILL_SECONDS` seconds, and the API ended it |
| `PARSE_MEMORY_LIMIT` | no | The child needed more memory than `CLAUSEANCHOR_PARSE_MEMORY_MIB` allows |
| `PARSE_FAILED` | yes | The child exited with an error, wrote output the API could not read, or could not start |
| `ANALYSIS_INVALID_RESULT` | no | The analyzer returned a result that failed the checks of section 10. The API discards it and stores nothing |
| `ANALYSIS_FAILED` | yes | The analyzer raised any other exception |

The parser's `EMPTY_FILE`, `FILE_TOO_LARGE` and `UNSUPPORTED_TYPE` stop at the upload (section 2), so a job does not carry them. A cancelled or timed-out analysis is a status and not an error code.

404 `NOT_FOUND` for an unknown id, another session's job, and a job whose document was deleted. 401 `SESSION_INVALID` for a bad token.

### `POST /api/v1/jobs/{job_id}/cancel`

Stops an analysis that is waiting or running. Send no body.

202 with the job, as `GET /api/v1/jobs/{job_id}` shows it. A waiting analysis is `cancelled` in the reply. A running one stops at the core's next check between units of work, so the reply can still say `running`. Poll the job until it has ended. No result is stored for a cancelled analysis.

409 `JOB_NOT_CANCELLABLE` for a parse and for an analysis that has ended. A cancel that arrives after the analysis ended is not an error the client can retry. 404 `NOT_FOUND` for an unknown id or another session's job. 401 `SESSION_INVALID` for a bad token.

### `POST /api/v1/documents/{document_id}/analyses`

Queues an analysis of a parsed document and answers at once. The role does not travel here. It goes with the party binding (3-A, `Phases.md` D1).

```json
{ "category_ids": ["cuad.governing_law", "in.arbitration"], "jurisdiction_scope": "india_review" }
```

| Field | Type | Rule |
|---|---|---|
| `category_ids` | array of strings | Required. From 1 to 100 ids of at most 64 characters each, none repeated, each one an `id` in the catalogue (section 5). The API holds no id of its own. In sample mode each must also be one the sample holds (section 10) |
| `jurisdiction_scope` | string | Required. `india_review` or `unspecified` (`Phases.md` D1) |

A field the table does not list is refused. The API runs these checks in order and stops at the first that fails:

1. The bearer token: 401 `SESSION_INVALID`.
2. The body: the API reads it after the bearer check and stops at `MAX_JSON_BODY_BYTES`. 422 `VALIDATION_ERROR` for a body over that size, a missing, mistyped or extra field, an empty list or one over 100 ids, an id over 64 characters, or invalid JSON.
3. The document: 404 `NOT_FOUND` for an unknown id and for another session's document.
4. The parse: 409 `DOCUMENT_NOT_PARSED` unless the document's `status` is `parsed`.
5. The analyzer: 503 `NOT_READY` while it is `loading` or `failed`.
6. The catalogue: 503 `CATALOGUE_UNAVAILABLE` when it is missing or invalid, and 422 `VALIDATION_ERROR` for a repeated id or one the catalogue lacks.
7. Sample mode only: 409 `SAMPLE_MODE_ONLY` for any document but the prepared sample, then 422 `VALIDATION_ERROR` for an id the sample does not hold.
8. One at a time: 409 `ANALYSIS_IN_PROGRESS` when the session already has an analysis waiting or running, on any of its documents.
9. The queue: 429 `ANALYSIS_QUEUE_FULL` when `ANALYSIS_QUEUE_LENGTH` analyses are already waiting. The job row is rolled back.

202:

```json
{ "analysis_id": "5a1c0e2b-7d3f-4b6e-9a10-2c8d4e6f8a31", "job_id": "9c4e1f20-6b7a-4d8e-8f01-3a5b7c9d1e42" }
```

The reply comes before the analysis runs. Poll the job, then read the analysis. A new analysis on the same document replaces the previous one, whose `analysis_id` then answers 404. The old job stays readable.

### `GET /api/v1/analyses/{analysis_id}`

The analysis as it stands, in the app form of the core's result (`docs/ml/Interface.md`, "App adapter"). The reply is always 200 for an analysis the session owns. While the job waits or runs, and after it was cancelled, timed out or failed, `categories` is empty, because the core returns a result whole or not at all.

```json
{
  "id": "5a1c0e2b-7d3f-4b6e-9a10-2c8d4e6f8a31",
  "document_id": "3b0f6c1e-3a3e-4a52-9c3c-2f1d3a5f7a10",
  "text_sha256": "30322bcb16c66addcdfc77828e9c0c5f8e5eff2a89ecac1615ade3e89b037e4a",
  "contract_version": "2.0",
  "artifact_manifest_sha256": "a2ea8d4cc291e733ff3e7050153d445ba4419229398e259e35dbaef90e0b88df",
  "status": "partial",
  "mode": "sample",
  "jurisdiction_scope": "india_review",
  "created_at": "2026-10-30T11:00:00Z",
  "finished_at": "2026-10-30T11:00:01Z",
  "scope_notice": "This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment.",
  "catalogue_version": "1.0.0",
  "processing_complete": false,
  "decision_coverage": { "resolved": 2, "requested": 4 },
  "categories": [
    {
      "category_id": "cuad.cap_on_liability",
      "status": "found",
      "decision_confidence": null,
      "reason_code": null,
      "search_complete": true,
      "windows_done": 1,
      "windows_total": 1,
      "unresolved_count": 0,
      "clauses": [
        {
          "id": "fixture-cap-1",
          "category_id": "cuad.cap_on_liability",
          "span": { "doc_id": "3b0f6c1e-3a3e-4a52-9c3c-2f1d3a5f7a10", "text_sha256": "30322b...", "start": 89, "end": 132, "text": "..." },
          "status": "accepted",
          "confidence": null,
          "confidence_band": "unvalidated",
          "calibration_scope": "unvalidated",
          "origin": "fixture",
          "rule_flags": [],
          "passages": [],
          "retrieval_status": "not_run"
        }
      ]
    }
  ],
  "warnings": ["FIXTURE_ONLY_NO_MODEL_INFERENCE", "CONFIDENCE_NOT_MEASURED"]
}
```

The example is the sample run, cut to its first category. It asked for four, and it ended `partial` because one of them (`in.seat_venue`) is `unavailable` with an unfinished search.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | The analysis id |
| `document_id` | string | The core's `doc_id`. The API passes the document id to the core as its `doc_id`, so every span carries it |
| `text_sha256` | string | The hash of the document's `source_text`. Every span repeats it |
| `contract_version` | string | The core's contract version, `2.0` |
| `artifact_manifest_sha256` | string or `null` | The core's identity for what produced the result: the model manifest in real mode, the fixture hash in sample mode. `null` until a result exists |
| `status` | string | The job's status, as in the table under `GET /api/v1/jobs/{job_id}` |
| `mode` | `sample` or `real` | The core's `mode`, with `stub` written as `sample` |
| `jurisdiction_scope` | string | What the request sent |
| `created_at`, `finished_at` | string, string or `null` | ISO-8601 UTC, in whole seconds. `finished_at` is `null` until the job has ended |
| `scope_notice` | string | The fixed text of `Phases.md`, Review scope. The same constant as in `capabilities` |
| `catalogue_version` | string | The catalogue's version when the analysis was read |
| `processing_complete` | boolean | Section 10. True only when nothing was left out |
| `decision_coverage` | object | `requested` is the number of categories asked for. `resolved` is defined in section 10 |
| `categories` | array | The core's `CategoryResult`, field for field, in the order requested. Section 10 lists what the API never changes |
| `warnings` | array of strings | The core's warning codes. Parser warnings are on the document |

A clause carries the core's `ClauseFinding` unchanged: `id`, `category_id`, `span`, `status` (`accepted` or `review_candidate`), `confidence` (a number or `null`), `confidence_band`, `calibration_scope`, `origin` (`model` or `fixture`), `rule_flags`, `passages` and `retrieval_status`. A span is `{doc_id, text_sha256, start, end, text}` with `source_text[start:end] == text`, in Unicode code points with an exclusive end. `polarity` and `actor_evidence` come with the party binding (3-A).

404 `NOT_FOUND` for an unknown id, another session's analysis and one a newer analysis replaced. 401 `SESSION_INVALID` for a bad token. 503 `CATALOGUE_UNAVAILABLE` if the catalogue is missing. That cannot happen once an analysis exists, because the start needs the catalogue, so the route keeps the check as a guard.

## 4. Configuration

The API reads the process environment once, at start. It does not read a `.env` file. A bad value stops the start with a message that names the variable and never shows its value.

| Variable | Default | Meaning |
|---|---|---|
| `CLAUSEANCHOR_ANALYZER` | `stub` | `stub` or `real`. The stub serves sample mode, and `real` loads Tanishq's `CandidateOnlyAnalyzer` from the artifacts (section 10) |
| `CLAUSEANCHOR_ARTIFACTS_DIR` | none | The artifacts directory. Required when the analyzer is `real` and ignored otherwise |
| `CLAUSEANCHOR_ARTIFACTS_SHA256` | none | The canonical SHA-256 of the artifact manifest: 64 lowercase hexadecimal digits, as Tanishq's export receipt gives them. Required when the analyzer is `real`. It is the trust anchor, and the core refuses a bundle whose manifest hashes to anything else. A wrong value fails the load, and `/ready` says `failed`. A malformed value stops the start |
| `CLAUSEANCHOR_DB_PATH` | `:memory:` | The SQLite path. The default writes nothing to disk. A file path works too, and its three tables are emptied at every start (D4). An upload's file name never reaches SQLite. A path the API cannot open stops the start |
| `CLAUSEANCHOR_SESSION_TTL_MINUTES` | `60` | Session lifetime. A whole number from 1 to 60, because the promise to users is deletion within 60 minutes |
| `CLAUSEANCHOR_PARSE_KILL_SECONDS` | `120` | Wall-clock limit for one parse. The slowest case measured in 2-C took 23 s, so 120 s stays (section 9) |
| `CLAUSEANCHOR_PARSE_QUEUE_LENGTH` | `2` | How many parses can wait while one runs (plan 9.3). A further upload gets 429 `QUEUE_FULL` |
| `CLAUSEANCHOR_PARSE_MEMORY_MIB` | `1536` | Memory cap of the parse child, in MiB (section 9) |
| `CLAUSEANCHOR_FRONTEND_DIST` | none | The folder of the built frontend (`frontend/dist`). When set, the API serves it at `/` on the same origin as the API: `index.html` for the root and the hashed files under `/assets/`. A request that no API route claims goes to the frontend, and an unknown `/api` path is still the 404 envelope. The folder must hold `index.html`, or the start fails. Unset in development, where the Vite server serves the page. The Docker image sets it (`Deploy.md`) |

The four numbers must be whole numbers of at least 1. The parser's own limits (file size, page count, text length) are not settings. They stay in the parser. No environment variable sets the limits in section 8.

## 5. Catalogue `[CONTRACT]`

Tanishq owns the categories: 41 CUAD categories plus 5 India extensions, 46 in all. The API loads them from one JSON file, `ml/configs/catalogue.json`, through `load_catalogue` in `app/services/scope.py`. It reads Tanishq's file in place and keeps no copy. `DEFAULT_CATALOGUE_PATH` in `app/config.py` finds the file from its own location, so the working directory does not matter. The API reads the file once, at start, so a changed file needs a restart.

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

The API reports two failure states and never guesses. With no file, `/ready` says `catalogue: missing` and `/capabilities` answers 503. With a broken file, `/ready` says `catalogue: invalid` and `/capabilities` answers 503. The committed file loads, and `tests/test_real_catalogue.py` pins what Tanishq's file promises: 46 unique ids, 41 `cuad` and 5 `india_extension`, and the ten categories that plan 4.3 annotates. It pins neither `catalogue_version` nor any `support_status`. Tanishq changes both as categories get validated, and `/capabilities` passes them through unchanged.

## 6. Differences from plan section 9

This file governs, and the plan will copy it.

- Health and readiness sit at `/api/v1/health` and `/api/v1/ready`. The plan has `/healthz` and `/readyz` outside the base path. The readiness body is `{ready, checks}`, where the plan has `{ready, mode, artifact_manifest_sha256}`.
- `Capabilities` has `scope_notice`, `mode`, `catalogue_version` and `categories`. The plan's also lists `contract_version`, upload limits, `upload_enabled` and `artifact_ready`. The parts that own those values add them.
- A category has four fields. The plan's `CategorySpec` adds `description`.
- The error envelope keeps the five fields of plan 9.1's `Error`. `details` is `{}` except on `NOT_READY`.
- `POST /api/v1/sessions` returns `token` and `expires_at`. The plan's `Session` adds `session_id`, which the frontend has no use for, so the API does not show it.
- The plan says "401 invalid capability" and 410 for an expired document or job. Here every bad token is one 401, `SESSION_INVALID` (section 7). A document lives and dies with its session (D5), so after expiry a request fails the bearer check before it reaches a document route, and 410 does not occur.
- Readiness adds `store` and `database` to the checks.
- `POST /api/v1/documents` takes the raw file as the body, where the plan has multipart with `role` and `jurisdiction_scope` fields. The raw body keeps the file off disk, and the role and scope travel later (`Phases.md` D1). The file name comes from `Content-Disposition`.
- The plan's 409 for sample mode on upload does not exist here. A parse does not depend on the analyzer, and the default analyzer is the stub, so every upload would get the 409. Sample mode limits the analysis (2-D).
- The upload statuses are 413, 415 and 429, as the plan says, plus 400 `EMPTY_FILE`, which the plan does not list. A full session and a full queue both answer 429, with `DOCUMENT_LIMIT` and `QUEUE_FULL` to tell them apart. `QUEUE_FULL` also answers when 4 uploads are already arriving (section 8).
- `GET /api/v1/documents/{document_id}` has no `include_text` query. The full text is always in `parsed`. The reply holds metadata and `parsed`, where the plan's `Document` is flat (`source_text`, `nodes`, `warnings` as strings). The nesting is final, and the 4-C adapter reads `parsed.source_text`, `parsed.text_sha256`, `parsed.nodes` and `parsed.warnings`.
- A failed job's `error` has `code`, `message` and `retryable`. The plan's `ErrorBody` adds `request_id` and `details`, which a job state has no use for. The job also leaves out the plan's `analysis_id`, `stage`, unit counts, `queue_position`, `result_url` and timestamps. 2-D adds the ones the analysis needs.
- An unreadable ZIP passes the upload and fails its parse job with `MALFORMED_FILE`. The type check reads the first bytes only.
- Analyses (2-D). The plan's three routes stay: `POST /documents/{id}/analyses`, `GET /analyses/{id}` and `POST /jobs/{id}/cancel`. The mock fetches the analysis by document id and the plan by analysis id. This file follows the plan and the route stays (2-E): the mock's `getAnalysis(token, documentId)` is a mismatch for the 4-C adapter, which keeps the `analysis_id` that the start returns and reads the analysis by it. No route reads the latest analysis of a document, and none is added.
- `category_ids` is required, at least one id, and the plan's `null` for "all" is not accepted. "All" would mean the whole catalogue in real mode and the sample's four ids in sample mode, so the client sends the ids it shows. `jurisdiction_scope` is required too. The plan puts it on the upload, and the mock's `startAnalysis` sends it with the start. The plan's `Idempotency-Key` header is not read.
- The plan lets a start answer 409 for "parse pending" and "already running". Here they are two codes (`DOCUMENT_NOT_PARSED`, `ANALYSIS_IN_PROGRESS`), and the second applies to the whole session as plan 9.3 says ("one active analysis per session"), where the plan's 409 reads as per document.
- Sample mode is enforced at the analysis start with 409 `SAMPLE_MODE_ONLY`, where the plan has the 409 at upload (section 6, above). The prepared sample document itself comes from the plan's `POST /samples/{sample_id}/open`, which part 3-C builds. Until then no HTTP route makes the sample document, and the tests put it in the store.
- The plan's `Job` has `analysis_id`, `stage`, `completed_units` and `total_units`, and this file adds them. It still leaves out `queue_position`, `result_url`, the timestamps and the job's own `error` body, as in 2-C. A cancel answers 202 with the job, as the plan says. The mock's `cancelJob` returns nothing and ignores an ended job, where the plan and this file answer 409.
- `timed_out` is a job status. The plan's `JobStatus` has no such value, and the frontend's `JobStatus` type needs it at 4-C. The plan says a time-out yields "a partial result". The core returns a result whole or not at all, so a time-out has no result and its analysis has no categories (a question for Tanishq: a snapshot on cancel).
- `decision_coverage.resolved` counts only `found` and `absent`. The mock counts every category that is not `unavailable`, so it counts `abstained` as resolved. The 4-C adapter follows this file (section 10).
- `Analysis` leaves out the plan's `party` (3-A) and the clauses' `polarity` and `actor_evidence` (3-A), and adds `scope_notice`, `catalogue_version`, `processing_complete`, `decision_coverage` and `finished_at`, which the mock names. The frontend's `Clause` lacks `origin`, and its `Passage` lacks `judgment_text_sha256` and `corpus_version`. The core has all three and this file passes them on.
- `GET /api/v1/ready` reports the analyzer as `ok`, `loading` or `failed`. The plan's `{ready, mode, artifact_manifest_sha256}` stays replaced by `{ready, checks}` (section 6, above).
- `CLAUSEANCHOR_ARTIFACTS_SHA256` is a new variable. D8 lists none for the manifest digest. The core needs the canonical digest from outside the bundle, and a digest stored inside the bundle would trust the bundle itself.

Differences settled in 2-E. The 4-C adapter follows each one, and `frontend/` does not change before then.

- Names. `scope_notice`, `catalogue_version`, `processing_complete` and `decision_coverage {resolved, requested}` are the mock's names, the API already serves them, and they stay. The plan has none of the four. `ReviewUnit`, `ManualReview` and `getManualReview` have no endpoint. They are reserved for 3-D (section 13).
- The mock's `DocNode.page` is a number, and the plan's `Node` also has `source_locator`. Here `page` is a number or `null`, and a node has no locator, because locators belong to blocks (`ParserContract.md` section 4). The plan's `offset_unit` is not served, because every offset is a code point.
- The mock's `name_span` is an optional object. Here a party node has it as an object or `null`, and no other node has the key (section 11).
- Parser warnings are objects `{code, page, detail}`. The plan's `Document.warnings` and the mock's are strings. The `warnings` of an analysis stay strings, because they are the core's codes (section 11).
- The mock has no `coverage` on a `Document`. It is `parsed.coverage.partial` here, and the partial-read notice follows it and not the warning list (section 11).
- The party binding is `role` with `party_node_id` or `selected_span {start, end}`. The plan has `selected_span` as a full `Span` and adds `alias_spans`, which is dropped until 3-A decides the short-name question (section 12).

## 7. Bearer token

A route that needs a session reads `Authorization: Bearer <token>`. The scheme name is not case sensitive. The API hashes the token with SHA-256 and looks up the hash, so the stored value is not a credential.

Every bad token gets the same reply: 401, `SESSION_INVALID` and `WWW-Authenticate: Bearer`. That covers a missing header, another scheme, an empty token, a token that was never issued and a token whose session expired or ended. The reply never repeats the token. Routes use one dependency for the check, `require_session` in `app/api/auth.py`.

One code covers unknown and expired, for two reasons. The frontend mock raises one `expired` error for any token it does not know. The Reader sends that error and `not_found` to the same Expired page, which takes its wording from the address (`?reason=`). And the server cannot tell the two apart: it deletes an expired session the first time it sees it, and from then on the token looks unknown.

## 8. Limits

These eight are fixed limits in `app/config.py`, and no environment variable sets any of them. `ANALYSIS_QUEUE_LENGTH` and `ANALYSIS_TIMEOUT_SECONDS` are also fields of `Settings`, so a test can change them. Plan 9.2 names a 429 for the session limit and gives no number, and neither plan section gives a document limit, so those values are proposals for Aryan to confirm. Plan 9.3 gives the analysis queue and the time, and 2-D.1 checked the time against the real model. The last three came with the 2-R review.

| Constant | Value | Meaning |
|---|---|---|
| `MAX_SESSIONS` | 25 | Live sessions at once. Past it, `POST /api/v1/sessions` answers 429 `SESSION_LIMIT`. Expired sessions do not count |
| `MAX_DOCUMENTS_PER_SESSION` | 5 | Documents one session can hold. The store enforces it, and `POST /api/v1/documents` answers 429 `DOCUMENT_LIMIT` past it. `DELETE /api/v1/documents/{document_id}` frees a slot |
| `SWEEP_INTERVAL_SECONDS` | 30 | How often the sweep runs. Every lookup checks the time, so an expired session is unreachable at once. The sweep sets how long its data stays in memory after that |
| `ANALYSIS_QUEUE_LENGTH` | 2 | Analyses that can wait while one runs (plan 9.3). A further start answers 429 `ANALYSIS_QUEUE_FULL`. A cancelled analysis gives its place back at once |
| `ANALYSIS_TIMEOUT_SECONDS` | 1800 | Wall-clock limit for one analysis, counted from the moment it starts running and not from the start request. Past it the API stops the analysis and the job ends `timed_out` (section 10) |
| `MAX_UPLOADS_IN_FLIGHT` | 4 | Uploads the API takes at once, from the bearer check to the reply. A fifth gets 429 `QUEUE_FULL`, and the server reads none of its body. Each upload holds its body twice while the chunks join, so 4 hold at most 80 MiB. The limit covers all sessions together |
| `MAX_JSON_BODY_BYTES` | 65536 | Largest JSON request body (64 KiB), today the analysis start. The API stops reading at this size and answers 422 `VALIDATION_ERROR` |
| `MAX_BLOCKS_AND_NODES` | 20000 | Blocks plus structure nodes that a parsed document may hold. The parse child counts them after the parse. Past the limit it sends `TOO_MUCH_TEXT` and no document, so the API never receives or stores one. The 25 contracts peak at 385 |

2-D.1 timed the real model on a laptop with torch's default 8 threads and a batch size of 1. A window took 0.34 to 0.51 s through the API (0.37 and 0.51 s in two runs of the 33-page contract below) and 0.68 s in the receiver check, which times the whole call. A 33-page contract (74,821 characters, 17,350 tokens) plans 50 to 55 windows for each category, so 2,185 for all 41 CUAD categories. That run takes 804 to 1,123 s at the two contract rates and 1,486 s at the receiver-check rate. All three fit in 1,800 s, so the limit stays. The same contract with every category stops fitting when a window costs more than 0.82 s. The plan's ceiling of 15,000 category-window pairs would take 1.5 to 2.8 hours at these rates, so the limit still ends the largest documents the parser accepts. The deploy host is unmeasured, and 4-C times it there.

2-C measured what a stored document costs (`BuildLog.md`). The largest document in the smoke set takes 1.9 MiB, which is about 12 bytes for each character of text. A document at the 500,000-character limit would take about 6.5 MiB at that ratio. So 25 sessions of 5 documents take 241 MiB at the smoke-set size and about 0.8 GiB at the limit. The ratio holds for text-heavy files only. A block or node costs about 550 bytes whatever its length, so a file of many short blocks costs far more for each character: 94 bytes at 6 characters a block. `MAX_BLOCKS_AND_NODES` bounds that. Made-up DOCX files at the limit stored as 10.3 MiB (9,990 blocks and 9,990 nodes), 10.8 MiB (20,000 blocks of 5 characters) and 11.5 MiB (20,000 blocks of 24 characters, 499,999 in all). So 125 documents that sit at both limits take 1.4 GiB. The stored documents fit in 1 GiB for ordinary files, and a store full of the densest files does not. A parse child at its 1,536 MiB cap does not fit beside them on a 1 GiB host, and 4-B decides what to do about that. With the real model loaded, the API process alone peaks at 1,281 MiB (`Architecture.md` section 5), so real mode needs a larger host than that.

## 9. Parse jobs

The API parses each upload in a child process, so a hostile file can cost parse time and parse memory only inside a process that the API can end. Three costs stay in the API process, each with a bound. The type check lists the members of a ZIP (a made-up 9.0 MiB ZIP with 200,000 entries took 0.87 s and 75 MiB), which the 10 MiB limit and the 4 uploads in flight bound. The child's reply is JSON that the API reads, and the API stores the parsed document. `MAX_BLOCKS_AND_NODES` bounds both (section 8).

- **One child per parse.** The child runs `python -m app.parse_worker`, parses one file and exits. A new child for each parse keeps the DOCX reader's process-wide settings out of the next parse.
- **One at a time.** A single worker thread takes jobs from a queue. One parse runs, and up to `CLAUSEANCHOR_PARSE_QUEUE_LENGTH` wait. A further upload gets 429 `QUEUE_FULL`. The bytes of a waiting upload stay in RAM, up to 10 MiB each.
- **No disk.** The bytes go to the child on stdin and the result comes back on stdout. No file is written. The API discards the child's stderr, because library messages can hold document text, and it logs the class name of an unexpected error and nothing else.
- **Wall-clock kill.** After `CLAUSEANCHOR_PARSE_KILL_SECONDS` the API ends the child, and the job fails with `PARSE_TIMEOUT`. The slowest case measured took 23 s: a dense 8 MiB PDF, which is the most decoded content the parser accepts.
- **Memory cap.** Each child runs under `CLAUSEANCHOR_PARSE_MEMORY_MIB`. On Windows the cap is a job object, and the child joins it before its first instruction. On Linux it is `RLIMIT_AS`. The default of 1,536 MiB leaves room for a PDF at the 500,000-character limit (about 1.2 GiB, extrapolated) and ends a 100 MiB DOCX of empty paragraphs (about 2.5 GiB, extrapolated) before it reaches that size.
- **What counts as a memory kill.** A library can turn a refused allocation into another error, so the API does not trust a child that came within 5 percent of its cap. On Windows the API reads the child's peak, and a peak of 95 percent of the cap or more fails the job with `PARSE_MEMORY_LIMIT` whatever the child said. On Linux the peak is not available, so only a `MemoryError` that the child itself catches gives that code. The Linux cap is untested, and 4-B measures it on the deploy host.
- **Delete and expiry.** `DELETE /api/v1/documents/{document_id}`, `DELETE /api/v1/sessions/current` and the expiry of a session each end the child of every document they remove. A delete waits up to 5 s for the child to exit, then returns. A waiting job loses its bytes. The API also catches a delete that lands after the upload stored the document and before the queue took it: once the queue accepts the job, the route reads it back and, if it is gone, tells the queue to drop the bytes. The upload still answers 202, and the job reads 404. A shutdown ends the running child too.

## 10. Analyses

An analysis runs a parsed document through Tanishq's core (`clauseanchor_core`). The API gives the core the stored text as the parser made it, and never rebuilds or cleans it (`Phases.md` D6).

- **One analyzer.** One analyzer serves the whole process. `stub` builds the core's `StubAnalyzer` from its sample fixture. `real` builds `CandidateOnlyAnalyzer` from `CLAUSEANCHOR_ARTIFACTS_DIR`, checked against `CLAUSEANCHOR_ARTIFACTS_SHA256`, on CPU with a batch size of 1. The API never falls back from `real` to the stub.
- **Loading.** The analysis worker loads the analyzer before it takes a job, so every other route answers meanwhile. `GET /api/v1/ready` reports `loading`, then `ok`, or `failed` if the load raised. A failed load logs the exception class and nothing else, and it does not retry.
- **One at a time.** A single worker thread feeds the analyzer one job at a time, in the order the starts arrived. The core serializes calls on one instance and raises a busy error on a concurrent one, so a second worker would fail. Up to `ANALYSIS_QUEUE_LENGTH` jobs wait (section 8). A session has one waiting or running analysis at a time, whichever of its documents it reads.
- **Progress.** The core reports a progress event between units of work, and the API copies `stage`, `completed_units` and `total_units` into the job each time. The numbers count work done. They do not measure risk.
- **Cancel.** A cancel sets a flag, and the core reads it between units. A waiting job ends `cancelled` before the cancel reply returns. A running job ends at the next check. The core cannot interrupt a unit already under way, so with the real model a stop waits for the window in progress.
- **Time limit.** The clock starts when the job starts running, not when it was queued. At `ANALYSIS_TIMEOUT_SECONDS` the API sets the same flag, and the job ends `timed_out`.
- **Delete and expiry.** Deleting a document, deleting a session and the expiry of a session each stop the analysis of every document they remove, by the same flag. The job goes with its document, so no status is left to read. The API catches a delete that lands after the start stored the job and before the queue took it the same way: once the queue accepts the job, the route reads it back and, if it is gone, tells the queue to drop the text. The start still answers 202, and the job reads 404. A shutdown stops the running analysis and waits up to 30 s for the worker.
- **Stopped means no result.** The core returns a result whole or not at all. A cancelled, timed-out or deleted analysis stores nothing, even if the analyzer finished first, and its `categories` stay empty.
- **Failures.** An analyzer exception ends the job `failed` with `ANALYSIS_FAILED`. The log holds the exception class and nothing else, because exception text can hold document text.

### Sample mode

The stub takes its own fixture text and its own categories and nothing else (`Phases.md` D7). The API tells the sample document from any other by its text hash, which must equal the hash of the fixture text. In sample mode a start on any other document gets 409 `SAMPLE_MODE_ONLY`, and an id outside the stub's four categories gets 422 `VALIDATION_ERROR`. Part 3-C builds the route that opens the sample document (section 6).

### Result checks

Every result passes these checks before the store takes it. A result that fails one ends the job `failed` with `ANALYSIS_INVALID_RESULT`, and the API stores nothing.

1. The core's `validate_result` against the document's text: each span matches the text it points at, the counts add up, and the states agree with each other.
2. `doc_id` is the id of the document that was analysed.
3. `mode` is the mode this process runs, so a stub result cannot pass as a real one.
4. The result holds the requested categories, no more and no fewer.
5. When the parse was `partial` (`coverage.partial`), no category reads `absent`. The parser says text may be missing, so "not found" would claim too much. The API rejects such a result and does not rewrite it.

### `processing_complete`

True only when all three hold:

- the parse was not `partial`,
- the job was not cancelled and did not time out,
- every requested category has `search_complete` true.

A job that ends with a result is `succeeded` when `processing_complete` is true and `partial` otherwise. A waiting, running, cancelled, timed-out or failed analysis reads false. The field says the run left nothing out. It does not say the contract is safe, and it does not say every clause was found.

### `decision_coverage`

`requested` is the number of categories asked for. `resolved` is the number whose status is `found` or `absent`, the two accepted decisions. A category that is `abstained` or `unavailable` is not resolved. `resolved` is 0 when there is no result.

The candidate-only analyzer (`docs/ml/RealAnalyzer.md`) cannot emit `found` or `absent`. Its processed categories are `abstained`, its findings are `review_candidate` with a null `confidence`, and its India categories are `unavailable`. So `resolved` is 0 in real mode until a later analyzer can decide a category. The frontend mock counts `abstained` as resolved, so the 4-C adapter changes to follow this definition.

### What the API never changes

The API adds the analysis id, the job status, the timestamps, the jurisdiction, the scope notice, the catalogue version, `processing_complete` and `decision_coverage`. It passes everything the core wrote through in its original kind:

- A `review_candidate` stays a `review_candidate`. The API never upgrades a status.
- `confidence` and `decision_confidence` stay as the core set them. A null stays null, and the API fills in none.
- `confidence_band`, `calibration_scope`, `origin`, `rule_flags`, `reason_code`, `search_complete`, the window counts and `unresolved_count` stay as the core set them. The API marks no category validated.
- No response holds a verdict, a risk score, a safety percentage or a completeness percentage.

## 11. Document fields

The document read (section 3) returns the parser's output under `parsed`. The API adds one field to it, `page` on every node. Take `page` off the nodes and `parsed` is the parser's output again, as `parser_output.schema.json` describes it.

### Nodes

A node holds the parser's fields (`ParserContract.md` section 7) and `page`.

| Field | Type | Meaning |
|---|---|---|
| `page` | integer or `null` | The page of the block that holds the node's `start`. A PDF gives its 1-based page number. A DOCX has no pages, so it gives `null`. It is also `null` for a `start` that no block holds, and the parser never produces one |

The API works `page` out when it serves the document. The parser, the parse child and `parser_output.schema.json` have no such field.

### `name_span` `[CONTRACT]`

A node of kind `party` has `name_span`, and no other node has the key (`ParserContract.md` section 8):

```json
{ "id": "n0001", "kind": "party", "start": 41, "end": 112, "page": 1, "name_span": { "start": 41, "end": 63 }, "...": "..." }
```

- `start` and `end` are code points into `source_text`, in the same coordinates as the node's own `start` and `end`, with `node.start <= start < end <= node.end`.
- It covers the party's name alone (`ABC Technologies, Inc.`) and not the defining phrase around it (`(the "Supplier")`), so the frontend never cuts a name at a comma.
- It is `null` when the parser cannot isolate the name.
- A `null` span, and a node without the key, read as the whole node text.

### Warnings

`parsed.warnings` is an array of objects `{code, page, detail}`, as the parser emits them (`ParserContract.md` section 10). It never holds strings.

```json
{ "code": "UNSUPPORTED_DOCX_FEATURE", "page": null, "detail": "altChunk" }
```

`code` is one of the parser's warning codes. `page` is a 1-based PDF page or `null`. `detail` is `null` or one of two fixed words, `altChunk` and `unknown_block`, so it never holds file text. The parser builds it from those two literals, and a test reads the parser's source to keep it so (`tests/test_document_read.py`). Before a parser release can put file text in `detail`, the API must drop the field.

The `warnings` of an analysis (section 3) are another list. They are the core's codes, as strings.

### Partial reads

`parsed.coverage.partial` is true when text may be missing from `source_text` (`ParserContract.md` section 6). Two causes raise no warning: a searchable scan page (an image page with 20 to 199 characters outside the margins) and a PDF form field or free-text annotation that holds text. So `partial` can be true while `warnings` is empty.

For the 4-C adapter: the frontend shows its partial-read notice whenever `coverage.partial` is true, whether or not a warning exists. A partial parse never reads as "nothing found".

## 12. Party binding `[CONTRACT]`

Part 3-A builds the endpoint, which the plan puts at `PATCH /api/v1/documents/{document_id}/party`. This section fixes the shape of its request, so the frontend and 3-A start from the same shape. There is no route, no model and no test for it yet, and it is not in section 3.

The request has `role` and exactly one of the two fields below. `role` is one of the plan's seven: `buyer_customer`, `supplier_vendor`, `employer`, `employee`, `licensor`, `licensee` and `other` (`Phases.md` D1).

| Field | Type | Meaning |
|---|---|---|
| `party_node_id` | string | The `id` of a node in `parsed.nodes` whose `kind` is `party` |
| `selected_span` | `{start, end}` | A party the parser missed. `start` and `end` are code points into `source_text` |

Validation, each failure a 422 `VALIDATION_ERROR`:

- Both fields, or neither.
- A `party_node_id` that names no node of the document, or a node whose `kind` is not `party`.
- A `selected_span` that breaks `0 <= start < end <= len(source_text)`.
- Any field the table does not list. `alias_spans` is not part of the shape until 3-A decides the short-name question (`Phases.md`, 3-A).

**None of these** (Aryan, 3 November 2026). When the user picks none of the detected parties, no binding exists. The client sends no binding request, and the analysis runs with no party, so polarity is not shown. If a binding exists and the user changes their mind, the client deletes it, and part 3-A defines that delete. The request keeps the rule above: exactly one of `party_node_id` or `selected_span`. The mock's `party_node_id: null` is not a valid body.

## 13. Reserved names

`ReviewUnit`, `ManualReview` and `getManualReview` are the frontend mock's names for the manual-review list. Part 3-D owns them and may change them. No endpoint serves them now, and `docs/app/openapi.json` holds none of the three.

## 14. The OpenAPI schema

`docs/app/openapi.json` is the OpenAPI document of the app, built in stub mode on the default settings, with sorted keys and one trailing newline, so the same code gives the same bytes. After any change to a route, a response model or the pinned FastAPI or Pydantic version, regenerate it from `backend/` with the virtual environment active:

```bash
python -m app.scripts.export_openapi
```

Three checks guard it (`tests/test_openapi_export.py`):

- The committed file equals what the app builds. The failure message names the command above.
- Every route in section 3 (a `###` heading with a method and a path) is in the schema, and every route in the schema is in section 3. The route that serves the schema itself is in neither.
- No field in the schema or in the parser's JSON Schema is named for a score, a verdict, a percentage, a risk or safety.

The schema types `parsed` as an open object, because the API passes the parser's output through as plain data. Its shape is `parser_output.schema.json` plus `page`. This file governs where the two disagree.
