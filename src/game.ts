import { ACESFilmicToneMapping, PCFShadowMap, SRGBColorSpace, Vector2, WebGLRenderer } from 'three';
import { CAMERA_NAMES, Cameras, NAMED_VERTICAL_FOV, type CameraName } from './camera';
import { World } from './world';
import { LANDMARKS, LANDMARK_LABELS } from './layout';
import { Input } from './input';
import { Physics, FIXED_STEP } from './physics';
import { Player } from './player';
import { Atmosphere } from './atmosphere';
import { CharacterLibrary } from './characters';
import { NPCSystem } from './npc';
import { Shop, type ItemId } from './shop';
import { getDialogue } from './dialogue';
import type { NamedNPCId } from './npc';
import { TravelSystem } from './travel';

export type GameState = 'boot' | 'play' | 'dialogue' | 'shop' | 'grid' | 'paused' | 'error';
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
  readonly characters = new CharacterLibrary();
  readonly shop = new Shop();
  readonly travel = new TravelSystem(this.world.scene);
  npcs: NPCSystem | null = null;
  readonly cameras = new Cameras(this.world.scene);
  readonly input: Input;
  player: Player | null = null;
  physics: Physics | null = null;
  readonly metrics: FrameMetrics = { fps: 0, frameMs: 0, draws: 0, tris: 0, geometries: 0, textures: 0, width: 0, height: 0, pixelRatio: 1 };
  readonly ready: Promise<void>;
  state: GameState = 'boot';
  error = '';
  landmark = 'west_gate';
  selectedHotbar = 0;
  readonly logs: Array<{ id: number; speaker: string; text: string }> = [
    { id: 1, speaker: 'System', text: 'West Gate. Welcome to Athen Hill.' },
    { id: 2, speaker: 'Linn', text: 'Meet me on the hill.' },
  ];
  toast = '';
  private toastRemaining = 0;
  private logSequence = 2;
  private activeNPC: NamedNPCId | null = null;
  private dialogueNode = 'greeting';
  private readonly spoken = new Set<NamedNPCId>();
  private visitedHill = false;
  private boughtFlask = false;
  private soldScrap = false;
  private linked = false;
  private ringInside = false;
  private accumulator = 0;
  private captureInProgress = false;
  private hour = 16;
  private disposed = false;
  private readonly reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
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
    this.travel.setReducedMotion(this.reducedMotion.matches);
    this.reducedMotion.addEventListener('change', this.motionChanged);
    this.input.onOrbit = (x, y) => {
      if (this.state !== 'play') return;
      this.cameras.orbit(x, y);
    };
    this.input.onMove = () => {
      if (this.state === 'play' && this.cameras.active !== this.cameras.follow) this.cameras.select('follow');
    };
    this.input.onPause = () => {
      if (['dialogue', 'shop', 'grid'].includes(this.state)) this.closeOverlay();
      else this.pause(this.state !== 'paused');
    };
    this.input.onReset = () => this.reset();
    this.input.onInteract = () => this.interact();
    this.input.onHotbar = (index) => this.selectHotbar(index);
    this.world.setSun(this.hour);
    this.atmosphere = new Atmosphere(this.renderer, this.world.scene, this.world.sun.position);
    this.resize();
    window.addEventListener('resize', this.resize);
    canvas.addEventListener('webglcontextlost', this.contextLost);
    this.ready = Promise.all([this.world.load(), this.characters.load()]).then(async () => {
      await this.characters.loadGuard();
      if (this.disposed) return;
      if (this.state === 'error') throw new Error(this.error);
      const physics = await Physics.create(this.world.colliderDefs);
      if (this.disposed) { physics.dispose(); return; }
      if (this.error) { physics.dispose(); throw new Error(this.error); }
      this.physics = physics;
      this.player = new Player(physics, this.world.scene, LANDMARKS.west_gate,
        this.characters.create({ id: 'player_colonist', kind: 'player' }));
      this.npcs = new NPCSystem(this.world.scene, this.characters, this.canvas.parentElement!);
      this.npcs.onInteract = (target) => {
        this.activeNPC = target.id;
        this.dialogueNode = 'greeting';
        this.spoken.add(target.id);
        this.npcs?.setTalking(target.id, true);
        this.openOverlay('dialogue');
        this.log(target.name, getDialogue(target.id).text);
      };
      this.cameras.attach(physics, this.player);
      this.cameras.update(0, true);
      this.state = 'play';
      this.onUpdate();
    }).catch((error: unknown) => {
      if (!this.disposed) this.fail(error instanceof Error ? error.message : 'The city could not be loaded.');
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

  get dialogue() {
    return this.state === 'dialogue' && this.activeNPC ? getDialogue(this.activeNPC, this.dialogueNode) : null;
  }

  get grid() { return this.state === 'grid' ? this.travel.snapshot : null; }

  get story() {
    const complete = this.visitedHill && this.spoken.size === 4 && this.boughtFlask && this.soldScrap && this.linked;
    const objective = !this.visitedHill ? 'Reach the Hill Tree.'
      : this.spoken.size < 4 ? `Meet the colonists · ${this.spoken.size}/4 conversations`
      : !this.boughtFlask || !this.soldScrap ? 'Buy a flask and sell your scrap at Basic General.'
      : !this.linked ? 'Use the Lattice Jack in the north court.' : 'A place on the hill. City visit complete.';
    return { spokenCount: this.spoken.size, spokenNPCs: [...this.spoken], visitedHill: this.visitedHill,
      boughtFlask: this.boughtFlask, soldScrap: this.soldScrap, linked: this.linked, complete, objective };
  }

  get nearbyInteraction(): { label: string; kind: 'npc' | 'lattice' | 'ring' } | null {
    if (this.state !== 'play' || !this.player) return null;
    const npc = this.npcs?.nearest;
    if (npc) return { label: `Talk to ${npc.name}`, kind: 'npc' };
    const p = this.player.position;
    if (Math.hypot(p.x, p.z + 39) < 3.15 && Math.abs(p.y - .5) < .8) return { label: 'Use Lattice Jack', kind: 'lattice' };
    if (Math.abs(p.x) < 5.4 && Math.abs(p.z - 36.1) < 2.8) return { label: 'Check Ring Gate', kind: 'ring' };
    return null;
  }

  private log(speaker: string, text: string) {
    this.logs.push({ id: ++this.logSequence, speaker, text });
    if (this.logs.length > 16) this.logs.shift();
  }

  private notify(text: string) {
    this.toast = text;
    this.toastRemaining = 4;
    this.onUpdate();
  }

  private openOverlay(state: 'dialogue' | 'shop' | 'grid') {
    this.input.clear();
    this.accumulator = 0;
    this.state = state;
    this.onUpdate();
  }

  interact() {
    if (this.state !== 'play') return;
    const target = this.nearbyInteraction;
    if (target?.kind === 'npc') this.npcs?.interact();
    else if (target?.kind === 'lattice') {
      this.travel.start();
      this.openOverlay('grid');
      this.log('Lattice Jack', 'Signal acquired. Opening the sector lattice.');
    } else if (target?.kind === 'ring') this.ringBark();
    else this.notify('Move closer to a colonist or terminal.');
  }

  chooseDialogue(id: string) {
    const node = this.dialogue;
    const choice = node?.choices.find((candidate) => candidate.id === id);
    if (!choice || !this.activeNPC) return;
    this.log('You', choice.label);
    if (choice.action === 'shop') this.openOverlay('shop');
    else if (choice.action === 'close') this.closeOverlay();
    else if (choice.next) {
      this.dialogueNode = choice.next;
      this.log(node!.speaker, getDialogue(this.activeNPC, choice.next).text);
      this.onUpdate();
    }
  }

  closeOverlay() {
    if (!['dialogue', 'shop', 'grid'].includes(this.state)) return;
    if (this.activeNPC) this.npcs?.setTalking(this.activeNPC, false);
    this.activeNPC = null;
    this.travel.close();
    this.state = 'play';
    this.input.clear();
    this.accumulator = 0;
    this.onUpdate();
    this.canvas.focus({ preventScroll: true });
  }

  buyItem(id: ItemId) {
    if (this.state !== 'shop') return false;
    const result = this.shop.buy(id);
    if (result.ok && id === 'water_flask') this.boughtFlask = true;
    this.log('Mira', result.message);
    this.notify(result.message);
    return result.ok;
  }

  sellItem(id: ItemId) {
    if (this.state !== 'shop') return false;
    const result = this.shop.sell(id);
    if (result.ok && id === 'scrap_coil') this.soldScrap = true;
    this.log('Mira', result.message);
    this.notify(result.message);
    return result.ok;
  }

  selectGridNode(id: string) {
    if (this.state !== 'grid') return false;
    const result = this.travel.selectNode(id);
    if (result.ok) this.linked = true;
    this.log('Lattice Jack', result.message);
    this.notify(result.message);
    return result.ok;
  }

  selectHotbar(index: number) {
    if (!Number.isInteger(index) || index < 0 || index > 5 || this.state !== 'play') return;
    this.selectedHotbar = index;
    if (index < 2) {
      const item = this.shop.snapshot.items.find((row) => row.id === (index === 0 ? 'water_flask' : 'medkit'))!;
      this.notify(`${item.name} · ${item.quantity} carried. ${item.description}`);
    } else if (index === 2) {
      if (this.nearbyInteraction?.kind === 'lattice') this.interact();
      else this.notify('The Lattice Jack is in the north court, beyond the hill.');
    } else if (index === 3) {
      if (this.npcs?.nearest) this.interact();
      else this.notify('Move close to a colonist to talk.');
    }
    this.onUpdate();
    if (this.state === 'play' && index < 4) this.canvas.focus({ preventScroll: true });
  }

  private ringBark() {
    const text = 'Destination offline. The far ring has gone quiet.';
    this.log('Ring Gate', text);
    this.notify(text);
  }

  pause(value: boolean) {
    if (this.state !== 'play' && this.state !== 'paused') return;
    this.state = value ? 'paused' : 'play';
    this.accumulator = 0;
    this.input.clear();
    this.onUpdate();
  }

  reset() {
    if (!this.player || this.state === 'error') return;
    this.closeOverlay();
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
      if (Math.hypot(this.player.position.x, this.player.position.z) < 7 && this.player.position.y > 1) this.visitedHill = true;
      const p = this.player.position;
      const inRing = Math.abs(p.x) < 5.4 && Math.abs(p.z - 36.1) < 2.6 && p.y > .3;
      if (inRing && !this.ringInside) this.ringBark();
      this.ringInside = inRing;
    } else this.accumulator = 0;
    const live = !['paused', 'boot', 'error'].includes(this.state) && !document.hidden;
    this.npcs?.update(live ? dt : 0,
      this.player ? { position: this.player.position, yaw: this.player.snapshot.yaw } : null);
    this.npcs?.projectLabels(this.cameras.active, this.canvas, this.state === 'play');
    if (live && this.state !== 'play') this.player?.character.update(dt, { speed: 0, talking: this.state === 'dialogue' });
    if (this.state === 'grid' && live) {
      const before = this.travel.snapshot?.phase;
      this.travel.update(dt);
      if (before !== this.travel.snapshot?.phase) this.onUpdate();
    }
    if (live && this.toastRemaining > 0) {
      this.toastRemaining = Math.max(0, this.toastRemaining - dt);
      if (!this.toastRemaining) { this.toast = ''; this.onUpdate(); }
    }
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

  private motionChanged = () => this.travel.setReducedMotion(this.reducedMotion.matches);

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
    this.reducedMotion.removeEventListener('change', this.motionChanged);
    this.input.dispose();
    this.player?.dispose();
    this.npcs?.dispose();
    this.characters.dispose();
    this.travel.dispose();
    this.physics?.dispose();
    this.atmosphere.dispose();
    this.world.dispose();
    this.renderer.dispose();
  }
}
