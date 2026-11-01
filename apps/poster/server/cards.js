import { readFile } from 'node:fs/promises';
import { parse } from 'yaml';

let resources;
export async function kanjiCard(entry) {
  // Load the heavier study data only when a card is opened.
  resources ??= Promise.all([
    readFile(new URL('../../../datasets/japanese/stokes.yaml', import.meta.url), 'utf8').then(parse),
    readFile(new URL('../../../datasets/japanese/card-examples.json', import.meta.url), 'utf8').then(JSON.parse),
  ]).catch(error => { resources = undefined; throw error; });
  const [strokes, examples] = await resources;
  return {
    ...entry,
    readings: entry.readings.map(reading => ({
      ...reading, examples: examples[entry.character]?.[reading.text] ?? [],
    })),
    strokes: { ...strokes.kanji[entry.character], viewbox: strokes.viewbox, source: strokes.source },
  };
}
