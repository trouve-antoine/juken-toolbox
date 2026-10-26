import { createApp } from './app.js';
import { loadKanji } from './kanji.js';

const port = Number(process.env.PORT ?? 3000);
const host = process.env.HOST ?? '127.0.0.1';
const server = createApp(await loadKanji());
server.listen(port, host, () => console.log(`Kanji poster: http://${host}:${port}/?n=6&level=e1`));
