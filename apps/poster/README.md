# Kanji poster and study cards

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

Example data lives in `datasets/japanese/card-examples.json`. It combines official
Agency for Cultural Affairs reading-specific examples with existing vocabulary
pronunciations, exact vocabulary alignments, explicit kun forms, and 90 locally
curated supplements in `datasets/japanese/card-example-supplements.json` for remaining
gaps and sound changes. All 4,388 readings have at least one example; coverage
tests are structural checks, not independent linguistic certification. Examples
can be above the poster's selected school grade. The vocabulary-derived examples
retain the private educational-use limitations described in `datasets/japanese/README.md`.

To rebuild the examples (Python requirements installed):

```sh
mkdir -p data/cards
curl -L --fail https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/kanji/joyokanjisakuin/index.html -o data/cards/joyo.html
.venv/bin/python datasets/japanese/scripts/build_card_examples.py
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
`apps/poster/public/themes/`; shared layout and print geometry stay in `apps/poster/public/style.css`.
To add a theme, create `apps/poster/public/themes/<id>.css` and register its id and label in
`apps/poster/public/themes.js`, then restart the server. Use the existing CSS variables and
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

The backend is independent of the poster, reads `datasets/japanese/kanji.yaml` and the
checked-in extraction `datasets/japanese/mext-readings.json` at startup,
and exposes versioned, read-only JSON endpoints for future clients:

- `GET /api/v1/levels` → `{ data: [{ id, label, count }] }`.
- `GET /api/v1/kanji?level=e1` → `{ data: [{ character, writingLevel, readings:
  [{ text, level, hint, type, displayText, specialOrNarrowUse, mextOrder }] }], meta: { level, total } }`.
- Omitting the API's `level` returns all kanji. Every result keeps **all** reading
  metadata; clients choose which readings to display. Unknown levels return 400.

`apps/poster/server/kanji.js` handles source loading/filtering, `apps/poster/server/app.js` HTTP routing,
and `apps/poster/public/` presentation. No frontend build step or framework is needed. The
server binds to loopback by default; `HOST` and `PORT` override the address.
Run backend/data checks with `npm test`.


All commands above run from the repository root.
