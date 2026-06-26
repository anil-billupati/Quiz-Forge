# ContestForge — AIDLC Phase 10: Backend Tasks

| | |
|---|---|
| **Phase** | 10 of 25 — Backend Tasks |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 9 (Task Breakdown), Phase 8 (Features) |
| **Feeds** | Implementation (Phase 25), test tasks (Phase 20) |

---

## Goal
Enumerate the **concrete backend tasks** per feature (using the Phase-9 taxonomy D/A/I/C/M/T/O), in
build-sequence order, so implementation can proceed feature-by-feature behind the Phase-7 framework.

## Assumptions
- Units 1–2 (F0–F4 core) exist; tasks below are the remainder + hardening.
- Tasks reference ports/adapters from Phase 7; contracts from Phases 14/15.

## Functional Requirements
*(Backend task list by feature. Abbreviated to task clusters; each cluster = 1–3 tasks.)*

### Wave 1 — Identity (remainder)
- **F5 Bulk import:** A-handler (parse CSV/JSON, per-row validate, capacity check) · I-batch insert +
  OTP generation · C-`BulkCreateParticipants{Request,Result}` · T-unit (dup/invalid/capacity), integration,
  isolation. *FR-3a.*
- **F2/F3/F4 hardening:** O-rate-limit on `/auth/login`; T-refresh rotation reuse-revokes-family; T-isolation
  on users/orgs.

### Wave 2 — Authoring
- **F6 Contest + lifecycle:** D-lifecycle state machine (legal transitions, locks) · A-CRUD + transition
  handler · I-repo + `ContestLifecycleEvent` writer · C-contest schemas · M-`contest`,`contest_lifecycle_event`
  + index · T-illegal-transition 409, lock-after-stage. *FR-6,7,9; BR-5.*
- **F7 Groups:** A/I/C/M-group CRUD; unique `(tenant,contest,sequence)`; T-Draft-only.
- **F8 Config block:** D-mode→scoring derivation + range invariants · A-PUT/GET with validation · I-repo ·
  C-`ConfigurationBlock` · M-`configuration_block` (+ partial uniques, CHECK one-of contest/group) · T-mode/
  scoring mismatch 422, lock 409. *FR-10,12; BR-3,4,6,20.*
- **F9 Wildcard config:** A/I/C/M-`wildcard_config` {type,eligibility}; unique `(block,type)`; T-eligibility enum.
- **F10 Elimination config:** A/I/C/M-`elimination_rule`,`checkpoint`; require rules+checkpoint+operator on
  ELIMINATION; T-422 paths. *FR-33,34; BR-4.*
- **F11 Questions/options:** A-create/edit/replace-options (exactly-one-correct) · I/M-`question`,`option`
  (+ partial uniques) · C-question schemas · T-<2 options/≠1 correct 422, seq conflict 409. *FR-10; BR-21.*

### Wave 3 — Registration & Real-time foundation
- **F12 Registration:** A-register/withdraw/list (atomic capacity) · I/M-`registration` (+ unique, status index) ·
  T-capacity race, stage 409, dup 409. *FR-3a.*
- **F13 WS gateway:** I-ticket mint/consume (Redis single-use) · I-connection registry + presence (participant
  + host heartbeat TTL) · I-pub/sub subscribe/fan-out · A-WS action router + RBAC per action · C-WS envelope
  (Phase 15) · O-WS metrics · T-ticket expiry/reuse, presence, cross-tenant reject. *FR-43; UC-7.*

### Wave 4 — Execution & Durability
- **F14 Execution engine:** D-phase model + progression rules · A-reveal (Auto schedule + Moderator trigger),
  advance override, between-group pause · I-leader election (Redis lease/heartbeat) · I-go-live scheduler
  (version-guarded) · I-host-presence auto-pause/resume · I/M-`contest_execution_state`,`question_window`
  (+ uniques, optimistic version) · O-reveal-latency metric · T-recover open window, idempotent go-live,
  auto-pause on host absent. *FR-9,17,18,19,21; UC-8,12,13.*
- **F15 Submission & durability:** A-validate (window/eliminated) + durable insert before ack · D-`idempotency_hash`
  builder + outcome eval · I/M-`answer_submission` (unique idempotency, partitioned by contest hash,
  `server_accepted_at` trigger via `clock_timestamp()`) + outbox write (same txn) · C-`answer.submit/ack`
  WS · T-late reject (`window_closed`), duplicate→one row, durability under induced failure. *FR-17,20,38,40,41;
  BR-7,9; NFR-5.*

### Wave 5 — Scoring core
- **F16 Scoring engine:** A-idempotent consumer (dedupe submission id) · D-Fixed (floor 0, no negative) /
  Time-Based (band upper-inclusive first-match / linear decay) / Second-Chance rate / Skip credit · D-tie-break
  capture (attempt-2 time) · I/M-`score` (unique per submission, co-partitioned), `participant_score_summary`
  upsert · O-scoring-lag metric · T-mode correctness matrix (NFR-10), at-most-once on replay. *FR-12–15,39; BR-8,14,14a,14c.*
- **F17 Wildcard runtime:** A-activate (enabled/eligibility/once-per-contest; Fifty-Fifty pre-answer) · D-effects
  (option removal preserve-correct; second attempt; skip credit) · I/M-`wildcard_activation` + audit · C-`wildcard.activate`
  WS · T-once-per-contest, eligibility @ question start, multi-on-one-question. *FR-23–27; BR-10,11,12,13.*
- **F18 Leaderboard engine:** A-ranking per criterion + tie display · I-ZSET per view (Contest/Group/Survivor) ·
  A-masked per-participant emit · A-update-frequency gating · O-push-latency metric · T-ranking/tie correctness,
  masked never broadcasts, rebuild-from-PG. *FR-28–32; BR-14,14b; NFR-3.*

### Wave 6 — Elimination, Results, Notifications, Audit
- **F19 Elimination engine:** A-checkpoint consumer; rule eval (AND/OR); bottom-X tie=all; survivor lock;
  reset/carry · I/M-`elimination_event` (+ unique) · A-notify + outbox · T-idempotent re-run, tie boundary,
  no-submit-after-eliminated. *FR-33–37; BR-16,25.*
- **F21 Results/exports/snapshot:** A-results assembly + breakdown · A-CSV/JSON export · I-S3 (optional) ·
  A/M-`contest_result_snapshot` on Archive (immutable) · T-pre-Completed 409, archived read-only. *FR-27,45; BR-27.*
- **F20 Notifications:** A-create/list/ack · I/M-`notification` + pub/sub push · T-types/ack. *FR-37,41.*
- **F22 Audit query:** A-query (tenant vs platform scope) · T-scope isolation. *tech-spec §6.*

### Wave 7 — Resilience & Performance
- **F23 Recovery:** A-startup state reload + unscored re-drive · A-outbox replay · A-ZSET/summary rebuild ·
  T-crash resume ≤30s no double-score (NFR-6,9), cache-loss rebuild (FR-44), reconnect snapshot ≤3s (NFR-7).
- **F24 Perf/obs hardening:** O-dashboards + alerts (NFR thresholds) · T-load (10k reveal ≤200ms; leaderboard
  push), soak; tune pools/partitions.

## Non-functional Requirements
- Every backend task ships tests (incl. failure path) and respects fail-closed tenancy + atomic outbox.
- Critical-path tasks (F14–F19, F23) have explicit durability/idempotency tests.

## Edge Cases
- `server_accepted_at` set by DB trigger (not app) to guarantee authoritative time.
- Migrations are expand/contract (backward-compatible) for rolling deploys.
- Partitioned tables (`answer_submission`,`score`) created with 64 hash partitions up front.

## Future Considerations
- CDC-based outbox; PgBouncer; read-replica routing for results/audit.

## Risks
- **Scoring correctness matrix gaps** → NFR-10 miss. *Mitigation:* exhaustive mode/wildcard test grid (F16/T).
- **Partition/migration mistakes** on hot tables. *Mitigation:* migration review + integration tests on partitions.

## Deliverables
- **D1** Backend task list by wave/feature (above).
- **D2** Critical-path task callouts (F14–F19, F23) with mandatory durability/idempotency tests.
- **D3** Migration task list (per feature M-tasks) → consolidated in Phase 13.

---
> **Next phase:** Phase 11 — UX Tasks.
