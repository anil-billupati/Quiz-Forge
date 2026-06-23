# ContestForge — AIDLC Phase 13: Database Design

| | |
|---|---|
| **Phase** | 13 of 25 — Database Design |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 8 (Features); **`docs/spec/domain-model.md` (source of truth)** |
| **Feeds** | Migrations (Phase 10 M-tasks), Phase 25 |

---

## Goal
Confirm and formalise the **physical database design**. The authoritative model already lives in
`docs/spec/domain-model.md` (entities, FKs, indexes, partitioning, business rules) and reflects the
ten approved decisions. This phase **validates** that model against the features (Phase 8) and data
flows (Phase 4), states the migration approach, and surfaces any gap as a decision — it does **not**
redesign the schema.

## Assumptions
- PostgreSQL (RDS Multi-AZ); SQLAlchemy + Alembic; UUIDv7 PKs; shared-schema multi-tenancy with
  `tenant_id` on every tenant-scoped table; composite FKs `(tenant_id, parent_id)`.
- The domain-model is correct and current (post-decisions: `WildcardConfig`={type,eligibility};
  no `wrong_points`/`default_negative_marking`; `SCHEDULED` lifecycle).

## Functional Requirements
### 13.1 Schema authority
- `domain-model.md` §2 (entities), §3 (physical design), §4 (ERD), §5 (BRs) are authoritative. This
  phase references, does not duplicate.

### 13.2 Tenancy enforcement (DB layer)
- Composite FKs include `tenant_id` (a child cannot reference a cross-tenant parent).
- Optional **RLS** policies per tenant-scoped table (defense-in-depth) alongside the app fail-closed mixin.

### 13.3 Keys, indexes, constraints (confirmed from domain-model §3.2)
- Uniques: `organization.slug/portal_url/custom_domain`; `(tenant,email)` partial + super-admin email
  partial; `configuration_block` partial uniques (one-of contest/group); `option` one-correct partial;
  `answer_submission (tenant,idempotency_hash)`; `score (tenant,answer_submission_id)`; etc.
- Hot-path indexes: `contest(tenant,lifecycle_status)`; `registration(tenant,contest,status)`;
  `answer_submission` recovery index `(tenant,contest,scored)`; `outbox (status,created_at) WHERE PENDING`.

### 13.4 Partitioning & high-write (domain-model §3.3–3.4)
- `answer_submission` HASH(contest_id) × 64; `score` co-partitioned ×64. `server_accepted_at` via DB
  trigger `clock_timestamp()`. Batch upserts for summary rebuild. Pool 10/100; PgBouncer optional.

### 13.5 Enums & types (§3.5)
- Native PG enums for stable low-cardinality; `smallint`-mapped enums for hottest tables if benchmarked.

### 13.6 Migration strategy
- Alembic, **expand/contract** (backward-compatible) for rolling deploys; partitions + RLS created in
  migrations; seed Super Admin via migration/CLI (not API). One revision per feature M-task; revisions
  reviewed for index/partition correctness.

### 13.7 Derived/rebuildable data
- `ParticipantScoreSummary`, leaderboard ZSETs (Redis) are derived from `Score` and rebuildable (FR-44);
  `ContestResultSnapshot` immutable on Archive.

## Non-functional Requirements
- No unscoped tenant access at the DB layer (composite FK + optional RLS).
- Write locality (UUIDv7), partition-local joins (co-partitioning), authoritative timestamps (trigger).
- Recoverability: all live state reconstructible from PG (Phase 4 DF-12).

## Edge Cases
- Partition pruning on `contest_id` for hot queries; cross-partition reporting via replica.
- RLS + app filter interaction (avoid double-filtering surprises) — tested.
- Enum evolution (add value) handled by migration; avoid removing enum values in-place.

## Future Considerations
- Detach old `answer_submission/score` partitions after retention (post-MVP).
- Read replica routing for results/audit; per-tenant region (residency) later.

## Risks
- **Partition/constraint errors on hot tables** → data/perf issues. *Mitigation:* integration tests on
  partitioned tables; migration review.
- **RLS misconfiguration** → over/under restriction. *Mitigation:* isolation suite covers DB layer.

## Deliverables
- **D1** Confirmation that `domain-model.md` is the authoritative physical design (no changes needed).
- **D2** Migration strategy (expand/contract, partitions, RLS, seed) → Phase 10 M-tasks.
- **D3** Index/constraint/partition checklist (from §3.2–3.4) for review.
- **D4** Gap log: **none material** found vs features/flows; open items = replica routing (Phase 21),
  partition detach (post-MVP).

---
> **Next phase:** Phase 14 — API Contracts.
