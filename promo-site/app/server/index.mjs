// Production entrypoint: node server/index.mjs (configured entirely by environment).
import http from 'node:http';
import https from 'node:https';
import fs from 'node:fs';
import { loadConfig } from './config.mjs';
import { loadSite, openSiteDb } from './boot.mjs';
import { createApp } from './app.mjs';

const config = loadConfig();
const site = loadSite(config);
const db = openSiteDb(config, site);
const app = createApp({ config, db, site });

const serverOpts = { requestTimeout: 15_000, headersTimeout: 10_000, keepAliveTimeout: 5_000, maxHeaderSize: 16 * 1024 };
const server = config.tlsCert && config.tlsKey
  ? https.createServer({ ...serverOpts, cert: fs.readFileSync(config.tlsCert), key: fs.readFileSync(config.tlsKey) }, (req, res) => { app.handle(req, res); })
  : http.createServer(serverOpts, (req, res) => { app.handle(req, res); });
server.maxRequestsPerSocket = 200;

const prune = setInterval(() => {
  try { app.store.pruneSessions(); } catch (e) { console.error('[prune]', String(e)); }
}, 60 * 60_000);
prune.unref();
app.store.pruneSessions();

server.listen(config.port, config.host, () => {
  const a = server.address();
  console.log(`[ashfall-promo] listening ${config.tlsCert ? 'https' : 'http'}://${typeof a === 'object' && a ? `${a.address}:${a.port}` : a} pid=${process.pid} release=${site.release} origin=${config.publicOrigin}`);
});

let closing = false;
function shutdown(sig) {
  if (closing) return;
  closing = true;
  console.log(`[ashfall-promo] ${sig}: shutting down`);
  server.close(() => {
    app.close();
    try { db.exec('PRAGMA wal_checkpoint(TRUNCATE)'); } catch { /* ignore */ }
    db.close();
    process.exit(0);
  });
  setTimeout(() => process.exit(0), 8000).unref();
  server.closeIdleConnections?.();
}
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
