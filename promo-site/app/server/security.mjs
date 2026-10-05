// Password hashing, session tokens, CSRF and in-memory abuse limits.
import crypto from 'node:crypto';
import { promisify } from 'node:util';

const scryptAsync = /** @type {(pw: crypto.BinaryLike, salt: crypto.BinaryLike, keylen: number, opts: crypto.ScryptOptions) => Promise<Buffer>} */ (promisify(crypto.scrypt));

const KEYLEN = 64;
const R = 8;
const P = 1;

/** @param {number} n */
const maxmem = (n) => 128 * n * R * 2 + 1024 * 1024;

/**
 * Hash a password with scrypt and a random 16-byte salt.
 * Format: scrypt$N$r$p$saltB64$hashB64
 * @param {string} password
 * @param {number} N
 */
export async function hashPassword(password, N) {
  const salt = crypto.randomBytes(16);
  const key = await scryptAsync(password.normalize('NFKC'), salt, KEYLEN, { N, r: R, p: P, maxmem: maxmem(N) });
  return `scrypt$${N}$${R}$${P}$${salt.toString('base64')}$${key.toString('base64')}`;
}

/**
 * Constant-time verify. Returns false for malformed hashes rather than throwing.
 * @param {string} password
 * @param {string} stored
 */
export async function verifyPassword(password, stored) {
  const parts = String(stored).split('$');
  if (parts.length !== 6 || parts[0] !== 'scrypt') return false;
  const N = Number(parts[1]);
  const r = Number(parts[2]);
  const p = Number(parts[3]);
  if (![N, r, p].every(Number.isSafeInteger) || N < 2 || N > 2 ** 20 || r < 1 || r > 32 || p < 1 || p > 16) return false;
  const salt = Buffer.from(parts[4], 'base64');
  const expected = Buffer.from(parts[5], 'base64');
  if (expected.length !== KEYLEN) return false;
  const key = await scryptAsync(password.normalize('NFKC'), salt, KEYLEN, { N, r, p, maxmem: 128 * N * r * 2 + 1024 * 1024 });
  return crypto.timingSafeEqual(key, expected);
}

/** @param {string} stored @param {number} N */
export function needsRehash(stored, N) {
  const parts = String(stored).split('$');
  return parts[0] !== 'scrypt' || Number(parts[1]) < N;
}

/** Random URL-safe token. @param {number} [bytes] */
export function randomToken(bytes = 32) {
  return crypto.randomBytes(bytes).toString('base64url');
}

/** @param {string} token */
export function sha256(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

/** Constant-time string compare. @param {string} a @param {string} b */
export function safeEqual(a, b) {
  const ab = Buffer.from(String(a));
  const bb = Buffer.from(String(b));
  if (ab.length !== bb.length) return false;
  return crypto.timingSafeEqual(ab, bb);
}

export const USERNAME_RE = /^[a-z0-9_-]{3,24}$/;
export const PASSWORD_MIN = 10;
export const PASSWORD_MAX = 200;

// A short deny-list of the most common passwords that satisfy the length rule.
const COMMON = new Set([
  '1234567890', '0123456789', '12345678910', 'qwertyuiop', 'password12', 'password123', 'password1234',
  'iloveyou12', 'qwerty1234', 'qwerty12345', 'abcdefghij', '1q2w3e4r5t', 'aaaaaaaaaa', 'letmein123',
  'administrator', 'welcome123', 'passw0rd123', 'football123', 'baseball123', 'princess123', 'sunshine123',
  'ashfall123', 'ashfallashfall', 'trustno1234', '1111111111', '0000000000', 'zaq12wsxcde',
]);

/**
 * @param {string} username
 * @param {string} password
 * @returns {string|null} error message or null
 */
export function passwordProblem(username, password) {
  if (typeof password !== 'string' || password.length < PASSWORD_MIN) return `Use at least ${PASSWORD_MIN} characters.`;
  if (password.length > PASSWORD_MAX) return `Use at most ${PASSWORD_MAX} characters.`;
  const lower = password.toLowerCase();
  if (COMMON.has(lower)) return 'That password is too common. Try a longer phrase.';
  if (username && lower.includes(username.toLowerCase())) return 'Your password must not contain your username.';
  if (new Set(password).size < 4) return 'That password is too repetitive.';
  return null;
}

/**
 * Fixed-window counters keyed by string. In-memory only (cleared on restart);
 * entries expire with their window, so nothing is retained longer than the longest window.
 */
export class RateLimiter {
  constructor() {
    /** @type {Map<string, {count:number, reset:number}>} */
    this.buckets = new Map();
    this.timer = setInterval(() => this.sweep(), 60_000);
    this.timer.unref();
  }

  /**
   * Consume one unit. Returns {ok, retryAfter}.
   * @param {string} key
   * @param {number} limit
   * @param {number} windowMs
   * @param {number} [now]
   */
  hit(key, limit, windowMs, now = Date.now()) {
    let b = this.buckets.get(key);
    if (!b || b.reset <= now) {
      b = { count: 0, reset: now + windowMs };
      this.buckets.set(key, b);
    }
    b.count++;
    if (b.count > limit) return { ok: false, retryAfter: Math.ceil((b.reset - now) / 1000) };
    return { ok: true, retryAfter: 0 };
  }

  /** Peek without consuming. @param {string} key @param {number} limit */
  blocked(key, limit, now = Date.now()) {
    const b = this.buckets.get(key);
    return !!b && b.reset > now && b.count >= limit;
  }

  /** @param {string} key */
  reset(key) {
    this.buckets.delete(key);
  }

  sweep(now = Date.now()) {
    for (const [k, b] of this.buckets) if (b.reset <= now) this.buckets.delete(k);
    // Hard cap on memory: drop the oldest entries if an attacker floods unique keys.
    if (this.buckets.size > 100_000) {
      const drop = this.buckets.size - 100_000;
      let i = 0;
      for (const k of this.buckets.keys()) { if (i++ >= drop) break; this.buckets.delete(k); }
    }
  }

  close() {
    clearInterval(this.timer);
  }
}

/** Limits: [limit, windowMs]. Tuned for an invited-friends pilot. */
export const LIMITS = {
  requestsPerIp: [600, 60_000],
  postsPerIp: [120, 60_000],
  signupPerIp: [5, 60 * 60_000],
  signupGlobal: [40, 60 * 60_000],
  loginPerIp: [20, 15 * 60_000],
  loginPerUser: [8, 15 * 60_000],
  postPerUser: [8, 10 * 60_000],
  postPerUserDay: [60, 24 * 60 * 60_000],
  likePerUser: [60, 10 * 60_000],
  reportPerUser: [10, 60 * 60_000],
  accountPerUser: [10, 60 * 60_000],
};
