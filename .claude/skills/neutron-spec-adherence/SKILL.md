---
name: neutron-spec-adherence
description: Apply whenever code is being written or modified in a
             project that has an approved spec in docs/spec/. Ground
             all implementation in the approved spec. Surface deviations
             immediately rather than implementing silently.
model: sonnet
version: 1.0.0
---

# Neutron Spec Adherence

## What this skill enforces
That all implementation is grounded in the approved spec. Code and spec
must not drift. Any deviation from the spec is surfaced and captured as
a decision before being implemented — never silently diverged from.

## When this skill applies
When any of the following are true:
- Code is being written for a feature covered by the approved spec
- Code is being modified that affects behaviour described in the spec
- An API endpoint is being added or changed
- A data model is being created or modified
- Business logic is being implemented

## When this skill does not apply
- Scaffolding and boilerplate generation during `/neutron:init` —
  no spec exists yet
- Bug fixes that restore behaviour to match the spec — these are
  spec-conformant by definition
- Refactoring with no behaviour change
- Test-only changes

## Rules

1. Before writing any implementation code, identify and read the
   relevant section of the approved spec:
   - `docs/spec/technical-spec.md` for implementation approach
   - `docs/spec/api-contracts.md` for any API surface
   - `docs/spec/domain-model.md` for entities and business rules

2. Implement exactly what the spec describes. Not more, not less.
   Scope creep — even small additions — must be flagged before
   implementation, not discovered after review.

3. If the spec is ambiguous about what is required, stop. Ask a
   clarifying question before writing code. Do not resolve ambiguity
   by assumption.

4. If the implementation requires something the spec does not cover,
   surface the gap explicitly:
   - State what is needed that the spec does not address
   - Propose how to handle it
   - Get confirmation before proceeding
   - Capture the resolution in `docs/decisions.md`

5. If a better approach than the spec describes becomes apparent during
   implementation, do not silently implement the better approach.
   Surface it, discuss it, update the spec if agreed, then implement.
   The spec is the source of truth — it changes through discussion,
   not through code.

6. After implementation, do a spec check before presenting the output:
   - Does the implementation match the spec's described behaviour?
   - Are all specified fields, parameters, and responses accounted for?
   - Are error cases handled as the spec describes?
   If any check fails, resolve it before presenting.

7. Every deviation from spec — even agreed improvements — is captured
   as follows before the code is committed:
   - Always: add a Tier 2 entry to `docs/decisions.md`
   - For medium or high significance deviations: also append an
     amendment entry to the `## Amendments` section of the affected
     spec document, linking back to the decisions.md entry

8. Amendments to spec documents take precedence over the original
   spec text. When the `## Amendments` section of a spec document
   contradicts earlier content in that document, the amendment
   is the current authoritative statement of intent.
