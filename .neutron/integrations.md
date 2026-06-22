# ContestForge — Integrations

| | |
|---|---|
| **Project** | ContestForge |
| **Status** | Draft |

---

## 1. Data Stores

### PostgreSQL (AWS RDS Multi-AZ)
- **Purpose:** authoritative system of record for all tenant, contest, config,
  answer, score, and result data.
- **Mode:** shared schema with `tenant_id` row-level scoping.
- **Failover:** Multi-AZ automatic failover; 35-day automated backups.
- **Access:** asyncpg/SQLAlchemy via IAM database authentication or Secrets
  Manager credentials rotated automatically.

### Redis (AWS ElastiCache for Redis Cluster, cluster mode enabled)
- **Purpose:** leaderboard ZSETs, per-contest pub/sub, WebSocket presence,
  idempotency/dedupe keys, rate-limit counters, command stream.
- **Topology:** cluster mode enabled; multi-AZ failover.
- **Key namespace:** `tenant:{tenant_id}:contest:{contest_id}:<purpose>`.
- **Eviction:** `allkeys-lru`; transient keys TTL 24 h after contest completion.

---

## 2. Message Transport

### Redis Streams
- **Purpose:** command stream from REST API / WS gateway to engine workers.
- **Partitioning:** by `contest_id` hash; one consumer group per engine type.
- **Semantics:** at-least-once delivery; idempotent consumers; exponential
  backoff retry; dead-letter stream after max attempts.

---

## 3. Edge & Networking

### AWS WAF + Application Load Balancer
- **Purpose:** L7 DDoS protection, TLS termination, rate limiting, routing to
  REST API and WS gateway.
- **WS Gateway:** ALB with sticky-session cookie for long-lived connections.

### CloudFront (optional)
- **Purpose:** static asset caching for Next.js frontend; deferred until
  production sizing.

---

## 4. Secrets & Identity

### AWS Secrets Manager
- **Purpose:** JWT signing keys, database credentials, Redis credentials,
  third-party API keys (future).
- **Rotation:** automatic rotation enabled for database credentials.

---

## 5. Observability

### OpenTelemetry + AWS CloudWatch
- **Purpose:** distributed traces, metrics, structured logs.
- **Sampling:** 100 % for errors, 1–10 % for normal traffic.
- **Metrics:** reveal fan-out latency, leaderboard push latency, answer-ack
  rate, scoring lag, queue depth, WS connection count, recovery duration.
- **Logs:** structured JSON with correlation IDs; audit log events retained
  1 year.

---

## 6. Region & Residency

- Platform region to be selected in `/neutron:plan`.
- v1 uses a single region for all tenants; per-tenant residency is deferred.
- Cross-region snapshots are optional and explicitly enabled at the platform
  level.
