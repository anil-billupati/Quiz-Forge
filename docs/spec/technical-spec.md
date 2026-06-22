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
FastAPI system running on ASGI/async workers: a REST API service for
administration and authoring, a horizontally scalable WebSocket gateway for
live participation, and background worker pools that run the server-authoritative
contest engines (Execution, Scoring, Leaderboard, Elimination). The frontend
is a Next.js/TypeScript web application. PostgreSQL is the authoritative store;
Redis provides leaderboard computation/cache, real-time fan-out, and the command
stream between API and workers.

### 1.1 Component Diagram (text)

```
                         ┌─────────────────────────────────┐
                         │   Next.js / TypeScript (Web)    │
                         │   Admin · Moderator · Player    │
                         └───────────┬───────────┬─────────┘
                                     │           │
                            HTTPS (REST)       WSS (live)
                                     │           │
                   ┌─────────────────┘           └─────────────────┐
                   ▼                                                 ▼
    ┌────────────────────────────┐                      ┌──────────────────────────┐
    │   FastAPI REST API Service  │                      │  FastAPI WS Gateway      │
    │  ┌──────────────────────┐  │                      │  ┌────────────────────┐  │
    │  │ Auth/RBAC · JWT      │  │                      │  │ Connection mgmt    │  │
    │  │ Tenant context       │  │                      │  │ Tenant validation  │  │
    │  │ Rate limiting        │  │                      │  │ Per-contest pub/sub│  │
    │  └──────────────────────┘  │                      │  └────────────────────┘  │
    │  REST: orgs, contests,     │                      │  WS: question push,      │
    │        config, questions,  │                      │      answer submit,      │
    │        registration,       │                      │      leaderboard push,   │
    │        results             │                      │      elimination events  │
    └─────────────┬──────────────┘                      └───────────┬──────────────┘
                  │                                                 │
                  │ enqueue/commands                                 │
                  │                                                  │
    ┌─────────────▼──────────────────────────────────────────────────▼─────────────┐
    │                              Redis Cluster                                    │
    │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐   │
    │  │ Command Stream  │  │ Pub/Sub Channels│  │ Leaderboard ZSETs / Presence│   │
    │  │ (Redis Streams) │  │ (per contest)   │  │ / Dedupe keys / Rate limits │   │
    │  └────────┬────────┘  └─────────────────┘  └─────────────────────────────┘   │
    │           │                                                                   │
    │           │ consumer groups                                                   │
    │           ▼                                                                   │
    │  ┌──────────────────────────────────────────────────────────────────────┐    │
    │  │                     Engine Worker Pools                               │    │
    │  │  ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐ ┌───────────┐ │    │
    │  │  │   Execution  │ │    Scoring   │ │   Leaderboard   │ │Elimination│ │    │
    │  │  │   Engine     │ │    Engine    │ │     Engine      │ │  Engine   │ │    │
    │  │  └──────────────┘ └──────────────┘ └─────────────────┘ └───────────┘ │    │
    │  └──────────────────────────────────────────────────────────────────────┘    │
    └──────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ authoritative writes / reads
                                           ▼
                              ┌──────────────────────────────┐
                              │    PostgreSQL (RDS Multi-AZ)  │
                              │  authoritative system of record│
                              │  shared schema, tenant_id scoped│
                              │  answers, scores, config durable│
                              └──────────────────────────────┘
```

**Command transport:** Redis Streams on AWS ElastiCache for Redis Cluster.
Each command carries `tenant_id` and `contest_id`; consumers are partitioned by
`contest_id` hash for isolation. Delivery is at-least-once; consumers are
idempotent (dedupe on `answer_submission_id` or command UUID). Failed commands
are retried with exponential backoff and dead-lettered after max attempts.

### 1.2 Auto-scaling triggers

| Service | Scale-out trigger | Scale-in trigger | Notes |
|---|---|---|---|
| REST API | CPU > 70 % or p99 latency > 200 ms | CPU < 30 % for 5 min | Stateless; scale by request count and latency. |
| WS Gateway | Connection count > 2,000 per pod or CPU > 70 % | Connections < 500 per pod | Sticky sessions via ALB cookie; memory-bound by open sockets. |
| Scoring Workers | Queue depth per partition > 100 or backlog age > 5 s | Queue depth < 20 for 5 min | Partition by `contest_id` hash; add replicas to handle bursts. |
| Leaderboard Workers | Update lag > 1 s or queue depth > 200 | Update lag < 100 ms for 5 min | Scale independently of scoring workers. |
| Execution Engine | N/A per contest; singleton per contest | N/A | One active Execution Engine instance per live contest; contest-level failover via leader election on Redis. |

---

## 2. Component Responsibilities

| Component | Owns |
|---|---|
| **Next.js Web App** | All UI: org/super-admin consoles, contest builder, moderator console, participant live view. Renders server timers as display only; never authoritative. |
| **FastAPI REST API Service** | HTTP endpoints (orgs, contests, configuration, questions, registration, results); authentication, JWT issue/verify, RBAC, tenant context resolution, rate limiting. |
| **FastAPI WebSocket Gateway** | Horizontally scalable live participation service. Holds long-lived WS connections, validates tenant/role/registration per connection, subscribes to per-contest Redis pub/sub channels, fans out questions/leaderboards/elimination events, and forwards answer/wildcard submissions to the command stream. Stateless across connections. |
| **Tenant Context** | FastAPI dependency/middleware that resolves `tenant_id` from the JWT on every request and stores it in a request-scoped context var. All repository/SQLAlchemy queries filter by `tenant_id` automatically via a base mixin or event listener; unscoped queries fail closed in production. Super Admin endpoints operate platform-scoped but still validate the requested tenant. See §7. |
| **Execution Engine (worker)** | Authoritative timers, reveal scheduling, submission-window open/close, per-question and per-group progression, moderator overrides. Tracks per-participant wildcard usage state (cooldown counters, group carryover/reset) in Redis for the duration of the contest. |
| **Scoring Engine (worker)** | Applies the Mode-derived scoring model (Fixed / Time-Based with configurable bands or linear decay), Second Chance / Skip adjustments, negative marking (value configured per Configuration Block), and tie-break data capture (`total_response_time_ms`, `wrong_answer_count`, `last_correct_submission_at`). Computes group-score rollup (Sum, Weighted Sum, Best N Groups). At-most-once per accepted answer. |
| **Leaderboard Engine (worker)** | Maintains Redis sorted sets per view (Contest / Group / Survivor); applies ranking criterion (Score Only, Score + Time, Accuracy) with the criterion-specific tie-break sequence from FR-30, plus tie display mode; pushes updates; rebuildable from Postgres. In `MASKED` visibility the engine computes the full ranking once, then the WS gateway emits a per-participant payload containing only that participant's rank/score (O(n log n) compute + O(n) fan-out), avoiding broadcast of the full board. |
| **Elimination Engine (worker)** | Evaluates elimination rules at checkpoints, computes eliminated/survivor sets, locks survivor list, emits notifications. |
| **PostgreSQL** | Authoritative system of record for all tenant data and accepted answers (durability source of truth). |
| **Redis** | AWS ElastiCache for Redis Cluster. Key namespace `tenant:{tenant_id}:contest:{contest_id}:...`. Holds leaderboard ZSETs, per-contest pub/sub channels, WS presence, idempotency/dedupe keys, rate-limit counters, and the command stream. Treated as rebuildable cache/transport, never as sole source of truth. Transient keys TTL = 24 h after contest completion; eviction policy `allkeys-lru`. |

---

## 3. Data Flow

### 3.1 Answer submission (critical path)
1. Participant submits an answer over WebSocket.
2. API validates: contest Live, question's submission window open per
   **server-side** close time (FR-20), participant not eliminated.
3. API records the answer **durably in PostgreSQL** with the server-accept
   timestamp and an `idempotency_hash` derived deterministically from
   `(contest_id, question_id, participant_id, attempt_no)`. `attempt_no` starts
   at 1 for the first submission and increments for each Second-Chance retry.
   This write is the durability boundary (FR-38, FR-40).
4. API returns an acknowledgement (accepted/rejected) to the participant
   (FR-41).
5. A scoring command is published to the contest's Redis Stream carrying
   `tenant_id`, `contest_id`, and the persisted `answer_submission_id`.
6. Scoring Engine consumes idempotently (dedupe on answer submission ID):
   re-establishes tenant context from the command, computes points per the
   active block's model, writes the score row (at-most-once, FR-39), and
   signals the Leaderboard Engine.
7. Leaderboard Engine updates the relevant Redis ZSET(s) and pushes deltas to
   subscribed clients.

### 3.2 Question reveal
1. Execution Engine determines reveal time per Reveal Mode (Automatic =
   schedule; Moderator-Controlled = on moderator trigger).
2. At reveal, the Execution Engine publishes the question payload to the
   contest's Redis pub/sub channel. The WebSocket gateway subscribes to this
   channel and fans the payload out to all connected participants within the
   contest, targeting p99 ≤ 200 ms (NFR-1).
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
| Backend language/framework | Python + FastAPI (ASGI) | Async I/O suits high-concurrency WebSocket fan-out; first-class typing/Pydantic for contract validation; team/stack preference. |
| Frontend | Next.js + TypeScript | SSR/SPA hybrid, strong TS ergonomics, suits admin consoles + live participant view. |
| Authoritative store | PostgreSQL (AWS RDS Multi-AZ) | Relational model fits tenant/contest/config/answer relationships; transactional durability underpins the answer-durability guarantees. Connection pool (asyncpg/SQLAlchemy) min 10 / max 100 per instance; PgBouncer if needed. Read replica for reports. Key indexes: `(tenant_id, contest_id, participant_id)` on `registration`; `(tenant_id, idempotency_key)` and `(tenant_id, contest_id, question_id, participant_id, attempt_no)` on `answer_submission`; `(tenant_id, answer_submission_id)` on `score`. Partition `answer_submission` and `score` by `contest_id` once table size exceeds threshold. |
| Cache / real-time / queue | Redis (AWS ElastiCache for Redis Cluster, cluster mode) | Sorted sets give O(log n) ranking; pub/sub enables low-latency fan-out; Redis Streams is the command transport. Treated as rebuildable. Key namespace includes `tenant_id`. |
| Real-time transport | WebSockets | Required for ≤200ms reveal push and live leaderboard updates. WS gateway is a separate horizontally scalable service behind an ALB. |
| Multi-tenancy | Shared schema + `tenant_id`, row-level enforcement | Lowest ops overhead, scales to many tenants; isolation enforced via SQLAlchemy mixin/RLS and verified by tests. |
| Auth | JWT (access + refresh), email/password | Stateless, scales horizontally; carries role + tenant scope. |
| Cloud | AWS | From kickoff. |
| Compute platform | ECS Fargate or EKS (to be finalized in /neutron:plan) | Containerized services with independent auto-scaling policies per service. |
| Edge protection | AWS WAF + ALB/CloudFront | L7 DDoS protection and rate limiting. |
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
  non-accepted acknowledgement and the client may retry; the deterministic
  `idempotency_hash` ensures a retried-and-eventually-persisted answer is not
  double-recorded (FR-39/41).
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

Tooling: OpenTelemetry SDK + AWS CloudWatch (or Prometheus/Grafana if the
compute platform is EKS). Traces use adaptive sampling: 100 % for error paths,
1–10 % for normal traffic.

### 6.1 Backup, Recovery, and SLOs

| Target | Value | Notes |
|---|---|---|
| RPO (answers) | ≤ 5 minutes | RDS Multi-AZ with automated backups; answer durability is the critical path. |
| RTO (full service) | ≤ 30 minutes | Includes container restart, queue replay, and Redis rebuild from PostgreSQL. |
| RDS backups | 35 days | Automated; cross-region snapshots optional. |
| Redis | Rebuildable cache | Leaderboard ZSETs and presence rebuilt from authoritative Score/Registration rows. |
| Audit logs | 1 year | Retained in CloudWatch Logs with tamper-evident storage. |

---

## 7. Security Approach (high level)

Detail lives in `.neutron/security.md`; high-level here:

- **Tenant isolation** is the primary security boundary: `tenant_id` enforced
  on every data access; automated tests assert no cross-tenant reads/writes
  (NFR-8).
- **AuthN:** JWT access/refresh; passwords hashed with a strong adaptive
  algorithm (e.g. argon2/bcrypt); short-lived access tokens, rotating refresh.
- **AuthZ:** role-based (Super Admin, Org Admin, Moderator, Participant)
  enforced per endpoint and per WS action. The role-permission matrix in
  `product-spec.md` §2.5 is the source of truth; every endpoint and WebSocket
  action is checked against it.
- **Transport:** TLS for HTTP and WSS for WebSockets.
- **Input validation:** all inputs validated server-side (Pydantic); answers
  and timing never trusted from the client.
- **Anti-abuse:** rate limiting enforced at AWS WAF/ALB and application level
  (Redis token bucket). Default limits: `/auth/login` 5 attempts/min per IP;
  REST API 100 req/min per user and 1,000 req/min per tenant; WS messages
  10 msg/sec per connection; answer submissions 1/sec per participant.
  Submission windows are enforced server-side.
- **Secrets:** managed via cloud secret store; never in source or logs.

### 7.1 Tenant enforcement mechanism

1. **JWT claims:** every access token carries `role` and, for tenant-scoped
   roles, `tenant_id`. The `tenant_slug` in the login request resolves to the
   canonical `Organization.id`.
2. **Request context:** FastAPI middleware/dependency reads the token, validates
   signature/expiry, and stores `tenant_id` in a context variable for the
   duration of the request.
3. **Automatic query scoping:** a SQLAlchemy mixin on all tenant-scoped models
   adds a `tenant_id` filter to every SELECT/UPDATE/DELETE. Production config
   enables a runtime assertion that rejects any unscoped query.
4. **Composite foreign keys:** every child table references its parent on
   `(tenant_id, parent_id)` so a bug cannot link a row to a parent in another
   tenant (see `domain-model.md`).
5. **Defense in depth:** PostgreSQL Row-Level Security (RLS) policies enforce
   `tenant_id` filtering at the database level for an additional barrier.
6. **Cross-tenant access:** any request whose JWT `tenant_id` does not match
   the resource's `tenant_id` is denied with `403` and logged as a security
   event. Super Admin platform endpoints may list all tenants but cannot
   impersonate a tenant's users.
7. **Worker context:** engine commands carry `tenant_id` in the command envelope,
   or workers re-resolve it from the authoritative `AnswerSubmission` row before
   any query.
8. **Validation:** the automated tenant-isolation suite (NFR-8) parameterizes
   every tenant-scoped endpoint and queries child tables directly to assert
   no leakage.

---

## 8. Constraints & Assumptions

- All timing, scoring, and ranking are server-authoritative; client clocks are
  display-only (FR-17).
- Multi-tenancy is foundational; the shared-schema + `tenant_id` model is the
  spec's chosen isolation strategy.
- Questions are multiple-choice in this engine version.
- Data is retained indefinitely while a tenant is active; Archived contests are
  read-only (FR-45). Archival is a state transition enforced at the API and RBAC
  layers; no data migration occurs on archive.
- Command transport is Redis Streams on ElastiCache for Redis Cluster; workers
  are partitioned by `contest_id` hash for isolation.
- Custom Milestone checkpoints are evaluated by the Execution Engine against
  an admin-defined absolute timestamp or event trigger.
- Compliance baseline is SOC 2 Type II and GDPR readiness; full certification
  scope to be confirmed with stakeholders before production launch.

---

## 9. Out of Scope (technical)

- Exact ECS/EKS cluster sizing, node instance types, and cost estimates
  (→ /neutron:plan).
- CI/CD pipeline and IaC definitions (→ /neutron:init, /neutron:plan).
- Schema-per-tenant or database-per-tenant isolation alternatives beyond the
  chosen shared-schema model.
- Third-party observability tooling selection beyond the OpenTelemetry + AWS
  CloudWatch baseline.
- Billing and payment processing (usage metering is in scope as a foundation).
- Mobile clients, SSO, billing, non-MCQ question types (see product-spec §6).
