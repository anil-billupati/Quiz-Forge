# ContestForge — AIDLC Phase 3: Use Cases

| | |
|---|---|
| **Phase** | 3 of 25 — Use Cases |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Source** | Phase 1 (Personas), Phase 2 (User Stories); product-spec FRs; domain-model BRs; api-contracts |
| **Depends on** | Phase 2 (User Stories) — approved |
| **Feeds** | Phase 4 (Data Flows), Phase 16 (Sequence Diagrams), Phase 20 (Testing) |

---

## Goal
Expand the user stories (Phase 2) into **detailed use cases** — actor-by-actor flows with
preconditions, a main (happy) flow, alternate flows, exception flows, and postconditions —
so that the *system behaviour* is unambiguous before any data-flow or sequence design. A use
case answers "what exactly happens, step by step, including when it goes wrong." These become
the backbone of Phase 4 data flows, Phase 16 sequence diagrams, and Phase 20 test scenarios.

## Assumptions
- One use case = one goal of one primary actor in one tenant context. Cross-tenant access is
  impossible and is treated as a global exception (§GX), not repeated per case.
- Every use case inherits the Phase 2 **Definition of Done** (tenant isolation, authz, audit,
  server-authoritative timing). These are stated once in §Global Pre/Exceptions.
- Flows describe behaviour, not implementation (no API/SQL/Redis specifics; those are later
  phases). Where the technical-spec already fixes a mechanism (e.g. durable write before ack),
  it is stated as a behavioural guarantee.
- "System" in a flow may be the REST API, WS gateway, or an engine worker; the responsible
  component is named only where it clarifies behaviour.
- Use cases cover v1 scope; deferred capabilities are out of scope here.

## Functional Requirements
*(The use-case catalogue — this phase's substance. Format per case: Actor · Level · Preconditions ·
Main flow · Alternate flows (Ax) · Exceptions (Ex) · Postconditions · Trace.)*

### Global pre-/exception conditions (apply to all)
- **GP1** Caller is authenticated with a valid, unexpired access token carrying role + tenant.
- **GP2** The target resource (if any) belongs to the caller's tenant.
- **GX1 — Unauthenticated/expired token:** abort → `401`.
- **GX2 — Wrong role:** abort → `403` (logged as security event).
- **GX3 — Cross-tenant target:** abort → `403`, logged; resource treated as non-existent (`404`
  where leakage of existence is itself sensitive).
- **GX4 — Suspended tenant:** all tenant-scoped use cases abort (users cannot operate).

---

### UC-1 — Create Organization
- **Actor:** Super Admin (P1) · **Level:** user goal
- **Preconditions:** Caller is `SUPER_ADMIN`.
- **Main flow:**
  1. Super Admin submits org name, unique `slug`, `portal_url`, optional `custom_domain`, and
     initial Org Admin details (email, name, temp password).
  2. System validates uniqueness of slug/portal_url/custom_domain.
  3. System creates `Organization` (`ACTIVE`) + `TenantSettings` (defaults) + initial `ORG_ADMIN`.
  4. System writes platform audit `org.create` and returns the org + admin.
- **Alternate:** *A1* `custom_domain` omitted → created without vanity domain.
- **Exceptions:** *E1* slug/portal_url/custom_domain already in use → `409`, nothing persisted.
  *E2* invalid slug pattern → `422`.
- **Postconditions:** Tenant exists and is ready; one Org Admin can log in.
- *Trace:* US-A1; FR-1; BR-19.

### UC-2 — Bulk-import Participants
- **Actor:** Org Admin (P2) · **Level:** user goal
- **Preconditions:** Caller is `ORG_ADMIN`; tenant `ACTIVE`.
- **Main flow:**
  1. Org Admin submits a list/CSV of `{email, first_name, last_name}` (≤5,000 rows).
  2. System validates each row (format) and checks email uniqueness within the tenant.
  3. For each valid, non-duplicate row: create a `PARTICIPANT` with a generated one-time password.
  4. System returns per-row results: `CREATED` (+ one-time password + user_id) or `SKIPPED` (+ reason).
- **Alternate:** *A1* rows exceed `max_participants_per_contest`/tenant capacity → rows up to the
  cap succeed; remaining rows `SKIPPED` (reason `capacity_exceeded`).
- **Exceptions:** *E1* empty/oversized payload → `422`. *E2* malformed CSV header → `422`.
- **Postconditions:** New participant accounts exist; Org Admin holds credentials to distribute
  out-of-band (no email sent).
- *Trace:* US-B5; FR-3a; product-spec §2.2.

### UC-3 — Author and Publish a Contest (Lifecycle)
- **Actor:** Org Admin (P2) · **Level:** summary (composite)
- **Preconditions:** Caller is `ORG_ADMIN`; tenant `ACTIVE`.
- **Main flow:**
  1. Create contest (Draft); choose `structure` (Normal | Grouped) and, if Grouped, rollup strategy.
  2. (Grouped) Add sequenced groups.
  3. Set Configuration Block(s): one (Normal) or one per group (Grouped) — see UC-4.
  4. Author questions + options (UC-5).
  5. Advance `DRAFT → PUBLISHED` (structure locks).
  6. Advance `PUBLISHED → REGISTRATION_OPEN` (configuration locks; participants may register).
  7. Advance `REGISTRATION_OPEN → REGISTRATION_CLOSED` (participant list finalised).
  8. Advance `REGISTRATION_CLOSED → SCHEDULED` (supply `scheduled_start_at`).
  9. System arms the contest for automatic go-live (see UC-11).
- **Alternate:** *A1* Org Admin starts a Grouped contest with a single group (allowed).
- **Exceptions:** *E1* skipping a stage or unmet precondition (e.g. publish with no questions, or
  ELIMINATION block missing rules) → `409`/`422`, no transition. *E2* editing metadata/structure
  after Draft → `409`. *E3* `SCHEDULED` without `scheduled_start_at` → `409`.
- **Postconditions:** Each transition recorded in `ContestLifecycleEvent`; contest is armed to go Live.
- *Trace:* US-C1..C5; FR-6–9; BR-5.

### UC-4 — Configure a Configuration Block (with validation)
- **Actor:** Org Admin (P2) · **Level:** user goal
- **Preconditions:** Contest is `DRAFT` or `PUBLISHED` (before `REGISTRATION_OPEN`).
- **Main flow:**
  1. Org Admin submits the block (Normal = contest scope; Grouped = with `group_id`): Mode,
     durations, reveal mode, ranking criterion, tie display, visibility, update frequency.
  2. System derives the scoring model from Mode (STANDARD/ELIMINATION → Fixed fields; SPEED →
     bands **or** decay).
  3. (ELIMINATION) System requires ≥1 rule, ≥1 checkpoint, and an `AND|OR` combine operator.
  4. System validates duration ranges (5–300 / 0–60) and scoring fields; persists the block.
- **Alternate:** *A1* Speed block supplies linear `decay` instead of `time_bands` (mutually exclusive).
  *A2* Wildcards enabled with `eligibility` (ALL | TOP_50_PERCENT).
- **Exceptions:** *E1* block edited after `REGISTRATION_OPEN` → `409`. *E2* mode/scoring mismatch,
  out-of-range duration, or elimination fields on a non-elimination block → `422`.
- **Postconditions:** A valid block governs the quiz (Normal) or its group (Grouped).
- *Trace:* US-D1..D4; FR-10,12,22,26,33,34; BR-3,4,6,13.

### UC-5 — Author a Question
- **Actor:** Org Admin (P2) · **Level:** user goal
- **Preconditions:** Contest is `DRAFT`.
- **Main flow:** Org Admin submits text, optional explanation, sequence, (Grouped) `group_id`, and
  ≥2 options with exactly one `is_correct`; system validates and persists.
- **Exceptions:** *E1* <2 options or ≠1 correct → `422`. *E2* duplicate sequence in scope → `409`.
  *E3* authoring after Draft → `409`.
- **Postconditions:** Question is part of the contest content.
- *Trace:* US-E1,E2; FR-10; BR-21.

### UC-6 — Participant Registers for a Contest
- **Actor:** Participant (P4) · **Level:** user goal
- **Preconditions:** Caller is `PARTICIPANT`; contest is `REGISTRATION_OPEN`.
- **Main flow:** Participant requests registration; system checks capacity and no existing
  registration; creates `Registration` (`REGISTERED`).
- **Alternate:** *A1* Participant withdraws before `REGISTRATION_CLOSED` → registration removed.
- **Exceptions:** *E1* contest not in `REGISTRATION_OPEN` → `409`. *E2* already registered → `409`.
  *E3* contest at `max_participants_per_contest` → `409` (atomic; no over-admission under race).
- **Postconditions:** Participant is on the finalised roster at registration close.
- *Trace:* US-F1,F2; FR-3a.

### UC-7 — Join Live Contest (and Reconnect)
- **Actor:** Participant (P4) · **Level:** user goal
- **Preconditions:** Contest is `LIVE`; caller has an `ACTIVE`/`REGISTERED` registration.
- **Main flow:**
  1. Participant requests a single-use live ticket (authenticated).
  2. System validates role, tenant, and registration; issues a short-lived ticket.
  3. Participant opens the WS connection presenting the ticket; system consumes it, resolves the
     principal, and upgrades.
  4. System subscribes the connection to the contest channel and pushes the current snapshot
     (current question without correctness, authoritative `submission_close_at`, my status/score).
- **Alternate (Reconnect):** *A1* After a drop, the participant repeats steps 1–4 (or calls
  `GET /live-state`); the system restores state and the open submission window within ≤3 s p99.
  An answer accepted before the drop remains accepted; a spent wildcard remains spent.
- **Exceptions:** *E1* ticket expired/used/invalid → rejected before upgrade. *E2* not registered
  or eliminated-without-spectator → `403`. *E3* contest not Live → `409`.
- **Postconditions:** Participant receives live events; reconnection is loss-free.
- *Trace:* US-G1, US-M1; FR-43; NFR-7.

### UC-8 — Reveal Question (Automatic & Moderator-Controlled)
- **Actor:** Execution Engine (automatic) **or** Moderator (P3) · **Level:** user goal
- **Preconditions:** Contest is `LIVE`; a next question exists in the active block.
- **Main flow (Automatic):**
  1. Execution Engine reaches the scheduled reveal time for the next question.
  2. System records the authoritative `QuestionWindow` (`revealed_at`, `submission_close_at`).
  3. System publishes `question.reveal` (no correctness) to the contest channel; the WS gateway
     fans out to all participants, p99 ≤ 200 ms.
  4. The submission window opens.
- **Alternate (Moderator-Controlled):** *A1* The interval timer is paused; the Moderator triggers
  the reveal; from step 2 the flow is identical.
- **Alternate (host disconnect — OI-1 resolved):** *A2* If the controlling host (Moderator)
  disconnects while in Moderator-Controlled mode, the contest **auto-pauses** before the next
  reveal: any already-open `QuestionWindow` continues to close on its server-side schedule (in-flight
  answers are unaffected, UC-9), but **no new question is revealed**. Participants see a "waiting for
  host" state. Reveal resumes when the **Moderator, a co-Moderator, or an Org Admin** reconnects and
  triggers the next reveal (the role-permission matrix already grants Org Admin reveal/override). The
  pause has no scoring effect; server timers for open windows are never paused.
- **Exceptions:** *E1* Non-moderator/non-Org-Admin attempts manual reveal → `403`. *E2* No next
  question → progression evaluates end-of-group/contest (UC-10/UC-12).
- **Postconditions:** Exactly one open `QuestionWindow`; all live participants see the question.
- *Trace:* US-G2,G3; FR-18,19; NFR-1.

### UC-9 — Submit Answer (critical path: durability + idempotency)
- **Actor:** Participant (P4) · **Level:** user goal · **Criticality:** highest
- **Preconditions:** Contest is `LIVE`; a `QuestionWindow` is open; participant not eliminated.
- **Main flow:**
  1. Participant sends `answer.submit` (question, selected option, `attempt_no`) over WS.
  2. System validates: contest Live, window open per **server-side** `submission_close_at`,
     participant not eliminated.
  3. System **durably persists** the `AnswerSubmission` with the server-accept timestamp and a
     deterministic `idempotency_hash` of `(contest, question, participant, attempt_no)`. This
     durable write is the acceptance boundary.
  4. System returns `answer.ack {accepted:true}`.
  5. System emits a scoring command (carrying the persisted submission id) for asynchronous scoring
     (UC-10). The participant's score updates via leaderboard push, not in the ack.
- **Alternate:** *A1* Retried/duplicate submit (same idempotency inputs) → resolves to the single
  stored answer; one ack, no double record (BR-8). *A2* Second-Chance retry → `attempt_no = 2`
  (only after a WRONG first attempt); its response time drives that question's Speed/tie-break.
- **Exceptions:** *E1* `server_accepted_at > submission_close_at` → `answer.ack {accepted:false,
  reason: window_closed}` (not an error). *E2* Participant eliminated → rejected. *E3* Durable
  write fails → non-accepted ack; client may retry; idempotency prevents a later double-record.
- **Postconditions:** Accepted answer is durable and survives any single component failure; it will
  be scored exactly once with the first-accept timestamp.
- *Trace:* US-H1,H2,H3, US-I2; FR-17,20,38,39,40,41; BR-7,8,9; NFR-5.

### UC-10 — Score Answer & Update Leaderboard
- **Actor:** Scoring Engine → Leaderboard Engine (system) · **Level:** subfunction
- **Preconditions:** An accepted `AnswerSubmission` exists with a scoring command.
- **Main flow:**
  1. Scoring Engine consumes the command **idempotently** (dedupe on submission id); re-establishes
     tenant context.
  2. It applies the block's scoring model: Fixed (correct = `correct_points`, wrong/timeout = 0,
     **no negative marking**, score floored at 0) or Time-Based (band upper-inclusive, first match
     wins; or linear decay). Applies Second-Chance rate / Skip credit as applicable.
  3. It writes the `Score` row (unique per submission → at-most-once) and tie-break data
     (total response time using attempt-2 time on Second Chance; wrong count; last-correct-at).
  4. Leaderboard Engine updates the relevant view ZSET(s) and pushes deltas per `update_frequency`
     and visibility, p99 ≤ 500 ms (≤5,000 users).
- **Alternate:** *A1* `update_frequency = PER_QUESTION/PER_GROUP` → recompute at window close /
  group end rather than per answer. *A2* `MASKED` visibility → full board computed server-side; only
  the participant's own rank is emitted.
- **Exceptions:** *E1* Duplicate scoring command → deduped, no second `Score`. *E2* Transient failure
  → retried with backoff; poison message dead-lettered without blocking the contest.
- **Postconditions:** Score is at-most-once; leaderboard reflects authoritative scores.
- *Trace:* US-H2, US-J1,J2,J3; FR-28,30,31,32,39,40; BR-8,14,14b,14c; NFR-3.

### UC-11 — Evaluate Elimination Checkpoint
- **Actor:** Elimination Engine (system), triggered by Execution Engine · **Level:** user goal
- **Preconditions:** Active block Mode = ELIMINATION; a configured checkpoint is reached.
- **Main flow:**
  1. Execution Engine signals the checkpoint (After Question | After Group | Custom Milestone).
  2. Elimination Engine evaluates the rule set, combined by the block's single `AND|OR` operator,
     against authoritative scores.
  3. It computes the eliminated set. For Bottom-X% landing inside a tie, **all tied participants in
     the cut are eliminated** (tie never split).
  4. It persists `EliminationEvent`s, sets affected `Registration.status = ELIMINATED`, and **locks
     the survivor list**.
  5. It emits elimination notifications (final rank/score; spectator flag if granted).
  6. Leaderboard Engine refreshes the Survivor view; Execution Engine pauses to show the group
     leaderboard and announce eliminations before the next block applies.
- **Alternate:** *A1* `survivor_score_reset = true` → survivors' scores reset at next group start;
  otherwise carried forward. *A2* Custom Milestone fires at an admin-defined timestamp/event.
- **Exceptions:** *E1* Eliminated participant attempts to submit → rejected (BR-16). *E2* Re-run of
  the same checkpoint (recovery) → idempotent; no participant eliminated twice.
- **Postconditions:** Survivor list is authoritative and locked for the checkpoint; eliminated
  participants are notified and (optionally) spectators.
- *Trace:* US-K1,K2; FR-33–37; BR-16,25; FR-34 (tie rule).

### UC-12 — Automatic Go-Live
- **Actor:** Execution Engine (system) · **Level:** user goal
- **Preconditions:** Contest `lifecycle_status = SCHEDULED` with a `scheduled_start_at`.
- **Main flow:**
  1. The platform tracks armed contests; when `scheduled_start_at` is reached, the Execution Engine
     transitions the contest to `LIVE` and initialises `ContestExecutionState`.
  2. It records the lifecycle event and begins the per-question loop (UC-8).
- **Alternate:** *A1* Moderator-Controlled reveal → contest is Live but waits for the first manual reveal.
- **Exceptions:** *E1* Engine restart near start time → transition is **idempotent**; the contest
  starts exactly once (optimistic-lock/version guard). *E2* Start time already passed at arming →
  go Live immediately.
- **Postconditions:** Contest is Live exactly once at/after its scheduled time, with no human action.
- *Trace:* US-C4; FR-9 (auto-start); BR-5.

### UC-13 — Moderator Monitors & Overrides a Live Contest
- **Actor:** Moderator (P3) · **Level:** user goal
- **Preconditions:** Contest is `LIVE`; caller is `MODERATOR` (or `ORG_ADMIN`).
- **Main flow:** Moderator views live participant count, current leaderboard, and elimination events;
  optionally issues a reveal (UC-8) or an advance override (`scope = QUESTION | GROUP`), accepted `202`.
- **Alternate:** *A1* Advance GROUP mid-question → the closing question's already-accepted answers
  still score (UC-9/UC-10) before the group transition.
- **Exceptions:** *E1* Non-moderator → `403`. *E2* Override when not Live → `409`.
- **Postconditions:** Progression reflects the override; actions are audit-logged.
- *Trace:* US-G4,G5; FR-21.

### UC-14 — Recover Contest After Crash / Cache Loss
- **Actor:** System (engine workers) / SRE (P6) · **Level:** user goal
- **Preconditions:** An API/worker crash or a Redis loss has occurred during a Live contest.
- **Main flow (crash):**
  1. On restart, workers reload `ContestExecutionState` and open `QuestionWindow`s from PostgreSQL.
  2. Persisted-but-unscored answers are re-driven through the idempotent Scoring Engine; dedupe
     prevents double-scoring.
  3. The contest resumes from the durable phase within ≤30 s; score totals match pre-failure exactly.
- **Alternate (cache loss):** *A1* Leaderboard ZSETs / `ParticipantScoreSummary` are rebuilt from
  authoritative `Score` rows with identical ranks/scores; no score/rank changes.
- **Exceptions:** *E1* A checkpoint that had partially evaluated re-runs idempotently (UC-11/E2).
- **Postconditions:** Contest integrity preserved: no lost answers, no double-scoring, ranks intact.
- *Trace:* US-M2,M3,M4; FR-42,44; NFR-6,9; BR-18,23.

### UC-15 — View / Export Results & Audit
- **Actor:** Org Admin (P2) (Moderator read-only) · **Level:** user goal
- **Preconditions:** Contest is `COMPLETED` or `ARCHIVED`.
- **Main flow:** Org Admin retrieves final leaderboard + per-participant breakdown; exports CSV/JSON;
  reviews wildcard-activation audit and elimination events; queries the tenant audit log.
- **Exceptions:** *E1* Results requested before Completed → `409`. *E2* Archived contest is read-only
  (no mutation) (BR-27).
- **Postconditions:** Reports are produced from the immutable `ContestResultSnapshot` (written on Archive).
- *Trace:* US-L1,L3; FR-27,45; BR-27.

## Non-functional Requirements
*(Quality requirements for the use-case artifact.)*
- Each use case names a **single primary actor and goal**, and lists **preconditions,
  postconditions, and at least one exception flow** (the failure path is mandatory, not optional).
- Each use case traces to ≥1 user story and ≥1 FR/BR (see §D2).
- Use cases are **mechanism-light**: behaviour is fixed; the *how* is deferred to Phases 4/13/16,
  except where the spec already mandates a behavioural guarantee (durable-write-before-ack).
- The critical-path case (UC-9) and recovery (UC-14) are specified to a depth sufficient to drive
  durability/idempotency tests directly.

## Edge Cases
- **Concurrent registration at capacity** (UC-6/E3) — atomic check; exactly one of two racers wins.
- **Submit at the exact close instant** (UC-9/E1) — `≤ close` accepted, `> close` rejected; server clock only.
- **Second Chance after a correct first attempt** (UC-9/A2) — rejected; only WRONG enables attempt 2.
- **Wildcard activation then disconnect before ack** (UC-7/A1) — wildcard remains spent on reconnect.
- **Group advance with answers in flight** (UC-13/A1) — in-flight accepted answers still score for
  the closing question.
- **Auto-go-live during worker restart** (UC-12/E1) — starts exactly once.
- **Bottom-X% cut inside a tie** (UC-11/step 3) — all tied participants eliminated; never split.
- **Checkpoint partially evaluated then crash** (UC-11/E2, UC-14/E1) — re-run is idempotent.
- **Masked leaderboard** (UC-10/A2) — only own rank leaves the server.

## Future Considerations
- **Moderator-disconnect reveal fallback** (OI-1) — RESOLVED as UC-8/A2 (auto-pause + host
  reconnect). A small new user story for "resume after host disconnect" should be back-filled into
  Phase 2 Epic G when Phase 2 is next revised.
- **Spectator scope** — exactly which later groups/views an eliminated participant may observe.
- **Custom-milestone trigger types** beyond timestamp (event-based) — UC-11/A2 may expand.
- **Self-registration** use case if open onboarding is later in scope (UC-6 variant).
- **Result streaming/large-export** use case if exports exceed synchronous limits.

## Risks
- **Critical-path under-specification:** if UC-9/UC-10/UC-14 are vague, durability/at-most-once can't
  be tested. *Mitigation:* these three are specified to test-ready depth here.
- **Exception-flow omission:** happy-path-only use cases hide the riskiest behaviour. *Mitigation:*
  every case carries explicit exceptions; §Edge Cases consolidates the dangerous ones.
- **Open issue drift (OI-1): RESOLVED** — moderator-disconnect now has an explicit auto-pause +
  host-reconnect fallback (UC-8/A2). *Residual:* "host present/absent" must be observable so the
  pause and the "waiting for host" state can be driven — a presence signal, not necessarily a new
  lifecycle/phase value; to be settled in Phase 4 (Data Flows) / Phase 13.
- **Mechanism leakage:** describing *how* (Redis/SQL) here would prematurely constrain Phases 4/13.
  *Mitigation:* behaviour-only, with named guarantees where the spec mandates them.

## Deliverables

### D1 — Use-case catalogue
15 use cases (UC-1..UC-15) spanning all 13 Phase-2 epics and personas P1–P6, each with main /
alternate / exception flows and pre/postconditions (see §Functional Requirements).

### D2 — Use-case → story / FR traceability
| UC | Title | Stories | FR/BR |
|---|---|---|---|
| 1 | Create Organization | A1 | FR-1; BR-19 |
| 2 | Bulk-import Participants | B5 | FR-3a |
| 3 | Author & Publish Contest | C1–C5 | FR-6–9; BR-5 |
| 4 | Configure Block | D1–D4 | FR-10,12,22,26,33,34; BR-3,4,6,13 |
| 5 | Author Question | E1,E2 | FR-10; BR-21 |
| 6 | Register | F1,F2 | FR-3a |
| 7 | Join Live & Reconnect | G1,M1 | FR-43; NFR-7 |
| 8 | Reveal Question | G2,G3 | FR-18,19; NFR-1 |
| 9 | Submit Answer | H1,H2,H3,I2 | FR-17,20,38–41; BR-7,8,9; NFR-5 |
| 10 | Score & Leaderboard | H2,J1–J3 | FR-28,30,31,32,39,40; BR-8,14,14b,14c; NFR-3 |
| 11 | Elimination Checkpoint | K1,K2 | FR-33–37; BR-16,25 |
| 12 | Automatic Go-Live | C4 | FR-9; BR-5 |
| 13 | Moderator Control | G4,G5 | FR-21 |
| 14 | Recovery | M2,M3,M4 | FR-42,44; NFR-6,9; BR-18,23 |
| 15 | Results & Audit | L1,L3 | FR-27,45; BR-27 |

### D3 — Resolved decision (OI-1)
- **OI-1 — Moderator disconnect in Moderator-Controlled mode → RESOLVED: option (a).** On host
  disconnect the contest **auto-pauses** before the next reveal; the **Moderator, a co-Moderator, or
  an Org Admin** can reconnect and resume reveal. Open submission windows continue to close on their
  server-side schedule (no scoring impact); participants see "waiting for host." See UC-8/A2.
  *Residual for Phase 4/13:* a "host present" presence signal so the pause/resume and the
  participant-facing waiting state can be driven (likely a presence flag, not a new lifecycle stage).

### D4 — Open questions carried forward
1. Spectator view scope for eliminated participants (Phase 4/6).
2. Event-based custom milestones (Phase 4).
3. Synchronous vs async large exports (Phase 4/14).

---

> **Next phase (await approval):** Phase 4 — Data Flows. Do not generate until approved.
> **Note:** OI-1 is now resolved (auto-pause + host reconnect, UC-8/A2); Phase 4 can finalise the
> execution data flow and will define the "host present" presence signal.
