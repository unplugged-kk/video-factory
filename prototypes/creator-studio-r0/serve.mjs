import { createServer } from 'node:http';
import { constants, openSync, closeSync, readFileSync, fstatSync, lstatSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export const origin = 'http://127.0.0.1:4786';
const routes = new Map([
  ['/', ['index.html', 'text/html']], ['/app.mjs', ['app.mjs', 'text/javascript']],
  ['/fixtures.mjs', ['fixtures.mjs', 'text/javascript']], ['/style.css', ['style.css', 'text/css']],
  ['/icon.svg', ['icon.svg', 'image/svg+xml']],
]);
export const paths = [...routes.keys()];
const csp = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; media-src 'self'; font-src 'self'; connect-src 'none'; form-action 'none'; frame-src 'none'; frame-ancestors 'none'; object-src 'none'; worker-src 'none'; base-uri 'none'";

export function fixtureServer() {
  const site = new URL('./site/', import.meta.url);
  if (!lstatSync(new URL('../site', site)).isDirectory()) throw new Error('Expected real fixture directory');
  const assets = new Map([...routes].map(([path, [file, type]]) => {
    const fd = openSync(new URL(file, site), constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    try {
      if (!fstatSync(fd).isFile()) throw new Error(`Expected regular fixture: ${file}`);
      return [path, { bytes: readFileSync(fd), type }];
    } finally { closeSync(fd); }
  }));
  return createServer((req, res) => {
    const asset = assets.get(req.url);
    const status = req.headers.host !== new URL(origin).host ? 421
      : !['GET', 'HEAD'].includes(req.method) ? 405 : !asset ? 404 : 200;
    const bytes = status === 200 ? asset.bytes : Buffer.from('Not served by fixture host');
    res.writeHead(status, {
      'Content-Type': `${status === 200 ? asset.type : 'text/plain'}; charset=utf-8`,
      'Content-Length': bytes.length, 'Content-Security-Policy': csp,
      'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store',
    });
    res.end(req.method === 'HEAD' ? undefined : bytes);
  });
}

export function start(server) { return server.listen(4786, '127.0.0.1'); }
if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  start(fixtureServer()).on('listening', () => console.log(`Cutting Room (fixtures only): ${origin}`));
}
