# ContestForge — Testing Strategy

| | |
|---|---|
| **Project** | ContestForge |
| **Stack** | Backend: Python + FastAPI · Frontend: Next.js + TypeScript · PostgreSQL + Redis |
| **Date** | 2026-06-19 |
| **Status** | Draft — for approval |

---

## 1. Testing Philosophy

ContestForge's correctness guarantees (server-authoritative scoring,
at-most-once counting, no answer loss, tenant isolation) are the product. Tests
exist primarily to prove these guarantees hold — including under failure. The
test pyramid is broad at the unit layer (engine logic), substantial at
integration (durability, tenancy, lifecycle), and focused at e2e (live contest
journeys). A dedicated **resilience/chaos** suite proves the durability NFRs.

Tests are written in the same step as the code they cover — implementation
presented without tests is incomplete.

---

## 2. Backend (Python / FastAPI)

**Frameworks:** `pytest`, `pytest-asyncio`, `httpx` (ASGI test client),
`testcontainers` (PostgreSQL + Redis), `factory_boy`/fixtures for test data,
`freezegun` (deterministic time), `schemathesis` (OpenAPI contract testing).

### 2.1 Unit tests
Pure engine logic, no I/O. Highest density.

- **Scoring Engine:** Fixed scoring (correct/wrong/negative/no-answer); Speed
  band scoring at each boundary (0–5/5–10/10–15/15–20/20+) and linear decay
  including the floor; Second Chance reduced rate; Skip = full (Fixed) / floor
  (Speed). Asserts mode→model mapping (BR-3, FR-12).
- **Tie-break logic:** the deterministic order — fastest total time → fewest
  wrong → earliest last correct (BR-14/FR-15) — across constructed ties.
- **Group rollup:** Sum, Weighted Sum, Best N (BR-15/FR-16).
- **Elimination rules:** First Wrong, N Wrong, Bottom X%, Min Score, plus
  AND/OR combinations (BR-4, FR-34).
- **Leaderboard ranking + tie display:** Shared Rank (1,1,3), Fastest, Least
  Incorrect (FR-32).
- **Lifecycle state machine:** legal transitions allowed, skips rejected, lock
  points enforced (BR-5/FR-7,9).
- **Config validation:** duration ranges, elimination-requires-rules invariant
  (BR-4,6).

### 2.2 Integration tests
Real PostgreSQL + Redis via testcontainers.

- **Tenant isolation (NFR-8):** for every tenant-scoped endpoint and query,
  a user from tenant A cannot read/write tenant B's data; cross-tenant access →
  `403`/`404`. Parameterized across all resources.
- **Answer durability path (FR-38/39/40/41):** an accepted answer is persisted
  before ack; idempotency key prevents duplicate rows; score row is unique per
  submission (at-most-once); `server_accepted_at` is set once and used for
  scoring even after a retried submit.
- **Late submission (FR-20):** answers past the server-side close time are
  rejected regardless of supplied client time (use `freezegun`).
- **Lifecycle + config locking:** editing config after Registration Open → 409.
- **Leaderboard rebuild (FR-44):** flush Redis, rebuild from Score rows, assert
  identical ranks/scores.
- **Wildcard rules:** once-per-contest usage (re-use rejected), eligibility
  (ALL vs TOP_50_PERCENT evaluated at question start), Fifty-Fifty
  blocked-after-answer, multiple wildcards on one question allowed.

### 2.3 Contract tests
- Run `schemathesis` against the live ASGI app using `api-contracts.yaml` to
  assert request/response conformance and status codes. CI fails on drift
  between implementation and the spec.

### 2.4 Resilience / chaos suite (proves NFRs)
Tagged `@resilience`, run in CI nightly and pre-release.

- **No answer loss (NFR-5):** drive 10,000 submissions with a 1% induced
  persistence-failure rate (fault-injection wrapper on the persistence layer);
  assert < 0.01 % lost answers after reconciliation.
- **Contest recovery (NFR-6):** kill and restart workers mid-contest; assert
  resume ≤30s, state intact, no double-scoring.
- **Ranking recovery:** total Redis loss; assert ranks correct after rebuild.
- **Consistent scoring (NFR-9):** snapshot score totals before fault, compare
  after recovery — must match.
- **Reconnection (NFR-7):** drop and reconnect a WS participant; assert state
  and open submission window restored ≤3s (FR-43).

### 2.5 Performance tests
- **Reveal fan-out (NFR-1):** measure p99 question delivery latency to 10,000
  simulated WS clients (≤ 200 ms server-side dispatch).
- **Leaderboard push (NFR-3):** p99 ≤ 500 ms at 5,000 / ≤ 2 s at 20,000
  simulated clients.
- **Timer accuracy (NFR-2):** p99 server-side drift ≤ ±50 ms over a 5-minute
  session.
- **Rate limiting (NFR-11):** verify per-user, per-tenant, and per-IP limits
  reject excess traffic while allowing legitimate loads.

Tooling: `locust` or `k6` (WS) for load; results gated against NFR thresholds.
Fault-injection and percentile metrics are captured in the observability
backend.

---

## 3. Frontend (Next.js / TypeScript)

**Frameworks:** `Vitest` + `React Testing Library` (unit/component), `MSW` (API
mocking), `Playwright` (e2e), mock WebSocket server for live-view tests.

- **Unit/component:** contest builder forms (config validation mirrors backend
  ranges), leaderboard rendering (shared-rank display, masked visibility),
  participant question view (timer display is presentational only; never drives
  scoring), wildcard UI states (available/used/ineligible).
- **Integration (MSW):** API flows for login, contest CRUD, registration,
  results — against mocked endpoints derived from `api-contracts.yaml`.
- **e2e (Playwright):** see §4.

---

## 4. End-to-End Journeys (Playwright)

Full stack against a test deployment (real API + Postgres + Redis):

1. **Super Admin → org creation → Org Admin login.**
2. **Normal Standard contest:** build, publish, register, run live, submit
   answers, verify scores and final leaderboard.
3. **Grouped mixed-mode contest** (Standard + Speed + Elimination, per PRD §2.2
   example): verify per-group config applies, Speed scoring differs, Bottom-50%
   elimination removes participants, Survivor Leaderboard appears, rollup =
   correct contest score.
4. **Moderator-controlled reveal:** moderator triggers reveals; interval timer
   pauses between questions.
5. **Reconnection:** participant disconnects mid-question and reconnects;
   submission window honored.

---

## 5. Test Data Strategy

- **Factories/fixtures** build tenants, users (each role), contests (Normal &
  Grouped), config blocks per mode, questions/options, and registrations.
- **Deterministic time** via `freezegun` (backend) and fixed clocks (frontend)
  so timing/scoring assertions are reproducible.
- **Seed scenarios:** a canonical "Fresher Hiring Challenge" grouped contest
  mirroring the PRD example, reused across integration and e2e.
- **Isolation:** each test runs in a transaction rollback or a fresh
  testcontainer schema; no shared mutable state between tests.

---

## 6. Mocking Strategy

- **External boundaries only:** notification transport and any future
  third-party integrations are mocked; the contest engines and data stores are
  exercised for real (via testcontainers) because they embody the guarantees.
- **Frontend:** mock the REST API (MSW) and WebSocket server; never mock
  internal frontend logic under test.
- **Fault injection:** a thin, test-only wrapper around the persistence/cache
  layers injects failures for the resilience suite — not a mock of the store
  itself.

---

## 7. Coverage Targets

| Layer | Target | Notes |
|---|---|---|
| Engine units (scoring, tie-break, elimination, rollup, lifecycle) | ≥ 95% line + branch | Core correctness; branch coverage on all mode/rule combinations. |
| Backend overall | ≥ 85% | |
| API endpoints | 100% covered by integration/contract tests | Every path + auth/tenant case. |
| Frontend components | ≥ 80% | |
| NFR criteria | 100% have a dedicated resilience/perf test | Each NFR-5..NFR-10 maps to a named test. |
| Tenant isolation | 100% of tenant-scoped resources tested | NFR-8. |

CI gates merges on: unit + integration + contract green, coverage thresholds
met, and the resilience suite green (nightly + pre-release). Performance gates
run pre-release against NFR thresholds.

---

## 8. Traceability

Each FR/NFR/BR maps to at least one test (tagged with the requirement id in the
test name or marker), so the suite doubles as living verification of the spec.
The Success Criteria table in `product-spec.md §5` is the acceptance gate.
