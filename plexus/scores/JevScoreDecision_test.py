"""Feature: JevScore elements and decision model.

A score declares elements (sub-questions answered in the same single Jev
request) and an optional decision model that combines them into the final value.
"""
import math

import pytest

from plexus.JevScorecard import JevScorecard
from plexus.jev import JevSession
from plexus.scores.JevScore import JevScore
from plexus.scores.Score import Score


class _Usage:
    def model_dump(self):
        return {"input_tokens": 100, "output_tokens": 10}


class _Response:
    model = "jev-test"
    usage = _Usage()

    def __init__(self, answers):
        self.answers = answers


class _Client:
    def __init__(self, answers):
        self._answers = answers
        self.calls = []

    async def system_one(self, *, state, questions):
        self.calls.append(questions)
        return _Response(self._answers)


def sigmoid(z):
    return 1 / (1 + math.exp(-z))


def logit(p):
    return math.log(p / (1 - p))


SCORE = {
    "name": "Objection Handled", "key": "objection_handled", "id": "id-obj",
    "class": "JevScore",
    "question_type": "noul",
    "instructions": "Did the agent handle the objection?",
    "elements": [
        {"key": "acknowledged", "question_type": "noul",
         "instructions": "Did the agent acknowledge the objection first?"},
        {"key": "tone", "question_type": "choice", "instructions": "Agent tone?",
         "criteria": {"empathetic": None, "dismissive": None}},
    ],
}

DECISION = {
    "model": "multinomial_logistic",
    "classes": ["Yes", "No"],
    "features": ["self.holistic.logit_p", "acknowledged.logit_p", "tone.clr.dismissive"],
    "parameters": {"weights": {"Yes": {
        "intercept": -0.5,
        "self.holistic.logit_p": 1.0,
        "acknowledged.logit_p": 0.5,
        "tone.clr.dismissive": -1.0,
    }}},
}

ANSWERS = {
    "Objection Handled": {"type": "noul", "noul": 0.7},
    "objection_handled.acknowledged": {"type": "noul", "noul": 0.9},
    "objection_handled.tone": {
        "type": "choice", "choice": "empathetic", "confidence": 0.8,
        "probabilities": {"empathetic": 0.8, "dismissive": 0.2}},
}


def make_score(client, session=None, **overrides):
    score = JevScore(scorecard_name="Jev test", **{**SCORE, **overrides})
    score.attach_session(session or JevSession(client_factory=lambda: client))
    return score


@pytest.mark.asyncio
async def test_elements_ride_in_the_same_single_request_under_namespaced_names():
    client = _Client(ANSWERS)
    score = make_score(client)

    await score.predict(None, Score.Input(text="x"))

    assert len(client.calls) == 1
    assert set(client.calls[0]) == {
        "Objection Handled", "objection_handled.acknowledged", "objection_handled.tone"}


@pytest.mark.asyncio
async def test_without_a_decision_the_holistic_answer_is_the_result_and_elements_are_recorded():
    result = await make_score(_Client(ANSWERS)).predict(None, Score.Input(text="x"))

    assert result.value == "Yes"
    assert result.confidence == pytest.approx(0.7)
    elements = result.metadata["jev"]["elements"]
    assert elements["acknowledged"]["noul"] == 0.9
    assert elements["tone"]["probabilities"]["dismissive"] == 0.2


@pytest.mark.asyncio
async def test_decision_combines_elements_and_holistic_answer_into_value_and_confidence():
    result = await make_score(_Client(ANSWERS), decision=DECISION).predict(
        None, Score.Input(text="x"))

    tone_clr = math.log(0.2) - (math.log(0.2) + math.log(0.8)) / 2
    z = -0.5 + logit(0.7) + 0.5 * logit(0.9) - tone_clr
    assert result.value == "Yes"
    assert result.confidence == pytest.approx(sigmoid(z))
    detail = result.metadata["decision"]
    assert detail["coverage"] == 1.0
    assert detail["top_contributions"][0]["feature"] in DECISION["features"]
    assert "acknowledged.logit_p" in result.explanation or "holistic" in result.explanation


@pytest.mark.asyncio
async def test_decision_can_overrule_the_holistic_answer():
    heavy = {**DECISION, "parameters": {"weights": {"Yes": {
        "intercept": -0.5, "self.holistic.logit_p": 0.1, "tone.clr.dismissive": 5.0}}}}
    answers = {
        **ANSWERS,
        "Objection Handled": {"type": "noul", "noul": 0.3},
        "objection_handled.tone": {
            "type": "choice", "choice": "dismissive",
            "probabilities": {"empathetic": 0.1, "dismissive": 0.9}},
    }

    holistic_only = await make_score(_Client(answers)).predict(None, Score.Input(text="x"))
    with_decision = await make_score(_Client(answers), decision=heavy).predict(
        None, Score.Input(text="x"))

    assert holistic_only.value == "No"
    assert with_decision.value == "Yes"


@pytest.mark.asyncio
async def test_a_missing_element_answer_degrades_to_zero_and_lowers_coverage():
    answers = {k: v for k, v in ANSWERS.items() if k != "objection_handled.tone"}

    result = await make_score(_Client(answers), decision=DECISION).predict(
        None, Score.Input(text="x"))

    z = -0.5 + logit(0.7) + 0.5 * logit(0.9)
    assert result.confidence == pytest.approx(sigmoid(z))
    assert result.metadata["decision"]["coverage"] == pytest.approx(2 / 3)


@pytest.mark.asyncio
async def test_two_scores_can_share_an_element_with_one_registration():
    shared = {"key": "transferred", "question_type": "noul", "instructions": "Was it transferred?"}
    session = JevSession(client_factory=lambda: _Client({}))
    first = JevScore(scorecard_name="s", name="A", key="a", question_type="noul",
                     instructions="?", shared_elements=[shared])
    second = JevScore(scorecard_name="s", name="B", key="b", question_type="noul",
                      instructions="?", shared_elements=[shared])

    first.attach_session(session)
    second.attach_session(session)

    assert list(session.questions).count("shared.transferred") == 1


def test_a_shared_element_with_a_different_body_is_an_authoring_error():
    session = JevSession(client_factory=lambda: _Client({}))
    first = JevScore(scorecard_name="s", name="A", key="a", question_type="noul", instructions="?",
                     shared_elements=[{"key": "t", "question_type": "noul", "instructions": "one"}])
    second = JevScore(scorecard_name="s", name="B", key="b", question_type="noul", instructions="?",
                      shared_elements=[{"key": "t", "question_type": "noul", "instructions": "two"}])
    first.attach_session(session)

    with pytest.raises(ValueError, match="shared.t"):
        second.attach_session(session)


def test_session_registration_is_idempotent_for_identical_bodies_and_rejects_conflicts():
    session = JevSession(client_factory=lambda: _Client({}))
    body = {"type": "noul", "instructions": "q"}
    session.register_question("q", body, owner="A")
    session.register_question("q", dict(body), owner="B")
    with pytest.raises(ValueError, match="q"):
        session.register_question("q", {"type": "noul", "instructions": "different"}, owner="C")


def test_a_decision_referencing_an_undeclared_element_is_rejected():
    bad = {**DECISION, "features": ["nonexistent.logit_p"],
           "parameters": {"weights": {"Yes": {"intercept": 0.0}}}}
    with pytest.raises(ValueError, match="nonexistent"):
        JevScore(scorecard_name="s", **{**SCORE, "decision": bad})


def test_a_decision_using_a_term_the_element_cannot_produce_is_rejected():
    bad = {**DECISION, "features": ["acknowledged.clr.maybe"],
           "parameters": {"weights": {"Yes": {"intercept": 0.0}}}}
    with pytest.raises(ValueError, match="clr.maybe"):
        JevScore(scorecard_name="s", **{**SCORE, "decision": bad})


def test_element_keys_may_not_contain_dots_or_reserved_words():
    for key in ("a.b", "shared", "self"):
        with pytest.raises(ValueError):
            JevScore(scorecard_name="s", **{**SCORE, "elements": [
                {"key": key, "question_type": "noul", "instructions": "?"}]})


def test_a_score_needs_a_holistic_question_or_a_decision():
    with pytest.raises(ValueError):
        JevScore(scorecard_name="s", name="X", instructions="?")


@pytest.mark.asyncio
async def test_a_scorecard_still_sends_one_request_when_scores_have_elements():
    client = _Client({**ANSWERS, "Other": {"type": "noul", "noul": 0.3}})
    session = JevSession(client_factory=lambda: client)
    scorecard = JevScorecard(scorecard="Jev test", jev_session=session)
    scorecard.register_jev_score({**SCORE, "decision": DECISION, "scorecard_name": "Jev test"})
    scorecard.register_jev_score({"name": "Other", "key": "other", "id": "id-other",
                                  "class": "JevScore", "question_type": "noul",
                                  "instructions": "Other?", "scorecard_name": "Jev test"})

    results = await scorecard.predict_scorecard("some text")

    assert len(client.calls) == 1
    assert set(results) == {"Objection Handled", "Other"}
    assert "decision" in results["Objection Handled"].metadata
