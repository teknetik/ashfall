// Test helpers: spawn an isolated server (temp DB, temp self-signed TLS) and a tiny cookie-aware HTTP client.
// Nothing here touches real user data; every run uses a fresh mkdtemp directory that is deleted afterwards.
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import https from 'node:https';
import http from 'node:http';
import net from 'node:net';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

export const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const ORIGIN = 'https://ashfall.teknetik.co';
export const HOST = 'ashfall.teknetik.co';

/** Random disposable credentials; never printed. */
export function genUser(prefix = 't') {
  return { username: `${prefix}_${crypto.randomBytes(5).toString('hex')}`.slice(0, 24), password: `pw-${crypto.randomBytes(18).toString('base64url')}` };
}

export async function freePort() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.listen(0, '127.0.0.1', () => {
      const { port } = /** @type {net.AddressInfo} */ (s.address());
      s.close(() => resolve(port));
    });
    s.on('error', reject);
  });
}

/** Self-signed cert for the canonical host so Secure cookies work end-to-end over real TLS. */
export function makeCert(dir) {
  const key = path.join(dir, 'key.pem');
  const cert = path.join(dir, 'cert.pem');
  execFileSync('openssl', ['req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:prime256v1', '-nodes', '-keyout', key, '-out', cert, '-days', '2',
    '-subj', `/CN=${HOST}`, '-addext', `subjectAltName=DNS:${HOST},IP:127.0.0.1`], { stdio: 'ignore' });
  return { key, cert };
}

/**
 * Start the real production entrypoint with an isolated DB.
 * @param {{tls?: boolean, env?: Record<string,string>, dir?: string, port?: number}} [o]
 */
export async function startServer(o = {}) {
  const dir = o.dir || fs.mkdtempSync(path.join(os.tmpdir(), 'ashfall-test-'));
  const port = o.port || await freePort();
  const tls = o.tls !== false;
  const certs = tls ? (fs.existsSync(path.join(dir, 'cert.pem')) ? { key: path.join(dir, 'key.pem'), cert: path.join(dir, 'cert.pem') } : makeCert(dir)) : null;
  const env = {
    PATH: process.env.PATH,
    ASHFALL_PUBLIC_ORIGIN: ORIGIN,
    ASHFALL_DB_PATH: path.join(dir, 'community.sqlite'),
    ASHFALL_PORT: String(port),
    ASHFALL_HOST: '127.0.0.1',
    ASHFALL_SCRYPT_N: '16384',
    ASHFALL_LOG_REQUESTS: 'true',
    ASHFALL_SIGNUP_PER_IP_HOUR: '1000',
    ...(certs ? { ASHFALL_TLS_CERT: certs.cert, ASHFALL_TLS_KEY: certs.key } : {}),
    ...(o.env || {}),
  };
  const child = spawn(process.execPath, ['server/index.mjs'], { cwd: APP, env, stdio: ['ignore', 'pipe', 'pipe'] });
  let logs = '';
  child.stdout.on('data', (d) => { logs += d; });
  child.stderr.on('data', (d) => { logs += d; });
  const deadline = Date.now() + 10_000;
  while (!/listening/.test(logs)) {
    if (child.exitCode !== null) throw new Error(`server exited early: ${logs}`);
    if (Date.now() > deadline) { child.kill(); throw new Error(`server did not start: ${logs}`); }
    await new Promise((r) => setTimeout(r, 50));
  }
  return {
    dir, port, tls: !!certs, child, env,
    get logs() { return logs; },
    base: `${certs ? 'https' : 'http'}://127.0.0.1:${port}`,
    async stop() {
      if (child.exitCode !== null) return;
      const done = new Promise((r) => child.once('exit', r));
      child.kill('SIGTERM');
      await done;
    },
    cleanup() { fs.rmSync(dir, { recursive: true, force: true }); },
  };
}

/** Cookie jar client that speaks to the server as the public host. */
export class Client {
  constructor(server) {
    this.server = server;
    /** @type {Map<string,string>} */
    this.jar = new Map();
    /** @type {string[]} */
    this.setCookies = [];
  }

  /**
   * @param {string} method
   * @param {string} p
   * @param {{form?: Record<string,string>|URLSearchParams, headers?: Record<string,string>, body?: string|Buffer, origin?: string|null}} [o]
   */
  request(method, p, o = {}) {
    const lib = this.server.tls ? https : http;
    /** @type {Record<string, string>} */
    const headers = { Host: HOST, ...(o.headers || {}) };
    let body = o.body;
    if (o.form) {
      body = (o.form instanceof URLSearchParams ? o.form : new URLSearchParams(o.form)).toString();
      headers['Content-Type'] = headers['Content-Type'] || 'application/x-www-form-urlencoded';
    }
    if (method === 'POST' && o.origin !== null && !('Origin' in headers)) headers.Origin = o.origin || ORIGIN;
    if (this.jar.size) headers.Cookie = [...this.jar].map(([k, v]) => `${k}=${v}`).join('; ');
    if (body !== undefined) headers['Content-Length'] = String(Buffer.byteLength(body));
    return new Promise((resolve, reject) => {
      const req = lib.request({ host: '127.0.0.1', port: this.server.port, method, path: p, headers, servername: HOST, rejectUnauthorized: false }, (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const sc = res.headers['set-cookie'] || [];
          this.setCookies = sc;
          for (const c of sc) {
            const [kv] = c.split(';');
            const i = kv.indexOf('=');
            const k = kv.slice(0, i).trim();
            const v = kv.slice(i + 1).trim();
            if (/Max-Age=0/i.test(c) || v === '') this.jar.delete(k); else this.jar.set(k, v);
          }
          resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks).toString('utf8'), raw: Buffer.concat(chunks) });
        });
      });
      req.on('error', reject);
      if (body !== undefined) req.write(body);
      req.end();
    });
  }

  get(p, o) { return this.request('GET', p, o); }

  post(p, form, o = {}) { return this.request('POST', p, { ...o, form }); }

  /** Fetch a page and return the CSRF token embedded in its first form. */
  async csrf(p) {
    const r = await this.get(p);
    const m = /name="_csrf" value="([^"]+)"/.exec(r.body);
    if (!m) throw new Error(`no csrf token on ${p} (status ${r.status})`);
    return m[1];
  }

  async join(user, extra = {}) {
    const t = await this.csrf('/join');
    return this.post('/join', { _csrf: t, username: user.username, password: user.password, confirm: user.password, privacy: 'yes', ...extra });
  }

  async login(user) {
    const t = await this.csrf('/login');
    return this.post('/login', { _csrf: t, username: user.username, password: user.password });
  }
}

/** Run the operator CLI against a test server's DB. */
export function cli(server, ...args) {
  return execFileSync(process.execPath, ['server/cli.mjs', ...args], { cwd: APP, env: server.env, encoding: 'utf8' });
}
