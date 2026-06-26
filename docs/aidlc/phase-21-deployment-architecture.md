# ContestForge — AIDLC Phase 21: Deployment Architecture

| | |
|---|---|
| **Phase** | 21 of 25 — Deployment Architecture |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 5 (Architecture), Phase 19 (Obs), technical-spec §1.2, §6.1 |
| **Feeds** | Phase 22 (CI/CD), infra IaC |

---

## Goal
Define the **AWS deployment architecture**: compute platform, networking, the per-role scaling
topology, data stores, secrets, edge protection, environments, and DR — realising the Phase-5
runtime roles with the tech-spec auto-scaling triggers and SLOs.

## Assumptions
- AWS, containerized, deployment-agnostic (ADR-003). Compute platform finalised here. PostgreSQL = RDS
  Multi-AZ; Redis = ElastiCache cluster; S3 for exports; secrets in Secrets Manager.

## Functional Requirements
### 21.1 Compute platform decision
- **Recommendation: ECS Fargate for v1** (lower ops overhead, fits stateless roles + per-service scaling)
  with a documented path to **EKS** if/when finer scheduling or ecosystem needs arise. (Tech-spec left
  this open; this is the proposed decision — confirm. A new ADR will record it.)

### 21.2 Service topology (per-role services)
| Service | Min/Max | Scaling signal | Notes |
|---|---|---|---|
| REST API | 2 / N | CPU>70% or p99>200ms | behind ALB; stateless |
| WS Gateway | 2 / N | conns>2000/pod or CPU>70% | ALB sticky (cookie); WSS |
| Execution worker | per-contest leader | leader election; failover | lightweight |
| Scoring worker | 2 / N | queue depth>100 / backlog>5s | partition by contest hash |
| Leaderboard worker | 2 / N | update lag>1s / depth>200 | independent of scoring |
| Elimination worker | 1 / N | with scoring | |
| Relay/Scheduler | 2 (idempotent) | outbox backlog | go-live + outbox + presence expiry |

### 21.3 Networking
- VPC; public subnets (ALB/NAT) + private subnets (services, RDS, ElastiCache). Security groups least-
  privilege; RDS/Redis not publicly reachable. CloudFront (static/SSR assets) + WAF on ALB.

### 21.4 Data stores
- RDS PostgreSQL Multi-AZ (+ read replica for reports/audit); automated backups 35 days, optional
  cross-region snapshots. ElastiCache Redis cluster mode (rebuildable). S3 for exports (lifecycle rules).
- Connection pooling per instance (10/100); PgBouncer (transaction pooling) if needed at peak.

### 21.5 Edge & TLS
- ACM certs; TLS everywhere; WSS for WS; WAF managed rules + rate-based rules (L7 DoS) complementing app
  limits.

### 21.6 Secrets & config
- Secrets Manager (DB/Redis/JWT keys), rotation; per-environment parameterization; no secrets in images.

### 21.7 Environments
- dev / staging / prod isolated (separate VPC/accounts recommended). Staging mirrors prod for load tests.
- Single platform region v1 (residency per-tenant deferred).

### 21.8 DR / SLOs
- RPO ≤5min (answers), RTO ≤30min (incl. container restart + queue replay + Redis rebuild). Multi-AZ
  failover for RDS; stateless roles reschedule; recovery drills (Phase 19/20).

## Non-functional Requirements
- Independent per-role autoscaling; no single role holds authoritative state. Multi-AZ availability.
- Least-privilege IAM per service; encrypted at rest/in transit; rebuildable Redis.

## Edge Cases
- WS sticky sessions vs pod scale-in: drain connections gracefully (clients reconnect + snapshot).
- Execution leader pod loss: fast re-election; contest resumes from PG. Redis node loss: rebuild from PG.
- Read-replica lag for results: archived snapshot authoritative for finals.

## Future Considerations
- EKS migration; multi-region/active-active; per-tenant region; spot capacity for workers; blue/green at
  infra level; CDN tuning.

## Risks
- **Sticky-session imbalance / scale-in drops** → connection draining + reconnect UX. **RDS as scaling
  ceiling** → replica + pooling + partitioning; revisit if write-bound. **ECS→EKS later migration cost**
  → mitigated by container/IaC portability (ADR-003).

## Deliverables
- **D1** Compute-platform recommendation (ECS Fargate v1; EKS path) — **decision to confirm; new ADR**.
- **D2** Per-role service topology + scaling signals (21.2).
- **D3** Networking, data stores, edge, secrets, environments (21.3–21.7).
- **D4** DR/SLO plan (21.8) tied to RPO/RTO. (Exact instance sizing → IaC/`/neutron:plan` follow-up.)

---
> **Next phase:** Phase 22 — CI/CD Pipeline.
