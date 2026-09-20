"""Serving-side decision: features in, value + confidence + explanation out."""
from typing import Any, Dict, List, Mapping, Optional, Tuple

from plexus.decision_head.models.linear import (
    INTERCEPT, class_logits, class_weights, declared_features)
from plexus.decision_head.registry import REGISTRY

TOP_CONTRIBUTIONS = 3


def decide(features: Mapping[str, float], head: Mapping) -> Tuple[str, float, Dict[str, Any]]:
    """Return ``(value, confidence, detail)``; confidence is P(value)."""
    probabilities = REGISTRY[head["model"]].predict_proba(features, head)
    ranked = sorted(probabilities, key=probabilities.get, reverse=True)
    top, runner_up = ranked[0], ranked[1]

    weights = class_weights(head)
    contributions = [
        {"feature": name,
         "contribution": (weights[top].get(name, 0.0) - weights[runner_up].get(name, 0.0))
         * features.get(name, 0.0)}
        for name in declared_features(head) if name in features
    ]
    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)

    declared = declared_features(head)
    coverage = (sum(1 for name in declared if name in features) / len(declared)) if declared else 1.0
    band = float(head.get("abstain_band", 0.0))
    margin = (probabilities[top] - probabilities[runner_up]) / 2.0
    detail = {
        "model": head["model"],
        "probabilities": probabilities,
        "coverage": coverage,
        "top_contributions": contributions[:TOP_CONTRIBUTIONS],
        "abstain": margin < band,
    }
    return top, probabilities[top], detail


def explain(value: str, confidence: float, detail: Mapping) -> str:
    """A deterministic explanation from the largest contributions, so reviewers have
    something to react to."""
    drivers = ", ".join(
        f"{c['feature']} ({c['contribution']:+.2f})" for c in detail["top_contributions"])
    return f"{value} at {confidence:.0%}. Largest drivers: {drivers or 'none'}."


def validate_head(head: Mapping, features: Optional[List[str]] = None) -> List[str]:
    """Problems with a decision head, as messages; empty means valid."""
    problems: List[str] = []
    if head.get("model") not in REGISTRY:
        return [f"unknown model {head.get('model')!r}; expected one of {sorted(REGISTRY)}"]
    classes = head.get("classes") or []
    if len(classes) < 2 or not all(isinstance(c, str) for c in classes):
        problems.append("classes must list at least two label strings")
        return problems
    if head["model"] == "linear_threshold":
        if len(classes) != 2:
            problems.append("linear_threshold needs exactly two classes")
        if head.get("positive_class") not in classes:
            problems.append(f"positive_class {head.get('positive_class')!r} is not in classes")
        if problems:
            return problems
    else:
        for name in (head.get("weights") or {}):
            if name not in classes:
                problems.append(f"weights are given for {name!r}, which is not in classes")
        if problems:
            return problems
    if features is not None:
        for name in declared_features(head):
            if name not in features:
                problems.append(f"weight for {name!r} is not a declared feature")
    return problems
