# ADR-002 — Server-authoritative engines with transactional outbox, Redis Streams transport, and idempotent at-most-once scoring

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-22 |
| **Deciders** | Team contest (Lead: Hussain) |
| **Context source** | docs/spec/technical-spec.md §1–3, docs/spec/product-spec.md §3 (FR-38–44), domain-model.md (OutboxEvent) |

## Context

The product's core promise is contest integrity under partial failure: no
submitted answer is ever lost (FR-38), each accepted answer is scored exactly
once (FR-39), the authoritative scoring time is the moment of first server
acceptance (FR-40), and contest state is reconstructible at any point (FR-42).
At the same time, question delivery and answer intake happen over WebSockets at
up to 10,000 concurrent participants with ≤200 ms fan-out. We must decide how
the API/WS tier hands work to the scoring/leaderboard/elimination logic such
that those guarantees hold, before building the live path.

The tension: a fast WS acknowledgement vs. durable, exactly-once-effect
processing across separately scaled services.

## Decision

Adopt **server-authoritative engine workers** fed by a **transactional outbox +
Redis Streams** command bus with **idempotent consumers**:

1. The WS gateway/API persists an accepted answer to PostgreSQL **durably first**
   (server-accept timestamp + idempotency key `(contest, question, participant,
   attempt_no)`) — this write is the durability boundary — and acks the
   participant only after it commits (FR-38/40/41).
2. In the **same transaction**, an `OutboxEvent` is written; a relay publishes
   it to a **Redis Stream** (at-least-once).
3. The **Scoring Engine** consumes idempotently (dedupe on
   `answer_submission_id`; unique `score.answer_submission_id`), giving
   **at-most-once scoring** (FR-39). Leaderboard and Elimination engines consume
   downstream the same way.
4. **Redis is treated as rebuildable** — leaderboard ZSETs and presence are
   reconstructed from authoritative Postgres rows on cache loss (FR-44).
5. Workers are partitioned by `contest_id` hash and reload
   `ContestExecutionState` on restart for recovery within 30 s (FR-42, NFR-6).

## Consequences

**Makes easier:**
- The four guarantees (no-loss, at-most-once, authoritative timestamp,
  recoverability) follow directly from the outbox + idempotency design.
- Each engine scales independently on Streams consumer-group lag.
- A cache wipe or worker crash is non-destructive and self-healing.

**Makes harder:**
- More moving parts than synchronous scoring: outbox relay, Streams consumer
  groups, dead-letter handling, and idempotency keys must all be implemented and
  tested (covered by the resilience/chaos suite, NFR-5/6/9).
- Scoring is eventually-consistent relative to the ack; the leaderboard lags the
  answer by the processing window (bounded by NFR-3 push targets).
- Operational dependency on Redis Streams availability for timely processing
  (degrades gracefully — answers remain durable and are replayed).

## Alternatives considered

- **Synchronous in-request scoring:** simplest, but couples the ≤200 ms live
  path to scoring/ranking work and makes at-most-once-under-retry and recovery
  hard. Rejected.
- **External managed queue (SQS/Kafka) instead of Redis Streams:** viable and
  more durable out-of-the-box, but adds another infrastructure dependency when
  Redis is already required for ZSETs/pub-sub; Streams meets the need and keeps
  the footprint smaller. Chosen Redis Streams for v1; the outbox makes swapping
  the transport later low-risk.
- **No outbox (publish-after-commit):** risks a lost command if the process dies
  between commit and publish. Rejected — violates FR-38/39.
