# ContestForge — Project Kickoff

| | |
|---|---|
| **Project** | ContestForge |
| **Type** | Full-stack platform |
| **Backend service pattern** | Hybrid (HTTP service + worker) |
| **Date** | 2026-06-19 |
| **Neutron version** | 1.0 |
| **Status** | Approved |

---

## 1. Project Identity

- **Name:** ContestForge
- **Type:** Full-stack platform (backend service + web frontend)
- **Service pattern (backend):** Hybrid — an HTTP/WebSocket API service for
  contest administration and live participation, plus background workers for
  the server-authoritative Execution, Scoring, Leaderboard, and Elimination
  engines.
- **Stack:**
  - Backend: Python + FastAPI
  - Frontend: Next.js + TypeScript
  - Data stores: PostgreSQL (multi-tenant system of record), Redis
    (leaderboards, cache, real-time fan-out)
  - Real-time: WebSockets for live question delivery and leaderboard push
- **Cloud:** AWS

---

## 2. Problem Statement

ContestForge is a multi-tenant live contest/quiz engine. Organizations need to
run timed competitive quizzes at scale (up to 10,000+ concurrent participants)
with strict integrity guarantees: no submitted answer is ever lost, scoring is
server-authoritative and at-most-once, and contest state is reconstructible
after partial failure.

The platform must support three contest **Modes** — Standard (fixed scoring),
Speed (time-based scoring), and Elimination (fixed scoring with knockout
rules) — applied to two **Structures** — Normal (one configuration for the
whole quiz) and Grouped (per-group configuration run in sequence). Supporting
engines cover Execution (timing/progression), Scoring, Wildcards, Leaderboards,
and Elimination.

**Multi-tenancy is required from day one.** A super admin can create
organizations; a tenant table isolates each organization's data. Org-level
admins and moderators build and operate contests within their tenant.

---

## 3. Users & Key Workflows

| User type | Key workflows |
|---|---|
| **Super Admin** | Create and manage organizations (tenants); platform-wide administration. |
| **Org Admin** | Configure contests (structure, modes, scoring, wildcards, elimination rules); manage participants and lifecycle (Draft → Archived). |
| **Moderator** | Control reveal timing and progression during a Live contest (Moderator-Controlled reveal mode); issue overrides to advance. |
| **Participant** | Register for a contest, compete live, submit answers within server-side windows, activate wildcards, view leaderboards and results. |

---

## 4. Goals — What Success Looks Like

- Contest Mode (Standard / Speed / Elimination) applies correctly to both
  Normal and Grouped structures, with the correct scoring model per mode in
  100% of regression cases.
- Server-authoritative timing: questions delivered within 200ms of scheduled
  reveal at up to 10,000 concurrent users; timer accuracy within ±50ms over a
  5-minute session.
- Durability guarantees met: zero answer loss across 10,000 submissions with a
  1% induced persistence-failure rate; at-most-once scoring; contest recovery
  within 30s of a simulated crash; reconnection restored within 3s.
- Leaderboard updates pushed within 500ms (≤5,000 users) and within 2s at peak
  load (≤20,000).
- Strict tenant data isolation enforced from the first release.

---

## 5. Constraints

- **Technical:**
  - All timing, scoring, and ranking computed server-side; client clocks are
    display-only and never authoritative.
  - Answers submitted after the server-side close time are rejected regardless
    of client clock.
  - Multi-tenancy and the organization/tenant model are foundational, not a
    later addition.
- **Scale/NFR:** Up to 10,000 concurrent users (20,000 at peak for leaderboard
  push targets); see Goals for latency/accuracy targets.
- **Timeline:** Not yet defined — open question.
- **Budget:** Not yet defined — open question.

---

## 6. Integrations

- **PostgreSQL** — authoritative multi-tenant data store (tenants, contests,
  configuration blocks, participants, answers, results).
- **Redis** — leaderboard computation/cache and real-time fan-out; must be
  recoverable from authoritative data (cache loss must not change any score or
  rank).
- **WebSockets** — live question delivery and leaderboard/elimination push to
  participants.

No external third-party APIs identified at kickoff.

---

## 7. Compliance Requirements

**None stated.**

> **Open question:** ContestForge is a multi-tenant SaaS holding participant
> personal data and is classified Confidential. Compliance regimes such as
> SOC 2 and GDPR are commonly required for this profile. Recorded as "none"
> per current input; to be confirmed with stakeholders before architecture
> finalisation in /neutron:plan.

---

## 8. Team

- **Team name:** contest
- **Project lead:** Hussain
- **Key stakeholders:** Product Team, ContestForge (per PRD)

---

## 9. Open Questions

1. **Compliance** — Confirm whether SOC 2 / GDPR (or other regimes) apply
   given multi-tenant participant data. Currently recorded as "none".
2. **Timeline** — No delivery dates or milestones provided.
3. **Budget** — Not specified.
4. **Tenant isolation strategy** — Shared-schema-with-tenant-id vs.
   schema-per-tenant vs. database-per-tenant; to be decided in /neutron:plan.
5. **AWS region(s) and environments** — To be determined in /neutron:plan.

---

## 10. Source Artifacts

- `ContestForge_PRD_v1.md` — Core Contest Engine PRD v2.3 (includes AIDLC flow
  intent and multi-tenancy/organization/super-admin/tenant-table directives).
