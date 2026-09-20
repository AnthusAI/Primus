"""Decision model registry: name -> serving function and the data it needs.

Adding an architecture is one module plus one entry here. ``min_n_effective`` is
the smallest Kish effective sample size at which fitting the model is defensible.
"""
from dataclasses import dataclass
from typing import Callable, Dict, Mapping

from plexus.decision_head.models import linear


@dataclass(frozen=True)
class ModelSpec:
    name: str
    predict_proba: Callable[[Mapping[str, float], Mapping], Dict[str, float]]
    min_n_effective: int
    description: str


REGISTRY: Dict[str, ModelSpec] = {
    "linear_threshold": ModelSpec(
        "linear_threshold", linear.predict_proba, 1,
        "Hand-authorable two-class rule: weighted sum against a threshold."),
    "multinomial_logistic": ModelSpec(
        "multinomial_logistic", linear.predict_proba, 50,
        "Multinomial logistic regression over named features."),
}
