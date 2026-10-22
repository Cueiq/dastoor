# Dastoor

*Dastoor* (دستور, Persian for "grammar") is a grammar index for English learners. Given a sentence, it
finds the grammar points the sentence uses (*have been + -ing*, *used to*,
*must have + past participle*), and the exact words that make each one.
For every point it has a learner's note: what it does, how it is built, the
mistakes learners make with it (Persian speakers' first), what it is easily
confused with, and exercises.

No language model is called. Points are found by rules over spaCy's parse
of the sentence, and every rule is tested on sentences it must and must not
match.

It is made for learning from films and series, so subtitles are its first
input: it joins a sentence that a subtitle breaks across lines. It works on
any English sentence.

## What it has

**38 points, A1–B2**, each with its rules, its tests and its note. Most are
told by their form:

| told by | points | how well (on film subtitles) |
|---|---|---|
| form | 33: the present continuous and perfect, *going to*, *will*, *can*, *could*, *might*, *should*, *have to*, the passive, comparatives, superlatives, *so* and *such*, conditionals, question tags, *let's*, *some* and *any*, verb + *to* or *-ing*, relative clauses, reported speech… | most 0.96–1.00 precision, every match read on a held-out half of the subtitles; a few points have too few lines yet to tell |
| meaning | 5: *must* (a guess or an obligation?), *must be*, *have got*, *would* for a past habit | the rule finds the line; its meaning is left to the reader |

A meaning point's matches are marked as candidates: the words alone can't
settle them. *Would* for a past habit is right so rarely by its form that
it isn't tagged at all. The method and every number are in
[docs/spike-report.md](docs/spike-report.md).

## Install

Dastoor needs Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                # Dastoor and spaCy's small English model
uv sync --all-groups   # and the transformer model too
```

The small model is 15 MB and runs at about 1,300 sentences a second. The
transformer model is more accurate: on comparatives, about 0.94 precision
against the small model's 0.81. It needs about 1 GB with PyTorch (the CPU
build, on Linux). The models are in the project's dependency groups (`sm`,
`trf`): a plain `uv sync` or `uv run` keeps only the small one, so with the
transformer, sync with `--all-groups` and run with `uv run --all-groups`.

## Use

```bash
dastoor test                                      # every point's tests
dastoor --model en_core_web_trf tag episode.srt   # each line's points
dastoor tag episode.srt --json                    # the same, as JSON
dastoor export                                    # every note, as one JSON file
dastoor score <courses folder> --split test       # score the rules on lessons whose grammar is marked
```

`--model` picks the spaCy pipeline; the small one is the default.

## A point

One YAML file per point in [points/](points/), named by its id:

```yaml
id: used-to
title: { en: "used to + verb", fa: "used to: عادت یا حالتِ گذشته" }
keywords: ["used to", "past habit", "قبلاً", "عادت گذشته"]   # to search it by
topic: past_habits
cefrj: ["140", "140-1", "140-2"]   # its items in the CEFR-J Grammar Profile
match:                              # what finds it: spaCy patterns
  - form: all
    tree:                           # a word and the words around it
      word: { LOWER: { IN: [used, use] } }
      has:
        - word: { DEP: xcomp, TAG: VB }
          has: [ { DEP: aux, LOWER: to } ]
      lacks: [ { LEMMA: be, DEP: { IN: [aux, auxpass] } } ]
exclude: []                         # look-alikes to leave out
tests:
  words: [used, use]                # to sample lines that may use it
  match: ["We used to live here."]
  no_match: ["I'm used to the noise."]
level: B1                           # the learner's note
note:
  gist: { en: "…", fa: "…" }
  forms: [ … ]                      # how it is built, an example each
  mistakes: [ … ]                   # wrong, right and why
  contrast: [ … ]                   # what not to mix it up with
exercises: [ … ]                    # choose, fix, rewrite
```

A rule is either `tokens`, a spaCy Matcher pattern of words in order, or a
`tree`: a word, the words that must or mustn't hang on it, and the word it
hangs on. The format is described in
[src/dastoor/rules.py](src/dastoor/rules.py). A point may also say:

- `needs_meaning: true` when its words can't settle what it means;
- `tag: false` when its rule shouldn't mark lines at all;
- `aliases` for other ids the same point goes by.

Every note has the same shape, so an app can show it, or a lesson take it,
as it is.

## Adding a point

1. Write its rules and its tests. Include sentences it must match, and the
   look-alikes it mustn't: *I'm used to it* is not *used to + verb*.
2. Run `dastoor test` on both models.
3. Score it on real subtitles, and read what it matched and what it missed.
   Tune on one half of the files (`--split dev`) and report on the other
   (`--split test`).
4. Write its note and exercises, as Dastoor's own. Nothing is copied from
   the English Grammar Profile or the Core Inventory.

Quote any word YAML could read as true or false (`"no"`, `"yes"`): the
loader refuses one unquoted.

## Licence

- **The code** is [MIT](LICENSE).
- **The points** (their rules, tests, notes and exercises) are [CC BY-SA
  4.0](points/LICENSE.md): use and adapt them, also commercially, crediting
  Dastoor and sharing what you make from them alike.

## Sources

Levels come from the [CEFR-J Grammar
Profile](https://github.com/openlanguageprofiles/olp-en-cefrj) (Tono
Laboratory, Tokyo University of Foreign Studies), which may be used for
commercial purposes when cited. Its rows carry each item's level in the
English Grammar Profile, the Core Inventory and Pearson's GSE too. A point's
`level` is the English Grammar Profile's lowest, as CEFR-J records it. Where
no item has one, it is CEFR-J's own, or the level the lessons it was scored
on gave it. A few are set by hand where that level would mislead a learner,
each with its reason in its file (`level_from: hand`): verb + *-ing* is A2,
not the profile's B2.

## Why it exists

There are lists of grammar points by level: the English Grammar Profile,
the Core Inventory and CEFR-J. There are research tools that find grammar in
text, such as POLKE (a closed API) and GrammarTagger (non-commercial
models). None is open, and none gives both the matching and a learner's
notes and exercises. Dastoor aims to be that.
