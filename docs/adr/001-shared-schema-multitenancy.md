# ADR-001 — Shared-schema multi-tenancy with tenant_id, RLS, and composite FKs

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-22 |
| **Deciders** | Team contest (Lead: Hussain) |
| **Context source** | docs/spec/technical-spec.md §7.1, docs/spec/domain-model.md |

## Context

ContestForge is multi-tenant from day one: a Super Admin creates organizations
(tenants), and each tenant's data (contests, questions, participants, answers,
results) must be strictly isolated (FR-3, NFR-8). The platform targets many
tenants and up to 10,000 concurrent participants per contest. We must choose how
tenant data is physically separated before any persistence code is written, as
the choice pervades every model, query, and migration and is expensive to
reverse.

Three isolation models were available: shared schema with a `tenant_id`
discriminator, schema-per-tenant, and database-per-tenant.

## Decision

Use a **single shared PostgreSQL schema** where every tenant-scoped table
carries a `tenant_id` column, enforced by:
1. A SQLAlchemy scoping mixin that adds a `tenant_id` filter to every
   SELECT/UPDATE/DELETE, with a production runtime assertion rejecting unscoped
   queries.
2. **Composite foreign keys** `(tenant_id, parent_id)` so a row can never link
   to a parent in another tenant.
3. **PostgreSQL Row-Level Security (RLS)** policies as defence-in-depth at the
   database layer.
4. Request-scoped `tenant_id` resolved from JWT claims; cross-tenant access →
   `403` + security-event log.

## Consequences

**Makes easier:**
- Lowest operational overhead — one schema, one migration path, one connection
  pool; scales to many tenants cheaply.
- Cross-tenant platform queries (Super Admin listings, usage aggregates) are
  straightforward.
- Simple, uniform indexing and partitioning (`answer_submission`/`score` by
  `contest_id`).

**Makes harder:**
- Isolation is enforced in software + RLS rather than by physical separation, so
  a scoping bug is a cross-tenant risk — mitigated by the mandatory mixin
  assertion, composite FKs, RLS, and the automated isolation suite (NFR-8).
- Per-tenant data residency or per-tenant restore is not possible without
  additional work (explicitly deferred).
- Very large noisy-neighbour tenants share resources (mitigated by per-tenant
  rate limits and `contest_id`-partitioned workers).

## Alternatives considered

- **Schema-per-tenant:** stronger logical isolation, but migrations must fan out
  across N schemas and connection/catalog management grows with tenant count.
  Rejected for operational cost at scale.
- **Database-per-tenant:** strongest isolation and per-tenant residency/restore,
  but highest cost and ops complexity; suited to a few regulated enterprise
  tenants, not a high-volume SaaS. Rejected for v1; can be offered later for
  specific tenants without changing the shared-schema default.
