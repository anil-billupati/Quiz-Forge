---
description: Run before raising any pull request. Reviews the changes
             against the spec, Fission engineering standard, security
             baseline, and CLAUDE.md. Uses tiered model execution —
             fast triage, then deep review of findings.
argument-hint: Optional — specific concern to focus on
model: haiku
version: 1.0.0
---

# /neutron:review

## Purpose
The review command is the quality gate before a PR is raised. It reviews
the current changes against four dimensions: spec conformance, engineering
standards, security baseline, and code quality. It uses a tiered approach —
fast triage to identify what needs deep review, then focused deep review
on the areas that matter. The output is actionable findings, not a pass/fail.

## Prerequisites
- Changes must be staged or committed in the current branch
- `docs/spec/` should exist for spec conformance review
- `CLAUDE.md` must exist
- `content/standards/engineering-standard.md` must be accessible

## Gather phase
Read in this order:
1. The git diff of current changes
2. `CLAUDE.md` for project conventions and active standards
3. The relevant `docs/spec/` sections for the changed code
4. `docs/adr/` for decisions relevant to the changed area

No questions required. The review proceeds from these artifacts.
If spec documents do not exist, note it and proceed with
standards and security review only.

## Confirmation gate
Not applicable. This command produces findings, not artifacts
requiring approval. Proceed directly to execution.

## Execute phase

**Stage 1 — Triage (haiku)**
Scan the diff for:
- Files changed and approximate scope
- Whether this looks like a feature, bug fix, or refactor
- Whether any security-sensitive areas are touched
- Whether any API surfaces are changed
- Obvious issues (commented-out code, debug statements, missing tests)

**Stage 2 — Standards review (sonnet)**
Review changed code against the Fission engineering standard:
- Function length and single responsibility
- Naming conventions
- Error handling — are errors handled or propagated with context?
- Logging — structured, no sensitive data, correct levels
- Documentation — docstrings on new public interfaces
- Test presence — are new functions and behaviours tested?
- Test quality — do tests assert real behaviour, not just execution?

**Stage 3 — Spec conformance review (sonnet)**
If spec documents exist:
- Does the implementation match the spec's described behaviour?
- Are all specified fields, parameters, and error cases handled?
- If this is an API change — does it match api-contracts.md?
- Are any deviations captured in docs/decisions.md?

**Stage 4 — Security review (sonnet, triggered if security-sensitive
areas are touched)**
- No secrets in the diff
- Input validation present on new external inputs
- No new wildcard CORS or permissive policies
- Sensitive data not in log output
- New dependencies reviewed (if any added)

**Stage 5 — Output**
Present findings in this format:

```
## Review findings — {branch name}

### Must fix before merge
{numbered list of blocking issues}
{each issue: file:line, what the problem is, what to do instead}

### Should fix
{numbered list of non-blocking but important issues}

### Consider
{numbered list of suggestions worth discussing}

### Passed
{brief statement of what was reviewed and found clean}
```

If there are no must-fix issues, say so explicitly.

6. Write the session log entry.

## Outputs
- Review findings (presented in session)
- `docs/session-log.md` (appended)

## Scope boundary
This command does not:
- Fix issues — it identifies them for the engineer to fix
- Approve PRs — that is a human responsibility
- Review infrastructure changes — those are reviewed by the DevOps tool
- Replace human code review — it supplements it

## Model guidance
Be specific. "This function is too long" is not a finding.
"src/api/users.py:handleUpdate is 67 lines — extract the validation
logic into a separate function" is a finding. Every must-fix issue
must include the file, line, and specific remediation.

> Model note: Triage can use a fast model. Deep review of complex
> security or spec conformance issues benefits from a more capable model.
