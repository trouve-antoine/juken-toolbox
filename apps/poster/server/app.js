import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { levels, selectKanji } from './kanji.js';
import { themes } from '../public/themes.js';
import { kanjiCard } from './cards.js';

const assets = new Map([
  ['/', ['index.html', 'text/html']],
  ['/training.js', ['training.js', 'text/javascript']],
  ['/training-layout.js', ['training-layout.js', 'text/javascript']],
  ['/app.js', ['app.js', 'text/javascript']],
  ['/readings.js', ['readings.js', 'text/javascript']],
  ['/card.js', ['card.js', 'text/javascript']],
  ['/card.css', ['card.css', 'text/css']],
  ['/style.css', ['style.css', 'text/css']],
  ['/themes.js', ['themes.js', 'text/javascript']],
  ...themes.map(({ id }) => [`/themes/${id}.css`, [`themes/${id}.css`, 'text/css']]),
]);

export function createApp(entries) {
  return createServer(async (request, response) => {
    const json = (status, value) => {
      response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
      response.end(JSON.stringify(value));
    };
    try {
      if (!['GET', 'HEAD'].includes(request.method)) {
        response.setHeader('Allow', 'GET, HEAD');
        return json(405, { error: 'Method not allowed' });
      }
      const url = new URL(request.url, 'http://localhost');
      if (url.pathname.startsWith('/api/v1/kanji/')) {
        let character;
        try { character = decodeURIComponent(url.pathname.slice('/api/v1/kanji/'.length)); }
        catch { return json(400, { error: 'Invalid character encoding' }); }
        const entry = entries.find(entry => entry.character === character);
        if (!entry) return json(404, { error: 'Kanji not found' });
        return json(200, { data: await kanjiCard(entry) });
      }
      if (url.pathname === '/api/v1/levels') {
        return json(200, { data: levels.map(level => ({
          ...level, count: selectKanji(entries, level.id).length,
        })) });
      }
      if (url.pathname === '/api/v1/kanji') {
        const level = url.searchParams.get('level') ?? 'all';
        if (!levels.some(item => item.id === level)) return json(400, { error: 'Unknown level', allowed: levels.map(item => item.id) });
        const data = selectKanji(entries, level);
        return json(200, { data, meta: { level, total: data.length } });
      }
      const asset = assets.get(url.pathname);
      if (!asset) return json(404, { error: 'Not found' });
      const body = await readFile(new URL(`../public/${asset[0]}`, import.meta.url));
      response.writeHead(200, { 'Content-Type': `${asset[1]}; charset=utf-8` });
      response.end(body);
    } catch (error) {
      console.error(error);
      if (!response.headersSent) json(500, { error: 'Internal server error' });
      else response.end();
    }
  });
}
