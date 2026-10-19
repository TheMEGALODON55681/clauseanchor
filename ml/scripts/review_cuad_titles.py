r"""Screen CUAD source titles for further related-document review candidates.

Run: python ml/scripts/review_cuad_titles.py
Requires the verified official data, saved similarity report and family manifest.
No new dependencies, downloads, source edits, family decisions or splits.
Outputs (ignored by Git): data/processed/cuad/title_candidates.json and
data/processed/cuad/title_review.md. Differing existing reports are not replaced.

The source title is a dataset filename, not authoritative SEC metadata. Extract
issuer text using the two dated filename formats or an explicit ' - ' separator.
Only the comparison issuer key is NFKC-normalized, casefolded and reduced to
alphanumeric characters. Original titles, contexts and offsets remain unchanged.
Do not strip company suffixes or guess aliases for renamed companies.
Comparison exhibit keys collapse whitespace and case; numeric EX- segments
also drop leading zeroes, so EX-10.02 and EX-10.2 produce the same hint.

Flag every pair of distinct exact-text groups sharing an extracted issuer key.
Date/exhibit matches prioritize review; they are not proof of the same filing
or agreement. Collapse title-pair repetitions into one group pair. Show existing
confirmed family membership separately, including transitive relationships.
Expose unparsed or incomplete titles explicitly. This complements the lexical
screen; it does not establish that all related contracts have been found.
"""

from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
import json
from pathlib import Path
import re
import unicodedata

from audit_cuad_questions import require
from build_cuad_inventory import build_groups, load_sources
from check_cuad_families import (
    REPORT_PATH, canonical_sha256, member_record, read_json, validate_manifest,
)
from review_cuad_similarity import save_outputs


SCREEN_VERSION = "1.0.0"
DATED_TITLE = re.compile(
    r"^(?P<issuer>.+?)_(?:(?P<compact>[0-9]{8})_|"
    r"(?P<separated>[0-9]{2}_[0-9]{2}_[0-9]{4})-)(?P<rest>.*)$"
)


def issuer_key(text):
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def exhibit_key(label):
    key = " ".join(label.casefold().split())
    numeric = re.fullmatch(r"ex-([0-9]+(?:\.[0-9]+)*)", key)
    if numeric:
        return "ex-" + ".".join(str(int(part)) for part in numeric[1].split("."))
    return key


def parse_title(title):
    result = {
        "source_title": title, "format": "unparsed", "issuer_text": None,
        "issuer_key": None, "filing_date_from_title": None,
        "exhibit_label_from_title": None, "exhibit_key": None, "issues": [],
    }
    dated = DATED_TITLE.fullmatch(title)
    if dated:
        result["format"] = "dated_compact" if dated["compact"] else "dated_separated"
        result["issuer_text"] = dated["issuer"]
        raw_date = dated["compact"] or dated["separated"]
        try:
            result["filing_date_from_title"] = datetime.strptime(
                raw_date, "%Y%m%d" if dated["compact"] else "%m_%d_%Y"
            ).date().isoformat()
        except ValueError:
            result["issues"].append("invalid_title_date")
        rest = dated["rest"]
        label = None
        if dated["compact"]:
            metadata = re.match(
                r"^.+?_(?P<first>EX[^_]+)_[0-9]+_(?P<second>EX[^_]+)(?:_|$)", rest
            )
            if metadata:
                if exhibit_key(metadata["first"]) == exhibit_key(metadata["second"]):
                    label = metadata["first"]
                else:
                    result["issues"].append("conflicting_title_exhibit_labels")
            else:
                result["issues"].append("unparsed_title_exhibit")
        else:
            metadata = re.match(r"^(EX(?:1A)?-[^-]+)-", rest)
            if metadata:
                label = metadata[1]
            else:
                result["issues"].append("unparsed_title_exhibit")
        if label is not None:
            result["exhibit_label_from_title"] = label
            result["exhibit_key"] = exhibit_key(label)
    elif " - " in title:
        issuer, description = title.split(" - ", 1)
        if issuer.strip() and description.strip():
            result["format"] = "explicit_issuer_description"
            result["issuer_text"] = issuer.strip()
        else:
            result["issues"].append("unparsed_issuer")
    else:
        result["issues"].append("unparsed_issuer")
    if result["issuer_text"] is not None:
        key = issuer_key(result["issuer_text"])
        if key:
            result["issuer_key"] = key
        else:
            result["issues"].append("empty_comparison_issuer")
    return result


def title_signals(a, b):
    require(a["issuer_key"] and a["issuer_key"] == b["issuer_key"], "Issuer keys must match.")
    signals = ["matching_issuer_key"]
    if a["filing_date_from_title"] and a["filing_date_from_title"] == b["filing_date_from_title"]:
        signals.append("matching_title_date")
        if a["exhibit_key"] and a["exhibit_key"] == b["exhibit_key"]:
            signals.append("matching_title_date_and_exhibit")
    return signals


def screen_titles(groups, manifest):
    by_id = {g["group_id"]: g for g in groups}
    buckets = defaultdict(list)
    titles = []
    for group in groups:
        for doc in group["source_documents"]:
            metadata = {"group_id": group["group_id"], "official_split": group["official_split"],
                        **parse_title(doc["title"])}
            titles.append(metadata)
            if metadata["issuer_key"]:
                buckets[metadata["issuer_key"]].append(metadata)
    confirmed_family = {
        member["group_id"]: family["family_id"]
        for family in manifest["families"] for member in family["members"]
    }
    pairs = {}
    exact_pairs = 0
    for key in sorted(buckets):
        for a, b in combinations(sorted(buckets[key], key=lambda m: m["source_title"]), 2):
            if a["group_id"] == b["group_id"]:
                exact_pairs += 1
                continue
            if a["group_id"] > b["group_id"]:
                a, b = b, a
            edge = (a["group_id"], b["group_id"])
            if edge not in pairs:
                existing = confirmed_family.get(edge[0])
                if existing != confirmed_family.get(edge[1]):
                    existing = None
                pairs[edge] = {
                    "left": member_record(by_id[edge[0]]),
                    "right": member_record(by_id[edge[1]]),
                    "crosses_official_split": a["official_split"] != b["official_split"],
                    "existing_family_id": existing,
                    "review_status": "already_in_reviewed_family" if existing else "pending_source_review",
                    "title_evidence": [],
                }
            pairs[edge]["title_evidence"].append({
                "left_source_title": a["source_title"], "right_source_title": b["source_title"],
                "issuer_key": key, "signals": title_signals(a, b),
            })
    candidates = list(pairs.values())
    for candidate in candidates:
        candidate["strongest_title_signal"] = max(
            (e["signals"] for e in candidate["title_evidence"]), key=len
        )[-1]
    strength = {"matching_title_date_and_exhibit": 0, "matching_title_date": 1, "matching_issuer_key": 2}
    candidates.sort(key=lambda c: (
        c["review_status"] != "pending_source_review", not c["crosses_official_split"],
        strength[c["strongest_title_signal"]], c["left"]["group_id"], c["right"]["group_id"],
    ))
    for index, candidate in enumerate(candidates, start=1):
        candidate["review_id"] = f"title-{index:03d}"
    titles.sort(key=lambda m: m["source_title"])
    pending = [c for c in candidates if c["review_status"] == "pending_source_review"]
    split_counts = Counter("cross" if c["crosses_official_split"] else c["left"]["official_split"]
                           for c in pending)
    summary = {
        "source_documents": len(titles), "exact_text_groups": len(groups),
        "titles_with_issuer_key": sum(m["issuer_key"] is not None for m in titles),
        "titles_without_issuer_key": sum(m["issuer_key"] is None for m in titles),
        "titles_with_date_and_exhibit": sum(bool(m["filing_date_from_title"] and m["exhibit_key"]) for m in titles),
        "titles_with_parse_issues": sum(bool(m["issues"]) for m in titles),
        "repeated_issuer_keys": sum(len(v) > 1 for v in buckets.values()),
        "same_exact_group_title_pairs_skipped": exact_pairs,
        "candidate_group_pairs": len(candidates),
        "already_in_reviewed_family": len(candidates) - len(pending),
        "pending_source_review": len(pending),
        "pending_cross_split_pairs": split_counts["cross"],
        "pending_training_only_pairs": split_counts["train"],
        "pending_test_only_pairs": split_counts["test"],
        "pending_matching_date_and_exhibit": sum(c["strongest_title_signal"] == "matching_title_date_and_exhibit" for c in pending),
    }
    return {"summary": summary, "titles": titles, "candidates": candidates}


def markdown_report(report):
    s = report["summary"]
    lines = [
        "# CUAD source-title review candidates", "",
        f"Title screen: {SCREEN_VERSION}; family manifest snapshot: {report['family_manifest_version']}.", "",
        "This report proposes source-review candidates. It makes no new family decisions.",
        "Company names, dates and exhibit labels here come from dataset titles, not verified SEC metadata.",
        "A shared company does not establish a shared agreement. Read the original contexts before deciding.", "",
        "## Coverage", "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in s.items())
    lines += ["", "## Interpretation and next review", "",
              "- Review pending cross-split pairs first, prioritizing matching date/exhibit hints.",
              "- Check agreement names, parties, referenced dates, amendment links and attachment relationships in the source text.",
              "- Record related, unrelated, or unresolved decisions with evidence separately; do not edit this generated report.",
              "- Existing reviewed-family status includes transitive membership, not only previously screened pair edges.",
              "- Multiple source-title pairs can support one group pair; exact-group self-pairs are skipped.",
              "- Missing dates/exhibits remain null. Issuer aliases and cross-issuer relationships may be missed.",
              "- No source text, annotation, official membership, family manifest or internal split is changed.", "",
              "## Titles requiring extraction review", ""]
    issues = [m for m in report["titles"] if m["issues"]]
    for m in issues:
        lines += [f"- `{m['source_title']}`: {', '.join(m['issues'])}."]
    if not issues:
        lines.append("No title parsing issues in this snapshot.")
    lines += ["", "## Candidate pairs", ""]
    metadata = {m["source_title"]: m for m in report["titles"]}
    for c in report["candidates"]:
        lines += [f"### {c['review_id']}", "",
                  f"Status: `{c['review_status']}`; splits: {c['left']['official_split']} / {c['right']['official_split']}.",
                  f"Strongest title signal: `{c['strongest_title_signal']}`.", ""]
        if c["existing_family_id"]:
            lines += [f"Existing reviewed family: `{c['existing_family_id']}`.", ""]
        for side in ("left", "right"):
            lines += [f"**{side.capitalize()} group:** `{c[side]['group_id']}`", ""]
            for title in c[side]["source_titles"]:
                m = metadata[title]
                lines.append(f"- `{title}`")
                lines.append(f"  Title date: {m['filing_date_from_title'] or 'unknown'}; "
                             f"exhibit: {m['exhibit_label_from_title'] or 'unknown'}.")
            lines.append("")
        lines += ["Source-review decision: pending." if c["review_status"] == "pending_source_review"
                  else "Relationship already covered by the pinned reviewed-family manifest.", ""]
    return "\n".join(lines) + "\n"


def main():
    repo = Path(__file__).resolve().parents[2]
    full, train, test, provenance = load_sources(repo)
    groups = build_groups(full, train, test)
    manifest = read_json(repo / "ml/configs/cuad_family_manifest.json")
    validate_manifest(manifest, read_json(repo / REPORT_PATH), groups, provenance)
    report = {
        "title_screen_version": SCREEN_VERSION, "provenance": provenance,
        "family_manifest_version": manifest["manifest_version"],
        "family_manifest_canonical_sha256": canonical_sha256(manifest),
        "method": {
            "issuer_key": "NFKC then casefold then retain Unicode alphanumeric characters",
            "pair_rule": "Distinct exact-text groups sharing an extracted issuer key",
            "priority_hints": ["matching_title_date_and_exhibit", "matching_title_date", "matching_issuer_key"],
            "normalization_scope": "Comparison metadata only; source text and offsets unchanged",
            "automatic_family_assignment": False,
            "limitation": "Titles are not authoritative filing metadata; aliases, renamed issuers and cross-issuer families may be missed.",
        },
        **screen_titles(groups, manifest),
    }
    output_dir = repo / "data/processed/cuad"
    outputs = {
        output_dir / "title_candidates.json": (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        output_dir / "title_review.md": markdown_report(report).encode("utf-8"),
    }
    created = save_outputs(outputs)
    s = report["summary"]
    print("Pinned source, spans, official memberships and reviewed-family manifest: verified")
    print(f"Source documents: {s['source_documents']}; exact-text groups: {s['exact_text_groups']}")
    print(f"Titles with issuer keys: {s['titles_with_issuer_key']}; without issuer keys: {s['titles_without_issuer_key']}")
    print(f"Titles with date and exhibit: {s['titles_with_date_and_exhibit']}; title parsing issues: {s['titles_with_parse_issues']}")
    print(f"Exact-group title pairs skipped: {s['same_exact_group_title_pairs_skipped']}")
    print(f"Title candidate group pairs: {s['candidate_group_pairs']}")
    print(f"Already in reviewed families: {s['already_in_reviewed_family']}")
    print(f"Pending source review: {s['pending_source_review']} "
          f"({s['pending_cross_split_pairs']} cross-split; {s['pending_training_only_pairs']} training-only; "
          f"{s['pending_test_only_pairs']} test-only)")
    print(f"Pending pairs with matching title date/exhibit: {s['pending_matching_date_and_exhibit']}")
    print(f"Created {created} report files." if created else "Existing reports match; no files changed.")
    print("Review report: data/processed/cuad/title_review.md")
    print("PASS: source-title screening completed; source data and family decisions unchanged.")
    print("REVIEW REQUIRED: title matches are candidates only; no exclusions or internal splits applied.")


if __name__ == "__main__":
    main()
