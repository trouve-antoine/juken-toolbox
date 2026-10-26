const dialog = document.querySelector('#kanji-card');
const body = document.querySelector('#card-body');
let request;
const playbacks = new Set();
let wordPreviewId = 0;
const cardCache = new Map();
let sequence = [];
let currentIndex = -1;
const previous = document.querySelector('#previous-kanji');
const next = document.querySelector('#next-kanji');
const close = document.querySelector('#close-card');

export function setCardSequence(characters) {
  sequence = [...characters];
}

function navigate(offset) {
  if (!dialog.open || currentIndex < 0) return;
  const target = currentIndex + offset;
  if (target >= 0 && target < sequence.length) openCard(sequence[target]);
}
previous.addEventListener('click', () => navigate(-1));
next.addEventListener('click', () => navigate(1));
dialog.addEventListener('keydown', event => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey
      || event.target.closest('input, textarea, select, [contenteditable="true"]')) return;
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault();
    navigate(event.key === 'ArrowLeft' ? -1 : 1);
  }
});
function node(tag, text, className = '') {
  const el = document.createElement(tag);
  el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
document.querySelector('#close-card').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => {
  const rect = dialog.getBoundingClientRect();
  if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
});
function stopPlaybacks() {
  for (const stop of playbacks) stop();
  playbacks.clear();
}
dialog.addEventListener('close', () => { request?.abort(); stopPlaybacks(); });

async function loadCard(character, signal) {
  if (cardCache.has(character)) return cardCache.get(character);
  const response = await fetch(`/api/v1/kanji/${encodeURIComponent(character)}`, { signal });
  if (!response.ok) throw new Error(`Could not load ${character}. Please try again.`);
  const { data } = await response.json();
  cardCache.set(character, data);
  return data;
}

function strokePanel(data, { compact = false } = {}) {
  const panel = node('section', undefined, 'stroke-panel');
  let animation;
  panel.stopPlayback = () => animation?.cancel();
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', data.strokes.viewbox.join(' '));
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', `${data.character} stroke order`);
  const paths = data.strokes.paths.map((d, index) => {
    const path = document.createElementNS(ns, 'path');
    for (const [key, value] of Object.entries({ d, fill: 'none', stroke: '#284f40', 'stroke-width': '3', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })) path.setAttribute(key, value);
    svg.append(path);
    return path;
  });
  const labels = data.strokes.labels.map(([x, y], index) => {
    const text = document.createElementNS(ns, 'text');
    text.setAttribute('x', x); text.setAttribute('y', y);
    text.setAttribute('font-size', '7'); text.setAttribute('fill', '#b05436');
    text.textContent = index + 1;
    svg.append(text);
    return text;
  });
  let position = paths.length;
  const counter = node('p');
  const show = () => {
    paths.forEach((path, i) => path.style.opacity = i < position ? '1' : '.12');
    labels.forEach((label, i) => label.style.opacity = i < position ? '1' : '0');
    counter.textContent = `${position} / ${paths.length} strokes`;
  };
  const controls = node('div', undefined, 'stroke-controls');
  const replay = node('button', 'Replay');
  const step = node('button', 'Next stroke');
  replay.type = step.type = 'button';
  step.addEventListener('click', () => { animation?.cancel(); position = position === paths.length ? 1 : position + 1; show(); });
  replay.addEventListener('click', async () => {
    animation?.cancel();
    position = 0; show();
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { position = paths.length; show(); return; }
    replay.disabled = true;
    step.disabled = true;
    playbacks.add(panel.stopPlayback);
    try {
      for (const path of paths) {
        if (!dialog.open || !panel.isConnected) break;
        position++; show();
        const length = path.getTotalLength();
        animation = path.animate([{ strokeDasharray: `${length}`, strokeDashoffset: length }, { strokeDasharray: `${length}`, strokeDashoffset: 0 }], { duration: 500, easing: 'ease-in-out' });
        await animation.finished;
      }
    } catch { /* Closing the card cancels playback. */ }
    finally { playbacks.delete(panel.stopPlayback); replay.disabled = false; step.disabled = false; }
  });
  controls.append(replay, step);
  const credit = node('p');
  const link = node('a', 'KanjiVG · © Ulrich Apel');
  link.href = 'https://kanjivg.tagaini.net/'; link.target = '_blank'; link.rel = 'noopener';
  const license = node('a', 'CC BY-SA 3.0');
  license.href = 'https://creativecommons.org/licenses/by-sa/3.0/'; license.target = '_blank'; license.rel = 'noopener';
  credit.append(link, node('br'), license, node('br'), 'Source paths retained; colors and animation added.');
  panel.append(svg);
  if (!compact) panel.append(counter, controls);
  // The main preview supplies the shared KanjiVG attribution for the card.
  if (!compact) panel.append(credit);
  show();
  return panel;
}

function wordExample(example, signal) {
  const li = node('li');
  li.append(node('span', example.word), node('span', example.reading, 'word-reading'));
  const characters = [...example.word].filter(character => /\p{Script=Han}/u.test(character));
  if (!characters.length) return li;
  const toggle = node('button', '筆順 ▾', 'word-strokes-toggle');
  toggle.type = 'button';
  toggle.setAttribute('aria-label', `${example.word}の筆順`);
  toggle.setAttribute('aria-expanded', 'false');
  const preview = node('div', undefined, 'word-strokes');
  preview.id = `word-strokes-${++wordPreviewId}`;
  preview.hidden = true;
  toggle.setAttribute('aria-controls', preview.id);
  let loaded = false;
  let loading = false;
  toggle.addEventListener('click', async () => {
    preview.hidden = !preview.hidden;
    toggle.setAttribute('aria-expanded', String(!preview.hidden));
    toggle.textContent = preview.hidden ? '筆順 ▾' : '筆順 ▴';
    if (preview.hidden) {
      preview.querySelectorAll('.stroke-panel').forEach(panel => panel.stopPlayback());
      return;
    }
    if (loaded || loading || signal.aborted) return;
    loading = true;
    preview.setAttribute('aria-busy', 'true');
    preview.replaceChildren(node('p', '筆順を読み込み中…', 'card-note'));
    try {
      // Preserve the word's order, including repeated kanji. Kana need no panel.
      const cards = await Promise.allSettled(characters.map(character => loadCard(character, signal)));
      if (signal.aborted) return;
      preview.replaceChildren(...cards.map((result, index) => {
        if (result.status === 'rejected') {
          const missing = node('section', undefined, 'word-strokes-missing');
          missing.append(node('h4', characters[index]), node('p', '筆順を表示できません。閉じて再度開くと再試行します。', 'card-note'));
          return missing;
        }
        return strokePanel(result.value, { compact: true });
      }));
      loaded = cards.every(result => result.status === 'fulfilled');
    } catch (error) {
      if (!signal.aborted) {
        const message = node('p', `${error.message} Close and reopen this row to retry.`, 'card-note');
        message.setAttribute('role', 'alert');
        preview.replaceChildren(message);
      }
    } finally {
      loading = false;
      preview.removeAttribute('aria-busy');
    }
  });
  li.append(toggle, preview);
  return li;
}

export async function openCard(character) {
  request?.abort(); stopPlaybacks();
  currentIndex = sequence.indexOf(character);
  previous.disabled = currentIndex <= 0;
  next.disabled = currentIndex < 0 || currentIndex >= sequence.length - 1;
  // Keep focus inside the dialog when replacing focused stroke controls or
  // disabling a navigation button at the first/last card.
  if (dialog.open && (body.contains(document.activeElement)
      || document.activeElement === previous && previous.disabled
      || document.activeElement === next && next.disabled)) close.focus();
  const controller = new AbortController(); request = controller;
  const updateHeading = () => {
    document.querySelector('#card-title').textContent = `${character} — 漢字カード`;
    document.querySelector('#card-position').textContent = currentIndex < 0 ? '' : `${currentIndex + 1} / ${sequence.length}`;
  };
  body.querySelector('.card-error')?.remove();
  if (!dialog.open) {
    updateHeading();
    body.replaceChildren(node('p', 'Loading readings and examples…'));
    dialog.showModal();
    dialog.scrollTop = 0;
  }
  body.setAttribute('aria-busy', 'true');
  try {
    const data = await loadCard(character, controller.signal);
    if (controller.signal.aborted) return;
    const layout = node('div', undefined, 'card-layout');
    const list = node('section'); list.lang = 'ja';
    list.append(node('p', 'All official readings, including later school stages. Examples can be above the selected grade.', 'card-note'));
    for (const reading of data.readings) {
      const section = node('section', undefined, 'card-reading');
      const title = node('h3', reading.displayText);
      title.append(node('small', `${{e:'小学校',j:'中学校',h:'高校'}[reading.level] ?? '未指定'}${reading.specialOrNarrowUse ? ' · 特別な音訓' : ''}`));
      const examples = node('ul');
      for (const example of reading.examples) {
        examples.append(wordExample(example, controller.signal));
      }
      if (!reading.examples.length) examples.append(node('li', '例語は未登録です'));
      section.append(title, examples); list.append(section);
    }
    layout.append(strokePanel(data), list);
    // Build off-DOM, then swap the complete card in one paint. The existing
    // card and dialog stay visible throughout navigation and network delays.
    updateHeading();
    body.replaceChildren(layout);
    dialog.scrollTop = 0;
  } catch (error) {
    if (!controller.signal.aborted && error.name !== 'AbortError') {
      const message = node('p', error.message, 'card-error');
      message.setAttribute('role', 'alert');
      body.prepend(message);
    }
  } finally {
    if (request === controller) body.removeAttribute('aria-busy');
  }
}
