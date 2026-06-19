---
description: Run after review is clean and all findings are resolved.
             Verifies the definition of done, produces a commit message
             and PR description, and confirms the change is ready to merge.
argument-hint: Optional — PR title override
model: haiku
version: 1.0.0
---

# /neutron:ship

## Purpose
The ship command is the final gate before a change is committed and a
PR is raised. It verifies the definition of done is fully met, produces
a well-structured commit message and PR description, and confirms there
is nothing blocking merge. It is deliberately lightweight — by the time
/neutron:ship is run, /neutron:review should have already caught all issues.

## Prerequisites
- `/neutron:review` must have been run and all must-fix findings resolved
- The definition of done checklist must be completable
- Changes must be ready to commit

## Gather phase
Read:
1. `content/standards/definition-of-done.md`
2. The git diff to verify the state of changes
3. `docs/decisions.md` for any decisions made during this change
4. `docs/plan/delivery-plan.md` to identify which unit this ships

Walk through the definition of done checklist item by item against
the actual state of the changes. Flag any items that are not met.

Do not ask questions — assess the state from the artifacts.
If a must-have item in the definition of done is not met, block
and state specifically what needs to be done before proceeding.

## Confirmation gate
```
Definition of done: {all items checked | N items not met}

{If items not met — list them. Do not proceed.}

Commit message:
{type}({scope}): {description}

{body — why this change was made}

{footer — unit reference or bug reference}

PR description:
## What
{what changed}

## Why
{why this was needed}

## How
{approach taken}

## Testing
{what was tested}

Decisions captured: {list or "none"}

Ready to ship? [yes / adjust]
```

## Execute phase

1. If any definition of done items are unmet, present them and stop.
   Do not proceed to commit.

2. On confirmation, produce:
   - Final commit message following git-conventions.md format
   - PR description following the PR template in git-conventions.md
   - Confirm the branch name follows naming conventions

3. Write the session log entry.

4. Present: "Change is ready. Commit with the message above, push,
   and raise a PR. Assign at least one reviewer."

## Outputs
- Definition of done verification result
- Commit message
- PR description
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Run git commands — the engineer commits and pushes
- Fix issues — those are resolved before /neutron:ship is run
- Approve or merge PRs — that is a human responsibility

## Model guidance
The definition of done check is binary — either an item is met or
it is not. Do not be lenient. If tests are missing, block. If
documentation is missing, block. The ship command's value is in
being a reliable gate, not a rubber stamp.

> Model note: This command is primarily checklist verification and
> text generation. A fast, efficient model is appropriate.
