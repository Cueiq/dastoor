"""How often each point is heard: the share of subtitle lines that use it,
counted over a set of English subtitles (`dastoor heard`), kept in
`data/heard.json` for the export to carry."""

from __future__ import annotations

import json
from pathlib import Path

from .score import english
from .subtitles import pieces, read

HEARD = Path(__file__).resolve().parents[2] / "data" / "heard.json"


def subtitle_files(paths: list[Path]) -> list[Path]:
    """The English subtitles among `paths`: the files given, and every .srt
    and .vtt in the folders given."""
    found: set[Path] = set()
    for path in paths:
        path = path.expanduser()
        if path.is_dir():
            found.update(path.glob("**/*.srt"))
            found.update(path.glob("**/*.vtt"))
        elif path.is_file():
            found.add(path)
    return sorted(path for path in found if english(path))


def count(nlp, points, files: list[Path]) -> dict:
    """Each point's count of the subtitles' sentences that use it. A sentence
    said in more than one file (two copies of an episode) counts once; a
    sentence counts once for a point however often it uses it. Points that
    ask not to be tagged are left out, as `tag` leaves them."""
    sentences = sorted({piece.text for path in files for piece in pieces(read(path))})
    counts = {point.id: 0 for point in points if point.tag}
    tagged = [point for point in points if point.tag]
    for doc in nlp.pipe(sentences, batch_size=256):
        for point in tagged:
            if point.find(doc):
                counts[point.id] += 1
    return {"files": len(files), "sentences": len(sentences), "points": dict(sorted(counts.items()))}


def load() -> dict | None:
    """The counts kept, if they have been counted."""
    return json.loads(HEARD.read_text()) if HEARD.is_file() else None
