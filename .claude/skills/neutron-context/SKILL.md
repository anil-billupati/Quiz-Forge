---
name: neutron-context
description: Apply at the start of any session on an existing project
             — when CLAUDE.md is present and the project has been
             previously initialised. Read project state before taking
             any action. Do not act without context.
model: sonnet
version: 1.0.0
---

# Neutron Context

## What this skill enforces
That the AI always understands the current state of a project before
acting. No implementation, review, or decision proceeds without reading
the project's existing context — spec, delivery plan, ADRs, and
CLAUDE.md — first.

## When this skill applies
At the start of any session where:
- CLAUDE.md is present at the repo root
- The project has existing docs (kickoff, spec, plan, or ADRs)
- A command is about to be run on an existing project
- A question is asked about the project's state or history

## When this skill does not apply
- When running `/neutron:kickoff` on a brand new project with no
  existing docs — there is no context to read yet
- When answering a general engineering question unrelated to the
  current project state

## Rules

1. Before any action on an existing project, read in this order:

   **If `docs/context-summary.md` exists:**
   - `CLAUDE.md` — project identity, type, stack, active skills
   - `docs/context-summary.md` — compressed project history,
     key decisions, current state, recent activity
   - `docs/plan/delivery-plan.md` — delivery unit status

   **If `docs/context-summary.md` does not exist:**
   - `CLAUDE.md` — project identity, type, stack, active skills
   - `docs/plan/delivery-plan.md` — what has been built, what remains
   - `docs/decisions.md` — medium and high significance entries only.
     Skip entries with `significance: low`
   - `docs/adr/` — titles and status first, full content for
     accepted ADRs only
   - `docs/session-log.md` — last 3 sessions only, not the full file

2. Read the relevant spec section before any implementation:
   - `docs/spec/technical-spec.md` for implementation tasks
   - `docs/spec/api-contracts.yaml` for API work
   - `docs/spec/domain-model.md` for business logic or data work
   - Check `## Amendments` section of each spec document for
     deviations that postdate the original spec

3. Read `.neutron/security.md` before any work involving auth,
   data handling, compliance, or sensitive data.

4. Read `.neutron/integrations.md` before any work involving
   external systems, APIs, queues, or data stores.

5. If a required context file is missing, surface it immediately:
   state which file is missing and which command generates it.
   Do not proceed by guessing at missing context.

6. If `docs/session-log.md` exceeds 500 lines and no
   `docs/context-summary.md` exists, recommend running
   `/neutron:checkpoint` before proceeding. Do not block — warn once.

7. After reading context, produce a one-paragraph summary of the
   project's current state before acting. This confirms the AI
   has the right context and gives the engineer a chance to correct
   any misunderstanding before work begins.

8. Never assume the current session continues from a previous one.
   Each session is independent. Always reload context from files.
