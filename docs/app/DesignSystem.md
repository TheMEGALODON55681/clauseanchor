# Design System

The source of truth for how ClauseAnchor looks and reads. Every frontend part follows it and extends it. A new token or rule goes in this file in the same part that adds it.

Tokens are CSS custom properties in `frontend/src/index.css`. The tokens, type styles and colour changes that `FrontendDesign.md` adds land in FE-2, and this file is updated in that part. Until then it describes the baseline. The token `anchor/600` is `--anchor-600`, `status/review` splits into `--status-review-fg`, `--status-review-bg` and `--status-review-border`, and so on. Light values live under `:root`, dark values under `.dark`.

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
| `ink/tertiary` | `#7A7F85` | `#858079` | Captions, placeholders |
| `rule/default` | `#E2DCD0` | `#2C3137` | Borders, dividers |
| `rule/strong` | `#C9C1B2` | `#3E444B` | Input borders, emphasized dividers |
| `anchor/600` | `#0F4C5C` | `#6FB8C8` | Brand, primary action, accepted findings |
| `anchor/700` | `#0A3945` | `#8FCBD8` | Hover, pressed |
| `anchor/100` | `#E1EDEF` | `#15313A` | Tints |
| `focus/ring` | `#2F7FA0` | `#8FCBD8` | Focus outline, 2px, 2px offset |

`anchor/600` is a deep ink teal. It is the product's identity. Do not substitute a standard blue.

### 3.2 Color: semantic (every one must also carry an icon and a text label, never color alone)

| Token set | Light fg / bg / border | Dark fg / bg / border | Meaning |
|---|---|---|---|
| `status/found` | `#0F4C5C` / `#E1EDEF` / `#9CC3CC` | `#8FCBD8` / `#15313A` / `#2E5A66` | Clause located with validated confidence |
| `status/review` | `#8A5A0B` / `#FBF1DC` / `#E6C98A` | `#E8C27A` / `#33280F` / `#6B5320` | **Needs a lawyer** (abstained or review candidate) |
| `status/unvalidated` | `#5D636A` / transparent / `#9AA0A6` dashed | `#A8A29A` / transparent / `#5A6068` dashed | Confidence not validated for this category |
| `status/absent` | `#6E7278` / `#EFEDE8` / `#D6D1C6` | `#9A958D` / `#1F2327` / `#353A40` | No clause found at the validated threshold |
| `status/unavailable` | `#8C3B2E` / `#F6E6E2` / `#E2B8AF` | `#E3A195` / `#34201C` / `#6A3A31` | Processing did not complete (operational only) |
| `polarity/exposure` | `#9A4A1F` / `#F8E9DF` | `#E7A77F` / `#34231A` | Clause places a burden on the user's side |
| `polarity/protection` | `#3C6B48` / `#E5F0E7` | `#9BC9A6` / `#1C2D21` | Clause benefits the user's side |
| `polarity/mixed` | `#5B4E8C` / `#ECE9F5` | `#B6AAE0` / `#25213A` | Burden and benefit both apply |
| `polarity/neutral` | `#6E7278` / `#EFEDE8` | `#9A958D` / `#1F2327` | Mechanical clause, no direction |
| `polarity/unresolved` | `#6E7278` / transparent, dotted border | `#9A958D` / transparent, dotted border | Could not determine which party it affects |
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

Highlights are **underlines plus a faint tint**, never solid fills. Text must stay fully legible.

### 3.4 Typography

| Family | Role | Source |
|---|---|---|
| **Source Serif 4** | Contract text, quoted judgment passages, display headings | Google Fonts, OFL |
| **IBM Plex Sans** | All UI: buttons, labels, navigation, body UI copy | Google Fonts, OFL |
| **IBM Plex Mono** | Character offsets, hashes, citations metadata, keyboard hints | Google Fonts, OFL |

The fonts load from Google Fonts through a CSS import in `index.css`. That sends a request to a third party, which sits badly with the privacy promise. `FrontendDesign.md` section 11.1 proposes self-hosting (decision D3).

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
| `overline` | IBM Plex Sans, 600 | 11 / 16 | 8%, uppercase | Category group headers |
| `document/body` | Source Serif 4, 400 | 17 / 30 | 0 | Contract reading text |
| `document/number` | Source Serif 4, 600 | 17 / 30 | 0, tabular figures | Clause numbers (1.1, (a)) |
| `quote/passage` | Source Serif 4, 400 italic | 15 / 26 | 0 | Verbatim judgment text |
| `citation` | Source Serif 4, 500 small caps | 13 / 20 | 3% | Case citations |
| `mono/sm` | IBM Plex Mono, 400 | 12 / 18 | 0 | Offsets like `4210 to 4488`, hashes |

Contract reading measure: **68 to 80 characters per line**. Never justify contract text; left-align it.

### 3.5 Spacing, radius, elevation, layout

- **Spacing:** 4px base. Tokens `space/1` = 4 through `space/12` = 48, plus `space/16` = 64.
- **Radius:** `radius/sm` 4px (chips, inputs), `radius/md` 6px (buttons, cards), `radius/lg` 10px (panels, modals). **No full pill shapes** except the tiny count badge.
- **Elevation:** paper-like, almost flat. `elevation/1`: 0 1px 0 `rule/default` (a printed edge). `elevation/2`: 0 2px 8px rgba(27,31,36,0.06). `elevation/3` (modals only): 0 12px 32px rgba(27,31,36,0.12). No glows.
- **Borders:** 1px `rule/default` by default. Emphasis via a **4px left rule** in a semantic color (the "margin rule"), used on cards and notices.
- **Grid:** desktop 12 columns, 1280 frame, 24px gutters, 32px margins. Reader layout slots: left sidebar 280px, document column max 760px, right detail panel 400px. Mobile 4 columns, 360 frame, 16px margins.
- **Touch targets:** minimum 44 x 44 px on every interactive element.
- **Focus:** 2px `focus/ring` outline with 2px offset on every focusable component.
- **Motion:** 120ms ease-out for hover and press, 200ms ease-in-out for panels and drawers. Every animated component has a reduced-motion variant with no movement, only opacity.

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
- Reduced-motion variants for Spinner, Skeleton, Drawer and Stage progress.
- Dark mode for every component through the theme tokens.
- Text styles readable at 200% zoom; no text inside images.
