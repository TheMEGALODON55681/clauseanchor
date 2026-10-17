# Annotation Guidelines

Rules for annotating the Indian contract set (plan v1.1 section 4.3). Aryan annotates contracts 001 to 025 and Tanishq 026 to 050. Both annotate the same 10 documents. Every annotation records the `guideline_version` it was made under.

**Version 0.1, draft.** The version stays below 1.0 until the pilot on the 10 development documents has tested the rules and Tanishq has answered the open items.

Open in this draft: two unconfirmed ids, the CUAD fixed questions and the record keys marked "proposed" (section 9). Tanishq supplies the fixed questions, and section 2 gives a working definition for each until they arrive. The ceiling counts (section 8) are not run.

Every example in this file is made up. No text comes from a real contract, and none may be added (`Rules.md` section 5).

## 1. States and ground rules

For each of the ten labels, an annotator gives each contract one state:

| State | Meaning |
|---|---|
| `present` | At least one span carries the label |
| `absent` | The whole text was readable and nothing in it carries the label |
| `unassessable` | The text cannot settle the question: part of the document is missing or unreadable, or the provision depends on text that is not there (6.3 and 6.4) |

The three names are the working ones. The 2-0B record fixes them.

Ground rules for every label:

- **Which text counts.** Read all of `source_text`: body, tables, schedules and footnotes. Headings and recitals count only when they hold operative words. A blank placeholder (`[●]`, a row of underscores) leaves the provision present.
- `absent` describes the text. It does not say the contract is complete or safe.
- A category outside the ten is not annotated, and it is not a negative.
- A span says what the text says. Never label stamp payment, enforceability, a case outcome, fairness or who a term favours. A stamping clause is not proof that an instrument is stamped, and a missing one is not proof that it is not.
- When a reading turns on law, annotate the words and write the question on the faculty review list (section 7).

## 2. The label set

Ten labels. Five are the India extensions of plan v1.1 section 4.3. Five are CUAD categories, annotated for a limited domain-shift check.

| Id | Source | Id status | Fixed question |
|---|---|---|---|
| `in.arbitration` | India | Confirmed | Which text provides for arbitration of disputes? |
| `in.seat_venue` | India | Confirmed | Which text states the seat or venue of arbitration? |
| `in.stamping_registration` | India | Confirmed | Which text addresses stamp duty, stamping or registration? |
| `in.forum_selection` | India | Confirmed | Which text selects courts or a judicial forum for disputes? |
| `in.dispute_escalation` | India | Confirmed | Which text requires negotiation, mediation or another step before formal dispute resolution? |
| `cuad.non_compete` | CUAD | Confirmed | Pending from Tanishq |
| `cuad.liquidated_damages` | CUAD | Confirmed | Pending from Tanishq |
| `cuad.cap_on_liability` | CUAD | Confirmed | Pending from Tanishq |
| `cuad.uncapped_liability` | CUAD | **Unconfirmed** | Pending from Tanishq |
| `cuad.governing_law` | CUAD | **Unconfirmed** | Pending from Tanishq |

Confirmed means the id appears in plan v1.1 or in `ml/fixtures`. The two unconfirmed ids appear in neither. Tanishq confirms them with the fixed questions, and the ids are final when he answers.

Each label has a one-line definition and a test. Apply the test to one sentence or sub-clause at a time.

**`in.arbitration`**
- Definition: text under which disputes between the parties go to arbitration.
- In: the sentence agrees to arbitrate or says which disputes go to arbitration, with the tribunal, rules or procedure when they sit in that sentence.
- Out: arbitration is named in passing (a cost term, a carve-out, a pointer such as "under clause 12"), or the sentence is about courts.

**`in.seat_venue`**
- Definition: text that names the place of the arbitration.
- In: the sentence names a place for the arbitration, with the word that says what the place is, if it has one.
- Out: a place for courts, notices, performance or a party's address.
- Attribute `designation` (proposed key): `seat` when the text calls the place the seat or the place of arbitration, `venue` when it calls the place the venue and not the seat, and `ambiguous` when it names a place with neither word. The attribute records the words and never their legal effect.

| Text | `designation` |
|---|---|
| The seat of the arbitration shall be Pune. | `seat` |
| The venue of the arbitration shall be Chennai. | `venue` |
| The arbitration shall be held at Nagpur. | `ambiguous` |
| The seat and venue of the arbitration shall be Delhi. | `seat` |

**`in.stamping_registration`**
- Definition: text on stamp duty, stamping or registration of this agreement or an instrument under it.
- In: the sentence names stamp duty, stamp paper, stamping or registration of the instrument, with who pays or acts, by when, or on what condition, when it says.
- Out: registration of anything else (a company, a trademark, a licence, a tax account) and a party's "registered office".
- Stamp certificate pages are an open item (section 9).

**`in.forum_selection`**
- Definition: text that picks the courts or the judicial forum for disputes.
- In: the sentence names a court, or the courts of a place, with exclusivity when it says. Courts named to supervise an arbitration or grant relief in one are in.
- Out: text that picks only the governing law, and text about arbitration.

**`in.dispute_escalation`**
- Definition: text that requires a step, such as negotiation or mediation, before formal dispute resolution.
- In: the sentence makes a step compulsory, or makes formal proceedings wait for it, with the stage, deadline or condition when it says.
- Out: voluntary wording ("may", "are encouraged to") and steps that do not come before formal proceedings.

**`cuad.non_compete`**
- Definition: text that bars a party from competing, or from a stated business, sector or area.
- In: the sentence bars a party from competing with the other party, or from a stated line of business, technology or territory, during the term or for a period after it.
- Out: bans on soliciting customers or staff, exclusive dealing or supply, and confidentiality.

**`cuad.liquidated_damages`**
- Definition: text that fixes a sum payable for breach, or a fee payable on termination.
- In: a stated amount or formula payable on breach, delay or early termination, with who pays and the trigger. A termination fee is in.
- Out: interest on late payment, and a right to claim damages with no fixed sum.

**`cuad.cap_on_liability`**
- Definition: text that limits how much a party must pay for breach, or how long a claim can be brought.
- In: a maximum amount, a multiple or share of fees, a link to insurance cover, or a deadline for claims, applied to a party's liability.
- Out: a waiver of indirect or consequential loss with no amount or time limit, a limit on a price or fee, and a duty to carry insurance.

**`cuad.uncapped_liability`** (id unconfirmed)
- Definition: text that says a party's liability has no limit, or that a cap does not apply to a named breach or loss.
- In: wording such as "unlimited", or "this limit does not apply to" a stated breach or loss.
- Out: silence. A contract with no cap does not say that liability is uncapped.

**`cuad.governing_law`** (id unconfirmed)
- Definition: text that names the law governing the agreement.
- In: the sentence names the country, state or legal system whose law governs the agreement, its interpretation or its performance.
- Out: a court or a seat, a statute that applies to one topic only (the Act under which an arbitration runs), and a general duty to follow "applicable law".

## 3. Spans

A span is one unbroken slice of `source_text`. A finding is one provision, and it has one or more spans.

### 3.1 Start and end

The sentence is the default unit.

- **Start** at the first character of the first operative sentence. Leave out the clause number, the heading and a run-in heading ("Governing law.").
- **End** at the last word of the last operative sentence, with its closing full stop. Leave out a closing semicolon and a joining "and" or "or".
- **No white space at either end.** A span may hold line breaks inside it.
- **Sub-clause.** When the label's words sit in one lettered or numbered item, the span is that item without its label.
- **Clause.** When every sentence of a clause passes the answer test (3.2), the span is the whole clause body.
- A typed label in the middle of a span stays in it, because the span is a slice. A Word label in the middle is not in the text (3.6).

### 3.2 Complete operative spans: the answer test

A span is complete when a reader who sees only the span can answer the label's fixed question: who is bound, to what, how much, for how long, where, on what condition. It includes each qualifier that changes the answer: a condition, an exception, an amount, a period, a place, a word of exclusivity.

1. Read the span alone and ask the fixed question. If the answer is missing a part, widen the span to the sentence that gives it.
2. Drop each sentence in turn. If the answer stays the same, leave that sentence out.

Example 1:

```text
12.1 Any dispute arising out of this Agreement shall be finally settled by arbitration before a sole arbitrator.
12.2 Each party shall bear its own costs of the arbitration.
7.3 The Buyer may withhold a disputed invoice until any arbitration under clause 12 ends.
```

- `in.arbitration`: "Any dispute arising out of this Agreement shall be finally settled by arbitration before a sole arbitrator."
- Clause 12.2 adds nothing to the answer, so it is out. Clause 7.3 names arbitration in passing, so it gets no span.

### 3.3 One finding, several spans

A finding has one span unless its operative words are not contiguous. These are the cases:

1. A lead-in and one item of a list (Example 2).
2. A page break with furniture inside the provision (Example 3).
3. A value that another passage supplies (section 5).
4. An amendment that changes part of a provision (6.2).
5. A footnote that changes the operative text. A DOCX footnote sits at the end of the text and carries no marker back to its place (`ParserContract.md` 12.1), so this is rare.

The spans of one finding run in text order, never overlap and never touch. Two spans with nothing but separators between them are one span. Use one span wherever one slice will do. A core v2.0 finding holds a single span, so how a multi-span finding is grouped and scored is an open item (section 9).

Example 2. A list whose lead-in and last item belong to one label:

```text
15.1 A dispute shall be taken through these steps in order:
(a) talks between the managing directors, for 20 days;
(b) mediation, if the talks fail; and
(c) arbitration before a sole arbitrator, if the mediation fails.
```

- `in.dispute_escalation`: one span, from "A dispute" to "if the talks fail". The typed `(a)` and `(b)` stay inside it. The closing "; and" is out.
- `in.arbitration`: two spans, "A dispute shall be taken through these steps in order:" and "arbitration before a sole arbitrator, if the mediation fails." Items (a) and (b) sit between them and do not concern arbitration.

Example 3. A provision split by a page break. `Page 3 of 9` and `SERVICES AGREEMENT` are a footer and a header, so they are in `decorations`:

```text
8.5 If the Buyer ends this Agreement in its first year, it shall pay the
Supplier a fee of ₹2,00,000 and
Page 3 of 9
SERVICES AGREEMENT
the fees already due.
```

- `cuad.liquidated_damages`: one finding, two spans. The first runs from "If the Buyer" to "₹2,00,000 and" and holds the line break. The second is "the fees already due." Neither touches the furniture.

### 3.4 Overlap between labels

Labels are independent. Two labels may share a span in whole or in part. A label takes the span the answer test gives it, whatever another label takes. The spans of one label never overlap in a document: if two spans of one label share words, they are one finding.

| Pair | Where they meet | What to do |
|---|---|---|
| `in.arbitration`, `in.seat_venue` | One sentence agrees to arbitrate and names the place | Both take the sentence. In separate sentences, each takes its own |
| `in.arbitration`, `in.dispute_escalation` | Talks first, then arbitration | Each takes its own sentence (Example 4) |
| `in.forum_selection`, `cuad.governing_law` | One sentence picks law and courts | Both take the sentence (Example 5) |
| `cuad.cap_on_liability`, `cuad.uncapped_liability` | A cap with a carve-out | Each takes its own sentence (Example 6) |
| `cuad.liquidated_damages`, `cuad.cap_on_liability` | A fixed sum that is also the sole, capped remedy | Both take the sentence |

Example 4:

```text
11.1 The parties shall first refer a dispute to their senior managers, who have 15 days to settle it. A dispute not settled in that time shall be referred to arbitration.
```

- `in.dispute_escalation`: "The parties shall first refer a dispute to their senior managers, who have 15 days to settle it."
- `in.arbitration`: "A dispute not settled in that time shall be referred to arbitration."

Example 5:

```text
16.1 This Agreement is governed by the laws of India, and the courts at Delhi have exclusive jurisdiction over any dispute under it.
```

- `cuad.governing_law` and `in.forum_selection` both take the whole sentence, because its two halves share a subject. If the halves were two sentences, each label would take its own.

Example 6:

```text
13.1 The Supplier's total liability under this Agreement shall not exceed the fees paid in the 12 months before the claim. This limit does not apply to liability for fraud or for death caused by negligence.
```

- `cuad.cap_on_liability`: the first sentence.
- `cuad.uncapped_liability`: "This limit does not apply to liability for fraud or for death caused by negligence."

### 3.5 Multiple occurrences

Annotate every occurrence. Each provision is its own finding, even when two are alike, such as a clause and a schedule row that repeats it. The state is `present` once, whatever the number of findings.

Two sentences of one label are two findings when they differ in payer, trigger or party, and one finding when the second only completes the first. A sentence that only points to the provision is not an occurrence (5.1).

Example 7:

```text
8.6 If the Buyer ends this Agreement in its first year, it shall pay the Supplier a fee of ₹2,00,000. If the Supplier delivers late, it shall pay ₹5,000 for each day of delay.
```

- `cuad.liquidated_damages`: two findings. Their payers and triggers differ. One span each: "If the Buyer ends this Agreement in its first year, it shall pay the Supplier a fee of ₹2,00,000." and "If the Supplier delivers late, it shall pay ₹5,000 for each day of delay."

### 3.6 What never goes in a span

- **A Word list label.** The label of a numbered Word paragraph (`list_label` in the block locator) is not in `source_text`, so no span can hold it. The annotation tool shows it beside the block. Use it to read the clause number and to follow cross-references ("see clause 12.3"), and start the span at the first character of the text. A clause with its number only in the locator is annotated like any other. Only the offsets differ (section 4).
- **Decorations.** No span overlaps a range in `decorations`, the header and footer blocks. A provision that crosses a page break is split around the furniture (Example 3). Footnotes are not decorations.
- **Typed numbers, headings and end white space** are out under 3.1.

## 4. Offsets

- Offsets are Unicode code points into `source_text` as parsed at `parser_version` 1.1.0. They are zero-based, and `end` is exclusive: `source_text[start:end]` is the span text.
- They are not bytes and not UTF-16 units. A browser counts UTF-16 units, so a character outside the Basic Multilingual Plane, such as an emoji, is one code point and two units there. The annotation tool converts. Do not convert by hand.
- Never find a span by searching the text. Read the offsets from the selection. Never normalise the text.
- Record the `text_sha256` of the parse you annotated. The same hash is the same text. A minor or patch release never moves `source_text` (`ParserContract.md` 2.1), so a 1.1.x or 1.2.0 parse of the file has the same hash and offsets. A major release may move it, and the hash tells you.
- Offsets belong to one file in one format. A PDF and a DOCX of the same contract give different offsets.

Worked calculation. The text has two blocks, and the second holds the rupee sign U+20B9, one code point (3 UTF-8 bytes, 1 UTF-16 unit):

```text
5. Fees
5.1 The Client shall pay ₹50,000 within 30 days. Any dispute shall be referred to arbitration.
```

The span is the second sentence, "Any dispute shall be referred to arbitration."

1. Block 1, `5. Fees`, has 7 code points. It runs from 0 to 7. The separator `\n` is at offset 7.
2. Block 2 starts at 8.
3. Count the code points of block 2 before the span: `5.1 ` is 4, `The Client shall pay ` is 21, `₹50,000` is 7 (the sign counts as 1), and ` within 30 days. ` is 17. The prefix is 4 + 21 + 7 + 17 = 49.
4. `start` = 8 + 49 = 57.
5. The span text has 45 code points, so `end` = 57 + 45 = 102.
6. Check: `source_text[57:102]` equals the span text, and 102 is also the length of `source_text`.

A byte count puts the span at 59, because the rupee sign takes 3 bytes. A UTF-16 count gives 57, because the sign is one unit.

The same clause in a Word file. The paragraph numbers `5.` and `5.1` sit in the locators, so the text is `Fees` (4 code points, 0 to 4), then `\n`, then block 2 from 5. Its prefix is `The Client shall pay ₹50,000 within 30 days. `, which is 45. The span is 50 to 95. That is 7 less than in the typed text, the length of `5. ` and `5.1 `.

## 5. Following a provision to other text

A sentence can point to another passage. Follow the pointer only when the passage supplies a value the label cannot be read without: an amount, a period, a territory, a place or a payer. Annotate that passage as a further span of the same finding. Do not follow a pointer that only sets priority or names an exception ("subject to clause 14", "except under clause 15"). A pointer to something outside the document, such as another agreement, a statute or an institution's rules, is not followed either.

### 5.1 Cross-references

A sentence that only points to a provision names it in passing, so it carries no label. The provision it points to carries the label (Example 1, clause 7.3). When the pointer is the only text on the point, ask whether the pointer answers the fixed question. "Disputes shall be arbitrated under Annexure C" answers `in.arbitration` and is `present`. "The seat shall be as stated in Annexure C" does not answer `in.seat_venue`. If Annexure C is not in the text, the label is `unassessable` (6.3).

### 5.2 Schedules

Text in a schedule is annotated like any clause. A table row is annotated by its cells. In a DOCX each cell is a block, and `\n` sits between blocks. A schedule row that repeats a clause is a further occurrence (3.5). A schedule row that supplies the value a clause points to is a further span of that clause's finding.

Example 8:

```text
13.2 The Supplier's liability under this Agreement is limited to the amount in Schedule 2.
SCHEDULE 2
Liability limit
₹10,00,000
```

- `cuad.cap_on_liability`: one finding, two spans. The first is the clause 13.2 sentence. The second is "Liability limit\n₹10,00,000", the two cells. The amount is a value the first span needs.

### 5.3 Definitions

A definition is annotated only when it supplies a value in the sense above. A definitions list is otherwise not annotated. A defined term's span starts at its opening quote and ends at its full stop.

Example 9:

```text
1.4 "Liability Cap" means ₹5,00,000.
13.1 The Supplier's liability under this Agreement shall not exceed the Liability Cap.
```

- `cuad.cap_on_liability`: one finding, two spans. The first is "The Supplier's liability under this Agreement shall not exceed the Liability Cap." The second runs from the opening quote to the full stop: `"Liability Cap" means ₹5,00,000.` The typed number `1.4` is out of it.

## 6. Hard cases

### 6.1 Negation

A sentence that denies a provision is about the category it denies, so annotate it. State `present`, cut the span as usual, and set the attribute `negated` to true (proposed key). Where the set has a label for the opposite, use that label and leave `negated` off. "Liability is not limited" is `cuad.uncapped_liability`, not a negated cap.

Example 10:

```text
10.3 Nothing in this Agreement restricts either party from competing with the other.
```

- `cuad.non_compete`: the sentence, `present`, with `negated` true. Tanishq decides how the evaluation scores negated findings. The flag keeps them apart.

### 6.2 Amended provisions

Annotate the text that is in force according to the document's own words. A clause the document says is replaced or deleted gets no span. The replacing text does. When an amendment changes only part of a provision, such as an amount or a period, the original clause stays a span and the amendment sentence is a further span of the same finding.

Formatting is not in `source_text`. A struck-through clause reads like any other, so the tool cannot show it. Annotate the text as written and flag the clause for adjudication (section 7).

Example 11:

```text
12.1 All disputes shall be settled by the courts at Mumbai.
AMENDMENT 1. Clause 12.1 is replaced with: "All disputes shall be settled by the courts at Pune."
```

- `in.forum_selection`: "All disputes shall be settled by the courts at Pune." The span leaves out the quote marks and the lead-in. Clause 12.1 gets no span.

### 6.3 Missing clauses

| Situation | State |
|---|---|
| The whole text is readable and no sentence passes the label's test | `absent` |
| The label's answer lives only in text that is not in the file (an annexure that is not attached) | `unassessable` |
| Part of the text is missing or unreadable (6.4) | `unassessable`, unless a span makes the label `present` |

Read the whole text before you give `absent`. A keyword search finds words and not provisions.

### 6.4 Unreadable text

The parser cannot read some content, and the annotator may meet more. Signs:

- From the parser: `coverage.partial` is true, or a warning is `PARTIALLY_SCANNED_PDF`, `UNMAPPED_GLYPHS`, `EMBEDDED_OBJECT` or `UNSUPPORTED_DOCX_FEATURE`. A damaged glyph shows in the text as `(cid:` and a number.
- From the reading: text that reads as nonsense (a wrong font map gives plausible wrong letters and no warning, `ParserContract.md` 12.2), blacked-out text, and a gap in page or clause numbers (page 4 of 9, then page 6).

For each sign, open the original file at the place and look:

- It holds no provisions (a blank page, signatures, a stamp). It changes nothing.
- It holds provisions that `source_text` lacks, or it cannot be read. Every label with no span is `unassessable`, because a provision there cannot become a span. The core follows the same rule: when `partial` is true, report "not checked" and never "not found".
- One sentence is damaged. If the readable words still answer the fixed question, annotate it. If not, the labels that sentence could carry are `unassessable`.

The state applies to the document. A label with a span elsewhere stays `present`.

Example 12:

```text
17.2 Any dispute shall be referred to (cid:65)(cid:66)(cid:67) in Pune.
```

- The hidden word could be arbitration, a tribunal or a court. With no other span, `in.arbitration` and `in.forum_selection` are `unassessable`. Neither is `absent`.

## 7. Disagreement resolution

Ten documents are annotated by both annotators, independently. Neither sees the other's labels or any model prediction first.

1. Take the agreement figures from the original labels before any discussion: presence agreement, Cohen's kappa where defined, and span-level agreement (plan v1.1 section 4.3).
2. Discuss every state mismatch, every span with no overlapping partner, and every pair whose edges differ by a sentence or more.
3. Keep both original annotations unchanged. Record the joint decision as a separate adjudicated annotation, with a one-line reason and the section of this file it rests on.
4. A mismatch that no rule settles is a gap in the rules. Add the rule to the next version. Documents annotated under an older version are checked against the new rule and take the new `guideline_version`.
5. A mismatch that turns on a legal reading goes to the faculty review list as a written question. The annotation follows the words (section 1). The question stays unresolved until faculty answer.
6. Annotators may read held-out documents. They must not use model errors from those documents to change a rule or the system.

## 8. Ceiling counts (part 2-0A)

Part 2-0A also measures four parser ceilings on contracts 001 to 025 (`Phases.md`, open ceilings; `ParserContract.md` 12.3 and 12.6). The counts need the contract files, and none is in `data/` yet. **Nothing is counted.**

**Input.** Contracts 001 to 025 as files in one folder under `data/`, which Git ignores, parsed at 1.1.0. If fewer than 25 arrive, count those and report how many.

**The four counts.** Each is a number of files. A file counts once per ceiling, however many places it has.

| Ceiling | Files in scope | A file counts when | Record |
|---|---|---|---|
| Athens-style list (12.6) | All | A numbered list inside a section takes the section's numbers, so the tree misses a section or holds a false one | The list's numbering style (typed numbers, a heading word such as `Section 5`, or a Word list), the missed labels and the false labels |
| Level (12.6) | PDFs, and files with a typed list | A numeral list follows a letter list, and the tree reads its first numeral as the next letter | The labels involved |
| Number format (12.6) | DOCX | Letters and numerals share one Word level in different lists, and the tree reads one list as the other | The labels involved |
| Fused paragraphs (12.3) | PDF | A page body holds two or more paragraphs in one block | The pages affected, per file and in total |

**Procedure.** For each file:

1. Parse it with the existing command in its default form, which prints no contract text: `python -m app.scripts.parse_file FILE`. The output has node labels, kinds, levels, offsets, block locators, boxes and warnings.
2. List the level 1 section labels in order. A gap, a repeat or a label out of order is a candidate for the Athens count.
3. List each node that is the next sibling in a letter run and whose label can be a letter or a numeral: `(i)`, `(v)`, `(x)`, `(c)`, `(d)`, `(l)`, `(m)`. With no `list_level` in its locator it is a candidate for the level count. With one it is a candidate for the number format count.
4. For a PDF, list each page whose body is one block, and each block whose box covers more than half the page height. These are candidates for the fused paragraph count.
5. Open each candidate in the original file, at the page or paragraph its locator names, and read it. Only a confirmed candidate counts. The lists narrow the reading, and a defect seen while reading counts too.
6. Name the cause. A wrong tree from another cause in 12.6 (a contents page read as clauses, a short all-capitals line that closes nodes, a list that opens above 1) counts for none of the four. Log it with its 12.6 row.

**Script.** Steps 1 to 4 are mechanical, and doing them by eye over 25 files invites mistakes. One throwaway script would run them over the folder and print, per file: the file name, the warning codes, the level 1 labels with gaps and repeats marked, the nodes of step 3 with their locators and offsets, and the pages of step 4. It reads files and prints labels, numbers and offsets. It prints no contract text and writes nothing. It stays outside the repository because it serves this one count. **It is not written.** Aryan approves it first.

**Threshold.** A ceiling gets a fix part when it counts in 3 or more files, which is one file in eight of the set. With 0 to 2 files it stays a documented ceiling with its count recorded. The threshold is set before any count and does not move afterwards.

**What a fix part does.** Each fix changes nodes or blocks and no character of `source_text`, so every annotated offset stays valid. It ships as a minor release (`ParserContract.md` 2.1). A fused paragraph fix lands before 3-D, which builds its display units from the blocks.

**Where the results go.** The counts go in the BuildLog (file ids and labels only, no text), in the open-ceilings table of `Phases.md`, and in the matching rows of `ParserContract.md` 12.3 and 12.6.

## 9. Open items

For Tanishq, with the 2-0B record questions:

1. The fixed question for each CUAD label, and confirmation of `cuad.uncapped_liability` and `cuad.governing_law`.
2. The record keys this file proposes: `designation` with the values `seat`, `venue` and `ambiguous`, and `negated`. Also the state names, the adjudication status values, and whether the record groups the spans of one finding. A core v2.0 `ClauseFinding` holds one span, so the evaluation must say how it scores a finding with several.

For the pilot:

3. Stamp certificate pages. The text of a stamp certificate or franking endorsement at the front of a contract addresses stamp duty. The proposal is to annotate it as `in.stamping_registration`, with the span recording that the text exists and nothing about payment or sufficiency. The pilot checks whether it floods the label.
