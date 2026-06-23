# Design Decisions (Tier 2)

Tier 2 = implementation-level choices that don't rise to an ADR but are worth
recording. Tier 1 architectural decisions live in `docs/adr/`.

---

## 2026-06-22 — Unit 1: Tenant-scoping mechanism (realises ADR-001)

**Decision:** Implement automatic tenant scoping with two SQLAlchemy
session-level hooks rather than ad-hoc per-query filters:
- `do_orm_execute` + `with_loader_criteria(TenantScoped, …)` appends a
  `tenant_id` filter to every SELECT/UPDATE/DELETE touching a tenant-scoped
  entity, and raises `UnscopedQueryError` when enforcement is on and no tenant
  context is set.
- `before_flush` auto-stamps `tenant_id` on new tenant-scoped rows from request
  context, so the value is never client-supplied and cannot drift from the FK
  chain.

**Why:** Centralises isolation in one place (the heart of ADR-001), so no
individual query can forget to scope; the assertion converts a silent
cross-tenant leak into a hard failure that the NFR-8 suite can detect.

**Alternatives:** per-repository manual filters (error-prone, easy to forget);
RLS-only (loses ORM-level safety and clear errors). RLS is kept as
defence-in-depth, not the sole mechanism.

## 2026-06-22 — Unit 1: tenant_id stored as String(36) in scaffold

**Decision:** The `TenantScoped.tenant_id` column is `String(36)` for now.
**Why:** Keeps the foundation backend-agnostic and testable on SQLite before the
`organization` table exists. **Follow-up:** Unit 2 converts it to a UUID column
with a composite FK `(tenant_id, parent_id)` to its parent, per ADR-001.

## 2026-06-22 — Unit 1: RLS GUC wiring deferred (FINDING, not yet resolved)

**Observation:** The `0001_foundation` migration enables RLS with a policy on
`current_setting('app.tenant_id', true)`, but Unit 1 enforces isolation at the
ORM layer and does **not** yet set the `app.tenant_id` Postgres session GUC per
transaction. Until that GUC is set, the RLS policy is present but inert (the
ORM-level scoping is the active guard).
**Plan:** Wire a per-session `SET LOCAL app.tenant_id = :tenant` from the tenant
context in Unit 2 (when real DB sessions carry an authenticated tenant), so RLS
becomes the active second layer. Surfaced rather than silently implemented to
stay within Unit 1's scope.

## 2026-06-22 — Unit 2: initial credentials set by creator (contract change)

**Decision:** With email delivery out of scope for v1, the creator supplies the
password at creation time: `POST /super-admins` (own password), org creation
(`admin_password` for the provisioned Org Admin, set by the Super Admin), and
`POST /users` (password set by the Org Admin). Users change it later via
`POST /auth/change-password`.
**Contract change (logged):** added `admin_password` to
`CreateOrganizationRequest`; made `password` required (minLength 8) on
`CreateUserRequest`. `docs/spec/api-contracts.yaml` + `.md` updated to match.
**Why:** No transport to deliver an invite/temp credential; creator-set
passwords are the simplest correct v1 path and keep the onboarding chain working.

## 2026-06-22 — Unit 2: User not covered by the auto-scoping mixin

**Decision:** `User` carries a nullable `tenant_id` (null for SUPER_ADMIN), so
it does NOT use the `TenantScoped` mixin (which requires non-null tenant_id and
auto-filters). User queries are scoped to the caller's tenant explicitly in
`user_service`. **Why:** User spans platform + tenant scopes; forcing it through
the mixin would either break SUPER_ADMIN or mis-filter. Cross-tenant isolation
for User is covered by an explicit test (`test_cross_tenant_user_isolation`).

## 2026-06-22 — WebSocket auth: single-use ticket, never a JWT in the URL

**Decision:** WebSocket connections authenticate via a short-lived (~30s),
single-use **connection ticket**, not a JWT query parameter. The client calls
`POST /contests/{id}/live-ticket` with the normal `Authorization: Bearer`
header to mint a ticket, then presents it on the WS handshake via the
`Sec-WebSocket-Protocol` header.
**Why:** Browsers cannot set an `Authorization` header on a WebSocket handshake,
so the original draft used a query token — but a long-lived JWT in a URL leaks
into logs, proxies, and history. A single-use short-TTL ticket keeps the
credential exchange header-based and puts nothing sensitive in the URL.
**Contract:** `api-contracts.md` §WebSocket rewritten; `POST .../live-ticket`
added to `api-contracts.yaml`. Implemented in Unit 7 (WebSocket gateway).

## 2026-06-22 — Swagger Authorize button (HTTPBearer)

**Decision:** `get_principal` uses FastAPI `HTTPBearer(auto_error=False)` instead
of reading the raw `Authorization` header. **Why:** registers the Bearer security
scheme so Swagger UI shows the **Authorize** button; behaviour for clients is
unchanged (still `Authorization: Bearer <token>`), and `auto_error=False`
preserves the standard error envelope on 401.

## 2026-06-22 — Unit 2: timezone-safe refresh-token expiry comparison

**Decision:** When comparing `RefreshToken.expires_at` to now, coerce a naive
timestamp to UTC. **Why:** Postgres returns tz-aware datetimes but SQLite
(used in tests, and a valid local dev DB) returns naive ones; the guard makes
the check correct on both without depending on the backend's tz handling.
