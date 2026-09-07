/** Original line symbols, shared by the pack, quick slots and trading window. */
const paths: Record<string, string> = {
  flask: '<path d="M10 3h12m-9 0v9L7 24q-1 5 4 5h10q5 0 4-5l-6-12V3M10 21h12"/><path class="icon-fill" d="m12 22-2 4h12l-2-4z"/>',
  medkit: '<path d="M5 10h22v18H5zM11 10V5h10v5"/><path class="icon-fill" d="M14 14h4v4h4v4h-4v4h-4v-4h-4v-4h4z"/>',
  coil: '<path d="m7 8 18 5M7 14l18 5M7 20l18 5M8 6v21m16-16v18M7 4l18 5"/>',
  lattice: '<path d="m16 3 11 6v14l-11 6-11-6V9zM5 9l11 7 11-7M16 16v13M16 3v13M5 23l11-7 11 7"/>',
  talk: '<path d="M4 5h24v17H16l-7 6v-6H4zM9 11h14M9 16h9"/>',
  pack: '<path d="M7 9h18l2 20H5zM11 9V4h10v5M6 16h20M12 16v5h8v-5"/>',
  notes: '<path d="M7 3h18v26H7zM11 9h10M11 14h10M11 19h10M11 24h6"/>',
  pause: '<path d="M10 7v18M22 7v18"/>',
  close: '<path d="m9 9 14 14M23 9 9 23"/>',
};
export function icon(name: string): string {
  return `<svg class="ui-icon icon-${name}" viewBox="0 0 32 32" aria-hidden="true" focusable="false">${paths[name] ?? paths.notes}</svg>`;
}
