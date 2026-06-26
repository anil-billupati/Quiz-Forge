# ContestForge — Ways of Working: Backend ⇄ UI Contract Sync

| | |
|---|---|
| **Purpose** | Keep the backend and UI teams in lockstep while implementing the AIDLC plan |
| **Model** | Contract-first · parallel · meet-in-the-middle |
| **Status** | Active playbook |
| **Date** | 2026-06-23 |

---

## 1. The single source of truth
- **REST contract:** `docs/spec/api-contracts.yaml` (OpenAPI 3.0.3) + `api-contracts.md` companion.
- **WebSocket contract:** `docs/aidlc/phase-15-websocket-contracts.md`, encoded for the UI as
  `frontend/src/types/ws.ts` (hand-authored — WS is not expressible in OpenAPI).
- **Shared design assets:** design tokens + component library (Phase 6), error/message catalogue
  (Phase 18).

If it isn't in the contract, it doesn't exist. Both teams build against these, not against each other.

## 2. The sync model
```
   docs/spec/api-contracts.yaml  +  frontend/src/types/ws.ts   (frozen per feature)
            /                                              \
   Backend implements                                UI generates types + builds
   behind the contract                               against MSW + mock WS
   (schemathesis proves it matches)                  (src/test/msw, src/lib/mockWs)
            \                                              /
              →  integrate in staging  →  contract tests  →  wave demo
```

## 3. Per-feature cadence (the ritual)
1. **Contract freeze (both teams, ~30 min):** review/agree any change to `api-contracts.yaml` and
   `ws.ts` for the feature. **Within v1, changes are additive only.** Merge the contract change first.
2. **Parallel build:**
   - **Backend:** implement the endpoint/engine behind the frozen contract; keep FastAPI's emitted
     OpenAPI matching the committed spec.
   - **UI:** run `npm run generate:api`, build against MSW mocks (`src/test/msw/handlers.ts`) and the
     mock WS emitter (`src/lib/mockWs.ts`).
3. **Integrate:** point the UI at real endpoints in staging.
4. **Verify:** contract tests (schemathesis vs `api-contracts.yaml`) + tenant-isolation suite green.
5. **Demo** the paired BE+FE feature; mark done only when both halves + tests exist.

## 4. Tooling (already wired)
- **REST types:** `cd frontend && npm run generate:api` → `src/types/api.gen.ts` (openapi-typescript).
  UI never hand-writes API types; spec drift becomes a TypeScript error.
- **WS types:** `frontend/src/types/ws.ts` — the shared envelope/event/action contract.
- **REST mocks:** `frontend/src/test/msw/{handlers,server,browser}.ts` (MSW). Browser worker lets UI
  run with **no backend** (`NEXT_PUBLIC_API_MOCK=1`).
- **Live mocks:** `frontend/src/lib/mockWs.ts` — replays reveal → ack → evaluation → leaderboard →
  progress (and host-disconnect auto-pause) typed by `ws.ts`. Swap for the real WS client at integration.
- **Contract test (CI gate):** schemathesis vs `api-contracts.yaml` (Phase 22) — the BE/FE convergence proof.

## 5. Who owns what
- **Backend:** engines, durability, scoring/elimination correctness, the OpenAPI/WS contract content.
- **UI:** surfaces, components, the design system, the WS client + mock parity.
- **Shared (change together):** `api-contracts.yaml`, `ws.ts`, design tokens, error/message catalogue.

## 6. Build order (parallelisable)
- UI can start **today, in parallel** with backend: foundation (shell, tokens, component library,
  typed client, MSW, mock WS), then track each wave (Phase 8/25):
  - **W1** F5 import ↔ FE3 · **W2** authoring F6–F11 ↔ FE4 builder · **W3** F12/F13 ↔ FE5 lobby ·
    **W4–5** live engines F13–F18 ↔ FE6 live / FE7 moderator · **W6** results/notifs ↔ FE8/FE9.
- The **live/WS surface is the riskiest sync point** — freeze `ws.ts` (event names + ack semantics)
  before either team starts the live wave; the mock WS lets UI build it ahead of the engine.

## 7. Rules that prevent drift
- Additive-only contract changes within `/v1`; breaking changes → `/v2` + joint sign-off.
- A contract change is **not done** until: spec updated · `generate:api` re-run · MSW handlers updated ·
  `ws.ts` updated (if WS) · schemathesis green.
- UI never trusts client time/score; the server is authoritative (timers/ranks are presentational).
- No false "accepted": the live UI only shows accepted after `answer.ack {accepted:true}`.

## 8. Definition of done (paired feature)
BE endpoint/engine + tests (unit/integration/contract/isolation) · FE surface + tests (RTL/MSW/axe,
Playwright for critical live flows) · contract green · observability wired · demoed end-to-end.

---
> Start here: the sync foundation (codegen + `ws.ts` + MSW + mock WS) is in place. UI can build the
> foundation and Wave-1 surfaces immediately; backend can start F5 → Wave 2 in parallel.
