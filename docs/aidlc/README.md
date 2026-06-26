# ContestForge — AIDLC Artifacts

AI-Driven SDLC phase outputs for ContestForge. One file per phase, produced and
**approved one at a time** (no phase is generated before the previous is approved).
Source of truth for *what/how* remains `docs/spec/`; these documents are the
design-process trail that builds on top of it.

## Phase index

| # | Phase | File | Status |
|---|---|---|---|
| 1 | User Personas | [phase-01-personas.md](phase-01-personas.md) | Approved |
| 2 | User Stories | [phase-02-user-stories.md](phase-02-user-stories.md) | Approved |
| 3 | Use Cases | [phase-03-use-cases.md](phase-03-use-cases.md) | Approved |
| 4 | Data Flows | [phase-04-data-flows.md](phase-04-data-flows.md) | Approved |
| 5 | High-Level Architecture | [phase-05-architecture.md](phase-05-architecture.md) | Approved |
| 6 | Base UX Framework | [phase-06-base-ux-framework.md](phase-06-base-ux-framework.md) | Approved |
| 7 | Base Backend Framework | [phase-07-base-backend-framework.md](phase-07-base-backend-framework.md) | Approved |
| 8 | Feature Decomposition | [phase-08-feature-decomposition.md](phase-08-feature-decomposition.md) | Approved |
| 9 | Task Breakdown | [phase-09-task-breakdown.md](phase-09-task-breakdown.md) | Draft — under review |
| 10 | Backend Tasks | [phase-10-backend-tasks.md](phase-10-backend-tasks.md) | Draft — under review |
| 11 | UX Tasks | [phase-11-ux-tasks.md](phase-11-ux-tasks.md) | Draft — under review |
| 12 | UI Tasks | [phase-12-ui-tasks.md](phase-12-ui-tasks.md) | Draft — under review |
| 13 | Database Design | [phase-13-database-design.md](phase-13-database-design.md) | Draft — under review |
| 14 | API Contracts | [phase-14-api-contracts.md](phase-14-api-contracts.md) | Draft — under review |
| 15 | WebSocket Contracts | [phase-15-websocket-contracts.md](phase-15-websocket-contracts.md) | Draft — under review |
| 16 | Sequence Diagrams | [phase-16-sequence-diagrams.md](phase-16-sequence-diagrams.md) | Draft — under review |
| 17 | Security Design | [phase-17-security-design.md](phase-17-security-design.md) | Draft — under review |
| 18 | Error Handling Strategy | [phase-18-error-handling.md](phase-18-error-handling.md) | Draft — under review |
| 19 | Logging & Monitoring | [phase-19-logging-monitoring.md](phase-19-logging-monitoring.md) | Draft — under review |
| 20 | Testing Strategy | [phase-20-testing-strategy.md](phase-20-testing-strategy.md) | Draft — under review |
| 21 | Deployment Architecture | [phase-21-deployment-architecture.md](phase-21-deployment-architecture.md) | Draft — under review |
| 22 | CI/CD Pipeline | [phase-22-cicd-pipeline.md](phase-22-cicd-pipeline.md) | Draft — under review |
| 23 | Folder Structure | [phase-23-folder-structure.md](phase-23-folder-structure.md) | Draft — under review |
| 24 | Coding Standards | [phase-24-coding-standards.md](phase-24-coding-standards.md) | Draft — under review |
| 25 | Implementation | [phase-25-implementation.md](phase-25-implementation.md) | Draft — under review |

Each phase document follows the fixed template: Goal · Assumptions · Functional
Requirements · Non-functional Requirements · Edge Cases · Future Considerations ·
Risks · Deliverables.

## Execution

- [Ways of Working — Backend ⇄ UI Contract Sync](ways-of-working-contract-sync.md) — the
  contract-first, parallel build playbook that keeps the backend and UI teams in sync.
