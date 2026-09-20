"""Feature: calibration and accuracy metrics for decision heads."""
import math

import pytest

from plexus.decision_head.evaluate import brier, expected_calibration_error, log_loss


def test_perfectly_calibrated_confidences_have_zero_ece():
    confidences = [0.8] * 10
    correct = [1] * 8 + [0] * 2
    assert expected_calibration_error(confidences, correct) == pytest.approx(0.0)


def test_overconfidence_is_measured_as_the_gap_between_confidence_and_accuracy():
    assert expected_calibration_error([0.9] * 10, [1] * 5 + [0] * 5) == pytest.approx(0.4)


def test_ece_weights_bins_by_how_many_items_fall_in_them():
    confidences = [0.95] * 8 + [0.55] * 2
    correct = [1] * 8 + [0] * 2
    ece = expected_calibration_error(confidences, correct)
    assert ece == pytest.approx(0.8 * 0.05 + 0.2 * 0.55)


def test_brier_and_log_loss():
    assert brier([1.0, 0.0], [1, 1]) == pytest.approx(0.5)
    assert log_loss([0.5, 0.5]) == pytest.approx(math.log(2))
    assert log_loss([1.0]) == pytest.approx(0.0, abs=1e-9)
