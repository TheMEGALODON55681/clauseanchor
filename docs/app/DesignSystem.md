# Design System

The source of truth for how ClauseAnchor looks and reads. Every frontend part follows it and extends it. A new token or rule goes in this file in the same part that adds it.

Tokens are CSS custom properties in `frontend/src/index.css`. The token `anchor/600` is `--anchor-600`, `status/review` splits into `--status-review-fg`, `--status-review-bg` and `--status-review-border`, and so on. Light values live under `:root`, dark values under `.dark`. Motion and width tokens are not themed and live under a second `:root` block. FE-2 added the motion tokens, the type styles, the colour changes in 3.1 and the patterns in section 6.

---

## 1. Product context

ClauseAnchor is a web app that reads a commercial contract and points at the clauses that carry risk. The user uploads a contract and says which party they are. The app highlights each clause of interest inside the document, says whether it runs for or against the user, flags clauses where Indian statute changes the effect, shows passages from real Indian court judgments about that kind of clause, and shows how confident it is. When it is unsure, it says **"Needs a lawyer"** instead of guessing.

The app never writes legal advice. Everything on screen is either text copied from the user's contract, text copied from a published judgment, or a short label. The UI must make that visible: quoted text looks quoted, labels look like labels, and nothing looks like a verdict.

**Who uses it:** small business owners, freelancers, employees and students reading a contract with no lawyer in the room. They are often anxious. The interface must feel **calm, precise and supportive**, like a careful senior colleague reading over their shoulder. Never alarming, never salesy, never cute.

**Design personality in three words:** Precise. Calm. Accountable.

---

## 2. Design concept: "Marginalia"

The signature idea: **findings look like a careful reader's marks in the margin of a printed document.** Lawyers annotate contracts with pencil underlines, bracket marks, marginal notes and section references. ClauseAnchor turns that craft into a digital system.

This concept is what makes the product unique. Apply it consistently:

- **The contract is paper.** Warm off-white page, serif body text, generous line height, real margins.
- **Findings are ink marks, not colored boxes.** Highlights are underlines and bracket marks with a faint tint, never heavy filled rectangles.
- **The risk strip is a margin ruler.** A thin vertical ledger rule with tick marks where findings sit.
- **Evidence cards are library index cards.** Ruled lines, a sepia edge, citations set in small caps.
- **Legal glyphs are the motif.** Section sign `§`, pilcrow `¶`, square brackets `⟦ ⟧` and the anchor icon appear as quiet structural elements.

**Explicitly avoid:** scales of justice, gavels, courthouse columns, shields, padlocks as decoration, stock "AI sparkle" icons, gradient blobs, glassmorphism, neon, pill-shaped buttons everywhere, generic SaaS blue (#3B82F6 family), red-for-danger verdict styling, emoji, mascots, illustrations of people.

---

## 3. Foundations

Every component references these tokens, never raw hex values. Each token has a light and a dark value.

### 3.1 Color: core

| Token | Light | Dark | Use |
|---|---|---|---|
| `paper/base` | `#F6F3EC` | `#131619` | App background |
| `paper/sheet` | `#FFFDF8` | `#1A1E22` | Contract page, cards |
| `paper/sunken` | `#EFEBE2` | `#0F1214` | Sidebars, wells, input backgrounds |
| `ink/primary` | `#1B1F24` | `#ECE7DD` | Body text, headings |
| `ink/secondary` | `#4E545B` | `#B4AEA3` | Supporting text |
| `ink/tertiary` | `#646970` | `#8B867F` | Captions, placeholders |
| `rule/default` | `#E2DCD0` | `#2C3137` | Borders, dividers |
| `rule/strong` | `#C9C1B2` | `#3E444B` | Dividers and emphasis rules. Not for controls |
| `control-border` | `#85817A` | `#6A6E72` | Outline of every input, radio, checkbox, switch, select and dropzone |
| `anchor/600` | `#0F4C5C` | `#6FB8C8` | Brand, primary action, accepted findings |
| `anchor/700` | `#0A3945` | `#8FCBD8` | Hover, pressed |
| `anchor/100` | `#E1EDEF` | `#15313A` | Tints |
| `focus/ring` | `#2F7FA0` | `#8FCBD8` | Focus outline, 2px, 2px offset |

`anchor/600` is a deep ink teal. It is the product's identity. Do not substitute a standard blue.

**FE-2 colour changes.** Seven values changed and one token is new. Each keeps its hue. Ratios are WCAG relative luminance, against the surfaces named, and `src/tokens.test.ts` asserts every new pair so a later edit cannot drop below the bar. Light surfaces are base `#F6F3EC`, sheet `#FFFDF8` and sunken `#EFEBE2`. Dark surfaces are base `#131619`, sheet `#1A1E22` and sunken `#0F1214`.

| Token | Mode | Old | New | Ratio, new (old) | Why |
|---|---|---|---|---|---|
| `ink/tertiary` | Light | `#7A7F85` | `#646970` | 4.99 base, 5.44 sheet, 4.65 sunken (3.64, 3.97, 3.39) | Captions and placeholders failed AA |
| `ink/tertiary` | Dark | `#858079` | `#8B867F` | 5.03 base, 4.64 sheet, 5.21 sunken (4.28 on sheet) | Failed AA on the sheet |
| `status/absent` text, `polarity/neutral` text, `polarity/unresolved` text | Light | `#6E7278` | `#666A70` | 4.65 on `#EFEDE8`, 5.35 on sheet (4.13, 4.76) | One shared value failed on the tinted chip. The three stay equal |
| `control-border` (new) | Light | `rule/strong` `#C9C1B2` | `#85817A` | 3.50 base, 3.81 sheet, 3.26 sunken (1.50 to 1.76) | Form outlines need 3:1 |
| `control-border` (new) | Dark | `rule/strong` `#3E444B` | `#6A6E72` | 3.53 base, 3.26 sheet, 3.66 sunken (1.70 to 1.91) | Same |
| `status/unvalidated` border | Light | `#9AA0A6` | `#8A9096` | 3.17 on sheet (2.60) | The dashed border is the only edge of a transparent chip |
| `status/unvalidated` border | Dark | `#5A6068` | `#7F858C` | 4.50 on sheet (2.64) | Same |

The focus ring (`#2F7FA0` light, 3.78 to 4.43 on the three surfaces, `#8FCBD8` dark, 9.3 to 10.5) already passed and is unchanged.

### 3.2 Color: semantic (every one must also carry an icon and a text label, never color alone)

| Token set | Light fg / bg / border | Dark fg / bg / border | Meaning |
|---|---|---|---|
| `status/found` | `#0F4C5C` / `#E1EDEF` / `#9CC3CC` | `#8FCBD8` / `#15313A` / `#2E5A66` | Clause located with validated confidence |
| `status/review` | `#8A5A0B` / `#FBF1DC` / `#E6C98A` | `#E8C27A` / `#33280F` / `#6B5320` | **Needs a lawyer** (abstained or review candidate) |
| `status/unvalidated` | `#5D636A` / transparent / `#8A9096` dashed | `#A8A29A` / transparent / `#7F858C` dashed | Confidence not validated for this category |
| `status/absent` | `#666A70` / `#EFEDE8` / `#D6D1C6` | `#9A958D` / `#1F2327` / `#353A40` | No clause found at the validated threshold |
| `status/unavailable` | `#8C3B2E` / `#F6E6E2` / `#E2B8AF` | `#E3A195` / `#34201C` / `#6A3A31` | Processing did not complete (operational only) |
| `polarity/exposure` | `#9A4A1F` / `#F8E9DF` | `#E7A77F` / `#34231A` | Clause places a burden on the user's side |
| `polarity/protection` | `#3C6B48` / `#E5F0E7` | `#9BC9A6` / `#1C2D21` | Clause benefits the user's side |
| `polarity/mixed` | `#5B4E8C` / `#ECE9F5` | `#B6AAE0` / `#25213A` | Burden and benefit both apply |
| `polarity/neutral` | `#666A70` / `#EFEDE8` | `#9A958D` / `#1F2327` | Mechanical clause, no direction |
| `polarity/unresolved` | `#666A70` / transparent, dotted border | `#9A958D` / transparent, dotted border | Could not determine which party it affects |
| `statute/flag` | `#43397A` / `#ECEAF6` / `#C4BEE3` | `#B9B0EA` / `#221E3A` / `#4A4275` | Indian statutory review flag |
| `evidence/case` | `#6B4E2E` / `#F5EEE3` / `#D9C7AC` | `#D7BD99` / `#2A2219` / `#56462F` | Court judgment evidence |

Rules for semantic color:
- `status/review` is warm ochre, deliberately calm. It means "a person should look at this", not "danger".
- `status/unavailable` (brick) is used only for technical failures, never for a legal finding.
- **Nothing in the system is red-for-risk.** Exposure is sienna, not red.
- All text on its background must meet **WCAG AA (4.5:1)**.

### 3.3 Highlight tints (for spans inside the contract text)

| Token | Light | Dark | Use |
|---|---|---|---|
| `mark/found` | underline `#0F4C5C` 2px + tint `#0F4C5C` at 8% | underline `#6FB8C8` 2px + tint 12% | Accepted finding |
| `mark/review` | underline `#B07A18` 2px dashed + tint `#B07A18` at 10% | underline `#E8C27A` dashed + tint 14% | Needs a lawyer |
| `mark/focused` | tint 18% + 1px outline in the status color + bracket marks | same, adjusted | Currently selected span |
| `mark/overlap` | stacked underlines, 2px each, 2px apart, max 3 visible then a `+n` marker in the margin | same | Two or more findings on the same text |

Highlights are **underlines plus a faint tint**, never solid fills. Text must stay fully legible. A found or review mark is drawn as two background layers, the underline over the tint, so the ink-in can sweep each one (section 6). The review underline is a repeating gradient, a 6px dash and a 4px gap.

### 3.4 Typography

| Family | Role | Source |
|---|---|---|
| **Source Serif 4** | Contract text, quoted judgment passages, display headings | Own origin, SIL OFL 1.1 |
| **IBM Plex Sans** | All UI: buttons, labels, navigation, body UI copy | Own origin, SIL OFL 1.1 |
| **IBM Plex Mono** | Character offsets, hashes, citations metadata, keyboard hints | Own origin, SIL OFL 1.1 |

The fonts are served from `frontend/public/fonts/`, so no page makes a request to a third party. There are twelve font files and the three licence texts: seven Latin-subset files (Source Serif 4 variable weight, normal and italic, IBM Plex Sans 400, 500 and 600, IBM Plex Mono 400 and 500) and five Latin-extended files (Source Serif 4 normal and italic, IBM Plex Sans 400, 500 and 600). Every `@font-face` carries a `unicode-range`, so a page fetches a Latin-extended file only when it holds a character in that range. The landing page requests none. Each family has a fallback face (`Georgia`, `Arial`, `Courier New`) with `size-adjust` and metric overrides, so the swap from the fallback to the web font does not move the layout. The line boxes match exactly at 24, 19 and 15 px and the widths are within 0.6 percent.

The rupee sign (U+20B9) comes from the Latin-extended files, and Source Serif 4 renders it in the contract text. The bracket marks `⟦ ⟧` and every non-Latin script fall back to a system font.

Type scale (sizes in px, line height in px):

| Style | Family, weight | Size / line | Tracking | Use |
|---|---|---|---|---|
| `display/lg` | Source Serif 4, 600 | 40 / 48 | -0.5% | Rare, marketing-level headings |
| `display/md` | Source Serif 4, 600 | 30 / 38 | -0.5% | Section titles |
| `heading/lg` | IBM Plex Sans, 600 | 22 / 30 | 0 | Panel titles |
| `heading/md` | IBM Plex Sans, 600 | 18 / 26 | 0 | Card titles |
| `heading/sm` | IBM Plex Sans, 600 | 15 / 22 | 0 | Group labels |
| `body/md` | IBM Plex Sans, 400 | 15 / 24 | 0 | Default UI text |
| `body/sm` | IBM Plex Sans, 400 | 13 / 20 | 0 | Secondary UI text |
| `label/md` | IBM Plex Sans, 500 | 14 / 20 | 0.2% | Buttons, inputs |
| `label/sm` | IBM Plex Sans, 500 | 12 / 16 | 0.4% | Chips, badges |
| `overline` | IBM Plex Sans, 600 | 12 / 16 | 8%, uppercase | Category group headers |
| `display/xl` | Source Serif 4, 500 | `clamp(2.5rem, 1.9rem + 2.2vw, 3.5rem)` (40 to 56) / 1.08 | -1% | The landing hero heading only |
| `display/md` | Source Serif 4, 600 | 30 / 38 | -0.5% | Section headings on the landing page |
| `section-mark` | Source Serif 4, 500 | 24 / 32, tabular figures, `anchor/600` | 0 | A "§ 1" mark in the margin column beside a section heading |
| `marginal-note` | IBM Plex Sans, 400 | 14 / 21, `ink/secondary`, 28 characters wide at most | 0 | A short note in the margin column or the aside |
| `prose/lg` | Source Serif 4, 400 | 19 / 32, `ink/secondary` | 0 | Body copy on the landing page and the long-form pages. UI text stays at `body/md` |
| `document/body` | Source Serif 4, 400 | 17 / 30 | 0 | Contract reading text |
| `document/number` | Source Serif 4, 600 | 17 / 30 | 0, tabular figures | Clause numbers (1.1, (a)) |
| `quote/passage` | Source Serif 4, 400 italic | 15 / 26 | 0 | Verbatim judgment text |
| `citation` | Source Serif 4, 500 small caps | 13 / 20 | 3% | Case citations |
| `mono/sm` | IBM Plex Mono, 400 | 12 / 18 | 0 | Offsets like `4210 to 4488`, hashes |

Contract reading measure: **68 to 80 characters per line**. Never justify contract text; left-align it.

Hero subline measure: capped at `66ch` (`max-w-[66ch]`), which gives a longest line of 71 characters from 768 to 1440 px. A cap of 68ch left a 75 character line. The hero heading needs none, and the sample sheet and quote in the hero are not capped (FrontendDesign.md 17.4, AM).

**12 px is the floor.** Nothing in the app renders below it. The classes are `t-display-xl`, `t-display-md`, `t-overline`, `t-section-mark`, `t-marginal-note` and `t-prose-lg` in `index.css`. The mono kicker is retired. `section-mark` sets tabular figures. Counts and metric cells do not yet, and FE-4 and FE-6 add `font-variant-numeric: tabular-nums` where numbers must align in a column.

**Heading rhythm in long-form text.** A heading sits closer to what it introduces than to what precedes it. Inside a `.flow` container an `h2` has 48 px above and 16 px below, an `h3` has 32 px above and 12 px below, and the first child has no top margin.

### 3.5 Spacing, radius, elevation, layout

- **Spacing:** 4px base. Tokens `space/1` = 4 through `space/12` = 48, plus `space/16` = 64, `space/24` = 96 and `space/32` = 128. The last two have no CSS token, because Tailwind derives `py-24` and `py-32` from `--spacing`.
- **Radius:** `radius/sm` 4px (chips, inputs), `radius/md` 6px (buttons, cards), `radius/lg` 10px (panels, modals). **No full pill shapes** except the tiny count badge.
- **Elevation:** paper-like, almost flat. `elevation/1`: 0 1px 0 `rule/default` (a printed edge). `elevation/2`: 0 2px 8px rgba(27,31,36,0.06). `elevation/3` (modals only): 0 12px 32px rgba(27,31,36,0.12). No glows.
- **Borders:** 1px `rule/default` by default. Emphasis via a **4px left rule** in a semantic color (the "margin rule"), used on notices (`NoticeBanner`), rule-flag cards (`RuleFlagCard`) and judgment cards (`JudgmentCard`), where it marks a different voice. Controls take `control-border`. `ErrorCard`, `Toast`, `ScopePanel`, `ManualReviewList` and `PerformanceTableRow` still carry the baseline 4px rule. FE-5 and FE-6 remove it from the ones they recompose. `RadioCard` and `PartyBindingField` lost it in FE-4. A chosen choice card takes a 2px `anchor/600` border and a tint instead.
- **Grid:** the marketing grid is the margin grid in section 6: a 9rem margin column, a 42rem main column and an aside, in a page 1200px wide. The Reader keeps its three panes: left sidebar 280px, document column max 760px, right detail panel 400px. FE-5 sets the Reader widths below 1440. Mobile is one column with 16px side gutters.
- **Touch targets:** a hit area of at least 44 x 44 px on every interactive element, reached with padding or the `.hit` class (a 44px `::after` centred on the control). The button sizes S 32, M 40 and L 48 are visual sizes. Neighbouring hit areas do not overlap.
- **Focus:** one rule in `index.css`: `:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px }`. Components carry no focus code of their own. `.focus-inset` pulls the ring inside for full-width rows. Programmatic focus on a heading or on `main` (`tabindex="-1"`) shows no ring.
- **Motion:** tokens in `index.css`, used by every component.

  | Token | Value | Use |
  |---|---|---|
  | `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | Everything entering. No overshoot |
  | `--ease-exit` | `cubic-bezier(0.4, 0, 0.2, 1)` | Everything leaving, and route changes |
  | `--dur-press` | 120ms | Hover and press |
  | `--dur-state` | 200ms | A state change, a chevron turning, a route cross-fade |
  | `--dur-panel` | 320ms | Panels, drawers, scroll reveals |
  | `--dur-ink` | 400ms | The ink-in sweep on a mark (`.ca-ink`, used by the landing hero and by the Reader from FE-5) |
  | `--stagger` | 50ms | Delay between siblings (first used for the Reader's rows entering, FE-5) |

  Animate `transform` and `opacity` only. One `prefers-reduced-motion` block at the end of `index.css` shortens every animation and transition to near zero, switches the route cross-fade off, and keeps the slow opacity fade on the spinner. Scroll behaviour is instant under it.
- **Widths:** `--w-page` 1200px, `--w-main` 42rem, `--w-margin` 9rem.

### 3.6 Iconography

- 20px and 16px grids, **1.5px stroke**, rounded caps and joins, outline style. Based on Lucide or Phosphor (regular).
- Custom glyphs in the same style: **anchor** (brand mark and "found"), **section sign §** (statutory flag), **pilcrow ¶** (clause), **bracket pair ⟦ ⟧** (span), **index card** (case evidence), **margin ruler** (risk strip), **hand-raised or person-with-document** (needs a lawyer; must feel like "ask a professional", not "error").
- Status icons: found = anchor; review = person-with-document; unvalidated = dashed circle; absent = empty bracket pair; unavailable = broken link or cloud-off.
- Polarity icons: exposure = downward arrow landing inside a bracket; protection = upward arrow leaving a bracket; mixed = two-way vertical arrow; neutral = short horizontal line; unresolved = question mark in a dotted circle. Do not use shields, locks or warning triangles.

---

## 4. Voice and microcopy (apply to every label in every component)

| Principle | Use | Never use |
|---|---|---|
| Describe, do not judge | "This clause limits what you can do after the contract ends." | "This clause is risky", "Dangerous", "Bad clause" |
| Supportive, not alarming | "Worth a closer look", "Needs a lawyer" | "Warning!", "Alert", "Critical" |
| Never imply safety | "No clause found at the validated threshold" | "Clear", "Safe", "All good", "No risks" |
| Never state law as fact | "Review under Section 27, Indian Contract Act 1872" | "This clause is void", "This is unenforceable", "Illegal" |
| Honest about the machine | "Confidence not validated for this category" | "AI is sure", "Guaranteed", "100% accurate" |
| Plain words | "Upload contract", "Who are you in this contract?" | "Ingest document", "Select stakeholder persona" |

Fixed phrases (use exactly, sentence case):
- "Needs a lawyer"
- "No clause found at the validated threshold"
- "Confidence not validated"
- "Not legal advice. ClauseAnchor points to text in your contract and in published judgments. It does not tell you what the law requires."
- "Your contract is processed in memory and deleted within 60 minutes."
- "Sample mode: showing a prepared example. Uploads are turned off."

Buttons use verb-first sentence case: "Upload contract", "Start review", "Download report", "Delete document", "View full passage".

---

## 5. Accessibility requirements

- Every color pair meets WCAG AA.
- **Status is never color-only**: every status has icon + text.
- Every interactive component has a visible focus state.
- Minimum 44px touch targets.
- Reduced-motion variants for Spinner, Skeleton, Drawer and Stage progress. One global rule covers them, and an element can opt out only with a reason.
- Dark mode for every component through the theme tokens.
- Text styles readable at 200% zoom; no text inside images.
- **Forced colours.** Windows high contrast removes backgrounds, which would erase every mark in the contract text. Under `forced-colors: active` a mark falls back to a 2px underline in `LinkText`, and the selected mark takes a `Highlight` outline.
- **Scrollbars stay visible.** Every scroll container uses `scrollbar-width: thin` with the thumb in `control-border`, and the Reader's panes set `scrollbar-gutter: stable`, so the cue that a pane scrolls stays and the layout does not shift.
- **Browser surfaces are themed.** `::selection` takes an ink tint (`rgba(15, 76, 92, 0.22)` light, `rgba(111, 184, 200, 0.32)` dark). `caret-color` and `accent-color` are `anchor/600`.
- **Page titles and focus.** Every route sets its own title ("How it works | ClauseAnchor"). Home keeps "ClauseAnchor". On a path change, focus moves to the page `h1`, or to `main` when there is none, so a screen reader announces the new page. Skip to content sits first in the tab order.

---

## 6. Patterns added in FE-2 to FE-4

| Pattern | Spec |
|---|---|
| `Container`, `Section`, `MarginGrid` | In `components/Layout.tsx`. `Container` is the page width (`--w-page`) with side gutters of 16px below 768, 24px from 768 and 32px from 1024. `Section` has vertical padding of 64, 96 and 128px at the same breakpoints, takes an `id` and `aria-labelledby`, and takes a `mark` (a "§ 1", hidden from assistive technology) for the margin column. `MarginGrid` is one column below 1024, margin and main from 1024 with the aside under the main column, and margin, main and a 320px aside from 1280 |
| Scroll reveal | `useReveal` in `lib/useReveal.ts`, with the pure core in `lib/reveal.ts`. An element rises 12px and fades in once, over `--dur-panel`. With no attribute it is visible, so the page reads without script and under reduced motion. The observer fires at 10 percent from the bottom edge |
| Disclosure | A native `<details>` in `components/Disclosure.tsx` with a chevron, a 44px summary row and a hairline below. The browser supplies the keyboard behaviour. The ring is the global one |
| Link | `components/Link.tsx`. A link inside a sentence is underlined 1px at `0.2em` offset, and a visited one turns `ink/tertiary` (the baseline visited colour could not be told from the link colour). Navigation and external links keep the anchor colour and get a 44px hit area. A `#/` address goes through the router with a view transition |
| Route transition | A 200ms cross-fade of the whole page through the View Transitions API, with an instant change where the browser lacks it |
| Not found and load error | `NotFound` and `RootError` are plain editorial pages with no warning colour. A bad address is not an error in the product and not an expired session. `RootError` shows no error text, because it could carry contract text |
| Preview controls | Development only, in `components/PreviewControls.tsx`. A floating drawer holding the mock adapter's switches and the gallery link. It is loaded behind `import.meta.env.DEV`, so a production build holds none of it |
| Favicon | `public/favicon.svg`, the logomark, with a dark-mode variant. One SVG covers the 16 and 32px sizes |
| Ink-in | `.ca-ink` in `index.css`. A found or review mark is two background layers, the underline over the tint, and `ca-ink` animates both `background-size` values from zero over `--dur-ink`, starting at `--ink-delay`. The mark's own style is the final state and the keyframe carries only the start, so a mark that cannot animate is simply drawn. The Reader adopts it in FE-5 |
| Hero demo | `pages/landing/HeroDemo.tsx`, styled by `.hero-demo` in `index.css`. One run: the sheet is still for 600ms, the mark inks in from 600 to 1000ms, the ruler tick fades in from 1000 to 1200ms and the panel rises 12px over `--dur-panel` from 1200 to 1520ms. Hover or focus inside the sheet or the panel pauses it. "Next example" replays the run with a new React key. Reduced motion draws the final state. The ruler is hidden below 640px |
| Section frame | `SectionFrame` in `components/Layout.tsx`: the rule above, the vertical rhythm and the page width. `Section` is a `SectionFrame` holding one `MarginGrid`. A section that needs several grid rows, such as How it works, builds them inside a `SectionFrame` |
| Button as a link | `Button` takes `to`, a router address, and then renders a router link with the same look and the 44px hit area. Without `to` it is a `button` |
| Labels, not controls | A component that shows a fact and has no action is not a button. `StatuteTag` is a label. `RuleFlagCard` has no "Read the section" button until the data holds the statute text. `ConfidenceBand` is plain text until the data gives a calibration scope, and then its label opens a popover. `ClauseDetailPanel` shows Close only with `onClose` and Case law only when case law data is given |
| Choice card | `RadioCard` in `components/RadioCard.tsx`, styled by `.radio-card` in `index.css`. A label around a native radio input, so the group has one tab stop and the arrow keys move inside it. The card is at least 44px high. The chosen card has a 2px `anchor/600` border (the 1px border and a 1px inset line), the `anchor/100` tint and a check icon, so the state does not rest on colour. It can carry a tag such as "Suggested" after its title and extra content under its description. Each group has its own name, made with `useId`, so two groups on one page never un-check each other |
| Stepper | The text "Step 2 of 3" and, from 1024px in the margin column, an ordered list of the three step names with `aria-current="step"` on the current one. The step number uses tabular numerals. No percentage bar. The step heading takes focus on a change of step |
| Summary | `pages/start/Summary.tsx`. A list of File, Role, Party and Scope, each reading "Not chosen yet" until decided. It shows in the aside from 1280px and in step 3 below that. On steps 1 and 2 below 1280px it is one line of the chosen values joined by a middle dot. It has no Change link |
| Header action | The primary "Review a contract" button sits at the far right of the header from 768px and inside the menu below it. It is absent on `/start` and in the Reader, which have their own primary action |
| Loading button | `Button` in the `loading` state shows a spinner, sets `aria-busy` and ignores clicks. It is not `disabled`, so keyboard focus stays on it |

The Reader rail is defined here when FE-5 builds it.
