#!/usr/bin/env python
"""Live smoke test for JevScorecard against the Jev-Calibration sentiment dataset.

Runs items through the scorecard by asking for each score separately (the
``Score.predict()`` path) and verifies that one Jev request served both scores.

    python scripts/jev_scorecard_smoke.py --project ~/Projects/Jev-Calibration --limit 50

Requires ``typesafe-sdk`` and ``TYPESAFE_API_KEY`` (read from the environment or
from ``<project>/.env``; the key is never printed).
"""
import argparse
import asyncio
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plexus.jev import JevSession  # noqa: E402
from plexus.JevScorecard import JevScorecard  # noqa: E402

SCORES = [
    {"name": "Positive", "key": "positive", "id": "jev-positive", "class": "JevScore",
     "question_type": "noul", "instructions": "Is the overall sentiment of this text positive?"},
    {"name": "Sentiment", "key": "sentiment", "id": "jev-sentiment", "class": "JevScore",
     "question_type": "choice", "instructions": "What is the overall sentiment of this text?",
     "criteria": {"positive": None, "negative": None}},
]

# With --elements the Sentiment score also asks two evidence questions in the same request and
# decides through a hand-authored head. Weight 2.0 on the two-option CLR feature reproduces
# Jev's own choice exactly (clr = half the log-odds), so accuracy should not move.
ELEMENTS = [
    {"key": "strong_language", "question_type": "noul",
     "instructions": "Does the text use strong or emphatic language?"},
    {"key": "emotional_tone", "question_type": "choice",
     "instructions": "What is the emotional tone of this text?",
     "criteria": {"warm": None, "cold": None, "neutral": None}},
]
DECISION = {
    "model": "multinomial_logistic", "classes": ["positive", "negative"],
    "features": ["self.holistic.clr.positive", "strong_language.logit_p"],
    "parameters": {"weights": {"positive": {
        "intercept": 0.0, "self.holistic.clr.positive": 2.0, "strong_language.logit_p": 0.0}}},
}

FILES = {f"{tier}_{label}.txt": (label, tier)
         for tier in ("strong", "medium", "weak", "neutral") for label in ("positive", "negative")}


def load_rows(project: Path):
    import hashlib
    rows, seen = [], set()
    for filename, (expected, tier) in FILES.items():
        for line in (project / "dataset" / filename).read_text(encoding="utf-8").splitlines():
            text = line.strip()
            eid = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
            if text and not text.startswith("#") and eid not in seen:
                seen.add(eid)
                rows.append({"id": eid, "text": text, "expected": expected, "tier": tier})
    return rows


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="~/Projects/Jev-Calibration")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--test-split", action="store_true", help="use only the held-out test split")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--elements", action="store_true",
                        help="add elements and a decision to the Sentiment score")
    args = parser.parse_args()
    project = Path(args.project).expanduser()
    load_dotenv(project / ".env")

    rows = load_rows(project)
    if args.test_split:
        splits = json.loads((project / "data" / "splits.json").read_text())
        rows = [r for r in rows if splits.get(r["id"]) == "test"]
    random.Random(42).shuffle(rows)
    rows = rows[: args.limit]

    reference = {}
    raw = project / "data" / "jev_raw.jsonl"
    if raw.exists():
        for line in raw.read_text().splitlines():
            record = json.loads(line)
            reference[record["id"]] = record["answers"]

    session = JevSession()
    scorecard = JevScorecard(scorecard="Jev sentiment", jev_session=session)
    for config in SCORES:
        if args.elements and config["key"] == "sentiment":
            config = {**config, "elements": ELEMENTS, "decision": DECISION}
        scorecard.register_jev_score({**config, "scorecard_name": "Jev sentiment"})

    sem = asyncio.Semaphore(args.concurrency)
    correct = defaultdict(lambda: [0, 0])
    mismatches = 0

    async def one(row):
        nonlocal mismatches
        async with sem:
            async def ask(score):
                result = await scorecard.get_score_result(
                    scorecard="Jev sentiment", score=score, text=row["text"],
                    metadata={}, modality=None, results=[])
                return result[0]
            positive, sentiment = await asyncio.gather(ask("Positive"), ask("Sentiment"))
        predicted = sentiment.value
        for bucket in ("all", row["tier"]):
            correct[bucket][1] += 1
            correct[bucket][0] += predicted == row["expected"]
        ref = reference.get(row["id"])
        if ref and ref["sentiment"]["choice"] != predicted:
            mismatches += 1

    await asyncio.gather(*(one(r) for r in rows))

    print(f"items={len(rows)} requests_sent={session.requests_sent} "
          f"(expected {len(rows)}, not {2 * len(rows)}) input_tokens={session.input_tokens}")
    for bucket, (ok, total) in sorted(correct.items()):
        print(f"  {bucket:8s} choice accuracy {ok}/{total} = {ok / total:.3f}")
    if reference:
        print(f"choice answers differing from research run: {mismatches}/{len(rows)}")
    assert session.requests_sent == len(rows), "expected exactly one request per item"


if __name__ == "__main__":
    asyncio.run(main())
