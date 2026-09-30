// Adaptive Probe Volume sky-occlusion setup and bake for Ward. Source: docs/apv-sky-occlusion-recipe.md (30 Sep 2026),
// adapted: the town volume is computed from the saved scene, the first bake uses 1.5 m spacing and 1024 samples, and
// probe sampling noise is 0.08 because the High preset now uses TAA. Launch 1 (Configure, -nographics ok) changes the
// PC pipeline asset to Probe Volumes, the project default light baker to the Unity Compute Light Baker, adds a
// LightingSettings asset, a baking set, two ProbeVolumes and GI-contributor flags. Launch 2 (BakeBatch) must run with
// -force-vulkan, WITHOUT -nographics and WITHOUT -quit.
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

        // Town volume = union of the city render chunks and the static art roots below (the basin is excluded),
        // padded, from just below the ground to ~30 m above the roofs. Computed from the saved scene in Configure().
        static readonly string[] TownBoundsRoots = { "Ward shop architecture", "Ward district retrofit", "Karaveen caravan market", "Outer Berms", "Meshy Ring Gate" };

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
            var town = TownBounds();
            EnsureVolume("APV Town", ProbeVolume.Mode.Local, town.center, town.size, false, 0, 3);
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

            foreach (var r in UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include))
                if (GameObjectUtility.GetStaticEditorFlags(r.gameObject).HasFlag(StaticEditorFlags.ContributeGI) && !MarkContributor(r)) flagged--;
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

            set.minDistanceBetweenProbes = 2f;            // first bake: 2 m keeps the bake within memory; refine once the look is judged
            set.simplificationLevels = 3;
            set.minRendererVolumeSize = 0.1f;
            set.renderersLayerMask = ~0;                  // narrow if actors share layers with static art
            set.skyOcclusion = true;
            set.skyOcclusionBakingSamples = 1024;
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
            // Opaque only (cut-out foliage and glass would block the sky like solid walls), and no empty submeshes
            // (the compute ray tracer dispatches zero thread groups for them and drops the mesh).
            var f = r.GetComponent<MeshFilter>(); var m = f ? f.sharedMesh : null;
            var mats = r.sharedMaterials;
            bool ok = m && mats.Length > 0 && mats.All(x => x && x.renderQueue < (int)RenderQueue.AlphaTest)
                      && Enumerable.Range(0, m.subMeshCount).All(i => m.GetSubMesh(i).vertexCount > 0 && m.GetIndexCount(i) > 0);
            var flags = GameObjectUtility.GetStaticEditorFlags(r.gameObject);
            flags = ok ? flags | StaticEditorFlags.ContributeGI : flags & ~StaticEditorFlags.ContributeGI;
            GameObjectUtility.SetStaticEditorFlags(r.gameObject, flags);
            var so = new SerializedObject(r);                 // never lightmaps: most meshes have no valid UV1
            so.FindProperty("m_ReceiveGI").intValue = (int)ReceiveGI.LightProbes;
            so.ApplyModifiedPropertiesWithoutUndo();
            if (PrefabUtility.IsPartOfPrefabInstance(r))
            {   // Prefab-instance edits are dropped on save unless recorded as overrides.
                PrefabUtility.RecordPrefabInstancePropertyModifications(r);
                PrefabUtility.RecordPrefabInstancePropertyModifications(r.gameObject);
            }
            EditorUtility.SetDirty(r); EditorUtility.SetDirty(r.gameObject);
            return ok;
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
            o.samplingNoise.Override(0.08f);              // High preset uses TAA since 30 Sep, which resolves this noise
            o.normalBias.Override(0.1f);
            o.viewBias.Override(0.15f);
            EditorUtility.SetDirty(o); EditorUtility.SetDirty(profile);
        }

        static Bounds TownBounds()
        {
            var b = new Bounds(); bool any = false;
            void Add(Renderer r) { if (!r || !r.enabled) return; if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds); }
            foreach (var chunks in UnityEngine.Object.FindObjectsByType<StaticRenderChunks>())
                if (chunks.generatedRoot) foreach (var r in chunks.generatedRoot.GetComponentsInChildren<MeshRenderer>(true)) Add(r);
            foreach (var name in TownBoundsRoots) { var root = GameObject.Find(name); if (root) foreach (var r in root.GetComponentsInChildren<MeshRenderer>(false)) Add(r); }
            if (!any) throw new InvalidOperationException("No town geometry found for the APV volume.");
            var min = b.min - new Vector3(6, 2, 6); var max = new Vector3(b.max.x + 6, Mathf.Min(b.max.y, b.min.y + 40) + 6, b.max.z + 6);
            var result = new Bounds(); result.SetMinMax(min, max);
            Debug.Log("APV town volume " + result.center + " size " + result.size);
            return result;
        }

        static void EnsureFolder(string folder)
        {
            if (AssetDatabase.IsValidFolder(folder)) return;
            string parent = Path.GetDirectoryName(folder).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(folder));
        }

        // Read-only: which renderers the bake will treat as GI contributors, and which look risky for the ray tracer.
        public static void DiagnoseBatch()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var rows = new List<object>(); int contributors = 0, lightmapped = 0;
            foreach (var r in UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude))
            {
                if (!GameObjectUtility.GetStaticEditorFlags(r.gameObject).HasFlag(StaticEditorFlags.ContributeGI)) continue;
                contributors++;
                var f = r.GetComponent<MeshFilter>(); var m = f ? f.sharedMesh : null;
                bool lm = r.receiveGI == ReceiveGI.Lightmaps; if (lm) lightmapped++;
                bool empty = !m || m.vertexCount == 0 || m.subMeshCount == 0 || Enumerable.Range(0, m ? m.subMeshCount : 0).Any(i => m.GetIndexCount(i) == 0);
                bool cutout = r.sharedMaterials.Any(x => x && x.renderQueue >= (int)RenderQueue.AlphaTest);
                if (lm || empty || cutout || (m && !m.isReadable) || (m && m.vertexBufferCount > 1))
                    rows.Add(new { path = PathOf(r.transform), mesh = m ? m.name : null, verts = m ? m.vertexCount : 0, subMeshes = m ? m.subMeshCount : 0, readable = m && m.isReadable, streams = m ? m.vertexBufferCount : 0, lightmapped = lm, empty, cutout });
            }
            var path = Path.GetFullPath(Path.Combine(Directory.GetParent(Application.dataPath).FullName, "../evidence/rendering/20260930/apv/diagnose.json"));
            File.WriteAllText(path, JsonConvert.SerializeObject(new { contributors, lightmapped, flagged = rows.Count, rows }, Formatting.Indented));
            Debug.Log("APV_DIAGNOSE contributors=" + contributors + " lightmapped=" + lightmapped + " flagged=" + rows.Count);
            EditorApplication.Exit(0);
        }

        static string PathOf(Transform t) { var parts = new List<string>(); for (; t; t = t.parent) parts.Add(t.name); parts.Reverse(); return string.Join("/", parts); }

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
                // The 12 GB card also hosts the desktop (~3 GB); full-resolution scene textures plus the bake ran it out
                // of memory and crashed the driver twice. Sky occlusion uses a constant albedo, so textures can load at 1/8.
                QualitySettings.globalTextureMipmapLimit = 3;
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
