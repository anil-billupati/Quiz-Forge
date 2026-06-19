# ContestForge — API Contracts (Companion)

Human-readable companion to `api-contracts.yaml` (OpenAPI 3.0.3). All
tenant-scoped endpoints require a JWT bearer token; the token's claims carry
the caller's `role` and `tenant_id`. Cross-tenant access is rejected with `403`.

Base URL (placeholder): `https://api.contestforge.example/v1`

---

## Authentication

All users (Super Admin, Org Admin, Moderator, Participant) authenticate with
email + password and receive a JWT access/refresh token pair. The access token
is short-lived (~15 min); the refresh token rotates.

### POST /auth/login
```json
// request
{ "email": "admin@acme.test", "password": "••••••••", "tenant_slug": "acme" }

// 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900,
  "role": "ORG_ADMIN"
}
```

### POST /auth/refresh
Exchanges a valid refresh token for a fresh token pair. Returns `401` if the
refresh token is invalid/expired.

---

## Organizations (Super Admin only)

| Method | Path | Description |
|---|---|---|
| POST | `/organizations` | Create a tenant; provisions the initial Org Admin. |
| GET | `/organizations` | List all tenants. |
| PATCH | `/organizations/{orgId}/status` | Suspend / reactivate a tenant. |

```json
// POST /organizations  (201)
{ "name": "Acme University", "admin_email": "lead@acme.test",
  "admin_display_name": "Acme Lead" }
```
Authorization: a token without role `SUPER_ADMIN` is rejected with `403`.

---

## Contests (Org Admin)

| Method | Path | Description | Notes |
|---|---|---|---|
| POST | `/contests` | Create a contest in Draft. | `structure` locks at Published. |
| GET | `/contests` | List contests in caller's tenant. | `?status=` filter. |
| GET | `/contests/{id}` | Get contest with groups + configuration. | |
| PATCH | `/contests/{id}` | Update metadata. | `409` if not Draft. |

```json
// POST /contests  (201)
{ "name": "Fresher Hiring Challenge", "structure": "GROUPED",
  "group_score_rollup": "SUM" }
```

---

## Groups & Configuration

| Method | Path | Description |
|---|---|---|
| POST | `/contests/{id}/groups` | Add a group (Grouped, Draft only). |
| PUT | `/contests/{id}/configuration` | Set the Configuration Block (Normal: contest scope; Grouped: include `group_id`). Editable until Registration Open. |

The Configuration Block is the heart of the system. `mode` determines the
scoring model — `STANDARD`/`ELIMINATION` use fixed scoring fields
(`correct_points`, `wrong_points`, `second_chance_rate`); `SPEED` uses
`time_bands` or `decay`. `elimination_rules` and `checkpoints` are required when
`mode = ELIMINATION` and ignored otherwise. Submitting elimination config for a
non-elimination block, or omitting it for an elimination block, returns `409`.

```json
// PUT /contests/{id}/configuration  — Speed group example
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
// Elimination group example (excerpt)
{
  "group_id": "c3d4...",
  "mode": "ELIMINATION",
  "question_duration_s": 90,
  "ranking_criterion": "SCORE_ONLY",
  "elimination_rules": [
    { "type": "BOTTOM_X_PERCENT", "percent_value": 50, "combine_operator": "OR" }
  ],
  "checkpoints": [ { "type": "AFTER_GROUP" } ]
}
```

---

## Questions (Org Admin, Draft only)

| Method | Path | Description |
|---|---|---|
| POST | `/contests/{id}/questions` | Add a question with ≥2 options (exactly one correct). |
| GET | `/contests/{id}/questions` | List questions (admin view includes correctness). |

```json
// POST  (201)
{ "group_id": "b2c3...", "sequence": 1, "text": "What is 2+2?",
  "explanation": "Basic arithmetic.",
  "options": [ { "text": "3", "is_correct": false },
               { "text": "4", "is_correct": true } ] }
```

> Participant-facing question payloads (delivered over WebSocket at reveal) omit
> `is_correct` and `explanation` until the evaluation/explanation phase.

---

## Lifecycle

### POST /contests/{id}/lifecycle
Advances the contest one stage along the fixed sequence:
`DRAFT → PUBLISHED → REGISTRATION_OPEN → REGISTRATION_CLOSED → SCHEDULED → LIVE
→ COMPLETED → ARCHIVED`. Skipping a stage or failing preconditions returns
`409`. `SCHEDULED` requires `scheduled_start_at`.

```json
{ "target_status": "SCHEDULED", "scheduled_start_at": "2026-07-01T10:00:00Z" }
```

---

## Registration

| Method | Path | Description |
|---|---|---|
| POST | `/contests/{id}/registrations` | Participant self-registers (Registration Open only; `409` otherwise or if already registered). |
| GET | `/contests/{id}/registrations` | Org Admin / Moderator list registrations. |

---

## Results & Leaderboards

| Method | Path | Description |
|---|---|---|
| GET | `/contests/{id}/leaderboard` | Snapshot of a leaderboard view (`?view=CONTEST\|GROUP\|SURVIVOR`, optional `group_id`). Live updates come over WebSocket; this is a REST fallback/snapshot. |
| GET | `/contests/{id}/results` | Final results + per-participant breakdown (Completed/Archived). |
| GET | `/contests/{id}/wildcard-audit` | Wildcard activation audit log (Org Admin). |

---

## WebSocket Channel (live contest)

REST covers authoring and results; the live contest runs over a WebSocket
connection. The transport contract (finalized in implementation) is summarized
here so frontend and backend agree.

**Connect:** `wss://api.contestforge.example/v1/contests/{contestId}/live`
with the JWT supplied as a connection token (subprotocol or query token). The
server validates role, tenant, and an active Registration.

**Server → client events**

| Event | Payload (summary) | When |
|---|---|---|
| `question.reveal` | question id, text, options (no correctness), server close time | At reveal (≤200ms fan-out). |
| `answer.ack` | submission id, accepted (bool), reason | After a submission is durably accepted/rejected. |
| `question.evaluation` | correct option id, explanation | After the submission window closes. |
| `leaderboard.update` | view, ranked entries (delta or snapshot) | Per configured `update_frequency`. |
| `elimination.event` | participant id, final rank/score, spectator flag | At a checkpoint. |
| `contest.progress` | current group/question, lifecycle/live state | On group/question advance. |

**Client → server actions**

| Action | Payload | Rules |
|---|---|---|
| `answer.submit` | question id, selected option id, attempt_no, client idempotency key | Rejected if past server-side close time (`reason: window_closed`) or participant eliminated. Server timestamp is authoritative. |
| `wildcard.activate` | type, question id | Subject to enabled set, usage limit, eligibility, cooldown; Fifty-Fifty rejected after an answer is selected. |
| `moderator.reveal` | question id | Moderator only; Moderator-Controlled reveal mode. |
| `moderator.advance` | group/question target | Moderator override of progression. |

**Durability/ack semantics:** an `answer.submit` is acknowledged only after the
answer is durably persisted with its server-accept timestamp. The client
idempotency key plus the server-side `(contest, question, participant, attempt)`
key ensure retries are not double-counted. A delayed ack does not revoke an
already-accepted answer.

---

## Common Error Shape

```json
{ "error": { "code": "CONFLICT_INVALID_TRANSITION",
             "message": "Cannot edit configuration after Registration Open.",
             "details": { "current_status": "REGISTRATION_OPEN" } } }
```

| Status | Meaning |
|---|---|
| 400 | Validation error (schema/range). |
| 401 | Missing/invalid token. |
| 403 | Role or tenant not permitted. |
| 404 | Resource not found in caller's tenant. |
| 409 | Invalid state transition / precondition failure. |
