import { PMREMGenerator, Scene, type Vector3, type WebGLRenderer, type WebGLRenderTarget } from 'three';
import { Sky } from 'three/addons/objects/Sky.js';

/** One analytic daylight sky and one prefiltered environment map; no GI. */
export class Atmosphere {
  readonly sky = new Sky();
  private environment: WebGLRenderTarget | null = null;
  private readonly renderer: WebGLRenderer;
  private readonly scene: Scene;
  private disposed = false;

  constructor(renderer: WebGLRenderer, scene: Scene, sun: Vector3) {
    this.renderer = renderer;
    this.scene = scene;
    this.sky.name = 'SKY_dusty_afternoon';
    this.sky.scale.setScalar(10000);
    this.sky.frustumCulled = false;
    const u = this.sky.material.uniforms;
    u.turbidity.value = 3.2;
    u.rayleigh.value = 2.4;
    u.mieCoefficient.value = 0.005;
    u.mieDirectionalG.value = 0.78;
    u.cloudCoverage.value = 0.24;
    u.cloudDensity.value = 0.28;
    u.cloudElevation.value = 0.42;
    scene.add(this.sky);
    scene.environmentIntensity = 0.35;
    this.syncSun(sun);
  }

  /** Called only for explicit time changes, never from the render loop. */
  syncSun(sun: Vector3) {
    if (this.disposed) return;
    const u = this.sky.material.uniforms;
    if (this.environment && u.sunPosition.value.equals(sun)) return;
    const previousSun = u.sunPosition.value.clone();
    u.sunPosition.value.copy(sun);
    const environmentScene = new Scene();
    const parent = this.sky.parent;
    const showSunDisc = u.showSunDisc.value;
    const pmrem = new PMREMGenerator(this.renderer);
    environmentScene.add(this.sky);
    u.showSunDisc.value = 0;
    try {
      const environment = pmrem.fromScene(environmentScene, 0.02, 0.1, 20000, { size: 128 });
      const previous = this.environment;
      this.environment = environment;
      this.scene.environment = environment.texture;
      previous?.dispose();
    } catch (error) {
      u.sunPosition.value.copy(previousSun);
      throw error;
    } finally {
      u.showSunDisc.value = showSunDisc;
      this.sky.removeFromParent();
      parent?.add(this.sky);
      pmrem.dispose();
    }
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    if (this.scene.environment === this.environment?.texture) this.scene.environment = null;
    this.environment?.dispose();
    this.environment = null;
    // The sky mesh remains owned by World.scene and is released by World.dispose().
  }
}
