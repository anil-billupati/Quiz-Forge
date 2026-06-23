# ContestForge — AIDLC Phase 8: Feature Decomposition

| | |
|---|---|
| **Phase** | 8 of 25 — Feature Decomposition |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Source** | Phases 2–7; product-spec FRs; domain-model; architecture modules |
| **Depends on** | Phase 7 (Base Backend Framework) — approved |
| **Feeds** | Phase 9 (Task Breakdown), Phases 10–12 (BE/UX/UI tasks), delivery sequencing |

---

## Goal
Decompose ContestForge into a **catalogue of features** sized for delivery — each feature a coherent,
independently valuable, testable slice mapped to architecture modules (Phase 5), use cases (Phase 3),
and FRs. Establish **dependencies, priority (MoSCoW), and a build sequence** so Phase 9 can break
features into tasks and the team can deliver one feature at a time without rework. This is *our*
decomposition (not the pre-existing Neutron delivery plan), though it deliberately stays compatible
with the same bounded contexts so existing Units 1–2 slot in.

## Assumptions
- Feature = vertical slice (domain + application + adapters + tests; UI tracked as paired frontend
  features) deliverable behind the Phase 7 framework. Cross-cutting scaffolding (F0) already exists.
- **Units 1–2 are done** (platform foundation; tenancy/identity core): F0 and most of F1–F4 are
  implemented; this phase still lists them for a complete dependency graph and to scope the remainder
  (e.g. F5 bulk import is new).
- Priority uses **MoSCoW** for v1 (Must = core engine integrity & live contest; Should = operability;
  Could = niceties; Won't = deferred per product-spec §6).
- Backend and frontend features are listed separately but paired; a contest capability isn't "done"
  until both halves and tests exist (Phase 2 Definition of Done).
- Sequence respects the hard rule: **real-time + execution + durability must precede scoring,
  leaderboard, elimination** (you cannot score what you cannot durably submit).

## Functional Requirements
*(The feature catalogue — this phase's substance. Each: ID · feature · module · priority · key FR/UC ·
depends-on.)*

### Backend / full-stack features
| ID | Feature | Module | Pri | FR / UC | Depends on |
|---|---|---|---|---|---|
| **F0** | Platform foundation (config, async DB, Redis, error model, observability, CI, health/ready) | platform | Must | tech-spec §5,6 | — |
| **F1** | Organization provisioning & status (create, suspend/reactivate, audit) | identity | Must | FR-1,2 / UC-1 | F0 |
| **F2** | Tenant settings & usage aggregates | identity | Must | FR-3a,3b / UC-1 | F1 |
| **F3** | Auth & session (JWT access/refresh rotation, change-pwd, login rate-limit) | identity | Must | FR-4,5 / UC(GP1) | F0 |
| **F4** | User management (create/list/update; super-admin create) | identity | Must | FR-5 / UC | F1,F3 |
| **F5** | Bulk participant import (CSV/JSON, per-row result, OTP) | identity | Must | FR-3a / UC-2 | F4 |
| **F6** | Contest CRUD & lifecycle state machine (incl. lifecycle events, locking) | authoring | Must | FR-6,7,9 / UC-3 | F4 |
| **F7** | Groups (Grouped contests; sequence/weight) | authoring | Must | FR-8 / UC-3 | F6 |
| **F8** | Configuration blocks (mode-derived scoring, validation, ranges) | authoring | Must | FR-10,12 / UC-4 | F6,F7 |
| **F9** | Wildcard config (enabled set + eligibility) | authoring | Must | FR-22,26 / UC-4 | F8 |
| **F10** | Elimination rules & checkpoints config | authoring | Must | FR-10,33,34 / UC-4 | F8 |
| **F11** | Questions & options (≥2 options, exactly one correct) | authoring | Must | FR-10 / UC-5 | F6,F7 |
| **F12** | Registration (self-register, withdraw, list, capacity) | execution | Must | FR-3a / UC-6 | F6,F4 |
| **F13** | Real-time foundation: WS gateway (ticket auth, presence incl. host, pub/sub fan-out) | execution/platform | Must | FR-43 / UC-7 | F3,F6 |
| **F14** | Execution engine (timers, reveal Auto+Moderator, progression, go-live scheduler, auto-pause/host-presence, leader election) | execution | Must | FR-9,17,18,19,21 / UC-8,12,13 | F8,F11,F13 |
| **F15** | Answer submission & durability (durable write→ack, idempotency, late-reject) | scoring | Must | FR-17,20,38,40,41 / UC-9 | F13,F14 |
| **F16** | Scoring engine (Fixed/Time-Based, Second-Chance/Skip, at-most-once, tie-break data) | scoring | Must | FR-12,13,14,15,39 / UC-10 | F15,F8 |
| **F17** | Wildcard runtime (Fifty-Fifty, Second Chance, Skip; once-per-contest; eligibility) | scoring | Must | FR-23,24,25,26,27 / UC-9 | F16,F9 |
| **F18** | Leaderboard engine (Contest/Group/Survivor views, ranking criteria, visibility incl. masked, update freq) | scoring | Must | FR-28,29,30,31,32 / UC-10 | F16 |
| **F19** | Elimination engine (checkpoint eval, AND/OR, bottom-X tie rule, survivor lock, notify) | elimination | Must | FR-33–37 / UC-11 | F16,F18,F10 |
| **F20** | Notifications (in-app: ack, progress, elimination, spectator) | platform | Should | FR-37,41 / UC-11,L2 | F13,F19 |
| **F21** | Results, exports & immutable snapshot (CSV/JSON, breakdowns, wildcard/elim audit) | platform | Must | FR-27,45 / UC-15 | F16,F18,F19 |
| **F22** | Audit log query (tenant + platform scope) | platform | Should | tech-spec §6 / UC-15 | F1,F6 |
| **F23** | Resilience: recovery & reconnection hardening (crash resume, cache rebuild, reconnect snapshot) | platform/all | Must | FR-42,43,44 / UC-14 | F14,F15,F16,F18 |
| **F24** | Performance & observability hardening (load to NFR targets, dashboards, alerts) | platform | Should | NFR-1..11 | F23 |

### Frontend features (paired)
| ID | Feature | Surface | Pri | Depends on (BE) |
|---|---|---|---|---|
| **FE1** | Auth + role-aware shell (login, change-pwd, routing) | all | Must | F3 |
| **FE2** | Platform Console (orgs, status, settings, usage) | Super Admin | Should | F1,F2 |
| **FE3** | Org Console — Users + bulk import panel | Org Admin | Must | F4,F5 |
| **FE4** | Contest Builder (lifecycle-gated: structure/groups/config/questions) | Org Admin | Must | F6–F11 |
| **FE5** | Registration & lobby | Participant | Must | F12 |
| **FE6** | Participant Live App (question, answer/ack, timer, wildcards, leaderboard, reconnect, spectator) | Participant | Must | F13–F19 |
| **FE7** | Moderator Console (reveal, advance, monitor, take-over/host) | Moderator | Must | F13,F14,F18,F19 |
| **FE8** | Results & exports views | Org Admin | Should | F21 |
| **FE9** | Notifications UI | Participant | Should | F20 |

## Non-functional Requirements
- Each feature is **independently testable** and ships with tests (unit/integration; isolation where
  tenant-scoped) per the Definition of Done.
- Features map to ≥1 FR/UC; no orphan features; the dependency graph is acyclic.
- **Must** features collectively satisfy the Phase-5 success criteria (durability, recovery, isolation,
  latency, mode correctness). **Should/Could** features improve operability/UX without gating launch.
- Vertical slices keep coupling low: a feature touches its module + ports, not other modules' internals.

## Edge Cases
- **F15 before F16 must hold integrity alone:** answer submission is "done" (durable + acked) even if
  scoring (F16) lags or is offline — the durability guarantee cannot depend on the scorer.
- **F14 go-live scheduler vs F13 presence:** auto-pause (host-presence) is part of F14 but needs F13
  presence; sequence enforces F13 first.
- **F18 masked leaderboard depends on full compute (F16):** masked view still requires the full ranking
  server-side; not a separate ranking path.
- **F19 elimination re-run idempotency** depends on F23 recovery semantics; F19 must be built
  idempotent from the start (not retrofitted by F23).
- **F5 bulk import capacity** interacts with F2 tenant limits — F5 depends on F2.
- **F21 results** depend on F19 (eliminations) and F18 (final ranks) — results are not just F16 scores.

## Future Considerations (Won't — v1)
- Self-registration / join codes; email/SMS notification transport; billing/subscriptions; non-MCQ
  question types; question bank/reuse; public spectator viewer; native mobile; SSO; i18n. (Each becomes
  a future feature behind the same module boundaries / ports — per product-spec §6.)

## Risks
- **Sequencing inversion:** building scoring/leaderboard before durable submission + execution causes
  rework. *Mitigation:* the build sequence (§D2) fixes execution+durability before scoring.
- **Feature bloat in the Builder (F8/FE4):** the config block is the most complex feature; risk of a
  mega-feature. *Mitigation:* split config (F8), wildcards (F9), elimination (F10), questions (F11) as
  separate features with their own validation.
- **Cross-module leakage under deadline:** features reaching into other modules to "save time."
  *Mitigation:* port-only boundary contract (Phase 5 §D3) enforced in review/CI.
- **"Done" without the frontend half:** a BE feature looking complete while unusable. *Mitigation:*
  paired FE features + DoD requiring both halves for a user-facing capability.
- **Resilience treated as a late feature (F23):** retrofitting recovery is costly. *Mitigation:*
  idempotency/outbox built into F15/F16/F19 from the start; F23 *validates and hardens*, not invents.

## Deliverables
### D1 — Feature catalogue
24 backend/full-stack features (F0–F24) + 9 paired frontend features (FE1–FE9), each mapped to module,
priority, FR/UC, and dependencies (see §Functional Requirements).

### D2 — Build sequence (waves, dependency-ordered)
1. **Wave 0 (done):** F0 platform foundation.
2. **Wave 1 — Identity & Tenancy:** F1, F2, F3, F4, F5. *(Units 1–2 cover F1–F4; F5 is new.)*
3. **Wave 2 — Authoring:** F6 → F7 → F8 → (F9, F10, F11).
4. **Wave 3 — Registration & Real-time foundation:** F12, F13.
5. **Wave 4 — Execution & Durability:** F14 → F15.
6. **Wave 5 — Scoring core:** F16 → F17 → F18.
7. **Wave 6 — Elimination & Results:** F19 → F21; F20 notifications; F22 audit.
8. **Wave 7 — Resilience & Performance:** F23 → F24.
9. **Frontend** tracks each wave: FE1 (W1), FE3/FE4 (W2), FE5 (W3), FE6/FE7 (W4–6), FE2/FE8/FE9 (W6–7).

### D3 — Dependency graph (text)
```
F0 → {F1,F3}
F1 → F2 → F5         F1 → F4 → {F5,F6,F12}
F3 → {F4,F13}
F6 → {F7,F11,F12,F22};  F7 → F8;  F8 → {F9,F10,F16}
F13 → F14;  {F8,F11,F13} → F14 → F15 → F16
F16 → {F17,F18};  {F16,F18,F10} → F19
{F16,F18,F19} → F21;  {F13,F19} → F20
{F14,F15,F16,F18} → F23 → F24
```

### D4 — Priority summary
- **Must (launch-gating):** F0–F19, F21, F23 + FE1,FE3–FE7. These deliver a correct, durable, recoverable
  live multi-tenant contest with results.
- **Should (operability/UX):** F20, F22, F24 + FE2,FE8,FE9.
- **Won't (v1):** product-spec §6 deferrals.

### D5 — Open questions carried forward
1. Spectator feature scope (which views) — affects F19/FE6 (open since Phase 3).
2. Whether FE2 (Platform Console) is v1-Must or Should (Super Admin could operate via API initially).
3. Notifications (F20) Must vs Should — in-app ack overlaps with F15's WS ack; confirm scope split.

---

> **Next phase (await approval):** Phase 9 — Task Breakdown. Do not generate until approved.
