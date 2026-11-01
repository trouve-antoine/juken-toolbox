# Reading frequency from BCCWJ

This first pass computes **lemma-weighted reading estimates** using NINJAL's
BCCWJ short-unit frequency list v1.0, corrected 2015-11-18. It does not change
the source kanji database, API, or poster ordering.

The source aggregates by lemma, lemma reading, part of speech, lemma subclass,
and word type. Its frequencies merge written forms (including kana), inflections,
and pronunciation variants. Consequently these are not observations of the
individual written kanji or its exact pronunciation in context. In particular,
this dataset alone cannot provide unbiased surface-reading probabilities.

## Reproduce

From the repository root, with the existing Python requirements installed:

```sh
mkdir -p data/bccwj
curl -L --fail https://repository.ninjal.ac.jp/record/3234/files/BCCWJ_frequencylist_suw_ver1_0.zip -o data/bccwj/BCCWJ_frequencylist_suw_ver1_0.zip
.venv/bin/python datasets/japanese/scripts/compute_reading_frequency.py
.venv/bin/python -m unittest discover -s tests -p test_reading_frequency.py -v
```

Outputs under `data/bccwj/`:

- `reading-frequency.json`: every official reading, estimated count, separate OT
  textbook count, rank, share of mapped weight, examples, per-character coverage,
  source checksums, method version and overall accounting.
- `reading-frequency.audit.jsonl`: every eligible source row, its counts,
  classification, and up to two complete alignments. Two indicates ambiguity.
- `reading-frequency.md`: computed summary and example rankings.

The archive checksum is pinned, and the program checks the documented totals:
185,136 rows and 104,612,423 word occurrences. It hashes the kanji inventory too.
Raw and generated data stay in the existing Git-ignored `data/` directory.
The source permits educational/research use, prohibits redistribution, and
requires consultation for commercial use. Local output is not a redistribution
license. See section 6 of the source manual.

## Calculation

1. Exclude proper-name rows. Identify headwords containing our kanji inventory.
2. Normalize NFC and convert katakana readings to hiragana for comparison.
3. Match the **entire** headword pronunciation against its characters' official
   readings and literal kana. Dotted readings must match and consume their
   written okurigana as well (生きる → い.きる, not simply 生 → い).
4. Accept only a unique complete alignment. Never divide ambiguous weights,
   choose a preferred candidate, or attribute only a conveniently matched prefix.
5. Add the row's `frequency` to each aligned kanji/reading occurrence. Repeated
   characters contribute repeatedly. Keep `OT_frequency` separately; never add
   overlapping register totals together. OT is not a grade-specific corpus.
6. Rank readings per character by estimated count. Ties share a rank. A zero
   retains `rank: null` because absence of mapped evidence is not rarity.

`share_of_mapped` divides a reading's weight by all mapped weight for that kanji.
`coverage` divides mapped character weight by eligible character weight, including
unmapped and ambiguous headwords in the denominator but excluding proper names.
Neither is a probability of that reading among all actual written occurrences.

The matcher deliberately leaves rendaku, gemination, inflected/shortened
okurigana in compounds, repetition marks, non-inventory characters and spelling
variants unresolved. Even a unique spelling-compatible alignment is a heuristic,
not a linguistically certified annotation. The audit supports targeted review.
For example, 学校 is unresolved, while 学生 can map exactly. Short-unit segmentation
also splits some numeral readings: no mapped evidence for 一「ひと.つ」 does not
mean that ひとつ is uncommon. Surface-token corpus annotations would be needed to
address the underlying lemma/segmentation biases rather than just adding rules.

## Sources

- [NINJAL BCCWJ frequency lists](https://clrd.ninjal.ac.jp/bccwj/freq-list.html)
- [Short-unit frequency list](https://doi.org/10.15084/00003218)
- [Method, columns, corpus totals and use conditions](https://clrd.ninjal.ac.jp/bccwj/data-files/frequency-list/BCCWJ_frequencylist_manual_ver1_0b.pdf)
