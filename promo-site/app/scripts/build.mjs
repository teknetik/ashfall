// Reproducible build: reads the read-only inputs (../content, ../assets) and writes app/dist/.
// dist/public is the ONLY directory served as static files; it contains web image variants,
// fonts, CSS and JS. Originals, manifests, editorial copy, inventory, ops and DB are never copied there.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { buildContent } from './lib/render-content.mjs';
import { buildDevelopment } from './lib/development.mjs';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SITE = path.resolve(APP, '..');
const DIST = path.join(APP, 'dist');
const PUB = path.join(DIST, 'public');

const sha = (buf) => crypto.createHash('sha256').update(buf).digest('hex');

fs.rmSync(DIST, { recursive: true, force: true });
fs.mkdirSync(path.join(PUB, 'img'), { recursive: true });
fs.mkdirSync(path.join(PUB, 'fonts'), { recursive: true });

// 1. Assets: verify every manifest variant hash, copy with content hash in the name.
const manifest = JSON.parse(fs.readFileSync(path.join(SITE, 'assets/manifest.json'), 'utf8'));
const KIND = { 'generated-concept': 'concept', 'existing-concept': 'concept', 'build-screenshot': 'build' };
/** @type {Record<string, any>} */
const assets = {};
for (const a of manifest.assets) {
  const byWidth = new Map();
  for (const v of a.web_variants) {
    const src = path.join(SITE, 'assets', v.file);
    const buf = fs.readFileSync(src);
    if (sha(buf) !== v.sha256) throw new Error(`Asset hash mismatch: ${v.file}`);
    if (buf.length === 0) throw new Error(`Empty asset: ${v.file}`);
    const ext = path.extname(v.file);
    const name = `${path.basename(v.file, ext)}.${v.sha256.slice(0, 10)}${ext}`;
    fs.writeFileSync(path.join(PUB, 'img', name), buf);
    const key = v.width;
    if (!byWidth.has(key)) byWidth.set(key, { width: v.width, height: v.height });
    byWidth.get(key)[v.format === 'jpeg' ? 'jpg' : v.format] = `/img/${name}`;
  }
  const variants = [...byWidth.values()].sort((x, y) => x.width - y.width);
  for (const v of variants) if (!v.avif || !v.webp || !v.jpg) throw new Error(`Incomplete variant set for ${a.id} @${v.width}`);
  const kind = KIND[a.category] || 'concept';
  assets[a.id] = {
    id: a.id, title: a.title, alt: a.alt, caption: a.caption, label: a.label,
    kind, category: a.category, planned: /planned/i.test(a.label) || a.id === 'tir-world-map', variants,
  };
}
for (const [id, a] of Object.entries(assets)) {
  if (a.kind === 'build' && !/build capture/i.test(a.label)) throw new Error(`Build capture ${id} must carry an in-build label`);
  if (a.kind === 'concept' && !/^Concept/i.test(a.label)) throw new Error(`Concept ${id} must carry a concept label`);
}

// User-supplied brand artwork, preserved byte-for-byte with a cache-safe URL.
const logo = fs.readFileSync(path.join(APP, 'client/brand/ashfall-desert-emblem.png'));
const logoName = `ashfall-desert-emblem.${sha(logo).slice(0, 10)}.png`;
fs.writeFileSync(path.join(PUB, 'img', logoName), logo);
const logoUrl = `/img/${logoName}`;

// 2. Fonts (SIL OFL), self-hosted.
const FONTS = [
  ['@fontsource-variable/fraunces/files/fraunces-latin-full-normal.woff2', 'fraunces.woff2'],
  ['@fontsource-variable/source-sans-3/files/source-sans-3-latin-wght-normal.woff2', 'source-sans-3.woff2'],
  ['@fontsource-variable/source-sans-3/files/source-sans-3-latin-wght-italic.woff2', 'source-sans-3-italic.woff2'],
  ['@fontsource/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff2', 'jetbrains-mono-400.woff2'],
  ['@fontsource/jetbrains-mono/files/jetbrains-mono-latin-500-normal.woff2', 'jetbrains-mono-500.woff2'],
];
/** @type {Record<string,string>} */
const fontUrls = {};
for (const [src, name] of FONTS) {
  const buf = fs.readFileSync(path.join(APP, 'node_modules', src));
  const out = name.replace('.woff2', `.${sha(buf).slice(0, 10)}.woff2`);
  fs.writeFileSync(path.join(PUB, 'fonts', out), buf);
  fontUrls[name] = `/fonts/${out}`;
}
const licences = ['@fontsource-variable/fraunces', '@fontsource-variable/source-sans-3', '@fontsource/jetbrains-mono']
  .map((p) => `=== ${p} ===\n${fs.readFileSync(path.join(APP, 'node_modules', p, 'LICENSE'), 'utf8')}`).join('\n\n');
fs.writeFileSync(path.join(PUB, 'fonts', 'LICENSES.txt'), licences);

// 3. Content.
const copy = fs.readFileSync(path.join(SITE, 'content/WEBSITE_COPY.md'), 'utf8');
const content = buildContent(copy, assets);
const devJson = fs.readFileSync(path.join(SITE, 'content/DEVELOPMENT.json'), 'utf8');
content.development = buildDevelopment(JSON.parse(devJson), assets);
const buildInfo = {
  builtAt: new Date().toISOString(),
  copySha256: sha(copy),
  developmentSha256: sha(devJson),
  manifestSha256: sha(fs.readFileSync(path.join(SITE, 'assets/manifest.json'))),
};

fs.writeFileSync(path.join(PUB, 'favicon.svg'), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#14110e"/><rect x="9" y="9" width="14" height="14" fill="none" stroke="#c8a15a" stroke-width="3" transform="rotate(45 16 16)"/><circle cx="16" cy="16" r="2.5" fill="#5fd3d0"/></svg>');

// 4. CSS + JS, content-hashed.
let css = fs.readFileSync(path.join(APP, 'client/site.css'), 'utf8');
for (const [name, url] of Object.entries(fontUrls)) css = css.replaceAll(`__FONT_${name}__`, url);
if (/__FONT_/.test(css)) throw new Error('Unresolved font placeholder in CSS');
css += `\n/* atlas hotspots (generated) */\n${content.atlas.spotsCss}\n`;
const bundles = {};
for (const [file, content] of [['site.css', css], ['site.js', fs.readFileSync(path.join(APP, 'client/site.js'), 'utf8')]]) {
  const ext = path.extname(file);
  const out = `${path.basename(file, ext)}.${sha(content).slice(0, 10)}${ext}`;
  fs.writeFileSync(path.join(PUB, out), content);
  bundles[file] = `/${out}`;
}

// og:image: 1200x630 crop from the hero, generated deterministically with ImageMagick if available,
// otherwise fall back to the 1536 hero JPEG (still concept art, still labelled in og:image:alt).
const heroJpg = path.join(SITE, 'assets/web/ashfall-ward-hero-1536.jpg');
let ogUrl = assets['ashfall-ward-hero'].variants.at(-1).jpg;
try {
  const { execFileSync } = await import('node:child_process');
  const tmp = path.join(DIST, 'og.jpg');
  execFileSync('magick', [heroJpg, '-resize', '1200x', '-gravity', 'center', '-crop', '1200x630+0+0', '+repage', '-strip', '-quality', '82', tmp], { stdio: 'ignore' });
  const buf = fs.readFileSync(tmp);
  const name = `og-ashfall.${sha(buf).slice(0, 10)}.jpg`;
  fs.renameSync(tmp, path.join(PUB, 'img', name));
  ogUrl = `/img/${name}`;
} catch {
  console.warn('[build] ImageMagick unavailable; og:image uses the hero JPEG');
}

fs.writeFileSync(path.join(DIST, 'content.json'), JSON.stringify({ content, assets, bundles, fonts: fontUrls, ogUrl, logoUrl, buildInfo }));

// 5. Guard: no editorial/internal material in anything we produced.
const BANNED = [
  /> ?src:/i, /SOURCE_INVENTORY/, /\[Implementer/i, /playable faction/i,
  // spoiler register (DESIGN §9 / inventory §5)
  /deliberately disconnected/i, /quarantin/i, /ghost network/i, /authority node/i, /authority level/i,
  /rejoin/i, /nervous system of something/i, /route 00/i, /planetary (machine )?intelligence/i, /true collapse/i,
  /reconnect it\?/i, /buried inside the player/i, /what they have just connected/i,
];
const scan = (p) => {
  for (const f of fs.readdirSync(p, { withFileTypes: true })) {
    const fp = path.join(p, f.name);
    if (f.isDirectory()) { scan(fp); continue; }
    if (!/\.(json|css|js|html|txt)$/.test(f.name) || f.name === 'LICENSES.txt') continue;
    const t = fs.readFileSync(fp, 'utf8');
    for (const re of BANNED) if (re.test(t)) throw new Error(`Banned/internal text ${re} found in ${path.relative(APP, fp)}`);
  }
};
scan(DIST);
const files = fs.readdirSync(path.join(PUB, 'img')).length;
console.log(`[build] ok: ${Object.keys(assets).length} assets (${files} image files), ${content.chapters.length} chapters, ${content.atlas.regionCount} regions, ${content.topics.length} topics, ${content.faq.length} FAQ, development log ${content.development.updated} (${content.development.timeline.length} entries, ${content.development.pairs.length} pairs)`);

// 6. Structural guard: every placed component and figure is present exactly where expected.
{
  const byId = Object.fromEntries(content.chapters.map((c) => [c.id, c.bodyHtml + c.leadHtml]));
  const expect = [
    ['lattice', 'class="capacity"'], ['build', 'class="slots"'], ['companions', 'class="ladder"'],
    ['ward', 'data-asset="build-ward-hill-20261001"'], ['ward', 'data-asset="ward-vanguard-hall-concept"'],
    ['build', 'data-asset="build-field-pack-20261001"'], ['world', 'data-asset="tir-world-map"'],
    ['opening', 'data-asset="ashfall-nano-infirmary-awakening"'], ['machines', 'data-asset="ashfall-first-signal-node"'],
    ['machines', 'data-asset="outer-berms-depot-concept"'], ['companions', 'data-asset="ashfall-companion-recovery"'],
  ];
  for (const [id, needle] of expect) if (!byId[id].includes(needle)) throw new Error(`Chapter ${id} is missing ${needle}`);
  if (/@@/.test(JSON.stringify(content))) throw new Error('Unresolved content placeholder');
}
