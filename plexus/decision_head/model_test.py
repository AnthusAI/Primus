"""Feature: a decision model turns named features into a value and a confidence."""
import math

import pytest

from plexus.decision_head.model import decide, validate_head
from plexus.decision_head.registry import REGISTRY


def sigmoid(z):
    return 1 / (1 + math.exp(-z))


LOGISTIC = {
    "model": "multinomial_logistic",
    "classes": ["Yes", "No"],
    "weights": {
        "Yes": {"intercept": -1.0, "a.logit_p": 2.0, "b.logit_p": 1.0},
    },
}


def test_multinomial_logistic_returns_top_class_with_its_probability_as_confidence():
    value, confidence, detail = decide({"a.logit_p": 1.0, "b.logit_p": 0.5}, LOGISTIC)
    assert value == "Yes"
    assert confidence == pytest.approx(sigmoid(1.5))
    assert detail["probabilities"]["No"] == pytest.approx(1 - sigmoid(1.5))


def test_missing_features_contribute_zero_and_lower_coverage():
    value, confidence, detail = decide({"a.logit_p": 1.0}, LOGISTIC)
    assert confidence == pytest.approx(sigmoid(1.0))
    assert detail["coverage"] == 0.5


def test_contributions_name_the_biggest_drivers_first():
    _, _, detail = decide({"a.logit_p": 0.1, "b.logit_p": 3.0}, LOGISTIC)
    names = [c["feature"] for c in detail["top_contributions"]]
    assert names[0] == "b.logit_p"


def test_linear_threshold_is_a_hand_authorable_two_class_rule():
    head = {"model": "linear_threshold", "classes": ["Pass", "Fail"],
            "positive_class": "Pass", "threshold": 0.5,
            "weights": {"intercept": 0.0, "a.p": 1.0}}
    assert decide({"a.p": 0.9}, head)[0] == "Pass"
    assert decide({"a.p": 0.1}, head)[0] == "Fail"


def test_abstain_band_flags_near_threshold_items_without_changing_the_value():
    head = {**LOGISTIC, "abstain_band": 0.1}
    _, _, near = decide({"a.logit_p": 0.5}, head)
    _, _, far = decide({"a.logit_p": 3.0}, head)
    assert near["abstain"] is True
    assert far["abstain"] is False


def test_validate_head_reports_problems_instead_of_raising():
    assert validate_head(LOGISTIC, features=["a.logit_p", "b.logit_p"]) == []
    problems = validate_head({**LOGISTIC, "model": "wat"}, features=[])
    assert any("model" in p for p in problems)
    problems = validate_head(
        {**LOGISTIC, "weights": {"Maybe": {"intercept": 0}}}, features=["a.logit_p"])
    assert any("Maybe" in p for p in problems)
    problems = validate_head(LOGISTIC, features=["a.logit_p"])
    assert any("b.logit_p" in p for p in problems)


def test_registry_lists_the_inline_models():
    assert {"linear_threshold", "multinomial_logistic"} <= set(REGISTRY)
    assert REGISTRY["multinomial_logistic"].min_n_effective > 0
