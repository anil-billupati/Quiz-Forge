---
description: Run after /neutron:kickoff is approved. Converts the
             kickoff document into structured engineering specifications
             that define what is being built and how.
argument-hint: Optional — specific area to focus on
model: opus
version: 1.0.0
---

# /neutron:spec

## Purpose
The spec command transforms the approved kickoff document into a set
of structured engineering artifacts that define the system precisely
enough for architecture planning and implementation to proceed without
ambiguity. Specs are the source of truth for what is being built.
They are human-approved before any planning or implementation begins.

## Prerequisites
- `docs/kickoff.md` must exist and be approved
- All open questions in kickoff.md must be resolved before running
  this command — surface any unresolved open questions before proceeding

## Gather phase
Read `docs/kickoff.md` in full. Extract all available information
about the system being built.

Identify gaps — things required for the spec documents that are not
covered in the kickoff:

For product spec gaps:
- User workflows not described in sufficient detail
- Success metrics not defined
- Edge cases or error scenarios not mentioned

For technical spec gaps:
- Non-functional requirements not stated (performance, availability,
  scalability expectations)
- Data retention or archival requirements
- Error handling strategy not defined

For API contracts gaps (if project-type is backend or ai-service):
- Endpoints implied but not described
- Request/response schemas not defined
- Authentication requirements on specific endpoints not clarified

For domain model gaps:
- Entities mentioned but relationships not described
- Business rules implied but not stated

Ask about gaps only. If the kickoff document is thorough, the gather
phase may produce no questions and proceed directly to confirmation.

## Confirmation gate
```
I will generate the following specification documents from
docs/kickoff.md:

- docs/spec/product-spec.md
- docs/spec/technical-spec.md
- docs/spec/api-contracts.yaml {if applicable}
- docs/spec/api-contracts.md {if applicable}
- docs/spec/domain-model.md
- docs/spec/testing-strategy.md

Gaps resolved in this session:
{list of gaps and answers, or "none — kickoff document was complete"}

Confirm? [yes / adjust]
```

## Execute phase

1. Create `docs/spec/` directory.

2. Write `docs/spec/product-spec.md` containing:
   - Problem statement (from kickoff)
   - User types and primary workflows — detailed enough to design against
   - Functional requirements — what the system must do, numbered
   - Non-functional requirements — performance, availability, scalability
   - Success criteria — measurable outcomes
   - Out of scope — explicit list of what this project does not do
   - Open questions remaining

3. Write `docs/spec/technical-spec.md` containing:
   - System overview and component diagram (text-based if no diagram tool)
   - Component responsibilities — what each part of the system owns
   - Data flow — how data moves through the system
   - Technology decisions already made (from kickoff) and rationale
   - Error handling strategy — how errors are handled and surfaced
   - Logging and observability approach
   - Security approach (high level — detail in .neutron/security.md)
   - Constraints and assumptions
   - Out of scope

4. Write `docs/spec/api-contracts.yaml` if project-type is backend,
   frontend (BFF), or ai-service. OpenAPI 3.x format. For each endpoint:
   - Method and path
   - Description
   - Authentication required
   - Request parameters and body schema
   - Response schema for success and error cases

5. Write `docs/spec/api-contracts.md` as a human-readable companion
   to api-contracts.yaml. Summarises each endpoint with examples.

6. Write `docs/spec/domain-model.md` containing:
   - Core entities with their attributes and types
   - Relationships between entities (Mermaid ER diagram)
   - Business rules that govern entity behaviour
   - Bounded contexts if multiple domains are present

7. Write `docs/spec/testing-strategy.md` containing:
   - Testing approach for this project type and stack
   - What is unit tested, integration tested, e2e tested
   - Test data strategy
   - Mocking strategy for external dependencies
   - Coverage targets per layer

8. Write the session log entry.

9. Present next step: "Review and approve the specification documents.
   Once approved, run /neutron:plan to generate the architecture and
   delivery plan."

## Outputs
- `docs/spec/product-spec.md`
- `docs/spec/technical-spec.md`
- `docs/spec/api-contracts.yaml` (if applicable)
- `docs/spec/api-contracts.md` (if applicable)
- `docs/spec/domain-model.md`
- `docs/spec/testing-strategy.md`
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Make architectural decisions — those are made during /neutron:plan
- Produce a delivery plan or task breakdown
- Generate code or scaffolding
- Define infrastructure requirements in detail — those flow into
  infra.yaml during /neutron:plan

## Model guidance
Produce real, specific content — not generic templates with
placeholders. Every section should be written as if an engineer
is about to implement against it tomorrow. If something cannot
be specified without more information, flag it as an open question
in the document rather than writing a vague placeholder.

> Model note: Specification generation requires deep reasoning over
> requirements and the ability to identify ambiguity and completeness
> gaps. Use the most capable model available.
