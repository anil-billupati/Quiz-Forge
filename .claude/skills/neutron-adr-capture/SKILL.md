---
name: neutron-adr-capture
description: Apply when a Tier 1 architectural decision is being made —
             specifically: choosing a technology, framework, or library
             the project depends on; defining a service boundary or API
             contract; selecting a data model or storage pattern; making
             a security or compliance architecture choice; changing an
             established pattern that existing code already follows;
             or any decision that would require significant rework to
             reverse. Do not apply for implementation details,
             routine refactors, or trivially reversible choices.
model: sonnet
version: 1.0.0
---

# Neutron ADR Capture

## What this skill enforces
That every Tier 1 architectural decision is captured as a formal ADR
in `docs/adr/` before it is implemented. Undocumented architectural
decisions are not acceptable outputs from any Neutron session.

## When this skill applies
When any of the following are true:
- A technology, framework, or library is being chosen that the project
  will depend on going forward
- A service boundary or API contract is being defined or changed
- A data model or storage pattern is being selected
- A security or compliance architecture choice is being made
- An established pattern that existing code already follows is being
  changed — this is a significant implicit decision
- A decision is being made that would require significant rework to
  reverse

## When this skill does not apply
- Choosing between two implementation approaches for a single function
  — this is a Tier 2 decision log entry, not an ADR
- Routine refactoring with no behaviour or architecture change
- Bug fixes that restore behaviour to match the existing spec
- Test or documentation changes
- Dependency version updates (unless changing the dependency itself)

## Rules

1. When a Tier 1 decision is identified, pause implementation and
   surface it explicitly before proceeding:
   - State the decision that needs to be made
   - Present the options available with pros and cons
   - Make a recommendation with rationale
   - Get explicit human confirmation of the choice

2. After confirmation, invoke `/neutron:adr` to create the formal ADR
   document. Do not proceed with implementation until the ADR is written
   and approved.

3. ADRs are numbered sequentially in `docs/adr/` starting at `001`.
   Check the existing ADRs before numbering a new one.

4. Follow the ADR format defined in
   `content/standards/decisions-format.md` exactly.

5. The ADR status starts as `proposed`. It becomes `accepted` when the
   human confirms. It does not become `accepted` automatically.

6. Reference the ADR number in the implementation code as a comment
   where the decision is materialised:
   `# See ADR-003: chose Redis over Memcached for session storage`

7. If a previously accepted ADR is being contradicted by a new decision,
   the existing ADR must be updated to `superseded` and a new ADR
   written. Architectural history must be continuous and traceable.
