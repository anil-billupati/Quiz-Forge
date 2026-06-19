---
name: neutron-session-capture
description: Apply during every command session. Log all artifacts
             read, gaps identified, questions asked, answers given,
             trade-offs presented, decisions made, and outputs produced
             to docs/session-log.md. This skill is a recording layer —
             it does not change what commands do, it ensures every
             session is fully auditable.
model: haiku
version: 1.0.0
---

# Neutron Session Capture

## What this skill enforces
That every Neutron command session produces a complete, auditable log
in `docs/session-log.md`. The session log is the raw conversational
audit trail — complementary to but distinct from the decision log
and ADRs.

## When this skill applies
During every command session. Any time a Neutron command is invoked.

## When this skill does not apply
- General conversation not associated with a command
- Read-only context loading at session start (covered by neutron-context)
- Answering quick questions that do not produce artifacts or decisions

## Rules

1. Every command session opens a new log entry in `docs/session-log.md`
   with the exact format defined in
   `content/standards/session-log-format.md`.

2. Log every artifact read — file path and what was extracted from it
   relevant to the current task.

3. Log every gap identified — the gap description and why it matters
   to the output being produced.

4. Log every question asked verbatim. Log every answer received verbatim.

5. Log every trade-off presented — the options, the recommendation made,
   and the outcome chosen.

6. Log the confirmation summary presented to the human before execution
   begins. Log the human's response — confirm or adjustments made.

7. Log every output artifact produced — exact file path and a one-line
   description of what was written.

8. Log every decision captured — tier, brief description, and where it
   was logged (decisions.md, docs/adr/, PR description).

9. The session log is append-only. Never edit or delete existing entries.

10. The session log entry is committed alongside the artifacts it produced.
    They are inseparable — a committed artifact without a session log
    entry is an incomplete record.

11. If `docs/session-log.md` does not exist, create it with a header:
    `# Session Log — {project-name}` before writing the first entry.
