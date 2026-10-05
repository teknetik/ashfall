// Build-time rendering of editorial content into HTML fragments (dist/content.json).
// Runs only on trusted inputs (content/WEBSITE_COPY.md, assets/manifest.json).
import { parseCopy, parseRail, renderBlocks, inline, escapeHtml, badgeHtml } from './content.mjs';
import { blocks as blocksOf } from './markdown.mjs';

/** Approximate hotspot positions (% of the concept map). Placement is indicative, as the map caption says. */
export const MAP_SPOTS = {
  ward: [68.6, 49.4], 'outer-berms': [70.4, 57.5], 'salt-expanse': [53.9, 37.8], 'dune-wastes': [39.4, 48.3],
  'ariden-plateau': [21.4, 48.8], 'bleached-flats': [39.4, 60.8], 'verdant-fold': [13.8, 60.8], 'blooming-keys': [7.6, 88.4],
  'glass-coast': [17.3, 29.5], 'shattered-spine': [27.6, 13.3], 'frostbite-reach': [64.9, 7.7], 'iron-grave': [47, 19.3],
  'ashfall-basin': [69, 23], 'neon-dominion': [90.5, 38.7], 'nexus-prime': [95, 45], 'shimmer-isles': [91.2, 56.2],
  'fractured-isles': [89.1, 21.2], 'broken-teeth': [89.8, 81], 'sundered-delta': [71.8, 78.3], 'sunscar-reach': [40.7, 78.3],
  'stormreach-sea': [6.2, 35], 'viridian-sea': [6.2, 76.4], 'cobalt-deep': [93.9, 72.7],
};

/**
 * @param {any} asset manifest entry (with public variant URLs)
 * @param {{sizes?: string, cls?: string, eager?: boolean, set?: string, badgeHtml?: string}} [o]
 */
export function figureHtml(asset, o = {}) {
  const largest = asset.variants[asset.variants.length - 1];
  const pic = pictureHtml(asset, { sizes: o.sizes || '(min-width: 1200px) 1120px, 100vw', eager: o.eager });
  const label = `<span class="badge badge--${asset.kind}">${escapeHtml(asset.label)}</span>`;
  return `<figure class="fig ${o.cls || ''}" data-asset="${escapeHtml(asset.id)}">
  <a class="fig__link" href="${largest.jpg}" data-lightbox="${escapeHtml(o.set || 'page')}" data-id="${escapeHtml(asset.id)}" aria-label="Enlarge image: ${escapeHtml(asset.title)}">${pic}</a>
  <div class="fig__badge">${label}</div>
  <figcaption><span class="fig__title">${escapeHtml(asset.title)}.</span> ${escapeHtml(asset.caption)}</figcaption>
</figure>`;
}

/** @param {any} asset @param {{sizes?: string, eager?: boolean, cls?: string}} o */
export function pictureHtml(asset, o = {}) {
  const v = asset.variants;
  const set = (fmt) => v.map((x) => `${x[fmt]} ${x.width}w`).join(', ');
  const small = v[0];
  const big = v[v.length - 1];
  const loading = o.eager ? 'loading="eager" fetchpriority="high"' : 'loading="lazy" decoding="async"';
  return `<picture><source type="image/avif" srcset="${set('avif')}" sizes="${o.sizes}"><source type="image/webp" srcset="${set('webp')}" sizes="${o.sizes}"><img src="${o.eager ? big.jpg : small.jpg}" srcset="${set('jpg')}" sizes="${o.sizes}" width="${big.width}" height="${big.height}" alt="${escapeHtml(asset.alt)}" ${loading}${o.cls ? ` class="${o.cls}"` : ''}></picture>`;
}

/** @param {ReturnType<typeof parseRail>} items @param {string} id */
function railHtml(items, id) {
  if (!items.length) return '';
  const build = items.filter((x) => x.badge.kind === 'build');
  const other = items.filter((x) => x.badge.kind !== 'build');
  const list = (arr) => `<ul class="rail__list">${arr.map((x) => `<li>${badgeHtml(x.badge)}<span>${x.labelHtml}</span></li>`).join('')}</ul>`;
  return `<aside class="rail" aria-labelledby="${id}-rail-h"><details class="rail__details" open><summary id="${id}-rail-h" class="rail__title">Status: what exists and what is planned</summary>
  ${build.length ? `<p class="rail__group">In the build today</p>${list(build)}` : ''}
  ${other.length ? `<p class="rail__group">Planned or exploring</p>${list(other)}` : ''}
  </details></aside>`;
}

function capacityExplainer(caption) {
  /** @type {Array<[string, string, number]>} */
  const mods = [
    ['mapping', 'Mapping', 10], ['item', 'Item analysis', 10], ['craft', 'Crafting assistant', 15],
    ['threat', 'Threat analysis', 30], ['env', 'Environmental scanner', 20], ['machine', 'Machine communication', 20],
  ];
  /** @type {Array<[string, string, number]>} */
  const comps = [['drone', 'Companion link: maintenance drone', 15], ['recon', 'Companion link: recon unit', 30], ['fab', 'Companion link: industrial fabricator', 55]];
  /** @param {[string, string, number]} m @param {string} type */
  const chip = ([id, label, cost], type) => `<label class="chip"><input type="${type}" ${type === 'radio' ? 'name="cap-companion"' : ''} value="${cost}" data-cap-id="${id}" data-label="${escapeHtml(label)}"><span>${escapeHtml(label)}</span><span class="chip__cost">${cost}</span></label>`;
  return `<section class="capacity" aria-labelledby="cap-h" data-capacity="100">
  <p class="kicker" id="cap-h">Try it: Lattice Capacity</p>
  <div class="capacity__bar" aria-hidden="true"><div class="capacity__fill"></div><span class="capacity__readout">0 / 100</span></div>
  <fieldset class="capacity__chips"><legend>Modules (choose any)</legend>${mods.map((m) => chip(m, 'checkbox')).join('')}</fieldset>
  <fieldset class="capacity__chips"><legend>One major companion</legend><label class="chip"><input type="radio" name="cap-companion" value="0" data-cap-id="none" data-label="No companion" checked><span>No companion</span><span class="chip__cost">0</span></label>${comps.map((m) => chip(m, 'radio')).join('')}</fieldset>
  <p class="capacity__status lattice-line" role="status" aria-live="polite">Using 0 of 100. No modules running.</p>
  <p class="capacity__note">${inline(caption.trim().replace(/^"|"$/g, '')) || 'Illustrative. Module names, costs and capacity are design examples, not final values.'}</p>
</section>`;
}

function weaponSlots() {
  const weapons = [
    { name: 'Scrap pistol', badge: { kind: 'build', text: 'In build' }, note: 'In the current build: grip, barrel and power-cell mods.', slots: ['Barrel', 'Grip', 'Power cell'] },
    { name: 'Corporate pistol', badge: { kind: 'planned', text: 'Planned' }, note: 'Example recipe from the design notes.', slots: ['Barrel', 'Grip', 'Optic', 'Power cell', 'Internal mod'] },
    { name: 'Plasma rifle', badge: { kind: 'planned', text: 'Planned' }, note: 'Example recipe from the design notes.', slots: ['Emitter', 'Stock', 'Optic', 'Power cell', 'Cooling unit', 'Core', 'Internal'] },
  ];
  return `<section class="slots" aria-labelledby="slots-h"><h3 id="slots-h">Weapon recipes own their slots</h3><div class="slots__grid">${weapons
    .map((w) => `<div class="slots__weapon"><p class="slots__name">${escapeHtml(w.name)} ${badgeHtml(w.badge)}</p><ul class="slots__list" aria-label="${escapeHtml(w.name)} modification slots">${w.slots.map((s) => `<li>${escapeHtml(s)}</li>`).join('')}</ul><p class="slots__note">${escapeHtml(w.note)}</p></div>`)
    .join('')}</div></section>`;
}

const INSURANCE = [
  ['No companion', 'The Karaveen find you, and your gear is expensive to reclaim.'],
  ['Basic', 'Transmits your exact location, guards you and saves a little.'],
  ['Cargo', 'Hauls much more and slashes salvage costs.'],
  ['Medical', 'Stabilises severe injuries and can prevent some trauma altogether.'],
  ['Advanced trauma', "May revive you without anyone else's help."],
];

/**
 * Render a chapter body with placeholders resolved.
 * @param {any} ch
 * @param {{id:string, assets: Record<string, any>, figures?: Record<number, string>, lead?: string}} o
 */
function chapterBody(ch, o) {
  const out = [];
  let ladderNext = false;
  let pIndex = 0;
  for (const b of ch.body) {
    const text = b.type === 'p' ? b.lines.join(' ') : '';
    if (b.type === 'p' && text.startsWith('@@PULLQUOTE@@')) {
      const pq = /^"([^"]+)"\s*(.*)$/.exec(ch.fields['pull quote']);
      out.push(`<blockquote class="pull"><p>${inline(pq ? `“${pq[1]}”` : ch.fields['pull quote'])}</p></blockquote>`);
      // Narrative text that follows the quote in the copy is ordinary prose, not part of the quote.
      if (pq && pq[2]) out.push(`<p>${inline(pq[2])}</p>`);
      continue;
    }
    const aside = /^@@ASIDE (\d+) ([^@]*)@@$/.exec(text);
    if (aside) {
      const a = ch.asides[Number(aside[1])];
      const asset = o.assets[aside[2]];
      out.push(`<aside class="inbuild" aria-label="In the build today"><p class="inbuild__kicker">${badgeHtml({ kind: 'build', text: 'In the build today' })}</p><div class="inbuild__grid">${asset ? figureHtml(asset, { sizes: '(min-width: 1024px) 560px, 100vw', set: 'page' }) : ''}<p>${inline(a.value)}</p></div></aside>`);
      continue;
    }
    const comp = /^@@COMPONENT (.+)@@$/.exec(text);
    if (comp) {
      const value = ch.fields[`component:${comp[1]}`] || '';
      if (/capacity/i.test(comp[1])) out.push(capacityExplainer(value.split('Caption:')[1] || ''));
      else if (/recovery/i.test(comp[1])) { out.push(`<p>${inline(value)}</p>`); ladderNext = true; }
      continue;
    }
    if (b.type === 'ol' && ladderNext) {
      ladderNext = false;
      out.push(`<section class="ladder" aria-labelledby="ladder-h"><h4 id="ladder-h" class="kicker">Recovery outcomes, best to worst ${badgeHtml({ kind: 'planned', text: 'Planned' })}</h4><div class="ladder__grid"><ol class="ladder__steps">${b.lines.map((l) => `<li>${inline(l)}</li>`).join('')}</ol><div class="ladder__side"><p class="ladder__side-h">How your companion changes the odds</p><dl>${INSURANCE.map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd>`).join('')}</dl></div></div></section>`);
      continue;
    }
    out.push(renderBlocks([b], { headingLevel: 3 }));
    if (b.type === 'p') {
      pIndex++;
      if (o.figures && o.figures[pIndex]) out.push(o.figures[pIndex]);
    }
  }
  return out.join('\n');
}

/**
 * @param {string} rawCopy
 * @param {Record<string, any>} assets public asset index
 */
export function buildContent(rawCopy, assets) {
  const c = parseCopy(rawCopy);
  const A = assets;
  const fig = (id, o = {}) => figureHtml(A[id], o);
  const full = (id) => fig(id, { cls: 'fig--bleed', sizes: '100vw' });
  const wide = (id) => fig(id, { cls: 'fig--wide' });

  /** chapter specs: id, nav label, topic slug, parchment, lead figure, inline figures by paragraph index */
  const specs = [
    { id: 'world', key: 'world', nav: 'The World', topic: 'world', figures: { 3: wide('tir-world-map') } },
    { id: 'ward', key: 'ward', nav: 'Ward', topic: 'ward', figures: { 1: wide('ward-vanguard-hall-concept') } },
    { id: 'opening', key: 'opening', nav: 'Story', topic: 'opening', lead: full('ashfall-nano-infirmary-awakening') },
    { id: 'lattice', key: 'lattice', nav: 'The Lattice', topic: 'lattice', parchment: true },
    { id: 'build', key: 'build', nav: 'Survive & Build', topic: 'build', parchment: true, extra: weaponSlots(), extraAfter: 6 },
    { id: 'machines', key: 'machines', nav: 'Machines', topic: 'machines', lead: full('ashfall-first-signal-node'), figures: { 3: wide('outer-berms-depot-concept') } },
    { id: 'companions', key: 'companions', nav: 'Companions', topic: 'companions', parchment: true, lead: full('ashfall-companion-recovery') },
    { id: 'jacks', key: 'jacks', nav: null, topic: 'companions', sub: true },
  ];
  const chapters = specs.map((s, i) => {
    const ch = c.chapters[s.key];
    const figures = { ...(s.figures || {}) };
    if (s.extra) figures[s.extraAfter] = (figures[s.extraAfter] || '') + s.extra;
    return {
      id: s.id,
      nav: s.nav,
      topic: s.topic,
      parchment: !!s.parchment,
      sub: !!s.sub,
      number: s.sub ? null : i + 1,
      kicker: ch.fields.kicker || '',
      titleHtml: inline(ch.fields.title || ''),
      title: ch.fields.title || '',
      standfirstHtml: ch.fields.standfirst ? inline(ch.fields.standfirst) : '',
      leadHtml: s.lead || '',
      bodyHtml: chapterBody(ch, { id: s.id, assets: A, figures }),
      railHtml: railHtml(parseRail(ch.fields['status rail']), s.id),
    };
  });

  // Atlas
  const atlas = c.atlas;
  const regionsHtml = atlas.groups.map((g) => `<div class="atlas__group"><h3 class="atlas__group-h">${escapeHtml(g.name)} ${g.status ? badgeHtml(g.status) : ''}</h3>${g.regions
    .map((r) => `<details class="region" id="region-${r.slug}" data-region="${r.slug}"><summary><span class="region__name">${escapeHtml(r.name)}</span>${r.status ? badgeHtml(r.status) : ''}<span class="region__hook">${r.hookHtml}</span></summary><div class="region__body">${r.banner && A[r.banner] ? figureHtml(A[r.banner], { sizes: '(min-width: 1024px) 520px, 100vw', set: 'atlas' }) : ''}<p>${r.bodyHtml}</p></div></details>`)
    .join('')}</div>`).join('');
  const spots = atlas.groups.flatMap((g) => g.regions).map((r) => {
    const p = MAP_SPOTS[r.slug];
    if (!p) throw new Error(`No map hotspot for region ${r.slug}`);
    return `<a class="spot${r.status && r.status.kind === 'build' ? ' spot--build' : ''}" href="#region-${r.slug}" data-region="${r.slug}"><span class="visually-hidden">${escapeHtml(r.name)}</span></a>`;
  }).join('');
  const spotsCss = atlas.groups.flatMap((g) => g.regions).map((r) => `.spot[data-region="${r.slug}"]{left:${MAP_SPOTS[r.slug][0]}%;top:${MAP_SPOTS[r.slug][1]}%}`).join('\n');
  const regionCount = atlas.groups.reduce((n, g) => n + g.regions.length, 0);
  const atlasHtml = {
    kicker: atlas.fields.kicker, title: atlas.fields.title, introHtml: inline(atlas.fields.intro), mapCaption: atlas.fields['map caption'],
    regionsHtml, spots, spotsCss, betweenHtml: atlas.betweenHtml, regionCount,
  };

  const testing = c.chapters.testing;
  const testingHtml = {
    kicker: testing.fields.kicker, titleHtml: inline(testing.fields.title), title: testing.fields.title,
    bodyHtml: renderBlocks(testing.body),
    figuresHtml: `<div class="testing__figs">${fig('build-ward-hill-20261001', { sizes: '(min-width: 1024px) 560px, 100vw', set: 'testing' })}${fig('build-field-pack-20261001', { sizes: '(min-width: 1024px) 560px, 100vw', set: 'testing' })}</div>`,
  };

  return {
    meta: c.meta,
    hero: {
      kicker: c.hero.kicker, title: c.hero.title, premise: c.hero['premise line'], boot: c.hero.boot,
      ctaPrimary: c.hero['cta primary'], ctaSecondary: c.hero['cta secondary'],
    },
    chapters,
    atlas: atlasHtml,
    testing: testingHtml,
    discuss: c.discuss,
    topics: c.topics,
    galleryIntros: c.galleryIntros,
    aboutHtml: renderBlocks(blocksOf(c.about.rest)),
    aboutTitle: c.about.fields.title,
    rulesHtml: renderBlocks(blocksOf(c.rules)),
    faq: c.faq,
  };
}


