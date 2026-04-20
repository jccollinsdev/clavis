#!/bin/bash
# Print the current Clavis session context.

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

printf '%s\n' "Clavis session start"
printf '%s\n' "- Read: AGENTS.md"
printf '%s\n' "- Read: docs/STATE/project_state.md"
printf '%s\n' "- Read: docs/STATUS/roadmap.md"
printf '%s\n' ""
printf '%s\n' "Current state file:"
sed -n '1,80p' "$ROOT_DIR/docs/STATE/project_state.md"
