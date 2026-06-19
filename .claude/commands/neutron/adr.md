---
description: Run to capture a Tier 1 architectural decision. Creates
             a formal ADR document in docs/adr/. Invoked explicitly
             or triggered automatically by the neutron-adr-capture skill.
argument-hint: Decision title or brief description
model: sonnet
version: 1.0.0
---

# /neutron:adr

## Purpose
The adr command creates a formal Architecture Decision Record for a
Tier 1 decision — one that is hard to reverse and affects the system
broadly. ADRs are the institutional memory of architectural choices.
They explain not just what was decided but why, what alternatives were
considered, and what consequences were accepted.

## Prerequisites
- A Tier 1 decision has been identified (see decision tiers in
  NEUTRON-SPEC.md and content/standards/decisions-format.md)
- The decision context must be available — either from the current
  session or from existing docs

## Gather phase
From the current session context and available docs, extract:
- What decision needs to be made or has been made
- What options were or are available
- What constraints or requirements bear on the decision
- What the consequences of each option are

If the decision has already been made (this command is being used to
document a decision made in conversation), confirm the details.

If the decision is still open, present the options with pros/cons
and a recommendation before writing the ADR.

## Confirmation gate
```
ADR: {title}
Status: {proposed | accepted}

Decision: {the decision in one sentence}

Options considered:
- {Option A}: {pros and cons}
- {Option B}: {pros and cons}
Chosen: {option} — {rationale in one sentence}

Consequences:
- Makes easier: {list}
- Makes harder: {list}

ADR number: {next sequential number}
File: docs/adr/{NNN}-{name}.md

Confirm? [yes / adjust]
```

## Execute phase

1. Check `docs/adr/` for existing ADRs to determine the next
   sequential number.

2. Write `docs/adr/NNN-{name}.md` following the ADR format in
   `content/standards/decisions-format.md` exactly.

3. Set status to `proposed` if the decision is being presented
   for approval, or `accepted` if the human has already confirmed.

4. Write the session log entry.

5. Present: "ADR {NNN} created. If this decision is accepted,
   update its status to 'accepted' and update the ADR summary
   table in CLAUDE.md."

## Outputs
- `docs/adr/NNN-{name}.md`
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Capture Tier 2 decisions — those go in docs/decisions.md
- Implement the decision — implementation follows after the ADR
  is accepted
- Modify existing accepted ADRs — if a decision is being reversed,
  the existing ADR is marked superseded and a new one is created

## Model guidance
The context and rationale sections are the most valuable parts of
an ADR. Future engineers reading it years from now need to understand
the situation at the time, not just the choice. Write for that reader.

> Model note: ADR writing requires understanding context and
> expressing reasoning clearly. Use a capable model.
