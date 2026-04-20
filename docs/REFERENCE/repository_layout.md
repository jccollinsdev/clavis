# Repository Layout Reference

This is the working map for the codebase. It is meant to answer one question fast: where should a change go?

## Top Level

- `backend/` server, jobs, API routes, tests, and containerization
- `ios/` SwiftUI client app and generated Xcode project
- `supabase/` schema migrations and database seed work
- `docs/` project documentation and operating references
- `scripts/` repo utilities, bootstrap scripts, and maintenance helpers
- `BACKFILL_IMPORT/` saved run artifacts from backfill executions

## Backend

- `backend/app/main.py` app bootstrap and route wiring
- `backend/app/routes/` HTTP endpoints grouped by concern
- `backend/app/services/` shared integrations and auth helpers
- `backend/app/pipeline/` background jobs, analyzers, and scoring logic
- `backend/app/scripts/` command-line entry points for background workflows
- `backend/tests/` backend test suite

## iOS

- `ios/Clavis/App/` app shell, theme, and root navigation
- `ios/Clavis/Views/` feature screens organized by domain
- `ios/Clavis/ViewModels/` state and API coordination
- `ios/Clavis/Models/` data models and decoding helpers
- `ios/Clavis/Services/` client-side API and auth services
- `ios/Clavis/Resources/` assets, fonts, and plist files

## Docs

- `docs/ARCHITECTURE/` system-level and workflow architecture
- `docs/GUIDES/` operational and implementation guides
- `docs/PRODUCT/` product behavior, framing, and methodology
- `docs/REFERENCE/` durable reference docs for contributors
- `docs/STATUS/` current status, roadmap, and active session memory

## Generated Artifacts

- `BACKFILL_IMPORT/` contains captured backfill run inputs, stage outputs, LLM calls, and per-ticker analysis payloads
- Treat these as historical artifacts, not source files
- If you need to inspect one, read the manifest for the run first

## Change Routing

- API behavior changes usually belong in `backend/app/routes/`
- Shared business logic belongs in `backend/app/services/` or `backend/app/pipeline/`
- UI changes belong in `ios/Clavis/Views/` and `ios/Clavis/ViewModels/`
- Cross-cutting project decisions belong in `docs/ARCHITECTURE/` or `docs/STATUS/`
