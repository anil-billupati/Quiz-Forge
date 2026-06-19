---
description: Run after the delivery plan is approved. Scaffolds the
             project repository with the correct structure, CLAUDE.md,
             CI/CD skeleton, and observability baseline for the project
             type and stack.
argument-hint: Optional — stack override if different from kickoff
model: haiku
version: 1.0.0
---

# /neutron:init

## Purpose
The init command creates the project's repository structure from the
approved architecture and stack. It is mechanical — it does not make
decisions, it implements what has already been decided. The result is
a repository an engineer can clone, run, and immediately begin
implementing against.

## Prerequisites
- `docs/kickoff.md` must exist (for project type and stack)
- `docs/plan/architecture.md` must exist (for repo structure)
- `docs/plan/delivery-plan.md` must exist (for delivery status in CLAUDE.md)
- `infra.yaml` must be complete

## Gather phase
Read `docs/kickoff.md` for: project name, type, service pattern,
stack (language and framework), cloud provider, team name.

Read `docs/plan/architecture.md` for: component structure, directory
organisation implied by the architecture.

Read the relevant archetype from `archetypes/{project-type}/` for:
standard directory structure, standard files, CI/CD template, and
observability baseline for this type and stack.

Gaps that require clarification:
- If stack is not specified in kickoff.md — ask once
- If multiple language options exist for the type — ask once
- If the archetype has required configuration values not in kickoff.md — ask

If all information is available, proceed directly to confirmation.

## Confirmation gate
```
I will scaffold the following structure for {project-name}:

Type: {project-type} / {service-pattern}
Stack: {language} + {framework}
Archetype: archetypes/{project-type}/{language}/

Will create:
- Repository directory structure (see archetypes/{type}/{lang}/)
- CLAUDE.md from template with project values filled in
- .neutron/ context files (security.md, integrations.md, environment.md)
- CI/CD skeleton (.github/workflows/)
- Observability baseline (logging config, health check)
- Test directory structure
- README.md skeleton

Confirm? [yes / adjust]
```

## Execute phase

1. Create the directory structure defined in
   `archetypes/{project-type}/{language}/ARCHETYPE.md`.

2. Copy and populate `CLAUDE.md` from
   `adapters/claude-code/CLAUDE.md.template`:
   - Fill all {placeholder} values from kickoff.md and plan docs
   - Populate delivery status table from delivery-plan.md units
   - Populate ADR summary if any ADRs exist
   - Set `last-updated` to today's date

3. Create `.neutron/` directory with three files populated from
   templates in `adapters/claude-code/.neutron/`:
   - `security.md` — fill auth mechanism and compliance from kickoff.md
   - `integrations.md` — fill from kickoff.md integrations section
   - `environment.md` — fill environments from infra.yaml

4. Create `.github/workflows/` with CI/CD skeleton appropriate for
   the stack. Minimum: test pipeline triggered on push to any branch,
   deploy pipeline triggered on merge to main.

5. Create observability baseline:
   - Logging configuration for structured JSON logging
   - Health check endpoint stub (for backend and ai-service types)
   - Metrics configuration stub

6. Create test directory structure matching `docs/spec/testing-strategy.md`.

7. Create `README.md` with:
   - Project name and one-sentence description
   - Prerequisites and setup instructions (with stack-specific commands)
   - How to run locally
   - How to run tests
   - Link to `docs/spec/` for full specification
   - Link to `docs/plan/delivery-plan.md` for delivery status

8. Write the session log entry.

9. Present next step: "Repository is scaffolded. Begin implementation
   with /neutron:feature '{Unit 1 name from delivery-plan.md}'"

## Outputs
- Complete repository directory structure
- `CLAUDE.md` (populated)
- `.neutron/security.md`, `.neutron/integrations.md`,
  `.neutron/environment.md` (populated)
- `.github/workflows/` (CI/CD skeleton)
- Observability baseline files
- Test directory structure
- `README.md`
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Implement any business logic
- Write application code beyond structural boilerplate
- Provision infrastructure — that is the DevOps tool
- Make architectural decisions — those are already in the plan

## Model guidance
This is a mechanical command. Follow the archetype exactly.
Do not add files or directories not specified in the archetype or
this command. Do not make technology choices — they were made during
kickoff and plan. If something in the archetype conflicts with the
project's kickoff doc, surface the conflict before proceeding.

> Model note: This command is primarily mechanical and does not
> require deep reasoning. A fast, efficient model is appropriate.
