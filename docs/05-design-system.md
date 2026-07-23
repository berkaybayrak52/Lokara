# 05 — Design system

> Source: the Lokara Brand Board v1.0 (2026). Modern, minimal, Apple-like, lots of white space —
> but **understandable "from 7 to 70"**, made measurable via **WCAG 2.1 AA / BFSG**.
> Apple-style reduction is for aesthetics only (white space, typography) — **never** at the cost of a
> clear label or contrast.

## Color palette

| Token            | Name        | HEX       | RGB       | Role                                              |
| ---------------- | ----------- | --------- | --------- | ------------------------------------------------- |
| `--color-ink`    | Petrol Ink  | `#18212A` | 24·33·42  | **Primary** — text, frames, dark surfaces         |
| `--color-green`  | Lokara Grün | `#1A6558` | 26·101·88 | **Accent** — signals, highlights, primary actions |
| `--color-forest` | Forest Deep | `#123F37` | —         | Deep green — hover/pressed, dark accents          |
| `--color-mint`   | Mint Tint   | `#E7EFEB` | —         | Soft tint — subtle backgrounds, selected states   |
| `--color-slate`  | Slate       | `#5C6A6B` | —         | Muted text, borders, secondary labels             |
| `--color-paper`  | Paper       | `#FBFBFA` | —         | App background / light surface                    |

### Contrast guidance (WCAG AA)

- Body text: Petrol Ink on Paper (very high contrast — safe).
- **Slate is for secondary text only** — verify ≥4.5:1 on its background; never use it for primary
  body copy on Paper at small sizes.
- Lokara Grün as a button background needs white/Paper text; verify ≥4.5:1 (it passes for normal text).
- Green-on-mint is decorative/low-contrast — never use it for text that must be read.

## Typography

| Role        | Typeface       | Usage                                                                 |
| ----------- | -------------- | --------------------------------------------------------------------- |
| **Display** | **Montserrat** | Headlines, big numbers, section titles ("Räume mit klarer Struktur")  |
| **Text**    | **Manrope**    | Body, labels, UI elements, tables — "from business card to dashboard" |

Weights in use: **Regular 400, Medium 500, SemiBold 600, Bold 700** (SemiBold 600 is the workhorse
emphasis weight in the brand board). Use system font fallbacks; load via `next/font` for performance.

- **Scalable type is a BFSG requirement** — use `rem`, respect user zoom, don't cap font scaling.

## The block motif ("Baustein-Motiv")

The blocks in the icon are the heart of the brand: a **flexible grid of square modules**. Use sparingly
as a pattern, divider, or graphic accent — always in **Petrol Ink + Lokara Grün**. Don't overuse; it's
an accent, not a background texture on every screen.

## Logo usage

- **Primary**: horizontal lockup (icon + "Lokara" wordmark) on light — the default.
- **Invers**: white lockup on Petrol Ink.
- **Icon / Bildmarke**: the window-with-blocks mark alone.
- **Monochrome**: single-color version for constrained contexts.
- **App icon**: rounded-square, Petrol Ink ground with the green blocks. **Avatar**: Lokara Grün
  circle with the mark.

## Tailwind wiring (M0)

Expose the tokens as CSS variables + Tailwind theme extension:

```js
// tailwind.config — theme.extend.colors
colors: {
  ink:    '#18212A',
  green:  '#1A6558',
  forest: '#123F37',
  mint:   '#E7EFEB',
  slate:  '#5C6A6B',
  paper:  '#FBFBFA',
}
// fontFamily: { display: ['Montserrat', ...], sans: ['Manrope', ...] }
```

No component uses a raw hex or an off-palette font — everything references a token
(this is checkable and is part of the UI Definition of Done in `CLAUDE.md`).

## Look & feel / motion principles (the "Apple-like" bar)

Tokens give structure; this section gives the _feel_. The target is **modern, minimal, calm,
high-quality** — pleasing motion, generous space, nothing busy. Build to this from M3; reject UI that
feels flat, cramped, or cluttered.

### Minimalism (the discipline, not just the aesthetic)

- **One primary action per screen.** Exactly one filled Lokara-Grün button; everything else is
  secondary (ghost/outline) or tertiary (text link). If two things compete, one is wrong.
- **Progressive disclosure.** Show the common path; hide advanced options behind "Mehr anzeigen",
  an accordion, or a details drawer. Never wall the user in with every field at once.
- **Content first, chrome last.** Let data and whitespace carry the screen. No decorative borders or
  boxes where spacing alone separates things. The block motif is a rare accent, not a texture.
- **Restraint over reduction.** Minimal never means hiding a needed control or dropping a label —
  that fights the "7-to-70" goal. Reduce ornament, never clarity.

### Spacing & layout

- **8px spacing scale** (4 / 8 / 12 / 16 / 24 / 32 / 48 / 64). Everything snaps to it.
- **Generous whitespace** — err larger. Section padding ≥ 24px; card padding ≥ 16–24px.
- **Constrain measure** — body/content columns ~640–760px max for readability; don't stretch text full-bleed.
- **Calm surfaces** — Paper background, soft **radius** (8–12px on cards, 8px on inputs/buttons), a
  single very soft shadow for elevation (no heavy drop shadows, no double borders).

### Motion (Framer Motion)

- **Fast and subtle.** Durations **150–250ms** for most UI (hovers ~120–150ms, page/section
  transitions ~250–300ms). If a user notices the duration, it's too slow.
- **Easing:** ease-out for enters (`[0.16, 1, 0.3, 1]`-style), ease-in for exits. Never linear.
- **Move a little.** Fades + small translate/scale (4–8px, 0.98→1). No big slides, spins, or bounces.
- **Purposeful only.** Motion signals a state change (open/close, appear, confirm) — never decoration.
- **Respect `prefers-reduced-motion`** — collapse to instant/opacity-only. (Also in the a11y checklist.)
- **60fps** — animate only `transform` and `opacity`; never animate layout/width/height/top/left.

### Interaction feel

- Every interactive element has **hover, focus-visible, active, and disabled** states — visible, not subtle-to-invisible.
- **Optimistic + instant feedback:** buttons show a pressed/loading state immediately; autosave shows a
  quiet "Gespeichert" confirmation, never a blocking spinner for small saves.
- **Skeletons, not spinners** for content loads; keep layout stable (no content-shift jank).
- **Empty states are designed**, not blank — a short line + the one action that fills them.

### Reference bar (anchor the quality, don't copy)

Apple system UI / apple.com, **Linear**, **Stripe Dashboard**, **Notion**. Calm color, strong
typographic hierarchy, tight motion, lots of air. When a screen doesn't feel like it belongs next to
these, it's not done.

## Accessibility checklist (every screen)

- [ ] Contrast ≥ 4.5:1 for text (≥3:1 for large text / UI components).
- [ ] Visible focus states on all interactive elements (keyboard nav works end to end).
- [ ] Labels are explicit and always visible (no icon-only critical actions without a label/aria-label).
- [ ] Type scales with user zoom; layout survives 200% zoom.
- [ ] Motion (Framer Motion) respects `prefers-reduced-motion`.
