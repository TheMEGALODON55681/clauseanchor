r"""Find text-similarity candidates for manual CUAD family review.

Run: python ml/scripts/review_cuad_similarity.py
Outputs (ignored): data/processed/cuad/similarity_candidates.json and
data/processed/cuad/similarity_review.md. No network or new dependencies.

Compare distinct five-word phrases after casefolding and Unicode \w+ tokenization
for comparison only. Original text and offsets are never changed. Phrases do not
cross paragraph boundaries. Global token IDs make tuple comparison exact; no
probabilistic phrase hashing, sampling, or model embeddings are used.

Screen every pair of distinct exact-text groups. Flag Jaccard >= 0.80, or
containment >= 0.90 with at least 200 shared distinct phrases. These are fixed
screening heuristics, not learned thresholds or proof of shared template origin.
Reordered phrases, common boilerplate, and parent/attachment relationships can
produce candidates. Paraphrases and other families can still be missed.

No source records, annotations, benchmark memberships, or exact groups are
modified. Candidate pairs are not automatically merged into training groups.
"""

from collections import Counter
import json
from pathlib import Path
import re

from audit_cuad_questions import contexts, require
from build_cuad_inventory import build_groups, load_sources


SCREEN_VERSION = "1.0.0"
PHRASE_WORDS = 5
MIN_CONTAINMENT_SHARED = 200


def phrase_set(text_sequence, vocabulary):
    phrases = set()
    words_total = 0
    for text in text_sequence:
        words = [vocabulary.setdefault(token, len(vocabulary))
                 for token in re.findall(r"\w+", text.casefold())]
        words_total += len(words)
        phrases.update(tuple(words[i:i + PHRASE_WORDS])
                       for i in range(len(words) - PHRASE_WORDS + 1))
    return phrases, words_total


def screen_pair(left, right):
    smaller = min(len(left), len(right))
    if smaller == 0:
        return None
    shared = len(left & right)
    union = len(left) + len(right) - shared
    # Integer comparisons preserve the thresholds at their exact boundaries.
    jaccard_match = 5 * shared >= 4 * union
    containment_match = shared >= MIN_CONTAINMENT_SHARED and 10 * shared >= 9 * smaller
    if not (jaccard_match or containment_match):
        return None
    return {
        "shared_distinct_phrases": shared,
        "union_distinct_phrases": union,
        "smaller_distinct_phrase_count": smaller,
        "jaccard": round(shared / union, 6),
        "containment": round(shared / smaller, 6),
        "triggers": (["jaccard_at_least_0.80"] if jaccard_match else [])
                    + (["containment_at_least_0.90_with_200_shared"] if containment_match else []),
    }


def find_candidates(groups, full, progress=None):
    vocabulary, comparison_sets, details = {}, [], []
    for group in groups:
        titles = [document["title"] for document in group["source_documents"]]
        phrases, word_count = phrase_set(contexts(full[titles[0]]), vocabulary)
        comparison_sets.append(phrases)
        details.append({
            "group_id": group["group_id"],
            "official_split": group["official_split"],
            "source_titles": titles,
            "paragraphs": group["paragraphs"],
            "comparison_word_count": word_count,
            "distinct_phrase_count": len(phrases),
        })
    if progress:
        progress("Comparison phrases ready; screening all group pairs...")
    candidates = []
    examined = 0
    for i, left in enumerate(comparison_sets):
        for j in range(i + 1, len(comparison_sets)):
            examined += 1
            scores = screen_pair(left, comparison_sets[j])
            if scores is None:
                continue
            candidates.append({
                "left": details[i],
                "right": details[j],
                "crosses_official_split": details[i]["official_split"] != details[j]["official_split"],
                "review_status": "pending_manual_review",
                **scores,
            })
        if progress and (i + 1) % 100 == 0:
            progress(f"Screened pairs starting from {i + 1}/{len(groups)} groups...")
    # Review benchmark-boundary candidates first. IDs/order are reproducible.
    candidates.sort(key=lambda pair: (
        not pair["crosses_official_split"], -pair["jaccard"], -pair["containment"],
        pair["left"]["group_id"], pair["right"]["group_id"],
    ))
    for index, pair in enumerate(candidates, start=1):
        pair["review_id"] = f"similarity-{index:03d}"
    return candidates, examined, [d["group_id"] for d in details if d["distinct_phrase_count"] == 0]


def markdown_report(report):
    summary = report["summary"]
    lines = [
        "# CUAD similarity candidates", "",
        f"Screen version: {SCREEN_VERSION}. All candidates await manual review.", "",
        f"Compared {summary['exact_text_groups']} exact-text groups across "
        f"{summary['group_pairs_examined']:,} pairs; found {summary['candidate_pairs']} candidates.",
        f"Candidates crossing official train/test membership: {summary['cross_official_split_candidates']}.", "",
        "These are candidates, not confirmed duplicate or template families. No groups or official splits changed.", "",
        "## How to read the numbers", "",
        "Comparison uses distinct five-word phrases, ignoring case and punctuation only in the comparison view.",
        "Jaccard is shared phrases divided by all distinct phrases in either text.",
        "Containment is shared phrases divided by the smaller text's distinct phrase count.",
        "A candidate meets Jaccard >= 0.80, or containment >= 0.90 with at least 200 shared phrases.",
        "These screening thresholds do not establish a complete family/leakage audit.", "",
        "## Review procedure", "",
        "Read both original contexts and compare unique sections, parties, dates, amendments, and attachments.",
        "Distinguish a related document family from generic shared boilerplate. Do not decide from titles alone.",
        "Record a reasoned decision separately, retaining source titles, group IDs, and any exact evidence ranges.",
        "Do not edit this generated report: differing existing outputs are preserved rather than overwritten.",
        "Confirmed training families will inform later internal splits. Preserve official benchmark membership;",
        "report any confirmed cross-benchmark overlap separately, including a sensitivity analysis when appropriate.",
        "The earlier exact-duplicate annotation disagreements remain pending and are not resolved by similarity.",
        "Paraphrases, shorter shared passages, and other related templates may be missed by this screen.", "",
    ]
    for pair in report["candidates"]:
        lines += [f"## {pair['review_id']}", "",
                  f"Official splits: {pair['left']['official_split']} / {pair['right']['official_split']}.",
                  f"Jaccard: {pair['jaccard']:.6f}; containment: {pair['containment']:.6f}; "
                  f"shared distinct phrases: {pair['shared_distinct_phrases']:,}.", ""]
        for side in ("left", "right"):
            item = pair[side]
            lines += [f"**{side.capitalize()} group:** `{item['group_id']}`", ""]
            lines.extend(f"- `{title}`" for title in item["source_titles"])
            lines += [""]
        lines += ["Decision: pending manual review.", ""]
    return "\n".join(lines) + "\n"


def save_outputs(outputs):
    for path, payload in outputs.items():
        if path.exists():
            require(path.read_bytes() == payload, f"Existing report differs; it was not replaced: {path}")
    created = 0
    for path, payload in outputs.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(payload)
            created += 1
    return created


def main():
    repo_root = Path(__file__).resolve().parents[2]
    full, train, test, provenance = load_sources(repo_root)
    groups = build_groups(full, train, test)
    del train, test
    print("Pinned source, spans, and official memberships: verified", flush=True)
    candidates, examined, empty = find_candidates(groups, full, progress=lambda text: print(text, flush=True))
    split_counts = Counter("cross_official_split" if p["crosses_official_split"]
                           else p["left"]["official_split"] for p in candidates)
    summary = {
        "source_documents": len(full),
        "exact_text_groups": len(groups),
        "group_pairs_examined": examined,
        "groups_without_comparison_phrases": len(empty),
        "candidate_pairs": len(candidates),
        "within_train_candidates": split_counts["train"],
        "within_test_candidates": split_counts["test"],
        "cross_official_split_candidates": split_counts["cross_official_split"],
    }
    report = {
        "screen_version": SCREEN_VERSION,
        "provenance": provenance,
        "method": {
            "tokens": "Unicode regex \\w+ on casefolded comparison text; original contexts unchanged",
            "phrases": "Distinct contiguous five-token tuples; never cross paragraph boundaries",
            "comparison": "All pairs of distinct exact-text groups; exact tuple-set intersections",
            "jaccard_threshold": "4/5",
            "containment_threshold": "9/10",
            "containment_minimum_shared_phrases": MIN_CONTAINMENT_SHARED,
            "automatic_family_assignment": False,
            "limitation": "Candidate screen only; generic boilerplate may match and other related families may be missed.",
        },
        "summary": summary,
        "groups_without_comparison_phrases": empty,
        "candidates": candidates,
    }
    out_dir = (repo_root / "data/processed/cuad").resolve()
    require(out_dir.is_relative_to(repo_root / "data"), "Output must remain inside data/.")
    outputs = {
        out_dir / "similarity_candidates.json": (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        out_dir / "similarity_review.md": markdown_report(report).encode("utf-8"),
    }
    created = save_outputs(outputs)
    print(f"Source documents: {len(full)}")
    print(f"Exact-text groups compared: {len(groups)}")
    print(f"Group pairs examined: {examined:,}")
    print(f"Groups without comparison phrases: {len(empty)}")
    print(f"Similarity candidate pairs: {len(candidates)}")
    print(f"Within official training: {split_counts['train']}")
    print(f"Within official test: {split_counts['test']}")
    print(f"Across official train/test: {split_counts['cross_official_split']}")
    print(f"Created {created} report files." if created else "Existing reports match; no files changed.")
    print("Review report: data/processed/cuad/similarity_review.md")
    print("PASS: similarity screen completed; source data and official splits unchanged.")
    print("REVIEW REQUIRED: candidates are not confirmed families; no groups merged or internal splits assigned.")


if __name__ == "__main__":
    main()
