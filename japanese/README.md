# 国語 — 高校受験

## Stroke-order data

`stokes.yaml` (filename as requested) is a separate, generated KanjiVG dataset:
**2,136 characters / 22,366 strokes**, approximately 2.47 MB of UTF-8 YAML.
It matches the exact character set in `kanji.yaml`, including 𠮟, and does not
modify the educational kanji or vocabulary databases.

- `paths`: original SVG path strings, in stroke order; one item per stroke.
- `labels`: corresponding stroke-number positions as `[x, y]` pairs.
- `viewbox`: shared `[0, 0, 109, 109]` coordinate system.
- `source`: pinned revision, archive checksum, attribution, licence and changes.

Source: [KanjiVG](https://kanjivg.tagaini.net/), © Ulrich Apel,
[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/), revision
`55b5ba92a7cad78a62ef04db4be6f9562d949b7f`. The original compressed source,
including its copyright/licence notices, is retained in
`sources/kanjivg-55b5ba92.tar.gz`. This community source is the agreed exception
to our official/academic-source preference for stroke-order information only;
it has not been individually checked against Japanese school references.

Regenerate locally with `python3 japanese/scripts/import_strokes.py` from the
project root (Python standard library and Ruby's YAML parser required).
The importer filters canonical SVG filenames to our character set, preserves
geometry and label coordinates, and omits XML/component metadata. It validates
coverage, stroke IDs/order, label numbering/counts, coordinate systems, absence
of geometry transforms, and a round-trip through an independent YAML parser.
These are structural checks, not certification of pedagogical correctness.

## Kanji and vocabulary data

The two editable UTF-8 databases are `kanji.yaml` and `vocab.yaml`. Both are flat
mappings, sorted by Unicode code point. Generated on 2026-09-06 from Japanese
official and academic sources; no foreign-language learner dictionaries were used.

- `kanji.yaml`: all **2,136 常用漢字**, all **4,388 official readings**, and the
  **1,026 elementary character allocations** in `writing`.
- `vocab.yaml`: **10,359 written forms / 10,569 word-reading pairs**, collectively
  covering **every one of the 2,136 characters**. This is a selected vocabulary
  collection, not an exhaustive Japanese dictionary or a certified entrance-exam list.

### Level codes and missing information

`e1`–`e6`, `j1`–`j3`, and `h1`–`h3` denote individual school years. `e`, `j`, and
`h` denote an entire school stage **with the exact year unspecified**. A stage
must not silently be converted to its first year. `null` means no supported learning
level has been assigned; it does not mean unsuitable, easy, or optional.

MEXT's reading table specifies school stages, not individual years. Consequently
the kanji readings use `e`, `j`, or `h`. Earlier examples in this conversation used
illustrative, unverified years and must not be treated as curriculum facts.

`writing: e4` records the character's official elementary introduction grade and
serves as the start of writing practice in this project. It does **not** assert a
national requirement to master every use of that character by the end of 小4.
Missing `writing` means outside our 1,026-character required writing set, not a
prohibition on learning to write it. Dots mark okurigana boundaries: `はぶ.く` → `省く`.

For vocabulary, a verified MEXT stage is retained for direct single-character
lexical forms and for the official whole-word appendix (such as `今日: きょう`).
Other word levels are `null`: neither corpus frequency nor the latest introduction
grade of a word's characters establishes its learning year. These levels can later
be filled from a named textbook/edition or explicitly chosen family curriculum.
Reading values support both `YEAR` and `[YEAR, short Japanese disambiguation]`;
the first value may also be a stage code or `null`.

### Sources and selection

1. [MEXT, 音訓の小・中・高等学校段階別割り振り表 (2017)](https://www.mext.go.jp/a_menu/shotou/new-cs/1385768.htm):
   character set, elementary grades, all reading stages, and 134 whole-word/reading
   allocations from both appendices, including alternate written forms and the
   explicitly listed prefecture names. The table also contains high-school readings;
   knowing all characters by 中3 does not require every such reading.
2. [Agency for Cultural Affairs, 常用漢字表の音訓索引](https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/kanji/joyokanjisakuin/index.html):
   independent character/reading cross-check, official example words, and okurigana.
3. [NINJAL, BCCWJ short-unit frequency list v1.0](https://doi.org/10.15084/00003218),
   corrected 2015-11-18: Japanese word forms, lemma readings, overall frequency,
   and textbook-register frequency (`OT_frequency`). This is the separately released
   educational-use frequency list, not the more restrictive 2011 textbook CD-ROM.

Selection includes corpus-attested official examples, frequent eligible words
(at least 1,000 corpus occurrences), and up to three candidates per character,
ranked by official-example status, textbook frequency, then overall frequency.
Additional attested readings of selected words are retained where supported.
Words use 常用漢字 plus kana/々; corpus proper names are excluded. Official standalone
examples and appendix entries supplement the selection. A few coverage exceptions
(e.g. 壱万円, 干潟, 憧憬, 朕) use official examples/readings directly. Character variants
叱/剥/填/頬 are normalized to 𠮟/剝/塡/頰. Corpus readings are converted to hiragana.

Corpus lemma spellings may differ from a school textbook's preferred spelling.
Vocabulary remains a source-derived import, not an individually reviewed teaching
list; NINJAL documents residual analysis errors. `sources` identifies the evidence
for each word, not a claim that each source attests every reading or its learning year.
Short disambiguations are locally authored.

The NINJAL frequency list permits educational/research use without application but
prohibits redistribution; commercial use requires consultation. Keep the derived
vocabulary file for private educational use. See the
[source manual, section 6](https://clrd.ninjal.ac.jp/bccwj/data-files/frequency-list/BCCWJ_frequencylist_manual_ver1_0b.pdf).

### Validation

The extracted character and undotted reading sets match the independent official
HTML table exactly. Elementary counts are 80, 160, 200, 202, 193, and 191. Reading
stage counts are elementary 2,062; junior high 2,008; high school 318. The PDF's
graphic-only 𠮟 glyph was checked visually and restored. YAML was independently
parsed with duplicate-key detection; counts, formats, source references, and full
vocabulary character coverage were checked. These checks verify the import, not
the pedagogical suitability of every vocabulary item.

Source SHA-256 checksums:

```text
mext.pdf  0bc189982a50122f1e35dd6a751bfdff0ec5a0ad67e99eda916d012f859a5ae4
joyo.html 33cb7b99d88d069a5e6e228a71f587285c9fa3cc6937e74022928524569f26f3
bccwj.zip 4e082faa51bedb77b69003358b55278c6736fd32124fc38a93b1b125c64834ba
```

## Earlier study notes

このフォルダでは、高校受験の国語に関する教材、学習記録、間違い直しを管理する。

## AIの役割

AIは「答えを教える先生」ではなく、次の4役として使う。

1. **出題者** — 学年・志望校レベルに合わせて小テストを作る
2. **対話型の解説者** — すぐ正解を言わず、ヒントを一段ずつ出す
3. **添削者** — 記述答案の不足・根拠・表現を具体的に指摘する
4. **分析者** — 間違いを分類し、次に復習すべき内容を決める

教科書、学校の教材、信頼できる問題集、志望校の過去問を正解の基準にする。AIが作った古文本文、語義、文法説明には誤りがあり得るため、重要事項は教材で確認する。

## 学習の基本サイクル

1. 子どもがまず自力で解く
2. 答えだけでなく、そう考えた根拠も話す
3. AIは正解をすぐ示さず、必要なヒントを1つだけ出す
4. 解答後に「知識不足・読み違い・根拠不足・ケアレスミス」に分類する
5. 翌日、1週間後、1か月後に短く再出題する

## 分野別の使い方

### 漢字

- 読み、書き、熟語、同音異義語を混ぜた5〜10問の小テスト
- 間違えた漢字を使った短文作り
- 部首、意味、熟語のつながりによる記憶補助
- 手書き答案は写真で見せ、誤字の理由も確認する

おすすめプロンプト：

> 高校受験レベルの漢字テストを10問、1問ずつ出してください。読み5問、書き5問。私が答えるまで正解を表示しないでください。誤答は意味・部首・例文を使って短く解説し、最後に復習リストを作ってください。

### 古文

- 歴史的仮名遣いと現代仮名遣いの変換
- 頻出古語の意味を文脈から判断
- 主語の省略を補い、「誰が・何をした」を整理
- 助動詞・助詞・敬語を、本文中の働きと結びつける
- 一文ずつ現代語訳し、直訳と自然な訳を比べる

おすすめプロンプト：

> 次の古文を高校受験生向けに指導してください。まず私に主語と重要語句を考えさせ、正解はまだ言わないでください。誤った場合はヒントを1段階ずつ出し、最後に文法・現代語訳・読み取りの根拠を整理してください。

### 古典（作品・背景知識）

- 作品名、作者、時代、ジャンルのカード化
- 説話、随筆、物語、日記、和歌の特徴比較
- 古典常識（身分、住居、時刻、方角、季節感）の確認
- 背景知識を本文読解にどう使うか説明させる

おすすめプロンプト：

> 高校受験で必要な古典文学史を、作品名・作者・時代・ジャンルの4項目で確認する一問一答にしてください。間違えた問題は出題順を変えて最後にもう一度出してください。

## 親の関わり方

- 「なぜそう思った？」と根拠を聞く
- AIへの入力を親が全部代行せず、子ども自身に説明させる
- 正答数より、同じ種類のミスが減っているかを見る
- 1回15〜25分程度に区切り、最後に本人が学んだことを1文でまとめる
- AIの長い説明は読ませず、「今必要なヒントだけ」に絞る

## 最初の2週間（例）

| 頻度 | 内容 | 時間 |
|---|---|---:|
| 毎日 | 漢字10問＋間違い直し | 10分 |
| 週3回 | 短い古文を主語・語句・現代語訳の順で読む | 20分 |
| 週1回 | 古典文学史・古典常識の確認 | 15分 |
| 週1回 | その週の誤答だけを再テスト | 20分 |

## 次にそろえる情報

- 学年と現在のおおよその成績
- 志望校・都道府県（出題傾向を合わせるため）
- 使用中の教科書・問題集
- 漢字、古文、現代文のうち特に苦手な分野
- 直近の答案や模試で見られたミス
