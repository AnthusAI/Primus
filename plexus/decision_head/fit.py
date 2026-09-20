"""Fit decision heads from cached feature vectors. scikit-learn is used here only;
the fitted head serves with the stdlib-only code in ``model.py``."""
from typing import Dict, List, Mapping, Optional, Sequence


def build_matrix(rows: Sequence[Mapping[str, float]], feature_names: Sequence[str]):
    """Feature matrix in declared order. Training requires complete coverage: imputing a
    neutral value would bias a new feature's weight toward zero and get it retired."""
    import numpy as np

    matrix = []
    for index, row in enumerate(rows):
        missing = [name for name in feature_names if name not in row]
        if missing:
            raise ValueError(f"row {index} is missing features {missing}; training needs full coverage")
        matrix.append([row[name] for name in feature_names])
    return np.array(matrix, dtype=float)


def fit_logistic(
    rows: Sequence[Mapping[str, float]],
    labels: Sequence[str],
    feature_names: Sequence[str],
    *,
    C: float,
    sample_weight: Optional[Sequence[float]] = None,
    max_iter: int = 2000,
) -> Dict:
    """Fit a multinomial logistic head and return it in serving form."""
    from sklearn.linear_model import LogisticRegression

    matrix = build_matrix(rows, feature_names)
    clf = LogisticRegression(C=C, max_iter=max_iter)
    clf.fit(matrix, list(labels), sample_weight=sample_weight)
    classes: List[str] = [str(c) for c in clf.classes_]
    if len(classes) == 2:
        # sklearn stores one coefficient vector for the second class; the first is the reference.
        weights = {classes[1]: {"intercept": float(clf.intercept_[0]),
                                **{n: float(w) for n, w in zip(feature_names, clf.coef_[0])}}}
    else:
        weights = {c: {"intercept": float(b), **{n: float(w) for n, w in zip(feature_names, coef)}}
                   for c, b, coef in zip(classes, clf.intercept_, clf.coef_)}
    return {"model": "multinomial_logistic", "classes": classes, "weights": weights}
