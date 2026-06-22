# ContestForge — API Contracts (Companion)

Human-readable companion to `api-contracts.yaml` (OpenAPI 3.0.3, v1.0.0). The
YAML is the source of truth; this document summarises each resource, gives
examples, states the conventions, and documents the WebSocket live channel
(which is not expressible in OpenAPI).

Base URL (placeholder): `https://api.contestforge.example/v1`

---

## Conventions

### Authentication & roles
Every endpoint requires a JWT bearer token **except** `POST /auth/login`,
`POST /auth/refresh`, `GET /health`, and `GET /ready`. The token's claims carry
the caller's `role` and `tenant_id`. Roles: `SUPER_ADMIN`, `ORG_ADMIN`,
`MODERATOR`, `PARTICIPANT`. Cross-tenant access is rejected with `403`.

**Onboarding chain (no public self-signup):**
1. The first **Super Admin** is created by an SQL bootstrap script — *not*
   exposed in the API.
2. The Super Admin creates an organization via `POST /organizations`, which
   provisions that tenant's initial **Org Admin**.
3. An **Org Admin** creates co-Org-Admins, Moderators, and Participants via
   `POST /users`. `POST /users` rejects `role = SUPER_ADMIN`.

### Error model
All errors share one shape:
```json
{ "error": { "code": "CONFLICT_INVALID_TRANSITION",
             "message": "Cannot edit configuration after Registration Open.",
             "details": { "current_status": "REGISTRATION_OPEN" } } }
```

| Status | Meaning |
|---|---|
| 200 / 201 / 204 | Success / created / no content |
| 202 | Accepted (async live-control commands) |
| 400 | Malformed request (schema/parse error) |
| 401 | Missing/invalid token |
| 403 | Role or tenant not permitted |
| 404 | Resource not found in caller's tenant |
| 409 | Invalid state transition / precondition failure |
| 422 | Semantic validation (e.g. ELIMINATION block missing rules) |
| 503 | Not ready (readiness probe) |

### Pagination
List endpoints accept `limit` (1–200, default 50) and an opaque `cursor`, and
return a `Page` envelope:
```json
{ "items": [ ... ], "next_cursor": "eyJ...", "has_more": true }
```

---

## Auth & Session

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Authenticate; returns access/refresh tokens. |
| POST | `/auth/refresh` | Rotate the refresh token for a new pair. |
| POST | `/auth/logout` | Revoke the presented refresh token (and rotation chain). |
| GET | `/auth/me` | Current authenticated principal. |
| POST | `/auth/change-password` | Change the caller's password. |

```json
// POST /auth/login
{ "email": "admin@acme.test", "password": "••••••••", "tenant_slug": "acme" }
// 200
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer",
  "expires_in": 900, "role": "ORG_ADMIN" }
```
Refresh tokens rotate: each `/auth/refresh` revokes the used token and issues a
new one (domain rule BR-20). `/auth/logout` revokes immediately.

---

## Users (Org Admin)

| Method | Path | Description |
|---|---|---|
| POST | `/users` | Create a tenant user (`ORG_ADMIN | MODERATOR | PARTICIPANT`). |
| GET | `/users` | List/filter by `role`, `status` (paginated). |
| GET | `/users/{userId}` | Get a user. |
| PATCH | `/users/{userId}` | Update first/last name or status. |

```json
// POST /users (201)
{ "email": "ravi@acme.test", "first_name": "Ravi", "last_name": "Kumar",
  "role": "PARTICIPANT" }
```
`role = SUPER_ADMIN` → `422`. Duplicate email within the tenant → `409`.

---

## Organizations (Super Admin)

| Method | Path | Description |
|---|---|---|
| POST | `/organizations` | Create a tenant + initial Org Admin. |
| GET | `/organizations` | List tenants (paginated). |
| GET | `/organizations/{orgId}` | Get a tenant. |
| PATCH | `/organizations/{orgId}` | Update `name`, `custom_domain`. |
| PATCH | `/organizations/{orgId}/status` | Suspend / reactivate. |

```json
// POST /organizations (201)
{ "name": "Acme University", "slug": "acme",
  "portal_url": "https://acme.contestforge.com",
  "admin_email": "lead@acme.test", "admin_first_name": "Asha",
  "admin_last_name": "Rao" }
```
`slug` and `portal_url` are unique platform-wide and **immutable** once the
tenant publishes its first contest (BR-19) — `PATCH /organizations/{orgId}` does
not accept them. Conflicts on `slug`/`portal_url`/`custom_domain` → `409`.

---

## Contests & Lifecycle (Org Admin)

| Method | Path | Description | Notes |
|---|---|---|---|
| POST | `/contests` | Create in Draft. | `structure` locks at Published. |
| GET | `/contests` | List in tenant. | `?status=` filter, paginated. |
| GET | `/contests/{id}` | Detail (groups + configuration). | |
| PATCH | `/contests/{id}` | Update metadata. | `409` if not Draft. |
| DELETE | `/contests/{id}` | Delete. | Draft only, else `409`. |
| POST | `/contests/{id}/lifecycle` | Advance one stage. | See below. |

```json
// POST /contests (201)
{ "name": "Fresher Hiring Challenge", "structure": "GROUPED",
  "group_score_rollup": "SUM" }

// POST /contests/{id}/lifecycle
{ "target_status": "SCHEDULED", "scheduled_start_at": "2026-07-01T10:00:00Z" }
```
Lifecycle is fixed and non-skippable:
`DRAFT → PUBLISHED → REGISTRATION_OPEN → REGISTRATION_CLOSED → SCHEDULED → LIVE
→ COMPLETED → ARCHIVED`. Illegal transitions / unmet preconditions → `409`.
`SCHEDULED` requires `scheduled_start_at`.

---

## Groups (Grouped contests, Draft)

| Method | Path | Description |
|---|---|---|
| POST | `/contests/{id}/groups` | Add a group. |
| GET | `/contests/{id}/groups` | List groups. |
| PATCH | `/contests/{id}/groups/{groupId}` | Update name/sequence/weight. |
| DELETE | `/contests/{id}/groups/{groupId}` | Delete group. |

---

## Configuration

| Method | Path | Description |
|---|---|---|
| PUT | `/contests/{id}/configuration` | Set a Configuration Block. Editable until Registration Open. |
| GET | `/contests/{id}/configuration` | Return block(s): one for Normal, one per group for Grouped. |

The Configuration Block is the core of the system. **`mode` determines the
scoring model** — `STANDARD`/`ELIMINATION` use the fixed-scoring fields
(`correct_points`, `wrong_points`, `second_chance_rate`); `SPEED` uses
`time_bands` or `decay`. Reveal modes are `AUTOMATIC | MODERATOR_CONTROLLED`.
For `ELIMINATION`, `elimination_rules`, `checkpoints`, and a block-level
`elimination_combine_operator` (`AND`/`OR`) are required; supplying them on a
non-elimination block, or omitting them on an elimination block, → `422`.

```json
// PUT /contests/{id}/configuration — Speed group
{
  "group_id": "b2c3...",
  "mode": "SPEED",
  "question_duration_s": 20,
  "question_interval_s": 5,
  "explanation_duration_s": 10,
  "leaderboard_duration_s": 10,
  "reveal_mode": "AUTOMATIC",
  "ranking_criterion": "SCORE_TIME",
  "tie_display": "SHARED_RANK",
  "leaderboard_visibility": "POST_QUESTION",
  "update_frequency": "PER_QUESTION",
  "time_bands": [
    { "max_seconds": 5,  "points": 100 },
    { "max_seconds": 10, "points": 75 },
    { "max_seconds": 15, "points": 50 },
    { "max_seconds": 20, "points": 25 }
  ],
  "wildcards": [
    { "type": "FIFTY_FIFTY", "usage_limit": 1, "eligibility": "ALL",
      "cooldown_questions": 3, "carry_over": false }
  ]
}
```

```json
// Elimination group (excerpt)
{
  "group_id": "c3d4...",
  "mode": "ELIMINATION",
  "question_duration_s": 90,
  "ranking_criterion": "SCORE_ONLY",
  "elimination_combine_operator": "OR",
  "survivor_score_reset": false,
  "elimination_rules": [
    { "type": "BOTTOM_X_PERCENT", "percent_value": 50 }
  ],
  "checkpoints": [ { "type": "AFTER_GROUP" } ]
}
```

---

## Questions & Options (Draft)

| Method | Path | Description |
|---|---|---|
| POST | `/contests/{id}/questions` | Add a question (≥2 options, exactly one correct). |
| GET | `/contests/{id}/questions` | List (admin view incl. correctness); `?group_id=`. |
| GET | `/contests/{id}/questions/{qid}` | Get one. |
| PATCH | `/contests/{id}/questions/{qid}` | Update text/explanation/sequence/group. |
| DELETE | `/contests/{id}/questions/{qid}` | Delete. |
| PUT | `/contests/{id}/questions/{qid}/options` | Replace the full option set. |

```json
// POST /contests/{id}/questions (201)
{ "group_id": "b2c3...", "sequence": 1, "text": "What is 2+2?",
  "explanation": "Basic arithmetic.",
  "options": [ { "text": "3", "is_correct": false },
               { "text": "4", "is_correct": true } ] }
```
> Participant-facing question payloads (delivered over WebSocket at reveal, and
> in `GET /contests/{id}/live-state`) omit `is_correct` and `explanation` until
> the evaluation/explanation phase.

---

## Registration

| Method | Path | Description |
|---|---|---|
| POST | `/contests/{id}/registrations` | Participant self-registers (Registration Open; `409` otherwise/duplicate). |
| GET | `/contests/{id}/registrations` | Org Admin / Moderator list (paginated, `?status=`). |
| GET | `/contests/{id}/registrations/me` | Caller's own registration. |
| DELETE | `/contests/{id}/registrations/{registrationId}` | Withdraw (self before close, or Org Admin). |

A `Registration` carries `status`, `spectator_access`, and (after completion)
`final_rank` / `final_score`.

---

## Live runtime (REST complements the WebSocket channel)

| Method | Path | Description |
|---|---|---|
| GET | `/contests/{id}/live-state` | Participant reconnect snapshot (FR-43): current question without correctness, authoritative `submission_close_at`, caller status/score. `409` if not Live. |
| POST | `/contests/{id}/control/reveal` | **Moderator**: manually reveal current/next question (Moderator-Controlled mode). `202`. |
| POST | `/contests/{id}/control/advance` | **Moderator**: override progression (`scope: QUESTION | GROUP`). `202`. |

Real-time delivery and answer submission happen over WebSocket (below). These
REST endpoints exist for reconnection recovery and moderator console actions.

---

## Results, Leaderboards & Eliminations

| Method | Path | Description |
|---|---|---|
| GET | `/contests/{id}/leaderboard` | Snapshot; `?view=CONTEST\|GROUP\|SURVIVOR`, optional `group_id`. REST fallback for the live WS push. |
| GET | `/contests/{id}/results` | Final results + per-participant breakdown (Completed/Archived). |
| GET | `/contests/{id}/results/export` | Export results; `?format=csv\|json`. |
| GET | `/contests/{id}/eliminations` | Elimination events (Org Admin / Moderator). |
| GET | `/contests/{id}/wildcard-audit` | Wildcard activation audit (Org Admin). |

---

## Notifications (participant)

| Method | Path | Description |
|---|---|---|
| GET | `/me/notifications` | List caller's notifications; `?unread_only=`, paginated. |
| POST | `/me/notifications/{notificationId}/ack` | Mark delivered/read. |

Notification `type` ∈ `ELIMINATION | ANSWER_ACK | SPECTATOR_GRANTED |
CONTEST_PROGRESS`; `payload` carries type-specific data (e.g. final rank/score
for `ELIMINATION`).

---

## Audit

| Method | Path | Description |
|---|---|---|
| GET | `/audit` | Query the audit log. Org Admin = tenant-scoped; Super Admin = platform-wide. Filters: `entity_type`, `action`, `actor_user_id`, `from`, `to`; paginated. |

---

## Ops

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness (unauthenticated). |
| GET | `/ready` | Readiness incl. DB/Redis dependency checks; `503` if not ready. |

---

## WebSocket Channel (live contest)

REST covers authoring, administration, and results. The live contest runs over
a WebSocket connection; the contract is documented here so frontend and backend
agree (it is not part of the OpenAPI document).

**Connect:** `wss://api.contestforge.example/v1/contests/{contestId}/live`
with the JWT supplied as a connection token (subprotocol or query token). The
server validates role, tenant, and an active Registration.

**Server → client events**

| Event | Payload (summary) | When |
|---|---|---|
| `question.reveal` | question id, sequence, text, options (no correctness), `submission_close_at` | At reveal (≤200ms fan-out, NFR-1). |
| `answer.ack` | submission id, `attempt_no`, accepted (bool), reason | After a submission is durably accepted/rejected (FR-41). |
| `question.evaluation` | correct option id, explanation | After the submission window closes. |
| `leaderboard.update` | view, ranked entries (delta or snapshot) | Per configured `update_frequency`. |
| `elimination.event` | participant id, final rank/score, spectator flag | At a checkpoint. |
| `contest.progress` | current group/question, phase | On group/question advance. |

**Client → server actions**

| Action | Payload | Rules |
|---|---|---|
| `answer.submit` | question id, selected option id, `attempt_no`, client idempotency key | Rejected if past server-side `submission_close_at` (`reason: window_closed`, FR-20) or participant eliminated. Server timestamp is authoritative (FR-40). |
| `wildcard.activate` | type, question id | Subject to enabled set, usage limit, eligibility, cooldown; Fifty-Fifty rejected after an answer is selected (FR-23/26). |
| `moderator.reveal` | question id | Moderator only; Moderator-Controlled mode (mirrors `POST /control/reveal`). |
| `moderator.advance` | scope (QUESTION/GROUP) | Moderator override (mirrors `POST /control/advance`). |

**Durability / ack semantics:** an `answer.submit` is acknowledged only after
the answer is durably persisted with its server-accept timestamp against the
authoritative `QuestionWindow`. The client idempotency key plus the server-side
`(contest, question, participant, attempt_no)` key ensure retries are not
double-counted (FR-39). A delayed ack does not revoke an already-accepted
answer (FR-41).

---

## Traceability (capabilities → endpoints)

| PRD / FR capability | Covered by |
|---|---|
| Tenancy, org create/suspend (FR-1/2) | `/organizations*` |
| Identity, JWT, roles (FR-4/5) | `/auth/*`, `/users*` |
| Tenant isolation (FR-3) | enforced cross-cutting; `403` on every tenant-scoped path |
| Contest model & lifecycle (FR-6–9) | `/contests*`, `/contests/{id}/lifecycle` |
| Configuration block, modes, scoring (FR-10–16) | `/contests/{id}/configuration`, `ConfigurationBlock` schema |
| Execution, reveal, progression (FR-17–21) | WebSocket channel, `/control/*`, `/live-state` |
| Wildcards (FR-22–27) | `WildcardConfig` in config; WS `wildcard.activate`; `/wildcard-audit` |
| Leaderboards (FR-28–32) | `/leaderboard`, WS `leaderboard.update` |
| Elimination (FR-33–37) | elimination config; `/eliminations`; WS `elimination.event` |
| Durability/recovery (FR-38–44) | WS ack semantics, `/live-state`, idempotency keys |
| Notifications (FR-37/41) | `/me/notifications*`, WS events |
| Audit (tech-spec §6) | `/audit`, `/wildcard-audit` |
| Results & export | `/results`, `/results/export` |
| Ops/observability | `/health`, `/ready` |
