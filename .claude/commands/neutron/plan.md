---
description: Run after spec documents are approved. Produces the
             architecture, delivery plan, and completed infra.yaml.
             The delivery plan drives all subsequent feature implementation.
argument-hint: Optional — specific planning concern to focus on
model: opus
version: 1.0.0
---

# /neutron:plan

## Purpose
The plan command takes the approved specification and produces three
things: a system architecture, a sequenced delivery plan broken into
implementation units, and the completed infra.yaml for the DevOps tool.
The delivery plan is the direct input to /neutron:feature — every
feature implementation unit comes from here.

## Prerequisites
- All documents in `docs/spec/` must exist and be approved
- `docs/kickoff.md` must exist
- Open questions in spec documents must be resolved

## Gather phase
Read all documents in `docs/spec/` and `docs/kickoff.md`.

Identify what needs architectural decisions:
- Component structure — how many services or modules, their boundaries
- Data storage — which store for which data, why
- Inter-component communication — sync vs async, protocols
- Deployment topology — how components are deployed
- Observability — logging, metrics, tracing approach
- Security architecture — where auth is enforced, secrets access pattern

For each decision that has meaningful trade-offs, surface it as a
discussion point before producing the plan. These may become ADRs.

Identify what can be parallelised in delivery — which implementation
units have no dependencies on each other and can be worked on
simultaneously.

## Confirmation gate
```
I will generate the following planning artifacts:

- docs/plan/architecture.md
- docs/plan/delivery-plan.md
- infra.yaml (completed)
- docs/adr/001-*.md (if architectural decisions were made)

Architectural decisions made in this session:
{list of decisions with choices made, or "none"}

Delivery units proposed: {N} units
Parallelisation opportunities: {describe or "none identified"}

Confirm? [yes / adjust]
```

## Execute phase

1. Create `docs/plan/` directory.

2. Write `docs/plan/architecture.md` containing:
   - Architecture overview — one paragraph describing the system shape
   - Component diagram (text-based Mermaid or ASCII)
   - Component descriptions — what each component is responsible for
     and what it explicitly is not responsible for
   - Data flow description — how data moves through the system
   - Integration points — how this system connects to external systems
   - Observability approach — logging, metrics, alerting strategy
   - Deployment overview — environments and how components are deployed

3. Write `docs/plan/delivery-plan.md` containing:
   - Introduction: how to use this plan, one unit at a time with
     /neutron:feature
   - For each implementation unit:
     ```
     ### Unit N: {descriptive name}
     Dependencies: {prior units this depends on, or "none"}
     Parallelisable with: {units that can run concurrently, or "none"}
     Spec reference: {which spec sections this implements}
     What: {precise description of what is implemented in this unit}
     Includes:
     - {specific deliverable}
     - {specific deliverable}
     Done when:
     - {checkable completion criteria}
     - {checkable completion criteria}
     Estimated complexity: {low | medium | high}
     ```
   - Recommended execution sequence with rationale

4. Complete `infra.yaml` — fill in all `tbd` fields based on the
   architecture decisions made. Fields to complete:
   - region (default to primary cloud region for the cloud provider)
   - environments: [dev, staging, production]
   - data-stores: list with type, name, and purpose
   - integrations: list with name, type, and direction

5. Write ADRs for any Tier 1 architectural decisions made during
   planning. Follow format in `content/standards/decisions-format.md`.
   Number starting from 001 or continuing from existing ADRs.

6. Write the session log entry.

7. Present next steps:
   - "Share infra.yaml with the Fission DevOps Tool to provision
     infrastructure."
   - "Run /neutron:init to scaffold the project repository."
   - "Then begin implementation with /neutron:feature 'Unit 1: ...'"

## Outputs
- `docs/plan/architecture.md`
- `docs/plan/delivery-plan.md`
- `infra.yaml` (completed)
- `docs/adr/NNN-*.md` (if architectural decisions made)
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Scaffold the repository — that is /neutron:init
- Implement any feature — that is /neutron:feature
- Provision infrastructure — that is the DevOps tool consuming infra.yaml
- Define detailed test cases — those are written during /neutron:feature

## Model guidance
The delivery plan is the most consequential output of this command.
Unit decomposition must be genuinely useful — units that are too large
will be unwieldy, units that are too small create unnecessary overhead.
A good unit is one to three days of focused implementation. Flag units
that seem significantly larger and suggest splitting them.

> Model note: Architecture and delivery planning require deep reasoning
> about system design, dependencies, and sequencing. Use the most
> capable model available.
