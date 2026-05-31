# Clavix v1 Launch Scope — Decision Record

**Date:** 2026-05-31
**Status:** Authoritative for v1 launch scope. Amends `CLAVIX_TRUTH.md` §11 and §16 (Truth bumped to v2.1).
**Owner decision:** Self-directed investor app, launch lean, **no brokerage integration in v1.**

---

## 1. Scope decision: brokerage is OUT of v1

**Decision:** Clavix v1 launches **without any brokerage / automatic position sync** (no SnapTrade, no Plaid, no Alpaca). Reason: legal/admin/EIN exposure from handling brokerage-linked financial account data is not acceptable for the launch window.

**Rules this imposes:**
1. **Brokerage is NOT required for Pro.** Pro's value is depth, history, alerts, and audit — not account sync.
2. **No working brokerage CTA may ship.** Every brokerage entry point (onboarding step, Holdings "Connect/Refresh from brokerage", Settings "Connected brokerage", empty-state "Connect brokerage" button) must be either **removed** or **clearly labeled "Coming later"** and non-functional (no portal launch).
3. **No user-visible copy implies brokerage works today.** Website, App Store metadata, paywall, onboarding — none may promise brokerage sync as a current feature.
4. Backend `/brokerage/*` endpoints and the SnapTrade config may **remain in code** (internal, dormant) but must not be reachable from a shipping CTA.
5. **Privacy Policy fix:** the live policy names "Plaid or Alpaca" as the brokerage processor. Since brokerage is deferred, the brokerage data-handling paragraph should be **removed or rewritten to "not offered at this time"** rather than naming any processor.
6. **CSV import becomes the primary "bulk add" path** for users with many positions (manual, no third-party financial-account linkage, low legal exposure). It is a Pro lever (see below) — but only ship it when actually implemented; otherwise label "Coming later."

**What replaces the lost convenience:** Without auto-sync, Pro must justify $20/mo on *depth* (verbose briefing, full history, advanced alerts, audit depth, export) and *capacity* (unlimited holdings/watchlist), plus CSV import for bulk entry when ready.

---

## 2. Revised Free vs Pro value split (replaces Truth §16 table)

Positioning: **Free is genuinely useful and fully trustworthy** (you can see and audit every rating). **Pro is "depth, history, and a real morning briefing."** The methodology/transparency moat stays free — that is the trust pitch and the SEO/marketing engine. Pro deepens it, it does not gate the basics.

| Capability | Free | Pro | Build status |
|---|---|---|---|
| Sign up / sign in / onboarding | ✓ | ✓ | shipped |
| Manual holdings | ✓ **up to 3** | ✓ **unlimited** | shipped (gate is UI-only; add backend enforcement) |
| Watchlist | ✓ **up to 5** | ✓ **unlimited** | shipped |
| CSV import (bulk add positions) | — | ✓ | **NOT built — label "Coming later" until done** |
| Universal search + ticker detail | ✓ | ✓ | shipped |
| Five-dimension scores + grade | ✓ | ✓ | shipped |
| **Methodology drill-down** (formula, current inputs, grade rationale) | ✓ | ✓ | shipped — **stays free (trust moat)** |
| Deeper audit (per-dimension 90-day history, regression coefficients + R², per-article sentiment reasoning, audit export) | — | ✓ | partial — needs history depth + export |
| Recent news per ticker | ✓ **last 7 days** | ✓ **last 30 days** | shipped (after relevance fix) |
| Score history | ✓ **30-day composite** | ✓ **90-day, all 5 dims, sparklines** | shipped (history accrual ongoing) |
| Morning digest — Brief + Standard | ✓ | ✓ | shipped (pipeline freshness fix pending) |
| Morning digest — **Verbose** | — | ✓ | shipped (gate) |
| Manual ticker refresh | — | ✓ **5/day/ticker** | needs build/verify |
| Grade-change alerts (holdings) | ✓ | ✓ | shipped (generation freshness pending) |
| Major-news alerts (holdings) | ✓ | ✓ | shipped |
| **Advanced alerts** — watchlist, macro-shock, portfolio-grade-change, severity threshold | — | ✓ | partial |
| Email digest of alerts | — | ✓ | **needs SMTP — label "Coming later" until wired** |
| Portfolio & score-history CSV export | — | ✓ | needs build |
| Account data export (rights-based) + delete account | ✓ | ✓ | shipped |
| ~~Brokerage / auto position sync~~ | **— (not in v1)** | **— (not in v1)** | **deferred post-v1** |

**Pricing (unchanged from Truth §16):** Free **$0**; Pro **$20/month** (post-Apple-cut target; product `clavix_pro_monthly` at $19.99). **14-day Pro free trial**, no credit card, auto-downgrades to Free on day 15. No annual plan at launch (revisit v1.1).

### Headline Pro pitch (for paywall + website, brokerage-free)
> **Clavix Pro** — Track your whole book (unlimited holdings & watchlist), get the **verbose morning briefing** that explains what overnight news means for each position, **90 days of score history across all five dimensions**, **advanced alerts** the moment risk shifts, **email digests**, **CSV export**, and the **deepest audit view** — every coefficient, every article's reasoning. $20/mo, 14 days free.

### Free pitch (honest, strong)
> **Clavix Free** — Rate up to 3 holdings and 5 watchlist names, read your daily briefing, and **audit every score** — the same transparent methodology, for free. Upgrade when you want depth, history, and your whole portfolio.

---

## 3. Honesty guardrails (do not advertise what isn't built)

At launch, **gate or hide** any Pro line whose build status above is not "shipped":
- CSV import → hide or "Coming later"
- Email digest of alerts → hide or "Coming later" (depends on SMTP)
- Manual ticker refresh, CSV export, advanced alerts → ship only the implemented subset; hide the rest
- Push notifications → "Coming later" until APNs `.p8` is deployed (`/health` currently `apns:missing`)

The paywall must list **only features a Pro user can actually use on day one**, plus an optional "Coming soon to Pro" sub-section that is clearly future-tense.

---

## 4. Truth doc amendments applied (v2.1)
- §11 Portfolio Mechanics: brokerage-sync path marked **deferred to post-v1**; manual entry + CSV (when built) are the v1 paths.
- §16 Tier Split: SnapTrade row removed; tiers revised per the table above; methodology stays Free.
- §2 banned list already covers "SnapTrade" in user-visible copy — reinforced: no working brokerage CTA.

See `CLAVIX_TRUTH.md` for the in-place edits.
