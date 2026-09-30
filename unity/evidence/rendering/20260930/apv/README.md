# APV sky occlusion — status 30 Sep 2026: configured, bake blocked on this host

Recipe: `docs/apv-sky-occlusion-recipe.md`. Script: `Assets/AthenHill/Editor/ApvSkyOcclusionBake.cs`
(ConfigureBatch, DiagnoseBatch, BakeBatch).

## What is in place
- Baking set `Scenes/AthenHill/AthenHill Baking Set.asset` (sky occlusion, 2 m min spacing, 1024 samples, 2 bounces,
  albedo 0.45, sky direction, dilation + virtual offset), town volume from scene bounds (176 × 29 × 114 m) and a
  coarse basin volume, LightingSettings asset, Probe Volume options on the grade volume.
- 1,469 opaque static renderers marked ContributeGI and receive-GI = light probes, recorded as prefab overrides where
  needed (diagnose.json: 0 lightmapped, 0 cut-out, 0 empty-submesh contributors). Chunk rebuilds keep the flags.
- Project default light baker: Unity Compute Light Baker (no NVIDIA OpenCL on this host).
- **The PC pipeline is back on legacy light probes (`m_LightProbeSystem: 0`)** because nothing is baked; switch it to 1
  after a successful bake.

## Why the bake failed (three attempts, logs kept here)
1. `bake-attempt1-crash.log` — 28 meshes with empty submeshes failed BLAS creation ("Thread group size must be above
   zero"); 1,191 contributors were still lightmap receivers (prefab-instance edits not recorded) so the light-transport
   stage packed a 1.2 GB lightmap scene; SIGSEGV in libnvidia-glcore during the path tracer. Fixed in ConfigureBatch.
2. `bake-attempt2-vram.log` — contributors clean; "Vulkan - Suboptimal memory type … because of low memory" hundreds of
   times, then SIGSEGV in the NVIDIA driver in the path tracer. The 12 GB card hosts the desktop (~3 GB).
3. `bake-attempt3-ram.log` — textures forced to 1/8 resolution; still low-VRAM warnings, and the Editor exceeded the
   14 GB RAM cap (killed by the scope, as intended — an earlier unbounded run of several GPU jobs crashed the machine).

## To bake later
Run on a quiet machine (no other Unity/Blender/player, desktop apps closed) with ≥ 20 GB free RAM and ≥ 10 GB free
VRAM, or on a 16–24 GB GPU: `ConfigureBatch` (-nographics), then `BakeBatch` with `-force-vulkan`, no `-nographics`,
no `-quit`. Consider 3 m spacing / 512 samples first. Then set `m_LightProbeSystem: 1`, build, and A/B natively per
recipe §8.
