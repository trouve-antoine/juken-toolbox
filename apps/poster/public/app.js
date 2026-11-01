import { themes } from './themes.js';
import { posterReadings } from './readings.js';
import { openCard, setCardSequence } from './card.js';

const params = new URLSearchParams(location.search);
const theme = themes.find(item => item.id === params.get('theme'))?.id ?? 'simple';
const showAll = params.get('showAll') === '1';
const printDocument = params.get('print') === '1';
document.documentElement.classList.toggle('print-document', printDocument);
const level = params.get('level') ?? 'e1';
const rawColumns = params.get('n') ?? '6';
const columns = Number(rawColumns);
const pages = document.querySelector('#pages');
const status = document.querySelector('#status');
const printButton = document.querySelector('#print');
document.querySelector('#columns').value = rawColumns;
const themeSelect = document.querySelector('#theme');
themeSelect.replaceChildren(...themes.map(({ id, label }) => {
  const option = element('option', '', label);
  option.value = id;
  return option;
}));
themeSelect.value = theme;
themeSelect.addEventListener('change', () => themeSelect.form.requestSubmit());
const allReadingsCheckbox = document.querySelector('#show-all');
allReadingsCheckbox.checked = showAll;
allReadingsCheckbox.addEventListener('change', () => allReadingsCheckbox.form.requestSubmit());

const themeReady = theme === 'simple' ? Promise.resolve() : new Promise((resolve, reject) => {
  const stylesheet = document.querySelector('#theme-style');
  stylesheet.onload = resolve;
  stylesheet.onerror = () => reject(new Error('Could not load the theme. Please reload.'));
  stylesheet.href = `/themes/${theme}.css`;
});
printButton.addEventListener('click', () => {
  const url = new URL(location.href);
  url.searchParams.set('print', '1');
  url.searchParams.set('theme', theme);
  // A separate document keeps app controls out of embedded-browser printing too.
  window.open(url, '_blank', 'noopener');
});

function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function tile(entry) {
  const node = element('article', 'tile');
  node.lang = 'ja';
  if (!printDocument) {
    node.tabIndex = 0;
    node.setAttribute('role', 'button');
    node.setAttribute('aria-label', `${entry.character} — open study card`);
    node.setAttribute('aria-haspopup', 'dialog');
    node.addEventListener('click', () => openCard(entry.character));
    node.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openCard(entry.character);
      }
    });
  }
  node.append(element('div', 'character', entry.character));
  const readings = element('div', 'readings');
  // Year assignments describe characters, not reading mastery within that year.
  const selected = posterReadings(entry.readings, level, showAll);
  selected.forEach((reading, index) => {
    if (index) readings.append(document.createTextNode('・'));
    const label = element('span', `reading${reading.specialOrNarrowUse ? ' special-reading' : ''}`, reading.displayText);
    if (reading.specialOrNarrowUse) label.title = 'MEXT: special or narrowly used reading';
    readings.append(label);
  });
  node.append(readings);
  return node;
}

function posterTitle(level) {
  if (level === 'all') return '漢字：すべて';
  const school = { e: '小学校', j: '中学校', h: '高等学校' }[level[0]];
  const year = level[1] ? `${'０１２３４５６'[Number(level[1])]}年生` : '';
  return `漢字：${school}${year}`;
}

function render(entries, rows) {
  pages.replaceChildren();
  const capacity = columns * rows;
  const count = Math.ceil(entries.length / capacity);
  for (let page = 0; page < count; page++) {
    const sheet = element('section', 'sheet');
    sheet.style.setProperty('--columns', columns);
    sheet.style.setProperty('--rows', rows);
    sheet.style.setProperty('--kanji-size', `${Math.min(23, 95 / columns)}mm`);
    sheet.style.setProperty('--reading-size', `${Math.max(7, Math.min(10, 48 / columns))}pt`);
    const header = element('header', 'sheet-header');
    const title = element('h2', '', posterTitle(level));
    title.lang = 'ja';
    header.append(title, element('span', '', `${page + 1} / ${count}`));
    const grid = element('div', 'grid');
    entries.slice(page * capacity, (page + 1) * capacity).forEach(entry => grid.append(tile(entry)));
    const footer = element('footer', 'sheet-footer');
    footer.append(element('span', '', 'JUKEN  /  毎日の漢字'), element('span', '', `${columns} × ${rows}  ·  ${showAll ? '全音訓' : '音訓３つまで'}  ·  小さい字：特別・用法の狭い音訓`));
    sheet.append(header, grid, footer);
    const preview = element('div', 'sheet-preview');
    preview.append(sheet);
    pages.append(preview);
  }
}

async function start() {
  try {
    await themeReady;
    const levelsResponse = await fetch('/api/v1/levels');
    if (!levelsResponse.ok) throw new Error('Could not load levels. Please reload.');
    const { data: levels } = await levelsResponse.json();
    const select = document.querySelector('#level');
    select.replaceChildren(...levels.map(item => {
      const option = element('option', '', `${item.label} (${item.count})`);
      option.value = item.id;
      return option;
    }));
    select.value = level;
    const selected = levels.find(item => item.id === level);
    if (!selected) throw new Error('Unknown level. Choose a level above and select Update.');
    if (!/^\d+$/.test(rawColumns) || !Number.isInteger(columns) || columns < 2 || columns > 10) {
      throw new Error('Columns (n) must be a whole number from 2 to 10.');
    }
    const response = await fetch(`/api/v1/kanji?level=${encodeURIComponent(level)}`);
    if (!response.ok) throw new Error('Could not load kanji. Please reload.');
    const { data: entries } = await response.json();
    setCardSequence(entries.map(entry => entry.character));
    if (!entries.length) {
      status.textContent = 'No kanji assigned to this exact year. Try a school stage or an elementary year.';
      return;
    }
    let rows = Math.floor(255 / (190 / columns));
    render(entries, rows);
    await document.fonts.ready;
    // Measure actual Japanese glyphs and wrapped readings. Reduce row count until
    // every tile fits, keeping the selected readings and every character.
    while (rows > 1 && [...pages.querySelectorAll('.tile')].some(node => {
      const content = [...node.children].reduce((sum, child) => sum + child.getBoundingClientRect().height, 0);
      const style = getComputedStyle(node);
      return content + parseFloat(style.rowGap) + parseFloat(style.paddingTop) + parseFloat(style.paddingBottom)
        + parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth) + 1 > node.getBoundingClientRect().height;
    })) {
      render(entries, --rows);
    }
    status.textContent = `${entries.length} kanji · ${columns} columns × ${rows} rows · ${pages.children.length} A4 pages. ${showAll ? 'All readings' : 'Up to 3 readings per kanji'} for the selected stage, in MEXT order with special/narrow-use readings last.`;
    printButton.disabled = false;
    if (!printDocument) {
      // Scale only after measuring the full-size A4 layout. The wrapper reserves
      // the scaled height, so pages stay together when the phone rotates.
      const resizePreview = () => {
        const style = getComputedStyle(pages);
        const available = pages.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
        const sheetWidth = pages.querySelector('.sheet').offsetWidth;
        pages.style.setProperty('--preview-scale', Math.min(1, available / sheetWidth));
      };
      new ResizeObserver(resizePreview).observe(pages);
      resizePreview();
    }
    if (printDocument) {
      // Let layout and painting settle before opening the native print dialog.
      requestAnimationFrame(() => requestAnimationFrame(() => window.print()));
    }
  } catch (error) {
    pages.replaceChildren();
    status.textContent = error.message;
  }
}
start();
