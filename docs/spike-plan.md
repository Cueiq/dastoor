# The spike: can rules find grammar points in subtitles?

The question: can rules, with no language model, find grammar points in
subtitle English accurately enough to replace Claude's grammar entries in a
Bembegoo lesson? Subtitle English is hard on a parser: fragments, *gonna*,
two voices in one line, and lines cut mid-sentence.

The spike answers it for 10 points before anything else is built.

## The 10 points

All 10 are taught in Bembegoo's courses already, so there are real lines to
test on. Seven can be told by form; three pairs are told apart by meaning,
to see where rules stop.

| point | told by | look-alike a rule must not match |
|---|---|---|
| `be-going-to` | form | *I'm going to the shop* (a place, not a verb) |
| `present-perfect-continuous` | form | *I've been to Paris*; *He's been chosen* |
| `used-to` | form | *I'm used to it* (be used to) |
| `modal-passive` | form | *It must be nice* (an adjective, not a participle) |
| `comparatives` | form | *teacher*, *never* (-er that isn't a comparison) |
| `must-have-past-participle` | form | *You must have a ticket* |
| `second-conditional` | form, mostly | *If you were there, you saw it* |
| `must-obligation` / `must-guess` | **meaning** | each other: *You must go* / *You must be tired* |
| `would-past-habit` | **meaning** | *I would go if I could*; *Would you like…?* |

## A point's file

One YAML file per point, in `points/`. The spike writes only `match` and
`tests`; the note and the exercises come once rules are shown to work.

```yaml
id: used-to
title: { en: "used to + verb" }
topic: past_habits
cefrj: ["140", "140-1", "140-2"]   # MD.used_to: affirmative, negative, question
match:
  # spaCy Matcher patterns, one per form.
  - name: positive
    pattern:
      - { LOWER: used }
      - { LOWER: to }
      - { POS: VERB, TAG: VB }
  - name: negative
    pattern:
      - { LEMMA: do }
      - { LOWER: { IN: ["not", "n't"] } }
      - { LOWER: { IN: [use, used] } }
      - { LOWER: to }
      - { TAG: VB }
  - name: question
    pattern:
      - { LEMMA: do }
      - { POS: PRON }
      - { LOWER: { IN: [use, used] } }
      - { LOWER: to }
      - { TAG: VB }
exclude:
  # be used to + noun or -ing is a different point.
  - pattern:
      - { LEMMA: be }
      - { OP: "?", POS: ADV }
      - { LOWER: used }
      - { LOWER: to }
needs_meaning: false
tests:
  match:
    - "We used to live here."
    - "I didn't use to like it."
    - "Did you use to play?"
    - "My dad used to say that, you know."
  no_match:
    - "I'm used to the noise."
    - "She's getting used to living alone."
    - "They used two cars."
```

A point whose rule can't settle its meaning says `needs_meaning: true`. Its
matches are reported as *candidates*, and the spike counts how many there
are, to see what a meaning check (a small model, or a person) would cost.

## The engine

Python and spaCy. spaCy's Matcher handles token patterns, and its
DependencyMatcher handles parse trees. Rust has nothing as good for parsing
English.

- `dastoor test`: runs every point's tests. A failing test fails the run.
- `dastoor tag <file.srt> --json`: every line's points, with each match's
  form and the words it spans.
- `dastoor score`: the spike's scoring, below.

Both spaCy models are tried: `en_core_web_sm` (small and fast) and
`en_core_web_trf` (more accurate, needs PyTorch). The spike reports both, so
the trade-off is measured, not guessed.

## Scoring

**The lines.** Every subtitle of Bembegoo's guided courses: 10 episodes so
far, 3,339 lines.

**What counts as right.** Two sets:

- **The guides' marks.** A grammar entry's anchors are every line of its
  scene that uses the point, and its `heard` lines are the rest of the
  episode's. So in an episode that teaches a point, the guide says which
  lines use it. A rule's **recall** is the share of those lines it finds.
  Its matches the guide didn't mark are either the rule's mistakes or the
  guide's misses; each is looked at and called.
- **A hand-checked sample.** For each point, 50 lines the rule matched and
  50 it didn't, from episodes that don't teach the point, are checked by
  reading. From these come the **precision**, and the misses in the rest.

**The bar.** For the seven points told by form: precision 0.9 or better,
and recall 0.8 or better, against both sets. For the three meaning pairs,
the spike reports what share of matches a rule can settle. Below the bar,
the spike says why: the parser, the pattern, or the line itself.

## What the spike delivers

1. The 10 point files, their tests passing.
2. `dastoor test`, `tag` and `score`.
3. A report: each point's precision and recall, both models, the time per
   episode, and the mistakes grouped by cause.
4. A recommendation: build the library this way, a hybrid, or not at all.

## Not in the spike

- The notes and exercises.
- Bembegoo's side: prepare calling `dastoor tag`, and the short entry for a
  point Dastoor has.
- Points beyond these 10; the CEFR-J list sets which come next.
- A public repository: it stays local until the owner says otherwise.

## Open questions

- **Licence.** I'd make the code MIT, like Sanjeh, and the notes and
  exercises CC BY-SA 4.0, so others can use them while they stay open.
- **How fine a point is.** The English Grammar Profile has about 1,200
  items, while a learner wants notes the size of *used to*. A point covers
  several CEFR-J items: `used-to` covers 140, 140-1 and 140-2.
- **POLKE.** Ask its authors whether its API may be used as a second
  yardstick.
