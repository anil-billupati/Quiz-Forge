---
description: Run to add a bounded feature to a project that already has
             a completed delivery plan and implementation. Lighter than
             the full spec cycle — amends existing artifacts rather than
             creating new ones. All decision capture follows Neutron
             standards exactly.
argument-hint: Feature name or brief description
model: sonnet
version: 1.0.0
---

# /neutron:add

## Purpose
The add command extends a completed project with a bounded feature.
It is the bridge between a shipped delivery plan and new scope that
is too significant for ad-hoc implementation but too small to justify
a full spec cycle. All Neutron decision capture, session logging, and
spec adherence applies — the difference is scope: amendments only,
no new top-level artifacts.

## Prerequisites
- `docs/plan/delivery-plan.md` must exist with at least one completed unit
- `docs/spec/technical-spec.md` must exist
- The feature must be describable as an amendment to existing spec sections

If the feature requires a new top-level spec document, a new ADR sequence
from scratch, or a significant rearchitecture — it is not a small feature.
Use `/neutron:kickoff` to start a proper spec cycle for it.

## Gather phase
Read in this order:
1. `docs/plan/delivery-plan.md` — understand existing scope and completed units
2. The relevant sections of `docs/spec/technical-spec.md`
3. `docs/spec/api-contracts.md` if the feature involves an API surface
4. `docs/spec/domain-model.md` if the feature involves entities or business logic
5. `docs/spec/testing-strategy.md` for testing approach
6. Existing code in the directories the feature will touch
7. `docs/adr/` for decisions relevant to this feature's domain
8. `docs/decisions.md` for recent design choices in this area

After reading, auto-assess scope signals:
- Does this require a new domain entity or data model not in the current spec?
- Does this require a new external integration not in `.neutron/integrations.md`?
- Does this touch more than one existing unit's domain boundary?

If any signal is found, surface them before continuing:

```
Scope signals detected:
- {signal description}

This may be larger than a small feature.
Continue lightweight [add] or start a full spec cycle [kickoff]?
```

If the engineer chooses to continue: proceed to confirmation gate.
If no signals: proceed directly to confirmation gate.

## Confirmation gate

```
Adding: {feature name}
Spec amendment: {which section of technical-spec.md will be amended}

What will be built:
{bullet list of specific deliverables}

Done when:
{completion criteria}

Will create/modify:
{list of files}

Tests to be written:
{list of test scenarios}

Scope signals: {none | list}

Confirm? [yes / adjust]
```

## Execute phase

1. **Spec amendment** — append to the existing spec document's `## Amendments`
   section. If no `## Amendments` section exists, create it at the end of the file.
   Follow the exact format from `content/standards/decisions-format.md`:

   ```markdown
   ## Amendments

   ### Amendment NNN — {YYYY-MM-DD}
   Section affected: {e.g. "API Contracts — /api/v1/users POST"}
   What changed: {one sentence describing the change}
   Why: {rationale}
   Decisions.md reference: {entry title}
   Significance: {medium | high}
   ```

   Only `medium` or `high` significance changes get an amendment entry.
   `low` significance goes to `docs/decisions.md` only.

2. **Plan amendment** — add one or more new units to `docs/plan/delivery-plan.md`
   with explicit dependency links to the existing units they build on.

3. **Implementation** — implement in this order:
   a. Domain/business logic layer — entities, rules, services
   b. Infrastructure/data layer — repositories, external adapters
   c. API/interface layer — handlers, controllers, routes
   d. Tests for each layer as it is built — not at the end

4. Run neutron-spec-adherence check before presenting output:
   - Does the implementation match the amended spec?
   - Are all specified fields, parameters, and responses present?
   - Are error cases handled as the spec describes?

5. If a deviation from the amended spec is required, stop and surface it.
   Capture in `docs/decisions.md` as a Tier 2 entry before implementing.

6. If a Tier 1 architectural decision arises, trigger `/neutron:adr`
   before proceeding with implementation.

7. Update `docs/decisions.md` with any Tier 2 design choices made
   during implementation. Include the `Significance:` field.

8. Update the delivery status table in `CLAUDE.md`:
   add the new unit(s) and mark them complete.

9. Write the session log entry to `docs/session-log.md`.

10. Present output summary: files created/modified, tests written,
    decisions captured. Suggest running `/neutron:review` before raising PR.

## Outputs
- Implemented code for the new feature
- Tests for all new code
- Inline documentation for new public interfaces
- `docs/spec/technical-spec.md` (amended)
- `docs/plan/delivery-plan.md` (new units appended)
- `docs/decisions.md` (appended if decisions made)
- `docs/adr/NNN-*.md` (if a Tier 1 decision was made)
- `CLAUDE.md` (delivery status updated)
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Create new top-level spec documents — amendments to existing docs only
- Start a new ADR sequence from scratch — if the feature needs that,
  it is not a small feature; redirect to `/neutron:kickoff`
- Replace the full spec cycle for features that warrant one
- Raise PRs — that is `/neutron:ship` after `/neutron:review`
- Make architectural decisions unilaterally — those go through
  `/neutron:adr` with human confirmation
- Implement beyond the scope confirmed at the confirmation gate

## Model guidance
The add command requires careful reading of existing artifacts before
acting. The spec amendment must be precise — too narrow and it under-
specifies the feature; too broad and it expands scope beyond what was
intended. Use the most capable model available for features with
significant domain logic or API surface changes.

> Model note: For features with architectural complexity or new API
> surfaces, use the most capable model available. For simple additions
> (a new field, a config option, a minor endpoint), sonnet is sufficient.
