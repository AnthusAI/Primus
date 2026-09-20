#!/usr/bin/env python
"""Does a decision head over Jev element answers beat Jev's own answer?

Two stages on the Jev-Calibration sentiment dataset:

    extract  one Jev request per item asking the holistic question plus element
             questions; answers are cached (resumable) so fitting costs no Jev calls
    fit      fit heads on the dataset's 'calibration' split, evaluate on 'test'

    python scripts/jev_head_experiment.py extract --cache DIR [--limit N]
    python scripts/jev_head_experiment.py fit --cache DIR

Requires typesafe-sdk (extract) and scikit-learn (fit). TYPESAFE_API_KEY comes from
the environment or <project>/.env and is never printed.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jev_scorecard_smoke import load_rows  # noqa: E402

SCORE = {
    "name": "Sentiment", "key": "sentiment", "scorecard_name": "Jev head experiment",
    "question_type": "choice", "instructions": "What is the overall sentiment of this text?",
    "criteria": {"positive": None, "negative": None},
    "elements": [
        {"key": "praise", "question_type": "noul",
         "instructions": "Does the text express praise or approval of something?"},
        {"key": "criticism", "question_type": "noul",
         "instructions": "Does the text express criticism or disapproval of something?"},
        {"key": "mixed", "question_type": "noul",
         "instructions": "Does the text express both positive and negative feelings?"},
        {"key": "irony", "question_type": "noul",
         "instructions": "Is the text sarcastic or ironic?"},
        {"key": "recommend", "question_type": "noul",
         "instructions": "Would the author recommend or endorse the thing being discussed?"},
        {"key": "expectation", "question_type": "choice",
         "instructions": "How did the thing being described compare with what the author expected?",
         "criteria": {"exceeded": None, "met": None, "fell_short": None, "unclear": None}},
        {"key": "intensity", "question_type": "score",
         "instructions": "How strong is the emotion expressed in the text?",
         "criteria": ["none", "mild", "moderate", "strong"]},
    ],
}


def cache_file(cache: Path) -> Path:
    return cache / "element_answers.jsonl"


async def extract(args):
    from plexus.jev import JevSession
    from plexus.scores.JevScore import JevScore

    project = Path(args.project).expanduser()
    load_dotenv(project / ".env")
    rows = load_rows(project)
    if args.limit:
        rows = rows[: args.limit]
    args.cache.mkdir(parents=True, exist_ok=True)
    path = cache_file(args.cache)
    done = {json.loads(line)["id"] for line in path.read_text().splitlines()} if path.exists() else set()
    todo = [r for r in rows if r["id"] not in done]

    session = JevSession()
    JevScore(**SCORE).attach_session(session)
    sem, failures = asyncio.Semaphore(args.concurrency), 0
    handle = path.open("a")

    async def one(row):
        nonlocal failures
        async with sem:
            try:
                jev = await session.answer_all(row["text"])
            except Exception as error:  # noqa: BLE001 - report and continue; rerun resumes
                failures += 1
                print(f"failed {row['id']}: {type(error).__name__}", file=sys.stderr)
                return
            handle.write(json.dumps({"id": row["id"], "model": jev.model, "usage": jev.usage,
                                     "answers": jev.answers}) + "\n")
            handle.flush()

    await asyncio.gather(*(one(r) for r in todo))
    handle.close()
    print(f"requested={len(todo)} already_cached={len(done)} failures={failures} "
          f"requests_sent={session.requests_sent} input_tokens={session.input_tokens}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["extract", "fit"])
    parser.add_argument("--project", default="~/Projects/Jev-Calibration")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=16)
    args = parser.parse_args()
    if args.stage == "extract":
        asyncio.run(extract(args))
    else:
        from jev_head_fit import fit_stage  # noqa: WPS433
        fit_stage(args)


if __name__ == "__main__":
    main()
