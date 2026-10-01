using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: city paving and texture streaming (next-wins item 2). The whole city floor is one render-chunk
    /// source, `Paving` (120 x 90 m cube). This pass diagnoses mipmap streaming, then gives the floor a new sandstone
    /// flag material (new asset; the old `Paving Local wear` stays for rollback).
    /// Batch: -executeMethod AthenHill.Editor.CityPavingPass.RunBatch --steps diag[,...] -nographics
    /// </summary>
    public static class CityPavingPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string OldMatPath = "Assets/AthenHill/Art/Weathering/Paving Local wear.mat";
        const string Evidence = "../evidence/city-paving/20261001/";

        // ------------------------------------------------------------------ diagnostic
        public static string Diagnose()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var r = new Dictionary<string, object>();
            var paving = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Paving");
            var joints = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Paving Joints");
            var col = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "COL_Ground");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            object Tf(Transform t) => t ? new { pos = t.position.ToString("F3"), rot = t.eulerAngles.ToString("F2"), scale = t.lossyScale.ToString("F3") } : null;
            if (paving)
            {
                var mf = paving.GetComponent<MeshFilter>(); var mr = paving.GetComponent<MeshRenderer>();
                var m = mf ? mf.sharedMesh : null;
                r["paving"] = new
                {
                    tf = Tf(paving.transform), mesh = m ? m.name + " " + AssetDatabase.GetAssetPath(m) : null,
                    uvMin = m ? m.uv.Aggregate(Vector2.positiveInfinity, Vector2.Min).ToString("F3") : null,
                    uvMax = m ? m.uv.Aggregate(Vector2.negativeInfinity, Vector2.Max).ToString("F3") : null,
                    uvMetric = m ? m.GetUVDistributionMetric(0) : 0,
                    rendererEnabled = mr ? mr.enabled : false, mats = mr ? mr.sharedMaterials.Select(x => x ? AssetDatabase.GetAssetPath(x) : "null").ToArray() : null,
                    shadows = mr ? mr.shadowCastingMode.ToString() : null, children = paving.transform.childCount,
                    components = paving.GetComponents<Component>().Select(c => c.GetType().Name).ToArray(),
                };
            }
            if (chunks)
            {
                var vis = new List<object>();
                for (int i = 0; i < chunks.sources.Length; i++)
                {
                    var s = chunks.sources[i];
                    if (!s) continue;
                    if (s.name == "Paving" || s.name.StartsWith("Paving joint") || s.name.StartsWith("Avenue service band") || s.name.StartsWith("Plaza inset"))
                        vis.Add(new { s.name, path = PathOf(s.transform), visible = chunks.sourceVisibility[i], active = s.gameObject.activeInHierarchy, mats = s.sharedMaterials.Select(x => x ? x.name : "null").ToArray(), bounds = s.bounds.center.ToString("F2") + " " + s.bounds.size.ToString("F2") });
                }
                r["chunkSources"] = vis;
                r["chunkRoots"] = chunks.sourceRoots.Select(t => t ? PathOf(t) : "null").ToArray();
                r["chunkCount"] = chunks.generatedRoot ? chunks.generatedRoot.childCount : 0;
                r["chunkFingerprintOk"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
                r["groundChunks"] = chunks.generatedRoot ? chunks.generatedRoot.GetComponentsInChildren<MeshRenderer>(true)
                    .Where(x => x.sharedMaterial && (x.sharedMaterial.name.Contains("Paving") || x.sharedMaterial.name.Contains("Gunmetal")))
                    .Select(x => new { x.name, mat = x.sharedMaterial.name, mesh = x.GetComponent<MeshFilter>().sharedMesh.name, uvMetric = x.GetComponent<MeshFilter>().sharedMesh.GetUVDistributionMetric(0), bounds = x.bounds.center.ToString("F2") + " " + x.bounds.size.ToString("F2") }).ToArray() : null;
            }
            r["joints"] = joints ? new { active = joints.activeSelf, count = joints.transform.childCount } : null;
            r["colGround"] = col ? new { tf = Tf(col.transform), box = col.GetComponent<BoxCollider>() ? col.GetComponent<BoxCollider>().size.ToString("F2") : null } : null;
            var mat = AssetDatabase.LoadAssetAtPath<Material>(OldMatPath);
            r["material"] = MatInfo(mat);
            r["textures"] = new[] { "_BaseMap", "_BumpMap" }.Select(p => TexInfo(mat.GetTexture(p) as Texture2D)).ToArray();
            var q = new List<object>();
            for (int i = 0; i < QualitySettings.names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                q.Add(new { name = QualitySettings.names[i], QualitySettings.streamingMipmapsActive, QualitySettings.streamingMipmapsMemoryBudget, QualitySettings.streamingMipmapsMaxLevelReduction, QualitySettings.streamingMipmapsRenderersPerFrame, QualitySettings.globalTextureMipmapLimit, aniso = QualitySettings.anisotropicFiltering.ToString() });
            }
            r["quality"] = q;
            // Ground-level surfaces near the avenue (to coordinate with other passes' separate meshes).
            r["groundSurfaces"] = UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include)
                .Where(x => x.bounds.max.y < 0.35f && x.bounds.size.x * x.bounds.size.z > 20 && x.gameObject.activeInHierarchy)
                .Select(x => PathOf(x.transform) + " | " + (x.sharedMaterial ? x.sharedMaterial.name : "null") + " | " + x.bounds.center.ToString("F1") + " " + x.bounds.size.ToString("F1") + " | enabled " + x.enabled)
                .OrderBy(x => x).ToArray();
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "diagnose.json", json);
            return "wrote " + Evidence + "diagnose.json";
        }

        static object MatInfo(Material m) => m ? new
        {
            path = AssetDatabase.GetAssetPath(m), shader = m.shader.name, keywords = m.shaderKeywords,
            tex = m.GetTexturePropertyNames().Where(p => m.GetTexture(p)).Select(p => p + "=" + m.GetTexture(p).name + " st " + m.GetTextureScale(p) + m.GetTextureOffset(p)).ToArray(),
        } : null;

        static object TexInfo(Texture2D t)
        {
            if (!t) return null;
            var path = AssetDatabase.GetAssetPath(t);
            var i = AssetImporter.GetAtPath(path) as TextureImporter;
            return new
            {
                path, t.width, t.height, mips = t.mipmapCount, format = t.format.ToString(), t.streamingMipmaps, t.streamingMipmapsPriority, t.anisoLevel, filter = t.filterMode.ToString(),
                importer = i ? new { type = i.textureType.ToString(), i.sRGBTexture, i.maxTextureSize, compression = i.textureCompression.ToString(), npot = i.npotScale.ToString(), i.convertToNormalmap, i.heightmapScale } : null,
                runtimeMB = UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(t) / 1048576.0,
            };
        }

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        // ------------------------------------------------------------------ review cameras (player eye 1.62 m)
        public const string CamRootName = "City paving review cameras";
        public static readonly (string name, Vector3 pos, Vector3 target, float fov)[] ReviewViews =
        {
            ("cam_pv_feet", new Vector3(40f, 1.62f, 10f), new Vector3(40.6f, 0f, 12.4f), 60),              // ground at the player's feet
            ("cam_pv_east_lane", new Vector3(31f, 1.62f, -16f), new Vector3(31.5f, 0.6f, 14f), 60),        // 2-40 m along the east lane
            ("cam_pv_north_lane", new Vector3(-14f, 1.62f, 26f), new Vector3(20f, 0.5f, 25.5f), 60),       // north lane, grazing
            ("cam_pv_west_open", new Vector3(-34f, 1.62f, -16f), new Vector3(-50f, 0.4f, 10f), 60),        // big open west paving
            ("cam_pv_courtyard_edge", new Vector3(17f, 1.62f, -4f), new Vector3(11f, 0f, -11f), 60),      // meets the courtyard stone
            ("cam_pv_south_lane", new Vector3(-30f, 1.62f, -23.5f), new Vector3(8f, 0.5f, -23f), 60),      // south lane by the hall
        };

        public static string AddReviewCameras()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            foreach (var (name, pos, target, fov) in ReviewViews)
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var c = go.AddComponent<Camera>(); c.enabled = false; c.fieldOfView = fov; c.nearClipPlane = .05f;
            }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return ReviewViews.Length + " cameras under " + CamRootName;
        }

        // ------------------------------------------------------------------ assets: textures + material
        const string ArtRoot = "Assets/AthenHill/Art/CityPaving/";
        const string TexDir = ArtRoot + "Textures/";
        public const string MatPath = ArtRoot + "Materials/PV_CityFlags.mat";
        const string ShaderName = "Athen Hill/Ward Paving Lit";
        const string SourceDir = "../../art/city_paving_20261001/out/";
        public const int StreamingBudgetMB = 5632;

        static Texture2D ImportTex(string src, string dst, bool srgb, bool normal, int max)
        {
            File.Copy(SourceDir + src, dst, true);
            AssetDatabase.ImportAsset(dst, ImportAssetOptions.ForceSynchronousImport);
            var i = (TextureImporter)AssetImporter.GetAtPath(dst);
            i.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            i.sRGBTexture = srgb && !normal; i.alphaSource = TextureImporterAlphaSource.FromInput; i.alphaIsTransparency = false;
            i.mipmapEnabled = true; i.wrapMode = TextureWrapMode.Repeat; i.filterMode = FilterMode.Trilinear; i.anisoLevel = 8;
            i.maxTextureSize = max; i.textureCompression = TextureImporterCompression.CompressedHQ; i.npotScale = TextureImporterNPOTScale.None;
            // The city floor is always under the camera: keep it fully resident instead of trusting the streaming estimate.
            i.streamingMipmaps = false;
            i.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(dst);
        }

        public static string BuildAssets()
        {
            Directory.CreateDirectory(TexDir); Directory.CreateDirectory(ArtRoot + "Materials");
            var baseMap = ImportTex("PV_Flags_BaseMap_2k.png", TexDir + "PV_Flags_BaseMap.png", true, false, 2048);
            var normal = ImportTex("PV_Flags_Normal_2k.png", TexDir + "PV_Flags_Normal.png", false, true, 2048);
            var mask = ImportTex("PV_Flags_Mask_2k.png", TexDir + "PV_Flags_Mask.png", false, false, 2048);
            var grain = ImportTex("PV_Grain_Normal_1k.png", TexDir + "PV_Grain_Normal.png", false, true, 1024);
            var shader = Shader.Find(ShaderName);
            if (!shader) throw new Exception("shader missing: " + ShaderName);
            var old = AssetDatabase.LoadAssetAtPath<Material>(OldMatPath);
            var m = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
            if (!m) { m = new Material(shader) { name = "PV_CityFlags" }; AssetDatabase.CreateAsset(m, MatPath); }
            m.shader = shader;
            m.SetTexture("_BaseMap", baseMap); m.SetTexture("_MainTex", baseMap);
            // mesh UVs of the 120 x 90 m Paving cube -> 4 m tiles (used only by the depth/meta passes and the debug views;
            // the forward pass maps the flags in world XZ)
            m.SetTextureScale("_BaseMap", new Vector2(30f, 22.5f)); m.SetTextureScale("_MainTex", new Vector2(30f, 22.5f));
            m.SetTexture("_BumpMap", normal); m.SetFloat("_BumpScale", 1f); m.EnableKeyword("_NORMALMAP");
            m.SetTexture("_PavingMask", mask); m.SetTexture("_GrainNormal", grain);
            foreach (var p in new[] { "_WearStrength", "_WearScale", "_BaseWear" }) m.SetFloat(p, old.GetFloat(p));
            m.SetColor("_WearTint", old.GetColor("_WearTint"));
            m.SetFloat("_Smoothness", .5f); m.SetFloat("_Metallic", 0); m.SetFloat("_ReceiveShadows", 1);
            m.SetFloat("_EnvironmentReflections", 1); m.SetFloat("_SpecularHighlights", 1);
            m.enableInstancing = true;
            m.SetShaderPassEnabled("MotionVectors", false);
            ApplyTuning(m);
            EditorUtility.SetDirty(m); AssetDatabase.SaveAssets();
            return "material " + MatPath + " (" + shader.name + "), textures " + string.Join(", ", new Texture2D[] { baseMap, normal, mask, grain }.Select(t => t.name + " " + t.width + " " + t.format));
        }

        /// The plaza bands framing the hill block (the old `Plaza inset` strips, which still carried the old paving texture)
        /// get the same flags run north-south with their own tint: PV_CityFlags_Band = PV_CityFlags + tuning-band.json.
        public const string BandMatPath = ArtRoot + "Materials/PV_CityFlags_Band.mat";
        const string OldBandMatPath = "Assets/AthenHill/Art/Weathering/PlazaPaving Local wear.mat";

        public static string BuildBandMaterial()
        {
            var src = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
            var m = AssetDatabase.LoadAssetAtPath<Material>(BandMatPath);
            if (!m) { m = new Material(src) { name = "PV_CityFlags_Band" }; AssetDatabase.CreateAsset(m, BandMatPath); }
            m.CopyPropertiesFromMaterial(src); m.shaderKeywords = src.shaderKeywords;
            ApplyTuning(m, "../tuning-band.json");
            EditorUtility.SetDirty(m); AssetDatabase.SaveAssets();
            return "band material " + BandMatPath + " axis " + m.GetFloat("_CourseAxis");
        }

        /// Idempotent: points the Plaza inset strips at the band material and rebuilds the render chunks.
        public static string InstallBands()
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(BandMatPath);
            if (!mat) throw new Exception("run bandmat first");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            var insets = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshRenderer>(true)).Where(x => x.name.StartsWith("Plaza inset")).ToArray();
            var changed = insets.Where(x => x.sharedMaterial != mat).ToArray();
            if (changed.Length > 0)
            {
                chunks.ShowSources(true);
                foreach (var x in changed) x.sharedMaterial = mat;
                StaticRenderChunksEditor.Rebuild(chunks);
            }
            var rec = new { insets = insets.Select(x => PathOf(x.transform) + " " + x.bounds.center.ToString("F1") + " " + x.bounds.size.ToString("F1")).ToArray(), changed = changed.Length, oldMaterial = OldBandMatPath, newMaterial = BandMatPath, utc = DateTime.UtcNow.ToString("O") };
            var json = JsonConvert.SerializeObject(rec, Formatting.Indented);
            File.WriteAllText(Evidence + "install-bands.json", json);
            return json;
        }

        /// Material tuning lives here (one place, re-applied by "assets"), so look iterations are a re-run, not hand edits.
        static void ApplyTuning(Material m, string file = "../tuning.json")
        {
            var tune = File.Exists(SourceDir + file) ? Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(SourceDir + file)) : new Newtonsoft.Json.Linq.JObject();
            foreach (var p in tune.Properties())
            {
                if (p.Value.Type == Newtonsoft.Json.Linq.JTokenType.Array)
                {
                    var a = p.Value.Select(x => (float)x).ToArray();
                    m.SetColor(p.Name, new Color(a[0], a[1], a[2], a.Length > 3 ? a[3] : 1));
                }
                else m.SetFloat(p.Name, (float)p.Value);
            }
        }

        // ------------------------------------------------------------------ install (one time) / verify
        static readonly string[] RetireNames = { "Avenue service band" };   // the dark gunmetal "rails" on the avenue ring

        public static string Install()
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
            if (!mat) throw new Exception("run assets first");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var paving = scene.GetRootGameObjects().First(g => g.name == "Paving");
            var r = paving.GetComponent<MeshRenderer>();
            var rec = new Dictionary<string, object>();
            Directory.CreateDirectory(Evidence + "rollback");
            if (!File.Exists(Evidence + "rollback/before-city-paving.unity")) File.Copy(ScenePath, Evidence + "rollback/before-city-paving.unity", true);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            chunks.ShowSources(true);
            rec["oldMaterial"] = r.sharedMaterial ? AssetDatabase.GetAssetPath(r.sharedMaterial) : null;
            r.sharedMaterial = mat;
            rec["newMaterial"] = MatPath;
            var joints = scene.GetRootGameObjects().First(g => g.name == "Paving Joints");
            rec["jointsWasActive"] = joints.activeSelf; joints.SetActive(false);
            var retired = new List<string>();
            foreach (var t in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)))
                if (RetireNames.Contains(t.name) && t.gameObject.activeSelf) { t.gameObject.SetActive(false); retired.Add(PathOf(t) + " @" + t.position.ToString("F1")); }
            rec["retired"] = retired;
            StaticRenderChunksEditor.Rebuild(chunks);      // saves the scene
            rec["streamingBudget"] = SetStreamingBudget(StreamingBudgetMB);
            rec["utc"] = DateTime.UtcNow.ToString("O");
            var json = JsonConvert.SerializeObject(rec, Formatting.Indented);
            File.WriteAllText(Evidence + "install.json", json);
            return json;
        }

        /// PC quality level only. Returns "old -> new".
        static string SetStreamingBudget(int mb)
        {
            var qs = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/QualitySettings.asset").FirstOrDefault();
            var so = new SerializedObject(qs);
            var levels = so.FindProperty("m_QualitySettings");
            for (int i = 0; i < levels.arraySize; i++)
            {
                var lvl = levels.GetArrayElementAtIndex(i);
                if (lvl.FindPropertyRelative("name").stringValue != "PC") continue;
                var b = lvl.FindPropertyRelative("streamingMipmapsMemoryBudget");
                var old = b.floatValue; b.floatValue = mb;
                so.ApplyModifiedPropertiesWithoutUndo(); AssetDatabase.SaveAssets();
                return old + " -> " + mb;
            }
            throw new Exception("PC quality level not found");
        }

        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
            var paving = scene.GetRootGameObjects().First(g => g.name == "Paving");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            var gen = chunks.generatedRoot.GetComponentsInChildren<MeshRenderer>(true);
            var pavingChunks = gen.Where(x => x.sharedMaterial == mat).ToArray();
            var r = new Dictionary<string, object>
            {
                ["installed"] = paving.GetComponent<MeshRenderer>().sharedMaterial == mat,
                ["material"] = MatInfo(mat),
                ["shader"] = mat.shader.name, ["shaderSupported"] = mat.shader.isSupported,
                ["pavingChunks"] = pavingChunks.Select(x => x.name + " " + x.GetComponent<MeshFilter>().sharedMesh.GetUVDistributionMetric(0).ToString("F1")).ToArray(),
                ["bandChunks"] = gen.Where(x => x.sharedMaterial && AssetDatabase.GetAssetPath(x.sharedMaterial) == BandMatPath).Select(x => x.name).ToArray(),
                ["insets"] = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshRenderer>(true)).Where(x => x.name.StartsWith("Plaza inset")).Select(x => x.name + " " + (x.sharedMaterial ? x.sharedMaterial.name : "null")).ToArray(),
                ["oldBandMaterialChunks"] = gen.Count(x => x.sharedMaterial && AssetDatabase.GetAssetPath(x.sharedMaterial) == OldBandMatPath),
                ["oldMaterialChunks"] = gen.Count(x => x.sharedMaterial && AssetDatabase.GetAssetPath(x.sharedMaterial) == OldMatPath),
                ["chunkFingerprintOk"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks) && !chunks.editingSources,
                ["chunkMetricsUnset"] = gen.Count(x => Mathf.Approximately(x.GetComponent<MeshFilter>().sharedMesh.GetUVDistributionMetric(0), 1f)),
                ["chunkCount"] = gen.Length,
                ["missingMaterials"] = gen.Count(x => x.sharedMaterials.Any(m => !m)),
                ["jointsActive"] = scene.GetRootGameObjects().First(g => g.name == "Paving Joints").activeSelf,
                ["serviceBandsActive"] = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).Count(t => RetireNames.Contains(t.name) && t.gameObject.activeInHierarchy),
                ["colGround"] = scene.GetRootGameObjects().Any(g => g.name == "COL_Ground" && g.activeSelf && g.GetComponent<BoxCollider>()),
                ["oldMaterialKept"] = File.Exists(OldMatPath) && File.Exists("Assets/AthenHill/Art/Textures/AAA/Paving_Albedo.png"),
                ["textures"] = new[] { "_BaseMap", "_BumpMap", "_PavingMask", "_GrainNormal" }.Select(p => TexInfo(mat.GetTexture(p) as Texture2D)).ToArray(),
                ["reviewCameras"] = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName)?.transform.childCount ?? 0,
            };
            for (int i = 0; i < QualitySettings.names.Length; i++)
                if (QualitySettings.names[i] == "PC") { QualitySettings.SetQualityLevel(i, false); r["pcStreamingBudgetMB"] = QualitySettings.streamingMipmapsMemoryBudget; }
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        // ------------------------------------------------------------------ A/B builds from one snapshot of the saved scene
        // "on" = the saved scene; "off" = a copy with the paving and band materials reverted to the old ones (sources + their
        // chunk renderers, fingerprint recomputed in the copy). Retired strips and the budget are identical in both arms.
        const string AbOnCopy = "Assets/AthenHill/Scenes/__cp_ab_on.unity", AbOffCopy = "Assets/AthenHill/Scenes/__cp_ab_off.unity";

        static string AbBuild(string arm)
        {
            string src;
            if (arm == "on")
            {
                var scene = EditorSceneManager.OpenScene(ScenePath);
                if (!EditorSceneManager.SaveScene(scene, AbOnCopy, true)) throw new Exception("could not write " + AbOnCopy);
                var swap = new Dictionary<Material, Material>
                {
                    [AssetDatabase.LoadAssetAtPath<Material>(MatPath)] = AssetDatabase.LoadAssetAtPath<Material>(OldMatPath),
                    [AssetDatabase.LoadAssetAtPath<Material>(BandMatPath)] = AssetDatabase.LoadAssetAtPath<Material>(OldBandMatPath),
                };
                var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
                int swapped = 0;
                foreach (var x in chunks.sources.Concat(chunks.generatedRoot.GetComponentsInChildren<MeshRenderer>(true)))
                    if (x && x.sharedMaterial && swap.TryGetValue(x.sharedMaterial, out var o)) { x.sharedMaterial = o; swapped++; }
                if (swapped < 3) throw new Exception("expected the paving + band sources and chunks, swapped " + swapped);
                chunks.sourceFingerprint = StaticRenderChunksEditor.Fingerprint(chunks);
                if (!EditorSceneManager.SaveScene(scene, AbOffCopy, true)) throw new Exception("could not write " + AbOffCopy);
                src = AbOnCopy;
            }
            else
            {
                if (!File.Exists(AbOffCopy)) throw new Exception("Run abbuild:on first (it writes the scene snapshot for both arms).");
                src = AbOffCopy;
            }
            try { return BuildPlayer("ab-" + arm, src); }
            finally { if (arm == "off") { AssetDatabase.DeleteAsset(AbOnCopy); AssetDatabase.DeleteAsset(AbOffCopy); } }
        }

        // ------------------------------------------------------------------ development player builds (own folders)
        /// Builds a development player (OpenGL) from a scene path into Builds/cp-&lt;name&gt;. Never modifies the scene.
        static string BuildPlayer(string name, string scenePath)
        {
            EditorSceneManager.OpenScene(scenePath);
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneLinux64, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneLinux64, new[] { UnityEngine.Rendering.GraphicsDeviceType.OpenGLCore });
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { scenePath }, locationPathName = "Builds/cp-" + name + "/AthenHill.x86_64",
                target = BuildTarget.StandaloneLinux64, options = BuildOptions.Development,
            });
            if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("build failed: " + name);
            return "Builds/cp-" + name + " " + report.summary.totalTime.TotalSeconds.ToString("0") + " s, " + (report.summary.totalSize / 1048576) + " MB";
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 ? args[i + 1].Split(',') : new[] { "diag" };
            try
            {
                foreach (var s in steps)
                {
                    var parts = s.Split(':');
                    var result = parts[0] switch
                    {
                        "diag" => Diagnose(),
                        "cameras" => AddReviewCameras(),
                        "build" => BuildPlayer(parts[1], ScenePath),
                        "assets" => BuildAssets(),
                        "install" => Install(),
                        "bandmat" => BuildBandMaterial(),
                        "bands" => InstallBands(),
                        "verify" => Verify(),
                        "abbuild" => AbBuild(parts[1]),
                        _ => throw new Exception("unknown step " + s),
                    };
                    Debug.Log("CityPavingPass " + s + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
