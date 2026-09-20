"""Inline linear models: pure arithmetic over serialized numbers, stdlib only.

Both models reduce to a softmax over per-class logits, so serving has one code
path. ``linear_threshold`` is the hand-authorable two-class special case.
"""
import math
from typing import Dict, List, Mapping, Tuple

INTERCEPT = "intercept"


def class_weights(head: Mapping) -> Dict[str, Dict[str, float]]:
    """Per-class weight maps, with the hand-authored form expanded to the general one."""
    classes: List[str] = list(head["classes"])
    if head["model"] == "linear_threshold":
        positive = head["positive_class"]
        flat = dict(head["weights"])
        flat[INTERCEPT] = flat.get(INTERCEPT, 0.0) - float(head.get("threshold", 0.0))
        return {c: (flat if c == positive else {}) for c in classes}
    weights = head.get("weights") or {}
    return {c: dict(weights.get(c, {})) for c in classes}


def declared_features(head: Mapping) -> List[str]:
    names: List[str] = []
    for weights in class_weights(head).values():
        for name in weights:
            if name != INTERCEPT and name not in names:
                names.append(name)
    return names


def class_logits(features: Mapping[str, float], head: Mapping) -> Dict[str, float]:
    return {
        cls: weights.get(INTERCEPT, 0.0)
        + sum(w * features.get(name, 0.0) for name, w in weights.items() if name != INTERCEPT)
        for cls, weights in class_weights(head).items()
    }


def predict_proba(features: Mapping[str, float], head: Mapping) -> Dict[str, float]:
    logits = class_logits(features, head)
    top = max(logits.values())
    exps = {c: math.exp(z - top) for c, z in logits.items()}
    total = sum(exps.values())
    return {c: e / total for c, e in exps.items()}
