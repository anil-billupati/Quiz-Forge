# Frontend test & mock harness

Lets the UI team build against the API/WS contracts **before the backend exists**.
See `docs/aidlc/ways-of-working-contract-sync.md` for the full process.

## Generate typed REST client
```bash
npm run generate:api      # OpenAPI → src/types/api.gen.ts
```
Use the generated `components["schemas"][...]` / `paths` types in the API client and
tighten the MSW handler bodies to them.

## REST mocks (MSW)
- `msw/handlers.ts` — contract-shaped responses (auth, /users/bulk, contests, leaderboard, live-state, live-ticket).
- `msw/server.ts` — Node (vitest/integration). `msw/browser.ts` — browser (local dev).

**Run the UI with no backend:**
```bash
npx msw init public/ --save     # one-time: emit the service worker
NEXT_PUBLIC_API_MOCK=1 npm run dev
```
(Enable the worker in a client entrypoint guarded by `NEXT_PUBLIC_API_MOCK`.)

**Use in vitest:**
```ts
import { server } from "@/test/msw/server";
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## Live (WebSocket) mock
`@/lib/mockWs.ts` replays the live event sequence typed by `@/types/ws`:
```ts
import { startMockWs } from "@/lib/mockWs";
const ch = startMockWs((event) => dispatch(event), { speed: 4 });          // fast demo
const ch2 = startMockWs(onEvent, { simulateHostDisconnect: true });        // OI-1 auto-pause
ch.send({ type: "answer.submit", id: crypto.randomUUID(), ts: new Date().toISOString(),
          contest_id: "...", data: { question_id: "...", selected_option_id: "opt-b", attempt_no: 1 } });
ch.close();
```
Swap `startMockWs` for the real ticket→wss client at integration — event types are identical.

## Keeping in sync
After any contract change: re-run `generate:api`, update `msw/handlers.ts`, update `types/ws.ts` (if WS),
and ensure schemathesis (CI) is green. Do it at the per-feature **contract freeze**.
