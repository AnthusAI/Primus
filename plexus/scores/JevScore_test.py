"""Feature: JevScore turns Jev answers into Score.Result values."""
import pytest

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
        self.calls = 0

    async def system_one(self, *, state, questions):
        self.calls += 1
        return _Response(self._answers)


def make_score(client, **overrides):
    config = {"scorecard_name": "Jev test", "name": "Q", "question_type": "noul",
              "instructions": "Is it good?", **overrides}
    score = JevScore(**config)
    score.attach_session(JevSession(client_factory=lambda: client))
    return score


@pytest.mark.asyncio
async def test_noul_maps_probability_to_yes_no_with_confidence():
    result = await make_score(_Client({"Q": {"type": "noul", "noul": 0.9}})).predict(
        None, Score.Input(text="x"))
    assert result.value == "Yes"
    assert result.confidence == pytest.approx(0.9)

    result = await make_score(_Client({"Q": {"type": "noul", "noul": 0.2}})).predict(
        None, Score.Input(text="x"))
    assert result.value == "No"
    assert result.confidence == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_choice_returns_option_with_probabilities():
    answers = {"Q": {"type": "choice", "choice": "b", "confidence": 0.5,
                     "probabilities": {"a": 0.25, "b": 0.75}}}
    score = make_score(_Client(answers), question_type="choice",
                       criteria={"a": None, "b": None})
    result = await score.predict(None, Score.Input(text="x"))
    assert result.value == "b"
    assert result.confidence == pytest.approx(0.75)
    assert result.metadata["jev"]["probabilities"] == {"a": 0.25, "b": 0.75}
    assert result.metadata["jev"]["confidence"] == 0.5


@pytest.mark.asyncio
async def test_score_question_returns_expected_score_string():
    answers = {"Q": {"type": "score", "score": 1.6, "confidence": 0.7,
                     "legend": {"0": "low", "1": "high"},
                     "probabilities": {"0": 0.4, "1": 0.6}}}
    score = make_score(_Client(answers), question_type="score", criteria=["low", "high"])
    result = await score.predict(None, Score.Input(text="x"))
    assert result.value == "1.6"
    assert result.metadata["jev"]["score"] == 1.6


@pytest.mark.asyncio
async def test_answer_map_renames_values():
    score = make_score(_Client({"Q": {"type": "noul", "noul": 0.9}}),
                       answer_map={"Yes": "Pass", "No": "Fail"})
    result = await score.predict(None, Score.Input(text="x"))
    assert result.value == "Pass"


@pytest.mark.asyncio
async def test_standalone_score_makes_its_own_single_question_request():
    client = _Client({"Q": {"type": "noul", "noul": 0.9}})
    score = make_score(client)
    await score.predict(None, Score.Input(text="x"))
    await score.predict(None, Score.Input(text="x"))
    assert client.calls == 1


def test_invalid_question_type_is_rejected():
    with pytest.raises(ValueError):
        JevScore(scorecard_name="s", name="Q", question_type="essay", instructions="?")
