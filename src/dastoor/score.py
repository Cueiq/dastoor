"""The spike's scoring (docs/spike-plan.md, "Scoring").

Against Bembegoo's guides: a grammar entry's anchors and `heard` lines are
the lines of its episode that use its point, so in an episode that teaches
a point the guide says which lines use it. A rule's recall is the share of
those it finds. Its other matches there are listed, to be called right or
wrong by reading.

For precision, and for misses outside the guides, samples are drawn from
the lines of every English subtitle in the courses outside the episodes
teaching the point: 50 it matched and 50 it didn't that have the point's
words in them. Each sample is a file to fill in, one verdict a line.
"""

from __future__ import annotations

import csv
import json
import random
import re
import time
import zlib
from collections import defaultdict
from pathlib import Path

from . import model
from . import points as points_module
from .subtitles import pieces, read

SAMPLE = 50


def episodes(courses: Path) -> list[Path]:
    return sorted(
        path.parent
        for path in courses.glob("*/*/entries.json")
        if (path.parent / "en.srt").is_file()
    )


def marked(episode: Path) -> dict[str, set[int]]:
    """The lines a guide marks for each grammar point."""
    lines: dict[str, set[int]] = defaultdict(set)
    data = json.loads((episode / "entries.json").read_text())
    for scene in data.get("scenes", []):
        for entry in scene.get("entries", []):
            grammar = entry.get("grammar")
            if not grammar or not grammar.get("point"):
                continue
            heard = grammar.get("heard") or entry.get("heard") or []
            for anchor in list(entry.get("anchors", [])) + list(heard):
                if anchor.get("cue") is not None:
                    lines[grammar["point"]].add(int(anchor["cue"]))
    return lines


def english(path: Path) -> bool:
    if re.search(r"farsi|persian|\bfa\b|\.fa\.", path.name, re.IGNORECASE):
        return False
    text = path.read_text(encoding="utf-8-sig", errors="replace")[:4000]
    latin = len(re.findall(r"[A-Za-z]", text))
    other = len(re.findall(r"[؀-ۿ]", text))
    return latin > 200 and other < latin / 20


def run(args) -> int:
    courses = Path(args.courses).expanduser()
    out = Path(args.out)
    (out / "samples").mkdir(parents=True, exist_ok=True)
    nlp = model.load(args.model)
    points = points_module.load(nlp)
    wanted = {point.id for point in points}

    taught = episodes(courses)
    # Every English subtitle, each line once by what it says.
    files = sorted({*courses.glob("**/*.srt")})
    files = [path for path in files if path.name != "fa.srt" and english(path)]
    if args.split:
        # Half the files to tune the rules on, half to grade them on, by a
        # hash of the file's place, so a file is always on the same side.
        side = {"dev": 0, "test": 1}[args.split]
        files = [
            path
            for path in files
            if zlib.crc32(str(path.relative_to(courses)).encode()) % 2 == side
        ]
    lines_of: dict[Path, list] = {path: read(path) for path in files}
    pieces_of = {path: pieces(lines) for path, lines in lines_of.items()}
    sentences = sorted({piece.text for each in pieces_of.values() for piece in each})
    started = time.time()
    docs = dict(zip(sentences, nlp.pipe(sentences, batch_size=256)))
    parsing_s = time.time() - started

    def found_by_cue(point, path: Path) -> dict[int, list[str]]:
        """Each cue's matches: a match in a sentence broken across cues
        counts for every cue its words are in."""
        by_cue: dict[int, list[str]] = defaultdict(list)
        for piece in pieces_of[path]:
            doc = docs[piece.text]
            for each in point.find(doc):
                span = doc[each.start : each.end]
                for cue in piece.cues(span.start_char, span.end_char):
                    by_cue[cue].append(span.text)
        return by_cue

    report = [
        f"# Spike report ({args.model}{', ' + args.split + ' half' if args.split else ''})",
        "",
        f"{len(sentences)} sentences from {len(files)} subtitle files parsed in {parsing_s:.1f} s; "
        f"{len(taught)} episodes have guides.",
        "",
        "| point | taught in | marked lines | found | recall | unmarked matches there | matches elsewhere |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    rng = random.Random(args.seed)
    for point in points:
        marked_total = found_total = unmarked = 0
        teaching = []
        misses = []
        extra = []
        for episode in taught:
            marks = marked(episode)
            cues = set().union(*(marks.get(id, set()) for id in [point.id, *point.aliases]))
            if not cues:
                continue
            teaching.append(episode)
            srt = episode / "en.srt"
            if srt not in lines_of:
                lines_of[srt] = read(srt)
                pieces_of[srt] = pieces(lines_of[srt])
                for piece in pieces_of[srt]:
                    docs.setdefault(piece.text, nlp(piece.text))
            by_cue = found_by_cue(point, srt)
            for line in lines_of[srt]:
                words = by_cue.get(line.cue, [])
                if line.cue in cues:
                    marked_total += 1
                    if words:
                        found_total += 1
                    else:
                        misses.append((episode.name, line.cue, "", " / ".join(line.said)))
                elif words:
                    unmarked += 1
                    extra.append((episode.name, line.cue, ", ".join(words), " / ".join(line.said)))

        # Outside the teaching episodes, each line once.
        teaching_srt = {episode / "en.srt" for episode in teaching}
        seen: set[str] = set()
        matched, unmatched = [], []
        keys = [word.lower() for word in point.tests.get("words", [])]
        for path in files:
            if path in teaching_srt or any(path.samefile(srt) for srt in teaching_srt):
                continue
            by_cue = found_by_cue(point, path)
            for line in lines_of[path]:
                said = " / ".join(line.said)
                if not said or said in seen:
                    continue
                seen.add(said)
                words = by_cue.get(line.cue, [])
                if words:
                    matched.append((path.parent.name or path.name, line.cue, ", ".join(words), said))
                elif keys and re.search(r"\b(" + "|".join(map(re.escape, keys)) + r")\b", said, re.IGNORECASE):
                    unmatched.append((path.parent.name or path.name, line.cue, "", said))
        rng.shuffle(matched)
        rng.shuffle(unmatched)
        with open(out / "samples" / f"{point.id}.tsv", "w", newline="") as file:
            writer = csv.writer(file, delimiter="\t")
            writer.writerow(["verdict", "kind", "where", "cue", "found", "line"])
            for kind, rows in (
                ("guide-miss", misses),
                ("guide-unmarked", extra),
                ("matched", matched[:SAMPLE]),
                ("not-matched", unmatched[:SAMPLE]),
            ):
                for where, cue, words, said in rows:
                    writer.writerow(["", kind, where, cue, words, said])
        recall = f"{found_total / marked_total:.2f}" if marked_total else "–"
        report.append(
            f"| `{point.id}`{' (meaning)' if point.needs_meaning else ''} | {len(teaching)} | {marked_total} | "
            f"{found_total} | {recall} | {unmarked} | {len(matched)} |"
        )
    report += [
        "",
        "Samples to judge are in `samples/`: a `y` or `n` in each line's verdict.",
        "",
    ]
    (out / "report.md").write_text("\n".join(report))
    print("\n".join(report))
    missing = wanted - {point.id for point in points}
    if missing:
        print("not loaded:", missing)
    return 0
