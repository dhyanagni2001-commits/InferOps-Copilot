"""Small, transparent diagnostic evaluation metrics."""


def score_case(expected: dict, result: dict) -> dict[str, float]:
    diagnosis = result.get("diagnosis", {})
    summary = diagnosis.get("summary", "").lower()
    keywords = [item.lower() for item in expected.get("keywords", [])]
    keyword_score = sum(item in summary for item in keywords) / max(1, len(keywords))
    evidence = set(diagnosis.get("evidence_ids", []))
    valid_ids = {item["id"] for item in result.get("evidence", [])}
    citation_score = 1.0 if evidence and evidence <= valid_ids else 0.0
    return {"keyword_score": keyword_score, "citation_score": citation_score}


def average(scores: list[dict[str, float]]) -> dict[str, float]:
    if not scores:
        return {}
    return {key: sum(item[key] for item in scores) / len(scores) for key in scores[0]}
