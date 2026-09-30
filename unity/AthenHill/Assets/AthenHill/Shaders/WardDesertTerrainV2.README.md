# Ward Desert Terrain V2 (`Athen Hill/Ward Desert Terrain V2`)

Layered PBR terrain for the desert basin ("Desert Landscape", `Art/Terrain/DesertBasin.glb`).
It replaces `Athen Hill/Desert Terrain`, which rendered one sandstone albedo plus a
geology tint, with no normal maps, no roughness and minimal lighting.

It is a drop-in replacement:

- **Properties:** every old property keeps its meaning.
- **Vertex colours:** R is the authored noon shadow and G is the baked sky access, as
  before.
- **Globals:** `_AthenTerrainTime` and `_AthenTerrainHazeScale` (set by
  `CityTimeOfDay`) drive the same noon-shadow handover and the same distance haze.

Status (30 Sep 2026): the shader was written without opening Unity. It has had two
checks:

- **Compile check:** every pass compiles with `glslangValidator` (HLSL to SPIR-V)
  against stub declarations that match the URP 17.6 signatures in `Library/PackageCache`.
  Variants covered: base, cluster light loop with light layers and rendering layers,
  additional lights, ShadowCaster directional and punctual, DepthOnly, and DepthNormals
  with oct normals.
- **Visual check:** the albedo, normal and layer logic was mirrored on the CPU and
  ray-marched over a heightfield rasterised from the real `DesertBasin.glb`, with the
  real textures. Views: the West Gate mouth, a ground close-up and an overview, at noon
  and at 17:00.

**No native Unity compile, capture or GPU timing exists yet.**

## Textures used (all already in the project, no downloads)

| Slot | Asset | Why |
| --- | --- | --- |
| `_RockTex` (existing) | `Art/Terrain/SandstoneAlbedo.png` | Keeps the tuned mid-scale jointed sandstone, 13.7 m tiles at `_DetailScale` 0.073, so the far basin keeps its colour. |
| `_Geology` (existing) | `Art/Terrain/Geology.png` | Two macro octaves (111 m and about 410 m), an 11 m mid noise, and the varnish-streak pattern. |
| `_RockDetailAlbedo` | `Art/Courtyard/Textures/sandstone_cracks_diff_2k.jpg` | Poly Haven "Sandstone Cracks" (CC0, already credited in `Art/THIRD_PARTY_LICENSES.txt`). Weathered, cracked sandstone that fits the cliffs. |
| `_RockDetailNormal` | `Art/Courtyard/Textures/sandstone_cracks_nor_gl_2k.jpg` | Same set; already imported as a Normal map. |
| `_GroundAH` | `Art/WestGate/Ground/BermsGroundLayers_AH.png` (Texture2DArray) | The Berms Ground albedo + height array. Layer 0 is dry_ground_rocks (scree), layer 1 dense_sand (sand). |
| `_GroundNRA` | `Art/WestGate/Ground/BermsGroundLayers_NRA.png` (Texture2DArray) | Normal XY, roughness and AO for the same layers. Using the Berms layers at the Berms sizes (4 m and 1.8 m) makes the basin floor continuous with the Berms floor. |

Considered and not used:

- `rock_boulder_dry`: a grey granite look.
- HeroMasonry `rock_surface`: dark and flat.
- The `sandstone_cracks` smoothness map: it is almost all zero, so a constant
  `_RockSmoothness` is used instead.
- `sandy_gravel_02` (layer 2) and `dry_ground_01` (layer 3) are available through
  `_GravelLayer` and `_SandLayer`.

## Integration

1. **Create the material.** Duplicate `Materials/Terrain/SandstoneBasin.mat` as
   `Materials/Terrain/SandstoneBasinV2.mat` and set its shader to
   **Athen Hill/Ward Desert Terrain V2**. The existing values carry over:
   - `_RockTex`, `_Geology`
   - `_DetailScale` 0.073, `_Relief` 0.14, `_HazeDensity` 0.0068
   - `_Haze` (.66, .54, .40), `_Sand` (.59, .46, .30), `_RockTint` white

   Leftover `_Rock` and `_LightRock` values are ignored.
2. **Assign the new textures** as in the table above.
3. **Assign the material to the 8 basin renderers.** These are
   `DesertBasin_00.004` … `DesertBasin_07.004` under the "Desert Landscape" prefab
   instance. The scene overrides `m_Materials[0]` on each with `SandstoneBasin.mat`.
   Switching the shader on `SandstoneBasin.mat` in place also works, but the duplicate
   keeps a one-click rollback.
4. **Shadows.**
   - **Receiving:** the shader always receives shadows. URP ignores the renderer's
     Receive Shadows flag.
   - **Casting:** the scene sets Cast Shadows **Off** on those 8 renderers (the old
     shader had no ShadowCaster pass). Turn Cast Shadows **On** so the cliffs shadow
     the basin and the city approaches within the 150 m cascades. The basin is only
     5,120 triangles, so casting is cheap.
5. **Leave the clock alone.** `CityTimeOfDay` keeps writing `_AthenTerrainTime` and
   `_AthenTerrainHazeScale`. The noon-bake to live-shadow handover is identical to the
   old shader, and is merged into the main light's shadow term inside URP's PBR
   lighting.
6. **Check the Berms edge.** Berms Ground fades its edge to the old flat `_RockTex`
   look (`_EdgeBlend` 7 m). Where it meets the new basin, compare the look in the
   Berms overview. Lowering `_EdgeBlend` on `BermsGround.mat` should give a seamless
   join, because both now use the same ground layers.

## What it does

- **Layer masks.**
  - Rock where the slope (1 − n.y) exceeds `_RockSlope` (0.075, about 22°), broken up
    by noise.
  - Sand on flats and in hollows, driven by low baked sky access, low elevation and
    patch noise, controlled by `_SandAmount`.
  - Scree everywhere between.

  A height blend per layer (Berms style, `_HeightBlend`) then makes sand fill cracks
  and rock and scree keep their relief.
- **Cliff rock.**
  - Triplanar with whiteout normals. Each projection is skipped when its weight is
    under 2%.
  - The basin is mostly gentle: in the mesh, only 10% of its area is steeper than 37°.
    So most rock pixels sample only the plan view.
  - The mid sandstone uses two scales blended by noise.
  - The Sandstone Cracks detail is applied as albedo ÷ its mean (so the tuned hue is
    kept) plus a normal map.
  - The old `_Relief` screen-space bump is kept for mid-scale joints.
- **Strata.**
  - Folded horizontal beds in world Y (`_StrataThickness` 1.7 m) with finer
    laminations. Bed boundaries and laminations are antialiased by their own
    footprint.
  - Beds appear only on steep faces, `smoothstep(0.1, 0.45, slope)`, so gentle slopes
    do not show contour rings.
  - Ledges add relief (`_StrataRelief`).
  - Desert-varnish streaks hang from the ledges (`_StreakStrength`).
- **Sand ripples.** Skewed-sine crests across `_WindDirection`, with wavy crests
  (`_RippleWavelength` 0.2 m). A second megaripple octave at 9× the wavelength keeps
  the wind visible to about 50 m. Both fade with distance and their own pixel
  footprint.
- **Anti-tiling.**
  - Scree and sand use index bombing: an 11 m noise picks one of eight offsets, and
    neighbours cross-fade along the texture height. A second sample is fetched only in
    the blend zones.
  - Mid rock uses two scales and a domain warp.
  - Albedo is varied by two macro octaves and the 11 m noise.
- **Distance.** Detail textures fade to each layer's mean colour between
  `_DetailFadeStart` (40 m) and `_DetailFadeEnd` (140 m). Beyond that, scree, sand and
  rock detail are not sampled at all. The macro variation and mid rock carry the far
  basin.
- **Lighting and haze.**
  - URP PBR: InitializeBRDFData, GlobalIllumination (SH + probes, SSAO indirect) and
    LightingPhysicallyBased.
  - Cascaded and soft main-light shadows, light cookies and layers, and the Forward+
    cluster loop.
  - Then the unchanged Desert Terrain haze.
  - URP fog is available through `_FogBlend`, default 0. The scene's linear fog ends at
    420 m, so full fog would wash out the ridges beyond 420 m.
- **Passes.**
  - UniversalForward and ShadowCaster (URP bias, punctual variant).
  - DepthOnly.
  - DepthNormals with the geometric normal: PC_Renderer's SSAO reconstructs from depth,
    and a full-detail DepthNormals would double the cost.
  - SRP Batcher compatible.

## Properties

| Property | Default | Notes |
| --- | --- | --- |
| **Existing** `_RockTex`, `_Geology`, `_RockTint`, `_Sand`, `_Haze`, `_DetailScale`, `_Relief`, `_HazeDensity` | as before | Same meaning. `_Relief` also scales the detail normal: 0.14 = 1×. |
| `_MacroScale`, `_MacroStrength` | .009, .35 | Macro repeats per metre (the old value was hard-coded at .009); variation strength. |
| `_RockDetailAlbedo`, `_RockDetailNormal`, `_RockDetailMean` | –, –, (.641, .359, .177) | The mean is measured linear RGB of the albedo. Update it if you swap the texture. |
| `_RockDetailSize`, `_RockDetailStrength`, `_RockSmoothness` | 3.2 m, .6, .12 | About 640 px/m at player height. |
| `_StrataThickness`, `_StrataStrength`, `_StrataDark`, `_StrataLight` | 1.7 m, 1, (.73, .65, .56), (1.13, 1.03, .87) | The multipliers are the old bed colours. |
| `_StrataRelief`, `_StreakStrength` | .35, .3 | Ledges and desert varnish. |
| `_GroundAH`, `_GroundNRA`, `_GravelLayer`, `_SandLayer` | arrays, 0, 1 | Berms ground arrays. |
| `_GravelSize`, `_SandSize` | 4 m, 1.8 m | Matches Berms. |
| `_GravelColor`, `_GravelMean`, `_SandMean` | (.55, .44, .31), (.312, .182, .084), (.293, .218, .127) | Texture ÷ mean × colour; ratios are clamped at 1.8. |
| `_GroundNormalStrength` | 1.2 | Scree and sand normal strength. |
| `_RockSlope`, `_SlopeBlend`, `_SandAmount`, `_HeightBlend` | .075, .035, .5, .18 | Layer placement. |
| `_WindDirection`, `_RippleWavelength`, `_RippleStrength` | (−1, 0, .35), .2 m, 1 | Ripples. |
| `_DetailFadeStart`, `_DetailFadeEnd` | 40 m, 140 m | Near-detail range. |
| `_SkyOcclusion` | 1 | Baked sky access (vertex G) on indirect light, as the old shader did. |
| `_FogBlend` | 0 | URP fog blend. |

## Cost (estimate)

Texture samples per pixel, roughly, by where the pixel is:

| Case | Samples |
| --- | --- |
| Macro (every pixel) | 3 |
| Plan-view rock | 2 (far) or 4 (near) |
| Each side projection | 3 (far) or 5 (near) |
| Scree or sand, near only | 2–4 each (4 only in bombing blend zones) |

Totals:

| Situation | Total samples |
| --- | --- |
| Far basin, the typical full-screen case | 5–8 |
| Near sand flats | 7–11 |
| A near cliff with scree | 12–15 |
| A worst-case three-way near corner | about 20 |

ALU is about 600 ops plus URP lighting.

Expected GPU time on an RTX 3060 at 1080p: about 0.4–0.8 ms for a full-screen basin
with soft shadows and SSAO. Mostly distant views are cheaper. Measure it with the
profiler in the West Gate and Berms overview views.

## Tune first (native, 12:00 and 17:00)

1. **How much is rock.** `_RockSlope` (lower means more rock, closer to the old
   all-rock look) and `_SandAmount`.
2. **Bed readability.** `_StrataStrength`, `_StrataThickness` and `_StrataRelief` on
   the West Gate cliff face.
3. **Sand.** `_Sand` colour, and the ripple direction and strength against the actual
   wind and dust.
4. **Near-detail range.** `_DetailFadeStart` and `_DetailFadeEnd` against aliasing and
   cost.
5. **Berms edge.** The seam at the Berms edge (see integration step 6).
