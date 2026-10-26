import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('reading_frequency', Path(__file__).resolve().parents[1] / 'japanese/scripts/compute_reading_frequency.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def inventory(**entries):
    return {char: {'readings': dict.fromkeys(readings, 'e')} for char, readings in entries.items()}


class ReadingFrequencyTests(unittest.TestCase):
    def test_okurigana_requires_written_suffix(self):
        data = inventory(生=['セイ', 'い.きる', 'う.まれる'], 活=['カツ'])
        self.assertEqual(module.align('生活', 'セイカツ', data), ((('生', 'セイ'), ('活', 'カツ')),))
        self.assertEqual(module.align('生きる', 'イキル', data), ((('生', 'い.きる'),),))
        self.assertEqual(module.align('生', 'イ', data), ())
        self.assertEqual(module.align('生まれる', 'ウマレル', data), ((('生', 'う.まれる'),),))

    def test_irregular_words_and_sound_changes_are_not_guessed(self):
        data = inventory(今=['コン', 'いま'], 日=['ニチ', 'ひ'], 学=['ガク'], 校=['コウ'])
        self.assertEqual(module.align('今日', 'キョウ', data), ())
        self.assertEqual(module.align('学校', 'ガッコウ', data), ())

    def test_multiple_segmentations_are_ambiguous(self):
        data = inventory(甲=['ア', 'アイ'], 乙=['イウ', 'ウ'])
        self.assertEqual(len(module.align('甲乙', 'アイウ', data)), 2)

    def test_conservation_names_repeated_characters_and_zero_evidence(self):
        data = inventory(人=['ジン', 'ひと'], 山=['サン', 'やま'])
        rows = [
            {'lemma': '人人', 'lForm': 'ヒトヒト', 'pos': '名詞', 'frequency': '7', 'OT_frequency': '2'},
            {'lemma': '山', 'lForm': 'ヤマ', 'pos': '名詞-固有名詞', 'frequency': '100', 'OT_frequency': '0'},
            {'lemma': '人', 'lForm': 'ニン', 'pos': '名詞', 'frequency': '3', 'OT_frequency': '1'},
        ]
        result, audit = module.compute(rows, data)
        person = result['kanji']['人']
        self.assertEqual(person['eligible_character_weight'], 17)
        self.assertEqual(person['mapped_character_weight'], 14)
        self.assertEqual(sum(r['estimated_count'] for r in person['readings']), 14)
        self.assertEqual(person['readings'][0]['textbook_estimated_count'], 4)
        self.assertIsNone(person['readings'][1]['rank'])
        self.assertIsNone(result['kanji']['山']['coverage'])
        self.assertEqual(len(audit), 2)

    def test_ambiguous_weight_not_assigned_to_any_reading(self):
        data = inventory(甲=['ア', 'アイ'], 乙=['イウ', 'ウ'])
        result, _ = module.compute([{'lemma': '甲乙', 'lForm': 'アイウ', 'pos': '名詞', 'frequency': '10', 'OT_frequency': '0'}], data)
        self.assertEqual(result['statistics']['ambiguous']['frequency'], 10)
        self.assertEqual(result['kanji']['甲']['mapped_character_weight'], 0)
        self.assertEqual(result['kanji']['甲']['eligible_character_weight'], 10)


if __name__ == '__main__':
    unittest.main()
