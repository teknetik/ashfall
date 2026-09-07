import { ACESFilmicToneMapping, PCFShadowMap, SRGBColorSpace, Vector2, WebGLRenderer } from 'three';
import { CAMERA_NAMES, Cameras, NAMED_VERTICAL_FOV, type CameraName } from './camera';
import { World } from './world';
import { LANDMARKS, LANDMARK_LABELS } from './layout';
import { Input } from './input';
import { Physics, FIXED_STEP } from './physics';
import { Player } from './player';
import { Atmosphere } from './atmosphere';

export type GameState = 'boot' | 'play' | 'paused' | 'error';
export interface FrameMetrics {
  fps: number;
  frameMs: number;
  draws: number;
  tris: number;
  geometries: number;
  textures: number;
  width: number;
  height: number;
  pixelRatio: number;
}

export class Game {
  readonly renderer: WebGLRenderer;
  readonly atmosphere: Atmosphere;
  readonly world = new World();
  readonly cameras = new Cameras(this.world.scene);
  readonly input: Input;
  player: Player | null = null;
  physics: Physics | null = null;
  readonly metrics: FrameMetrics = { fps: 0, frameMs: 0, draws: 0, tris: 0, geometries: 0, textures: 0, width: 0, height: 0, pixelRatio: 1 };
  readonly ready: Promise<void>;
  state: GameState = 'boot';
  error = '';
  landmark = 'west_gate';
  private accumulator = 0;
  private captureInProgress = false;
  private hour = 16;
  private disposed = false;
  private previousFrame = 0;
  private sampleStart = 0;
  private sampleFrames = 0;
  private captureQueue: Promise<unknown> = Promise.resolve();
  onUpdate: () => void = () => {};

  constructor(readonly canvas: HTMLCanvasElement) {
    const context = canvas.getContext('webgl2', { antialias: true, alpha: false });
    if (!context) throw new Error('A WebGL2 browser is required to explore Athen Hill.');
    this.renderer = new WebGLRenderer({ canvas, context, antialias: true });
    this.renderer.outputColorSpace = SRGBColorSpace;
    this.renderer.toneMapping = ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 0.72;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = PCFShadowMap;
    // Count the shadow pass together with the visible pass, resetting once per complete frame.
    this.renderer.info.autoReset = false;
    this.input = new Input(canvas);
    this.input.onOrbit = (x, y) => {
      if (this.state !== 'play') return;
      this.cameras.orbit(x, y);
    };
    this.input.onMove = () => {
      if (this.state === 'play' && this.cameras.active !== this.cameras.follow) this.cameras.select('follow');
    };
    this.input.onPause = () => this.pause(this.state !== 'paused');
    this.input.onReset = () => this.reset();
    this.world.setSun(this.hour);
    this.atmosphere = new Atmosphere(this.renderer, this.world.scene, this.world.sun.position);
    this.resize();
    window.addEventListener('resize', this.resize);
    canvas.addEventListener('webglcontextlost', this.contextLost);
    this.ready = this.world.load().then(async () => {
      if (this.disposed) return;
      if (this.state === 'error') throw new Error(this.error);
      const physics = await Physics.create(this.world.colliderDefs);
      if (this.disposed) { physics.dispose(); return; }
      if (this.error) { physics.dispose(); throw new Error(this.error); }
      this.physics = physics;
      this.player = new Player(physics, this.world.scene, LANDMARKS.west_gate);
      this.cameras.attach(physics, this.player);
      this.cameras.update(0, true);
      this.state = 'play';
      this.onUpdate();
    }).catch((error: unknown) => {
      if (!this.disposed) this.fail(error instanceof Error ? error.message : 'The greybox city could not be loaded.');
      throw error;
    });
    // Loading errors are also visible through ready rejection and the UI; avoid an unhandled promise.
    void this.ready.catch(() => {});
    this.renderer.setAnimationLoop(this.frame);
  }

  get timeOfDay() { return this.hour; }
  set timeOfDay(value: number) {
    if (!Number.isFinite(value) || value < 0 || value > 24) throw new Error('timeOfDay must be between 0 and 24.');
    this.hour = value;
    this.world.setSun(value);
    this.atmosphere.syncSun(this.world.sun.position);
  }

  selectCamera(name: string) {
    this.cameras.select(name);
    this.onUpdate();
  }

  goto(landmark: string) {
    const coordinates = Object.hasOwn(LANDMARKS, landmark) ? LANDMARKS[landmark] : undefined;
    if (!coordinates) throw new Error(`Unknown landmark: ${landmark}`);
    if (!this.player) throw new Error('The city is still loading.');
    this.input.clear();
    this.accumulator = 0;
    this.player.teleport(coordinates);
    this.landmark = landmark;
    this.cameras.anchor(this.player.position);
    this.cameras.update(0, true);
    this.onUpdate();
  }

  get locationLabel() { return LANDMARK_LABELS[this.landmark] ?? this.landmark; }

  pause(value: boolean) {
    if (this.state !== 'play' && this.state !== 'paused') return;
    this.state = value ? 'paused' : 'play';
    this.accumulator = 0;
    this.input.clear();
    this.onUpdate();
  }

  reset() {
    if (!this.player || this.state === 'error') return;
    this.pause(false);
    this.cameras.resetOrbit();
    this.goto('west_gate');
  }

  shot(name: string): Promise<string> {
    if (!CAMERA_NAMES.includes(name as CameraName)) return Promise.reject(new Error(`Unknown named camera: ${name}`));
    const result = this.captureQueue.then(() => this.capture(name as CameraName));
    this.captureQueue = result.catch(() => {});
    return result;
  }

  private async capture(name: CameraName): Promise<string> {
    await this.ready;
    if (this.disposed || this.state === 'error') throw new Error(this.error || 'The renderer is unavailable.');
    const camera = this.cameras.named[name];
    const size = this.renderer.getSize(new Vector2());
    const pixelRatio = this.renderer.getPixelRatio();
    const aspect = camera.aspect;
    const fov = camera.fov;
    const playerVisible = this.player?.model.visible ?? true;
    let dataUrl: string;
    this.captureInProgress = true;
    // All render and restoration work is synchronous, before any promise can yield to the main loop.
    try {
      if (this.player) this.player.model.visible = true;
      this.renderer.setPixelRatio(1);
      this.renderer.setSize(1920, 1080, false);
      camera.aspect = 1920 / 1080;
      camera.fov = NAMED_VERTICAL_FOV;
      camera.updateProjectionMatrix();
      this.renderer.info.reset();
      this.renderer.render(this.world.scene, camera);
      dataUrl = this.canvas.toDataURL('image/png');
    } finally {
      if (this.player) this.player.model.visible = playerVisible;
      camera.aspect = aspect;
      camera.fov = fov;
      camera.updateProjectionMatrix();
      this.renderer.setPixelRatio(pixelRatio);
      this.renderer.setSize(size.x, size.y, false);
      this.captureInProgress = false;
      this.render();
    }
    const blob = await (await fetch(dataUrl)).blob();
    const local = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
    if (local) {
      const response = await fetch(`/__athen__/shots/${name}.png`, { method: 'PUT', headers: { 'Content-Type': 'image/png' }, body: blob });
      if (response.headers.get('content-type')?.includes('application/json')) {
        const result = await response.json() as { path?: string; error?: string };
        if (!response.ok || !result.path) throw new Error(result.error || 'Screenshot save failed.');
        return result.path;
      }
      if (response.status !== 404 && response.status !== 405 && !response.ok) throw new Error(`Screenshot save failed (${response.status}).`);
    }
    // Static hosts have no write endpoint. Download the same PNG without claiming a repository save.
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${name}.png`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    return `download:${name}.png`;
  }

  private render() {
    this.renderer.info.reset();
    this.renderer.render(this.world.scene, this.cameras.active);
    const info = this.renderer.info;
    this.metrics.draws = info.render.calls;
    this.metrics.tris = info.render.triangles;
    this.metrics.geometries = info.memory.geometries;
    this.metrics.textures = info.memory.textures;
    this.metrics.width = this.canvas.width;
    this.metrics.height = this.canvas.height;
    this.metrics.pixelRatio = this.renderer.getPixelRatio();
  }

  private frame = (time: number) => {
    if (this.disposed || this.state === 'error') return;
    if (!this.sampleStart) this.sampleStart = time;
    else this.sampleFrames += 1;
    const dt = this.previousFrame ? Math.min((time - this.previousFrame) / 1000, 0.1) : 0;
    if (this.previousFrame) this.metrics.frameMs = time - this.previousFrame;
    this.previousFrame = time;
    if (this.state === 'play' && !document.hidden && !this.captureInProgress && this.player) {
      this.accumulator += dt;
      const intent = this.input.intent;
      while (this.accumulator >= FIXED_STEP) {
        this.player.update(FIXED_STEP, intent, this.cameras.yaw);
        this.accumulator -= FIXED_STEP;
      }
      this.cameras.update(dt);
    } else this.accumulator = 0;
    this.render();
    if (time - this.sampleStart >= 500) {
      this.metrics.fps = this.sampleFrames * 1000 / (time - this.sampleStart);
      this.sampleFrames = 0;
      this.sampleStart = time;
      if (this.player) {
        let closest = Infinity;
        for (const [id, point] of Object.entries(LANDMARKS)) {
          const distance = Math.hypot(this.player.position.x - point[0], this.player.position.z - point[2]);
          if (distance < closest) { closest = distance; this.landmark = id; }
        }
      }
      this.onUpdate();
    }
  };

  private resize = () => {
    const width = Math.max(1, this.canvas.clientWidth);
    const height = Math.max(1, this.canvas.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    this.renderer.setSize(width, height, false);
    this.cameras.resize(width / height);
  };

  private contextLost = (event: Event) => {
    event.preventDefault();
    this.fail('The WebGL2 context was lost. Reload to reinitialize the renderer.');
  };

  private fail(message: string) {
    this.error = message;
    this.state = 'error';
    this.renderer.setAnimationLoop(null);
    this.onUpdate();
  }

  dispose() {
    this.disposed = true;
    this.renderer.setAnimationLoop(null);
    window.removeEventListener('resize', this.resize);
    this.canvas.removeEventListener('webglcontextlost', this.contextLost);
    this.input.dispose();
    this.player?.dispose();
    this.physics?.dispose();
    this.atmosphere.dispose();
    this.world.dispose();
    this.renderer.dispose();
  }
}
