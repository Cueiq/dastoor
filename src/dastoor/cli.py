"""dastoor test | tag | score"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import yaml

from . import model as model_module
from . import points as points_module
from . import score as score_module
from .subtitles import pieces, read

MODEL = "en_core_web_sm"


def found_in(point, nlp, sentence: str) -> list[str]:
    doc = nlp(sentence)
    return [doc[each.start : each.end].text for each in point.find(doc)]


def test(args) -> int:
    nlp = model_module.load(args.model)
    failed = 0
    total = 0
    for point in points_module.load(nlp):
        # A learner finds a point by its names: one in Persian, and words
        # to search it by.
        total += 1
        if not point.title.get("fa") or not point.keywords:
            failed += 1
            print(f"FAIL {point.id}: needs a Persian title (title.fa) and keywords")
        for sentence in point.tests.get("match", []):
            total += 1
            if not found_in(point, nlp, sentence):
                failed += 1
                print(f"FAIL {point.id}: should match: {sentence}")
        for sentence in point.tests.get("no_match", []):
            total += 1
            found = found_in(point, nlp, sentence)
            if found:
                failed += 1
                print(f"FAIL {point.id}: should not match: {sentence} (found {found})")
    print(f"{total - failed} of {total} tests pass ({args.model})")
    return 1 if failed else 0


def tag(args) -> int:
    """Each cue's points. A sentence broken across cues is parsed whole, and
    a match counts for every cue its words are in. Points that ask not to be
    tagged (`tag: false`) are left out: their rules mislead more than help."""
    nlp = model_module.load(args.model)
    points = [point for point in points_module.load(nlp) if point.tag]
    lines = read(Path(args.file))
    by_cue: dict[int, list[dict]] = {}
    for piece in pieces(lines):
        doc = nlp(piece.text)
        for point in points:
            for each in point.find(doc):
                span = doc[each.start : each.end]
                for cue in piece.cues(span.start_char, span.end_char):
                    by_cue.setdefault(cue, []).append(
                        {
                            "point": point.id,
                            "form": each.form,
                            "words": span.text,
                            "candidate": point.needs_meaning,
                        }
                    )
    out = [
        {"cue": line.cue, "text": " / ".join(line.said), "points": by_cue.get(line.cue, [])}
        for line in lines
        if line.cue in by_cue or args.all
    ]
    if args.json:
        json.dump({"model": args.model, "lines": out}, sys.stdout, ensure_ascii=False, indent=1)
        print()
    else:
        for line in out:
            marks = ", ".join(f"{each['point']} «{each['words']}»" for each in line["points"])
            print(f"#{line['cue']:<4} {line['text']}\n      {marks}")
    return 0


def export(args) -> int:
    """Every point's note and exercises, as one JSON file for a tool that
    fills them in (Bembegoo's build). Each carries `note_from`: its id and a
    hash of its file, so a guide made from it can tell when it changed."""
    points = {}
    for path in sorted(points_module.POINTS.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if "note" not in data:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        points[data["id"]] = {
            "title": data.get("title", {}),
            "level": data.get("level"),
            "topic": data.get("topic"),
            "keywords": data.get("keywords", []),
            # The other ids guides gave the point: a guide's note on one is
            # this point's.
            "aliases": data.get("aliases", []),
            "needs_meaning": bool(data.get("needs_meaning", False)),
            "tag": data.get("tag", True),
            "example": data["note"]["forms"][0]["text"] if data["note"].get("forms") else "",
            "note": data["note"],
            "exercises": data.get("exercises", []),
            "note_from": f"dastoor:{data['id']}@{digest}",
        }
    json.dump({"dastoor": 1, "points": points}, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dastoor")
    parser.add_argument("--model", default=MODEL, help="the spaCy pipeline")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("test", help="run every point's tests")
    tagging = commands.add_parser("tag", help="the points each subtitle line uses")
    tagging.add_argument("file")
    tagging.add_argument("--json", action="store_true")
    tagging.add_argument("--all", action="store_true", help="lines with no point too")
    commands.add_parser("export", help="every point's note, as JSON")
    scoring = commands.add_parser("score", help="the spike's scoring against Bembegoo's guides")
    scoring.add_argument("courses", help="the folder of Bembegoo courses")
    scoring.add_argument("--out", default="spike", help="where the report and samples go")
    scoring.add_argument("--seed", type=int, default=7)
    scoring.add_argument("--split", choices=["dev", "test"], help="score on one half of the files only")
    args = parser.parse_args(argv)
    started = time.time()
    try:
        code = {"test": test, "tag": tag, "export": export, "score": score_module.run}[args.command](args)
    except model_module.MissingModel as error:
        print(f"dastoor: {error}", file=sys.stderr)
        return 2
    print(f"({time.time() - started:.1f} s)", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
