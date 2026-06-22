# ContestForge — Security Approach

| | |
|---|---|
| **Project** | ContestForge |
| **Status** | Draft — aligned with product-spec and technical-spec |

---

## 1. Threat Model

The primary security boundary is **tenant isolation**. The most severe
realized risk is cross-tenant data leakage, followed by answer tampering,
unauthorized contest manipulation, and credential compromise.

| Threat | Mitigation |
|---|---|
| Cross-tenant read/write | `tenant_id` on every tenant-scoped table; SQLAlchemy mixin auto-filter; composite FKs; PostgreSQL RLS; fail-closed tests (NFR-8). |
| Answer tampering / replay | Server-authoritative timestamps; idempotency keys; durable PostgreSQL write before ack; at-most-once scoring. |
| Unauthorized lifecycle/config changes | RBAC with role-permission matrix; state-transition preconditions. |
| Credential stuffing / brute force | Argon2/bcrypt password hashing; rate limiting on `/auth/login` (5/min per IP). |
| Token theft / replay | Short-lived access tokens (~15 min); rotating refresh tokens; revocation on password change or tenant suspension. |
| DDoS / traffic abuse | AWS WAF + ALB; per-user, per-tenant, and per-IP rate limits; WS message throttling. |
| Secret exposure | AWS Secrets Manager; no secrets in source or logs. |
| PII exposure | Encryption at rest (RDS/ElastiCache); TLS/WSS in transit; audit logs without raw PII. |

---

## 2. Authentication

- Email + password for all user types.
- Passwords hashed with Argon2id (preferred) or bcrypt (cost ≥ 12).
- Access token lifetime ~15 minutes; refresh token rotates and is bound to a
  session/device fingerprint.
- Tokens carry `sub` (user id), `role`, and `tenant_id` (null for Super Admin).
- On login, `tenant_slug` resolves to `Organization.id`; mismatches or inactive
  tenants reject authentication.
- Tenant suspension: all tokens for the tenant are treated as revoked; active
  WebSocket connections are closed.

---

## 3. Authorization

- Role-permission matrix in `product-spec.md` §2.5 is the source of truth.
- Every REST endpoint and WebSocket action checks both role and tenant scope.
- Super Admin is platform-scoped but cannot run contests or submit answers.
- Cross-tenant access attempts return `403` and are logged as security events.

---

## 4. Data Protection

- **Encryption in transit:** TLS 1.2+ for HTTP, WSS for WebSockets.
- **Encryption at rest:** RDS storage encryption, ElastiCache at-rest encryption,
  S3/Secrets Manager encryption where used.
- **PII:** participant `email` and `display_name` are encrypted at the
  application level in addition to storage encryption. Right-to-erasure and
  data-export flows are supported via tenant deletion or user deletion.
- **Secrets:** JWT signing keys, database credentials, Redis credentials stored
  in AWS Secrets Manager and injected at runtime.

---

## 5. Audit & Logging

- Structured JSON logs with correlation IDs; never log full JWTs or passwords.
- Audit log events: organization create/suspend, lifecycle transitions,
  wildcard activations, elimination events, tie-break resolutions,
  cross-tenant access attempts, role changes.
- Audit logs retained for 1 year.

---

## 6. Rate Limiting & Abuse

| Layer | Limit |
|---|---|
| AWS WAF / ALB | L7 DDoS rules; configurable per deployment. |
| `/auth/login` | 5 attempts/min per IP. |
| REST API | 100 req/min per user; 1,000 req/min per tenant. |
| WebSocket messages | 10 msg/sec per connection. |
| Answer submissions | 1/sec per participant. |

---

## 7. Tenant Lifecycle Security

- Organizations are soft-deleted with a 30-day grace period, then hard-deleted
  with cascading removal of tenant data.
- Suspended tenants are blocked at JWT validation and all active sessions are
  terminated.
- Data residency is determined by the single platform region for v1 (configured
  in `infra.yaml`); per-tenant region selection is deferred to a later release.
