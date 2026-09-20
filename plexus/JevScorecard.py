from typing import Dict, Optional

from plexus.Registries import ScoreRegistry
from plexus.Scorecard import Scorecard
from plexus.jev import JevSession
from plexus.scores.JevScore import JevScore
from plexus.scores.Score import Score


class JevScorecard(Scorecard):
    """
    A scorecard whose scores are all answered by one Jev (System One) request.

    Jev processes every question on the scorecard at once, so the preferred entry
    point is ``predict_scorecard(text)``. Per-score calls (``Score.predict()`` or
    ``get_score_result``) still work: they run the whole-scorecard request, keep
    it in the shared ``JevSession`` cache, and return just the one score, so
    asking for several scores of the same item in sequence (or concurrently)
    sends a single request.
    """

    def __init__(self, *, jev_session: Optional[JevSession] = None, **kwargs):
        super().__init__(**kwargs)
        if type(self) is JevScorecard and kwargs.get("api_data") is None:
            # Built directly rather than from YAML: the base class would share one registry
            # across every instance, leaking scores between scorecards.
            self.score_registry = ScoreRegistry()
        self.jev_session = jev_session or JevSession()
        self._jev_scores: Dict[str, JevScore] = {}
        if not hasattr(self, "scores") or not isinstance(self.scores, list):
            self.scores = []

    def register_jev_score(self, config: dict) -> None:
        """Register a JevScore configuration (used for programmatic scorecards)."""
        self.score_registry.register(
            cls=JevScore,
            properties=config,
            name=config.get("name"),
            key=config.get("key"),
            id=config.get("id"),
        )
        if config.get("name") not in {s.get("name") for s in self.scores}:
            self.scores.append(config)

    def _jev_score_configs(self):
        seen = set()
        for properties in list(self.score_registry._properties_by_name.values()):
            if properties.get("class") == "JevScore" and id(properties) not in seen:
                seen.add(id(properties))
                yield properties

    async def _prepare(self) -> None:
        """Create every JevScore and register its question so requests cover the whole scorecard."""
        for properties in self._jev_score_configs():
            name = properties["name"]
            if name in self._jev_scores:
                continue
            instance = await JevScore.create(
                **{**properties, "scorecard_name": self.scorecard_identifier, "score_name": name}
            )
            instance.attach_session(self.jev_session)
            self._jev_scores[name] = instance

    async def jev_score_instance(self, score: str) -> Optional[JevScore]:
        await self._prepare()
        properties = self.score_registry.get_properties(score)
        return self._jev_scores.get(properties["name"]) if properties else None

    async def predict_scorecard(
        self, text: str, metadata: Optional[dict] = None
    ) -> Dict[str, Score.Result]:
        """Answer every score on the scorecard for ``text`` with one Jev request."""
        await self._prepare()
        answers = await self.jev_session.answer_all(text)
        return {
            name: score.result_from_answers(answers)
            for name, score in self._jev_scores.items()
        }

    async def get_score_result(self, *, score, **kwargs):
        instance = await self.jev_score_instance(score)
        if instance is not None:
            # Reuse the session-attached instance so the base flow (dependencies,
            # processors, cost tracking) runs against it rather than a fresh one.
            self._score_instance_cache.setdefault(score, instance)
        return await super().get_score_result(score=score, **kwargs)
