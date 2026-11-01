import { test } from 'node:test';
import assert from 'node:assert/strict';
import { trainingLayout, selectedCharacters } from '../public/training-layout.js';

test('training grid fills the printable width with the maximum whole square rows', () => {
  for (let columns = 5; columns <= 10; columns++) {
    const layout = trainingLayout(new URLSearchParams({ n: columns }));
    assert.ok(layout.square * columns <= 276 && layout.square * columns > 275.99);
    assert.ok(layout.square * layout.rows <= 189);
    assert.ok(layout.square * (layout.rows + 1) > 189);
    assert.equal(layout.blanks, layout.rows - 2);
    assert.ok(layout.blanks >= 1);
  }
});
test('training settings reject fractional and out-of-range column counts', () => {
  for (const query of ['n=1', 'n=4', 'n=5.5', 'n=11', 'n=']) {
    assert.throws(() => trainingLayout(new URLSearchParams(query)));
  }
});
test('selection survives URL encoding, removes duplicates, and retains supplementary kanji', () => {
  const params = new URLSearchParams({ selected: '一𠮟二一' });
  assert.deepEqual(selectedCharacters(new URLSearchParams(params.toString())), ['一', '𠮟', '二']);
  assert.deepEqual(selectedCharacters(new URLSearchParams()), []);
});
