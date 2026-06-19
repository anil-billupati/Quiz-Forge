---
description: Run to implement one unit from the delivery plan.
             Takes a specific unit name as argument. Reads the
             relevant spec sections and implements exactly what
             the unit describes — no more, no less.
argument-hint: Unit name from delivery-plan.md e.g. "Unit 3: User authentication"
model: sonnet
version: 1.0.0
---

# /neutron:feature

## Purpose
The feature command implements one delivery plan unit at a time.
It is the primary implementation command — the bridge between the
approved plan and working code. Each invocation is scoped to a
single unit. Implementation is grounded in the approved spec.
Tests and documentation are produced alongside implementation,
not after.

## Prerequisites
- `/neutron:init` must have been run — repo must be scaffolded
- `docs/plan/delivery-plan.md` must exist with the target unit defined
- All units this unit depends on must be marked complete
- Spec documents relevant to this unit must exist in `docs/spec/`
- The unit name must be passed as the command argument

## Gather phase
Read in this order:
1. The target unit definition from `docs/plan/delivery-plan.md`
2. The relevant sections of `docs/spec/technical-spec.md`
3. `docs/spec/api-contracts.md` if this unit involves API surfaces
4. `docs/spec/domain-model.md` if this unit involves entities or
   business logic
5. `docs/spec/testing-strategy.md` for testing approach
6. Existing code in the directories this unit will touch
7. `docs/adr/` for decisions relevant to this unit's domain
8. `docs/decisions.md` for recent design choices in this area

Identify gaps — things needed to implement this unit that the
above documents do not fully define:
- Spec is ambiguous about expected behaviour in a specific case
- A dependency unit's output does not match what this unit expects
- An external integration detail is missing from .neutron/integrations.md

For each gap, ask one focused question. Wait for the answer.

If the unit definition and relevant spec sections are complete,
proceed to confirmation.

## Confirmation gate
```
Implementing: {unit name}
Spec reference: {which spec sections this implements}

What will be built:
{bullet list of specific deliverables from the unit definition}

Done when:
{the unit's completion criteria from delivery-plan.md}

Will create/modify:
{list of files that will be created or modified}

Tests to be written:
{list of test scenarios based on spec and unit definition}

Gaps resolved in this session:
{list or "none"}

Confirm? [yes / adjust]
```

## Execute phase

1. Implement the unit's deliverables in this order:
   a. Domain/business logic layer first — entities, rules, services
   b. Infrastructure/data layer — repositories, external adapters
   c. API/interface layer — handlers, controllers, routes
   d. Tests for each layer as it is built — not at the end

2. For each file created or modified:
   - Follow the project's naming conventions from CLAUDE.md
   - Follow the Fission engineering standard
   - Write tests in the same step as the implementation

3. Run neutron-spec-adherence check before presenting output:
   - Does the implementation match the spec's described behaviour?
   - Are all specified fields, parameters, and responses present?
   - Are error cases handled as the spec describes?

4. If a deviation from spec is required, stop and surface it:
   - Describe the deviation and why it is necessary
   - Get confirmation before implementing
   - Log in `docs/decisions.md` as a Tier 2 entry

5. If an architectural decision is required, trigger /neutron:adr
   before proceeding with implementation.

6. Update `docs/decisions.md` with any Tier 2 design choices made
   during this unit's implementation.

7. Update the delivery status table in `CLAUDE.md`:
   change this unit's status from "not started" to "complete".

8. Write the session log entry.

9. Present output summary: files created/modified, tests written,
   decisions captured. Suggest running /neutron:review before raising PR.

## Outputs
- Implemented code for the target unit
- Tests for all new code
- Inline documentation for new public interfaces
- `docs/decisions.md` (appended if decisions made)
- `docs/adr/NNN-*.md` (if Tier 1 decision was made)
- `CLAUDE.md` (delivery status updated)
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Implement beyond the scope of the target unit
- Modify code in units not yet started
- Raise PRs — that is /neutron:ship after /neutron:review
- Make architectural decisions unilaterally — those go through
  /neutron:adr with human confirmation

## Model guidance
Stay strictly within the scope of the target unit. If implementing
the unit reveals that adjacent work is needed, surface it as a
finding rather than implementing it silently. The delivery plan is
the boundary — expanding scope mid-unit creates the exact drift
the plan is designed to prevent.

> Model note: Feature implementation benefits from strong reasoning
> on the spec to code translation. For units with significant
> architectural complexity, use the most capable model available.
