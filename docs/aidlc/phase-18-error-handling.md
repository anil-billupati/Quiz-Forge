# ContestForge — AIDLC Phase 18: Error Handling Strategy

| | |
|---|---|
| **Phase** | 18 of 25 — Error Handling Strategy |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 7 (error model), Phase 14/15 (contracts), Phase 6 (UX states) |
| **Feeds** | Implementation, testing |

---

## Goal
Define a **consistent, layered error-handling strategy** across domain, application, API, WS, workers,
and UI — including retries, idempotency, dead-lettering, and how errors surface to each persona.

## Assumptions
- Single error shape `{error:{code,message,details}}` (REST) and `error` event (WS). Server-authoritative;
  late submit is a rejected ack, not an error. Technical-spec §5 is the baseline.

## Functional Requirements
### 18.1 Error taxonomy → mapping
| Class | Source | Surface |
|---|---|---|
| Validation (schema) | Pydantic | 400 |
| Semantic validation | domain (e.g. ELIMINATION missing rules; <2 options) | 422 |
| State conflict | lifecycle/locked config/illegal transition | 409 |
| AuthN | missing/invalid/expired token | 401 |
| AuthZ / cross-tenant | RBAC/tenant mismatch | 403 (404 if existence sensitive) + security log |
| Not found (in tenant) | repo | 404 |
| Rate limited | limiter | 429 (+ Retry-After) |
| Not ready | readiness | 503 |
| Unexpected | bug/infra | 500 + correlation id (detail server-side only) |
| Late submit / eliminated | submission | WS `answer.ack {accepted:false, reason}` (not error) |
| Durability fault | failed durable write | non-accepted ack; client retry safe (idempotent) |

### 18.2 Layered handling
- **Domain:** raise typed exceptions (`InvariantViolation`, `StateConflict`) — no HTTP knowledge.
- **Application:** translate domain → application errors; enforce idempotency.
- **API/WS adapters:** central handler maps to status/ack + correlation id; never leak internals/secrets.
- **Workers:** errors are retried/dead-lettered, not returned to a user.

### 18.3 Retry, backoff, idempotency (workers)
- At-least-once consume + **idempotent handlers** (dedupe submission id / command UUID). Transient →
  exponential backoff (capped, jittered). Poison → **dead-letter** after max attempts; alert; never block
  the contest. Re-drive on recovery is idempotent (scored flag, unique Score).

### 18.4 Client/UX surfacing (per Phase 6)
- Inline (422 field) · banner (409 state, e.g. config locked / concurrent change) · toast (transient) ·
  full-screen (auth/connection loss). Live: ack rejected reasons (`window_closed`,`eliminated`),
  reconnect banner, waiting-for-host. **Never** show false "accepted".

### 18.5 Correlation & observability
- Every error carries a correlation id (also returned on 500) tying client report → server logs/traces.
  4xx logged at info/warn (no PII), 5xx at error with stack server-side.

### 18.6 Idempotency & exactly-once boundaries
- Submission idempotency hash (retry-safe); Score unique per submission (at-most-once); elimination
  idempotent re-run; go-live version-guarded. These are the integrity-critical error paths.

## Non-functional Requirements
- Uniform error shape everywhere; no stack traces/secrets to clients; correlation id on 5xx.
- Failure paths are tested (negative-path ACs from Phase 2/3).
- A contest never halts due to a single poison message (dead-letter isolation).

## Edge Cases
- Ack lost post-commit → retry accepted via idempotency. DB down on submit → non-accepted ack +
  client retry. Redis (limiter) down → fail-open/closed per policy (Phase 17). Partial bulk-import →
  per-row errors, 200 envelope. Concurrent builder edit after lock → 409 banner + refresh.

## Future Considerations
- Problem+JSON (RFC 9457) adoption; user-facing error catalog localization; circuit breakers if external
  deps added (email/SMS).

## Risks
- **Inconsistent ad-hoc errors** → central handler + contract tests. **Silent answer loss masked as
  error** → durability boundary + idempotency tests. **Dead-letter pile-up unnoticed** → alerting (Phase 19).

## Deliverables
- **D1** Error taxonomy → status/ack mapping (18.1).
- **D2** Layered handling rules (18.2) + worker retry/backoff/dead-letter (18.3).
- **D3** UX surfacing tiers + message catalogue link (18.4).
- **D4** Idempotency/exactly-once error-path register (18.6) — integrity-critical, test-mandatory.

---
> **Next phase:** Phase 19 — Logging & Monitoring.
