"""Join official reading-specific examples to vocabulary pronunciations."""
import hashlib, html, json, re
from pathlib import Path
import yaml
from compute_reading_frequency import align, kana
ROOT=Path(__file__).resolve().parents[2]
k=yaml.safe_load((ROOT/'japanese/kanji.yaml').read_text())['kanji']
v=yaml.safe_load((ROOT/'japanese/vocab.yaml').read_text())['vocab']
source=(ROOT/'data/cards/joyo.html').read_bytes()
assert hashlib.sha256(source).hexdigest()=='33cb7b99d88d069a5e6e228a71f587285c9fa3cc6937e74022928524569f26f3', 'Official source changed; review table parsing before updating the pin'
s=source.decode('cp932','replace')
def clean(x): return html.unescape(re.sub('<[^>]+>','',x)).strip()
result={c:{r:[] for r in e['readings']} for c,e in k.items()}
for row in re.findall(r'<tr>(.*?)</tr>',s,re.S|re.I):
 cells=re.findall(r'<td[^>]*>(.*?)</td>',row,re.S|re.I)
 if len(cells)!=4: continue
 char=clean(cells[0])[:1]
 if char=='叱': char='𠮟'
 if char not in k: continue
 readings=[clean(x) for x in re.split(r'<br\s*/?>',cells[1],flags=re.I)]
 examples=[clean(x) for x in re.split(r'<br\s*/?>',cells[2],flags=re.I)]
 if len(readings)!=len(examples): continue
 for reading, words in zip(readings,examples):
  canonical=next((r for r in k[char]['readings'] if r.replace('.','')==reading),None)
  if canonical is None: continue
  for word in words.split('，'):
   word=word.strip()
   choices=list(v.get(word,{}).get('readings',{}))
   for pronunciation in choices:
    matches=align(word,pronunciation,k)
    if any((char,canonical) in m for m in matches) or (len(choices)==1 and kana(canonical.split('.')[0]) in pronunciation):
     result[char][canonical].append({'word':word,'reading':pronunciation,'source':'joyo-vocab'})
# Exact, unique alignment of vocabulary words fills gaps without substring guessing.
for word,entry in v.items():
 for pronunciation in entry['readings']:
  matches=align(word,pronunciation,k)
  if len(matches)!=1: continue
  for char,reading in matches[0]:
   if len(result[char][reading])<3 and not any(x['word']==word and x['reading']==pronunciation for x in result[char][reading]):
    result[char][reading].append({'word':word,'reading':pronunciation,'source':'vocab-exact-alignment'})
# A canonical kun reading with explicit okurigana supplies a standalone form.
for char,e in k.items():
 for r in e['readings']:
  if not result[char][r] and '.' in r:
   result[char][r].append({'word':char+r.split('.')[1],'reading':r.replace('.',''),'source':'official-kun-form'})
supplements=json.loads((ROOT/'japanese/card-example-supplements.json').read_text())
for char,readings in supplements.items():
 for reading,example in readings.items():
  assert reading in result[char]
  if not result[char][reading]: result[char][reading].append(example)
result={c:{r:xs[:3] for r,xs in e.items()} for c,e in result.items()}
missing=[(c,r) for c,e in result.items() for r,x in e.items() if not x]
print('missing',len(missing),'of',sum(len(e) for e in result.values()))
print('first grade missing',[(c,r) for c,r in missing if k[c].get('writing')=='e1'])
assert not missing, missing
(ROOT/'japanese/card-examples.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
