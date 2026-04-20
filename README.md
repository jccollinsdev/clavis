# Clavis

Clavis is a portfolio risk data platform for self-directed investors. It tracks holdings, filters news, scores downside risk, and surfaces alerts and digests.

## Repo Layout

- `backend/` FastAPI backend, background jobs, tests, and Docker setup
- `ios/` SwiftUI app and XcodeGen project
- `supabase/` database migrations and schema work
- `docs/` architecture, product, guide, and reference docs
- `scripts/` repo utilities and session bootstrap helpers
- `BACKFILL_IMPORT/` generated backfill artifacts and run traces

## Where To Edit

- Backend API and jobs: `backend/app/`
- Backend tests: `backend/tests/`
- iOS UI and models: `ios/Clavis/`
- Database changes: `supabase/migrations/`
- Product and architecture docs: `docs/`

## Dev And Prod

- Local backend: use the Docker compose stack in the repo root
- Production backend: runs on the VPS behind Cloudflare Tunnel
- iOS: generated from `ios/project.yml` with XcodeGen

## Documentation Map

- `docs/ARCHITECTURE/CODEBASE_ARCHITECTURE.md` high-level system map
- `docs/REFERENCE/repository_layout.md` file and folder guide
- `docs/REFERENCE/backend_organization.md` backend structure guide
- `docs/GUIDES/dev_prod_workflow.md` edit, test, and deploy workflow
- `docs/GUIDES/backfill_artifacts.md` generated run artifacts and trace files

## Notes

- Secrets stay local or on the VPS, never in tracked docs or source
- Generated artifacts belong in `BACKFILL_IMPORT/` and should not be hand-edited
- The product is framed as informational risk intelligence, not investment advice
