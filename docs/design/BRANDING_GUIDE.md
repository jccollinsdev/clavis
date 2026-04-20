# Clavis Branding Guide

## Purpose

This document captures the visual brand system for Clavis: fonts, colors, spacing, tone, and UI presentation rules.

Clavis should feel like a serious portfolio risk intelligence product: dark, precise, calm, and trustworthy.

---

## Brand Positioning

- Portfolio risk intelligence for self-directed investors
- Informational, not advisory
- Evidence-first, not hype-driven
- Premium, technical, and restrained

### Voice

- Clear
- Direct
- Calm
- Factual
- Never prescriptive

### Avoid

- Consumer-finance fluff
- Loud marketing language
- Advice-style copy like buy, sell, or hold
- Overuse of bright color

---

## Typography

### Fonts

- `Inter` for UI text, labels, titles, and copy
- `JetBrains Mono` for numeric data, scores, grades, and technical readouts

### Font roles

| Role | Font | Use |
|---|---|---|
| Hero score | JetBrains Mono | Primary risk score display |
| Page title | Inter | Screen titles and major headers |
| Section title | Inter | Card and section headings |
| Data number | JetBrains Mono | Prices, values, percentages, grades |
| Labels | Inter | Uppercase metadata and small UI labels |
| Row ticker | Inter | Ticker symbols in lists |
| Row score | JetBrains Mono | Compact list scores |
| Body | Inter | Explanatory text |

### Rules

- Use Inter for readability.
- Use JetBrains Mono for anything that should feel like measured data.
- Do not mix decorative fonts.
- Keep typography restrained and consistent.

---

## Type Scale

The app currently uses these design-system tokens:

| Token | Style |
|---|---|
| `portfolioScore` | 52 mono |
| `h1` | 28 Inter medium |
| `h2` | 20 Inter medium |
| `dataNumber` | 22 mono |
| `gradeTag` | 13 mono |
| `label` | 11 Inter medium |
| `rowTicker` | 13 Inter medium |
| `rowScore` | 13 mono |
| `bodySmall` | 13 Inter regular |
| `body` | 15 Inter regular |
| `bodyStrong` | 15 Inter medium |
| `footnote` | 12 Inter regular |
| `footnoteEmphasis` | 12 Inter medium |
| `metric` | 32 mono |
| `grade` | 36 mono |
| `heroNumber` | 48 mono |
| `heroLabel` | 24 Inter medium |
| `brandTitle` | 18 Inter bold |

---

## Color System

### Base surfaces

| Token | Hex | Use |
|---|---|---|
| `backgroundPrimary` | `#0F1117` | App background |
| `surface` | `#161B24` | Cards and panels |
| `surfaceElevated` | `#1E2530` | Raised cards and overlays |
| `border` | `#2A3140` | Dividers and outlines |

### Text

| Token | Hex | Use |
|---|---|---|
| `textPrimary` | `#E8ECF0` | Main content |
| `textSecondary` | `#7A8799` | Supporting text |
| `textTertiary` | `#7A8799` | Alias for secondary metadata |

### Informational

| Token | Hex | Use |
|---|---|---|
| `informational` | `#1A6494` | Non-risk blue, links, neutral UI accent |

### Risk scale

| State | Hex | Meaning |
|---|---|---|
| `riskA` | `#1D9E75` | Safe |
| `riskB` | `#639922` | Stable |
| `riskC` | `#BA7517` | Watch |
| `riskD` | `#D85A30` | Risky |
| `riskF` | `#C8342B` | Critical |

### Grade tag backgrounds

| State | Background | Text |
|---|---|---|
| A | `#E1F5EE` | `#085041` |
| B | `#EAF3DE` | `#27500A` |
| C | `#FAEEDA` | `#633806` |
| D | `#FAECE7` | `#712B13` |
| F | `#FCEBEB` | `#791F1F` |

### Semantic surfaces

| Token | Hex / Style | Use |
|---|---|---|
| `successSurface` | `#1D9E75` at 12% | Positive state background |
| `warningSurface` | `#BA7517` at 12% | Caution state background |
| `dangerSurface` | `#C8342B` at 12% | Critical state background |
| `clavisAlertBg` | `#C8342B` at 12% | Alert emphasis background |

---

## Core Branding Rules

### Background hierarchy

- Use the dark surface stack consistently.
- Treat `backgroundPrimary` as canvas.
- Use `surface` for cards.
- Use `surfaceElevated` for layered emphasis.

### Accent usage

- Use the informational blue sparingly.
- Do not use blue for risk semantics.
- Use risk colors only for grade and severity meaning.

### Data presentation

- Scores, grades, and prices should read like data.
- Use mono for numeric precision.
- Keep labels quieter than the values they describe.

### Card styling

- Corner radius: `8`
- Inner corner radius: `4`
- Screen padding: `16`
- Card padding: `16`
- Section spacing: `20`

### Layout rhythm

- Small spacing: `8`
- Medium spacing: `16`
- Large spacing: `24`
- Extra large spacing: `48`
- Floating tab inset: `16`
- Floating tab height: `74`

---

## Brand Mark

- App logo asset: `AppLogo`
- Brand mark should be treated as a simple logo element, not an illustration
- Do not add extra decoration around it

---

## UI Tone

### Good examples

- `Portfolio is stable, but 2 names are deteriorating`
- `Analysis is still running`
- `Updated 7:42 AM`

### Bad examples

- `Your portfolio is in trouble!`
- `Buy these names now`
- `Hot picks`
- `Best stocks to hold`

---

## Copy Rules

- Prefer precise, short phrases
- Use grades and freshness context whenever possible
- Explain why a surface exists
- Show confidence or evidence quality when relevant
- Keep wording informational and non-advisory

---

## Design Checklist

- Inter for UI copy
- JetBrains Mono for scores and numbers
- dark navy surfaces
- one restrained blue accent
- risk colors only for meaning
- visible freshness on score surfaces
- premium, calm, and technical presentation
