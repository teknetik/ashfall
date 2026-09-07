import { ACESFilmicToneMapping, PCFShadowMap, SRGBColorSpace, Vector2, Vector3, WebGLRenderer } from 'three';
import { CAMERA_NAMES, Cameras, LANDMARKS, PROBE_VERTICAL_FOV, type CameraName } from './camera';
import { World } from './world';

export type GameState = 'boot' | 'probe' | 'error';
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
  readonly world = new World();
  readonly cameras = new Cameras(this.world.scene);
  readonly player = { x: 0, y: 0, z: 0, yaw: 0 };
  readonly metrics: FrameMetrics = { fps: 0, frameMs: 0, draws: 0, tris: 0, geometries: 0, textures: 0, width: 0, height: 0, pixelRatio: 1 };
  readonly ready: Promise<void>;
  state: GameState = 'boot';
  error = '';
  landmark = 'probe';
  private hour = 16;
  private disposed = false;
  private previousFrame = 0;
  private sampleStart = 0;
  private sampleFrames = 0;
  private captureQueue: Promise<unknown> = Promise.resolve();
  onUpdate: () => void = () => {};

  constructor(readonly canvas: HTMLCanvasElement) {
    const context = canvas.getContext('webgl2', { antialias: true, alpha: false });
    if (!context) throw new Error('A WebGL2 browser is required to render the pipeline probe.');
    this.renderer = new WebGLRenderer({ canvas, context, antialias: true });
    this.renderer.outputColorSpace = SRGBColorSpace;
    this.renderer.toneMapping = ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = PCFShadowMap;
    // Count the shadow pass together with the visible pass, resetting once per complete frame.
    this.renderer.info.autoReset = false;
    this.world.setSun(this.hour);
    this.resize();
    window.addEventListener('resize', this.resize);
    canvas.addEventListener('webglcontextlost', this.contextLost);
    this.ready = this.world.load().then(() => {
      if (this.disposed) return;
      if (this.state === 'error') throw new Error(this.error);
      this.state = 'probe';
      this.onUpdate();
    }).catch((error: unknown) => {
      this.fail(error instanceof Error ? error.message : 'The Blender probe could not be loaded.');
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
  }

  selectCamera(name: string) {
    this.cameras.select(name);
    this.onUpdate();
  }

  goto(landmark: string) {
    const coordinates = Object.hasOwn(LANDMARKS, landmark) ? LANDMARKS[landmark] : undefined;
    if (!coordinates) throw new Error(`Unknown landmark: ${landmark}`);
    [this.player.x, this.player.y, this.player.z] = coordinates;
    this.landmark = landmark;
    this.cameras.anchor(new Vector3(...coordinates));
    this.onUpdate();
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
    let dataUrl: string;
    // All render and restoration work is synchronous, before any promise can yield to the main loop.
    try {
      this.renderer.setPixelRatio(1);
      this.renderer.setSize(1920, 1080, false);
      camera.aspect = 1920 / 1080;
      camera.fov = PROBE_VERTICAL_FOV;
      camera.updateProjectionMatrix();
      this.renderer.info.reset();
      this.renderer.render(this.world.scene, camera);
      dataUrl = this.canvas.toDataURL('image/png');
    } finally {
      camera.aspect = aspect;
      camera.fov = fov;
      camera.updateProjectionMatrix();
      this.renderer.setPixelRatio(pixelRatio);
      this.renderer.setSize(size.x, size.y, false);
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
    if (this.previousFrame) this.metrics.frameMs = time - this.previousFrame;
    this.previousFrame = time;
    this.render();
    if (time - this.sampleStart >= 500) {
      this.metrics.fps = this.sampleFrames * 1000 / (time - this.sampleStart);
      this.sampleFrames = 0;
      this.sampleStart = time;
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
    this.world.scene.traverse((object) => {
      const mesh = object as import('three').Mesh;
      mesh.geometry?.dispose();
      const materials = mesh.material ? (Array.isArray(mesh.material) ? mesh.material : [mesh.material]) : [];
      for (const material of materials) material.dispose();
    });
    this.renderer.dispose();
  }
}
