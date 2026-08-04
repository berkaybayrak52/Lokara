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
| `--color-slate`  | Slate       | `#5C6A6B` | —         | Muted text, borders, secondary labels — **never tier 1** |
| `--color-paper`  | Paper       | `#FBFBFA` | —         | App background / light surface                    |

### Contrast guidance (WCAG AA)

- Body text: Petrol Ink on Paper (very high contrast — safe).
- **Slate is for secondary text only** — verify ≥4.5:1 on its background; never use it for primary
  body copy on Paper at small sizes.
- **Slate is excluded from tier 1 outright — it is not a judgement call.** Slate reaches **5,44 on
  Paper** and **4,81 on Mint**; those are its only two grounds in this system, and **neither reaches
  7:1**. So there is no background on which Slate can carry verification content, and no size at
  which that changes — the AAA large-text relaxation is declined for tier 1 (see *Legally required
  disclosure* below). Picking Slate for legally required text is therefore always wrong, not usually
  wrong. Slate keeps its role on tier 2 and on non-legal secondary framing text, where 4,5:1 is the
  bar and it clears it on Paper. If a surface must be quiet **and** tier 1, buy the quietness with
  **weight** (400 against a 600/700 neighbour), never with a lighter ink: **Forest Deep** is the
  quiet tier-1 ink at 11,32 on Paper and 10,01 on Mint.
- Lokara Grün as a button background needs white/Paper text; verify ≥4.5:1 (it passes for normal text).
- Green-on-mint is decorative/low-contrast — never use it for text that must be read.

### Measured ratios of the brand pairs

Computed with the WCAG 2.1 relative-luminance formula from the hexes above. A palette fact — cite it,
don't re-derive it per surface.

| Pair                | Ratio     | Role                                                        |
| ------------------- | --------- | ----------------------------------------------------------- |
| Petrol Ink on Paper | **15,72** | body copy on the page ground; legally required text         |
| Petrol Ink on Mint  | **13,91** | text on a tinted surface; legally required text — default   |
| Forest Deep on Paper| **11,32** | headings on the page ground                                  |
| Forest Deep on Mint | **10,01** | legally required text, secondary emphasis                    |
| Lokara Grün on Paper| 6,66      | AA text, links, icons — **not** legally required text        |
| Lokara Grün on Mint | 5,89      | decorative only — never body text                            |
| Slate on Paper      | 5,44      | tier 2 and non-legal secondary framing text — **never tier 1** |
| Slate on Mint       | 4,81      | AA by 0,31 — **never tier 1**; avoid on re-tintable surfaces  |

### Legally required disclosure — two tiers, split by what the content is *for*

Body copy stays at **AA**. Content we show because a statute (or our own compliance rule) compels it
is held higher — but **not to one flat bar**. An earlier version of this section had a single tier
(`legal-contrast` ≥ 7:1 + `legal-size` ≥ body copy) over everything legally required; that was ruled
wrong on **04.08.2026** and is superseded by the two tiers below. The split is **by the job the text
does for the reader**, never by a size band or a word count.

Which text on a given document belongs to which tier is named by that document's spec (for the
statement: `docs/08`). The **thresholds live here and only here** — a design-system rule with two
homes is a rule waiting to disagree with itself.

#### Tier 1 — verification content (`legal-t1-size`, `legal-t1-contrast`)

**What it is.** The **four BGH formal minimums** — Gesamtkosten, Umlageschlüssel, Anteil des Mieters,
Vorauszahlungen — **and anything that explains them**: the Umlageschlüssel, the Bemessung, the
Gesamtbemessung, the amounts, the CO₂ reconciliation. Anything a reader needs in order to *recompute
their own share*.

**Why it is held highest.** German case law requires the statement to be **verständlich für einen
durchschnittlichen Mieter** — an average tenant must be able to follow it without expert help
(BGH-Mindestangaben on the formal validity of a Betriebskostenabrechnung, § 259 BGB). Tier 1 *is*
precisely the content that requirement is about. Text a reader squints at is disclosure in form only.

- **`legal-t1-size` — never smaller than body copy.** Set at **≥ the document's own body font-size**,
  read from the stylesheet, not against a constant. Deliberately comparative and deliberately
  anchored to *body copy*, not to "the smallest text on the page": the latter is satisfiable by
  shrinking everything else, which makes the page worse and the check pass.
- **`legal-t1-contrast` — ≥ 7:1 on its own background.** Provenance: **WCAG 2.1 Level AAA, Success
  Criterion 1.4.6 *Contrast (Enhanced)*** — 7:1 for normal text, 4.5:1 for large text (≥ 18 pt, or
  ≥ 14 pt bold). We do **not** take the large-text relaxation for tier 1: it is never set large.
  Qualifying token pairs, from the table above: **Petrol Ink on Paper (15,72)**, **Petrol Ink on Mint
  (13,91)**, **Forest Deep on Paper (11,32)**, **Forest Deep on Mint (10,01)**. Slate is retired from
  tier 1 at both 5,44 and 4,81. Tokens only — no ad-hoc hex, and no new colour is needed.

#### Tier 2 — provenance and attestation (`legal-t2-contrast`, `legal-t2-scale`)

**What it is.** The `Rechtsstand` stamps and the *"rechtskonform, keine Rechts- oder Steuerberatung"*
disclaimer. These state **where the rules came from** and **what the document is not**. They are
**not** part of the BGH minimums — no court requires a `Rechtsstand` line; it is **our own rule**,
from `CLAUDE.md` (*"Show `Rechtsstand MM/JJJJ` in every legal output"*, *"Tool, not advice"*). A
reader does not recompute anything from them.

**The bar: present and legible, not prominent.**

- **`legal-t2-contrast` — ≥ 4,5:1 on its own background.** Provenance: **WCAG 2.1 Level AA, SC 1.4.3
  *Contrast (Minimum)*** — the same bar as body copy, i.e. tier 2 is never *below* the page's ordinary
  standard. Slate on Paper (5,44) qualifies; Slate on Mint (4,81) qualifies numerically but is a
  0,31 margin and is discouraged for any surface that may be re-tinted.
- **`legal-t2-scale` — must scale.** It respects user zoom / text-size settings like everything else
  (`rem`, no capped scaling) — the BFSG requirement in *Typography* above. In a print PDF this is
  discharged by the medium: the viewer zooms the whole page. It is therefore **stated, not asserted**
  against a print stylesheet.
- **No size floor. Deliberately.** In the lead's words, recorded because it *is* the rule and not a
  footnote to it: *"I am not inventing a second magic number, and any ratio I picked would land
  conveniently on the current 8 pt, which is the same error as the 9,0 pt floor."* A tier-2 threshold
  derived by picking a fraction of body copy would be fitted to the page that already exists — that is
  the defect, not the fix. **Tier 2 has no size assertion, and a check that adds one is wrong until
  this paragraph changes.**

> **Why there is no absolute pt floor** (applies to both tiers). **DIN 1450** (Schriften —
> Leserlichkeit), the German legibility norm, specifies minimum sizes via **x-height and reading
> distance**, not point size; no point number falls out of it, so none can be cited. And the brand
> typefaces are **not embedded** in the generated PDF — it renders HelveticaNeue/ArialMT — so a pt
> floor asserted today would measure a font we do not ship. Any absolute number would be fitted to the
> defect it was written to catch. If an absolute floor is ever wanted, what would resolve it is an
> embedded-font decision plus a DIN-1450 x-height calculation at a stated reading distance — not a
> round number.

#### Assigning a carrier to a tier

Every carrier of legally required text belongs to **exactly one** tier — unassigned is not a state.
The question is not "how important does this look" but: **can the reader verify a number with it?**
If yes → tier 1. If it only says where the rule came from or what the document is not → tier 2.
Statutory *notices that change how a figure must be read* (e.g. "this Verbrauch is an estimate", "the
consumption key was replaced by the area key") are **tier 1**, because without them the printed
Umlageschlüssel is not the one that was applied.

Both tiers carry the usual typographic hygiene at these sizes: **line-height ≥ 1,4**, weight ≥ 400,
no all-caps, no negative letter-spacing, and `font-variant-numeric: tabular-nums` on numeric columns
so figures align for comparison.

**Rechtsstand 08/2026** for the legal basis cited here (BGH-Mindestangaben / § 259 BGB). WCAG 2.1 and
DIN 1450 are standards, not statute, and carry no `Rechtsstand`.

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

**Tailwind v4** (current major) — CSS-first config via the `@theme` directive, not a `tailwind.config.js`
`theme.extend`. Declare the tokens as theme CSS variables; utilities (`bg-ink`, `text-green`, …) and the
shadcn variables both read from them:

```css
/* globals.css */
@import "tailwindcss";

@theme {
  --color-ink:    #18212A;
  --color-green:  #1A6558;
  --color-forest: #123F37;
  --color-mint:   #E7EFEB;
  --color-slate:  #5C6A6B;
  --color-paper:  #FBFBFA;

  --font-display: "Montserrat", sans-serif;   /* headlines, big numbers */
  --font-sans:    "Manrope", sans-serif;      /* body, labels, tables */
}
```

No component uses a raw hex or an off-palette font — everything references a token
(this is checkable and is part of the UI Definition of Done in `CLAUDE.md`).

## Component layer — shadcn/ui (themed to these tokens)

The web app's component kit is **shadcn/ui** (copy-in React components on Radix + Tailwind), living in
the `ui/` workspace. shadcn is the base; the **brand tokens above are the theme** — never ship shadcn's
default palette.

- Map shadcn's CSS variables (`--background`, `--foreground`, `--primary`, `--muted`, `--accent`,
  `--ring`…) onto the brand tokens: `--primary` → Lokara Grün, `--primary-foreground` → Paper,
  `--background` → Paper, `--foreground` → Petrol Ink, `--muted` → Mint Tint, `--border`/`--ring` → Slate.
- Set the shadcn radius to the brand's 8–12px and fonts to Montserrat (display) / Manrope (text).
- It is fine to **overwrite** shadcn defaults to meet the brand board; the tokens win over shadcn's ships-with styling.
- Every shadcn component still owes the **WCAG 2.1 AA / BFSG** checklist below (contrast, focus, scalable type).

> Mobile (Expo/React Native) doesn't use shadcn (web-only). It shares the **same tokens + theme** through
> a React Native theme object, so colors, type scale, and radii match across platforms.

## Semantic status colors (resolved — extends the brand board)

The brand board ships no status palette, but the product needs one: destructive actions (delete a
building, revoke a membership), **form/validation errors** (a 422 must read as an error), the **3-colour
Zustell-Ampel** (§556 proof-of-receipt), and **Guard/Wächter** severity (§556 deadline, Eichfrist,
15%-AfA).

**Only two new hues are needed** — success reuses Lokara Grün (see the note below).

| Token             | HEX       | Contrast on Paper | White on it | Role                                        |
| ----------------- | --------- | ----------------- | ----------- | ------------------------------------------- |
| `--color-danger`  | `#A4262C` | **7.01** ✓        | **7.26** ✓  | Errors, destructive actions, Ampel *rot*    |
| `--color-warning` | `#92400E` | **6.85** ✓        | **7.09** ✓  | Warnings, pending guards, Ampel *gelb*      |
| `--color-success` | `#1A6558` | **6.66** ✓        | **6.89** ✓  | = **Lokara Grün** — confirmations, Ampel *grün* |

Tint surfaces (for alert/banner backgrounds), all with Ink text ≥13:1 and their own fg ≥6:1:

| Tint                   | HEX       | fg on tint | Pairs with |
| ---------------------- | --------- | ---------- | ---------- |
| `--color-danger-tint`  | `#FBEAE9` | 6.24 ✓     | `danger`   |
| `--color-warning-tint` | `#FBF1E5` | 6.35 ✓     | `warning`  |
| `--color-success-tint` | `#E7EFEB` | 6.09 ✓     | = **Mint Tint** (already in the palette) |

All values are computed WCAG ratios against Paper `#FBFBFA`; every one clears **AA (4.5:1)** for normal
text, so they're also safe as borders, icons, and large text (which need only 3:1). The trio sits at
7.01 / 6.85 / 6.66 — near-identical weight, so they read as a family rather than three loud accents.

**Why success is not its own green.** A dedicated success green (e.g. `#166534`) lands at a **1.03
luminance ratio to Lokara Grün** — same lightness, barely distinguishable, and worse for colour-blind
users. Reusing the brand green is cleaner: green already means "good" here. Distinguish a *success
message* from a *primary action* by **form, not hue** — primary actions are filled buttons; success
feedback is a **tint surface + icon + label**.

**Why warning looks like burnt ochre, not bright amber.** Any true amber (`#F59E0B`) fails AA on a light
background — around 2:1. At AA on Paper, "amber" is necessarily dark. This is a constraint, not a
compromise.

> **BFSG: never signal by colour alone.** Every status carries an **icon + text label** as well —
> required for colour-blind users, and the Ampel is legally meaningful (§556 Zugangsnachweis).

Wire them alongside the brand tokens in `@theme`, and map shadcn's `destructive` variant onto
`--color-danger` (it currently ships omitted):

```css
@theme {
  --color-danger:       #A4262C;
  --color-danger-tint:  #FBEAE9;
  --color-warning:      #92400E;
  --color-warning-tint: #FBF1E5;
  --color-success:      #1A6558;   /* = Lokara Grün */
  --color-success-tint: #E7EFEB;   /* = Mint Tint   */
}
```

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
- [ ] **Tier 1** (verification content — BGH minimums and anything that explains them) meets
      `legal-t1-contrast` (≥ 7:1, WCAG 2.1 AAA SC 1.4.6) **and** `legal-t1-size` (never smaller than
      body copy) — see *Legally required disclosure — two tiers* above.
- [ ] **Tier 2** (provenance/attestation — `Rechtsstand`, disclaimer) meets `legal-t2-contrast`
      (≥ 4,5:1, WCAG 2.1 AA SC 1.4.3) and `legal-t2-scale`. **No size floor** — do not add one.
- [ ] Every carrier of legally required text is assigned to exactly one tier.
- [ ] Visible focus states on all interactive elements (keyboard nav works end to end).
- [ ] Labels are explicit and always visible (no icon-only critical actions without a label/aria-label).
- [ ] Type scales with user zoom; layout survives 200% zoom.
- [ ] Motion (Framer Motion) respects `prefers-reduced-motion`.
