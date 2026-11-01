"""Conservative BCCWJ lemma-weighted reading estimates (not surface token counts)."""
import argparse
from collections import Counter, defaultdict
import csv
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import unicodedata
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[3]
SOURCE_URL = 'https://repository.ninjal.ac.jp/record/3234/files/BCCWJ_frequencylist_suw_ver1_0.zip'
SOURCE_SHA256 = '4e082faa51bedb77b69003358b55278c6736fd32124fc38a93b1b125c64834ba'
MEMBER = 'BCCWJ_frequencylist_suw_ver1_0.tsv'


def kana(text):
    text = unicodedata.normalize('NFC', text)
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in text)


def align(word, pronunciation, inventory):
    """Return at most two complete alignments; two means ambiguous, never guess.

    Dotted readings consume their written okurigana too. No automatic rendaku,
    gemination, inflection, spelling-variant or irregular whole-word guessing.
    """
    word, pronunciation = unicodedata.normalize('NFC', word), kana(pronunciation)

    @lru_cache(None)
    def visit(i, j):
        if i == len(word):
            return ((),) if j == len(pronunciation) else ()
        char = word[i]
        choices = []
        if char in inventory:
            for reading in inventory[char]['readings']:
                stem, dot, suffix = reading.partition('.')
                if dot and not word.startswith(suffix, i + 1):
                    continue
                spoken = kana(stem + suffix)
                choices.append((spoken, i + 1 + len(suffix), (char, reading)))
        elif 'ぁ' <= kana(char) <= 'ゖ' or char == 'ー':
            choices.append((kana(char), i + 1, None))
        else:
            return ()
        results = []
        for spoken, next_i, assignment in choices:
            if pronunciation.startswith(spoken, j):
                for tail in visit(next_i, j + len(spoken)):
                    result = ((assignment,) if assignment else ()) + tail
                    if result not in results:
                        results.append(result)
                    if len(results) == 2:
                        return tuple(results)
        return tuple(results)
    return visit(0, 0)


def compute(rows, inventory):
    counts, textbook = Counter(), Counter()
    eligible, mapped = Counter(), Counter()
    examples = defaultdict(Counter)
    stats = defaultdict(lambda: {'rows': 0, 'frequency': 0, 'textbook_frequency': 0})
    audit = []
    for row in rows:
        word, reading = row['lemma'], row['lForm']
        frequency = int(row['frequency'])
        ot = int(row['OT_frequency'] or 0)
        if frequency < 0 or ot < 0 or ot > frequency:
            raise ValueError('Invalid source count')
        chars = [c for c in word if c in inventory]
        matches = ()
        if '固有名詞' in row['pos']:
            status = 'excluded_proper_name'
        elif not chars:
            status = 'no_inventory_kanji'
        else:
            for char in chars:
                eligible[char] += frequency
            matches = align(word, reading, inventory)
            status = 'mapped' if len(matches) == 1 else 'ambiguous' if matches else 'unmapped'
        stats[status]['rows'] += 1
        stats[status]['frequency'] += frequency
        stats[status]['textbook_frequency'] += ot
        if status == 'mapped':
            for char, canonical in matches[0]:
                key = (char, canonical)
                counts[key] += frequency
                textbook[key] += ot
                mapped[char] += frequency
                examples[key][(word, reading)] += frequency
        if chars and status != 'excluded_proper_name':
            audit.append({'lemma': word, 'lemma_reading': reading, 'pos': row['pos'],
                          'frequency': frequency, 'textbook_frequency': ot,
                          'status': status, 'alignments': matches})
    result = {}
    for char, entry in inventory.items():
        readings = []
        for reading in entry['readings']:
            key = (char, reading)
            count = counts[key]
            readings.append({
                'reading': reading, 'estimated_count': count,
                'textbook_estimated_count': textbook[key],
                'rank': 1 + sum(counts[(char, r)] > count for r in entry['readings']) if count else None,
                'share_of_mapped': count / mapped[char] if mapped[char] else None,
                'examples': [{'word': w, 'lemma_reading': r, 'weight': n}
                             for (w, r), n in examples[key].most_common(5)],
            })
        result[char] = {
            'eligible_character_weight': eligible[char],
            'mapped_character_weight': mapped[char],
            'coverage': mapped[char] / eligible[char] if eligible[char] else None,
            'readings': sorted(readings, key=lambda r: (-r['estimated_count'], r['reading'])),
        }
    return {'statistics': dict(stats), 'kanji': result}, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ROOT / 'data/bccwj/BCCWJ_frequencylist_suw_ver1_0.zip')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/bccwj/reading-frequency.json')
    args = parser.parse_args()
    archive_hash = hashlib.sha256(args.archive.read_bytes()).hexdigest()
    if archive_hash != SOURCE_SHA256:
        raise ValueError('Source checksum mismatch; review the source version before changing the pin')
    inventory_path = ROOT / 'datasets/japanese/kanji.yaml'
    inventory = yaml.safe_load(inventory_path.read_text())['kanji']
    with zipfile.ZipFile(args.archive) as archive:
        with archive.open(MEMBER) as raw:
            rows = csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8-sig'), delimiter='\t')
            if not {'lemma', 'lForm', 'pos', 'frequency', 'OT_frequency'} <= set(rows.fieldnames):
                raise ValueError('Unexpected source columns')
            result, audit = compute(rows, inventory)
    total_rows = sum(s['rows'] for s in result['statistics'].values())
    total_frequency = sum(s['frequency'] for s in result['statistics'].values())
    if (total_rows, total_frequency) != (185136, 104612423):
        raise ValueError(f'Unexpected corpus totals: {total_rows}, {total_frequency}')
    result = {'schema': 1, 'method': 'exact-unambiguous-lemma-alignment-v1',
              'source': {'name': 'BCCWJ short-unit frequency list v1.0 (2015-11-18 correction)',
                         'url': SOURCE_URL, 'archive_sha256': archive_hash,
                         'inventory_sha256': hashlib.sha256(inventory_path.read_bytes()).hexdigest()},
              'limitations': [
                  'Lemma-weighted estimates, not observed written-kanji or surface-reading token counts.',
                  'Lemma frequency merges spelling, pronunciation and inflection variants.',
                  'Proper names excluded; only unique complete exact alignments counted.',
                  'Unmapped and ambiguous lemmas contribute no reading counts.',
                  'No inferred rendaku, gemination, inflected okurigana, repetition marks or character variants.',
                  'Zero means no mapped evidence, not a rare or unused reading.',
                  'Shares are conditional on mapped evidence; coverage must be considered.',
                  'Textbook counts are the OT register, not school-year assignments.',
              ], **result}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    audit_path = args.output.with_suffix('.audit.jsonl')
    with audit_path.open('w') as stream:
        for row in audit:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    stats = result['statistics']
    eligible_weight = sum(stats[s]['frequency'] for s in ('mapped', 'unmapped', 'ambiguous'))
    kanji = result['kanji']
    report = [
        '# BCCWJ reading-frequency estimates', '',
        'These are **lemma-weighted estimates**, not counts of written kanji or exact surface pronunciations.',
        'Spelling, pronunciation and inflection variants are grouped under dictionary headwords in this source.',
        'Use coverage alongside ranks. Zero counts mean missing mapped evidence, not that a reading is unused.', '',
        f'- Source rows: {total_rows:,}; total corpus word frequency: {total_frequency:,}.',
        f'- Mapped eligible lemma frequency: {stats["mapped"]["frequency"]:,} / {eligible_weight:,} '
        f'({stats["mapped"]["frequency"] / eligible_weight:.1%}).',
        f'- Kanji with mapped evidence: {sum(v["mapped_character_weight"] > 0 for v in kanji.values()):,} / {len(kanji):,}.',
        f'- Readings with mapped evidence: {sum(r["estimated_count"] > 0 for v in kanji.values() for r in v["readings"]):,} '
        f'/ {sum(len(v["readings"]) for v in kanji.values()):,}.', '',
        '| Classification | Rows | Word frequency | OT textbook frequency |',
        '| --- | ---: | ---: | ---: |',
    ]
    for status, values in stats.items():
        report.append(f'| {status} | {values["rows"]:,} | {values["frequency"]:,} | {values["textbook_frequency"]:,} |')
    report.extend(['', '## Example rankings', '',
                   'Coverage is the mapped share of eligible character weight in headwords, excluding proper names.',
                   'Each repeated character contributes separately. This differs from the word-frequency coverage above.', '',
                   '| Kanji | Coverage | Top mapped readings (estimated weight) |', '| --- | ---: | --- |'])
    for char in '生上下日行一':
        entry = kanji[char]
        top = ', '.join(f'{r["reading"]} ({r["estimated_count"]:,})' for r in entry['readings'][:5] if r['estimated_count'])
        report.append(f'| {char} | {entry["coverage"]:.1%} | {top} |')
    report.extend(['', '## Interpretation limits', '',
                   '- 下「くださる」 includes kana spellings grouped into the same lemma.',
                   '- Numeral/suffix segmentation can separate 一 and つ; a zero for ひと.つ is not evidence of rarity.',
                   '- 学校 → がっこう is excluded by this exact matcher; it does not infer がっ → ガク.',
                   '- Irregular whole-word readings such as 今日 → きょう are not split between characters.',
                   '- Counts use only frequency and OT_frequency, never sums of overlapping corpus registers.',
                   '- Neither frequency nor OT presence supplies a school-year assignment.', '',
                   'Source: ' + SOURCE_URL, '',
                   'Method and reproduction: `datasets/japanese/reading-frequency.md`. Full source-row decisions: the sibling `.audit.jsonl` file.', ''])
    args.output.with_suffix('.md').write_text('\n'.join(report))
    print(json.dumps(result['statistics'], indent=2))
    print(f'Output: {args.output}\nAudit: {audit_path}')


if __name__ == '__main__':
    main()
