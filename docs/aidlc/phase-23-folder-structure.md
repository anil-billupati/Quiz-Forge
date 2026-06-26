# ContestForge — AIDLC Phase 23: Folder Structure

| | |
|---|---|
| **Phase** | 23 of 25 — Folder Structure |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 5 (modules), Phase 7 (framework); existing `backend/`, `frontend/` |
| **Feeds** | Implementation |

---

## Goal
Define the **repository/folder structure** that expresses the module boundaries (Phase 5) and the
hexagonal layering (Phase 7), extending the existing `backend/`/`frontend/` layout rather than
reorganising it.

## Assumptions
- Monorepo: `backend/` (FastAPI + workers), `frontend/` (Next.js), `docs/`, infra. Existing files
  (`app/main.py`, `app/config.py`, `app/db.py`, `app/middleware/*`, `app/models/*`, `app/security/*`,
  `app/routers/*`, `app/services/*`, `app/workers/*`, `migrations/`, `tests/*`) are kept and extended.

## Functional Requirements
### 23.1 Backend layout (module-oriented, hexagonal)
```
backend/
  app/
    main.py                # API ASGI app (exists)
    cli.py                 # role entrypoints: api|ws|worker|relay (exists)
    config.py  db.py  redis_client.py  dependencies.py   # framework (exist)
    middleware/            # tenant_context, errors, logging (exist) + rate_limit
    observability/         # tracing (exists) + metrics, logging setup
    security/              # passwords, tokens (exist) + rbac dependency
    platform/              # shared kernel: outbox, eventbus, uow, base repo,
                           #   notifications, audit, presence, leader election
    modules/
      identity/            # org, tenant_settings, user, refresh_token, bulk import
        domain/ application/ adapters/ schemas/ router.py
      authoring/           # contest, group, config_block, wildcard_config,
                           #   elimination_rule, checkpoint, question, option
      execution/           # execution_state, question_window, reveal, scheduler,
                           #   moderator control, ws gateway handlers
      scoring/             # answer_submission, score, summary, wildcard runtime,
                           #   leaderboard
      elimination/         # checkpoint eval, elimination_event, survivor
    models/                # SQLAlchemy models (base exists) — per module or per-module subpkg
    schemas/               # shared Pydantic (pagination exists)
    workers/               # consumer entrypoints per engine (exists)
  migrations/              # alembic (exists)
  tests/ unit/ integration/ contract/ isolation/   # (unit+integration exist)
```
- Each `modules/<m>/` follows hexagonal layering: `domain/` (entities, invariants), `application/`
  (use-case handlers), `adapters/` (repos, redis), `schemas/` (Pydantic), `router.py` (driving adapter).
- **Boundary rule (CI-enforced, Phase 22):** a module imports only its own packages + `platform/` +
  shared `schemas/`; never another module's `domain/`/`adapters/`.

### 23.2 Frontend layout (Next.js App Router)
```
frontend/src/
  app/                     # routes per surface (auth, platform, org, live, moderator) (exists: layout/page)
  components/              # design-system primitives + domain components
  features/                # per-surface feature modules (builder, live, moderator, ...)
  lib/                     # apiClient (exists), wsClient, auth store, query cache
  styles/ tokens/          # design tokens, theme (light/dark)
  types/                   # generated API types + WS types (types/index.ts exists)
  test/                    # RTL, MSW handlers, Playwright, axe
```

### 23.3 Cross-cutting
- `docs/spec/` (source of truth), `docs/aidlc/` (these phases), `docs/adr/`, `docs/plan/`, `.neutron/`.
- Infra (IaC) in a dedicated dir (Phase 21/22) — to be added.

## Non-functional Requirements
- Structure mirrors architecture (screaming architecture); module boundaries discoverable + enforceable.
- Tests co-located/mirrored per module; shared kernel isolated in `platform/`.

## Edge Cases
- Models per module vs central `models/`: keep tenant mixin + base central; module-specific models in
  module (or a `models/<module>.py`) — consistency enforced by convention (Phase 24).
- Avoid `platform/` becoming a dumping ground: only genuinely shared cross-module concerns.

## Future Considerations
- Extracting a module to its own service → lift `modules/<m>/` + its adapters behind the same ports.
- Shared types package between BE/FE (codegen) if drift appears.

## Risks
- **God `platform/` package** → review discipline + boundary tests. **Module/model placement drift** →
  Phase 24 conventions + lint.

## Deliverables
- **D1** Backend module/hexagonal layout (23.1) extending existing `app/`.
- **D2** Frontend App-Router layout (23.2) extending existing `frontend/src/`.
- **D3** Boundary rule (module imports) for CI architecture tests (Phase 22).
- **D4** Cross-cutting/docs/infra placement (23.3).

---
> **Next phase:** Phase 24 — Coding Standards.
