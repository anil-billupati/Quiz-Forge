# ContestForge — AIDLC Phase 11: UX Tasks

| | |
|---|---|
| **Phase** | 11 of 25 — UX Tasks |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phase 6 (Base UX), Phase 8 (Features) |
| **Feeds** | Phase 12 (UI Tasks) |

---

## Goal
Enumerate the **UX design tasks** (flows, wireframes, interaction specs, content, a11y) that turn the
Phase-6 base framework into per-surface designs ready for UI implementation (Phase 12).

## Assumptions
- Design tasks precede their paired UI tasks; both gate "done" for a user-facing capability.
- Token system + component library (Phase 6) are the substrate; tasks compose, not re-invent.

## Functional Requirements
*(UX tasks by surface.)*

### UX-Foundation
- Finalise design tokens (palette, type scale, spacing, intents, dark mode) + component states.
- Build component-library specs (states: default/disabled/error/loading/empty + live variants).
- Define motion + reduced-motion variants; a11y checklist per component.
- Author the **message catalogue** (server error code → human copy), i18n-ready.

### Auth & shell (FE1)
- Login, change-password, first-login flows; role-aware landing + nav per surface; error states (401/locked).

### Platform Console (FE2 — Super Admin)
- Org list/create/suspend wireframes; settings + usage views; empty/permission states.

### Org Console — Users & import (FE3)
- User list/create flows; **bulk-import** flow: upload → per-row result → OTP reveal/copy/CSV-download
  (security note); partial-success UX.

### Contest Builder (FE4)
- Builder IA (tabs + lifecycle-gated editing); structure/groups step; **config block** progressive
  disclosure by Mode; wildcard + elimination config; question editor; lifecycle control (only-legal-next,
  lock affordances); validation/error inline patterns.

### Registration & lobby (FE5)
- Browse/register; lobby with countdown to `scheduled_start_at`; withdraw; full/closed states.

### Participant Live App (FE6) — highest-priority UX
- Question view (focus-first, large targets); option selection; **answer-ack** states (submitting →
  accepted/rejected+reason); authoritative **countdown** (urgency, syncing/snap); **wildcard bar**
  (available/used/ineligible); leaderboard (Always/Post-question/Hidden/Masked); **reconnect banner**;
  **waiting-for-host** overlay; **elimination → spectator** transition; result screen.

### Moderator Console (FE7)
- Single live dashboard: reveal control, advance override (confirm-to-prevent-misfire), presence +
  "you are host/take over", live count, leaderboard, elimination feed.

### Results & notifications (FE8/FE9)
- Results dashboard + export; per-participant breakdown; notifications list/ack UX.

## Non-functional Requirements
- Every flow defines loading/empty/error/disconnected states.
- WCAG 2.1 AA per surface (keyboard, SR/aria-live, contrast, targets, reduced-motion).
- Mobile-first for FE5/FE6; desktop-first for FE2/FE3/FE4/FE7.

## Edge Cases
- False-accepted prevention in ack flow; timer snap-to-server; masked-tie display; spectator no-submit;
  builder lock on concurrent state change; 4k-OTP import panel scroll/download.

## Future Considerations
- Tenant white-label theming flows; i18n/RTL; PWA/offline participant.

## Risks
- **Builder complexity overwhelm** → progressive disclosure by Mode. **Live-view cognitive load under
  pressure** → focus-first, minimal nav. **A11y-vs-timing** → documented essential exception (Phase 6).

## Deliverables
- **D1** Foundation UX tasks (tokens, components, motion, copy catalogue).
- **D2** Per-surface flow/wireframe/interaction-spec task lists (FE1–FE9).
- **D3** A11y task checklist per component/surface.
- **D4** Live interaction specs (ack, timer, reconnect, waiting-for-host, masked board) — design-side
  contract for FE6/FE7.

---
> **Next phase:** Phase 12 — UI Tasks.
