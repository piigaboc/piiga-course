# piigacourse — Theme Tokens ("stone")

Warm-neutral design system inspired by the shadcn **stone** theme. Light mode is
primary; dark mode is provided via `<html class="dark">`. All styling consumes the
CSS custom properties defined in [`stone.css`](./stone.css) — components must not
hard-code colors, radii, or shadows.

Import once at the app root (e.g. in the global stylesheet / layout):

```css
@import "./theme/stone.css";
```

---

## 1. Token reference

### Surfaces
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#FAFAF9` | `#1C1917` | App canvas / page background |
| `--surface` | `#FFFFFF` | `#292524` | Cards, popovers, menus, sheets, modals |
| `--surface-2` | `#F5F5F4` | `#322E2C` | Inset fills, hover states, muted backgrounds, table stripes |

### Lines & text
| Token | Light | Dark | Use |
|---|---|---|---|
| `--border` | `#E7E5E4` | `#44403C` | Card / input / divider borders (1px) |
| `--text` | `#1C1917` | `#FAFAF9` | Primary text, headings, icons |
| `--muted` | `#78716C` | `#A8A29E` | Secondary text, placeholders, captions, disabled labels |

### Accent (stone primary)
| Token | Light | Dark | Use |
|---|---|---|---|
| `--accent` | `#1C1917` | `#FAFAF9` | Primary button fill, active toggles, focus ring, progress fill |
| `--accent-fg` | `#FAFAF9` | `#1C1917` | Text / icons placed ON `--accent` |
| `--accent-subtle` | `#F0EEEC` | `#2E2A28` | Soft tinted fill: calendar studied-day, selected rows, soft chips |

### Shape & elevation
| Token | Value | Use |
|---|---|---|
| `--radius` | `10px` | Base radius — Card, Input, Button |
| `--radius-sm` | `6px` | Badge, small/compact controls, focus-ring corners |
| `--radius-lg` | `14px` | Large panels, modals, hero cards |
| `--shadow-sm` | soft 1px | Resting cards, inputs |
| `--shadow-md` | soft 2-layer | Raised cards, popovers, hover lift |

### Status tints (course status)
Muted, stone-compatible. Each pairs a `-bg` with a readable `-fg` (AA on its own bg).

| Status | `-bg` token | `-fg` token | Light bg/fg |
|---|---|---|---|
| `planned` | `--status-planned-bg` | `--status-planned-fg` | `#F5F5F4` / `#57534E` (neutral grey) |
| `in_progress` | `--status-in-progress-bg` | `--status-in-progress-fg` | `#EAF1F4` / `#3F5A66` (muted slate-blue) |
| `completed` | `--status-completed-bg` | `--status-completed-fg` | `#EAF1EC` / `#3F5F49` (muted sage) |
| `paused` | `--status-paused-bg` | `--status-paused-fg` | `#F6F0E8` / `#6B5733` (muted amber) |

---

## 2. Spacing & typography

- **Spacing scale (4px base):** `4 8 12 16 24 32 48 64`. Use multiples of 4 only.
  Card padding `16–24`; control padding-x `12–16`; gap between cards `16`.
- **Type scale (px):** `12` caption · `14` body (base) · `16` lead · `20` h3 ·
  `24` h2 · `30` h1. Body line-height `1.5`, headings `1.25`.
- **Weights:** body `400`, labels/buttons `500`, headings `600`.
- **Font stack:** system UI sans (see `stone.css` body); monospace for code/IDs.

---

## 3. Component → token mapping

### Button
| Variant | Background | Text | Border | Notes |
|---|---|---|---|---|
| **primary** | `--accent` | `--accent-fg` | none | hover: 92% opacity overlay / slight darken |
| **secondary** | `--surface-2` | `--text` | `--border` | hover: `--surface-2` → blend toward border |
| **outline** | transparent | `--text` | `--border` | hover bg `--surface-2` |
| **ghost** | transparent | `--text` | none | hover bg `--surface-2` |
| **destructive** | `--status-paused-fg`* | `--accent-fg` | none | *or app-level danger token if added |

- Radius `--radius`; padding `8 16` (height ~36px); font-weight `500`.
- Focus: ring `2px var(--accent)` offset `2px` (from base reset).
- Disabled: `opacity: 0.5; cursor: not-allowed`.

### Card
- Background `--surface`; border `1px var(--border)`; radius `--radius`;
  shadow `--shadow-sm` (use `--shadow-md` on hover/raised). Padding `16–24`.
- Title `--text` (16–20px / 600); description / meta `--muted`.
- Section dividers use `--border`.

### Badge (generic + status)
- Radius `--radius-sm`; padding `2 8`; font `12px / 500`; inline-flex.
- **Neutral badge:** bg `--surface-2`, text `--muted`, optional border `--border`.
- **Accent badge:** bg `--accent`, text `--accent-fg`.
- **Status badge:** bg `--status-{status}-bg`, text `--status-{status}-fg`.
  Map course status string → token pair:
  - `planned` → planned-bg / planned-fg
  - `in_progress` → in-progress-bg / in-progress-fg
  - `completed` → completed-bg / completed-fg
  - `paused` → paused-bg / paused-fg

### StatTile (dashboard metric)
- Container = Card (bg `--surface`, border `--border`, radius `--radius`, `--shadow-sm`).
- **Value** (big number): `--text`, 24–30px / 600.
- **Label**: `--muted`, 12–14px / 500, uppercase optional (letter-spacing `0.04em`).
- **Icon**: in a `--accent-subtle` rounded square (`--radius-sm`), icon color `--text`.
- **Delta/trend**: positive → `--status-completed-fg`; negative → `--status-paused-fg`.

### Input (text / select / textarea)
- Background `--surface`; border `1px var(--border)`; radius `--radius`;
  text `--text`; placeholder `--muted`; padding `8 12`; height ~36px.
- **Hover:** border darkens toward `--muted`.
- **Focus:** border `--accent` + ring `2px var(--accent)` offset `2px` (or inset).
- **Disabled:** bg `--surface-2`, text `--muted`, `opacity: 0.6`.
- **Error:** border + ring use `--status-paused-fg`; helper text same.
- Label `--text` (14px / 500); helper/hint `--muted` (12px).

### Calendar day cell
| State | Background | Text | Notes |
|---|---|---|---|
| default | transparent | `--text` | square/rounded `--radius-sm`, centered |
| outside month | transparent | `--muted` | dimmed |
| hover | `--surface-2` | `--text` | |
| **studied day** | `--accent-subtle` | `--text` | the daily-activity highlight; optional dot in `--accent` |
| today | transparent | `--text` | `1px` ring `--border` (or `--accent` if also selected) |
| selected | `--accent` | `--accent-fg` | strongest state, overrides studied highlight |
| disabled | transparent | `--muted` | `opacity: 0.4` |

- Grid gap `4`; cell min-size `32–36px`; weekday header text `--muted` (12px).
- A day that is both *studied* and *selected* renders as **selected** (accent fill);
  if studied + today, keep `--accent-subtle` and add the `--border` today ring.

---

## 4. Accessibility notes

- Body text `--text` on `--bg`/`--surface` exceeds WCAG AA (≈ 16:1).
- `--muted` on `--bg` meets AA for normal text (≥ 4.5:1) — do not use `--muted`
  for text smaller than 12px on `--surface-2`.
- Every status `-fg` is tuned to ≥ 4.5:1 on its paired `-bg`; never place status
  `-fg` on `--bg` without its `-bg`, and never rely on color alone for status —
  pair the badge with a text label.
- Focus is always visible via the accent ring; do not remove `:focus-visible`.
- Respect `prefers-reduced-motion` for any hover-lift / shadow transitions.

---

## 5. Acceptance checklist (engineers)

- [ ] `stone.css` imported once at app root; no other file redeclares these vars.
- [ ] No component hard-codes a hex color, radius, or shadow — all via tokens.
- [ ] Dark mode toggles purely by adding/removing `.dark` on `<html>`; no JS color swaps.
- [ ] Button/Card/Badge/StatTile/Input/calendar-cell use the mapped tokens above.
- [ ] Status badges render the correct `-bg`/`-fg` pair per status string and include a text label.
- [ ] Calendar studied-day uses `--accent-subtle`; selected uses `--accent` + `--accent-fg`.
- [ ] Focus-visible ring present and visible on all interactive elements in both modes.
- [ ] Spot-check contrast (text, muted, each status pair) passes AA in light and dark.
