# ContestForge — AIDLC Phase 19: Logging & Monitoring

| | |
|---|---|
| **Phase** | 19 of 25 — Logging & Monitoring |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 7 (observability base), technical-spec §6 |
| **Feeds** | Phase 21/22 (deploy/CI), Phase 24, runbooks |

---

## Goal
Define **observability**: structured logging, metrics, distributed tracing, dashboards, SLOs, and
alerting — aligned to the NFR targets and the durability/recovery guarantees.

## Assumptions
- OpenTelemetry SDK → AWS CloudWatch (or Prometheus/Grafana if EKS). Adaptive sampling (100% errors,
  1–10% normal). Logs structured JSON.

## Functional Requirements
### 19.1 Logging
- JSON logs with correlation id + `tenant_id`/`contest_id`/`participant_id` where applicable. **No
  secrets/JWTs/PII.** Levels: debug/info/warn/error. **Audit logs** (separate, 1-yr retention) for org
  create/suspend, lifecycle transitions, wildcard activations, elimination events, tie-break resolutions.
- Security events (cross-tenant attempts, auth failures, rate-limit breaches) flagged + alertable.

### 19.2 Metrics (NFR-aligned)
| Metric | NFR |
|---|---|
| reveal fan-out latency p99 | NFR-1 (≤200ms) |
| timer drift p99 | NFR-2 (±50ms) |
| leaderboard push latency p99 | NFR-3 (≤500ms/≤2s) |
| answer-accept rate / durable-write latency | NFR-5 |
| scoring lag / queue depth per partition | scale triggers |
| WS connection count per pod | NFR-4 / scaling |
| recovery duration | NFR-6 (≤30s) |
| reconnect restore time p99 | NFR-7 (≤3s) |
| outbox PENDING age / dead-letter count | integrity ops |
| error rate by code | <0.1% target |

### 19.3 Tracing
- Distributed traces across **API → Redis Stream → engine workers** for the answer/scoring path; spans
  for submission durable write, scoring, leaderboard push. Trace id == correlation id.

### 19.4 Dashboards
- **Live contest** (per-contest): participants, reveal latency, scoring lag, leaderboard push, eliminations.
- **Platform health:** role CPU/mem, WS connections, queue depths, DB pool, Redis. **Integrity:** outbox
  age, dead-letters, recovery events. **Security:** auth failures, cross-tenant attempts.

### 19.5 SLOs & alerting
- SLOs from NFRs (reveal ≤200ms p99; push ≤500ms; recovery ≤30s; error <0.1%). Alerts on breach,
  rising scoring lag/queue depth, outbox backlog/dead-letters, durable-write failure spikes, security
  events. Health/readiness probes per role; paging policy for live-contest-impacting alerts.

### 19.6 Backup/DR signals
- RPO ≤5min (answers), RTO ≤30min (service); RDS 35-day backups; alert on backup failure; recovery
  drills tracked.

## Non-functional Requirements
- Every request/command observable end-to-end (correlation/trace). No PII/secrets in telemetry.
- Alert noise controlled (symptom-based, NFR-threshold alerts; dedupe).

## Edge Cases
- High-cardinality labels (per-participant) avoided in metrics (use logs/traces). Sampling must keep
  100% of error/durability-fault traces. Clock-skew affects timer-drift metric interpretation.

## Future Considerations
- Per-tenant usage dashboards (billing foundation); anomaly detection; log-based SLO burn alerts;
  synthetic live-contest canaries.

## Risks
- **Blind spots on integrity** (outbox/dead-letter) → explicit metrics + alerts. **Telemetry cost/
  cardinality** → sampling + label hygiene. **Alert fatigue** → symptom-based SLO alerts only.

## Deliverables
- **D1** Logging spec + audit-log catalogue + redaction rules (19.1).
- **D2** Metrics catalogue mapped to NFRs (19.2) + tracing plan (19.3).
- **D3** Dashboard set (19.4) + SLOs/alerting policy (19.5).
- **D4** DR/backup signals (19.6) tied to RPO/RTO.

---
> **Next phase:** Phase 20 — Testing Strategy.
