# ContestForge — AIDLC Phase 20: Testing Strategy

| | |
|---|---|
| **Phase** | 20 of 25 — Testing Strategy |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | **`docs/spec/testing-strategy.md` (source of truth)**; Phases 2/3/7 |
| **Feeds** | Phase 22 (CI gates), implementation |

---

## Goal
Confirm and formalise the **testing strategy**. `docs/spec/testing-strategy.md` is authoritative
(already updated for the wildcard once-per-contest/eligibility changes). This phase aligns it to the
features/use cases and fixes the integrity-critical test suites and CI gates.

## Assumptions
- Tests co-located with code (per testing-strategy). Pytest + async fixtures; ephemeral PG/Redis
  containers; schemathesis for contracts; Playwright/RTL/MSW/axe on frontend.

## Functional Requirements
### 20.1 Test pyramid
- **Unit** (domain/services via fake adapters — ports enable infra-free tests): scoring math, lifecycle
  state machine, tie-break, eligibility, idempotency hash.
- **Integration** (real PG/Redis): repos, migrations, **tenant scoping**, outbox/consumer, leader
  election, partitions.
- **Contract:** schemathesis vs `api-contracts.yaml`; WS contract conformance (Phase 15) via a harness.
- **E2E:** Playwright for participant live flow + moderator console + builder happy paths.

### 20.2 Integrity-critical suites (must-pass gates)
| Suite | Asserts | NFR |
|---|---|---|
| **Tenant isolation** | no cross-tenant read/write on 100% of tenant-scoped resources/WS actions | NFR-8 |
| **Durability** | 0 lost answers / 10k submits @ 1% induced persistence failure | NFR-5 |
| **Recovery** | resume ≤30s post-crash, totals identical, no double-score | NFR-6,9 |
| **Cache-loss rebuild** | ranks/scores identical after Redis flush | FR-44 |
| **Reconnection** | restore ≤3s | NFR-7 |
| **Mode correctness** | correct scoring model in 100% regression cases | NFR-10 |
| **Idempotency** | duplicate submit→one row/score; duplicate scoring→one Score | FR-39 |
| **Late submission** | `> close_at` rejected regardless of client clock (freezegun) | FR-20 |

### 20.3 Domain test grids
- **Scoring matrix:** {Standard, Speed(bands), Speed(decay), Elimination} × {correct, wrong, timeout,
  skip, second-chance} → expected points (incl. floor 0, no negative, band upper-inclusive, attempt-2 time).
- **Tie-break:** total-time (attempt-2 on SC) → fewest-wrong → earliest-last-correct.
- **Wildcards:** once-per-contest, eligibility @ question start, Fifty-Fifty pre-answer, multi-on-one-Q.
- **Elimination:** rule combos AND/OR; bottom-X tie = all; survivor lock/reset; no-submit-after-eliminated.
- **Lifecycle:** legal transitions only; locks at PUBLISHED/REGISTRATION_OPEN; auto-go-live idempotent.

### 20.4 Performance/load
- 10k concurrent participants/contest: reveal fan-out p99 ≤200ms; leaderboard push ≤500ms (≤5k) /≤2s
  (≤20k); soak for timer drift ≤±50ms; scoring lag under burst. Tooling: load harness (e.g. k6/locust + WS).

### 20.5 Frontend tests
- RTL component (ack states, masked board, timer snap); MSW integration vs OpenAPI; Playwright e2e
  (answer→ack, reconnect, waiting-for-host, elimination→spectator); axe a11y (WCAG AA).

### 20.6 CI gates (→ Phase 22)
- Unit+integration green; contract conformance green; tenant-isolation suite green; coverage threshold;
  migration check (expand/contract); lint/type. Load/soak run on a schedule/pre-release, not every PR.

## Non-functional Requirements
- Negative/failure paths tested, not just happy paths. Integrity suites are **blocking** in CI.
- Tests deterministic (freeze time; seed; container isolation).

## Edge Cases
- Boundary submit at exact `close_at`; SC after correct rejected; capacity race; partition-spanning
  queries; reduced-motion UI; 4k-OTP import; masked tie display.

## Future Considerations
- Chaos testing (kill workers/Redis mid-contest); contract testing for WS via shared schema; mutation
  testing on scoring; per-tenant load profiles.

## Risks
- **Mode-correctness gaps** → exhaustive grid (20.3). **Flaky live/WS e2e** → deterministic harness +
  retries-with-cause. **Load infra cost** → scheduled, not per-PR.

## Deliverables
- **D1** Confirmation `testing-strategy.md` is authoritative; this phase aligns + extends.
- **D2** Integrity-critical suite list (20.2) as blocking CI gates.
- **D3** Domain test grids (20.3) + performance/load plan (20.4).
- **D4** Frontend test set (20.5) + CI gate definition (20.6 → Phase 22).

---
> **Next phase:** Phase 21 — Deployment Architecture.
