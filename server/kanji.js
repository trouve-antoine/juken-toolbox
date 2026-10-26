import { readFile } from 'node:fs/promises';
import { parse } from 'yaml';

export const levels = [
  ['all', 'All kanji'], ['e', 'Elementary school'],
  ...Array.from({ length: 6 }, (_, i) => [`e${i + 1}`, `Elementary · year ${i + 1}`]),
  ['j', 'Junior high school'], ['h', 'High school'],
  ...['j', 'h'].flatMap(stage => [1, 2, 3].map(year =>
    [`${stage}${year}`, `${stage === 'j' ? 'Junior high' : 'High school'} · year ${year} (unassigned)`])),
].map(([id, label]) => ({ id, label }));

// Stage queries match reading assignments; exact years match character introduction.
// Return every reading with its metadata so each client can choose its presentation.
export function selectKanji(entries, level) {
  if (!levels.some(item => item.id === level)) throw new RangeError('Unknown level');
  return entries.filter(entry => level === 'all' || (level.length === 2
    ? entry.writingLevel === level
    : entry.readings.some(reading => reading.level === level || reading.level?.startsWith(level))));
}

export async function loadKanji(path = new URL('../japanese/kanji.yaml', import.meta.url)) {
  const data = parse(await readFile(path, 'utf8'));
  const mext = JSON.parse(await readFile(new URL('../japanese/mext-readings.json', import.meta.url), 'utf8')).kanji;
  return Object.entries(data.kanji).map(([character, entry]) => ({
    character,
    writingLevel: entry.writing ?? null,
    readings: Object.entries(entry.readings).map(([text, value]) => {
      const order = mext[character]?.readings.findIndex(reading => reading.inventory_key === text);
      const source = mext[character]?.readings[order];
      if (!source || source.stage !== (Array.isArray(value) ? value[0] : value)) {
        throw new Error(`MEXT metadata mismatch: ${character} ${text}`);
      }
      return {
      text, level: Array.isArray(value) ? value[0] : value,
      hint: Array.isArray(value) ? value[1] : null,
      type: /^[\u30a0-\u30ff]+$/.test(text.replaceAll('.', '')) ? 'on' : 'kun',
      displayText: source.text,
      specialOrNarrowUse: source.special_or_narrow_use,
      mextOrder: order,
      };
    }),
  }));
}
