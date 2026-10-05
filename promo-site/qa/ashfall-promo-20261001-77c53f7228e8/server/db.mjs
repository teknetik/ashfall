// SQLite persistence (node:sqlite, built into Node; no native addon to compile).
// All statements are parameterised; no SQL is ever built from request data.
import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

/** Ordered, append-only migrations. Never edit a shipped migration; add a new one. */
export const MIGRATIONS = [
  {
    version: 1,
    name: 'initial community schema',
    sql: `
      CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
        pw_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member','moderator')),
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended')),
        created_at INTEGER NOT NULL,
        password_changed_at INTEGER NOT NULL
      );
      CREATE TABLE sessions (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        csrf TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        last_seen_at INTEGER NOT NULL
      );
      CREATE INDEX sessions_user ON sessions(user_id);
      CREATE INDEX sessions_expiry ON sessions(expires_at);
      CREATE TABLE topics (
        slug TEXT PRIMARY KEY,
        locked INTEGER NOT NULL DEFAULT 0,
        locked_at INTEGER,
        locked_by INTEGER REFERENCES users(id) ON DELETE SET NULL
      );
      CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        topic TEXT NOT NULL REFERENCES topics(slug),
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        parent_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
        type TEXT NOT NULL CHECK (type IN ('idea','feedback','reply')),
        tag TEXT CHECK (tag IS NULL OR tag IN ('story','mechanics','art','build')),
        body TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        edited_at INTEGER,
        deleted_at INTEGER,
        removed_at INTEGER,
        removed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        removed_reason TEXT
      );
      CREATE INDEX posts_topic ON posts(topic, parent_id, id);
      CREATE INDEX posts_user ON posts(user_id);
      CREATE INDEX posts_parent ON posts(parent_id);
      CREATE TABLE topic_likes (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        topic TEXT NOT NULL REFERENCES topics(slug),
        created_at INTEGER NOT NULL,
        PRIMARY KEY (user_id, topic)
      );
      CREATE TABLE post_likes (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        created_at INTEGER NOT NULL,
        PRIMARY KEY (user_id, post_id)
      );
      CREATE INDEX post_likes_post ON post_likes(post_id);
      CREATE TABLE reports (
        id INTEGER PRIMARY KEY,
        post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        reason TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        resolved_at INTEGER,
        resolved_by INTEGER REFERENCES users(id) ON DELETE SET NULL
      );
      CREATE UNIQUE INDEX reports_once ON reports(post_id, user_id) WHERE resolved_at IS NULL;
      CREATE TABLE mod_log (
        id INTEGER PRIMARY KEY,
        actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        action TEXT NOT NULL,
        target TEXT NOT NULL,
        reason TEXT,
        created_at INTEGER NOT NULL
      );
    `,
  },
];

export const SCHEMA_VERSION = MIGRATIONS[MIGRATIONS.length - 1].version;

/**
 * Open (creating if needed) the database, apply pragmas and pending migrations.
 * @param {string} dbPath
 * @param {{topics?: string[], migrate?: boolean}} [opts]
 */
export function openDb(dbPath, opts = {}) {
  const dir = path.dirname(dbPath);
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  const existed = fs.existsSync(dbPath);
  const db = new DatabaseSync(dbPath);
  if (!existed) fs.chmodSync(dbPath, 0o600);
  db.exec('PRAGMA journal_mode = WAL');
  db.exec('PRAGMA synchronous = NORMAL');
  db.exec('PRAGMA foreign_keys = ON');
  db.exec('PRAGMA busy_timeout = 5000');
  db.exec('PRAGMA secure_delete = ON');
  if (opts.migrate !== false) migrate(db);
  if (opts.topics) ensureTopics(db, opts.topics);
  return db;
}

/** @param {DatabaseSync} db */
export function currentVersion(db) {
  db.exec('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at INTEGER NOT NULL)');
  const row = /** @type {{v:number|null}} */ (db.prepare('SELECT MAX(version) AS v FROM schema_migrations').get());
  return row.v ?? 0;
}

/** @param {DatabaseSync} db */
export function migrate(db) {
  const have = currentVersion(db);
  if (have > SCHEMA_VERSION) throw new Error(`Database schema v${have} is newer than this app (v${SCHEMA_VERSION}); refusing to run an older release against it`);
  const applied = [];
  for (const m of MIGRATIONS) {
    if (m.version <= have) continue;
    db.exec('BEGIN IMMEDIATE');
    try {
      db.exec(m.sql);
      db.prepare('INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)').run(m.version, m.name, Date.now());
      db.exec('COMMIT');
      applied.push(m.version);
    } catch (e) {
      db.exec('ROLLBACK');
      throw e;
    }
  }
  return applied;
}

/** @param {DatabaseSync} db @param {string[]} slugs */
export function ensureTopics(db, slugs) {
  const ins = db.prepare('INSERT OR IGNORE INTO topics (slug) VALUES (?)');
  for (const s of slugs) ins.run(s);
}

/**
 * Run fn inside a transaction.
 * @template T
 * @param {DatabaseSync} db
 * @param {() => T} fn
 * @returns {T}
 */
export function tx(db, fn) {
  db.exec('BEGIN IMMEDIATE');
  try {
    const r = fn();
    db.exec('COMMIT');
    return r;
  } catch (e) {
    db.exec('ROLLBACK');
    throw e;
  }
}
