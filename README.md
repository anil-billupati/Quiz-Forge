# ContestForge

A multi-tenant live contest/quiz engine supporting Standard, Speed, and
Elimination modes with server-authoritative timing, scoring, wildcards,
leaderboards, and elimination — durable under partial failure, built for up to
10,000 concurrent participants.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI (API, WebSocket gateway, engine workers) |
| Frontend | Next.js + TypeScript |
| Data | PostgreSQL (authoritative), Redis (cache, pub/sub, Streams bus) |
| Cloud | AWS (deployment-agnostic containers — ADR-003) |

## Repository layout

```
backend/      FastAPI service + engine workers (app/, migrations/, tests/)
frontend/     Next.js web app (src/app, components, lib, tests)
docs/         kickoff, spec/, plan/, adr/
.neutron/     local security/integrations/environment context
.github/      CI/CD workflows
infra.yaml    infrastructure descriptor for the DevOps tool
docker-compose.yml   local Postgres + Redis + API
```

## Prerequisites

- Python 3.12+
- Node.js 22+
- Docker (for local Postgres + Redis)

## Run locally

### 1. Start datastores + API
```bash
docker compose up
```

### Backend (without Docker)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head            # once migrations exist (Unit 1)
uvicorn app.main:app --reload   # http://localhost:8000  (docs at /docs)
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev                     # http://localhost:3000
```

## Run tests

```bash
# Backend
cd backend
pytest                 # unit + integration (integration uses testcontainers)
ruff check . && mypy app

# Frontend
cd frontend
npm test               # unit/component (Vitest)
npm run test:e2e       # end-to-end (Playwright)
```

## Documentation

- **Specification:** [docs/spec/](docs/spec/) — product, technical, API
  contracts, domain model, testing strategy.
- **Architecture & ADRs:** [docs/plan/architecture.md](docs/plan/architecture.md),
  [docs/adr/](docs/adr/).
- **Delivery status / next unit:** [docs/plan/delivery-plan.md](docs/plan/delivery-plan.md).
