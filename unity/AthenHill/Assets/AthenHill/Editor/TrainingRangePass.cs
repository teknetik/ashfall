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

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: the Wardens' training range in the Outer Berms. Carl: "the training robot section could use work."
    /// The range beyond the West Gate (three steel knockdown plates in front of a bare mound) and the machines recruits
    /// drill against become a working Warden range: three timber firing bays at the tutorial's firing line, a timber-
    /// revetted earth backstop with impact scars and a red flag, distance posts, a range officer's table and range orders,
    /// a machine lane (tyre run, cover barricades, a tethered training drone, a stripped worker droid in a target frame)
    /// and a robot service apron (drone docks under a shade shelter, repair bench, compressor, welding cart, generator).
    ///
    /// Sources: art/training_range_20261001 (README; layout.py → layout.json; author_range.py and prepare_ph_props.py in
    /// Blender; make_textures.py and prepare_prop_textures.py). Batch: -executeMethod AthenHill.Editor.TrainingRangePass.RunBatch
    /// --steps survey|build|cameras|install|reinstall|verify|capture|toggle:on|toggle:off [--out dir]. Install is one time
    /// (TrainingRangeInstall). Gameplay objects (plates, reset station, briefing board, Wardens, locker, encounters,
    /// landmarks) are never moved; the replaced range clutter stays in the scene, inactive.
    /// </summary>
    public static class TrainingRangePass
    {
        public const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        public const string Root = "Assets/AthenHill/Art/TrainingRange/";
        public const string StructDir = Root + "Structures/";
        public const string PropDir = Root + "Props/";
        public const string TexDir = Root + "Textures/";
        public const string MatDir = Root + "Materials/";
        public const string PrefabDir = "Assets/AthenHill/Prefabs/TrainingRange/";
        public const string WestGateMats = "Assets/AthenHill/Art/WestGate/Materials/";
        public const string Evidence = "../evidence/training-range/20261001/";
        public const string ArtSrc = "../../art/training_range_20261001/";
        public const string RootName = "Warden training range";
        public const string CamRootName = "Training range review cameras";
        const string DecalTemplate = "Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat";

        public static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] V(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };

        // survey window (world metres)
        const float X0 = -98f, X1 = -54f, Z0 = -16f, Z1 = 36f;
        static bool InWindow(Bounds b) => b.max.x >= X0 && b.min.x <= X1 && b.max.z >= Z0 && b.min.z <= Z1;
        static bool InWindow(Vector3 p) => p.x >= X0 && p.x <= X1 && p.z >= Z0 && p.z <= Z1;

        // ------------------------------------------------------------------ survey (read-only)
        /// Ground heights (Berms ground and the highest non-trigger surface), colliders, gameplay markers, lights, cameras and
        /// renderers around the range, written to art/training_range_20261001/survey.json for layout.py. Never saves.
        public static string Survey()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Physics.SyncTransforms();
            var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).ToList();
            var groundT = all.FirstOrDefault(t => PathOf(t) == "Outer Berms/Berms ground");
            var groundCol = groundT ? groundT.GetComponent<MeshCollider>() : null;
            var grid = new List<float[]>();
            const float step = .5f;
            for (float z = Z0; z <= Z1 + 1e-3f; z += step)
                for (float x = X0; x <= X1 + 1e-3f; x += step)
                {
                    float gy = float.NaN, top = float.NaN;
                    if (groundCol && groundCol.Raycast(new Ray(new Vector3(x, 60, z), Vector3.down), out var gh, 200)) gy = gh.point.y;
                    var hits = Physics.RaycastAll(new Vector3(x, 60, z), Vector3.down, 200, ~(1 << 8), QueryTriggerInteraction.Ignore);
                    if (hits.Length > 0) top = hits.Max(q => q.point.y);
                    grid.Add(new[] { x, z, gy, top });
                }
            var colliders = new List<object>();
            foreach (var c in all.SelectMany(t => t.GetComponents<Collider>()))
            {
                if (!c.gameObject.activeInHierarchy || !c.enabled) continue;
                var b = c.bounds; if (!InWindow(b)) continue;
                if (c == groundCol) continue;
                object obb = null;
                if (c is BoxCollider bc)
                {
                    var s = Vector3.Scale(bc.size, c.transform.lossyScale);
                    obb = new { center = V(c.transform.TransformPoint(bc.center)), size = V(new Vector3(Mathf.Abs(s.x), Mathf.Abs(s.y), Mathf.Abs(s.z))), yaw = c.transform.eulerAngles.y, pitch = c.transform.eulerAngles.x, roll = c.transform.eulerAngles.z };
                }
                colliders.Add(new { path = PathOf(c.transform), type = c.GetType().Name, trigger = c.isTrigger, layer = c.gameObject.layer, min = V(b.min), max = V(b.max), obb });
            }
            var markers = new List<object>();
            void Mark(string kind, Transform t, object extra = null) { if (t && InWindow(t.position)) markers.Add(new { kind, path = PathOf(t), pos = V(t.position), yaw = t.eulerAngles.y, active = t.gameObject.activeInHierarchy, extra }); }
            foreach (var n in UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("npc", n.transform);
            foreach (var w in UnityEngine.Object.FindObjectsByType<WorldInteractable>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("interactable", w.transform, new { w.prompt, w.range });
            foreach (var r in UnityEngine.Object.FindObjectsByType<RangeTarget>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("target", r.transform, new { aim = V(r.GetComponent<Health>().AimPoint) });
            foreach (var e in UnityEngine.Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                Mark("encounter", e.transform, new { e.displayName });
                foreach (var s in e.spawns) if (s.point) Mark("spawn", s.point, new { prefab = s.prefab ? s.prefab.name : null, aggro = s.prefab ? s.prefab.aggroRadius : 0, leash = s.prefab ? s.prefab.leashRadius : 0, wander = s.prefab ? s.prefab.wanderRadius : 0 });
            }
            foreach (var w in UnityEngine.Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (w.waypoints != null) foreach (var p in w.waypoints) Mark("route", p, new { walker = w.name });
            var landmarks = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Landmarks");
            if (landmarks) foreach (Transform t in landmarks.transform) Mark("landmark", t);
            foreach (var t in all.Where(t => t.name.Contains("Respawn") || t.name.Contains("fabricator") || t.name.Contains("Fabricator"))) Mark("misc", t);
            var lights = all.Select(t => t.GetComponent<Light>()).Where(l => l && InWindow(l.transform.position))
                .Select(l => new { path = PathOf(l.transform), pos = V(l.transform.position), type = l.type.ToString(), l.range, l.intensity, shadows = l.shadows.ToString(), active = l.gameObject.activeInHierarchy }).ToArray();
            var cams = all.Select(t => t.GetComponent<Camera>()).Where(c => c && InWindow(c.transform.position))
                .Select(c => new { name = c.name, path = PathOf(c.transform), pos = V(c.transform.position), fwd = V(c.transform.forward), c.fieldOfView }).ToArray();
            var renderers = new List<object>();
            foreach (var r in all.Select(t => t.GetComponent<Renderer>()).Where(r => r && InWindow(r.bounds)))
            {
                var mesh = r is SkinnedMeshRenderer s ? s.sharedMesh : r.TryGetComponent<MeshFilter>(out var mf) ? mf.sharedMesh : null;
                long tris = 0; if (mesh) for (int k = 0; k < mesh.subMeshCount; k++) tris += (long)mesh.GetIndexCount(k) / 3;
                renderers.Add(new { path = PathOf(r.transform), active = r.gameObject.activeInHierarchy, r.enabled, tris, min = V(r.bounds.min), max = V(r.bounds.max), mats = r.sharedMaterials.Select(m => m ? m.name : null).ToArray() });
            }
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var tutorial = UnityEngine.Object.FindAnyObjectByType<BermsTutorial>();
            var result = new
            {
                scene = ScenePath, window = new[] { X0, X1, Z0, Z1 }, gridStep = step, grid,
                colliders, markers, lights, cameras = cams, renderers,
                chunkSourceRoots = chunks ? chunks.sourceRoots.Where(t => t).Select(PathOf).ToArray() : null,
                circuit = circuit ? new { practical = circuit.practicalLights.Length, nightOnly = circuit.nightOnlyLights.Length, circuit.fullLightDistance, circuit.culledLightDistance, circuit.shadowDistance } : null,
                tutorial = tutorial ? new { targets = tutorial.targets.Select(t => t ? PathOf(t.transform) : null).ToArray(), firstContact = tutorial.firstContact ? PathOf(tutorial.firstContact.transform) : null, depot = tutorial.depot ? PathOf(tutorial.depot.transform) : null } : null,
                roots = scene.GetRootGameObjects().Select(g => g.name).ToArray(),
            };
            Directory.CreateDirectory(ArtSrc);
            File.WriteAllText(ArtSrc + "survey.json", JsonConvert.SerializeObject(result));
            return $"survey: {grid.Count} ground samples, {colliders.Count} colliders, {markers.Count} markers, {renderers.Count} renderers";
        }

        // ------------------------------------------------------------------ build: textures, materials, prefabs
        [MenuItem("Athen Hill/Outer Berms/Training range: build assets")]
        public static string BuildAssets()
        {
            AssetDatabase.Refresh();
            foreach (var glb in Directory.GetFiles(StructDir, "*.glb").Concat(Directory.GetFiles(PropDir, "*.glb", SearchOption.AllDirectories)))
                AssetDatabase.ImportAsset(glb.Replace('\\', '/'), ImportAssetOptions.ForceUpdate);
            ConfigureTextures();
            var mats = BuildMaterials();
            Directory.CreateDirectory(PrefabDir);
            var missing = new HashSet<string>();
            var built = new List<object>();
            foreach (var glb in Directory.GetFiles(StructDir, "*.glb").OrderBy(x => x)) built.Add(StructurePrefab(glb.Replace('\\', '/'), mats, missing));
            var props = JObject.Parse(File.ReadAllText(PropDir + "tr-props.json"));
            foreach (var p in props.Properties()) built.Add(PropPrefab(p.Name, (JObject)p.Value, mats, missing));
            built.Add(TrainingDronePrefab());
            built.Add(WorkerShellPrefab());
            AssetDatabase.SaveAssets();
            var report = new { prefabs = built, materials = mats.Count, unmapped = missing.OrderBy(x => x).ToArray() };
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(report, Formatting.Indented);
            File.WriteAllText(Evidence + "build-assets.json", json);
            return $"{built.Count} prefabs, {mats.Count} materials, unmapped: {string.Join(", ", missing)}";
        }

        static void ConfigureTextures()
        {
            foreach (var g in AssetDatabase.FindAssets("t:Texture", new[] { TexDir.TrimEnd('/'), PropDir.TrimEnd('/') }))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                var file = Path.GetFileNameWithoutExtension(path);
                bool normal = file.EndsWith("_Normal"), mask = file.EndsWith("_Mask"), decal = file.StartsWith("TR_Decal");
                bool alphaBase = file.EndsWith("_BaseMap") && path.EndsWith(".png");
                bool small = path.Contains("/Props/") && new FileInfo(path).Length < 1_200_000 && !file.StartsWith("old_military") && !file.StartsWith("portable_welding");
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !normal && !mask;
                ti.alphaSource = mask || decal || alphaBase ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                ti.alphaIsTransparency = decal || alphaBase;
                ti.mipMapsPreserveCoverage = alphaBase;
                if (alphaBase) ti.alphaTestReferenceValue = .4f;
                ti.wrapMode = decal ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
                ti.maxTextureSize = decal ? 1024 : small ? 1024 : 2048;
                ti.mipmapEnabled = true; ti.streamingMipmaps = true; ti.anisoLevel = 8;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
            }
        }

        static Material Mat(string name, Shader shader)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
            else if (m.shader != shader) m.shader = shader;
            return m;
        }

        static Texture2D T(JToken s) => s == null || s.Type == JTokenType.Null ? null : AssetDatabase.LoadAssetAtPath<Texture2D>((string)s);
        static Color C(JToken a, float alpha = 1) => new Color((float)a[0], (float)a[1], (float)a[2], alpha);

        public static Dictionary<string, Material> BuildMaterials()
        {
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var mats = new Dictionary<string, Material>();
            foreach (var p in JObject.Parse(File.ReadAllText(TexDir + "materials.json")).Properties())
            {
                var s = (JObject)p.Value; var m = Mat(p.Name, lit); mats[p.Name] = m;
                m.SetColor("_BaseColor", s["color"] != null ? C(s["color"], s["alpha"] != null ? (float)s["alpha"] : 1) : Color.white);
                var bm = T(s["base"]); m.SetTexture("_BaseMap", bm);
                var nm = T(s["normal"]); m.SetTexture("_BumpMap", nm); m.SetFloat("_BumpScale", 1);
                if (nm) m.EnableKeyword("_NORMALMAP"); else m.DisableKeyword("_NORMALMAP");
                var mk = T(s["mask"]);
                m.SetFloat("_Smoothness", s["smoothness"] != null ? (float)s["smoothness"] : .5f);
                if (mk)
                {
                    m.SetTexture("_MetallicGlossMap", mk); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                    m.SetTexture("_OcclusionMap", mk); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1);
                }
                else
                {
                    m.SetTexture("_MetallicGlossMap", null); m.DisableKeyword("_METALLICSPECGLOSSMAP");
                    m.SetTexture("_OcclusionMap", null); m.DisableKeyword("_OCCLUSIONMAP");
                    m.SetFloat("_Metallic", s["metallic"] != null ? (float)s["metallic"] : 0);
                }
                m.SetFloat("_SmoothnessTextureChannel", 0);
                float tile = s["tile"] != null ? (float)s["tile"] : 0;
                m.SetTextureScale("_BaseMap", tile > 0 ? Vector2.one / tile : Vector2.one);
                bool two = s["twoSided"] != null && (bool)s["twoSided"];
                if (s["alphaClip"] != null && (bool)s["alphaClip"])
                {
                    m.SetFloat("_AlphaClip", 1); m.SetFloat("_Cutoff", s["cutoff"] != null ? (float)s["cutoff"] : .45f); m.EnableKeyword("_ALPHATEST_ON");
                    m.SetOverrideTag("RenderType", "TransparentCutout"); m.renderQueue = (int)RenderQueue.AlphaTest;
                }
                else { m.SetFloat("_AlphaClip", 0); m.DisableKeyword("_ALPHATEST_ON"); m.SetOverrideTag("RenderType", ""); m.renderQueue = -1; }
                if (s["transparent"] != null && (bool)s["transparent"])
                {
                    m.SetFloat("_Surface", 1); m.SetFloat("_Blend", 0); m.SetFloat("_ZWrite", 0);
                    m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                    m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.SetOverrideTag("RenderType", "Transparent"); m.renderQueue = (int)RenderQueue.Transparent;
                }
                if (s["emission"] != null)
                {
                    var e = C(s["emission"]) * (s["emissionIntensity"] != null ? (float)s["emissionIntensity"] : 1);
                    m.SetColor("_EmissionColor", e); m.EnableKeyword("_EMISSION"); m.SetTexture("_EmissionMap", T(s["emissionMap"]));
                    m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
                }
                else { m.DisableKeyword("_EMISSION"); m.SetColor("_EmissionColor", Color.black); }
                m.SetFloat("_Cull", two ? 0 : 2); m.doubleSidedGI = two;
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
            }
            // decals: copies of the accepted weathering decal material with this pass's maps
            var template = AssetDatabase.LoadAssetAtPath<Material>(DecalTemplate);
            if (!template || !template.HasProperty("Base_Map")) throw new Exception("Decal template material missing: " + DecalTemplate);
            foreach (var f in Directory.GetFiles(TexDir, "TR_Decal*.png"))
            {
                var name = Path.GetFileNameWithoutExtension(f);
                var path = MatDir + name + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!m) { m = new Material(template) { name = name }; AssetDatabase.CreateAsset(m, path); }
                m.SetTexture("Base_Map", AssetDatabase.LoadAssetAtPath<Texture2D>(f.Replace('\\', '/')));
                if (m.HasProperty("Normal_Blend")) m.SetFloat("Normal_Blend", 0);
                EditorUtility.SetDirty(m);
                mats[name] = m;
            }
            // the West Gate kit's materials (olive paint, rust steel, plywood, hessian, hazard, concrete, lamp lenses...)
            foreach (var f in Directory.GetFiles(WestGateMats, "WG_*.mat"))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(f.Replace('\\', '/'));
                if (m) mats[m.name] = m;
            }
            AssetDatabase.SaveAssets();
            return mats;
        }

        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m) && m) return m;
            var trimmed = System.Text.RegularExpressions.Regex.Replace(name, @"\.\d+$", "");
            return mats.TryGetValue(trimmed, out m) ? m : null;
        }

        static void StaticFlags(GameObject root)
        {
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
        }

        static long Tris(Mesh m) { long n = 0; if (m) for (int i = 0; i < m.subMeshCount; i++) n += m.GetIndexCount(i) / 3; return n; }

        /// Blender-authored structure: LOD0 (+LOD1) renderers, COL_ proxies → box colliders (the revetment's strip →
        /// mesh collider), LIGHT_ empties kept as light anchors; small parts cast no shadow.
        static object StructurePrefab(string glb, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var name = Path.GetFileNameWithoutExtension(glb);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb);
            if (!model) throw new Exception("not imported " + glb);
            var root = new GameObject(name);
            try
            {
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(model); inst.transform.SetParent(root.transform, false); inst.name = name + " model";
                var lod = new SortedDictionary<int, List<Renderer>>();
                foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                {
                    var mf = r.GetComponent<MeshFilter>();
                    if (r.name.StartsWith("COL_"))
                    {
                        r.enabled = false;
                        r.sharedMaterials = r.sharedMaterials.Select(_ => Lookup(mats, "WG_Collider")).ToArray();
                        if (!mf || !mf.sharedMesh) continue;
                        if (r.name.StartsWith("COL_Revetment")) { var mc = r.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; }
                        else { var b = r.gameObject.AddComponent<BoxCollider>(); b.center = mf.sharedMesh.bounds.center; b.size = mf.sharedMesh.bounds.size; }
                        continue;
                    }
                    var slots = r.sharedMaterials;
                    for (int i = 0; i < slots.Length; i++) { var m = slots[i] ? Lookup(mats, slots[i].name) : null; if (m) slots[i] = m; else missing.Add(name + ":" + (slots[i] ? slots[i].name : "null")); }
                    r.sharedMaterials = slots;
                    var mt = System.Text.RegularExpressions.Regex.Match(r.name, @"_LOD(\d)(\.\d+)?$");
                    int k = mt.Success ? int.Parse(mt.Groups[1].Value) : 0;
                    if (!lod.ContainsKey(k)) lod[k] = new List<Renderer>(); lod[k].Add(r);
                    var size = r.bounds.size.magnitude;
                    // painted numbers/signs and small parts: no shadow; LOD1 of mid-size pieces: no shadow either
                    bool cast = size >= .45f && (k == 0 || size > 4f);
                    r.shadowCastingMode = cast ? ShadowCastingMode.On : ShadowCastingMode.Off;
                    if (r is MeshRenderer mr) { mr.receiveGI = ReceiveGI.LightProbes; mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; }
                }
                long lod0 = lod.TryGetValue(0, out var l0) ? l0.Sum(r => Tris(r.GetComponent<MeshFilter>()?.sharedMesh)) : 0;
                float big = lod.Count > 0 ? lod[0].Select(r => r.bounds.size.magnitude).Max() : 1;
                if (lod.Count > 1)
                {
                    var group = root.AddComponent<LODGroup>();
                    float[] cut = big > 8 ? new[] { .45f, .04f } : big > 3 ? new[] { .30f, .03f } : big > 1 ? new[] { .25f, .04f } : new[] { .14f, .03f };
                    var levels = lod.Values.Select((rs, i) => new LOD(cut[Math.Min(i, cut.Length - 1)], rs.ToArray())).ToArray();
                    group.SetLODs(levels); group.RecalculateBounds(); group.fadeMode = LODFadeMode.None;
                }
                else if (lod.Count == 1 && big < 2.5f)
                {
                    // single-level small pieces still cull with distance
                    var group = root.AddComponent<LODGroup>();
                    group.SetLODs(new[] { new LOD(big < .8f ? .03f : .015f, lod[0].ToArray()) }); group.RecalculateBounds(); group.fadeMode = LODFadeMode.None;
                }
                StaticFlags(root);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + name + ".prefab");
                return new { name, lods = lod.Count, lod0Triangles = lod0, colliders = root.GetComponentsInChildren<Collider>(true).Length,
                             lights = root.GetComponentsInChildren<Transform>(true).Count(t => t.name.StartsWith("LIGHT_")) };
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        /// Poly Haven prop: three LOD files (street-dressing pattern), box collider for the large ones.
        static object PropPrefab(string id, JObject spec, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var size = spec["size"].Select(x => (float)x).ToArray(); float max = size.Max();
            var root = new GameObject("TRP_" + id);
            try
            {
                var lods = new List<LOD>();
                float[] cuts = max < .5f ? new[] { .2f, .06f, .02f } : max < 1.2f ? new[] { .3f, .08f, .02f } : new[] { .4f, .1f, .015f };
                long lod0 = 0;
                for (int i = 0; i < 3; i++)
                {
                    var glb = $"{PropDir}{id}/{id}_LOD{i}.glb";
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb);
                    if (!model) throw new Exception("not imported " + glb);
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(model); inst.transform.SetParent(root.transform, false); inst.name = "LOD" + i;
                    var rs = inst.GetComponentsInChildren<Renderer>(true);
                    foreach (var r in rs)
                    {
                        var slots = r.sharedMaterials;
                        for (int k = 0; k < slots.Length; k++) { var m = slots[k] ? Lookup(mats, slots[k].name) : null; if (m) slots[k] = m; else missing.Add(id + ":" + (slots[k] ? slots[k].name : "null")); }
                        r.sharedMaterials = slots;
                        r.shadowCastingMode = (i == 0 && max > .3f) || (i == 1 && max > 1.2f) ? ShadowCastingMode.On : ShadowCastingMode.Off;
                        if (i == 0) lod0 += Tris(r.GetComponent<MeshFilter>()?.sharedMesh);
                    }
                    lods.Add(new LOD(cuts[i], rs));
                }
                var g = root.AddComponent<LODGroup>(); g.SetLODs(lods.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                if (max >= .5f && size[1] >= .3f)
                {
                    var b = root.AddComponent<BoxCollider>(); b.center = new Vector3(0, size[1] / 2, 0); b.size = new Vector3(size[0] * .92f, size[1], size[2] * .92f);
                }
                StaticFlags(root);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + "TRP_" + id + ".prefab");
                return new { name = "TRP_" + id, lods = 3, lod0Triangles = lod0, size };
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        /// A Warden training drone: the accepted yellow hover drone's visual meshes (split body, rotors, lens) without its
        /// AI, health, audio or effects, as a static prop (docked on a charge plate, or hung from the tether gantry).
        /// Origin at the bottom centre of the body.
        static object TrainingDronePrefab()
        {
            const string src = "Assets/AthenHill/Prefabs/OuterBerms/FeralScrapDrone.prefab";
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(src));
            var root = new GameObject("TR_TrainingDrone");
            try
            {
                var parts = new List<(Mesh mesh, Material[] mats, Matrix4x4 m)>();
                foreach (var r in inst.GetComponentsInChildren<MeshRenderer>(false))
                {
                    if (!r.enabled) continue;
                    var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh || mf.sharedMesh.name.Contains("RotorDisc")) continue;
                    parts.Add((mf.sharedMesh, r.sharedMaterials, inst.transform.worldToLocalMatrix * r.transform.localToWorldMatrix));
                }
                var b = new Bounds(); bool first = true;
                foreach (var p in parts) foreach (var c in Corners(p.mesh.bounds)) { var w = p.m.MultiplyPoint3x4(c); if (first) { b = new Bounds(w, Vector3.zero); first = false; } else b.Encapsulate(w); }
                var offset = new Vector3(-b.center.x, -b.min.y, -b.center.z);
                long tris = 0;
                foreach (var p in parts)
                {
                    var go = new GameObject(p.mesh.name, typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(root.transform, false);
                    go.transform.localPosition = p.m.GetPosition() + offset; go.transform.localRotation = p.m.rotation; go.transform.localScale = p.m.lossyScale;
                    go.GetComponent<MeshFilter>().sharedMesh = p.mesh; var mr = go.GetComponent<MeshRenderer>(); mr.sharedMaterials = p.mats;
                    mr.shadowCastingMode = p.mesh.bounds.size.magnitude * p.m.lossyScale.x > .3f ? ShadowCastingMode.On : ShadowCastingMode.Off;
                    tris += Tris(p.mesh);
                }
                var lg = root.AddComponent<LODGroup>(); lg.SetLODs(new[] { new LOD(.02f, root.GetComponentsInChildren<Renderer>()) }); lg.RecalculateBounds(); lg.fadeMode = LODFadeMode.None;
                StaticFlags(root);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + "TR_TrainingDrone.prefab");
                return new { name = "TR_TrainingDrone", parts = parts.Count, lod0Triangles = tris, size = V(b.size) };
            }
            finally { UnityEngine.Object.DestroyImmediate(root); UnityEngine.Object.DestroyImmediate(inst); }
        }

        static IEnumerable<Vector3> Corners(Bounds b)
        {
            for (int i = 0; i < 8; i++) yield return new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z);
        }

        /// A stripped worker droid used as a target: the accepted worker droid's rig baked in its combat-idle stance to a
        /// static mesh, in a dust-dulled variant of its material with dead optics. Origin between the feet.
        static object WorkerShellPrefab()
        {
            const string worker = "Assets/AthenHill/Art/OuterBerms/WorkerDroid.glb";
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(worker);
            var clips = AssetDatabase.LoadAllAssetsAtPath(worker).OfType<AnimationClip>().ToDictionary(c => c.name);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            try
            {
                var anim = inst.GetComponentInChildren<Animation>();
                AnimationMode.StartAnimationMode();
                AnimationMode.BeginSampling(); AnimationMode.SampleAnimationClip(anim ? anim.gameObject : inst, clips["idle"], 0); AnimationMode.EndSampling();
                var smr = inst.GetComponentInChildren<SkinnedMeshRenderer>();
                var baked = new Mesh { name = "TR_WorkerDroidShell" }; smr.BakeMesh(baked, true);
                var toRoot = inst.transform.worldToLocalMatrix * smr.transform.localToWorldMatrix;
                var v = baked.vertices; var nn = baked.normals;
                for (int i = 0; i < v.Length; i++) { v[i] = toRoot.MultiplyPoint3x4(v[i]); nn[i] = toRoot.MultiplyVector(nn[i]).normalized; }
                AnimationMode.StopAnimationMode();
                float minY = v.Min(p => p.y); float cx = (v.Min(p => p.x) + v.Max(p => p.x)) / 2, cz = (v.Min(p => p.z) + v.Max(p => p.z)) / 2;
                for (int i = 0; i < v.Length; i++) { v[i].y -= minY; v[i].x -= cx; v[i].z -= cz; }
                baked.vertices = v; baked.normals = nn; baked.RecalculateBounds(); baked.RecalculateTangents();
                var meshPath = StructDir + "TR_WorkerDroidShell.asset";
                if (AssetDatabase.LoadAssetAtPath<Mesh>(meshPath)) AssetDatabase.DeleteAsset(meshPath);
                AssetDatabase.CreateAsset(baked, meshPath);
                var src = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/OuterBerms/Materials/RB_WorkerDroid.mat");
                var shell = Mat("TR_WorkerShellPaint", src ? src.shader : Shader.Find("Universal Render Pipeline/Lit"));
                if (src) shell.CopyPropertiesFromMaterial(src);
                if (shell.HasProperty("_BaseColor")) shell.SetColor("_BaseColor", shell.GetColor("_BaseColor") * new Color(.86f, .82f, .76f, 1));
                shell.DisableKeyword("_EMISSION"); if (shell.HasProperty("_EmissionColor")) shell.SetColor("_EmissionColor", Color.black);
                shell.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack;
                EditorUtility.SetDirty(shell);
                var root = new GameObject("TR_WorkerDroidShell");
                try
                {
                    var go = new GameObject("TR_WorkerDroidShell mesh", typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(root.transform, false);
                    go.GetComponent<MeshFilter>().sharedMesh = baked; go.GetComponent<MeshRenderer>().sharedMaterial = shell;
                    var b = baked.bounds; var col = root.AddComponent<BoxCollider>(); col.center = b.center; col.size = Vector3.Scale(b.size, new Vector3(.7f, 1, .7f));
                    var lg = root.AddComponent<LODGroup>(); lg.SetLODs(new[] { new LOD(.02f, new Renderer[] { go.GetComponent<MeshRenderer>() }) }); lg.RecalculateBounds(); lg.fadeMode = LODFadeMode.None;
                    StaticFlags(root);
                    PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + "TR_WorkerDroidShell.prefab");
                    return new { name = "TR_WorkerDroidShell", lod0Triangles = Tris(baked), size = V(b.size) };
                }
                finally { UnityEngine.Object.DestroyImmediate(root); }
            }
            finally { if (AnimationMode.InAnimationMode()) AnimationMode.StopAnimationMode(); UnityEngine.Object.DestroyImmediate(inst); }
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.TrainingRangePass.RunBatch --steps build,install,verify,capture [--out dir]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "survey").Split(',');
            var outDir = Arg("--out", Evidence + "editor-review");
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "survey" => Survey(),
                        "build" => BuildAssets(),
                        "cameras" => TrainingRangeInstall.CamerasOnly(),
                        "install" => TrainingRangeInstall.Install(false),
                        "reinstall" => TrainingRangeInstall.Install(true),
                        "verify" => TrainingRangeInstall.Verify(),
                        "capture" => TrainingRangeInstall.CaptureViews(parts.Length > 1 ? Path.Combine(outDir, parts[1]) : outDir, parts.Length > 2 ? parts[2] : null),
                        "toggle" => Toggle(parts[1] == "on"),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("TrainingRangePass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        /// Measurement only (A/B frame time): switches the whole range root off or on in the saved scene (the retired
        /// clutter stays retired, so "off" is the range without this pass's objects, not the 30 Sep scene).
        static string Toggle(bool on)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = GameObject.Find("Outer Berms").transform.Find(RootName);
            if (!root) throw new Exception("not installed");
            root.gameObject.SetActive(on);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return RootName + (on ? " on" : " off");
        }
    }
}
