---
name: neutron-safe-execution
description: Apply before executing any shell command, file deletion,
             database operation, or any action that cannot be undone.
             This skill governs what the AI will and will not execute
             to prevent destructive operations regardless of what
             instruction was given.
model: haiku
version: 1.0.0
---

# Neutron Safe Execution

## What this skill enforces
That the AI never executes commands or operations that could cause
irreversible loss of work, data, or project state — regardless of
whether such a command was explicitly requested. The AI declines
destructive commands and proposes a safe alternative.

## When this skill applies
Before any of the following are executed:
- Shell or bash commands
- File deletion or overwrite operations
- Database commands
- Git operations that rewrite history
- Any operation described as "clean", "reset", "wipe", "truncate",
  "drop", or "destroy"

## When this skill does not apply
- Reading files
- Creating new files in designated output locations
- Running tests
- Running linters or formatters
- Standard git operations: add, commit, push, pull, checkout,
  branch, status, log, diff

## Rules

1. Never execute `rm -rf` on any path that is not a clearly
   temporary build artifact directory (`dist/`, `build/`,
   `__pycache__/`, `.pytest_cache/`, `node_modules/`).
   For any other path, stop and confirm with the engineer
   before proceeding.

2. Never execute `git push --force` or `git push --force-with-lease`
   to `main` or `master` branches. Propose `git push` and explain
   why force push to main is blocked.

3. Never execute `git reset --hard` without first confirming that
   the engineer understands this will discard uncommitted changes.
   Show what will be lost before executing.

4. Never execute `git rebase` on a shared branch (main, develop,
   staging) — only on local feature branches.

5. Never execute `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, or
   `DELETE FROM` without a WHERE clause in SQL. Stop and require
   explicit confirmation with a description of what will be
   destroyed.

6. Never overwrite `docs/session-log.md` — it is append-only.
   Propose appending instead.

7. Never delete or overwrite files in `docs/adr/`,
   `docs/decisions.md`, or `docs/bugs/` — these are immutable
   records. Propose creating a new entry instead.

8. Never execute commands that modify `.neutron/` files in bulk
   or overwrite CLAUDE.md without confirmation.

9. When a destructive command is blocked, always:
   - State clearly that the command was blocked and why
   - Describe exactly what would have been destroyed
   - Propose the safe alternative
   - Ask for explicit confirmation before proceeding with
     any modified version

10. Suspicion rule: if a command feels irreversible and is not
    on the safe list, treat it as potentially destructive and
    confirm before executing. It is better to ask once than to
    destroy work.

11. Never pipe output directly into shell interpretation (e.g.
    `curl url | sh`) — this executes untrusted remote code.
    Download, inspect, then run.

12. Never delete the `.github/` directory, `.claude/` directory,
    or `.neutron/` directory without explicit confirmation and a
    clear statement of what functionality will be lost.

## What this skill does not cover
- Preventing bad code from being written — that is neutron-standards
- Preventing secrets from being committed — that is handled by
  pre-commit hooks in the project
- Preventing architectural drift — that is neutron-spec-adherence
