from contextlib import redirect_stdout, redirect_stderr
import io
import math
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from juken.__main__ import main
from juken.quiz import Reading, Question, check_answer, eligible, load_vocab, make_quiz
from juken.storage import Store
from juken.weights import _word_weight as word_weight
from juken.weights import word_weight as review_weight


FIXTURE = """vocab:
  学校:
    readings:
      がっこう: e2
  今日:
    readings:
      きょう: [e, 今日という日]
      こんにち: j
  海:
    readings:
      うみ: null
  空:
    sources: []
"""


class QuizTests(unittest.TestCase):
    def setUp(self):
        # General quiz tests use the original weighting policy; review-mode tests
        # explicitly select the user's zero-weight policy below.
        weighting = patch("juken.quiz.word_weight", side_effect=word_weight)
        weighting.start()
        self.addCleanup(weighting.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vocab_path = self.root / "vocab.yaml"
        self.vocab_path.write_text(FIXTURE, encoding="utf-8")
        self.vocab = load_vocab(self.vocab_path)

    def test_levels_do_not_invent_years_or_include_unknown(self):
        self.assertEqual([q.word for q in eligible(self.vocab, "e2")], ["学校"])
        self.assertEqual([q.word for q in eligible(self.vocab, "e")], ["学校", "今日"])
        self.assertEqual([q.word for q in eligible(self.vocab, "j")], ["今日"])
        self.assertEqual([q.word for q in eligible(self.vocab, "unassigned")], ["海"])
        self.assertEqual(len(eligible(self.vocab, "all")), 3)
        with self.assertRaisesRegex(ValueError, "No words assigned"):
            make_quiz(self.vocab, "j1", 10)

    def test_alternate_readings_and_hiragana_validation(self):
        question = eligible(self.vocab, "e")[1]
        self.assertTrue(check_answer(question, " きょう　"))
        self.assertTrue(check_answer(question, "こんにち"))
        self.assertFalse(check_answer(question, "きょ"))
        self.assertEqual(question.readings[0].hint, "今日という日")
        self.assertFalse(check_answer(question, ""))
        self.assertFalse(check_answer(question, " 　"))
        for answer in ("キョウ", "kyou", "今日", "きょ う"):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                check_answer(question, answer)
        self.assertTrue(check_answer(self.vocab[0], "か\u3099っこう"))

    def test_sampling_is_bounded_and_does_not_repeat_words(self):
        questions = make_quiz(self.vocab, "all", 100)
        self.assertEqual(len(questions), 3)
        self.assertEqual(len({q.word for q in questions}), 3)
        with self.assertRaises(ValueError):
            make_quiz(self.vocab, "all", 0)

    def test_weight_formula_and_long_histories(self):
        self.assertEqual(word_weight(), 1)
        self.assertAlmostEqual(word_weight(1, 0), 0.8)
        self.assertAlmostEqual(word_weight(0, 1), 1.5)
        self.assertAlmostEqual(word_weight(2, 1), 0.96)
        self.assertGreater(word_weight(100000, 0), 0)
        self.assertTrue(math.isfinite(word_weight(0, 100000)))

    def test_zero_weights_exclude_words_and_shorten_quiz(self):
        with patch("juken.quiz.word_weight", side_effect=review_weight):
            questions = make_quiz(self.vocab, "all", 20,
                                  {"学校": (0, 1), "今日": (5, 0)})
        self.assertEqual([q.word for q in questions], ["学校"])

    def test_all_zero_weights_do_not_start_a_session(self):
        with patch("juken.quiz.word_weight", side_effect=review_weight):
            self.assertEqual(make_quiz(self.vocab, "all", 20), [])
            code, output = self.run_cli(["quiz", "--profile", "yuta", "--level", "e"])
        self.assertEqual(code, 0)
        self.assertIn("No words with positive weight", output)
        store = Store(self.root / "cli.sqlite3")
        self.addCleanup(store.close)
        self.assertEqual(store.stats("yuta")["sessions"], 0)

    def test_invalid_weights_have_clear_error(self):
        for weight in (-1, float("nan"), float("inf")):
            with self.subTest(weight=weight), patch("juken.quiz.word_weight", return_value=weight):
                with self.assertRaisesRegex(ValueError, "finite and nonnegative"):
                    make_quiz(self.vocab, "all", 1)

    def test_weighted_sampling_favors_missed_words_without_repeats(self):
        history = {"学校": (8, 0), "今日": (0, 3)}
        counts = {q.word: 0 for q in self.vocab}
        rng = random.Random(42)
        with patch("juken.quiz.random.choices", side_effect=rng.choices):
            for _ in range(4000):
                counts[make_quiz(self.vocab, "all", 1, history)[0].word] += 1
            questions = make_quiz(self.vocab, "all", 100, history)
        self.assertEqual(len({q.word for q in questions}), 3)
        total_weight = 0.8 ** 8 + 1.5 ** 3 + 1
        for word, weight in (("学校", 0.8 ** 8), ("今日", 1.5 ** 3), ("海", 1)):
            self.assertAlmostEqual(counts[word] / 4000, weight / total_weight, delta=0.03)

    def test_cli_uses_saved_counts_for_selected_profile_across_levels(self):
        db = self.root / "cli.sqlite3"
        store = Store(db)
        for profile, level, correct in (("yuta", "e", True), ("yuta", "e2", False),
                                        ("antoine", "e2", True)):
            session = store.start(profile, level, 1)
            store.record(session, 1, self.vocab[0], "がっこう" if correct else "", correct)
            store.finish(session, False)
        store.close()
        store = Store(db)
        self.assertEqual(store.answer_counts("yuta"), {"学校": (1, 1)})
        self.assertEqual(store.answer_counts("antoine"), {"学校": (1, 0)})
        self.assertEqual(store.answer_counts("new-profile"), {})
        store.close()
        with patch("juken.__main__.make_quiz", wraps=make_quiz) as make:
            code, _ = self.run_cli(["quiz", "--profile", "yuta", "--level", "e2"], ["がっこう"])
        self.assertEqual(code, 0)
        self.assertEqual(make.call_args.args[3], {"学校": (1, 1)})

    def test_persistence_and_profile_isolation(self):
        db = self.root / "stats.sqlite3"
        store = Store(db)
        session = store.start("yuta", "e2", 2)
        store.record(session, 1, self.vocab[0], "がこう", False)
        store.finish(session, False)
        store.close()
        store = Store(db)
        self.addCleanup(store.close)
        self.assertEqual(store.stats("yuta")["answered"], 1)
        self.assertEqual(store.stats("yuta")["mistakes"][0]["word"], "学校")
        self.assertEqual(store.stats("antoine")["answered"], 0)
        self.assertEqual(store.db.execute("SELECT status FROM sessions").fetchone()[0], "aborted")

    def run_cli(self, command, answers=()):
        profiles = self.root / "profiles.yaml"
        profiles.write_text("profiles: {yuta: yuta, antoine: antoine}\n", encoding="utf-8")
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output), redirect_stderr(output):
            code = main(["--vocab", str(self.vocab_path), "--profiles", str(profiles),
                         "--db", str(self.root / "cli.sqlite3"), *command])
        return code, output.getvalue()

    def test_cli_reprompts_invalid_input_and_saves_once(self):
        code, output = self.run_cli(["quiz", "--profile", "yuta", "--level", "e2"],
                                    ["gakkou", "がっこう"])
        self.assertEqual(code, 0)
        self.assertIn("Result: 1/1", output)
        code, output = self.run_cli(["stats", "--profile", "yuta"])
        self.assertIn("1/1 correct", output)
        self.assertIn("1 sessions", output)

    def test_stats_show_all_current_readings_for_missed_words(self):
        code, _ = self.run_cli(["quiz", "--profile", "yuta", "--level", "j"], [""])
        self.assertEqual(code, 0)
        code, output = self.run_cli(["stats", "--profile", "yuta"])
        self.assertEqual(code, 0)
        self.assertIn("今日 (きょう / こんにち): 1 mistakes / 1 answers", output)

    def test_suru_accepts_and_displays_all_readings_in_j_quiz(self):
        vocab = load_vocab(Path(__file__).resolve().parents[1] / "datasets/japanese/vocab.yaml")
        question = next(q for q in eligible(vocab, "j") if q.word == "擦る")
        expected = {"こする", "さする", "する", "なする"}
        self.assertTrue(expected.issubset(question.answers))
        for answer in expected | {"ちがう"}:
            with self.subTest(answer=answer), patch("juken.__main__.load_vocab", return_value=(question,)):
                code, output = self.run_cli(
                    ["quiz", "--profile", "yuta", "--level", "j", "--count", "1"],
                    [answer])
            self.assertEqual(code, 0)
            self.assertIn("Result: 1/1" if answer in expected else "Result: 0/1", output)
            self.assertIn("Readings: " + " / ".join(question.answers), output)
        store = Store(self.root / "cli.sqlite3")
        self.addCleanup(store.close)
        self.assertEqual(store.stats("yuta")["correct"], 4)

    def test_cli_blank_answer_is_saved_as_incorrect_and_advances(self):
        with patch("juken.quiz.random.choices", return_value=[0]):
            code, output = self.run_cli(
                ["quiz", "--profile", "yuta", "--level", "all", "--count", "2"],
                ["", "きょう"])
        self.assertEqual(code, 0)
        self.assertIn("✗ Incorrect.", output)
        self.assertIn("Readings: がっこう", output)
        self.assertIn("Result: 1/2", output)
        store = Store(self.root / "cli.sqlite3")
        self.addCleanup(store.close)
        row = store.db.execute(
            "SELECT answer,correct FROM attempts WHERE position=1").fetchone()
        self.assertEqual(tuple(row), ("", 0))
        self.assertEqual(store.stats("yuta")["answered"], 2)
        self.assertEqual(store.db.execute("SELECT status FROM sessions").fetchone()[0], "completed")

    def test_cli_abort_preserves_answer_and_profile_selection(self):
        with patch("juken.quiz.random.choices", return_value=[0]):
            code, output = self.run_cli(["quiz", "--level", "all"],
                                       ["yuta", "がっこう", ":quit"])
        self.assertEqual(code, 0)
        self.assertIn("Result: 1/1", output)
        store = Store(self.root / "cli.sqlite3")
        self.addCleanup(store.close)
        self.assertEqual(store.stats("yuta")["answered"], 1)
        self.assertEqual(store.db.execute("SELECT status FROM sessions").fetchone()[0], "aborted")

    def test_cli_empty_level_and_unknown_profile_do_not_start_sessions(self):
        code, output = self.run_cli(["quiz", "--profile", "yuta", "--level", "e1"])
        self.assertEqual(code, 1)
        self.assertIn("No words assigned", output)
        self.assertFalse((self.root / "cli.sqlite3").exists())
        code, output = self.run_cli(["quiz", "--profile", "nobody"])
        self.assertEqual(code, 1)
        self.assertIn("Unknown profile", output)


if __name__ == "__main__":
    unittest.main()
