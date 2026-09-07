import { CAMERA_NAMES, type CameraName } from './camera';
import type { FrameMetrics, Game, GameState } from './game';
import type { ProbeInfo } from './world';
import { Vector3 } from 'three';

export interface AthenDebug {
  readonly version: string;
  readonly phase: 0;
  readonly state: GameState;
  readonly player: { x: number; y: number; z: number; yaw: number };
  readonly fps: number;
  readonly draws: number;
  readonly tris: number;
  readonly ready: Promise<void>;
  readonly probe: ProbeInfo;
  readonly renderer: FrameMetrics & { webgl2: true };
  readonly cameras: readonly CameraName[];
  readonly cameraTransforms: Record<CameraName, { sceneObject: boolean; position: number[]; direction: number[]; fov: number; aspect: number }>;
  readonly activeCamera: string;
  readonly landmark: string;
  readonly error: string;
  readonly scope: string;
  shot(name: string): Promise<string>;
  goto(landmark: string): void;
  view(name: string): void;
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
    version: '0.0.1-phase0', phase: 0,
    get state() { return game.state; },
    get player() { return { ...game.player }; },
    get fps() { return game.metrics.fps; },
    get draws() { return game.metrics.draws; },
    get tris() { return game.metrics.tris; },
    get ready() { return game.ready; },
    get probe() { return structuredClone(game.world.probe); },
    get renderer() { return { ...game.metrics, webgl2: true as const }; },
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
    scope: 'Phase 0 pipeline probe. Player is an anchor only; named cameras frame the Blender cube. City and walking begin in Phase 1.',
    shot: (name) => game.shot(name),
    goto: (landmark) => game.goto(landmark),
    view: (name) => game.selectCamera(name),
    get timeOfDay() { return game.timeOfDay; },
    set timeOfDay(value) { game.timeOfDay = value; },
  };
  window.__ATHEN__ = api;
  Object.defineProperty(window, '__THREE_GAME_DIAGNOSTICS__', {
    configurable: true,
    get: () => ({ version: api.version, phase: api.phase, state: api.state, player: api.player,
      renderer: api.renderer, probe: api.probe, activeCamera: api.activeCamera, error: api.error }),
  });
}
