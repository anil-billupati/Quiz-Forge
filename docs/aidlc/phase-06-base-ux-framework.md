# ContestForge — AIDLC Phase 6: Base UX Framework

| | |
|---|---|
| **Phase** | 6 of 25 — Base UX Framework |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Source** | Phase 1 (Personas), Phase 3 (Use Cases), Phase 4 (Data Flows), Phase 5 (Architecture) |
| **Depends on** | Phase 5 (Architecture) — approved |
| **Feeds** | Phase 11 (UX Tasks), Phase 12 (UI Tasks), Phase 18 (Error Handling — UX side) |

---

## Goal
Establish the **foundational UX system** — not screens — that every later UI builds on: the surface
map (which apps exist for which personas), information architecture & navigation, the responsive +
accessibility-first framework, the design-token/theming foundation, the base component library, and
the **interaction & feedback patterns** specific to a real-time, server-authoritative, high-stakes
contest (answer acknowledgement, reconnect, "waiting for host", leaderboard visibility modes). Detailed
screens/flows are Phase 12 (UI Tasks); this phase fixes the rules they must follow.

## Assumptions
- **Web only** (no native mobile); **Next.js + TypeScript** frontend (Phase 5 Role A consumer).
- **Two posture archetypes:** participant/live = **mobile-first**, touch, flaky networks; admin/
  moderator = **desktop-first**, dense, keyboard-driven. Both must remain usable on the other form
  factor (responsive, not separate codebases).
- **Accessibility-first = WCAG 2.1 AA** is a baseline requirement, not a later pass.
- Server is authoritative for all timing/scoring; **UI timers and ranks are presentational only** and
  must visibly reconcile to server truth (never the reverse).
- English-only v1 (no i18n), but copy is centralised so i18n is a later swap, not a rewrite.
- Design system is **token-driven** and framework-pragmatic (e.g. a headless/utility approach) so it
  can theme per tenant later without re-architecture.

## Functional Requirements
*(The base UX framework — this phase's substance.)*

### 6.1 Surface map (apps per persona)
| Surface | Persona | Posture | Rendering (Next.js) | Purpose |
|---|---|---|---|---|
| **Platform Console** | Super Admin (P1) | Desktop | SSR (auth-gated) | Orgs, suspend/reactivate, limits, usage |
| **Org Console / Builder** | Org Admin (P2) | Desktop | SSR + client forms | Users/import, contest authoring, config, questions, lifecycle, results |
| **Moderator Console** | Moderator (P3) | Desktop | Client-heavy (live WS) | Reveal, advance, monitor; auto-pause/resume |
| **Participant Live App** | Participant (P4)/Spectator (P5) | **Mobile-first** | Client-heavy (live WS) | Register, join, answer, wildcards, leaderboard, reconnect, spectator |
| **Auth surface** | all | both | SSR | Login, change password, first-login |

Shared shell, distinct navigation per surface; one design system across all. *Trace:* personas P1–P5;
UC-1..15.

### 6.2 Information architecture & navigation
- **Role-aware shell:** after login the JWT role determines which surface and nav the user lands on;
  no cross-surface leakage (Super Admin never sees a tenant's contest nav — matches Phase 5 isolation).
- **Org Console IA:** `Contests` (list → builder tabs: Overview · Structure/Groups · Configuration ·
  Questions · Registrations · Lifecycle · Results) · `Users` (list + bulk import) · `Audit`.
- **Builder as a stepper + tabs hybrid:** lifecycle stage gates what's editable (Draft = all; after
  `REGISTRATION_OPEN` = config locked, read-only with clear lock affordances). The UI mirrors the
  state machine, never offering an illegal transition.
- **Participant IA (minimal, focus-first):** `My Contests` → `Lobby` (registered, countdown) → `Live`
  (single-question focus) → `Result`. Live view is deliberately shallow (no nested nav) to reduce
  cognitive load under time pressure.
- **Moderator IA:** single live dashboard (current question, controls, presence, leaderboard,
  elimination feed) — one screen, no drilling during a live event.
*Trace:* UC-3/7/8/13; lifecycle BR-5.

### 6.3 Responsive & layout framework
- **Breakpoints (mobile-first):** `base <640` · `sm 640` · `md 768` · `lg 1024` · `xl 1280`. Participant
  designed at `base`; admin/moderator at `lg+` with graceful `md` fallback.
- **Grid:** 4-col (mobile) / 12-col (desktop) fluid grid; max content width for admin tables; live
  participant view is single-column, thumb-reachable primary action (answer/submit) in the bottom 1/3.
- **Density modes:** comfortable (participant) vs compact (admin tables) as a token set.

### 6.4 Design tokens & theming
- **Token tiers:** primitive (palette, spacing scale, radius, type scale, z-index) → semantic
  (`color.bg.surface`, `color.intent.success|warn|danger|info`, `state.timer.normal|urgent`) →
  component. Tenant theming later overrides **semantic** tokens only.
- **Typography:** one variable font; type scale tuned for glanceability on the live view (large
  question text, high-contrast option buttons).
- **Color & state intents:** success (answer accepted), danger (rejected/eliminated), warn (window
  closing/urgent timer), info (waiting/spectator). All intents pass AA contrast and **never rely on
  color alone** (icon + text).
- **Dark mode** as a token theme from day one (live views are often used in dimmed rooms).

### 6.5 Base component library (foundations, not screens)
- **Primitives:** Button, IconButton, Input, Select, Checkbox/Radio, Toggle, Badge, Tag, Tooltip,
  Modal/Dialog, Drawer, Toast/Notification, Tabs, Stepper, Table (sortable/paginated, cursor-based),
  Card, Avatar, Skeleton, Spinner, EmptyState, Banner/Alert, Pagination (cursor).
- **Domain components (live):** `QuestionCard`, `OptionButton` (selectable/disabled/correct/
  eliminated states), `Countdown` (presentational, reconciles to `submission_close_at`), `AnswerAck`
  (pending → accepted/rejected), `WildcardBar` (available/used/ineligible), `LeaderboardList`
  (full/masked/hidden modes, shared-rank rendering), `WaitingForHost` overlay, `EliminationNotice`,
  `ReconnectBanner`.
- **Domain components (admin):** `ConfigBlockForm` (mode-driven field visibility), `LifecycleControl`
  (only-legal-next-stage), `QuestionEditor`, `BulkImportPanel` (per-row result + OTP reveal/copy),
  `RegistrationTable`, `ResultsExport`.
*Trace:* UC-2/4/5/8/9/11; FR-32 (visibility), FR-26 (wildcards).

### 6.6 Interaction & feedback patterns (the high-stakes core)
- **Answer acknowledgement (UC-9):** the single most important pattern. On submit: optimistic
  "submitting…" → on `answer.ack` show **accepted** (clear, persistent) or **rejected** with reason
  (`window_closed`, `eliminated`). The UI **never claims accepted without the server ack**; a pending
  ack that resolves late still flips to accepted (no silent loss). Re-submit is idempotent-safe.
- **Server-authoritative timer:** `Countdown` renders from `submission_close_at`; on reconnect or drift
  it **snaps to server truth** and may show "syncing". Visual urgency state in the last N seconds; the
  timer never *grants* time the server won't honour.
- **Reconnect (UC-7/A1, NFR-7):** non-blocking `ReconnectBanner` ("reconnecting…"); on restore, state
  snapshot (current question, window, my score) re-renders within ≤3s; in-flight answer state restored.
- **Waiting for host (OI-1):** when `host_present=false` in Moderator-Controlled mode, participants see
  a calm `WaitingForHost` overlay (not an error); it clears automatically on resume. Moderator/Org-Admin
  surfaces show a prominent "you are the host / take over reveal" affordance.
- **Leaderboard visibility (FR-32):** one component, four modes — Always, Post-question (revealed after
  window), Hidden, Masked (own rank only). Mode is server-driven; the client cannot reveal a hidden board.
- **Elimination & spectator (UC-11):** `EliminationNotice` with final rank/score and a clear transition
  to **view-only spectator** (controls removed, not merely disabled, to avoid false affordance).
- **Optimistic vs authoritative:** optimistic UI only for non-scoring affordances (selection
  highlight); anything that affects score waits for server confirmation.

### 6.7 Accessibility framework (WCAG 2.1 AA)
- Full **keyboard operability** (answer selection/submit, moderator controls, builder forms); visible
  focus states; logical tab order.
- **Screen-reader support:** semantic landmarks; `aria-live` for the live region (new question, ack
  result, timer-urgent, elimination) — announcements are throttled to avoid overwhelming.
- **Contrast AA** for text and UI state; **never color-only** signalling; respect
  `prefers-reduced-motion` (timer/leaderboard animations degrade gracefully).
- **Targets:** ≥44px touch targets on the participant app; option buttons large and well-spaced.
- **Timing:** WCAG "Timing Adjustable" is in tension with timed contests — documented as an *essential
  exception* (the timed nature is intrinsic), but everything non-essential is untimed and the timer is
  perceivable via text + ARIA, not color alone.

### 6.8 Content, empty, loading & error states
- Centralised **copy/message catalogue** (i18n-ready), including all server error codes mapped to
  human messages (feeds Phase 18).
- Every data surface defines **loading (skeleton), empty, and error** states; live views additionally
  define **disconnected** and **waiting-for-host** states.
- Error surfacing tiers: inline field (422 validation) · banner (409 state conflict, e.g. config
  locked) · toast (transient) · full-screen (auth/connection loss).

## Non-functional Requirements
- **Accessibility:** WCAG 2.1 AA across all surfaces (auditable per component).
- **Performance (perceived):** live view interactive ≤2s on mid-tier mobile/3G; question render and
  ack feedback feel instant; skeletons for any >300ms load.
- **Resilience UX:** every live pattern has a defined degraded state (offline, reconnecting, waiting,
  syncing) — no dead-ends, no false "accepted".
- **Consistency:** one token system + component library across all surfaces; tenant theming via
  semantic tokens only.
- **Maintainability:** components are presentational + prop-driven; server truth flows down, events
  flow up; no business rules duplicated in the UI (it reflects, not decides).

## Edge Cases
- **Ack arrives after the question advanced:** UI still records the prior question's accepted state in
  history; current question unaffected.
- **Timer shows time left but server has closed:** on the next tick/ack the UI reconciles to
  `window_closed`; selection is locked.
- **Masked board with a tie:** participant sees only their own (possibly shared) rank; never the full
  ordering.
- **Spectator on a flaky link:** spectator view degrades to read-only snapshots; no submit affordance
  ever reappears.
- **Builder open when contest auto-transitions** (another admin advanced it / auto-go-live): UI detects
  the state change and locks/refreshes rather than allowing a now-illegal edit (optimistic-concurrency
  surfaced as a banner).
- **Bulk import returns 4,000 OTPs:** panel must paginate/scroll, allow CSV download of results, and not
  freeze; OTPs are copy-once with a security note.
- **Reduced-motion users:** leaderboard re-ordering and urgency pulse use non-motion cues.

## Future Considerations
- **Per-tenant white-label theming** (semantic-token overrides, custom logo/domain) — foundation laid.
- **Internationalisation/RTL** — copy catalogue centralised now to enable later.
- **Native/PWA participant app** if mobile leaves out-of-scope (offline answer queueing).
- **Spectator-only public view** styling variant.
- **Accessibility AAA / enhanced low-vision** modes for inclusive contests.
- **Component analytics/telemetry** for UX research.

## Risks
- **False "accepted" feedback:** the worst failure — a participant believing a lost answer counted.
  *Mitigation:* ack pattern (6.6) forbids claiming accepted without server confirmation; covered by
  Phase 20 UX tests.
- **Timer-trust drift:** users trusting a client timer the server won't honour. *Mitigation:* timer is
  presentational, snaps to server truth, urgency shown honestly.
- **Accessibility-vs-timing tension:** timed contests conflict with WCAG timing guidance. *Mitigation:*
  documented essential exception + perceivable, non-color timer cues; non-essential timeouts removed.
- **Two-posture sprawl:** building effectively two front-ends (mobile live vs desktop admin) risks
  duplication. *Mitigation:* one design system/token set, shared primitives, surface-specific
  composition only.
- **Over-designing the builder:** the config block is complex; a heavy UI could overwhelm. *Mitigation:*
  mode-driven progressive disclosure (only show fields relevant to the chosen Mode).

## Deliverables
### D1 — Surface map & navigation model
5 surfaces (6.1), role-aware shell, per-surface IA (6.2) mirroring the lifecycle state machine.

### D2 — Responsive + token foundation
Breakpoints, grid, density modes (6.3); three-tier design tokens incl. dark mode and state intents
(6.4); tenant theming via semantic tokens only.

### D3 — Base component library spec
Primitives + live-domain + admin-domain components (6.5), each with defined states (default/disabled/
error/loading/empty and live-specific accepted/rejected/eliminated/masked/waiting).

### D4 — Interaction & feedback pattern catalogue
Answer ack, authoritative timer, reconnect, waiting-for-host, leaderboard-visibility, elimination/
spectator, optimistic-vs-authoritative rules (6.6) — the contract for all live UI.

### D5 — Accessibility framework
WCAG 2.1 AA checklist per component, keyboard/SR/contrast/targets/reduced-motion rules, and the
documented timing exception (6.7).

### D6 — State & content framework
Loading/empty/error/disconnected/waiting state requirements + centralised i18n-ready message catalogue
mapping server error codes to copy (6.8) — feeds Phase 18.

### D7 — Open questions carried forward
1. Design-system tooling choice (headless lib vs in-house) → Phase 12.
2. Exact tenant-theming scope for v1 (logo only vs palette) → product decision.
3. Spectator feature scope (which views) — still open from Phase 3.

---

> **Next phase (await approval):** Phase 7 — Base Backend Framework. Do not generate until approved.
