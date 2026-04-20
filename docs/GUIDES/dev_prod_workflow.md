# Dev And Prod Workflow

This guide keeps day-to-day editing predictable across local development and production deployment.

## Development

1. Make backend changes under `backend/app/`
2. Make iOS changes under `ios/Clavis/`
3. Keep schema changes in `supabase/migrations/`
4. Update docs in `docs/` when the system shape changes
5. Run the relevant local checks before asking for deploy help

## Production

- Production backend runs on the VPS behind Cloudflare Tunnel
- Do not edit production-only secrets in tracked files
- Use the repo as the source of truth for code and docs, not the server filesystem

## Editing Rules

- Route changes: `backend/app/routes/`
- Shared business logic: `backend/app/services/` or `backend/app/pipeline/`
- UI and view state: `ios/Clavis/Views/` and `ios/Clavis/ViewModels/`
- Product decisions and architecture notes: `docs/`

## Generated Files

- `BACKFILL_IMPORT/` stores captured backfill artifacts and trace files
- These files are useful for debugging and audits, but they are not hand-authored source
- When a run matters, document it in `docs/STATUS/project_state.md` or a dedicated reference doc

## What To Keep Stable

- Public API shape
- Database migration history
- Production secrets handling
- The distinction between app source, docs, and generated artifacts
