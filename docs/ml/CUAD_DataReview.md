# CUAD data review

## 2026-10-18: identical training text with conflicting annotations

**Status:** text identity and annotation differences verified; label adjudication
is pending. No dataset records, labels, or official split files were changed.

### Source identity

- Full dataset: `data/raw/cuad/CUAD_v1/CUAD_v1.json`.
- Hugging Face repository: `theatticusproject/cuad`.
- Hugging Face revision: `a3c393f5d103fd0c516374e4fdff676c8176dcb1`.
- Full-file SHA-256: `ed0b77d85bdf4014d7495800e8e4a70565b48ee6f8a2e5dca9cf8655dbf10eae`.
- Official split repository: `The-Atticus-Project/cuad`.
- Official split revision: `67faa0e6023b04fcaae6cc09497ab00e5d63a2a2`.
- Verification script: `ml/scripts/audit_cuad_questions.py`.
- Dataset attribution and license: [CUAD README](../../data/raw/cuad/README.md).

### The duplicate pair

Both source titles belong to the official training split:

- **A:** `ADUROBIOTECH,INC_06_02_2020-EX-10.7-CONSULTING AGREEMENT`
- **B:** `ADUROBIOTECH,INC_06_02_2020-EX-10.7-CONSULTING AGREEMENT(1)`

Each record has one paragraph containing exactly the same 12,020 Unicode code
points. The SHA-256 of the UTF-8 encoding of that context is:

```text
23255988c8f39e0b67d7ff8a2b316a17c3bf4cc0557141d6a7e6e9cc7d770ad3
```

This is a hash of the decoded CUAD context, not the JSON file. It uses no
whitespace or Unicode normalization. The source context belongs to neither a
parser output nor a transformed training example at this stage.

Each copy has 41 original category questions. Their question text, answer state,
and answer-span multisets agree for 39 categories. Two categories differ.

### Annotation differences

The table describes the source annotations; it does not adjudicate which label
is correct. An empty answer list is not proof that a clause is absent.

| CUAD category | Copy A | Copy B | Annotated span in B |
|---|---|---|---|
| Anti-Assignment | 0 spans; `is_impossible=true` | 1 span; `is_impossible=false` | `[11550, 11603)` |
| Exclusivity | 0 spans; `is_impossible=true` | 1 span; `is_impossible=false` | `[8854, 9244)` |

Offsets refer to `paragraphs[0].context` in the original CUAD JSON. They count
Unicode code points; starts are inclusive and ends are exclusive. Both passages
exist at these same positions in both copies.

**Anti-Assignment:** the 53-character span reads:

> This Agreement shall not be assignable by Consultant.

The sentence exists in both copies, but only B marks it as an answer. This is a
difference between annotation records, not a missing passage or an offset error.

**Exclusivity:** the 390-character span concerns consulting work or other
engagements that would materially conflict with the agreement or prevent
compliance with its terms. Only B marks it as an answer. Determining whether that
passage meets the CUAD category definition requires annotation review; text
identity alone cannot decide the label.

### Handling rule for subsequent data preparation

1. Preserve the official benchmark files and their original annotations.
2. Treat A and B as one exact-text group when assigning derived training,
   validation, or calibration splits. They must not be assigned independently.
3. Retain both source titles as provenance. Do not silently choose a preferred
   copy or combine its positive labels with the other copy's labels.
4. Until adjudication, hold out both copies' examples for the two disputed
   categories from supervised loss and scored evaluation in our derived clean
   datasets. This covers four original question records, not the full documents.
   This is a preparation rule; filtering has not yet been implemented.
5. Deduplication of the 39 agreeing categories should preserve every distinct
   answer occurrence and the original source identities. That transformation
   has not yet been implemented either.
6. Record any later label decision with the reviewer, date, guideline rationale,
   and exact retained spans. Keep derived decisions separate from source data.

The exact-text group prevents this known pair from crossing derived splits.
Near-duplicate and related-contract checks remain a separate preparation task.

### Question-format finding

The official training file contains 22,450 records representing 16,728 original
questions: 11,270 records have no answers and 11,180 have one answer. Questions
with multiple answers are expanded into separate training records.

The official test file retains the original question grouping: 4,182 questions,
including 482 with multiple answers. Answer order sometimes differs from the
full source. The audit compares exact `(answer_start, text)` pairs with their
multiplicities, allowing reordering without losing repeated occurrences.

The completed audit found zero source-to-split answer differences and verified
all 13,823 full-source spans, 11,180 training spans, and 2,643 test spans. The
pending duplicate-label review is separate from those successful integrity
checks.
