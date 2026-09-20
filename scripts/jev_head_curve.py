#!/usr/bin/env python
"""Learning curve and dataset checks for the Jev decision-head experiment.

    python scripts/jev_head_curve.py --cache DIR

Uses the answers cached by ``jev_head_experiment.py extract``; makes no Jev calls.
Prints (1) mean element intensity by tier and label, to show that intensity marks the
tier rather than the label, and (2) test accuracy and raw ECE as the fit set shrinks.
"""
import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jev_head_fit import (  # noqa: E402
    C_GRID, LOG_LOSS_FLOOR, TIERS, all_features, feature_sets, sources)
from jev_scorecard_smoke import load_rows  # noqa: E402
from plexus.decision_head.evaluate import expected_calibration_error  # noqa: E402
from plexus.decision_head.fit import build_matrix  # noqa: E402

SIZES = (60, 120, 250, 500, 1000, 2500, 5280)
SUBSAMPLES = 6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="~/Projects/Jev-Calibration")
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()

    project = Path(args.project).expanduser()
    rows = {r["id"]: r for r in load_rows(project)}
    splits = json.loads((project / "data" / "splits.json").read_text())
    srcs = sources()
    cached = {}
    for line in (args.cache / "element_answers.jsonl").read_text().splitlines():
        record = json.loads(line)
        cached[record["id"]] = all_features(record["answers"], srcs)

    by_group = defaultdict(list)
    for item_id, vector in cached.items():
        by_group[(rows[item_id]["tier"], rows[item_id]["expected"])].append(
            vector["sentiment.intensity.expected_level"] if "sentiment.intensity.expected_level" in vector
            else vector["intensity.expected_level"])
    print("mean intensity (0-1) by tier and label:")
    for tier in TIERS:
        print(f"  {tier:8s} positive {np.mean(by_group[(tier, 'positive')]):.3f}"
              f"  negative {np.mean(by_group[(tier, 'negative')]):.3f}")

    sets = feature_sets(srcs)
    fit_ids = [i for i in cached if splits.get(i) == "calibration"]
    test_ids = [i for i in cached if splits.get(i) == "test"]
    test_x = {k: build_matrix([cached[i] for i in test_ids], names) for k, names in sets.items()}
    test_y = np.array([rows[i]["expected"] == "positive" for i in test_ids])

    def score(p):
        predicted = p >= 0.5
        confidence = np.where(predicted, p, 1 - p)
        correct = (predicted == test_y).astype(int)
        return correct.mean(), expected_calibration_error(list(confidence), list(correct))

    # Jev's own answer: half the two-option CLR feature is half the log-odds, so p = sigmoid(2 * clr).
    holistic = np.array([cached[i]["self.holistic.clr.positive"] for i in test_ids])
    jev = score(1 / (1 + np.exp(-2 * holistic)))

    def fit(model, names, subset):
        y = np.array([rows[i]["expected"] == "positive" for i in subset])
        if y.all() or not y.any():
            return None
        x = build_matrix([cached[i] for i in subset], names)
        if model == "gbm":
            return HistGradientBoostingClassifier(
                max_depth=3, learning_rate=0.05, max_iter=200, l2_regularization=1.0,
                random_state=0).fit(x, y)
        folds = min(5, max(2, int(min(y.sum(), (~y).sum()))))
        best = min(C_GRID, key=lambda C: -np.mean(cross_val_score(
            LogisticRegression(C=C, max_iter=3000), x, y, cv=folds, scoring="neg_log_loss")))
        return LogisticRegression(C=best, max_iter=3000).fit(x, y)

    print(f"\nlearning curve: mean over {SUBSAMPLES} random subsamples; test accuracy / raw ECE")
    print(f"{'n':>5s}  {'H logistic':>13s}  {'HE logistic':>13s}  {'HEC gbm':>13s}  {'jev raw':>13s}")
    for n in SIZES:
        results = defaultdict(list)
        for seed in range(SUBSAMPLES):
            subset = random.Random(seed).sample(fit_ids, n)
            for label, key, model in (("H", "H", "lr"), ("HE", "HE", "lr"), ("gbm", "HEC", "gbm")):
                clf = fit(model, sets[key], subset)
                if clf is not None:
                    results[label].append(score(clf.predict_proba(test_x[key])[:, 1]))
        cell = lambda k: "%.3f / %.3f" % tuple(np.mean(results[k], axis=0))
        print(f"{n:5d}  {cell('H'):>13s}  {cell('HE'):>13s}  {cell('gbm'):>13s}  {'%.3f / %.3f' % jev:>13s}")


if __name__ == "__main__":
    main()
