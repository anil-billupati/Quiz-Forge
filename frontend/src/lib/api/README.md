# ContestForge Frontend API Clients

This directory contains thin REST clients for the ContestForge backend. Each
module maps to a backend router and exports typed request/response helpers.

## Participant role coverage

### Integrated (backend router exists)

| Client module | Endpoints | Status |
|---|---|---|
| `auth.ts` | `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`, `/auth/change-password` | Integrated |
| `registrations.ts` | `/contests/{id}/registrations`, `/contests/{id}/registrations/me`, `/contests/{id}/registrations/{id}` | Integrated |
| `live.ts` | `/contests/{id}/live-ticket`, `/contests/{id}/live-state` | Integrated |

### Blocked on backend units (do not wire until routers land)

The following Participant-facing APIs are defined in
`docs/spec/api-contracts.md` but are not yet implemented in the backend. The
frontend intentionally does not call these endpoints.

| Capability | Spec reference | Blocked by backend unit |
|---|---|---|
| Results + export | `GET /contests/{id}/results`, `GET /contests/{id}/results/export` | Unit 15 |
| Leaderboard snapshot | `GET /contests/{id}/leaderboard` | Unit 12 |
| Elimination list | `GET /contests/{id}/eliminations` | Unit 13 |
| Notifications | `GET /me/notifications`, `POST /me/notifications/{id}/ack` | Unit 14 |
| Wildcard audit | `GET /contests/{id}/wildcard-audit` | Unit 15/16 |
| WebSocket `wildcard.activate` | `docs/spec/api-contracts.md` §WebSocket | Unit 11 |
| Server event `question.evaluation` | `docs/spec/api-contracts.md` §WebSocket | Unit 11/12 |
| Server event `leaderboard.update` | `docs/spec/api-contracts.md` §WebSocket | Unit 12 |
| Server event `elimination.event` | `docs/spec/api-contracts.md` §WebSocket | Unit 13 |
| Server event `wildcard.applied` | Unit 11 delivery plan | Unit 11 |

## WebSocket wire format

The shared typed contract lives in `src/types/ws.ts` and uses envelope-shaped
messages. The current backend uses a flatter format keyed by `action` / `event`.
The translation happens in `src/hooks/useLiveContest.ts` (`toBackendAction`),
so component code stays typed while the wire format matches the backend.
