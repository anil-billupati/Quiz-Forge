# ContestForge — AIDLC Phase 24: Coding Standards

| | |
|---|---|
| **Phase** | 24 of 25 — Coding Standards |
| **Status** | Draft — for review/approval |
| **Date** | 2026-06-23 |
| **Depends on** | Phases 5/7/23; global + project CLAUDE.md; Fission standards |
| **Feeds** | Implementation, CI lint gates |

---

## Goal
Define **coding standards & conventions** (backend + frontend) enforcing the design principles (SOLID,
DRY, KISS, YAGNI, clean/hexagonal) and the integrity rules, so all features are consistent, readable,
and maintainable.

## Assumptions
- Standards apply repo-wide; enforced by linters/formatters/type-checkers in CI (Phase 22). Aligns with
  the global CLAUDE.md (clean code, SOLID, explicit null checks) adapted to Python/TS.

## Functional Requirements
### 24.1 Python (backend)
- **Formatting/lint:** black + ruff; **typing:** mypy strict; full type hints on public functions.
- **Async:** no blocking I/O on the event loop; async repos/clients; bounded pools.
- **Null/None:** explicit `is None`/`is not None` (Python idiom; the global "ObjectUtils/StringUtils"
  rule maps to explicit None/empty checks + small helpers, not Java utils).
- **SOLID/hexagonal:** domain depends on ports only; no SQLAlchemy/Redis imports in `domain/`; one
  responsibility per class/handler; small interfaces (ISP).
- **Errors:** typed domain exceptions; central mapping (Phase 18); never swallow/`except: pass`.
- **Pydantic** for all I/O; validate at the boundary; never trust client time/score.
- **Naming:** snake_case (funcs/vars), PascalCase (classes), UPPER_SNAKE (consts); descriptive, no abbr.
- **Tenant safety:** never write a raw query without an explicit tenant filter; use the scoped repo.
- **Docstrings:** modules/public functions documented as written (neutron-documentation principle).

### 24.2 TypeScript (frontend)
- **Lint/format:** eslint + prettier; **tsc strict** (no `any` without justification).
- **Components:** functional + hooks; presentational vs container separation; props typed; no business
  logic duplicated from backend (UI reflects server truth).
- **State:** server cache lib for server state; local store for UI state; no ad-hoc globals.
- **Types:** generated from OpenAPI + WS schema; do not hand-maintain API types.
- **A11y:** semantic HTML, aria where needed, keyboard support — lint with jsx-a11y + axe tests.
- **Naming:** PascalCase components, camelCase funcs/vars; files kebab/Pascal per convention.

### 24.3 Cross-cutting
- **DRY/KISS/YAGNI:** reuse via `platform/` + shared components; no speculative abstractions; simplest
  design that satisfies the AC.
- **Module boundaries:** imports obey Phase-23 rule (CI architecture test).
- **Logging:** structured, no PII/secrets; correlation id propagated (Phase 19).
- **Idempotency/at-most-once:** use the shared idempotency-hash builder + unique constraints; never
  reinvent dedupe.
- **Tests:** written with the code (same unit); negative paths included.
- **Comments:** explain *why*, not *what*; match surrounding density.

### 24.4 Git/PR conventions
- Small, focused PRs per task; conventional commit messages; PR description ties to feature/FR/UC; review
  against this standard + security baseline + spec adherence (neutron-review style); no hooks skipped.

### 24.5 Tooling/config
- Pre-commit hooks (format/lint/type); CI mirrors local; editorconfig; dependency pinning + scanning.

## Non-functional Requirements
- Consistency machine-enforced (lint/type/format) — style is not a review topic.
- Readability/maintainability prioritised over cleverness; functions small and single-purpose.

## Edge Cases
- Performance hotspots may justify a documented deviation (e.g. smallint enums) — record rationale.
- Generated code (API/WS types) excluded from some lint rules but type-checked.

## Future Considerations
- Shared lint config package; codegen pipeline for types; mutation testing on critical modules; ADR
  template for deviations.

## Risks
- **Standard drift / bikeshedding** → automate everything automatable. **Domain importing infra** →
  architecture tests catch it. **`any`/raw-SQL escape hatches** → lint + review block.

## Deliverables
- **D1** Python standards (24.1) + **D2** TypeScript standards (24.2).
- **D3** Cross-cutting rules: boundaries, idempotency, logging, tenant safety, tests (24.3).
- **D4** Git/PR + tooling/pre-commit/CI config conventions (24.4–24.5).

---
> **Next phase:** Phase 25 — Implementation.
