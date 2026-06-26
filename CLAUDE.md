# ContestForge — Project Context (CLAUDE.md)

| | |
|---|---|
| **Project** | ContestForge — multi-tenant live contest/quiz engine |
| **Type** | Full-stack (hybrid backend service + worker; web frontend) |
| **Stack** | Python + FastAPI · Next.js + TypeScript · PostgreSQL + Redis |
| **Cloud** | AWS (deployment-agnostic containers) |
| **Team** | contest (Lead: Hussain) |
| **Last updated** | 2026-06-26 |

## What this is

A multi-tenant engine for running timed competitive quizzes at scale (up to
10,000 concurrent participants) with strict integrity guarantees: no answer
loss, server-authoritative at-most-once scoring, and recoverability after
partial failure. Supports Standard / Speed / Elimination modes over Normal and
Grouped structures.

## Where things live

- **Specs (source of truth):** `docs/spec/` — `product-spec.md`,
  `technical-spec.md`, `api-contracts.yaml` + `.md`, `domain-model.md`,
  `testing-strategy.md`.
- **Architecture & plan:** `docs/plan/architecture.md`,
  `docs/plan/delivery-plan.md`.
- **Decisions:** `docs/adr/`.
- **Local context:** `.neutron/security.md`, `.neutron/integrations.md`,
  `.neutron/environment.md`.
- **Code:** `backend/` (FastAPI app + engines), `frontend/` (Next.js).

## Working conventions

- Ground all implementation in the approved specs; surface deviations rather
  than implementing silently.
- Multi-tenancy is foundational: every tenant-scoped table carries `tenant_id`;
  use the scoping mixin and never trust client-supplied tenant/timing data.
- Write tests within the same unit as the code (see `testing-strategy.md`).
- Implement one delivery unit at a time via `/neutron:feature`.
- **Method logging:** decorate every service/business function with `@logged`
  from `app.observability.method_logging` so it emits `method.enter` /
  `method.exit` (with `duration_ms`) and `method.error` on failure. It supports
  both `async def` and `def`. Do not log argument values that may contain
  secrets (sessions, passwords, tokens) — `@logged` omits args by default; pass
  `log_args=True` only when every argument is known to be safe. HTTP requests are
  logged automatically by `RequestLoggingMiddleware`, which binds a `request_id`
  shared by all method logs in that request.

## Architecture Decision Records

| ADR | Title | Status |
|---|---|---|
| [001](docs/adr/001-shared-schema-multitenancy.md) | Shared-schema multi-tenancy (tenant_id + RLS + composite FKs) | Accepted |
| [002](docs/adr/002-authoritative-engines-outbox-idempotent-scoring.md) | Authoritative engines + outbox + idempotent at-most-once scoring | Accepted |
| [003](docs/adr/003-deployment-agnostic-horizontal-scalability.md) | Deployment-agnostic, horizontally scalable stateless services | Accepted |

## Delivery status

Units from `docs/plan/delivery-plan.md`. Status: ☐ not started · ◐ in progress · ☑ done.

| # | Unit | Status |
|---|---|---|
| 1 | Platform foundation | ☑ |
| 2 | Tenancy & Identity | ☑ |
| 3 | Contest authoring — contests, groups & lifecycle | ☑ |
| 4 | Configuration blocks | ☑ |
| 5 | Questions & options | ☑ |
| 6 | Registration | ☑ |
| 7 | Real-time foundation (WebSocket gateway) | ☑ |
| 8 | Execution Engine | ☑ |
| 9 | Answer submission & durability | ☑ |
| 10 | Scoring Engine | ☑ |
| 11 | Wildcard runtime | ☑ |
| 12 | Leaderboard Engine | ☐ |
| 13 | Elimination Engine | ☐ |
| 14 | Notifications | ☐ |
| 15 | Results & exports | ☐ |
| 16 | Audit log | ☐ |
| 17 | Resilience, recovery & performance hardening | ☐ |
| 18 | Frontend (18a admin/authoring, 18b live/participant) | ☐ |

**Next:** `/neutron:feature "Unit 12: Leaderboard Engine"`

> Note: Unit 4 keeps configuration **Draft-only** (locks at PUBLISHED), an
> accepted deviation from spec BR-5 (which specifies a Registration-Open lock).
> See `docs/session-log.md` (2026-06-25).
