# ContestForge — AIDLC Phase 9: Task Breakdown

| | |
|---|---|
| **Phase** | 9 of 25 — Task Breakdown |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 8 (Feature Decomposition) |
| **Feeds** | Phases 10 (Backend), 11 (UX), 12 (UI) tasks; delivery tracking |

---

## Goal
Define **how features (F0–F24, FE1–FE9) decompose into tasks**: the task taxonomy, sizing, Definition
of Ready/Done, and the cross-cutting work that recurs in every feature. Phases 10–12 then enumerate the
concrete Backend/UX/UI tasks. This phase is the work-breakdown method + the master structure.

## Assumptions
- A task is ≤1–2 days, single-discipline where possible, independently verifiable, and traceable to a
  feature + FR/UC. Larger items are split.
- Every feature yields tasks across: **domain**, **application/service**, **adapter/infra**, **API/WS
  contract**, **migration**, **tests**, **frontend (paired)**, **docs/observability**.
- Tasks inherit the Phase-2 Definition of Done (tenant isolation, authz, audit, server-authoritative,
  tests incl. failure path, a11y for UI).

## Functional Requirements
### 9.1 Task taxonomy (per feature)
| Type | Examples |
|---|---|
| **D** Domain | entities/value objects, invariants (BR-#), domain services |
| **A** Application | use-case command/query handlers, validation, orchestration |
| **I** Infra/adapter | SQLAlchemy repo, Redis adapter, S3, consumer wiring |
| **C** Contract | Pydantic schemas, OpenAPI path, WS event/action schema |
| **M** Migration | Alembic revision, indexes, partitions, RLS policy |
| **T** Test | unit (fakes), integration (PG/Redis), contract, isolation, load |
| **F** Frontend | component, page, state, a11y, MSW mocks |
| **O** Ops/Obs | metrics, logs, traces, dashboards, alerts, runbook |

### 9.2 Definition of Ready (task may start)
Feature dependency merged · contract/schema agreed · acceptance criteria from the source story/UC ·
test approach noted · tenant-scope + authz identified.

### 9.3 Definition of Done (task complete)
Code + tests pass (incl. negative path) · tenant-isolation asserted where applicable · contract
conformance (schemathesis) green · docs/observability updated · reviewed against standards (Phase 24).

### 9.4 Estimation/sizing
T-shirt → ideal-day mapping (XS≈0.5d, S≈1d, M≈2d, L = split). Critical-path features (F14–F19, F23)
get explicit risk buffers.

### 9.5 Master WBS (feature → task clusters)
Each Must feature expands into D/A/I/C/M/T (+F for paired FE). Phases 10–12 list them. Cross-cutting
recurring tasks (apply per feature): tenant-scope tests, audit hooks, error mapping, OTel spans,
contract tests.

## Non-functional Requirements
- 100% of tasks trace to a feature and FR/UC; no orphan tasks.
- Each feature's task set, taken together, satisfies the feature's acceptance criteria.
- Test tasks are first-class, not implied.

## Edge Cases
- A "small" config change touching the state machine (F6) may fan out to many contract+test tasks —
  split rather than hide.
- Shared adapters (Redis EventBus) are built once (F13) and reused — tracked as foundation tasks, not
  duplicated per feature.

## Future Considerations
- Auto-generate a task tracker (issues) from this WBS.
- Velocity calibration after Wave 2 to refine estimates.

## Risks
- **Under-counting test/infra tasks** → schedule slip. *Mitigation:* taxonomy forces T/I/M per feature.
- **Hidden cross-feature tasks** (shared adapters) double-counted or dropped. *Mitigation:* foundation
  tasks owned by F13/F0.

## Deliverables
- **D1** Task taxonomy + Ready/Done (9.1–9.3).
- **D2** Sizing scheme (9.4).
- **D3** Master WBS mapping (9.5) → drilled in Phases 10–12.
- **D4** Recurring cross-cutting task checklist (per feature).

---
> **Next phase:** Phase 10 — Backend Tasks.
