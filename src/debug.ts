import { CAMERA_NAMES, type CameraName, type Cameras } from './camera';
import type { FrameMetrics, Game, GameState } from './game';
import { LANDMARKS, type ColliderDef } from './layout';
import type { Physics } from './physics';
import type { Player } from './player';
import { Vector3 } from 'three';
import type { World } from './world';

export interface AthenDebug {
  readonly version: string;
  readonly phase: 5;
  readonly world: World['assets'];
  readonly characters: Game['characters']['diagnostics'];
  readonly playerAnimation: import('./characters').CharacterInstance['diagnostics'] | null;
  readonly npcs: import('./npc').NPCSystem['diagnostics'] | null;
  readonly story: Game['story'];
  readonly inventory: Game['shop']['snapshot'];
  readonly dialogue: Game['dialogue'];
  readonly grid: Game['grid'];
  readonly interaction: Game['nearbyInteraction'];
  readonly logs: Game['logs'];
  readonly selectedHotbar: number;
  readonly state: GameState;
  readonly player: Player['snapshot'] | null;
  readonly fps: number;
  readonly draws: number;
  readonly tris: number;
  readonly ready: Promise<void>;
  readonly renderer: FrameMetrics & { webgl2: true };
  readonly physics: Physics['diagnostics'] | null;
  readonly camera: Cameras['snapshot'];
  readonly colliders: ColliderDef[];
  readonly landmarks: typeof LANDMARKS;
  readonly input: { forward: number; right: number; run: boolean };
  readonly cameras: readonly CameraName[];
  readonly cameraTransforms: Record<CameraName, { sceneObject: boolean; position: number[]; direction: number[]; fov: number; aspect: number }>;
  readonly activeCamera: string;
  readonly landmark: string;
  readonly error: string;
  readonly scope: string;
  nearbyColliders(radius?: number): unknown;
  shot(name: string): Promise<string>;
  goto(landmark: string): void;
  view(name: string): void;
  reset(): void;
  pause(value: boolean): void;
  timeOfDay: number;
}

declare global {
  interface Window {
    __ATHEN__: AthenDebug;
    __THREE_GAME_DIAGNOSTICS__: Record<string, unknown>;
  }
}

export function attachDebug(game: Game) {
  const api: AthenDebug = {
    version: '0.5.0-city-verbs', phase: 5,
    get world() { return structuredClone(game.world.assets); },
    get characters() { return game.characters.diagnostics; },
    get playerAnimation() { return game.player?.character.diagnostics ?? null; },
    get npcs() { return game.npcs?.diagnostics ?? null; },
    get story() { return game.story; },
    get inventory() { return game.shop.snapshot; },
    get dialogue() { return game.dialogue; },
    get grid() { return game.grid; },
    get interaction() { return game.nearbyInteraction; },
    get logs() { return structuredClone(game.logs); },
    get selectedHotbar() { return game.selectedHotbar; },
    get state() { return game.state; },
    get player() { return game.player?.snapshot ?? null; },
    get fps() { return game.metrics.fps; },
    get draws() { return game.metrics.draws; },
    get tris() { return game.metrics.tris; },
    get ready() { return game.ready; },
    get renderer() { return { ...game.metrics, webgl2: true as const }; },
    get physics() { return game.physics?.diagnostics ?? null; },
    get camera() { return game.cameras.snapshot; },
    get colliders() { return structuredClone(game.world.colliderDefs); },
    get landmarks() { return structuredClone(LANDMARKS); },
    get input() { return game.input.intent; },
    cameras: CAMERA_NAMES,
    get cameraTransforms() {
      const transforms = {} as AthenDebug['cameraTransforms'];
      for (const name of CAMERA_NAMES) {
        const camera = game.cameras.named[name];
        transforms[name] = { sceneObject: game.world.scene.getObjectByName(name) === camera,
          position: camera.position.toArray(), direction: camera.getWorldDirection(new Vector3()).toArray(),
          fov: camera.fov, aspect: camera.aspect };
      }
      return transforms;
    },
    get activeCamera() { return game.cameras.active.name; },
    get landmark() { return game.landmark; },
    get error() { return game.error; },
    scope: 'Phase 5 city verbs: four conversations, local buy/sell and Lattice sector connections. Audio and final beauty acceptance remain pending.',
    nearbyColliders: (radius = 3) => {
      if (!Number.isFinite(radius) || radius <= 0 || radius > 150) throw new Error('Radius must be greater than 0 and at most 150 metres.');
      return game.player && game.physics ? game.physics.nearby(game.player.position, radius) : [];
    },
    shot: (name) => game.shot(name),
    goto: (landmark) => game.goto(landmark),
    view: (name) => game.selectCamera(name),
    reset: () => game.reset(),
    pause: (value) => game.pause(value),
    get timeOfDay() { return game.timeOfDay; },
    set timeOfDay(value) { game.timeOfDay = value; },
  };
  window.__ATHEN__ = api;
  Object.defineProperty(window, '__THREE_GAME_DIAGNOSTICS__', {
    configurable: true,
    get: () => ({ version: api.version, phase: api.phase, state: api.state, player: api.player,
      renderer: api.renderer, physics: api.physics, camera: api.camera, activeCamera: api.activeCamera, error: api.error }),
  });
}
