import { randomUUID } from 'node:crypto';
import { mkdir, rename, writeFile } from 'node:fs/promises';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { fileURLToPath } from 'node:url';
import { defineConfig, type Plugin } from 'vite';

const cameras = new Set(['cam_gate', 'cam_avenue', 'cam_hill', 'cam_grid', 'cam_whompah', 'cam_hero']);
const shotDirectory = fileURLToPath(new URL('./tools/shots/', import.meta.url));
const bodyLimit = 12 * 1024 * 1024;
const isLoopback = (address: string | undefined) => ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(address ?? '');

function reply(response: ServerResponse, status: number, body: object) {
  response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
  response.end(JSON.stringify(body));
}

/** Local development evidence writer. No general file paths or external origins accepted. */
async function saveShot(request: IncomingMessage, response: ServerResponse, next: () => void) {
  const path = (request.url ?? '').split('?')[0];
  if (!path.startsWith('/__athen__/shots')) return next();
  const name = /^\/__athen__\/shots\/([a-z_]+)\.png$/.exec(path)?.[1];
  if (!name || !cameras.has(name)) return reply(response, 400, { error: 'Unknown named camera.' });
  if (request.method !== 'PUT') return reply(response, 405, { error: 'Use PUT with an image/png body.' });
  const host = request.headers.host ?? '';
  if (!isLoopback(request.socket.remoteAddress) || !/^(127\.0\.0\.1|localhost|\[::1\]):\d+$/.test(host)
    || request.headers.origin !== `http://${host}` || request.headers['sec-fetch-site'] === 'cross-site') {
    return reply(response, 403, { error: 'Screenshot writes require a same-origin localhost browser.' });
  }
  if (request.headers['content-type'] !== 'image/png') return reply(response, 415, { error: 'Expected image/png.' });
  const expectedLength = Number(request.headers['content-length']);
  if (Number.isFinite(expectedLength) && expectedLength > bodyLimit) return reply(response, 413, { error: 'PNG exceeds 12 MiB.' });
  try {
    let length = 0;
    const chunks: Buffer[] = [];
    for await (const chunk of request) {
      const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      length += buffer.length;
      if (length > bodyLimit) return reply(response, 413, { error: 'PNG exceeds 12 MiB.' });
      chunks.push(buffer);
    }
    const png = Buffer.concat(chunks);
    const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
    if (png.length < 33 || !png.subarray(0, 8).equals(signature) || png.toString('ascii', 12, 16) !== 'IHDR'
      || png.readUInt32BE(16) !== 1920 || png.readUInt32BE(20) !== 1080) {
      return reply(response, 400, { error: 'Expected a 1920 × 1080 PNG.' });
    }
    await mkdir(shotDirectory, { recursive: true });
    const temporary = `${shotDirectory}.${name}-${randomUUID()}.tmp`;
    await writeFile(temporary, png, { flag: 'wx' });
    await rename(temporary, `${shotDirectory}${name}.png`);
    reply(response, 200, { path: `tools/shots/${name}.png` });
  } catch (error) {
    reply(response, 500, { error: error instanceof Error ? error.message : 'Screenshot could not be saved.' });
  }
}

function localShots(): Plugin {
  return {
    name: 'athen-local-shots',
    configureServer(server) { server.middlewares.use((req, res, next) => { void saveShot(req, res, next); }); },
    configurePreviewServer(server) { server.middlewares.use((req, res, next) => { void saveShot(req, res, next); }); },
  };
}

export default defineConfig({
  base: './',
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
  plugins: [localShots()],
});
