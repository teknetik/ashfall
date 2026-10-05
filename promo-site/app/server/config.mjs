// Runtime configuration. Every value comes from the environment (systemd EnvironmentFile
// /etc/ashfall-promo/app.env in production). Nothing secret has a default.
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const APP_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/** @param {string|undefined} v @param {number} d */
function int(v, d) {
  if (v === undefined || v === '') return d;
  const n = Number.parseInt(v, 10);
  if (!Number.isFinite(n)) throw new Error(`Invalid integer config value: ${v}`);
  return n;
}

/** @param {string|undefined} v @param {boolean} d */
function bool(v, d) {
  if (v === undefined || v === '') return d;
  if (/^(1|true|yes|on)$/i.test(v)) return true;
  if (/^(0|false|no|off)$/i.test(v)) return false;
  throw new Error(`Invalid boolean config value: ${v}`);
}

/**
 * @typedef {object} Config
 * @property {string} host
 * @property {number} port
 * @property {string} publicOrigin canonical origin, e.g. https://ashfall.teknetik.co
 * @property {string} dbPath
 * @property {string} distDir
 * @property {string} clientIpHeader header set authoritatively by the trusted loopback proxy ('' = use socket address)
 * @property {boolean} signupEnabled
 * @property {string} signupInviteCode optional shared invite code (empty = open signup)
 * @property {string} tlsCert optional PEM path; when set with tlsKey the server listens with HTTPS (QA harness)
 * @property {string} tlsKey
 * @property {number} scryptN
 * @property {number} sessionDays
 * @property {boolean} logRequests
 * @property {number} signupPerIpHour
 * @property {boolean} testMode enables nothing user-visible; only relaxes nothing security-related (reserved)
 */

/** @returns {Config} */
export function loadConfig(env = process.env) {
  const publicOrigin = (env.ASHFALL_PUBLIC_ORIGIN || '').replace(/\/$/, '');
  if (!publicOrigin) throw new Error('ASHFALL_PUBLIC_ORIGIN is required (e.g. https://ashfall.teknetik.co)');
  const u = new URL(publicOrigin);
  if (u.protocol !== 'https:') throw new Error('ASHFALL_PUBLIC_ORIGIN must be an https:// origin; cookies are always Secure');
  if (u.pathname !== '/' || u.search || u.hash) throw new Error('ASHFALL_PUBLIC_ORIGIN must be a bare origin');
  const dbPath = env.ASHFALL_DB_PATH || '';
  if (!dbPath) throw new Error('ASHFALL_DB_PATH is required (e.g. /var/lib/ashfall-promo/community.sqlite)');
  const host = env.ASHFALL_HOST || '127.0.0.1';
  const cfg = {
    host,
    port: int(env.ASHFALL_PORT, 3187),
    publicOrigin: u.origin,
    dbPath: path.resolve(dbPath),
    distDir: path.resolve(env.ASHFALL_DIST_DIR || path.join(APP_ROOT, 'dist')),
    clientIpHeader: (env.ASHFALL_CLIENT_IP_HEADER || '').toLowerCase(),
    signupEnabled: bool(env.ASHFALL_SIGNUP_ENABLED, true),
    signupInviteCode: env.ASHFALL_SIGNUP_INVITE_CODE || '',
    tlsCert: env.ASHFALL_TLS_CERT || '',
    tlsKey: env.ASHFALL_TLS_KEY || '',
    scryptN: int(env.ASHFALL_SCRYPT_N, 32768),
    sessionDays: int(env.ASHFALL_SESSION_DAYS, 30),
    logRequests: bool(env.ASHFALL_LOG_REQUESTS, true),
    signupPerIpHour: int(env.ASHFALL_SIGNUP_PER_IP_HOUR, 10),
    testMode: false,
  };
  if (cfg.scryptN < 16384 || (cfg.scryptN & (cfg.scryptN - 1)) !== 0) throw new Error('ASHFALL_SCRYPT_N must be a power of two >= 16384');
  if (cfg.sessionDays < 1 || cfg.sessionDays > 90) throw new Error('ASHFALL_SESSION_DAYS must be 1..90');
  if (!['127.0.0.1', '::1', 'localhost'].includes(host) && !bool(env.ASHFALL_ALLOW_NON_LOOPBACK, false)) {
    throw new Error('Refusing to bind a non-loopback address; the app must sit behind the loopback proxy');
  }
  if (cfg.clientIpHeader && !/^[a-z0-9-]+$/.test(cfg.clientIpHeader)) throw new Error('ASHFALL_CLIENT_IP_HEADER must be a header name');
  if (cfg.signupInviteCode && cfg.signupInviteCode.length < 12) throw new Error('ASHFALL_SIGNUP_INVITE_CODE must be at least 12 characters when set');
  return cfg;
}
