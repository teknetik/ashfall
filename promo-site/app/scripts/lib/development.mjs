// /development page data: validates content/DEVELOPMENT.json against the asset map and
// precomputes the passes chart. Text stays plain (views escape it); only the chart SVG is raw.

const STATUSES = { done: 'Done', now: 'In progress', next: 'Next', later: 'Later' };
const DAY = 86400000;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const day = (iso) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) throw new Error(`Development: bad date ${iso}`);
  return Date.parse(`${iso}T00:00:00Z`);
};
const short = (ms) => { const d = new Date(ms); return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`; };
const long = (ms) => { const d = new Date(ms); return `${d.getUTCDate()} ${['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][d.getUTCMonth()]} ${d.getUTCFullYear()}`; };
const attr = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** Bars per day plus a running-total line, sized for a 720×260 viewBox. */
function passesChart(passes, [fromIso, toIso], title, caption) {
  const from = day(fromIso);
  const days = Math.round((day(toIso) - from) / DAY) + 1;
  const counts = new Array(days).fill(0);
  for (const p of passes) {
    const i = Math.round((day(p.date) - from) / DAY);
    if (i < 0 || i >= days || !Number.isInteger(p.count) || p.count < 1) throw new Error(`Development: pass ${p.date} out of range`);
    counts[i] += p.count;
  }
  const total = counts.reduce((a, b) => a + b, 0);
  const W = 720, H = 270, L = 48, R = 48, T = 40, B = 44;
  const pw = W - L - R, ph = H - T - B;
  const maxBar = Math.max(...counts), barTop = Math.ceil(maxBar / 4) * 4;
  const slot = pw / days, bw = Math.max(4, slot * 0.62);
  const x = (i) => L + slot * i + slot / 2;
  const yBar = (v) => T + ph - (v / barTop) * ph;
  const yTot = (v) => T + ph - (v / total) * ph;
  const f = (n) => Math.round(n * 10) / 10;

  let run = 0;
  const pts = counts.map((c, i) => { run += c; return [x(i), yTot(run)]; });
  const line = pts.map(([px, py], i) => `${i ? 'L' : 'M'}${f(px)} ${f(py)}`).join(' ');
  const area = `${line} L${f(pts.at(-1)[0])} ${T + ph} L${f(pts[0][0])} ${T + ph} Z`;
  // No "0" label: the axis line marks zero, and the label would collide with the first date.
  const grid = [barTop / 2, barTop].map((v) => `<line class="chart__grid" x1="${L}" x2="${W - R}" y1="${f(yBar(v))}" y2="${f(yBar(v))}"/><text class="chart__tick" x="${L - 10}" y="${f(yBar(v) + 4)}" text-anchor="end">${v}</text>`).join('');
  const legend = `<text class="chart__legend" x="${L}" y="${T - 16}"><tspan class="chart__legend-bar">■</tspan> passes per day (left scale)  <tspan class="chart__legend-line">—</tspan> running total</text>`;
  const bars = counts.map((c, i) => (c ? `<rect class="chart__bar" x="${f(x(i) - bw / 2)}" y="${f(yBar(c))}" width="${f(bw)}" height="${f(T + ph - yBar(c))}"><title>${short(from + i * DAY)}: ${c} pass${c === 1 ? '' : 'es'}</title></rect>` : '')).join('');
  const ticks = [];
  for (let i = 0; i < days; i += 7) ticks.push(i);
  // Always label the last day; drop a weekly tick that would crowd it.
  if (days - 1 - ticks.at(-1) < 5) ticks.pop();
  ticks.push(days - 1);
  const xTicks = ticks.map((i) => `<text class="chart__tick" x="${f(x(i))}" y="${H - B + 26}" text-anchor="middle">${short(from + i * DAY)}</text>`).join('');
  const endLabel = `<text class="chart__total" x="${f(pts.at(-1)[0] + 8)}" y="${f(pts.at(-1)[1] + 5)}">${total}</text>`;
  const svg = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="passes-chart-title passes-chart-desc" preserveAspectRatio="xMidYMid meet"><title id="passes-chart-title">${attr(title)}</title><desc id="passes-chart-desc">${attr(caption)}</desc>${legend}${grid}<path class="chart__area" d="${area}"/>${bars}<path class="chart__line" d="${line}"/>${endLabel}<line class="chart__axis" x1="${L}" x2="${W - R}" y1="${T + ph}" y2="${T + ph}"/>${xTicks}</svg>`;
  run = 0;
  const rows = passes.map((p) => { run += p.count; return { label: short(day(p.date)), count: p.count, total: run }; });
  return { svg, rows, total };
}

/**
 * @param {any} dev parsed content/DEVELOPMENT.json
 * @param {Record<string, any>} assets build asset map (id -> {kind, ...})
 */
export function buildDevelopment(dev, assets) {
  const need = (id, kind, where) => {
    const a = assets[id];
    if (!a) throw new Error(`Development: unknown asset ${id} (${where})`);
    if (kind && a.kind !== kind) throw new Error(`Development: ${id} must be ${kind} art (${where})`);
    return id;
  };
  const text = (v, where) => {
    if (typeof v !== 'string' || !v.trim()) throw new Error(`Development: missing text for ${where}`);
    return v;
  };
  const list = (v, where) => {
    if (!Array.isArray(v) || !v.length) throw new Error(`Development: ${where} must be a non-empty list`);
    return v.map((s, i) => text(s, `${where}[${i}]`));
  };
  const updated = day(dev.updated);
  for (const p of dev.pairs) { need(p.concept, 'concept', `pair ${p.title}`); need(p.build, 'build', `pair ${p.title}`); }
  for (const id of [...dev.gallery.day, ...dev.gallery.night]) need(id, 'build', 'gallery');
  for (const r of dev.roadmap) if (!STATUSES[r.status]) throw new Error(`Development: roadmap status ${r.status}`);
  const timeline = dev.timeline.map((t) => ({ date: new Date(day(t.date)).toISOString().slice(0, 10), label: text(t.label, 'timeline label'), title: text(t.title, 'timeline title'), body: text(t.body, 'timeline body'), tags: t.tags || [] }));
  for (let i = 1; i < timeline.length; i++) if (timeline[i].date < timeline[i - 1].date) throw new Error('Development: timeline out of order');
  const chart = passesChart(dev.passes, dev.passesRange, text(dev.passesTitle, 'passesTitle'), text(dev.passesCaption, 'passesCaption'));
  return {
    updated: dev.updated, updatedLabel: long(updated),
    kicker: text(dev.kicker, 'kicker'), title: text(dev.title, 'title'), lede: text(dev.lede, 'lede'), buildLine: text(dev.buildLine, 'buildLine'),
    stats: dev.stats.map((s) => ({ value: text(s.value, 'stat value'), label: text(s.label, 'stat label') })),
    playableTitle: text(dev.playableTitle, 'playableTitle'), playableIntro: text(dev.playableIntro, 'playableIntro'), playable: list(dev.playable, 'playable'),
    timelineTitle: text(dev.timelineTitle, 'timelineTitle'), timelineIntro: text(dev.timelineIntro, 'timelineIntro'), timeline,
    passesTitle: dev.passesTitle, passesCaption: dev.passesCaption, chart,
    pairsTitle: text(dev.pairsTitle, 'pairsTitle'), pairsIntro: text(dev.pairsIntro, 'pairsIntro'),
    pairs: dev.pairs.map((p) => ({ concept: p.concept, build: p.build, title: text(p.title, 'pair title'), body: text(p.body, 'pair body') })),
    galleryTitle: text(dev.galleryTitle, 'galleryTitle'), galleryIntro: text(dev.galleryIntro, 'galleryIntro'),
    gallery: { day: dev.gallery.day, night: dev.gallery.night },
    roadmapTitle: text(dev.roadmapTitle, 'roadmapTitle'), roadmapIntro: text(dev.roadmapIntro, 'roadmapIntro'),
    roadmap: dev.roadmap.map((r) => ({ name: text(r.name, 'roadmap name'), status: r.status, statusLabel: STATUSES[r.status], body: text(r.body, 'roadmap body') })),
    roughTitle: text(dev.roughTitle, 'roughTitle'), rough: list(dev.rough, 'rough'),
    nextTitle: text(dev.nextTitle, 'nextTitle'), next: list(dev.next, 'next'),
  };
}
