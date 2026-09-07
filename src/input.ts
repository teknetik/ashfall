export interface MoveIntent { forward: number; right: number; run: boolean }

/** Input is collected here; only the fixed simulation loop consumes movement. */
export class Input {
  private keys = new Set<string>();
  private touches = new Map<number, string>();
  private drag: { id: number; x: number; y: number } | null = null;
  private abort = new AbortController();
  onOrbit: (x: number, y: number) => void = () => {};
  onPause: () => void = () => {};
  onReset: () => void = () => {};
  onMove: () => void = () => {};
  onInteract: () => void = () => {};
  onHotbar: (index: number) => void = () => {};

  constructor(private canvas: HTMLCanvasElement) {
    const options = { signal: this.abort.signal };
    window.addEventListener('keydown', (event) => {
      if (event.code === 'Escape') {
        if (!event.repeat) this.onPause();
        return;
      }
      if (event.code === 'KeyR' && !(event.target instanceof HTMLElement && event.target.closest('select, input, textarea'))) {
        if (!event.repeat) this.onReset();
        return;
      }
      if (event.target instanceof HTMLElement && event.target.closest('select, input, textarea, button, summary')) return;
      if (event.code === 'KeyE') {
        event.preventDefault();
        if (!event.repeat) this.onInteract();
        return;
      }
      if (/^Digit[1-6]$/.test(event.code)) {
        event.preventDefault();
        if (!event.repeat) this.onHotbar(Number(event.code.slice(-1)) - 1);
        return;
      }
      if (['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ShiftLeft', 'ShiftRight'].includes(event.code)) {
        event.preventDefault();
        this.keys.add(event.code);
        this.onMove();
      }
    }, options);
    window.addEventListener('keyup', (event) => this.keys.delete(event.code), options);
    window.addEventListener('blur', () => this.clear(), options);
    document.addEventListener('visibilitychange', () => { if (document.hidden) this.clear(); }, options);
    canvas.addEventListener('contextmenu', (event) => event.preventDefault(), options);
    canvas.addEventListener('pointerdown', (event) => {
      canvas.focus({ preventScroll: true });
      if ((event.pointerType !== 'touch' && event.button !== 2) || this.drag) return;
      event.preventDefault();
      this.drag = { id: event.pointerId, x: event.clientX, y: event.clientY };
      canvas.setPointerCapture(event.pointerId);
    }, options);
    canvas.addEventListener('pointermove', (event) => {
      if (!this.drag || event.pointerId !== this.drag.id) return;
      this.onOrbit(event.clientX - this.drag.x, event.clientY - this.drag.y);
      this.drag.x = event.clientX;
      this.drag.y = event.clientY;
    }, options);
    const release = (event: PointerEvent) => {
      if (this.drag?.id === event.pointerId) this.drag = null;
    };
    for (const type of ['pointerup', 'pointercancel', 'lostpointercapture'] as const) canvas.addEventListener(type, release, options);
  }

  bindTouch(root: HTMLElement) {
    const options = { signal: this.abort.signal };
    root.querySelectorAll<HTMLButtonElement>('[data-move]').forEach((button) => {
      button.addEventListener('pointerdown', (event) => {
        event.preventDefault();
        this.touches.set(event.pointerId, button.dataset.move!);
        button.setPointerCapture(event.pointerId);
        button.dataset.held = 'true';
        this.onMove();
      }, options);
      const release = (event: PointerEvent) => {
        this.touches.delete(event.pointerId);
        button.dataset.held = 'false';
      };
      for (const type of ['pointerup', 'pointercancel', 'lostpointercapture'] as const) button.addEventListener(type, release, options);
    });
  }

  get intent(): MoveIntent {
    const touch = (direction: string) => [...this.touches.values()].includes(direction);
    const up = this.keys.has('KeyW') || this.keys.has('ArrowUp') || touch('forward');
    const down = this.keys.has('KeyS') || this.keys.has('ArrowDown') || touch('back');
    const right = this.keys.has('KeyD') || this.keys.has('ArrowRight') || touch('right');
    const left = this.keys.has('KeyA') || this.keys.has('ArrowLeft') || touch('left');
    return { forward: Number(up) - Number(down), right: Number(right) - Number(left),
      run: this.keys.has('ShiftLeft') || this.keys.has('ShiftRight') || touch('run') };
  }

  clear() {
    this.keys.clear();
    this.touches.clear();
    if (this.drag && this.canvas.hasPointerCapture(this.drag.id)) this.canvas.releasePointerCapture(this.drag.id);
    this.drag = null;
    document.querySelectorAll<HTMLElement>('[data-held]').forEach((button) => { button.dataset.held = 'false'; });
  }

  dispose() { this.clear(); this.abort.abort(); }
}
