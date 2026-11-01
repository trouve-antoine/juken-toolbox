import argparse
from pathlib import Path
import sqlite3
import sys

# Enable Unicode-aware line editing for input(); the terminal's default echo
# can leave stale cells when deleting double-width Japanese characters.
try:
    import readline
except ImportError:
    readline = None  # Optional on Python builds without readline (e.g. Windows).
else:
    # Do not let another profile recall previous quiz answers with the up arrow.
    readline.set_auto_history(False)

import yaml

from .quiz import LEVELS, check_answer, eligible, load_profiles, load_vocab, make_quiz
from .storage import Store

ROOT = Path(__file__).resolve().parents[3]


def choose(label, choices):
    print(label)
    for key, name in choices.items():
        print(f"  {key}: {name}")
    while True:
        value = input("> ").strip()
        if value in choices:
            return value
        print("Choose one of the listed IDs.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Kanji reading quiz — answer in hiragana.")
    parser.add_argument("--vocab", type=Path, default=ROOT / "datasets/japanese/vocab.yaml")
    parser.add_argument("--profiles", type=Path, default=ROOT / "apps/quiz/profiles.yaml")
    parser.add_argument("--db", type=Path, default=ROOT / "data/juken.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("profiles", help="List pre-registered profiles")
    commands.add_parser("levels", help="List available word counts")
    quiz = commands.add_parser("quiz", help="Start a reading quiz")
    quiz.add_argument("--profile")
    quiz.add_argument("--level", choices=LEVELS)
    quiz.add_argument("--count", type=int, default=10)
    stats = commands.add_parser("stats", help="Show persistent profile statistics")
    stats.add_argument("--profile")
    args = parser.parse_args(argv)
    store = None
    try:
        if args.command == "levels":
            vocab = load_vocab(args.vocab)
            for level in LEVELS:
                print(f"{level:12} {len(eligible(vocab, level)):5} words")
            return 0
        profiles = load_profiles(args.profiles)
        if args.command == "profiles":
            for key, name in profiles.items():
                print(f"{key}: {name}")
            return 0
        profile = args.profile or choose("Select profile:", profiles)
        if profile not in profiles:
            raise ValueError(f"Unknown profile {profile!r}. Run 'profiles' to see choices.")
        if args.command == "stats":
            store = Store(args.db)
            result = store.stats(profile)
            total = result["answered"]
            accuracy = result["correct"] / total * 100 if total else 0
            print(f"{profiles[profile]}: {result['correct']}/{total} correct ({accuracy:.0f}%)")
            print(f"{result['sessions']} sessions; {result['words']} distinct words")
            for row in result["levels"]:
                print(f"  {row['level']}: {row['correct']}/{row['answered']} correct")
            if result["mistakes"]:
                readings = {q.word: " / ".join(q.answers) for q in load_vocab(args.vocab)}
                print("Words to practise (lifetime mistakes):")
                for row in result["mistakes"]:
                    reading = readings.get(row["word"], "reading unavailable")
                    print(f"  {row['word']} ({reading}): {row['mistakes']} mistakes / {row['answered']} answers")
            return 0
        if args.count < 1:
            raise ValueError("Question count must be positive.")
        vocab = load_vocab(args.vocab)
        available = {level: f"{len(eligible(vocab, level))} words" for level in LEVELS
                     if eligible(vocab, level)}
        level = args.level or choose("Select level:", available)
        if not eligible(vocab, level):
            raise ValueError(f"No words assigned to {level}. Run 'levels' to see available choices.")
        store = Store(args.db)
        questions = make_quiz(vocab, level, args.count, store.answer_counts(profile))
        if not questions:
            print(f"No words with positive weight for {profiles[profile]} at level {level}. "
                  "The current weighting function excludes all matching words.")
            return 0
        session = store.start(profile, level, len(questions))
        correct = answered = 0
        print(f"{profiles[profile]} · {level} · {len(questions)} words")
        print("Write one reading in hiragana. Empty Enter counts as incorrect. :quit ends the quiz. Any listed reading is accepted.")
        try:
            for position, question in enumerate(questions, 1):
                while True:
                    answer = input(f"[{position}/{len(questions)}] {question.word}: ")
                    if answer.strip() == ":quit":
                        raise EOFError
                    try:
                        is_correct = check_answer(question, answer)
                        break
                    except ValueError as error:
                        print(error)
                store.record(session, position, question, answer, is_correct)
                answered += 1
                correct += int(is_correct)
                print("✓ Correct!" if is_correct else "✗ Incorrect.")
                print("Readings: " + " / ".join(
                    r.text + (f" ({r.hint})" if r.hint else "") for r in question.readings))
        except (EOFError, KeyboardInterrupt):
            print("\nQuiz stopped; answered questions are saved.")
        finally:
            store.finish(session, answered == len(questions))
        print(f"Result: {correct}/{answered} correct. Stats saved.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 0
    finally:
        if store is not None:
            store.close()


if __name__ == "__main__":
    sys.exit(main())
