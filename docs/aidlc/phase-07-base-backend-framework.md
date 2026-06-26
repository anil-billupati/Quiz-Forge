# ContestForge — AIDLC Phase 7: Base Backend Framework

| | |
|---|---|
| **Phase** | 7 of 25 — Base Backend Framework |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Source** | Phase 5 (Architecture), Phase 4 (Data Flows); technical-spec §1–7; existing `backend/` (Units 1–2) |
| **Depends on** | Phase 5/6 — approved |
| **Feeds** | Phase 10 (Backend Tasks), Phase 13 (DB), Phase 14 (API), Phase 23 (Folder structure), Phase 24 (Coding standards) |

---

## Goal
Define the **foundational backend framework** — the cross-cutting scaffolding every feature module
plugs into — so feature work (Units 3+) never re-invents tenant scoping, the command bus, the outbox,
auth, error handling, or observability. This phase specifies the **app composition, hexagonal
ports/adapters, tenant-context enforcement, repository base, command-bus + outbox + worker runtime,
configuration/secrets, auth/session, the error model, and the test harness**. It builds on what
already exists (`backend/` Units 1–2: platform foundation + tenancy/identity) and makes the patterns
explicit and reusable. Folder layout is Phase 23; naming/style conventions are Phase 24.

## Assumptions
- Python + **FastAPI/ASGI**, async throughout; **SQLAlchemy (async) + asyncpg**; **Alembic** migrations;
  **Pydantic v2** for I/O contracts; **Redis** (redis-py async) for streams/pub-sub/zset/presence.
- The repo already has working foundations to extend, not replace: `app/main.py`, `app/config.py`,
  `app/db.py`, `app/redis_client.py`, `app/middleware/{tenant_context,errors,logging}.py`,
  `app/models/base.py`, `app/security/{passwords,tokens}.py`, `app/dependencies.py`, `migrations/`,
  and a `tests/` harness (Units 1–2). This phase formalises and extends them.
- One codebase, **three runtime roles** (Phase 5): the same app object/module graph runs as API, WS
  gateway, or worker via an entrypoint switch (`app/cli.py` exists).
- All design principles apply; hexagonal ports keep the domain framework-agnostic and testable.

## Functional Requirements
*(The base backend framework — this phase's substance.)*

### 7.1 Application composition & runtime roles
- **Single app graph, role-selected entrypoint:** `API` (FastAPI ASGI), `WS_GATEWAY` (FastAPI ASGI with
  WS routes), `WORKER` (consumer loop per engine kind), `RELAY/SCHEDULER` (outbox relay + go-live
  scheduler). Selected via env/CLI; shares config, models, ports, adapters.
- **Lifespan management:** async startup/shutdown wires adapters (DB engine/pool, Redis client, OTel),
  exposes `/health` (liveness) and `/ready` (DB+Redis dependency checks → 503 if not ready) — already
  present for API; extended to workers.
- **Dependency injection:** FastAPI `Depends` for request scope (auth principal, tenant context, unit
  of work); a lightweight container/factory for worker scope (no request).

### 7.2 Hexagonal ports & adapters (the contract layer)
Ports (interfaces) the domain/application layers depend on; adapters implement them:

| Port | Responsibility | Default adapter |
|---|---|---|
| `Repository[T]` | Persistence per aggregate, tenant-scoped | SQLAlchemy async repo |
| `UnitOfWork` | Transaction boundary; commits domain change **+ outbox** atomically | SQLAlchemy session txn |
| `EventBus` (producer) | Publish commands/events | Redis Streams adapter |
| `EventConsumer` | Consume with consumer-group + idempotency | Redis Streams adapter |
| `Cache` / `LeaderboardStore` | ZSET ops, presence, dedupe, rate counters | Redis adapter |
| `Clock` | Authoritative time | DB `clock_timestamp()` / monotonic |
| `Notifier` | Persist + push notifications | PG + pub/sub adapter |
| `PasswordHasher`, `TokenService` | Argon2/bcrypt; JWT issue/verify | existing `security/*` |
| `BlobStore` | Result exports | S3 adapter |

**Rule:** application services orchestrate use cases (Phase 3) against ports only; no domain code
imports SQLAlchemy/Redis. This is the microservice-extraction seam (Phase 5 §D3).

### 7.3 Tenant context enforcement (fail-closed)
- **Request path:** ASGI middleware reads/validates the JWT, resolves `tenant_id` + `role` into a
  request-scoped `contextvar` (`tenant_context.py` exists). Super Admin → platform scope (null tenant).
- **Auto-scoping:** a `TenantScopedMixin` + SQLAlchemy event listener injects a `tenant_id` filter into
  every SELECT/UPDATE/DELETE on tenant-scoped models; **a query lacking tenant scope raises in prod**
  (fail-closed). Composite FKs `(tenant_id, parent_id)` enforce at the DB; RLS as defense-in-depth.
- **Worker path:** consumers re-establish tenant context from the **command envelope** (`tenant_id`)
  or the authoritative row before any query — never ambient.
- **Cross-tenant attempt:** denied `403` (or `404` where existence is sensitive) and logged as a
  security event.
*Trace:* tech-spec §7.1; NFR-8; ADR-001.

### 7.4 Persistence & Unit of Work
- **Async SQLAlchemy** with `(min 10 / max 100)` pool per instance; PgBouncer (transaction pooling)
  optional. UUIDv7 PKs (write locality). Native enums; `smallint`-mapped enums for hottest tables if
  benchmarked.
- **UnitOfWork** wraps a session transaction so a state change **and its `OutboxEvent`** commit
  atomically (the outbox invariant, BR-24).
- **Base repository** offers tenant-scoped CRUD + cursor pagination (opaque cursor, matches API
  `Page` envelope) + optimistic concurrency (`version`) for `ContestExecutionState`.
- **Idempotency helpers:** deterministic `idempotency_hash` builder for `AnswerSubmission`; unique
  constraints are the enforcement, code computes the key.

### 7.5 Command bus, outbox & worker runtime
- **Transactional outbox:** `OutboxEvent` (PENDING→PROCESSED→DEAD_LETTER) written in the UoW; a
  **Relay** role polls PENDING (partial index) and publishes to Redis Streams, marking PROCESSED only
  after enqueue. (Mechanism = poller in v1; logical-replication/Debezium deferred — Phase 5 §D5.)
- **Consumer framework:** consumer-group per engine kind, **partitioned by `contest_id` hash**;
  at-least-once delivery; **idempotent handler base** (dedupe on submission id / command UUID via
  `{{Dedupe}}`); retry with exponential backoff; **dead-letter** after max attempts without blocking
  the contest.
- **Execution singleton:** per-contest **leader election** on Redis (lease + heartbeat) so exactly one
  Execution instance drives a live contest; fast re-election on failure (Phase 5 risk mitigation).
- **Scheduler:** the relay/scheduler role also performs **idempotent auto-go-live** (version-guarded)
  and **host-presence** heartbeat expiry handling for auto-pause.
*Trace:* ADR-002; DF-8/9/10/11/12; BR-23/24.

### 7.6 Configuration & secrets
- **Typed settings** (`config.py`, Pydantic `BaseSettings`): env-driven, validated at startup, per-role
  overrides. Secrets (DB/Redis creds, JWT keys) from the cloud secret store — **never** in source/logs.
- **Feature flags / tenant defaults** read from `Organization.settings`/`TenantSettings`.

### 7.7 AuthN/AuthZ framework
- **JWT** access (short-lived) + refresh (rotating, family-tracked) — `security/tokens.py`, `RefreshToken`
  rotation (BR-26). Passwords hashed with Argon2/bcrypt (`security/passwords.py`).
- **RBAC dependency:** a reusable `require_role(...)`/`require_perm(...)` dependency checks the caller
  against the **role-permission matrix** (single source of truth) — applied per REST endpoint and per
  **WS action**. Bootstrap Super Admin via migration/seed (`cli.py`), not the API.
- **Rate limiting:** Redis token-bucket middleware (per user / per tenant / per IP; per-connection WS
  message rate) with the documented default limits.

### 7.8 WebSocket gateway framework
- **Ticket auth:** single-use, short-lived connection ticket minted by REST, consumed at WS upgrade
  (no token in URL). Principal resolved pre-upgrade.
- **Connection registry & presence:** per-connection tenant/role/registration validation; participant
  and **host presence** recorded in Redis with heartbeat TTL.
- **Channel fan-out:** subscribe connections to per-contest pub/sub; outbound event envelope schema
  shared with the frontend (Phase 15). Inbound actions (`answer.submit`, `wildcard.activate`,
  `moderator.reveal/advance`) validated and forwarded to the command path.

### 7.9 Error model & exception handling
- **Single error shape** `{ error: { code, message, details } }` (matches api-contracts). A central
  exception-handler (`middleware/errors.py`) maps domain/application exceptions → HTTP/WS status:
  domain `ValidationError`→422, `StateConflict`→409, `NotFound`→404, `Forbidden`/cross-tenant→403,
  auth→401, durability-fault→non-accepted ack, unexpected→500 + correlation id (detail logged
  server-side only). Late submit → **rejected ack, not an error** (DF-8).

### 7.10 Observability framework
- **Structured JSON logs** with correlation id + `tenant_id`/`contest_id`/`participant_id`; **no
  secrets/JWTs**. **OTel** traces across API→bus→workers (answer/scoring path), adaptive sampling
  (100% errors, 1–10% normal). **Metrics** per NFR (reveal latency, scoring lag, queue depth, WS
  count, recovery duration). Health/readiness per role; alerts on NFR breach.

### 7.11 Testing harness (base)
- **Pytest** + async fixtures; ephemeral PostgreSQL + Redis (containers) per the existing
  `tests/conftest.py`. Layers: **unit** (domain/services via fake adapters — ports make this possible),
  **integration** (real PG/Redis: repos, migrations, tenant scoping), **contract** (schemathesis vs
  `api-contracts.yaml`), **tenant-isolation suite** (parameterised over every tenant-scoped resource,
  NFR-8). Tests live **within the unit** of code (testing-strategy).

## Non-functional Requirements
- **Fail-closed tenancy:** no code path can issue an unscoped tenant query in production.
- **Atomic outbox:** no state change is published without a committed outbox row in the same txn.
- **Idempotency everywhere on consume:** every worker handler is safe to run twice.
- **Async, non-blocking:** no sync I/O on the event loop in API/WS roles.
- **Testability:** domain/application layers unit-testable with zero infrastructure (ports + fakes).
- **Observability by default:** every request/command carries correlation + tenant context.

## Edge Cases
- **Outbox row committed but relay down:** event stays PENDING; replayed on relay recovery (no loss).
- **Consumer crash mid-handle:** at-least-once redelivery + idempotent handler → no double effect.
- **Leader lease expiry while leader alive (clock skew):** brief dual-leader risk → guarded by
  optimistic `version` on `ContestExecutionState` (writes from a stale leader rejected).
- **JWT valid but tenant suspended:** request rejected (GX4) even with a good token.
- **Migration applied to one role's instance before others roll:** backward-compatible migrations
  required (expand/contract); enforced as a backend rule (Phase 22/24).
- **Rate-limit counter store (Redis) down:** fail-open vs fail-closed decision — default **fail-open
  for product traffic, fail-closed for `/auth/login`** (security-sensitive); documented.

## Future Considerations
- **Outbox via logical replication/CDC** instead of polling (throughput) — Phase 5 §D5.
- **PgBouncer / connection-pool tuning** under peak (Phase 21).
- **Service extraction** of a worker kind — ports already isolate it.
- **Pluggable notifier** (email/SMS) behind the `Notifier` port when transport is added.
- **Multi-region** adapter configuration (data residency).

## Risks
- **Hexagonal overhead vs delivery speed:** strict ports can feel heavy for simple CRUD. *Mitigation:*
  thin repositories for CRUD; full port discipline reserved for the engine/critical paths (KISS).
- **Tenant-scoping bypass via raw SQL/escape hatches:** a single raw query can leak. *Mitigation:*
  fail-closed listener + RLS + isolation suite; raw SQL must pass explicit tenant param (lint/review).
- **Outbox poller latency at scale:** polling adds fan-out delay. *Mitigation:* tuned poll interval +
  partial index + metric/alert; CDC path reserved.
- **Dual-leader window:** clock skew in lease-based election. *Mitigation:* version-guarded execution
  state writes (correctness preserved even if two leaders briefly exist).
- **Idempotency-key correctness:** a wrong hash composition breaks at-most-once. *Mitigation:* single
  shared builder + unique constraint + dedicated tests.

## Deliverables
### D1 — Ports & adapters catalogue
The port interfaces (7.2) and their default Redis/PG/S3 adapters; the domain↔infra dependency rule.

### D2 — Cross-cutting framework specs
Tenant context (7.3), UoW + base repository + idempotency (7.4), command bus/outbox/worker runtime +
leader election + scheduler (7.5), config/secrets (7.6), auth/RBAC/rate-limit (7.7), WS gateway (7.8).

### D3 — Error & observability framework
Single error model + exception mapping (7.9); logging/tracing/metrics/health baseline (7.10).

### D4 — Test harness baseline
Unit/integration/contract/isolation layers + fixtures (7.11); tests co-located with code.

### D5 — Reuse map (what exists vs what this phase adds)
| Concern | Exists (Units 1–2) | Added/formalised here |
|---|---|---|
| App/config/db/redis | ✅ | role entrypoints, worker lifespan |
| Tenant context middleware | ✅ | fail-closed listener rule, worker re-establishment |
| Security (pwd/tokens) | ✅ | RBAC dependency + WS-action checks, rate-limit middleware |
| Error/logging middleware | ✅ | full exception→status mapping, correlation propagation |
| Models base | ✅ | ports, UoW, base repo, outbox relay, consumer base, leader election |
| Tests | ✅ | contract + isolation suites, fake-adapter unit layer |

### D6 — Open questions carried forward
1. Outbox relay mechanism (poller vs CDC) — Phase 21/ops.
2. Rate-limit fail-open/closed policy confirmation per endpoint class.
3. DI container choice for worker scope (lightweight factory vs library) — Phase 23.

---

> **Next phase (await approval):** Phase 8 — Feature Decomposition. Do not generate until approved.
