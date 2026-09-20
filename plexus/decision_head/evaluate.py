"""Calibration and scoring metrics. Pure; stdlib only."""
import math
from typing import List, Sequence


def expected_calibration_error(
    confidences: Sequence[float], correct: Sequence[int], bins: int = 10
) -> float:
    """Item-weighted mean gap between confidence and accuracy over equal-width bins."""
    total = len(confidences)
    if total == 0:
        return 0.0
    buckets: List[List[int]] = [[] for _ in range(bins)]
    for index, confidence in enumerate(confidences):
        buckets[min(int(confidence * bins), bins - 1)].append(index)
    error = 0.0
    for members in buckets:
        if members:
            mean_confidence = sum(confidences[i] for i in members) / len(members)
            accuracy = sum(correct[i] for i in members) / len(members)
            error += len(members) / total * abs(mean_confidence - accuracy)
    return error


def brier(confidences: Sequence[float], correct: Sequence[int]) -> float:
    """Top-label Brier score: mean squared gap between confidence and correctness."""
    return sum((c - k) ** 2 for c, k in zip(confidences, correct)) / len(confidences)


def log_loss(true_class_probabilities: Sequence[float], eps: float = 1e-12) -> float:
    """Mean negative log probability assigned to the true class."""
    return -sum(math.log(max(p, eps)) for p in true_class_probabilities) / len(
        true_class_probabilities)
