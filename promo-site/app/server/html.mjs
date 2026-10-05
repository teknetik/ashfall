// Auto-escaping HTML tagged template. Interpolated values are escaped unless wrapped in raw().

const ESC = /[&<>"']/g;
/** @type {Record<string,string>} */
const MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

/** @param {unknown} s */
export function esc(s) {
  return String(s ?? '').replace(ESC, (c) => MAP[c]);
}

export class Raw {
  /** @param {string} value */
  constructor(value) {
    this.value = value;
  }

  toString() {
    return this.value;
  }
}

/** Mark trusted, already-safe HTML. Never pass user input. @param {string} s */
export const raw = (s) => new Raw(String(s));

/** @param {unknown} v @returns {string} */
function render(v) {
  if (v === null || v === undefined || v === false) return '';
  if (v instanceof Raw) return v.value;
  if (Array.isArray(v)) return v.map(render).join('');
  return esc(v);
}

/**
 * @param {TemplateStringsArray} strings
 * @param {...unknown} values
 * @returns {Raw}
 */
export function html(strings, ...values) {
  let out = strings[0];
  for (let i = 0; i < values.length; i++) out += render(values[i]) + strings[i + 1];
  return new Raw(out);
}

/**
 * Render user-authored plain text: escape, then turn line breaks into <br>.
 * No links, no markup.
 * @param {string} text
 */
export function userText(text) {
  const paras = String(text).replace(/\r\n?/g, '\n').split(/\n{2,}/);
  return raw(paras.map((p) => `<p>${esc(p).replace(/\n/g, '<br>')}</p>`).join(''));
}
