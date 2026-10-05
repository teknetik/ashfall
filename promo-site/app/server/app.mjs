// HTTP application: routing, security middleware, auth and community handlers.
import fs from 'node:fs';
import path from 'node:path';
import net from 'node:net';
import { createStore, cleanText, PAGE_SIZE, BODY_MIN, REPLY_MIN, BODY_MAX, REPORT_REASONS, TAGS, RESERVED_USERNAMES } from './store.mjs';
import { createViews } from './views.mjs';
import { hashPassword, verifyPassword, needsRehash, randomToken, sha256, safeEqual, passwordProblem, RateLimiter, LIMITS, USERNAME_RE, PASSWORD_MAX } from './security.mjs';
import { SCHEMA_VERSION } from './db.mjs';

const SESSION_COOKIE = '__Host-ashfall_session';
const CSRF_COOKIE = '__Host-ashfall_csrf';
const MAX_BODY = 16 * 1024;
const TOUCH_INTERVAL = 5 * 60_000;

const MIME = {
  '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.avif': 'image/avif', '.webp': 'image/webp',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.txt': 'text/plain; charset=utf-8', '.ico': 'image/x-icon',
};

const CSP = [
  "default-src 'none'", "script-src 'self'", "style-src 'self'", "img-src 'self'", "font-src 'self'", "connect-src 'self'",
  "form-action 'self'", "frame-ancestors 'none'", "base-uri 'none'", "object-src 'none'", "manifest-src 'self'", 'upgrade-insecure-requests',
].join('; ');

export class HttpError extends Error {
  /** @param {number} status @param {string} message @param {Record<string,string>} [headers] */
  constructor(status, message, headers = {}) {
    super(message);
    this.status = status;
    this.headers = headers;
    /** @type {string|undefined} post-login return path for 401s */
    this.next = undefined;
  }
}

/** Parse Cookie header without throwing. */
function parseCookies(header) {
  /** @type {Record<string,string>} */
  const out = {};
  if (!header) return out;
  for (const part of header.split(';')) {
    const i = part.indexOf('=');
    if (i < 0) continue;
    const k = part.slice(0, i).trim();
    if (!k || k in out) continue;
    out[k] = part.slice(i + 1).trim();
  }
  return out;
}

const TOKEN_RE = /^[A-Za-z0-9_-]{20,100}$/;

/** Safe local redirect target. */
export function safeNext(next) {
  if (typeof next !== 'string' || next.length > 200) return '';
  if (!/^\/(?:discuss(?:\/[a-z-]+)?|account|gallery|about)?(?:#[a-z0-9-]+)?$/.test(next)) return '';
  return next;
}

/**
 * @param {{config: import('./config.mjs').Config, db: import('node:sqlite').DatabaseSync, site: any, log?: (line: string) => void}} opts
 */
export function createApp({ config, db, site, log = (l) => process.stdout.write(`${l}\n`) }) {
  const store = createStore(db);
  const views = createViews({ ...site, origin: config.publicOrigin });
  const limiter = new RateLimiter();
  LIMITS.signupPerIp = [config.signupPerIpHour, 60 * 60_000];
  const topicSlugs = new Set(site.content.topics.map((t) => t.slug));
  const publicHost = new URL(config.publicOrigin).host;
  const startedAt = Date.now();
  const DUMMY_HASH_P = hashPassword(randomToken(16), config.scryptN);

  // Static files: exact-match map built once from dist/public (no path joins from request data).
  const PUB = path.join(config.distDir, 'public');
  /** @type {Map<string, {file: string, type: string, immutable: boolean, size: number}>} */
  const statics = new Map();
  const walk = (dir, prefix) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const fp = path.join(dir, e.name);
      if (e.isDirectory()) { walk(fp, `${prefix}${e.name}/`); continue; }
      const ext = path.extname(e.name);
      if (!MIME[ext]) continue;
      statics.set(`/${prefix}${e.name}`, { file: fp, type: MIME[ext], immutable: /\.[0-9a-f]{10}\.[a-z0-9]+$/.test(e.name), size: fs.statSync(fp).size });
    }
  };
  walk(PUB, '');

  /** Determine the client address used for abuse limits. */
  function clientIp(req) {
    const peer = req.socket.remoteAddress || 'unknown';
    if (config.clientIpHeader) {
      const loopback = peer === '127.0.0.1' || peer === '::1' || peer === '::ffff:127.0.0.1';
      const v = req.headers[config.clientIpHeader];
      // Only the controlled loopback proxy may supply the client address, and only as a single valid IP.
      if (loopback && typeof v === 'string' && net.isIP(v.trim())) return v.trim();
    }
    return peer;
  }

  function securityHeaders(res) {
    res.setHeader('Content-Security-Policy', CSP);
    res.setHeader('Strict-Transport-Security', 'max-age=31536000');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'same-origin');
    res.setHeader('X-Frame-Options', 'DENY');
    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
    res.setHeader('Cross-Origin-Resource-Policy', 'same-origin');
    res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()');
  }

  function send(res, status, body, type = 'text/html; charset=utf-8', extra = {}) {
    res.statusCode = status;
    res.setHeader('Content-Type', type);
    for (const [k, v] of Object.entries(extra)) res.setHeader(k, v);
    if (!res.getHeader('Cache-Control')) res.setHeader('Cache-Control', 'no-store');
    res.end(body);
  }

  function redirect(res, location, status = 303) {
    res.statusCode = status;
    res.setHeader('Location', location);
    res.setHeader('Cache-Control', 'no-store');
    res.end();
  }

  function sessionCookie(token, maxAgeS) {
    return `${SESSION_COOKIE}=${token}; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=${maxAgeS}`;
  }
  const clearSessionCookie = () => `${SESSION_COOKIE}=; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=0`;

  /** Load the session, if any. */
  function loadSession(req, res, now) {
    const tok = req.cookies[SESSION_COOKIE];
    if (!tok || !TOKEN_RE.test(tok)) return null;
    const h = sha256(tok);
    const s = store.session(h);
    if (!s) { res.setHeader('Set-Cookie', clearSessionCookie()); return null; }
    if (Number(s.expires_at) <= now) { store.deleteSession(h); res.setHeader('Set-Cookie', clearSessionCookie()); return null; }
    if (now - Number(s.last_seen_at) > TOUCH_INTERVAL) store.touchSession(h, now);
    return { hash: h, csrf: s.csrf, user: { id: Number(s.id), username: s.username, role: s.role, status: s.status, created_at: s.created_at } };
  }

  /** Anonymous form token (double-submit cookie). Issued only on pages with forms. */
  function anonCsrf(req, res) {
    let t = req.cookies[CSRF_COOKIE];
    if (!t || !TOKEN_RE.test(t)) {
      t = randomToken(24);
      appendCookie(res, `${CSRF_COOKIE}=${t}; Path=/; Secure; HttpOnly; SameSite=Strict`);
    }
    return t;
  }

  function appendCookie(res, c) {
    const prev = res.getHeader('Set-Cookie');
    res.setHeader('Set-Cookie', prev ? [...(Array.isArray(prev) ? prev : [String(prev)]), c] : c);
  }

  /** Origin/Fetch-metadata check for every state-changing request. */
  function checkOrigin(req) {
    const sfs = req.headers['sec-fetch-site'];
    if (sfs && sfs !== 'same-origin' && sfs !== 'none') throw new HttpError(403, 'Cross-site request refused.');
    const origin = req.headers.origin;
    if (origin) {
      if (origin !== config.publicOrigin) throw new HttpError(403, 'Request origin not allowed.');
      return;
    }
    const ref = req.headers.referer;
    if (ref) {
      let o = '';
      try { o = new URL(ref).origin; } catch { /* fallthrough */ }
      if (o === config.publicOrigin) return;
    }
    throw new HttpError(403, 'Missing or invalid request origin.');
  }

  function checkCsrf(req, form) {
    const sent = form.get('_csrf') || '';
    const expected = req.session ? req.session.csrf : req.cookies[CSRF_COOKIE] || '';
    if (!expected || !sent || !safeEqual(sent, expected)) throw new HttpError(403, 'Your form expired. Please go back, reload the page and try again.');
  }

  async function readForm(req) {
    const ct = String(req.headers['content-type'] || '').split(';')[0].trim().toLowerCase();
    if (ct !== 'application/x-www-form-urlencoded') throw new HttpError(415, 'Unsupported form encoding.');
    const len = Number(req.headers['content-length'] || 0);
    if (len > MAX_BODY) throw new HttpError(413, 'That submission is too large.');
    const chunks = [];
    let size = 0;
    for await (const c of req) {
      size += c.length;
      if (size > MAX_BODY) throw new HttpError(413, 'That submission is too large.');
      chunks.push(c);
    }
    const text = Buffer.concat(chunks).toString('utf8');
    const params = new URLSearchParams(text);
    if ([...params.keys()].length > 20) throw new HttpError(400, 'Too many fields.');
    return params;
  }

  function limit(key, which) {
    const [n, w] = LIMITS[which];
    const r = limiter.hit(`${which}:${key}`, n, w);
    if (!r.ok) throw new HttpError(429, 'Too many requests. Please wait a little and try again.', { 'Retry-After': String(r.retryAfter) });
  }

  const requireUser = (req, next = '') => {
    if (!req.session) { const e = new HttpError(401, 'Please sign in.'); e.next = next; throw e; }
    return req.session.user;
  };
  const requireActive = (req) => {
    const u = requireUser(req);
    if (u.status !== 'active') throw new HttpError(403, 'Your account is suspended.');
    return u;
  };
  const requireMod = (req) => {
    const u = requireUser(req);
    if (u.role !== 'moderator' || u.status !== 'active') throw new HttpError(403, 'Moderators only.');
    return u;
  };

  const flashOf = (req) => {
    const c = req.url.searchParams.get('done') || '';
    return /^[a-z]{1,20}$/.test(c) ? c : '';
  };
  const csrfFor = (req) => (req.session ? req.session.csrf : '');
  const base = (req) => ({ user: req.session?.user || null, csrf: csrfFor(req) });

  async function startSession(res, userId) {
    const token = randomToken(32);
    const now = Date.now();
    const maxAge = config.sessionDays * 86400;
    store.createSession(sha256(token), userId, randomToken(24), now, now + maxAge * 1000);
    appendCookie(res, sessionCookie(token, maxAge));
    appendCookie(res, `${CSRF_COOKIE}=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0`);
  }

  function intParam(v) {
    if (!/^[1-9][0-9]{0,9}$/.test(v || '')) return null;
    return Number(v);
  }

  /* ------------------------------ handlers ------------------------------ */

  const routes = [];
  const route = (method, pattern, handler) => routes.push({ method, pattern, handler });

  route('GET', /^\/$/, (req, res) => {
    const html = views.home({ ...base(req), counts: store.counts(), recent: store.recentPublic(3), flashCode: flashOf(req) });
    send(res, 200, String(html));
  });
  route('GET', /^\/gallery$/, (req, res) => send(res, 200, String(views.gallery(base(req)))));
  route('GET', /^\/development$/, (req, res) => send(res, 200, String(views.development({ ...base(req), counts: store.counts() }))));
  route('GET', /^\/about$/, (req, res) => send(res, 200, String(views.about(base(req)))));
  route('GET', /^\/privacy$/, (req, res) => send(res, 200, String(views.privacy({ ...base(req), sessionDays: config.sessionDays }))));
  route('GET', /^\/discuss$/, (req, res) => send(res, 200, String(views.discussIndex({ ...base(req), counts: store.counts(), flashCode: flashOf(req) }))));

  route('GET', /^\/discuss\/([a-z-]+)$/, (req, res, m) => {
    const slug = m[1];
    if (!topicSlugs.has(slug)) throw new HttpError(404, 'No such topic.');
    renderTopic(req, res, slug, {});
  });

  function renderTopic(req, res, slug, { status = 200, error = '', form = null }) {
    const sort = req.url.searchParams.get('sort') === 'liked' ? 'liked' : 'new';
    const page = Math.min(50, intParam(req.url.searchParams.get('page')) || 1);
    const { posts, repliesByParent, hasMore } = store.topicPosts(slug, sort, page * PAGE_SIZE);
    const counts = store.counts()[slug];
    const user = req.session?.user;
    const flashCode = req.url.searchParams.get('done') || '';
    const html = views.topicPage({
      ...base(req), slug, posts, repliesByParent, counts, sort, page, hasMore, flashCode: /^[a-z]{1,20}$/.test(flashCode) ? flashCode : '',
      likedTopic: user ? store.topicLiked(user.id, slug) : false, likedPosts: user ? store.likedPostsInTopic(user.id, slug) : new Set(), error, form,
    });
    send(res, status, String(html));
  }

  route('POST', /^\/discuss\/([a-z-]+)\/posts$/, async (req, res, m, form) => {
    const slug = m[1];
    if (!topicSlugs.has(slug)) throw new HttpError(404, 'No such topic.');
    const user = requireActive(req);
    limit(user.id, 'postPerUser');
    limit(user.id, 'postPerUserDay');
    const topic = store.topic(slug);
    if (topic.locked) throw new HttpError(403, 'This topic is locked.');
    const type = form.get('type') || '';
    const body = cleanText(form.get('body'));
    if (!['idea', 'feedback', 'reply'].includes(type)) throw new HttpError(400, 'Choose idea or feedback.');
    let parentId = null;
    if (type === 'reply') {
      parentId = intParam(form.get('parent'));
      const parent = parentId && store.post(parentId);
      if (!parent || parent.topic !== slug || parent.parent_id !== null || parent.deleted_at || parent.removed_at) throw new HttpError(400, 'You can only reply to a visible post in this topic.');
    }
    const min = type === 'reply' ? REPLY_MIN : BODY_MIN;
    const tagRaw = form.get('tag') || '';
    const tag = type === 'feedback' && TAGS.includes(tagRaw) ? tagRaw : null;
    if (body.length < min || body.length > BODY_MAX) {
      const error = `Write between ${min} and ${BODY_MAX} characters (you wrote ${body.length}).`;
      if (type === 'reply') throw new HttpError(400, error);
      return renderTopic(req, res, slug, { status: 400, error, form: { type, tag: tagRaw, body } });
    }
    const id = store.createPost({ topic: slug, userId: user.id, parentId, type, tag, body });
    redirect(res, `/discuss/${slug}?done=${type === 'reply' ? 'replied' : 'posted'}#post-${id}`);
  });

  route('POST', /^\/discuss\/([a-z-]+)\/like$/, async (req, res, m) => {
    const slug = m[1];
    if (!topicSlugs.has(slug)) throw new HttpError(404, 'No such topic.');
    const user = requireActive(req);
    limit(user.id, 'likePerUser');
    if (store.topic(slug).locked) throw new HttpError(403, 'This topic is locked.');
    const on = store.toggleTopicLike(user.id, slug);
    redirect(res, `/discuss/${slug}?done=${on ? 'liked' : 'unliked'}`);
  });

  const loadPost = (m) => {
    const id = intParam(m[1]);
    const p = id && store.post(id);
    if (!p || p.deleted_at) throw new HttpError(404, 'That post does not exist.');
    return p;
  };

  route('POST', /^\/posts\/([0-9]+)\/like$/, async (req, res, m) => {
    const user = requireActive(req);
    limit(user.id, 'likePerUser');
    const p = loadPost(m);
    if (p.removed_at || p.type === 'reply') throw new HttpError(400, 'That post cannot be liked.');
    if (p.user_id === user.id) throw new HttpError(400, "You can't like your own post.");
    if (store.topic(p.topic).locked) throw new HttpError(403, 'This topic is locked.');
    const on = store.togglePostLike(user.id, p.id);
    redirect(res, `/discuss/${p.topic}?done=${on ? 'liked' : 'unliked'}#post-${p.id}`);
  });

  route('GET', /^\/posts\/([0-9]+)\/edit$/, (req, res, m) => {
    const user = requireUser(req);
    const p = loadPost(m);
    if (p.user_id !== user.id) throw new HttpError(403, 'You can only edit your own posts.');
    if (p.removed_at) throw new HttpError(403, 'Removed posts cannot be edited.');
    send(res, 200, String(views.editPost({ ...base(req), post: p })));
  });

  route('POST', /^\/posts\/([0-9]+)\/edit$/, async (req, res, m, form) => {
    const user = requireActive(req);
    limit(user.id, 'postPerUser');
    const p = loadPost(m);
    if (p.user_id !== user.id) throw new HttpError(403, 'You can only edit your own posts.');
    if (p.removed_at) throw new HttpError(403, 'Removed posts cannot be edited.');
    if (store.topic(p.topic).locked) throw new HttpError(403, 'This topic is locked.');
    const body = cleanText(form.get('body'));
    const min = p.type === 'reply' ? REPLY_MIN : BODY_MIN;
    if (body.length < min || body.length > BODY_MAX) {
      return send(res, 400, String(views.editPost({ ...base(req), post: { ...p, body }, error: `Write between ${min} and ${BODY_MAX} characters.` })));
    }
    store.editPost(p.id, body);
    redirect(res, `/discuss/${p.topic}?done=edited#post-${p.id}`);
  });

  route('POST', /^\/posts\/([0-9]+)\/delete$/, async (req, res, m) => {
    const user = requireUser(req);
    const p = loadPost(m);
    if (p.user_id !== user.id) throw new HttpError(403, 'You can only delete your own posts.');
    store.deletePost(p.id);
    redirect(res, `/discuss/${p.topic}?done=deleted`);
  });

  route('POST', /^\/posts\/([0-9]+)\/report$/, async (req, res, m, form) => {
    const user = requireActive(req);
    limit(user.id, 'reportPerUser');
    const p = loadPost(m);
    if (p.user_id === user.id) throw new HttpError(400, "You can't report your own post.");
    const reason = form.get('reason') || '';
    if (!REPORT_REASONS.includes(reason)) throw new HttpError(400, 'Choose a reason.');
    store.report(p.id, user.id, reason);
    redirect(res, `/discuss/${p.topic}?done=reported#post-${p.id}`);
  });

  /* ---- auth ---- */
  route('GET', /^\/join$/, (req, res) => {
    if (req.session) return redirect(res, '/account');
    const csrf = anonCsrf(req, res);
    send(res, 200, String(views.authForm({ mode: 'join', user: null, csrf, next: safeNext(req.url.searchParams.get('next')), inviteRequired: !!config.signupInviteCode, signupEnabled: config.signupEnabled })));
  });
  route('GET', /^\/login$/, (req, res) => {
    if (req.session) return redirect(res, '/account');
    const csrf = anonCsrf(req, res);
    send(res, 200, String(views.authForm({ mode: 'login', user: null, csrf, next: safeNext(req.url.searchParams.get('next')) })));
  });

  route('POST', /^\/join$/, async (req, res, _m, form) => {
    if (req.session) return redirect(res, '/account');
    if (!config.signupEnabled) throw new HttpError(403, 'Signup is closed.');
    limit(req.ip, 'signupPerIp');
    limit('all', 'signupGlobal');
    const username = String(form.get('username') || '').trim().toLowerCase();
    const password = String(form.get('password') || '');
    const confirm = String(form.get('confirm') || '');
    const next = safeNext(form.get('next'));
    /** @type {Record<string,string>} */
    const fieldErrors = {};
    if (!USERNAME_RE.test(username)) fieldErrors.username = 'Use 3–24 characters: lowercase letters, numbers, - and _.';
    else if (RESERVED_USERNAMES.has(username)) fieldErrors.username = 'That username is reserved. Please choose another.';
    const pwProblem = passwordProblem(username, password);
    if (pwProblem) fieldErrors.password = pwProblem;
    if (!fieldErrors.password && password !== confirm) fieldErrors.confirm = "The passwords don't match.";
    if (form.get('privacy') !== 'yes') fieldErrors.privacy = 'Please confirm you have read the privacy notice.';
    if (config.signupInviteCode && !safeEqual(String(form.get('invite') || '').trim(), config.signupInviteCode)) fieldErrors.invite = "That invite code isn't right.";
    const honeypot = form.get('website');
    if (honeypot) fieldErrors.username = fieldErrors.username || 'Please try again.';
    if (!fieldErrors.username && store.findUser(username)) fieldErrors.username = 'That username is taken. Please choose another.';
    if (Object.keys(fieldErrors).length) {
      const csrf = anonCsrf(req, res);
      return send(res, 400, String(views.authForm({ mode: 'join', user: null, csrf, error: 'Please fix the highlighted fields.', fieldErrors, values: { username, privacy: form.get('privacy') === 'yes' }, next, inviteRequired: !!config.signupInviteCode, signupEnabled: true })));
    }
    const hash = await hashPassword(password, config.scryptN);
    let userId;
    try {
      userId = store.createUser(username, hash);
    } catch (e) {
      if (/UNIQUE/.test(String(e))) {
        const csrf = anonCsrf(req, res);
        return send(res, 400, String(views.authForm({ mode: 'join', user: null, csrf, error: 'Please fix the highlighted fields.', fieldErrors: { username: 'That username is taken. Please choose another.' }, values: { username }, next, inviteRequired: !!config.signupInviteCode, signupEnabled: true })));
      }
      throw e;
    }
    await startSession(res, userId);
    redirect(res, next ? `${next}${next.includes('?') || next.includes('#') ? '' : '?done=welcome'}` : '/discuss?done=welcome');
  });

  route('POST', /^\/login$/, async (req, res, _m, form) => {
    if (req.session) return redirect(res, '/account');
    limit(req.ip, 'loginPerIp');
    const username = String(form.get('username') || '').trim().toLowerCase().slice(0, 64);
    const password = String(form.get('password') || '').slice(0, PASSWORD_MAX + 1);
    const next = safeNext(form.get('next'));
    const fail = () => {
      const csrf = anonCsrf(req, res);
      send(res, 401, String(views.authForm({ mode: 'login', user: null, csrf, error: "That username and password don't match an account.", values: { username }, next })));
    };
    // Per-account throttle (does not reveal whether the account exists).
    const acctKey = `loginPerUser:${username}`;
    if (limiter.blocked(acctKey, LIMITS.loginPerUser[0])) throw new HttpError(429, 'Too many sign-in attempts for this account. Please wait 15 minutes.', { 'Retry-After': '900' });
    const u = USERNAME_RE.test(username) ? store.findUser(username) : null;
    const ok = u ? await verifyPassword(password, u.pw_hash) : (await verifyPassword(password, await DUMMY_HASH_P), false);
    if (!ok || !u) {
      limiter.hit(acctKey, LIMITS.loginPerUser[0], LIMITS.loginPerUser[1]);
      return fail();
    }
    limiter.reset(acctKey);
    if (needsRehash(u.pw_hash, config.scryptN)) store.setPassword(u.id, await hashPassword(password, config.scryptN), u.password_changed_at);
    await startSession(res, Number(u.id));
    redirect(res, next || '/discuss?done=signedin');
  });

  route('POST', /^\/logout$/, async (req, res) => {
    if (req.session) store.deleteSession(req.session.hash);
    appendCookie(res, clearSessionCookie());
    redirect(res, '/?done=signedout');
  });

  route('GET', /^\/account$/, (req, res) => {
    const user = requireUser(req, '/account');
    const code = req.url.searchParams.get('done') || '';
    send(res, 200, String(views.account({ ...base(req), posts: store.userPosts(user.id), flashCode: /^[a-z]{1,20}$/.test(code) ? code : '' })));
  });

  route('POST', /^\/account\/password$/, async (req, res, _m, form) => {
    const user = requireUser(req);
    limit(user.id, 'accountPerUser');
    const row = store.userById(user.id);
    const current = String(form.get('current') || '').slice(0, PASSWORD_MAX + 1);
    const password = String(form.get('password') || '');
    const confirm = String(form.get('confirm') || '');
    /** @type {Record<string,string>} */
    const fieldErrors = {};
    if (!(await verifyPassword(current, row.pw_hash))) fieldErrors.current = "That isn't your current password.";
    const p = passwordProblem(user.username, password);
    if (p) fieldErrors.password = p;
    else if (password !== confirm) fieldErrors.confirm = "The passwords don't match.";
    if (Object.keys(fieldErrors).length) {
      return send(res, 400, String(views.account({ ...base(req), posts: store.userPosts(user.id), error: 'Your password was not changed.', fieldErrors })));
    }
    store.setPassword(user.id, await hashPassword(password, config.scryptN));
    store.deleteOtherSessions(user.id, req.session.hash);
    redirect(res, '/account?done=password');
  });

  route('POST', /^\/account\/delete$/, async (req, res, _m, form) => {
    const user = requireUser(req);
    limit(user.id, 'accountPerUser');
    const row = store.userById(user.id);
    if (!(await verifyPassword(String(form.get('password') || '').slice(0, PASSWORD_MAX + 1), row.pw_hash))) {
      return send(res, 400, String(views.account({ ...base(req), posts: store.userPosts(user.id), error: 'Your account was not deleted.', fieldErrors: { delete: "That isn't your password." } })));
    }
    store.deleteAccount(user.id);
    appendCookie(res, clearSessionCookie());
    redirect(res, '/?done=accountdeleted');
  });

  /* ---- moderation ---- */
  route('GET', /^\/moderation$/, (req, res) => {
    requireMod(req);
    const code = req.url.searchParams.get('done') || '';
    send(res, 200, String(views.moderation({ ...base(req), reports: store.openReports(), removed: store.removedPosts(), recent: store.recentPosts(), users: store.users(), flashCode: /^[a-z]{1,20}$/.test(code) ? code : '' })));
  });
  route('POST', /^\/moderation\/posts\/([0-9]+)\/remove$/, async (req, res, m, form) => {
    const mod = requireMod(req);
    const p = loadPost(m);
    const reason = cleanText(form.get('reason')).slice(0, 200);
    if (!reason) throw new HttpError(400, 'Give a reason for the removal.');
    store.removePost(p.id, mod.id, reason);
    redirect(res, `${backTo(req, `/discuss/${p.topic}`)}${'?done=removed'}`);
  });
  route('POST', /^\/moderation\/posts\/([0-9]+)\/restore$/, async (req, res, m) => {
    const mod = requireMod(req);
    const p = loadPost(m);
    store.restorePost(p.id, mod.id);
    redirect(res, `${backTo(req, `/discuss/${p.topic}`)}?done=restored`);
  });
  route('POST', /^\/moderation\/posts\/([0-9]+)\/resolve$/, async (req, res, m) => {
    const mod = requireMod(req);
    const p = loadPost(m);
    store.resolveReports(p.id, mod.id);
    redirect(res, '/moderation?done=resolved');
  });
  route('POST', /^\/moderation\/topics\/([a-z-]+)\/(lock|unlock)$/, async (req, res, m) => {
    const mod = requireMod(req);
    if (!topicSlugs.has(m[1])) throw new HttpError(404, 'No such topic.');
    store.setTopicLock(m[1], m[2] === 'lock', mod.id);
    redirect(res, `/discuss/${m[1]}?done=topic${m[2]}ed`);
  });
  route('POST', /^\/moderation\/users\/([0-9]+)\/(suspend|unsuspend)$/, async (req, res, m) => {
    const mod = requireMod(req);
    const id = intParam(m[1]);
    const target = id && store.userById(id);
    if (!target) throw new HttpError(404, 'No such user.');
    if (target.role === 'moderator') throw new HttpError(400, 'Moderators are managed from the server command line.');
    store.setStatus(target.id, m[2] === 'suspend' ? 'suspended' : 'active', mod.id);
    redirect(res, `/moderation?done=${m[2]}ed`);
  });

  /** Return the moderator to the moderation page if that's where they came from. */
  function backTo(req, fallback) {
    const ref = req.headers.referer;
    try {
      const u = new URL(ref);
      if (u.origin === config.publicOrigin && u.pathname === '/moderation') return '/moderation';
    } catch { /* ignore */ }
    return fallback;
  }

  /* ---- health ---- */
  route('GET', /^\/api\/health$/, (req, res) => {
    let dbOk;
    try { dbOk = db.prepare('SELECT 1 AS ok').get().ok === 1; } catch { dbOk = false; }
    const body = JSON.stringify({ status: dbOk ? 'ok' : 'degraded', db: dbOk ? 'ok' : 'error', schema: SCHEMA_VERSION, release: site.release || 'dev', uptimeS: Math.round((Date.now() - startedAt) / 1000) });
    send(res, dbOk ? 200 : 503, body, 'application/json; charset=utf-8');
  });

  route('GET', /^\/robots\.txt$/, (req, res) => send(res, 200, 'User-agent: *\nDisallow: /account\nDisallow: /moderation\nDisallow: /login\nDisallow: /join\nDisallow: /posts/\n', 'text/plain; charset=utf-8', { 'Cache-Control': 'public, max-age=3600' }));

  /* ------------------------------ dispatcher ------------------------------ */

  async function handle(req, res) {
    const t0 = process.hrtime.bigint();
    let pathname = '/';
    securityHeaders(res);
    try {
      if (req.method !== 'GET' && req.method !== 'HEAD' && req.method !== 'POST') throw new HttpError(405, 'Method not allowed.', { Allow: 'GET, HEAD, POST' });
      const rawUrl = req.url || '/';
      if (rawUrl.length > 2048) throw new HttpError(414, 'Address too long.');
      let url;
      try { url = new URL(rawUrl, config.publicOrigin); } catch { throw new HttpError(400, 'Bad address.'); }
      pathname = url.pathname;
      req.url = url;
      // Host guard: only the canonical public host (health is also reachable via loopback for local probes).
      const host = String(req.headers.host || '').toLowerCase();
      if (host !== publicHost && !(pathname === '/api/health' && /^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$/.test(host))) {
        throw new HttpError(421, 'Misdirected request.');
      }
      req.ip = clientIp(req);

      // Static assets first (exact match only). They sit before the per-IP request limit: a cold
      // /gallery view alone is ~40 requests, and visitors behind one address (NAT, the proxy before
      // the client-IP header is set) would otherwise exhaust the budget on images and CSS.
      if ((req.method === 'GET' || req.method === 'HEAD') && statics.has(pathname)) {
        const f = statics.get(pathname);
        res.statusCode = 200;
        res.setHeader('Content-Type', f.type);
        res.setHeader('Content-Length', String(f.size));
        res.setHeader('Cache-Control', f.immutable ? 'public, max-age=31536000, immutable' : 'public, max-age=3600');
        if (req.method === 'HEAD') { res.end(); return; }
        await new Promise((resolve, reject) => {
          const s = fs.createReadStream(f.file);
          s.on('error', reject);
          res.on('finish', resolve);
          res.on('close', resolve);
          s.pipe(res);
        });
        return;
      }

      limit(req.ip, 'requestsPerIp');
      req.cookies = parseCookies(req.headers.cookie);
      const now = Date.now();
      req.session = loadSession(req, res, now);

      const method = req.method === 'HEAD' ? 'GET' : req.method;
      let matched = null;
      let allowed = false;
      for (const r of routes) {
        const m = r.pattern.exec(pathname);
        if (!m) continue;
        allowed = true;
        if (r.method === method) { matched = { r, m }; break; }
      }
      if (!matched) throw allowed ? new HttpError(405, 'Method not allowed.', { Allow: 'GET, HEAD, POST' }) : new HttpError(404, "We couldn't find that page.");

      let form = null;
      if (method === 'POST') {
        limit(req.ip, 'postsPerIp');
        checkOrigin(req);
        form = await readForm(req);
        checkCsrf(req, form);
      }
      await matched.r.handler(req, res, matched.m, form);
    } catch (e) {
      const err = e instanceof HttpError ? e : null;
      if (!err) log(`[error] ${req.method} ${pathname} ${e && e.stack ? e.stack.split('\n').slice(0, 4).join(' | ') : String(e)}`);
      const status = err ? err.status : 500;
      if (res.headersSent) { res.destroy(); return; }
      if (status === 401) {
        const n = safeNext(err.next || '');
        redirect(res, `/login${n ? `?next=${encodeURIComponent(n)}` : ''}`);
      } else {
        for (const [k, v] of Object.entries(err ? err.headers : {})) res.setHeader(k, v);
        const message = err ? err.message : 'Something went wrong on our side. Please try again.';
        if (pathname.startsWith('/api/')) send(res, status, JSON.stringify({ error: message }), 'application/json; charset=utf-8');
        else {
          const titles = { 400: 'That request didn\u2019t work', 403: 'Not allowed', 404: 'Page not found', 405: 'Not allowed', 413: 'Too large', 415: 'Not supported', 421: 'Wrong address', 429: 'Slow down', 500: 'Something went wrong' };
          let html;
          try { html = String(views.errorPage({ status, title: titles[status] || 'Error', message, user: req.session?.user || null, csrf: req.session?.csrf || '' })); } catch { html = message; }
          send(res, status, html);
        }
      }
    } finally {
      if (config.logRequests) {
        const ms = Number(process.hrtime.bigint() - t0) / 1e6;
        log(`${req.method} ${pathname.slice(0, 200)} ${res.statusCode} ${ms.toFixed(1)}ms`);
      }
    }
  }

  return { handle, store, limiter, close: () => limiter.close() };
}
