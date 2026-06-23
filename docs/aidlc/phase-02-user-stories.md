# ContestForge — AIDLC Phase 2: User Stories

| | |
|---|---|
| **Phase** | 2 of 25 — User Stories |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Source** | Phase 1 personas; product-spec FRs; domain-model BRs; api-contracts |
| **Depends on** | Phase 1 (Personas) — approved |
| **Feeds** | Phase 3 (Use Cases), Phase 8 (Feature Decomposition), Phase 20 (Testing) |

---

## Goal
Translate the approved personas (P1–P6) into **testable user stories** that express *who*
wants *what* and *why*, each with **acceptance criteria** and **traceability** to the
functional requirements (FR-#) and business rules (BR-#). These stories are the contract
between product intent and implementation: every later phase (use cases, tasks, tests) must
map back to a story, and every story must map back to an FR or an explicit persona need.
Stories describe behaviour, not design — no API shapes or UI here (those are Phases 12–15).

## Assumptions
- Personas and the four-role model are fixed (Phase 1). Each story names a persona and
  implicitly its role + tenant scope.
- INVEST is the quality bar: stories are Independent, Negotiable, Valuable, Estimable, Small,
  Testable. Where a capability is large, it is split into multiple stories under one epic.
- Acceptance criteria are written in a Given/When/Then style and are the seed for Phase 20
  test cases; they assert observable behaviour, including the **negative** path.
- "Done" for a story includes tenant-isolation enforcement and audit logging where the BRs
  require it — not repeated in every story but treated as a global Definition of Done (§DoD).
- Stories cover **v1 scope only**; deferred items (self-signup, email transport, billing) are
  captured as Future Considerations, not stories.

## Functional Requirements
*(The story catalogue — the functional substance of this phase. Grouped by epic. Each story:
ID · statement · key acceptance criteria · traceability.)*

### Epic A — Platform & Tenancy (P1 Super Admin)
**US-A1 — Create organization**
> As a Super Admin, I want to provision a new organization with its initial Org Admin, so a
> new customer can start building contests in isolation.
- **AC1** Given a unique `slug`/`portal_url`, when I create the org with admin details, then
  the org is `ACTIVE`, an `ORG_ADMIN` user is created, and both are returned.
- **AC2** Given a `slug`/`portal_url`/`custom_domain` already in use, then creation is
  rejected `409` and nothing is persisted.
- **AC3** The action is recorded in the platform audit log (`org.create`).
- *Trace:* FR-1, BR-19; api `POST /organizations`.

**US-A2 — Suspend / reactivate organization**
> As a Super Admin, I want to suspend or reactivate an org, so I can enforce
> non-payment/policy actions without deleting data.
- **AC1** When suspended, the org's users cannot authenticate or run contests; data is retained.
- **AC2** When reactivated, normal access resumes.
- **AC3** Both transitions are audit-logged. *Trace:* FR-2; api `PATCH /organizations/{id}/status`.

**US-A3 — Set tenant resource limits**
> As a Super Admin, I want to configure per-tenant limits (max concurrent live contests, max
> participants/contest, max questions/contest), so one tenant cannot exhaust platform capacity.
- **AC1** Limits persist in `TenantSettings` and are enforced at the API (exceeding → `422`/`409`).
- *Trace:* FR-3a; api `PATCH /organizations/{id}/settings`.

**US-A4 — View platform-wide usage**
> As a Super Admin, I want per-tenant usage aggregates, so I can plan capacity and seed future
> billing.
- **AC1** Usage record returns contests created, live peak, participant-minutes, submissions, etc.
- *Trace:* FR-3b; api `GET /organizations/{id}/usage`.

**US-A5 — Boundary: no tenant entry**
> As a Super Admin, I must not be able to view inside or operate a tenant's contests, so tenant
> isolation is absolute even for platform staff.
- **AC1** Any Super Admin call to a tenant-scoped contest resource is denied `403` and logged.
- *Trace:* product-spec §2.5, NFR-8.

### Epic B — Identity & Onboarding (P2 Org Admin, P4 Participant)
**US-B1 — Authenticate**
> As any tenant user, I want to log in with email + password (+ tenant slug) and receive
> access/refresh tokens, so I can use the platform securely.
- **AC1** Valid credentials → token pair carrying role + tenant scope; **AC2** invalid → `401`;
  **AC3** login is rate-limited (5/min/IP). *Trace:* FR-4; api `POST /auth/login`.

**US-B2 — Rotate / revoke session**
> As a user, I want refresh-token rotation and logout, so a stolen token has limited value.
- **AC1** Each refresh revokes the used token and issues a new one in the same family; **AC2**
  reuse of a revoked token revokes the whole family. *Trace:* FR-4, BR-26.

**US-B3 — Change password**
> As a user provisioned with a temporary password, I want to change it, so my account is mine.
- **AC1** Correct current password → updated; wrong → `401`. *Trace:* api `POST /auth/change-password`.

**US-B4 — Create tenant users**
> As an Org Admin, I want to create Org Admins, Moderators, and Participants, so my team and
> competitors can access contests.
- **AC1** Role ∈ {ORG_ADMIN, MODERATOR, PARTICIPANT}; **AC2** `SUPER_ADMIN` rejected; **AC3**
  duplicate email in tenant → `409`. *Trace:* FR-5; api `POST /users`.

**US-B5 — Bulk-import participants (CSV)**
> As an Org Admin, I want to import thousands of participants from a CSV, so I can populate a
> large contest without one-by-one entry.
- **AC1** Given a list/CSV of `{email,first_name,last_name}`, valid rows become `PARTICIPANT`
  accounts with generated one-time passwords returned for distribution.
- **AC2** Duplicate/invalid rows are **skipped with a per-row reason**; valid rows still succeed
  (partial success), and counts are reported.
- **AC3** Import is bounded (≤5,000 rows/request) and respects the tenant participant limit.
- *Trace:* FR-3a, product-spec §2.2; api `POST /users/bulk`.

### Epic C — Contest Authoring & Lifecycle (P2 Org Admin)
**US-C1 — Create contest (Draft)**
> As an Org Admin, I want to create a Normal or Grouped contest in Draft, so I can begin
> configuring it.
- **AC1** `structure` chosen at creation; contest starts `DRAFT`; Grouped allows a rollup
  strategy. *Trace:* FR-6; api `POST /contests`.

**US-C2 — Manage groups (Grouped, Draft)**
> As an Org Admin, I want to add/edit/remove sequenced groups, so a multi-round contest is
> structured.
- **AC1** Groups have unique sequence within the contest; **AC2** editable only in Draft.
- *Trace:* FR-8; api `/contests/{id}/groups`.

**US-C3 — Advance lifecycle**
> As an Org Admin, I want to move a contest through the fixed lifecycle, so it progresses from
> setup to live to archive without skipping stages.
- **AC1** Only the next legal stage is accepted; skipping/unmet preconditions → `409`.
- **AC2** `SCHEDULED` requires `scheduled_start_at`.
- **AC3** Structure locks at `PUBLISHED`; configuration locks at `REGISTRATION_OPEN`.
- **AC4** Each transition is recorded in `ContestLifecycleEvent`.
- *Trace:* FR-7, FR-9, BR-5; api `POST /contests/{id}/lifecycle`.

**US-C4 — Automatic go-live**
> As an Org Admin, I want a Scheduled contest to go Live automatically at its start time, so I
> don't have to click "start" at the exact moment.
- **AC1** Given `lifecycle_status = SCHEDULED` and `scheduled_start_at` reached, then the
  contest transitions to `LIVE` with no human action.
- **AC2** The transition is idempotent — a restart near the start time cannot double-start.
- *Trace:* FR-9 (auto-start), BR-5; technical-spec Execution Engine.

**US-C5 — Edit/delete only while Draft**
> As an Org Admin, I want edits/deletes blocked once a contest leaves Draft, so a published
> contest can't be silently changed.
- **AC1** Metadata edit or delete after Draft → `409`. *Trace:* FR-7; api `PATCH/DELETE /contests/{id}`.

### Epic D — Configuration Blocks (P2 Org Admin)
**US-D1 — Configure a block**
> As an Org Admin, I want to set a Configuration Block (Normal = one; Grouped = one per group),
> so the contest behaves per my chosen mode and timing.
- **AC1** Block captures Mode, durations (5–300s question; 0–60s interval/explanation/leaderboard),
  reveal mode, ranking criterion, tie display, visibility, update frequency.
- **AC2** Editable until `REGISTRATION_OPEN`, then locked (`409`).
- **AC3** Out-of-range durations → `422`. *Trace:* FR-10, BR-6; api `PUT /contests/{id}/configuration`.

**US-D2 — Mode derives scoring**
> As an Org Admin, I want scoring to follow the chosen Mode automatically, so I can't create an
> inconsistent mode/scoring pair.
- **AC1** STANDARD/ELIMINATION → Fixed fields (`correct_points`, `second_chance_rate`; wrong = 0,
  **no negative marking**); SPEED → `time_bands` **or** `decay` (mutually exclusive).
- **AC2** Supplying Speed fields on a Fixed block (or vice-versa) → `422`.
- *Trace:* FR-12, BR-3; api ConfigurationBlock schema.

**US-D3 — Configure elimination (Elimination mode)**
> As an Org Admin, I want to define elimination rules + checkpoints + a combine operator on an
> Elimination block, so knockout behaviour is precise.
- **AC1** ELIMINATION block requires ≥1 rule, ≥1 checkpoint, and a non-null `AND|OR` operator.
- **AC2** Supplying these on a non-Elimination block, or omitting on Elimination → `422`.
- *Trace:* FR-10, FR-33, FR-34, BR-4.

**US-D4 — Enable wildcards**
> As an Org Admin, I want to enable any of the three wildcards with an eligibility setting, so
> participants get power-ups under my chosen policy.
- **AC1** Each enabled wildcard has `eligibility ∈ {ALL, TOP_50_PERCENT}`; no usage_limit/cooldown/
  carryover fields exist (each usable once per contest by rule).
- *Trace:* FR-22, FR-26, BR-13.

### Epic E — Questions & Options (P2 Org Admin)
**US-E1 — Author a question**
> As an Org Admin, I want to add a multiple-choice question with options and exactly one correct
> answer (and optional explanation), so the contest has content.
- **AC1** ≥2 options, exactly one `is_correct`; otherwise `422`.
- **AC2** Unique sequence within contest (Normal) or group (Grouped).
- **AC3** Draft-only. *Trace:* FR-10, BR-21; api `/contests/{id}/questions`.

**US-E2 — Edit/replace options**
> As an Org Admin, I want to edit question text/explanation/sequence and replace the option set,
> so I can fix content before publishing.
- **AC1** Draft-only; replacing options re-validates the exactly-one-correct rule.
- *Trace:* FR-10; api `PUT .../options`.

### Epic F — Registration (P4 Participant, P2 Org Admin)
**US-F1 — Self-register for a contest**
> As a Participant, I want to register for a contest while registration is open, so I can compete.
- **AC1** Allowed only in `REGISTRATION_OPEN`; otherwise `409`.
- **AC2** Duplicate registration → `409`; **AC3** respects `max_participants_per_contest`.
- *Trace:* FR-6 flow, FR-3a; api `POST /contests/{id}/registrations`.

**US-F2 — Withdraw / view my registration**
> As a Participant, I want to see and withdraw my registration before it closes, so I control my
> participation.
- **AC1** Self-withdraw allowed before `REGISTRATION_CLOSED`; **AC2** `GET .../registrations/me`
  returns my status/score. *Trace:* api `/contests/{id}/registrations/me`, `DELETE`.

**US-F3 — Org Admin views registrations**
> As an Org Admin/Moderator, I want to list registrations by status, so I can monitor sign-ups.
- *Trace:* api `GET /contests/{id}/registrations`.

### Epic G — Live Execution (P3 Moderator, P4 Participant)
**US-G1 — Join the live contest**
> As a registered Participant, I want to securely connect to the live channel, so I receive
> questions in real time.
- **AC1** I obtain a short-lived single-use ticket (auth'd) and upgrade the WS with it; expired/
  used tickets are rejected before upgrade. **AC2** Unregistered/ineligible → `403`/`409`.
- *Trace:* api `POST /contests/{id}/live-ticket`, WS handshake.

**US-G2 — Receive a question at reveal**
> As a Participant, I want each question pushed the moment it's revealed (without the correct
> answer), so I can answer within the window.
- **AC1** `question.reveal` arrives ≤200 ms p99 from scheduled reveal; payload omits correctness
  and carries the authoritative `submission_close_at`. *Trace:* FR-18, NFR-1.

**US-G3 — Moderator-controlled reveal**
> As a Moderator, I want to manually reveal each question (Moderator-Controlled mode), so I can
> pace a live show.
- **AC1** Reveal triggers fan-out; interval timer pauses between questions; non-moderator → `403`.
- *Trace:* FR-19; api `POST /control/reveal`, WS `moderator.reveal`.

**US-G4 — Progression override**
> As a Moderator, I want to advance question/group manually, so I can recover from stalls or
> end a round early.
- **AC1** `scope ∈ {QUESTION, GROUP}` accepted `202`; between groups the engine shows the group
  leaderboard and announces eliminations. *Trace:* FR-21; api `POST /control/advance`.

**US-G5 — Monitor live**
> As a Moderator, I want live participant count, current leaderboard, and elimination events, so
> I can run the event with situational awareness.
- *Trace:* product-spec §2.3.

### Epic H — Answer Submission & Durability (P4 Participant)
**US-H1 — Submit an answer**
> As a Participant, I want to submit my answer and get a clear accept/reject, so I know it counted.
- **AC1** A durably-persisted submission returns `answer.ack {accepted:true}` with the server time.
- **AC2** Submissions after the server-side `submission_close_at` are rejected
  (`reason: window_closed`), regardless of client clock. **AC3** Eliminated participants are
  rejected. *Trace:* FR-17, FR-20, FR-41, BR-9.

**US-H2 — At-most-once / idempotent**
> As a Participant, I want retries not to double-count or lose my answer, so transient faults
> don't change my score.
- **AC1** Identical retried submissions resolve to one stored answer (idempotency hash) and one
  score. **AC2** The scoring timestamp is the first server-accept time even after retries.
- *Trace:* FR-39, FR-40, BR-7, BR-8.

**US-H3 — Durability under failure**
> As a Participant, I want an accepted answer never lost, so a component crash can't erase my work.
- **AC1** Across 10,000 submissions with 1% induced persistence failures, zero accepted answers
  are lost. *Trace:* FR-38, NFR-5.

### Epic I — Wildcards (P4 Participant)
**US-I1 — Fifty-Fifty**
> As an eligible Participant, I want to remove two wrong options before answering, so I improve
> my odds.
- **AC1** Two incorrect options removed, correct always preserved; **AC2** rejected after an
  answer is selected; **AC3** usable once in the contest. *Trace:* FR-23, BR-11, BR-13.

**US-I2 — Second Chance**
> As an eligible Participant, I want one retry after a wrong answer at reduced points, so a slip
> isn't fatal.
- **AC1** One extra attempt (`attempt_no=2`) only after a WRONG first attempt; scored at
  `second_chance_rate`. **AC2** The second attempt's response time drives that question's Speed
  score and tie-break contribution. *Trace:* FR-24, BR-10, FR-15.

**US-I3 — Skip**
> As an eligible Participant, I want to skip a question for full credit, so I can avoid a question
> I dislike.
- **AC1** Question not shown/attempted; Fixed → full correct value; Speed → floor score (not 0).
- *Trace:* FR-25, BR-12.

**US-I4 — Wildcard eligibility & once-per-contest**
> As a Participant, I want clear feedback when a wildcard is unavailable, so I'm not confused.
- **AC1** `TOP_50_PERCENT` is evaluated against the last committed leaderboard at the start of the
  current question; ineligible/already-used activations are rejected with a reason.
- **AC2** Multiple different wildcards may be used on the same question.
- **AC3** Every activation is audit-logged. *Trace:* FR-26, FR-27, BR-13.

### Epic J — Leaderboards (P4 Participant, P3 Moderator)
**US-J1 — See live ranking**
> As a Participant, I want near-real-time rankings per the configured visibility, so I know where
> I stand.
- **AC1** Updates pushed per `update_frequency`; ≤500 ms p99 (≤5,000 users). **AC2** Visibility
  honoured: Always / Post-question / Hidden / Masked (own rank only). *Trace:* FR-28, FR-31,
  FR-32, NFR-3.

**US-J2 — Ranking criterion & ties**
> As an Org Admin, I want to pick the ranking criterion, so the board reflects my contest's intent.
- **AC1** SCORE_ONLY / SCORE_TIME / ACCURACY each apply their specified tie-break sequence;
  ACCURACY uses correct ÷ questions-revealed-so-far. **AC2** Tie display mode honoured (shared
  rank default). *Trace:* FR-30, FR-32, BR-14, BR-14b.

**US-J3 — Group & Survivor views**
> As a Participant, I want group and survivor leaderboards where they apply, so multi-round and
> elimination standings are clear.
- **AC1** Group view resets at group start (Grouped); Survivor view active from first checkpoint
  (Elimination). *Trace:* FR-29.

### Epic K — Elimination (P4 Participant, P3 Moderator)
**US-K1 — Be eliminated by rule**
> As a Participant in an Elimination round, I want fair, deterministic elimination at checkpoints,
> so the cut is transparent.
- **AC1** At a checkpoint the rule set (combined AND/OR) is evaluated against authoritative scores;
  the eliminated set is computed, persisted, and the survivor list locked.
- **AC2** Bottom-X% at a tie boundary eliminates **all tied participants in the cut** (never splits).
- **AC3** Once eliminated, no further submissions are accepted. *Trace:* FR-33–36, BR-16, FR-34.

**US-K2 — Elimination notification + spectator**
> As an eliminated Participant, I want a notification with my final rank/score and optional
> view-only access, so I have closure and can keep watching.
- **AC1** Notification carries final rank/score; **AC2** if granted, spectator access is view-only
  (no submit). **AC3** Survivors carry scores forward unless `survivor_score_reset` is set.
- *Trace:* FR-37, BR-25.

### Epic L — Results, Notifications & Audit (P2 Org Admin, P4 Participant)
**US-L1 — View & export results**
> As an Org Admin, I want final results, per-participant breakdowns, and CSV/JSON export, so I can
> report outcomes.
- **AC1** Available in Completed/Archived; includes wildcard audit and elimination events.
- *Trace:* FR-27, api `/results`, `/results/export`, `/wildcard-audit`, `/eliminations`.

**US-L2 — Receive in-app notifications**
> As a Participant, I want in-app notifications (answer ack, progress, elimination, spectator), so
> I stay informed without email.
- **AC1** `GET /me/notifications` lists mine; ack marks delivered. *Trace:* FR-41, FR-37.

**US-L3 — Query audit log**
> As an Org Admin (tenant) or Super Admin (platform), I want to query the audit log, so I can
> investigate actions.
- **AC1** Org Admin sees only their tenant; Super Admin sees platform-wide. *Trace:* tech-spec §6.

### Epic M — Recovery & Operations (P4 Participant, P6 SRE)
**US-M1 — Reconnect without loss**
> As a Participant who dropped connection, I want my state and open window restored quickly, so a
> network blip doesn't cost me the round.
- **AC1** On reconnect, `GET /live-state` (or WS resnapshot) restores current question (no
  correctness), authoritative `submission_close_at`, and my status/score within ≤3 s p99.
- *Trace:* FR-43, NFR-7.

**US-M2 — Contest recovery after crash**
> As an SRE, I want a contest to resume after an API/worker crash with no lost answers and no
> double-scoring, so integrity holds under failure.
- **AC1** Within 30 s of a simulated crash, the contest resumes from durable state; score totals
  match pre-failure exactly. *Trace:* FR-42, NFR-6, NFR-9, BR-23.

**US-M3 — Cache loss safe**
> As an SRE, I want leaderboards rebuildable from authoritative data, so a Redis loss never changes
> scores or ranks.
- **AC1** After flushing cache, ZSETs/summaries rebuild from Score rows with identical ranks/scores.
- *Trace:* FR-44, BR-18.

**US-M4 — Observe contest health**
> As an SRE, I want metrics/traces/alerts on reveal latency, scoring lag, queue depth, WS count,
> and recovery duration, so I can act before NFRs breach.
- **AC1** Dashboards expose the NFR-aligned metrics; alerts fire on threshold breach. *Trace:*
  tech-spec §6.

## Non-functional Requirements
*(Story-quality requirements for this phase's artifact.)*
- Every story is **independently testable** and maps to ≥1 FR/BR or an explicit persona need;
  orphan stories (no trace) are not allowed.
- Acceptance criteria include the **negative/failure path**, not only the happy path (security
  and durability stories especially).
- Stories are **role/tenant-aware**: the Definition of Done (§DoD) applies tenant isolation,
  authz, and audit globally so individual ACs stay focused.
- Stories are **stable references**: IDs (US-x#) are permanent and cited by later phases.

## Edge Cases
- **Registration race at capacity:** two participants register simultaneously at the limit — one
  succeeds, one gets `409`; no over-admission. (US-F1)
- **Submit exactly at `submission_close_at`:** boundary is server-authoritative; `≤ close` accepted,
  `> close` rejected — must be deterministic. (US-H1)
- **Second Chance after a *correct* first attempt:** must be rejected (only WRONG enables it). (US-I2)
- **Wildcard used, then participant disconnects before ack:** on reconnect the wildcard is still
  spent (idempotent activation). (US-I4, US-M1)
- **Auto-go-live while the scheduler/worker is mid-restart:** must start exactly once. (US-C4)
- **Bulk import partially exceeds participant cap:** rows up to the cap succeed, the rest skipped
  with a clear reason. (US-B5)
- **Moderator advances group while answers are still in flight:** in-flight accepted answers must
  still score for the closing question. (US-G4, US-H2)
- **Masked leaderboard:** participant sees only their own rank; full board never leaves the server.
  (US-J1)

## Future Considerations
- **Self-registration / join-code** stories (new participant onboarding flow) — deferred.
- **Email/SMS notification** stories once transport is integrated (today in-app only).
- **Billing/subscription** stories built on `TenantUsageRecord`.
- **Question bank / reusable content** stories if authoring is decoupled from a single contest.
- **Spectator-only public viewer** stories if contests become publicly watchable.
- **Bulk participant *invite* (vs import)** once email delivery exists.

## Risks
- **Story/FR drift:** if a story is added without an FR, scope creeps silently. *Mitigation:* the
  traceability matrix (§Deliverables D2) is mandatory and reviewed.
- **Over-decomposition:** splitting durability/recovery into too many micro-stories obscures the
  end-to-end guarantee. *Mitigation:* Epic M stories are end-to-end and test the guarantee, not
  the mechanism.
- **Happy-path bias:** writers favour the success path; the riskiest behaviour (late submit,
  idempotency, tie boundaries) lives in the negative path. *Mitigation:* negative ACs required.
- **Hidden cross-cutting work:** tenant isolation/audit appear in almost every story; if not
  centralised they get under-estimated. *Mitigation:* global Definition of Done (§DoD).
- **Moderator-disconnect gap (carried from Phase 1):** no story yet owns "who reveals if the
  moderator drops." *Mitigation:* logged as an open question for Phase 3/4, not silently assumed.

## Deliverables

### D1 — Story catalogue
13 epics (A–M), ~50 stories with Given/When/Then acceptance criteria covering all v1 FRs and
personas P1–P6 (see §Functional Requirements above).

### D2 — Traceability matrix (story → FR/BR)
| Epic | Stories | Primary FR/BR coverage |
|---|---|---|
| A Platform & Tenancy | A1–A5 | FR-1,2,3a,3b; BR-19; NFR-8 |
| B Identity & Onboarding | B1–B5 | FR-4,5,3a; BR-26 |
| C Authoring & Lifecycle | C1–C5 | FR-6,7,8,9; BR-5 |
| D Configuration Blocks | D1–D4 | FR-10,12,22,26,33,34; BR-3,4,6,13 |
| E Questions & Options | E1–E2 | FR-10; BR-21 |
| F Registration | F1–F3 | FR-3a, registration flow |
| G Live Execution | G1–G5 | FR-18,19,21; NFR-1 |
| H Submission & Durability | H1–H3 | FR-17,20,38,39,40,41; BR-7,8,9; NFR-5 |
| I Wildcards | I1–I4 | FR-23,24,25,26,27; BR-10,11,12,13 |
| J Leaderboards | J1–J3 | FR-28,29,30,31,32; BR-14,14b; NFR-3 |
| K Elimination | K1–K2 | FR-33–37; BR-16,25 |
| L Results/Notifs/Audit | L1–L3 | FR-27,37,41; tech-spec §6 |
| M Recovery & Ops | M1–M4 | FR-42,43,44; NFR-6,7,9; BR-18,23 |

### D3 — Definition of Done (global, applies to every story)
1. Tenant isolation enforced and **negative-path tested** (no cross-tenant read/write).
2. AuthN/AuthZ checked against the role-permission matrix.
3. Audit/lifecycle events written where BRs require.
4. Server-authoritative timing/scoring (never trust client clock/score).
5. Acceptance criteria automated as tests (Phase 20) including failure paths.
6. Accessibility (WCAG 2.1 AA) for any participant/admin-facing UI story.

### D4 — Open questions carried forward
1. **Moderator-disconnect fallback** during Live (auto-reveal vs pause) — needs an owning story
   once decided (Phase 3/4).
2. **Spectator scope** — which later groups/views an eliminated participant may see (Phase 3).
3. **Bulk-import credential distribution** UX — how Org Admin safely hands out one-time passwords
   (Phase 6).

---

> **Next phase (await approval):** Phase 3 — Use Cases. Do not generate until approved.
