"""Check development fixtures, not the running application or a trained model.

The small interval reference below is a test oracle for Plan 1.1 section 10.7.
It is deliberately outside clauseanchor_core and is not an HTTP API or analyzer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from clauseanchor_core import from_dict, text_digest, validate_result
from clauseanchor_core.contract import Span, validate_span

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "scope"
SCOPE_NOTICE = (
    "This review checks the listed clause categories. Other provisions and "
    "interactions between clauses may need manual review. Unhighlighted text "
    "is not a safety assessment."
)
MANUAL_EXPLANATION = (
    "These passages have no accepted finding, or are only partly highlighted, "
    "for the selected categories. This does not establish whether they are "
    "harmless or harmful. Read them with the surrounding agreement."
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_keys(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names.split()),
            f"Unexpected fields in {label}.")


def read_json(path):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=unique_object)


def load_families(root=FIXTURES):
    manifest = read_json(root / "manifest.json")
    exact_keys(manifest, "fixture_format_version files", "manifest")
    require(manifest["fixture_format_version"] == "1.0", "Unknown fixture version.")
    expected_files = manifest["files"]
    actual_files = {p.name for p in root.iterdir() if p.is_file()} - {"manifest.json"}
    require(set(expected_files) == actual_files, "Manifest file set mismatch.")
    for name, digest in expected_files.items():
        relative = PurePosixPath(name)
        require(len(relative.parts) == 1 and relative.name == name and "\\" not in name
                and name not in (".", ".."), "Unsafe manifest path.")
        path = root / name
        require(not path.is_symlink(), "Fixture symlink is not allowed.")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                f"Fixture checksum mismatch: {name}")
    artifact_hash = hashlib.sha256((root / "artifact.json").read_bytes()).hexdigest()
    families = [read_json(root / name) for name in sorted(expected_files)
                if re.fullmatch(r"0[1-8]_[a-z_]+\.json", name)]
    require([f["family"] for f in families] == list(range(1, 9)),
            "Exactly eight ordered scenario families are required.")
    case_ids = set()
    for family in families:
        exact_keys(family, "fixture_format_version family title cases", "family")
        require(family["fixture_format_version"] == "1.0", "Unknown fixture version.")
        require(bool(family["cases"]), "Empty scenario family.")
        for case in family["cases"]:
            require(case["id"] not in case_ids, "Duplicate case ID.")
            case_ids.add(case["id"])
            result = case["core_result"]
            if result is not None:
                require(result["artifact_manifest_sha256"] == artifact_hash,
                        "Wrong fixture artifact identity.")
    return families


def paragraph_units(text):
    """Split on blank lines, retaining exact source boundaries within each unit."""
    ranges, start = [], 0
    for separator in re.finditer(r"\n[ \t]*\n", text):
        ranges.append((start, separator.start()))
        start = separator.end()
    ranges.append((start, len(text)))
    return [{"id": f"paragraph-{a}-{b}", "start": a, "end": b, "text": text[a:b]}
            for a, b in ranges if text[a:b].strip()]


def display_units(text, nodes):
    """Validate hierarchy; choose leaves once; preserve substantive gaps."""
    try:
        require(isinstance(nodes, list) and bool(nodes), "No parser structure.")
        index = {}
        for node in nodes:
            exact_keys(node, "id parent_id kind start end", "parser node")
            require(isinstance(node["id"], str) and node["id"] and
                    node["id"] not in index, "Duplicate or empty node ID.")
            a, b = node["start"], node["end"]
            require(type(a) is int and type(b) is int and 0 <= a < b <= len(text),
                    "Invalid parser range.")
            require(isinstance(node["kind"], str) and node["kind"], "Invalid node kind.")
            require(node["parent_id"] is None or isinstance(node["parent_id"], str),
                    "Invalid parent ID.")
            index[node["id"]] = node
        for node in nodes:
            seen, child = {node["id"]}, node
            while child["parent_id"] is not None:
                parent_id = child["parent_id"]
                require(parent_id in index and parent_id not in seen,
                        "Missing or cyclic parser parent.")
                seen.add(parent_id)
                parent = index[parent_id]
                require(parent["start"] <= child["start"] < child["end"] <= parent["end"],
                        "Child escapes parser parent.")
                child = parent
        parents = {n["parent_id"] for n in nodes}
        leaves = sorted((n for n in nodes if n["id"] not in parents),
                        key=lambda n: (n["start"], n["end"]))
        units, cursor = [], 0
        for leaf in leaves:
            a, b = leaf["start"], leaf["end"]
            require(a >= cursor, "Overlapping parser leaves.")
            if text[cursor:a].strip():
                units.append({"id": f"gap-{cursor}-{a}", "start": cursor,
                              "end": a, "text": text[cursor:a]})
            if text[a:b].strip():
                units.append({"id": leaf["id"], "start": a, "end": b, "text": text[a:b]})
            cursor = b
        if text[cursor:].strip():
            units.append({"id": f"gap-{cursor}-{len(text)}", "start": cursor,
                          "end": len(text), "text": text[cursor:]})
        return "parser_leaves_with_gaps", units
    except ValueError:
        return "paragraph_fallback", paragraph_units(text)


def validate_inputs(case):
    exact_keys(case, "id purpose document catalogue requested_category_ids parser job "
               "core_result anchors expected", "case")
    document = case["document"]
    exact_keys(document, "doc_id text text_sha256", "document")
    text = document["text"]
    require(isinstance(text, str) and bool(text), "Empty source text.")
    require(document["text_sha256"] == text_digest(text), "Source hash mismatch.")
    catalogue = case["catalogue"]
    exact_keys(catalogue, "version simulated categories", "catalogue")
    require(catalogue["simulated"] is True and catalogue["version"], "Fixture catalogue required.")
    support = {}
    for entry in catalogue["categories"]:
        exact_keys(entry, "category_id support_state", "catalogue entry")
        cid = entry["category_id"]
        require(isinstance(cid, str) and cid and cid not in support, "Bad catalogue category.")
        require(entry["support_state"] in ("supported", "proposed_unvalidated"),
                "Unknown catalogue support state.")
        support[cid] = entry["support_state"]
    requested = case["requested_category_ids"]
    require(isinstance(requested, list) and bool(requested) and
            len(requested) == len(set(requested)) and set(requested) <= set(support),
            "Requested category scope mismatch.")
    parser, job = case["parser"], case["job"]
    exact_keys(parser, "complete nodes unavailable_regions", "parser")
    exact_keys(job, "status unfinished_stages candidate_search_truncated boundary_coverage_complete", "job")
    for flag in (parser["complete"], job["candidate_search_truncated"], job["boundary_coverage_complete"]):
        require(type(flag) is bool, "Processing flags must be booleans.")
    require(job["status"] in ("completed", "partial", "cancelled"), "Unknown job status.")
    require(isinstance(job["unfinished_stages"], list) and
            all(isinstance(s, str) and s for s in job["unfinished_stages"]), "Bad unfinished stages.")
    require(isinstance(parser["unavailable_regions"], list), "Bad unavailable regions.")
    for region in parser["unavailable_regions"]:
        exact_keys(region, "locator reason", "unavailable region")
        require(all(isinstance(v, str) and v for v in region.values()), "Missing region description.")
    require(not parser["unavailable_regions"] or not parser["complete"],
            "Missing source regions contradict complete parsing.")
    raw = case["core_result"]
    if raw is None:
        require(job["status"] == "cancelled", "Only cancelled fixtures omit the core result.")
        result = None
    else:
        result = from_dict(raw)
        validate_result(result, text)
        require(result.doc_id == document["doc_id"], "Document ID mismatch.")
        require(result.mode == "stub", "Scope fixtures must remain in stub mode.")
        require([c.category_id for c in result.categories] == requested,
                "Core categories do not match requested order/scope.")
        incomplete = (not parser["complete"] or job["status"] != "completed" or
                      bool(job["unfinished_stages"]) or job["candidate_search_truncated"] or
                      not job["boundary_coverage_complete"])
        for category in result.categories:
            require(category.decision_confidence is None, "Fixture decision confidence must be null.")
            require(not (incomplete and category.status == "absent"),
                    "Incomplete fixture must not claim absence.")
            if support[category.category_id] == "proposed_unvalidated":
                require(category.status == "unavailable" and not category.clauses,
                        "Proposed category cannot claim a supported decision.")
            for finding in category.clauses:
                require(finding.confidence is None and finding.confidence_band == "unvalidated"
                        and finding.calibration_scope == "unvalidated" and finding.origin == "fixture",
                        "Fixture finding claims model confidence.")
    anchor_ids = set()
    for anchor in case["anchors"]:
        exact_keys(anchor, "id role span", "anchor")
        require(anchor["id"] not in anchor_ids, "Duplicate anchor.")
        anchor_ids.add(anchor["id"])
        validate_span(Span(**anchor["span"]), text, document["doc_id"])
    return result


def observe(case):
    """Compute a reference snapshot independently of the checked-in expectations."""
    result = validate_inputs(case)
    parser, job = case["parser"], case["job"]
    text = case["document"]["text"]
    categories = result.categories if result else []
    findings = [f for c in categories for f in c.clauses]
    accepted = [f for f in findings if f.status == "accepted"]
    ready = (result is not None and parser["complete"] and not parser["unavailable_regions"]
             and job["status"] == "completed" and not job["unfinished_stages"]
             and not job["candidate_search_truncated"] and job["boundary_coverage_complete"]
             and all(c.search_complete for c in categories))
    unit_source, units = display_units(text, parser["nodes"])
    manual = [] if ready else None
    for unit in units:
        a, b = unit["start"], unit["end"]
        hits = [f for f in accepted if f.span.start < b and f.span.end > a]
        unit["accepted_finding_ids"] = [f.id for f in hits]
        coverage = "not_computed"
        if ready:
            intervals = sorted((max(a, f.span.start), min(b, f.span.end)) for f in hits)
            covered, end = 0, a
            for left, right in intervals:
                covered += max(0, right - max(left, end))
                end = max(end, right)
            coverage = "none" if covered == 0 else "full" if covered == b - a else "partial"
            if coverage != "full":
                manual.append({"unit_id": unit["id"], "label": "Partly highlighted"
                               if coverage == "partial" else "Text without accepted findings"})
        unit["coverage"] = coverage
    count = len(manual) if ready else None
    support = {e["category_id"]: e["support_state"] for e in case["catalogue"]["categories"]}
    return {
        "category_states": {c.category_id: c.status for c in categories},
        "navigation": {
            "status": "ready" if ready else "processing_incomplete",
            "processing_label": None if ready else "Processing incomplete",
            "unit_source": unit_source, "display_units": units,
            "manual_review_items": manual, "manual_review_count": count,
            "accepted_finding_ids": [f.id for f in accepted],
            "review_candidate_ids": [f.id for f in findings if f.status == "review_candidate"],
            "unavailable_regions": parser["unavailable_regions"],
        },
        "presentation": {
            "scope_notice": SCOPE_NOTICE,
            "scope_notice_locations": ["upload", "results", "report"],
            "manual_review_explanation": MANUAL_EXPLANATION,
            "full_text_required": True, "context_navigation_required": True,
            "review_candidate_entry_required": True,
            "catalogue_version": case["catalogue"]["version"],
            "selected_category_ids": case["requested_category_ids"], "support_states": support,
            "sample_only": True, "fixture_confidence_label": "Unvalidated fixture",
            "safety_verdict_allowed": False, "interaction_assessment_claim_allowed": False,
            "automatic_risk_label_allowed": False,
            "report": {"scope_notice_required": True, "selected_scope_required": True,
                       "processing_incomplete": not ready, "manual_review_count": count,
                       "unavailable_regions": parser["unavailable_regions"]},
        },
    }


def verify_case(case):
    observed = observe(case)
    if observed != case["expected"]:
        import difflib
        before = json.dumps(case["expected"], ensure_ascii=False, indent=2, sort_keys=True)
        after = json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=True)
        difference = "\n".join(difflib.unified_diff(before.splitlines(), after.splitlines(),
                                                   fromfile="expected", tofile="reference"))
        raise ValueError(f"{case['id']}: expected/reference mismatch\n{difference}")
    return observed


def main():
    families = load_families()
    total = 0
    for family in families:
        for case in family["cases"]:
            observed = verify_case(case)
            nav = observed["navigation"]
            print(f"{case['id']}: {nav['status']}; manual_review_count={nav['manual_review_count']}")
            total += 1
    print(f"PASS: {len(families)} scope families; {total} cases; exact spans and reference expectations.")
    print("Development fixtures only. Backend, browser and report integration have not been tested here.")


if __name__ == "__main__":
    main()
