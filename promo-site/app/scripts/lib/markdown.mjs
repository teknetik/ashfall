// Minimal, deliberately strict Markdown subset renderer for the build step.
// Input is trusted editorial copy, but every text run is still HTML-escaped first,
// so the only markup that can appear in output is the markup emitted here.

/** @param {string} s */
export function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const STATUS_RE = /`\[(IN BUILD(?: — [^\]]+)?|PLANNED|EXPLORING|CONCEPT ART)\]`/g;

/**
 * Map a copy status tag to a badge descriptor.
 * @param {string} tag
 */
export function statusBadge(tag) {
  const t = tag.trim();
  if (t.startsWith('IN BUILD')) {
    const qual = t.slice('IN BUILD'.length).replace(/^\s*—\s*/, '').trim();
    return { kind: 'build', text: qual ? `In build · ${qual}` : 'In build' };
  }
  if (t === 'PLANNED') return { kind: 'planned', text: 'Planned' };
  if (t === 'EXPLORING') return { kind: 'exploring', text: 'Exploring' };
  return { kind: 'concept', text: 'Concept art' };
}

/** @param {{kind:string,text:string}} b */
export function badgeHtml(b) {
  return `<span class="badge badge--${b.kind}">${escapeHtml(b.text)}</span>`;
}

/**
 * Inline formatting: status tags, **bold**, *italic*, `code`.
 * @param {string} text
 */
export function inline(text) {
  const tags = [];
  let s = text.replace(STATUS_RE, (_m, tag) => {
    tags.push(badgeHtml(statusBadge(tag)));
    return `\u0000${tags.length - 1}\u0000`;
  });
  s = escapeHtml(s);
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g, '$1<em>$2</em>');
  // eslint-disable-next-line no-control-regex
  s = s.replace(/\u0000(\d+)\u0000/g, (_m, i) => tags[Number(i)]);
  return s;
}

/**
 * Render a Lattice (diegetic) block.
 * @param {string[]} lines
 */
export function latticeHtml(lines) {
  const text = lines.join('\n');
  return `<figure class="lattice" role="group" aria-label="Lattice interface readout (fiction from the design notes)"><pre data-type>${escapeHtml(text)}</pre></figure>`;
}

/**
 * Split markdown into blocks.
 * @param {string} md
 * @returns {Array<{type:string, lines:string[], lang?:string}>}
 */
export function blocks(md) {
  const lines = md.split('\n');
  /** @type {Array<{type:string, lines:string[], lang?:string}>} */
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {
      const lang = line.slice(3).trim();
      const body = [];
      i++;
      while (i < lines.length && !/^```\s*$/.test(lines[i])) body.push(lines[i++]);
      i++;
      out.push({ type: 'fence', lang, lines: body });
      continue;
    }
    if (!line.trim()) { i++; continue; }
    if (/^#{3,4} /.test(line)) { out.push({ type: 'heading', lines: [line] }); i++; continue; }
    if (/^---\s*$/.test(line)) { i++; continue; }
    if (/^\|/.test(line)) {
      const body = [];
      while (i < lines.length && /^\|/.test(lines[i])) body.push(lines[i++]);
      out.push({ type: 'table', lines: body });
      continue;
    }
    if (/^(- |\d+\. )/.test(line)) {
      const ordered = /^\d+\. /.test(line);
      const body = [];
      while (i < lines.length && lines[i].trim() && !/^```/.test(lines[i])) {
        if (/^(- |\d+\. )/.test(lines[i])) body.push(lines[i].replace(/^(- |\d+\. )/, ''));
        else body[body.length - 1] += ' ' + lines[i].trim();
        i++;
      }
      out.push({ type: ordered ? 'ol' : 'ul', lines: body });
      continue;
    }
    const body = [];
    while (i < lines.length && lines[i].trim() && !/^```/.test(lines[i]) && !/^\|/.test(lines[i]) && !/^#{3,4} /.test(lines[i])) {
      if (body.length && /^(- |\d+\. )/.test(lines[i])) break;
      body.push(lines[i].trim());
      i++;
    }
    out.push({ type: 'p', lines: body });
  }
  return out;
}

/**
 * Render a list of blocks to HTML.
 * @param {ReturnType<typeof blocks>} bs
 * @param {{olClass?: string, headingLevel?: number}} [opts]
 */
export function renderBlocks(bs, opts = {}) {
  const hl = opts.headingLevel ?? 3;
  return bs.map((b) => {
    switch (b.type) {
      case 'fence':
        return b.lang === 'lattice' ? latticeHtml(b.lines) : `<pre>${escapeHtml(b.lines.join('\n'))}</pre>`;
      case 'heading': {
        const txt = b.lines[0].replace(/^#+ /, '');
        return `<h${hl}>${inline(txt)}</h${hl}>`;
      }
      case 'table': {
        const rows = b.lines.filter((l) => !/^\|\s*-/.test(l)).map((l) => l.replace(/^\||\|$/g, '').split('|').map((c) => c.trim()));
        const [head, ...rest] = rows;
        return `<div class="table-wrap"><table><thead><tr>${head.map((h) => `<th scope="col">${inline(h)}</th>`).join('')}</tr></thead><tbody>${rest
          .map((r) => `<tr>${r.map((c, ci) => (ci === 0 ? `<th scope="row">${inline(c)}</th>` : `<td>${inline(c)}</td>`)).join('')}</tr>`)
          .join('')}</tbody></table></div>`;
      }
      case 'ul':
        return `<ul>${b.lines.map((l) => `<li>${inline(l)}</li>`).join('')}</ul>`;
      case 'ol':
        return `<ol${opts.olClass ? ` class="${opts.olClass}"` : ''}>${b.lines.map((l) => `<li>${inline(l)}</li>`).join('')}</ol>`;
      default:
        return `<p>${inline(b.lines.join(' '))}</p>`;
    }
  }).join('\n');
}

/** @param {string} md */
export function renderMarkdown(md, opts = {}) {
  return renderBlocks(blocks(md), opts);
}
