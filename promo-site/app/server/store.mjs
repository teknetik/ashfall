// Community data access. Pure functions over a DatabaseSync handle; every query is parameterised.
import { tx } from './db.mjs';

export const PAGE_SIZE = 20;
export const BODY_MIN = 10;
export const REPLY_MIN = 2;
export const BODY_MAX = 2000;
export const REPORT_REASONS = ['spam', 'abuse', 'personal', 'spoiler', 'other'];
export const TAGS = ['story', 'mechanics', 'art', 'build'];
export const RESERVED_USERNAMES = new Set(['admin', 'administrator', 'moderator', 'mod', 'mods', 'root', 'system', 'ashfall', 'teknetik', 'carl', 'deleted', 'anonymous', 'staff', 'support', 'security', 'null', 'undefined', 'official', 'lattice', 'warden', 'wardens']);

/** Normalise user-supplied text: NFC, CRLF->LF, strip control chars except \n and \t, trim, collapse 3+ blank lines. */
export function cleanText(s) {
  return String(s ?? '')
    .normalize('NFC')
    .replace(/\r\n?/g, '\n')
    // eslint-disable-next-line no-control-regex
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F\u200B-\u200F\u202A-\u202E\u2066-\u2069\uFEFF]/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/** @param {import('node:sqlite').DatabaseSync} db */
export function createStore(db) {
  // Rows from node:sqlite are untyped records; callers coerce numeric columns explicitly.
  /** @param {string} sql @returns {any} */
  const q = (sql) => db.prepare(sql);
  const s = {
    userByName: q('SELECT * FROM users WHERE username = ?'),
    userById: q('SELECT * FROM users WHERE id = ?'),
    insertUser: q('INSERT INTO users (username, pw_hash, created_at, password_changed_at) VALUES (?, ?, ?, ?)'),
    setPw: q('UPDATE users SET pw_hash = ?, password_changed_at = ? WHERE id = ?'),
    setRole: q('UPDATE users SET role = ? WHERE id = ?'),
    setStatus: q('UPDATE users SET status = ? WHERE id = ?'),
    insertSession: q('INSERT INTO sessions (token_hash, user_id, csrf, created_at, expires_at, last_seen_at) VALUES (?, ?, ?, ?, ?, ?)'),
    sessionByHash: q(`SELECT s.token_hash, s.csrf, s.expires_at, s.last_seen_at, u.id, u.username, u.role, u.status, u.created_at
                      FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?`),
    touchSession: q('UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?'),
    deleteSession: q('DELETE FROM sessions WHERE token_hash = ?'),
    deleteUserSessions: q('DELETE FROM sessions WHERE user_id = ?'),
    deleteOtherSessions: q('DELETE FROM sessions WHERE user_id = ? AND token_hash <> ?'),
    pruneSessions: q('DELETE FROM sessions WHERE expires_at <= ?'),
    topic: q('SELECT * FROM topics WHERE slug = ?'),
    lockTopic: q('UPDATE topics SET locked = ?, locked_at = ?, locked_by = ? WHERE slug = ?'),
    counts: q(`SELECT t.slug, t.locked,
                 (SELECT COUNT(*) FROM topic_likes l WHERE l.topic = t.slug) AS likes,
                 (SELECT COUNT(*) FROM posts p WHERE p.topic = t.slug AND p.type = 'idea' AND p.deleted_at IS NULL AND p.removed_at IS NULL) AS ideas,
                 (SELECT COUNT(*) FROM posts p WHERE p.topic = t.slug AND p.type = 'feedback' AND p.deleted_at IS NULL AND p.removed_at IS NULL) AS feedback
               FROM topics t`),
    insertPost: q('INSERT INTO posts (topic, user_id, parent_id, type, tag, body, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)'),
    postById: q(`SELECT p.*, u.username, u.role AS author_role FROM posts p LEFT JOIN users u ON u.id = p.user_id WHERE p.id = ?`),
    topLevelNew: q(`SELECT p.*, u.username, u.role AS author_role, (SELECT COUNT(*) FROM post_likes l WHERE l.post_id = p.id) AS likes
                    FROM posts p LEFT JOIN users u ON u.id = p.user_id
                    WHERE p.topic = ? AND p.parent_id IS NULL
                      AND (p.deleted_at IS NULL OR EXISTS (SELECT 1 FROM posts c WHERE c.parent_id = p.id AND c.deleted_at IS NULL))
                    ORDER BY p.id DESC LIMIT ?`),
    topLevelLiked: q(`SELECT p.*, u.username, u.role AS author_role, (SELECT COUNT(*) FROM post_likes l WHERE l.post_id = p.id) AS likes
                      FROM posts p LEFT JOIN users u ON u.id = p.user_id
                      WHERE p.topic = ? AND p.parent_id IS NULL AND p.type = 'idea' AND p.deleted_at IS NULL AND p.removed_at IS NULL
                      ORDER BY likes DESC, p.id DESC LIMIT ?`),
    replies: q(`SELECT p.*, u.username, u.role AS author_role, 0 AS likes FROM posts p LEFT JOIN users u ON u.id = p.user_id
                WHERE p.topic = ? AND p.parent_id IS NOT NULL AND p.deleted_at IS NULL ORDER BY p.id ASC`),
    liveChildren: q('SELECT COUNT(*) AS n FROM posts WHERE parent_id = ? AND deleted_at IS NULL'),
    deletePostRow: q('DELETE FROM posts WHERE id = ?'),
    softDeletePost: q("UPDATE posts SET body = '', tag = NULL, user_id = NULL, deleted_at = ?, removed_reason = NULL WHERE id = ?"),
    editPost: q('UPDATE posts SET body = ?, edited_at = ? WHERE id = ?'),
    removePost: q('UPDATE posts SET removed_at = ?, removed_by = ?, removed_reason = ? WHERE id = ?'),
    restorePost: q('UPDATE posts SET removed_at = NULL, removed_by = NULL, removed_reason = NULL WHERE id = ?'),
    topicLiked: q('SELECT 1 AS x FROM topic_likes WHERE user_id = ? AND topic = ?'),
    likeTopic: q('INSERT OR IGNORE INTO topic_likes (user_id, topic, created_at) VALUES (?, ?, ?)'),
    unlikeTopic: q('DELETE FROM topic_likes WHERE user_id = ? AND topic = ?'),
    postLiked: q('SELECT 1 AS x FROM post_likes WHERE user_id = ? AND post_id = ?'),
    likePost: q('INSERT OR IGNORE INTO post_likes (user_id, post_id, created_at) VALUES (?, ?, ?)'),
    unlikePost: q('DELETE FROM post_likes WHERE user_id = ? AND post_id = ?'),
    userLikedInTopic: q('SELECT l.post_id FROM post_likes l JOIN posts p ON p.id = l.post_id WHERE l.user_id = ? AND p.topic = ?'),
    report: q('INSERT OR IGNORE INTO reports (post_id, user_id, reason, created_at) VALUES (?, ?, ?, ?)'),
    openReports: q(`SELECT p.id, p.topic, p.body, p.removed_at, u.username, MIN(r.created_at) AS reported_at,
                      GROUP_CONCAT(DISTINCT r.reason) AS reason, COUNT(*) AS report_count
                    FROM reports r JOIN posts p ON p.id = r.post_id LEFT JOIN users u ON u.id = p.user_id
                    WHERE r.resolved_at IS NULL GROUP BY p.id ORDER BY reported_at ASC LIMIT 200`),
    resolveReports: q('UPDATE reports SET resolved_at = ?, resolved_by = ? WHERE post_id = ? AND resolved_at IS NULL'),
    removedPosts: q(`SELECT p.*, u.username FROM posts p LEFT JOIN users u ON u.id = p.user_id WHERE p.removed_at IS NOT NULL AND p.deleted_at IS NULL ORDER BY p.removed_at DESC LIMIT 100`),
    recentPosts: q(`SELECT p.*, u.username FROM posts p LEFT JOIN users u ON u.id = p.user_id WHERE p.deleted_at IS NULL ORDER BY p.id DESC LIMIT 50`),
    recentPublic: q(`SELECT p.id, p.topic, p.type, p.body, p.created_at, u.username FROM posts p LEFT JOIN users u ON u.id = p.user_id
                     WHERE p.parent_id IS NULL AND p.deleted_at IS NULL AND p.removed_at IS NULL ORDER BY p.id DESC LIMIT ?`),
    userPosts: q(`SELECT id, topic, type, body, created_at, removed_at FROM posts WHERE user_id = ? AND deleted_at IS NULL ORDER BY id DESC LIMIT 200`),
    userPostIds: q('SELECT id FROM posts WHERE user_id = ? ORDER BY id DESC'),
    deleteUserReports: q('DELETE FROM reports WHERE user_id = ?'),
    deleteUser: q('DELETE FROM users WHERE id = ?'),
    orphanDeleted: q('SELECT id FROM posts p WHERE p.deleted_at IS NOT NULL AND NOT EXISTS (SELECT 1 FROM posts c WHERE c.parent_id = p.id AND c.deleted_at IS NULL)'),
    users: q(`SELECT u.id, u.username, u.role, u.status, u.created_at, (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id AND p.deleted_at IS NULL) AS posts
              FROM users u ORDER BY u.id DESC LIMIT 500`),
    modLog: q('INSERT INTO mod_log (actor_id, action, target, reason, created_at) VALUES (?, ?, ?, ?, ?)'),
    userCount: q('SELECT COUNT(*) AS n FROM users'),
    postCount: q('SELECT COUNT(*) AS n FROM posts'),
  };

  const store = {
    db,
    findUser: (name) => s.userByName.get(name),
    userById: (id) => s.userById.get(id),
    createUser(username, pwHash, now = Date.now()) {
      const r = s.insertUser.run(username, pwHash, now, now);
      return Number(r.lastInsertRowid);
    },
    setPassword(userId, pwHash, now = Date.now()) { s.setPw.run(pwHash, now, userId); },
    setRole(userId, role) { s.setRole.run(role, userId); },
    setStatus(userId, status, actorId, now = Date.now()) {
      tx(db, () => {
        s.setStatus.run(status, userId);
        s.modLog.run(actorId ?? null, status === 'suspended' ? 'suspend' : 'unsuspend', `user:${userId}`, null, now);
      });
    },
    createSession(tokenHash, userId, csrf, now, expires) { s.insertSession.run(tokenHash, userId, csrf, now, expires, now); },
    session: (tokenHash) => s.sessionByHash.get(tokenHash),
    touchSession(tokenHash, now) { s.touchSession.run(now, tokenHash); },
    deleteSession(tokenHash) { s.deleteSession.run(tokenHash); },
    deleteUserSessions(userId) { s.deleteUserSessions.run(userId); },
    deleteOtherSessions(userId, keepHash) { s.deleteOtherSessions.run(userId, keepHash); },
    pruneSessions(now = Date.now()) { return Number(s.pruneSessions.run(now).changes); },
    topic: (slug) => s.topic.get(slug),
    setTopicLock(slug, locked, actorId, now = Date.now()) {
      tx(db, () => {
        s.lockTopic.run(locked ? 1 : 0, locked ? now : null, locked ? actorId : null, slug);
        s.modLog.run(actorId, locked ? 'lock' : 'unlock', `topic:${slug}`, null, now);
      });
    },
    counts() {
      /** @type {Record<string, {likes:number, ideas:number, feedback:number, locked:number}>} */
      const out = {};
      for (const r of s.counts.all()) out[r.slug] = { likes: Number(r.likes), ideas: Number(r.ideas), feedback: Number(r.feedback), locked: Number(r.locked) };
      return out;
    },
    createPost({ topic, userId, parentId = null, type, tag = null, body, now = Date.now() }) {
      const r = s.insertPost.run(topic, userId, parentId, type, tag, body, now);
      return Number(r.lastInsertRowid);
    },
    post: (id) => s.postById.get(id),
    topicPosts(topic, sort, limit) {
      const top = (sort === 'liked' ? s.topLevelLiked : s.topLevelNew).all(topic, limit + 1);
      const hasMore = top.length > limit;
      const posts = top.slice(0, limit);
      const ids = new Set(posts.map((p) => p.id));
      /** @type {Map<number, any[]>} */
      const repliesByParent = new Map();
      for (const r of s.replies.all(topic)) {
        if (!ids.has(r.parent_id)) continue;
        if (!repliesByParent.has(r.parent_id)) repliesByParent.set(r.parent_id, []);
        repliesByParent.get(r.parent_id).push(r);
      }
      return { posts, repliesByParent, hasMore };
    },
    /** Owner deletion: hard delete unless other people's live replies hang off it. */
    deletePost(id, now = Date.now()) {
      tx(db, () => {
        const n = Number(s.liveChildren.get(id).n);
        if (n > 0) s.softDeletePost.run(now, id);
        else s.deletePostRow.run(id);
        cleanupOrphans();
      });
    },
    editPost(id, body, now = Date.now()) { s.editPost.run(body, now, id); },
    removePost(id, actorId, reason, now = Date.now()) {
      tx(db, () => {
        s.removePost.run(now, actorId, reason, id);
        s.resolveReports.run(now, actorId, id);
        s.modLog.run(actorId, 'remove', `post:${id}`, reason, now);
      });
    },
    restorePost(id, actorId, now = Date.now()) {
      tx(db, () => {
        s.restorePost.run(id);
        s.modLog.run(actorId, 'restore', `post:${id}`, null, now);
      });
    },
    resolveReports(id, actorId, now = Date.now()) {
      tx(db, () => {
        s.resolveReports.run(now, actorId, id);
        s.modLog.run(actorId, 'dismiss-reports', `post:${id}`, null, now);
      });
    },
    toggleTopicLike(userId, topic, now = Date.now()) {
      return tx(db, () => {
        if (s.topicLiked.get(userId, topic)) { s.unlikeTopic.run(userId, topic); return false; }
        s.likeTopic.run(userId, topic, now);
        return true;
      });
    },
    topicLiked: (userId, topic) => !!s.topicLiked.get(userId, topic),
    togglePostLike(userId, postId, now = Date.now()) {
      return tx(db, () => {
        if (s.postLiked.get(userId, postId)) { s.unlikePost.run(userId, postId); return false; }
        s.likePost.run(userId, postId, now);
        return true;
      });
    },
    likedPostsInTopic: (userId, topic) => new Set(s.userLikedInTopic.all(userId, topic).map((r) => Number(r.post_id))),
    report(postId, userId, reason, now = Date.now()) { return Number(s.report.run(postId, userId, reason, now).changes) > 0; },
    openReports: () => s.openReports.all(),
    removedPosts: () => s.removedPosts.all(),
    recentPosts: () => s.recentPosts.all(),
    recentPublic: (n) => s.recentPublic.all(n),
    userPosts: (userId) => s.userPosts.all(userId),
    users: () => s.users.all(),
    /** Delete the account: erase all post text, remove the user and every row tied to them. */
    deleteAccount(userId, now = Date.now()) {
      tx(db, () => {
        for (const { id } of s.userPostIds.all(userId)) {
          const n = Number(s.liveChildren.get(id).n);
          if (n > 0) s.softDeletePost.run(now, id);
          else s.deletePostRow.run(id);
        }
        s.deleteUserReports.run(userId);
        s.deleteUser.run(userId);
        cleanupOrphans();
      });
    },
    stats: () => ({ users: Number(s.userCount.get().n), posts: Number(s.postCount.get().n) }),
  };

  function cleanupOrphans() {
    // Placeholders whose replies have all gone are no longer needed.
    for (let i = 0; i < 5; i++) {
      const rows = s.orphanDeleted.all();
      if (!rows.length) break;
      for (const r of rows) s.deletePostRow.run(r.id);
    }
  }

  return store;
}
