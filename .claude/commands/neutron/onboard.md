---
description: Run when a new engineer joins an existing project.
             Reads the project's current state and produces a
             structured briefing covering context, decisions,
             delivery status, and how to get started.
argument-hint: Optional — engineer name or specific area to focus on
model: sonnet
version: 1.0.0
---

# /neutron:onboard

## Purpose
The onboard command removes the friction of joining an existing
project mid-stream. Rather than an engineer spending days reading
docs to get context, this command synthesises the project's current
state into a structured briefing. It covers what the project is,
what decisions have been made, what has been built, what remains,
and how to get started contributing immediately.

## Prerequisites
- A project repo must exist and be open in the AI tool
- No other prerequisites — this command handles all states including
  projects with no Neutron docs at all

**Degraded mode:** If the project predates Neutron and has no
kickoff.md, delivery plan, or ADRs, this command switches to
adoption mode automatically. See Gather phase for full behaviour.

## Gather phase

First determine which mode applies by checking what exists:

**Standard mode** — CLAUDE.md and at least docs/kickoff.md exist:
Read in this order:
1. `CLAUDE.md` — project identity, type, stack, current status
2. `docs/context-summary.md` if it exists, otherwise:
   `docs/kickoff.md`, `docs/plan/delivery-plan.md`,
   `docs/decisions.md` (medium/high significance only),
   `docs/adr/` titles and accepted ADR content
3. `docs/session-log.md` — last 3 sessions only

No questions required. Proceed directly to briefing.

**Degraded mode** — project predates Neutron, minimal or no docs:
Detected when: CLAUDE.md is absent OR docs/kickoff.md is absent.

In degraded mode:
1. Read whatever exists — README.md, any docs/, existing code
   structure, package.json / pyproject.toml / pom.xml
2. Extract what can be inferred: project name, language, framework,
   rough purpose, entry points
3. Produce a partial briefing clearly marked as reconstructed
4. At the end of the briefing, present the adoption path:
   "This project predates Neutron. To adopt Neutron fully,
   follow the mid-project adoption path in USAGE.md."

## Confirmation gate
Not applicable. This command produces a briefing, not an artifact
requiring approval. Present the briefing directly.

## Execute phase

**Standard mode output:**
1. Produce a structured briefing:

   **Project overview**
   What this project is, what problem it solves, who uses it.

   **Current state**
   What phase the project is in. What has been built. What remains.
   Reference delivery plan units and their status.

   **Key decisions**
   Most important architectural and design decisions.
   Why they were made. Where to read full context.

   **How the codebase is organised**
   Top-level directory structure and what each part does.
   Where to find main entry points.

   **How to get started**
   Exact commands to clone, set up, and run locally.
   How to run tests.

   **What to work on next**
   Next incomplete unit from delivery plan.
   What context to read before starting it.

   **Who to ask**
   Project lead and team from CLAUDE.md.

**Degraded mode output:**
Produce the same briefing structure but mark each section with
its confidence level:
- `[FROM DOCS]` — derived from existing documentation
- `[INFERRED]` — inferred from code structure or config files
- `[UNKNOWN]` — could not be determined, needs clarification

End with:
```
## Adoption path
This project predates Neutron. Recommended next steps:
1. Run /neutron:kickoff in "current state" mode
2. Run /neutron:spec to reconstruct specifications
3. Follow the mid-project adoption path in USAGE.md
```

2. Write the session log entry noting which documents were read,
   which mode was used, and what was synthesised.

## Outputs
- Onboarding briefing (presented in session, not written to file)
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Make decisions or change any project artifacts
- Generate code or implementation
- Update CLAUDE.md or any project documentation
- Replace reading the spec for a new engineer — it supplements it

## Model guidance
Write the briefing for a competent engineer who is new to this
specific project, not new to engineering. Do not over-explain
general concepts. Focus on what is specific to this project —
the decisions made, the patterns used, the current state.

> Model note: This command requires synthesis across multiple
> documents into a coherent narrative. Use a capable model.
