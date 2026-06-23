# ContestForge — AIDLC Phase 17: Security Design

| | |
|---|---|
| **Phase** | 17 of 25 — Security Design |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 5/7; technical-spec §7; `.neutron/security.md`; ADR-001 |
| **Feeds** | Phases 18–22, 25 |

---

## Goal
Define the **security design**: trust boundaries, threat model, the tenant-isolation control stack,
authN/Z, secrets, transport, anti-abuse, data protection, and compliance posture — security by design.

## Assumptions
- Tenant isolation is the **primary security boundary** (NFR-8). JWT + email/password (no SSO v1).
  AWS managed services; WAF/ALB edge. SOC 2 Type II + GDPR readiness baseline.

## Functional Requirements
### 17.1 Trust boundaries
Client ↔ edge (WAF/ALB/TLS) ↔ API/WS (authn/z, tenant ctx) ↔ workers (envelope-scoped tenant) ↔ PG/Redis
(network-isolated, encrypted). Super Admin is platform-scoped but cannot enter tenants.

### 17.2 Threat model (STRIDE highlights)
- **Spoofing:** JWT signature/expiry; ticket single-use for WS; password hashing (Argon2/bcrypt).
- **Tampering:** server-authoritative timing/scoring; client never trusted for time/score; input
  validation (Pydantic); composite FKs.
- **Repudiation:** audit log (org/lifecycle/wildcard/elimination/tiebreak); correlation ids.
- **Information disclosure:** **tenant isolation** (app fail-closed + composite FK + RLS); masked
  leaderboard server-side; no PII in logs; 404 where existence is sensitive.
- **DoS:** WAF + ALB; app rate limits (per user/tenant/IP; WS msg rate); answer 1/sec; submission windows.
- **Elevation:** RBAC per endpoint + per WS action vs the role-permission matrix; `POST /users` rejects
  SUPER_ADMIN; super-admin bootstrap out-of-band.

### 17.3 Tenant isolation control stack (defense in depth)
1. JWT carries role + tenant_id. 2. Request middleware sets tenant contextvar. 3. SQLAlchemy mixin
auto-scopes; **unscoped query fails closed** in prod. 4. Composite FKs `(tenant_id,parent_id)`. 5. RLS
policies. 6. Cross-tenant → 403 + security log. 7. Workers re-establish tenant from envelope/row.
8. **Automated isolation suite** parameterised over every tenant-scoped resource (NFR-8).

### 17.4 AuthN/Z
- Access JWT short-lived; refresh rotating, family-tracked; reuse-revokes-family (BR-26). Logout revokes.
  Passwords hashed adaptively; min length; change-password flow. RBAC matrix = single source of truth.

### 17.5 Transport & secrets
- TLS for HTTP, WSS for WS. Secrets in cloud secret store (DB/Redis/JWT keys); never in source/logs/env
  dumps. Key rotation policy for JWT signing keys.

### 17.6 Data protection & privacy
- Encryption at rest (RDS/ElastiCache) + in transit; app-level encryption for participant PII. GDPR:
  right to erasure/export via tenant deletion or per-user flows; tenant soft-delete 30-day grace → hard
  delete cascade. Retention: active/archived indefinite while tenant active.

### 17.7 Anti-abuse
- Rate limits (defaults: login 5/min/IP; REST 100/min/user, 1000/min/tenant; WS 10 msg/sec; answer
  1/sec). Bulk-import bounded (≤5000). Single-use WS tickets. No public signup (reduced attack surface).

## Non-functional Requirements
- No cross-tenant access on any endpoint/WS action (NFR-8), test-verified at 100% coverage of resources.
- Secrets never logged; security events (cross-tenant, auth failures) logged + alertable.
- Least privilege for service IAM roles and DB users.

## Edge Cases
- Suspended tenant: all tenant operations denied even with valid JWT. Rate-limit store down →
  fail-closed for `/auth/login`, fail-open elsewhere (documented). Ticket replay rejected. Stale token
  after role change → short access TTL bounds exposure.

## Future Considerations
- SSO/SAML/OIDC; MFA for admins; per-tenant region/residency; full SOC 2 audit; anomaly detection;
  field-level encryption expansion; WAF managed rule tuning.

## Risks
- **Single unscoped query = breach.** *Mitigation:* fail-closed + RLS + isolation suite + raw-SQL review.
- **JWT key compromise.** *Mitigation:* secret store + rotation + short TTL.
- **DoS on live WS at scale.** *Mitigation:* edge + app limits + gateway autoscale + tickets.
- **PII exposure in logs.** *Mitigation:* structured-log redaction rules + review.

## Deliverables
- **D1** Trust boundary + STRIDE threat model (17.1–17.2).
- **D2** Tenant-isolation control stack (17.3) + isolation-suite requirement.
- **D3** AuthN/Z, transport, secrets, data-protection, anti-abuse specs (17.4–17.7).
- **D4** Compliance posture (SOC2/GDPR) + open items (full audit scope) → references `.neutron/security.md`.

---
> **Next phase:** Phase 18 — Error Handling Strategy.
