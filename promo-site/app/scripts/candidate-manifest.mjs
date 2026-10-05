// Candidate manifest + release package.
// Hashes (SHA-256) every app source file, the content/design inputs the build consumed, and every
// built file under dist/. Derives a release id from those hashes, writes dist/RELEASE, and packs the
// runtime (server/ + dist/ + package.json + deploy/ + docs) into release/ashfall-promo-<id>.tar.gz.
// Usage: npm run build && node scripts/candidate-manifest.mjs
// Outputs (all under app/release/): MANIFEST.json, SHA256SUMS, ashfall-promo-<id>.tar.gz(.sha256)
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SITE = path.resolve(APP, '..');
const DIST = path.join(APP, 'dist');
const OUT = path.join(APP, 'release');

const sha = (buf) => crypto.createHash('sha256').update(buf).digest('hex');
/** @param {string} dir @returns {string[]} sorted relative file paths */
function walk(dir, base = dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(p, base));
    else if (e.isFile()) out.push(path.relative(base, p));
  }
  return out.sort();
}
/** @param {string} root @param {string[]} rels */
const hashList = (root, rels) => rels.map((r) => ({ path: r, sha256: sha(fs.readFileSync(path.join(root, r))), bytes: fs.statSync(path.join(root, r)).size }));

if (!fs.existsSync(path.join(DIST, 'content.json'))) { console.error('dist/ missing: run "npm run build" first'); process.exit(1); }

// 1. App source (everything tracked by intent; never node_modules, dist, evidence, release).
const SRC_DIRS = ['server', 'client', 'scripts', 'test', 'deploy'];
const SRC_FILES = ['package.json', 'package-lock.json', 'eslint.config.js', 'tsconfig.json', 'README.md', 'RUNBOOK.md', '.gitignore'];
const srcRels = [...SRC_DIRS.flatMap((d) => walk(path.join(APP, d)).map((r) => path.join(d, r))), ...SRC_FILES.filter((f) => fs.existsSync(path.join(APP, f)))].sort();
const source = hashList(APP, srcRels);

// 2. Inputs consumed by the build (read-only, owned by upstream cards).
const inputRels = ['content/WEBSITE_COPY.md', 'content/DEVELOPMENT.json', 'assets/manifest.json', 'design/DESIGN.md', 'ops/PREFLIGHT.md', 'PROJECT_BRIEF.md'].filter((f) => fs.existsSync(path.join(SITE, f)));
const manifest = JSON.parse(fs.readFileSync(path.join(SITE, 'assets/manifest.json'), 'utf8'));
const webRels = walk(path.join(SITE, 'assets', 'web')).map((r) => path.join('assets', 'web', r));
const inputs = hashList(SITE, [...inputRels, ...webRels]);

// 3. Built output (excluding RELEASE, which is derived from these hashes).
const distRels = walk(DIST).filter((r) => r !== 'RELEASE');
const dist = hashList(DIST, distRels);

const digest = (list) => sha(list.map((f) => `${f.sha256}  ${f.path}\n`).join(''));
const sourceDigest = digest(source);
const inputsDigest = digest(inputs);
const distDigest = digest(dist);
const releaseId = `${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${sha(sourceDigest + inputsDigest + distDigest).slice(0, 12)}`;
fs.writeFileSync(path.join(DIST, 'RELEASE'), `${releaseId}\n`);

// 4. Runtime package: what goes to /srv/ashfall-promo/releases/<id>/. No node_modules are needed at runtime.
fs.mkdirSync(OUT, { recursive: true });
for (const f of fs.readdirSync(OUT)) fs.rmSync(path.join(OUT, f), { recursive: true, force: true });
const pkgRels = ['server', 'dist', 'deploy', 'package.json', 'README.md', 'RUNBOOK.md'].filter((f) => fs.existsSync(path.join(APP, f)));
const tarName = `ashfall-promo-${releaseId}.tar.gz`;
const tarPath = path.join(OUT, tarName);
execFileSync('tar', ['--sort=name', '--owner=0', '--group=0', '--numeric-owner', '--mtime=@0', '--mode=go-w',
  '--transform', `s,^,ashfall-promo-${releaseId}/,`, '-czf', tarPath, '-C', APP, ...pkgRels], { stdio: 'inherit' });
const tarSha = sha(fs.readFileSync(tarPath));
fs.writeFileSync(`${tarPath}.sha256`, `${tarSha}  ${tarName}\n`);

let git;
try {
  const head = execFileSync('git', ['-C', SITE, 'rev-parse', 'HEAD'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  const tracked = execFileSync('git', ['-C', SITE, 'ls-files', '--', 'promo-site'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  git = { repoHead: head, promoSiteTracked: tracked.length > 0, note: tracked.length ? 'see git status' : 'promo-site is untracked in the parent repo; file hashes below are the identity' };
} catch { git = null; }

const pkg = JSON.parse(fs.readFileSync(path.join(APP, 'package.json'), 'utf8'));
const out = {
  releaseId,
  generatedAt: new Date().toISOString(),
  node: process.version,
  package: { name: pkg.name, version: pkg.version },
  git,
  digests: { source: sourceDigest, inputs: inputsDigest, dist: distDigest },
  runtimePackage: { file: tarName, sha256: tarSha, bytes: fs.statSync(tarPath).size, contains: pkgRels, runtimeNpmDependencies: Object.keys(pkg.dependencies || {}) },
  assetsManifestEntries: Array.isArray(manifest.assets) ? manifest.assets.length : Object.keys(manifest.assets || manifest).length,
  counts: { source: source.length, inputs: inputs.length, dist: dist.length },
  source, inputs, dist,
};
fs.writeFileSync(path.join(OUT, 'MANIFEST.json'), JSON.stringify(out, null, 2));
const sums = [
  ...source.map((f) => `${f.sha256}  app/${f.path}`),
  ...inputs.map((f) => `${f.sha256}  ${f.path}`),
  ...dist.map((f) => `${f.sha256}  app/dist/${f.path}`),
  `${tarSha}  app/release/${tarName}`,
].join('\n');
fs.writeFileSync(path.join(OUT, 'SHA256SUMS'), `${sums}\n`);
console.log(JSON.stringify({ releaseId, tar: path.relative(SITE, tarPath), tarSha256: tarSha, counts: out.counts, digests: out.digests }, null, 2));
