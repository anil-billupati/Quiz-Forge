---
name: neutron-standards
description: Apply when any engineering task is being performed in a
             Fission project. This skill is always active. It injects
             Fission's engineering conventions into every session so
             that standards are enforced without being explicitly
             requested.
model: haiku
version: 1.0.0
---

# Neutron Standards

## What this skill enforces
Fission's universal engineering conventions as defined in
`content/standards/engineering-standard.md`. Applied to every
action taken in a Neutron project regardless of type, stack, or phase.

## When this skill applies
Always. Every session. Every action. No exceptions.

## When this skill does not apply
This skill has no exclusions. It is the baseline for all Fission
engineering work.

## Rules

1. Functions and methods do one thing. If a name contains "and",
   it should be split into two functions.

2. Maximum function length is 40 lines. If exceeded, add a comment
   explaining why the exception is warranted.

3. No commented-out code. Use version control — delete unused code.

4. No magic numbers or strings. Named constants only.

5. Error handling is explicit. Errors are either handled at the point
   they occur or propagated with context added. Never swallowed silently.

6. Logging is structured JSON. No unstructured log strings in
   production code paths. No print statements or console.log.

7. Names are descriptive. Abbreviations only if universally understood
   in the domain. Boolean names read as statements: `isActive`,
   `hasPermission`, not `active`, `permission`.

8. Every public function, method, class, and module has a docstring
   or JSDoc comment stating what it does.

9. No direct commits to main. Every change goes through a pull request.

10. AI-generated code is subject to the same standards as human-written
    code. The author is responsible for all code merged regardless of
    how it was produced.

11. Dependencies are explicit. No implicit global state. Every new
    dependency has a documented reason in the codebase.

12. Tests are written alongside implementation. Never after, never
    as a separate task.
