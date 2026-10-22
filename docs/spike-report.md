# The spike's report

**The question** (docs/spike-plan.md): can rules, with no language model, find
grammar points in subtitle English well enough to replace Claude's grammar
entries in a Bembegoo lesson?

**The answer: yes, for points told by their form, but not for points told
by their meaning.** Six of the seven form points matched with precision
0.98–1.00 and missed nothing in their samples. The seventh, comparatives,
reached 0.81 with the small model and about 0.94 with the transformer model.
Of the meaning points, *must* is right about nine times in ten by its form
alone. *Would* for a past habit is right one time in twenty, so it can't be
found by rules.

## What was run

- **Lines:** 42 English subtitle files in Bembegoo's courses (Extra English,
  Stuart Fails to Save the Universe, and a few more), 9,440 sentences once
  duplicates are dropped. Ten of the episodes have guides.
- **Halves:** the files were split in two by a hash of their names. The
  rules were tuned on the dev half and graded on the test half, which I did
  not read until the rules were final. One exception: `be-going-to`'s first
  fixes were made on a sample drawn before the split, so a few test lines
  (*Nick's going to be*, *Everything's going to be explained*) had been seen.
- **Grading:** every match in each test sample was read and called right or
  wrong, 50 a point at most. So were 50 unmatched lines a point that
  contain the point's words (*going*, *been*, *if*…), to find misses. I did
  the calling; the lines I wasn't sure of are listed at the end, for the
  owner to call.
- **Models:** spaCy's `en_core_web_sm` and `en_core_web_trf`.

## The form points (test half, small model)

| point | matches read | wrong | precision | misses in the sample of 50 unmatched |
|---|---:|---:|---:|---:|
| `be-going-to` | 50 | 1 | 0.98 | 0 |
| `comparatives` | 37 | 7 | 0.81 (≈0.94 with trf) | 0 |
| `present-perfect-continuous` | 12 | 0 | 1.00 | 0 |
| `modal-passive` | 5 | 0 | 1.00 | 0 |
| `second-conditional` | 5 | 0 | 1.00 | 0 |
| `used-to` | 4 | 1 | 0.75 | 0 |
| `must-have-past-participle` | 1 | 0 | 1.00 | 0 |

Against the guides' marks, six of the form points found every line their
guides mark: 24 lines. `second-conditional` found 2 of its 4. The other two
are *I would run a comic book store…* and the line after it, which a guide
marked as a second conditional though they have no *if*. And the rule did
better than the guide once: it found *It'd be different if I signed up for
it*, a second conditional the guide hadn't marked.

**The wrong matches:**

- `be-going-to`: *I'm going to the beautician's to check*, a place followed
  by "in order to".
- `used-to`: *the word I used to hypnotise Nick*, also "in order to". This
  needs a rule: *used* after a noun it describes.
- `comparatives`, with the small model:
  - *had better*, three times;
  - *T-shirts* (the parser split the word);
  - *no more giant moths* and *one more great* (*more* as a quantity);
  - *More importantly*.

  The transformer model avoids all but *More importantly* and *Better have
  finished what?*, and misses only *Faster!* alone.

**Too few to judge:** `must-have-past-participle` (1 match), `used-to` (4),
`modal-passive` (5) and `second-conditional` (5). Our ten episodes use them
rarely. Their numbers say the rules aren't wrong; they don't yet say how
often.

## The meaning points (both halves)

| point | matches read | meaning right | share |
|---|---:|---:|---:|
| `must-obligation` (*must* + a verb) | 85 | 78 | 0.92 |
| `must-guess` (*must be*) | 24 | 18 | 0.75 |
| `would-past-habit` (*would* + a verb) | 38 | 3 | 0.08 |

- *must* + a verb is an obligation unless it's a guess: *Girls must love
  you*, *The girls must know a good plumber*.
- *must be* is a guess unless it's an order: *Mummy says I must be home
  before 5*, *I must always be ready*.
- *would* + a verb is a wish, a condition, a promise or a polite request far
  more often than a past habit. A rule can't tell *my mom and I would play
  20 questions* from *I would write to you*.

## What was learned beyond the numbers

1. **Subtitles break sentences across cues.** *I am going...* / *to look for
   a job.* Parsed cue by cue, the rule missed it. Dastoor now joins a cue
   that ends on a comma or without a stop to the next. It joins a cue that
   trails off (*...*) only when the next carries on in small letters. This
   alone took `be-going-to`'s recall against the guides from 0.33 to 1.00.
2. **The parser's labels can't be trusted for small words.** It has called
   *'s* a possessive (*Nick's going*), a passive helper (*It's been
   raining*) and even a subject (*Someone's been sending*). Rules match such
   words by their forms, not the parser's labels.
3. **YAML reads an unquoted `no` as false.** The loader now refuses
   true/false where a word should be.
4. **Speed is no concern.** The small model parses about 1,300 sentences a
   second and the transformer about 330. An episode of 500 lines takes
   1.5 s with the transformer.

## The recommendation

**Build the library this way, as a hybrid:**

- **Form points by rules alone**, with the transformer model in Bembegoo's
  prepare. These are most of what an A1–B2 learner meets: tenses, *going
  to*, passives, comparatives, conditionals, *used to*, modals with *have*.
- **Meaning points as candidates.** The rule finds the lines, and its
  default reading stands unless something checks it. *must* is right about
  nine times in ten. A one-word check by a small model ("guess or
  obligation?") costs a few tokens a line, against the hundreds a grammar
  entry costs today.
- **Points like *would* for a past habit** come only from the guide writer,
  or from a model asked about each candidate line.

**Before trusting the numbers further:**

1. **More lines.** Subtitles of more shows, so the rare points get 30
   matches or more each. Our ten episodes are one sitcom and one learner
   series.
2. **The next 20 points,** chosen from the CEFR-J list and our courses.
3. **The owner calls the doubtful lines below.**

## Lines I wasn't sure of

| point | line | my call |
|---|---|---|
| `modal-passive` | *Should we be concerned?* | right: a participle used as an adjective, but still be + past participle |
| `modal-passive` | *We'd be honored to accept…* | right, for the same reason |
| `be-going-to` | *What is shaking it gonna do?* | right: broken English, but *gonna do* is the future |
| `second-conditional` | *If we got to the device, you could really reset the universe?* | right: *could* as the result |
| `comparatives` | *More importantly, you and I are back together.* | wrong: a fixed phrase, not a comparison |
| `must-obligation` | *What must I look like?* | wrong: a guess |
| `would-past-habit` | *He would come to my apartment again.* | right: a habit, though it may be a promise |
| `must-guess` | *You must... There must be more...* | not counted: too broken to call |

## The next 16 (2026-10-22)

The 16 points told by form from the proposal, with the same method and the
transformer model throughout. The rules were tuned on the dev half and
graded on the test half. **The grades below are from before the fixes I made
after reading the test half.** Those fixes are listed after the table.

| point | matches read | wrong | precision |
|---|---:|---:|---:|
| `present-continuous` | 50 | 0 | 1.00 |
| `look-adjective` | 50 | 0 | 1.00 |
| `lets` | 49 | 0 | 1.00 |
| `dont-imperative` | 47 | 0 | 1.00 |
| `have-to` | 42 | 0 | 1.00 |
| `past-simple-questions` | 41 | 0 | 1.00 |
| `past-continuous` | 19 | 0 | 1.00 |
| `too-adjective` | 19 | 0 | 1.00 |
| `question-tags` | 16 | 0 | 1.00 |
| `should` | 15 | 0 | 1.00 |
| `be-supposed-to` | 6 | 0 | 1.00 |
| `if-present` | 46 | 1 | 0.98 |
| `present-simple-questions` | 50 | 2 | 0.96 |
| `present-perfect` | 50 | 2 | 0.96 |
| `superlatives` | 24 | 2 | 0.92 |
| **these 15** | **524** | **7** | **0.99** |

**`have-got` became a meaning point.** Its form is right in 49 of 50 lines,
but only 41 mean *have*. The others are *obtained* (*I've got the part*),
*caught* (*We've got her!*) and *understood* (*I've got it*). It is marked
`needs_meaning`, and Claude settles it, as with *must*.

**Against the guides:**

- Every point found all its marked lines, except `if-present`, which found
  2 of 4. The other two are one sentence broken across cues with a capital
  letter: *If H isn't for Howard...* / *Then H is for Hector!*
- `if-present` follows the guides: *if* + the present, whatever the result.
  At first I had required *will*, and it found none of their lines.
- The present perfect is one point, scored against both the guides'
  `present-perfect` and `present-perfect-experience`.

**Real misses** in the unmatched samples, at most a few a point:

- *What did your last slave die of?* (an adjective in the subject);
- *Let's just check* (an adverb after *let's*);
- *Should it be glowing?* (*should be* + *-ing*);
- *if we cannot eat*, *If you're strong enough.* (a modal in the *if* part,
  and an *if* part said alone);
- *too good-looking* (the subtitle splits the word at its hyphen);
- *hasn't got any clothes on* (the parser makes it a clause).

Short answers with no verb (*Maybe we should.*, *You have to.*) can't be
found by form, and aren't counted.

**Fixed after grading** (each with a test): the misses above, and three of the
seven wrong matches:

- *for the best*;
- *Do you mind if…*;
- *supposed to have been* and *Better have finished*, by requiring *have* to
  be a finite verb.

**Known false matches** left in:

- *Don't you worry.* reads as *Don't you see?* to the rules; only the full
  stop tells them apart.
- *Okay, is it?* reads as a question tag.
- *Best Buddies* (a name) reads as a superlative.

**Tests:** 223, all passing on both models.

## The four modals (2026-10-22)

The guides taught narrow uses: *I'll* as a decision made now, *can* as
ability, *could* as past ability. On 50 lines each, the form gives that use
for only about 15% of the *will* lines, 50% of the *can* lines and 6% of the
*could* lines. The rest are:

- *will*: predictions, promises, threats and questions;
- *can*: permission, requests, possibility and *can't believe*;
- *could*: requests, possibility, suggestions and imagined things.

Marked as candidates, *will* alone would put about 20 marks an episode in the
dialogue, most of them wrong.

**The owner's decision:** one note per modal, covering all its uses, as
CEFR-J has one item per modal. The guides' ids are aliases: `will`
(`will-decisions`), `can` (`can-ability`), `could` (`could-past-ability`).
Told this way, they are form points.

| point | form right | against the guides |
|---|---:|---|
| `will` | 50 of 50 | all 30 marked lines |
| `can` | 50 of 50 | all 7 |
| `could` | 50 of 50 | 4 of 7: the other 3 have no verb (*I could!*) |
| `might` | 14 of 16, before excluding *might wanna* (polite advice) | 1 of 1 |

So the library holds 30 points: 25 told by form, and 5 meaning points that
Claude settles (`must-obligation`, `must-guess`, `have-got`, and the untagged
`would-past-habit`). There are 252 tests, all passing on both models.

## Notes for all 30 (2026-10-22)

Every point has its note now: a gist in English and Persian, its forms, the
mistakes learners make, what it is easily confused with, and three exercises.
All 30 validate against Bembegoo's entry schema. The Persian passes the lint;
the only flags are English sentences quoted inside it.

Where the guides had copies of a note, the new one starts from the best of
them, with their faults fixed. Merged points get one note covering every use:

- *will*, *can* and *could*;
- the present continuous: now, and plans already arranged;
- the present perfect: a result, and an experience.

**What an episode gets now:** on Stuart e06, 116 of 495 lines carry a mark,
127 marks in all. Most come from A1 points: the present continuous on 39
lines, *can* on 14. Stuart is a B1 course, and a guide teaches what is at the
course's level and above.
