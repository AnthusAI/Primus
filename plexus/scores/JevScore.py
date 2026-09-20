import re
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from plexus.decision_head.features import HOLISTIC, available_terms, extract_terms, split_feature
from plexus.decision_head.model import decide, explain, validate_head
from plexus.jev import JevAnswers, JevSession, build_question
from plexus.scores.Score import Score

QuestionType = Literal["noul", "choice", "score"]
RESERVED_ELEMENT_KEYS = {"self", "shared"}
DEFAULT_CLIP = 0.01


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


class ElementSpec(BaseModel):
    """A sub-question answered in the same Jev request as the score's own question."""

    key: str
    question_type: QuestionType
    instructions: Optional[Union[str, dict, list]] = None
    criteria: Optional[Union[Dict[str, Any], List[Any]]] = None

    @field_validator("key")
    @classmethod
    def _valid_key(cls, key: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", key) or key in RESERVED_ELEMENT_KEYS:
            raise ValueError(
                f"element key {key!r} must be letters, digits, '_' or '-' (no dots) "
                f"and not one of {sorted(RESERVED_ELEMENT_KEYS)}")
        return key


class DecisionSpec(BaseModel):
    """A decision model over element answers. ``parameters.weights`` holds fitted values."""

    model_config = ConfigDict(protected_namespaces=())

    model: str
    classes: List[str]
    features: List[str]
    parameters: Dict[str, Any]
    positive_class: Optional[str] = None
    threshold: float = 0.0
    transform: Dict[str, Any] = {"probability": "logit", "clip": DEFAULT_CLIP}
    missing_feature_policy: Literal["zero"] = "zero"
    abstain_band: float = 0.0
    version: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    calibration: Optional[Dict[str, Any]] = None

    @field_validator("features", mode="before")
    @classmethod
    def _feature_names(cls, features):
        return [f["name"] if isinstance(f, dict) else f for f in features or []]

    def head(self) -> dict:
        return {
            "model": self.model, "classes": self.classes, "weights": self.parameters.get("weights"),
            "positive_class": self.positive_class, "threshold": self.threshold,
            "abstain_band": self.abstain_band,
        }


class JevScore(Score):
    """
    A score answered by the TypeSafe Jev (System One) model.

    Each JevScore defines one typed question (``noul`` yes/no, ``choice``, or
    ``score`` rubric). Jev answers all the questions on a scorecard in a single
    request, so a JevScore never calls Jev on its own when it belongs to a
    ``JevScorecard``: it asks the scorecard's shared ``JevSession`` for the
    whole-scorecard answers (cached per item) and pulls out its own.

    A score may also declare ``elements``: further questions that ride in the same
    request as evidence rather than verdicts. Their answers are recorded in
    ``metadata["jev"]["elements"]``. With a ``decision`` block, a small model over
    the element answers (and optionally Jev's own answer to the score's question,
    ``self.holistic.*``) produces the final value and a confidence. The decision's
    ``classes`` are the final labels, so ``answer_map`` does not apply to it.

    Example configuration:

        - name: Objection Handled
          class: JevScore
          question_type: noul
          instructions: Did the agent handle the objection?
          elements:
            - {key: acknowledged, question_type: noul,
               instructions: Did the agent acknowledge the objection first?}
          decision:
            model: multinomial_logistic
            classes: ["Yes", "No"]
            features: [self.holistic.logit_p, acknowledged.logit_p]
            parameters:
              weights: {"Yes": {intercept: -0.5, self.holistic.logit_p: 1.0,
                                acknowledged.logit_p: 0.5}}
    """

    class Parameters(Score.Parameters):
        model_config = ConfigDict(protected_namespaces=())

        question_type: Optional[QuestionType] = None
        instructions: Optional[Union[str, dict, list]] = None
        criteria: Optional[Union[Dict[str, Any], List[Any]]] = None
        # Optional renaming of result values, e.g. {"Yes": "Pass", "No": "Fail"}.
        answer_map: Optional[Dict[str, str]] = None
        elements: Optional[List[ElementSpec]] = None
        # Elements registered as ``shared.<key>`` so several scores can reuse one question.
        shared_elements: Optional[List[ElementSpec]] = None
        decision: Optional[DecisionSpec] = None

        @model_validator(mode="after")
        def _validate_elements_and_decision(self):
            if self.question_type is None and self.decision is None:
                raise ValueError("a JevScore needs a question_type or a decision")
            for label, specs in (("elements", self.elements), ("shared_elements", self.shared_elements)):
                keys = [spec.key for spec in specs or []]
                if len(keys) != len(set(keys)):
                    raise ValueError(f"{label} has duplicate keys: {keys}")
            if self.decision is not None:
                self._validate_decision()
            return self

        def _validate_decision(self):
            refs: Dict[str, Tuple[str, Any]] = {}
            if self.question_type is not None:
                refs[HOLISTIC] = (self.question_type, self.criteria)
            for spec in self.elements or []:
                refs[spec.key] = (spec.question_type, spec.criteria)
            for spec in self.shared_elements or []:
                refs[f"shared.{spec.key}"] = (spec.question_type, spec.criteria)
            for feature in self.decision.features:
                ref, term = split_feature(feature)
                if ref not in refs:
                    raise ValueError(
                        f"decision feature {feature!r} refers to {ref!r}, which is not a declared "
                        f"element (declared: {sorted(refs)})")
                if term not in available_terms(*refs[ref]):
                    raise ValueError(f"decision feature {feature!r}: {ref!r} has no term {term!r}")
            problems = validate_head(self.decision.head(), features=self.decision.features)
            if problems:
                raise ValueError("invalid decision: " + "; ".join(problems))

    def __init__(self, **parameters):
        super().__init__(**parameters)
        self._session: Optional[JevSession] = None

    @classmethod
    async def create(cls, **parameters) -> "JevScore":
        return cls(**parameters)

    @property
    def question_name(self) -> str:
        return self.parameters.name or self.parameters.key

    def question(self) -> Optional[dict]:
        """The score's own (holistic) question, if it has one."""
        if self.parameters.question_type is None:
            return None
        return build_question(
            question_type=self.parameters.question_type,
            instructions=self.parameters.instructions,
            criteria=self.parameters.criteria,
        )

    def _element_questions(self) -> List[Tuple[str, str, ElementSpec]]:
        """``(element ref, qualified question name, spec)`` for every element."""
        slug = _slug(self.parameters.key or self.parameters.name)
        own = [(spec.key, f"{slug}.{spec.key}", spec) for spec in self.parameters.elements or []]
        shared = [(f"shared.{spec.key}", f"shared.{spec.key}", spec)
                  for spec in self.parameters.shared_elements or []]
        return own + shared

    def attach_session(self, session: JevSession) -> None:
        """Share a scorecard's session so this score is answered from its cached request."""
        self._session = session
        holistic = self.question()
        if holistic is not None:
            session.register_question(self.question_name, holistic, owner=self.question_name)
        for _, name, spec in self._element_questions():
            session.register_question(
                name,
                build_question(question_type=spec.question_type,
                               instructions=spec.instructions, criteria=spec.criteria),
                owner=self.question_name)

    def _session_or_standalone(self) -> JevSession:
        if self._session is None:
            self.attach_session(JevSession())
        return self._session

    async def predict(self, context, model_input: Score.Input) -> Score.Result:
        session = self._session_or_standalone()
        return self.result_from_answers(await session.answer_all(model_input.text))

    def result_from_answers(self, jev: JevAnswers) -> Score.Result:
        decision = self.parameters.decision
        if decision is None:
            answer = jev.answers[self.question_name]
            value, confidence, detail = self._interpret(answer)
            if self.parameters.answer_map:
                value = self.parameters.answer_map.get(value, value)
            metadata = {"jev": detail}
            explanation = None
        else:
            value, confidence, decision_detail = decide(self._feature_vector(jev), decision.head())
            explanation = explain(value, confidence, decision_detail)
            detail = {}
            metadata = {"jev": detail, "decision": decision_detail}
        detail.update({"model": jev.model, "usage": jev.usage})
        elements = self._element_answers(jev)
        if elements:
            detail["elements"] = elements
        return Score.Result(
            parameters=self.parameters,
            value=value,
            confidence=confidence,
            explanation=explanation,
            metadata=metadata,
        )

    def _element_answers(self, jev: JevAnswers) -> Dict[str, dict]:
        return {
            ref: jev.answers[name]
            for ref, name, _ in self._element_questions() if name in jev.answers
        }

    def _feature_vector(self, jev: JevAnswers) -> Dict[str, float]:
        """Named features for the declared decision features; unanswered ones are left out
        (they contribute zero, which in logit space means no evidence)."""
        decision = self.parameters.decision
        eps = float(decision.transform.get("clip", DEFAULT_CLIP))
        sources: Dict[str, Tuple[str, str, Any]] = {}
        if self.parameters.question_type is not None:
            sources[HOLISTIC] = (self.question_name, self.parameters.question_type,
                                 self.parameters.criteria)
        for ref, name, spec in self._element_questions():
            sources[ref] = (name, spec.question_type, spec.criteria)

        terms_by_ref: Dict[str, Dict[str, float]] = {}
        vector: Dict[str, float] = {}
        for feature in decision.features:
            ref, term = split_feature(feature)
            if ref not in terms_by_ref:
                name, question_type, criteria = sources[ref]
                answer = jev.answers.get(name)
                terms_by_ref[ref] = (
                    extract_terms(answer, question_type, criteria, eps) if answer else {})
            if term in terms_by_ref[ref]:
                vector[feature] = terms_by_ref[ref][term]
        return vector

    def _interpret(self, answer: dict):
        kind = answer["type"]
        if kind == "noul":
            probability = answer["noul"]
            value = "Yes" if probability >= 0.5 else "No"
            return value, max(probability, 1 - probability), {"type": kind, "noul": probability}
        if kind == "choice":
            choice = answer["choice"]
            probabilities = answer.get("probabilities", {})
            return choice, probabilities.get(choice), {
                "type": kind,
                "probabilities": probabilities,
                "confidence": answer.get("confidence"),
            }
        if kind == "score":
            probabilities = answer.get("probabilities", {})
            return str(answer["score"]), answer.get("confidence"), {
                "type": kind,
                "score": answer["score"],
                "legend": answer.get("legend"),
                "probabilities": probabilities,
                "confidence": answer.get("confidence"),
            }
        raise ValueError(f"Unsupported Jev answer type: {kind!r}")

    def load_context(self, context=None):
        pass

    def predict_validation(self):
        pass

    def register_model(self):
        pass

    def save_model(self):
        pass
