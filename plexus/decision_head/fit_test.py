"""Feature: fitting a decision head from cached feature vectors."""
import random

import pytest

pytest.importorskip("sklearn")

from plexus.decision_head.fit import fit_logistic  # noqa: E402
from plexus.decision_head.model import decide  # noqa: E402


def synthetic(n=400, seed=0):
    rng = random.Random(seed)
    rows, labels = [], []
    for _ in range(n):
        a, b = rng.gauss(0, 1), rng.gauss(0, 1)
        z = 2.0 * a - 1.0 * b + 0.3
        labels.append("Yes" if rng.random() < 1 / (1 + 2.718281828 ** -z) else "No")
        rows.append({"a.logit_p": a, "b.logit_p": b})
    return rows, labels


def test_fit_recovers_the_generating_weights():
    rows, labels = synthetic()
    head = fit_logistic(rows, labels, ["a.logit_p", "b.logit_p"], C=100.0)
    weights = head["weights"]["Yes"]
    assert weights["a.logit_p"] == pytest.approx(2.0, abs=0.5)
    assert weights["b.logit_p"] == pytest.approx(-1.0, abs=0.5)


def test_fitted_head_serves_the_same_probabilities_as_the_fitting_library():
    from sklearn.linear_model import LogisticRegression
    import numpy as np

    rows, labels = synthetic()
    names = ["a.logit_p", "b.logit_p"]
    head = fit_logistic(rows, labels, names, C=1.0)
    clf = LogisticRegression(C=1.0, max_iter=1000).fit(
        np.array([[r[n] for n in names] for r in rows]), labels)
    expected = clf.predict_proba(np.array([[r[n] for n in names] for r in rows[:25]]))
    for row, probs in zip(rows[:25], expected):
        value, confidence, detail = decide(row, {**head, "model": "multinomial_logistic"})
        assert detail["probabilities"]["Yes"] == pytest.approx(probs[list(clf.classes_).index("Yes")], abs=1e-9)


def test_training_refuses_rows_that_lack_a_declared_feature():
    rows, labels = synthetic(n=20)
    del rows[3]["b.logit_p"]
    with pytest.raises(ValueError, match="b.logit_p"):
        fit_logistic(rows, labels, ["a.logit_p", "b.logit_p"], C=1.0)


def test_fit_supports_sample_weights():
    rows, labels = synthetic()
    head = fit_logistic(rows, labels, ["a.logit_p", "b.logit_p"], C=1.0,
                        sample_weight=[1.0] * len(rows))
    assert head["classes"] and head["weights"]
