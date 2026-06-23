# ContestForge — AIDLC Phase 1: User Personas

| | |
|---|---|
| **Phase** | 1 of 25 — User Personas |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Source** | docs/spec/product-spec.md, technical-spec.md, domain-model.md, api-contracts.{md,yaml}, ContestForge_PRD_v1.md |
| **Depends on** | (none — first phase) |
| **Feeds** | Phase 2 (User Stories), Phase 17 (Security/RBAC), Phase 6 (UX) |

---

## Goal
Establish the **canonical set of user personas** for ContestForge so that every later
phase (user stories, use cases, UX, API surface, RBAC) traces back to a real human with
explicit goals, context, and constraints. The persona set must map cleanly onto the four
system roles (`SUPER_ADMIN`, `ORG_ADMIN`, `MODERATOR`, `PARTICIPANT`) defined in
product-spec §2.5, while surfacing **sub-archetypes and secondary actors** the role model
alone hides (e.g. the eliminated-but-watching participant, the on-call operator). The
output is a decision-making lens, not decoration: each persona carries the goals,
frustrations, environment, and success metrics that constrain design.

## Assumptions
- The role model is fixed (four roles); personas refine, not redefine, it. Cross-tenant
  access is impossible, so every tenant-scoped persona lives inside exactly one organization.
- **No public self-signup.** Participants exist because an Org Admin created or CSV-imported
  them; they receive credentials out-of-band (no email delivery in v1).
- Web client only (no native mobile), but participants are assumed to be **predominantly on
  mobile browsers** over variable networks — this drives mobile-first, reconnect-tolerant UX.
- Contests are **time-bound, high-stakes-feeling, synchronous events** (hiring rounds,
  certifications, competitions): the participant's emotional state during Live is "stressed,
  time-pressured, intolerant of latency or ambiguity."
- A single human can hold different roles in different tenants (separate accounts); within
  one tenant, role is singular per account.
- English-only UI in v1 (i18n out of scope), but accessibility (WCAG 2.1 AA) is in scope by
  our "accessibility-first" principle.
- Scale per persona context: a Participant may be 1 of up to 10,000 concurrent; an Org Admin
  may run several contests but rarely operates one live themselves.

## Functional Requirements
*(What the system must do, framed as each persona's core capability needs — the demand side
that later phases must satisfy.)*

**P1 — Super Admin ("Priya, Platform Operator")**
- Provision/suspend/reactivate organizations; assign the initial Org Admin; set tenant
  resource limits; view platform-wide usage. Operates above tenants, **cannot run or see
  inside contests**, cannot impersonate tenant users.

**P2 — Org Admin ("Hassan, Contest Owner/Author")** — *the heaviest authoring persona*
- Create contests (Normal/Grouped); author groups, configuration blocks, questions/options;
  manage the lifecycle up to (but not the automatic part of) going Live; **create
  participants individually or bulk-import via CSV**; view results, exports, wildcard/
  elimination audits.

**P3 — Moderator ("Maria, Live Show-Runner")** — *operates under time pressure, live*
- Drive a Live contest in Moderator-Controlled reveal mode: reveal each question, override
  progression (question/group), and monitor live participant count, leaderboard, and
  elimination events. Read-only on authoring.

**P4 — Participant ("Arjun, Competitor")** — *the highest-volume, lowest-tolerance persona*
- Register during Registration Open; join Live; receive questions inside the authoritative
  window; submit answers with a clear accept/reject ack; activate the three wildcards where
  eligible; view leaderboard per configured visibility; **reconnect without losing state or
  their open window**.

**P5 — Eliminated Participant / Spectator ("Arjun, after the cut")**
- Receive a clear elimination notification with final rank/score; optionally retain
  **view-only spectator access** to later groups; understand *why* they were eliminated.

**P6 — Platform SRE / On-Call ("Sam, Reliability Engineer")** *(secondary, operational)*
- Observe contest health (reveal latency, scoring lag, queue depth, WS connections), confirm
  durability/recovery guarantees, and act on NFR-breach alerts. Consumes observability
  surfaces, not the product UI.

## Non-functional Requirements
*(Persona-derived quality expectations that bind later phases.)*
- **Participant (P4/P5):** perceived instant feedback — question appears ≤200 ms after reveal
  (NFR-1), answer ack feels immediate, reconnect restores state ≤3 s (NFR-7). Mobile-first,
  one-handed, high-contrast, works on flaky 3G/4G. Zero tolerance for "did my answer count?"
  ambiguity → ack semantics must be visceral, not subtle.
- **Moderator (P3):** live console updates in near-real-time (≤500 ms leaderboard push,
  NFR-3), controls **hard to misfire** (advancing a group is irreversible-ish) with immediate
  confirmation. Desktop-first (operator at a workstation).
- **Org Admin (P2):** authoring is correctness-critical, not latency-critical — strong inline
  validation (mode↔scoring coupling, elimination requires rules, duration ranges) prevents
  publishing a broken contest. Desktop-first; tolerates multi-step flows. CSV import reports
  per-row outcomes clearly.
- **Super Admin (P1):** low-frequency, high-privilege — clarity and auditability over speed;
  every action logged.
- **Cross-cutting:** WCAG 2.1 AA, keyboard navigability, screen-reader support; tenant
  isolation must be invisible-but-absolute (a persona must *never* perceive another tenant).

## Edge Cases
- **Multi-role human:** the same person is an Org Admin in tenant A and a Participant in
  tenant B (separate accounts) — personas must not assume one human = one role; login carries
  tenant scope.
- **Org Admin acting as Moderator:** the matrix lets Org Admin perform live control. The
  "author" and "show-runner" personas can collapse into one human for small orgs — UX must
  serve both without forcing role-switching friction.
- **Participant created but never given credentials** (import succeeded, distribution failed)
  → a "provisioned but cannot log in" persona state.
- **Eliminated participant who keeps the socket open** (P5): must degrade to spectator
  cleanly, not error.
- **Super Admin temptation to "help" inside a tenant:** persona boundary must be enforced —
  no impersonation, no contest visibility — even when a tenant asks for support.
- **Moderator disconnects mid-Live:** who reveals the next question? (Surfaces a reliability
  requirement; auto-reveal fallback vs paused contest — to be resolved in execution phase,
  flagged here.)
- **Participant on a shared/locked-down kiosk** (exam-hall context) — no app install,
  web-only, possibly no reconnect ability.
- **Bulk import of 5,000 rows with 30% duplicates** — Org Admin needs partial-success
  ergonomics, not all-or-nothing failure.

## Future Considerations
- **Participant self-service onboarding** (invite links / join codes) if open registration is
  ever in scope — would add a new "self-registering participant" persona; deferred now by
  explicit decision.
- **Org-level Billing Admin / Finance persona** once usage metering becomes billing
  (`TenantUsageRecord` is the seed).
- **Dedicated Question Author / Content Reviewer** persona if authoring is split from
  operations (currently folded into Org Admin).
- **Auditor / Compliance reviewer** persona once SOC 2 / GDPR flows mature (read-only
  audit-log consumer).
- **Spectator-only / public viewer** persona if contests ever become publicly watchable
  (today spectator = eliminated participant only).
- **Native-mobile participant** persona when mobile apps leave out-of-scope.

## Risks
- **Persona collapse (Org Admin = Moderator = Author):** designing three distinct consoles for
  what is often one busy person risks over-engineering (violates KISS/YAGNI). *Mitigation:*
  treat P2/P3 as one human with two modes; don't force artificial separation.
- **Under-serving the Participant under stress:** designing from the admin's calm desktop
  viewpoint ships a participant experience that fails on mobile/flaky networks — the persona
  most numerous and least forgiving. *Mitigation:* participant journeys are first-class,
  tested on degraded networks.
- **Invisible operator persona (P6):** if SRE needs aren't treated as a persona, observability
  becomes an afterthought and NFR-5/6/9 (durability/recovery) can't be validated.
  *Mitigation:* P6 is in the canonical set.
- **Credential-distribution gap:** "no email delivery" pushes a real operational burden onto
  the Org Admin persona; if unacknowledged, onboarding fails silently at scale. *Mitigation:*
  bulk-import returns one-time passwords explicitly.
- **Accessibility deferral risk:** treating WCAG as "later" contradicts our accessibility-first
  principle and is costly to retrofit, especially the live timed views. *Mitigation:* bake
  into persona NFRs now.

## Deliverables

### D1 — Persona-to-role traceability
| Persona | Archetype | Mapped role | Device / context | Frequency |
|---|---|---|---|---|
| P1 | Platform Operator | `SUPER_ADMIN` | Desktop | Rare, high-privilege |
| P2 | Contest Owner/Author | `ORG_ADMIN` | Desktop | Recurring (pre-event) |
| P3 | Live Show-Runner | `MODERATOR` (or `ORG_ADMIN`) | Desktop console | Per live event |
| P4 | Competitor | `PARTICIPANT` | Mobile-first, flaky net | Per event, high-volume |
| P5 | Spectator (eliminated) | `PARTICIPANT` | Mobile-first | Per elimination |
| P6 | Reliability Engineer | operational (non-product) | Dashboards | Continuous / on-call |

### D2 — Per-persona profile fields (card schema for the design system)
Each persona card carries: **name/archetype · mapped role · goals · frustrations ·
environment (device/network/context) · proficiency · frequency · success metrics ·
accessibility needs.**

### D3 — Explicit persona boundaries (feed RBAC + security phases)
- Super Admin: platform-scoped; **no tenant entry, no impersonation, no contest visibility**.
- Moderator: live control only; **no authoring**.
- Eliminated participant: **view-only spectator**, never re-enters scoring.
- Participant: single tenant; cannot see other tenants or admin surfaces.

### D4 — Open persona questions logged for later phases
1. Moderator-disconnect fallback during Live (auto-reveal vs pause) → Phase 4/16 (execution).
2. Author vs operator console split for the collapsed P2/P3 human → Phase 6 (UX).
3. Kiosk/exam-hall participant constraints (no reconnect) → Phase 6/18 (live UX).

---

> **Next phase (await approval):** Phase 2 — User Stories. Do not generate until approved.
