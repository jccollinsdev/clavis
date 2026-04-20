# Backend Organization

This backend is structured to keep web routes, integrations, and background analysis separate.

## Folder Roles

- `backend/app/main.py` creates the FastAPI app and attaches routers and middleware
- `backend/app/routes/` contains request handlers grouped by domain
- `backend/app/services/` contains reusable integrations and helper services
- `backend/app/pipeline/` contains the long-running analysis and refresh workflows
- `backend/app/scripts/` contains command-line entry points for operational tasks
- `backend/app/models/` contains typed data models used by the backend
- `backend/tests/` contains tests for route behavior, parsing, and pipeline helpers

## Recommended Editing Rules

- Put HTTP behavior in `routes`
- Put database or third-party integration code in `services`
- Put multi-step analysis and scheduling logic in `pipeline`
- Put one-off operational entry points in `scripts`
- Keep tests adjacent to the behavior they protect

## Production Structure

- The backend is expected to run in Docker
- Production should use the VPS deployment path, not local process state
- Secrets belong in `backend/.env` on the VPS or in local secret storage
- Generated runtime artifacts should stay out of the main application directories

## Backend Touch Points

- User API surfaces: holdings, positions, digest, alerts, preferences, news, tickers
- Admin/operator surfaces: admin dashboard, S&P backfill, cache status, manual refreshes
- Background jobs: scheduler, cache refresh, backfill orchestration, digest generation

## When Adding New Code

- Add the smallest new module that fits the concern
- Prefer extending existing route groups before creating new top-level patterns
- Keep naming consistent with the current split between route, service, and pipeline layers
