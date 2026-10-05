import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { APP } from '../helpers.mjs';
import { stripEditorial, parseCopy, parseRail, COPY_CORRECTIONS } from '../../scripts/lib/content.mjs';
import { inline, escapeHtml, renderMarkdown } from '../../scripts/lib/markdown.mjs';

const COPY = fs.readFileSync(path.join(APP, '../content/WEBSITE_COPY.md'), 'utf8');
const DIST = path.join(APP, 'dist');

test('editorial > src: lines are stripped entirely', () => {
  const s = stripEditorial('a\n> src: CN L1\n> continued\nb\n> quote that is not src\n');
  assert.equal(s, 'a\nb\n> quote that is not src\n');
  const parsed = JSON.stringify(parseCopy(COPY));
  assert.ok(!/src:/.test(parsed));
  assert.ok(!/\[Implementer/.test(parsed));
});

test('boss-requested correction applied: no "playable factions"', () => {
  assert.equal(COPY_CORRECTIONS.length, 1);
  const c = parseCopy(COPY);
  const rail = parseRail(c.chapters.ward.fields['status rail']);
  assert.ok(rail.some((r) => /cultures and institutions/.test(r.label)));
  assert.ok(!/playable/i.test(JSON.stringify(c)));
});

test('content parse is complete: chapters, 23 atlas regions, 10 topics, FAQ', () => {
  const c = parseCopy(COPY);
  for (const k of ['world', 'ward', 'opening', 'lattice', 'build', 'machines', 'companions', 'jacks', 'testing']) assert.ok(c.chapters[k].body.length > 1, k);
  const regions = c.atlas.groups.flatMap((g) => g.regions);
  assert.equal(regions.length, 23);
  const build = regions.filter((r) => r.status.kind === 'build').map((r) => r.name);
  assert.deepEqual(build, ['Ward', 'The Outer Berms']);
  assert.ok(regions.filter((r) => r.status.kind === 'planned').length === 21);
  assert.equal(c.topics.length, 10);
  assert.ok(c.faq.length >= 17);
});

test('status rails classify build vs planned explicitly', () => {
  const c = parseCopy(COPY);
  const items = parseRail(c.chapters.build.fields['status rail']);
  const byKind = (k) => items.filter((x) => x.badge.kind === k).map((x) => x.label);
  assert.ok(byKind('build')[0].startsWith('Modular scrap pistol'));
  assert.ok(byKind('build').some((l) => l.startsWith('Early character sheet')), 'the 1 Oct character sheet is in build');
  assert.ok(byKind('planned').some((l) => /trickle-down progression and implant effects/.test(l)), 'the designed system stays planned');
  assert.deepEqual(byKind('exploring'), ['Walk-in crafting tutorial']);
  const comp = parseRail(c.chapters.companions.fields['status rail']);
  assert.equal(comp[0].badge.kind, 'planned');
});

test('markdown inline escapes before formatting', () => {
  assert.equal(inline('**<b>x</b>**'), '<strong>&lt;b&gt;x&lt;/b&gt;</strong>');
  assert.equal(escapeHtml(`"'<>&`), '&quot;&#39;&lt;&gt;&amp;');
  assert.ok(renderMarkdown('```lattice\n<x>\n```').includes('&lt;x&gt;'));
});

test('built output has no spoilers, editorial or internal files exposed', () => {
  assert.ok(fs.existsSync(path.join(DIST, 'content.json')), 'run npm run build first');
  const banned = [/src:/i, /SOURCE_INVENTORY/, /quarantin/i, /ghost network/i, /authority node/i, /rejoin/i, /deliberately disconnected/i, /playable faction/i, /\[Implementer/];
  const text = fs.readFileSync(path.join(DIST, 'content.json'), 'utf8');
  for (const re of banned) assert.ok(!re.test(text), String(re));
  const pub = [];
  const walk = (d) => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const f = path.join(d, e.name); if (e.isDirectory()) walk(f); else pub.push(path.relative(path.join(DIST, 'public'), f)); } };
  walk(path.join(DIST, 'public'));
  assert.ok(pub.every((f) => /^(img\/.+\.(avif|webp|jpg)|img\/ashfall-desert-emblem\.[0-9a-f]{10}\.png|fonts\/.+\.(woff2|txt)|site\.[0-9a-f]{10}\.(css|js)|favicon\.svg)$/.test(f)), `unexpected public file: ${pub.find((f) => !/^(img|fonts)\//.test(f) && !/^site\./.test(f) && f !== 'favicon.svg')}`);
  assert.ok(!pub.some((f) => /originals|\.md$|\.json$|\.sqlite/.test(f) || (f.endsWith('.png') && !/^img\/ashfall-desert-emblem\.[0-9a-f]{10}\.png$/.test(f))));
});

test('every manifest asset is published with all formats and its label', () => {
  const site = JSON.parse(fs.readFileSync(path.join(DIST, 'content.json'), 'utf8'));
  const manifest = JSON.parse(fs.readFileSync(path.join(APP, '../assets/manifest.json'), 'utf8'));
  assert.equal(Object.keys(site.assets).length, manifest.assets.length);
  for (const a of manifest.assets) {
    const pub = site.assets[a.id];
    assert.ok(pub, a.id);
    assert.equal(pub.label, a.label);
    for (const v of pub.variants) for (const f of ['avif', 'webp', 'jpg']) {
      const file = path.join(DIST, 'public', v[f]);
      assert.ok(fs.statSync(file).size > 0, file);
    }
  }
});
