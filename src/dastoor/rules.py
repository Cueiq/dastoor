"""A point's rules, matched against a parsed sentence.

A rule is either `tokens`, a spaCy Matcher pattern (words in order), or
`tree`, a word and the words around it in the parse:

    tree:
      word: { TAG: VBG }             # the word itself
      has:                           # words hanging on it, each one found
        - { DEP: aux, LEMMA: have }
        - { DEP: aux, LOWER: been }
      lacks:                         # words that must not hang on it
        - { DEP: mark, LOWER: if }
      head: { word: {...}, has: [...] }   # the word it hangs on, as a tree

A word's attributes are spaCy's: LOWER, LEMMA, POS, TAG, DEP, TEXT. A value
is a string, or `{IN: [...]}`, `{NOT_IN: [...]}` or `{REGEX: "..."}`. A
child under `has` may itself be a tree: `{word: {...}, has: [...]}`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from spacy.matcher import Matcher
from spacy.tokens import Doc, Token

ATTRIBUTES = {
    "LOWER": lambda token: token.lower_,
    "LEMMA": lambda token: token.lemma_.lower(),
    "POS": lambda token: token.pos_,
    "TAG": lambda token: token.tag_,
    "DEP": lambda token: token.dep_,
    "TEXT": lambda token: token.text,
}


@dataclass(frozen=True)
class Found:
    """A rule matched: the words it covers, by their index in the doc."""

    form: str
    words: tuple[int, ...]

    @property
    def start(self) -> int:
        return min(self.words)

    @property
    def end(self) -> int:
        return max(self.words) + 1


def _value_matches(value, wanted) -> bool:
    # Words compare without case: a subtitle's capitals are its own.
    value = value.lower()
    if isinstance(wanted, dict):
        # Every test given must hold: { REGEX: "ing$", NOT_IN: [thing] }.
        unknown = set(wanted) - {"IN", "NOT_IN", "REGEX"}
        if unknown or not wanted:
            raise ValueError(f"unknown test {wanted}")
        if "IN" in wanted and value not in {str(each).lower() for each in wanted["IN"]}:
            return False
        if "NOT_IN" in wanted and value in {str(each).lower() for each in wanted["NOT_IN"]}:
            return False
        if "REGEX" in wanted and re.search(wanted["REGEX"], value, re.IGNORECASE) is None:
            return False
        return True
    return value == str(wanted).lower()


def word_matches(token: Token, spec: dict) -> bool:
    for key, wanted in spec.items():
        if key not in ATTRIBUTES:
            raise ValueError(f"unknown attribute {key}")
        if not _value_matches(ATTRIBUTES[key](token), wanted):
            return False
    return True


def _node(spec: dict) -> dict:
    """A child spec is a bare word, or a tree with `word`."""
    return spec if "word" in spec else {"word": spec}


def tree_matches(token: Token, tree: dict) -> tuple[int, ...] | None:
    """The words a tree covers when its word is `token`, or None."""
    if not word_matches(token, tree.get("word", {})):
        return None
    words = [token.i]
    used: set[int] = set()
    for child_spec in tree.get("has", []):
        child_tree = _node(child_spec)
        found = None
        for child in token.children:
            if child.i in used:
                continue
            found = tree_matches(child, child_tree)
            if found is not None:
                used.add(child.i)
                break
        if found is None:
            return None
        words.extend(found)
    for child_spec in tree.get("lacks", []):
        child_tree = _node(child_spec)
        if any(tree_matches(child, child_tree) is not None for child in token.children):
            return None
    if "head" in tree:
        head = token.head
        if head.i == token.i:
            return None
        found = tree_matches(head, _node(tree["head"]))
        if found is None:
            return None
        words.extend(found)
    return tuple(sorted(set(words)))


class Rules:
    """One point's rules, ready to run on docs of one pipeline."""

    def __init__(self, point_id: str, match: list[dict], exclude: list[dict], vocab):
        self.point_id = point_id
        self.match = match
        self.exclude = exclude
        self.matcher = Matcher(vocab)
        for at, rule in enumerate(match + exclude):
            if "tokens" in rule:
                self.matcher.add(f"{at}", [rule["tokens"]])

    def _run(self, doc: Doc, rules: list[dict], offset: int) -> list[Found]:
        found: list[Found] = []
        by_key: dict[str, list[tuple[int, int]]] = {}
        for key, start, end in self.matcher(doc) if len(self.matcher) else []:
            by_key.setdefault(doc.vocab.strings[key], []).append((start, end))
        for at, rule in enumerate(rules):
            form = rule.get("form", "")
            if "tokens" in rule:
                for start, end in by_key.get(f"{at + offset}", []):
                    found.append(Found(form, tuple(range(start, end))))
            if "tree" in rule:
                for token in doc:
                    words = tree_matches(token, rule["tree"])
                    if words is not None:
                        found.append(Found(form, words))
        return found

    def find(self, doc: Doc) -> list[Found]:
        """What the point's rules match in `doc`, less what an exclude
        rule covers too."""
        matched = self._run(doc, self.match, 0)
        excluded = self._run(doc, self.exclude, len(self.match))
        kept = [
            each
            for each in matched
            if not any(set(each.words) & set(other.words) for other in excluded)
        ]
        # One match per set of words: forms that find the same words agree.
        unique: dict[tuple[int, ...], Found] = {}
        for each in kept:
            unique.setdefault(each.words, each)
        # A form finding part of what another form found is the same use
        # ('m gonna tell, and gonna tell in it); a form inside its own
        # larger match is another use (a clause in a clause).
        uses = [
            each
            for each in unique.values()
            if not any(
                other.form != each.form and set(each.words) < set(other.words)
                for other in unique.values()
            )
        ]
        return sorted(uses, key=lambda each: each.words)
