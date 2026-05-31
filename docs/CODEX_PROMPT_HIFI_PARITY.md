# Codex Prompt — Clavix iOS Hi-Fi Live Parity Port

Paste the section below into a fresh Claude / Codex session that has the
Clavix repo at `/Users/sansarkarki/Documents/Clavis` and the iOS simulator
available via `mcp__xcode__*` tools.

---

## Goal

Port every live SwiftUI tab in `ios/Clavis/Views/` to match its
`ClavixVisualQA<Screen>` counterpart in `ios/Clavis/App/ClavixVisualQA.swift`,
wired to real view-model data, atom-for-atom. The VQA file is the design
canon for *layout*; `docs/CLAVIX_TRUTH.md` is the canon for *what the
product is and what data is real*. When the two disagree, CLAVIX_TRUTH wins.

The punch list of routes, classifications, and per-route port plans lives
in `docs/HIFI_LIVE_PARITY_GAP.md`. Work through it section by section.

## The five fixed dimensions

Equal-weighted. Never four, never six. Never invent a sixth.

1. **Financial Health** — `FIN`
2. **News Sentiment** — `NEWS`
3. **Macro Exposure** — `MAC`
4. **Sector Exposure** — `SEC`
5. **Volatility** — `VOL`

## Hard rules (do not violate any of these)

1. **Never fabricate previous scores or deltas.** If `score_delta == nil`,
   render `—` or "New". Never display `current − 8` or any synthetic value.
   CLAVIX_TRUTH §8 is explicit.
2. **Never rename internal `Clavis*` symbols.** The Swift module is
   `Clavis`, the directory is `ios/Clavis/`, the type prefix is `Clavis*`.
   User-facing brand strings are "Clavix". Do not touch the internal
   identifiers.
3. **User-visible brand is always "Clavix".** Banned UI strings: `Clavis`,
   `Clavynx`, `SnapTrade`, `MiroFish`, "Shared ticker cache", or any raw
   backend status string surfaced via `.capitalized`.
4. **Banned vocabulary in user-visible copy** (per CLAVIX_TRUTH §2):
   *coverage, monitor, momentum, analyst, research, thesis, provisional,
   current read, recommendation, suggest, advise, predict, forecast.*
   Use instead: *rating, track, trend, data, evidence, signal, change,
   observation.* `String.clavixVocabSafe` in
   `ios/Clavis/App/DisplayText.swift` already enforces this whole-word
   for backend-leaked strings; route any new dynamic strings through it.
5. **The five dimensions are fixed and equal-weight.** See above.
6. **Never invent fixture data as a workaround.** If a VQA element
   ("T1/T2/T3 source mix", "was 67 · 5 days ago", "Composite −1 vs last
   week") depends on a field the backend does not ship, render `—` /
   "Unavailable" and add (or cross-reference) a backlog item.

## Work loop (per screen)

Repeat until every PORTABLE and PARTIAL screen in
`docs/HIFI_LIVE_PARITY_GAP.md` is landed (STRUCTURAL screens stay parked
with their backlog row).

1. **Pick the next screen** from `docs/HIFI_LIVE_PARITY_GAP.md`. Read the
   per-route "Port plan" carefully before opening any Swift file.
2. **See the target.** Boot the sim with the VQA mock at the route key:
   ```
   mcp__xcode__stop_app_sim()
   mcp__xcode__launch_app_sim(env={
     "CLAVIX_USE_VQA_MOCK": "1",
     "CLAVIX_DEBUG_OPEN": "<route-key>"   # e.g. "ticker", "alert-detail"
   })
   mcp__xcode__screenshot(returnFormat="path")
   ```
3. **See the live counterpart.** Boot normally with the debug bypass (see
   "Local debug JWT" below for minting `/tmp/clavix_debug_jwt_7ff` if
   missing):
   ```
   mcp__xcode__stop_app_sim()
   mcp__xcode__launch_app_sim(env={
     "CLAVIX_DEBUG_BYPASS_AUTH": "1",
     "CLAVIX_DEBUG_JWT": <contents of /tmp/clavix_debug_jwt_7ff>,
     "CLAVIX_DEBUG_USER_ID": "7ff5a6c5-8e49-4c2f-be1c-bdc869926699"
   })
   ```
   Or use the launch arguments form when invoking through `xcodebuild`:
   `--clavix-debug-auth-bypass --clavix-debug-jwt $(cat
   /tmp/clavix_debug_jwt_7ff) --clavix-debug-user-id
   7ff5a6c5-8e49-4c2f-be1c-bdc869926699`. Tap to the relevant tab/screen
   and screenshot.
4. **Verify the atoms.** Confirm the live view uses the production atoms
   from `ios/Clavis/Views/Shared/Components/ClavixVQAComponents.swift`:
   `ClavixScreen`, `ClavixLargeHeader`, `ClavixEyebrow`, `ClavixCard`,
   `ClavixSection`, `ClavixGradeBadge`, `ClavixScoreBar`, `ClavixPill`,
   `ClavixColumnHeader`, `ClavixMiniSpark`, `ClavixTabBar`. The VQA file
   uses `VQA*`-prefixed private mirrors — never reach into the VQA file
   from production code.
5. **Port one screen.** Edit the relevant `Views/.../*.swift` file
   per the port plan. Swap `VQA*` → `Clavix*` in your mental mapping, bind
   the view model's `@Published` fields to the exact element the VQA
   shows, and route any missing field through an honest "Unavailable" or
   `—` placeholder.
6. **Build.**
   ```
   xcodebuild \
     -workspace ios/Clavis.xcodeproj/project.xcworkspace \
     -scheme Clavis \
     -destination 'platform=iOS Simulator,name=iPhone 17' build
   ```
   Or via the MCP tool: `mcp__xcode__build_sim()` (run
   `mcp__xcode__session_show_defaults()` first to confirm the project /
   scheme / simulator).
7. **Install + relaunch.** After every build:
   `mcp__xcode__install_app_sim(appPath=…)` then
   `mcp__xcode__launch_app_sim()`. Do not skip — `launch_app_sim()` alone
   re-runs the installed binary, which is stale.
8. **Screenshot live vs VQA.** Save both to
   `docs/screenshots/qa/qa-parity-<screen>.jpg`. Read them back with
   `Read(<path>)` and compare visually — colors, font (mono / serif /
   Inter), spacing, corner radius (cards 10, controls 7, badges 3), badge
   sizes, alignment, missing or extra elements.
9. **Iterate** on the SwiftUI view until the live screen matches the VQA
   mock at default Dynamic Type. Then move on to the next screen.

## Build / install / launch reference

- Build target: iPhone 17 simulator (the project's default).
- App path after build:
  `~/Library/Developer/Xcode/DerivedData/Clavis-gwrxdzeojwrjhbglmivjzniaqokb/Build/Products/Debug-iphonesimulator/Clavis.app`
- Bundle ID: `com.clavisdev.portfolioassistant`
- Always `mcp__xcode__session_show_defaults()` once at session start before
  the first `mcp__xcode__build_run_sim()` call.

## Local debug JWT

If `/tmp/clavix_debug_jwt_7ff` is missing, mint a fresh 8-hour JWT using
the Supabase service-role secret stored in `backend/.env`. Never commit
this token; it is local only.

```bash
python3 - <<'PY'
import os, time, json, hmac, hashlib, base64, pathlib

env = pathlib.Path("backend/.env").read_text()
secret = next(
    line.split("=", 1)[1].strip()
    for line in env.splitlines()
    if line.startswith("SUPABASE_JWT_SECRET=")
)

def b64url(payload):
    return base64.urlsafe_b64encode(payload).rstrip(b"=")

header  = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
now     = int(time.time())
payload = b64url(json.dumps({
    "iss":   "supabase",
    "ref":   "uwvwulhkxtzabykelvam",
    "role":  "authenticated",
    "sub":   "7ff5a6c5-8e49-4c2f-be1c-bdc869926699",
    "aud":   "authenticated",
    "iat":   now,
    "exp":   now + 8 * 3600,
}, separators=(",", ":")).encode())
sig     = b64url(hmac.new(secret.encode(), header + b"." + payload, hashlib.sha256).digest())
token   = (header + b"." + payload + b"." + sig).decode()

pathlib.Path("/tmp/clavix_debug_jwt_7ff").write_text(token)
print(token)
PY
```

The token is valid for the seeded test user
`7ff5a6c5-8e49-4c2f-be1c-bdc869926699`. Re-run when it expires.

## Acceptance criteria per screen

A screen is "landed" when all of the following are true:

- The live screen visually matches the VQA mock at default Dynamic Type,
  inspected via side-by-side screenshots.
- Every real field renders from the view model — no hand-coded fixture
  strings except where the VQA reference itself is a static label
  (eyebrows, methodology pipeline descriptors, grade-band reference table).
- Missing fields render honest `—` or "Unavailable" — never fabricated.
- `xcodebuild` passes with no new warnings of substance.
- A `docs/screenshots/qa/qa-parity-<screen>.jpg` capture exists.
- No banned vocabulary in any user-visible string introduced by the diff.
- No new `Clavis*` user-facing string introduced; "Clavix" everywhere
  user-visible.

## Stop conditions

You may stop the loop when:

- Every PORTABLE and PARTIAL screen in `docs/HIFI_LIVE_PARITY_GAP.md` is
  either landed or explicitly parked behind a backlog row that already
  exists (cross-reference the row number in the PR description).
- Every STRUCTURAL screen has a corresponding row in `backlog.md` under
  the 2026-05-27 section (these already exist as items 21–30).
- `xcodebuild` is green.
- `grep -rnE "Clavis(?!Typography|Theme|Copy|Atmosphere|DesignSystem|Loading|PrimaryButton|StandardCard|SecondaryCard|App)" ios/Clavis/Views/`
  returns no user-facing string leaks.
- No fabricated scores, no fake "was N" or "−N from yesterday" values.

## Commit cadence

Commit incrementally — one PR per ~3-5 screens. Use the standard footer:

```
ios: <imperative one-line summary, lowercase, no period>

<body explaining what shipped and what is still parked, two or three
short paragraphs at most>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

For each PR:

1. Stage only the specific files you touched plus any new screenshot you
   produced under `docs/screenshots/qa/`. Never `git add -A` from the
   repo root — `BACKFILL/` is large and untracked.
2. Run `git status` after the commit; verify no `.env`, no JWT files, no
   `apns.p8` keys, and no `BACKFILL_IMPORT/` made it in.
3. Push to `main` unless the user instructs otherwise. GitHub Actions
   deploy is currently a no-op (missing `PROD_SSH_KEY`) so the push is
   safe; backend changes require the manual rsync described in
   `docs/AGENT_HANDOFF_HIFI_PARITY.md` §5.

## Reference docs to keep open while working

- `docs/HIFI_LIVE_PARITY_GAP.md` — the per-screen punch list.
- `docs/AGENT_HANDOFF_HIFI_PARITY.md` — design tokens, atom inventory,
  build dance, banned vocabulary, session log.
- `docs/CLAVIX_TRUTH.md` — product truth; settles every "should it look
  like this?" question against "is the data even real?".
- `backlog.md` — the persistent record of backend gaps. The 2026-05-27
  section (items 21–30) is the contract you ship against.
