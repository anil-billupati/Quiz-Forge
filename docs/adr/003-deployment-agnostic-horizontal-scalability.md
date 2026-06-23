# ADR-003 — Deployment-agnostic, horizontally scalable stateless services

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-22 |
| **Deciders** | Team contest (Lead: Hussain) |
| **Context source** | Planning session steer; docs/spec/technical-spec.md §4, §9 |

## Context

The technical spec deferred the concrete compute platform (ECS Fargate vs. EKS)
and region to the planning step. During planning the team's steer was explicit:
**do not commit to a deployment/scaling topology now — keep the application
flexible.** At the same time the system must meet aggressive scale and latency 
NFRs (10,000 concurrent participants, ≤200 ms fan-out) which require horizontal
scalability. We need a principle that satisfies both: build for horizontal scale
without binding the code to any particular platform or region.

## Decision

Design every backend service to be **stateless and horizontally scalable**, with
all durable and coordination state externalized to PostgreSQL and Redis. No
service keeps authoritative contest state in process memory beyond a recoverable
cache. Concretely:

1. **12-factor containers** — configuration via environment/secret store; no
   host or platform assumptions. The same image runs on Fargate, EKS, plain
   Docker, or on-prem.
2. **Independent scaling per service** — API on request rate, WS gateway on
   connection count, engine workers on Redis Streams consumer-group lag.
3. **No sticky in-memory state** — WS sessions and presence live in Redis;
   contest progression lives in `ContestExecutionState` (Postgres); leaderboards
   are rebuildable Redis ZSETs (ADR-002).
4. **`contest_id`-hash partitioning** of engine workers for isolation and
   parallelism.
5. **Region and compute platform are configuration**, supplied at provisioning
   time (`infra.yaml` + IaC), not embedded in the architecture.

## Consequences

**Makes easier:**
- Defers a costly, hard-to-reverse platform decision until real operational
  needs are known; avoids premature lock-in.
- Any service can scale out under load; recovery and rolling deploys are safe
  because instances are interchangeable.
- Portable across clouds/regions and testable locally with Docker Compose.

**Makes harder:**
- Requires discipline: no in-memory authoritative state, every state access goes
  through Postgres/Redis — enforced in review and the resilience suite.
- Concrete autoscaling thresholds, instance sizing, and IaC remain undefined
  here and must be set at provisioning/init time (intentionally deferred).
- Externalizing all state puts more load on Postgres/Redis, addressed by
  pooling, read replicas, partitioning, and ZSET caching (technical-spec §4).

## Alternatives considered

- **Commit to ECS Fargate now:** lowest ops burden and a fine default, but the
  team explicitly chose not to fix deployment yet. Recorded as the likely
  default to revisit at provisioning time.
- **Commit to EKS now:** maximum control and portability, but premature
  operational complexity for the current team and stage. Deferred.
- **Pin a region (e.g. ap-south-1):** would simplify `infra.yaml` but contradicts
  the flexibility steer and the single-region-as-config decision; region stays a
  changeable default.
