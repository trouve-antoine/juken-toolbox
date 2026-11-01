import { trainingLayout, selectedCharacters } from './training-layout.js';

const make = (tag, className, text) => {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};
const cache = new Map();
async function strokes(character) {
  if (!cache.has(character)) cache.set(character, fetch(`/api/v1/kanji/${encodeURIComponent(character)}`)
    .then(async response => {
      if (!response.ok) throw new Error(`Could not load strokes for ${character}. Change the selection to retry.`);
      return (await response.json()).data.strokes;
    }).catch(error => { cache.delete(character); throw error; }));
  return cache.get(character);
}
function model(data, character, numbered = false) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', data.viewbox.join(' '));
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', `${character} ${numbered ? "numbered stroke model" : "tracing model"}`);
  for (const d of data.paths) {
    const path = document.createElementNS(ns, 'path');
    path.setAttribute('d', d);
    svg.append(path);
  }
  if (numbered) data.labels.forEach(([x, y], index) => {
    const label = document.createElementNS(ns, 'text');
    label.setAttribute('x', x);
    label.setAttribute('y', y);
    label.textContent = index + 1;
    svg.append(label);
  });
  return svg;
}
async function sheets(characters, layout) {
  const data = await Promise.all(characters.map(strokes));
  const result = document.createDocumentFragment();
  const count = Math.ceil(characters.length / layout.columns);
  for (let page = 0; page < count; page++) {
    const sheet = make('section', 'sheet training-sheet');
    sheet.style.setProperty('--square', `${layout.square}mm`);
    const grid = make('div', 'practice-grid');
    for (let index = page * layout.columns; index < (page + 1) * layout.columns; index++) {
      const column = make('div', 'practice-column');
      if (index < characters.length) {
        const reference = make('div', 'practice-square tracing numbered-model');
        reference.append(model(data[index], characters[index], true));
        column.append(reference);
        const trace = make('div', 'practice-square tracing');
        trace.append(model(data[index], characters[index]));
        column.append(trace);
      }
      const blanks = index < characters.length ? layout.blanks : layout.rows;
      for (let row = 0; row < blanks; row++) column.append(make('div', 'practice-square'));
      grid.append(column);
    }
    sheet.append(grid);
    const preview = make('div', 'training-sheet-preview');
    preview.append(sheet);
    result.append(preview);
  }
  return result;
}
export async function renderTrainingPrint(params, target, entries) {
  const allowed = new Set(entries.map(entry => entry.character));
  const characters = selectedCharacters(params).filter(character => allowed.has(character));
  if (!characters.length) throw new Error('Select at least one kanji before printing.');
  const layout = trainingLayout(params);
  document.documentElement.classList.add('training-print');
  target.replaceChildren(await sheets(characters, layout));
}
export function initTraining(params, entries, picker, printButton) {
  const layout = trainingLayout(params);
  const allowed = new Set(entries.map(entry => entry.character));
  const selected = new Set(selectedCharacters(params).filter(character => allowed.has(character)));
  const hidden = document.querySelector('#selected-kanji');
  const summary = document.querySelector('#selection-count');
  const target = document.querySelector('#training-pages');
  const status = document.querySelector('#training-status');
  document.querySelector('#selection-tools').hidden = false;
  document.querySelector('#training-preview').hidden = false;
  document.querySelector('#print-hint').textContent = 'Select kanji below · landscape A4 · numbered black model, grey tracing model, then blank practice squares';
  picker.setAttribute('aria-label', 'Select kanji for writing sheets');
  const resize = () => {
    const width = target.clientWidth;
    const sheet = target.querySelector('.training-sheet');
    if (sheet) target.style.setProperty('--training-scale', Math.min(1, width / sheet.offsetWidth));
  };
  new ResizeObserver(resize).observe(target);
  let revision = 0;
  const boxes = [];
  const update = async () => {
    const current = ++revision;
    // Keep source order regardless of the order in which boxes were checked.
    const characters = entries.map(entry => entry.character).filter(character => selected.has(character));
    hidden.value = characters.join('');
    const url = new URL(location.href);
    url.searchParams.set('selected', hidden.value);
    history.replaceState(null, '', url);
    const count = Math.ceil(characters.length / layout.columns);
    summary.textContent = `${characters.length} kanji selected · ${count} landscape ${count === 1 ? "sheet" : "sheets"}`;
    boxes.forEach(({ box, tile }) => { box.checked = selected.has(box.value); tile.classList.toggle('selected-tile', box.checked); });
    printButton.disabled = true;
    target.replaceChildren();
    status.textContent = characters.length ? 'Loading stroke models…' : 'Check kanji above to build your writing sheets.';
    try {
      const result = await sheets(characters, layout);
      if (current !== revision) return;
      target.replaceChildren(result);
      resize();
      status.textContent = characters.length ? `${layout.blanks} blank squares per kanji · print at 100% with browser headers and footers off` : status.textContent;
      printButton.disabled = !characters.length;
    } catch (error) { if (current === revision) status.textContent = error.message; }
  };
  picker.querySelectorAll('.tile').forEach((original, index) => {
    // Replace the card button with a native, keyboard-accessible checkbox label.
    const tile = make('label', 'tile selectable-tile');
    tile.lang = 'ja';
    const box = make('input', 'kanji-checkbox');
    box.type = 'checkbox'; box.value = entries[index].character;
    box.setAttribute('aria-label', `Select ${box.value}`);
    tile.append(box, ...original.childNodes);
    original.replaceWith(tile);
    boxes.push({ box, tile });
    box.addEventListener('change', () => { box.checked ? selected.add(box.value) : selected.delete(box.value); update(); });
  });
  document.querySelector('#select-all').onclick = () => { entries.forEach(entry => selected.add(entry.character)); update(); };
  document.querySelector('#clear-selection').onclick = () => { selected.clear(); update(); };
  update();
}
