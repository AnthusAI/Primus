# Design and open questions

Part of the [Jev decision-head lab notes](index.md). Results are on the
[experiment 1 page](experiment-1-sentiment.md).

## What exists today

Built and covered by specs (mocked Jev client, no network):

- `JevScorecard` and `JevScore`: one Jev request per item for every score on the
  scorecard; per-score calls and `Score.predict()` are served from that one cached
  response, including concurrent calls (they await the same in-flight request).
- Elements and a decision block on `JevScore`: elements ride in the same request
  under namespaced question names; an optional decision turns element answers into
  the final value, a confidence and a short explanation. Two serving models exist,
  a multinomial logistic model and a hand-writable linear threshold rule.
- `plexus/decision_head/`: feature extraction, the model registry, serving,
  calibration metrics and a logistic fitter, all pure functions. Serving code uses
  only the standard library.
- Experiment scripts under `scripts/` (see the results page).

Not built yet: fitting from real feedback (with the sampling correction), calibration
wired into the serving path, the optimizer Procedure integration, the confidence-gated
model, artifact storage for large models, and the `depends_on` fix for whole-scorecard
prediction.

## Configuration shape

A score keeps its own holistic question and gains two optional blocks. With neither,
it behaves exactly as before.

```yaml
name: Objection Handled
class: JevScore
question_type: noul
instructions: Did the agent handle the objection?

elements:
  - key: acknowledged
    question_type: noul
    instructions: Did the agent acknowledge the objection first?
  - key: tone
    question_type: choice
    instructions: What was the agent's tone?
    criteria: {empathetic: null, dismissive: null}

decision:
  model: multinomial_logistic
  classes: ["Yes", "No"]
  features: [self.holistic.logit_p, acknowledged.logit_p, tone.clr.dismissive]
  parameters:
    weights:
      "Yes":
        intercept: -0.5
        self.holistic.logit_p: 1.0
        acknowledged.logit_p: 0.5
        tone.clr.dismissive: -1.0
```

Naming: **elements** are the sub-questions, **features** are the numbers the model
weights. Weights are keyed by feature name, never by position, so adding an element
does not scramble existing weights, and a feature that is absent when serving counts
as zero. Question names on the wire are `<score key>.<element key>`, with
`shared.<key>` for elements several scores reuse. Registering the same shared element
twice is allowed if the definition is identical and an error if it differs.

## Decisions and the reasons for them

- **Jev's economics make elements cheap.** Input tokens are dominated by the text, so
  8 questions cost about 501 tokens per item against about 335 for 2. The same
  decomposition with LLM prompts would multiply cost by the number of elements.
- **Centered log-ratio for choices.** Option probabilities sum to one, so per-option
  log-odds are collinear; regularization then splits weight arbitrarily and two refits
  on the same data give different weights. The centered log-ratio sums to zero and is
  stable.
- **Clip probabilities at 0.01.** Jev's tails are not calibrated and answers flip
  about 1% of the time between identical runs. Without a clip, one flipped answer at
  0.995 versus 0.005 is a swing of more than ten log-odds units.
- **Missing means zero when serving, but training refuses it.** In log-odds space zero
  means no evidence, so a missing feature degrades gracefully. Training on
  imputed-neutral rows would bias a newly added element's weight toward zero and the
  optimizer would conclude its own proposal was useless. Training therefore requires
  full coverage.
- **Weights are versioned with the score.** For small models the fitted weights live
  inline in the score's YAML, so they ride the existing score-version history, champion
  and challenger promotion, diffing and rollback. Plexus has no working artifact store
  for trained models today. Large models (hundreds of megabytes if a text encoder were
  ever added) would need an artifact reference instead; the `parameters:` block and
  `model:` registry leave room for that without a schema break. A head that re-reads
  the raw text would also give up cheap refits and the readable weights, and needs far
  more labels than a feedback set usually has.
- **Any architecture over a fixed feature contract.** Adding a model is one module plus
  one registry entry. Because features are cached, comparing architectures on the same
  folds costs no Jev calls.
- **Sampling correction (not yet exercised).** Feedback datasets are sampled per
  confusion-matrix cell, which makes the training class balance synthetic. Selection is
  on the pair of the previous prediction and the human label, so class weighting is the
  wrong fix; the plan is per-cell inverse-probability weights, guarded by the Kish
  effective sample size rather than the raw item count. Skipping it produces a head that
  looks excellent on the sampled evaluation and over-predicts the rare class in
  production.
- **Calibrate on out-of-fold predictions only**, and choose the method by sample size:
  isotonic regression memorizes on small samples. Experiment 1 also showed it can make an
  already-calibrated head slightly worse.
- **Confidence is a gate, not just a feature.** Jev's `confidence` says how reliable the
  answer is, while its probabilities say what the text suggests. A model that multiplies
  each element's evidence by a learned function of its confidence would generalize the
  additive version. Not yet tested; the experiment only added confidences as plain
  features (HEC).

## Open questions and untested claims

1. **Do elements built from real guidelines find hidden factors?** Experiment 1's
   elements were restatements of sentiment. The plan's premise, that feedback surfaces
   factors stakeholders never named, needs a scorecard with real feedback.
2. **Sampling correction on real feedback.** Untested; the sentiment set has no
   confusion-cell sampling.
3. **Does answering a question inside a larger request change its answer?** The
   holistic answer moved on 1.26% of items against about 1% run-to-run, so the effect
   is small if real. It matters for caching factor answers per question across
   different question sets, and it should be checked for element answers too, not just
   the holistic one.
4. **How much of the gain is averaging noise?** A control would ask the holistic
   question several times in different wordings and average them, then compare with
   distinct elements.
5. **Feature importance the optimizer can trust.** Raw coefficients mislead (see the
   intensity example). Standardized coefficients or permutation importance are needed
   before an optimizer reasons about which factors matter.
6. **The capability ladder.** The plan gates model class and calibration method on
   effective sample size. Experiment 1 gives one data point (logistic wins below about
   250 items, boosting from about 500) on clean data; real thresholds need real
   feedback.
7. **Serving-time stability.** With about 1% answer noise and many elements, a
   noticeable share of items has at least one flipped element. Whether the final value
   flips depends on the weights and the distance to the threshold. Measure it by
   running a holdout twice.
8. **Mixed scorecards.** One non-Jev score on a scorecard currently drops back to one
   request per Jev score, silently losing the shared request. Whole-scorecard
   prediction also ignores `depends_on` gating, so a score that should be skipped still
   gets a value.
9. **Explanations.** The head emits a number and a list of top contributions, not prose.
   Reviewers react to explanations and their reactions are the training signal, so the
   quality of the generated explanation matters for the feedback loop.

## Next experiments

- Repeat on a real Plexus scorecard's feedback to test the sampling correction and the
  hidden-factor premise.
- Confidence-gated model against the additive logistic head on the same folds.
- The repeated-question control from item 4.
- Reliability diagrams and a serving-stability run, for the article figures.