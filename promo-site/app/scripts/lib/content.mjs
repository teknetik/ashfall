// Parses content/WEBSITE_COPY.md (read-only input) into structured, pre-rendered data.
// Editorial "> src:" lines are removed before anything else and never reach output.
import { blocks, renderBlocks, inline, statusBadge, badgeHtml, escapeHtml } from './markdown.mjs';

/**
 * Exact, reviewed text corrections required by the boss review comment on t_96803b8f.
 * Each `from` must exist exactly once in the source, otherwise the build fails loudly
 * (so a later copy revision is noticed rather than silently ignored).
 */
export const COPY_CORRECTIONS = [
  {
    why: 'Wardens/Karaveen are cultures and institutions of the setting, not established playable factions (boss review).',
    from: '· Wardens and Karaveen as playable factions\n`[PLANNED]`.',
    to: '· Wardens and Karaveen as cultures and institutions in the story `[PLANNED]`.',
  },
];

/** Strip editorial source-reference blockquotes ("> src: ..." and their "> " continuations). */
export function stripEditorial(md) {
  const out = [];
  let inSrc = false;
  for (const line of md.split('\n')) {
    if (/^>\s*src:/i.test(line)) { inSrc = true; continue; }
    if (inSrc && /^>/.test(line)) continue;
    inSrc = false;
    out.push(line);
  }
  return out.join('\n');
}

/** @param {string} md */
export function applyCorrections(md) {
  let s = md;
  for (const c of COPY_CORRECTIONS) {
    const n = s.split(c.from).length - 1;
    if (n !== 1) throw new Error(`Copy correction source text found ${n} times (expected 1): ${c.from}`);
    s = s.replace(c.from, c.to);
  }
  return s;
}

/** Split into "## " sections keyed by heading text. */
export function sections(md) {
  /** @type {Record<string,string>} */
  const out = {};
  let key = '_preamble';
  let buf = [];
  for (const line of md.split('\n')) {
    const m = /^## (.+)$/.exec(line);
    if (m) { out[key] = buf.join('\n'); key = m[1].trim(); buf = []; continue; }
    buf.push(line);
  }
  out[key] = buf.join('\n');
  return out;
}

/** Find section by numeric/label prefix, e.g. "1." or "/about". */
function sec(all, prefix) {
  const k = Object.keys(all).find((x) => x.startsWith(prefix));
  if (!k) throw new Error(`Missing copy section ${prefix}`);
  return all[k];
}

/**
 * Pull "**Label:** value" paragraphs (value may wrap across lines until a blank line).
 * Returns the extracted fields and the remaining markdown.
 * @param {string} md
 */
export function extractFields(md) {
  /** @type {Record<string,string>} */
  const fields = {};
  /** @type {Array<{label:string, value:string, index:number}>} */
  const asides = [];
  const lines = md.split('\n');
  const rest = [];
  let i = 0;
  while (i < lines.length) {
    const m = /^\*\*([^*]+?):\*\*\s?(.*)$/.exec(lines[i]);
    const comp = /^\*\*\[Component: ([^\]—]+?)(?: — [^\]]*)?\]\*\*\s?(.*)$/.exec(lines[i]);
    if (m || comp) {
      const start = i;
      const val = [m ? m[2] : comp[2]];
      i++;
      while (i < lines.length && lines[i].trim() && !/^```/.test(lines[i]) && !/^\*\*[^*]+?:\*\*/.test(lines[i])) val.push(lines[i++].trim());
      const value = val.join(' ').trim();
      if (comp) {
        rest.push(`@@COMPONENT ${comp[1].trim()}@@`);
        fields[`component:${comp[1].trim()}`] = value;
      } else if (/^In (the )?build today/.test(m[1])) {
        const id = /`([^`]+)`/.exec(m[1]);
        asides.push({ label: m[1], value, index: rest.length });
        rest.push(`@@ASIDE ${asides.length - 1} ${id ? id[1] : ''}@@`);
      } else if (/^(Kicker|Title|Standfirst|Pull quote|Status rail|Intro|Map caption|Premise line|CTA primary|CTA secondary|Image badge|Teaser heading|Teaser empty state|CTA|Hook)$/i.test(m[1])) {
        fields[m[1].toLowerCase()] = value;
        if (/^pull quote$/i.test(m[1])) rest.push('@@PULLQUOTE@@');
      } else {
        // An inline lead-in paragraph like "**The Wardens.** ..." does not match (no colon inside **).
        for (let k = start; k < i; k++) rest.push(lines[k]);
      }
      continue;
    }
    rest.push(lines[i]);
    i++;
  }
  return { fields, asides, rest: rest.join('\n') };
}

/**
 * Split a status rail into badge items.
 * @param {string} rail
 */
export function parseRail(rail) {
  if (!rail) return [];
  const items = [];
  for (const part of rail.split(/\s·\s/)) {
    const tagCount = (part.match(/`\[/g) || []).length;
    const pieces = tagCount > 1 ? part.split(/(?<=\.)\s+(?=[A-Z])/) : [part];
    for (const p of pieces) {
      const tags = [...p.matchAll(/`\[([^\]]+)\]`/g)].map((x) => x[1]);
      let label = p.replace(/`\[[^\]]+\]`/g, '').replace(/\s+/g, ' ').replace(/\s+([.,)])/g, '$1').replace(/—\s*—/g, '—').trim();
      label = label.replace(/^[—–-]\s*/, '').replace(/\s*[—–-]\s*$/, '').replace(/\.$/, '').trim();
      label = label.charAt(0).toUpperCase() + label.slice(1);
      const badge = statusBadge(tags[0] || 'PLANNED');
      items.push({ label, badge, labelHtml: inline(label) });
    }
  }
  return items;
}

/** @param {string} s */
const unquote = (s) => s.replace(/^"|"$/g, '').replace(/^“|”$/g, '');

/**
 * @param {string} md raw markdown of a chapter section
 * @param {object} [opts]
 */
function chapter(md, opts) {
  const { fields, asides, rest } = extractFields(md);
  const body = blocks(rest);
  return { fields, asides, body, opts };
}

/**
 * Parse the atlas section into groups and regions.
 * @param {string} md
 */
export function parseAtlas(md) {
  const { fields, rest } = extractFields(md);
  const groups = [];
  let cur = null;
  let region = null;
  let tail = [];
  for (const raw of rest.split('\n')) {
    const line = raw.trimEnd();
    const g = /^### (.+?)(?:\s+`\[([^\]]+)\]`)?$/.exec(line);
    if (g) {
      if (/world between regions/i.test(g[1])) { cur = null; region = null; tail = []; groups.push({ name: g[1], status: null, regions: [], between: tail }); continue; }
      cur = { name: g[1], status: g[2] ? statusBadge(g[2]) : null, regions: [] };
      groups.push(cur);
      region = null;
      continue;
    }
    if (!cur) { if (groups.length && groups[groups.length - 1].between) tail.push(line); continue; }
    const r = /^\*\*([^*]+)\*\*(?:\s+—\s+`\[([^\]]+)\]`)?\s*$/.exec(line);
    if (r) {
      region = { name: r[1], status: r[2] ? statusBadge(r[2]) : cur.status, hook: '', body: [], banner: null };
      cur.regions.push(region);
      continue;
    }
    if (!region) continue;
    const h = /^\*Hook:\*\s*(.+)$/.exec(line);
    if (h) { region.hook = h[1]; continue; }
    const b = /^\*Banner art:\*\s*`([^`]+)`/.exec(line);
    if (b) { region.banner = b[1]; continue; }
    if (line.trim()) region.body.push(line.trim());
  }
  for (const gr of groups) for (const r of gr.regions) {
    r.slug = r.name.toLowerCase().replace(/^the /, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    r.bodyHtml = inline(r.body.join(' '));
    r.hookHtml = inline(r.hook);
  }
  const between = groups.find((x) => x.between);
  return {
    fields,
    groups: groups.filter((x) => !x.between),
    betweenHtml: between ? renderBlocks(blocks(between.between.join('\n'))) : '',
  };
}

/** Topics table → array. */
export function parseTopics(md) {
  const rows = md.split('\n').filter((l) => /^\| `/.test(l));
  return rows.map((l) => {
    const c = l.replace(/^\||\|$/g, '').split('|').map((x) => x.trim());
    return { slug: c[0].replace(/`/g, ''), title: c[1], prompt: c[2] };
  });
}

/** FAQ: bold question line followed by answer paragraph. */
export function parseFaq(md) {
  const items = [];
  const parts = md.split(/\n(?=\*\*[^*]+\?\*\*\s*$)/m);
  for (const p of parts) {
    const m = /^\*\*([^*]+\?)\*\*\s*\n([\s\S]*)$/.exec(p.trim());
    if (m) items.push({ q: m[1].trim(), aHtml: renderBlocks(blocks(m[2].trim())) });
  }
  return items;
}

/** Meta bullet list. */
export function parseMeta(md) {
  const meta = {};
  const text = md.replace(/\n {2,}/g, ' ');
  for (const m of text.matchAll(/^- \*\*([^*]+):\*\*\s*(.+)$/gm)) meta[m[1].toLowerCase()] = m[2].trim();
  return meta;
}

/** Parse the whole copy document. */
export function parseCopy(rawMd) {
  const md = applyCorrections(stripEditorial(rawMd));
  const all = sections(md);
  const meta = parseMeta(sec(all, 'Site meta'));
  const hero = extractFields(sec(all, '0.'));
  const bootMatch = /```lattice\n([\s\S]*?)\n```/.exec(sec(all, '0.'));
  const chapters = {
    world: chapter(sec(all, '1.')),
    ward: chapter(sec(all, '2.')),
    opening: chapter(sec(all, '3.')),
    lattice: chapter(sec(all, '4.')),
    build: chapter(sec(all, '5.')),
    machines: chapter(sec(all, '6.')),
    companions: chapter(sec(all, '7.')),
    jacks: chapter(sec(all, '7b.')),
    testing: chapter(sec(all, '9.')),
  };
  const atlas = parseAtlas(sec(all, '8.'));
  const discuss = extractFields(sec(all, '10.'));
  const topics = parseTopics(sec(all, '10.'));
  const galleryIntros = {};
  for (const m of sec(all, 'Gallery captions').replace(/\n {2,}/g, ' ').matchAll(/^- \*\*([^*]+)\*\* filter intro:\s*(.+)$/gm)) galleryIntros[m[1].toLowerCase()] = m[2].trim();
  const about = extractFields(sec(all, '/about'));
  const rules = sec(all, 'Discussion rules').trim();
  const faq = parseFaq(sec(all, 'FAQ'));
  /** @type {Record<string, string>} */
  const heroOut = { ...hero.fields, boot: bootMatch ? bootMatch[1].trim() : '' };
  return { meta, hero: heroOut, chapters, atlas, discuss: discuss.fields, topics, galleryIntros, about, rules, faq };
}

export { inline, renderBlocks, blocks, badgeHtml, escapeHtml, unquote };
