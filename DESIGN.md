---
name: Saudi API Catalogue
description: A verified, bilingual catalogue of Saudi APIs, built in the Al-Balad rawashin world.
colors:
  coral-stone: "oklch(0.936 0.006 75)"
  coral-stone-panel: "oklch(0.962 0.005 75)"
  teak-ink: "oklch(0.255 0.032 52)"
  teak: "oklch(0.34 0.045 50)"
  teak-muted: "oklch(0.45 0.03 55)"
  teak-hairline: "oklch(0.8 0.02 62)"
  rawashin-turquoise: "oklch(0.5 0.085 192)"
  turquoise-wash: "oklch(0.9 0.03 192)"
  lattice-shut: "oklch(0.84 0.016 65)"
  reach-green: "oklch(0.47 0.09 150)"
  degraded-amber: "oklch(0.55 0.12 70)"
  blocked-brick: "oklch(0.5 0.15 32)"
  code-teak: "oklch(0.255 0.032 52)"
  code-ink: "oklch(0.93 0.01 80)"
  night-teak: "oklch(0.205 0.018 52)"
  night-stone-ink: "oklch(0.93 0.008 75)"
  night-turquoise: "oklch(0.74 0.1 190)"
typography:
  display:
    fontFamily: "Readex Pro, ui-sans-serif, system-ui, sans-serif"
    fontSize: "3rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Readex Pro, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Readex Pro, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Readex Pro, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Readex Pro, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.4
  code:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.8rem"
    fontWeight: 400
    lineHeight: 1.625
rounded:
  sm: "0.075rem"
  lg: "0.125rem"
spacing:
  gutter: "1rem"
  row: "1rem"
  section: "2.5rem"
  container: "72rem"
components:
  button-primary:
    backgroundColor: "{colors.rawashin-turquoise}"
    textColor: "{colors.coral-stone-panel}"
    rounded: "{rounded.sm}"
    padding: "0 1rem"
    height: "2rem"
  input:
    backgroundColor: "{colors.coral-stone-panel}"
    textColor: "{colors.teak-ink}"
    rounded: "{rounded.sm}"
    height: "2rem"
  chip:
    textColor: "{colors.teak-ink}"
    rounded: "{rounded.sm}"
    padding: "0.125rem 0.5rem"
  invocable-tag:
    backgroundColor: "{colors.turquoise-wash}"
    textColor: "{colors.teak}"
    rounded: "{rounded.sm}"
    padding: "1px 0.375rem"
  code-block:
    backgroundColor: "{colors.code-teak}"
    textColor: "{colors.code-ink}"
    rounded: "{rounded.sm}"
    typography: "{typography.code}"
    padding: "0.75rem 1rem"
  facts-panel:
    backgroundColor: "{colors.coral-stone-panel}"
    textColor: "{colors.teak-ink}"
    rounded: "{rounded.sm}"
    padding: "0.75rem 1rem"
---

# Design System: Saudi API Catalogue

## Overview

**Creative North Star: "The Al-Balad rawashin"**

The directory reads like the carved wooden window screens of Jeddah's old town: dense,
ordered panels of fine teak rules on coral stone, where light comes through only where the
screen is open. Here the light is access. Every API carries a small carved lattice of five
apertures, lit in the painted turquoise of the rawashin, as many as the API is open: five
for open data, one for a restricted programme. The rest of the interface stays quiet and
standard so developers find things before they notice the world.

It is an Operate surface: familiar controls, dense ruled lists, a facts panel, code. The
world lends type, palette, density and the one signature move, never the layout or the
controls. It works in Arabic and English with the same weight, mirroring right-to-left,
with code, URLs and identifiers kept as left-to-right islands.

**Key Characteristics:**

- Coral-stone ground and teak ink; one accent, the rawashin turquoise.
- Ruled rows and panels with hairline teak borders and near-square corners.
- The access lattice on every API, lit by the access filter.
- One family (Readex Pro) for Arabic and Latin UI; JetBrains Mono only for code.
- No cards grid, no shadows for decoration, no eyebrow labels.

## Colors

A restrained palette: neutrals tinted from coral stone and teak, one accent, and three
state colours that appear only where they carry meaning.

### Primary

- **Rawashin Turquoise** (`oklch(0.5 0.085 192)`): primary buttons, links, focus rings,
  selection tint, and the lit apertures of the access lattice. At night it brightens to
  `oklch(0.74 0.1 190)`.

### Neutral

- **Coral Stone** (`oklch(0.936 0.006 75)`): the page ground. Low chroma: grey stone, not
  cream.
- **Coral Stone Panel** (`oklch(0.962 0.005 75)`): header, footer, inputs and panels.
- **Teak Ink** (`oklch(0.255 0.032 52)`): text, and the code ground.
- **Teak** (`oklch(0.34 0.045 50)`): the brand mark, method badges, lattice frames.
- **Teak Muted** (`oklch(0.45 0.03 55)`): secondary text; 4.5:1 or better on the ground.
- **Teak Hairline** (`oklch(0.8 0.02 62)`): borders and rules, usually at 15 to 40% for
  row dividers.
- **Lattice Shut** (`oklch(0.84 0.016 65)`): the closed apertures of the lattice.
- **Night Teak** (`oklch(0.205 0.018 52)`) and **Night Stone Ink**
  (`oklch(0.93 0.008 75)`): the dark scheme's ground and text.

### State

- **Reach Green** (`oklch(0.47 0.09 150)`): reachable.
- **Degraded Amber** (`oklch(0.55 0.12 70)`): HTTP error, timeout, beta, deprecated.
- **Blocked Brick** (`oklch(0.5 0.15 32)`): unreachable, TLS error, destructive.

### Named Rules

**The Light Is Access Rule.** Turquoise light marks openness and action. It never
decorates a surface that does neither.

**The Stone Not Cream Rule.** The ground stays grey stone at chroma 0.006; a warmer
ground drifts into the generic cream default.

## Typography

**Display Font:** Readex Pro (with ui-sans-serif, system-ui)
**Body Font:** Readex Pro
**Label/Mono Font:** JetBrains Mono, for code, URLs, parameters and identifiers only

**Character:** one variable family designed with matched Arabic and Latin, so a bilingual
page has one voice; the mono face appears only where text is literally code.

### Hierarchy

- **Display** (600, 3rem on desktop, 1.875rem on phones, 1.25): the home page's one
  statement.
- **Headline** (600, 1.875rem, 1.25): page titles (API, dataset, provider).
- **Title** (600, 1.25rem): section headings; 1.125rem inside detail pages.
- **Body** (400, 1rem, line height 1.6 in English and 1.8 in Arabic): prose capped at 65
  to 72ch.
- **Label** (400, 0.75rem to 0.875rem): fact labels, counts, row metadata.
- **Code** (JetBrains Mono, 0.8rem, 1.625): code blocks, paths, parameters.

### Named Rules

**The Code Is LTR Rule.** Code, URLs, JSON, HTTP methods and paths render left-to-right
inside Arabic pages, in their own element with `dir="ltr"`.

**The Arabic Leading Rule.** Arabic body text runs at line height 1.8, set once on
`html[lang="ar"] body`.

## Layout

A 72rem container with a 1rem gutter. Directory pages pair a 15rem filter column with the
results; detail pages pair the content with a 22rem facts column that sticks on desktop;
both collapse to one column below their breakpoints (`lg`, 1024px). Lists are ruled rows,
not cards: each API row splits into description (left) and a compact definition list of
access, authentication, endpoints and reachability (right). Sections are separated by
2.5rem, with more space above a heading than below it. Grid children shrink below their
content (`min-width: 0`) so code scrolls or wraps inside its block rather than widening the
page.

## Elevation & Depth

Flat. Depth comes from tonal layering (stone ground, lighter stone panels, teak code
blocks) and hairline teak rules. The only glow is the lit lattice when the access filter
selects its level (`drop-shadow(0 0 4px var(--lattice-open))`).

### Named Rules

**The Flat Facade Rule.** No decorative shadows; a surface is set apart by its tone and its
rule, as panels are on a carved facade.

## Shapes

Near-square corners (2px or less) everywhere: buttons, inputs, chips, panels, code
blocks. Borders are 1px teak hairlines. The lattice's apertures are diamonds (squares
rotated 45 degrees) in a ruled frame; the brand mark is one such aperture on a teak square.

## Components

### Buttons

- **Shape:** near-square (`0.075rem`).
- **Primary:** turquoise ground, stone text, 2rem high, 1rem padding; hover darkens to 90%.
- **Ghost:** used only inside code blocks (the copy button), stone text on teak.

### Chips

- **Style:** 1px teak border at 25%, no fill; hover turns the border and text turquoise.
  Used for search suggestions and sector links.
- **Invocable tag:** turquoise wash with teak text, marking APIs agents may call.

### Facts panel

- **Background:** stone panel; 1px teak border at 30%; rows divided by teak hairlines.
- **Layout:** a 6.5rem label column and a value column; values hold the lattice, auth
  schemes, pricing, formats, reachability, base URLs and the agent rule.

### Inputs / Fields

- **Style:** 1px input border, stone panel ground, near-square corners, 2rem high.
- **Focus:** border turns turquoise with a 2px ring; native selects keep native behavior.

### Navigation

- Header on the stone panel with a teak hairline below: brand mark and name, five plain
  links, the search field and the language switch, which keeps the page and its query.
  On phones the links wrap under the brand and the header search hides (pages carry their
  own search).

### Access lattice (signature)

Five diamond apertures in a 56 by 14 frame. Lit apertures count down from five (open) to
one (restricted); the frame mirrors in right-to-left pages so the count starts at the
reading edge. It carries an accessible name ("Access: Registration, 2 of 5, from open to
restricted"). Selecting an access filter lights every lattice of that level.

### Reachability chip

A 0.5rem dot in a state colour and the outcome; its tooltip and screen-reader text say when
the check ran and from which region.

### Code block

Teak ground, stone ink, JetBrains Mono at 0.8rem, a toolbar row with the copy button, and
either horizontal scroll (examples) or wrapping at token boundaries (one-line commands).

## Do's and Don'ts

### Do:

- **Do** show access with the lattice and its word together; never the lattice alone.
- **Do** keep lists as ruled rows with facts readable in the row.
- **Do** use turquoise only for action, focus, selection and lit apertures.
- **Do** write every UI string in both `messages/en.json` and `messages/ar.json`.
- **Do** use logical spacing and position utilities (`ms-`, `pe-`, `start-`) so pages mirror.

### Don't:

- **Don't** put a kicker or eyebrow label above a heading; context goes below it.
- **Don't** lay out APIs as a grid of same-size cards.
- **Don't** warm the ground into cream or add texture to suggest wood or stone.
- **Don't** use monospace for anything that is not code, a URL or an identifier.
- **Don't** add decorative shadows, gradients or glass.
