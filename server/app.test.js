import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { createApp } from './app.js';
import { loadKanji, selectKanji } from './kanji.js';
import { posterReadings } from '../public/readings.js';
import { kanjiCard } from './cards.js';

let entries, server, base;
before(async () => {
  entries = await loadKanji();
  server = createApp(entries);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => new Promise(resolve => server.close(resolve)));

test('uses the complete source and exact elementary introduction grades', () => {
  assert.equal(entries.length, 2136);
  assert.deepEqual([1, 2, 3, 4, 5, 6].map(year => selectKanji(entries, `e${year}`).length), [80, 160, 200, 202, 193, 191]);
  assert.equal(selectKanji(entries, 'j1').length, 0);
  assert.equal(selectKanji(entries, 'h3').length, 0);
});

test('stage selection retains metadata and readings from other stages for reuse', async () => {
  const response = await fetch(`${base}/api/v1/kanji?level=e1`);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.meta.total, 80);
  const upper = body.data.find(entry => entry.character === '上');
  assert.equal(upper.writingLevel, 'e1');
  assert.ok(upper.readings.some(reading => reading.text === 'ショウ' && reading.level === 'h'));
  assert.ok(selectKanji(entries, 'j').every(entry => entry.readings.some(reading => reading.level === 'j')));
});

test('API discovery, defaults and client errors', async () => {
  const levels = await (await fetch(`${base}/api/v1/levels`)).json();
  assert.equal(levels.data.find(level => level.id === 'e1').count, 80);
  assert.equal((await (await fetch(`${base}/api/v1/kanji`)).json()).meta.total, 2136);
  assert.equal((await fetch(`${base}/api/v1/kanji?level=invalid`)).status, 400);
  assert.equal((await fetch(`${base}/api/v1/kanji`, { method: 'POST' })).status, 405);
  assert.equal((await fetch(`${base}/japanese/kanji.yaml`)).status, 404);
  assert.equal((await fetch(`${base}/`)).status, 200);
});

test('poster caps readings after stage filtering and MEXT special-use ordering', () => {
  const seven = entries.find(entry => entry.character === '七');
  assert.deepEqual(posterReadings(seven.readings, 'e1').map(r => r.displayText), ['シチ', 'なな', 'ななつ']);
  const allSeven = posterReadings(seven.readings, 'e1', true);
  assert.equal(allSeven.length, 4);
  assert.equal(allSeven[3].displayText, 'なの');
  assert.equal(allSeven[3].specialOrNarrowUse, true);
  const upper = entries.find(entry => entry.character === '上');
  assert.deepEqual(posterReadings(upper.readings, 'e1').map(r => r.displayText), ['ジョウ', 'うえ', 'かみ']);
  assert.equal(posterReadings(upper.readings, 'e1', true).at(-1).displayText, 'うわ');
  for (const entry of selectKanji(entries, 'e1')) {
    assert.ok(posterReadings(entry.readings, 'e1').length <= 3);
  }
  assert.equal(entries.flatMap(e => e.readings).filter(r => r.specialOrNarrowUse).length, 178);
});

test('every reading has an example and every card has numbered stroke paths', async () => {
  for (const entry of entries) {
    const card = await kanjiCard(entry);
    assert.ok(card.strokes.paths.length > 0);
    assert.equal(card.strokes.paths.length, card.strokes.labels.length);
    for (const reading of card.readings) {
      assert.ok(reading.examples.length, `${entry.character} ${reading.text}`);
      for (const example of reading.examples) {
        assert.ok(example.word.includes(entry.character), example.word);
        assert.match(example.reading, /^[\u3041-\u3096ー]+$/);
      }
    }
  }
  const response = await fetch(`${base}/api/v1/kanji/${encodeURIComponent('七')}`);
  assert.equal(response.status, 200);
  const card = (await response.json()).data;
  assert.equal(card.strokes.paths.length, 2);
  assert.ok(card.readings.find(r => r.text === 'なの').examples.some(e => e.word === '七日' && e.reading === 'なのか'));
  assert.equal((await fetch(`${base}/api/v1/kanji/unknown`)).status, 404);
});
