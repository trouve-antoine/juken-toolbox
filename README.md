# Juken

Two independent Japanese study apps share the datasets in this repository.
Run the commands below from the repository root.

| Location | Purpose |
| --- | --- |
| [apps/quiz/](apps/quiz/README.md) | Python terminal vocabulary quiz, profiles, weighted review, and SQLite statistics |
| [apps/poster/](apps/poster/README.md) | Node server and browser UI for printable kanji posters and study cards |
| [datasets/japanese/](datasets/japanese/README.md) | Shared vocabulary, kanji, official readings, strokes, examples, and provenance |
| datasets/japanese/scripts/ | Data extraction and generation tools |
| tests/ | Python quiz and data-pipeline tests |
| data/ | Ignored local database, downloaded sources, and generated analysis outputs |
| juken/ | Compatibility bridge for `python -m juken`; implementation is in apps/quiz/juken/ |

The poster API is read-only and independent of the quiz. It does not serve quiz
sessions, profiles, or statistics.

## Terminal quiz

Requires Python 3.9 or later.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m juken quiz
```

Profiles live in `apps/quiz/profiles.yaml`. Existing statistics remain at
`data/juken.sqlite3`. See the [quiz documentation](apps/quiz/README.md).

## Browser poster

Requires Node 20 or later.

```sh
npm install
npm start
```

For development, run `npm run dev` to restart the server automatically when
poster code, browser assets, or Japanese datasets change. Refresh the browser to
see the changes. This uses Node’s built-in watch mode (directory watching on
macOS and Windows), with no extra dependencies. Stop it with Ctrl-C.


Open http://127.0.0.1:3000/?n=6&level=e1. See the
[poster documentation](apps/poster/README.md).

## Checks and local dependencies

```sh
npm test
.venv/bin/python -m unittest discover -s tests -v
```

Node dependencies and scripts are managed by the root `package.json`; Python
runtime dependencies are in `requirements.txt`. Some data tools need additional
dependencies documented beside the datasets.

`.venv/` and `node_modules/` contain installed dependencies. The ignored `source/`
directory is an older Python virtual environment, not application source.
Dataset provenance, regeneration commands, and use restrictions are documented in
[datasets/japanese/README.md](datasets/japanese/README.md).
