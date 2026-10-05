# Frontend Design Direction

The plan for rebuilding the ClauseAnchor frontend on top of the imported baseline. It follows `DesignSystem.md`, which stays the source of truth for tokens and voice, and it extends that file where this one says so. FE-1 wrote it. FE-2 to FE-R build to it and keep it true to what was built.

Status: for review. No file under `frontend/src` has changed in FE-1.

---

## 0. How to read this file

Sections 1 to 3 hold the rules, the audit and the principles. Sections 4 to 7 say what to build. Sections 8 and 9 cover the words and the trust map, 10 to 13 how the work runs, 14 to 16 the part scopes, decisions and deviations, and 17 the amendments from the design review.

Three labels recur. **Decided** binds FE-2 onward unless Aryan changes it. **Open** needs an answer and is listed in section 15. **Estimate** has not been measured yet, and the section names the part that measures it.

Figures in the audit come from the production build served by `pnpm preview`, driven through a headless Edge with extensions disabled, at 375 and 1280 px in the light theme unless a row says otherwise. Screenshots are in `frontend/.screens/FE-0/` (70 images, every view at five widths and both themes) and `frontend/.screens/FE-1/` (16 images of states). Both folders are gitignored.

---

## 1. Constraints and quality bars

This section moved here from `Phases.md`, which keeps a one-line pointer.

### 1.1 Standing constraints for every FE part

- Frontend parts edit `frontend/`, `docs/app/` and `README.md`. They never touch `backend/`, `ml/`, `docs/ml/` or root config. Git is read-only for the assistant; Aryan runs every write.
- No dependency is added without approval. A request names the package, its gzipped size, its licence and why CSS or a few lines of code cannot do the job.
- `src/api/client.ts` is the only data interface. Components never import the mock.
- Nothing goes to localStorage, sessionStorage, IndexedDB or cookies. The session, the contract text and the job ids live in React memory only.
- Every slice of contract text goes through `lib/offsets.ts`. A backend offset is never applied to a JavaScript string directly.
- The UI never writes legal advice. Each string on screen is text quoted from the contract, text quoted from a published judgment, or a short label.
- No em dashes or en dashes anywhere. No tool, assistant or generator names in `frontend/`, `README.md` or commit messages.

### 1.2 Checks every part runs before it stops

- `pnpm install --frozen-lockfile`, `pnpm typecheck` and `pnpm build` pass with no warnings. From FE-2 on, `pnpm test` passes too.
- The dev server starts and every route renders with no console error or warning.
- Screenshots at 375, 768, 1024, 1280 and 1440 px, light and dark, for every route the part touched, in `frontend/.screens/<part>/`. Runs use a headless browser with extensions disabled.
- The tool-name grep over `frontend/`, the `Rules.md` section 1 scrub, and the dash check over `frontend/src`, `docs/app` and `README.md` print nothing.
- No calibration figure is hard-coded: `grep -rnoE "Calibrated on [^\"]{0,40}|[0-9]+ examples from [0-9]+ contracts|Reviewed as of [^\"]{0,20}" frontend/src frontend/dist` prints nothing. While no verified passage is set for the landing Evidence section (D7), `grep -rl "Evidence you can check" frontend/dist` prints nothing too.
- `/ponytail:ponytail-review` on the part's diff. Every P1 is fixed. Every P2 is listed with what was done.
- If Windows App Control blocks a native binary, stop and report the file and the error. Do not swap the toolchain.

### 1.3 Quality bars, measured at FE-R

| Bar | Target |
|---|---|
| Lighthouse, mobile, route `/` | Performance 95 or more, Accessibility 100, Best Practices 95 or more, CLS under 0.05, LCP under 2.5 s |
| axe | Zero serious or critical issues on every route, in both themes |
| Keyboard | A keyboard-only run from landing to start to reader to clause to judgment, with a visible 2 px focus ring everywhere and 44 px targets |
| Contrast | WCAG 2.2 AA in light and dark |
| Bundle | Initial-route JavaScript under 200 KB gzipped. The actual figure is reported (143 KB at FE-0) |
| Fonts | Served from our own origin. No request to a third-party host on any route |
| Reading measure | An average of 68 to 80 characters on the full lines of the reader's contract text at 1280 px and wider (section 2.4) |

---

## 2. Audit of the baseline

Severity: **P1** breaks a stated promise or a quality bar, **P2** weakens the experience, **P3** is polish. The last column is the part that fixes it.

### 2.1 Privacy, structure and accessibility

| ID | Finding | Evidence | Sev | Part |
|---|---|---|---|---|
| A1 | The fonts load from Google Fonts on every route, which contradicts "nothing leaves your session" | `fonts.googleapis.com` and `fonts.gstatic.com` requested on all routes | P1 | FE-2 |
| A2 | Expired, NotFound, Reader and Gallery have no `h1` | DOM audit, all four routes | P1 | FE-2, FE-5, FE-6 |
| A3 | `document.title` is the constant "ClauseAnchor" on every route, and focus does not move on a route change. Only the skip link focuses `main` | DOM audit | P1 | FE-2 |
| A4 | The unknown-route catch-all renders the "session expired" page, which is wrong for a bad URL | `routes.tsx` | P1 | FE-2 |
| A5 | 13 of 21 controls on the mobile home are under 44 px: the logo link (165 by 31), the theme and menu buttons (32 by 32), nav links (21 tall), the Switch (40 by 24), Dismiss (24 by 24), Choose file (105 by 40), the Accuracy sort buttons (32 tall) | DOM audit, 375 px | P1 | FE-2 |
| A6 | `DesignSystem.md` contradicts itself: button sizes S 32 and M 40, and "44 minimum" | Section 3.5 against section 5 | P2 | FE-2 |
| A7 | The skip link shows the browser default focus ring (auto, 1 px), not the 2 px ring | Focus run | P2 | FE-2 |
| A8 | The seven role cards are seven tab stops. A radio group should be one stop with arrow keys | Focus run, Home | P2 | FE-4 |
| A9 | In How it works the "§" sits inside the `h2` text, so a screen reader reads it | `HowItWorks.tsx` | P3 | FE-6 |
| A10 | The footer link "Data sources and credits" opens the top of How it works, not the Credits section | `Root.tsx` passes `#/how-it-works` | P3 | FE-6 |
| A11 | The mobile menu button has no `aria-expanded` or `aria-controls` | `AppHeader.tsx` | P2 | FE-2 |
| A12 | No favicon, so every cold load logs a 404 for `/favicon.ico` | Console, all routes | P3 | FE-2 |

### 2.2 Contrast (computed, WCAG relative luminance, 70 pairs)

Every failing pair is in the table in 5.4, with its old and new ratio. In short: light `ink/tertiary` and the shared grey of `status/absent` and `polarity/neutral` miss 4.5, dark `ink/tertiary` misses 4.5 on the sheet, and the input, radio and unvalidated borders miss 3.

The chip borders for found and needs-a-lawyer (1.4 to 2.0) are not a failure. Those chips are identified by an icon and a text label, so the border carries no information, and WCAG 1.4.11 does not require it. Decorative dividers (`rule/default`) are likewise exempt.

### 2.3 Layout and composition

| ID | Finding | Evidence | Sev | Part |
|---|---|---|---|---|
| B1 | The reader's contract column is too narrow. See 2.4 | Measured at four widths | P1 | FE-5 |
| B2 | The sidebar's Review scope card and its Validated, Pooled and Not validated counts take about half the first view, so the category list starts low | `reader-selected-found-1280-light.png` | P2 | FE-5 |
| B3 | Category names truncate to one letter ("E") or "Notice Period to ..." because the status chip and the count badge squeeze them | Same screenshot | P1 | FE-5 |
| B4 | The margin ruler renders as one short tick, not the ledger strip `DesignSystem.md` describes. It may be sticky-short by design, which FE-5 checks first | Same screenshot | P2 | FE-5 |
| B5 | At 375 px the reader toolbar wraps "Download report" and "Delete document" onto two lines | `reader-375-clause-sheet-light.png` | P2 | FE-5 |
| B6 | At 1024 px the clause panel is still docked, which leaves about 50 characters per line | `reader-1024-light.png` | P1 | FE-5 |
| B7 | The Accuracy page is 5779 px tall at 375, its columns clip ("Not measured" is cut off) and 230 text nodes are under 12 px | DOM audit | P1 | FE-6 |
| B8 | `/gallery` scrolls horizontally at 1280 and ships in the production build with the mock settings panel from Home | DOM audit, `Home.tsx` | P1 | FE-2 |
| B9 | The mobile drawer animates `height` and `width`, which forces layout on every frame | Impeccable detector | P3 | FE-2 |

### 2.4 Reader measure (the corrected figures)

The contract column measures 392 px at 1024, 368 px at 1280, 528 px at 1440 and 588 px at 1920. The serif at 17 px averages 7.83 px per character (canvas measurement of Source Serif 4, weight 400, over a 425 character sample). By width, one line holds about **50, 47, 67 and 75 characters**. The target is 68 to 80. Only 1440 and wider come close, and 1280 is the width most laptops use.

A first pass at this audit counted wrapped lines and reported 35, 54 and 54. That method understates, because inline marks and short last lines inflate the line count. A direct count of the full lines (every line except the last of each paragraph, over 13 paragraphs of the sample) gives an average of **47.5, 44.3, 65.9 and 73.7** at 1024, 1280, 1440 and 1920. Capacity by width runs 1 to 3 characters above that, so it is a fair quick estimate. FE-5 accepts on the full-line average and uses capacity by width while tuning.

### 2.5 Landing composition

| ID | Finding | Evidence | Sev | Part |
|---|---|---|---|---|
| C1 | The hero has no call to action. The upload form sits about 1000 px down at 375, below an argument the visitor has not asked for yet | `home-light-375.png` | P1 | FE-3 |
| C2 | The mono kicker "§ CONTRACT REVIEW, INDIA" above the heading is a template tell and says nothing | `Home.tsx` | P2 | FE-3 |
| C3 | The "01 02 03" steps in the hero repeat What happens next and How it works | `Home.tsx` | P2 | FE-3 |
| C4 | The does and does-not cards are two equal boxes. The page has no moment where the product shows itself working | `home-light-1280.png` | P2 | FE-3 |
| C5 | The privacy and legal-scope notices sit below the Start button as two stacked banners, after the decision to upload | `home-light-1280.png` | P2 | FE-4 |
| C6 | The counts "27 validated, 14 pooled, 5 not validated" are mock values. They must not appear on the landing page | `catalogue.ts` | P1 | FE-3 |
| C7 | The mock judgments carry the citation "[Placeholder citation]" and the provenance status `placeholder`. Showing one on the landing page would be fake proof | `mock.ts` | P1 | FE-3 |
| C8 | The Start button's help line says "The review takes about a minute on real documents." Nothing measures that yet, and the CPU benchmark is part 4-C | `Home.tsx` | P2 | FE-4 |

### 2.6 Motion and code signals

- No animation runs on the home page, with or without reduced motion. Six transitions exist outside the gallery.
- Reduced-motion guards exist only in `index.css` (`.shimmer`, `.reduce-motion-safe`) and in the Reader. The new motion in this plan needs one global guard (section 7.4).
- The impeccable detector found five side-stripe hits, a 4 px left border on `CategoryRow`, `ClauseDetailPanel` (two), `JudgmentCard` and `Gallery`. The 4 px margin rule is the brief's brand device, so the plan keeps it where it means something and removes it where it only decorates (section 3.3).
- Performance baseline, local and unthrottled, which is not a Lighthouse run: LCP 156 ms, CLS 0, 7 requests, two third-party hosts (the fonts). The build is 491.26 kB of JavaScript, 143.37 kB gzipped.

---

## 3. Principles

### 3.1 The seven principles from the brief, applied

1. Show, don't claim. The landing hero runs the product (section 6.1).
2. Honesty is the conversion argument. State the limits and the abstention.
3. Specificity signals competence. Exact section paths, offsets, court and year, confidence bands.
4. Reassure at the point of action. The privacy line sits next to the upload.
5. One primary action per screen. "Review a contract" is the primary action. "Try the sample contract" is the low-commitment alternative.
6. Visible progress. Real counts, never a fake percentage.
7. No dark patterns. No timers, no hidden costs, no confirm-shaming.

### 3.2 Design principles for this system

- **The margin is the layout device.** A narrow left column holds § marks and short notes. The text column is the measure. Nothing floats on a full-width canvas.
- **Sections sit on the page.** Space and a single rule separate them. A boxed card is reserved for the things that are cards in the product: a notice, a judgment, a clause panel.
- **Findings are ink.** An underline and a faint tint mark them. The one accent is ink teal. Ochre means "a person should look".
- **Editorial and exacting.** Serif for reading and headings, sans for interface, mono for offsets and keys. Numbers are specific and adjectives are rare.
- **Calm.** Motion confirms a state change. Nothing loops.

### 3.3 The 4 px margin rule, narrowed

The brief calls the 4 px left rule the brand device. The detector flags it as a side stripe when it appears on every card. **Decided:** keep it on notices (`NoticeBanner`, `RuleFlagCard`) and on the judgment card, where it marks "this is a different voice". Remove it from `CategoryRow`, `ClauseDetailPanel` sections and the Gallery. The selected category row takes a tint and the bracket mark ⟦ in `anchor/600`. `DesignSystem.md` 3.5 changes at FE-2 to say this.

### 3.4 Banned, in full

From the brief:

- **Layout clichés:** a centred hero over a gradient, three identical icon cards in a row, bento grids for decoration, testimonial carousels, logo walls, "Trusted by" bars.
- **Fake proof:** star ratings, counters, or any number without a citable source.
- **Decoration:** gradient blobs, glassmorphism, neon glow, purple to blue, heavy drop shadows, `rounded-2xl` on everything, pills other than `CountBadge`, emoji, sparkle or AI icons, gavels, scales, shields, courthouse columns, stock illustrations of people.
- **Motion gimmicks:** scroll-jacking, cursor followers, decorative parallax, autoplay video, bouncy springs, typewriter headlines.
- **Copy:** "revolutionize", "unlock", "seamless", "empower", "supercharge", "cutting-edge", "AI-powered", "in seconds", and any promise of a legal outcome. In UI copy also never "safe", "risky", "void", "clear" or "danger" (`DesignSystem.md` section 4).

Added by this audit:

- A mono kicker above a heading. A numbered "01, 02, 03" row that decorates instead of navigating.
- Two equal boxes side by side where one idea needs one column.
- A claim of "free", "instant" or "accurate". Pricing is unconfirmed and accuracy is a measured figure.
- A claim that no third-party request is made, until FE-2 self-hosts the fonts and FE-R verifies it.
- Any statistic about missed clauses or the cost of contract review, until someone supplies a source.

---

## 4. Information architecture

The target IA from the brief stands. Changes are called out with a reason.

### 4.1 Routes

| Route | Page | `h1` | Document title | Primary action |
|---|---|---|---|---|
| `/` | Landing | Hero heading | ClauseAnchor, then the hero line | Review a contract |
| `/start` | Stepped start flow, step in `?step=1`, `2` or `3` | Review a contract | Review a contract \| ClauseAnchor | Next, then Start review |
| `/review/:documentId` | Reader | Visually hidden, the filename is not used | Review \| ClauseAnchor | Download report |
| `/how-it-works` | Long-form explainer | How it works | How it works \| ClauseAnchor | Review a contract |
| `/accuracy` | Measured performance | How well each category is found | Accuracy \| ClauseAnchor | Review a contract |
| `/expired` | Session ended or document deleted, `?reason=deleted` | The variant heading | Session ended \| ClauseAnchor | Review a contract |
| `*` | NotFound (new) | We could not find that page. | Page not found \| ClauseAnchor | Review a contract |
| `/gallery` | Component gallery | None | None | Development builds only |

Reasons for the changes:

- **`/start` is new** because one decision per screen converts better than one long form, and parsing can run while the user picks a role. The `?step=` search parameter makes Back, reload and deep links work with the hash router.
- **NotFound is new** because a bad URL is not an expired session. Today the catch-all renders Expired.
- **The Reader title never includes the filename.** Browser history keeps page titles, and the promise is that nothing is kept after the session.
- **The Reader's `h1` is visually hidden** because the toolbar already shows the filename as the visible heading. The hidden `h1` reads "Contract review".
- **Titles use a vertical bar,** not a dash.

React 19 hoists a `<title>` element rendered inside a page into `document.head`, so each page renders its own title. No hook or dependency is needed.

### 4.2 Navigation

- **Header, from left to right:** logo (home), How it works, Accuracy, the quiet label "Not legal advice", the theme toggle, then the primary button **Review a contract** at the far right. The old "Review" link goes, because it duplicated the primary action.
- **The header button is hidden on `/start` and `/review/*`,** where the page has its own primary action. Below 768 px the header shows the logo, the theme toggle and a menu button. The menu holds How it works, Accuracy and the button.
- **The "Not legal advice" label stays.** Removing a disclaimer from the one place the Reader shows it (the Reader has no footer) would be a regression.
- **Footer, three groups:** Product (Review a contract, How it works, Accuracy), Sources (CUAD, OpenNyaya, NyayaAnumana, "Data sources and credits" opening the Credits section) and the two fixed lines (the legal-scope line and the privacy line). The Credits link carries the section id in router state, because the hash router cannot use a fragment.
- **The menu button** gets `aria-expanded` and `aria-controls`, and Escape closes it.

### 4.3 Route changes

**The journey, with every exit (amendment B):**

```text
Review a contract (header, hero, mid-page, final)  to  /start step 1, then step 2, then step 3, then /review/:id
Try the sample contract (hero, final)              to  /start?sample=secondment, which lands on step 2
/review/:id, Delete document                       to  /expired?reason=deleted
/review/:id, session ended, reload or pasted link  to  /expired
Header: How it works, Accuracy.   Footer: the same links, and Credits.
```

A `/review/:id` URL opened with no session in memory, which a reload or a pasted link produces, goes to `/expired`. The Reader already does this and FE-5 keeps it.

On a pathname change, the app sets focus on the page's `h1` (made programmatically focusable, no visible ring on programmatic focus) or on `main` when there is none, and scrolls to the top except inside the Reader. Search parameter changes, such as `?step=`, move focus to the new step heading and do not scroll.

---

## 5. Layout system and tokens

### 5.1 Breakpoints

375 is the design width for phones. Layouts change at 768, 1024, 1280 and 1440, using Tailwind's `md`, `lg` and `xl` plus a `min-[1440px]` variant. No new breakpoint token is added. The Reader keeps `useMedia` because its drawers need state.

### 5.2 Layout primitives (built in FE-2)

| Primitive | Behaviour |
|---|---|
| `Container` | Content width max 1200 px (`--w-page`), centred. Side padding sits outside that width: 16 px below 768, 24 px from 768, 32 px from 1024 |
| `Section` | Vertical padding 64 px below 768, 96 px from 768, 128 px from 1024. Takes an `id` and an `aria-labelledby`. Takes an optional `mark` rendered in the margin column |
| `MarginGrid` | From **1280 px**: `grid-template-columns: 9rem minmax(0, 42rem) minmax(0, 1fr)` with a 2 rem column gap. The three children are the margin, the main column and the aside. From 1024 to 1279 px: two columns, the margin and the main column, with the aside content stacked under the main content. Below 1024 it is one column and the margin content renders inline above the main column |

The three live in one file, `components/Layout.tsx`, and not in a `layout/` folder (amendment N). At 1280 px and wider the aside is 320 px (1200 minus 144, 672 and two 32 px gaps). The three-column grid starts at 1280 and not at 1024 because at 1024 the aside would be about 80 px, too narrow for a clause panel (amendment I). The § mark is decorative and `aria-hidden`. The main column's 42 rem measure gives about 75 characters of 19 px serif.

The `/start` flow uses `MarginGrid` too: a 640 px form column in the main slot and the summary rail in the aside slot. The aside shows only from 1280 px, the same width at which the grid gets its third column (17.4, AE).

### 5.3 Type

`DesignSystem.md` 3.4 stays. These are added or changed:

| Style | Spec | Use |
|---|---|---|
| `display/xl` | Source Serif 4, 500, `clamp(2.5rem, 1.9rem + 2.2vw, 3.5rem)` (40 to 56 px), line height 1.08, tracking -1% | Landing hero heading only |
| `overline` | 11 changes to **12** / 16, 600, tracking 8%, uppercase | Group headers. 12 px is the floor for all text |
| `section-mark` | Source Serif 4, 500, 24 / 32, tabular figures, `anchor/600`, content "§ 1" | In the margin column beside a section heading |
| `marginal-note` | IBM Plex Sans, 400, 14 / 21, `ink/secondary`, max 28 characters wide | Short notes in the margin column or the aside |
| `prose/lg` | Source Serif 4, 400, 19 / 32, `ink/secondary` | Body copy on the landing page and the long-form pages. UI text stays at `body/md` 15 / 24 |

The mono kicker is retired. `mono/sm` stays at 12 px. Nothing in the app renders below 12 px (the audit found 230 text nodes below it on `/accuracy`).

The document text keeps `document/body` at 17 / 30.

### 5.4 Colour changes (approved at FE-2, decision D6)

Every change keeps the hue, so the identity stays. Ratios are WCAG relative luminance against the surfaces named. Light surfaces are base `#F6F3EC`, sheet `#FFFDF8`, sunken `#EFEBE2`. Dark surfaces are base `#131619`, sheet `#1A1E22`, sunken `#0F1214`.

| Token | Mode | Old | New | Ratios, new (old) | Reason |
|---|---|---|---|---|---|
| `ink/tertiary` | Light | `#7A7F85` | `#646970` | 4.99 base, 5.44 sheet, 4.65 sunken (3.64, 3.97, 3.39) | Captions and placeholders fail AA |
| `ink/tertiary` | Dark | `#858079` | `#8B867F` | 5.03 base, 4.64 sheet, 5.21 sunken (4.28 on sheet) | Fails AA on the sheet |
| `status/absent` text, `polarity/neutral` text, `polarity/unresolved` text | Light | `#6E7278` | `#666A70` | 4.65 on `#EFEDE8`, 5.35 on sheet (4.13, 4.76) | One shared value fails on the tinted chip. The three stay equal |
| `control-border` (new) | Light | `rule/strong` `#C9C1B2` | `#85817A` | 3.50 base, 3.81 sheet, 3.26 sunken (1.50 to 1.76) | Input, radio, checkbox and switch outlines need 3:1 |
| `control-border` (new) | Dark | `rule/strong` `#3E444B` | `#6A6E72` | 3.53 base, 3.26 sheet, 3.66 sunken (1.70 to 1.91) | Same |
| `status/unvalidated` border | Light | `#9AA0A6` | `#8A9096` | 3.17 on sheet (2.60) | The dashed border is the only edge of a transparent chip |
| `status/unvalidated` border | Dark | `#5A6068` | `#7F858C` | 4.50 on sheet (2.64) | Same |

`rule/strong` stays for dividers. `control-border` is used only on interactive controls. The focus ring (`#2F7FA0` light, 3.78 to 4.43 on the three surfaces, and `#8FCBD8` dark, 9.3 to 10.5) already passes and stays. The review mark line `#B07A18` on the sheet is 3.66 and passes as a non-text mark.

`DesignSystem.md` 3.1 and 3.2 now hold the new values, and `src/tokens.test.ts` reads `index.css` and asserts every pair in this table, so a later edit cannot drop below the bar unnoticed.

### 5.5 Spacing, rhythm and widths

- The 4 px base stays. `DesignSystem.md` extends its list with `space/24` (96) and `space/32` (128). No CSS token is needed, because Tailwind derives `py-24` and `py-32` from `--spacing`.
- Inside a section: heading to body 16 px, paragraph gap 16 px, gap between components 32 px, gap between a component and its marginal note 24 px.
- **A heading is always closer to what it introduces than to what precedes it.** In long-form pages an `h2` has 48 px above and 16 px below, an `h3` 32 px above and 12 px below. FE-2 reads the computed values to check.
- Width tokens (CSS custom properties): `--w-page` 1200 px, `--w-main` 42 rem, `--w-margin` 9 rem. The 640 px form column is an inline `max-w-[640px]`.
- The Reader's widths are in 6.3.

### 5.6 Hit area and focus

- **Hit area is 44 by 44 px minimum on every interactive element,** reached with padding or an `::after` that extends the target, with the visual size unchanged. `DesignSystem.md` button sizes S 32, M 40 and L 48 become visual sizes, and the hit area rule sits above them. Adjacent targets keep at least 8 px between hit areas.
- Fixed targets: the logo link (padding), theme and menu buttons, nav links (block padding), the Switch (the whole label row is the target), Dismiss, Choose file, the sort buttons.
- **One global focus rule** in `index.css`: `:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px }`. Components stop carrying their own. The skip link uses it too. Sticky bars set `scroll-padding-top` so a focused element is never hidden under them (WCAG 2.4.11).

### 5.7 Elevation

Unchanged. The panel and drawer shadow is `elevation/2`. The margin rule and the page edge do the rest.

### 5.8 Browser surfaces and links

Defaults that belong to no design system are themed from the palette (amendment F):

- `::selection` takes an ink tint (`rgba(15, 76, 92, 0.22)` light, `rgba(111, 184, 200, 0.32)` dark) and leaves the text colour alone. `caret-color` and `accent-color` are `anchor/600`.
- **Scrollbars stay visible.** The baseline hides the thumb until hover, which removes the cue that a pane scrolls, and the Reader has three panes. The rule becomes `scrollbar-width: thin` with `scrollbar-color: var(--control-border) transparent`, plus `scrollbar-gutter: stable` on the Reader's panes so the layout does not shift.
- Numbers that align in columns or change in place use `font-variant-numeric: tabular-nums`: offsets, counts, step numbers and the metric cells.
- Links inside prose are underlined 1 px with `text-underline-offset: 0.2em`. **A visited prose link turns `ink/tertiary`.** The baseline's "visited" variant is `#0A3945` against `#0F4C5C`, which no reader can tell apart. Navigation links and buttons do not take a visited colour.

---

## 6. Page compositions

The words are in section 8. Section numbers below use the brief's list, and the § marks on the page count only the sections that render.

### 6.1 Landing (`/`)

Grid: `MarginGrid` on every section. The margin column holds the § mark and, where useful, one marginal note. Sections are separated by space and a 1 px `rule/default`, with no background bands.

**Hero (no mark)**

- Main column: `h1`, a three-sentence subheading, the primary button **Review a contract** and the secondary **Try the sample contract**, then the fixed privacy line in quiet text under the buttons. The privacy line sits at the point of decision.
- Below that, still in the main column, **the live demo**: a short excerpt of the sample contract on a sheet, with a caption "Sample contract, fictional parties. Reading as the Provider."
- Aside column from 1280 px (below the sheet under that, see the layout table below): the clause panel, which opens as a marginal note beside the sheet with its top aligned to the sheet's top.
- The demo uses the real components: `SpanHighlight`, `MarginRuler`, `StatusChip`, `PolarityBadge`, `ConfidenceBand`, `StatuteTag`, `OffsetTag` and a compact `ClauseDetailPanel`.
- **Above the fold (amendment A).** The hierarchy is brand, heading, subheading, buttons, privacy line, then the demo. At 375 by 667 the header, heading, subheading, both buttons and the privacy line show without scrolling, and the primary button is fully visible. At 1280 by 720 the first screen also shows the top of the excerpt. Both are checked at FE-3.
- **Sequence, once:** the excerpt sits static for 600 ms, the highlight inks in (400 ms, left to right), the ruler tick appears (200 ms), and the panel fades in with a 12 px slide (320 ms). The whole run is under 2 s. Hovering or focusing inside the demo pauses it. Under reduced motion it renders in its final state with no movement.
- **Base styles are the final state (amendment E).** The CSS keyframes carry the hidden start and use `animation-fill-mode: backwards`, so if animation is off, unsupported or interrupted, the whole demo is visible. Content never waits behind a timer.
- **Controls:** "Next example", with the position ("Example 2 of 3"). After the third example it wraps to the first. A visually hidden status line announces "Example 2 of 3: Notice Period to Terminate Renewal, Found".
- **Three examples,** each captioned with what it shows: Non-Compete ("Found, a burden on the Provider", with the Section 27 note), Notice Period to Terminate Renewal ("Found, applies to both sides"), and Competitive Restriction Exception ("Needs a lawyer"). The third shows the abstention, which is the honest part of the pitch. This is a short walk through three different outcomes and not a carousel of the same one.
- **Semantics (amendment J).** The excerpt is a `figure` with a `figcaption`. The finding is a `<mark>` preceded by visually hidden text ("Finding, Found: Non-Compete"). The panel is a `role="group"` named "Finding detail".
- **The panel shows only what is verified:** the quoted contract text with its offsets, the category, the status, the direction, the confidence band as a word, and the statute note. It shows no confidence decimal, because mock values would be invented precision, and no case law, because the mock judgments are placeholders (C7).
- **Implementation:** a CSS animation sequence with `animation-delay` steps and `animation-play-state: paused` on `:hover` and `:focus-within`. "Next example" changes a React `key`, which remounts the demo and replays it. No timer and no state machine.
- **Data:** a typed fixture in `src/pages/landing/heroExamples.ts` (open decision D1). Each entry holds the excerpt, the code point offsets of the finding and its quote. A test slices through `lib/offsets.ts` and checks the quote and that the excerpt appears verbatim in the sample contract.

**§ 1 The problem (brief section 2)**

- One idea: contracts are long, and the clause types worth asking about are a known list.
- Main column: the heading, one paragraph that states the CUAD facts, and a link to the source. The margin note names the source and licence.
- No statistic about missed clauses appears (3.4). If Aryan supplies a sourced one, it goes here.

**§ 2 How it works (brief section 3)**

- Three steps, each paired with a real component fragment in the aside: the `UploadDropzone` (idle), the `RoleSelector` with one card selected, a `SpanHighlight` with its `StatusChip` and `OffsetTag`.
- Each fragment reveals on scroll (section 7.3). Steps are numbered in the text, not with a decorative row.
- **Mid-page call to action** closes the section: "Review a contract".

**§ 3 Evidence you can check (brief section 4)**

- One `JudgmentCard` with a verbatim passage, its court, year, citation and authority status, and a link to the source. Quoted, never paraphrased. It reveals on scroll.
- **Gate (open decision D7):** the card needs one real passage from the same corpus the product serves. Until Aryan gets a corpus id from Tanishq and the quote is verified, **the section does not render** and the § marks renumber. It is not stubbed with a placeholder.

**§ 4 Built to tell you when to call a lawyer (brief section 5)**

- A short paragraph, then a two-column list in the main column and aside: "What it does" and "What it does not do", set as plain lists with a hairline between, not as two cards.
- Under them, the abstention shown with the real component: a `StatusChip` "Needs a lawyer" and one sentence.

**§ 5 What it checks (brief section 6)**

- The 46 categories in seven groups, browsable. Each group is a native `<details>` element with the category names inside. The first group is open. Labels come from `catalogue.ts`. The landing page shows names only, because support status counts are mock values (C6).
- A sentence states the limit: a category not on the list is not checked.

**§ 6 Privacy and accuracy (brief section 7)**

- The privacy statement and the link to `/accuracy`. One job: what happens to the contract and how far to trust the figures.
- The accuracy sentence is honest about the current state: the page shows labelled example numbers until the evaluation completes. It changes when real numbers exist.

**§ 7 Questions (amendment E)**

- A short list of native `<details>` that answers the objections (section 8.4), one job per section. It is the only place on the landing page that carries the fixed legal-scope line, because the footer carries it on every route and a separate banner here would repeat it a third time.
- This section is new. The brief folds the objections into section 7, which would give that section three jobs (privacy, accuracy, objections).

**Final call to action (brief section 8, no mark)**

- A closing line, the primary button and the secondary link.

**Layout by viewport (amendment I)**

| Viewport | Layout |
|---|---|
| 375 to 767 | One column. Margin content and the § mark sit inline above each heading. The two buttons stack at full width, 44 px high. The panel sits below the sheet as a marginal note with a 1 px left hairline (not the 4 px rule) |
| 768 to 1023 | One column at the 42 rem measure. The buttons sit side by side. The panel is below the sheet and spans its full width (17.4, AB) |
| 1024 to 1279 | Two columns, margin and main. § marks sit in the margin column. The panel is below the sheet in the main column and spans the sheet's full width (17.4, AB) |
| 1280 and wider | Three columns. The panel opens in the aside beside the sheet |

### 6.2 Start flow (`/start`)

Three steps, one decision each, in a 640 px column. A summary rail sits in the aside from 1280 px (file, role, party, scope). Below 1280 the summary is one line above the buttons on steps 1 and 2 and a full list in step 3 (17.4, AE).

| Step | Heading | Content | Next is enabled when |
|---|---|---|---|
| 1 | Upload the contract | The dropzone, or the sample contract. The fixed privacy line sits directly under it. The four upload errors show inline | The file is uploaded. Parsing may still run |
| 2 | Say which side you are | Role as a radio group (one tab stop, arrow keys). Then the party list once parsing is done, or a "Reading your document" line while it runs | A role is chosen, parsing is done, and a party or "None of these" is chosen |
| 3 | Confirm the scope | The Indian law switch with its description, the fixed review-scope notice, the fixed legal-scope notice, a one-screen summary | Always. The button reads **Start review** |

The page shows "Step n of 3", Back and Next. The step number lives in `?step=`.

**Flow state is a pure reducer** in `src/lib/startFlow.ts`, tested first (section 13). State: `seq`, `upload` (idle, validating, uploaded, error with a code), `parse` (idle, running, done, failed), `role` (null until chosen), `party`, `partyNone` and `india`. The step is not in the state. The address owns it and `clampStep` says which step the state allows (17.4, AD). Actions: `upload-started`, `upload-done`, `upload-failed`, `parse-done`, `parse-failed`, `set-role`, `set-party`, `set-party-none` and `set-india`. Every action that answers a request carries the `seq` of its upload, so a late answer for a replaced file changes nothing. Rules:

- `maxReachableStep` is 1 until a file is uploaded, 2 until step 2 is complete, then 3. It is read off `nextBlocker`, so a step is reachable exactly when nothing blocks Next on the one before it. `clampStep` never returns a step past it. A `?step=3` link that is not reachable is corrected to the highest reachable step with a replace, so Back does not trap the user. `nextBlocker` names what stops Next on a step, and the page turns it into the hint under the buttons.
- Back keeps every input. Going back to step 1 and replacing the file resets the party and `partyNone` and keeps the role and the scope.
- **No party is preselected, and no role either.** The party that fits the role best is listed first and marked "Suggested". The user must choose one. A wrong binding silently flips Burden and Benefit on every finding, so it needs an explicit act. A contract that names no party has only "None of these" to choose, so `parse-done` with no parties records that choice itself.
- The upload, the polling and the calls to `client` stay in a small hook, `pages/start/useStartFlow.ts`. The reducer holds no side effect.

Errors use the four exact messages from `UploadDropzone`:

- "This file type is not supported. Upload a PDF or DOCX."
- "This file is larger than 10 MB."
- "This PDF looks scanned. ClauseAnchor needs selectable text. Try the original digital file."
- "This file is password protected. Remove the password and upload again."

The sample contract is one option on step 1. "Try the sample contract" on the landing page links to `/start?sample=secondment`. The flow reads that parameter once, starts the sample upload, and removes the parameter with a replace so a reload does not run it again (amendment B). Whether the real API accepts a sample id while uploads are on is open (D8). The mock accepts it.

### 6.3 Reader (`/review/:documentId`)

Same route, same data logic, same components, recomposed.

**Pane widths**

| Viewport | Layout | Sheet | Text column | Capacity by width (estimate) |
|---|---|---|---|---|
| 1440 and wider | Sidebar 264, sheet, panel 384 | 708 (the space left, capped at 740) | 580 | about 74 |
| 1280 to 1439 | Rail 64, sheet, panel 360 | 740 | 612 | about 78 |
| 1024 to 1279 | Sheet, drawers for categories and the panel | 740 | 612 | about 78 |
| 768 to 1023 | Sheet, drawers | 684 | 556 | about 71 |
| Below 768 | Sheet, categories drawer, the panel as a bottom sheet | the viewport minus 32 | about 300 | 36 to 45 |

The sheet's side padding stays 64 px. The rail holds one icon button with a 12 px label, Categories. It opens the full sidebar as an overlay drawer, where the manual-review list is one tap away. **Rejected alternatives for 1280:** keeping the 280 px sidebar and shrinking the panel gives about 56 characters, still short, and moving the panel into a drawer removes the evidence from beside the text, which is the product's core. The figures are estimates. FE-5 measures the full-line average (2.4) at 1024, 1280, 1440 and 1920 and adjusts the sheet padding to land between 68 and 80.

**Sidebar**

- The scope card keeps the full fixed notice, because the notice must stay visible. The Validated, Pooled and Not validated counts leave it (they are mock numbers and belong on `/accuracy`). The row "46 categories reviewed, View list" stays.
- Category rows wrap their names and never truncate. The status icon and its text move to a second line. The count badge stays on the right.
- The selected row takes a tint and the bracket mark ⟦, with no left stripe (3.3).

**Margin ruler:** FE-5 first checks whether the short tick is a bug or by design. The target is the ledger strip: full height of the sheet, a tick at each finding at its position in the text, a click jumps to it, and the strip stays in view while scrolling.

**Toolbar:** below 768, Download report stays on one line and the other actions move into the existing "..." menu. The filename is the visible heading.

**Analysing, as a designed moment.** The parsed text is already readable, so the sheet shows it at once. A slim band above the sheet shows `StageProgress` with the real counts ("Finding clauses: 18 of 46 categories"), never a percentage. As each category resolves, its row enters the sidebar (200 ms fade, 50 ms stagger) and its mark inks in on the sheet. The panel says "Nothing selected" and, once one finding exists, offers **Read the first finding** instead of selecting it for the user. Cancel stays.

**Selection.** Selecting a finding scrolls it to the middle of the sheet (smooth, or instant under reduced motion) and cross-fades the panel through the View Transitions API with an instant fallback. J and K move between findings and Escape closes. The key hint line moves below the sheet from 1024 px and stays in the empty panel.

**When nothing is found (amendment C).** If every category resolves with no finding, a quiet band above the sheet reads "46 categories reviewed. No clause found at the validated threshold." That is the fixed phrase, and the band never says the contract is fine. The empty panel then offers "Open the manual review list" in place of "Read the first finding".

**Reload guard (amendment D).** While a review exists, the page registers a `beforeunload` handler, because a reload ends the session and the text is gone. The browser shows its own generic prompt. The app writes no message of its own.

**Large documents (amendment K).** The parser accepts up to 500,000 code points, and the mock sample is about 1,300 words. FE-5 renders a generated 500,000 code point document and checks that no main-thread task blocks for more than 200 ms while scrolling and selecting a finding. If one does, FE-5 asks for approval before adding any windowing. This is an estimate until it is measured.

**Parser warnings.** The parser can return `PARTIALLY_SCANNED_PDF`, `UNSUPPORTED_DOCX_FEATURE` and `EMBEDDED_OBJECT`, with `coverage.partial` set. The mock's `warnings` array is the only slot today. FE-5 reserves a notice above the sheet for those warnings, and the final wording waits for API.md (2-E). A partial parse must never read as "nothing found".

### 6.4 How it works (`/how-it-works`)

- `MarginGrid`. The "On this page" list moves into the margin column and sticks from 1024 px, with the § number beside each entry. The seven sections keep their text and order. The § mark beside each heading is `aria-hidden`.
- Component fragments sit beside the text in the aside where they explain it: the status chips beside "Saying how sure it is", the polarity labels beside "Reading from your side", a statute tag beside "Indian law review". They reveal on scroll.
- Corrections to the text, made in FE-6 with the copy pass: the first section says scanned files are refused, and the parser now refuses only a file that is scanned throughout, while a file with some scanned pages is read and the unreadable pages are flagged. The Credits link target works (A10).

### 6.5 Accuracy (`/accuracy`)

- The heading, the review-scope notice and, directly under them, a prominent **example numbers** banner while `is_example` is true. The inline chip is replaced by a banner with the same dashed style.
- From 768 px the table spans the main and aside columns, with a sticky header. Below 768 each category becomes a stacked block: the name, the support, then Precision, Recall, Silent miss and Abstention as a two-by-two grid of `MetricCell`. Nothing clips and nothing is below 12 px.
- The glossary moves beside the table in the aside from 1024 px, as marginal notes.
- Silent miss keeps its emphasis, because it is the number that matters: misses with no warning.

### 6.6 Expired and NotFound

- Both are a single centred column of 560 px with an `h1`. Expired keeps its two variants ("Your contract has been deleted." and "This session has ended"). NotFound reads "We could not find that page." with the line "The link may be wrong or out of date." and two links: Review a contract, How it works.
- Neither uses a warning colour. NotFound is not an error in the product, so it takes no brick tint.

### 6.7 Development-only controls

- `/gallery` is registered only when `import.meta.env.DEV` is true and is loaded with a dynamic import, so the production build holds no Gallery code.
- The mock settings panel leaves the Home page and becomes a floating **Preview controls** drawer, rendered by `Root` only in development, also lazy-imported.
- The drawer holds six switches: sample mode, partial run, failed analysis, fail parse, short session and fail next request. The retry that follows a forced failure turns that switch off (17.4, AN).
- **Build check at FE-2 and FE-R:** `grep -rl "Preview controls" frontend/dist` and a listing of `frontend/dist/assets` for a Gallery chunk both print nothing.

### 6.8 Loading and code splitting

Routes other than the landing page load with the router's own `lazy`, so the landing page does not pay for the Reader, the largest module. This is a built-in feature and adds no dependency. Fonts are covered in section 11.

### 6.9 Interaction states for new and changed surfaces (amendment C)

The existing components keep the states `DesignSystem.md` and the gallery already define. This table covers what this plan adds or changes. Each cell says what the user sees.

| Surface | Loading | Empty | Error | Partial |
|---|---|---|---|---|
| Route chunk | The previous page stays until the next one is ready. No spinner and no fake bar | n/a | A root error page: "This page could not load." with a Reload button. The router's default developer error screen never shows in production | n/a |
| Page without JavaScript | n/a | `<noscript>` line in `index.html`: "ClauseAnchor needs JavaScript to read your contract." | n/a | n/a |
| Hero demo | n/a, the data is local | n/a | A fixture that fails its test fails the build, so the page never shows a broken example | Interrupted animation shows the final state |
| Start step 1 | The dropzone's validating state | The idle dropzone with the privacy line | The four upload messages inline, and the network `ErrorCard` with Retry | File uploaded, parsing still running: Next is available |
| Start step 2 | A "Reading your document" line and the party skeleton | No party found: the line "We will mark party-specific clauses as Party unclear." and no party to choose (17.4, AN) | Parse failed: the card "We could not read your document" with "Try again, or go back and choose a different file." and a Try again button. Next stays disabled and the role is kept (17.4, AN) | Role chosen, parsing running: Next waits with "Still reading your document" |
| Start step 3 | Start review in its loading state | n/a | The network `ErrorCard` with Retry. Every input is kept | n/a |
| Reader, analysing | The stage band with real counts | Zero findings: the fixed-phrase band in 6.3 | Failed analysis: `ErrorCard` with Retry. Cancelled: a line saying the review was cancelled and Start again | Some categories Unavailable: the existing partial notice. A partial parse shows the parser-warning notice. Neither reads as "not found" |
| Clause panel | n/a | "Nothing selected" with one action | A retrieval failure: "Case law was not retrieved for this clause." | One passage reviewed and one overruled: the status shows on each passage |
| Accuracy | Skeleton rows | "No evaluation results yet." | `ErrorCard` with Retry | A category with no measurement shows "Not measured" and never a zero |
| Long filename | n/a | n/a | n/a | In the summary rail the name wraps anywhere. In the Reader toolbar it truncates at the end and keeps the extension |

---

## 7. Motion

### 7.1 Tokens (added to `index.css` in FE-2)

| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | Enter |
| `--ease-exit` | `cubic-bezier(0.4, 0, 0.2, 1)` | Exit |
| `--dur-press` | 120 ms | Hover, press |
| `--dur-state` | 200 ms | A state change, a route cross-fade |
| `--dur-panel` | 320 ms | Panels, drawers, scroll reveals |
| `--dur-ink` | 400 ms | The ink-in sweep |
| `--stagger` | 50 ms | Between siblings |

`DesignSystem.md` 3.5 gives 200 ms to panels and drawers. It changes to 320 ms in FE-2, as the brief sets.

### 7.2 Rules

- Animate only `opacity`, `transform` and, for the ink-in, `background-size`. Never `height`, `width`, `top` or `left`. The mobile drawer moves to a `transform` slide (B9).
- No single step of a sequence runs longer than 560 ms.
- Nothing loops except the skeleton shimmer, which is an opacity fade and is static under reduced motion.
- No spring overshoot. No motion library. CSS and native APIs only.

### 7.3 The patterns

| Pattern | Trigger | Motion | Reduced motion |
|---|---|---|---|
| **Ink-in** | A finding first renders, in the hero and in the Reader | A tint and underline sweep from left to right over `--dur-ink`, built from `background-size` on the mark | The mark shows at once |
| **Scroll reveal** | A How it works fragment or the judgment card enters the viewport | Opacity 0 to 1 and a rise of at most 12 px over `--dur-panel`, once per element | The element is never hidden |
| **Panel** | Selecting a finding | Cross-fade through the View Transitions API, `--dur-state` | Instant |
| **Drawer and bottom sheet** | Open or close | `transform` over `--dur-panel` | Opacity only |
| **Route change** | Navigating | A view transition cross-fade, `--dur-state` | Instant |
| **Rows entering** | A category resolves | Opacity over `--dur-state`, `--stagger` between rows, capped at six rows | Instant |
| **Hover and press** | Pointer | Colour or opacity over `--dur-press` | Same, it is not movement |
| **Hero** | Page load, once | The sequence in 6.1 | Final state, no movement |

**The reveal hook.** `src/lib/reveal.ts` holds the logic as a pure function, `revealOnce(element, observerFactory, reduced)`, and `useReveal` is a six-line wrapper. The hook marks the element pending only after the observer exists, in a layout effect before the first paint, so content is visible without JavaScript and never flashes. It marks the element shown on the first intersection, disconnects, and does nothing under reduced motion. The scroll reveal is used on the How it works fragments and the judgment card, and nowhere else.

**Route transitions.** React Router supports `viewTransition` on `Link`, `NavLink` and `navigate`. The general docs were checked. The behaviour in the pinned version (8.4.0) is not verified yet, so FE-2 checks it against that version's docs before use. The fallback is an instant change.

### 7.4 One global reduced-motion rule

`index.css` gets a single `@media (prefers-reduced-motion: reduce)` block that sets `animation-duration` and `transition-duration` to a near-zero value, forces `scroll-behavior: auto` and disables the view-transition animation. The per-component guards stay for the Reader, and the new motion needs no further guard.

---

## 8. Copy plan

Prose goes through copywriting, then copy-editing, then stop-slop. Everything below is a draft for review. The fixed phrases from `DesignSystem.md` 4 are used verbatim and in sentence case. The banned list in 3.4 applies.

### 8.1 Verified facts the copy may use

| Fact | Source |
|---|---|
| CUAD labels 41 kinds of clause in 510 commercial contracts, with more than 13,000 annotations | The Atticus Project, CUAD v1, CC BY 4.0 (atticusprojectai.org/cuad), and Hendrycks, Burns, Chen and Ball, NeurIPS 2021, arXiv 2103.06268 |
| The catalogue has 46 categories: the 41 from CUAD and 5 added for India | Repo docs, `Phases.md` review scope |
| Uploads are PDF or DOCX, up to 10 MB and 100 pages | `UploadDropzone` |
| A contract is processed in memory and deleted within 60 minutes | The fixed privacy phrase |

Not verified and therefore not used: any figure for missed clauses, time saved, cost of review, number of users, or accuracy.

### 8.2 Landing: headlines and calls to action

**Hero heading, three options for Aryan to pick from:**

- **A (recommended):** "Know which clauses to ask a lawyer about." It states the outcome and turns the "just go to a lawyer" objection into the pitch.
- B: "Read your contract with the evidence beside every finding." It leads with proof.
- C: "Before you sign, see which clauses deserve a second look." It leads with the moment.

**Subheading:** "ClauseAnchor checks your contract against 46 listed clause categories and marks each match in the margin. Every finding quotes your text, and some add a passage from a published Indian judgment. Where it is unsure, it says Needs a lawyer." The "some" is deliberate: not every category has a judgment.

**Buttons:** "Review a contract" (primary), "Try the sample contract" (secondary). **Under the buttons:** the fixed line "Your contract is processed in memory and deleted within 60 minutes."

**Demo:** caption "Sample contract, fictional parties. Reading as the Provider." Control "Next example". Status "Example 2 of 3".

| Section | Heading | Body, in one line |
|---|---|---|
| § 1 | Contracts run long. The clause types worth asking about are a known list. | "The Contract Understanding Atticus Dataset labels 41 kinds of clause across 510 commercial contracts, with more than 13,000 annotations. ClauseAnchor starts from those 41 and adds five for Indian agreements." |
| § 2 | Three steps. Every finding can be checked. | 1 "Upload a PDF or DOCX with selectable text, up to 10 MB and 100 pages." 2 "Pick your role and the party you are. That decides whether a clause reads as a burden or a benefit for you." 3 "Every finding points to exact text. Select one to see the quoted wording, the confidence band and any case law." |
| § 3 | Evidence you can check. | "Case law appears as a quoted passage with its court, year and citation, so you can look it up yourself. Nothing is paraphrased." |
| § 4 | Built to tell you when to call a lawyer. | "When the evidence for a category is close, ClauseAnchor does not guess. It marks the category Needs a lawyer and shows you the text it found. Take the marked clauses and their quoted evidence to a lawyer, and start the conversation at the clause." |
| § 5 | 46 clause categories, in seven groups. | "From basics such as governing law to India-specific clauses such as stamping and registration. A category that is not on the list is not checked." |
| § 6 | Your contract is deleted within 60 minutes. | "Your contract is processed in memory and deleted within 60 minutes. Reloading the page ends your session, and nothing is written to your browser's storage. The Accuracy page lists the measured figures for each category once the evaluation is complete. Until then it shows labelled example numbers." |
| § 7 | Questions before you upload. | The five answers in 8.4. |
| Final | Start with the contract in front of you. | Buttons as above. |

The mid-page button after § 2 reads "Review a contract".

### 8.3 Other pages

**Start flow.** Heading "Review a contract". Steps: "Upload the contract", "Say which side you are", "Confirm the scope". Buttons: "Back", "Next", "Start review". Step line: "Step 2 of 3". Waiting line: "Reading your document." Party label: "Suggested". Blocked Next: "Still reading your document." The Indian law switch keeps the text it has today: "Review under Indian law" and its description. The baseline's line "The review takes about a minute on real documents." is dropped until 4-C measures a real run (C8). The hints, the summary labels and the parse-failure card are new strings, listed in 17.4.

**NotFound.** "We could not find that page." "The link may be wrong or out of date." Links "Review a contract" and "How it works".

**Document titles.** In 4.1. **Meta description** (149 characters, changed at the end of FE-4, 17.4 AL): "Know which clauses to ask a lawyer about. Every finding quotes your contract or a published judgment, and your contract is deleted within 60 minutes."

### 8.4 The objections list (native `<details>`, § 7)

| Question | Answer |
|---|---|
| Is this legal advice? | "No. ClauseAnchor points to text in your contract and in published judgments. It does not tell you what the law requires." |
| What happens to my file? | "Your contract is processed in memory and deleted within 60 minutes. Choose Delete document in the reader to remove it sooner." |
| What if it misses something? | "It can. This review checks the listed clause categories. Other provisions and interactions between clauses may need manual review. Unhighlighted text is not a safety assessment." |
| Which files work? | "PDF or DOCX with selectable text, up to 10 MB and 100 pages. A file that is scanned throughout, or password protected, is refused." |
| Which law does it cover? | "Indian law review adds notes that cite Indian statutes and passages from Indian judgments. Turn it off for a contract under another country's law." |

No answer claims the product is free, instant or accurate.

---

## 9. Trust and conversion map

| Element | Principle served | Objection it answers | Proof it uses |
|---|---|---|---|
| Hero demo | 1 Show, 3 Specificity | "Is this a real tool or a promise?" | The real components on a sample, with offsets and a band |
| Privacy line under the hero buttons | 4 Reassure at the point of action | "Where does my contract go?" | The fixed 60-minute phrase |
| § 1 The problem | 3 Specificity | "Why do I need this?" | The CUAD facts and a link to the source |
| § 2 How it works | 6 Visible progress | "How much work is this?" | Three steps, real fragments |
| § 3 Evidence | 1 Show, 3 Specificity | "Is the case law real?" | One verified verbatim passage, or the section is omitted |
| § 4 Lawyer | 2 Honesty | "Why not just ask a lawyer?" | The abstention shown, and the pitch of arriving prepared |
| § 5 Categories | 3 Specificity | "Does it check what I care about?" | The 46 names, and the limit stated |
| § 6 Privacy and accuracy | 2 Honesty, 4 Reassure | "What if it is wrong?" | The objections list, labelled example numbers |
| Header button, hero, mid-page, final | 5 One primary action | None | The same words every time |
| "Try the sample contract" | 5, low commitment | "I do not want to upload yet" | A fictional contract, labelled |
| `/start` steps | 5, 6, 7 | "Is this a long form?" | One decision per screen, Back keeps inputs |

**Friction budget.** From the landing page to a running review: Review a contract, upload, role, party, Start review. The reducer lets parsing finish while the user chooses a role, so the wait is hidden. There is no sign-up and no email field.

**Principle 7, no dark patterns.** No countdown, no urgency copy, no hidden cost, and the decline option "None of these" for the party is as prominent as a party.

### 9.1 The journey, scene by scene (amendment D)

| Scene | The visitor does | The visitor feels | What the plan does |
|---|---|---|---|
| 1 | Lands on `/` | Wary. The contract is private and the stakes are real | A specific heading, the product working beside it, the privacy line under the button |
| 2 | Watches the demo | Curious, still checking whether it is real | A finding inks in with exact text and offsets. Nothing is proven by an adjective |
| 3 | Chooses the sample or uploads | Reluctant to hand over a file | The sample is one click and labelled fictional. The upload sits beside the 60-minute line |
| 4 | Picks a role and a party | Afraid of choosing wrong | Plain role words. "None of these" is as prominent as a party. Nothing preselected, because the choice flips every label |
| 5 | Waits for the review | Anxious | The text is readable at once. Real counts replace a bar. Cancel is always there |
| 6 | Reads the first finding | Oriented, with some relief | "Read the first finding" instead of an empty panel |
| 7 | Meets "Needs a lawyer" | Tests whether the tool is honest | It abstains and shows the text it found. This scene builds the trust |
| 8 | Opens a judgment | Wants to check it | A verbatim passage with court, year and citation |
| 9 | Leaves | Decides what to do next | Download report and Delete document sit in the toolbar. The session notice warns before the end. A reload shows the browser's prompt |

Time horizons. In the first 5 seconds the heading and the demo say what this is. In 5 minutes the visitor has read one finding and one passage. After 5 years the lasting impression is whether the tool was honest about its limits.

The landing page's lawyer section says to bring the marked clauses to a lawyer. It does not mention the downloadable report, because 3-B has not confirmed that the report lists the findings with their quotes (decision D12).

---

## 10. Skills and commands

The installed set was listed at the start of FE-1 (the user skills folder and the commands folder; the commands folder is empty). The plugins present are frontend-design, ponytail, superpowers, code-review, context7, skill-creator and coderabbit. The first column is the category from the brief.

| Category | Skill or command | Runs in | FE-1 status |
|---|---|---|---|
| UI and visual design | `ui-ux-pro-max` | FE-1, FE-3 | Ran (search only, nothing written). At FE-3 the rule list only, because Python is not installed and the search script cannot run |
| | `frontend-design` | FE-1, FE-3, FE-5 | Ran |
| | `impeccable` | FE-1, FE-R | Ran (detector only, read-only) |
| | `design-taste-frontend` | FE-3 | Ran at FE-3 as a review lens. Its bans on section-number marks, a serif display and a line under the buttons conflict with the approved direction, which stands (17.3) |
| | `tailwindcss` | FE-2 | Available, not run yet |
| | `emil-design-eng` | FE-3, FE-5 | Ran at FE-3. The hero is one explanatory run, not repeated interface motion, so its 300 ms limit does not apply |
| Motion | `animate` | FE-2, FE-3 | Ran at FE-2 and FE-3 |
| | `find-animation-opportunities` | FE-5 | Available, not run yet |
| | `improve-animations`, `optimize-web-animations` | FE-R | Available, not run yet |
| | `animation-vocabulary` | As needed | Reference only |
| | `gsap`, `gsap-scrolltrigger-storytelling`, `cinematic-gsap-lenis-motion-system`, `animation-on-scroll`, `threejs` | Not used | Each adds a dependency or a banned pattern (scroll-jacking, decorative parallax) |
| Design review | `gstack-design-consultation` | FE-1 | Ran as method only: its preamble and its design-file output were skipped because they write outside the allowed folders |
| | `gstack-plan-design-review` | FE-1 | Ran on this spec as method only, same adaptation (section 17.1) |
| | `gstack-design-review`, `gstack-qa`, `gstack-qa-only` | FE-R | Not run yet |
| | `gstack-benchmark` | FE-R | Not run yet |
| | `gstack-design-shotgun`, `gstack-design-html` | Not used | They generate variants and files outside the allowed folders |
| Marketing, conversion, psychology | `copywriting` | FE-1, FE-3, FE-4, FE-6 | Ran at FE-1 and FE-3, and at the end of FE-4 over the FE-4 strings (17.4, AO) |
| | `copy-editing`, `stop-slop` | Every part with prose | `stop-slop` ran on this file and on the FE-4 strings, and again on the FE-4 copy edits. `copy-editing` ran at FE-3 and at the end of FE-4 |
| | `cro` | FE-1, FE-3 | Ran |
| | `signup` | FE-1, FE-4 | Ran at FE-1 (applied to the start flow, which has no account). Not run as a pass at FE-4 |
| | `onboarding` | FE-1, FE-5 | Ran (applied to the first run of the reader) |
| | `marketing-psychology` | FE-1 | Ran |
| | `site-architecture` | FE-1 | Ran |
| | `seo-audit` | FE-R | Titles, descriptions and headings only |
| | `analytics`, `ab-testing` | Not used | The product collects nothing by design |
| Prose | `stop-slop` on every user-facing string and doc | Every part | See above |
| Code quality | `ponytail` (always on) and `/ponytail:ponytail-review` | Every part | Ran at the end of FE-1 to FE-4 |
| | `superpowers:test-driven-development` | FE-2 (reveal, tokens), FE-3 (fixture), FE-4 (reducer) | Ran at FE-2 and FE-3 (the fixture test, seen failing first), and at FE-4 (the reducer tests, red while the module did not exist, then green, with six mutation checks that each fail at least one test) |
| | `superpowers:verification-before-completion` | Every part | Applied |
| | `superpowers:systematic-debugging` | When a test fails | Not needed yet |
| Accessibility and performance | None installed that is dedicated to either | | `impeccable`, `gstack-qa`, `gstack-qa-only` and `gstack-benchmark` are the nearest. Lighthouse and axe-core run through `npx` in a scratch folder at FE-R, and need approval (section 11) |
| Phase end | `/coderabbit:code-review` over the FE range, `/gstack-review`, `/gstack-cso`, one independent second review | FE-R | Not run yet |
| | `graphify` | FE-R | Regenerate the frontend tree for Architecture.md |

Skills and plugins for other tools, for mobile apps, for marketing channels (ads, email, SMS, social) and for video have no use in this track and are not listed.

---

## 11. Dependency requests

No runtime dependency is requested. No motion library and no icon library either.

### 11.1 Fonts: self-host (decision D3, needs approval and a download)

The three families load from Google today (A1). The fix is to serve them from our own origin. Latin subset, woff2, size in bytes:

| File | Bytes |
|---|---|
| Source Serif 4, variable weight, normal | 50,824 |
| Source Serif 4, variable weight, italic | 51,516 |
| IBM Plex Sans 400, 500, 600 | 22,588 / 24,184 / 24,252 |
| IBM Plex Mono 400, 500 | 14,708 / 14,888 |

The used set totals about 203 KB, none of it in the JavaScript bundle. The licence is SIL OFL 1.1. The sizes are from the package registry and CDN metadata for version 5.3.0 of the Fontsource packages. No file has been downloaded.

- **Option A:** three Fontsource packages as development dependencies (`@fontsource-variable/source-serif-4`, `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono`). Vite copies and hashes the files.
- **Option B (recommended):** vendor the seven woff2 files in `frontend/public/fonts/` with a hand-written `@font-face` block and the OFL text beside them. No dependency, exact files, and updates are rare.

Both options need a download, which needs Aryan's explicit permission: the seven filenames, the source (the CDN or registry tarball for the packages above) and about 203 KB. Either way: `font-display: swap`, preload only the two or three files the first screen needs (Source Serif 4 normal and IBM Plex Sans 400, with 600 if the header uses it), and a fallback face with `size-adjust` and the ascent and descent overrides so the swap does not move the layout (CLS under 0.05).

One limit to state: none of these files covers Devanagari. Contract text in that script falls back to a system font.

### 11.2 Test runner (decision D4)

There is none today. Recommended: Node's built-in runner, `node --test`, with its type stripping, which needs no dependency. **Checked in FE-1:** on this machine (Node 24.16, `"type": "module"`) a throwaway `.ts` test that imports `lib/offsets.ts` ran and passed. Limits:

- It tests pure `.ts` logic only: the offsets, the start-flow reducer, the reveal core, the hero fixture and the token contrast. It cannot test `.tsx`.
- Files under test import with explicit `.ts` extensions (the tsconfig already allows this) and use only erasable syntax: no `enum`, no parameter properties, no path alias.
- Type stripping is on by default from Node 22.18. The README's "Node 22 or later" becomes "22.18 or later" when `pnpm test` lands.

If this proves too limited, the fallback is Vitest as a development dependency. Ask only then.

### 11.3 Lighthouse and axe-core, at FE-R

Run through `npx` from a scratch folder outside the repo, against the production preview, with a Chromium browser path. Both download and execute code, so they need approval. Nothing is added to `package.json`.

---

## 12. Accessibility plan (WCAG 2.2 AA)

| Criterion | What the plan does |
|---|---|
| 1.3.1, 2.4.6 | One `h1` per route, headings in order, landmarks for header, nav, main and footer. The decorative § is `aria-hidden` |
| 1.4.3, 1.4.11 | The colour changes in 5.4, and a contrast test |
| 1.4.4, 1.4.10 | Text reflows at 200% zoom and at 320 CSS px. Nothing below 12 px |
| 2.2.2 | The hero runs under 2 s, which is under the five-second threshold, plays once and does not loop. Next example is a user action. Hover and focus pause it as a courtesy |
| 2.4.1, 2.4.3 | The skip link works and shows the 2 px ring. Focus moves to the `h1` on a route change |
| 2.4.2 | A distinct title per route (4.1) |
| 2.4.7, 2.4.11 | One global 2 px focus rule, and `scroll-padding-top` under sticky bars |
| 2.5.8 | 44 px hit areas, 8 px between neighbours. The project bar is above the AA minimum of 24 px |
| 3.3.2, 3.3.7 | Visible labels. Step data is kept when the user goes back, so nothing is asked twice |
| 4.1.2 | Role cards become a radio group built on native `<input type="radio">`, so arrow keys and the single tab stop come from the browser. The menu button has `aria-expanded` and `aria-controls`. Tabs and drawers keep their roles |
| 1.4.11 in forced colours | Backgrounds are removed in Windows high contrast, which would erase every mark. Under `@media (forced-colors: active)` marks use a `text-decoration` underline in `LinkText` and the focused mark a `Highlight` outline. Checked at FE-R with forced-colours emulation (amendment J) |
| 3.3.2 | Every input has a programmatic label. A placeholder is never the only label. The category filter has an `aria-label` today and keeps it |
| 2.5.7 | Uploading has a single-pointer path: the Choose file button. Drag and drop is an extra |
| Hero demo | The excerpt is a `figure`, the finding a `mark` with hidden text naming its status, the panel a named group (6.1) |
| 4.1.3 | Status messages for upload, parsing, analysis stages and the hero use `aria-live="polite"` |
| Reduced motion | The global rule in 7.4, and a final-state hero |
| Keyboard | A scripted keyboard run at FE-R, landing to start to reader to clause to judgment |

A manual screen-reader pass is a gap if no reader is available at FE-R. The BuildLog says so in that case, and does not claim one.

---

## 13. Tests

The runner is `node --test` (11.2). Tests sit next to the file they cover as `*.test.ts`. They are written first.

| Part | Test | What it asserts |
|---|---|---|
| FE-2 | `lib/reveal.test.ts` | Shows at once when no observer exists. Shows at once under reduced motion. Marks pending, then shown on the first intersection. Disconnects after the first intersection. Never marks shown while not intersecting. Works once per element. Uses a fake observer and a plain object, no DOM |
| FE-2 | `tokens.test.ts` | Reads `index.css` and checks every pair in 5.4, in both themes, against 4.5 or 3 |
| FE-3 | `pages/landing/heroExamples.test.ts` | Each finding's `start` and `end` slice the excerpt through `lib/offsets.ts` to its quote. Each excerpt appears verbatim in the sample contract. Includes one example with an astral character in a fixture string to prove code point handling |
| FE-4 | `lib/startFlow.test.ts` | 17 tests on the reducer and its helpers. A fresh flow has nothing chosen and only step 1 in reach. `maxReachableStep` at each state, including a refused file and a file still parsing. A forced step is corrected, and the `step` value reads as 1, 2 or 3 and anything else as 1. Back keeps inputs. Replacing the file resets the party and `partyNone` and keeps role and scope. A role is never preselected and choosing one does not choose a party. "None of these" counts as a decision, clears a chosen party and the reverse. A contract with no parties needs no choice. A failed parse blocks step 3. A late result for a replaced file is ignored. Each of the four refusals keeps its code. The suggested party follows the role. `nextBlocker` names what is missing on each step. `maxReachableStep` reads from it, so a step is reachable exactly when Next is open on the one before |
| FE-5 | A measurement script, not a unit test | The full-line average, and capacity by width, at 1024, 1280, 1440 and 1920 |

What these cannot cover is the `.tsx` layer. That is checked by the headless run, the screenshots, axe and the keyboard run at FE-R.

---

## 14. Part scopes and acceptance

| Part | Builds | Accepted when |
|---|---|---|
| FE-2 | Tokens (motion, type, spacing, widths, `control-border`), the colour changes, layout primitives, the reveal core and hook, route transitions and titles, the global focus and reduced-motion rules, 44 px hit areas, the favicon from `BrandMark` (16 and 32), `NotFound`, the dev-only gallery and Preview controls, route-level `lazy`, a root error page, the `<noscript>` line, the themed browser surfaces and visible scrollbars (5.8), the disclosure pattern, fonts self-hosted if approved, `pnpm test` | Tests pass. The build check in 6.7 prints nothing. No request leaves the origin. The contrast test passes. No target under 44 px on the audited routes. A forced route error shows the error page. Heading spacing reads as 6.1 and 5.5 say |
| FE-3 | The landing page with the live hero and the `heroExamples` fixture | The composition renders, with the Evidence section only if D7 is answered. The primary button is visible at 375 by 667 without scrolling. The hero runs once and holds still under reduced motion. No mock number and no placeholder judgment is on the page. LCP is measured |
| FE-4 | `/start`, the reducer, the radio-group roles, step state in `?step=` | The reducer tests pass. A keyboard-only run from the landing button to a started review works. The four upload errors show inline |
| FE-5 | The Reader recomposition (6.3) | The full-line average lands between 68 and 80 at 1280 and wider. Rows never truncate. The ruler is a strip. The toolbar does not wrap at 375. The `h1` exists. A 500,000 code point document scrolls without a main-thread block over 200 ms. The zero-findings band and the reload guard exist |
| FE-6 | How it works, Accuracy, Expired, NotFound | Accuracy has no clipped column and no text under 12 px at 375. Every route has an `h1` and a title |
| FE-R | The sweep in section 10, the measurements in 1.3, before and after screenshots for every route | Every P1 is fixed and every P2 is listed |

Each part also updates `Phases.md`, `Architecture.md`, this file, `DesignSystem.md`, `BuildLog.md` and, if commands or routes change, the README.

---

## 15. Open decisions

Each has a recommendation. FE-2 did not start until D1 to D6 were answered. D7 to D13 block only the part named. Section 17.2 records the answers to D1 to D13 as of FE-2.

| ID | Decision | Recommendation | Blocks |
|---|---|---|---|
| D1 | Hero data: a typed static fixture, or the client's sample mode (which needs a session on the landing page) | The fixture. It keeps the landing page free of a session and a network call, and a test guards it | FE-3 |
| D2 | The hero plays once and then offers "Next example", instead of looping and pausing on hover | Play once. A loop of three examples exceeds five seconds and would need a pause control | FE-3 |
| D3 | Font self-hosting: option B (vendored files) or A (Fontsource packages), and permission to download about 203 KB | B, with permission to download the seven files | FE-2 |
| D4 | Test runner: `node --test` or Vitest | `node --test`, checked on this machine | FE-2 |
| D5 | Keep the 4 px margin rule on notices and the judgment card only, or on everything | Notices and the judgment card only (3.3) | FE-2 |
| D6 | The colour changes in 5.4 | Approve all of them | FE-2 |
| D7 | The landing evidence quote: one verified verbatim passage (case, court, year, citation, text) from the corpus the product serves. Needs a corpus id from Tanishq | If it is not ready at FE-3, the section does not render | FE-3 |
| D8 | Does the real API accept a sample id while uploads are on? "Try the sample contract" depends on it | Ask when 2-E fixes API.md. Until then it follows the mock | FE-3, FE-4 |
| D9 | The problem section: only the CUAD facts, or a sourced statistic if one exists | CUAD facts only | FE-3 |
| D10 | The hero heading: A, B or C | A | FE-3 |
| D11 | The 1280 to 1439 Reader layout: a 64 px rail (recommended), or one of the rejected options | The rail | FE-5 |
| D12 | The report: does the PDF from 3-B list each finding with its quoted text? The landing page can tell visitors to take the report to a lawyer only if it does | Ask when 3-B is specified. Until then the copy does not mention the report | FE-3 |
| D13 | Sample mode on the landing page: when uploads are off, the hero shows "Try the sample contract" as the only button. The client has no way to report the mode before a session exists, so the capabilities call from 2-A would need a client method | Add the method at 4-C. Until then the landing page shows both buttons and `/start` handles the mode | FE-3, FE-4 |

The favicon stays in FE-2 as already agreed.

---

## 16. Deviations from the brief

Each is deliberate and needs Aryan's sign-off through the decisions above.

1. **The hero plays once** and offers "Next example", instead of pausing on hover or focus as a looping demo. The sequence still pauses on hover and focus while it runs. (D2)
2. **The hero reads a typed fixture,** not the mock adapter. The fixture is checked against the sample contract by a test. (D1)
3. **The hero panel shows no case law and no confidence decimal,** because the mock judgments are placeholders and the mock decimals are invented. The brief says the panel opens "with its quoted evidence", which here is the quoted contract text.
4. **The Evidence section may be omitted** until a verified quote exists, instead of showing a placeholder. (D7)
5. **The Problem section carries no statistic** about missed clauses. (D9)
6. **The panel and drawer duration changes from 200 ms to 320 ms** in `DesignSystem.md`, to match the brief's motion spec.
7. **The 4 px margin rule is narrowed** to notices and the judgment card. (D5)
8. **The header "Review" link is replaced** by the primary button.
9. **Mock counts leave the landing page and the Reader sidebar.** They stay on `/accuracy` under the example label.
10. **The Reader's below-1280 behaviour covers 1024 to 1279** with drawers, as the brief says, which changes today's docked panel at 1024.
11. **The landing page gains a seventh numbered section, "Questions",** because the brief's privacy and accuracy section would otherwise carry three jobs.
12. **The three-column margin grid starts at 1280, not 1024,** because the aside is about 80 px at 1024 and cannot hold a clause panel.
13. **The landing page promises no report,** until 3-B confirms what the report contains. (D12)

---

## 17. Amendments

Amendments are lettered. Each says what changed in the sections above. Later parts add their own below, with the part id.

### 17.1 FE-1: plan design review

**Method and its limits.** The plan design review was applied to this file as a method, with the same adaptation as the design consultation. Skipped, because they write outside `frontend/`, `docs/app/` and `README.md`: the skill's start-up routine (update check, telemetry, artifact sync), the generated mockups and comparison board, the review log and the plan-file report. Outside voices were not run. The review also asks one question per issue. Here Aryan's review of this file is the gate, so every finding is written in as a proposed amendment and nothing waits mid-run.

**Ratings.** The seven pass ratings, 7 of 10 overall before and 9 of 10 after the amendments, are in the BuildLog FE-1 entry. They are a record of the review and not part of the spec.

**Amendments**

| ID | Pass | Change | Sections touched |
|---|---|---|---|
| A | 1 | Above-the-fold budget: the primary button is visible at 375 by 667, and the hierarchy is brand, heading, subheading, buttons, privacy line, demo | 6.1, 14 |
| B | 1 | The journey diagram, the sample link's one-time `?sample=` parameter, and the Reader's redirect to `/expired` | 4.3, 6.2 |
| C | 2 | A state table for the new and changed surfaces, a root error page, a `<noscript>` line, the zero-findings band | 6.9, 6.3, 14 |
| D | 3 | The scene-by-scene journey, the reload guard, and the rule that the landing copy does not mention the report until D12 is answered | 9.1, 6.3, 15 |
| E | 4 | A seventh section, "Questions", so no section carries three jobs. The legal line appears once on the landing page. Base styles are the final state. Each hero example has a caption | 6.1, 8.2, 8.4 |
| F | 4 | Themed selection, caret, accent and scrollbars. Visible scrollbar thumbs. Tabular numerals. Prose link underline offset and a visited colour that differs. The `prose/lg` size. Heading spacing | 5.3, 5.5, 5.8 |
| G | 4 | Accepted detector hits, listed below | 3.3, here |
| H | 5 | The new patterns and the `DesignSystem.md` edits owed at FE-2, listed below | 14, here |
| I | 6 | The three-column grid starts at 1280. The landing layout is specified per viewport | 5.2, 6.1 |
| J | 6 | Forced-colours marks, native radio inputs, semantics for the hero demo | 12, 6.1 |
| K | 7 | A 500,000 code point document as a Reader acceptance check | 6.3, 14 |
| L | 1 | The reader-measure correction: the first audit counted wrapped lines and understated the measure, and the width method replaced it | 2.4 |

**G: accepted detector hits.** The design detector will flag these. Each is accepted for the reason given, and FE-R re-runs the detector and lists every remaining hit.

| Rule | Where | Why it stays |
|---|---|---|
| Numbered section labels | The § marks in the margin | The brief's device. They carry meaning: How it works uses the same numbers in its contents list |
| Cream default palette | Warm paper and sheet | The Marginalia identity, kept by the brief |
| Border accent on a card | The 4 px rule on notices and the judgment card | Narrowed to the places where it marks a different voice (3.3) |
| Look guessable from the category | A legal product in serif on warm paper | Accepted risk. The distinct part is the margin grid and the live ink-in, not the colours |

**H: new patterns to define in `DesignSystem.md`.**

| Pattern | Spec |
|---|---|
| Disclosure | A native `<details>` with a chevron icon, a 44 px summary row and a hairline below. Focus uses the global ring |
| Stepper | The text "Step 2 of 3" and an ordered list of the three step names with `aria-current="step"` on the current one. No percentage bar |
| Summary rail | A list of file, role, party and scope in the aside, each with a Change link back to its step |
| Reader rail | A 64 px column holding one icon button, Categories, with a 12 px label (6.3) |
| Preview controls | Development only. A floating drawer holding the mock switches |
| Container, Section, MarginGrid | 5.2 |

`DesignSystem.md` edits owed at FE-2:

| Section | Edit |
|---|---|
| 3.1 and 3.2 | The colour changes in 5.4 and the new `control-border` token |
| 3.4 | `overline` becomes 12 px. Add `display/xl`, `section-mark`, `marginal-note` and `prose/lg`. The fonts note says they are served from our own origin |
| 3.5 | Narrow the margin rule (3.3). Add the motion tokens and make panels 320 ms. Put the 44 px hit area above the button sizes. Record the Reader widths and the marketing grid |
| 5 | Add forced colours and visible scrollbars |
| New | The patterns in the table above |

**Not in scope.**

- Right-to-left text, and Devanagari fonts. Contract text in those scripts falls back to a system font.
- A print stylesheet. The PDF report is the printable output.
- Saving the theme choice. Nothing is stored, so the theme follows the system on each load.
- Analytics, experiments and any tracking. The product collects nothing by design.
- Accounts, email capture, pricing, multi-document review, offline use, translation.
- Mockups. None were generated in FE-1.

**What already exists, and is reused.** The 50 components and the icon set (`NoticeBanner`, `StatusChip`, `PolarityBadge`, `ConfidenceBand`, `StatuteTag`, `OffsetTag`, `SpanHighlight`, `MarginRuler`, `JudgmentCard`, `ClauseDetailPanel`, `UploadDropzone`, `PartyBindingField`, `RoleSelector`, `StageProgress`, `ErrorCard`, `EmptyState`, `Tabs`, `MetricCell`, `KeyboardHint`, `DropdownMenu`, `MobileDrawer`, `CategorySidebar`, `ReaderToolbar`), the token file, `lib/offsets.ts`, `api/catalogue.ts`, the mock adapter's job timeline, and the gallery as a record of component states. From the platform: React 19 `<title>` hoisting, React Router's `lazy` and `viewTransition`, native `<details>`, native radio inputs, CSS animations, and `node --test`.

### 17.2 FE-2: foundations

**Decisions.** Aryan answered D1 to D7 and left D8 to D13 to the recommendations in section 15. None of D8 to D13 adds a dependency, changes a fixed phrase or moves a route, so each recommendation stands.

| ID | Answer |
|---|---|
| D1 | A static typed fixture. A test slices it through `lib/offsets.ts`. Built in FE-3 |
| D2 | The hero plays once, pauses on hover and focus while it runs, then offers "Next example". The reason is below |
| D3 | Option B. Seven font files are vendored in `frontend/public/fonts/`. Done in FE-2 |
| D4 | `node --test` with type stripping. Done in FE-2 (`pnpm test`) |
| D5 | The 4 px margin rule stays on notices, judgment cards and rule-flag cards only. Removed from `CategoryRow`, `ClauseDetailPanel` and the Gallery in FE-2 |
| D6 | All seven colour changes and the new `control-border` token. Landed in FE-2 |
| D7 | The Evidence section stays unrendered until Aryan sends a verified passage from Tanishq. FE-3 |
| D8 | Follow the mock for the sample id |
| D9 | CUAD facts only in the problem section |
| D10 | Hero heading A, "Know which clauses to ask a lawyer about." |
| D11 | A 64 px Reader rail from 1280 to 1439 |
| D12 | The landing copy does not mention the report |
| D13 | Both landing buttons are shown, and `/start` handles sample mode |

**D2 and WCAG 2.2.2.** Success criterion 2.2.2 (Pause, Stop, Hide, level A) asks for a way to pause, stop or hide content that moves on its own, lasts more than five seconds and sits beside other content. A looping hero meets all three conditions. A hero that plays one example, stops and offers "Next example" has nothing moving after the run, so the criterion never applies, and a visitor on a touch screen, who has no hover, still has a stopped end state. The run keeps the brief's pause on hover and focus, and it renders static under reduced motion. FE-3 keeps each run under five seconds. This is deviation 1 in section 16, now signed off.

**Amendments**

| ID | Change | Sections touched |
|---|---|---|
| N | `Container`, `Section` and `MarginGrid` live in one file, `components/Layout.tsx`, not in a `layout/` folder. The three are 44 lines in all, and a folder with an index would add a file to every import | 5.2, Architecture.md 7.3 |
| O | A baseline bug, found and fixed: the `Link` atom called `preventDefault` on every click, so no internal link in the header, footer or page body navigated. A `#/` address now goes through the router, with a view transition. Other addresses behave as links | 5.8 |
| P | `MobileDrawer` in fixed mode stays mounted and slides on `transform`, hidden and `aria-hidden` when closed, so it can animate out. The Reader still mounts the bottom sheet only while a finding is selected, so the sheet slides in and leaves with no exit animation. Focus does not move into a drawer on open or back on close. Both belong to FE-5 | 6.3, 7.3 |
| Q | Hit areas fixed beyond the plan's list: the menu trigger in `DropdownMenu`, the group header in the Reader sidebar (36 to 44 px), the filter field (the whole 44 px box now focuses the input, and its reset button has a 44 px area) and the confidence button | 5.6 |
| R | The `CategoryRow` bracket mark takes no space in the row. An in-flow placeholder cost every name about 16 px | 5.4 |
| S | The font files carry the Latin range only. The rupee sign U+20B9, the bracket marks `⟦ ⟧` and every non-Latin script fall back to a system font. A Latin-extended subset is worth adding, because contracts in India contain the rupee sign. The three licence texts were fetched with the seven files, one step beyond the seven files that D3 named | 11.1 |
| T | The contents links on How it works are inline blocks with 13 px of block padding, a visible spacing change that FE-6 redoes. `scroll-mt-8` is gone, because the page's `scroll-padding-top` of 80 px is the one offset | 6.4 |

**Deferred, with the owner**

| Item | Owner |
|---|---|
| The ink-in keyframes. Resolved in FE-3 (17.3, W). `--stagger` is still unused and belongs to the Reader's rows entering (7.3) | FE-5 |
| The header restructure: the primary "Review a contract" button, hidden on `/start` and `/review`. `/start` exists as an interim page from FE-3 (17.3, U), and the not-found and expired pages link to it. Resolved in FE-4 (17.4, AH) | Done |
| The footer Credits link target (A10 in the plan) | FE-6 |
| The 4 px rule on `ErrorCard`, `Toast`, `ScopePanel`, `ManualReviewList`, `PartyBindingField`, `PerformanceTableRow` and `RadioCard`. FE-4 removed it from `PartyBindingField` and `RadioCard` (17.4, AG). `ErrorCard`, `Toast`, `ScopePanel`, `ManualReviewList` and `PerformanceTableRow` keep it | FE-5, FE-6, whichever recomposes the component |
| Category names squeezed to one letter by the chip and the count (B3 in the audit). The unvalidated row shows about 8 px of its name at 1440 | FE-5 |
| The ruler's ticks are 12 by 3 px and cluster at the top of a short document. Their hit boxes overlap, so they cannot be enlarged. The marks in the text and the category rows reach every finding from the keyboard | FE-5, which replaces the ruler with a strip |
| Tabular numerals on counts and metric cells. FE-4 applied them to the step line and the summary note only. Counts and metric cells are still proportional | FE-5, FE-6 |
| The confidence popover stated a calibration figure with no cited source. Resolved in FE-3 (17.3, Y): the band shows calibration detail only when the data carries it | Done |
| A Latin-extended font subset (S). Resolved in FE-3 (17.3, X) | Done |

### 17.3 FE-3: landing and the live hero

**Built.** The landing page at `/`, in the order of 6.1: the hero with its live demo, sections § 1 to § 6 and the closing call to action. D1, D2, D8, D9, D10 and D13 are built as recorded in 17.2, and D12 holds: the copy does not mention the report. The Evidence section is built and stays out of the build until D7 is answered (below).

**Amendments**

| ID | Change | Sections touched |
|---|---|---|
| U | A page at `/start` ships in FE-3, ahead of the plan's FE-4, because the landing buttons need a destination. It is the baseline form moved out of `Home`, with the marketing hero removed, the heading "Review a contract" and the title "Review a contract \| ClauseAnchor". It reads `?sample=secondment` once, for known sample ids only, then replaces the address. The header "Review" link and the not-found and expired pages point to it. FE-4 replaces the page with the stepped flow | 4.1, 6.2, Architecture.md 7.3 |
| V | The hero ruler is hidden below 640 px. At 375 px a 28 px rail would take about 9 percent of the sheet. From 640 px the tick shows | 6.1 |
| W | A found or review mark is two background layers, the underline over the tint, so the ink-in can sweep `background-size`. `.ca-ink` plays the sweep over `--dur-ink` from `--ink-delay`, and the mark keeps its final state as its base style. The review underline is a repeating gradient (6 px dash, 4 px gap) in place of the 2 px dashed border. The Reader uses the same mark, so FE-5 only has to add the class | 3.3, 7.3, DesignSystem.md 3.3 and 6 |
| X | Five Latin-extended files (Source Serif 4 normal and italic, IBM Plex Sans 400, 500 and 600, 135,184 bytes in all) from the package version D3 used, each with a `unicode-range`. A page fetches them only when it holds a character in that range, and the landing page requests none. The rupee sign renders in Source Serif 4: a probe in the hero paragraph and the Reader at clause 2.2 both used the web font, and with the files blocked the sign fell to Georgia. None of the three hero excerpts contains a rupee sign, and the mock has no finding on clause 2.2. Resolves S | 11.1 |
| Y | `ConfidenceBand` shows calibration detail only when the data gives it. A `calibration` prop, `category` or `pooled`, which the Reader passes from `calibration_scope`, turns the label into a button that opens "Calibration: category-specific" or "Calibration: pooled". Without the prop the band is plain text. The "How confidence works" button and the line "Calibrated on 214 examples from 48 contracts" are gone, and a grep guards the count (1.2) | 1.2, 6.3 |
| Z | Shared components lose controls that did nothing, and the hero gets the options it needs. `RuleFlagCard` has no "Read the section" button and `StatuteTag` is a label, because no data holds the statute text. `ClauseDetailPanel` shows Close only with `onClose` and the Case law section only when case law data is given, and takes `titleAs` so a page that shows the panel as an example adds no heading. `MarginRuler` takes `viewport={false}` and `caption=""`, and is a tab stop only with `onSelect`. `Button` takes `to` and renders a router link with the same look. `Layout.tsx` gains `SectionFrame`, which `Section` now uses | 5.2, 6.3 |

**Copy beyond 8.2.** The does and does-not lists, the three example captions, the sentence under "Needs a lawyer", the margin source note, the link texts and the page title are new ("ClauseAnchor \| Know which clauses to ask a lawyer about"). The last item of the does-not list is "Promise that nothing was missed", which replaces a storage claim that the privacy section and the footer already make. The strings went through copywriting, copy-editing and stop-slop. Three changed: the third caption names ClauseAnchor instead of "it", the does list says "when it is unsure" to echo the hero, and "with character offsets" became "and shows where each quote sits".

**Skill advice not followed.** The design-taste review lens bans section-number marks, a serif display, a line under the buttons and a subheading over 20 words. Decisions A to L and D10 choose each of those, so they stand.

**What was checked** (production build; the browser pane for page structure and the Reader, headless captures for the layouts). The build, bundle and grep checks ran on the final build. The rest were measured earlier in this part, before the last copy edits, the removal of the two dead buttons and a link alignment fix:

- `pnpm typecheck`, `pnpm test` (20 of 20: 7 reveal, 8 colour tokens, 5 hero fixture) and `pnpm build` (162 modules) pass. The index chunk is 239.47 kB (72.61 kB gzipped) and the `/start` chunk 3.96 kB gzipped.
- Landing first load: 0.7 kB of HTML, six script files at 121.4 kB gzipped, 7.3 kB of CSS and five font files at 136.6 kB. That is 22 kB under the FE-0 figure of 143 kB, which was one script file for every route.
- Fold: at 375 by 667 the privacy line ends at 619 px and the primary button starts at 455 px. At 1280 by 720 the sheet and the panel both start at 550 px, so the excerpt shows.
- The hero run: the sheet is still until 600 ms, the mark inks in from 600 to 1000 ms, the ruler tick fades in from 1000 to 1200 ms and the panel rises from 1200 to 1520 ms. Hover or focus in the sheet or the panel pauses it. "Next example" replays the run and is not frozen by its own hover. Reduced motion draws the final state at once. The status line reads "Example n of 3: category, status".
- The page has one `h1` and a heading outline with no skipped level. It has 26 controls, all named, no horizontal overflow, no text under 12 px and no console output. Two targets are under 44 px, both links inside running text, which WCAG 2.5.8 exempts.
- With no passage set, `grep -rl` for "Evidence you can check", "evidence-title", "look it up yourself" and "EvidencePassage" over `dist` prints nothing. With a fake passage the section renders after § 2 and the later marks run to § 7. The constant was set back to `null` and the build repeated, with the same file hash as before.
- The Reader after the shared changes: marks draw as two layers (a 2 px underline over the tint, and the repeating dash for a review mark), the band label opens its calibration popover, Case law keeps its section and its empty state, Close panel is present, and no "Read the section" button shows.

**Open, not measured.** LCP and CLS for `/` were not measured, because the capture run was blocked and the browser pane records no paint while its window is hidden. The acceptance row for FE-3 asks for LCP, so it moves to the FE-R Lighthouse run unless Aryan wants a rerun first. The Reader was not captured at five widths: its marks and band were checked by structure and computed style, not by eye.

**Deferred, with the owner**

| Item | Owner |
|---|---|
| The heading "Nothing is kept after your session" sits above a body that says the contract is deleted within 60 minutes. A reader can take the heading to mean that nothing remains once the session ends. The meta description says the same. Resolved at the start of FE-4 (17.4, AA): the heading now reads "Your contract is deleted within 60 minutes." The meta description in 8.3 and `index.html` now says "your contract is deleted within 60 minutes" (17.4, AL) | Done |
| The hero panel stacks under the sheet from 768 to 1279 px at the margin grid width, which leaves the right half of the row empty (amendment I). Resolved at the start of FE-4 (17.4, AB) | Done |
| The Reader's confidence popover keeps its open state when another finding is selected | FE-5 |
| `JudgmentCard` carries the authority label "Reviewed as of Sep 2026" as a fixed string. Resolved at the start of FE-4 (17.4, AC): the label comes from the passage's authority status | Done |
| LCP and CLS for `/` (above) | FE-R |

### 17.4 FE-4: the stepped start flow

**Built.** `/start` is the three-step flow of 6.2: Upload the contract, Say which side you are, Confirm the scope. The step lives in `?step=`. The rules are a pure reducer in `lib/startFlow.ts`, written test first (17 tests), and the upload and the polling are in `pages/start/useStartFlow.ts`. The header gains its primary button (AH), the role and party cards are native radio groups (AF, AG) and the summary rail shows from 1280 px (AE). Three carry-over fixes from FE-3 were made at the start of the part (AA to AC), and a fault in the loading button was found and fixed at the end (AK). A last pass changed the meta description, capped the hero subline, added a Fail parse switch and ran the copy and ponytail reviews again (AL to AO).

**Amendments**

| ID | Change | Sections touched |
|---|---|---|
| AA | The landing § 6 heading reads "Your contract is deleted within 60 minutes." A trailing period was added, to match the other section headings. The meta description followed at the end of the part (AL) | 8.2, 17.3 |
| AB | The hero panel spans the sheet's full width from 768 to 1279 px. Side by side was rejected: it needs about 1,180 px (two columns of about 573 px for 60 characters, and a 32 px gap), and the main column is 720 px in a 768 px viewport, 784 px at 1024 and 1024 px at 1279. The shell width of `ClauseDetailPanel` is `var(--panel-w, 400px)` and `.hero-demo .hero-panel` sets `--panel-w: 100%`. From 1280 the panel stays 320 px in the aside. Measured characters on a full line: 72 to 82 at 768 and 78 to 82 at 1024, for the sheet and the quote alike. At 1279 both run 115 to 120. The sheet was already that long before this change, and the measure is not capped | 6.1, 17.3 |
| AC | `JudgmentCard` labels follow the passage's authority status: "Reviewed", "Later overruled or modified" or "Not yet reviewed". "Reviewed" carries no date, because the passage data has no date field. The default `authority` prop is `"not-reviewed"` and not `"reviewed"`, so a card given no status never claims a review. The grep in 1.2 also covers `Reviewed as of` | 1.2, 6.3, 17.3 |
| AD | The step is not part of the reducer state, which 6.2 listed. A copy in the state and a copy in the address needed two effects to stay equal, and the two raced on browser Back. The address owns the step, `clampStep(state, requested)` corrects it, and the reducer has no next, back or goto action | 6.2 |
| AE | The summary rail shows from 1280 px, where the margin grid has its aside, and not from 1024, where the aside is about 80 px wide (amendment I). Below 1280 the summary is one line above the buttons on steps 1 and 2, with the chosen values joined by a middle dot and Scope left out, and a full list in step 3. The list has four rows, and a row reads "Not chosen yet" until it is decided. The rail has no Change link, which 17.1 (H) had planned: Back and the browser's Back keep every input | 5.2, 6.2 |
| AF | No role is preselected and no party either. "None of these" is the last radio of the party group, not a separate text button. Choosing a party clears it, and the reverse. The party that fits the role is listed first with the tag "Suggested" | 6.2 |
| AG | `RadioCard` is a label around a native radio input, so the single tab stop and the arrow keys come from the browser. The chosen card has a 2 px border (the 1 px border and a 1 px inset line), the `anchor-100` tint and a check icon, so the state does not rest on colour alone. The 4 px rule is gone from `RadioCard` and `PartyBindingField`. `RadioCard` gains `tag`, `children`, `value` and `checked`. Each group generates its own name with `useId`: the Gallery shows a light and a dark panel side by side, and a shared name made their radios un-check each other. `RoleSelector` is controlled, with `null` for no role, takes `hideLegend` and drops its `radiogroup` role, because the fieldset and its legend group the cards. `RoleKey` moves to `lib/startFlow.ts`. `PartyBindingField` is a radio group labelled by its question, takes `none` and `suggested`, and shows "Reading your document." while the file is parsed | 5.6, 6.2, DesignSystem.md 3.5 and 6 |
| AH | The header carries the primary button "Review a contract" at the far right from 768 px. It is absent on `/start` and in the Reader, and below 768 px it sits inside the menu. The "Review" link is gone. This builds 4.2 | 4.2 |
| AI | `NoticeBanner` shows its dismiss button only when `onDismiss` is given, so the sample-mode and scope notices on `/start` carry no dead control. The refusal line of `UploadDropzone` has `role="alert"`, so a screen reader announces the reason when it appears | 12 |
| AJ | History and parameters. A step change pushes a history entry. A forced or unreachable `?step=` is corrected with a replace, so Back leaves `/start`. Browser Back from step 2 returns to step 1 with the file kept. The sample link replaces `/start?sample=secondment` with `/start`, starts the upload, then pushes `?step=2`. On a step change, focus moves to the step heading and the page does not scroll | 4.3, 6.2 |
| AK | `Button` in the loading state ignores clicks. It is not `disabled`, so keyboard focus stays on it, and it keeps `aria-busy`. Found at the end of FE-4: clicks on "Start review" 30 ms apart called `startAnalysis` once each, three calls for three clicks, and now call it once. The baseline page had the same fault | DesignSystem.md 6 |
| AL | The meta description in `index.html` and 8.3 reads "Know which clauses to ask a lawyer about. Every finding quotes your contract or a published judgment, and your contract is deleted within 60 minutes." (149 characters). "Nothing is stored after your session" is gone. The sentence follows the landing § 6 heading and the privacy line word for word, so it is passive like both | 8.3 |
| AM | The hero subline is capped at `max-w-[66ch]`. A cap of 68ch was tried first and left lines of 73, 72 and 75 characters, and 75 is not under 75. At 66ch the longest line is 71 at 768, 1100, 1200, 1279 and 1280 px. Before the cap it was 93 at 1100 and 111 at 1279. The heading has no cap: its longest line is 27 characters at 1100 and 34 at 1279, and 66ch of its display size is wider than its text. The hero sheet and the quote were not touched. They still run 93 to 96 characters at 1100 and 117 to 120 at 1279 | 6.1, DesignSystem.md 3.4 |
| AN | `failParse` joins `MockSettings`, and the Preview controls show a "Fail parse" switch beside "Failed analysis". A document uploaded while it is on gets a parse job that fails 1 s in (half of `PARSE_MS`), so step 2 shows the failure card with no patched call. "Try again" on that card turns the switch off before it uploads again, as the reader does for `failAnalysis`, and only when the parse had failed: a retry after a network error leaves it alone. The states table in 6.9 now names the shipped failure card and the empty-party line. It had planned "This file could not be read." with Replace file, and a longer empty-party sentence | 6.7, 6.9 |
| AO | The copy pass ran in the order copywriting, copy-editing, stop-slop. Changed: the parse-failure card reads "We could not read your document" over "Try again, or go back and choose a different file." (it was "Your document was not read", a passive title over a message that said the same again), and the rail heading is "Your choices", the words of its label for assistive technology (it was "Your review"). Left as written: the three step titles, "Upload a contract to begin.", "Choose a sample contract to begin.", "Checking your file.", "Still reading your document.", "Choose your role to continue.", "Choose a party, or None of these, to continue.", "Not chosen yet", "Indian law review on" and "off", and "Suggested". "Still" is an adverb and stays because it says the read goes on. The hints say "continue" while the button says "Next", and 8.3 fixes "Next". The `JudgmentCard` label "Reviewed" does not say who reviewed, and no document defines the status, so it is Aryan's call | 8.3 |

**Rules for the next parts.** Call `setSearchParams` with a whole object and never the updater form: the setter keeps the parameters of the render it came from, and a call that outlives its render put `sample` back. End async work with an `alive` flag, not a counter bumped in an effect cleanup: React's StrictMode runs a test unmount in development, and the counter dropped the first upload. Give every radio group its own name.

**Copy beyond 8.3.** The strings new in this part: "Choose your role to continue.", "Choose a party, or None of these, to continue.", "Your choices" (the rail heading and its label for assistive technology), the rail labels "File", "Role", "Party" and "Scope", "Not chosen yet", "Indian law review on" and "Indian law review off", the parse-failure card "We could not read your document" with "Try again, or go back and choose a different file." and its code "ERR_PARSE", "Checking your file." as the hint while the upload is checked, and the Preview controls note "Reading the document stops partway. Try again turns it off." (development only). The upload hints come from the baseline. The strings went through `copywriting`, `copy-editing` and `stop-slop` at the end of the part (AO), and `stop-slop` ran again on the edits.

**What was checked.** Measured earlier in this part, in headless Edge over the DevTools protocol against the dev server, extensions disabled:

- The reducer tests were red first, because the module did not exist, then green. Six mutations of the reducer and its helpers each fail at least one test.
- A keyboard-only run from the landing header button to a started review at `/review/doc_...` passes, with the arrow keys moving inside each radio group and one tab stop per group.
- The four upload refusals show inline with the exact messages, and a good file after a refusal recovers. A forced `?step=3` is corrected with a replace and Back leaves `/start`. Browser Back from step 2 returns to step 1 with the file kept.
- The sample link replaces the address, uploads and lands on step 2. Sample mode (uploads off) works. With the mock set to fail the next request, "Try again" works and lands on step 2.
- The header button sits at the far right, is absent on `/start` and the Reader, and sits in the menu below 768 px. The "Review" link is gone.
- The Gallery shows every `RadioCard` and `PartyBindingField` state, and the role specimens on the landing page stay inert.
- A route sweep at 375 and 1280 px prints nothing to the console and shows no horizontal overflow, except the development-only `/gallery`, which overflows at 1280. Whether that predates FE-4 was not checked.
- The Reader regression pass: 24 captures in `frontend/.screens/FE-4/reader-clean/` (four widths, both themes, and nothing selected, a found finding selected and a review finding selected). Pixel differences against FE-2 are in `reader-diff/`. The sheet, the marks, the band and the chips are identical, and the differences are run-state data. The one visual change is that the empty "Nothing selected" panel lost its Close button (17.3, Z). FE-2 has no review-selected baseline, and its `reader-selected-1440-dark.png` is a light-theme capture, so 1440 px dark with a found finding selected was compared by eye only.

Run again at the end of the part, on the final code:

- `pnpm typecheck` exit 0, `pnpm test` 37 of 37 (7 reveal, 8 colour tokens, 5 hero fixture, 17 flow) and `pnpm build` 165 modules with no warnings, run again on the final code after the last edits. The index chunk is 239.45 kB (72.67 kB gzipped). The `/start` chunk is 15.24 kB (5.66 kB gzipped, up from 3.96 at FE-3). `dist` holds no "Preview controls", "Fail parse" or "Failed analysis" string. The identifier `failParse` is in the production chunks (the mock settings and the retry), as `failAnalysis` is. The three new modules are `startFlow.ts`, `useStartFlow.ts` and `Summary.tsx`.
- The parse-failed path through the new switch, in headless Edge with no patched call: with "Fail parse" on, the sample link lands on step 2 and the card "We could not read your document" shows with "Try again, or go back and choose a different file." and `ERR_PARSE`. Next is disabled, the party group is hidden and the console is empty. "Try again" turns the switch off, step 2 shows the party group with its three radios (two parties and None of these) and the card is gone. Capture: `frontend/.screens/FE-4/fail-parse-final/`.
- AK: with a counter around `client.startAnalysis` and three clicks on "Start review" at most 30 ms apart, the original line made three calls and the fixed line made one. A test that calls `click()` twice in one synchronous run proves nothing, because both clicks land before React commits the loading state.
- The hero measure after the cap (AM), in headless Edge at 768, 1100, 1200, 1279 and 1280 px with reduced motion on, counting the glyphs on each rendered line: the subline's longest line is 71 characters at every width. The heading, the sheet and the quote were measured in the same run. Captures at 1100 and 1280 px: `frontend/.screens/FE-4/hero-cap/`.
- `/ponytail:ponytail-review` over the full FE-4 diff, at the end of the part. Fixed, three: `RoleSelector` still re-exported `RoleKey` and nothing imported it from there. `PartyOption` in `useStartFlow.ts` repeated `PartyChoice` field for field and is gone. `maxReachableStep` repeated the gate `nextBlocker` already holds and now reads from it, which left the test that compared the two with nothing to compare, so that test is deleted (18 tests became 17). Fixed, one smaller: the one-line summary excluded the Scope row by its label text and now takes the first three rows. Kept, three: the four refusal codes are listed in the reducer's type, in `REFUSALS` and in `REFUSAL_ZONE` (one line to save, three files to touch). `RoleSelector` holds its own state only for the gallery's uncontrolled example. `upload({ sampleId }, ...)` stands at three call sites in `Start.tsx`, and a helper saves no lines. About 22 lines out, 5 of source and 17 of test.

**Open, not measured.** LCP and CLS for `/`, because no run measured them (FE-R). The hero sheet and quote still run 93 to 96 characters at 1100 px and 117 to 120 at 1279 px (AM).

**Deferred, with the owner**

| Item | Owner |
|---|---|
| LCP and CLS for `/` | FE-R |
| The 4 px rule on `ErrorCard`, `Toast`, `ScopePanel`, `ManualReviewList` and `PerformanceTableRow` | FE-5, FE-6, whichever recomposes the component |
| Tabular numerals on counts and metric cells. FE-4 applied them to the step line and the summary note only | FE-5, FE-6 |
| The hero sheet and quote at 1100 to 1279 px, 93 to 120 characters. One cap on the sheet would fix it, if Aryan asks | FE-R |
| The `JudgmentCard` label "Reviewed" does not say who reviewed. It needs a definition of the status first | Aryan |
| Whether the real API accepts a sample id while uploads are on (D8) | 4-C |
| The `/gallery` overflow at 1280 px, development only, and whether it predates FE-4 | FE-R |
