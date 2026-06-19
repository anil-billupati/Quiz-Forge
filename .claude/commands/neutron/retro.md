---
description: Run at the end of a sprint, milestone, or significant
             delivery phase. Reviews what was shipped, what was learned,
             and what should improve. Identifies pattern library
             candidates from the project's decisions and bugs.
argument-hint: Optional — milestone or sprint name
model: sonnet
version: 1.0.0
---

# /neutron:retro

## Purpose
The retro command closes a delivery phase with reflection. It synthesises
the session log, decisions, bug records, and ADRs into a structured
retrospective and identifies reusable patterns for the Fission pattern
library. The retro is how individual project learning becomes
organisational knowledge.

## Prerequisites
- At least one complete delivery unit or milestone must exist
- `docs/session-log.md` should have entries from the period being reviewed
- `docs/decisions.md` should be current

## Gather phase
Read:
1. `docs/session-log.md` — sessions from the period being reviewed
2. `docs/decisions.md` — decisions made during the period
3. `docs/bugs/` — bug records from the period
4. `docs/adr/` — ADRs created or changed during the period
5. `docs/plan/delivery-plan.md` — units completed vs planned

Identify:
- What was delivered vs what was planned — accuracy of estimates
- Decisions that proved correct and why
- Decisions that proved incorrect and what the actual outcome was
- Bugs that revealed systemic issues
- Patterns used that were effective and reusable
- Friction points — what slowed the team down

No questions required if the above documents are present. Proceed
to the retro output directly.

## Confirmation gate
Not applicable. The retro command produces a document and pattern
candidates — no approval gate before writing.

## Execute phase

1. Write `docs/retro/{YYYY-MM}-{milestone-name}.md` containing:

   **What was delivered**
   Units completed. Comparison to what was planned. Honest assessment
   of accuracy.

   **What went well**
   Specific decisions, patterns, or practices that worked. Concrete
   examples from the session log and decisions.

   **What did not go well**
   Specific friction points. Undocumented surprises. Bugs that
   revealed design gaps. Decisions that had to be revisited.

   **Decisions reviewed**
   Brief assessment of Tier 1 and Tier 2 decisions made — which
   held up, which should be reconsidered.

   **Pattern library candidates**
   Specific patterns, approaches, or solutions from this project
   that are reusable across other Fission projects. For each:
   - What the pattern is
   - When to use it
   - The implementation approach
   - Reference to where it was used in this project

   **Improvements for next phase**
   Specific, actionable changes to process, conventions, or tooling.
   Not vague — each improvement has an owner and a definition of done.

2. For each pattern library candidate, create a candidate entry in
   `docs/patterns/` (project-local staging area, not the Neutron
   pattern library). Flag for AO Office review for inclusion in
   Neutron's `patterns/` directory.

3. Update `CLAUDE.md` — set `last-updated` date and update any
   delivery status rows that changed during this phase.

4. Write the session log entry.

## Outputs
- `docs/retro/{YYYY-MM}-{milestone}.md`
- `docs/patterns/` candidates (if patterns identified)
- `CLAUDE.md` (last-updated, delivery status)
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Make changes to the codebase
- Add patterns directly to the Neutron pattern library —
  that requires AO Office review
- Plan the next sprint or milestone — that is a separate activity

## Model guidance
The retrospective is most valuable when it is honest and specific.
Vague positives ("the team communicated well") and vague negatives
("estimation was hard") are not useful. Ground every observation in
specific examples from the session log and decision records.

> Model note: Synthesis across multiple documents into honest,
> specific observations requires careful reasoning. Use a capable model.
