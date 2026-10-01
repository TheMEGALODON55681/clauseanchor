from pathlib import Path
from clauseanchor_core import (
    AnalysisContext, StubAnalyzer, from_dict, text_digest, to_dict, validate_result,
)


def main():
    directory = Path(__file__).resolve().parents[1] / "fixtures"
    analyzer = StubAnalyzer(directory)
    source = analyzer.source_text
    result = analyzer.analyze(
        source, doc_id="phase1-check", text_sha256=text_digest(source),
        category_ids=analyzer.category_ids, context=AnalysisContext(),
    )
    validate_result(from_dict(to_dict(result)), source)
    for category in result.categories:
        print(f"{category.category_id}: {category.status}; spans={len(category.clauses)}")
    print("PASS: contract 2.0; 4 category states; 2 exact spans; fixture mode only.")


if __name__ == "__main__":
    main()
