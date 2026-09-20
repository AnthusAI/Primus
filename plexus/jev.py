"""Whole-scorecard access to the TypeSafe Jev (System One) model.

Jev answers many typed questions about one piece of state in a single request.
``JevSession`` owns the question set for a scorecard and guarantees that one
item costs one request: results are cached per (item, question set), and
concurrent callers for the same item await the same in-flight request.
"""
import asyncio
import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

DEFAULT_MAX_CACHE_ENTRIES = 1024


@dataclass(frozen=True)
class JevAnswers:
    """The answers from one Jev request, as plain dictionaries keyed by question name."""

    answers: Dict[str, dict]
    model: Optional[str] = None
    usage: Optional[dict] = None


def _default_client():
    try:
        from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy
    except ImportError as error:
        raise ImportError(
            "JevScorecard requires the 'typesafe-sdk' package (pip install typesafe-sdk)."
        ) from error
    return AsyncTypeSafeClient(retry=RetryPolicy(max_retries=6, backoff_max=30.0))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _as_dict(value: Any) -> dict:
    return value.model_dump() if hasattr(value, "model_dump") else dict(value)


def build_question(*, question_type: str, instructions: Any = None, criteria: Any = None) -> dict:
    """Build a Jev question in wire form (no SDK import needed)."""
    question: Dict[str, Any] = {"type": question_type}
    if instructions is not None:
        question["instructions"] = instructions
    if question_type == "noul":
        if criteria:
            question["criteria"] = criteria
    else:
        question["criteria"] = criteria
    return question


@dataclass
class JevSession:
    """Shared question set, client, and per-item cache for one Jev scorecard."""

    client_factory: Callable[[], Any] = _default_client
    max_cache_entries: int = DEFAULT_MAX_CACHE_ENTRIES
    questions: Dict[str, dict] = field(default_factory=dict)
    requests_sent: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self):
        self._client = None
        self._cache: "OrderedDict[str, asyncio.Future]" = OrderedDict()
        self._owners: Dict[str, Optional[str]] = {}
        self._fingerprint: Optional[str] = None

    def register_question(self, name: str, question: dict, owner: Optional[str] = None) -> None:
        """Add a question. Re-registering an identical body is a no-op (that is how scores
        share an element); a different body under the same name is an authoring error."""
        existing = self.questions.get(name)
        if existing is not None:
            if _canonical(existing) != _canonical(question):
                raise ValueError(
                    f"Jev question {name!r} is already registered"
                    f"{f' by {self._owners[name]!r}' if self._owners.get(name) else ''}"
                    f" with a different definition{f' (now from {owner!r})' if owner else ''}.")
            return
        self.questions[name] = question
        self._owners[name] = owner
        self._fingerprint = None

    @property
    def question_set_fingerprint(self) -> str:
        """Identifies the question set; any change invalidates every cached answer."""
        if self._fingerprint is None:
            self._fingerprint = hashlib.sha256(_canonical(self.questions).encode("utf-8")).hexdigest()
        return self._fingerprint

    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(
            f"{self.question_set_fingerprint}\x00{text}".encode("utf-8")).hexdigest()

    async def answer_all(self, text: str) -> JevAnswers:
        """Answer every registered question about ``text`` with at most one request."""
        if not self.questions:
            raise ValueError("JevSession has no questions registered.")
        key = self._cache_key(text)
        future = self._cache.get(key)
        if future is not None:
            self._cache.move_to_end(key)
            return await future

        future = asyncio.get_running_loop().create_future()
        self._cache[key] = future
        while len(self._cache) > self.max_cache_entries:
            self._cache.popitem(last=False)
        try:
            future.set_result(await self._request(text, dict(self.questions)))
        except BaseException as error:
            self._cache.pop(key, None)
            future.set_exception(error)
            # Waiters observe the exception; mark it retrieved for the owner-only case.
            future.exception()
            raise
        return future.result()

    async def _request(self, text: str, questions: Dict[str, dict]) -> JevAnswers:
        if self._client is None:
            self._client = self.client_factory()
        response = await self._client.system_one(state={"text": text}, questions=questions)
        self.requests_sent += 1
        usage = _as_dict(response.usage) if getattr(response, "usage", None) else None
        if usage:
            self.input_tokens += usage.get("input_tokens", 0)
            self.output_tokens += usage.get("output_tokens", 0)
        return JevAnswers(
            answers={name: _as_dict(answer) for name, answer in response.answers.items()},
            model=getattr(response, "model", None),
            usage=usage,
        )
