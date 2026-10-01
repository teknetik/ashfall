using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: wall-foot sand and grounding (art-direction review item 6, "where buildings meet the paving the
    /// junction is knife-clean"). Low wind-laid sand banks along the feet of the avenue-ring buildings (the eight shops'
    /// porch risers, steps, side and rear walls and porch-deck facades, the Basic General booth, Vanguard Hall's podium and
    /// deck walls, the hill plinth and stair cheeks), banks in the inside corners, collars with lee tails round the lamp and
    /// service-lane posts and thin sand floors in the four shop alleys; plus URP decals: a sand-dust band on the ground along
    /// each banked stretch, a dust and contact-grime skirt on the walls, collars under the posts and sheets under the alley
    /// sand. Heavier on faces into the west-south-west wind; doors, bays, steps' walked middles, props, routes and NPC points
    /// kept clear (art/wall_foot_drifts_20261001/layout.py validates every placement).
    ///
    /// Sources: art/wall_foot_drifts_20261001 (author_drift_kit.py → Art/WallFootDrifts/Models/WFD_Kit.glb: eight pieces,
    /// LOD0-2; make_textures.py → the sand material and decal textures; faces.py + probe_faces.py → the measured wall feet;
    /// layout.py → layout.json). One sand material (URP Lit), four decal materials (copies of the Ward weathering decal).
    /// No shadows, no colliders, no lights; nothing retired; not a render-chunk source.
    /// Menu: Athen Hill → Wall-foot drifts → Build assets, Install (one time; rollback copy), Verify saved scene, Add review
    /// cameras. Batch: RunBatch --steps build,install,verify,capture[:filter[:off]] [--out dir].
    /// </summary>
    public static class WallFootDriftsPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/WallFootDrifts/";
        const string ModelPath = Root + "Models/WFD_Kit.glb";
        const string TexDir = Root + "Textures/";
        const string MatDir = Root + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/WallFootDrifts/";
        const string DecalTemplate = "Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat";
        // a copy of the Ward weathering decal graph (Art/Weathering/WardDecal.shadergraph) with angle fade enabled, so ground
        // films fade off walls and props and wall skirts fade off the ground (the shared graph has angle fade off)
        const string DecalGraph = Root + "Shaders/WFD_Decal.shadergraph";
        const string LayoutPath = "../../art/wall_foot_drifts_20261001/layout.json";
        const string Evidence = "../evidence/wall-foot-drifts/20261001/";
        public const string RootName = "Ward wall-foot drifts";
        public const string CamRootName = "Wall-foot drift review cameras";
        static readonly string[] Pieces = { "Run_L", "Run_M", "Run_S", "Run_Low", "Corner_L", "Corner_S", "Post", "Sheet" };
        static readonly string[] DecalNames = { "WFD_DecalFootBand", "WFD_DecalWallSkirt", "WFD_DecalPost", "WFD_DecalSheet" };

        // LOD switches (metres at 60° FOV, PC lodBias 2): LOD0 within ~10 m, LOD1 to ~28 m, LOD2 to ~60 m, culled beyond.
        const float Lod0Distance = 10f, Lod1Distance = 28f, CullDistance = 60f, LodBias = 2f;
        const float DecalDistance = 40f;                      // the district's decals stay under the 45 m cap
        const float SandTile = 1.5f;                          // metres per sand texture tile (mesh UV0 is in metres)

        static JObject Layout() => JObject.Parse(File.ReadAllText(LayoutPath));
        static string PrefabPath(string piece) => PrefabDir + "WFD_" + piece + ".prefab";
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);

        // ------------------------------------------------------------------ build assets
        [MenuItem("Athen Hill/Wall-foot drifts/Build assets")]
        public static string BuildAssets()
        {
            AssetDatabase.Refresh();
            ImportTextures();
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceUpdate);
            Directory.CreateDirectory(MatDir);
            var sand = SandMaterial();
            var decals = DecalMaterials();
            Directory.CreateDirectory(PrefabDir);
            var report = new Dictionary<string, object>();
            foreach (var p in Pieces) report[p] = BuildPrefab(p, sand);
            AssetDatabase.SaveAssets();
            var json = JsonConvert.SerializeObject(new { prefabs = report, sand = AssetDatabase.GetAssetPath(sand), decals = decals.Keys.ToArray() }, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "build-assets.json", json);
            return "prefabs " + report.Count + ", decal materials " + decals.Count;
        }

        static void ImportTextures()
        {
            foreach (var f in Directory.GetFiles(TexDir, "*.png"))
            {
                var path = f.Replace('\\', '/');
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                if (!ti) continue;
                var name = Path.GetFileNameWithoutExtension(path);
                ti.mipmapEnabled = true; ti.streamingMipmaps = true; ti.anisoLevel = 8; ti.maxTextureSize = 2048;
                if (name == "WFD_Sand_Normal")
                {
                    ti.textureType = TextureImporterType.NormalMap; ti.sRGBTexture = false; ti.wrapMode = TextureWrapMode.Repeat;
                    ti.textureCompression = TextureImporterCompression.CompressedHQ;
                }
                else if (name == "WFD_Sand_BaseMap")
                {
                    ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.wrapMode = TextureWrapMode.Repeat;
                    ti.alphaSource = TextureImporterAlphaSource.None; ti.textureCompression = TextureImporterCompression.Compressed;
                }
                else
                {
                    // decals: bands and skirts fade out at both ends (segments overlap by the fade), collars and sheets all round
                    ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.alphaIsTransparency = true;
                    ti.alphaSource = TextureImporterAlphaSource.FromInput; ti.anisoLevel = 4;
                    ti.wrapMode = TextureWrapMode.Clamp;           // non-tiling: every decal texture fades out at its edges
                    ti.textureCompression = TextureImporterCompression.CompressedHQ;
                }
                ti.SaveAndReimport();
            }
        }

        static Texture2D Tex(string name)
        {
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + name + ".png");
            if (!t) throw new Exception("Texture missing: " + TexDir + name + ".png (run make_textures.py)");
            return t;
        }

        static Material SandMaterial()
        {
            var path = MatDir + "WFD_Sand.mat";
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? throw new Exception("URP Lit shader missing");
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader) { name = "WFD_Sand" }; AssetDatabase.CreateAsset(m, path); }
            m.shader = shader;
            m.SetTexture("_BaseMap", Tex("WFD_Sand_BaseMap"));
            m.SetTextureScale("_BaseMap", Vector2.one / SandTile);
            m.SetColor("_BaseColor", new Color(1f, 0.985f, 0.96f, 1f));
            m.SetTexture("_BumpMap", Tex("WFD_Sand_Normal"));
            m.SetFloat("_BumpScale", 1f);
            m.EnableKeyword("_NORMALMAP");
            m.SetFloat("_Metallic", 0f);
            m.SetFloat("_Smoothness", 0.12f);
            m.SetTexture("_MetallicGlossMap", null);
            m.DisableKeyword("_METALLICSPECGLOSSMAP");
            m.SetFloat("_EnvironmentReflections", 1f);
            m.SetFloat("_SpecularHighlights", 1f);
            m.SetFloat("_ReceiveShadows", 1f);
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            return m;
        }

        static Dictionary<string, Material> DecalMaterials()
        {
            var template = AssetDatabase.LoadAssetAtPath<Material>(DecalTemplate);
            if (!template || !template.HasProperty("Base_Map")) throw new Exception("Decal template missing or without Base_Map: " + DecalTemplate);
            AssetDatabase.ImportAsset(DecalGraph, ImportAssetOptions.ForceUpdate);
            var graph = AssetDatabase.LoadAssetAtPath<Shader>(DecalGraph) ?? throw new Exception("Decal shader graph missing: " + DecalGraph);
            var mats = new Dictionary<string, Material>();
            foreach (var n in DecalNames)
            {
                var path = MatDir + n + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!m) { m = new Material(template) { name = n }; AssetDatabase.CreateAsset(m, path); }
                else { m.shader = template.shader; m.CopyPropertiesFromMaterial(template); }
                m.shader = graph;
                m.SetTexture("Base_Map", Tex(n));
                if (m.HasProperty("Normal_Blend")) m.SetFloat("Normal_Blend", 0);
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
                mats[n] = m;
            }
            return mats;
        }

        static Dictionary<string, Material> LoadDecalMaterials()
        {
            var d = new Dictionary<string, Material>();
            foreach (var n in DecalNames)
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(MatDir + n + ".mat");
                if (!m) throw new Exception("Decal material missing (build first): " + MatDir + n + ".mat");
                d[n] = m;
            }
            return d;
        }

        static int Tris(Mesh mesh)
        {
            if (!mesh) return 0;
            int n = 0;
            for (int s = 0; s < mesh.subMeshCount; s++) n += (int)mesh.GetIndexCount(s) / 3;
            return n;
        }

        static object BuildPrefab(string piece, Material sand)
        {
            var meshes = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Mesh>().ToList();
            var root = new GameObject("WFD_" + piece);
            var rec = new Dictionary<string, object>();
            try
            {
                var levels = new List<LOD>();
                for (int lod = 0; lod < 3; lod++)
                {
                    var mesh = meshes.FirstOrDefault(m => m.name == $"WFD_{piece}_LOD{lod}") ?? meshes.FirstOrDefault(m => m.name.StartsWith($"WFD_{piece}_LOD{lod}"));
                    if (!mesh) throw new Exception($"Mesh WFD_{piece}_LOD{lod} not in {ModelPath} (have: {string.Join(", ", meshes.Select(m => m.name))})");
                    var go = new GameObject("LOD" + lod);
                    go.transform.SetParent(root.transform, false);
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var r = go.AddComponent<MeshRenderer>();
                    r.sharedMaterial = sand;
                    r.shadowCastingMode = ShadowCastingMode.Off;          // low sand: SSAO and the receiving shadows ground it
                    r.receiveShadows = true;
                    r.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
                    r.receiveGI = ReceiveGI.LightProbes; r.lightProbeUsage = LightProbeUsage.BlendProbes;
                    r.reflectionProbeUsage = ReflectionProbeUsage.BlendProbes;
                    levels.Add(new LOD(new[] { .5f, .2f, .01f }[lod], new Renderer[] { r }));
                    rec["LOD" + lod] = Tris(mesh);
                }
                var g = root.AddComponent<LODGroup>();
                g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                float H(float d) => Mathf.Clamp(g.size * LodBias / (2f * d * Mathf.Tan(30f * Mathf.Deg2Rad)), .002f, .98f);
                var cuts = new[] { H(Lod0Distance), H(Lod1Distance), H(CullDistance) };
                for (int i = 0; i < levels.Count; i++) levels[i] = new LOD(cuts[i], levels[i].renderers);
                g.SetLODs(levels.ToArray()); g.RecalculateBounds();
                rec["lodCuts"] = cuts.Select(c => Math.Round(c, 4)).ToArray();
                rec["size"] = Math.Round(g.size, 2);
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(piece));
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
            return rec;
        }

        // ------------------------------------------------------------------ scene helpers
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        static readonly Dictionary<string, string> GroupNames = new Dictionary<string, string>
        {
            ["relay_works"] = "Relay Works", ["air_water"] = "Air + Water", ["tool_exchange"] = "Tool Exchange", ["salvage"] = "Salvage",
            ["finery"] = "Finery", ["field_supply"] = "Field Supply", ["repairs"] = "Repairs", ["thread_hide"] = "Thread + Hide",
            ["basic_general"] = "Basic General", ["vanguard_hall"] = "Vanguard Hall", ["ward_hill"] = "Hill plinth and stairs",
            ["post"] = "Posts", ["alley"] = "Shop alleys",
        };

        static string GroupOf(string source)
        {
            var key = source.Split('/')[0].Split(' ')[0];
            return GroupNames.TryGetValue(key, out var n) ? n : key;
        }

        static Transform Group(Transform root, string name)
        {
            var t = root.Find(name);
            if (!t) { t = new GameObject(name).transform; t.SetParent(root, false); }
            return t;
        }

        static GameObject Place(UnityEngine.SceneManagement.Scene scene, JObject layout, out Dictionary<string, object> record)
        {
            var root = new GameObject(RootName);
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
            var prefabs = Pieces.ToDictionary(p => p, p => AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(p)) ?? throw new Exception("Prefab missing (build first): " + PrefabPath(p)));
            var mats = LoadDecalMaterials();
            var byPiece = new Dictionary<string, int>();
            foreach (JObject p in layout["pieces"])
            {
                var piece = (string)p["piece"];
                var src = (string)p["source"];
                var parent = Group(root.transform, GroupOf(src));
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefabs[piece], scene);
                go.transform.SetParent(parent, false);
                go.transform.SetPositionAndRotation(V3(p["pos"]), Quaternion.Euler(0, (float)p["yaw"], 0));
                go.transform.localScale = Vector3.one * (float)p["scale"];
                var tail = src.Contains('/') ? src.Substring(src.IndexOf('/') + 1) : src;
                go.name = piece + " · " + tail;
                byPiece[piece] = byPiece.TryGetValue(piece, out var c) ? c + 1 : 1;
            }
            var byDecal = new Dictionary<string, int>();
            foreach (JObject d in layout["decals"])
            {
                var kind = (string)d["kind"];
                var src = (string)d["source"];
                var parent = Group(Group(root.transform, GroupOf(src)), "Decals");
                var go = new GameObject("Decal " + kind + " · " + (src.Contains('/') ? src.Substring(src.IndexOf('/') + 1) : src));
                go.transform.SetParent(parent, false);
                var proj = go.AddComponent<DecalProjector>();
                proj.material = kind switch
                {
                    "band" => mats["WFD_DecalFootBand"],
                    "skirt" => mats["WFD_DecalWallSkirt"],
                    "post" => mats["WFD_DecalPost"],
                    _ => mats["WFD_DecalSheet"],
                };
                var size = V3(d["size"]);
                var fwd = V3(d["fwd"]).normalized;
                var uv = d["uv"];
                if (uv != null && uv.Type == JTokenType.Array) { proj.uvScale = new Vector2((float)uv[0], (float)uv[1]); proj.uvBias = new Vector2((float)uv[2], (float)uv[3]); }
                proj.fadeFactor = (float)d["opacity"]; proj.drawDistance = DecalDistance; proj.fadeScale = .75f;
                if (kind == "skirt")
                {
                    // on the wall: projected into it, texture V up the wall; box 0.2 m either side of the face
                    go.transform.SetPositionAndRotation(V3(d["pos"]), Quaternion.LookRotation(fwd, Vector3.up));
                    proj.size = size; proj.pivot = Vector3.zero;
                    proj.startAngleFade = 45; proj.endAngleFade = 70;   // the ground and the sand tops do not take it
                }
                else
                {
                    // on the ground: projected down from 0.25 m above the surface to 0.25 m below; texture V along fwd
                    go.transform.SetPositionAndRotation(V3(d["pos"]) + Vector3.up * (size.z * .5f), Quaternion.LookRotation(Vector3.down, fwd));
                    proj.size = size; proj.pivot = new Vector3(0, 0, size.z * .5f);
                    proj.startAngleFade = 50; proj.endAngleFade = 75;   // ground, decks and the sand itself, not walls or props
                }
                byDecal[kind] = byDecal.TryGetValue(kind, out var c) ? c + 1 : 1;
            }
            record = new Dictionary<string, object> { ["pieces"] = byPiece, ["decals"] = byDecal, ["groups"] = root.transform.Cast<Transform>().Select(t => t.name).ToArray() };
            return root;
        }

        // ------------------------------------------------------------------ install
        [MenuItem("Athen Hill/Wall-foot drifts/Install (one time)")]
        public static string Install() => Install(false);

        /// Authoring iteration only: replaces the installed root (the first rollback copy of the scene is kept).
        public static string Reinstall() => Install(true);

        static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (existing && !replace) throw new Exception("The wall-foot drifts are already installed; edit them in place.");
            if (existing) UnityEngine.Object.DestroyImmediate(existing);
            var layout = Layout();
            Directory.CreateDirectory(Evidence + "rollback");
            if (!replace) File.Copy(ScenePath, Evidence + "rollback/before-wall-foot-drifts.unity", true);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            string fpBefore = chunks ? chunks.sourceFingerprint : null;
            var root = Place(scene, layout, out var record);
            record["retired"] = new string[0];
            AddCameras(scene, layout);
            record["reviewCameras"] = layout["cameras"].Count();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            if (chunks) record["chunkFingerprintUnchanged"] = chunks.sourceFingerprint == fpBefore && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + (replace ? "reinstall.json" : "install.json"), json);
            return json;
        }

        /// Measurement only (A/B frame time): switches the root off or on in the saved scene. Do not use on the shared
        /// scene while other passes build (the orchestrator builds A/B arms from scene snapshots).
        static string Toggle(bool on)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            root.SetActive(on);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return RootName + (on ? " on" : " off");
        }

        // ------------------------------------------------------------------ review cameras
        static void AddCameras(UnityEngine.SceneManagement.Scene scene, JObject layout)
        {
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (!root) { root = new GameObject(CamRootName); UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene); }
            foreach (var c in layout["cameras"])
            {
                var name = (string)c["name"];
                var t = root.transform.Find(name);
                if (!t) { t = new GameObject(name).transform; t.SetParent(root.transform, false); }
                var pos = V3(c["pos"]);
                t.SetPositionAndRotation(pos, Quaternion.LookRotation(V3(c["target"]) - pos, Vector3.up));
                var cam = t.GetComponent<Camera>();                  // Unity objects: no ?? (fake null)
                if (!cam) cam = t.gameObject.AddComponent<Camera>();
                cam.enabled = false; cam.fieldOfView = (float)c["fov"]; cam.nearClipPlane = .05f;
            }
        }

        [MenuItem("Athen Hill/Wall-foot drifts/Add review cameras")]
        public static string ReviewCameras()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            AddCameras(scene, layout);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return "review cameras: " + layout["cameras"].Count();
        }

        /// Editor captures (MainCamera clone, post-processing on) of the review cameras; the scene is never saved. Before
        /// the install the drifts and cameras are placed in memory only. filter: '+'-separated camera-name prefixes (≤ 6 per
        /// run); mode "off" captures the same views with the drifts switched off (before/after pairs).
        public static string CaptureViews(string outDir, string filter, string mode)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (!root) root = Place(scene, layout, out _);
            AddCameras(scene, layout);
            root.SetActive(mode != "off");
            var views = layout["cameras"]
                .Where(c => string.IsNullOrEmpty(filter) || filter.Split('+').Any(f => ((string)c["name"]).StartsWith(f)))
                .Select(c => ((string)c["name"] + (mode == "off" ? "-off" : ""), V3(c["pos"]), V3(c["target"]), (float)c["fov"])).Take(6).ToList();
            return string.Join(",", StreetDressingPass.Capture(outDir, views));
        }

        // ------------------------------------------------------------------ verify
        [MenuItem("Athen Hill/Wall-foot drifts/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            if (root)
            {
                r["active"] = root.activeSelf;
                var groups = root.GetComponentsInChildren<LODGroup>(true);
                r["instances"] = groups.Length;
                r["expectedInstances"] = layout["pieces"].Count();
                r["prefabLinked"] = groups.Count(m => PrefabUtility.IsPartOfPrefabInstance(m.gameObject));
                r["nonUniformScale"] = groups.Where(m => { var s = m.transform.lossyScale; return Mathf.Abs(s.x - s.y) > 1e-4f || Mathf.Abs(s.x - s.z) > 1e-4f; }).Select(m => PathOf(m.transform)).ToArray();
                var rends = root.GetComponentsInChildren<Renderer>(true);
                r["renderers"] = rends.Length;
                r["missingMaterials"] = rends.Count(x => x.sharedMaterials.Length == 0 || x.sharedMaterials.Any(m => !m));
                r["materials"] = rends.SelectMany(x => x.sharedMaterials).Where(m => m).Select(m => m.name + " (" + m.shader.name + ")").Distinct().OrderBy(x => x).ToArray();
                var lodTris = new long[3];
                foreach (var gg in groups)
                {
                    var lods = gg.GetLODs();
                    for (int i = 0; i < Math.Min(3, lods.Length); i++)
                        lodTris[i] += lods[i].renderers.Where(x => x).Sum(x => { var mf = x.GetComponent<MeshFilter>(); return mf ? (long)Tris(mf.sharedMesh) : 0L; });
                }
                r["trianglesAllInstances"] = new { LOD0 = lodTris[0], LOD1 = lodTris[1], LOD2 = lodTris[2] };
                r["shadowCasters"] = rends.Count(x => x.shadowCastingMode != ShadowCastingMode.Off);
                r["colliders"] = root.GetComponentsInChildren<Collider>(true).Length;
                r["lights"] = root.GetComponentsInChildren<Light>(true).Length;
                var decals = root.GetComponentsInChildren<DecalProjector>(true);
                r["decals"] = decals.Length;
                r["expectedDecals"] = layout["decals"].Count();
                r["decalsWithMaterial"] = decals.Count(d => d.material);
                r["decalMaxDrawDistance"] = decals.Length > 0 ? decals.Max(d => d.drawDistance) : 0;
                r["groups"] = root.transform.Cast<Transform>().Select(t => t.name + " (" + t.GetComponentsInChildren<LODGroup>(true).Length + " banks, " + t.GetComponentsInChildren<DecalProjector>(true).Length + " decals)").ToArray();
            }
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            var cams = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            r["reviewCameras"] = cams ? cams.GetComponentsInChildren<Camera>(true).Select(c => c.name + (c.enabled ? " (ENABLED)" : "")).ToArray() : new string[0];
            r["expectedCameras"] = layout["cameras"].Count();
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.WallFootDriftsPass.RunBatch --steps build,install,verify,capture[:filter[:off]] [--out dir]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "verify").Split(',');
            var outDir = Arg("--out", Evidence + "editor");
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "build" => BuildAssets(),
                        "install" => Install(),
                        "reinstall" => Reinstall(),
                        "cameras" => ReviewCameras(),
                        "toggle" => Toggle(parts[1] == "on"),
                        "capture" => CaptureViews(outDir, parts.Length > 1 ? parts[1] : "", parts.Length > 2 ? parts[2] : "on"),
                        "verify" => Verify(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("WallFootDriftsPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
