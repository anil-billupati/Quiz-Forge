# ContestForge — Product Specification

| | |
|---|---|
| **Project** | ContestForge |
| **Source** | docs/kickoff.md |
| **Date** | 2026-06-19 |
| **Status** | Draft — for approval |

---

## 1. Problem Statement

Organizations need to run timed, competitive quizzes at scale (up to 10,000+
concurrent participants) with strict integrity guarantees: no submitted answer
is ever lost, scoring is server-authoritative and applied at most once, and
contest state is reconstructible after partial failure.

ContestForge is a multi-tenant live contest/quiz engine. A super admin creates
organizations (tenants); each organization's admins and moderators build and
operate contests in isolation from other tenants; participants register and
compete live.

The engine supports three **Modes** — Standard (fixed scoring), Speed
(time-based scoring), and Elimination (fixed scoring with knockout rules) —
applied to two **Structures** — Normal (one Configuration Block for the whole
quiz) and Grouped (a Configuration Block per group, run in sequence).

---

## 2. User Types & Primary Workflows

### 2.1 Super Admin (platform-level)
Operates above all tenants.

- **Create organization:** provision a new tenant (organization), assign an
  initial Org Admin, set tenant status (active/suspended).
- **Manage organizations:** list, suspend, reactivate tenants; view
  platform-wide usage.
- Super Admin is not scoped to any single tenant and cannot run contests.

### 2.2 Org Admin (tenant-scoped)
Owns contest configuration within one organization.

- **Manage tenant users:** create Org Admins, Moderators, and Participants
  individually, **or bulk-import Participants from a CSV** (`email, first_name,
  last_name`). Bulk import creates `PARTICIPANT` accounts and returns generated
  one-time credentials for out-of-band distribution (v1 has no email delivery);
  duplicates are skipped with a per-row reason. There is no public self-signup.
- **Create contest (Draft):** choose Structure (Normal | Grouped); set
  metadata (name, description, schedule).
- **Configure Configuration Block(s):** Mode, Question/Interval/Explanation/
  Leaderboard durations, wildcards (enabled set + eligibility), elimination
  rules (if Mode = Elimination), reveal mode, ranking criteria. For Normal one
  block; for Grouped one block per group.
- **Author questions:** add questions, options, correct answer, optional
  explanation; for Grouped, assign questions to groups.
- **Manage lifecycle:** Draft → Published → Registration Open → Registration
  Closed → Scheduled → Live → Completed → Archived (no stage skipped).
- **View results:** final leaderboards, per-participant breakdowns, wildcard
  audit, exports.

### 2.3 Moderator (tenant-scoped)
Controls a Live contest in real time.

- **Reveal control** (Moderator-Controlled reveal mode): trigger each question
  reveal manually; the interval timer pauses between questions.
- **Progression override:** advance question or group manually.
- **Monitor:** live participant count, current leaderboard, elimination events.

### 2.4 Participant (tenant-scoped)
Competes in contests.

- **Register** for a contest during Registration Open.
- **Join live** at start; receive questions within the server-authoritative
  window.
- **Submit answers** before the server-side close time; receive accept/reject
  acknowledgement.
- **Activate wildcards** (Fifty-Fifty, Second Chance, Skip) where enabled and
  eligible.
- **View leaderboards** per configured visibility; on Elimination, receive
  notification with final rank/score and optional spectator access.
- **Reconnect:** on disconnect/reconnect, current state and submission window
  are restored.

---

## 2.5 Role-Permission Matrix

| Operation | Super Admin | Org Admin | Moderator | Participant |
|---|---|---|---|---|
| Create / list / suspend organizations | ✅ | ❌ | ❌ | ❌ |
| Create / update / delete contests (Draft) | ❌ | ✅ | ❌ | ❌ |
| Configure groups / configuration blocks (Draft) | ❌ | ✅ | ❌ | ❌ |
| Author questions / options (Draft) | ❌ | ✅ | ❌ | ❌ |
| Advance contest lifecycle | ❌ | ✅ | ❌ | ❌ |
| View contest results / exports | ❌ | ✅ | ✅* | ❌ |
| Control live reveal / progression override | ❌ | ✅ | ✅ | ❌ |
| Self-register for a contest | ❌ | ❌ | ❌ | ✅ |
| Submit answers / activate wildcards | ❌ | ❌ | ❌ | ✅ |
| View live leaderboards | ❌ | ✅ | ✅ | ✅ |

\* Moderator may view live dashboards and post-contest results; Org Admin owns
all result exports and wildcard audit logs. All tenant-scoped operations are
filtered to the caller's tenant; cross-tenant access is denied and logged.

---

## 3. Functional Requirements

Numbered for traceability. **FR-#**.

### Tenancy & Identity
- **FR-1** A Super Admin can create an organization (tenant) and assign an
  initial Org Admin.
- **FR-2** A Super Admin can suspend/reactivate an organization.
- **FR-3** Every tenant-scoped entity (contest, question, participant, answer,
  result) is isolated to its organization; no cross-tenant read or write is
  possible.
- **FR-3a** Each organization has configurable resource limits:
  max concurrent live contests, max participants per contest, max questions per
  contest, and max API/WebSocket request rates. Limits are enforced at the API
  and stored in `TenantSettings`.
- **FR-3b** The platform records per-tenant usage aggregates (`TenantUsageRecord`)
  for capacity planning and future billing, even though billing itself is out of
  scope for v1.
- **FR-4** All user types authenticate via email + password and receive a JWT
  (access + refresh). Tokens carry the user's role and tenant scope (except
  Super Admin, which is platform-scoped).
- **FR-5** Roles are: Super Admin, Org Admin, Moderator, Participant. Role
  governs which operations and tenants are accessible. The first Super Admin
  account is bootstrapped at deployment and is not created through the tenant
  API.

### Contest Model & Lifecycle
- **FR-6** A contest is created with exactly one Structure (Normal | Grouped),
  chosen at creation.
- **FR-7** Structure locks at Published; Configuration becomes locked at
  Registration Open.
- **FR-8** A Normal contest has exactly one Configuration Block; a Grouped
  contest has one Configuration Block per group (≥1 group).
- **FR-9** The contest progresses through the fixed lifecycle (Draft →
  Published → Registration Open → Registration Closed → Scheduled → Live →
  Completed → Archived); no stage may be skipped. All transitions are explicit
  operator (Org Admin) actions **except Scheduled → Live, which is automatic**:
  once a contest is Scheduled with `scheduled_start_at`, the platform goes Live
  automatically when that time is reached, with no human action.
- **FR-10** A Configuration Block contains: Mode; Question Duration (5–300s);
  Question Interval (0–60s); Explanation Duration (0–60s); Leaderboard
  Duration (0–60s); enabled Wildcards with eligibility (each usable once per
  contest; no cooldown/carryover); Elimination Rules (required iff Mode =
  Elimination); Reveal Mode; Ranking Criterion. Scoring Model is derived from
  Mode and not independently set.

### Modes & Scoring
- **FR-11** Mode ∈ {Standard, Speed, Elimination}, available to both Normal and
  Grouped structures.
- **FR-12** Standard and Elimination use Fixed Scoring; Speed uses Time-Based
  Scoring. Scoring model cannot be chosen independently of Mode.
- **FR-13** Fixed Scoring: correct = +10 (configurable); wrong = 0
  (**no negative marking**); no answer/timeout = 0; Second Chance correct =
  reduced rate (default 50%). A participant's cumulative score never falls
  below 0.
- **FR-14** Time-Based Scoring: points decrease as response time increases,
  using configurable bands (default 100/75/50/25/10 across 0–5/6–10/11–15/
  16–20/20+ seconds) or a linear decay
  `points = max(floor, maxPoints − elapsedSeconds × decayRate)`; bands and
  decay are mutually exclusive per block. Bands match deterministically:
  each band is defined by its upper bound (`max_seconds`), a response falls in
  the **lowest band whose upper bound it does not exceed** (upper-inclusive,
  first match wins), so exactly 5.000 s → 100 and 5.001 s → 75. Response time
  is measured server-side from the authoritative `QuestionWindow.revealed_at`
  to server acceptance (single reveal instant, not per-client delivery).
  Timeout = 0 (no floor).
- **FR-15** Tie-breaking applies in order: (1) fastest total completion time,
  (2) fewest wrong answers, (3) earliest last correct submission. The sequence
  is deterministic and logged. When Second Chance is used on a question, that
  question contributes the **second attempt's** response time to the total.
- **FR-16** Grouped contests roll up group scores via one configurable
  strategy: Sum (default), Weighted Sum, or Best N Groups.

### Execution
- **FR-17** All timing is computed server-side; client clocks are display-only
  and never authoritative.
- **FR-18** Per-question flow: Display → Timer → Submission → Evaluation →
  Explanation → Leaderboard → Interval → Next, with durations from the active
  Configuration Block.
- **FR-19** Reveal Mode ∈ {Automatic, Moderator-Controlled},
  independent of Contest Mode, configured per quiz/group.
- **FR-20** Answers submitted after the server-side close time are rejected
  regardless of client clock.
- **FR-21** In Grouped contests, the engine advances between groups when: all
  group questions complete, OR elimination criteria are satisfied
  (Elimination groups), OR a moderator override is issued. Between groups it
  pauses to show the group leaderboard and announce eliminations.

### Wildcards
- **FR-22** Wildcards are disabled by default and configured per Configuration
  Block. Supported: Fifty-Fifty, Second Chance, Skip Question.
- **FR-23** Fifty-Fifty removes two incorrect options (correct always
  preserved); cannot be used after an answer is selected.
- **FR-24** Second Chance allows one more attempt after a wrong answer at
  reduced points (default 50%). The second attempt's response time is the one
  used for that question's Speed scoring and tie-break contribution (FR-15).
- **FR-25** Skip Question awards full points without showing/attempting it: in
  Fixed scoring, the full correct value; in Speed, the floor score (the minimum
  score for a correct answer; distinct from timeout, which awards 0).
- **FR-26** Each enabled wildcard is usable **at most once per participant for
  the entire contest** (not per group); there is **no cooldown** and **no
  per-group carryover/reset** — once used anywhere it is spent. A participant
  may use more than one wildcard on the same question (no per-question limit).
  Eligibility is `ALL` or `TOP_50_PERCENT` (top 50% by score), evaluated
  against the **last committed leaderboard at the start of the current
  question**.
- **FR-27** Every wildcard activation is logged (participant ID, type, question
  number, timestamp, outcome) and included in result exports.

### Leaderboards
- **FR-28** The engine maintains near-real-time rankings, computed server-side
  and pushed to clients; the server ranking is authoritative.
- **FR-29** Views: Contest Leaderboard (all contests), Group Leaderboard
  (Grouped; resets at group start), Survivor Leaderboard (Elimination; updates
  per checkpoint).
- **FR-30** Ranking criterion is configurable per block:
  - **Score Only:** highest score first; tie-break uses the full FR-15 sequence
    (fastest total completion time, fewest wrong answers, earliest last correct
    submission).
  - **Score + Time:** score first, then shortest total completion time;
    tie-break uses fewest wrong answers, then earliest last correct submission.
  - **Accuracy:** highest correct percentage first (correct ÷ **questions
    revealed so far**); tie-break uses score, then fastest total completion
    time.
- **FR-31** Update frequency is configurable: after every answer (≤500
  participants), after every question (default), or after every group (>5,000
  participants).
- **FR-32** Tie display modes: Shared Rank (default, e.g. 1,1,3), Fastest
  Participant, Least Incorrect. Visibility: Always | Post-question only |
  Hidden | Masked (own rank only).

### Elimination
- **FR-33** The Elimination Engine is active only when a block's Mode =
  Elimination; in Grouped contests, only Elimination groups are affected.
- **FR-34** Elimination rules — First Wrong Answer, N Wrong Answers (default 3),
  Bottom X Percent, Minimum Score Threshold — may be combined with AND/OR
  within one block. For Bottom X Percent, if the cut-off lands inside a group
  of tied participants, **all tied participants in the cut are eliminated** (a
  tie is never split).
- **FR-35** Checkpoints: After Question (specific question close), After Group,
  or Custom Milestone (admin-defined timestamp/event).
- **FR-36** At a checkpoint: evaluate rule → determine eliminated set → notify
  → lock survivor list → update leaderboard → proceed. Eliminated participants
  cannot answer further.
- **FR-37** Eliminated participants are notified with final rank/score and may
  be granted spectator (view-only) access. Survivors carry accumulated scores
  forward unless a reset is configured. The Survivor Leaderboard is active from
  the first checkpoint.

### Durability & Recovery
- **FR-38** Once an answer is accepted it is never lost; it survives any single
  component failure (server, cache, persistence layer).
- **FR-39** Each accepted answer is scored exactly once; retries/restarts do
  not double-count or drop submissions.
- **FR-40** The authoritative scoring timestamp is the moment the server first
  accepted the answer, regardless of later retry/recovery delay.
- **FR-41** A participant is told whether an answer was accepted; an accepted
  answer remains accepted even if confirmation is delayed by a fault.
- **FR-42** Contest state and recorded answers are reconstructible from
  authoritative storage at any point.
- **FR-43** On participant disconnect/reconnect, state is restored and the
  submission window honoured as it stood at disconnect. Transient network
  faults must not lose answers or advance the contest incorrectly; affected
  participants are notified.
- **FR-44** A cache loss must not change any participant's score or rank;
  rankings are recoverable from authoritative data.

### Data Retention
- **FR-45** Archived contests are read-only; results and leaderboards are
  preserved. Contest data is retained indefinitely.

---

## 4. Non-Functional Requirements

All latency targets are server-side, measured at the API/WebSocket gateway
unless otherwise noted. "Support" means the target is met while error rate
remains < 0.1 %.

- **NFR-1 (Latency — delivery):** p99 question fan-out latency ≤ 200 ms from
  scheduled reveal to WebSocket dispatch, at up to 10,000 concurrent
  participants per contest.
- **NFR-2 (Timer accuracy):** p99 server-side timer drift ≤ ±50 ms over a
  5-minute session.
- **NFR-3 (Leaderboard push):** p99 leaderboard update push latency ≤ 500 ms at
  ≤ 5,000 concurrent participants; ≤ 2 s at peak load (≤ 20,000).
- **NFR-4 (Scale):** Support up to 10,000 concurrent participants per contest;
  leaderboard push target covers 20,000 at peak.
- **NFR-5 (Durability):** Answer loss rate < 0.01 % across 10,000 submissions
  with a 1 % induced persistence-failure rate.
- **NFR-6 (Recovery):** A contest resumes within 30 s of a simulated crash of
  the API service or worker pods; state is intact and no double-scoring occurs.
- **NFR-7 (Reconnection):** p99 participant restore time ≤ 3 s after a
  WebSocket reconnect (server-side state + open submission window).
- **NFR-8 (Tenant isolation):** No cross-tenant data access on any implemented
  endpoint or WebSocket action; verified by an automated isolation suite that
  covers 100 % of tenant-scoped resources.
- **NFR-9 (Consistency):** Score totals are identical before a failure and after
  recovery (exact integer equality per participant and in aggregate).
- **NFR-10 (Mode correctness):** Each mode applies its correct scoring model in
  100 % of regression cases.
- **NFR-11 (Rate limiting):** API and WebSocket rate limits are enforced per
  user, per tenant, and per IP; legitimate traffic is never throttled below
  the configured limits.

---

## 5. Success Criteria

Measurable, mapped to the PRD acceptance criteria:

| Criterion | Pass condition |
|---|---|
| No answer loss | Zero of 10,000 submissions lost at 1% induced persistence-failure rate (NFR-5). |
| Contest recovery | Resume within 30s of simulated crash, state intact, no double-scoring (NFR-6). |
| Ranking recovery | Rankings correct after total cache-data loss (FR-44, NFR-9). |
| Consistent scoring | Score totals identical pre-failure and post-recovery (NFR-9). |
| Mode correctness | Correct scoring model applied in 100% of regression cases (NFR-10). |
| Reconnection | Participant restored within 3s (NFR-7). |
| Delivery latency | ≤200ms reveal fan-out at 10,000 users (NFR-1). |
| Tenant isolation | No cross-tenant access in automated isolation suite (NFR-8). |

---

## 6. Out of Scope

The Core Contest Engine spec does **not** cover:

- Billing, subscriptions, or payment processing.
- Question content authoring beyond multiple-choice (no free-text/coding
  questions in this engine version).
- AI-generated questions or auto-grading of non-MCQ answers.
- Public marketing site / participant discovery / contest marketplace.
- Email/SMS delivery infrastructure (notifications are emitted; transport is a
  later integration concern).
- Native mobile applications (web client only).
- Advanced anti-cheat/proctoring (camera, screen monitoring).
- Internationalization/localization of content.
- SSO/social login (deferred; JWT + email/password only for this version).

---

## 7. Compliance & Data Lifecycle

- **Compliance baseline:** SOC 2 Type II and GDPR readiness. Full certification
  scope to be confirmed with stakeholders before production launch.
- **Data residency:** v1 operates in a single platform region (configured in
  `infra.yaml`); per-tenant region selection is deferred to a later release.
- **Encryption:** TLS/WSS in transit; RDS/ElastiCache encryption at rest;
  application-level encryption for participant PII.
- **Retention:** active and archived contest data retained indefinitely while
  the tenant is active. Tenant soft-delete grace period is 30 days, followed by
  hard deletion with cascade.
- **Right to erasure / export:** supported via tenant deletion or per-user
  deletion flows; documented in `.neutron/security.md`.

## 8. Open Questions Remaining

1. **Compliance** — Baseline set to SOC 2 Type II and GDPR readiness; full
   audit/certification scope to be confirmed with stakeholders before production
   launch.
2. **Timeline / Budget** — Not yet provided (carried from kickoff).
3. **Notification transport** — In-app WebSocket events for v1; email/SMS/webhooks
   deferred to a later integration.
4. **Negative marking** — Resolved: negative marking is **not supported**. A
   wrong answer always scores 0 and cumulative score is floored at 0. The
   `wrong_points` field and the `default_negative_marking` tenant setting are
   removed.
