# ContestForge — Technical Specification

| | |
|---|---|
| **Project** | ContestForge |
| **Source** | docs/kickoff.md, docs/spec/product-spec.md |
| **Date** | 2026-06-19 |
| **Status** | Draft — for approval |

---

## 1. System Overview

ContestForge is a full-stack, multi-tenant platform. The backend is a hybrid
FastAPI service: a synchronous HTTP/WebSocket API for administration and live
participation, plus background workers that run the server-authoritative
contest engines (Execution, Scoring, Leaderboard, Elimination). The frontend
is a Next.js/TypeScript web application. PostgreSQL is the authoritative store;
Redis provides leaderboard computation/cache and real-time fan-out.

### 1.1 Component Diagram (text)

```
                         ┌──────────────────────────────┐
                         │  Next.js / TypeScript (Web)   │
                         │  Admin · Moderator · Player    │
                         └───────────────┬───────────────┘
                            HTTPS (REST)  │  WSS (live)
                                          ▼
                ┌─────────────────────────────────────────────┐
                │             FastAPI API Service              │
                │  ┌────────────┐  ┌─────────────────────────┐ │
                │  │ Auth/RBAC  │  │ Tenant context (tenant_id│ │
                │  │ JWT        │  │ resolved per request)    │ │
                │  └────────────┘  └─────────────────────────┘ │
                │  REST: orgs, contests, config, questions,    │
                │        registration, results                  │
                │  WS:   question push, answer submit,          │
                │        leaderboard push, elimination events   │
                └───────┬───────────────────────┬──────────────┘
                        │                        │
          enqueue/commands              pub/sub + cache
                        │                        │
                        ▼                        ▼
         ┌──────────────────────────┐   ┌────────────────────┐
         │   Engine Workers          │   │       Redis         │
         │  ┌─────────────────────┐ │   │  - leaderboard ZSET │
         │  │ Execution Engine    │ │◄──┤  - pub/sub channels │
         │  │ (timers, reveal,    │ │   │  - WS presence      │
         │  │  progression)       │ │   │  - dedupe keys      │
         │  ├─────────────────────┤ │   └─────────┬───────────┘
         │  │ Scoring Engine      │ │             │ rebuildable from
         │  ├─────────────────────┤ │             │ authoritative data
         │  │ Leaderboard Engine  │ │             ▼
         │  ├─────────────────────┤ │   ┌────────────────────┐
         │  │ Elimination Engine  │ │──►│     PostgreSQL      │
         │  └─────────────────────┘ │   │  authoritative SoR  │
         └──────────────┬───────────┘   │  (shared schema,    │
                        │               │   tenant_id scoped) │
                        └──────────────►│  answers (durable)  │
                                        └────────────────────┘
```

Message/queue transport between the API and engine workers (e.g. Redis
Streams, SQS, or a Postgres-backed outbox) is a `/neutron:plan` decision; the
spec assumes a durable, at-least-once command channel plus idempotent
consumers.

---

## 2. Component Responsibilities

| Component | Owns |
|---|---|
| **Next.js Web App** | All UI: org/super-admin consoles, contest builder, moderator console, participant live view. Renders server timers as display only; never authoritative. |
| **FastAPI API Service** | HTTP endpoints (orgs, contests, configuration, questions, registration, results); WebSocket gateway (question push, answer submit, leaderboard/elimination events); authentication, JWT issue/verify, RBAC, tenant context resolution. |
| **Tenant Context** | Resolves `tenant_id` from JWT on every request; injects it into all queries; rejects cross-tenant access. Super Admin operates platform-scoped. |
| **Execution Engine (worker)** | Authoritative timers, reveal scheduling, submission-window open/close, per-question and per-group progression, moderator overrides. Tracks per-participant wildcard usage state (cooldown counters, group carryover/reset) in Redis for the duration of the contest. |
| **Scoring Engine (worker)** | Applies the Mode-derived scoring model (Fixed / Time-Based with configurable bands or linear decay), Second Chance / Skip adjustments, negative marking (value configured per Configuration Block), and tie-break data capture (`total_response_time_ms`, `wrong_answer_count`, `last_correct_submission_at`). Computes group-score rollup (Sum, Weighted Sum, Best N Groups). At-most-once per accepted answer. |
| **Leaderboard Engine (worker)** | Maintains Redis sorted sets per view (Contest / Group / Survivor); applies ranking criterion (Score Only, Score + Time, Accuracy) with the criterion-specific tie-break sequence from FR-30, plus tie display mode; pushes updates; rebuildable from Postgres. In Masked visibility mode the fan-out layer redacts all entries except the requesting participant's before pushing. |
| **Elimination Engine (worker)** | Evaluates elimination rules at checkpoints, computes eliminated/survivor sets, locks survivor list, emits notifications. |
| **PostgreSQL** | Authoritative system of record for all tenant data and accepted answers (durability source of truth). |
| **Redis** | Leaderboard ZSETs, WebSocket pub/sub fan-out, presence, and idempotency/dedupe keys. Treated as rebuildable cache, never as sole source of truth. |

---

## 3. Data Flow

### 3.1 Answer submission (critical path)
1. Participant submits an answer over WebSocket.
2. API validates: contest Live, question's submission window open per
   **server-side** close time (FR-20), participant not eliminated.
3. API records the answer **durably in PostgreSQL** with the server-accept
   timestamp and an idempotency key `(contest_id, question_id, participant_id,
   attempt_no)`. `attempt_no` starts at 1 for the first submission and
   increments for each Second-Chance retry. This write is the durability
   boundary (FR-38, FR-40).
4. API returns an acknowledgement (accepted/rejected) to the participant
   (FR-41).
5. A scoring command is published to the engine channel referencing the
   persisted answer ID.
6. Scoring Engine consumes idempotently (dedupe on answer ID): computes points
   per the active block's model, writes the score row (at-most-once, FR-39),
   and signals the Leaderboard Engine.
7. Leaderboard Engine updates the relevant Redis ZSET(s) and pushes deltas to
   subscribed clients.

### 3.2 Question reveal
1. Execution Engine determines reveal time per Reveal Mode (Automatic =
   schedule; Moderator-Controlled = on moderator trigger).
2. At reveal, it publishes the question payload to the contest's Redis pub/sub
   channel; the API fans out to all WS connections within 200ms (NFR-1).
3. The submission window opens; the server-side close time is recorded.

### 3.3 Elimination checkpoint
1. Execution Engine reaches a configured checkpoint and signals the Elimination
   Engine.
2. Elimination Engine evaluates the rule set against authoritative scores.
   Rules are combined with a single top-level operator (AND | OR) configured
   in the block; all enabled rules participate. It computes the eliminated set,
   persists it, locks the survivor list, and emits notifications.
3. Leaderboard Engine refreshes the Survivor Leaderboard.
4. Execution Engine pauses to display the group leaderboard and announce
   eliminations before applying the next group's Configuration Block (FR-21).

### 3.4 Recovery
1. On restart, workers reload contest state from PostgreSQL (FR-42).
2. Unscored-but-persisted answers are re-driven through the (idempotent)
   Scoring Engine; dedupe prevents double-scoring (FR-39).
3. Leaderboard ZSETs are rebuilt from authoritative score rows if Redis was
   lost (FR-44).

---

## 4. Technology Decisions (made) & Rationale

| Decision | Choice | Rationale |
|---|---|---|
| Backend language/framework | Python + FastAPI | Async I/O suits high-concurrency WebSocket fan-out; first-class typing/Pydantic for contract validation; team/stack preference. |
| Frontend | Next.js + TypeScript | SSR/SPA hybrid, strong TS ergonomics, suits admin consoles + live participant view. |
| Authoritative store | PostgreSQL | Relational model fits tenant/contest/config/answer relationships; transactional durability underpins the answer-durability guarantees. |
| Cache / real-time | Redis | Sorted sets give O(log n) ranking; pub/sub enables low-latency fan-out; treated as rebuildable. |
| Real-time transport | WebSockets | Required for ≤200ms reveal push and live leaderboard updates. |
| Multi-tenancy (spec assumption) | Shared schema + `tenant_id`, row-level enforcement | Lowest ops overhead, scales to many tenants; isolation enforced in the data-access layer and verified by tests. Final infra confirmed in /neutron:plan. |
| Auth | JWT (access + refresh), email/password | Stateless, scales horizontally; carries role + tenant scope. |
| Cloud | AWS | From kickoff. |
| Super Admin bootstrap | Deployment-time seed (env var or migration) | The first Super Admin is created outside the tenant API; subsequent Super Admins can only be created by an existing Super Admin. |

---

## 5. Error Handling Strategy

- **Validation errors (4xx):** Pydantic-validated request bodies; structured
  error responses `{ error: { code, message, details } }`. Invalid contest-state
  transitions (e.g. editing a locked config) return `409 Conflict`.
- **Authn/Authz:** `401` for missing/invalid token; `403` for role/tenant
  violations. Cross-tenant access attempts are denied and logged as security
  events.
- **Late submissions:** answers past the server-side close time return a
  rejected acknowledgement (not an error), with reason `window_closed`
  (FR-20).
- **Durability faults:** if the durable answer write fails, the API returns a
  non-accepted acknowledgement and the client may retry; the idempotency key
  ensures a retried-and-eventually-persisted answer is not double-recorded
  (FR-39/41).
- **Engine failures:** commands are consumed idempotently; transient failures
  are retried with backoff; poison messages are dead-lettered for inspection
  without blocking the contest.
- **WebSocket drops / network faults:** treated as transient; on reconnect the
  client re-subscribes and the server restores state and the open submission
  window within 3 seconds (FR-43, NFR-7). Transient network faults must not
  lose answers or advance the contest incorrectly; affected participants are
  notified.
- **5xx:** unexpected errors return a generic message with a correlation ID;
  full detail is logged server-side only.

---

## 6. Logging & Observability

- **Structured logs** (JSON) with correlation IDs, `tenant_id`, `contest_id`,
  and `participant_id` where applicable. Never log secrets or full JWTs.
- **Audit logs** for: org create/suspend, lifecycle transitions, wildcard
  activations (FR-27), elimination events, and tie-break resolutions (FR-15).
- **Metrics:** reveal fan-out latency, leaderboard push latency, answer-accept
  rate, scoring lag, queue depth, WS connection count, recovery duration —
  aligned to NFR targets.
- **Tracing:** distributed traces across API → queue → engine workers for the
  answer/scoring path.
- **Health/readiness** endpoints for API and workers; alerting on NFR
  breaches (latency, queue depth, scoring lag).

Concrete tooling (e.g. OpenTelemetry, CloudWatch, Prometheus/Grafana) is a
/neutron:plan decision.

---

## 7. Security Approach (high level)

Detail lives in `.neutron/security.md`; high-level here:

- **Tenant isolation** is the primary security boundary: `tenant_id` enforced
  on every data access; automated tests assert no cross-tenant reads/writes
  (NFR-8).
- **AuthN:** JWT access/refresh; passwords hashed with a strong adaptive
  algorithm (e.g. argon2/bcrypt); short-lived access tokens, rotating refresh.
- **AuthZ:** role-based (Super Admin, Org Admin, Moderator, Participant)
  enforced per endpoint and per WS action.
- **Transport:** TLS for HTTP and WSS for WebSockets.
- **Input validation:** all inputs validated server-side (Pydantic); answers
  and timing never trusted from the client.
- **Anti-abuse:** rate limiting on auth and submission endpoints; submission
  windows enforced server-side.
- **Secrets:** managed via cloud secret store; never in source or logs.

---

## 8. Constraints & Assumptions

- All timing, scoring, and ranking are server-authoritative; client clocks are
  display-only (FR-17).
- Multi-tenancy is foundational; the shared-schema + `tenant_id` model is the
  spec's working assumption pending /neutron:plan confirmation.
- Questions are multiple-choice in this engine version.
- Data is retained indefinitely; Archived contests are read-only (FR-45). Archival is a state transition enforced at the API and RBAC layers; no data migration occurs on archive.
- A durable, at-least-once command channel with idempotent consumers is assumed
  between API and engine workers (concrete technology TBD in /neutron:plan).
- Custom Milestone checkpoints are evaluated by the Execution Engine against
  an admin-defined absolute timestamp or event trigger.
- Compliance recorded as "none" (open question).

---

## 9. Out of Scope (technical)

- Concrete queue/streaming technology selection and infra sizing (→
  /neutron:plan).
- CI/CD pipeline and IaC definitions (→ /neutron:init, /neutron:plan).
- Final tenant-isolation infra (schema vs. db) beyond the spec assumption.
- Observability tooling selection.
- Mobile clients, SSO, billing, non-MCQ question types (see product-spec §6).
