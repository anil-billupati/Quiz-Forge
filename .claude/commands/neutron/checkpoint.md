---
description: Run when the session log or decisions.md has grown
             large enough to slow down context loading. Compresses
             project history into a rolling summary that
             neutron-context reads instead of raw files. Run at
             the end of each milestone or when docs/session-log.md
             exceeds 500 lines.
argument-hint: Optional — milestone name or reason for checkpoint
model: sonnet
version: 1.0.0
---

# /neutron:checkpoint

## Purpose
As a project ages, docs/session-log.md and docs/decisions.md grow
large. Reading them in full at the start of every session becomes
expensive and increasingly ineffective — the AI processes thousands
of lines to extract a few relevant facts. The checkpoint command
compresses project history into a rolling summary that captures
essential context without the volume. neutron-context reads the
summary by default once it exists, keeping sessions fast and focused.

## Prerequisites
- Project must be past its first delivery unit — at least some
  history must exist to summarise
- Typically run at the end of a milestone, sprint, or when
  docs/session-log.md exceeds 500 lines

## Gather phase
Read in full:
1. `docs/session-log.md` — entire file
2. `docs/decisions.md` — all entries
3. `docs/adr/` — all accepted ADRs
4. `CLAUDE.md` — current delivery status
5. `docs/context-summary.md` — existing summary if present
   (will be updated, not replaced)

No questions required. Proceed directly to confirmation.

## Confirmation gate
```
Checkpoint: {milestone name or date}

Will compress:
- Session log: {N} entries → summary
- Decisions: {N} entries ({M} high, {K} medium, {J} low)
- ADRs: {N} accepted decisions

Will create/update:
- docs/context-summary.md

Raw files are preserved unchanged — this is non-destructive.
session-log.md and decisions.md remain intact for full audit.

Confirm? [yes / adjust]
```

## Execute phase

1. Write or update `docs/context-summary.md` with these sections:

   **Project identity** (from CLAUDE.md)
   Name, type, stack, cloud, neutron-version, team.

   **Current delivery state**
   Which units are complete, in progress, not started.
   Last updated date.

   **Architectural decisions in effect**
   One line per accepted ADR: number, title, choice made.
   Full detail in docs/adr/.

   **Key design decisions** (medium and high significance only)
   The 10-15 most consequential Tier 2 decisions, newest first.
   Format: date, decision, rationale in one sentence.

   **Patterns established**
   Recurring patterns identified across sessions — how the team
   has resolved similar problems consistently.

   **Open questions and known gaps**
   Unresolved questions from session log and decisions.
   Spec sections marked [RECONSTRUCTED] if mid-project adoption.

   **Recent activity summary**
   Last 3-5 sessions summarised in 2-3 sentences each.
   What was worked on, what was decided, what was produced.

   **Checkpoint metadata**
   ```
   Last checkpoint: {ISO date}
   Sessions compressed: {N}
   Decisions compressed: {N} ({M} high, {K} medium, {J} low)
   Session log lines at checkpoint: {N}
   ```

2. Write the session log entry for this checkpoint session.

3. Present: "Checkpoint complete. docs/context-summary.md updated.
   neutron-context will now read this summary at session start
   instead of the raw session log and decisions files. Raw files
   are unchanged and remain available for full audit."

## Outputs
- `docs/context-summary.md` (created or updated)
- `docs/session-log.md` (appended — checkpoint session entry)

## Scope boundary
This command does not:
- Delete or modify the raw session log — it is append-only
- Delete or modify decisions.md — it is append-only
- Modify ADRs
- Make any decisions or change project direction
- Replace the full audit trail — it supplements it with a
  faster-loading summary

## Model guidance
The context summary must be genuinely useful — not a list of
everything that happened but a curated view of what a returning
engineer needs to understand project state quickly. Prioritise
decisions that are still in effect, patterns that recur, and
open questions that remain unresolved. Historical decisions that
were later superseded should be noted but not given equal weight
to current decisions.

> Model note: Summarisation across large documents requires
> careful judgement about signal vs noise. Use a capable model.
