# Experiment 1: sentiment dataset

Run on 2026-09-20. Part of the [Jev decision-head lab notes](index.md).

## Question

Does a small model over Jev's element answers beat Jev's own holistic answer, in
accuracy and in confidence calibration, and how many labels does it take?

## Setup

- **Data**: the public 8,801-example sentiment set from the Jev-Calibration research
  project (duplicate texts removed). Each item is a short text labelled positive or
  negative and tagged with a strength tier: strong, medium, weak or neutral.
- **Splits**: the project's fixed splits. Heads were fit on the `calibration` split
  (5,280 items) and everything was judged on the held-out `test` split (3,521 items).
  The fit split was also used for out-of-fold calibration.
- **Jev**: model jev-1.13.0 through the TypeSafe SDK, one request per item, all
  questions in that request. 8,801 requests, no failures, 4,413,918 input tokens.
- **Holistic question**: "What is the overall sentiment of this text?" as a choice
  between positive and negative.
- **Seven elements**, asked in the same request:

| Element | Type | Question |
|---|---|---|
| praise | yes/no | Does the text express praise or approval of something? |
| criticism | yes/no | Does the text express criticism or disapproval of something? |
| mixed | yes/no | Does the text express both positive and negative feelings? |
| irony | yes/no | Is the text sarcastic or ironic? |
| recommend | yes/no | Would the author recommend or endorse the thing being discussed? |
| expectation | choice | How did the thing described compare with what the author expected? (exceeded, met, fell_short, unclear) |
| intensity | score | How strong is the emotion expressed? (none, mild, moderate, strong) |

- **Features**: computed by a fixed function of each answer, with no fitted
  preprocessing. Yes/no gives a clipped log-odds. Choices give a centered log-ratio
  per option. The score question gives its expected level. Probabilities are clipped
  at 0.01 so one noisy answer cannot dominate.
- **Feature sets compared**:
  - H: the holistic answer alone (one feature).
  - E: the elements alone, default features.
  - HE: holistic answer plus elements.
  - HEC: HE plus Jev's confidences and the entropy of choice answers.
- **Models**: L2-regularized logistic regression with the regularization strength
  chosen by 5-fold cross-validated log loss over 0.01, 0.03, 0.1, 0.3, 1, 3, 10 and
  100; and gradient boosting (depth 3, learning rate 0.05, 200 iterations, L2 1.0)
  on HEC.
- **Calibration**: the repo's two-stage method (temperature scaling then isotonic
  regression), fit only on out-of-fold predictions from the fit split and applied to
  test confidences. Confidence is the probability of the predicted class.
- **Serving check**: a logistic head served through the same stdlib-only code a
  scorecard uses produces probabilities matching scikit-learn's to 1e-9 (a spec).

No feedback-style sampling was involved here, so no sampling correction was applied.

## Results

Test split, 3,521 items. Accuracy by tier: strong, medium, weak, neutral.

| Variant | Acc | Strong | Medium | Weak | Neutral | ECE | Brier | Log loss | Mean conf |
|---|---|---|---|---|---|---|---|---|---|
| Jev holistic | 0.760 | 1.000 | 0.997 | 0.739 | 0.505 | 0.153 | 0.182 | 0.696 | 0.913 |
| Jev holistic, calibrated | 0.760 | 1.000 | 0.997 | 0.739 | 0.505 | 0.014 | 0.140 | n/a | 0.760 |
| H logistic | 0.758 | 1.000 | 0.997 | 0.736 | 0.502 | 0.062 | 0.155 | 0.470 | 0.794 |
| H logistic, calibrated | 0.758 | 1.000 | 0.997 | 0.736 | 0.502 | 0.009 | 0.143 | n/a | 0.760 |
| E logistic | 0.841 | 1.000 | 1.000 | 0.894 | 0.525 | 0.011 | 0.104 | 0.314 | 0.845 |
| E logistic, calibrated | 0.841 | 1.000 | 1.000 | 0.894 | 0.525 | 0.010 | 0.104 | n/a | 0.833 |
| HE logistic | 0.843 | 1.000 | 1.000 | 0.896 | 0.530 | 0.002 | 0.103 | 0.312 | 0.844 |
| HE logistic, calibrated | 0.843 | 1.000 | 1.000 | 0.896 | 0.530 | 0.013 | 0.103 | n/a | 0.833 |
| HEC logistic | 0.845 | 1.000 | 1.000 | 0.901 | 0.527 | 0.010 | 0.101 | 0.307 | 0.847 |
| HEC logistic, calibrated | 0.845 | 1.000 | 1.000 | 0.901 | 0.527 | 0.015 | 0.101 | n/a | 0.837 |
| HEC gradient boosting | 0.872 | 1.000 | 1.000 | 0.939 | 0.568 | 0.016 | 0.082 | 0.250 | 0.855 |
| HEC gradient boosting, calibrated | 0.872 | 1.000 | 1.000 | 0.939 | 0.568 | 0.013 | 0.082 | n/a | 0.865 |

Log loss uses a probability floor of 1e-6 and is shown for uncalibrated variants only,
because calibration here adjusts the confidence of the predicted class and not a full
distribution. Jev's own log loss is high because it often assigns exactly 1.0 or 0.0.

Paired bootstrap 95% intervals for the difference from the Jev holistic answer
(400 resamples of the test items):

| Variant | Accuracy difference | Raw ECE difference |
|---|---|---|
| H logistic | -0.007 to +0.002 | -0.107 to -0.074 |
| E logistic | +0.066 to +0.094 | -0.155 to -0.123 |
| HE logistic | +0.067 to +0.098 | -0.156 to -0.126 |
| HEC logistic | +0.068 to +0.100 | -0.153 to -0.125 |
| HEC gradient boosting | +0.097 to +0.125 | -0.147 to -0.117 |
| Jev holistic, calibrated | 0 (same predictions) | -0.151 to -0.116 |

The intervals treat items as independent.

## Reading the results

**What changed and what did not.** Jev's holistic answer is essentially the same with
seven extra questions in the request: its choice differed from the earlier
two-question run on 111 of 8,801 items (1.26%, mean change in probability 0.0108).
Identical-question run-to-run noise measured earlier was about 1% (35 of 3,521). So
the improvement in the final answer comes from the head combining the element
answers, not from a better holistic answer. Two controls back this up:

- The H logistic head, fit on the holistic answer alone, is at 0.758: fitting and
  recalibrating gains nothing in accuracy.
- The E head, which never sees the holistic answer, scores 0.841 against 0.843 for
  HE. The holistic coefficient in HE is small (-0.20).

**Calibration.** Jev's raw confidence averages 0.913 against 0.760 accuracy. The H
head already brings ECE from 0.153 to 0.062, which shows how much of the miscalibration
is a plain overconfidence shift. The fitted heads with elements reach ECE 0.002 to
0.011, which is at the noise floor and comparable to Jev after two-stage calibration
(0.014). The advantage of the head is in sharpness: Brier 0.103 against 0.140.
Calibrating a fitted head afterwards did not help for the logistic models.

**Where the gain is.** Strong and medium tiers were already near 1.0. Nearly all the
gain is in the weak tier (0.739 to 0.896 for HE, 0.939 for boosting). The neutral tier
barely moves (0.505 to 0.53, and 0.568 for boosting): those labels carry little
recoverable signal, so overall accuracy is capped near 0.87 here.

**Fitted weights, with a warning.** HE logistic, regularization 100, positive class:

| Feature | Weight |
|---|---|
| intensity.expected_level | -2.326 |
| praise.logit_p | +1.275 |
| recommend.logit_p | -1.272 |
| criticism.logit_p | -1.176 |
| mixed.logit_p | +0.606 |
| expectation.clr.fell_short | -0.439 |
| expectation.clr.exceeded | +0.427 |
| irony.logit_p | +0.220 |
| self.holistic.clr.positive | -0.203 |
| expectation.clr.unclear | +0.155 |
| expectation.clr.met | -0.143 |
| intercept | +1.146 |

Do not read these as importances. The features are on different scales (log-odds
range about plus or minus 4.6, expected level 0 to 1), so raw coefficients are not
comparable. The intensity coefficient is the largest, but mean intensity is almost
identical for positive and negative items within a tier:

| Tier | Mean intensity, positive | Mean intensity, negative |
|---|---|---|
| strong | 0.970 | 0.971 |
| medium | 0.206 | 0.222 |
| weak | 0.207 | 0.219 |
| neutral | 0.003 | 0.003 |

So intensity marks the tier, and the model uses it as an offset that changes how much
the praise and criticism features count. It is not a discovered concept. Also, the
negative sign on recommend and the slightly negative holistic weight are what you get
when several correlated features compete for the same signal. An optimizer that
reasons about factors needs standardized coefficients or permutation importance, not
these.

## Learning curve

Fit set subsampled at random six times per size; each cell is the mean over the six.
Test accuracy and raw ECE. Jev's own numbers are constant.

| Fit items | H logistic | HE logistic | HEC boosting | Jev raw |
|---|---|---|---|---|
| 60 | 0.760 / 0.071 | 0.806 / 0.046 | 0.792 / 0.066 | 0.760 / 0.149 |
| 120 | 0.761 / 0.073 | 0.816 / 0.038 | 0.814 / 0.068 | 0.760 / 0.149 |
| 250 | 0.759 / 0.070 | 0.824 / 0.030 | 0.827 / 0.058 | 0.760 / 0.149 |
| 500 | 0.759 / 0.069 | 0.827 / 0.023 | 0.840 / 0.036 | 0.760 / 0.149 |
| 1000 | 0.759 / 0.078 | 0.834 / 0.018 | 0.854 / 0.018 | 0.760 / 0.149 |
| 2500 | 0.757 / 0.067 | 0.839 / 0.009 | 0.866 / 0.017 | 0.760 / 0.149 |
| 5280 | 0.758 / 0.062 | 0.843 / 0.002 | 0.872 / 0.016 | 0.760 / 0.149 |

The curve script reconstructs Jev's probability from the clipped feature, so its Jev
ECE is 0.149 against 0.153 computed directly; accuracy is identical.

Takeaways: the logistic head with elements beats Jev at every size, including 60
labels. Boosting ties it near 250 items and wins from about 500, and is worse
calibrated below that. Holistic-only recalibration never changes accuracy at any size.
Real feedback sets are often in the hundreds, which is where the logistic head is the
right default and where a heavier model has not yet earned its place.

## What went wrong along the way

A first fit on a partial answer cache reported 0.966 accuracy. The cache had been
filled in file order (strong positive, strong negative, medium positive, and so on),
so it held almost no weak-tier negatives; the model learned that low intensity meant
positive and gave intensity a coefficient near -7.5. The partial run was discarded.
The clean run on all 8,801 items gives the numbers above. Check that your fit sample
is not confounded with how it was assembled.

## How to reproduce

The scripts are in the Plexus working tree (see the Kanbus tasks for their state) and
need `typesafe-sdk`, `scikit-learn`, `numpy` and `scipy`, plus a TypeSafe API key in
the environment or in the Jev-Calibration project's `.env`. The key is never printed.

```
python scripts/jev_head_experiment.py extract --cache tmp/jev_head_experiment
python scripts/jev_head_experiment.py fit --cache tmp/jev_head_experiment
python scripts/jev_head_curve.py --cache tmp/jev_head_experiment
```

`extract` is resumable and is the only step that calls Jev (8,801 requests, about
4.4 million input tokens, about 20 to 25 minutes at 16 concurrent requests). `fit` and
`curve` read the cached answers and cost nothing. The answer cache is a local
gitignored file under `tmp/`; delete it and `extract` rebuilds it, though Jev's ~1%
answer noise means a rebuilt cache will not reproduce every digit above.

A live smoke run (`scripts/jev_scorecard_smoke.py --elements`, 40 items) confirmed one
request per item with element questions and that the API accepts dotted question names
such as `sentiment.praise`. A three-item probe through the experiment script then
confirmed that all three question types (yes/no, choice, score) work against the real
API; the score type had not been run live before that.