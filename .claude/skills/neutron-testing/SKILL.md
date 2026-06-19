---
name: neutron-testing
description: Apply when any code is being written or modified. Ensure
             tests are written as part of the same implementation step,
             not planned as a follow-up. If implementation is presented
             without tests, it is incomplete.
model: sonnet
version: 1.0.0
---

# Neutron Testing

## What this skill enforces
That tests are a non-negotiable part of implementation, not an
optional follow-up. Code without tests is not complete code.
This applies to AI-generated code as much as human-written code.

## When this skill applies
When any of the following are being produced:
- New functions, methods, or classes
- Modified behaviour in existing functions or methods
- New API endpoints or modified endpoint behaviour
- New business logic or domain rules
- Bug fixes — regression test required

## When this skill does not apply
- Pure refactoring with no behaviour change — existing tests should
  still pass; no new tests required unless coverage gaps are found
- Documentation-only changes
- Configuration or infrastructure changes with no testable behaviour
- Scaffolding and boilerplate generation during `/neutron:init`

## Rules

1. Tests are written in the same implementation step as the code they
   test. Presenting implementation without tests is presenting
   incomplete work.

2. Every new public function or method has at least one unit test.
   Happy path minimum. Error cases where the function has meaningful
   error behaviour.

3. Every new API endpoint has an integration test covering:
   - Happy path — correct input, expected response
   - At least two error cases — invalid input and unauthorised access
     where applicable

4. Test names describe the scenario in plain language:
   `should return 404 when user does not exist`
   not `test_get_user_fail` or `testGetUser`.

5. Tests are independent. No test depends on state set by another test.
   Tests can be run in any order and individually.

6. Mocks are used for external dependencies only. Mocking internal
   logic is a signal the code needs refactoring, not more mocking.

7. Bug fixes require a regression test that:
   - Fails before the fix is applied
   - Passes after the fix is applied
   This confirms the fix addresses the actual root cause.

8. Test coverage on changed files must be at or above 80% line coverage.
   Coverage is a floor, not a target — meaningful assertions matter
   more than line counts.

9. If the testing strategy document exists at
   `docs/spec/testing-strategy.md`, follow the testing approach
   defined there for the current project type and stack.

10. Never suggest deferring tests to a follow-up PR or task.
    If time is the concern, reduce the scope of the implementation unit
    rather than reducing test coverage.
