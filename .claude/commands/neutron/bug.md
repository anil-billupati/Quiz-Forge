---
description: Run when a bug is reported or discovered. Structures
             the investigation, documents root cause, implements
             the fix with a regression test, and produces a bug
             record capturing the full context.
argument-hint: Bug description or issue reference
model: sonnet
version: 1.0.0
---

# /neutron:bug

## Purpose
The bug command brings the same rigour to bug fixes that /neutron:feature
brings to feature implementation. A bug fix without a root cause analysis
is a patch. A bug fix without a regression test is a bug waiting to recur.
This command ensures every non-trivial bug is investigated, understood,
fixed correctly, and documented.

## Prerequisites
- The bug must be described or reproducible in the current session
- The relevant codebase must be present
- `docs/spec/` should exist to verify expected vs actual behaviour

## Gather phase
Read in this order:
1. The bug description provided as argument or in the session
2. The relevant code in the area of the bug
3. `docs/spec/technical-spec.md` and `docs/spec/api-contracts.md`
   to understand expected behaviour
4. `docs/decisions.md` and relevant `docs/adr/` for context on
   why the affected code is structured the way it is
5. Existing tests in the affected area

From this reading, identify:
- Whether the bug is reproducible from the description alone or
  whether reproduction steps need to be established
- Whether the expected behaviour is clearly defined in the spec
- Whether this area of the code has known complexity or prior decisions

Gaps that may require questions:
- Reproduction steps are not clear
- Expected behaviour is ambiguous in the spec
- The severity or impact is not described

Ask only what is needed to proceed with confidence.

## Confirmation gate
```
Bug: {title}
Severity: {low | medium | high | critical}

Reproduction: {summary of reproduction steps}
Expected: {what should happen per spec}
Actual: {what is happening}
Affected: {files or components affected}

Fix approach: {proposed approach}
Regression test: {what the test will verify}

Will create:
- Fix in {file paths}
- Regression test in {test file paths}
- docs/bugs/{NNN}-{name}.md

Confirm? [yes / adjust]
```

## Execute phase

1. Write a regression test that:
   - Reproduces the bug (test must fail before the fix)
   - Verifies correct behaviour (test must pass after the fix)
   Write this test first, before the fix.

2. Implement the fix:
   - Address the root cause, not the symptom
   - Follow the Fission engineering standard
   - Keep the fix minimal — change only what is necessary to fix
     the bug. Do not refactor unrelated code in the same change.

3. Verify the regression test now passes.

4. Check for similar patterns elsewhere in the codebase that may
   have the same root cause. Surface findings — do not fix them in
   this command, but document them.

5. Write `docs/bugs/NNN-{name}.md` following the bug record format
   in `content/standards/decisions-format.md`.

6. Write the session log entry.

7. Present output: fix summary, regression test, bug record created,
   similar patterns found if any. Suggest running /neutron:review.

## Outputs
- Bug fix implementation
- Regression test
- `docs/bugs/NNN-{name}.md` (bug record)
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Fix multiple unrelated bugs in one session — one bug per invocation
- Refactor code beyond what is necessary to fix the bug
- Implement new features discovered while investigating
- Raise PRs — that is /neutron:ship after /neutron:review

## Model guidance
Root cause analysis is the most important part of this command.
Do not accept "it was a null check" as a root cause. Ask why the
null was not handled. Ask what assumption the original code made
that turned out to be wrong. The lessons learned section of the
bug record should be genuinely useful to future engineers.

> Model note: Root cause analysis and minimal correct fixes require
> careful reasoning. Use a capable model.
