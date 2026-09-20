"""Fit stage of jev_head_experiment.py: heads fit on the 'calibration' split, judged on 'test'."""
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

from jev_head_experiment import SCORE, cache_file
from jev_scorecard_smoke import load_rows
from plexus.confidence_calibration import apply_temperature_scaling, compute_two_stage_calibration
from plexus.decision_head.evaluate import brier, expected_calibration_error, log_loss
from plexus.decision_head.features import HOLISTIC, extract_terms
from plexus.decision_head.fit import build_matrix, fit_logistic
from plexus.decision_head.model import decide
from plexus.scores.JevScore import JevScore

EPS = 0.01
C_GRID = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 100.0]
TIERS = ["strong", "medium", "weak", "neutral"]
LOG_LOSS_FLOOR = 1e-6


def sources():
    score = JevScore(**SCORE)
    found = {HOLISTIC: (score.question_name, "choice", SCORE["criteria"])}
    for ref, name, spec in score._element_questions():
        found[ref] = (name, spec.question_type, spec.criteria)
    return found


def all_features(answers, srcs):
    """Every available term for every element, as {feature name: value}; None if incomplete."""
    vector = {}
    for ref, (name, question_type, criteria) in srcs.items():
        if name not in answers:
            return None
        for term, value in extract_terms(answers[name], question_type, criteria, EPS).items():
            vector[f"{ref}.{term}"] = value
    return vector


def feature_sets(srcs):
    elements = [r for r in srcs if r != HOLISTIC]
    default = []
    for ref in elements:
        _, question_type, criteria = srcs[ref]
        if question_type == "noul":
            default.append(f"{ref}.logit_p")
        elif question_type == "choice":
            default += [f"{ref}.clr.{o}" for o in criteria]
        else:
            default.append(f"{ref}.expected_level")
    extras = [f"{HOLISTIC}.confidence"]
    for ref in elements:
        _, question_type, _ = srcs[ref]
        if question_type != "noul":
            extras += [f"{ref}.confidence"] + ([f"{ref}.entropy"] if question_type == "choice" else [])
    holistic = [f"{HOLISTIC}.clr.positive"]
    return {
        "H": holistic,
        "E": default,
        "HE": holistic + default,
        "HEC": holistic + default + extras,
    }


def true_probability(probabilities, labels):
    return [p if y == "positive" else 1.0 - p for p, y in zip(probabilities, labels)]


def two_stage(conf_fit, correct_fit):
    temperature, isotonic, _ = compute_two_stage_calibration(list(conf_fit), list(correct_fit))
    def apply(conf):
        scaled = apply_temperature_scaling(list(conf), temperature)
        return list(isotonic.predict(scaled)) if isotonic is not None else scaled
    return apply, temperature


def bootstrap_difference(metric, a, b, correct_a, correct_b, tiers=None, n=400, seed=0):
    """Paired bootstrap 95% CI for metric(b) - metric(a)."""
    rng = random.Random(seed)
    size = len(correct_a)
    diffs = []
    for _ in range(n):
        index = [rng.randrange(size) for _ in range(size)]
        diffs.append(metric([b[i] for i in index], [correct_b[i] for i in index])
                     - metric([a[i] for i in index], [correct_a[i] for i in index]))
    diffs.sort()
    return diffs[int(0.025 * n)], diffs[int(0.975 * n)]


def fit_stage(args):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.linear_model import LogisticRegression

    project = Path(args.project).expanduser()
    rows = {r["id"]: r for r in load_rows(project)}
    splits = json.loads((project / "data" / "splits.json").read_text())
    srcs = sources()
    cached = {}
    for line in cache_file(args.cache).read_text().splitlines():
        record = json.loads(line)
        vector = all_features(record["answers"], srcs)
        if vector is not None:
            cached[record["id"]] = (vector, record["answers"])
    research = {}
    raw = project / "data" / "jev_raw.jsonl"
    for line in raw.read_text().splitlines():
        record = json.loads(line)
        research[record["id"]] = record["answers"]["sentiment"]

    def collect(split):
        ids = [i for i in cached if splits.get(i) == split]
        return ids, [cached[i][0] for i in ids], [rows[i]["expected"] for i in ids], [rows[i]["tier"] for i in ids]

    fit_ids, fit_x, fit_y, _ = collect("calibration")
    test_ids, test_x, test_y, test_tier = collect("test")
    print(f"items with complete answers: fit={len(fit_ids)} test={len(test_ids)}")

    # Question independence: does the holistic answer change when the request carries more questions?
    flips = shifts = compared = 0
    for i in cached:
        if i in research:
            new = cached[i][1][srcs[HOLISTIC][0]]
            compared += 1
            flips += new["choice"] != research[i]["choice"]
            shifts += abs(new["probabilities"]["positive"] - research[i]["probabilities"]["positive"])
    print(f"holistic answer, 8-question request vs research 2-question request: "
          f"{flips}/{compared} choices differ ({flips / compared:.2%}); "
          f"mean |dP(positive)| = {shifts / compared:.4f}")

    def outcome(prob_positive, labels):
        predicted = ["positive" if p >= 0.5 else "negative" for p in prob_positive]
        confidence = [max(p, 1 - p) for p in prob_positive]
        return predicted, confidence, [int(a == b) for a, b in zip(predicted, labels)]

    results = {}

    def record(name, prob_test, prob_fit_oof=None, calibrate=True):
        predicted, confidence, correct = outcome(prob_test, test_y)
        results[name] = {"predicted": predicted, "confidence": confidence, "correct": correct,
                         "true_p": true_probability(prob_test, test_y)}
        if calibrate and prob_fit_oof is not None:
            _, conf_fit, correct_fit = outcome(prob_fit_oof, fit_y)
            apply, temperature = two_stage(conf_fit, correct_fit)
            calibrated = apply(confidence)
            results[name + " +cal"] = {"predicted": predicted, "confidence": calibrated,
                                       "correct": correct, "temperature": temperature}

    # Jev's own answer, raw and calibrated on the fit split.
    jev_p = lambda ids: [cached[i][1][srcs[HOLISTIC][0]]["probabilities"]["positive"] for i in ids]
    record("jev holistic", jev_p(test_ids), jev_p(fit_ids))

    sets = feature_sets(srcs)
    folds = StratifiedKFold(5, shuffle=True, random_state=0)
    heads = {}
    for label, names in sets.items():
        matrix = build_matrix(fit_x, names)
        positive = np.array([y == "positive" for y in fit_y])

        def cv_log_loss(C):
            proba = cross_val_predict(LogisticRegression(C=C, max_iter=3000), matrix, fit_y,
                                      cv=folds, method="predict_proba")[:, 1]
            return -np.mean(np.log(np.where(positive, proba, 1 - proba).clip(LOG_LOSS_FLOOR)))

        best = min(C_GRID, key=cv_log_loss)
        oof = cross_val_predict(LogisticRegression(C=best, max_iter=3000), matrix, fit_y, cv=folds,
                                method="predict_proba")[:, 1]
        head = fit_logistic(fit_x, fit_y, names, C=best)
        heads[label] = (head, best)
        served = [decide(x, head)[2]["probabilities"]["positive"] for x in test_x]
        record(f"{label} logistic", served, list(oof))

    # Same features, gradient boosting: the architecture bake-off.
    names = sets["HEC"]
    matrix, test_matrix = build_matrix(fit_x, names), build_matrix(test_x, names)
    gbm = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                         l2_regularization=1.0, random_state=0)
    oof = cross_val_predict(gbm, matrix, fit_y, cv=folds, method="predict_proba")[:, 1]
    gbm.fit(matrix, fit_y)
    record("HEC gbm", list(gbm.predict_proba(test_matrix)[:, list(gbm.classes_).index("positive")]), list(oof))

    def summarize(name, r):
        per_tier = {}
        for tier in TIERS:
            picks = [k for k, t in enumerate(test_tier) if t == tier]
            per_tier[tier] = (sum(r["correct"][k] for k in picks) / len(picks)) if picks else float("nan")
        row = {"accuracy": sum(r["correct"]) / len(r["correct"]), **per_tier,
               "ECE": expected_calibration_error(r["confidence"], r["correct"]),
               "Brier": brier(r["confidence"], r["correct"]),
               "mean_conf": sum(r["confidence"]) / len(r["confidence"])}
        if "true_p" in r:
            row["logloss"] = log_loss(r["true_p"], LOG_LOSS_FLOOR)
        return row

    table = {name: summarize(name, r) for name, r in results.items()}
    header = f"{'variant':22s} {'acc':>6s} {'strong':>6s} {'medium':>6s} {'weak':>6s} {'neutral':>7s} {'ECE':>6s} {'Brier':>6s} {'logloss':>8s} {'conf':>6s}"
    print("\n" + header)
    for name, row in table.items():
        print(f"{name:22s} {row['accuracy']:6.3f} {row['strong']:6.3f} {row['medium']:6.3f} {row['weak']:6.3f} "
              f"{row['neutral']:7.3f} {row['ECE']:6.3f} {row['Brier']:6.3f} {row.get('logloss', float('nan')):8.3f} "
              f"{row['mean_conf']:6.3f}")

    base = results["jev holistic"]
    acc = lambda pred, corr: sum(corr) / len(corr)
    print("\npaired bootstrap 95% CI of (variant - jev holistic) on the test split")
    for name in results:
        if name in ("jev holistic",):
            continue
        r = results[name]
        lo_a, hi_a = bootstrap_difference(acc, base["correct"], r["correct"], base["correct"], r["correct"])
        lo_e, hi_e = bootstrap_difference(
            lambda c, k: expected_calibration_error(c, k), base["confidence"], r["confidence"],
            base["correct"], r["correct"])
        print(f"  {name:22s} accuracy [{lo_a:+.3f}, {hi_a:+.3f}]   ECE [{lo_e:+.3f}, {hi_e:+.3f}]")

    head, C = heads["HE"]
    weights = head["weights"]["positive"]
    print(f"\nHE logistic weights (C={C}), largest first:")
    for feature, w in sorted(((k, v) for k, v in weights.items() if k != "intercept"),
                             key=lambda kv: -abs(kv[1])):
        print(f"  {w:+8.3f}  {feature}")
    print(f"  {weights['intercept']:+8.3f}  intercept")
    (args.cache / "results.json").write_text(json.dumps({"table": table, "heads": {k: v[0] for k, v in heads.items()}}, indent=1))
