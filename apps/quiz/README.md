# Reading quiz

Python CLI with persistent SQLite statistics. All commands run from the repository root.

Requires Python 3.9 or later.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m juken quiz
```

Select a pre-registered profile (`yuta` or `antoine`), then a level. Answer each
word in hiragana. A quiz defaults to 10 weighted random words without repeats;
smaller pools use every available word. Type `:quit`, Ctrl-C, or Ctrl-D to stop.
Every answer is committed immediately, including wrong answers. Pressing Enter
with blank or whitespace-only input counts as incorrect, shows the readings, and
advances to the next word. Other non-hiragana input prompts again and does not
count as an attempt.

```sh
.venv/bin/python -m juken profiles
.venv/bin/python -m juken levels
.venv/bin/python -m juken quiz --profile yuta --level j --count 10
.venv/bin/python -m juken stats --profile yuta
```

Profiles are fixed in `apps/quiz/profiles.yaml`; the app has no profile creation or editing
commands. IDs are the statistics keys, so keep IDs stable when changing display
names. Profile selection is not authentication.

## Vocabulary and grading

The app reads `datasets/japanese/vocab.yaml` directly and excludes entries with no readings.
It supports both `reading: level` and `reading: [level, hint]` metadata.

- `e`, `j`, `h`: the selected stage, including any explicit years within it.
- `e1`–`e6`, `j1`–`j3`, `h1`–`h3`: only that exact year, not cumulative.
- `unassigned`: readings whose level is `null`.
- `all`: all words with readings, including unassigned ones.

The current dataset has no exact-year vocabulary assignments. Selecting `e2`
reports an empty pool; it never infers a vocabulary grade from kanji grades.
Interactive selection only offers levels with words. `levels` lists every level
and its pool size. See `datasets/japanese/README.md` for dataset provenance and limitations.

A word qualifies if at least one reading matches the selected level. Because
words have no sentence context, **any reading listed for that word is accepted**,
including readings assigned to other levels. All readings and available hints
are shown after answering. Input is trimmed and Unicode-normalized (NFC);
katakana and romaji are rejected. The long-vowel mark `ー` is allowed because it
occurs in the source readings.

## Statistics and architecture

Selection uses the selected profile's saved answers across all levels. The current
`word_weight` selects only words with at least one past incorrect answer, giving
them weight `1`. Words with no mistakes, including unseen words, have weight `0`
and are excluded. If fewer words qualify than requested, the quiz is shortened;
if none qualify, a message is shown and no session is started.
These are relative weights: each draw's probability
is the word's weight divided by the total weight of the remaining eligible words.
Selected words are removed from the pool so no word repeats within a quiz.

Tune `apps/quiz/juken/weights.py` directly; no configuration or database migration is needed.
Weights are recalculated from history when a quiz starts, so tuning applies to
existing answers as well. Committed answers from interrupted quizzes and blank
answers count; rejected non-hiragana input does not. Weights must be finite and
nonnegative. The original multiplier policy is retained as `_word_weight`: weight
`1` initially, multiplied by `0.8` per correct and `1.5` per incorrect answer,
bounded between `0.000001` and `1000000` for long histories.

`data/juken.sqlite3` stores sessions and individual attempts: profile, selected
level, word, submitted reading, accepted readings, correctness, and UTC timestamps.
Statistics show lifetime accuracy, totals by selected quiz level, distinct words,
and the ten words with the most mistakes. Aborted-session answers count. A process
kill can leave a session marked `in_progress`, but committed answers remain saved.
The database and virtual environment are ignored by Git.

- `apps/quiz/juken/quiz.py`: vocabulary loading, level selection, sampling, answer validation.
- `apps/quiz/juken/weights.py`: editable answer-history weighting function and multipliers.
- `apps/quiz/juken/storage.py`: SQLite persistence and aggregate statistics.
- `apps/quiz/juken/__main__.py`: terminal interaction only.

The browser poster is a separate application. Its read-only API does not expose quiz sessions or statistics.

Global flags override local file locations and go **before** the command:

```sh
.venv/bin/python -m juken --db /tmp/practice.sqlite3 quiz --profile antoine --level e
.venv/bin/python -m unittest discover -s tests -v
```
