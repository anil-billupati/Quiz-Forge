# ContestForge — AIDLC Phase 12: UI Tasks

| | |
|---|---|
| **Phase** | 12 of 25 — UI Tasks |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 11 (UX Tasks), Phase 6 (Base UX), Phases 14/15 (contracts) |
| **Feeds** | Implementation (Phase 25) |

---

## Goal
Enumerate the **frontend implementation tasks** (Next.js/TypeScript) realising the UX designs:
component build, state management, API/WS integration, accessibility, and tests.

## Assumptions
- Next.js (App Router) + TypeScript; SSR for admin/auth surfaces, client-heavy for live; typed API
  client generated from `api-contracts.yaml`; WS client per Phase 15.
- Design-system tooling decided here (recommend a headless/utility approach + token layer); state via
  a lightweight store + server-cache lib; MSW for mocked tests.

## Functional Requirements
*(UI tasks by area.)*

### Foundation
- Project scaffolding (App Router, TS strict, lint/format), token theme (light/dark), base component
  library implementation (primitives), typed API client (codegen from OpenAPI), WS client wrapper
  (ticket fetch → connect → reconnect/backoff → event dispatch), error→toast/banner mapping, auth/session
  store + route guards (role-aware).

### FE1 Auth & shell
- Login/change-pwd pages; role-aware layout + nav; protected routes; 401/lock handling.

### FE2 Platform Console
- Org table (cursor pagination), create/suspend dialogs, settings/usage views.

### FE3 Org Console — Users & import
- User table + create; **BulkImportPanel** (upload, parse feedback, per-row results, OTP copy/CSV download).

### FE4 Contest Builder
- Builder shell (tabs + lifecycle gating); structure/groups editor; **ConfigBlockForm** (mode-driven
  field visibility, range validation mirroring backend); wildcard/elimination editors; QuestionEditor
  (options, exactly-one-correct UX); LifecycleControl (legal-next only); optimistic-concurrency banner.

### FE5 Registration & lobby
- Contest browse/detail; register/withdraw; lobby countdown (to `scheduled_start_at`); state-gated CTAs.

### FE6 Participant Live App (critical)
- WS lifecycle (ticket→connect→subscribe→reconnect); `QuestionCard`/`OptionButton`; `AnswerAck`
  (pending/accepted/rejected, never false-accept); authoritative `Countdown` (snap-to-server);
  `WildcardBar`; `LeaderboardList` (4 visibility modes incl. masked); `ReconnectBanner`;
  `WaitingForHost`; `EliminationNotice` → spectator (controls removed); result view; aria-live region.

### FE7 Moderator Console
- Live dashboard; reveal button; advance override (confirm modal); presence + take-over affordance;
  live count; leaderboard; elimination feed; "you are host" indicator.

### FE8/FE9 Results & notifications
- Results dashboard + breakdown + export download; notifications list/ack + unread badge.

### Cross-cutting UI
- Accessibility implementation (keyboard, focus, aria-live, contrast, 44px targets, reduced-motion);
  responsive layouts; loading/empty/error/disconnected states; analytics hooks (optional).

## Non-functional Requirements
- Type-safe end-to-end (generated client + WS types); no business logic duplicated (UI reflects server).
- Perceived perf: live interactive ≤2s mid-tier mobile/3G; skeletons >300ms.
- Tests: component (RTL), integration (MSW vs OpenAPI), e2e (Playwright) for critical participant/moderator
  flows; a11y tests (axe).

## Edge Cases
- Ack-after-advance history; timer/server reconciliation; masked tie; spectator no-submit; builder lock
  on concurrent change; large OTP list virtualization.

## Future Considerations
- Tenant theming; i18n/RTL; PWA offline answer queue; component telemetry.

## Risks
- **WS client complexity (reconnect/ordering)** → robust wrapper with tests. **Two-posture duplication**
  → shared component library. **Client/server timer drift** → authoritative snap, e2e-tested.

## Deliverables
- **D1** Frontend foundation tasks (scaffold, tokens, components, typed API/WS clients, auth store).
- **D2** Per-surface UI task lists (FE1–FE9).
- **D3** Critical live-UI tasks (FE6/FE7) with ack/timer/reconnect/masked tests.
- **D4** A11y + test (RTL/MSW/Playwright/axe) task set.
- **D5** Decision: design-system tooling (recommend headless + tokens) — confirm in implementation.

---
> **Next phase:** Phase 13 — Database Design.
