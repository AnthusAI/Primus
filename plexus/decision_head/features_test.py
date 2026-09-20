"""Feature: Jev answers become named numeric features.

The mapping is a deterministic function of the configured criteria and the
answer alone: no fitted preprocessing, so weights stay keyed by feature name.
"""
import math

import pytest

from plexus.decision_head.features import available_terms, extract_terms

EPS = 0.01


def logit(p):
    return math.log(p / (1 - p))


def test_noul_terms_are_logit_probability_and_indicator():
    terms = extract_terms({"type": "noul", "noul": 0.9}, "noul", None, EPS)
    assert terms["logit_p"] == pytest.approx(logit(0.9))
    assert terms["p"] == 0.9
    assert terms["is_yes"] == 1.0
    assert extract_terms({"type": "noul", "noul": 0.2}, "noul", None, EPS)["is_yes"] == 0.0


def test_extreme_probabilities_are_clipped_so_one_noisy_answer_cannot_dominate():
    hi = extract_terms({"type": "noul", "noul": 0.9999}, "noul", None, EPS)["logit_p"]
    lo = extract_terms({"type": "noul", "noul": 0.0001}, "noul", None, EPS)["logit_p"]
    assert hi == pytest.approx(logit(0.99))
    assert lo == pytest.approx(logit(0.01))


def test_choice_uses_centered_log_ratio_so_features_are_not_collinear():
    answer = {"type": "choice", "choice": "b", "confidence": 0.7,
              "probabilities": {"a": 0.2, "b": 0.5, "c": 0.3}}
    terms = extract_terms(answer, "choice", {"a": None, "b": None, "c": None}, EPS)
    assert sum(terms[f"clr.{o}"] for o in "abc") == pytest.approx(0.0)
    assert terms["clr.b"] > terms["clr.c"] > terms["clr.a"]
    assert terms["top_p"] == 0.5
    assert 0.0 < terms["entropy"] < 1.0
    assert terms["confidence"] == 0.7
    assert terms["chosen.b"] == 1.0 and terms["chosen.a"] == 0.0


def test_choice_follows_configured_option_order_and_tolerates_omitted_options():
    answer = {"type": "choice", "choice": "a", "probabilities": {"a": 0.9}}
    terms = extract_terms(answer, "choice", {"a": None, "b": None}, EPS)
    assert set(t for t in terms if t.startswith("clr.")) == {"clr.a", "clr.b"}
    assert terms["clr.a"] > 0 > terms["clr.b"]
    assert sum(terms[f"clr.{o}"] for o in "ab") == pytest.approx(0.0)


def test_score_terms_normalize_over_configured_levels():
    answer = {"type": "score", "score": 1.6, "confidence": 0.7,
              "legend": {"0": "low", "1": "mid", "2": "high"},
              "probabilities": {"0": 0.1, "1": 0.3, "2": 0.6}}
    terms = extract_terms(answer, "score", ["low", "mid", "high"], EPS)
    assert terms["score_norm"] == pytest.approx(0.8)
    assert terms["expected_level"] == pytest.approx((0.3 + 1.2) / 2)
    assert terms["clr.2"] > terms["clr.1"] > terms["clr.0"]
    assert terms["confidence"] == 0.7


def test_score_legend_that_disagrees_with_criteria_is_a_hard_error():
    answer = {"type": "score", "score": 1.0, "legend": {"0": "x", "1": "y"},
              "probabilities": {"0": 0.5, "1": 0.5}}
    with pytest.raises(ValueError, match="legend"):
        extract_terms(answer, "score", ["low", "mid", "high"], EPS)


def test_available_terms_lists_exactly_what_extraction_can_produce():
    for question_type, criteria, answer in [
        ("noul", None, {"type": "noul", "noul": 0.5}),
        ("choice", {"a": None, "b": None},
         {"type": "choice", "choice": "a", "probabilities": {"a": 0.6, "b": 0.4}}),
        ("score", ["l", "h"],
         {"type": "score", "score": 0.5, "legend": {"0": "l", "1": "h"},
          "probabilities": {"0": 0.5, "1": 0.5}}),
    ]:
        assert available_terms(question_type, criteria) >= set(
            extract_terms(answer, question_type, criteria, EPS)) - {"confidence"}
