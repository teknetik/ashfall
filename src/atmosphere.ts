import { Color, PMREMGenerator, Scene, type Vector3, type WebGLRenderer, type WebGLRenderTarget } from 'three';
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
    // Sky's daylight radiance is several linear units near the horizon. At
    // the scene's fixed ACES exposure that clips its colour almost to white.
    // Calibrate only sky radiance, before both display tone mapping and PMREM.
    u.skyRadianceScale = { value: 0.12 };
    u.groundRadiance = { value: new Color('#c9baa5').multiplyScalar(0.4125) };
    u.environmentPass = { value: 0 };
    const output = 'gl_FragColor = vec4( texColor, 1.0 );';
    if (!this.sky.material.fragmentShader.includes(output)) throw new Error('Unsupported analytic sky shader.');
    this.sky.material.fragmentShader = this.sky.material.fragmentShader
      .replace('uniform float time;', 'uniform float time;\n uniform float skyRadianceScale;\n uniform vec3 groundRadiance;\n uniform float environmentPass;')
      .replace(output, `
        // Broad aerosol scattering softens the spectral blue, with a longer,
        // warmer optical path near the horizon. Keep the analytic sun lobe.
        float dust = 0.18 + 0.30 * exp(-max(direction.y, 0.0) * 5.0);
        float luminance = dot(texColor, vec3(0.2126, 0.7152, 0.0722));
        vec3 aerosol = luminance * vec3(1.14, 1.0, 0.75);
        texColor = mix(texColor, aerosol, dust) * skyRadianceScale;
        // Distant low sightlines accumulate warm dust. This display haze is
        // separate from the local irradiance captured at the player's feet.
        float distantHaze = exp(-max(direction.y, 0.0) * 10.0) * (1.0 - environmentPass);
        texColor = mix(texColor, vec3(1.05, 0.82, 0.48), distantHaze);
        // An empty sky-only PMREM otherwise lights the lower hemisphere with
        // more blue horizon. Use sunlit sandstone bounce below the horizon.
        float ground = (1.0 - smoothstep(-0.06, 0.08, direction.y)) * environmentPass;
        texColor = mix(texColor, groundRadiance, ground);
        ${output}
      `);
    scene.add(this.sky);
    scene.environmentIntensity = 5.05;
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
    const environmentPass = u.environmentPass.value;
    const pmrem = new PMREMGenerator(this.renderer);
    environmentScene.add(this.sky);
    u.showSunDisc.value = 0;
    u.environmentPass.value = 1;
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
      u.environmentPass.value = environmentPass;
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
