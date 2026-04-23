# Clavis iOS Page Map

This is a screen-by-screen reference for the current iOS app. It focuses on what is actually rendered on each screen today, including content blocks, controls, loading/error states, and navigation.

## App Shell

- App entry is `ContentView`.
- Auth gate order:
  - Not signed in: `LoginView`
  - Signed in, onboarding incomplete: `OnboardingContainerView`
  - Signed in, onboarding complete: `MainTabView`
- Main tabs today:
  - Home
  - Holdings
  - Digest
  - Alerts
  - Settings
- `NewsView` still exists, but it is not part of the bottom tab bar.

## Login Screen

### `LoginView`

Purpose: sign in or create an account.

What is on screen:
- App logo image
- Large `CLAVIX` wordmark
- Tagline: `Portfolio intelligence for self-directed investors`
- Email text field
- Password secure field
- Sign-in / sign-up primary button
- Toggle button to switch between sign in and sign up mode
- `Forgot password?` action
- Inline error message area
- Inline status message area

Behavior:
- The primary button switches between `Sign In` and `Create Account` depending on mode.
- Password field uses `.password` or `.newPassword` content type depending on mode.
- The primary button is disabled when email or password is empty, or while loading.
- `Forgot password?` sends a password reset for the entered email.
- The whole screen uses a dark background and card-like form container.

## Onboarding Flow

### `OnboardingContainerView`

Purpose: collect first-run profile and preferences before the main app.

What is always visible:
- Dark background
- Progress header showing current step and total steps
- One step view at a time

Steps:
- Welcome
- Date of birth
- Risk acknowledgment
- Preferences
- Brokerage

Other behavior:
- The brokerage step can open a Safari sheet for SnapTrade.
- A SnapTrade callback notification is handled in the background.
- The keyboard safe area is ignored at the bottom so form fields stay usable.

### Welcome Step

What is on screen:
- Small boxed `C` brand mark
- Headline: `Portfolio risk, measured.`
- Intro copy explaining the product answers three questions:
  - how risky is my portfolio
  - what changed
  - what should I look at first
- Name input field labeled `YOUR NAME`
- `Get started` button

Behavior:
- The name field is focused automatically if empty.
- `Get started` is disabled until a name is entered.

### Date of Birth Step

What is on screen:
- Title: `Date of birth`
- Supporting copy explaining age verification
- Compact date picker
- A formatted readout of the selected date
- Age-gate note stating the user must be at least 18
- `Continue` button
- `Back` button

Behavior:
- The date picker is capped at 18 years ago from today.
- The step is used only to derive age verification / birth year storage.
- `Continue` is disabled until the selected DOB is valid.

### Risk Acknowledgment Step

What is on screen:
- Title: `One thing before we begin.`
- Informational disclosure copy
- A bordered notice card titled `Risk acknowledgement`
- Additional disclaimer text about past scores not predicting future results
- A checkbox-style acknowledgment row
- `Agree & continue` button
- `Back` button

Behavior:
- The acknowledgment checkbox must be selected before continuing.
- The text explicitly frames the app as informational only.

### Preferences Step

What is on screen:
- Title: `Pick what wakes you up.`
- Supporting copy saying settings can be changed later
- Four toggle cards:
  - Morning digest
  - Grade changes
  - Major events
  - Large price moves
- `Continue` button
- `Back` button
- Inline error area if preferences save fails

Behavior:
- Toggling here initializes notification and digest preferences.
- The step is positioned as a quick setup rather than a full settings page.

### Brokerage Step

What is on screen:
- Title: `Connect your brokerage`
- Supporting copy describing SnapTrade as optional and read-only
- An info/notice card that changes based on connection state
- Optional inline info message
- Optional inline error message
- One of two action layouts:
  - Connected state: `Open Clavix`, `Sync holdings now`, `Back`
  - Not connected state: `Connect brokerage`, `I'll add manually for now`, `Back`

Behavior:
- If connected, the notice card shows the primary connected institution.
- If not connected, the user can skip brokerage and continue manually.
- `Sync holdings now` triggers a refresh without leaving onboarding.
- `Open Clavix` completes onboarding.

## Main Tab Shell

### `MainTabView`

What it provides:
- Native bottom tab bar
- Dark styling for nav and tab bar chrome
- Deep-link handling for opening digest or ticker detail from notifications

Tabs:
- Home
- Holdings
- Digest
- Alerts
- Settings

Behavior:
- A digest notification switches to the Digest tab.
- A position or analysis notification switches to Holdings and passes a ticker for detail opening.

## Home Screen

### `DashboardView`

Purpose: quick at-a-glance portfolio triage.

What is on screen:
- Top header
- Offline status banner when offline
- Loading card while data is first loading
- Active analysis run status card when a run is queued or running
- Error card for load failures
- Main hero card with refresh and run-analysis actions
- Stat strip
- Empty state if there are no holdings
- Needs-attention card when risky positions exist
- `What changed` card
- Digest teaser card

Behavior:
- Pull-to-refresh reloads dashboard data.
- Initial load happens automatically when the screen appears.
- If there are no holdings, the page swaps into a simpler empty state.
- The hero card exposes both refresh and analysis-triggering actions.
- `openHoldings` from the empty state switches to the Holdings tab.
- `openDigest` from the teaser switches to the Digest tab.

## Holdings Screen

### `HoldingsListView`

Purpose: manage positions, watchlist items, and ticker discovery.

What is on screen:
- Top header with add and refresh actions
- Search bar for holdings and ticker search
- Holdings summary card
- Offline banner when needed
- Error card for load failures
- Loading card while holdings load
- Ticker search results card when search text is present
- Empty state when there are no holdings
- Holdings control card with sort and filter controls
- Watchlist section
- Needs review section
- All holdings section
- Add-position sheet
- Ticker search sheet
- Full-screen progress sheet for adds
- Delete-position alert

What the screen shows in detail:
- The summary card surfaces counts and freshness/sync timing.
- The watchlist section lists watchlisted tickers as navigation rows.
- The needs-review section highlights holdings that have deteriorated or sit in high-risk grades.
- The all-holdings section shows every holding in a sorted list with inline sort control.
- Search results are ranked so exact ticker matches come first, then prefix matches, then broader matches.

Behavior:
- Typing in the search bar triggers ticker search after a short delay.
- Tapping a search result toggles watchlist state.
- Holding rows support:
  - opening ticker detail
  - context-menu star/unstar
  - context-menu delete
  - swipe-to-delete
  - leading-swipe star/unstar
- The add-position sheet and ticker-search sheet are separate flows.
- Deep links can open a specific ticker detail row automatically.

## Digest Screen

### `DigestView`

Purpose: show the day’s portfolio summary and supporting narrative.

What is on screen:
- Top header with quick link back to Holdings
- Offline banner when needed
- Active run status card
- Error card with reload action
- Timeout card if loading was slow or incomplete
- Digest hero card
- Macro section
- Sector overview section
- Position impacts section
- What matters section
- Watchlist alerts section
- What to watch section
- Full narrative section
- Empty state card when no digest exists yet
- Loading card when digest is still loading

Behavior:
- The Digest tab loads when selected, not eagerly on every app launch.
- Pull-to-refresh reloads the digest from the database.
- If nothing is available and no run is active, the screen shows an idle state instead of an error.

## Alerts Screen

### `AlertsView`

Purpose: review alert history and recent changes.

What is on screen:
- Top header
- Offline status banner
- Error card
- Loading card while alerts load
- Empty state when no alerts exist
- Alerts summary grid
- Filter chip row
- Timeline-style alert feed

Behavior:
- Alerts are loaded on first visit to the tab.
- The filter chips change the visible subset of the timeline.
- The timeline can deep-link into a related position or ticker detail when available.

## Settings Screen

### `SettingsView`

Purpose: manage preferences, account actions, legal links, and brokerage settings.

What is on screen:
- Wordmark header with subtitle `Preferences and account`
- Offline banner when offline
- Digest settings group
- Brokerage settings group
- Alerts settings group
- Notification settings group
- Account settings group
- About section
- Disclaimer card
- Sign-out button group
- Delete-account confirmation alert

Account group includes:
- email
- plan label when available
- account status message
- export account action
- delete account action

Behavior:
- The screen loads settings and brokerage status on first appearance.
- Delete account opens a destructive confirmation dialog.
- Confirming deletion signs the user out after the account request succeeds.
- If subscription tier is `pro` or `admin`, the plan label appears as `Clavix Pro` or `Admin`.

## Ticker Detail

### `TickerDetailView`

Purpose: provide the richest single-asset view for held or searched tickers.

What is on screen:
- Wordmark header with ticker and company subtitle
- Inline nav bar with back, watchlist toggle, and refresh
- Error card
- Loading card while the snapshot loads
- Hero card with:
  - ticker
  - company name
  - sector or industry
  - risk grade
  - score
  - previous score if available
  - rationale text
- Risk dimensions card
- Price card with current price, change text, direction, and selectable history horizon
- Held-position analysis refresh card when the ticker is already in holdings
- Fundamentals metric grid
- Risk score rationale card
- Event analyses card
- Urgent watch-items list
- Recent news list
- Recent alerts list

Behavior:
- The initial load fetches both ticker detail and price history.
- The refresh button is only available for Pro or Admin users.
- The watchlist button toggles between watched and unwatched state.
- Changing the price-history window reloads chart data.
- Held tickers can trigger a full analysis refresh from this screen.

Important detail:
- If AI dimensions exist, the risk-dimension card uses them first.
- If not, it falls back to the older score-based dimension fields.

## Article Detail

### `ArticleDetailView`

Purpose: show one news item in full.

What is on screen:
- Top bar with source title and back action
- Error card
- Loading card while the article loads
- Article header card
- Article body card
- Impact card when impact text exists
- Related alerts card when alerts exist
- Ticker detail link when the article has a related ticker

Behavior:
- The screen loads article data on appearance.
- Pull-to-refresh reloads the article.
- The ticker link opens the shared ticker detail screen.

## Legacy Position Detail

### `PositionDetailView`

Purpose: resolve a position ID into the ticker detail screen.

What is on screen:
- Nothing long-term unless resolution fails
- A skeleton/loading view while resolving
- An error message if the position cannot be resolved

Behavior:
- Once the position ID is resolved, the screen immediately shows `TickerDetailView` for that ticker.
- This is effectively a bridge screen, not a destination UX.

## News Screen

### `NewsView`

Purpose: browse portfolio and market stories.

What is on screen:
- Top bar with back action and subtitle showing recency
- Error card
- Horizontal category filter chips
- Loading card while stories load
- Hero story card
- `More stories` list section
- Empty state card when no stories exist

Filter chips:
- All
- Portfolio
- Watchlist
- Market
- Major

Behavior:
- The count shown on each chip comes from the loaded story counts when available.
- The hero story opens article detail.
- Additional stories are shown below in a card stack.
- This screen is currently not part of the bottom tab bar, so it is reached through links or older flows.

## Quick Routing Summary

- `ContentView` decides auth state and onboarding completion.
- `MainTabView` owns the main five-tab app shell.
- `DashboardView` links into Holdings and Digest.
- `HoldingsListView` links into `TickerDetailView`.
- `DigestView` is mostly self-contained, with a shortcut back to Holdings.
- `AlertsView` can deep-link into ticker or position detail.
- `NewsView` links into `ArticleDetailView`.
- `ArticleDetailView` links into `TickerDetailView`.
- `PositionDetailView` resolves into `TickerDetailView`.

## Reference Notes

- This doc reflects the current code, not the intended roadmap.
- Screen names can differ a little from the tab labels, but the content above matches the current implementation.
- If you want, this can be expanded next into a second doc that maps each screen to its view model and backend endpoints.
