# MVP deployment: Compose versus K3s

## Superseded Deployment Recommendation

The operator subsequently chose no Docker: local Vite/FastAPI and production
host Nginx plus systemd. The historical comparison below does not authorize
restoring Compose or container manifests. Use `../design.md`,
`../../09-23-novelai-compose/implement.md` and
`.trellis/spec/backend/deployment-contract.md` for the current contract.

## Original Research (2026-09-23)

Checked 2026-09-23 against primary documentation:

- Docker documents running Compose in production on a single server, including
  production overrides, restart policies, and rebuilding/recreating individual
  services: https://docs.docker.com/compose/how-tos/production/
- Docker volumes persist data outside container lifecycle; volume storage still
  needs a deliberate backup/recovery plan:
  https://docs.docker.com/engine/storage/volumes/
- K3s has its own minimum hardware requirements (server 2 cores/2 GB RAM,
  excluding application workloads): https://docs.k3s.io/installation/requirements

Recommendation (approved for the MVP on 2026-09-23): package web and API in separate
images, use Docker Compose locally and for an initial single-server deployment,
with persistent storage, backup/recovery, secret handling, HTTPS termination,
health checks, and versioned images. Do not create Kubernetes/K3s manifests
until an actual cluster or scaling/availability requirement exists. A single
server is a single point of failure; K3s alone does not back up this product's
local SQLite parameter history, which needs independent backup in either case.
