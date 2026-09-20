"""Feature: Jev whole-scorecard prediction.

One Jev request answers every question on the scorecard, and individual
Score.predict() calls are served from that one cached response.
"""
import asyncio

import pytest

from plexus.jev import JevSession
from plexus.JevScorecard import JevScorecard
from plexus.scores.JevScore import JevScore
from plexus.scores.Score import Score


class FakeUsage:
    def model_dump(self):
        return {"input_tokens": 300, "output_tokens": 40}


class FakeResponse:
    model = "jev-test"
    usage = FakeUsage()

    def __init__(self, answers):
        self.answers = answers


class FakeClient:
    """Stands in for AsyncTypeSafeClient; records every request."""

    def __init__(self, delay=0.0, fail_first=False):
        self.calls = []
        self.delay = delay
        self.fail_first = fail_first

    async def system_one(self, *, state, questions):
        self.calls.append({"state": state, "questions": questions})
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_first and len(self.calls) == 1:
            raise RuntimeError("boom")
        positive = "good" in state["text"]
        answers = {}
        for name, question in questions.items():
            if question["type"] == "noul":
                answers[name] = {"type": "noul", "noul": 0.9 if positive else 0.2}
            elif question["type"] == "choice":
                top = "positive" if positive else "negative"
                answers[name] = {
                    "type": "choice",
                    "choice": top,
                    "confidence": 0.8,
                    "probabilities": {"positive": 0.9 if positive else 0.1,
                                      "negative": 0.1 if positive else 0.9},
                }
            else:
                answers[name] = {
                    "type": "score", "score": 1.6, "confidence": 0.7,
                    "legend": {"0": "low", "1": "mid", "2": "high"},
                    "probabilities": {"0": 0.1, "1": 0.3, "2": 0.6},
                }
        return FakeResponse(answers)


SCORE_CONFIGS = [
    {"name": "Positive", "key": "positive", "id": "id-positive", "class": "JevScore",
     "question_type": "noul",
     "instructions": "Is the overall sentiment of this text positive?"},
    {"name": "Sentiment", "key": "sentiment", "id": "id-sentiment", "class": "JevScore",
     "question_type": "choice",
     "instructions": "What is the overall sentiment of this text?",
     "criteria": {"positive": None, "negative": None}},
]


def make_scorecard(client):
    session = JevSession(client_factory=lambda: client)
    scorecard = JevScorecard(scorecard="Jev test", jev_session=session)
    for config in SCORE_CONFIGS:
        scorecard.register_jev_score({**config, "scorecard_name": "Jev test"})
    return scorecard, session


@pytest.mark.asyncio
async def test_whole_scorecard_prediction_sends_one_request():
    """Scenario: Whole-scorecard prediction sends one request."""
    client = FakeClient()
    scorecard, _ = make_scorecard(client)

    results = await scorecard.predict_scorecard("a good day")

    assert len(client.calls) == 1
    assert set(client.calls[0]["questions"]) == {"Positive", "Sentiment"}
    assert results["Positive"].value == "Yes"
    assert results["Sentiment"].value == "positive"


@pytest.mark.asyncio
async def test_sequential_score_predictions_share_one_request():
    """Scenario: Individual score predictions share the cached result."""
    client = FakeClient()
    scorecard, _ = make_scorecard(client)
    text = "a good day"

    positive = await scorecard.get_score_result(
        scorecard="Jev test", score="Positive", text=text, metadata={},
        modality=None, results=[])
    sentiment = await scorecard.get_score_result(
        scorecard="Jev test", score="Sentiment", text=text, metadata={},
        modality=None, results=[])

    assert len(client.calls) == 1
    assert positive[0].value == "Yes"
    assert sentiment[0].value == "positive"


@pytest.mark.asyncio
async def test_concurrent_score_predictions_share_one_request():
    client = FakeClient(delay=0.05)
    scorecard, _ = make_scorecard(client)

    first, second = await asyncio.gather(
        scorecard.get_score_result(scorecard="Jev test", score="Positive",
                                   text="bad day", metadata={}, modality=None, results=[]),
        scorecard.get_score_result(scorecard="Jev test", score="Sentiment",
                                   text="bad day", metadata={}, modality=None, results=[]),
    )

    assert len(client.calls) == 1
    assert first[0].value == "No"
    assert second[0].value == "negative"


@pytest.mark.asyncio
async def test_score_predict_delegates_to_scorecard_cache():
    client = FakeClient()
    scorecard, _ = make_scorecard(client)
    positive = await scorecard.jev_score_instance("Positive")
    sentiment = await scorecard.jev_score_instance("Sentiment")

    await positive.predict(None, Score.Input(text="a good day"))
    await sentiment.predict(None, Score.Input(text="a good day"))

    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_different_item_triggers_new_request():
    """Scenario: A different item triggers a new request."""
    client = FakeClient()
    scorecard, _ = make_scorecard(client)

    await scorecard.predict_scorecard("a good day")
    await scorecard.predict_scorecard("a bad day")
    await scorecard.predict_scorecard("a good day")

    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_failed_request_is_not_cached():
    client = FakeClient(fail_first=True)
    scorecard, _ = make_scorecard(client)

    with pytest.raises(RuntimeError):
        await scorecard.predict_scorecard("a good day")
    results = await scorecard.predict_scorecard("a good day")

    assert len(client.calls) == 2
    assert results["Positive"].value == "Yes"


@pytest.mark.asyncio
async def test_cache_is_bounded():
    client = FakeClient()
    session = JevSession(client_factory=lambda: client, max_cache_entries=2)
    scorecard = JevScorecard(scorecard="Jev test", jev_session=session)
    scorecard.register_jev_score({**SCORE_CONFIGS[0], "scorecard_name": "Jev test"})

    for text in ("one", "two", "three", "one"):
        await scorecard.predict_scorecard(text)

    assert len(client.calls) == 4


@pytest.mark.asyncio
async def test_score_entire_text_uses_one_request_for_all_scores():
    client = FakeClient()
    scorecard, _ = make_scorecard(client)

    results = await scorecard.score_entire_text(text="a good day", metadata={})

    assert len(client.calls) == 1
    assert {name: r.value for name, r in results.items()} == {
        "id-positive": "Yes", "id-sentiment": "positive"}


@pytest.mark.asyncio
async def test_usage_is_recorded_once_per_real_request():
    client = FakeClient()
    scorecard, session = make_scorecard(client)

    await scorecard.predict_scorecard("a good day")
    await scorecard.predict_scorecard("a good day")

    assert session.requests_sent == 1
    assert session.input_tokens == 300


def test_yaml_scorecard_with_only_jev_scores_is_a_jev_scorecard(tmp_path):
    """Scenario: A scorecard made only of JevScores is a JevScorecard."""
    import yaml

    path = tmp_path / "jev.yaml"
    path.write_text(yaml.safe_dump({"name": "Jev yaml", "key": "jev-yaml",
                                    "scores": SCORE_CONFIGS}))

    from plexus.Scorecard import Scorecard
    scorecard_class = Scorecard.create_from_yaml(str(path))

    assert issubclass(scorecard_class, JevScorecard)
    assert isinstance(scorecard_class(scorecard="Jev yaml"), JevScorecard)


def test_api_scorecard_with_only_jev_scores_is_a_jev_scorecard():
    from plexus.Scorecard import Scorecard

    scorecard = Scorecard.create_instance_from_api_data(
        "sc-1", {"name": "Jev api"}, [dict(c) for c in SCORE_CONFIGS])

    assert isinstance(scorecard, JevScorecard)


def test_mixed_scorecard_stays_a_plain_scorecard(tmp_path):
    import yaml

    from plexus.Scorecard import Scorecard
    path = tmp_path / "mixed.yaml"
    other = {"name": "Other", "key": "other", "id": "id-other", "class": "KeywordClassifier",
             "keywords": ["x"]}
    path.write_text(yaml.safe_dump({"name": "Mixed", "key": "mixed",
                                    "scores": [SCORE_CONFIGS[0], other]}))

    assert not issubclass(Scorecard.create_from_yaml(str(path)), JevScorecard)
