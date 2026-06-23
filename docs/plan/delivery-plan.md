# ContestForge — Delivery Plan

| | |
|---|---|
| **Project** | ContestForge |
| **Source** | docs/spec/*, docs/plan/architecture.md, ADR-001..003 |
| **Date** | 2026-06-22 |
| **Status** | Draft — for approval |

---

## How to use this plan

Implement **one unit at a time** with `/neutron:feature "Unit N: …"`. Each unit
is sized for roughly one to three days of focused implementation; units flagged
**high** complexity will likely be split into sub-features during
`/neutron:feature`. Every unit lists its dependencies, what it includes, and
checkable "done when" criteria. Tests are written within each unit (per the
testing strategy), not deferred.

The **critical path** is the live engine chain (Units 7→8→9→10→11/12→13). Units
off that path (authoring, notifications, audit, frontend) can proceed in
parallel once their dependencies are met — see §"Execution sequence".

---

## Units

### Unit 1: Platform foundation
Dependencies: none
Parallelisable with: none (everything depends on it)
Spec reference: technical-spec §1–2, §6, §7.1; ADR-001, ADR-003
What: The deployable skeleton all services share — app/config bootstrap, DB and
Redis connectivity, migrations, tenant-context plumbing, error model, and
observability baseline.
Includes:
- FastAPI app bootstrap, settings/config via env, dependency-injection wiring.
- PostgreSQL (async SQLAlchemy) + Alembic migrations; Redis client + Streams
  helper.
- Tenant-context middleware (resolve `tenant_id` from JWT), the tenant-scoping
  SQLAlchemy mixin + unscoped-query assertion, RLS policy scaffolding.
- Standard error model `{error:{code,message,details}}`, exception handlers,
  pagination envelope.
- `/health`, `/ready` (DB+Redis checks); structured JSON logging, OpenTelemetry
  tracing, base metrics.
- Docker Compose for local Postgres+Redis; CI lint/test pipeline.
Done when:
- App boots; `/health` and `/ready` return correctly against local Postgres+Redis.
- A migration creates a sample tenant-scoped table; the scoping mixin filters by
  `tenant_id` and the unscoped-query assertion fails a deliberate violation in a
  test.
- CI runs lint + tests green.
Estimated complexity: medium

### Unit 2: Tenancy & Identity
Dependencies: Unit 1
Parallelisable with: none (most units need auth/RBAC)
Spec reference: product-spec FR-1..5, §2.5 role matrix; api-contracts Auth/Users/Organizations; domain-model Organization/User/RefreshToken; ADR-001
What: Authentication, the tenant/user model, and RBAC that gate everything else.
Includes:
- `Organization` CRUD (`POST/GET/PATCH /organizations`, status, settings, usage)
  with `slug`/`portal_url` uniqueness + immutability (BR-19); initial Org Admin
  provisioning.
- Super Admin bootstrap (deployment seed) + `POST /super-admins`.
- `User` CRUD (`POST/GET/PATCH /users`, role ≠ SUPER_ADMIN) within tenant.
- JWT login/refresh(rotating)/logout/me/change-password; argon2/bcrypt hashing;
  `RefreshToken` rotation (BR-20).
- RBAC dependency enforcing the role-permission matrix per endpoint.
- Tenant-isolation test suite scaffold (NFR-8) parameterized over resources.
Done when:
- Full onboarding chain works: seeded Super Admin → create org + Org Admin →
  Org Admin creates Moderator/Participant.
- Login returns role+tenant-scoped JWT; refresh rotates and revokes; logout
  revokes; expired/revoked tokens rejected.
- Cross-tenant access on a protected resource returns 403 in an automated test.
Estimated complexity: high

### Unit 3: Contest authoring — contests, groups & lifecycle
Dependencies: Unit 2
Parallelisable with: Unit 14, Unit 16, frontend units
Spec reference: product-spec FR-6..9; api-contracts Contests/Groups/Lifecycle; domain-model Contest/Group
What: Contest CRUD, the lifecycle state machine, and group management.
Includes:
- `Contest` CRUD; structure lock at Published; Draft-only edit/delete.
- Lifecycle transition endpoint enforcing the fixed non-skippable sequence with
  precondition checks (config-locked at Registration Open, `scheduled_start_at`
  required for SCHEDULED) → 409 on illegal transitions.
- `Group` CRUD (Draft only) with sequence/weight.
Done when:
- A Normal and a Grouped contest can be created, advanced through every stage,
  and illegal transitions/skips return 409.
- Edits/deletes after Draft are rejected; group changes after Draft rejected.
Estimated complexity: medium

### Unit 4: Configuration blocks
Dependencies: Unit 3
Parallelisable with: Unit 5
Spec reference: product-spec FR-10..16, FR-22..27 (config side), FR-33..35 (config); api-contracts Configuration; domain-model ConfigurationBlock/WildcardConfig/EliminationRule/Checkpoint; BR-2,3,4,6
What: The Configuration Block — the heart of the system — and its validation.
Includes:
- `PUT/GET /contests/{id}/configuration` for contest scope (Normal) and per
  group (Grouped); one block per scope (BR-2).
- Mode→scoring derivation and field validation (durations ranges; Speed bands/
  decay; fixed-scoring fields); reveal mode, ranking criterion, tie display,
  visibility, update frequency.
- `WildcardConfig` (enabled set, limits, eligibility, cooldown, carry_over).
- Elimination config: rules + checkpoints + block-level
  `elimination_combine_operator` + `survivor_score_reset`; required iff
  ELIMINATION else 422 (BR-4).
- Config lock at Registration Open.
Done when:
- Valid Standard/Speed/Elimination blocks persist and read back per scope.
- Invalid combinations (elimination block missing rules; bad ranges; config on
  locked contest) return 422/409 as specified.
Estimated complexity: high

### Unit 5: Questions & options
Dependencies: Unit 3
Parallelisable with: Unit 4
Spec reference: product-spec (authoring); api-contracts Questions; domain-model Question/Option
What: Question and option authoring, Draft-only.
Includes:
- `POST/GET/GET{id}/PATCH/DELETE` questions; `PUT …/options` to replace the set.
- Validation: ≥2 options, exactly one correct; group assignment for Grouped;
  sequence ordering; admin view includes correctness.
Done when:
- Questions with options can be created, listed (admin view), updated, deleted
  while Draft; post-Draft edits return 409; invalid option sets return 422.
Estimated complexity: low

### Unit 6: Registration
Dependencies: Unit 3 (Unit 2 for identity)
Parallelisable with: Unit 4, Unit 5
Spec reference: product-spec participant workflows; api-contracts Registration; domain-model Registration
What: Participant registration lifecycle.
Includes:
- `POST` self-register (Registration Open only), `GET` list (admin/moderator),
  `GET …/me`, `DELETE` withdraw (self before close, or Org Admin).
- Duplicate/closed-window handling → 409; participant-list finalization at
  Registration Closed.
Done when:
- A participant can register only during Registration Open, see their own
  registration, and withdraw before close; admins can list registrations.
Estimated complexity: low

### Unit 7: Real-time foundation (WebSocket gateway)
Dependencies: Unit 2, Unit 3
Parallelisable with: Unit 4, Unit 5, Unit 6
Spec reference: technical-spec §1–3; api-contracts §WebSocket, Live; FR-17, FR-43, NFR-1/7
What: The WebSocket gateway and Redis pub/sub fan-out the live contest rides on.
Includes:
- WS connect/auth (JWT, role, active registration), per-contest channel
  subscription, presence in Redis, connection lifecycle.
- Pub/sub fan-out scaffold (server→client event envelope), client→server action
  envelope, heartbeat/backpressure.
- `GET /contests/{id}/live-state` reconnect snapshot; reconnection restore path
  (≤3 s target).
Done when:
- A participant connects, authenticates, joins a contest channel, receives a
  broadcast test event, and on reconnect restores state via `/live-state`.
- Unauthorized/cross-tenant WS connects are rejected.
Estimated complexity: high

### Unit 8: Execution Engine
Dependencies: Unit 7, Unit 4, Unit 5
Parallelisable with: Unit 12 (after its own deps), Unit 14
Spec reference: product-spec FR-17..21; technical-spec §3.2; domain-model ContestExecutionState/QuestionWindow; FR-19/35 (custom milestone)
What: Server-authoritative timing, reveal, windows, and progression.
Includes:
- `ContestExecutionState` machine (phases), durable per-contest.
- `QuestionWindow` creation with authoritative `submission_close_at`; timers
  (±50 ms target, NFR-2).
- Reveal: Automatic (scheduled) + Moderator-Controlled; moderator `reveal`/
  `advance` controls (`POST /control/*`) and WS actions.
- Per-question and per-group progression incl. between-group pause for
  leaderboard/eliminations (FR-21).
Done when:
- An Automatic contest reveals questions on schedule and progresses to
  completion; a Moderator-Controlled contest advances only on moderator action.
- `QuestionWindow` close times are server-authoritative and persisted; state
  survives a worker restart (resumes from `ContestExecutionState`).
Estimated complexity: high

### Unit 9: Answer submission & durability
Dependencies: Unit 8
Parallelisable with: none (critical path)
Spec reference: product-spec FR-20, FR-38..42; technical-spec §3.1, §3.4; domain-model AnswerSubmission/OutboxEvent; ADR-002
What: The durable answer intake path and its guarantees.
Includes:
- WS `answer.submit` intake: window/eligibility/not-eliminated checks;
  late-submission rejection vs `submission_close_at` (FR-20).
- Durable Postgres write with server-accept timestamp + idempotency key;
  `answer.ack` only after commit (FR-38/40/41).
- Transactional `OutboxEvent` + Redis Streams publish; relay.
- Recovery: re-drive unscored persisted answers idempotently.
Done when:
- Accepted answers are durably persisted and acked; retries with the same
  idempotency key do not duplicate; late answers are rejected with
  `window_closed`.
- After a simulated crash, unscored answers are re-driven with no loss/dupes
  (feeds NFR-5/6 suite in Unit 17).
Estimated complexity: high

### Unit 10: Scoring Engine
Dependencies: Unit 9
Parallelisable with: none (critical path)
Spec reference: product-spec FR-12..16, FR-24/25 (scoring side); technical-spec §3.1; domain-model Score; BR-7,8,10,12; NFR-10
What: Authoritative point computation, at-most-once.
Includes:
- Fixed scoring (correct/wrong/negative/no-answer); Time-Based (bands + linear
  decay, floor); Second-Chance reduced rate; Skip (full Fixed / floor Speed).
- Tie-break data capture (total time, wrong count, last-correct timestamp).
- Group-score rollup (Sum/Weighted/Best-N).
- Idempotent Streams consumer; unique `score.answer_submission_id` (at-most-once).
Done when:
- Each mode produces correct points across boundary cases (unit-tested, NFR-10);
  a replayed scoring command does not double-score; rollup matches expected.
Estimated complexity: high

### Unit 11: Wildcard runtime
Dependencies: Unit 8, Unit 9, Unit 10
Parallelisable with: Unit 12
Spec reference: product-spec FR-22..27; domain-model WildcardActivation; BR-10,11,12,13; api-contracts §WebSocket wildcard.activate
What: Live wildcard activation and effects (the runtime gap noted in review).
Includes:
- WS `wildcard.activate` flow: validate enabled/limit/eligibility/cooldown/
  carryover; durable, at-most-once `WildcardActivation` log.
- Fifty-Fifty (server picks two incorrect to remove, correct preserved; blocked
  after answer selected); Second Chance (open attempt_no=2 window, reduced
  scoring); Skip (record SKIPPED, award full/floor).
- `wildcard.applied` server→client result event.
Done when:
- Each wildcard behaves per spec; limits/cooldown/eligibility enforced; a
  double-tap does not consume two uses; activations appear in the audit/export.
Estimated complexity: high

### Unit 12: Leaderboard Engine
Dependencies: Unit 10
Parallelisable with: Unit 11
Spec reference: product-spec FR-28..32; technical-spec §3.1; domain-model LeaderboardEntry; NFR-3; FR-44
What: Near-real-time ranking and push.
Includes:
- Redis ZSETs per view (Contest/Group/Survivor); ranking criteria (Score Only/
  Score+Time/Accuracy) with criterion-specific tie-break; tie display modes.
- Visibility (Always/Post-question/Hidden/Masked — Masked redaction in fan-out).
- Update frequency (per-answer/question/group); push via WS; `GET …/leaderboard`
  snapshot.
- Rebuild ZSETs from Postgres Score rows on cache loss (FR-44).
Done when:
- Rankings match expected order incl. ties under each criterion; Masked shows
  only own rank; push latency meets NFR-3 in a load check; a Redis flush rebuilds
  identical ranks.
Estimated complexity: high

### Unit 13: Elimination Engine
Dependencies: Unit 10, Unit 12
Parallelisable with: Unit 15 (after deps)
Spec reference: product-spec FR-33..37; technical-spec §3.3; domain-model EliminationEvent/Checkpoint; FR-21
What: Knockout evaluation and survivor management.
Includes:
- Checkpoint triggers (After Question/After Group/Custom Milestone); rule
  evaluation with block-level AND/OR; eliminated/survivor set computation.
- Survivor-list lock; score reset vs carry-forward (`survivor_score_reset`);
  spectator grant; Survivor Leaderboard activation.
- Elimination notifications (via Unit 14); `GET …/eliminations`.
Done when:
- The PRD §8.6 grouped example runs end-to-end (Bottom-50% then Top-10);
  eliminated participants cannot answer further; survivors carry/reset correctly;
  survivor leaderboard reflects checkpoints.
Estimated complexity: high

### Unit 14: Notifications
Dependencies: Unit 2 (consumed by Unit 13)
Parallelisable with: Unit 3, Unit 16, frontend
Spec reference: product-spec FR-37/41; api-contracts Notifications; domain-model Notification
What: Participant-facing notification record + delivery.
Includes:
- `Notification` entity; `GET /me/notifications`, `POST …/ack`.
- WS delivery of notification events (elimination, answer-ack, spectator,
  progress); created in the same outbox flow as their source event.
Done when:
- Notifications are persisted, delivered over WS, listable, and ack-able;
  delivery survives reconnection (re-fetch via REST).
Estimated complexity: low

### Unit 15: Results & exports
Dependencies: Unit 10, Unit 13
Parallelisable with: Unit 16
Spec reference: product-spec (results/exports); api-contracts Results
What: Final results, per-participant breakdown, exports, audits.
Includes:
- `GET …/results` (final leaderboard + per-participant breakdown) for
  Completed/Archived; `GET …/results/export` (CSV/JSON, incl. wildcard log).
- `GET …/wildcard-audit`.
- `final_rank`/`final_score` population at completion.
Done when:
- A completed contest returns correct results and a valid CSV/JSON export
  including wildcard activations; archived contests are read-only.
Estimated complexity: medium

### Unit 16: Audit log
Dependencies: Unit 2
Parallelisable with: Unit 3, Unit 14, Unit 15
Spec reference: technical-spec §6; api-contracts Audit; domain-model AuditLog; FR-15/27
What: The cross-cutting audit trail.
Includes:
- `AuditLog` entity + write hooks (org create/suspend, lifecycle transitions,
  wildcard activations, eliminations, tie-break resolutions).
- `GET /audit` (tenant-scoped for Org Admin; platform-wide for Super Admin) with
  filters + pagination.
Done when:
- Audited actions produce entries; `/audit` returns filtered, paginated, tenant-
  scoped results; Super Admin sees platform-wide.
Estimated complexity: low

### Unit 17: Resilience, recovery & performance hardening
Dependencies: Units 8–13
Parallelisable with: frontend
Spec reference: product-spec NFR-1..11, §5 success criteria; technical-spec §6.1; testing-strategy resilience/perf suites
What: Prove the durability/latency NFRs with automated suites.
Includes:
- Fault-injection persistence layer; no-answer-loss test (NFR-5); crash/recovery
  ≤30 s (NFR-6); Redis-loss rebuild (FR-44/NFR-9); reconnection ≤3 s (NFR-7).
- Load/perf harness: reveal fan-out ≤200 ms @10k (NFR-1), leaderboard push
  (NFR-3), timer accuracy (NFR-2); rate-limit enforcement (NFR-11).
Done when:
- All §5 success-criteria tests pass at target thresholds in CI (resilience
  nightly, perf pre-release).
Estimated complexity: high

### Unit 18: Frontend
Dependencies: API units (2–16) for the screens they back; can start against
contracts early.
Parallelisable with: backend units (developed against `api-contracts`)
Spec reference: product-spec §2 workflows; api-contracts (REST + WebSocket)
What: The Next.js/TypeScript web app. **Flag: high — split into 18a/18b.**
Includes:
- **18a Admin & authoring UI:** super-admin/org consoles, contest builder
  (structure, config blocks, wildcards, elimination, questions), registration
  management, results/exports, audit views.
- **18b Live & participant UI:** participant live view (question, timer-as-
  display, wildcards, leaderboard, notifications), moderator console (reveal/
  advance, monitor), reconnection handling.
Done when:
- 18a: an Org Admin can build and run a contest end-to-end through the UI.
- 18b: a participant can join live, answer, use wildcards, see the leaderboard,
  and reconnect; a moderator can control a live contest.
Estimated complexity: high (split)

---

## Execution sequence (recommended)

1. **Unit 1** (foundation) → **Unit 2** (identity) — strictly first; everything
   depends on them.
2. **Authoring wave (parallel):** Unit 3, then 4 + 5 in parallel, plus Unit 6;
   Unit 16 (audit) and Unit 14 (notifications) can start here too. Frontend 18a
   can begin against contracts.
3. **Live engine critical path (mostly sequential):** Unit 7 → Unit 8 → Unit 9
   → Unit 10 → then **Unit 11 + Unit 12 in parallel** → Unit 13.
4. **Results wave:** Unit 15 after 10+13; finalize Unit 14 wiring with 13.
5. **Hardening:** Unit 17 once 8–13 are in place.
6. **Frontend 18b** alongside the live engine path; integrate as engine units
   land.

Rationale: foundation and identity are global prerequisites; authoring has no
dependency on the live engine and parallelizes well; the engine chain is
inherently ordered by data flow (reveal → submit → score → rank/eliminate);
hardening validates the assembled system against the NFRs; the frontend tracks
the contracts and integrates progressively.

> Sizing note: Units 2, 4, 7, 8, 9, 10, 11, 12, 13, 17, 18 are **high**
> complexity and most will be split into 2–3 sub-features during
> `/neutron:feature`. Units 5, 6, 14, 16 are genuinely small.
