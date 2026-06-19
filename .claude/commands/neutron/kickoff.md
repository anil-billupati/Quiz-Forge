---
description: Run at the start of every new project. Gathers project
             context through structured conversation and produces the
             kickoff document and partial infra.yaml that all subsequent
             commands depend on.
argument-hint: Optional — project name or brief description
model: sonnet
version: 1.0.0
---

# /neutron:kickoff

## Purpose
The kickoff command establishes the foundational context for a new
project. It is the seed from which all specs, plans, and scaffolding
grow. Every subsequent command reads the kickoff document — it must
be complete, accurate, and approved before anything else proceeds.

This command is conversational by design. It reads whatever context
already exists and asks only about what is missing or ambiguous.

## Prerequisites
- A new project repo created from the Neutron GitHub template
- CLAUDE.md present at repo root (provided by the template)
- No prerequisite documents required — this is the first command

If partial context exists (e.g. a brief, a problem statement, meeting
notes), share it before running this command. The gather phase will
read it and reduce the number of questions asked.

## Gather phase
Read all available artifacts in the project directory in this order:
1. Any documents shared in the current session
2. Any existing markdown files at repo root
3. Any files in a `docs/` directory if it exists

From each artifact, extract:
- Problem statement and project goals
- Known stakeholders and user types
- Technology preferences or constraints mentioned
- Compliance or security requirements mentioned
- Integration points with external systems
- Timeline or delivery constraints
- Team size and composition

Identify gaps — required fields in the kickoff document that are not
covered by existing artifacts. Ask only about the gaps.

Required fields that must be resolved before execution:
- Project name and one-sentence description
- Problem being solved
- Primary users and their key workflows
- Project type: backend | frontend | data-pipeline | ai-service
- If backend: service pattern: http-service | worker | hybrid
- Technology stack (language, framework) — Fission defaults if
  client has no preference
- Cloud provider — AWS default if not specified
- Key integration points (data stores, external APIs, queues)
- Compliance requirements — none unless stated
- Team name and project lead

For each gap, ask one clear question. Do not ask multiple questions
in a single message. Wait for the answer before asking the next.

If all required fields are covered by existing artifacts, present
the confirmation summary immediately without asking any questions.

## Confirmation gate
Present a structured summary before writing any files:

```
Project: {name}
Type: {project-type} / {service-pattern if backend}
Stack: {language} + {framework}
Cloud: {cloud}
Problem: {one sentence}
Users: {brief description}
Integrations: {list or none}
Compliance: {requirements or none}
Team: {team name}

This will create:
- docs/kickoff.md
- infra.yaml (partial — /neutron:plan completes it)

Confirm? [yes / adjust]
```

Do not write any files until the engineer responds "yes" or an
equivalent confirmation.

## Execute phase

1. Create `docs/` directory if it does not exist.

2. Write `docs/kickoff.md` containing:
   - Project identity: name, type, service pattern, stack, cloud
   - Problem statement: what problem this solves and for whom
   - Users: primary user types and their key workflows
   - Goals: what success looks like for this project
   - Constraints: technical, timeline, compliance, budget if known
   - Integrations: external systems, APIs, data stores, queues
   - Compliance requirements: specific requirements or "none"
   - Team: team name, project lead, key stakeholders
   - Open questions: anything that could not be resolved in this session
   - Date and Neutron version

3. Write `infra.yaml` at repo root with fields that can be determined
   now. Mark fields that require /neutron:plan as `tbd`:

   ```yaml
   neutron-version: {version}
   project-name: {name}
   project-type: {neutron-type mapped to infra.yaml type}
   service-pattern: {pattern | n/a}
   cloud: {aws | azure | gcp}
   language: {language}
   framework: {framework}
   region: tbd
   environments: tbd
   data-stores: tbd
   integrations: tbd
   compliance: {requirements or none}
   ```

4. Write the session log entry for this session.

5. Present next step: "Run /neutron:spec to generate the technical
   specification from this kickoff document."

## Outputs
- `docs/kickoff.md`
- `infra.yaml` (partial)
- `docs/session-log.md` (created or appended)

## Scope boundary
This command does not:
- Generate technical specifications — that is /neutron:spec
- Make architectural decisions — those emerge during /neutron:plan
- Scaffold the repository — that is /neutron:init
- Produce a delivery plan — that is /neutron:plan

## Model guidance
Ask one question at a time. Do not front-load multiple questions.
Be specific about why each question matters — what it affects in the
output. If the engineer is uncertain about a field (e.g. compliance
requirements), default to the conservative choice and document it
as an open question to be confirmed.

> Model note: This command requires conversational reasoning and
> synthesis of potentially unstructured input. Use a capable model.
