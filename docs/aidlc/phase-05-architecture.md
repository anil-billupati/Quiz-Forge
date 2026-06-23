# ContestForge — AIDLC Phase 5: High-Level Architecture

| | |
|---|---|
| **Phase** | 5 of 25 — High-Level Architecture |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Source** | Phase 4 (Data Flows); technical-spec §1–4, §7; domain-model bounded contexts; ADRs 001–003 |
| **Depends on** | Phase 4 (Data Flows) — approved |
| **Feeds** | Phase 6/7 (Base frameworks), Phase 21 (Deployment), Phase 22 (CI/CD), Phase 23 (Folder structure) |

---

## Goal
Define the **high-level architecture** that realises the data flows (Phase 4) and honours the design
principles (SOLID, DDD, hexagonal, CQRS-where-needed, event-driven, API-first, security/observability
by design). Establish the **architectural style** (modular monolith, microservice-ready), the
**deployable units**, the **module/bounded-context boundaries**, the **layering** inside each module,
and how the architecture meets the durability/scale/isolation NFRs. This is the blueprint Phases 6/7
(base frameworks) and 21–23 (deployment/structure) build on. It does not yet specify folder structure
(Phase 23), code conventions (Phase 24), or physical schema (Phase 13).

## Assumptions
- The stack is fixed (technical-spec, ADRs): Python/FastAPI (ASGI), Next.js/TS, PostgreSQL (RDS
  Multi-AZ), Redis (ElastiCache cluster), AWS, containers.
- **Style: modular monolith, microservice-ready** (ADR-003). One codebase, strong internal module
  boundaries aligned to the five bounded contexts; deployed as a small number of independently
  scalable *runtime roles* (API, WS gateway, engine workers) sharing the codebase but not state.
- The four authoritative engines (Execution, Scoring, Leaderboard, Elimination) are **logical modules
  run as worker roles**, not yet separate services. The command bus (Redis Streams) is the seam that
  lets them split later without rewrites.
- Multi-tenancy (shared-schema + `tenant_id`, ADR-001) and outbox/idempotent scoring (ADR-002) are
  foundational and assumed throughout.
- Authoritative store = PostgreSQL; Redis is rebuildable transport/cache/presence (Phase 4 §D2).

## Functional Requirements
*(The architecture description — this phase's substance.)*

### 5.1 System context (C4 L1)
```
                ┌──────────────────────────────────────────────────────┐
   [Super Admin]│                                                      │
   [Org Admin]  │                  ContestForge Platform               │
   [Moderator]  │  (multi-tenant live contest engine; web + realtime)  │
   [Participant]│                                                      │
                └───────┬───────────────────────────────┬──────────────┘
                        │                                │
            ┌───────────▼──────────┐        ┌────────────▼─────────────┐
            │ AWS managed services │        │ Observability (CloudWatch │
            │ RDS (PG), ElastiCache│        │ / OTel), WAF, ALB, Secrets│
            │ (Redis), S3 (exports)│        │ Manager                   │
            └──────────────────────┘        └───────────────────────────┘
```
Actors are the Phase-1 personas. External dependencies are AWS managed services only (no third-party
runtime deps in v1). *Trace:* personas P1–P6; tech-spec §1.

### 5.2 Container / runtime-role view (C4 L2)
```
            ┌─────────────────────────────┐        ┌──────────────────────────┐
            │  Next.js Web App (SSR/SPA)  │        │  CDN / WAF / ALB (edge)  │
            └───────────────┬─────────────┘        └────────────┬─────────────┘
                 HTTPS (REST)│            WSS (live)             │
                            ▼                                    ▼
   ┌──────────────────────────────┐               ┌────────────────────────────┐
   │  ROLE A: REST API Service     │               │  ROLE B: WebSocket Gateway  │
   │  (FastAPI/ASGI, stateless)    │               │  (FastAPI/ASGI, stateless)  │
   │  auth/RBAC · tenant ctx ·     │               │  conn mgmt · ticket auth ·  │
   │  authoring · registration ·   │               │  presence · pub/sub fan-out·│
   │  results · live-ticket/control│               │  submit/wildcard forward    │
   └───────────────┬──────────────┘               └──────────────┬─────────────┘
                   │  shared codebase (modules)                   │
                   │  enqueue commands / write outbox             │ subscribe/publish
                   ▼                                              ▼
   ┌──────────────────────────────── Redis (ElastiCache cluster) ─────────────────────────┐
   │  Streams (command bus) · per-contest Pub/Sub · Leaderboard ZSETs · Presence (incl.    │
   │  host) · Dedupe/Tickets · Rate-limit counters                                         │
   └───────────────┬───────────────────────────────────────────────────────────────────────┘
                   │ consumer groups (partition by contest hash)
                   ▼
   ┌──────────────────────────────────────────────────────────────────────────────────────┐
   │  ROLE C: Engine Worker Pools (shared codebase; one process role per scaling concern)   │
   │   ┌────────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌────────────────────┐ │
   │   │ Execution  │ │ Scoring  │ │ Leaderboard  │ │ Elimination │ │ Outbox Relay /     │ │
   │   │ (1/contest │ │ (N, by   │ │ (N)          │ │ (N)         │ │ Scheduler (go-live)│ │
   │   │  leader)   │ │  hash)   │ │              │ │             │ │                    │ │
   │   └────────────┘ └──────────┘ └──────────────┘ └─────────────┘ └────────────────────┘ │
   └───────────────┬───────────────────────────────────────────────────────────────────────┘
                   │ authoritative reads/writes
                   ▼
            ┌──────────────────────────────┐
            │  PostgreSQL (RDS Multi-AZ)    │  authoritative system of record
            │  + read replica (reports)     │  shared schema, tenant_id scoped
            └──────────────────────────────┘   S3 ← result exports
```
**Three stateless runtime roles** (A/B/C) scale independently per the tech-spec auto-scaling triggers.
Execution Engine is a **singleton per live contest** via Redis leader election; all other engines are
horizontally scaled consumer pools partitioned by `contest_id` hash. *Trace:* tech-spec §1.1–1.2.

### 5.3 Module decomposition (bounded contexts → internal modules)
One codebase, five cohesive modules (aligned to domain-model contexts) + a platform/shared kernel:

| Module | Owns (entities) | Exposed via |
|---|---|---|
| **identity** | Organization, TenantSettings, User, RefreshToken | REST (auth, users, orgs) |
| **authoring** | Contest, Group, ConfigurationBlock, WildcardConfig, Question, Option | REST (contests…) |
| **execution** | ContestExecutionState, QuestionWindow; reveal/progression; go-live scheduler; host-presence | Worker + WS + control REST |
| **scoring** | AnswerSubmission (write), Score, ParticipantScoreSummary, WildcardActivation; Leaderboard | Worker + WS submit |
| **elimination** | Checkpoint, EliminationRule, EliminationEvent; survivor sets | Worker |
| **platform (shared kernel)** | OutboxEvent, Notification, AuditLog, ContestLifecycleEvent, TenantUsageRecord, ContestResultSnapshot; tenant context; command bus; observability | Cross-cutting |

**Boundary rules:** modules communicate **across the command bus or via explicit application-service
interfaces**, never by reaching into each other's repositories. Each module is a candidate future
service; the bus + outbox are the extraction seams. *Trace:* domain-model §1; ADR-002/003.

### 5.4 Hexagonal layering (inside every module)
```
        ┌─────────────────────────────────────────────┐
        │  Adapters (driving): REST routers, WS handlers│
        ├─────────────────────────────────────────────┤
        │  Application services (use-case orchestration,│  ← Phase 3 use cases live here
        │  CQRS: command handlers / query handlers)     │
        ├─────────────────────────────────────────────┤
        │  Domain (entities, value objects, domain      │  ← Phase 2/PRD business rules (BR-#)
        │  services, invariants) — framework-agnostic   │
        ├─────────────────────────────────────────────┤
        │  Ports (interfaces): Repository, EventBus,    │
        │  Clock, Cache, Notifier                       │
        ├─────────────────────────────────────────────┤
        │  Adapters (driven): SQLAlchemy repos, Redis    │
        │  Streams/PubSub, OTel, S3, password hasher     │
        └─────────────────────────────────────────────┘
```
- **Dependency inversion:** domain depends only on ports; infrastructure implements them. Enables unit
  testing the engines without Redis/PG and swapping adapters when extracting services.
- **CQRS where it pays:** the read-heavy leaderboard/results path uses dedicated query handlers reading
  `{{ZSET}}`/`ParticipantScoreSummary`/replica; the write path (submission/scoring) is command-side
  with the durable outbox. Not applied where a simple repository suffices (authoring CRUD). *Trace:*
  design principles; Phase 4 DF-9/DF-14.

### 5.5 Cross-cutting architecture
- **Tenant context:** ASGI middleware resolves `tenant_id` from the JWT into a request-scoped contextvar;
  a SQLAlchemy mixin/event-listener auto-scopes every query; unscoped queries fail closed in prod; RLS
  as defense-in-depth. Workers re-establish context from the command envelope. *Trace:* tech-spec §7.1.
- **AuthN/Z:** JWT access/refresh; RBAC enforced per endpoint and per WS action against the
  role-permission matrix (single source of truth). Edge: WAF + ALB rate-limit; app-level token-bucket
  in Redis.
- **Event-driven core:** transactional **outbox** (written in the same TXN as state change) + Redis
  Streams command bus give at-least-once delivery with idempotent consumers (ADR-002).
- **Observability by design:** OTel traces across API→bus→workers; structured logs with corr-id +
  tenant/contest/participant; metrics aligned to NFRs; health/readiness per role.
- **Recovery:** all live state reconstructable from PG; Redis rebuildable (Phase 4 DF-12).

### 5.6 How the architecture meets key NFRs
| NFR | Architectural mechanism |
|---|---|
| NFR-1 reveal ≤200ms | WS gateway role + per-contest pub/sub fan-out; Execution publishes once, gateway scales by connections |
| NFR-3 leaderboard ≤500ms | Dedicated Leaderboard worker pool + Redis ZSETs; scaled independently of scoring |
| NFR-5 durability | Durable PG write before ack (DF-8); outbox; synchronous commit |
| NFR-6 recovery ≤30s | Stateless roles + state in PG + idempotent re-drive + leader re-election |
| NFR-7 reconnect ≤3s | Stateless WS gateway + snapshot from PG/Redis (DF-6) |
| NFR-8 tenant isolation | Shared-schema + tenant_id mixin + composite FKs + RLS; isolation test suite |
| NFR-4 scale 10k/contest | Independent auto-scaling of roles A/B/C; partition-by-contest workers |

## Non-functional Requirements
*(Qualities of the architecture artifact / the system's architectural properties.)*
- **Modifiability:** module boundaries = bounded contexts; cross-module calls only via ports/bus →
  low coupling, high cohesion (SOLID).
- **Scalability:** three independently scalable stateless roles; engines partitioned by contest;
  Execution singleton-per-contest via leader election.
- **Availability/resilience:** Multi-AZ PG; rebuildable Redis; at-least-once bus + idempotent
  consumers + dead-letter; no single role holds authoritative state.
- **Security:** tenant isolation as the primary boundary, defense-in-depth (app + composite FK + RLS),
  edge protection, secrets in manager.
- **Testability:** hexagonal ports allow domain/engine unit tests without infra; isolation/durability
  suites at integration level.
- **Evolvability:** every module is a future-service candidate; bus + outbox are the seams (no
  distributed-transaction coupling introduced now — YAGNI).

## Edge Cases
- **Execution leader failover mid-contest:** new leader resumes from `ContestExecutionState` + open
  `QuestionWindow`; idempotent reveal/checkpoint prevents double-progression.
- **WS gateway pod loss during fan-out:** stateless; clients reconnect to another pod and snapshot;
  authoritative timing unaffected (in PG).
- **Hot contest hashing to few scoring partitions:** independent scaling + monitored queue depth;
  partition count (64) chosen to spread load (revisit Phase 21).
- **Outbox relay outage:** state remains durable in PG; PENDING events replay on recovery; fan-out
  delayed, not lost.
- **Module needs another module's data on the write path:** must go via application-service port or an
  event — never a cross-module repository read (prevents hidden coupling).
- **Read replica lag for results:** results served from replica may lag; archived snapshot is immutable
  and authoritative for final results.

## Future Considerations
- **Service extraction:** split Scoring/Leaderboard or the WS gateway into separate services if scaling
  or team boundaries demand it — the bus/outbox seams make this incremental (ADR-003).
- **Compute platform finalisation (ECS Fargate vs EKS):** deferred to Phase 21 / `/neutron:plan`.
- **Multi-region / data residency:** per-tenant region selection (deferred per product-spec §7).
- **Outbox relay mechanism** (poller vs logical replication / Debezium) — Phase 7.
- **Schema-per-tenant** isolation alternative if a large tenant needs hard isolation (out of scope now).
- **Edge caching / SSR strategy** for admin consoles vs live views (Phase 6).

## Risks
- **Modular-monolith erosion:** without enforced boundaries, modules entangle and the "microservice-
  ready" promise dies. *Mitigation:* port-only cross-module calls; lint/architecture tests in CI
  (Phase 22); ADR-003 as guardrail.
- **Execution singleton as a bottleneck/SPOF per contest:** one Execution leader per contest. *Mitigation:*
  it's lightweight (timers/progression only; scoring is offloaded), with fast leader re-election; a
  contest stall ≠ data loss (state in PG).
- **Premature CQRS/event complexity:** over-applying CQRS/event-driven adds cost (KISS/YAGNI breach).
  *Mitigation:* CQRS only on the read-heavy leaderboard/results and the durable write path; CRUD stays
  simple repository.
- **Cross-cutting tenant scoping gaps:** a single unscoped query is a breach. *Mitigation:* fail-closed
  mixin + RLS + automated isolation suite (NFR-8).
- **Redis as accidental source of truth:** convenient caching can drift into authority. *Mitigation:*
  Phase 4 store-authority map enforced; recovery tests flush Redis.

## Deliverables
### D1 — Architecture views
- L1 system context (5.1), L2 container/runtime-role view (5.2), module decomposition (5.3),
  hexagonal layering (5.4).

### D2 — Runtime-role catalogue
| Role | Scaling | State | Scale trigger (tech-spec §1.2) |
|---|---|---|---|
| A REST API | horizontal, stateless | none | CPU>70% / p99>200ms |
| B WS Gateway | horizontal, stateless | sockets only | conns>2000/pod or CPU>70% |
| C Execution worker | singleton per contest (leader) | in PG | per-contest; failover via leader election |
| C Scoring worker | horizontal, by contest hash | none | queue depth>100 / backlog>5s |
| C Leaderboard worker | horizontal | none | update lag>1s / depth>200 |
| C Elimination worker | horizontal | none | with scoring |
| C Outbox relay / Scheduler | horizontal (idempotent) | none | pending backlog |

### D3 — Module boundary contract
Cross-module interaction is **only** via (a) the command bus (Redis Streams) + outbox events, or
(b) explicit application-service port interfaces. No module imports another module's repositories or
ORM models. Shared concerns live in `platform` (shared kernel). This contract is the microservice-
extraction seam and will be enforced by CI architecture tests (Phase 22).

### D4 — Architecture decisions referenced / confirmed
- ADR-001 shared-schema multi-tenancy · ADR-002 authoritative engines + outbox + idempotent scoring ·
  ADR-003 deployment-agnostic horizontal scalability. No new ADR required by this phase; any future
  service split or compute-platform choice will be captured as a new ADR.

### D5 — Open questions carried forward
1. ECS Fargate vs EKS (Phase 21).
2. Outbox relay mechanism (Phase 7).
3. SSR vs SPA boundary for admin vs live UI (Phase 6).

---

> **Next phase (await approval):** Phase 6 — Base UX Framework. Do not generate until approved.
