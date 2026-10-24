"""dastoor test | tag | export | score | serve"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import yaml

from . import heard as heard_module
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


def marks(nlp, points, text: str) -> dict:
    """What one text uses: each point's match, its words and where they are
    in `text` (characters, as Python counts them: code points), and the
    text's sentences, in order."""
    doc = nlp(text)
    found = []
    for point in points:
        for each in point.find(doc):
            span = doc[each.start : each.end]
            found.append(
                {
                    "point": point.id,
                    "form": each.form,
                    "words": span.text,
                    "start": span.start_char,
                    "end": span.end_char,
                    "candidate": point.needs_meaning,
                }
            )
    found.sort(key=lambda mark: (mark["start"], mark["end"], mark["point"]))
    return {"sentences": [[sentence.start_char, sentence.end_char] for sentence in doc.sents], "points": found}


def serve(args) -> int:
    """The model loaded once, then a text a line: each line of stdin a JSON
    request, `{"id": …, "text": "…"}`, each answered by one line of stdout,
    the id given back with the text's marks (`marks`), or an `error`. The
    first line out says it is ready. Points that ask not to be tagged are
    left out, as `tag` leaves them."""
    nlp = model_module.load(args.model)
    points = [point for point in points_module.load(nlp) if point.tag]

    def say(answer: dict) -> None:
        print(json.dumps(answer, ensure_ascii=False), flush=True)

    say({"ready": True, "model": args.model, "points": len(points)})
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except ValueError as error:
            say({"id": None, "error": f"not JSON: {error}"})
            continue
        asked = request.get("id") if isinstance(request, dict) else None
        text = request.get("text") if isinstance(request, dict) else None
        if not isinstance(text, str):
            say({"id": asked, "error": "a request needs its text"})
            continue
        say({"id": asked, **marks(nlp, points, text)})
    return 0


def heard(args) -> int:
    """Count how often each point is heard in a set of English subtitles,
    and keep the counts (`data/heard.json`) for the export."""
    nlp = model_module.load(args.model)
    points = points_module.load(nlp)
    files = heard_module.subtitle_files([Path(each) for each in args.paths])
    if not files:
        print("no English subtitles there", file=sys.stderr)
        return 1
    started = time.time()
    counts = heard_module.count(nlp, points, files)
    counts["model"] = args.model
    heard_module.HEARD.parent.mkdir(exist_ok=True)
    heard_module.HEARD.write_text(json.dumps(counts, ensure_ascii=False, indent=1) + "\n")
    top = sorted(counts["points"].items(), key=lambda each: -each[1])[:5]
    print(f"{counts['sentences']} sentences in {counts['files']} files ({time.time() - started:.1f} s); most heard: "
          + ", ".join(f"{point} {n}" for point, n in top), file=sys.stderr)
    return 0


def export(args) -> int:
    """Every point's note and exercises, as one JSON file for a tool that
    fills them in (Bembegoo's build). Each carries `note_from`: its id and a
    hash of its file, so a guide made from it can tell when it changed; its
    place in a book (`place`); and, once counted (`dastoor heard`), how many
    of the subtitles' sentences use it (`heard`), the count's size in
    `heard` at the top."""
    counted = heard_module.load()
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
            "place": data.get("place", {}),
            "heard": counted["points"].get(data["id"]) if counted else None,
            "note": data["note"],
            "exercises": data.get("exercises", []),
            "note_from": f"dastoor:{data['id']}@{digest}",
        }
    out = {"dastoor": 1, "points": points}
    if counted:
        out["heard"] = {"files": counted["files"], "sentences": counted["sentences"]}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
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
    hearing = commands.add_parser("heard", help="count how often each point is heard in English subtitles")
    hearing.add_argument("paths", nargs="+", help="subtitle files, or folders of them")
    commands.add_parser("export", help="every point's note, as JSON")
    commands.add_parser("serve", help="answer texts line by line on stdin, the model loaded once")
    scoring = commands.add_parser("score", help="the spike's scoring against Bembegoo's guides")
    scoring.add_argument("courses", help="the folder of Bembegoo courses")
    scoring.add_argument("--out", default="spike", help="where the report and samples go")
    scoring.add_argument("--seed", type=int, default=7)
    scoring.add_argument("--split", choices=["dev", "test"], help="score on one half of the files only")
    args = parser.parse_args(argv)
    started = time.time()
    try:
        code = {"test": test, "tag": tag, "heard": heard, "export": export, "score": score_module.run, "serve": serve}[args.command](args)
    except model_module.MissingModel as error:
        print(f"dastoor: {error}", file=sys.stderr)
        return 2
    print(f"({time.time() - started:.1f} s)", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
