// Shared bootstrap: load config, built site and database.
import fs from 'node:fs';
import path from 'node:path';
import { openDb } from './db.mjs';

/** @param {import('./config.mjs').Config} config */
export function loadSite(config) {
  const file = path.join(config.distDir, 'content.json');
  if (!fs.existsSync(file)) throw new Error(`Built site not found at ${file}. Run "npm run build" first.`);
  const site = JSON.parse(fs.readFileSync(file, 'utf8'));
  const relFile = path.join(config.distDir, 'RELEASE');
  site.release = fs.existsSync(relFile) ? fs.readFileSync(relFile, 'utf8').trim().slice(0, 80) : 'dev';
  return site;
}

/** @param {import('./config.mjs').Config} config @param {any} site */
export function openSiteDb(config, site, opts = {}) {
  return openDb(config.dbPath, { topics: site.content.topics.map((t) => t.slug), ...opts });
}
