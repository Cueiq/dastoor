"""Subtitle lines as sentences to parse: markup, sound and speakers out, and a
line two people say split in two."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->")
MARKUP = re.compile(r"<[^>]+>|\{[^}]*\}")
SOUND = re.compile(r"\([^)]*\)|\[[^\]]*\]")
MUSIC = re.compile(r"♪[^♪]*♪|♪")
# A speaker's name in capitals before what they say: "BERT: It's me."
SPEAKER = re.compile(r"(^|(?<=[-–]\s))[A-Z][A-Z .']+:\s*")
# A new voice: a dash at a line's start, or after a sentence's end, with
# or without a space after it ("-Stop talking").
VOICE = re.compile(r"(?:^|(?<=[.!?…]\s)|(?<=\n))\s*[-–](?:\s+|(?=[A-Za-z\"'‘“]))")


@dataclass
class Line:
    cue: int
    start_ms: int
    text: str
    # What each voice says, cleaned, ready to parse.
    said: list[str]


def cleaned(text: str) -> list[str]:
    text = MARKUP.sub("", text)
    text = MUSIC.sub(" ", text)
    text = SOUND.sub(" ", text)
    parts = VOICE.split(text) if VOICE.search(text) else [text]
    out = []
    for part in parts:
        part = SPEAKER.sub("", part.strip())
        part = re.sub(r"\s+", " ", part).strip(" -–")
        if re.search(r"[A-Za-z]", part):
            out.append(part)
    return out


def read(path: Path) -> list[Line]:
    text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\r", "")
    lines = []
    for block in re.split(r"\n\s*\n", text.strip()):
        rows = block.split("\n")
        for at, row in enumerate(rows):
            time = TIME.search(row)
            if not time:
                continue
            hours, minutes, seconds, millis = map(int, time.groups())
            number = rows[0].strip()
            body = "\n".join(rows[at + 1 :])
            lines.append(
                Line(
                    cue=int(number) if number.isdigit() else len(lines) + 1,
                    start_ms=((hours * 60 + minutes) * 60 + seconds) * 1000 + millis,
                    text=body,
                    said=cleaned(body),
                )
            )
            break
    return lines


@dataclass
class Piece:
    """A sentence to parse, and which cue each stretch of it came from: a
    sentence a subtitle breaks across cues ("I am going..." / "to look for
    a job.") is parsed whole."""

    text: str
    # (cue, first character, past the last) in `text`.
    spans: list[tuple[int, int, int]]

    def cues(self, start_char: int, end_char: int) -> list[int]:
        return [cue for cue, start, end in self.spans if start < end_char and start_char < end]


# A cue ending on a comma or with no stop at all breaks a sentence off; one
# trailing off ("I am going...") may, if the next cue carries on in small
# letters ("to look for a job.").
BROKEN_OFF = re.compile(r"(,|[A-Za-z0-9'])$")
TRAILS_OFF = re.compile(r"(\.\.\.|…)$")
CARRIES_ON = re.compile(r"^(\.\.\.|…)?\s*[a-z]")


def pieces(lines: list[Line]) -> list[Piece]:
    out: list[Piece] = []
    carrying = ""
    for line in lines:
        for at, said in enumerate(line.said):
            if at == 0 and out and (carrying == "broken" or (carrying == "trailing" and CARRIES_ON.search(said))):
                last = out[-1]
                before = re.sub(r"(\.\.\.|…)$", "", last.text).rstrip()
                after = re.sub(r"^(\.\.\.|…)\s*", "", said)
                start = len(before) + 1
                last.text = f"{before} {after}"
                last.spans = [
                    (cue, begin, min(end, len(before))) for cue, begin, end in last.spans
                ] + [(line.cue, start, len(last.text))]
            else:
                out.append(Piece(said, [(line.cue, 0, len(said))]))
        last = line.said[-1] if line.said else ""
        carrying = "broken" if BROKEN_OFF.search(last) else "trailing" if TRAILS_OFF.search(last) else ""
    return out
