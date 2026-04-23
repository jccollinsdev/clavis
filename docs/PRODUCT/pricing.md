# Clavis Pricing

## Status: Draft — target $20/mo Pro tier

Last updated: April 21, 2026

---

## Launch Positioning

- Free = understand my portfolio.
- Pro = automate it and go deeper.
- The free tier should feel complete enough to trust.
- Pro should be worth $20/mo by saving time and unlocking automation, depth, and convenience.

## Feature Split

| Feature | Free | Pro | Notes |
|---|---:|---:|---|
| Sign up / sign in | Yes | Yes | Core access |
| Onboarding | Yes | Yes | Must stay free |
| Home dashboard | Yes | Yes | Core value |
| Holdings list | Yes | Yes | Core value |
| Manual holding entry | Yes | Yes | Needed for free users |
| Basic ticker detail | Yes | Yes | Score + summary |
| Basic risk rationale | Yes | Yes | Trust surface |
| Full methodology / deep rationale | Limited | Yes | Strong Pro value |
| Digest | Yes | Yes | Free should still feel useful |
| Digest depth / richer sections | Limited | Yes | Good paid differentiator |
| Alerts | Yes | Yes | Basic alerts stay free |
| Advanced alert controls | Limited | Yes | Paid lever |
| News feed | Yes | Yes | Core reading experience |
| Article detail | Yes | Yes | Core reading experience |
| Search / ticker lookup | Yes | Yes | Core utility |
| Watchlist | Limited | Yes | Pro workflow feature |
| Brokerage sync | No / limited | Yes | Strong Pro feature |
| Auto-sync holdings | No | Yes | Clear subscription value |
| Manual ticker refresh | Limited | Yes | Natural Pro gate |
| Historical analysis / score history | Limited | Yes | Good paid depth feature |
| Export data | Yes | Yes | Compliance / trust |
| Delete account | Yes | Yes | Compliance / trust |
| Push notifications | Basic | Advanced | Receipt free; smarter routing paid |
| Settings | Yes | Yes | Core control surface |
| Premium support | No | Yes | Optional Pro perk |

## Pricing Model

### Free Tier
- Up to 5 holdings
- Daily digest
- A–F grade per position
- Top news per holding
- Grade change alerts

### Pro — $20/month or $99/year
- Unlimited holdings
- Full score breakdown by dimension
- Position detail with methodology
- Alert history and event log
- Priority analysis during high-volume news days
- Brokerage sync and auto-refresh
- Faster iteration on alerting / analysis depth

---

## Cost Structure

### One-time
| Item | Cost |
|---|---|
| Business entity (LLC) | $550 |
| Legal | $500 |
| Apple Developer Program | $99 |
| **Total** | **$1,149** |

### Monthly Fixed
| Item | Cost |
|---|---|
| VPS | $15 |
| Supabase | $25 |
| Resend (email) | $20 |
| MiniMax Max (AI) | $50 |
| Domain | $1 |
| **Total** | **$111/mo** |

### Per User
| Item | Cost |
|---|---|
| SnapTrade API | $2/user/mo |

---

## Unit Economics

**Break-even:** roughly achievable at a small but real paid base if the app stays lean on compute and AI calls

Profit formula:
```
profit = (price × conversion × total_users) - 111 - (2 × total_users)
```

**At $20/mo, the model works if Pro includes the expensive time-saving features and the free tier stays trustworthy but bounded.**

---

## Pricing Decisions Log

### 2026-04-21 — Current launch split
- Saved the current free vs Pro plan locally
- Free is the complete understanding layer
- Pro is the automation and depth layer
- Payment integration will be implemented after the app is stable enough for family review

### 2026-04-12 — Initial model set
- Analyzed cost structure and break-even points
- $12/mo rejected: SnapTrade costs eat all margin, break-even at 277 users
- $20/mo selected as starting price
- **Rule:** if waitlist hits 50+ signups quickly, test $25-30

---

## Long Term

**$30/mo potential** — viable once waitlist shows strong demand signal (>50 signups in first 2 weeks)

**Data partnerships** — anonymized, aggregated retail investor signal data to research firms (v3)

**Institutional lite** — $49/mo tier for larger portfolios needing more frequent analysis cycles (v3)
