# Backfill Artifacts Guide

Backfill runs produce a lot of debug output. This repository keeps those outputs in a dedicated folder so they do not get mixed with source code.

## Location

- `BACKFILL_IMPORT/<analysis_run_id>/`

## Typical Contents

- `manifest.json` run metadata
- `feeds/` raw and normalized feed data
- `stages/` stage-by-stage pipeline snapshots
- `positions/` per-ticker analysis payloads
- `llm_calls/` model request and response traces
- `summary.json` or `final_outputs.json` run-level summaries

## How To Use It

1. Start with `manifest.json`
2. Read the stage files in order
3. Inspect one ticker folder when debugging a bad output
4. Cross-check `llm_calls/` if model behavior looks wrong

## Rules

- Do not treat these as source files
- Do not manually edit captured artifacts unless you are intentionally curating a forensic example
- Keep real code changes in `backend/app/`, `ios/Clavis/`, or `supabase/migrations/`
