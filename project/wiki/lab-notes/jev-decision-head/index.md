# Lab notes: layering an ML model on top of Jev

Started 2026-09-20. Status: experiment 1 complete, everything else open.

These notes record what we learned while building a supervised "decision head" on
top of TypeSafe's Jev (System One) model inside Plexus. They are written to become
an article on how to layer your own ML model over Jev, with Plexus as the worked
example. Numbers here are from real runs; where something is untested it says so.

Pages:

- [Experiment 1: sentiment dataset](experiment-1-sentiment.md): setup, full results,
  controls, learning curve, and how to reproduce.
- [Design and open questions](design-and-open-questions.md): the architecture, why
  each decision was made, what is built, and what is not yet tested.

## The idea

Jev answers many typed questions about one piece of text in a single request, and the
cost is dominated by the text, not the questions. So a Plexus score can ask Jev its
usual holistic question plus several sub-questions ("elements") in that same request
for very little extra cost. A small model of our own then takes all of Jev's answers
as numeric features and makes the final decision, learning how much to trust each
element from human labels. The plan is for an optimizer Procedure to keep refitting
that model from feedback, and to propose new elements over time.

Vocabulary used throughout:

- **Score**: what Plexus already calls a score (for example "Objection Handled").
- **Element**: one sub-question Jev answers in the same request as the score's own
  question. Evidence, not a verdict.
- **Feature**: one number the decision model weights. A yes/no element gives one
  feature; a choice element with K options gives K.
- **Holistic answer**: Jev's answer to the score's own question, which can itself be
  a feature.
- **Decision**: the model that turns features into the final value and a confidence.

## Headline results (experiment 1)

Held-out test split of 3,521 sentiment items. Heads were fit on a separate 5,280-item
split. Jev model version jev-1.13.0.

| Final answer comes from | Accuracy | Weak-tier accuracy | ECE, raw |
|---|---|---|---|
| Jev holistic answer | 0.760 | 0.739 | 0.153 |
| Jev holistic answer, recalibrated (temperature then isotonic) | 0.760 | 0.739 | 0.014 |
| Logistic model on the holistic answer only | 0.758 | 0.736 | 0.062 |
| Logistic model on the 7 elements only | 0.841 | 0.894 | 0.011 |
| Logistic model on holistic answer plus 7 elements | 0.843 | 0.896 | 0.002 |
| Gradient boosting on the same features plus confidences | 0.872 | 0.939 | 0.016 |

ECE is expected calibration error, lower is better. Its noise floor at this sample
size is roughly 0.01.

1. **The elements raise accuracy, and the gain is not a recalibration effect.**
   Fitting a model to the holistic answer alone leaves accuracy unchanged (0.758).
   Adding the elements gives +6.7 to +9.8 points (paired bootstrap 95% interval).
2. **The extra elements did not change Jev's own answer, but they changed ours.**
   Jev's holistic choice differed from an earlier two-question run on 1.26% of items,
   against about 1% run-to-run noise. The improvement comes from combining the
   element answers, not from a better holistic answer. The model given only the
   elements, with no holistic answer at all, scores 0.841 against 0.843 with it.
3. **The head is well calibrated without any final calibration step.** Raw ECE 0.002
   for the elements-plus-holistic logistic model, against 0.153 for Jev's own
   confidence and 0.014 for Jev after two-stage calibration. Its Brier score is also
   better (0.103 against 0.140), so it separates the classes better and is not merely
   better calibrated. Applying isotonic calibration on top of the fitted head made
   ECE slightly worse (0.010 to 0.015), so at this size the extra step adds noise.
4. **It helps with few labels.** Subsampling the fit set: +4.6 accuracy points over
   Jev at 60 labels and +6.4 at 250 for the logistic head. Gradient boosting only
   overtakes it at about 500 labels, and its calibration is worse below that.
5. **Adding questions is cheap.** 7 elements plus the holistic question averaged 501
   input tokens per item, against about 335 for two questions.

## Read these before believing it

- **The elements mostly restate sentiment.** Praise, criticism and would-recommend
  are the same signal in different words, so part of the gain is probably averaging
  several noisy readings. Whether elements built from real stakeholder guidelines
  surface genuinely hidden factors is untested.
- **The strongest weight is not a discovered concept.** Emotional intensity carries
  the largest coefficient, but it is nearly identical for positive and negative items
  within each tier; it acts as a tier offset. Coefficients on unstandardized features
  are also not comparable as importances. See the results page.
- **The data is unusually clean.** Labels are near-deterministic by construction and
  fit and test splits are identically distributed. Real feedback data is sampled by
  confusion-matrix cell, which this experiment could not exercise.
- **The neutral tier has no recoverable signal** (about 0.5 to 0.57 for every model).
  That is a ceiling of about 0.87 overall for this dataset, not a modeling failure.

## A trap worth putting in the article

A first run on a partial answer cache reported 0.966 accuracy and gave intensity a
coefficient of about -7.5. It was an artifact: the cache had been filled in file
order, so it contained almost no weak-tier negatives and the model learned "mild
emotion means positive". The clean full run gives 0.843. The lesson is to check that
your fit sample is not confounded with how you assembled it, and that a suspiciously
large weight deserves a look at the data behind it before a story.

## Article angle

Working thesis: Jev gives you many cheap, well-formed opinions about a piece of text;
a small supervised model gives you the judgment about which opinions to trust. The
combination keeps Jev's economics and adds calibration and accuracy that Jev alone
does not have, and the model's weights are an artifact a human can read.

Possible structure:

1. Why one holistic question leaves accuracy on the table.
2. Elements: asking seven questions for the price of two.
3. From answers to features (centered log-ratio for choices, clipping, why missing
   means zero when serving but is refused when training).
4. The controls that matter: recalibrate the holistic answer alone before crediting
   the elements.
5. Calibration for free, and when isotonic hurts.
6. How few labels you need, and when a bigger model earns its place.
7. What went wrong: the partial-cache artifact and the misleading weights.
8. Wiring it into Plexus so an optimizer can keep refitting it from feedback.

Figures still to produce: reliability diagrams for Jev, Jev recalibrated, and the
fitted head; the learning curve (accuracy and ECE against fit-set size); per-tier
accuracy bars; a plot of holistic-answer stability against the number of questions.