# ContestForge — AIDLC Phase 22: CI/CD Pipeline

| | |
|---|---|
| **Phase** | 22 of 25 — CI/CD Pipeline |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 20 (Testing), Phase 21 (Deploy), Phase 13 (migrations) |
| **Feeds** | Implementation, ops |

---

## Goal
Define the **CI/CD pipeline**: stages, quality gates, migration handling, and deployment strategy that
enforce the integrity guarantees and architectural boundaries on every change.

## Assumptions
- Git-based; containers to ECR; deploy to ECS Fargate (Phase 21). One monorepo (backend + frontend).

## Functional Requirements
### 22.1 CI stages (per PR)
1. **Lint/format/type** (ruff/black/mypy; eslint/prettier/tsc).
2. **Unit tests** (backend fakes; frontend RTL).
3. **Integration tests** (ephemeral PG/Redis; migrations apply; tenant scoping).
4. **Contract tests** (schemathesis vs `api-contracts.yaml`; WS contract harness).
5. **Architecture tests** (module boundary: no cross-module repo imports — Phase 5 §D3).
6. **Security checks** (dependency scan, secret scan, SAST).
7. **Tenant-isolation suite** (blocking, NFR-8).
8. **Coverage gate** (threshold; critical paths higher).
9. **Frontend e2e (smoke)** + **axe a11y**.

### 22.2 Blocking gates
PR cannot merge unless 1–8 pass. **Integrity suites (isolation, idempotency, mode-correctness,
late-submit) are blocking.** Load/soak + full e2e run on schedule/pre-release (not every PR).

### 22.3 Build & artifacts
- Build per-role container images (shared base) → ECR with immutable tags (git sha). Frontend built/SSR
  bundle. SBOM generated.

### 22.4 Migration strategy in CD
- **Expand/contract** only (backward-compatible). Migrations run as a gated step **before** rolling the
  new service version; partitions/RLS included. Rollback = forward-fix (no destructive down-migrations
  in prod) + image rollback.

### 22.5 Deployment strategy
- **Staging:** auto-deploy on main; run load/soak + full e2e + DR drill periodically.
- **Prod:** manual approval; **blue/green or rolling** per ECS service with health-check gating and
  connection draining (WS). Canary the WS gateway/Execution roles first. Auto-rollback on health/SLO breach.

### 22.6 Environments & secrets
- Per-env config via Secrets Manager/SSM; no secrets in CI logs/images. Least-privilege CI IAM (OIDC to AWS).

### 22.7 Observability hooks
- Deploy markers to dashboards; post-deploy smoke + SLO watch; alert if error rate/latency regresses.

## Non-functional Requirements
- Reproducible builds; immutable artifacts; fast feedback (<~15min PR pipeline; heavy suites async).
- No deploy bypasses migrations or integrity gates.

## Edge Cases
- Migration applied but rollout fails → service still backward-compatible (expand/contract) so old +
  new coexist safely. WS draining on deploy → clients reconnect + snapshot. Hotfix path documented.

## Future Considerations
- Progressive delivery (feature flags), automated canary analysis, ephemeral preview environments,
  chaos experiments in staging, multi-region pipelines.

## Risks
- **Destructive migration in prod** → expand/contract rule + review + no down-migrations. **Boundary
  erosion** → architecture tests as a gate. **Slow pipeline** → parallelize; heavy suites scheduled.

## Deliverables
- **D1** CI stage list + blocking gates (22.1–22.2), incl. integrity suites + architecture tests.
- **D2** Build/artifact + SBOM + ECR strategy (22.3).
- **D3** Migration-in-CD (expand/contract) + deployment strategy (blue/green, canary, draining,
  auto-rollback) (22.4–22.5).
- **D4** Secrets/IAM (OIDC) + post-deploy observability hooks (22.6–22.7).

---
> **Next phase:** Phase 23 — Folder Structure.
