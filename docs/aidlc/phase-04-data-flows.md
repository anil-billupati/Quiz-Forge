# ContestForge — AIDLC Phase 4: Data Flows

| | |
|---|---|
| **Phase** | 4 of 25 — Data Flows |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Source** | Phase 3 (Use Cases); technical-spec §3; domain-model; api-contracts |
| **Depends on** | Phase 3 (Use Cases) — approved; OI-1 resolved |
| **Feeds** | Phase 5 (Architecture), Phase 13 (DB), Phase 15 (WS), Phase 16 (Sequence) |

---

## Goal
Describe **how data moves** through ContestForge for each significant use case: which actors and
components produce/consume which data, which **data stores** it crosses, where the **durability and
idempotency boundaries** are, and where data is authoritative vs derived/rebuildable. This phase is
deliberately mechanism-aware (the technical-spec already fixes PostgreSQL/Redis/Streams), but stops
short of physical schema (Phase 13), API shapes (Phase 14), and timing diagrams (Phase 16). It also
formalises the **host-presence signal** introduced when OI-1 was resolved.

## Assumptions
- Stores and transports are fixed by the technical-spec: **PostgreSQL** = authoritative system of
  record; **Redis** (ElastiCache, cluster) = command stream (Redis Streams), per-contest pub/sub,
  leaderboard ZSETs, presence, idempotency/dedupe keys, rate-limit counters — all **rebuildable**,
  never sole source of truth.
- The **durability boundary** is the PostgreSQL commit of an accepted `AnswerSubmission` *before* the
  client ack. Everything downstream (scoring command, leaderboard) is asynchronous and idempotent.
- Command delivery is **at-least-once**; all consumers are **idempotent** (dedupe on submission id /
  command UUID).
- Every record and command carries `tenant_id` (+ `contest_id` where applicable); workers re-establish
  tenant context from the command envelope or the authoritative row.
- Data-flow notation: `[Actor]` external, `(Process)` component, `{{Store}}` data store, `→` data in
  motion (labelled with the payload).

## Functional Requirements
*(The data-flow catalogue — this phase's substance.)*

### Legend — stores
| Store | Role | Authority |
|---|---|---|
| `{{PG}}` PostgreSQL | Orgs, users, contests, config, questions, windows, submissions, scores, events | **Authoritative** |
| `{{Stream}}` Redis Streams | Command transport (scoring, checkpoint, lifecycle) | Transport (replayable) |
| `{{PubSub}}` Redis pub/sub | Per-contest fan-out channel (reveal, leaderboard, elimination) | Transport |
| `{{ZSET}}` Redis sorted sets | Leaderboard views per contest/group/view | Derived (rebuildable) |
| `{{Presence}}` Redis | WS presence: participants + **host presence** (Moderator/Org-Admin live) | Derived (rebuildable) |
| `{{Dedupe}}` Redis | Idempotency/dedupe keys, single-use live tickets | Derived (rebuildable) |
| `{{Rate}}` Redis | Token-bucket rate-limit counters | Derived (rebuildable) |

---

### DF-1 — Authentication & token lifecycle
```
[User] → (REST API: /auth/login {email, pwd, tenant_slug})
        → (resolve tenant_slug → Organization.id) ──read──> {{PG: organization}}
        → (verify password_hash) ──read──> {{PG: user}}
        → (issue access JWT {role, tenant_id} + refresh) ──write refresh hash──> {{PG: refresh_token}}
        → [User] {access, refresh}
[User] → (/auth/refresh) → rotate: revoke used, issue new (same family) → {{PG: refresh_token}}
```
- **Rate-limit:** login attempts decrement `{{Rate}}` (5/min/IP). Reuse of a revoked refresh token →
  whole family revoked.
- *Authority:* `{{PG}}`. Access token is stateless (claims only). *Trace:* UC (GP1), FR-4; BR-26.

### DF-2 — Organization provisioning
```
[Super Admin] → (REST API: POST /organizations)
   → validate slug/portal_url/custom_domain uniqueness ──read──> {{PG}}
   → TXN: create Organization + TenantSettings + initial ORG_ADMIN user ──write──> {{PG}}
   → write AuditLog(org.create) ──write──> {{PG}}
   → [Super Admin] {org, admin}
```
- All writes in one transaction (atomic). *Authority:* `{{PG}}`. *Trace:* UC-1; FR-1.

### DF-3 — Bulk participant import
```
[Org Admin] → (REST API: POST /users/bulk {rows[] | CSV})
   → per row: validate format + uniqueness ──read──> {{PG: user}}
   → for valid rows: create PARTICIPANT + generate one-time pwd ──write (batch)──> {{PG: user}}
   → enforce tenant capacity (TenantSettings) ──read──> {{PG: tenant_settings}}
   → [Org Admin] {per-row results: CREATED(+otp,user_id) | SKIPPED(reason)}
```
- Partial success; one-time passwords returned in-response only (never stored in plaintext).
  *Authority:* `{{PG}}`. *Trace:* UC-2; FR-3a.

### DF-4 — Contest authoring (write path)
```
[Org Admin] → (REST API: contests / groups / configuration / questions / options)
   → validate (lifecycle stage, BRs: mode↔scoring, ≥1 correct option, elim rules, ranges)
   → TXN write ──> {{PG: contest, group, configuration_block, wildcard_config,
                        elimination_rule, checkpoint, question, option}}
   → lifecycle transition writes ContestLifecycleEvent ──> {{PG}}
```
- Reads dominate validation; writes are transactional. No Redis involvement (not a live path).
  *Authority:* `{{PG}}`. *Trace:* UC-3,4,5; FR-6–10.

### DF-5 — Registration
```
[Participant] → (REST API: POST /contests/{id}/registrations)
   → check stage=REGISTRATION_OPEN + capacity + no existing reg (atomic) ──> {{PG: registration}}
   → write Registration(REGISTERED) ──> {{PG}}
```
- Capacity check + insert are atomic (unique `(tenant,contest,participant)` + counted insert) so two
  racers cannot both win the last slot. *Authority:* `{{PG}}`. *Trace:* UC-6; FR-3a.

### DF-6 — Live connection establishment + presence
```
[Participant] → (REST API: POST /live-ticket)  [Bearer auth]
   → validate role+tenant+active registration ──read──> {{PG}}
   → mint single-use ticket ──write (TTL ~30s)──> {{Dedupe: ticket}}
   → [Participant] {ticket}
[Participant] → (WS Gateway: connect, Sec-WebSocket-Protocol: ticket.<v>)
   → consume+invalidate ticket ──> {{Dedupe}} ; resolve principal
   → subscribe connection to contest channel ──> {{PubSub}}
   → record participant presence ──> {{Presence}}
[Moderator/Org Admin] → (WS Gateway connect, same ticket flow)
   → record HOST presence (role=MODERATOR|ORG_ADMIN) ──> {{Presence: host}}   ← OI-1 signal
```
- **Host-presence signal (OI-1 formalised):** `{{Presence}}` holds, per live contest, whether a host
  (Moderator or Org Admin) currently has an open control connection. Key:
  `tenant:{t}:contest:{c}:host_present` (set with heartbeat TTL; cleared on disconnect/expiry). It is
  **derived/rebuildable** (recomputed from live connections), never authoritative scoring data.
  *Trace:* UC-7; FR-43; OI-1.

### DF-7 — Question reveal & fan-out (Automatic + Moderator-Controlled + auto-pause)
```
(Execution Engine) reaches reveal point
   → AUTOMATIC: timer fires │ MODERATOR-CONTROLLED: waits for trigger
   → [check host presence] ──read──> {{Presence: host}}
        • MODERATOR-CONTROLLED & host absent → AUTO-PAUSE: emit "waiting_for_host", no reveal
        • else proceed
   → TXN: create/lock QuestionWindow {revealed_at, submission_close_at} ──> {{PG: question_window}}
   → publish question.reveal (no correctness, close_at) ──> {{PubSub}}
   → (WS Gateway) fan-out to subscribers ──> [Participants]   (p99 ≤ 200ms)
(host reconnects) → {{Presence: host}} set → host triggers reveal → resume from QuestionWindow write
```
- Open windows already revealed keep closing on their server schedule even while paused (pause blocks
  only the *next* reveal). The authoritative timing lives in `{{PG: question_window}}`; `{{PubSub}}`
  only transports. *Trace:* UC-8 (incl. A2); FR-18,19; NFR-1.

### DF-8 — Answer submission (critical path: durability + idempotency)
```
[Participant] → (WS Gateway: answer.submit {question, option, attempt_no})
   → forward to (REST/Submission handler)
   → rate-limit (1/sec/participant) ──> {{Rate}}
   → validate: contest LIVE, window open vs server submission_close_at, not eliminated
            ──read──> {{PG: question_window, registration}}
   ┌─ DURABILITY BOUNDARY ───────────────────────────────────────────────┐
   │ → compute idempotency_hash(contest|question|participant|attempt_no)   │
   │ → INSERT AnswerSubmission {server_accepted_at (trigger clock), hash}  │
   │      ──write, UNIQUE(tenant,hash)──> {{PG: answer_submission}}        │
   │ → (same TXN) write OutboxEvent(answer.accepted) ──> {{PG: outbox}}    │
   └──────────────────────────────────────────────────────────────────────┘
   → answer.ack {accepted:true} ──> [Participant]
(Outbox relay) → publish scoring command {tenant, contest, answer_submission_id} ──> {{Stream}}
```
- **Ack is sent only after the PG commit.** Duplicate submit → unique `(tenant, idempotency_hash)`
  collision resolves to the existing row (one record, one ack). On a failed write → non-accepted ack;
  client retries; the deterministic hash prevents a later double-record.
- **Late:** `server_accepted_at > submission_close_at` → `accepted:false, reason:window_closed`.
- *Authority:* `{{PG}}` (submission). *Trace:* UC-9; FR-17,20,38–41; BR-7,8,9; NFR-5.

### DF-9 — Scoring & leaderboard update
```
(Scoring Engine) ← consume scoring command (consumer group, partition by contest hash) ← {{Stream}}
   → dedupe on answer_submission_id ──> {{Dedupe}}
   → read submission + active ConfigurationBlock ──read──> {{PG}}
   → compute points (Fixed: correct_points/0, floored at 0; or Time-Based band/decay;
        Second-Chance rate; Skip credit)
   → INSERT Score (UNIQUE per answer_submission_id → at-most-once) ──> {{PG: score}}
   → mark AnswerSubmission.scored = true ──> {{PG}}
   → upsert ParticipantScoreSummary (derived) ──> {{PG}}
   → signal Leaderboard Engine ──> {{Stream/PubSub}}
(Leaderboard Engine)
   → update view ZSET(s) {Contest|Group|Survivor} ──> {{ZSET}}
   → per update_frequency + visibility, publish leaderboard.update ──> {{PubSub}} → [clients]
        • MASKED: compute full board in {{ZSET}}, emit only own rank per participant
```
- `{{Score}}` is authoritative; `{{ZSET}}` + `ParticipantScoreSummary` are derived and rebuildable.
  *Trace:* UC-10; FR-28,30–32,39,40; BR-8,14,14b,14c; NFR-3.

### DF-10 — Elimination checkpoint
```
(Execution Engine) reaches checkpoint → emit checkpoint.reached ──> {{Stream}}
(Elimination Engine) ← consume ← {{Stream}}
   → read authoritative scores/summaries ──read──> {{PG: score, participant_score_summary}}
   → evaluate rule set (AND|OR); compute eliminated set
        (Bottom-X% tie at boundary → eliminate ALL tied in cut)
   → TXN: write EliminationEvent[] + set Registration.status=ELIMINATED + lock survivor list ──> {{PG}}
   → write OutboxEvent(eliminations) ──> {{PG: outbox}}
(Outbox relay) → publish elimination.event + Notification rows ──> {{PubSub}} / {{PG: notification}}
(Leaderboard Engine) → refresh Survivor ZSET ──> {{ZSET}}
```
- Re-run after crash is idempotent (no double elimination). *Authority:* `{{PG}}`. *Trace:* UC-11;
  FR-33–37; BR-16,25.

### DF-11 — Automatic go-live
```
(Execution Engine: scheduler) polls/timers armed contests (lifecycle=SCHEDULED) ──read──> {{PG: contest}}
   → at scheduled_start_at: TXN transition LIVE + init ContestExecutionState (version guard)
        ──write──> {{PG: contest, contest_execution_state}}
   → write ContestLifecycleEvent ──> {{PG}}
   → begin reveal loop (DF-7)
```
- Version/optimistic lock → starts exactly once even across worker restarts. *Trace:* UC-12; FR-9; BR-5.

### DF-12 — Recovery (crash + cache loss)
```
CRASH (worker/API restart):
   (Engines) → reload ContestExecutionState + open QuestionWindows ──read──> {{PG}}
   → re-drive answer_submission WHERE scored=false through Scoring (idempotent) ──> {{PG: score}}
   → replay PENDING OutboxEvents ──> {{Stream/PubSub}}
   → resume within ≤30s; score totals identical (NFR-9)
CACHE LOSS (Redis flushed):
   (Leaderboard Engine) → rebuild ZSETs from Score / ParticipantScoreSummary ──read──> {{PG}}
   (Presence) → recomputed from live WS connections (incl. host presence)
   → ranks/scores unchanged (FR-44)
```
- No data flows *from* Redis as a source of truth on recovery — only `{{PG}}`. *Trace:* UC-14;
  FR-42,44; NFR-6,9; BR-18,23.

### DF-13 — Notifications
```
(Engines) write Notification rows (ELIMINATION|ANSWER_ACK|SPECTATOR_GRANTED|CONTEST_PROGRESS) ──> {{PG}}
   → publish to participant's channel ──> {{PubSub}} → [Participant]
[Participant] → (REST: GET /me/notifications | POST .../ack) → read/mark ──> {{PG: notification}}
```
- In-app only (v1); email/SMS deferred. *Authority:* `{{PG}}`. *Trace:* UC-11/15; FR-37,41.

### DF-14 — Results & export
```
[Org Admin] → (REST: GET /results | /results/export | /wildcard-audit | /eliminations)
   → read final leaderboard + breakdown ──read──> {{PG: score, registration, contest_result_snapshot,
                                                      wildcard_activation, elimination_event}}
   → (on ARCHIVE) ContestResultSnapshot written once (immutable) ──> {{PG}}
   → CSV/JSON ──> [Org Admin]
```
- Reads from authoritative + immutable snapshot. *Trace:* UC-15; FR-27,45; BR-27.

### DF-15 — Observability (cross-cutting)
```
(All components) → structured logs (corr-id, tenant, contest, participant) ──> {{CloudWatch/OTel}}
   → metrics: reveal latency, scoring lag, queue depth, WS count, recovery duration
   → traces: API → {{Stream}} → engines (answer/scoring path)
```
- No PII/secrets in logs. Feeds NFR alerting. *Trace:* UC-14; tech-spec §6.

## Non-functional Requirements
- Every flow names its **data stores**, the **direction** of each data movement, and which data is
  **authoritative vs derived**.
- The **durability boundary** (DF-8) and the **at-most-once boundary** (DF-9) are explicit and singular.
- No flow treats Redis as a source of truth; all `{{ZSET}}/{{Presence}}/{{Dedupe}}/{{Rate}}` are
  rebuildable from `{{PG}}` or live connections.
- Each flow carries `tenant_id`/`contest_id` end-to-end; workers re-establish tenant context from the
  command envelope or authoritative row (no ambient tenant).

## Edge Cases
- **Ack lost after commit (DF-8):** answer is durable; client retry hits the idempotency unique and
  gets an accepted ack — no double record.
- **Scoring command duplicated (DF-9):** dedupe on submission id → single `Score`.
- **Reveal published but gateway pod dies mid-fan-out (DF-7):** window timing is in `{{PG}}`;
  reconnecting clients get the snapshot (DF-6) and the correct `submission_close_at`.
- **Host disconnect mid-open-window (DF-7):** current window still closes on schedule; only the next
  reveal is paused.
- **Capacity race on registration (DF-5):** atomic insert prevents over-admission.
- **Outbox relay lag (DF-8/DF-10):** answers/eliminations remain durable in `{{PG}}`; relay replays
  PENDING events on recovery (DF-12).
- **Presence false-negative (DF-6):** if host heartbeat expires while host is actually connected, a
  spurious pause may occur → resolved on next heartbeat; never affects scores.

## Future Considerations
- **CDC/event-sourcing** for cross-service analytics if the monolith splits (architecture phase).
- **Read-replica routing** for heavy results/export reads (DF-14).
- **Email/SMS notification fan-out** as an additional DF-13 sink once transport is integrated.
- **Async/streamed exports** for very large contests (DF-14).
- **Per-tenant region data residency** affecting where `{{PG}}`/`{{Redis}}` live.

## Risks
- **Durability-boundary blur:** if any downstream step is mistaken for the acceptance point,
  at-most-once breaks. *Mitigation:* DF-8 marks the boundary as the PG commit before ack, singular.
- **Presence treated as authoritative:** using `{{Presence}}` for anything but pause/resume UX risks
  scoring on volatile data. *Mitigation:* presence is explicitly derived; never gates scoring/timing.
- **Hot-partition skew (DF-9):** one massive contest hashing to few partitions could lag. *Mitigation:*
  partition-by-contest + independent scoring/leaderboard scaling (revisited Phase 5/21).
- **Outbox backlog:** unbounded PENDING events delay fan-out. *Mitigation:* relay throughput +
  dead-lettering monitored (DF-15 metrics).

## Deliverables
### D1 — Data-flow catalogue
15 data flows (DF-1..DF-15) covering all Phase-3 use cases, each with store crossings, motion labels,
and authority annotation.

### D2 — Store authority map
Authoritative: `{{PG}}` only. Transport: `{{Stream}}`, `{{PubSub}}`. Derived/rebuildable: `{{ZSET}}`,
`{{Presence}}` (incl. host presence), `{{Dedupe}}`, `{{Rate}}`.

### D3 — Boundary register
- **Durability boundary:** PostgreSQL commit of `AnswerSubmission` before client ack (DF-8).
- **At-most-once boundary:** unique `Score.answer_submission_id`, dedupe on consume (DF-9).
- **Idempotent re-drive:** `answer_submission.scored=false` recovery path (DF-12).

### D4 — Resolved residual (OI-1)
**Host-presence signal** formalised in DF-6/DF-7: a derived Redis key
`tenant:{t}:contest:{c}:host_present` (heartbeat TTL), recomputed from live control connections, used
**only** to drive Moderator-Controlled auto-pause/resume and the "waiting for host" UX. **No new
lifecycle stage and no change to `ContestExecutionState.phase`.**

### D5 — Open questions carried forward
1. Heartbeat interval / TTL for host (and participant) presence → Phase 13/15 tuning.
2. Outbox relay implementation (poller vs logical replication) → Phase 5/7.
3. Read-replica usage policy for results → Phase 13/21.

---

> **Next phase (await approval):** Phase 5 — High-Level Architecture. Do not generate until approved.
