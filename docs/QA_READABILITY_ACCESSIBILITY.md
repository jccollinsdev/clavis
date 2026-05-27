# QA Readability Accessibility

## Checked
- Default text size on tested live screens is readable for the target older-investor audience
- Main tab targets are large enough
- Search results, alert rows, and holdings rows have adequate row height
- Back buttons on tested screens are visible and understandable
- Large numbers and grade badges did not clip on tested screens
- Scroll views on Today, Holdings, Search, Alerts, and Settings did not obviously trap content beneath the tab bar

## Risks

| Area | Risk | Severity | Notes |
| --- | --- | --- | --- |
| Ticker Detail news list | Dense article cards can feel visually busy | `P2` | Still readable, but cognitively heavy |
| Settings methodology | Darker presentation style breaks visual continuity | `P2` | More design-system mismatch than accessibility failure |
| Dynamic Type | Not explicitly tested in this pass | `P2` | Needs a larger-text pass before TestFlight |
| VoiceOver | Not explicitly tested in this pass | `P2` | Accessibility tree looked generally structured, but no audio pass was done |
| Search field | Keyboard-safe submission not fully audited | `P2` | Core typing worked in earlier pass, but not fully repeated here |

## Good outcomes after fixes
- Alert center now loads real data instead of appearing broken, which removes a major comprehension barrier
- Ticker Detail no longer traps users behind endless loading while waiting for chart data
- Active-tab-only mounting reduces hidden activity and makes the app feel more deterministic

## 2026-05-27 resume-pass notes
- Each dimension row is now a real navigation push, so VoiceOver reads it as a standard "button → audit view" action rather than as an opaque tap surface. The rows also carry `accessibilityIdentifier("dimension-row-<key>")` to keep future UI tests stable.
- The Ticker Detail history chip strip `1D 1W 1M 3M 1Y` continues to render on a single line at default Dynamic Type, with `1M` highlighted as the active selection.
- The Settings preferences-failure banner uses the existing `DashboardErrorCard` so it matches the rest of the app's failure-card readability conventions instead of relying on a hidden console error.
