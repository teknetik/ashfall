// Operator CLI. Run on the server with the same environment as the service, e.g.
//   sudo -u ashfall-promo env $(cat /etc/ashfall-promo/app.env | xargs) node server/cli.mjs <command>
// Commands never print password hashes, session tokens or post text.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { backup as sqliteBackup, DatabaseSync } from 'node:sqlite';
import { loadConfig } from './config.mjs';
import { openDb, migrate, currentVersion, SCHEMA_VERSION } from './db.mjs';
import { createStore } from './store.mjs';

const usage = `Usage: node server/cli.mjs <command>
  migrate                     Create the database if needed and apply pending migrations.
  status                      Show schema version and row counts.
  backup <dir> [--keep-daily N] [--keep-weekly N]
                              Consistent online backup (SQLite backup API) to <dir>/community-<UTC>.sqlite,
                              verified with integrity_check, then prune old backups (default 7 daily + 4 weekly).
  verify <file>               Run integrity_check on a backup and print its schema version and counts.
  restore <file> --yes        Restore a backup over ASHFALL_DB_PATH. The service MUST be stopped.
                              The current database is first copied aside as <db>.pre-restore-<UTC>.
  grant-moderator <username>  Give an existing account the moderator role.
  revoke-moderator <username> Remove the moderator role.
  suspend <username> | unsuspend <username>
  prune-sessions              Delete expired sessions.`;

function stamp() {
  return new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
}

function counts(db) {
  const n = (t) => Number(db.prepare(`SELECT COUNT(*) AS n FROM ${t}`).get().n);
  return { users: n('users'), sessions: n('sessions'), posts: n('posts'), topic_likes: n('topic_likes'), post_likes: n('post_likes'), reports: n('reports') };
}

function integrity(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  try {
    const r = db.prepare('PRAGMA integrity_check').get();
    const ok = Object.values(r)[0] === 'ok';
    const v = Number(db.prepare('SELECT MAX(version) AS v FROM schema_migrations').get().v);
    return { ok, version: v, counts: counts(db) };
  } finally {
    db.close();
  }
}

/** Keep the newest `daily` backups plus the newest backup of each of the last `weekly` ISO weeks. */
export function selectPrune(files, daily, weekly) {
  const sorted = [...files].sort().reverse();
  const keep = new Set(sorted.slice(0, daily));
  const weeks = new Map();
  for (const f of sorted) {
    const m = /community-(\d{4})(\d{2})(\d{2})T/.exec(f);
    if (!m) continue;
    const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    const wk = `${d.getUTCFullYear()}-${Math.floor((d.getTime() - Date.UTC(d.getUTCFullYear(), 0, 1)) / (7 * 86400000))}`;
    if (!weeks.has(wk)) weeks.set(wk, f);
  }
  [...weeks.values()].slice(0, weekly).forEach((f) => keep.add(f));
  return sorted.filter((f) => !keep.has(f));
}

async function main() {
  const [cmd, ...args] = process.argv.slice(2);
  if (!cmd || cmd === 'help' || cmd === '--help') { console.log(usage); return; }
  const config = loadConfig();
  switch (cmd) {
    case 'migrate': {
      const db = openDb(config.dbPath, { migrate: false });
      const before = currentVersion(db);
      const applied = migrate(db);
      console.log(`schema v${before} -> v${currentVersion(db)} (applied: ${applied.join(', ') || 'none'})`);
      db.close();
      return;
    }
    case 'status': {
      if (!fs.existsSync(config.dbPath)) { console.log('database does not exist yet'); return; }
      const db = openDb(config.dbPath, { migrate: false });
      console.log(JSON.stringify({ dbPath: config.dbPath, schema: currentVersion(db), appSchema: SCHEMA_VERSION, ...counts(db) }, null, 2));
      db.close();
      return;
    }
    case 'backup': {
      const dir = args[0];
      if (!dir) throw new Error('backup needs a destination directory');
      const opt = (name, d) => { const i = args.indexOf(name); return i > 0 ? Number(args[i + 1]) : d; };
      const keepDaily = opt('--keep-daily', 7);
      const keepWeekly = opt('--keep-weekly', 4);
      fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
      const db = openDb(config.dbPath, { migrate: false });
      const dest = path.join(path.resolve(dir), `community-${stamp()}.sqlite`);
      const tmp = `${dest}.partial`;
      await sqliteBackup(db, tmp);
      db.close();
      fs.chmodSync(tmp, 0o600);
      const check = integrity(tmp);
      if (!check.ok) { fs.rmSync(tmp, { force: true }); throw new Error('backup failed integrity_check; nothing kept'); }
      fs.renameSync(tmp, dest);
      const meta = { file: path.basename(dest), createdAt: new Date().toISOString(), schema: check.version, counts: check.counts, release: process.env.ASHFALL_RELEASE || readRelease(config) };
      fs.writeFileSync(`${dest}.json`, JSON.stringify(meta, null, 2), { mode: 0o600 });
      const all = fs.readdirSync(dir).filter((f) => /^community-\d{8}T\d{6}Z\.sqlite$/.test(f));
      const prune = selectPrune(all, keepDaily, keepWeekly);
      for (const f of prune) { fs.rmSync(path.join(dir, f), { force: true }); fs.rmSync(path.join(dir, `${f}.json`), { force: true }); }
      console.log(JSON.stringify({ backup: dest, schema: check.version, counts: check.counts, pruned: prune.length }, null, 2));
      return;
    }
    case 'verify': {
      const f = args[0];
      if (!f || !fs.existsSync(f)) throw new Error('verify needs an existing backup file');
      const r = integrity(f);
      console.log(JSON.stringify({ file: f, integrity: r.ok ? 'ok' : 'FAILED', schema: r.version, counts: r.counts }, null, 2));
      if (!r.ok) process.exitCode = 1;
      return;
    }
    case 'restore': {
      const f = args[0];
      if (!f || !fs.existsSync(f)) throw new Error('restore needs an existing backup file');
      if (!args.includes('--yes')) throw new Error('restore overwrites the live database; stop the service, then re-run with --yes');
      const r = integrity(f);
      if (!r.ok) throw new Error('backup failed integrity_check; refusing to restore');
      if (r.version > SCHEMA_VERSION) throw new Error(`backup schema v${r.version} is newer than this release (v${SCHEMA_VERSION})`);
      const target = config.dbPath;
      fs.mkdirSync(path.dirname(target), { recursive: true, mode: 0o700 });
      if (fs.existsSync(target)) {
        // Copy the current state aside consistently first.
        const cur = new DatabaseSync(target);
        const aside = `${target}.pre-restore-${stamp()}`;
        await sqliteBackup(cur, aside);
        cur.close();
        fs.chmodSync(aside, 0o600);
        console.log(`current database saved to ${aside}`);
      }
      const src = new DatabaseSync(f, { readOnly: true });
      const tmp = `${target}.restoring`;
      fs.rmSync(tmp, { force: true });
      await sqliteBackup(src, tmp);
      src.close();
      for (const ext of ['-wal', '-shm']) fs.rmSync(`${target}${ext}`, { force: true });
      fs.renameSync(tmp, target);
      fs.chmodSync(target, 0o600);
      const db = openDb(target);
      console.log(JSON.stringify({ restored: target, from: f, schema: currentVersion(db), counts: counts(db) }, null, 2));
      db.close();
      return;
    }
    case 'grant-moderator':
    case 'revoke-moderator':
    case 'suspend':
    case 'unsuspend': {
      const name = String(args[0] || '').toLowerCase();
      const db = openDb(config.dbPath);
      const store = createStore(db);
      const u = store.findUser(name);
      if (!u) { db.close(); throw new Error(`no such user: ${name}`); }
      if (cmd === 'grant-moderator') store.setRole(u.id, 'moderator');
      else if (cmd === 'revoke-moderator') store.setRole(u.id, 'member');
      else store.setStatus(u.id, cmd === 'suspend' ? 'suspended' : 'active', null);
      if (cmd === 'suspend') store.deleteUserSessions(u.id);
      console.log(`${cmd}: ${u.username} ok`);
      db.close();
      return;
    }
    case 'prune-sessions': {
      const db = openDb(config.dbPath);
      console.log(`expired sessions removed: ${createStore(db).pruneSessions()}`);
      db.close();
      return;
    }
    default:
      console.error(usage);
      process.exitCode = 2;
  }
}

function readRelease(config) {
  const f = path.join(config.distDir, 'RELEASE');
  return fs.existsSync(f) ? fs.readFileSync(f, 'utf8').trim() : 'dev';
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main().catch((e) => {
    console.error(`error: ${e.message}`);
    process.exitCode = 1;
  });
}
