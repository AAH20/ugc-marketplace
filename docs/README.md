# UGC Marketplace — Documentation

UGC Marketplace is a **Python / FastAPI** application (not a Node.js stack).
This directory holds the supporting documentation; the authoritative project
overview and quick start live in [`../README.md`](../README.md).

## What this project actually is

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Framework | FastAPI + Uvicorn |
| Validation | Pydantic v2 |
| Database | SQLAlchemy 2.0 — SQLite by default (`app/database.py`, `app/gtm/db.py`) |
| Cache / queue | In-process (pluggable) — no external server required |
| LLM | Optional — no LLM SDK is installed by default; agent modules import provider SDKs lazily |
| Tests | pytest (`873 passing`) |
| Deploy | Docker + Helm + Kubernetes; GitHub Actions CD is provider-agnostic |

## Entrypoint & health

```bash
# Application entrypoint used by the Dockerfile and docker-compose
uvicorn app.main:app --reload --port 8000

# Health check (root path — NOT /api/v1/health)
curl http://localhost:8000/health
```

## Documentation index

| Document | Description |
|----------|-------------|
| [../README.md](../README.md) | Project overview, features, full API summary |
| [API.md](./API.md) | REST API endpoint reference |
| [api-reference.md](./api-reference.md) | Extended endpoint specifications |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Docker, Kubernetes, and Helm deployment |
| [deployment-guide.md](./deployment-guide.md) | Kubernetes-oriented deployment guide |
| [development-guide.md](./development-guide.md) | Local development workflow |
| [architecture.md](./architecture.md) | Architecture overview |
| [user-guide.md](./user-guide.md) | End-user guide |
