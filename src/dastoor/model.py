"""The spaCy pipeline a command parses with."""

from __future__ import annotations

import spacy

# How each model Dastoor is tested with is installed (pyproject.toml's groups).
INSTALL = {
    "en_core_web_sm": "uv sync",
    "en_core_web_trf": "uv sync --all-groups",
}


class MissingModel(Exception):
    """The model asked for isn't installed."""


def load(name: str):
    try:
        return spacy.load(name)
    except OSError as error:
        # E050: no package or folder of that name.
        if "E050" not in str(error):
            raise
        how = INSTALL.get(name, f"install the spaCy pipeline {name}")
        raise MissingModel(f"the spaCy model {name} isn't installed; to install it: {how}") from None
