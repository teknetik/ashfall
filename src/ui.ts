import { CAMERA_NAMES } from './camera';
import type { Game } from './game';

const names = { cam_gate: 'West Gate', cam_avenue: 'Avenue', cam_hill: 'Hill Tree', cam_grid: 'Lattice Jack', cam_whompah: 'Ring Gate', cam_hero: 'Hero' };

export function createUI(root: HTMLElement) {
  root.innerHTML = `
    <canvas class="world-canvas" tabindex="0" aria-label="Athen Hill greybox city. Use WASD to walk and right-drag to look."></canvas>
    <header class="identity"><p class="eyebrow">Phase 1 · Greybox city</p><h1>Athen Hill</h1><p id="location" class="scope">West Gate</p></header>
    <div class="top-actions"><button id="pause" disabled>Pause</button><details class="instrumentation"><summary>Survey tools</summary>
      <p id="status" class="status" role="status">Building the city…</p>
      <div class="camera-controls"><label for="view">View</label><select id="view"><option value="follow">Player</option>${CAMERA_NAMES.map((name) => `<option value="${name}">${names[name]}</option>`).join('')}</select></div>
      <div class="tool-actions"><button id="save" disabled>Save frame</button><button id="reset" disabled>Return to gate</button></div>
      <p id="save-status" class="save-status" role="status">Choose a named view for a fixed capture.</p>
      <p id="metrics" class="metrics" aria-label="Renderer statistics">Waiting for renderer</p>
      <p id="position" class="position"></p>
    </details></div>
    <div id="boot-message" class="boot-message" role="status">Building the city…</div>
    <div id="pause-panel" class="pause-panel" hidden><p class="eyebrow">Exploration paused</p><h2>Back to the hill.</h2><button id="resume">Resume walking</button></div>
    <footer class="explore-hint"><p class="route">West Gate <span>→</span> Hill Tree <span>→</span> Ring Gate <span>→</span> Lattice Jack</p><p class="desktop-help"><kbd>WASD</kbd> walk <b>·</b> <kbd>Shift</kbd> run <b>·</b> Right-drag look <b>·</b> <kbd>Esc</kbd> pause <b>·</b> <kbd>R</kbd> return</p><p class="touch-help">Arrows to walk · Drag the city to look</p></footer>
    <nav class="touch-controls" aria-label="Movement controls"><button data-move="forward" aria-label="Walk forward">↑</button><button data-move="left" aria-label="Walk left">←</button><button data-move="back" aria-label="Walk backward">↓</button><button data-move="right" aria-label="Walk right">→</button></nav><button class="touch-run" data-move="run">Run</button>`;
  return root.querySelector<HTMLCanvasElement>('canvas')!;
}

export function bindUI(root: HTMLElement, game: Game) {
  const el = <T extends HTMLElement>(id: string) => root.querySelector<T>(`#${id}`)!;
  const status = el('status');
  const metrics = el('metrics');
  const select = el<HTMLSelectElement>('view');
  const save = el<HTMLButtonElement>('save');
  const saved = el('save-status');
  const pause = el<HTMLButtonElement>('pause');
  const reset = el<HTMLButtonElement>('reset');
  let saving = false;
  const update = () => {
    const ready = game.state === 'play' || game.state === 'paused';
    status.textContent = game.state === 'error' ? game.error : ready ? 'City ready · movement and collision active' : 'Building the city…';
    status.dataset.state = game.state;
    el('boot-message').hidden = ready;
    el('boot-message').textContent = status.textContent;
    el('location').textContent = game.locationLabel;
    metrics.textContent = `${Math.round(game.metrics.fps)} fps · ${game.metrics.draws} draws · ${game.metrics.tris.toLocaleString()} tris`;
    const player = game.player?.snapshot;
    el('position').textContent = player ? `x ${player.x.toFixed(1)} · y ${player.y.toFixed(2)} · z ${player.z.toFixed(1)} · ${player.grounded ? 'grounded' : 'falling'}` : '';
    const active = game.cameras.active.name;
    select.value = CAMERA_NAMES.includes(active as typeof CAMERA_NAMES[number]) ? active : 'follow';
    save.disabled = !ready || saving || select.value === 'follow';
    select.disabled = !ready;
    pause.disabled = !ready;
    reset.disabled = !ready;
    pause.textContent = game.state === 'paused' ? 'Resume' : 'Pause';
    el('pause-panel').hidden = game.state !== 'paused';
    root.dataset.state = game.state;
  };
  select.addEventListener('change', () => { game.selectCamera(select.value); select.blur(); });
  pause.addEventListener('click', () => { game.pause(game.state !== 'paused'); pause.blur(); });
  el('resume').addEventListener('click', () => { game.pause(false); game.canvas.focus(); });
  reset.addEventListener('click', () => { game.reset(); reset.blur(); });
  save.addEventListener('click', async () => {
    saving = true;
    const name = select.value;
    saved.textContent = 'Saving frame…';
    update();
    try {
      const path = await game.shot(name);
      saved.textContent = path.startsWith('download:') ? `Downloaded ${path.slice(9)}` : `Saved ${path}`;
    } catch (error) {
      saved.textContent = error instanceof Error ? error.message : 'Frame could not be saved.';
    } finally { saving = false; update(); save.blur(); }
  });
  game.input.bindTouch(root);
  game.onUpdate = update;
  update();
}

export function showBootError(root: HTMLElement, error: unknown) {
  const message = error instanceof Error ? error.message : 'The renderer could not start.';
  const status = root.querySelector<HTMLElement>('#status')!;
  status.textContent = message;
  status.dataset.state = 'error';
  root.querySelector<HTMLElement>('#boot-message')!.textContent = message;
  root.querySelector<HTMLSelectElement>('#view')!.disabled = true;
}
