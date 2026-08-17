# 05 — Design system

This is Lokara's canonical, living brand, component, accessibility, and interaction contract. It
separates binding design rules from repository delivery status. Superseded wording remains available
in Git with `git show 635acf9:docs/05-design-system.md`; it is not part of the active specification.

No Berkay calculation rule is owned by this file. `docs/08-statement-document.md` assigns statement
carriers to legal-disclosure tiers; this file alone owns the thresholds for those tiers.

## Reading guide and status vocabulary

| Status | Meaning |
| --- | --- |
| **Shipped** | Present on `main` in current source or an enforced test. This does not by itself prove that every use meets the complete design contract. |
| **Specified** | Binding design contract for present and future implementation; any repository discrepancy is an open gap. |
| **Future** | Direction is selected, but the implementation or asset is not present on `main`. |
| **Not repository-verified** | A retained attribution or claim has no tracked source that lets this repository independently confirm it. |

## 1. Brand foundations and ownership

The retained source attribution is the **Lokara Brand Board v1.0 (2026)**. The repository contains no
Brand Board source asset with which to revalidate that attribution, so the attribution is **Not
repository-verified**. The design decisions below remain the active contract.

Lokara is modern, minimal, calm, and Apple-like, with generous white space. It must also remain
understandable **"from 7 to 70"** (the **"7-to-70"** rule) and measurable through
**WCAG 2.1 AA / BFSG**. Apple-style
reduction applies only to aesthetics such as white space and typography. It never justifies removing
a clear label, needed control, readable contrast, or legally required content.

| Concern | Owner |
| --- | --- |
| Brand tokens, component rules, accessibility thresholds, spacing, motion, and interaction | This file, `docs/05` |
| Which statement text carries tier 1 or tier 2 | `docs/08-statement-document.md` |
| Shipped web token values and shadcn mappings | `packages/ui/src/tokens.css` |
| UI Definition of Done | `CLAUDE.md` |

## 2. Color, typography, logo, and motif

### 2.1 Brand palette

| Token | Name | HEX | RGB | Role |
| --- | --- | --- | --- | --- |
| `--color-ink` | Petrol Ink | `#18212A` | 24·33·42 | **Primary** — text, frames, dark surfaces |
| `--color-green` | Lokara Grün | `#1A6558` | 26·101·88 | **Accent** — signals, highlights, primary actions |
| `--color-forest` | Forest Deep | `#123F37` | — | Deep green — hover/pressed, dark accents |
| `--color-mint` | Mint Tint | `#E7EFEB` | — | Soft tint — subtle backgrounds, selected states |
| `--color-slate` | Slate | `#5C6A6B` | — | Muted text, borders, secondary labels — **never tier 1** |
| `--color-paper` | Paper | `#FBFBFA` | — | App background / light surface |
| `--color-white` | White | `#FFFFFF` | 255·255·255 | Supporting neutral — cards, inputs, popovers, and inverse foregrounds |

The seven tokens above are **Shipped** in `packages/ui/src/tokens.css`. White supports the palette; it
does not replace Paper as the app ground.

Binding contrast guidance:

- Body text uses Petrol Ink on Paper. It has very high contrast.
- Slate is secondary text only. Verify at least 4.5:1 against its own background; never use Slate
  for primary body copy on Paper at small sizes.
- Slate is excluded from tier 1 outright. It reaches **5,44:1 on Paper** and **4,81:1 on Mint**;
  neither reaches 7:1. No size changes that fact because Lokara declines the AAA large-text
  relaxation for tier 1. If tier-1 text must look quiet, use weight 400 beside a 600/700 neighbour,
  not a lighter ink. Forest Deep is the quiet tier-1 ink at **11,32:1 on Paper** and **10,01:1 on
  Mint**.
- Lokara Grün as a button background needs White or Paper text. Both pass 4.5:1; the shipped
  `--primary-foreground` mapping is White.
- Green on Mint is decorative/low-contrast in this system. Never use it for text that must be read.
  The pair is **5,89:1** and clears AA, but that does not change its assigned role. The current
  component discrepancy is recorded in § 6.

Appendix A contains every measured pair and its role.

### 2.2 Typography

| Role | Typeface | Usage |
| --- | --- | --- |
| **Display** | **Montserrat** | Headlines, big numbers, section titles such as “Räume mit klarer Struktur” |
| **Text** | **Manrope** | Body, labels, UI elements, tables — “from business card to dashboard” |

Use Regular 400, Medium 500, SemiBold 600, and Bold 700. SemiBold 600 is the workhorse emphasis
weight from the Brand Board. Use system fallbacks and load the web faces through `next/font` for
performance.

Scalable type is a BFSG requirement: use `rem`, respect user zoom and text-size settings, and never
cap font scaling.

### 2.3 The block motif (“Baustein-Motiv”)

The blocks in the icon are the heart of the brand: a flexible grid of square modules. Use the motif
sparingly as a pattern, divider, or graphic accent, always in Petrol Ink and Lokara Grün. It is an
accent, not a background texture on every screen.

The motif rule is **Specified**. No actual motif asset is present in the repository; asset delivery
is **Future**.

### 2.4 Logo usage

- **Primary:** horizontal lockup, icon plus “Lokara” wordmark, on a light surface; this is the
  default.
- **Inverse:** White lockup on Petrol Ink.
- **Icon / Bildmarke:** the window-with-blocks mark alone.
- **Monochrome:** single-colour version for constrained contexts.
- **App icon:** rounded square, Petrol Ink ground with green blocks.
- **Avatar:** Lokara Grün circle with the mark.

These usages are **Specified**. No primary, inverse, icon, monochrome, app-icon, or avatar asset is
present in the repository; their implementation is **Future**.

### 2.5 Semantic status colors

The Brand Board has no status palette, but Lokara needs one for destructive actions, form and 422
validation errors, the three-colour Zustell-Ampel under § 556, and Guard/Wächter severities such as
the § 556 deadline, Eichfrist, and 15%-AfA warning. Only two new hues are needed; success reuses
Lokara Grün.

| Token | HEX | Contrast on Paper | White on it | Role |
| --- | --- | ---: | ---: | --- |
| `--color-danger` | `#A4262C` | **7,01** ✓ | **7,26** ✓ | Errors, destructive actions, Ampel *rot* |
| `--color-warning` | `#92400E` | **6,85** ✓ | **7,09** ✓ | Warnings, pending guards, Ampel *gelb* |
| `--color-success` | `#1A6558` | **6,66** ✓ | **6,89** ✓ | Lokara Grün — confirmations, Ampel *grün* |

Tint surfaces pair the semantic foreground with a quiet ground. Ink on every tint is at least
13:1.

| Tint | HEX | Semantic foreground on tint | Pairs with |
| --- | --- | ---: | --- |
| `--color-danger-tint` | `#FBEAE9` | **6,24** ✓ | `danger` |
| `--color-warning-tint` | `#FBF1E5` | **6,35** ✓ | `warning` |
| `--color-success-tint` | `#E7EFEB` | **5,89** ✓ | Mint Tint; `success` |

Every pair clears AA at 4.5:1 for normal text and is safe for borders, icons, and large text, whose
floor is 3:1. The main status trio on Paper has near-identical visual weight at 7,01 / 6,85 / 6,66.

Why success is not a separate green: a candidate such as `#166534` has only a **1,03 luminance ratio
to Lokara Grün**. It is barely distinguishable, adds noise, and is worse for colour-blind users.
Primary actions are filled buttons; success feedback is a tint surface plus icon plus label.

Why warning is burnt ochre rather than bright amber: a true amber such as `#F59E0B` is around 2:1 on
a light background and fails AA. Amber that passes on Paper is necessarily dark.

**BFSG: never signal by colour alone.** Every status also needs a distinct icon and a text label.
This is especially important for the legally meaningful Zustell-Ampel.

## 3. Tailwind and shadcn token wiring

### 3.1 Tailwind v4 theme

Tailwind v4 uses CSS-first configuration through `@theme`, not a
`tailwind.config.js` `theme.extend`. This M0 foundation is **Shipped**. Brand utilities such as
`bg-ink` and `text-green`, font utilities, and shadcn semantic variables all resolve from
`packages/ui/src/tokens.css`.

The shipped theme declarations are:

```css
@theme {
  --color-ink: #18212a;
  --color-green: #1a6558;
  --color-forest: #123f37;
  --color-mint: #e7efeb;
  --color-slate: #5c6a6b;
  --color-paper: #fbfbfa;
  --color-white: #ffffff;

  --color-danger: #a4262c;
  --color-danger-tint: #fbeae9;
  --color-warning: #92400e;
  --color-warning-tint: #fbf1e5;
  --color-success: #1a6558;
  --color-success-tint: #e7efeb;

  --font-display: var(--font-montserrat), "Montserrat", ui-sans-serif, system-ui, sans-serif;
  --font-sans: var(--font-manrope), "Manrope", ui-sans-serif, system-ui, sans-serif;
}
```

No component may introduce a raw colour or an off-palette font. Component styling references tokens;
exceptions found in current source are delivery gaps, not changes to this rule.

### 3.2 Component layer — exact shipped shadcn mapping

The web component base is shadcn/ui: copy-in React components built with Radix and Tailwind, themed
to Lokara rather than the default shadcn palette. The shared workspace is `packages/ui`.

| shadcn variable | Shipped mapping |
| --- | --- |
| `--background` / `--foreground` | Paper / Petrol Ink |
| `--card` / `--card-foreground` | White / Petrol Ink |
| `--popover` / `--popover-foreground` | White / Petrol Ink |
| `--primary` / `--primary-foreground` | Lokara Grün / **White** |
| `--secondary` / `--secondary-foreground` | Mint Tint / Petrol Ink |
| `--muted` / `--muted-foreground` | Mint Tint / Slate |
| `--accent` / `--accent-foreground` | Mint Tint / Forest Deep |
| `--border` / `--input` / `--ring` | Slate |
| `--destructive` / `--destructive-foreground` | Danger / White |
| `--radius` | `0.625rem` = 10px, inside the 8–12px brand range |

White, not Paper, is deliberately used for cards, inputs, popovers, and inverse foregrounds. Paper
remains the page background. Brand tokens override shadcn defaults. Every component still owes the
complete WCAG 2.1 AA / BFSG checklist in § 4.

The **Shipped** shared subset exports `Button`, `Card`, `Input`, `Label`, native `Select`,
`StatusNote`, and `Table`, plus their supporting exports. “Shipped” describes presence, not blanket
accessibility approval for every consuming screen.

### 3.3 Mobile theme

Expo/React Native does not use shadcn. It must share the same colours, type scale, and radii through
a React Native theme object. The mobile app and theme object are **Future**; no mobile app exists in
the repository today.

## 4. Accessibility and legal-disclosure tiers

Ordinary body copy remains at WCAG 2.1 AA. Content shown because statute or Lokara's compliance rule
requires it follows one of two tiers based on **what the content is for**, never its size, length, or
visual prominence.

An older one-tier rule (`legal-contrast` at 7:1 plus `legal-size` at least body copy) was ruled wrong
on **04.08.2026** and is superseded. Appendix B keeps that history explicit.

### Legally required disclosure — two tiers, split by what the content is for

#### Tier 1 — verification content (`legal-t1-size`, `legal-t1-contrast`)

Tier 1 contains the **four BGH formal minimums** — Gesamtkosten, Umlageschlüssel, Anteil des Mieters,
Vorauszahlungen — and everything needed to explain or recompute them: Umlageschlüssel, Bemessung,
Gesamtbemessung, the amounts, and the CO₂ reconciliation.

German case law requires a statement to be **verständlich für einen durchschnittlichen Mieter**
under the BGH minimums for formal validity and § 259 BGB. Tier 1 is the content that requirement is
about; text a reader must squint at is disclosure in form only.

- **`legal-t1-size` — never smaller than body copy.** Compare with the document stylesheet's own
  body font size, not a constant and not the smallest text on the page. The latter could be satisfied
  by shrinking everything else.
- **`legal-t1-contrast` — at least 7:1 on its own background.** This comes from WCAG 2.1 Level AAA,
  Success Criterion 1.4.6, *Contrast (Enhanced)*: 7:1 for normal text and 4.5:1 for large text at
  least 18 pt or 14 pt bold. Lokara declines the large-text relaxation because tier 1 is never set
  large. Qualifying pairs are Petrol Ink on Paper (15,72), Petrol Ink on Mint (13,91), Forest Deep
  on Paper (11,32), and Forest Deep on Mint (10,01). Slate is excluded at 5,44 and 4,81. Use tokens;
  no ad-hoc hex or new colour is needed.

#### Tier 2 — provenance and attestation (`legal-t2-contrast`, `legal-t2-scale`)

Tier 2 contains `Rechtsstand` stamps and the “rechtskonform, keine Rechts- oder Steuerberatung”
disclaimer. They state where the rules came from and what the document is not. They are not BGH
minimums: no court requires a `Rechtsstand` line. They are Lokara's rules from `CLAUDE.md` under
“Version legal rules” and “Tool, not advice.” A reader recomputes no figure from them.

The bar is present and legible, not prominent:

- **`legal-t2-contrast` — at least 4.5:1 on its own background.** This is WCAG 2.1 Level AA, Success
  Criterion 1.4.3, *Contrast (Minimum)*, the same floor as body copy. Slate on Paper qualifies at
  5,44. Slate on Mint qualifies numerically at 4,81 but has only a 0,31 margin and is discouraged on
  any surface that may be re-tinted.
- **`legal-t2-scale` — must scale.** It respects zoom and text-size settings through `rem` without
  capped scaling. A print PDF discharges this through the medium because the viewer zooms the whole
  page; the rule is stated, not asserted against a print stylesheet.
- **No size floor, deliberately.** The recorded ruling remains binding: *“I am not inventing a
  second magic number, and any ratio I picked would land conveniently on the current 8 pt, which is
  the same error as the 9,0 pt floor.”* A tier-2 threshold derived as a fraction of current body copy
  would be fitted to the existing page. A test that adds such a floor is wrong until this paragraph
  changes.

**Why there is no absolute pt floor for either tier.** DIN 1450 (Schriften — Leserlichkeit) derives
minimum size from x-height and reading distance, not point size, so it supplies no honest absolute
point number. The brand typefaces are not embedded in the generated PDF; the stylesheet requests
them but falls back when unavailable. A point floor would therefore measure a font Lokara does not
ship. An absolute floor would require an embedded-font decision plus a DIN-1450 x-height calculation
at a stated reading distance, not a round number.

### Assigning a carrier to a tier

Every carrier of legally required text belongs to **exactly one** tier; unassigned is not a state.
Ask whether the reader can verify a number with it. If yes, it is tier 1. If it only states where the
rule came from or what the document is not, it is tier 2.

Statutory notices that change how a figure must be read are tier 1. Examples include “this Verbrauch
is an estimate” and “the consumption key was replaced by the area key,” because without those facts
the printed Umlageschlüssel is not the one actually applied.

Both tiers use line-height at least 1.4, weight at least 400, no all-caps, no negative letter spacing,
and `font-variant-numeric: tabular-nums` on numeric columns so figures align for comparison.

**Rechtsstand 08/2026** for the BGH minimums and § 259 BGB cited here. WCAG 2.1 and DIN 1450 are
standards, not statutes, and carry no `Rechtsstand`.

### Accessibility checklist for every screen

- [ ] Text contrast is at least 4.5:1; large text and UI components are at least 3:1.
- [ ] Tier 1 meets `legal-t1-contrast` at 7:1 and `legal-t1-size` at no smaller than body copy.
- [ ] Tier 2 meets `legal-t2-contrast` at 4.5:1 and `legal-t2-scale`; it has no size floor.
- [ ] Every legally required carrier belongs to exactly one tier.
- [ ] Every interactive element has a visible focus state and works end to end by keyboard.
- [ ] Labels are explicit and always visible; critical icon-only actions have a label or
  `aria-label`.
- [ ] Type scales with user zoom and the layout survives 200% zoom.
- [ ] Motion respects `prefers-reduced-motion`, whether implemented with current CSS/Tailwind or
  future Framer Motion.

## 5. Layout, motion, and interaction

The quality bar is modern, minimal, calm, and high-quality: generous space, purposeful motion, and
nothing busy. Tokens provide structure; these rules provide the feel. They apply from M3 onward.

### 5.1 Minimalism

- **One primary action per screen.** Use exactly one filled Lokara-Grün button. Everything else is
  secondary through ghost or outline styling, or tertiary as a text link. If two actions compete,
  one is wrong.
- **Progressive disclosure.** Show the common path. Put advanced options behind “Mehr anzeigen,” an
  accordion, or a details drawer; never confront the user with every field at once.
- **Content first, chrome last.** Let data and white space carry the screen. Do not add decorative
  borders or boxes where spacing is enough. The block motif is a rare accent, not a texture.
- **Restraint over reduction.** Minimal never means hiding a needed control or dropping a label.
  Reduce ornament, never clarity.

### 5.2 Spacing and layout

- Use the **8px spacing scale**: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64. Everything snaps to it.
- Prefer generous white space. Section padding is at least 24px; card padding is 16–24px.
- Constrain body and content columns to about 640–760px for readability; do not stretch prose
  full-bleed.
- Use calm surfaces: Paper background, an 8–12px card radius, 8px input/button radius, and one very
  soft elevation shadow. No heavy shadows or double borders.

### 5.3 Motion

CSS/Tailwind motion is **Shipped**. Framer Motion is selected but not installed and is **Future**.

- Keep motion fast and subtle: **150–250ms** for most UI, about 120–150ms for hovers, and about
  250–300ms for page or section transitions. If the duration attracts attention, it is too slow.
- Use ease-out for entrances, with a curve like `[0.16, 1, 0.3, 1]`, and ease-in for exits. Never
  use linear easing.
- Move only a little: fade plus 4–8px translate or a 0.98→1 scale. No large slides, spins, or
  bounces.
- Motion must explain a state change such as open, close, appear, or confirm. Never animate only for
  decoration.
- Respect `prefers-reduced-motion`; collapse to instant or opacity-only behavior.
- Preserve 60fps by animating only `transform` and `opacity`, never layout, width, height, top, or
  left.

### 5.4 Interaction feel

- Every interactive element has visible hover, focus-visible, active, and disabled states.
- Give optimistic, immediate feedback. A button shows pressed/loading state immediately; autosave
  uses a quiet “Gespeichert” confirmation rather than a blocking spinner for small saves.
- Use skeletons rather than spinners for content loads and keep the layout stable without content
  shift.
- Design empty states: one short line and the one action that fills the state.

### 5.5 Reference bar

Quality references are Apple system UI / apple.com, Linear, Stripe Dashboard, and Notion. Use their
calm colour, strong type hierarchy, tight motion, and generous air as a bar, not as designs to copy.

## 6. Current repository coverage and open gaps

| Area | Current repository truth | Status |
| --- | --- | --- |
| Web brand and semantic tokens | All palette, supporting White, status, tint, font, radius, and shadcn mappings in `packages/ui/src/tokens.css` | **Shipped** |
| Shared components | `Button`, `Card`, `Input`, `Label`, native `Select`, `StatusNote`, and `Table` exports | **Shipped** |
| Web fonts | Montserrat and Manrope weights 400/500/600/700 loaded with `next/font` in `apps/web/src/app/layout.tsx` | **Shipped** |
| Style guide | `/styleguide` demonstrates tokens, fonts, progressive disclosure, and shared components | **Shipped** |
| PDF palette | `statement.py` declares the six core brand tokens: Ink, Green, Forest, Mint, Slate, and Paper | **Shipped** |
| PDF legal typography | Tests enforce the six-token palette, exclusive tier assignment, tier-1 body-size and 7:1 floors, tier-2 4.5:1 floor with no size branch, line height, and tabular numerals | **Shipped** |
| Current motion | CSS/Tailwind transitions, including reduced-motion handling in the shared button | **Shipped** |
| Framer Motion | Selected dependency; not installed | **Future** |
| Mobile theme | Shared React Native token/theme object and app | **Future** |
| Logo and motif assets | Usage is specified, but no repository assets exist | **Future** |

Known delivery gaps are kept explicit instead of changing this contract silently:

- The generated PDF does not embed Montserrat or Manrope. Its stylesheet requests the brand faces
  and falls back to `Helvetica Neue`, then Arial. The exact resolved PDF font is environment
  dependent; the earlier snapshot recorded HelveticaNeue/ArialMT, which is **Not
  repository-verified** as a universal output fact.
- `Select` embeds the Slate hex in its inline SVG chevron instead of resolving the colour through a
  CSS token. `Card` uses an Ink-derived hard-coded `rgba(...)` shadow. Both are shipped source and
  remain gaps against the token-only rule; this documentation slice does not change them.
- `StatusNote` renders its success label as Green on Mint. The pair is 5,89:1 and passes AA, and the
  component also supplies a distinct icon and label, but the text use remains a gap against the
  stricter rule that Green on Mint must not carry meaning by itself.
- Presence of shared components and a style guide is not proof that every application screen passes
  the complete focus, keyboard, 200%-zoom, motion, one-primary-action, and spacing checklist. Each
  landlord-facing screen still requires its own review.

## 7. Appendices

### Appendix A — measured ratios of the brand pairs

The following values were recalculated from the shipped hex values with the WCAG 2.1
relative-luminance formula.

| Pair | Ratio | Role |
| --- | ---: | --- |
| Petrol Ink on Paper | **15,72** | Body copy on the page ground; legally required text |
| Petrol Ink on Mint | **13,91** | Text on a tinted surface; legally required text, default |
| Forest Deep on Paper | **11,32** | Headings on the page ground; quiet tier-1 text |
| Forest Deep on Mint | **10,01** | Legally required text with secondary emphasis |
| Lokara Grün on Paper | 6,66 | AA text, links, icons; not tier 1 |
| Lokara Grün on Mint | 5,89 | Decorative only; never body text or tier 1 |
| Slate on Paper | 5,44 | Tier 2 and non-legal secondary framing; never tier 1 |
| Slate on Mint | 4,81 | AA by 0,31; never tier 1 and avoid on re-tintable surfaces |

| Semantic pair | Ratio |
| --- | ---: |
| Danger on Paper | 7,01 |
| White on Danger | 7,26 |
| Warning on Paper | 6,85 |
| White on Warning | 7,09 |
| Success/Green on Paper | 6,66 |
| White on Success/Green | 6,89 |
| Danger on Danger Tint | 6,24 |
| Warning on Warning Tint | 6,35 |
| Success/Green on Success Tint/Mint | 5,89 |

### Appendix B — supersession and compatibility record

- The one-tier `legal-contrast` plus `legal-size` rule was superseded on **04.08.2026** by
  `legal-t1-size`, `legal-t1-contrast`, `legal-t2-contrast`, and `legal-t2-scale`. Tier 2 has no size
  floor. The heading **“Assigning a carrier to a tier”** remains a compatibility anchor.
- The pre-rewrite component mapping described `--primary-foreground` as Paper. The shipped and
  canonical mapping is White; Paper remains the app background.
- The pre-rewrite tint table reported Success/Green on Mint as **6,09:1** and said every semantic
  foreground on its tint was at least 6:1. Recalculation from `#1A6558` and `#E7EFEB` gives
  **5,89:1**. It still clears WCAG AA. The old 6,09 value is preserved here as superseded arithmetic,
  not as an active palette fact.
- The pre-rewrite status note said the shadcn destructive mapping was omitted. It is now shipped as
  Danger with White foreground.
- The exact 327-line document replaced by this living specification remains available with
  `git show 635acf9:docs/05-design-system.md`.
