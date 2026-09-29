# APV + Sky Occlusion recipe for Ward / Athen Hill

Researched 30 September 2026 against the **installed** packages: Unity 6000.6.0f1 (f7f8ed4d1e24),
`com.unity.render-pipelines.core@1691dee1b9ce` (17.6.0) and `com.unity.render-pipelines.universal@b9a66914c09e`
(17.6.0). Where the web documentation and the installed source disagree, this recipe follows the source.
Paths abbreviated `core/` and `urp/` mean `unity/AthenHill/Library/PackageCache/<package>@<hash>/`.

Status: research and a proposed script. Nothing in the project was changed. No Unity process was run and nothing was baked.
Numbers marked *estimate* are unmeasured and must be replaced by native measurements (AGENTS.md §7).

---

## 0. Verdict

| Question | Answer |
| --- | --- |
| APV + Sky Occlusion in URP 17.6? | **Yes.** URP enables APV and advertises `SupportedRenderingFeatures.skyOcclusion` when the asset's `lightProbeSystem == ProbeVolumes` (`urp/Runtime/UniversalRenderPipeline.cs:406-423`). |
| Forward+? | **Yes.** APV is bound in `ForwardLights.PreSetup/Setup` for both Forward and Forward+ (`urp/Runtime/ForwardLights.cs:596-618`). It is sampled per pixel in `SampleProbeVolumePixel` (`urp/ShaderLibrary/GlobalIllumination.hlsl:104-128`). The rendering path does not matter. |
| **Runtime** on OpenGLCore (Linux player)? | **Probably yes, but verify natively.** None of the runtime APV compute shaders (`ProbeVolumeUploadData(.L2).compute`, `ProbeVolumeBlendStates.compute`) or the Lit sampling code has a renderer restriction. The pool needs compute plus random-write 3D textures, which GL 4.5 provides. |
| **Baking** on OpenGLCore? | **No.** Probe placement, dilation, virtual offset and the sky-occlusion tracer are compiled with `#pragma only_renderers` lists that **exclude `glcore`**: `core/Editor/Lighting/ProbeVolume/ProbeVolumeSubdivide.compute:9`, `ProbeVolumeCellDilation.compute:3`, `VirtualOffset/TraceVirtualOffset.urtshader:1`, `DynamicGI/DynamicGISkyOcclusion.urtshader:1`, `RenderingLayerMask/TraceRenderingLayerMask.urtshader:1`. **Bake from an Editor started with `-force-vulkan`.** The shipped player stays on OpenGLCore, so the project's graphics API does not change. |
| APV debug views on GL? | **No.** `core/Runtime/Debug/ProbeVolume*Debug.shader` also exclude glcore. Use a Vulkan Editor for probe visualisation. URP's *Lighting Debug Mode = Global Illumination* (`urp/ShaderLibrary/Debug/DebugViewEnums.cs:277-293`) is a normal Lit variant and should work on GL. |
| Works with Trilight ambient rewritten every frame by `CityTimeOfDay`? | **Yes, with no extra API calls.** At runtime, sky occlusion multiplies the **ambient probe** (`unity_SHAr…unity_SHC`) by the baked visibility SH. The bake stores no sky radiance. For **Gradient (Trilight) or Color** ambient, Unity updates the ambient probe automatically when `RenderSettings.ambient*Color` changes. `DynamicGI.UpdateEnvironment` is only needed for *Skybox* ambient and is documented as very expensive. The per-frame skybox material edits only affect reflections/sky rendering. |
| Lightmapper on this host | **Hazard.** No NVIDIA OpenCL ICD is installed: `/etc/OpenCL/vendors` is missing and there is no `libnvidia-opencl`. The Progressive **GPU** lightmapper therefore cannot run. Progressive **CPU** is the one backend that double-counts sky with sky occlusion (`core/Editor/Lighting/ProbeVolume/ProbeVolumeBakingSetEditor.cs:436-440`). Use the **Unity Compute Light Baker** (compute/URT, runs on Vulkan), or install `opencl-nvidia` that matches driver 610.57.04 and use Progressive GPU. |
| Feasible? | **Yes, as an A/B experiment:** a two-launch batch bake (configure, then bake under Vulkan), a render-chunk static-flag fix, and a native GL verification pass. It fixes un-occluded *diffuse ambient* only (see §1.4). |

---

## 1. How it works in this version (source-verified)

### 1.1 Bake side
- `ProbeVolumeBakingSet.skyOcclusion = true` (`core/Runtime/Lighting/ProbeVolume/ProbeVolumeBakingSet.cs:242`). When it is on, **environment lighting is excluded from the probe SH bake**: `ignoreDirectEnvironment = ignoreIndirectEnvironment = m_BakingSet.skyOcclusion` (`core/Editor/Lighting/ProbeVolume/ProbeGIBaking.cs:1135-1161`). Probe SH then holds only Baked/Mixed lights.
- A separate GPU job (`DefaultSkyOcclusion`, `ProbeGIBaking.SkyOcclusion.cs`) traces `skyOcclusionBakingSamples` sphere rays per probe with `skyOcclusionBakingBounces` diffuse bounces. Each bounce uses a constant `skyOcclusionAverageAlbedo`, and scene albedo is ignored. The job stores an L0+L1 **visibility SH** (`DynamicGISkyOcclusion.urtshader`, RGBA16F per probe). With `skyOcclusionShadingDirection`, it also stores an 8-bit index of the most open direction.
- `skyOcclusionBackFaceCulling` is **ignored**; it is hard-coded to 0 (`ProbeGIBaking.SkyOcclusion.cs:168`).
- The tracing geometry is **only GI contributors**: renderers with `StaticEditorFlags.ContributeGI`, a `MeshFilter`, active, `enabled` and `isLOD0` (`core/Runtime/Lighting/ProbeVolume/ProbeVolumeGIContributor.cs:111-112,168`). **SkinnedMeshRenderers are skipped** (`SkyOcclusion.cs:217`), and static-batched renderers are rejected with an error (`ProbeGIBaking.LightTransport.cs:486-490`). The baking set's layer mask and min renderer size only affect **probe placement**, not what occludes the sky.
- Ray backend: hardware RT if `SystemInfo.supportsRayTracing`, otherwise compute emulation (`ProbeGIBaking.LightTransport.cs:406`, `core/Runtime/UnifiedRayTracing/RayTracingContext.cs:107-118`).

### 1.2 Runtime side
`EvaluateAdaptiveProbeVolume` (`core/Runtime/Lighting/ProbeVolume/ProbeVolume.hlsl:750-776`):

```
bake = L0 + L1(N)                                  // baked lights only (≈0 here: every light is Realtime)
if (_APVSkyOcclusionWeight > 0)
    bake += dot(SH(N), skyVisL0L1) * EvaluateAmbientProbe(skyDirection or N)   // :699-722
bake *= _APVWeight                                  // ProbeVolumesOptions.intensityMultiplier
invalid/outside volume -> EvaluateAmbientProbe(N)   // unoccluded fallback
```

- `EvaluateAmbientProbe` in URP reads `unity_SHAr…unity_SHC` (`core/ShaderLibrary/AmbientProbe.hlsl:45-58`, with `AMBIENT_PROBE_BUFFER 0` at `urp/ShaderLibrary/GlobalIllumination.hlsl:9-10`). No light-probe groups exist in the scene, so this is the scene ambient probe (Trilight).
- `_APVSkyOcclusionWeight = ProbeVolumesOptions.skyOcclusionIntensityMultiplier` when the loaded set was baked with sky occlusion (`core/Runtime/Lighting/ProbeVolume/ProbeReferenceVolume.Binding.cs:138-139`).
- Dynamic actors (player, NPCs, walkers) sample the same volume per pixel, so they darken correctly in alleys.

### 1.3 Scene/project facts that matter (audited from YAML, 30 Sep 2026)

| Item | Current value | Consequence |
| --- | --- | --- |
| `PC_RPAsset` | `m_LightProbeSystem: 0`, `m_ProbeVolumeSHBands: 1`, `m_ProbeVolumeMemoryBudget: 1024`, `m_ShEvalMode: 0` (Auto, which means per-pixel on desktop), `m_SupportsLightLayers: 1` | Switch to APV. The other defaults are fine. |
| Quality → pipeline | Standalone default = PC (`PC_RPAsset`). Mobile keeps `Mobile_RPAsset` with legacy probes. | Only PC gets APV. `GraphicsSettings.m_CustomRenderPipeline` is null. |
| `GameSettings.Start()` | Instantiates a runtime copy of the pipeline asset and assigns it (`Scripts/GameSettings.cs:76-82`) | The pipeline is recreated: APV is `Cleanup()`d and re-`Initialize()`d. Expect a brief reload. Check the player log for APV errors. |
| Scene lighting | `m_LightingSettings: {fileID: 0}` (no asset), `m_LightingDataAsset` = builtin default, `m_AmbientMode: 1` (Trilight), realtime GI off | Create a LightingSettings asset. The first APV bake creates `LightingData-0.asset` beside the baking set (`ProbeGIBaking.LightTransport.cs:299-356`). |
| Lights | 70 lights, **all Realtime** (`m_Lightmapping: 4`), including `Sun` (shadows) and **`Sky fill`** (directional, no shadows, 0.19) | Probe SH will be ≈ black and only sky occlusion contributes. The un-shadowed *Sky fill* stays un-occluded, so re-tune it (see §6). |
| Render chunks | 319 chunk renderers under `City Render Chunks/Generated material chunks`: **StaticEditorFlags 0**, `m_ReceiveGI: 1` (Lightmaps), `m_LightProbeUsage: 1` | **Not GI contributors.** They are created with `new GameObject` (`Editor/StaticRenderChunksEditor.cs:88`) and the whole root is destroyed on every Rebuild (`:84`), so flags must be applied **inside Rebuild**. The chunk *sources* are disabled (`renderer.enabled=false`) and are excluded by the contributor filter. |
| Chunk lightmap UVs | Only **5/319** chunk meshes have a UV1 channel. Those UVs come from merged source UV2 with `CombineMeshes(...hasLightmapData:false)`, so they overlap. | APV needs no UV1. Keep chunks out of lightmapping: `receiveGI = LightProbes`. |
| Non-chunk static art | The chunk sources are only `AuthoredWorld`, `Paving` and `Paving Joints`. `Ward shop architecture`, `Ward district retrofit`, `Landmarks`, `Desert Landscape` (= `Art/Terrain/DesertBasin.glb`, a mesh), `Meshy Ring Gate`, Basic General / Finery frontages, `Karaveen caravan market`, `Outer Berms` and `Post-war salvage` are separate roots. Only 19 renderers (Outer Berms depot) currently have ContributeGI. | **Awnings and shop fronts will not occlude the sky unless flagged.** |
| Terrain | No `Terrain` components; the basin is a mesh | The terrain ray-march path is unused. |
| Anti-aliasing | Cameras use SMAA (`m_Antialiasing: 2`), no TAA | `samplingNoise` is not animated and shows as static grain. Keep it at 0.05 or lower. |
| URP global settings | `ProbeVolumeBakingResources`, `ProbeVolumeRuntimeResources` and `ProbeVolumeDebugResources` are present (`Assets/Settings/UniversalRenderPipelineGlobalSettings.asset:442-489`) | No resource setup needed. |

### 1.4 What APV sky occlusion will *not* fix
- **Specular/reflections in shade.** URP 17.6 has no APV reflection-probe normalisation; there is no reference to it in `urp/`. Smooth materials under awnings still reflect the open-sky probe. Use local box-projected reflection probes and SSAO for that.
- **Sun bounce.** A sunlit desert street throws strong warm bounce into shade. Sky occlusion bounces only *sky* light (albedo override). Baked sun bounce needs lighting scenarios (§6).
- **Realtime fill lights** (`Sky fill`) and SSAO are unaffected.
- Visibility is treated as fully opaque, so leaves and glass block the sky completely. Keep foliage and glass out of ContributeGI.

---

## 2. Recommended starting configuration

| Setting | Where (field name) | Start value | Why |
| --- | --- | --- | --- |
| Light Probe System | `PC_RPAsset` `m_LightProbeSystem` | `1` (ProbeVolumes) | Enables APV (`UniversalRenderPipelineAsset.cs:491`) |
| SH bands | `m_ProbeVolumeSHBands` | `1` (L1) | Baked SH is ≈0 and sky visibility is always L0L1. L2 would add 16 B/probe for nothing. |
| Memory budget | `m_ProbeVolumeMemoryBudget` | `1024` (Medium) | Holds about 4.19 M probe slots. Low (1.05 M) is likely too small at 1 m spacing (§4). |
| GPU/Disk streaming, Scenarios, Blending | `m_SupportProbeVolume*` | all `0` | 250 m town fits resident. Scenarios only in phase 2. |
| SH eval | `m_ShEvalMode` | keep `0` (Auto = per-pixel) | Per-vertex looks poor on large combined chunk triangles. |
| Min probe spacing | `ProbeVolumeBakingSet.minDistanceBetweenProbes` | `1.0` m (min brick 3 m) | Resolves 2–4 m alleys and awning depth. Fall back to 1.5 m if the count or bake time is excessive. |
| Levels | `simplificationLevels` | `3` → max spacing 27 m, cell 81 m | Spacing = min × 3^level (`ProbeVolumeLightingTab.cs:1183`) |
| Renderer filter | `renderersLayerMask`, `minRendererVolumeSize` | all layers except actors/UI; `0.1` | Placement only |
| Sky occlusion | `skyOcclusion` | `true` | |
| Samples / bounces | `skyOcclusionBakingSamples` / `…Bounces` | 2048 / 2 (first iteration: 512 / 1) | Defaults; max 8192 |
| Albedo override | `skyOcclusionAverageAlbedo` | `0.45` | Sandstone/soil. Default 0.6 over-brightens bounce. |
| Sky direction | `skyOcclusionShadingDirection` | `true` | +1 B/probe. Better ambient direction in alleys, but watch for seams. |
| Dilation | internal `settings.dilationSettings` | enable, 1 m, threshold 0.25, 1 iter | **Source default is OFF** (`ProbeVolumeBakingProcessSettings.cs:14`); docs claim on. Dilation also fixes sky-occlusion data (`ProbeGIBaking.Dilate.cs:87-115`). |
| Virtual offset | internal `settings.virtualOffsetSettings` | on, threshold 0.25, search 0.2, geo bias 0.01 | Uses **renderer** geometry of contributors on `collisionMask` layers, not colliders (`ProbeGIBaking.VirtualOffset.cs:132-150`), despite the docs. |
| Volumes | `ProbeVolume` components | **APV Town**: `Mode.Local`, box around the playable district from basin floor to ~30 m above roofs, no override. **APV Basin**: `Mode.Global`, `overridesSubdivLevels=true`, `lowestSubdivLevelOverride=2`, `highestSubdivLevelOverride=3` (9–27 m) | Placement keeps a brick if *any* overlapping volume allows its level (`ProbePlacement.cs:280-291`), so the town stays fine while the basin stays cheap. |
| Options override | `ProbeVolumesOptions` in the scene's global volume profile | `leakReductionMode=Quality`, `skyOcclusionIntensityMultiplier=1` (tune 1–1.5), `samplingNoise=0.05`, `normalBias=0.1`, `viewBias=0.15` | Defaults are 0.05/0.1/0.1 (`ProbeVolumesOptions.cs:34-95`). |
| LightingSettings | new `.lighting` asset on the scene | `bakedGI=true`, `realtimeGI=false`, `autoGenerate=false`, `mixedBakeMode=IndirectOnly`, direct 32, indirect 256, environment 256, `lightProbeSampleCountMultiplier=1`, `maxBounces=2` | The APV lighting job still traces validity samples. The scene's legacy multiplier (4) would quadruple them. |
| Light baker | `EditorGraphicsSettings.defaultLightBaker` (+ `LightingSettings.lightmapper`) | `LightBaker.UnityComputeLightBaker` (+ `Lightmapper.UnityComputeGPU`) | No OpenCL on this host. This is a **project setting change** (`ProjectSettings/GraphicsSettings.asset m_DefaultLightBaker`), so record it. The alternative is installing `opencl-nvidia` and keeping Progressive GPU. |
| Contributors | chunk renderers + opaque static art roots | `ContributeGI` on; `receiveGI = ReceiveGI.LightProbes` | Opaque = `material.renderQueue < 2450`. Exclude foliage, glass, characters, droids, vehicles that move, and `District rebuild`. |

---

## 3. Batch-mode procedure

Preconditions:
- Close the interactive Editor: it holds the project lock and about 6 GB of VRAM (memory note).
- Keep the desktop session's `DISPLAY`/`WAYLAND_DISPLAY`, because the bake needs a real GPU device.
- Commit or stash first so the previous version stays recoverable (AGENTS.md §5.7).

```bash
U=/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity
P=/home/teknetik/code/ao2/unity/AthenHill
E=/home/teknetik/code/ao2/unity/evidence/rendering/20260930/apv
mkdir -p "$E"

# Launch 1 — configure assets/scene (any API; -nographics is fine here). The method calls Exit itself.
"$U" -batchmode -nographics -projectPath "$P" \
     -executeMethod AthenHill.Editor.ApvSkyOcclusionBake.ConfigureBatch -logFile "$E/configure.log"

# Launch 2 — bake. MUST be: no -nographics (GPU bake), -force-vulkan (glcore kernels are missing),
# and NO -quit (the bake is async and driven by EditorApplication.update; the method calls Exit when done).
setsid -f "$U" -batchmode -force-vulkan -projectPath "$P" \
     -executeMethod AthenHill.Editor.ApvSkyOcclusionBake.BakeBatch -logFile "$E/bake.log"
# poll for $E/apv-bake.json (written by the script) or for the Unity PID to exit.
```

Why two launches: the URP pipeline instance calls `ProbeReferenceVolume.instance.Initialize` only in its constructor (`UniversalRenderPipeline.cs:406-423`). Changing `m_LightProbeSystem` in a session whose pipeline already exists is not guaranteed to re-create it. In batch mode, nothing renders on its own, so the pipeline is never created unless the script forces one render. `AdaptiveProbeVolumes.BakeAsync()` then refuses to start if `!isInitialized || !enabledBySRP` (`ProbeGIBaking.cs:1258`, via `InitializeBake`).

What `AdaptiveProbeVolumes.BakeAsync()` does (`ProbeGIBaking.cs:1923-1943`):
- It is the "Bake Probe Volumes" button: APV only, and **lightmaps are skipped** (`BakePipelineDriver.StartBake` → `SetEnableBakedLightmaps(false)`, `AdaptiveProbeVolumes.BakePipelineDriver.cs:30-35`).
- It returns `false` immediately if `Lightmapping.isRunning` or preparation fails.
- It progresses on `EditorApplication.update` (`AsyncBakeCallback`, `:1903-1916`). `AdaptiveProbeVolumes.isRunning` goes false after `UpdateLightStatus()`.
- `PrepareAPVBake` (`ProbeVolumeLightingTab.cs:973-1080`) is batch-safe: dialogs are replaced by `Application.isBatchMode` warnings and `return false`.
- If no baking set exists, it silently creates one with defaults, which means **sky occlusion off**. Pre-create the set yourself.

`Lightmapping.BakeAsync()` ("Generate Lighting") would also bake APV through the `bakeStarted` hook. It would, however, try lightmaps for any ContributeGI renderer still set to `receiveGI=Lightmaps`, and re-bake reflection probes. Prefer the APV-only call.

---

## 4. Cost and memory

**VRAM.** The pool is allocated at the **full budget** at init, independent of scene content (`ProbeBrickPool.cs:193-218,627-634`). Per probe texel: L0 RGBA16F 8 B + L1 2×RGBA8 8 B + validity R8 1 B + sky occlusion RGBA16F 8 B + sky direction R8 1 B = **26 B** (L2 adds 16 B; `ProbeBrickPool.cs:566-605`). The index buffer is sized by budget too (`ProbeBrickIndex.cs:95-110`).

| Budget | Probe slots | Pool (L1+SO+dir) | Index | Total |
| --- | --- | --- | --- | --- |
| Low (512) | 1.05 M | 27 MB | 16 MB | **≈43 MB** |
| Medium (1024) | 4.19 M | 109 MB | 32 MB | **≈141 MB** |
| High (2048) | 16.8 M | 436 MB | 64 MB | ≈500 MB |

Scenario blending (phase 2) lazily adds two pools at the blending budget: Medium 256 → 2 × 262 k × 16 B ≈ 8 MB.

**Probe count (*estimate*).** Bricks are 4×4×4 = 64 probes, and finest bricks form a shell around contributor surfaces:
- **1 m spacing** (3 m bricks), 250×250 m town: ground shell ≈ 7–14 k bricks, walls and roofs ≈ 5 k bricks, so **≈ 0.8–1.3 M probes**. Low is insufficient; use Medium.
- **1.5 m spacing:** about 0.45× that.
- **2 m spacing:** about 0.25×.
- Basin at 9 m minimum spacing: under 0.1 M.

If loaded bricks exceed the pool, cells fail to load and those areas fall back to un-occluded ambient.

**Disk.** 26 B/probe in builds (`ProbeGIBaking.Serialization.cs:870-899`), about 25–35 MB at 1 m. Editor-only support data (about 32 B/probe) is stripped from builds (`ProbeVolumeBuildProcessor.cs:147-149`). The `.bytes` files live next to the baking set and go into StreamingAssets in the player (`probeVolumeDisableStreamingAssets: 0`).

**GPU (*estimate*, unmeasured).** Per pixel: index lookups plus 3 L1 fetches, 1 sky-occlusion fetch, 1 direction load and 1 validity load. `Quality` leak reduction can take 1–3 such samples. At 1920×1080 on the RTX 3060, expect roughly **0.3–0.8 ms** (Quality) or 0.15–0.4 ms (`Performance`). Measure it with the §7 warmed traversal and compare the p99 against the 16.67 ms criterion.

**CPU.** Per-camera `UpdateCellStreaming` plus a constant-buffer update, which is negligible without streaming. There is a one-off upload at scene load and again when `GameSettings` recreates the pipeline.

**Bake time (*estimate*).** Placement plus virtual offset takes minutes. Sky occlusion is about probes × samples × (1 + bounces) rays, roughly 5–8 G rays at 1 m and 2048 samples. That is minutes with hardware RT and possibly tens of minutes with compute emulation. Use 512 samples / 1 bounce for the first look.

---

## 5. C# sketch (not installed)

Intended path: `unity/AthenHill/Assets/AthenHill/Editor/ApvSkyOcclusionBake.cs`. The Editor folder has no asmdef, so it compiles into `Assembly-CSharp-Editor`, which auto-references `Unity.RenderPipelines.Core.Editor/Runtime`, URP and `AthenHill.Runtime`. Every APV name below was checked in the installed source (§8).

**Internal-API caveat.**
- `ProbeVolumeBakingSet.SetDefaults()` is internal, so it is called by reflection.
- `settings.*` and URP asset fields are set through `SerializedObject` because their setters are internal.
- Re-verify all of these after any package upgrade.

```csharp
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// Launch 1: ConfigureBatch (idempotent asset/scene setup, exits).
    /// Launch 2: BakeBatch under -force-vulkan, without -nographics and without -quit.
    public static class ApvSkyOcclusionBake
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string PipelinePath = "Assets/Settings/PC_RPAsset.asset";
        const string DataFolder = "Assets/AthenHill/Scenes/AthenHill";          // APV's own default: <sceneDir>/<sceneName>/
        const string BakingSetPath = DataFolder + "/AthenHill Baking Set.asset";
        const string LightingPath = DataFolder + "/AthenHill Lighting.lighting";
        const string ReportRelative = "../evidence/rendering/20260930/apv/apv-bake.json"; // relative to the project folder
        const double TimeoutSeconds = 3 * 60 * 60;

        // Measure these in the saved scene: playable district, basin floor to ~30 m above the roofs.
        static readonly Vector3 TownCenter = new Vector3(0f, 12f, 0f);
        static readonly Vector3 TownSize = new Vector3(280f, 50f, 280f);

        // Opaque static art outside the render-chunk sources. Review this list; never include actors, foliage or glass.
        static readonly string[] ExtraStaticRoots =
        {
            "Ward shop architecture", "Ward district retrofit", "Landmarks", "Desert Landscape", "Meshy Ring Gate",
            "Basic General authored frontage", "Basic General back panel", "Phase 1 Finery frontage",
            "Outer Berms", "Post-war salvage", "Mission Terminal Upgrade", "Hill weathered stones",
        };

        // ------------------------------------------------------------------ launch 1
        public static void ConfigureBatch()
        {
            int code = 0;
            try { Configure(); }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            EditorApplication.Exit(code);
        }

        public static void Configure()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            EnsureFolder(DataFolder);

            // URP asset: setters are internal (UniversalRenderPipelineAsset.cs:1222-1298) -> serialized fields (:484-502).
            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(PipelinePath);
            if (!pipeline) throw new InvalidOperationException("PC pipeline asset missing: " + PipelinePath);
            var p = new SerializedObject(pipeline);
            p.FindProperty("m_LightProbeSystem").intValue = (int)LightProbeSystem.ProbeVolumes;
            p.FindProperty("m_ProbeVolumeSHBands").intValue = (int)ProbeVolumeSHBands.SphericalHarmonicsL1;
            p.FindProperty("m_ProbeVolumeMemoryBudget").intValue = (int)ProbeVolumeTextureMemoryBudget.MemoryBudgetMedium;
            p.FindProperty("m_SupportProbeVolumeGPUStreaming").boolValue = false;
            p.FindProperty("m_SupportProbeVolumeDiskStreaming").boolValue = false;
            p.FindProperty("m_SupportProbeVolumeScenarios").boolValue = false;
            p.FindProperty("m_SupportProbeVolumeScenarioBlending").boolValue = false;
            p.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(pipeline);

            // No NVIDIA OpenCL ICD on this host: Progressive GPU would fall back to CPU, which double-counts sky
            // with sky occlusion. Project-wide setting (ProjectSettings/GraphicsSettings.asset m_DefaultLightBaker).
            UnityEditor.Rendering.EditorGraphicsSettings.defaultLightBaker = UnityEditor.Rendering.LightBaker.UnityComputeLightBaker;

            var ls = AssetDatabase.LoadAssetAtPath<LightingSettings>(LightingPath);
            if (!ls) { ls = new LightingSettings { name = "AthenHill Lighting" }; AssetDatabase.CreateAsset(ls, LightingPath); }
            ls.bakedGI = true; ls.realtimeGI = false; ls.autoGenerate = false;
            ls.lightmapper = LightingSettings.Lightmapper.UnityComputeGPU;
            ls.mixedBakeMode = MixedLightingMode.IndirectOnly;          // no probe occlusion / shadowmask data
            ls.directSampleCount = 32; ls.indirectSampleCount = 256; ls.environmentSampleCount = 256;
            ls.lightProbeSampleCountMultiplier = 1f; ls.maxBounces = 2;
            EditorUtility.SetDirty(ls);
            Lightmapping.SetLightingSettingsForScene(scene, ls);

            EnsureBakingSet(AssetDatabase.AssetPathToGUID(ScenePath));
            EnsureVolume("APV Town", ProbeVolume.Mode.Local, TownCenter, TownSize, false, 0, 3);
            // Global = encapsulates all contributors of the set; restricted to levels 2..3 (9..27 m at 1 m min spacing).
            EnsureVolume("APV Basin", ProbeVolume.Mode.Global, Vector3.zero, Vector3.one, true, 2, 3);

            int flagged = 0;
            foreach (var chunks in UnityEngine.Object.FindObjectsByType<StaticRenderChunks>())
                if (chunks.generatedRoot)
                    foreach (var r in chunks.generatedRoot.GetComponentsInChildren<MeshRenderer>(true))
                        if (MarkContributor(r)) flagged++;
            foreach (var rootName in ExtraStaticRoots)
            {
                var root = GameObject.Find(rootName);
                if (!root) { Debug.LogWarning("APV: root not found: " + rootName); continue; }
                foreach (var r in root.GetComponentsInChildren<MeshRenderer>(false))
                    if (r.enabled && !r.name.StartsWith("COL_") && MarkContributor(r)) flagged++;
            }

            EnsureOptions();
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Debug.Log($"APV_CONFIGURE ok: set={BakingSetPath} contributors={flagged}");
        }

        static ProbeVolumeBakingSet EnsureBakingSet(string sceneGuid)
        {
            var set = AssetDatabase.LoadAssetAtPath<ProbeVolumeBakingSet>(BakingSetPath);
            if (!set)
            {
                set = ScriptableObject.CreateInstance<ProbeVolumeBakingSet>();
                set.name = Path.GetFileNameWithoutExtension(BakingSetPath);
                // Same call the Lighting window makes (ProbeVolumeLightingTab.cs:556-559); internal (ProbeVolumeBakingSet.Editor.cs:380).
                typeof(ProbeVolumeBakingSet).GetMethod("SetDefaults", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(set, null);
                AssetDatabase.CreateAsset(set, BakingSetPath);
            }
            if (!set.sceneGUIDs.Contains(sceneGuid) && !set.TryAddScene(sceneGuid))
                throw new InvalidOperationException("Scene already belongs to another ProbeVolumeBakingSet; remove it there first.");

            set.minDistanceBetweenProbes = 1f;
            set.simplificationLevels = 3;
            set.minRendererVolumeSize = 0.1f;
            set.renderersLayerMask = ~0;                  // narrow if actors share layers with static art
            set.skyOcclusion = true;
            set.skyOcclusionBakingSamples = 2048;         // 512 for the first look
            set.skyOcclusionBakingBounces = 2;
            set.skyOcclusionAverageAlbedo = 0.45f;
            set.skyOcclusionShadingDirection = true;

            var s = new SerializedObject(set);            // internal ProbeVolumeBakingProcessSettings 'settings'
            s.FindProperty("settings.dilationSettings.enableDilation").boolValue = true;
            s.FindProperty("settings.dilationSettings.dilationDistance").floatValue = 1f;
            s.FindProperty("settings.dilationSettings.dilationValidityThreshold").floatValue = 0.25f;
            s.FindProperty("settings.dilationSettings.dilationIterations").intValue = 1;
            s.FindProperty("settings.virtualOffsetSettings.useVirtualOffset").boolValue = true;
            s.FindProperty("settings.virtualOffsetSettings.validityThreshold").floatValue = 0.25f;
            s.FindProperty("settings.virtualOffsetSettings.searchMultiplier").floatValue = 0.2f;
            s.FindProperty("settings.virtualOffsetSettings.outOfGeoOffset").floatValue = 0.01f;
            s.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(set);
            return set;
        }

        static void EnsureVolume(string name, ProbeVolume.Mode mode, Vector3 center, Vector3 size,
                                 bool overrideSpacing, int lowestLevel, int highestLevel)
        {
            var go = GameObject.Find(name);
            if (!go) go = new GameObject(name);
            var pv = go.GetComponent<ProbeVolume>();
            if (!pv) pv = go.AddComponent<ProbeVolume>();
            go.transform.SetPositionAndRotation(center, Quaternion.identity);
            go.transform.localScale = Vector3.one;
            pv.mode = mode;                               // Global/Scene recompute position+size at bake (ProbeVolume.cs:127-133)
            pv.size = size;
            pv.overridesSubdivLevels = overrideSpacing;
            pv.lowestSubdivLevelOverride = lowestLevel;   // spacing = minDistance * 3^level
            pv.highestSubdivLevelOverride = highestLevel;
            pv.fillEmptySpaces = false;
            EditorUtility.SetDirty(pv);
        }

        static bool MarkContributor(MeshRenderer r)
        {
            var m = r.sharedMaterial;
            bool opaque = m && m.renderQueue < (int)RenderQueue.AlphaTest;   // cut-out/transparent block sky fully
            var flags = GameObjectUtility.GetStaticEditorFlags(r.gameObject);
            flags = opaque ? flags | StaticEditorFlags.ContributeGI : flags & ~StaticEditorFlags.ContributeGI;
            GameObjectUtility.SetStaticEditorFlags(r.gameObject, flags);
            r.receiveGI = ReceiveGI.LightProbes;          // never lightmaps: chunks have no valid UV1
            EditorUtility.SetDirty(r.gameObject);
            return opaque;
        }

        static void EnsureOptions()
        {
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>();
            var profile = clock && clock.gradingVolume ? clock.gradingVolume.sharedProfile : null;
            if (!profile) { Debug.LogWarning("APV: no global grading profile; add Adaptive Probe Volumes Options manually."); return; }
            if (!profile.TryGet(out ProbeVolumesOptions o))
            {
                o = profile.Add<ProbeVolumesOptions>(false);
                if (AssetDatabase.Contains(profile)) AssetDatabase.AddObjectToAsset(o, profile);
            }
            o.leakReductionMode.Override(APVLeakReductionMode.Quality);
            o.skyOcclusionIntensityMultiplier.Override(1f);
            o.samplingNoise.Override(0.05f);              // no TAA (SMAA) -> static grain above ~0.05
            o.normalBias.Override(0.1f);
            o.viewBias.Override(0.15f);
            EditorUtility.SetDirty(o); EditorUtility.SetDirty(profile);
        }

        static void EnsureFolder(string folder)
        {
            if (AssetDatabase.IsValidFolder(folder)) return;
            string parent = Path.GetDirectoryName(folder).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(folder));
        }

        // ------------------------------------------------------------------ launch 2
        static double s_Start;
        static DateTime s_StartUtc;
        static readonly List<string> s_Problems = new List<string>();

        public static void BakeBatch()
        {
            try
            {
                if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Vulkan)
                    throw new InvalidOperationException("Start with -force-vulkan: APV placement/sky-occlusion kernels are not compiled for glcore.");
                EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
                ForceOneRender();                         // creates the URP pipeline -> ProbeReferenceVolume.Initialize
                if (!ProbeReferenceVolume.instance.isInitialized)
                    throw new InvalidOperationException("APV not initialised (m_LightProbeSystem not ProbeVolumes, or no render happened).");
                if (Lightmapping.isRunning) Lightmapping.Cancel();

                Application.logMessageReceived += Capture;
                s_Start = EditorApplication.timeSinceStartup; s_StartUtc = DateTime.UtcNow;
                if (!AdaptiveProbeVolumes.BakeAsync())
                    throw new InvalidOperationException("AdaptiveProbeVolumes.BakeAsync() refused to start; see log.");
                EditorApplication.update += Poll;         // no -quit: Editor keeps ticking until Exit()
            }
            catch (Exception e) { Debug.LogException(e); Finish(false, e.Message); }
        }

        static void ForceOneRender()
        {
            var go = new GameObject("APV bake init camera") { hideFlags = HideFlags.HideAndDontSave };
            var rt = new RenderTexture(64, 64, 24);
            try
            {
                var cam = go.AddComponent<Camera>();
                cam.cullingMask = 0; cam.targetTexture = rt;
                cam.Render();
                cam.targetTexture = null;
            }
            finally { UnityEngine.Object.DestroyImmediate(go); rt.Release(); UnityEngine.Object.DestroyImmediate(rt); }
        }

        static void Capture(string message, string stack, LogType type)
        {
            bool cpuFallback = type == LogType.Warning && message.IndexOf("CPU", StringComparison.OrdinalIgnoreCase) >= 0
                               && message.IndexOf("fall", StringComparison.OrdinalIgnoreCase) >= 0;
            if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert || cpuFallback)
                s_Problems.Add(type + ": " + message);
        }

        static void Poll()
        {
            if (AdaptiveProbeVolumes.isRunning)
            {
                if (EditorApplication.timeSinceStartup - s_Start > TimeoutSeconds)
                {
                    AdaptiveProbeVolumes.Cancel();
                    Finish(false, "timeout");
                }
                return;
            }
            var set = AssetDatabase.LoadAssetAtPath<ProbeVolumeBakingSet>(BakingSetPath);
            bool ok = set && set.HasBakedData() && FreshBakeOutput() && s_Problems.Count == 0;
            if (ok)
            {
                AssetDatabase.SaveAssets();
                // Saves the hidden ProbeVolumePerSceneData object and the new LightingData asset reference.
                EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
            }
            Finish(ok, ok ? "baked" : "bake failed or produced no fresh data");
        }

        static bool FreshBakeOutput() => BakeFiles().Any(f => f.Name.EndsWith(".CellSharedData.bytes") && f.LastWriteTimeUtc >= s_StartUtc);

        static FileInfo[] BakeFiles()
        {
            string dir = Path.GetFullPath(DataFolder);
            return Directory.Exists(dir) ? new DirectoryInfo(dir).GetFiles("*.bytes") : new FileInfo[0];
        }

        static void Finish(bool ok, string note)
        {
            EditorApplication.update -= Poll;
            Application.logMessageReceived -= Capture;
            try
            {
                var set = AssetDatabase.LoadAssetAtPath<ProbeVolumeBakingSet>(BakingSetPath);
                var so = set ? new SerializedObject(set) : null;
                var files = BakeFiles();
                long cellData = files.Where(f => f.Name.EndsWith("-Default.CellData.bytes")).Sum(f => f.Length);
                var report = new
                {
                    utc = DateTime.UtcNow.ToString("O"), ok, note,
                    device = SystemInfo.graphicsDeviceType.ToString(), gpu = SystemInfo.graphicsDeviceName,
                    hardwareRayTracing = SystemInfo.supportsRayTracing,
                    minutes = (EditorApplication.timeSinceStartup - s_Start) / 60.0,
                    bakedSkyOcclusion = so?.FindProperty("bakedSkyOcclusionValue")?.intValue,
                    bakedSkyDirection = so?.FindProperty("bakedSkyShadingDirectionValue")?.intValue,
                    approxProbeCount = cellData / 16,     // L0L1 = 16 B/probe (chunk-padded)
                    files = files.Select(f => new { f.Name, f.Length }).ToArray(),
                    problems = s_Problems,
                };
                string path = Path.GetFullPath(Path.Combine(Directory.GetParent(Application.dataPath).FullName, ReportRelative));
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                File.WriteAllText(path, JsonConvert.SerializeObject(report, Formatting.Indented));
            }
            catch (Exception e) { Debug.LogException(e); }
            EditorApplication.Exit(ok ? 0 : 2);
        }
    }
}
```

### Required change in `StaticRenderChunksEditor.Rebuild` (proposed; not applied)
Every chunk rebuild destroys and recreates the generated root (`StaticRenderChunksEditor.cs:84-89`), so flags set by the configure step are lost. After `r.receiveShadows=pair.Key.Item5;` on line 88, add:

```csharp
var mat = pair.Key.Item1;
if (mat && mat.renderQueue < (int)RenderQueue.AlphaTest) GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.ContributeGI);
r.receiveGI = ReceiveGI.LightProbes;
```

Also, any chunk rebuild changes the geometry the APV was baked against. Record the chunk `sourceFingerprint` in the bake report. Then extend `VerifyRenderChunks` (or a sibling `IPreprocessBuildWithReport`) to fail the build when the fingerprint differs from the one recorded at bake time. This matches the existing stale-source guard.

---

## 6. Optional phase 2: sun bounce through lighting scenarios

Start with sky-occlusion-only. The bake then carries **no sun indirect**, because every light is Realtime and a rotating sun cannot be baked once. If shade still lacks warm bounce after tuning, add scenarios:

**Configuration**
1. URP asset: `m_SupportProbeVolumeScenarios=1`, `m_SupportProbeVolumeScenarioBlending=1`. Blending requires compute, which GL 4.5 has (`ProbeReferenceVolume.cs:1046`).
2. Baking set: `TryAddScenario("Morning")`, `"Noon"`, `"Evening"`, `"Night"` (`ProbeVolumeBakingSet.Editor.cs:176`).

**Bake each scenario**
3. Rotate and colour the `Sun` to that hour's `DayNightLightingProfile` frame, and set it `LightmapBakeType.Mixed`. Keep `mixedBakeMode = IndirectOnly`, which keeps direct light realtime and bakes no occlusion.
4. Set `ProbeReferenceVolume.instance.lightingScenario = name`, then `BakeAsync`.
5. After the first scenario, freeze placement. This needs the set's internal `freezePlacement` (SerializedObject) **and** the internal static `AdaptiveProbeVolumes.isFreezingPlacement` (reflection; `ProbeGIBaking.cs:859`). Otherwise differing layouts make batch mode refuse with "incompatible cell layouts" (`ProbeVolumeLightingTab.cs:1053-1075`).
6. Sky-occlusion data is shared across scenarios (`cellSharedDataAsset`).

**Runtime**
7. In `CityTimeOfDay.Apply()`, call `ProbeReferenceVolume.instance.lightingScenario = a;` and `ProbeReferenceVolume.instance.BlendLightingScenario(b, t);` (`ProbeReferenceVolume.cs:818-858`).

**Cost:** +16 B/probe on disk per scenario, two blending pools (≈8 MB at Medium), and a compute blend on transitions. This is a separate, reviewable gameplay-lighting change.

---

## 7. Pitfalls

1. **Baking under OpenGL.** The kernels do not exist for glcore (§0), so placement or the sky-occlusion step fails. The sketch refuses to start unless `GraphicsDeviceType.Vulkan`. Also do not press *Generate Lighting* in the normal GL Editor.
2. **CPU lightmapper fallback.** Without OpenCL, Progressive GPU drops to CPU. CPU never honours `ignoreIndirectEnvironment`, so sky is double counted. Check `bake.log` for OpenCL/CPU fallback messages. Use the Unity Compute Light Baker, or install `opencl-nvidia`.
3. **Batch hangs / silent no-op.**
   - `BakeAsync` returns `false` when the pipeline is not initialised, `Lightmapping.isRunning`, no ProbeVolume/contributors exist, or the scene is in another set.
   - `PrepareAPVBake` returns `false` in batch mode for single-scene conflicts and incompatible layouts, with only a warning.
   - Never pass `-quit` (the async bake needs update ticks). Never pass `-nographics` for the bake launch.
   - Always use a timeout plus `EditorApplication.Exit`. `setsid -f` loses the exit code, so rely on the JSON report.
4. **Auto-created baking set.** If no set exists, `PrepareAPVBake` creates `<scene>/<scene> Baking Set.asset` with **sky occlusion off** (`ProbeVolumeLightingTab.cs:981-987,505-521`). Create the set first.
5. **Render chunks.** They are not contributors today, and Rebuild wipes their flags (§5 patch). Their sources are disabled and do not count. Rebake after every chunk rebuild.
6. **Shop fronts and awnings outside the chunk roots** must be flagged, or they will not occlude. They are prefab instances, so flagging creates scene overrides; that is acceptable, or flag the prefab assets.
7. **Foliage, glass, cut-out and transparent materials** occlude like solid grey. Keep them out of ContributeGI, or use a Probe Adjustment Volume in `OverrideSampleCount`/`InvalidateProbes` mode.
8. **Unreadable meshes.** If a mesh has no Raw index buffer and `GetIndices(0)` returns nothing, it is **silently skipped** from sky tracing (`ProbeGIBaking.LightTransport.cs:497-498`). Verify that glTFast imports such as `DesertBasin.glb` and the Meshy buildings actually occlude (debug view). If not, enable Read/Write on their importers.
9. **Thin or single-sided walls (Meshy shells) and 2–3 m alleys.**
   - Probes that see back faces become invalid. Then dilation or virtual offset pulls outside light in, or inside darkness out as dark halos at wall bases.
   - Mitigations, in order: keep `leakReductionMode = Quality`; raise `normalBias` to ~⅓ of the probe spacing; place Probe Adjustment Volumes (`InvalidateProbes`, `ApplyVirtualOffset`, `OverrideSkyDirection`) in problem interiors; use interior/exterior Rendering Layer masks (the set's internal `useRenderingLayers`/`renderingLayerMasks`; URP light layers are already on); thicken walls to about the local probe spacing.
   - Web docs say virtual offset tests colliders; the 17.6 source uses contributor *meshes* on `collisionMask` layers.
10. **Brick-size seams and sky-direction seams.** Visible as shading steps where 3 m and 9 m bricks meet. Raise `samplingNoise` slightly (static grain without TAA), or turn off `skyOcclusionShadingDirection`.
11. **Pool overflow.** Probes beyond the budget are not loaded and fall back to un-occluded ambient. Check the Rendering Debugger memory stats or the report's `approxProbeCount` against the budget table.
12. **Double ambient reduction.** Trilight ground and equator colours already fake bounce. With sky occlusion they are also multiplied by visibility, so re-tune `DayNightLightingProfile` ambient colours and `skyOcclusionIntensityMultiplier` together with `Sky fill`. The goal is contrast between shade and open ground, not a globally darker scene.
13. **Pipeline recreation at `GameSettings.Start`.** APV reloads. Check the player log for "Probe Volume System has already been initialized" or cell-loading errors.
14. **Static batching.** Do not bake in Play mode or after any `StaticBatchingUtility.Combine`: "Static batching is not supported when baking APV".
15. **Repository size.** The `.bytes` files (about 25–35 MB at 1 m, plus about 30 MB of editor support data) belong beside the baking set. Decide LFS handling before committing.

---

## 8. Verification

**1. Bake evidence** (`unity/evidence/rendering/20260930/apv/`)
- `configure.log`, `bake.log`, and `apv-bake.json` with `ok=true`, `device=Vulkan`, `bakedSkyOcclusion=1`, a plausible `approxProbeCount`, and empty `problems`.
- Record the bake time and the baking-set file sizes.

**2. Vulkan Editor visual check** (`-force-vulkan`, interactive)
- In *Rendering Debugger → Probe Volumes*, turn on *Display Probes* and view **Sky Occlusion SH** and **Sky Direction** (`DebugProbeShadingMode`, `ProbeReferenceVolume.Debug.cs:18-64`).
- Probes under awnings, in alleys and inside shops should read dark. Open ground and roofs should read bright.
- Check *Validity* for red (invalid) clusters in walls, and *Size* for brick distribution.

**3. GL native player A/B**, which is the real acceptance
- Build Linux OpenGLCore twice: legacy probes (baseline) and APV.
- Use the existing named cameras (`cam_avenue`, `cam_gate`, `cam_grid`, `cam_hill`, `cam_hero`, `cam_courtyard`, `cam_shop_recovery_close`, `cam_grounding_shop_side`), player-height close-ups under awnings and in shop doorways, and a moving walkthrough.
- Capture at fixed clock hours, for example 08:00, 13:00, 18:30 and 22:30 via the debug bridge.

**Look for:**
- shade/sun contrast returning without crushed blacks;
- no bright leaks inside shops;
- no dark halos on exterior wall bases;
- no brick seams on paving;
- NPCs and the player darkening smoothly when entering alleys;
- no change at night beyond the ambient colour;
- smooth time-of-day transitions (no popping, since only the ambient probe changes).

Also use the URP debug *Lighting Debug Mode = Global Illumination* to isolate the indirect term.

**4. Performance**
- Run the warmed standalone traversal per AGENTS.md §7 in both builds. Report p50/p95/p99/max and GPU time, plus the VRAM delta (expected ≈ +141 MB at Medium).
- If the p99 budget is at risk, try `leakReductionMode = Performance`, then 1.5 m spacing.

**5. Scoring:** use the AGENTS.md §7 0–5 rubric on lighting/depth and material readability in shade, with specific defects.

---

## 9. Source index (installed packages)

| Claim | Location |
| --- | --- |
| URP asset APV fields | `urp/Runtime/Data/UniversalRenderPipelineAsset.cs:484-502` (serialized), `:1213-1298` (internal setters), enums `:385-409`; `core/Runtime/Lighting/ProbeVolume/ProbeReferenceVolume.cs:132-166` (budget/SH enums) |
| APV init / per-camera enable / keywords | `urp/Runtime/UniversalRenderPipeline.cs:406-423, 964-975`; `urp/Runtime/ForwardLights.cs:596-618` |
| Runtime sampling and sky term | `core/Runtime/Lighting/ProbeVolume/ProbeVolume.hlsl:33-34, 699-722, 750-776`; `core/ShaderLibrary/AmbientProbe.hlsl:45-58`; `urp/ShaderLibrary/GlobalIllumination.hlsl:9-13, 80-128` |
| Sky weight from Volume | `core/Runtime/Lighting/ProbeVolume/ProbeReferenceVolume.Binding.cs:120-146`; `ProbeVolumesOptions.cs:28-95` |
| Baking-set fields | `core/Runtime/Lighting/ProbeVolume/ProbeVolumeBakingSet.cs:88-90, 184-270, 433`; `ProbeVolumeBakingSet.Editor.cs:79-99, 176, 380-388` |
| Dilation / VO defaults | `core/Runtime/Lighting/ProbeVolume/ProbeVolumeBakingProcessSettings.cs:12-52` |
| ProbeVolume component | `core/Runtime/Lighting/ProbeVolume/ProbeVolume.cs:17-81, 127-133, 170-183` |
| Bake entry / async / cancel | `core/Editor/Lighting/ProbeVolume/ProbeGIBaking.cs:342, 1253-1316, 1903-1951` |
| Env ignored when SO on | `ProbeGIBaking.cs:1135-1161` |
| Sky occlusion baker | `ProbeGIBaking.SkyOcclusion.cs:160-330`; `DynamicGI/DynamicGISkyOcclusion.urtshader` |
| Contributors filter | `core/Runtime/Lighting/ProbeVolume/ProbeVolumeGIContributor.cs:111-112, 157-180, 307-323` |
| APV-only bake skips lightmaps | `core/Editor/Lighting/ProbeVolume/AdaptiveProbeVolumes.BakePipelineDriver.cs:30-35` |
| Batch-mode prep / auto set | `core/Editor/Lighting/ProbeVolume/ProbeVolumeLightingTab.cs:505-521, 973-1080` |
| GL exclusions | `ProbeVolumeSubdivide.compute:9`, `ProbeVolumeCellDilation.compute:3`, `TraceVirtualOffset.urtshader:1`, `DynamicGISkyOcclusion.urtshader:1`, `TraceRenderingLayerMask.urtshader:1`, `core/Runtime/Debug/ProbeVolumeDebug.shader:10` |
| Pool / index memory | `core/Runtime/Lighting/ProbeVolume/ProbeBrickPool.cs:193-218, 562-634`; `ProbeBrickIndex.cs:95-132` |
| Disk layout | `core/Editor/Lighting/ProbeVolume/ProbeGIBaking.Serialization.cs:738-762, 870-899` |
| CPU lightmapper warning | `core/Editor/Lighting/ProbeVolume/ProbeVolumeBakingSetEditor.cs:430-441` |
| Unity Editor API names | `Editor/Data/Managed/UnityEngine/UnityEditor.CoreModule.xml` / `UnityEngine.CoreModule.xml` (6000.6.0f1): `EditorGraphicsSettings.defaultLightBaker`, `LightBaker.UnityComputeLightBaker`, `LightingSettings.Lightmapper.UnityComputeGPU`, `Lightmapping.SetLightingSettingsForScene`, `StaticEditorFlags.ContributeGI`, `MeshRenderer.receiveGI` |

Web references:
- [URP sky occlusion (6000.6)](https://docs.unity3d.com/6000.6/Documentation/Manual/urp/probevolumes-skyocclusion.html) — Gradient/Color ambient updates automatically; Skybox needs `DynamicGI.UpdateEnvironment`; CPU lightmapper double counts.
- [Use APV in URP](https://docs.unity3d.com/6000.6/Documentation/Manual/urp/probevolumes-use.html)
- [APV lighting panel reference](https://docs.unity3d.com/6000.6/Documentation/Manual/urp/probevolumes-lighting-panel-reference.html)
- [Probe Volumes Options override](https://docs.unity3d.com/6000.6/Documentation/Manual/urp/probevolumes-options-override-reference.html)
- [Choose a light baking backend](https://docs.unity3d.com/6000.6/Documentation/Manual/progressive-lightmapper.html)
- [Unity Compute Light Baker](https://docs.unity3d.com/6000.7/Documentation/Manual/unity-compute-light-baker.html)
- [APV light-leak troubleshooting](https://docs.unity3d.com/Manual/urp/probevolumes-troubleshoot-light-leaks.html)
