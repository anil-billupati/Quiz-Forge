# ContestForge — AIDLC Phase 15: WebSocket Contracts

| | |
|---|---|
| **Phase** | 15 of 25 — WebSocket Contracts |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 4 (Data Flows), Phase 13/14; api-contracts.md §WebSocket |
| **Feeds** | Phase 7/10 (WS gateway), Phase 12 (WS client), Phase 16/20 |

---

## Goal
Formalise the **live WebSocket contract** (not expressible in OpenAPI): connection/auth, the message
envelope, server→client events, client→server actions, presence/heartbeat, and durability/ack
semantics — extending api-contracts.md §WebSocket with the OI-1 host-presence additions.

## Assumptions
- WSS only; one connection per participant/host per live contest; per-contest pub/sub fan-out.
- Auth via single-use connection ticket (no token in URL); principal resolved pre-upgrade.

## Functional Requirements
### 15.1 Handshake & auth
1. `POST /contests/{id}/live-ticket` (Bearer) → `{ticket, expires_in≈30}` after role/tenant/registration check.
2. Connect `wss://…/contests/{id}/live` presenting `Sec-WebSocket-Protocol: ticket.<value>`; server
   consumes ticket (single-use), resolves principal, validates, upgrades. Expired/used/invalid → reject pre-upgrade.

### 15.2 Message envelope
```json
{ "type": "<event|action>", "id": "<uuid>", "ts": "<server ISO8601>",
  "contest_id": "<uuid>", "data": { ... } }
```
- Server stamps `ts` (authoritative). Client actions may include a client `id` for local correlation only.

### 15.3 Server → client events
| Event | Data | When |
|---|---|---|
| `question.reveal` | question id, sequence, text, options (no correctness), `submission_close_at` | reveal (≤200ms) |
| `answer.ack` | submission id, attempt_no, accepted(bool), reason? | after durable accept/reject |
| `question.evaluation` | correct option id, explanation | after window close |
| `leaderboard.update` | view, entries (delta|snapshot), masked? | per update_frequency |
| `elimination.event` | participant id, final rank/score, spectator flag | at checkpoint |
| `contest.progress` | current group/question, phase | on advance |
| `host.status` | `host_present` (bool) | host connect/disconnect (drives waiting-for-host) |
| `contest.paused` / `contest.resumed` | reason (`host_absent`) | Moderator-Controlled auto-pause/resume |

### 15.4 Client → server actions
| Action | Data | Rules |
|---|---|---|
| `answer.submit` | question id, option id, attempt_no | reject if `> submission_close_at` (`window_closed`) or eliminated; server time authoritative; idempotent by hash |
| `wildcard.activate` | type, question id | enabled+eligible (TOP_50 @ question start); once per contest; Fifty-Fifty pre-answer only |
| `moderator.reveal` | question id | Moderator/Org-Admin only; Moderator-Controlled mode |
| `moderator.advance` | scope QUESTION/GROUP | Moderator/Org-Admin override |
| `heartbeat` | — | keep-alive; refreshes presence TTL |

### 15.5 Presence & heartbeat (OI-1)
- Participant + **host** presence in Redis with heartbeat TTL. Host (Moderator|Org-Admin) presence drives
  `host.status` and auto-pause/resume. Presence is derived/rebuildable (Phase 4 §D4); never gates scoring.

### 15.6 Durability/ack semantics
- `answer.submit` acked only after durable PG persist with server-accept time vs authoritative window.
  Deterministic `idempotency_hash` dedupes retries (no client key needed). A delayed ack never revokes
  an already-accepted answer.

### 15.7 Reconnection
- On reconnect: re-ticket → reconnect → server pushes snapshot (current question w/o correctness,
  `submission_close_at`, my status/score) within ≤3s; missed events reconciled by snapshot, not replay.

### 15.8 Rate limiting & errors
- 10 msg/sec/connection; answer 1/sec/participant. Protocol errors → `error` event `{code,message}`;
  malformed → close with code. Rate-limit breach → throttle + `error`.

## Non-functional Requirements
- Reveal fan-out p99 ≤200ms (NFR-1); leaderboard push ≤500ms (NFR-3); reconnect ≤3s (NFR-7).
- Per-action RBAC; per-message tenant validation; no cross-contest leakage.
- Stateless gateway; presence/state rebuildable.

## Edge Cases
- Ticket reuse/expiry rejected pre-upgrade. Duplicate submit → one ack. Host disconnect mid-open-window
  → window still closes; only next reveal pauses. Reduced-motion clients still get state, not animation.
- Out-of-order delivery → client reconciles via snapshot + monotonic `ts`/sequence.

## Future Considerations
- Binary/compact framing for scale; backpressure strategy; multiplex spectator-only channel; email/SMS
  fan-out parity for notifications.

## Risks
- **Ordering/duplication** under reconnect → snapshot-based reconciliation + idempotent submit. **Presence
  flapping** → heartbeat TTL tuning (Phase 13/ops). **Fan-out latency at 10k** → gateway scaling + pub/sub.

## Deliverables
- **D1** Handshake/auth + envelope spec (15.1–15.2).
- **D2** Event/action catalogue incl. host.status/paused/resumed (15.3–15.4).
- **D3** Presence/heartbeat + durability/ack + reconnection semantics (15.5–15.7).
- **D4** Rate-limit/error rules (15.8). To be folded into api-contracts.md §WebSocket on approval.

---
> **Next phase:** Phase 16 — Sequence Diagrams.
