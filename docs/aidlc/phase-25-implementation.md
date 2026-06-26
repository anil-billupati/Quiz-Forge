# ContestForge — AIDLC Phase 25: Implementation

| | |
|---|---|
| **Phase** | 25 of 25 — Implementation |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phases 1–24 (all design phases) |
| **Feeds** | The build itself |

---

## Goal
Provide the **implementation roadmap** that turns the design phases into shipped software: the execution
order, per-wave entry/exit criteria, readiness checklist, and the recommended first coding step. This
phase is the **playbook for building**, not a dump of all code — actual coding proceeds feature-by-feature
(behind the Phase-7 framework) once you give the go, starting from where Units 1–2 left off.

## Assumptions
- Phases 1–24 approved; specs (`docs/spec/`) remain source of truth. Units 1–2 (F0–F4 core) are
  implemented. We build one feature/wave at a time with tests, honoring the Definition of Done.

## Functional Requirements
### 25.1 Execution order (from Phase 8 build sequence)
1. **Wave 1 finish — Identity:** F5 bulk import (+ F2/F3/F4 hardening) · FE1 shell, FE3 users/import.
2. **Wave 2 — Authoring:** F6→F7→F8→(F9,F10,F11) · FE4 builder.
3. **Wave 3 — Registration & Real-time foundation:** F12, F13 · FE5 lobby.
4. **Wave 4 — Execution & Durability:** F14→F15 · FE6 live (skeleton).
5. **Wave 5 — Scoring core:** F16→F17→F18 · FE6 live (full), FE7 moderator.
6. **Wave 6 — Elimination/Results/Notifs/Audit:** F19→F21, F20, F22 · FE8, FE9.
7. **Wave 7 — Resilience & Performance:** F23→F24 (load to NFR targets, DR drills).

### 25.2 Per-wave entry/exit criteria
- **Entry:** dependencies merged; contracts (Phase 14/15) agreed; tasks (Phase 10–12) ready (DoR).
- **Exit:** feature ACs met; unit+integration+contract+isolation tests green; observability wired;
  reviewed vs standards (Phase 24) + spec adherence; demoable end-to-end (BE+FE).

### 25.3 Integrity-first build rules
- Build **durability + idempotency into F15/F16/F19 from the start** (not retrofitted by F23).
- F15 "done" = durable write + ack even with scorer offline. Tenant scoping fail-closed from day one.
- Each critical path (submission, scoring, elimination, recovery) ships with its integrity suite
  (Phase 20) before the wave exits.

### 25.4 Readiness checklist (before coding a feature)
spec section ✓ · use case + ACs ✓ · contract (API/WS) ✓ · migration plan ✓ · test plan (incl. negative) ✓
· tenant-scope + RBAC identified ✓ · observability signals identified ✓.

### 25.5 Recommended first step
- **Implement F5 (bulk participant import)** — smallest net-new Must feature, unblocks large-contest
  onboarding, low risk, exercises the framework (validation, batch insert, OTP, isolation tests). Then
  proceed to Wave 2 (authoring), the largest value block.

### 25.6 Definition of "v1 launch-ready"
- All Must features (F0–F19, F21, F23 + FE1,FE3–FE7) complete; success criteria met: durability
  (NFR-5), recovery (NFR-6/9), isolation (NFR-8), latency (NFR-1/3), reconnection (NFR-7), mode
  correctness (NFR-10). Should features (F20,F22,F24,FE2/8/9) as capacity allows.

## Non-functional Requirements
- Every shipped feature meets the Definition of Done; integrity suites blocking in CI (Phase 22).
- No wave exits with a known unmitigated integrity gap.

## Edge Cases
- A wave reveals a spec gap → raise as a decision (the way the 10 decisions were handled), update
  `docs/spec/`, then proceed — never implement a silent deviation.
- Frontend lagging backend → BE feature still validated via contract/integration tests; capability
  "done" only when paired.

## Future Considerations
- Won't-v1 features (self-registration, email/SMS, billing, non-MCQ, SSO, i18n, native, public viewer)
  scheduled post-launch behind the same module boundaries/ports.

## Risks
- **Skipping integrity tests under deadline** → blocking CI gates (Phase 22). **Sequencing inversion** →
  fixed wave order (25.1). **Scope creep into Won't-v1** → MoSCoW + decision discipline.

## Deliverables
- **D1** Execution roadmap (waves + entry/exit) (25.1–25.2).
- **D2** Integrity-first build rules + readiness checklist (25.3–25.4).
- **D3** Recommended first step (F5) + v1 launch-ready definition (25.5–25.6).
- **D4** Open decisions to resolve as encountered: spectator scope; FE2 Must/Should; F20 Must/Should.

### Status note
This completes the 25-phase AIDLC design series. **Coding is the next action** and proceeds on your go,
starting at F5 → Wave 2. No code is written by this phase document itself.

---
> **End of AIDLC phase series (1–25).**
