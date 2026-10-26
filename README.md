# Juken — kanji reading quiz

## Kanji poster and Node API

Click a poster tile (or focus it and press Enter/Space) to open a kanji study
card. It shows a large numbered stroke diagram with Replay/Next stroke controls,
and example words with kana readings for **every** official reading, including
later school stages. Escape, Close, and backdrop clicks dismiss the native modal;
keyboard focus returns to the tile. Reduced-motion preferences disable animated
playback. Cards and their controls are excluded from print.
Previous/Next buttons and Left/Right arrow keys move through the current poster's
kanji list, across page boundaries. The card shows its position in that list;
navigation stops at the first and last kanji. Switching cards cancels any pending
request and stroke animation.

`GET /api/v1/kanji/:character` returns full reading groups with `examples` and
KanjiVG `strokes` (paths, labels, viewbox and attribution). The heavier card data
is loaded lazily; the existing list endpoint remains lightweight.

Example data lives in `japanese/card-examples.json`. It combines official
Agency for Cultural Affairs reading-specific examples with existing vocabulary
pronunciations, exact vocabulary alignments, explicit kun forms, and 90 locally
curated supplements in `japanese/card-example-supplements.json` for remaining
gaps and sound changes. All 4,388 readings have at least one example; coverage
tests are structural checks, not independent linguistic certification. Examples
can be above the poster's selected school grade. The vocabulary-derived examples
retain the private educational-use limitations described in `japanese/README.md`.

To rebuild the examples (Python requirements installed):

```sh
mkdir -p data/cards
curl -L --fail https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/kanji/joyokanjisakuin/index.html -o data/cards/joyo.html
.venv/bin/python japanese/scripts/build_card_examples.py
```

Stroke geometry is from KanjiVG, © Ulrich Apel, CC BY-SA 3.0. Attribution and
license links are shown in each card; original paths are retained while display
colors, numbering and playback are applied in the browser.

Requires Node 20 or later. From the project root:

```sh
npm install
npm start
```

Open `http://127.0.0.1:3000/?n=6&level=e1`. The vanilla HTML/CSS/JS page
accepts `n=2`–`10` **columns** (default 6) and `level` (default `e1`). Rows
are computed from the A4 portrait area and the actual rendered reading heights.
All selected kanji are split across as many pages as needed, in source order.
The final page retains the same tile size. Print on A4 at 100% scale with browser
headers and footers disabled. Japanese system fonts are used; install a Japanese
font such as Noto Serif CJK JP if your system does not provide one.
The Print A4 button opens a separate controls-free document (`&print=1`) and
requests the print dialog after fonts and layout are ready. Printing uses 10 mm
page margins and explicit page breaks. Kanji and readings start at fixed positions
within each tile, independent of the number of readings.

The Theme dropdown applies `theme=simple` (default) or `theme=colorful` to the
URL and preserves it when printing. Each theme lives in its own stylesheet under
`public/themes/`; shared layout and print geometry stay in `public/style.css`.
To add a theme, create `public/themes/<id>.css` and register its id and label in
`public/themes.js`, then restart the server. Use the existing CSS variables and
keep tile dimensions unchanged. Color printing requests background colors;
enable background graphics in the print dialog if the browser omits them.

`e1`–`e6` select exact elementary character introduction grades; `e`, `j`, and
`h` select kanji with readings assigned to that school stage. `all` selects all
2,136 kanji. Exact `j1`–`j3` and `h1`–`h3` return empty lists because the source
does not assign those years. Posters show up to three readings for the selected
stage (elementary readings for elementary year posters). MEXT unindented readings
come first, followed by special/narrow-use readings, preserving PDF order within
each category. Special/narrow-use readings use smaller text; on/kun type does not
determine priority. “Show all readings” (`showAll=1`) restores the complete list
and is preserved when printing. Display spelling follows the PDF, without dots.
This is not a frequency ranking, and no reading mastery year is inferred.

The backend is independent of the poster, reads `japanese/kanji.yaml` and the
checked-in extraction `japanese/mext-readings.json` at startup,
and exposes versioned, read-only JSON endpoints for future clients:

- `GET /api/v1/levels` → `{ data: [{ id, label, count }] }`.
- `GET /api/v1/kanji?level=e1` → `{ data: [{ character, writingLevel, readings:
  [{ text, level, hint, type, displayText, specialOrNarrowUse, mextOrder }] }], meta: { level, total } }`.
- Omitting the API's `level` returns all kanji. Every result keeps **all** reading
  metadata; clients choose which readings to display. Unknown levels return 400.

`server/kanji.js` handles source loading/filtering, `server/app.js` HTTP routing,
and `public/` presentation. No frontend build step or framework is needed. The
server binds to loopback by default; `HOST` and `PORT` override the address.
Run backend/data checks with `npm test`.

The first implementation is a Python CLI with persistent SQLite statistics.
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

Profiles are fixed in `profiles.yaml`; the app has no profile creation or editing
commands. IDs are the statistics keys, so keep IDs stable when changing display
names. Profile selection is not authentication.

## Vocabulary and grading

The app reads `japanese/vocab.yaml` directly and excludes entries with no readings.
It supports both `reading: level` and `reading: [level, hint]` metadata.

- `e`, `j`, `h`: the selected stage, including any explicit years within it.
- `e1`–`e6`, `j1`–`j3`, `h1`–`h3`: only that exact year, not cumulative.
- `unassigned`: readings whose level is `null`.
- `all`: all words with readings, including unassigned ones.

The current dataset has no exact-year vocabulary assignments. Selecting `e2`
reports an empty pool; it never infers a vocabulary grade from kanji grades.
Interactive selection only offers levels with words. `levels` lists every level
and its pool size. See `japanese/README.md` for dataset provenance and limitations.

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

Tune `juken/weights.py` directly; no configuration or database migration is needed.
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

- `juken/quiz.py`: vocabulary loading, level selection, sampling, answer validation.
- `juken/weights.py`: editable answer-history weighting function and multipliers.
- `juken/storage.py`: SQLite persistence and aggregate statistics.
- `juken/__main__.py`: terminal interaction only.

The staged plan is CLI → API → GUI. This change implements the CLI stage. The API
can reuse the quiz and persistence modules, then provide profile/level discovery,
server-held quiz sessions, answer submission, and statistics. The GUI can consume
those endpoints. Correct readings should stay on the server until submission.

Global flags override local file locations and go **before** the command:

```sh
.venv/bin/python -m juken --db /tmp/practice.sqlite3 quiz --profile antoine --level e
.venv/bin/python -m unittest discover -s tests -v
```
