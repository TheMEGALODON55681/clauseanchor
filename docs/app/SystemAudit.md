# System audit: scale, security, cost and failure

A written audit of ClauseAnchor as it is built and deployed on 11 November 2026 (HEAD `459bcf0`), before it grows. It asks six hard questions of the architecture, fixes the two findings that are small and real on the live demo, and records every other finding with an owner. The architecture is in [Architecture.md](Architecture.md), the limits in [API.md](API.md) section 8, the deployment in [Deploy.md](Deploy.md), and the part entry and the open items in [Phases.md](Phases.md), part 4-B.2.

## How to read this file

- **Where a number comes from.** Every figure carries a tag. **[M]** is measured, with the file or the command. **[C]** is cited from a page or a price list, with its address. **[E]** is an estimate, with its formula and its inputs. A figure with no tag is a count taken from the code, with its file.
- **Not measured on the host.** Nothing was timed on Azure. All timings are from the laptop runs in `BuildLog.md` (2-C, 2-D.1) and the CI run of 4-B. The live URL was not load tested, and no server and no browser ran for this audit. Load figures are worked on paper from the measured per-request costs.
- **The question every section answers.** "What would break at scale?" Each section ends with a jury of five (a Contrarian, a First-Principles engineer, an Attacker, an SRE and a Cost owner). Each juror pushes on the findings alone. A juror who finds something new adds it, and the round runs again. A section is done when a round finds nothing new.
- **Finding ids.** `SA1` to `SA20` are this audit's findings, listed with their triage in section 7. The 2-R ids (`R5`, `R19` and the rest) and their owners are in `Phases.md`. This file links to them and says whether the audit changes their status. It does not report them again.

## 0. What the app is, in numbers

| Item | Value | Source |
|---|---|---|
| Hosting | Azure Container Apps, Express environment, Consumption billing, Central India | `Deploy.md`, `deploy/azure-containerapp.yaml` |
| Size and replicas | 2 vCPU, 4 GiB, minimum 0, maximum 1 | `deploy/azure-containerapp.yaml` lines 31 to 34, 55 to 57 |
| Probes | Startup on `/api/v1/ready` (30 s delay, 30 s period, 10 tries), liveness on `/api/v1/health`, no readiness | same file, lines 34 to 54 |
| Logs | Destination none: live stream only | `Deploy.md` step 8 |
| Sessions | 25 live, 60 minutes fixed, 5 documents each | `config.py` lines 19, 27, 28 |
| Queues | 1 parse running and 2 waiting, 4 uploads in flight, 1 analysis running and 2 waiting | `config.py` lines 21, 33, 45 |
| Analysis limit | 1,800 s from the moment it starts running | `config.py` line 46 |
| Model | RoBERTa-base, v0 candidate, `.safetensors` weights | `Dockerfile` lines 42, 51 |
| Image | 1,671 MiB. Container peak 1,026 MiB, file cache included | [M] `Architecture.md` section 8.1, the CI run on `c26236b` |
| Tests before the audit | Backend 1785 passed, 27 skipped, ruff clean. Frontend 135 of 135 | [M] run on 11 November 2026, `BuildLog.md` |

## 1. Data model stress test

ClauseAnchor has no persistent database. The audit maps what exists and does not invent more.

### 1.1 The entities that exist

| Entity | Where it lives | Key | Refers to | Looked up by | Deleted by, and when |
|---|---|---|---|---|---|
| Session | SQLite `sessions` (`store.py` 37 to 42) | `id` (uuid4) and `token_hash` (SHA-256, unique) | none | the unique index on `token_hash`. The live count uses the `sessions_expiry` index | Expiry at its next access (`store.py` 190 to 202, 241 to 246), the sweep every 30 s (`store.py` 428 to 439, `main.py` 32 to 39), or `DELETE /sessions/current` (`routes.py` 186 to 193) |
| Document row | SQLite `documents` (`store.py` 43 to 50) | `id` (uuid4) | `session_id`, with delete cascade | primary key, and the `documents_session` index | With its session, or `DELETE /documents/{id}` |
| Document record | RAM dict `Store._documents` (`store.py` 99 to 111, 151) | document id | session id, the parsed document, the latest analysis | dict get, then a check of `doc.session_id` | Same moments as the row. RAM goes first (`store.py` 457 to 459) |
| Canonical text, blocks, nodes, warnings | Inside `ParsedDocument`, held by the document record | via the document | none | via the document | With the record |
| File name | The document record only, never SQLite | via the document | none | via the document | With the record |
| Upload bytes | RAM in the parse queue (`parse_jobs.py` 40 to 47, 75 to 85) | document id | none | dict by document id | When the parse starts (`parse_jobs.py` 141), or when the document goes |
| Parse job | SQLite `jobs`, kind `parse` | uuid4 | `document_id`, cascade | primary key, `jobs_document` index | With its document |
| Analysis job | SQLite `jobs`, kind `analysis`, with progress columns | uuid4, and a unique `analysis_id` | `document_id`, cascade | primary key, the `analysis_id` index | With its document. A new analysis does not remove the old row |
| Analysis record and result | RAM, `doc.analysis` (`store.py` 88 to 96) | analysis id | job id | via the document | Replaced by the next analysis (`store.py` 344 to 346), or with the document |
| Queue item (analysis) | RAM, `AnalysisQueue._items` and the FIFO (`analysis_jobs.py`) | job id | a reference to the parsed document, the category ids | dict by job id | The worker pops it after the run. A stopped waiting job now leaves at once (SA1) |
| Catalogue, analyzer | RAM, loaded once (`main.py` 114 to 119, `analysis_jobs.py` `_work`) | none | none | none | Process end |

Duplicated state, each kept in step by construction and never read from two places at once:

- `documents.expires_at` is a copy of the session's (`store.py` 228, 237). Both are fixed at creation, so they cannot drift.
- `media_type` and `byte_count` sit in SQLite and in the RAM record.
- The document's `status` mirrors the parse job's outcome (`store.py` 312).
- The analysis id and job id sit in `AnalysisRecord` and in the `jobs` row.

### 1.2 The 10,000 daily users simulation

The caps are real: 25 sessions, 5 documents each, one replica, a parse queue of 1 running and 2 waiting, an analysis queue of 1 running and 2 waiting, a 60 minute fixed lifetime and 4 GiB.

Inputs, each with its label.

| Input | Value | Label |
|---|---|---|
| Daily users | 10,000, and 100 and 1,000 for comparison | given |
| Share of the day's users who arrive in the peak hour | 15 percent | [E] assumption, no traffic data exists |
| What a user does | One visit, one upload, one analysis of 3 categories | [E] assumption |
| Parse time, a 14 to 44 page PDF | 1.1 to 4.7 s. A DOCX 0.49 to 0.53 s. The densest file 22.7 s | [M] `BuildLog.md` 2-C, laptop |
| Windows read for one category of a 33 page contract | 53.3 (2,185 windows over 41 categories) | [M] `API.md` section 8, 2-D.1 |
| Time for one window | 0.34 to 0.51 s | [M] 2-D.1, laptop with 8 threads |
| Analysis of 3 categories, laptop | 3 x 53.3 x 0.34 to 0.51 = 54 to 82 s | [E] from the two lines above. The slowest analysis measured was 80.4 s (`config.py` line 43) |
| Analysis of 3 categories, Azure at 2 vCPU | 108 to 326 s | [E] laptop time x k, with k between 2 and 4. Linear scaling from 8 threads to 2 would give 4, and 2 is a guess for less than linear. Unmeasured, and 4-C measures it |
| Analysis of all 41 categories, laptop | 804 to 1,123 s | [M] 2-D.1 |

**Arrivals.** 10,000 x 0.15 / 60 = 25 arrivals a minute in the peak hour, 1,500 an hour. For 1,000 users the figure is 2.5 a minute, and for 100 it is 0.25.

**The session cap is the first limit to break.** A session holds its slot for its full 60 minutes whether or not the user is still there, and nothing in the frontend ends it (SA3: no `DELETE /sessions/current` call exists in `frontend/src`, and `ApiClient` has no method for it). By Little's law the sessions a peak hour needs at once are arrivals x lifetime = 25 a minute x 60 minutes = 1,500. The cap is 25. The cap fills after 25 / 25 = 1 minute of peak. After that a slot opens only when an earlier session expires, so the app admits at most 25 new sessions in any rolling hour. At the peak that is 25 / 1,500 = 1.7 percent of arrivals. Over a day it is at most 25 x 24 = 600 sessions, which is 6 percent of 10,000 users, if arrivals spread evenly.

| Daily users | Peak-hour arrivals | Sessions needed at once | Admitted in the peak hour | Admitted in a day, at most |
|---|---|---|---|---|
| 100 | 15 | 15 (cap not reached) | 100 percent | all 100 |
| 1,000 | 150 | 150 | 25, so 17 percent | 600, so 60 percent |
| 10,000 | 1,500 | 1,500 | 25, so 1.7 percent | 600, so 6 percent |

All three rows are [E], from the two assumptions above. `SESSION_LIMIT` starts where arrivals in an hour pass 25, which is 25 / 0.15 = 167 daily users at the assumed peak share, or any class of 26 people who arrive together.

**`QUEUE_FULL` comes next, and only on bursts.** At most 25 uploads an hour are admitted, which is 0.42 a minute. A parse takes about 4 s [M, 33 to 44 page files], so the parse worker is busy 0.42 / 60 x 4 = 2.8 percent of the time [E]. Four uploads in flight at once, or 3 parses waiting, is rare for spread arrivals and certain for a class of 25 that all press Upload together.

**`ANALYSIS_QUEUE_FULL` is the real bottleneck.** Admitted analyses arrive at 25 an hour. The single worker's busy share is 25 / 3,600 x T, where T is the time for one analysis.

| T | Busy share of the worker | Worst wait for the third place (3 x T) |
|---|---|---|
| 54 to 82 s (laptop) | 0.38 to 0.57 | 162 to 246 s |
| 108 to 326 s (Azure estimate) | 0.75 to 2.26 | 324 to 978 s |

All values [E]. Above 1.0 (T above 3,600 / 25 = 144 s) the queue cannot keep up, the three places stay full and every further start gets `ANALYSIS_QUEUE_FULL`. The Azure estimate for T runs from 108 to 326 s, so a 3 category review of a 33 page contract is at the edge, and a 41 category review (27 to 75 minutes at k of 2 to 4, against the 30 minute limit) is likely to end `timed_out` (R6, owner 4-C).

**Memory is not the limit.** With the UI, a session keeps one document (a replaced file is deleted first, `useStartFlow.ts` lines 78 to 89). 25 documents at the largest smoke-set size (1.93 MiB [M]) are 48 MiB [E]. An attacker can reach 125 documents at 11.5 MiB, which is 1.4 GiB [M] and is R22.

### 1.3 Structural weaknesses

| Weakness | Evidence | What it costs |
|---|---|---|
| One lock guards SQLite and the RAM dict | `store.py` 150. Every route takes it, several times | Fine at a few hundred requests a second [E, unmeasured]. It is the single point every request queues on |
| The store lock is held across a wait for a killed child (B1) | `store.py` 246 to 257 and 448 to 462 call `on_drop`, which calls `ParseQueue.kill_documents`, which waits up to 5 s per child (`parse_jobs.py` 87 to 99) | A delete, a session delete, an expiry on access or a sweep can hold every store caller for up to 5 s. A killed child normally exits in milliseconds [E, not timed on Linux] |
| Async handlers take the store lock on the event loop | `create_session` and `delete_current_session` (`routes.py` 171 to 193), `ready` (`routes.py` 141 to 153) and the sweep (`main.py` 32 to 39) are `async def` and call the store directly | While a thread holds the lock, these block the whole event loop, `/health` included. This is R19, still accepted. The audit adds the four call sites. A single 5 s stall fails one liveness probe of the three it takes to restart (timeout 5 s, 3 failures) |
| Write amplification is small | `set_progress` is one UPDATE and one commit per progress event (`store.py` 371 to 378). The real model reports one event per window, so 1 / 0.34 to 1 / 0.51 = 2.0 to 2.9 a second [E] | A `:memory:` commit writes no file. The cost of one was not measured |
| The document read is recomputed every time | `read_document` runs `to_json` and a bisect for each node on each call (`routes.py` 76 to 86, 282 to 298) | Up to 20,000 blocks plus nodes. Cost not measured. The Reader reads it once per page load |
| Job rows are never pruned | `add_analysis_job` inserts a row and keeps the old ones (`store.py` 337 to 347, and API.md section 3 says "the old job stays readable") | One row about 300 bytes [E: record about 170 bytes plus three index entries of about 45 bytes each]. A start and cancel loop of 100 rounds a second for an hour adds 360,000 rows, about 110 MB [E]. Bounded by the 60 minute lifetime and the request rate, not by a limit (SA6) |
| A stopped waiting analysis stayed in the queue with its ids | Before this audit, `cancel` and `cancel_documents` only set flags. The item stayed in `_items` and the FIFO until the worker reached it, which can be 1,800 s away, and `submit` counted all of `_items` on each call | One round left the 46 category ids (about 4.1 KB [E]) and made `submit` slower. Fixed (SA1, section 1.4) |
| Slots free only by time | The sweep reclaims on expiry. The frontend never calls the session delete | SA3. The cause of the 25 users an hour ceiling |
| `SQLite` stays in `:memory:` | `config.py` default | Freed pages go back to SQLite's free list and not to the system. This is SQLite behaviour and was not tested here |

### 1.4 Fixed in this audit: SA1

`AnalysisQueue` kept a stopped job that was still waiting in `_items` with its category ids, until the single worker reached it. A client could hold the worker with one long analysis (up to 1,800 s) in one session and loop start and cancel in a second session. Each round cost the server about 4.1 KB [E: 46 ids x about 75 bytes each, plus the tuple]. `submit` also summed over every entry in `_items` on every call, so the loop slowed itself and the store lock behind it, because `cancel_documents` runs under that lock. At 100 rounds a second for 1,800 s the retained ids come to about 0.74 GB [E], on top of about 1.0 GiB at rest [M].

The fix is `_forget` in `backend/app/services/analysis_jobs.py`: a stopped job that has not started leaves `_items` and drops its ids at once, and stays in the FIFO as a bare marker (about 110 bytes [E]) until the worker reaches it. A job that is running is left alone, because the worker still reads it. Red run: `test_stopped_waiting_jobs_do_not_pile_up_while_the_worker_is_busy` failed in both cases with `assert 21 == 1`. Green: 131 passed across the four analysis test files. One existing test (`test_a_delete_between_the_insert_and_the_queue_leaves_no_text_on_the_item`) read the item from `_items` after the read-back, so it now captures the item at submit and also asserts that the job has left the lookup. This needs a new image and a deploy.

### 1.5 The persistent schema a later version would need

Paper only. It is **not built and not planned for the demo.** The demo keeps no accounts and no history on purpose. This sketch exists so that the memory-only choices are not mistaken for the only design.

| Table | Columns that matter | Keys and indexes | Retention |
|---|---|---|---|
| `accounts` | id, email_hash, created_at, deleted_at | primary key, unique on email_hash | Deleted account rows keep an id and a date only |
| `auth_sessions` | id, account_id, token_hash, expires_at, revoked_at | foreign key to accounts, unique on token_hash, index on (account_id, expires_at) | Expired rows swept daily |
| `documents` | id, account_id, sha256, media_type, byte_count, filename, status, created_at, retain_until | foreign key to accounts, index on (account_id, created_at desc), index on retain_until | The file and text go at `retain_until` or on user delete. The row keeps the hash and a deleted date |
| `document_texts` | document_id, text_sha256, parser_version, source_text (encrypted), blocks, nodes | primary key document_id, foreign key to documents | Deleted with the document. Kept apart so a metadata read never loads text |
| `parse_jobs` and `analysis_jobs` | id, document_id, status, error, stage, units, timings | foreign key to documents, index on (status, created_at) for the queue | 90 days, then aggregated |
| `analyses` | id, document_id, text_sha256, artifact_manifest_sha256, contract_version, jurisdiction_scope, status, created_at, finished_at | foreign key to documents, index on (document_id, created_at desc) | With the document |
| `analysis_categories` | analysis_id, category_id, status, search_complete, windows_done, windows_total | primary key (analysis_id, category_id) | With the analysis |
| `findings` | id, analysis_id, category_id, span_start, span_end, status, confidence, origin | foreign key to analysis_categories, index on (analysis_id, category_id) | With the analysis. The quoted text is re-read from `document_texts`, never copied |
| `party_bindings` | document_id, role, party_node_id, selected_start, selected_end | primary key document_id | With the document |
| `audit_events` | id, account_id, kind, at, request_id | index on (account_id, at) | 12 months, ids only, no contract text |

Rules for it: every foreign key cascades or is checked on delete, text and findings carry the document's retention date, and no table holds contract text outside `document_texts`.

### 1.6 Jury, round 1

| Juror | Pushed on | New |
|---|---|---|
| Contrarian | "RAM only is the right model for a demo, so what is the weakness?" RAM is not the weakness. A timer is: 25 slots and a 60 minute lifetime that no user action can shorten give 25 users an hour. | SA3 |
| First-Principles engineer | What must be capped is memory and CPU, and a session count is a poor stand-in for either. The same RAM could serve 60 sessions of 2 documents (120 documents, under today's 125). | SA3, design note |
| Attacker | Start and cancel in a loop while another session holds the worker (SA1, fixed). Dead items hold the 2 parse places until the worker reaches them. Job rows pile up (SA6). | SA1, SA5, SA6 |
| SRE | No signal shows "24 of 25 sessions used". `/ready` reports the analyzer, the catalogue, the sweep and the database and says nothing about capacity (SA19). The async handlers and the sweep take the lock on the event loop (SA7). | SA7, SA19 |
| Cost owner | A refused visit still wakes the replica. The cap protects memory and does not save money (section 4). | cross-reference |

### 1.7 Jury, round 2 (after adding SA1, SA3, SA5, SA6, SA7 and SA19)

The Contrarian asked whether SQLite earns its place: it holds 25 rows and a second lock-free read path would do. It earns nothing at demo size, and it carries the schema for later, so it stays. The First-Principles engineer found no state held in two places that is read from both. The Attacker looked for another unbounded structure: the parse queue is bounded (`queue.Queue(maxsize=2)` and `_items` popped in `finally`, `parse_jobs.py` 54, 122 to 125), the store is bounded by the caps, and the log keeps class names only. The SRE found nothing new. The Cost owner found nothing new. **Nothing new, so the section is done.**

### 1.8 Verdict

The data model fits one replica and one process, and it is honest about it: nothing durable, everything dies with the process or the clock. It stops serving new users at 25 an hour by design, and no user action can free a slot early. One structural defect was small enough to fix now (SA1). Capacity (SA3), the job-row growth (SA6, accepted) and the event-loop calls (SA7) are recorded.

## 2. Security blind-spot audit

Severity is High, Medium or Low for the live demo as it stands. Status is **handled**, **fix now** or **record**, and an accepted risk says what bounds it.

### 2.1 Session and authentication

| Risk | How it would be used on the live demo | Evidence | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| Guessing a token | Try tokens against any route that needs a session | `secrets.token_urlsafe(32)` gives 256 bits (`store.py` 173). Only the SHA-256 is stored and looked up (`store.py` 136 to 137, 190 to 202) | Low | None needed | Handled |
| A long-lived token | Steal one and keep using it | The lifetime is fixed at creation, at most 60 minutes, and nothing renews it (`store.py` 181 to 182, `config.py` 19). Only the session delete ends it sooner | Low | None needed | Handled |
| Where the browser keeps the token | Read it from storage with a script | React memory only (`session.tsx` 7 to 8, 40). A search of `frontend/src` finds no `localStorage`, `sessionStorage`, `indexedDB` or cookie code. It travels in the `Authorization` header and never in a URL | Low | A reload drops it. The server session lives on for up to 60 minutes (SA3) | Handled, capacity cost in SA3 |
| Reading another session's document or job by guessing an id | Send another session's id to any id route | Ids are uuid4 (`store.py` 182, 227, 265, 337). All six routes that take an id are listed below, and each checks the owner in the store. A stranger gets the same 404 as an unknown id | Low | None needed | Handled |
| After expiry or delete | Use a stale token or id | The bearer check fails first and drops an expired session (`store.py` 190 to 202). A delete removes the RAM record and cascades the rows (`store.py` 253 to 257). Data of an expired session lingers at most one sweep, 30 s, and is unreachable meanwhile | Low | None needed | Handled |
| Creating sessions from other people's browsers | A web page runs `fetch` with POST to `/api/v1/sessions`. This is a simple request, so it needs no preflight and the browser sends it. The page cannot read the reply, and the session is made anyway. The attacker's address never appears | `routes.py` 171 to 183, no Origin check, no CORS middleware (`main.py`) | Medium | A same-origin check on this one route, or a limit per address at the ingress | Record (SA5) |

The six routes that take an id:

| Route | Where the id is checked | Test that shows a stranger gets 404 |
|---|---|---|
| `GET /documents/{id}` | `routes.py` 287, `store.py` 240 to 244 | `test_another_sessions_document_and_job_are_404_never_403` (`tests/test_documents_api.py` 494) |
| `DELETE /documents/{id}` | `routes.py` 310, `store.py` 246 to 257 | the same test, which also checks that nothing was deleted |
| `GET /jobs/{id}` | `routes.py` 337, `store.py` 274 to 283 | the same test, and the next one |
| `POST /jobs/{id}/cancel` | `routes.py` 353 reads the job through the owner check and only then calls the queue | `test_another_sessions_ids_give_404_on_every_analysis_route` (`tests/test_analyses_api.py` 548), which also checks that the stranger changed nothing |
| `POST /documents/{id}/analyses` | `routes.py` 391, and `store.py` 324 to 328 checks again inside its critical section | the same test |
| `GET /analyses/{id}` | `routes.py` 435, `store.py` 349 to 369 | the same test |

### 2.2 Rate abuse

| Risk | How it would be used | Evidence | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| One client fills the 25 sessions | 25 `POST /sessions` calls. Every other visitor gets `SESSION_LIMIT` for up to an hour | `store.py` 171 to 180. The cap is global and not per client. The ingress gives no rate limit by default: the ingress page lists IP restrictions and says nothing of rate limits [C, `learn.microsoft.com/en-us/azure/container-apps/ingress-overview`, read 11 November 2026] | High for the demo's availability | A limit per address needs the client's address, and the app never reads it. uvicorn takes it from `X-Forwarded-For` only when the direct peer is in `forwarded_allow_ips`, which defaults to `127.0.0.1` and `::1` [C, `uvicorn/config.py` 361 to 363 in the installed 0.54.0, read 11 November 2026]. The Dockerfile does not set it, and whether the ingress peer is on that list was not checked. The ingress can block an address by hand | Accepted, R5 (see SA5, which widens it) |
| One client holds every upload place | Four slow uploads hold the 4 in-flight places. The ingress ends each at 240 s [C, ingress page] and the client reconnects | `config.py` 33, `routes.py` 223 to 229 | Medium | A body read timeout in a proxy | Accepted, R2, bounded by 240 s per connection but perpetual if the client reconnects (SA5) |
| One client holds the parse queue | Upload a slow file, then upload and delete files to fill the 2 waiting places. A deleted item keeps its place until the worker reaches it | `parse_jobs.py` 54, 87 to 99 | Medium | Per-client limits | Record (SA5) |
| One client holds the analysis worker and queue | Three sessions: one runs a 41 category review for up to 1,800 s, two fill the waiting places. Everyone else gets `ANALYSIS_QUEUE_FULL` | `config.py` 45 to 46, `store.py` 329 to 336 (one active analysis per session, not per client) | Medium to High | Per-client limits, a smaller time limit | Record (SA5) |
| Start and cancel in a loop | See section 1.4 | `analysis_jobs.py` | Medium | `_forget` | **Fixed (SA1)** |
| Flooding public routes | `GET /ready` and `POST /sessions` need no token. `/ready` takes the store lock | `routes.py` 141 to 153 | Medium | A rate limit at a proxy | Record (SA5) |

### 2.3 Upload attacks

| Risk | How it would be used | Evidence | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| A DOCX that inflates (zip bomb) | Upload a ZIP whose members decompress to gigabytes | Member names and methods are checked first, then each member is read in 64 KiB steps against 100 MiB in total (`docx.py` 369 to 401). A 100 MiB part would need about 2.5 GiB [M, extrapolated, `BuildLog.md` 2-C], and the child is ended at 95 percent of its 1,536 MiB cap and at 120 s | Low | The child process | Handled |
| A PDF whose content decodes to a huge size | A 16 KB file that decodes to 16 MB | 8 MiB decoded budget, 100 pages (`errors.py` 6, 9). The slowest dense file took 22.7 s [M] against a 120 s kill | Low | The budget and the kill | Handled |
| Deeply nested XML, entity expansion | A DOCX part with a DOCTYPE and nested entities | A part with a DOCTYPE is refused as `MALFORMED_FILE` (`docx.py` 416 to 422). Parsing runs in the child | Low | The child's cap | Handled |
| Huge single parts (B3, B5) | One 100,000 paragraph part | B5 is bounded to 100,000 paragraphs and 500,000 characters (`errors.py` 7, 10), 4.04 s and 191 MiB at the limit [M, `BuildLog.md` 1-R]. B3 has no library bound and rests on the cap and the kill (`BuildLog.md` 1-R step 1) | Low | The child's cap and kill | Handled by containment. The Linux cap has run once, in the CI smoke test (SA15) |
| Malformed files, a wrong extension or content type | Rename a text file `.pdf`, or send a lying `Content-Type` | The type comes from the bytes and the header is ignored (`detect.py` 17 to 33, `routes.py` 244 to 251). A macro-enabled file (`word/vbaProject.bin`) is refused | Low | None needed | Handled |
| Zip slip | A member named `../x` or `C:\x` | These names give `ARCHIVE_UNSAFE`, and nothing is extracted to disk (`docx.py` 369 to 373, 376 to 401) | Low | None needed | Handled |
| A ZIP with a huge central directory | A 9 MiB ZIP with 200,000 entries is listed in the API process | `detect.py` 23 to 24. 0.87 s and 75 MiB [M, `API.md` section 9]. Four uploads in flight bound it to 300 MiB [E: 4 x 75] | Low | The 4 upload cap | Accepted, documented |

### 2.4 Injection and rendering

| Risk | How it would be used | Evidence | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| Contract text rendered as HTML | A contract with `<script>` text | A search of `frontend/src` for `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function` and `srcdoc` finds nothing outside tests. Text, party names and the file name are React text children. The one navigation sink, `window.open(sourceUrl)`, runs only for an `https:` address and carries `noopener,noreferrer` (`lib/reader.ts` 43 to 50, `JudgmentCard.tsx` 171) | Low | None needed | Handled |
| File name tricks | A name with path parts, control characters, `U+202E` | The name is reduced to the text after the last separator, with every control, format, private-use and separator character removed, cut at 255 characters (`routes.py` 89 to 107). It lives in RAM and is shown as text | Low | None needed | Handled |
| Header injection | A name with a line break placed in a response header | No response header carries the name or any request input. The only reflected headers are fixed (`WWW-Authenticate`, `Allow`) | Low | None needed | Handled |
| Log injection | A path or name with a line break | The app logs class names only (`main.py` 39, `errors.py` 132, `parse_jobs.py` 120). uvicorn percent-encodes the path in its access line (`uvicorn/protocols/utils.py` 59). Access lines hold document and job ids and the peer address | Low | None needed | Handled |
| Path traversal in the static files | `GET /..%2f..%2fetc/passwd` | `CLAUSEANCHOR_FRONTEND_DIST` is set by the operator in the image. Starlette resolves the real path and compares it with `commonpath` (`starlette/staticfiles.py` 160 to 172), with symlinks off. Paths under `/api` never reach the files (`main.py` 75 to 80) | Low | None needed | Handled |

### 2.5 Data exposure

| Risk | How it would be used | Evidence | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| Error bodies leak input or exception text | Send bad input and read the reply | One fixed envelope with a fixed message for each code. The validation error names no field and echoes nothing. A crash is caught in the middleware and logs the class name (`errors.py` 106 to 133) | Low | None needed | Handled |
| Cached contract text | A shared proxy or the browser keeps a reply | `Cache-Control: no-store` on every reply except hashed files under `/assets/` (`errors.py` 134 to 138) | Low | None needed | Handled |
| Missing security headers | Embed the page in a frame, or sniff a type | The only header the app sets is `Cache-Control`. There is no `X-Content-Type-Options`, no `X-Frame-Options` or CSP `frame-ancestors`, no CSP, and the referrer policy is a meta tag only (`index.html`). TLS ends at the ingress, which redirects port 80 to 443 [C, ingress page] | Low. User text is never served as a page, and the token lives in memory | `X-Content-Type-Options: nosniff`, `frame-ancestors 'none'` and `Referrer-Policy: no-referrer` are safe: `dist` holds only html, js, css, svg and woff2 [M, 35 files], so a wrong type cannot block an asset the smoke test does not already check. Not added, because no browser may run for this audit and a header set that no browser has seen can break the page | Record, owner 4-R (already there since 4-B) |
| A stale document after delete | Read a document after `DELETE` | The RAM record is removed first (`store.py` 253, 457 to 459) | Low | None needed | Handled |
| A public process holds everyone's contracts | Any flaw that reads process memory shows every user's text | One process and one container hold all sessions. The app's own pages say the contract is processed in memory and deleted within 60 minutes (`Landing.tsx` 25, 207, `Start.tsx` 157), and none says that this is a public demo for sample contracts. `Deploy.md` step 10 tells Aryan to say so to visitors. The sample contract is not available in this build, so a visitor has nothing else to upload | Medium, a decision and not a bug | One sentence on the Start and Landing pages: this is a public demo, use a sample contract | Record (SA16). Not changed here, because the copy is Aryan's call |
| Logs | An operator reads contract text in the logs | Logs hold class names, access lines and no body. Destination none, so nothing is stored | Low | None needed | Handled |

### 2.6 Client-side trust

| What the backend takes from the client | How it is checked | Evidence | Status |
|---|---|---|---|
| Category ids | Required, 1 to 100 ids of at most 64 characters, no repeats, each one in the catalogue, unknown fields refused | `schemas.py` 104 to 112, `routes.py` 402 to 405 | Handled |
| Jurisdiction scope | A literal of two values | `schemas.py` 112 | Handled |
| Upload size | Counted from the stream. `Content-Length` is only a shortcut | `routes.py` 110 to 120, 233 to 243 | Handled |
| File type, file name | Read from the bytes, and cleaned | `detect.py`, `routes.py` 89 to 107 | Handled |
| Role and party | No route takes them yet (3-A) | `Phases.md` 3-A | Nothing to check |
| Limits | All are server constants, none comes from the client | `config.py` | Handled |

### 2.7 Supply chain

| Risk | Evidence | Severity | Status |
|---|---|---|---|
| The one action is pinned by a tag, not a commit | `actions/checkout@v7.0.1` (`image.yml` 31). A tag can move. The tag's commit, `3d3c42e5aac5ba805825da76410c181273ba90b1`, is in `BuildLog.md` (4-B close). Permissions are `contents: read` and `packages: write`, and `persist-credentials` is false | Low | Record, 4-R |
| Base images float | `node:22-slim` and `python:3.12-slim` (`Dockerfile` 6, 16) have no digest. A rebuild takes whatever the tag points to | Low to Medium | Record, 4-R |
| Installs without hashes | `pip install -r ... -c constraints.txt` (`Dockerfile` 28 to 35) uses 41 exact pins and no `--require-hashes`. torch 2.9.1 comes from the official CPU index by version only. pnpm 10.34.3 is pinned by version | Low to Medium | Record, 4-R |
| Known advisories on the model stack | torch 2.9.1 and transformers 4.57.6 had advisory records at 2-R (R12). `pip-audit` was not re-run in this audit: nothing may be installed and the database is online | Medium | Unchanged, R12, owner Tanishq then 4-A |
| The model file | The zip's SHA-256 is checked in CI (`image.yml` 43). The core checks the manifest digest again at build (`Dockerfile` 61 to 63) and at start (`Dockerfile` 51). The weights are `.safetensors`, so no pickle is loaded | Low | Handled. The digests sit in the repository, so write access to the repository is the trust anchor |
| The public image holds the weights | `Deploy.md` step 2.7 asks Aryan to confirm with Tanishq that the model may be public. The record does not show the answer | Medium, a licence matter | Aryan to confirm (section 8) |
| The parse child shares the API's user and environment | R14 | Low here | Accepted, R14, unchanged |

### 2.8 Jury, round 1

| Juror | Pushed on | New |
|---|---|---|
| Attacker | Drive-by session creation from visitors' browsers (SA5). Start and cancel loop (SA1). Flooding `/ready`, which takes the store lock. The three-session hold on the analysis worker. | SA1, SA5 |
| Contrarian | "Is nosniff worth a deploy?" Not alone. It belongs with the other headers in one change, after a browser has seen them. | none |
| First-Principles engineer | The thing that must never leak is the contract text. It sits in the memory of one process that every user shares, so a flaw in a framework reads every user's text. The control is the warning to use sample contracts, and the app does not show it. | SA16 |
| SRE | Under an attack nothing shows: logs are not stored and there is no counter of refused requests (SA19). | SA19 |
| Cost owner | An attacker who sends one request every four minutes keeps the replica awake at about USD 5.18 a day (section 4). No per-address limit exists, and the budget alert is an email. | cross-reference |

### 2.9 Jury, round 2

The Attacker looked at every route for a new loop. `PATCH` and `PUT` do not exist, the JSON body is capped at 64 KiB, and a failed bearer check costs one SHA-256 and one lock acquisition. Nothing new. The First-Principles engineer asked whether the Linux memory cap could be bypassed: the cap is `RLIMIT_AS` set in `preexec_fn` (`memcap.py` 124 to 136) and it ran once, in the CI smoke test. That is SA15, already in the list. The SRE and the Cost owner found nothing new. **Nothing new, so the section is done.**

### 2.10 Verdict

No exploit that reads another user's data was found, and every id route checks its owner. The defences against hostile files hold by containment: a hostile file can cost time and memory in a child that the API kills. The gaps are availability, not confidentiality: one client can take every shared pool (SA5), and that is a cost of having no identity behind the proxy. One defect was fixed (SA1). Headers, supply-chain pins, the public image licence and the missing "sample contracts only" line are recorded (SA8, SA9, SA16).

## 3. Vendor lock-in and migration

The app has no platform code. A search of `backend/app` and `frontend/src` for `azure`, `ghcr`, `containerapp`, `X-Forwarded` and `github.com` finds nothing. It listens on `0.0.0.0:8000`, reads 9 `CLAUSEANCHOR_` variables and 4 runtime variables (`OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `MALLOC_ARENA_MAX`, `HF_HUB_OFFLINE`), and exposes `/api/v1/health` and `/api/v1/ready`. Almost no state would have to move: sessions, documents and results live in RAM for at most 60 minutes and cannot be migrated. A move needs no export.

| Piece | What is hard to replace at 100,000 users | What state moves | Limit that hurts first | Cost of moving [E] |
|---|---|---|---|---|
| Azure Container Apps, Express | The 63 line spec (`deploy/azure-containerapp.yaml`) is an Azure resource schema. The probes, the scale rule and the ingress setting all have equivalents elsewhere. Express has no custom domain, no multiple revisions, no traffic splitting and no custom scalers [C, `learn.microsoft.com/en-us/azure/container-apps/express-overview`, read 11 November 2026] | None | The one replica, which is the app's state and not Azure's choice: Express allows 30 replicas [C, quotas page], and the app can use 1. The ingress ends a request at 240 s [C, ingress page] | One working day, about 4 to 8 hours: translate the spec, point DNS, run `smoke_test.py` against the new address. The smoke script already takes a URL (`image.yml` 65) |
| GitHub Container Registry | The image string appears in the spec and in the workflow's two tags. Any registry takes an OCI image | None. 1,671 MiB of image | Storage and bandwidth for a public package are free, and GitHub promises a month's notice of a change [C, `docs.github.com/en/billing/concepts/product-billing/github-packages`]. No pull rate limit is on that page | About 1 hour: change the push target and the image name |
| GitHub Actions | `image.yml` (80 lines) uses `gh release download`, `github.token`, `$GITHUB_STEP_SUMMARY` and the `ubuntu-24.04` runner. The build itself is plain `docker build` | None | Standard runners are free for public repositories [C, `docs.github.com/en/billing/concepts/product-billing/github-actions`] | About half a day to rewrite 80 lines for another CI |
| The GitHub release that holds the model | The CI downloads the zip from release `model-v0` at build time only, and checks its SHA-256 (`image.yml` 42 to 43). It is not on the request path | None | A release asset must be under 2 GiB, with no limit on bandwidth [C, `docs.github.com/en/repositories/releasing-projects-on-github/about-releases`]. The zip is 509,869,238 bytes, 24 percent of the limit [E: 509,869,238 / 2,147,483,648]. A larger retrained model would still fit | About 1 hour: upload the zip to any bucket and change one download line. The image already holds the weights |
| The Hugging Face model format | `.safetensors` weights and a tokenizer, loaded by `transformers` 4.57.6 and torch 2.9.1 with `HF_HUB_OFFLINE=1` (`Dockerfile` 28 to 29, 57). The Hub is never called at run time | None | The stack's advisories (R12), not the format. The planned ONNX export has no effect on hosting | None to host elsewhere |
| Azure CLI and the YAML spec | `Deploy.md` is written for Cloud Shell. Nothing in the app depends on `az` | None | None | The guide is rewritten for the new host |

**Keep doing, to stay portable.** One OCI image. Configuration through environment variables only. No platform SDK in the app. The 8000 port and the two health paths. The smoke test as the gate before a publish.

**What already breaks portability.**

1. State lives in one process, so a move to any host keeps the one-replica limit until state leaves the process (section 6).
2. `memcap.py` is platform code: a Windows job object and `Popen._handle` (`memcap.py` 99 to 122) and `RLIMIT_AS` with `preexec_fn` on Linux (`memcap.py` 124 to 136). It is documented and isolated in one file.
3. `OMP_NUM_THREADS=2` and `MKL_NUM_THREADS=2` are tied to the vCPU count (`Dockerfile` 54 to 55).
4. The model digest is written twice, in `Dockerfile` line 51 and in `image.yml` line 19, and they are two different digests (the zip's and the manifest's).
5. Two accepted risks lean on Azure's numbers: R2 on the 240 s ingress timeout, and the cost model on the 300 s cool-down and the per-second rates (section 4).
6. The claim "no environment fee" in `Deploy.md` is from the brief and was not found on the Express page. Section 4 has the detail.

### 3.1 Jury, round 1

| Juror | Pushed on | New |
|---|---|---|
| Contrarian | "Lock-in is a non-issue with no data and no SDK." The vendor lock is low, and the architecture (one process) limits every host. | SA14 |
| First-Principles engineer | The vendor gives the app TLS, a 240 s timeout, a probe loop that restarts a failed container and scale to zero. The app relies on each. A new host must reproduce them. The app does not read the client address, so a limit per address would need that from the host too. | SA14 |
| Attacker | A moved deployment loses the ingress's IP restrictions and the one environment. Nothing in the app limits a client. | cross-reference SA5 |
| SRE | The image tag by SHA is the only rollback. There is no previous-revision traffic split in Express [C]. A bad deploy ends every session and has no quick way back except a new update by the old SHA. | SA14 |
| Cost owner | The credit and the grant are Azure-only. A move to another host loses the free grant and gets a different price model. | cross-reference |

### 3.2 Jury, round 2

The Contrarian and the First-Principles engineer asked whether the weights in a public GHCR package create a second dependency on GitHub staying public. They do, and the answer is the same as for the release: the image is the copy. The Attacker, SRE and Cost owner found nothing new. **Nothing new, so the section is done.**

### 3.3 Verdict

Low lock-in. A move costs about one working day [E] and no data. The design choices to protect are the single image, environment-only configuration and the absence of a platform SDK. The architecture, one process holding all state, would limit any host.

## 4. Cost explosion simulation

### 4.1 Prices and limits, with their sources

| Fact | Value | Source |
|---|---|---|
| vCPU, active | USD 0.000024 a second | [C] Microsoft's retail price API, Azure Container Apps, Central India, standard rows, effective 2022-06-01, read 11 November 2026 (`prices.azure.com/api/retail/prices`) |
| vCPU, idle | USD 0.000003 a second | [C] same |
| Memory, active and idle | USD 0.000003 a GiB-second, both | [C] same |
| Requests | USD 0.40 a million | [C] same |
| Free grant, every month and subscription | 180,000 vCPU-seconds, 360,000 GiB-seconds, 2 million requests | [C] `learn.microsoft.com/en-us/azure/container-apps/billing` (ms.date 2025-12-09), and the India pricing page |
| Idle rate applies when | The revision has a minimum replica count above zero, is at that count, and the replica is processing no request, uses under 0.01 vCPU and receives under 1,000 bytes a second. Starting up and processing requests are active | [C] billing page |
| Scale to zero | A revision at zero replicas costs nothing. The cool-down before the last replica goes to zero is 300 s by default. The page does not say whether HTTP rules use it | [C] `learn.microsoft.com/en-us/azure/container-apps/scale-app` (ms.date 2026-05-19) |
| Express billing | "Express and Sandboxes follow the same pay-per-second pricing as Consumption Plan." No Express price or grant is listed | [C] India pricing page |
| Environment meters | Three rows, "Environment Management Hour", "Environment Planned Maintenance Hour" and "Environment Private Endpoint", at USD 0.10 an hour each, effective 2026-11-01. Which plan they apply to is not stated | [C] retail price API, 16 rows returned |
| Egress, probe requests | Not priced on the pages read | [C] billing page |
| The 10 request scale rule with a maximum of 1 | Not described. The rule adds replicas up to the maximum, and the maximum here is 1 | [C] scale page |
| Azure for Students | USD 100, valid one year, no card, renewable each year while a student. When it runs out, "your subscription and products will be disabled" | [C] `azure.microsoft.com/en-in/free/students/` and the Learn page (updated 2026-08-03) |
| Budget | `clauseanchor`, monthly, INR 850 (about USD 10), email at 80 percent of actual cost | `Deploy.md` step 9 |
| GHCR | Free for a public package | [C] GitHub packages billing page |

At 2 vCPU and 4 GiB, the replica costs, per second, 2 x 0.000024 + 4 x 0.000003 = USD 0.000060 when active, which is **USD 0.216 an hour** [E: x 3,600]. The vCPU is 80 percent of that (0.1728) and the memory 20 percent (0.0432). When idle it costs 2 x 0.000003 + 4 x 0.000003 = 0.000018 a second, **USD 0.0648 an hour** [E]. The free grant is 180,000 / (2 x 3,600) = 25.0 hours and 360,000 / (4 x 3,600) = 25.0 hours, both [E], worth 25 x 0.216 = USD 5.40.

### 4.2 The monthly cost at 100, 1,000 and 10,000 daily users

The meter that drives it is **vCPU-seconds**. With the minimum at 0 there is no idle billing, so every second a replica is up costs the active rate, and what matters is how many hours the replica stays awake.

Model [E]. Visits arrive at random times, at 1/24 of the day's count an hour. Each visit keeps the replica awake for T hours: the work (cold start, upload, parse, analysis) plus the cool-down. The share of time the replica is awake is 1 - exp(-visits an hour x T). Inputs: T = 0.2 hour (12 minutes: about 7 minutes of work and a 5 minute cool-down) and, as a check, T = 0.1. A month is 730 hours. A visit that the session cap refuses still wakes the replica, so refusals count as visits. Real traffic clusters, which would lower the figures.

| Daily users | Visits an hour | Awake share (T = 0.2) | Awake hours a month | Compute cost after the grant (T = 0.2) | Compute cost (T = 0.1) |
|---|---|---|---|---|---|
| 100 | 4.17 | 0.565 | 413 | (413 - 25) x 0.216 = **USD 83.7** | 249 h, **USD 48.4** |
| 1,000 | 41.7 | about 1.0 | 730 | (730 - 25) x 0.216 = **USD 152.3** | 719 h, USD 149.8 |
| 10,000 | 417 | about 1.0 | 730 | **USD 152.3** | USD 152.3 |

All values [E]. Three results follow.

- **The grant is crossed at about 4 daily users** [E: 730 x (1 - exp(-n/24 x 0.2)) = 25 gives n = 4.2], and at about 8 with T = 0.1. All three levels are far above it.
- **The cost has a ceiling.** One replica at most (`maxReplicas` 1) means no more than 730 hours: USD 152.3 a month [E], whatever the traffic. USD 100 of credit lasts about 100 / 152.3 x 30.4 = 20 days at the ceiling [E], and about 36 days at 100 daily users.
- **The sustainable load is small.** USD 100 over 12 months is about USD 8.3 a month. At T = 0.2 that is about 10 daily users (730 x (1 - exp(-0.0833)) = 58 hours, minus 25, times 0.216 = USD 7.2). This matches the INR 850 budget, which is the same order.

Requests. A full review sends about 180 to 960 requests [E: about 14 for the page and its files, 12 for the session, upload and parse polls at 450 ms, and 2 calls every 700 ms for 54 to 326 s of analysis]. The cap admits at most 600 sessions a day, so about 3.3 to 17.5 million requests a month, plus about 14 for every refused visit. At 10,000 daily users the 9,400 refused visits a day add about 4.0 million a month, so the total is 7.3 to 21.5 million, and (total - 2 million) x 0.40 is **USD 2 to 8** [E]. Requests are a minor meter.

Not priced. Outbound data. The page set is 839,824 bytes in 35 files [M, `frontend/dist`], with no compression in the app (`main.py` has no compression middleware) and fonts that are `no-store` (`errors.py` 134 to 138, 352,186 bytes of fonts [M]). A cold-cache visit downloads up to 0.84 MB [E]. 10,000 visits a day is 8.4 GB a day, about 250 GB a month [E]. The pages read give no egress price, so this stays a line to check in Cost Management (SA10). Fonts that are cached and a compressed response would cut it (SA11).

Minimum replicas at 1. If Express accepts the setting and the idle conditions hold, an idle replica costs 0.0648 x 730 = USD 47.3 a month [E], and each busy hour costs the active rate. Take 0.1 busy hour for each visit and no cool-down tail, because the replica stays up anyway. At 10 daily users that is 30.4 busy hours x 0.216 + 700 idle hours x 0.0648 = USD 52, or USD 46 after the grant, against USD 7 with scale to zero [E]. At 100 daily users it is 304 busy hours x 0.216 + 426 idle hours x 0.0648 = USD 93, or USD 88 after the grant, against USD 84 [E]. So from about 100 daily users a minimum of 1 costs about the same as scale to zero, and it stops the session loss of section 5. Express does not describe a minimum replica setting [C, Express page], so this is unverified on this app.

### 4.3 What spikes without warning

| Event | Cost [E] | Safeguard |
|---|---|---|
| Minimum replicas left at 1 after a demo | Idle 0.0648 x 24 = USD 1.56 a day, and up to USD 5.18 a day if it is busy. The whole month idle is USD 47.3 | Set it back to 0 straight after, and read it back (`Deploy.md` step 7). A calendar reminder |
| A bot or an uptime pinger | A request every 4 minutes, inside the 300 s cool-down, keeps the replica awake: 24 x 0.216 = USD 5.18 a day, USD 152 a month. The credit ends in about 20 days | No pinger on any app URL. An IP restriction for a known address. A lower budget. The alert is an email and it does not stop anything [E: budgets alert, and the pages read do not say otherwise] |
| One long analysis | At most 1,800 s of active time, 0.5 x 0.216 = USD 0.11 [E]. It holds the worker and barely moves the bill (SA5) | The time limit |
| A cold-start loop | A failed startup probe restarts the container after about 330 s (30 + 10 x 30). Starting up is billed at the active rate [C], so a loop costs USD 5.18 a day. A failed analyzer load stays `failed` and never recovers (`Architecture.md` section 2), so every restart would fail the same way | CI runs a smoke test and refuses to publish a bad image (`image.yml` 64 to 65). Update by SHA only. Watch the system log after an update |
| The GHCR pull on each cold start | Free for a public package [C]. It adds up to 1,671 MiB of pull time to each start [M, size], and that time is billed as active | None needed. 4-C times it |
| The Express environment meters | If the management meter applied, 0.10 x 730 = USD 73 a month [E], and the credit would last about 42 days. If all three applied, USD 219 a month and about 14 days. The private endpoint meter is unlikely to apply to this app | Look for an environment line in Cost Management now (SA10) |

At 80 percent of INR 850 (about USD 8 [E]) the alert fires after 8 / 0.216 = 37 active hours beyond the grant, which is 62 awake hours in the month, about 2.6 days of a replica that never sleeps [E].

### 4.4 Design choices that raise cost sensitivity, and the cheapest safeguards

1. **The model sets the size.** 2 vCPU and 4 GiB at USD 0.000060 a second is paid for every second the replica is up, even for a visitor who only reads the landing page. A static landing page elsewhere would leave the replica asleep for most visits. This is the biggest lever and is not cheap to change.
2. **In-memory state means scale to zero destroys sessions** (section 5), so keeping people's sessions alive means paying for awake time.
3. **Anything wakes it.** Any request wakes the app, including a bot, a link preview or a refused `SESSION_LIMIT`.
4. **The 10 request scale rule does nothing here.** With a maximum of 1 it only wakes the app from zero.
5. **No egress control.** Uncompressed assets and `no-store` fonts raise outbound data (SA10).

Cheapest safeguards: never leave the minimum at 1; a second budget alert at 50 percent and a forecast alert; a look at Cost Management for environment and outbound lines this week; IP restrictions for a known abuser; no pinger. None needs a code change.

### 4.5 Jury, round 1

| Juror | Pushed on | New |
|---|---|---|
| Cost owner | The grant is gone at 4 users a day. Scale to zero saves nothing from about 100 users a day. | SA10 |
| Contrarian | "The cap makes the cost bounded." It does: USD 152 a month at most. But that is more than the whole credit, so a bound is no comfort. | SA10 |
| First-Principles engineer | The money buys one CPU box that answers 25 users an hour. The cost per admitted user at 100 daily users is 83.7 / (100 x 30.4) = USD 0.028 [E]. At 10,000 daily users it is 152.3 / (600 x 30.4) = USD 0.008 [E]. Costs fall per user and the refused users cost nothing extra. | none |
| Attacker | A pinger at 4 minutes is the cheapest attack on the credit. | SA10 |
| SRE | The alert lags and is an email. Nothing automatic cuts spend. | SA10 |

### 4.6 Jury, round 2

The Cost owner checked whether the Express environment rows could apply and found they might (SA10). The Attacker asked whether `GET /api/v1/health` is a cheaper pinger than `/`. It is the same: any request wakes the app. Nothing else new. **Nothing new, so the section is done.**

### 4.7 Verdict

The demo is affordable only at about 10 daily users on the credit. Above about 100 it consumes the credit in about a month, and the ceiling is USD 152 a month because of the one replica. The steady-state safeguard is to stay under that traffic and never leave the minimum at 1. Three unknowns need Aryan's eyes in Cost Management: an environment line, outbound data, and whether a minimum of 1 takes on Express.

## 5. Failure mode simulation

The case: a class of 60 opens the link at once during the viva. The app is either asleep or kept warm for the demo (`Deploy.md` step 7).

### 5.1 In order of what happens

| Step | What happens | Number | Label |
|---|---|---|---|
| 0 (asleep) | The first request wakes the replica. Every other request waits at the ingress | Start-up is 1 to 3 minutes by Aryan's report (`Deploy.md`), the ingress limit is 240 s [C, ingress page], and the startup probe waits about 330 s. If start-up passes 240 s, early visitors get an error from the ingress and a reload works afterwards | [C], reported, not timed on this app |
| 1 | 60 pages load. One uvicorn process serves them from the threadpool | 60 x 0.84 MB = 50 MB at most [E]. Not a failure | [E] |
| 2 **fails first** | `POST /sessions`. The first 25 get 201 and 35 get 429 `SESSION_LIMIT`, which is 58 percent of the class | 35 / 60 | [E] arithmetic on the cap. This is the first hard failure and it comes within seconds. A retry does not help until a session expires, up to 60 minutes. The old message said "try again in a few minutes", which was not true (SA2, fixed) |
| 3 | The 25 admitted users upload together. Only 4 uploads can be in flight and only 3 parses can be running or waiting. The rest get 429 `QUEUE_FULL`, marked retryable | up to 21 of 25 on the first try | [E] |
| 4 **slows first** | The parse worker takes one file at a time. About 25 x 3 s of work (4 s is the measured time for 33 to 44 pages, 1.1 s for 14) | about 80 s on the laptop's figures, and longer on 2 vCPU | [E], unmeasured on Azure |
| 5 | Analyses. 3 places, then `ANALYSIS_QUEUE_FULL`. One analysis runs at a time | 25 x T: 22 to 34 minutes at the laptop's 54 to 82 s, and 45 minutes to 2.3 hours at the Azure estimate of 108 to 326 s | [E] |
| 6 | The scaler. 60 concurrent requests are above the 10 request rule, and the maximum is 1 | The rule adds nothing. The single replica serves everything, and the page does not describe the behaviour for a maximum of 1 | [C] |
| 7 | Memory. The model plus 25 documents | about 1.0 to 1.3 GiB [M] plus 48 MiB [E] of 4 GiB. No out-of-memory kill from this load | [M], [E] |
| 8 | Polling. 25 readers poll 2 calls every 700 ms, which is 71 requests a second [E: 25 x 2 / 0.7]. The 2 vCPU also run the model with 2 threads | The cost of a poll in CPU was not measured. It competes with inference and may slow it | [E], to measure in 4-C |

The 25 session cap fails first (step 2). The analysis queue slows first (step 5). The other queues and memory come after, and the scaler never matters.

### 5.2 State lost or inconsistent

| Event | Lost | What the browser still holds | What the user sees |
|---|---|---|---|
| Restart, a new revision, or an out-of-memory kill | Every session, document, job and result | The text and the findings already on screen, in React memory | A poll gets a 401 and the Reader moves to the Expired page: "This session has ended" and "Sessions end after a set time, or when the page is reloaded. Your contract was not kept. Upload it again" (`Expired.tsx` 13). True, and it does not name a restart. A user who is only reading sees nothing until the next request |
| Scale to zero | The same | The same | After 300 s [C, whether it applies to HTTP rules is not stated] with no request. **The Reader stops polling when the job ends, and selecting a finding is a local action, so a reader goes silent and the replica can be removed while they read.** The next action (Delete, or a new upload) wakes a new replica with no session: a 1 to 3 minute wait, then the Expired page (SA4) |
| A client holding a dead token | Nothing more | A token for a session that does not exist | Every route gives one 401 for unknown and expired alike (`auth.py`). The frontend maps it to the Expired page and clears the token (`Reader.tsx` 97 to 105) |
| The session banner | none | It counts from `expires_at` | It shows only in the last 10 minutes (`Reader.tsx` 769 to 771). After a restart or a scale to zero it can say "ends in 8 minutes" about a session the server lost earlier |
| A network error mid-review | none | The page | "Could not reach the server. Your contract is still open here." (`Reader.tsx` 772 to 774). True |
| Cancel, delete | The job, and the text at once | none | Handled and tested |

Messages checked for truth. `SESSION_LIMIT`: was false, now says a place can take up to an hour (SA2). `QUEUE_FULL` ("try again in a minute") and `ANALYSIS_QUEUE_FULL` ("a few minutes") are about right for the measured parse time and the laptop analysis time. `NOT_READY` ("still starting, try again in a minute") is true for the 6 to 43 s model load [M] and the startup probe normally keeps visitors out until the model is ready.

### 5.3 Monitoring with logs destination none

What exists: the container's console stream and the platform's system stream, live only, through `az containerapp logs show --follow` (`Deploy.md` step 8, not yet run on this app). They show uvicorn access lines and the app's error lines (class names only), and nothing older than the time you started watching. There is no request id in the log (R27), no counter of refused requests and no capacity figure. `/ready` says nothing about sessions or queue depth.

The minimum worth adding for free:

1. Two Cloud Shell tabs during a demo, one for the console stream and one for `--type system`. Count refusals live with `grep " 429 "`.
2. Open the app's Metrics page in the portal once and note which of requests, replica count, restarts and memory it offers for an Express app. If it offers them, they are the only history. Express lists Azure Monitor logging as not supported [C, Express page], so this is unverified.
3. A second budget alert at 50 percent, and a forecast alert (`Deploy.md` step 9).
4. After a demo, `az containerapp revision list` and `az containerapp replica list` for restarts. Not tried here.
5. One log line for each refused request, with the error code and nothing else, so the stream shows `SESSION_LIMIT` rates. A code change (SA19).

### 5.4 Safeguards

| Safeguard | Tag |
|---|---|
| Set the minimum to 1 fifteen minutes early, read it back, open the link once, and set it back to 0 afterwards (`Deploy.md` step 7). Do not deploy or change any setting during the demo | **demo now** |
| Keep the live use under 25 sessions. For a class of 60, have the class watch while up to 3 or 4 people try it, or show a recording. 60 people on one analysis worker would take 60 x T, which is hours [E] | **demo now** |
| Say "full" is not an error: a place can take up to an hour (SA2, fixed in the frontend, needs a deploy) | **demo now** |
| Watch the two log tabs. Know the one command that sets the minimum back to 0 | **demo now** |
| End the session when the user is done: `DELETE /sessions/current` from the Delete button and on leaving the page (SA3) | before a wider launch |
| A limit per address at a proxy, and the cross-site session creation closed (SA5) | before a wider launch |
| A sentence on the Start page: public demo, use a sample contract (SA16) | before a wider launch |
| Security headers in one change, checked in a browser (SA8) | before a wider launch |
| A log line for each refusal, request ids in the log, and a capacity figure in `/ready` (SA19) | before a wider launch |
| The time of an analysis and a parse on the host, so the limits and the queue sizes come from numbers (R6, SA12, SA13) | before a wider launch (4-C) |
| Sessions and results outside the process (a store such as Redis), so a replica can restart and a second one can run | only at real scale |
| Inference as a separate service that scales on queue depth, and polling replaced by push | only at real scale |

### 5.5 Jury, round 1

| Juror | Pushed on | New |
|---|---|---|
| SRE | The silent reader and scale to zero (SA4). A bad update ends every session and has no fast way back (SA14). The startup probe for a failed load is a restart loop. | SA4, SA14 |
| Contrarian | "A demo class of 60 is the wrong test." It is the one the owner named, and 25 of 60 fail before anything else. | none |
| First-Principles engineer | What the user needs to learn is why they failed and what to do. The `SESSION_LIMIT` copy told them the wrong time (SA2). The Expired page does not name the cause. | SA2, SA17 |
| Attacker | During the viva someone can fill the 25 places on purpose, and nobody would know why (SA5, SA19). | SA19 |
| Cost owner | A kept-warm replica for the viva is a few dollars of active time, and the cool-down tail runs 5 minutes beyond the last request. | none |

### 5.6 Jury, round 2

The SRE asked what the user sees if the replica restarts during the model load: `NOT_READY` is the answer for a request the ingress lets through, and the startup probe holds traffic until ready. The First-Principles engineer asked whether the Expired page should name the server restart. It says what is true and useful, and the wording is recorded as SA17. Nothing else new. **Nothing new, so the section is done.**

### 5.7 Verdict

The first thing to fail is the 25 session cap, within seconds, and 35 of 60 people would see it. The analysis worker is the next limit and it is hours deep for 25 people at the Azure estimate. Nothing runs out of memory. The most damaging silent failure is scale to zero while people read. The safeguards that matter for the viva cost nothing and need no code: stay under 25 sessions, keep the replica warm and watch the logs.

## 6. Completion versus stability

The question: assume 100 times the load. List the hidden debt, the shortcuts that do not scale and the weak separation, each with a file. 100 times today is about 2,500 admitted sessions an hour.

| # | Debt or shortcut | Evidence | What breaks at 100 times |
|---|---|---|---|
| 1 | All state is in one process | `store.py` 140 to 163, 151, `Dockerfile` 76 (`--workers 1`) | A second replica cannot find a session. Every update and every restart ends all sessions. This blocks every other item |
| 2 | One analysis worker, CPU bound on 2 vCPU | `analysis_jobs.py` `AnalysisQueue`, `_work` | 2,500 analyses an hour of 54 to 326 s need 2,500 x 54 / 3,600 = 38 to 2,500 x 326 / 3,600 = 226 boxes of this size [E] |
| 3 | Fixed polling, 2 requests every 700 ms for the whole analysis, no back-off, no change tag | `Reader.tsx` 39, 139 to 151, `useStartFlow.ts` 110 | 2,500 readers send about 7,100 requests a second [E: 2,500 x 2 / 0.7] into one Python process. A single process answering that is not measured and is unlikely |
| 4 | The store lock and SQLite plus a dict as two stores | `store.py` 140 to 462 | Every request waits on one lock. At 100 times the lock is in the path of thousands of requests a second |
| 5 | The lock is held across a child wait, and event-loop handlers take it | `store.py` 246 to 257, 448 to 462, `parse_jobs.py` 87 to 99, `routes.py` 141 to 193, `main.py` 32 to 39 | A stall of up to 5 s blocks the whole loop. This is R19 and SA7 |
| 6 | Limits are constants, not settings | `config.py` 27 to 46 | Changing a cap needs a new image and a deploy |
| 7 | The `on_drop` hook is a reassigned attribute, wired by construction order | `parse_jobs.py` 59, `analysis_jobs.py` 67 to 73, `main.py` 110 to 111 | A third consumer depends on the order, and a refactor of the order drops a hook |
| 8 | The routes are the use-case layer | `routes.py` 232 to 274 (`_take_upload`: read, detect, store, queue, read-back race) and 382 to 422 (`start_analysis`: nine checks) | Each Phase 3 endpoint copies the pattern. No service layer to test without HTTP |
| 9 | One Python interpreter is started for each parse | `parse_jobs.py` 142, `memcap.py` 94 to 136 | 2,500 parses an hour of 3 s is 2.1 CPU hours an hour [E: 2,500 x 3 / 3,600], which is the whole box. `memcap.py` is platform code that uses a private `Popen._handle` on Windows and `preexec_fn` in a multithreaded process on Linux, and it has run once on Linux (SA15) |
| 10 | Uploads are read whole into RAM and held twice | `routes.py` 110 to 120, `config.py` 33 | 4 in flight is 80 MiB [M]. At 100 times a stream to a spool or an object store is needed, and `Rules.md` section 5 forbids disk today |
| 11 | The document read sends the whole text, blocks and nodes and rebuilds them each call, with no compression and no change tag | `routes.py` 76 to 86, 282 to 298, `main.py` 93 to 123 | About 1 MB x 2 reads x 2,500 an hour is 5 GB an hour [E] |
| 12 | Job rows and queue markers are never pruned | `store.py` 337 to 347 | SA6. At 100 times, bounded only by the 60 minute lifetime |
| 13 | No metrics, no request id, a `/ready` with no capacity or worker check | `routes.py` 141 to 153, R18, R27 | The signals that show saturation cannot be read from the running app (SA19) |
| 14 | The model is baked into the image | `Dockerfile` 42 | A model change is a 1.7 GB rebuild and a full redeploy, and each new replica pulls 1,671 MiB |
| 15 | `Reader.tsx` holds polling, selection, panels, delete and the session banner in one 1,150 line component, with two `exhaustive-deps` suppressions | `Reader.tsx` 127, 161 | A stale closure bug is a matter of time as features land (3-A to 3-D) |
| 16 | Tests reach into private queue attributes | `test_analysis_jobs.py`, `test_analyses_api.py` (`queue._items`) | A change to the queue's internals breaks tests that pin behaviour |
| 17 | SQLite for 25 rows | `store.py` 33 to 67 | Not a bottleneck, and it only carries a schema for a later version |

### 6.1 Jury, round 1

| Juror | Pushed on | New |
|---|---|---|
| Contrarian | "100 times is not a plan for a portfolio demo." It is not. The audit says where it stops. Items 1 and 2 are the ones that matter and both are design limits, not defects. | none |
| First-Principles engineer | At 100 times, the inference cost (item 2) dominates every other item by two orders of magnitude, so fixing the lock or the polling first is the wrong order. | none |
| Attacker | Item 5 plus item 3: a flood of polling keeps the lock busy and slows the delete path that frees memory. | none |
| SRE | With items 13 and 14, an operator cannot see an incident and has no fast way back from a bad deploy. | SA14 |
| Cost owner | Item 2 turned into money: 38 to 226 boxes at USD 0.216 an hour is USD 8 to 49 an hour [E]. | none |

### 6.2 Jury, round 2

Nothing new from any juror. **Nothing new, so the section is done.**

### 6.3 Verdict

The build is complete for what it set out to be, a demo with real inference and an honest scope, and it is stable only inside one replica and 25 sessions an hour. At 100 times the first limits are structural (one process, one worker) and no tuning reaches them. The smaller items (constants, hooks, route size, polling) are real debt and none is urgent.

## 7. Triage

Every finding is one of three. **Fix now** means small, real on the live demo today and inside `backend/` or `frontend/`. **Record** means it goes into `Phases.md` with an owner. **Accepted** means a public demo can carry it, and the limit that bounds it is named. An owner is a Phase 3 part, 4-C, 4-R, or "only at real scale", or Aryan where only he can act.

| Id | Finding | Group | Owner | Reason |
|---|---|---|---|---|
| SA1 | A stopped waiting analysis stays in the queue with its ids, and `submit` counts them all (about 4.1 KB a round [E]) | **Fix now, done** | | Red and green tests. Needs a new image and a deploy |
| SA2 | `SESSION_LIMIT` says "a few minutes" when a place can take up to an hour | **Fix now, done** | | One string and one test. Needs a new image and a deploy |
| SA3 | A visitor holds a session slot for 60 minutes and the frontend never ends it, so the app serves 25 users an hour at most | Record | Aryan decides, then 4-C | The options are an end-session call on delete and on leaving, or 60 sessions of 2 documents (120 documents, under today's 125). Both change `API.md` section 8 and `config.py`, and the cap is a proposal Aryan owns |
| SA4 | Scale to zero ends every session while a reader is silent, after about 300 s [C] | Record | Aryan decides, then 4-C | A keep-alive from the Reader would hold the replica awake and cost money. Correctness and cost pull in opposite directions |
| SA5 | No limit per client on sessions, uploads, parse places, analysis places or public routes, and sessions can be made from other people's browsers. Widens R5 | Accepted | Only at real scale (a proxy with the client's address) | Bounded by the caps: a refusal for others for up to 60 minutes, and nothing is lost. Block an address by hand at the ingress |
| SA6 | Job rows are never pruned. About 300 bytes a row [E], 110 MB for a start and cancel loop at 100 rounds a second for an hour | Accepted | Only at real scale | Bounded by the 60 minute lifetime. Pruning would change "the old job stays readable" in `API.md` |
| SA7 | Four async call sites take the store lock on the event loop (`create_session`, `delete_current_session`, `ready`, the sweep). Restates R19 | Accepted | 4-C (R19, unchanged) | A stall is at most 5 s and a killed child exits in milliseconds [E]. One liveness failure of three |
| SA8 | No `X-Content-Type-Options`, frame, CSP or referrer header | Record | 4-R | Low severity. A browser must check the set first |
| SA9 | Floating base images, a tag-pinned action, installs without hashes | Record | 4-R | Low to Medium. Pin by digest and commit |
| SA10 | Cost unknowns: an environment meter (USD 0.10 an hour from 2026-11-01), outbound data, and whether a minimum of 1 takes on Express | Record | Aryan, this week | A look in Cost Management. If the management meter applies, the credit lasts about 42 days [E] |
| SA11 | Fonts and the favicon are `no-store`, and nothing is compressed | Record | 4-C | 352,186 bytes of fonts fetched again on every visit [M] |
| SA12 | A 41 category review of a 33 page contract is estimated at 27 to 75 minutes on 2 vCPU against a 30 minute limit. Widens R6 | Record | 4-C (R6) | The estimate rests on k of 2 to 4 and is unmeasured |
| SA13 | Polling costs 71 requests a second for 25 readers [E] on the CPU that runs the model | Record | 4-C | A measurement and then a back-off |
| SA14 | The platform behaviours the app relies on are not written down: TLS, the 240 s limit, the restart loop, no previous revision to return to | Record | 4-R | A note in `Deploy.md` and a rollback line |
| SA15 | The Linux memory cap and `preexec_fn` in a multithreaded process have run once, in the CI smoke test | Record | 4-C | It is in 4-C already ("that the cap itself kills an overshoot stays untested") |
| SA16 | No line on any page says this is a public demo for sample contracts | Record | Aryan, before the link goes wide | Copy is Aryan's call. One sentence on Start and Landing |
| SA17 | The Expired page does not name a server restart or a scale to zero | Record | 4-C | True and useful, but incomplete |
| SA18 | Public routes (`/ready`, `/capabilities`, `/openapi.json`) are open | Accepted | | The repository is public and the routes hold no user data |
| SA19 | No request id in logs, no count of refusals, no capacity figure in `/ready`. Restates R27 and R18 | Record | Before a wider launch (4-C) | The signals this audit needed cannot be read from the app |
| SA20 | `Reader.tsx` is 1,150 lines with two hook suppressions. Routes and the store are large | Record | Only at real scale | Separation debt with no failure today |

Findings about hostile files, ids and tokens are **handled** and are not triage items: sections 2.1 to 2.6.

## 8. What Aryan has to do, in order

1. **Read this file and decide SA3, SA4 and SA16.** They are product choices and not defects.
2. **Look in Cost Management for an environment line and for outbound data** (SA10), and set a second budget alert at 50 percent.
3. **Confirm with Tanishq that the model may sit in a public image** (`Deploy.md` step 2.7). The record does not show the answer.
4. **Commit** the audit and the two fixes, as the commits in the report suggest.
5. **Run the image workflow, then update the app by the full commit SHA** (`Deploy.md` steps 2 and 6). The two fixes (SA1, SA2) are in `backend/` and `frontend/`, so they reach the live app only after a new image and an update. An update ends every session, so do it well before the viva and not during it.
6. **For the viva**, follow section 5.4: minimum 1 fifteen minutes early, read it back, two log tabs, under 25 sessions, minimum 0 afterwards.
