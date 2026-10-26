"""Extract MEXT's 2017 main reading table, including narrow-use indentation.

Requires pdfplumber and PyYAML. Coordinates are pinned to the source checksum.
The final two appendix pages contain whole words and are outside this extractor.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

import pdfplumber
import yaml

ROOT = Path(__file__).resolve().parents[2]
URL = 'https://www.mext.go.jp/a_menu/shotou/new-cs/__icsFiles/afieldfile/2017/05/15/1385768.pdf'
SHA256 = '0bc189982a50122f1e35dd6a751bfdff0ec5a0ad67e99eda916d012f859a5ae4'
STAGES = {192.24: 'e', 232.56: 'j', 272.88: 'h'}


def extract(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Unexpected PDF checksum; review coordinates for the new version')
    data = {}
    current = None
    with pdfplumber.open(path) as document:
        assert len(document.pages) == 52
        for page_number, page in enumerate(document.pages[1:50], 2):
            words = page.extract_words(x_tolerance=1, y_tolerance=2)
            for column in range(3):
                offset = 240.24 * column
                rows = defaultdict(list)
                for word in words:
                    if 98 < word['top'] < 518 and 56 + offset <= word['x0'] < 296 + offset:
                        rows[round(word['top'])].append(word)
                for y, words_in_row in sorted(rows.items()):
                    words_in_row.sort(key=lambda w: w['x0'])
                    label = ''.join(w['text'] for w in words_in_row if w['x0'] < 110 + offset)
                    reading_words = [w for w in words_in_row if 110 + offset <= w['x0'] < 177 + offset]
                    if not reading_words:
                        continue
                    reading = ''.join(w['text'] for w in reading_words)
                    # 𠮟 is an outlined glyph without extractable text. Confirmed
                    # visually on physical PDF page 20 (printed page 19).
                    if (page_number, column, y) == (20, 2, 185):
                        assert not label and reading == 'シツ'
                        label = '𠮟'
                    if label:
                        match = re.fullmatch(r'(.)([1-6]?)', label)
                        assert match, (page_number, label)
                        current, year = match.groups()
                        assert current not in data, current
                        data[current] = {'introduction_grade': int(year) if year else None, 'readings': []}
                    assert current is not None
                    marks = [w for w in words_in_row if w['x0'] >= 177 + offset]
                    assert len(marks) == 1 and marks[0]['text'] == '○', (page_number, reading)
                    mark_x = marks[0]['x0'] - offset
                    stage_x = min(STAGES, key=lambda x: abs(x - mark_x))
                    assert abs(stage_x - mark_x) < .1
                    reading_x = reading_words[0]['x0'] - offset
                    assert any(abs(reading_x - x) < .1 for x in (121.2, 126.96, 127.44))
                    data[current]['readings'].append({
                        'text': reading, 'stage': STAGES[stage_x],
                        'special_or_narrow_use': reading_x > 124,
                        'pdf_page': page_number, 'printed_page': page_number - 1,
                        'column': column + 1, 'top_pt': y,
                        'reading_x_relative_pt': round(reading_x, 2),
                    })
    return data


def validate(data, inventory):
    assert set(data) == set(inventory) and len(data) == 2136
    stages = Counter()
    for character, entry in data.items():
        original = inventory[character]
        assert original.get('writing') == (f'e{entry["introduction_grade"]}' if entry['introduction_grade'] else None)
        expected = {reading.replace('.', ''): (reading, stage) for reading, stage in original['readings'].items()}
        assert len(expected) == len(original['readings'])
        assert {r['text'] for r in entry['readings']} == set(expected), character
        assert len(entry['readings']) == len(expected), character
        for reading in entry['readings']:
            canonical, stage = expected[reading['text']]
            assert reading['stage'] == stage, (character, reading)
            # Optional join key only: dots come from our inventory, not the PDF.
            reading['inventory_key'] = canonical
            stages[stage] += 1
    assert stages == {'e': 2062, 'j': 2008, 'h': 318}, stages
    assert sum(r['special_or_narrow_use'] for e in data.values() for r in e['readings']) == 178


def first_grade_report(data):
    lines = ['# 漢字：小学校１年生 — MEXT readings', '',
             'Extracted directly from the March 2017 MEXT PDF. Reading order and spelling follow the PDF; no frequency ranking is implied.', '',
             'The grade identifies when the **character** is introduced. Reading assignments are for the entire elementary, junior-high, or high-school stage, not a specific year.', '',
             'MEXT note 3 says indented readings have special or very narrow uses. They are separated below. Unindented does not mean “most frequent.”', '',
             '| Kanji | Elementary: unindented | Elementary: special / narrow use | Later-stage readings | PDF page |',
             '| :---: | --- | --- | --- | ---: |']
    for char, entry in data.items():
        if entry['introduction_grade'] != 1:
            continue
        normal, special, later = [], [], []
        for reading in entry['readings']:
            text = reading['text']
            if reading['stage'] == 'e':
                (special if reading['special_or_narrow_use'] else normal).append(text)
            else:
                stage = {'j': '中', 'h': '高'}[reading['stage']]
                later.append(f'{text} ({stage}{"・special" if reading["special_or_narrow_use"] else ""})')
        page = entry['readings'][0]['pdf_page']
        lines.append(f'| {char} | {"、".join(normal) or "—"} | {"、".join(special) or "—"} | {"、".join(later) or "—"} | {page} |')
    lines += ['', 'PDF pages are physical, one-based pages including the cover. The PDF omits okurigana separator dots.', '',
              f'[MEXT source PDF]({URL})', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, default=ROOT / 'data/mext/1385768.pdf')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/mext/readings.json')
    args = parser.parse_args()
    data = extract(args.pdf)
    inventory_path = ROOT / 'japanese/kanji.yaml'
    validate(data, yaml.safe_load(inventory_path.read_text())['kanji'])
    result = {'schema': 1, 'source': {'url': URL, 'sha256': SHA256, 'date': '2017-03',
              'scope': 'Main kanji table, physical pages 2–50; whole-word appendices excluded',
              'inventory_sha256': hashlib.sha256(inventory_path.read_bytes()).hexdigest()},
              'method': 'coordinate-table-extraction-v1',
              'notes': {'special_or_narrow_use': 'PDF note 3: indented readings are special or have very narrow uses, not a frequency ranking.',
                        'inventory_key': 'Join key from existing kanji.yaml; okurigana dots are not extracted from this PDF.',
                        'outlined_glyph': '𠮟 restored from visual inspection at physical page 20, column 3, top 185pt.'},
              'kanji': data}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    report = args.output.with_name('first-grade-readings.md')
    report.write_text(first_grade_report(data))
    first_grade_special = [(c, r['text']) for c, e in data.items() if e['introduction_grade'] == 1
                           for r in e['readings'] if r['stage'] == 'e' and r['special_or_narrow_use']]
    print(f'Validated {len(data)} kanji, 4388 readings, all grades and stage assignments against existing inventory.')
    print('178 special/narrow-use readings preserved. First-grade elementary subset:', first_grade_special)
    print(f'Data: {args.output}\nReport: {report}')


if __name__ == '__main__':
    main()
