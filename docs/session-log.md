# ContestForge — Session Log

## 2026-06-19 — /neutron:kickoff

**Command:** /neutron:kickoff

### Artifacts read
- `ContestForge_PRD_v1.md` — Core Contest Engine PRD v2.3, plus header notes
  specifying the AIDLC flow, multi-tenancy from day one, organization concept,
  super admin creating organizations, and a tenant table.

### Gaps identified
- Scope (full-stack vs. backend-only)
- Technology stack
- Cloud provider
- Compliance requirements
- Team name and project lead

### Questions asked & answers given
1. Full-stack platform or backend-only? → **Full-stack platform**
2. Technology stack? → **Backend: Python + FastAPI; Frontend: Next.js + TypeScript**
   (PostgreSQL + Redis proposed as data stores for the multi-tenant store and
   real-time leaderboards)
3. Cloud provider? → **AWS**
4. Compliance requirements? → **None** (flagged as open question given
   multi-tenant participant data)
5. Team name and project lead? → **Team: contest; Lead: Hussain**

### Decisions made
- Project type: full-stack; backend service pattern: hybrid (HTTP/WebSocket API
  + background workers for execution/scoring/leaderboard/elimination engines).
- Multi-tenancy is foundational: organization/tenant model present from day one.

### Trade-offs presented
- Proposed Fission default stack (Java/Spring) vs. client preference; client
  chose Python/FastAPI + Next.js/TypeScript.

### Outputs produced
- `docs/kickoff.md`
- `infra.yaml` (partial — region, environments, data-stores, integrations = tbd)
- `docs/session-log.md` (this file)

### Open questions carried forward
- Compliance (SOC 2 / GDPR?) ; Timeline ; Budget ; Tenant isolation strategy ;
  AWS region(s) and environments.

---

## 2026-06-19 — /neutron:spec

**Command:** /neutron:spec

### Artifacts read
- `docs/kickoff.md` (approved kickoff)

### Open questions surfaced
- Deferred to /neutron:plan (non-blocking for spec): tenant isolation infra,
  AWS region/environments.
- Carried forward (non-blocking): timeline, budget, compliance = none.

### Gaps identified & resolved this session
1. Authentication mechanism → **JWT + email/password** for all user types.
2. Data retention / Archived behaviour → **Retain indefinitely; Archived =
   read-only.**
3. Multi-tenant isolation model (spec working assumption) → **Shared schema +
   tenant_id with row-level enforcement** (final infra confirmed in
   /neutron:plan).

### Decisions made
- Backend modeled as hybrid: FastAPI HTTP/WebSocket API + background engine
  workers (Execution, Scoring, Leaderboard, Elimination).
- Answer durability boundary = durable PostgreSQL write before ack, with
  idempotency key `(contest, question, participant, attempt)` and unique
  Score.answer_submission_id for at-most-once scoring.
- Live contest runs over WebSocket; REST covers authoring + results.

### Outputs produced
- `docs/spec/product-spec.md` (45 FRs, 10 NFRs, success criteria, out-of-scope)
- `docs/spec/technical-spec.md` (component diagram, responsibilities, data
  flows, error handling, observability, security overview)
- `docs/spec/api-contracts.yaml` (OpenAPI 3.0.3) + `docs/spec/api-contracts.md`
  (companion incl. WebSocket channel contract)
- `docs/spec/domain-model.md` (entities, Mermaid ERD, 18 business rules)
- `docs/spec/testing-strategy.md` (pyramid + resilience/chaos suite mapped to
  NFRs, coverage targets, traceability)
- `docs/session-log.md` (this entry)

### Open questions remaining
- Compliance confirmation ; timeline ; budget ; notification transport
  (in-app vs. email) ; default negative-marking policy per tenant.

---

## 2026-06-22 — Principal-architect spec remediation (pre-DB model)

**Command:** User requested principal-architect review of PRD, product-spec,
technical-spec, and domain-model, with focus on multi-tenancy and 10,000
concurrent users, followed by spec remediation.

### Artifacts read
- `ContestForge_PRD_v1.md`
- `docs/spec/product-spec.md`
- `docs/spec/technical-spec.md`
- `docs/spec/domain-model.md`
- `docs/spec/api-contracts.yaml` and `docs/spec/api-contracts.md`
- `docs/spec/testing-strategy.md`
- `docs/kickoff.md`
- `infra.yaml`

### Gaps identified
- PRD listed `Scheduled` reveal mode while product/technical specs supported
  only `Automatic` and `Moderator Controlled`.
- PRD Configuration Block field list omitted `reveal_mode`, `ranking_criterion`,
  `tie_display`, `leaderboard_visibility`, `update_frequency`, and scoring
  fields already present in product-spec/domain-model.
- PRD §8.6 used a `Top 10 advance` example not supported by the formal
  elimination rules.
- Auth/tenant roles missing from PRD glossary; no role-permission matrix.
- Child entities (`Group`, `ConfigurationBlock`, `Option`, `EliminationRule`,
  `Checkpoint`) lacked `tenant_id` and composite FKs.
- `Organization.slug` missing despite login using `tenant_slug`.
- No concrete tenant-enforcement layer (SQLAlchemy mixin, RLS, repository base).
- No per-tenant resource limits or usage metering.
- NFRs used absolute language (`all`, `zero`, `within 3s`) without percentiles.
- Infrastructure (queue, Redis topology, DB pooling, WS gateway, rate limits,
  observability) was deferred to `/neutron:plan`.
- Compliance recorded as `none` despite multi-tenant participant PII.

### Decisions made
- v1 supports only `Automatic` and `Moderator Controlled` reveal modes;
  `Scheduled` deferred.
- PRD Configuration Block field list expanded to match product-spec.
- PRD elimination example rewritten to use existing `Minimum Score Threshold`.
- Compliance baseline set to **SOC 2 Type II and GDPR readiness**.
- Notification transport: in-app WebSocket events for v1.
- Negative marking default: `wrong_points = 0` per Configuration Block.
- Command transport: **Redis Streams** on AWS ElastiCache for Redis Cluster.
- Separate **WebSocket gateway** service from REST API for horizontal scaling.
- Tenant isolation: shared schema + `tenant_id` with SQLAlchemy mixin and
  PostgreSQL RLS as defense in depth.
- Observability: OpenTelemetry + AWS CloudWatch.

### Outputs produced
- Updated `ContestForge_PRD_v1.md` (reveal modes, config fields, glossary,
  retention, elimination example).
- Updated `docs/spec/product-spec.md` (role-permission matrix, FR-3a/3b, NFRs
  with percentiles, compliance section, open questions closed).
- Updated `docs/spec/technical-spec.md` (async/ASGI architecture, separate WS
  gateway, Redis Streams, auto-scaling, rate limits, tenant enforcement
  mechanism, RPO/RTO).
- Rewrote `docs/spec/domain-model.md` v0.2 per the modified DB model plan:
  UUIDv7 PKs, new entities (`QuestionWindow`, `ContestRuntimeState`,
  `ParticipantScoreSummary`, `ContestResultSnapshot`, `ContestLifecycleEvent`,
  `RefreshToken`), composite FKs/unique constraints, partitioning strategy,
  indexing strategy, physical design section, expanded business rules (BR-1
  to BR-27), and updated ERD. `Organization.region` was added then removed
  after review — v1 uses a single platform region.
- Updated `docs/spec/api-contracts.yaml` and `.md` (removed `SCHEDULED` and
  `reveal_at`; added `Organization.slug`; updated idempotency semantics).
- Updated `docs/spec/testing-strategy.md` (percentile language for performance
  tests).
- Updated `docs/kickoff.md` (compliance baseline, tenant isolation strategy,
  notification transport).
- Updated `infra.yaml` (queue, data-stores, integrations, compliance).
- Created `.neutron/security.md` and `.neutron/integrations.md`.

### Open questions remaining
- Timeline ; Budget ; AWS region(s) and environments ; exact ECS/EKS sizing and
  cost estimates ; full compliance certification scope before production launch.

---

## 2026-06-22 — Domain model: tenant URL, user names & schema gap-fill

**Trigger:** User (acting as product owner) request, executed via plan mode.

### Artifacts read
- `ContestForge_PRD_v1.md`, `docs/spec/domain-model.md`, and the user-edited
  `docs/spec/product-spec.md` / `docs/spec/technical-spec.md`.

### Questions asked & answers
1. Meaning of "URL for the schema" on the tenant table → **Tenant
   subdomain/portal URL** (not per-tenant DB schema, not JSON-schema URL).
2. Deliverable scope → **Update `docs/spec/domain-model.md` only** (DDL deferred
  to /neutron:init).

### Decisions / changes (domain-model.md only)
- **Organization:** added `slug`, `portal_url` (both unique, not null) and
  optional `custom_domain`.
- **User:** replaced `display_name` with `first_name` + `last_name`; made
  `(tenant_id, email)` composite-unique explicit.
- **New entities (gap-fill):** RefreshToken (FR-4), WildcardConfig (FR-26),
  ContestExecutionState (FR-42/NFR-6), QuestionWindow (FR-20/40), OutboxEvent
  (durable at-least-once channel), Notification (FR-37/41), AuditLog (tech-spec
  §6). Now five bounded contexts.
- **Modified entities:** ConfigurationBlock (+`survivor_score_reset`,
  +`elimination_combine_operator`, dropped SCHEDULED reveal mode);
  EliminationRule (combine_operator moved to block); Question (dropped
  `reveal_at`); Registration (+`joined_at`, `spectator_access`, `final_rank`,
  `final_score`); AnswerSubmission (+`question_window_id`).
- **Consistency alignment** with user's spec edits: reveal modes now
  `AUTOMATIC | MODERATOR_CONTROLLED`; elimination combine operator is
  block-level.
- Added **§5 Scale & Indexing** (UUID v7, key indexes, hash partitioning of
  answer_submission/score, RLS note) for the 10,000-concurrent-user target.
- ERD refreshed; business rules BR-19..BR-24 added; BR-4 updated.

### Outputs produced
- `docs/spec/domain-model.md` (updated)
- `docs/session-log.md` (this entry)

---

## 2026-06-22 — API contracts completion (spec only, no implementation)

**Trigger:** User request (professional API developer hat, Python/FastAPI),
executed via plan mode. Scope explicitly limited to **API contracts only**.

### Artifacts read
- `ContestForge_PRD_v1.md`, all `docs/spec/*`, prior `api-contracts.yaml`.

### Question asked & answer
- Participant onboarding model → **Admin-managed, no self-signup.** SQL
  bootstraps the Super Admin (not in API); Super Admin creates the org + initial
  Org Admin; Org Admin creates co-Org-Admins, Moderators, Participants via
  `POST /users` (role ≠ SUPER_ADMIN).

### Work done
- Rewrote `docs/spec/api-contracts.yaml` to OpenAPI 3.0.3 v1.0.0: **35 path
  items, 30 schemas**, covering Auth/session, Users, Organizations, Contests,
  Groups, Configuration, Questions/Options, Registration, Live runtime
  (reconnect snapshot + moderator controls), Results/Leaderboards/Eliminations/
  export, Notifications, Audit, and Ops (health/ready).
- Aligned schemas with current specs: reveal modes `AUTOMATIC |
  MODERATOR_CONTROLLED` (no SCHEDULED); block-level `elimination_combine_operator`;
  `survivor_score_reset`; structured `wildcards`; org `slug`/`portal_url`; user
  `first_name`/`last_name`. Added pagination envelope, standard error model,
  reusable params/responses.
- Rewrote `docs/spec/api-contracts.md` companion: per-resource tables, request
  examples, conventions, the WebSocket live-channel contract, and a
  capability→endpoint traceability matrix.

### Verification
- YAML parses; **no dangling `$ref`s and no unused components** (checked via
  script). Deep `openapi-spec-validator` not installed in env (noted).

### Outputs produced
- `docs/spec/api-contracts.yaml` (rewritten)
- `docs/spec/api-contracts.md` (rewritten)
- `docs/session-log.md` (this entry)

---

## 2026-06-22 — Merge conflict resolution: main → feature/product_spec_fix

**Command:** User merged `main` into `feature/product_spec_fix` and requested
conflict resolution without spec deviations.

### Conflicts resolved
- `docs/session-log.md` — kept all three preceding entries in chronological
  order.
- `docs/spec/api-contracts.yaml` — kept main's v1.0.0 contract; preserved
  remediation-aligned values (reveal modes, block-level combine operator,
  survivor_score_reset, org slug/portal_url).
- `docs/spec/api-contracts.md` — kept main's rewritten companion; aligned
  idempotency description with `idempotency_hash`.
- `docs/spec/domain-model.md` — merged main's structure (five bounded contexts,
  `first_name`/`last_name`, `portal_url`/`custom_domain`, `WildcardConfig`,
  `OutboxEvent`, `Notification`, `AuditLog`, `ContestExecutionState`) with
  remediation hardening (UUIDv7, composite tenant FKs, physical design section,
  expanded business rules BR-1..BR-27, derived `ParticipantScoreSummary`).

### Post-merge adjustments
- `Organization.region` removed — v1 uses a single platform region.
- `.neutron/` added to `.gitignore` per user request (files remain locally).

---

## 2026-06-22 — API contract alignment fixes

**Command:** User asked whether API contracts were up to date with PRD, product
spec, and technical spec.

### Discrepancies found and fixed
- `Organization.slug` regex capped at 40 chars while domain model allowed 3–64
  → updated regex to `{1,62}` (3–64 chars total).
- Missing Super Admin creation path (technical spec requires existing Super Admin
  can create another) → added `POST /super-admins` and `CreateSuperAdminRequest`.
- Missing `TenantSettings` endpoints required by FR-3a → added
  `GET/PATCH /organizations/{orgId}/settings`.
- Missing `TenantUsageRecord` endpoint required by FR-3b → added
  `GET /organizations/{orgId}/usage`.
- `Notification.contest_id` nullable in API but non-nullable in domain model →
  removed `nullable: true`.
- `WildcardActivation.outcome` typed as string in API but JSONB in domain model
  → changed to `object`.
- `LeaderboardEntry` omitted `last_correct_at` → added it.
- `slug`/`portal_url` immutability rule in `api-contracts.md` was not grounded
  in domain model → added immutability clause to BR-19.

### Outputs produced
- Updated `docs/spec/api-contracts.yaml`
- Updated `docs/spec/api-contracts.md`
- Updated `docs/spec/domain-model.md` (BR-19)

---

## 2026-06-22 — /neutron:plan (architecture + delivery plan + infra)

**Command:** /neutron:plan

### Artifacts read
- `docs/kickoff.md`, all `docs/spec/*` (current, user-expanded), `infra.yaml`.

### Questions asked & answers
1. Compute platform (Fargate vs EKS) → **don't commit; keep deployment-agnostic,
   horizontally scalable.**
2. AWS region → **don't pin; flexible, single-region as config.**

### Architectural decisions (ADRs written, accepted)
- **ADR-001** Shared-schema multi-tenancy (`tenant_id` + scoping mixin + RLS +
  composite FKs).
- **ADR-002** Server-authoritative engines + transactional outbox + Redis
  Streams transport + idempotent at-most-once scoring.
- **ADR-003** Deployment-agnostic, horizontally scalable stateless services
  (no committed compute platform/region; state externalized to Postgres/Redis).
  (Other decisions — FastAPI, Postgres, Redis, WS gateway, JWT, RLS — were
  already fixed in the specs and only consolidated, not re-decided.)

### Delivery plan
- **18 units** (several high-complexity flagged for sub-splitting): Foundation →
  Identity/Tenancy → Authoring (contests/config/questions/registration) →
  Real-time foundation → Execution → Answer durability → Scoring → {Wildcards,
  Leaderboard} → Elimination → Notifications → Results/Export → Audit →
  Resilience/Perf → Frontend (18a admin/authoring, 18b live/participant).
- Critical path = live engine chain (Units 7→8→9→10→11/12→13); authoring,
  notifications, audit, and frontend parallelize off-path.

### infra.yaml completed
- `environments: [dev, staging, production]`; services (api, ws-gateway,
  engine-workers, web); data-stores (postgresql, redis with purposes);
  `integrations: []` (in-app WS notifications only); `compute: container /
  platform-agnostic / horizontal`; `region: us-east-1` as changeable default;
  `compliance: [soc2-type-ii, gdpr-readiness]`.

### Outputs produced
- `docs/plan/architecture.md`
- `docs/plan/delivery-plan.md`
- `docs/adr/001-shared-schema-multitenancy.md`
- `docs/adr/002-authoritative-engines-outbox-idempotent-scoring.md`
- `docs/adr/003-deployment-agnostic-horizontal-scalability.md`
- `infra.yaml` (completed)
- `docs/session-log.md` (this entry)

---

## 2026-06-22 — /neutron:init (repository scaffold)

**Command:** /neutron:init

### Artifacts read
- `docs/kickoff.md`, `docs/plan/architecture.md`, `docs/plan/delivery-plan.md`,
  `infra.yaml`. No `archetypes/` or `adapters/` templates present → scaffolded
  from architecture + stack directly (surfaced as a note, proceeded).

### Scaffold created (structural boilerplate only — no business logic)
- **Backend (Python/FastAPI):** `backend/app/` (`main.py`, `config.py`, `db.py`,
  `redis_client.py`, `dependencies.py`, `middleware/{logging,tenant_context,
  errors}.py`, `routers/health.py`, plus `models/ schemas/ services/ workers/
  utils/` packages); Alembic (`alembic.ini`, `migrations/`); `pyproject.toml`
  (ruff/pytest/mypy); `requirements.txt`; `Dockerfile`; `.env.example`; tests
  (`unit/ integration/ fixtures/`, `conftest.py`, health smoke test).
- **Frontend (Next.js/TS):** `frontend/src/{app,components,hooks,lib,types}`,
  `package.json`, `tsconfig.json`, `next.config.js`, `Dockerfile`,
  `.env.example`, `tests/`.
- **Root:** `README.md`, `CLAUDE.md` (context + ADR summary + delivery-status
  table), `.neutron/{security,integrations,environment}.md`, `docker-compose.yml`,
  `.github/workflows/{ci,deploy}.yml`. Added `.ruff_cache/` to existing
  `.gitignore` (`.neutron/` already ignored).

### Verification
- All backend Python files parse (AST check) — OK.
- Ops endpoints (`/health`, `/ready`) implemented as the Unit-1 baseline.

### Next step
- Begin implementation: `/neutron:feature "Unit 1: Platform foundation"`.

---

## 2026-06-22 — /neutron:feature "Unit 1: Platform foundation"

**Command:** /neutron:feature (Unit 1)

### Spec reference
- technical-spec §1–2, §6, §7.1; ADR-001 (shared-schema multi-tenancy);
  ADR-003 (deployment-agnostic); delivery-plan Unit 1.

### Gaps
- None — scoping mechanism fully specified by ADR-001 + technical-spec §7.1.

### Built (completing the init scaffold)
- `app/models/base.py` — declarative `Base` + `TenantScoped` mixin (+ `new_uuid`).
- `app/db.py` — tenant-scoping machinery: `do_orm_execute` filter via
  `with_loader_criteria` + unscoped-query assertion; `before_flush` auto-stamps
  `tenant_id` from request context.
- `app/middleware/tenant_context.py` — `UnscopedQueryError`, context get/set/
  reset, and `TenantContextMiddleware` (ASGI; JWT population deferred to Unit 2).
- `app/redis_client.py` — Streams `stream_publish` / `stream_read` helpers.
- `app/schemas/pagination.py` — generic `Page[T]` envelope.
- `app/observability/tracing.py` — best-effort OpenTelemetry FastAPI
  instrumentation; wired in `main.py` alongside the tenant middleware.
- `app/models/foundation_probe.py` + `migrations/versions/0001_foundation.py` —
  pgcrypto extension + tenant-scoped probe table + RLS policy scaffold; wired
  `target_metadata` in `migrations/env.py`.
- Tests: `tests/unit/test_tenant_scoping.py` (4), `tests/integration/
  test_foundation_db.py` (testcontainers, marked integration).

### Verification
- Spun up a Python 3.13 venv, installed minimal deps, ran the scoping unit
  suite: **4/4 passed** (auto-stamp, tenant filter isolates rows, unscoped
  query raises, unscoped insert raises). Temp venv removed afterward.
- All backend Python files AST-parse cleanly.

### Decisions captured (docs/decisions.md, Tier 2)
- Scoping via SQLAlchemy session hooks (vs per-repo filters / RLS-only).
- `tenant_id` as `String(36)` in scaffold → UUID + composite FK in Unit 2.
- **Finding:** RLS policy present but inert until the `app.tenant_id` Postgres
  GUC is set per transaction — planned for Unit 2 (surfaced, not silently done).

### Status
- CLAUDE.md delivery table: Unit 1 → ☑ complete. Next: Unit 2 (Tenancy &
  Identity).
- Suggest `/neutron:review` before raising a PR.

---

## 2026-06-22 — /neutron:feature "Unit 2: Tenancy & Identity"

**Command:** /neutron:feature (Unit 2)

### Spec reference
- product-spec FR-1..5, FR-3a/3b, §2.5 role matrix; api-contracts Auth/Users/
  Organizations; domain-model Organization/TenantSettings/User/RefreshToken/
  TenantUsageRecord; ADR-001; BR-19, BR-20.

### Gap resolved
- Initial credentials: **creator sets the password** (no email transport in v1).
  Contract change: `admin_password` added to org creation; `password` required
  on `POST /users` (logged in docs/decisions.md).

### Built
- Models: `organization.py` (Organization + TenantSettings), `user.py`
  (User + RefreshToken), `tenant_usage.py` (TenantUsageRecord).
- Security: `security/passwords.py` (argon2), `security/tokens.py` (JWT access +
  opaque rotating refresh, sha256-hashed, token_family).
- Dependencies: `Principal`, `get_principal` (sets tenant context from JWT),
  `require_roles` RBAC (§2.5), `db_session`, pagination params.
- Services: `auth_service` (login/refresh-rotation+reuse-detection/logout/
  change-password), `user_service` (create/list/get/update + create_super_admin,
  tenant-scoped), `organization_service` (org CRUD + status + settings + usage;
  provisions initial Org Admin + TenantSettings atomically; BR-19 immutability).
- Routers: `auth`, `organizations` (SUPER_ADMIN), `users` (+ `/super-admins`);
  registered in `main.py`.
- `cli.py` — `python -m app.cli seed-superadmin` (env-seeded bootstrap).
- Migration `0002_tenancy_identity` (tables, uniques, indexes, partial unique
  index for SUPER_ADMIN email); models registered in `migrations/env.py`.
- Contract updated: `api-contracts.yaml` + `.md` (admin_password, password
  required).

### Verification (ran in a temp Python 3.13 venv; removed after)
- **17/17 passed**: security unit tests (hash, JWT roundtrip/tamper/expiry,
  refresh hashing) + tenant-scoping unit tests + Unit 2 integration suite
  (onboarding chain, login→refresh rotation + reuse detection, logout revoke,
  RBAC 403, cross-tenant user isolation, SUPER_ADMIN role rejected).
- Found & fixed two real bugs while verifying: missing `email-validator`
  dependency (added to requirements); naive/aware datetime comparison on refresh
  expiry (now tz-coerced — works on both Postgres and SQLite).
- Contract YAML re-validated: 38 paths, 35 schemas, no dangling refs.

### Decisions captured (docs/decisions.md, Tier 2)
- Creator-set credentials + contract change; User excluded from auto-scoping
  mixin (scoped explicitly); tz-safe refresh expiry comparison.

### Status
- CLAUDE.md: Unit 2 → ☑ complete. Next: Unit 3 (Contest authoring).
- Suggest `/neutron:review` before raising a PR.
