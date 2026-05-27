# QA Redundancy And Interaction Audit

## Redundancy findings

| Screen | Repeated info | Intentional progressive disclosure? | Why it is redundant or not | Suggested fix | Severity |
| --- | --- | --- | --- | --- | --- |
| Ticker Detail | Composite grade + score in hero, then dimension list below | yes | The hero gives headline status; dimensions add structure and deeper explanation | keep | `P3` |
| Ticker Detail | Recent news cards and key driver summary both mention similar risk narrative | yes | Driver summary condenses the thesis; article rows expose source-level detail | keep, but trim article body previews if needed | `P3` |
| Alerts | Repeated portfolio-risk alerts across days | no UI redundancy bug | The repetition comes from real daily alert generation, not duplicated rendering in one screen | keep, but consider grouping/summarizing in future | `P3` |
| Settings | account email appears twice in header | no | Name/email block plus fallback display duplicates the email when no user name exists | merge or hide duplicate subtitle when name is empty | `P2` |
| Settings | methodology section plus separate score explanation row | yes | Two distinct routes with different depth | keep | `P3` |

## Interaction audit highlights
- Before fixes, the tab shell kept all tabs alive, which triggered hidden loads and hidden writes. That created real interaction pollution and live-data risk.
- After moving to active-tab-only mounting, tab interactions became predictable and hidden preference writes stopped contaminating every launch path.
- Ticker Detail previously had fake depth via indefinite loading. After the fix, it renders the page immediately and honestly marks price-history gaps when the chart data is delayed or unavailable.
- Alerts now show real rows instead of an empty or broken state, but alert-row interaction still lacks a dedicated detail surface.

## 2026-05-27 resume-pass notes
- Ticker Detail's five dimension rows are now real `NavigationLink(value: AuditDestination)` push transitions, not sheets. There is one row per dimension, one destination per row, with a system back chevron, and zero modal stacking. The prior "Financial Health row does not open" regression is gone.
- `MethodologyDrawerSheet` is no longer reachable from Ticker Detail; the file remains in the tree but has no caller. If product later wants a "Compare all dimensions in one sheet" surface it can be wired back in.
- The Settings preferences banner (`preferencesMessage` → `DashboardErrorCard`) only renders on load or save failure, so the live success path stays uncluttered.
