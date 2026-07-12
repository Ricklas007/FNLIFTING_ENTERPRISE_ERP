def operational_risk_score(reasons: list[tuple[str, int]]) -> dict:
    """Deterministic local risk score used by rules and BI previews."""
    score = max(0, min(100, sum(points for _, points in reasons)))
    level = "BLOCKING" if score >= 80 else "ERROR" if score >= 60 else "WARNING" if score >= 30 else "INFO"
    return {"score": score, "level": level, "reasons": [{"reason": reason, "points": points} for reason, points in reasons]}
