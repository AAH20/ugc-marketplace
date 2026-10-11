# Deployment Guide — UGC Marketplace

UGC Marketplace is a Python/FastAPI application. The Docker image, docker-compose
stack, Helm chart, and Kubernetes manifests are all in this repository.

## Container image

```bash
docker build -t ugc-marketplace:local .
docker run -p 8000:8000 ugc-marketplace:local
curl http://localhost:8000/health
```

The image runs `uvicorn app.main:app` on port `8000` (see `Dockerfile`).

## Docker Compose

```bash
docker compose up -d          # app, db (optional), redis (optional), nginx
curl http://localhost:8000/health
```

The `app` service defaults to SQLite; `db`/`redis` are optional and only used
when `DATABASE_URL`/`REDIS_URL` point at them.

## Kubernetes (Helm)

```bash
helm install ugc-marketplace ./helm/ --namespace ugc-marketplace --create-namespace
```

`k8s/` holds kustomize base + overlays (`development`, `production`).

## Continuous Delivery (GitHub Actions)

- `.github/workflows/cd.yml` — **cloud-provider agnostic**: multi-arch build
  pushed to GHCR, SBOM (`anchore/sbom-action`), Trivy scan, and a smoke test
  that boots the pushed image and asserts `GET /health` returns 200. No cloud
  secrets required.
- `.github/workflows/deploy.yml` — builds the image and wires staging/production
  deploy jobs that target **AWS ECS**; those jobs run only on a manual
  `workflow_dispatch` and require `secrets.AWS_ACCESS_KEY_ID` /
  `secrets.AWS_SECRET_ACCESS_KEY`.
