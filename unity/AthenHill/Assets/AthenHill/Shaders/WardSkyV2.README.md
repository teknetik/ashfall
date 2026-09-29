# Ward Sky V2 (`Athen Hill/Ward Sky V2`)

`WardSkyV2.shader` is a procedural day/night skybox that drops in for the current
time-aware sky. It accepts every property of `Athen Hill/Ward Reference Sky`,
`Athen Hill/Ward Day Night Sky` and `Athen Hill/Desert Atmosphere`, with the same
meaning. Integrating it means changing one material's shader. Nothing else in code
or the scene needs to change.

Status (29 Sep 2026): the file was written without opening Unity. The HLSL body
compiles to SPIR-V with `glslangValidator`, using stubs for `UnityCG` and the
`tex2D`/`tex2Dlod` calls. A CPU (numpy) mirror of the shader was used to calibrate
constants and compare it with the current sky. **No native Unity compile, capture or
GPU timing exists yet.** Treat everything below as unverified in the game until
the integrator has tested it.

## What is in use today

| Item | Current value |
| --- | --- |
| Sky driven at runtime | `CityTimeOfDay.timeAwareSky` in `Scenes/AthenHill.unity` = `Art/ReferenceStreet/20260909/WardReferenceSky.mat` (shader `Athen Hill/Ward Reference Sky`) |
| Saved `RenderSettings.skybox` | `Materials/DesertSky.mat` (shader `Athen Hill/Desert Atmosphere`). The Editor shows it when not playing. In Play mode `CityTimeOfDay.OnEnable` replaces it with a runtime copy of `timeAwareSky`. |
| Profile | `Art/Atmosphere/Dustbowl/WardDustbowl.asset` (default hour 17) |

## How to switch

1. **Recommended, keeps a rollback:** duplicate `WardReferenceSky.mat` as
   `WardSkyV2.mat` in the same folder, set its shader to **Athen Hill/Ward Sky V2**,
   and assign it to `CityTimeOfDay.timeAwareSky` on the city clock object. Saved
   values (`_Noise` = `AtmosphereNoise`, `_Coverage` .53, `_CloudScale` 4.6,
   `_CloudEdge` .055, `_WispStrength` .07, `_CloudOpacity` .8, `_RidgeStrength` 0)
   carry over. The new properties take the defaults listed below.
2. **Minimal alternative:** change the shader on `WardReferenceSky.mat` itself.
3. Optionally switch `DesertSky.mat` as well, so the Editor Scene view matches. That
   material has no saved `_SunDirection`, so V2 would place the sun at the zenith.
   Copy `_SunDirection` across (for example from `WardReferenceSky.mat`), or leave
   `DesertSky.mat` alone.
4. Unused leftover values on those materials (`_AtmosphereThickness`, `_SunDisk`,
   `_SunSizeConvergence`, `_SkyTint`, `_GroundColor`) are ignored.
5. Editor passes still call `Shader.Find` with the old shader names
   (`ReferenceStreetPass.cs:250`, `DayNightPass.cs:34`, `AtmospherePass.cs:108`).
   Running them again would bring the old shaders back. NativeQa's `skyShader`
   evidence field will now read `Athen Hill/Ward Sky V2`.

## How the scripts drive it

- In Play mode, `CityTimeOfDay.OnEnable` makes a runtime copy of `timeAwareSky`
  and sets it as `RenderSettings.skybox`. On each clock change, `Apply()` writes
  these values from `DayNightLightingProfile.Evaluate(hour)`:
  - `_Zenith`, `_Middle`, `_Horizon`
  - `_CloudLight`, `_CloudShade`, `_RidgeColor`
  - `_Exposure` (the frame's `skyExposure`)
  - `_SunVisibility`
  - `_SunDirection`, set to `-keyLight.transform.forward`
- Unity converts Color properties to linear space. V2 uses them as linear radiance,
  exactly as the old shaders did.
- `CityAtmosphere` sets the global `_AthenAtmosphereTime`, which advances by
  `Time.deltaTime * windSpeed`. With `session.reducedMotion` on, the clock stops.
  Every animated term in V2 is driven by this clock: cloud drift, cloud evolution,
  cirrus drift and star twinkle. **Reduced Motion therefore freezes all of them.**
  `_CloudSpeed = 0` also freezes the clouds. The clock is 0 outside Play mode, which
  gives a static preview.

## Properties

### Existing properties (same meaning)

| Property | Default | Notes |
| --- | --- | --- |
| `_Noise` | gray | Must be `Art/Atmosphere/AtmosphereNoise.asset`, a 256² RGB periodic Perlin texture with 16, 42 and 91 cells per tile. |
| `_Zenith`, `_Middle`, `_Horizon` | .24/.39/.57, .54/.64/.68, .83/.68/.47 | The profile palette. The gradient blends the same colours, but the flat horizon band is replaced by an exponential falloff. |
| `_CloudLight`, `_CloudShade` | .96/.86/.68, .48/.55/.60 | Sunlit and shadowed cloud colours. `_CloudLight` also sets the colour of the sun, the Mie glow and the silver linings (the attenuated sunlight). |
| `_Coverage` | .48 | Calibrated to the old texture FBM (mean .47, std .075). The same value covers the same share of the sky: .53 ≈ 49%, .3 is clear, .7 ≈ 99%. |
| `_CloudScale` | 4.6 | Zenith feature size matches the previous shaders. |
| `_CloudEdge` | .055 | Edge softness, as `smoothstep(thr ± edge)`. |
| `_CloudOpacity` | .78 | Maximum cloud alpha. |
| `_WispStrength` | .035 | Cirrus strength. Peak alpha = `_WispStrength × _CirrusOpacity`. |
| `_CloudSpeed` | .0007 | Drift in noise cells per second of `_AthenAtmosphereTime`. 0 freezes the clouds. Slider range widened to .02. |
| `_Exposure` | 1 | Final multiplier. |
| `_SunSize` | .009 | Sun radius in radians. |
| `_SunVisibility` | 1 | Fades the sun disc, corona, Mie glow and horizon dust glow. It also drives night visibility: `1 - _SunVisibility`. |
| `_SunDirection` | (0,1,0) | Direction toward the sun. |
| `_RidgeColor`, `_RidgeStrength` | .61/.53/.42, .48 | Optional horizon ridges; the scene materials use 0. Silhouettes match the old ones, now drawn as two depths with haze at the base and a rim on the sunward side. `_RidgeColor` also tints the ground below the horizon. |

### New properties

| Group | Property | Default | Effect |
| --- | --- | --- | --- |
| Atmosphere | `_RayleighStrength` | .35 | Rayleigh phase modulation `3/4(1+μ²)`. Its mean over the sphere is 1, so it adds no energy. |
| | `_MieStrength`, `_MieG` | 1, .76 | Henyey-Greenstein aureole around the sun. Mean over the sphere is 0.012 × `_CloudLight`. |
| | `_HorizonDustGlow` | .6 | With a low sun, the sunward horizon gets warmer and the far side cooler. Azimuthal mean is 1. |
| | `_HorizonHaze` | .5 | Thin bright haze band that straddles the horizon. |
| | `_GroundDarkening` | .35 | Below the horizon: haze first, then a subtle ground tint. |
| Sun | `_SunIntensity` | 8 | **Mean** radiance of the disc. 4 reproduces the old `disc*4`. |
| | `_SunLimbDarkening` | 1 | Per-channel `μ^α` with α = (.397, .503, .652), which gives a redder limb. Normalised so the mean stays at `_SunIntensity`. |
| | `_SunCorona` | 1 | Old halo `.28·e^(-18θ)` plus a tight glow just outside the disc. |
| | `_SunTint` | white | Multiplies the derived sun colour: `_CloudLight` normalised to a peak of 1, then desaturated 30%. |
| Cumulus | `_CloudWind` (xz) | (-1,0,0) | World direction the clouds travel. The default matches the old drift. |
| | `_CloudEvolve` | .5 | How fast the shapes morph, relative to drift. |
| | `_PlanetRadius` | 50 | Curvature of the cloud shell, in cloud-base heights. The horizon is ~10× farther than the zenith. |
| | `_CloudDetail` | .6 | Weight of the texture octaves (calibrated at .6). |
| | `_CloudAbsorption`, `_CloudLightStep` | 6, .35 | Self-shadow optical depth and the length of the light march. |
| | `_CloudSilver`, `_CloudForward` | 1.2, .6 | Silver-lining strength and the HG `g` value. |
| | `_CloudBaseDarkening` | .5 | Dark flat cloud bases when looking up. |
| | `_CloudHaze`, `_CloudHorizonFade` | .15, .08 | Aerial perspective on distant cloud, and the elevation where clouds fade in. |
| Cirrus | `_CirrusCoverage`, `_CirrusScale`, `_CirrusOpacity`, `_CirrusSpeed` | .5, 1, 3, 1.6 | Upper streak layer. `_CirrusOpacity` 1 gives the old maximum alpha. |
| Night | `_MoonSource` | KeyLight | Where the moon is placed. **KeyLight:** at the key-light direction (see below). **OppositeSun:** at `-_SunDirection`. **MoonDirection:** at `_MoonDirection` (default (0,.5,-.85)). |
| | `_MoonSize`, `_MoonColor`, `_MoonIntensity`, `_MoonGlow` | .012, .80/.86/1, 1.2, 1 | Full disc with maria taken from `_Noise`, plus a glow that does not depend on phase. |
| | `_StarDensity`, `_StarBrightness` | .5, 1 | Stars, peaking at about 0.04–1.6 HDR. |
| | `_StarTwinkle`, `_StarTwinkleSpeed` | .35, 3 | Twinkle is stronger near the horizon and frozen when the clock stops. |
| | `_GalaxyStrength`, `_GalaxyPole` | .6, (.42,.62,-.66) | Galactic band with star clouds and a dust lane. |

**Why the moon defaults to KeyLight.** `WardDustbowl` turns the key light into
moonlight at night: at 00:00 it is at (32°, 40°), blue and at 0.07 intensity. So
`_SunDirection` at night already points at the moon, 20–32° above the horizon.
`-_SunDirection` would put the moon below the horizon all night. KeyLight also
keeps the disc lined up with the night shadows.

Side effect: during the 17:30→19:00 and 05:30→06:30 blends the key light swings
across the sky, and the moon (visible once `_SunVisibility` < 0.4) moves with it. A
proper fix is for `CityTimeOfDay` to write `_MoonDirection` and use `_MoonSource` =
MoonDirection. That is a script change, so it was not made here.

## Technique summary

- **Atmosphere.** The profile palette is shaped by an extinction-like curve,
  `1 - e^(-7h)`, with the zenith blend `h^0.65` kept as before. On top of that:
  energy-neutral Rayleigh phase, an HG Mie aureole, energy-neutral sunward dust
  glow at low sun, and a horizon haze band. Below the horizon the colour moves to
  haze and then a ground tint.
- **Cumulus.**
  - The ray meets a curved shell of radius R+1 (a stable quadratic), so clouds get
    smaller and flatter toward the horizon.
  - A gentle domain warp comes from two contrast-corrected R-channel lookups.
  - FBM: an ALU gradient-noise base octave, which never repeats, plus three
    rotated texture octaves at 2.03, 4.3 and 9.1 cells.
  - Coverage threshold, then a Nyquist fallback: when the pixel footprint gets too
    large near the horizon, the result blends to the expected coverage.
  - Self-shadowing: the density is extrapolated 0.5 and 1.5 steps toward the light
    using the analytic noise gradient, then Beer's law is applied. In CPU tests
    this was visually identical to a real two-sample march, at no extra fetch cost.
  - Shading: dark bases seen overhead, darker backlit cores, an HG silver lining
    on thin edges (HDR), and aerial perspective into the sky colour.
- **Cirrus.** A higher shell (4× the cumulus height, so less foreshortened) with
  fibres stretched along a wind turned 20°. Texture streaks, broken into patches,
  lit by strong forward scattering.
- **Night.**
  - Stars are hashed on a 3D grid. A star is kept only if it projects back into its
    own cell, so none are clipped. Each has a Gaussian footprint at least ~0.8 px
    wide, normalised so its energy stays the same at any size.
  - Stars fade with the local sky brightness, near the horizon, and behind cloud.
  - The galactic band uses a two-plane projection so the texture is never smeared
    across it.
  - The moon disc and glow are hidden behind cloud cover, and clouds get a faint
    moonlit silver lining.
- **No visible tiling.**
  - `AtmosphereNoise` was made periodic by bilinearly blending four Perlin samples.
    That leaves its contrast about 2.2× lower at the tile centre than at the edges:
    the measured standard deviation is 0.069 at the centre and 0.154 at the corners.
    This contrast grid is one cause of the repetition seen with the old sky.
  - `Destripe()` divides the deviation back out, which evens the contrast: after
    correction the G and B channels measure 0.15–0.18 at both centre and corners.
  - The large cloud masses come from ALU noise, not the texture.

## Luminance scale (linear HDR, before post-exposure and ACES)

A palette value of 1.0 means radiance 1.0 at `_Exposure` 1, as in the old shaders.
In the CPU mirror, the solid-angle-weighted upper-hemisphere mean luminance of V2,
compared with the current Reference Sky and using the same WardDustbowl frames and
materials:

| Frame | Old | V2 | Ratio | Cause of the difference |
| --- | --- | --- | --- | --- |
| 12:00 | 0.307 | 0.329 | 1.07 | |
| 17:00 | 0.165 | 0.170 | 1.03 | |
| 17:30 | 0.100 | 0.102 | 1.02 | |
| 00:00 | 0.0030 | 0.0040 | 1.33 | Added stars, galaxy and moon aureole on a tiny base |

Only the sun disc (about 10 at its centre), the moon disc (about 1.2) and the
silver linings or cirrus near the sun exceed 1.0; these are the bloom sources.
If night exposure is too bright, lower `_MoonGlow` or `_GalaxyStrength`.

## Performance (estimate, not measured)

| Case | Cost per pixel |
| --- | --- |
| Clouded day pixel | ~700–750 scalar ALU and 8 bilinear/trilinear fetches of one 256² texture; there are no loops |
| Night | adds ~150–250 ALU and 4 explicit-LOD fetches; the sun section is skipped |
| `_RidgeStrength` > 0 | adds ~80 ALU and 3 fetches |

The sun, night and ridge sections sit behind uniform branches, so each is skipped
entirely when it is off.

Expected GPU time on an RTX 3060 at 1920×1080:

| Sky coverage of the screen | Expected time |
| --- | --- |
| Full screen (worst case) | ~0.25–0.35 ms |
| Typical street view, 30–50% sky | ~0.1–0.15 ms |

Measure it natively in the profiler: time `DrawSkybox` or the Skybox pass while
looking straight up, then in `cam_avenue`. The cheapest optional saving is to set
`_WispStrength` to 0, which removes the cirrus contribution. Its ALU and 3 fetches
still run, because there is no branch around them.

## What to tune first (in-game, matched cameras)

1. **Before/after on the same view.** Compare `_Coverage`, `_CloudScale` and
   `_CloudDetail` against the old sky in `cam_hill`, `cam_avenue` and `cam_gate`.
2. **Cloud volume.** Adjust `_CloudAbsorption` and `_CloudBaseDarkening`. The
   profile's `cloudShade` is brownish at noon, and cores can read as dirty.
3. **Bloom.** Adjust `_SunIntensity` against the volume's bloom threshold (4 = old
   look), and `_CloudSilver`.
4. **Horizon.** Adjust `_PlanetRadius`, `_CloudHaze` and `_CloudHorizonFade`. A
   larger radius gives more foreshortening but a busier band near the horizon.
5. **Night.** Review in the 19:00 and 00:00 frames. Check `_StarBrightness` with
   post-exposure at +0.25, the moon behaviour during the dusk blend, and the cirrus
   streaks, which can read as light shafts at the zenith. Lower `_CirrusOpacity` if
   they do.

## Checks for the integrator

- Compile on Linux OpenGLCore and check the console for shader warnings.
- Play-mode sweep through 05:30, 06:30, 12:00, 17:00, 17:30, 19:00 and 00:00.
- Toggle Reduced Motion: clouds and twinkle should freeze.
- Set `_CloudSpeed` to 0: clouds should be static.
- Check reflection-probe refreshes from `CityTimeReflections` at night; stars
  should be faint, not sparkly.
- Take native captures and a GPU time measurement, and record the evidence under
  `unity/evidence/`.
