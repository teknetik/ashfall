import { CAMERA_NAMES } from './camera';
import type { Game } from './game';

const names = { cam_gate: 'Gate', cam_avenue: 'Avenue', cam_hill: 'Hill', cam_grid: 'Lattice Jack', cam_whompah: 'Ring Gate', cam_hero: 'Hero' };

export function createUI(root: HTMLElement) {
  root.innerHTML = `
    <canvas class="world-canvas" aria-label="Blender pipeline probe: a two metre blue cube"></canvas>
    <header class="identity"><p class="eyebrow">Phase 0 · Pipeline probe</p><h1>Athen Hill</h1><p class="scope">Blender → glTF → WebGL2</p></header>
    <section class="instrumentation" aria-label="Probe controls">
      <p id="status" class="status" role="status">Loading the Blender probe…</p>
      <div class="camera-controls"><label for="view">View</label><select id="view">${CAMERA_NAMES.map((name) => `<option value="${name}" ${name === 'cam_hill' ? 'selected' : ''}>${names[name]}</option>`).join('')}</select><button id="save" disabled>Save frame</button></div>
      <p id="save-status" class="save-status" role="status">Fixed captures · 1920 × 1080</p>
      <p id="metrics" class="metrics" aria-label="Renderer statistics">Waiting for renderer</p>
      <p class="phase-note">Pipeline verification. City and movement begin in Phase 1.</p>
    </section>`;
  return root.querySelector<HTMLCanvasElement>('canvas')!;
}

export function bindUI(root: HTMLElement, game: Game) {
  const status = root.querySelector<HTMLElement>('#status')!;
  const metrics = root.querySelector<HTMLElement>('#metrics')!;
  const select = root.querySelector<HTMLSelectElement>('#view')!;
  const save = root.querySelector<HTMLButtonElement>('#save')!;
  const saved = root.querySelector<HTMLElement>('#save-status')!;
  let saving = false;
  const update = () => {
    status.textContent = game.state === 'error' ? game.error : game.state === 'probe' ? 'Probe ready · 2 × 2 × 2 m' : 'Loading the Blender probe…';
    status.dataset.state = game.state;
    metrics.textContent = `${Math.round(game.metrics.fps)} fps · ${game.metrics.draws} draws · ${game.metrics.tris.toLocaleString()} tris`;
    save.disabled = game.state !== 'probe' || saving;
    select.disabled = game.state !== 'probe';
    if (game.cameras.active.name !== 'cam_anchor') select.value = game.cameras.active.name;
  };
  select.addEventListener('change', () => { game.selectCamera(select.value); });
  save.addEventListener('click', async () => {
    saving = true;
    saved.textContent = 'Saving frame…';
    update();
    try {
      const path = await game.shot(select.value);
      saved.textContent = path.startsWith('download:') ? `Downloaded ${path.slice(9)}` : `Saved ${path}`;
    } catch (error) {
      saved.textContent = error instanceof Error ? error.message : 'Frame could not be saved.';
    } finally {
      saving = false;
      update();
    }
  });
  game.onUpdate = update;
  update();
}

export function showBootError(root: HTMLElement, error: unknown) {
  const status = root.querySelector<HTMLElement>('#status')!;
  status.textContent = error instanceof Error ? error.message : 'The renderer could not start.';
  status.dataset.state = 'error';
  root.querySelector<HTMLSelectElement>('#view')!.disabled = true;
}
