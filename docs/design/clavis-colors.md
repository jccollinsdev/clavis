# Clavis — Color System

## Brand overview

Clavis is a portfolio risk intelligence app for serious self-directed investors. The visual language is dark, precise, and professional — closer to a Bloomberg terminal than a consumer finance app. Dark navy surfaces dominate. One bright accent color (Signal Blue) is used sparingly for interactive elements only. Color is reserved almost entirely for semantic meaning, especially the A–F risk grade system.

---

## Core palette

| Token | Hex | Usage |
|---|---|---|
| `midnight` | `#0B1929` | Primary app background |
| `navy` | `#0F2744` | Card and panel surfaces |
| `ocean` | `#163860` | Borders, dividers, subtle separators |
| `signal` | `#1D6FE8` | Primary CTAs, links, active states |
| `slate` | `#8FA8C4` | Secondary text, labels, metadata |
| `frost` | `#E8F1FC` | Light mode background (swap for midnight) |
| `white` | `#F8FAFC` | Primary text on dark surfaces |

---

## Risk grade system

Each grade has a foreground color (text/icon) and a background color (badge/card tint). Always pair them together — never use the foreground color alone on a dark background.

| Grade | Meaning | Foreground | Background |
|---|---|---|---|
| A | Safe to hold | `#16A34A` | `#DCFCE7` |
| B | Low risk | `#65A30D` | `#ECFCCB` |
| C | Watch | `#CA8A04` | `#FEF9C3` |
| D | Elevated risk | `#EA580C` | `#FFEDD5` |
| F | Review immediately | `#DC2626` | `#FEE2E2` |

Grade badges: render as `background = grade background`, `color = grade foreground`, `border-radius: 6px`, `font-weight: 500`, `padding: 2px 8px`.

---

## Semantic colors

| Token | Hex | Usage |
|---|---|---|
| `alert-amber` | `#D97706` | Push notifications, grade downgrade alerts |
| `alert-amber-bg` | `#FEF3C7` | Alert banner backgrounds |
| `confirm-green` | `#16A34A` | Grade improvement indicators |
| `danger-red` | `#DC2626` | Grade degradation, critical alerts |

---

## CSS custom properties

Paste this into your root stylesheet:

```css
:root {
  /* Brand foundation */
  --color-midnight: #0B1929;
  --color-navy: #0F2744;
  --color-ocean: #163860;
  --color-signal: #1D6FE8;
  --color-slate: #8FA8C4;
  --color-frost: #E8F1FC;
  --color-white: #F8FAFC;

  /* Risk grades — foreground */
  --grade-a: #16A34A;
  --grade-b: #65A30D;
  --grade-c: #CA8A04;
  --grade-d: #EA580C;
  --grade-f: #DC2626;

  /* Risk grades — background */
  --grade-a-bg: #DCFCE7;
  --grade-b-bg: #ECFCCB;
  --grade-c-bg: #FEF9C3;
  --grade-d-bg: #FFEDD5;
  --grade-f-bg: #FEE2E2;

  /* Semantic */
  --color-alert: #D97706;
  --color-alert-bg: #FEF3C7;
  --color-confirm: #16A34A;
  --color-danger: #DC2626;
}
```

---

## Tailwind config

If using Tailwind CSS, extend your theme with:

```js
theme: {
  extend: {
    colors: {
      clavis: {
        midnight: '#0B1929',
        navy:     '#0F2744',
        ocean:    '#163860',
        signal:   '#1D6FE8',
        slate:    '#8FA8C4',
        frost:    '#E8F1FC',
        white:    '#F8FAFC',
      },
      grade: {
        a:    '#16A34A',
        'a-bg': '#DCFCE7',
        b:    '#65A30D',
        'b-bg': '#ECFCCB',
        c:    '#CA8A04',
        'c-bg': '#FEF9C3',
        d:    '#EA580C',
        'd-bg': '#FFEDD5',
        f:    '#DC2626',
        'f-bg': '#FEE2E2',
      },
    },
  },
}
```

---

## Usage rules

**Backgrounds:** Layer midnight → navy → ocean for depth. Never use light colors as backgrounds in dark mode.

**Text:** Use `white` (#F8FAFC) for primary content on dark surfaces. Use `slate` (#8FA8C4) for secondary text, timestamps, labels, and metadata.

**Interactive elements:** Signal blue (#1D6FE8) is the only accent color. Use it for buttons, links, tab indicators, and focused input borders. Do not use it for decorative purposes.

**Risk grades:** Grade foreground colors are for text and icons inside a matching light background. Do not render grade colors as standalone text on dark navy surfaces — always use the paired background.

**Alerts:** Use `alert-amber` for push notifications and grade downgrade badges. Use `confirm-green` for grade upgrades. Use `danger-red` only for critical risk transitions (to grade F or from F).

**Light mode:** Swap `midnight` → `frost` as the page background. Keep all grade colors and semantic colors identical — they are designed to work in both modes.
