# ContestForge — AIDLC Phase 14: API Contracts

| | |
|---|---|
| **Phase** | 14 of 25 — API Contracts |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 8; **`docs/spec/api-contracts.yaml` + `.md` (source of truth)** |
| **Feeds** | Phase 12 (typed client), Phase 20 (contract tests), Phase 25 |

---

## Goal
Confirm and formalise the **REST API contracts**. The authoritative contract is
`docs/spec/api-contracts.yaml` (OpenAPI 3.0.3) with the `.md` companion — already updated for the ten
decisions (bulk import endpoint; trimmed `WildcardConfig`/`ConfigurationBlock`/`TenantSettings`). This
phase validates coverage against features/use cases and fixes API conventions; it does not redesign.

## Assumptions
- API-first: `api-contracts.yaml` is the source of truth; the typed frontend client and contract tests
  are generated from it. WebSocket is contracted separately (Phase 15).

## Functional Requirements
### 14.1 Conventions (confirmed)
- Bearer JWT on all except `/auth/login`,`/auth/refresh`,`/health`,`/ready`. Roles SUPER_ADMIN/ORG_ADMIN/
  MODERATOR/PARTICIPANT; cross-tenant → 403. Single error shape `{error:{code,message,details}}`. Cursor
  pagination (`Page` envelope, limit 1–200/50). Status codes 200/201/202/204/400/401/403/404/409/422/503.

### 14.2 Resource coverage (confirmed vs features)
- Auth/session (F3) · Users + **/users/bulk** (F4,F5) · Organizations + settings + usage (F1,F2) ·
  Contests + lifecycle (F6) · Groups (F7) · Configuration (F8/F9/F10) · Questions/options (F11) ·
  Registration (F12) · Live: live-ticket, live-state, control/reveal, control/advance (F13,F14) ·
  Leaderboard/results/export/eliminations/wildcard-audit (F18,F19,F21) · Notifications (F20) · Audit (F22)
  · Ops health/ready (F0). **Every feature has REST coverage** (or WS where live).

### 14.3 Traceability
- The companion's "capabilities → endpoints" table maps FRs to paths; this phase confirms it is complete
  for v1 (incl. the new bulk-import path).

### 14.4 Validation & semantics
- Pydantic request validation → 400/422; invalid state transitions → 409; semantic (e.g. ELIMINATION
  missing rules) → 422. Late submit is a WS concern (rejected ack, not REST error).

### 14.5 Versioning & evolution
- URL `/v1` prefix; additive changes only within v1; breaking changes → `/v2`. Contract changes require
  a spec update + regenerated client + green schemathesis (CI gate, Phase 22).

## Non-functional Requirements
- Contract conformance enforced in CI (schemathesis vs live ASGI). Backward-compatible within v1.
- No endpoint exposes cross-tenant data; participant-facing question payloads omit correctness until
  evaluation (companion note).

## Edge Cases
- `POST /users/bulk` partial success returns 200 with per-row results (not 207); documented.
- `live-ticket`/WS handshake auth is header/subprotocol-based (no token in URL).
- Export returns CSV or JSON by `?format=`.

## Future Considerations
- OpenAPI for future self-registration/notifications-transport endpoints; webhooks; API keys for
  server-to-server (none in v1).

## Risks
- **Spec/impl drift** → contract tests as the gate. **Over-fetching on results** → replica + pagination.

## Deliverables
- **D1** Confirmation `api-contracts.yaml` is authoritative and complete for v1 (incl. bulk import).
- **D2** Conventions register (auth, errors, pagination, status codes, versioning).
- **D3** Feature→endpoint coverage check (no gaps).
- **D4** CI contract-test requirement (schemathesis) → Phase 22.

---
> **Next phase:** Phase 15 — WebSocket Contracts.
