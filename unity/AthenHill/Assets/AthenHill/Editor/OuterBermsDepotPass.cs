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
    /// 27 September 2026: the machine depot at the far (south) end of the Outer Berms, rebuilt from five concrete
    /// boxes into a ruined processing hall / drone nest (sources: art/outer_berms_depot_20260927).
    ///
    /// Menu: Athen Hill → Outer Berms → Depot: sculpt ground (one-time; lifts the walkable ground above the desert
    /// basin mesh that poked through it), Depot: build assets (textures, URP materials, prefabs; existing materials
    /// are kept so Inspector edits survive) and Depot: install (refuses when the depot root exists). Gameplay objects
    /// (Machine depot nest encounter and its spawn points) keep their components and references; replaced visuals
    /// stay in the scene, inactive, under "Machine depot".
    /// </summary>
    public static class OuterBermsDepotPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Evidence = "../evidence/outer-berms-depot/20260927/";
        const string ArtDir = "../../art/outer_berms_depot_20260927/";
        // region whose ground may be lifted above the basin (depot and the south end of the road)
        const float RX0 = -101, RX1 = -62, RZ0 = -54, RZ1 = -18;

        // ------------------------------------------------------------------ ground
        [MenuItem("Athen Hill/Outer Berms/Depot: sculpt ground")]
        public static string SculptGround()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) throw new Exception("Open the saved Athen Hill scene first");
            var ground = GameObject.Find("Outer Berms/Berms ground").GetComponent<MeshCollider>();
            var mesh = ground.GetComponent<MeshFilter>().sharedMesh;
            Directory.CreateDirectory(Evidence);
            var backup = Evidence + "BermsGround-before-depot.asset";
            if (!File.Exists(backup)) File.Copy(AssetDatabase.GetAssetPath(mesh), backup);
            // Sculpt always starts from the pre-depot heights, so re-running with an edited layout is idempotent.
            const string SourcePath = "Assets/AthenHill/Art/OuterBerms/BermsGround-before-depot.asset";
            var source = AssetDatabase.LoadAssetAtPath<Mesh>(SourcePath);
            if (!source) { source = UnityEngine.Object.Instantiate(mesh); source.name = "Berms ground (before depot)"; AssetDatabase.CreateAsset(source, SourcePath); }
            var design = LoadDesign();
            var probes = BasinProbes();
            try
            {
                var v = source.vertices; int lifted = 0; float maxLift = 0;
                for (int i = 0; i < v.Length; i++)
                {
                    var w = ground.transform.TransformPoint(v[i]);
                    if (w.x < RX0 || w.x > RX1 || w.z < RZ0 || w.z > RZ1) continue;
                    float target = w.y;
                    if (BasinY(w.x, w.z, out float by)) target = Mathf.Max(target, by + .06f);
                    target += Drift(design, w.x, w.z);
                    if (target > w.y + 1e-4f) { maxLift = Mathf.Max(maxLift, target - w.y); w.y = target; v[i] = ground.transform.InverseTransformPoint(w); lifted++; }
                }
                mesh.vertices = v; mesh.RecalculateNormals(); mesh.RecalculateBounds(); EditorUtility.SetDirty(mesh);
                ground.sharedMesh = null; ground.sharedMesh = mesh;
                AssetDatabase.SaveAssets();
                Physics.SyncTransforms();
                var grid = ExportGrid(ground);
                EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
                return $"lifted {lifted} vertices, max {maxLift:F2} m; grid {grid}";
            }
            finally { foreach (var p in probes) UnityEngine.Object.DestroyImmediate(p); }
        }

        static JObject LoadDesign()
        {
            var p = ArtDir + "layout.json";
            return File.Exists(p) ? JObject.Parse(File.ReadAllText(p)) : new JObject();
        }

        /// Designed sand drifts (layout.json "drifts": x, z, rx, rz, h, yaw) added on top of the basin-safe height.
        static float Drift(JObject design, float x, float z)
        {
            if (design["drifts"] is not JArray drifts) return 0;
            float h = 0;
            foreach (JObject d in drifts)
            {
                float yaw = (float)d["yaw"] * Mathf.Deg2Rad, dx = x - (float)d["x"], dz = z - (float)d["z"];
                float u = (dx * Mathf.Cos(yaw) - dz * Mathf.Sin(yaw)) / (float)d["rx"], w = (dx * Mathf.Sin(yaw) + dz * Mathf.Cos(yaw)) / (float)d["rz"];
                float q = u * u + w * w; if (q >= 1) continue;
                h = Mathf.Max(h, (float)d["h"] * Mathf.Pow(Mathf.Cos(Mathf.Sqrt(q) * Mathf.PI / 2), 2));
            }
            return h;
        }

        static readonly List<GameObject> probeList = new();
        static List<GameObject> BasinProbes()
        {
            probeList.Clear();
            var basin = GameObject.Find("Desert Landscape");
            foreach (var r in basin.GetComponentsInChildren<MeshRenderer>())
            {
                var f = r.GetComponent<MeshFilter>(); var probe = new GameObject("depot basin probe") { layer = 31, hideFlags = HideFlags.DontSave };
                probe.transform.SetPositionAndRotation(r.transform.position, r.transform.rotation); probe.transform.localScale = r.transform.lossyScale;
                probe.AddComponent<MeshCollider>().sharedMesh = f.sharedMesh; probeList.Add(probe);
            }
            Physics.SyncTransforms();
            return probeList;
        }
        static bool BasinY(float x, float z, out float y)
        {
            y = 0;
            if (!Physics.Raycast(new Vector3(x, 150, z), Vector3.down, out var hit, 400, 1 << 31)) return false;
            y = hit.point.y; return true;
        }

        /// 0.5 m height grid of the walkable ground over the south half (Blender authoring and the splat use it).
        static string ExportGrid(MeshCollider ground)
        {
            var rows = new List<float[]>();
            for (float z = -54; z <= -14.01f; z += .5f)
                for (float x = -104; x <= -60.01f; x += .5f)
                    if (ground.Raycast(new Ray(new Vector3(x, 80, z), Vector3.down), out var h, 200)) rows.Add(new[] { x, (float)Math.Round(h.point.y, 3), z });
            var path = ArtDir + "depot-ground-grid.json";
            File.WriteAllText(path, JsonConvert.SerializeObject(rows));
            return path + " (" + rows.Count + " samples)";
        }
    
        // ------------------------------------------------------------------ assets
        const string Root = "Assets/AthenHill/Art/OuterBermsDepot/";
        const string MatDir = Root + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/OuterBermsDepot/";
        const string WgMatDir = "Assets/AthenHill/Art/WestGate/Materials/";
        const string WgPrefabDir = "Assets/AthenHill/Prefabs/WestGate/";
        const string DepotName = "Depot rebuild";

        // metres per texture repeat for the tiling DP materials (Blender UVs are in metres)
        static readonly Dictionary<string, float> Tile = new()
        {
            ["DP_FramePaint"] = 1.6f, ["DP_RoofSheet"] = 2.2f, ["DP_WallSheet"] = 2.4f, ["DP_Concrete"] = 3.2f, ["DP_ApronConcrete"] = 4.5f, ["DP_Belt"] = 1.4f,
        };

        [MenuItem("Athen Hill/Outer Berms/Depot: build assets")]
        public static string BuildAssets()
        {
            AssetDatabase.Refresh();
            ConfigureTextures();
            var mats = BuildMaterials();
            var made = BuildPrefabs(mats);
            BuildCarcassPrefabs(mats);
            AssetDatabase.SaveAssets();
            return "materials " + mats.Count + ", prefabs " + made;
        }

        static void ConfigureTextures()
        {
            var guids = AssetDatabase.FindAssets("t:Texture", new[] { Root.TrimEnd('/') });
            try
            {
                AssetDatabase.StartAssetEditing();
                foreach (var g in guids)
                {
                    var path = AssetDatabase.GUIDToAssetPath(g);
                    if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                    var file = Path.GetFileNameWithoutExtension(path);
                    bool normal = file.EndsWith("_Normal"), mask = file.EndsWith("_Mask"), decal = file.StartsWith("DP_Decal");
                    bool changed = false;
                    void Set<T>(T current, T value, Action<T> apply) { if (!EqualityComparer<T>.Default.Equals(current, value)) { apply(value); changed = true; } }
                    Set(ti.textureType, normal ? TextureImporterType.NormalMap : TextureImporterType.Default, v => ti.textureType = v);
                    Set(ti.sRGBTexture, !normal && !mask, v => ti.sRGBTexture = v);
                    bool big = path.Contains("/Textures/DP_") || path.Contains("/Meshy/");
                    Set(ti.maxTextureSize, big ? 2048 : 1024, v => ti.maxTextureSize = v);
                    Set(ti.alphaIsTransparency, (file.EndsWith("_BaseMap") || decal) && path.EndsWith(".png"), v => ti.alphaIsTransparency = v);
                    if (decal) Set(ti.wrapMode, TextureWrapMode.Clamp, v => ti.wrapMode = v);
                    Set(ti.anisoLevel, 8, v => ti.anisoLevel = v);
                    Set(ti.mipmapEnabled, true, v => ti.mipmapEnabled = v);
                    Set(ti.streamingMipmaps, true, v => ti.streamingMipmaps = v);
                    Set(ti.textureCompression, TextureImporterCompression.CompressedHQ, v => ti.textureCompression = v);
                    if (changed) ti.SaveAndReimport();
                }
            }
            finally { AssetDatabase.StopAssetEditing(); }
            AssetDatabase.Refresh();
        }

        static Material NewOrLoad(string name, out bool created)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            created = !m;
            if (created) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name }; AssetDatabase.CreateAsset(m, path); }
            return m;
        }
        static Texture2D Tex(string path) => AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        static Texture2D TexAny(string stem) => Tex(stem + ".jpg") ?? Tex(stem + ".png");

        static void SetupLit(Material m, Texture2D baseMap, Texture2D normal, Texture2D mask, Color color, float smoothness, float metallic, float tile, bool clip = false, bool twoSided = false)
        {
            m.SetTexture("_BaseMap", baseMap); m.SetColor("_BaseColor", color);
            m.SetTextureScale("_BaseMap", Vector2.one * tile);
            if (normal) { m.SetTexture("_BumpMap", normal); m.EnableKeyword("_NORMALMAP"); m.SetFloat("_BumpScale", 1); }
            if (mask)
            {
                m.SetTexture("_MetallicGlossMap", mask); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetTexture("_OcclusionMap", mask); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1);
                m.SetFloat("_Smoothness", smoothness);
            }
            else { m.SetFloat("_Smoothness", smoothness); m.SetFloat("_Metallic", metallic); }
            if (clip) { m.SetFloat("_AlphaClip", 1); m.SetFloat("_Cutoff", .45f); m.EnableKeyword("_ALPHATEST_ON"); m.renderQueue = (int)RenderQueue.AlphaTest; }
            if (twoSided) { m.SetFloat("_Cull", 0); m.doubleSidedGI = true; }
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
        }
        static void SetupEmissive(Material m, Color color, float intensity)
        {
            m.SetColor("_BaseColor", color * .25f); m.SetFloat("_Smoothness", .85f); m.SetFloat("_Metallic", 0);
            m.SetColor("_EmissionColor", color * intensity); m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive; m.enableInstancing = true;
            EditorUtility.SetDirty(m);
        }

        public static Dictionary<string, Material> BuildMaterials()
        {
            var mats = new Dictionary<string, Material>();
            // West Gate materials are reused by name (WG_*)
            foreach (var path in Directory.GetFiles(WgMatDir, "WG_*.mat"))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(path.Replace('\\', '/'));
                if (m) mats[Path.GetFileNameWithoutExtension(path)] = m;
            }
            foreach (var bm in Directory.GetFiles(Root + "Textures", "DP_*_BaseMap.*").Where(f => !f.EndsWith(".meta")))
            {
                var name = Path.GetFileName(bm); name = name.Substring(0, name.IndexOf("_BaseMap", StringComparison.Ordinal));
                var m = NewOrLoad(name, out bool created); mats[name] = m;
                if (!created) continue;
                float tile = Tile.TryGetValue(name, out var t) ? 1f / t : 1f;
                SetupLit(m, Tex(bm.Replace('\\', '/')), Tex(Root + "Textures/" + name + "_Normal.jpg"), Tex(Root + "Textures/" + name + "_Mask.png"), Color.white, 1f, 0, tile);
            }
            void Simple(string name, Action<Material> setup) { var m = NewOrLoad(name, out bool created); mats[name] = m; if (created) setup(m); }
            Simple("DP_CyanCell", m => SetupEmissive(m, new Color(.28f, .86f, .95f), 5.5f));
            // Poly Haven props converted for the depot
            var recs = JObject.Parse(File.ReadAllText(Root + "Props/Textures/materials.json"));
            foreach (var p in recs.Properties())
            {
                var m = NewOrLoad(p.Name, out bool created); mats[p.Name] = m;
                if (!created) continue;
                var r = (JObject)p.Value; string T(string k) => r[k] != null ? Root + "Props/Textures/" + (string)r[k] : null;
                var f = r["baseColorFactor"].ToObject<float[]>();
                if (p.Name.Contains("glass")) { SetupLit(m, null, null, null, new Color(.2f, .21f, .2f), .9f, 0, 1); continue; }
                bool wire = p.Name.Contains("fence_wire");
                SetupLit(m, T("baseMap") != null ? Tex(T("baseMap")) : null, T("normalMap") != null ? Tex(T("normalMap")) : null, T("maskMap") != null ? Tex(T("maskMap")) : null,
                    new Color(f[0], f[1], f[2], f[3]), 1, (float)r["metallicFactor"], 1, clip: (string)r["alphaMode"] != "OPAQUE" || wire, twoSided: (bool)r["doubleSided"] || wire);
            }
            // Meshy scrap (4k source maps)
            foreach (var n in new[] { "MX_ScrapHeapA", "MX_ScrapHeapB" })
            {
                var m = NewOrLoad(n, out bool created); mats[n] = m;
                if (created) SetupLit(m, Tex(Root + "Meshy/" + n + "_BaseMap.jpg"), Tex(Root + "Meshy/" + n + "_Normal.png"), Tex(Root + "Meshy/" + n + "_Mask.png"), Color.white, 1, 0, 1);
            }
            AssetDatabase.SaveAssets();
            return mats;
        }

        /// Non-emissive, tinted URP Lit copy of a robot material. Properties are copied explicitly: in this Unity build
        /// Material.CopyPropertiesFromMaterial(src) disables the _EMISSION keyword on the *source* material.
        static void DeadVariant(Material dead, Material src, Color tint, float smoothness)
        {
            dead.shader = src.shader;
            foreach (var t in new[] { "_BaseMap", "_BumpMap", "_MetallicGlossMap" }) dead.SetTexture(t, src.GetTexture(t));
            dead.SetFloat("_BumpScale", src.GetFloat("_BumpScale"));
            dead.EnableKeyword("_NORMALMAP"); dead.EnableKeyword("_METALLICSPECGLOSSMAP");
            dead.SetColor("_BaseColor", tint); dead.SetFloat("_Smoothness", smoothness);
            dead.SetTexture("_EmissionMap", null); dead.SetColor("_EmissionColor", Color.black); dead.DisableKeyword("_EMISSION");
            dead.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack; dead.enableInstancing = true;
            EditorUtility.SetDirty(dead);
        }

        /// Olive-grey machine paint for the charging cradles: the West Gate bone paint set, tinted, a little rougher.
        static Material CradlePaint()
        {
            var m = NewOrLoad("DP_CradlePaint", out _);
            var src = AssetDatabase.LoadAssetAtPath<Material>(WgMatDir + "WG_BonePaint.mat");
            m.shader = src.shader; m.CopyPropertiesFromMaterial(src);
            m.SetColor("_BaseColor", new Color(.6f, .63f, .6f)); m.SetFloat("_Smoothness", .8f); EditorUtility.SetDirty(m);
            return m;
        }

        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m)) return m;
            var trimmed = System.Text.RegularExpressions.Regex.Replace(name, @"\.\d+$", "");
            return mats.TryGetValue(trimmed, out m) ? m : null;
        }

        static int BuildPrefabs(Dictionary<string, Material> mats)
        {
            Directory.CreateDirectory(PrefabDir);
            var missing = new HashSet<string>(); int n = 0;
            foreach (var dir in new[] { "Structures", "Props", "Meshy" })
            foreach (var glb in Directory.GetFiles(Root + dir, "*.glb"))
            {
                var path = glb.Replace('\\', '/'); var name = Path.GetFileNameWithoutExtension(path);
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (!model) { Debug.LogWarning("Depot: not imported " + path); continue; }
                var root = new GameObject(name);
                try
                {
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(model); inst.transform.SetParent(root.transform, false); inst.name = name + " model";
                    var lod = new SortedDictionary<int, List<Renderer>>();
                    foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                    {
                        if (r.name.StartsWith("COL_"))
                        {
                            r.enabled = false;
                            var mf = r.GetComponent<MeshFilter>();
                            if (mf && mf.sharedMesh && !r.GetComponent<BoxCollider>()) { var b = r.gameObject.AddComponent<BoxCollider>(); b.center = mf.sharedMesh.bounds.center; b.size = mf.sharedMesh.bounds.size; }
                            r.sharedMaterials = r.sharedMaterials.Select(_ => Lookup(mats, "WG_Collider")).ToArray();
                            continue;
                        }
                        var slots = r.sharedMaterials;
                        for (int i = 0; i < slots.Length; i++) { var m = slots[i] ? Lookup(mats, slots[i].name) : null; if (m) slots[i] = m; else if (slots[i]) missing.Add(name + ":" + slots[i].name); }
                        // 27 Sep review: cradle housings in their own darker machine paint (bone paint read as copper)
                        if (name.StartsWith("DP_Cradle")) for (int i = 0; i < slots.Length; i++) if (slots[i] && slots[i].name == "WG_BonePaint") slots[i] = CradlePaint();
                        r.sharedMaterials = slots;
                        var mt = System.Text.RegularExpressions.Regex.Match(r.name, @"_LOD(\d)$");
                        if (mt.Success) { int k = int.Parse(mt.Groups[1].Value); if (!lod.ContainsKey(k)) lod[k] = new List<Renderer>(); lod[k].Add(r); }
                        var size = r.bounds.size.magnitude;
                        r.shadowCastingMode = size < .45f ? ShadowCastingMode.Off : ShadowCastingMode.On;
                        // detail meshes (bolts, rods) do not need to cast shadows
                        if (r.name.Contains("Detail_")) r.shadowCastingMode = ShadowCastingMode.Off;
                    }
                    if (lod.Count > 1)
                    {
                        var group = root.AddComponent<LODGroup>();
                        var size = lod[0].Select(r => r.bounds.size.magnitude).Max();
                        float[] cut = size > 8 ? new[] { .22f, .05f, .01f } : size > 3 ? new[] { .30f, .10f, .02f } : size > 1 ? new[] { .22f, .06f, .012f } : new[] { .12f, .035f, .008f };
                        var levels = lod.Values.Select((rs, i) => new LOD(cut[Math.Min(i, cut.Length - 1)] * (i == lod.Count - 1 ? .5f : 1), rs.ToArray())).ToArray();
                        group.SetLODs(levels); group.RecalculateBounds(); group.fadeMode = LODFadeMode.None;
                    }
                    bool hasCol = root.GetComponentsInChildren<Collider>(true).Any();
                    if (!hasCol && dir != "Structures")
                    {
                        var rs = (lod.Count > 0 ? lod[0].ToArray() : inst.GetComponentsInChildren<Renderer>()).Where(r => r.enabled).ToArray();
                        if (rs.Length > 0)
                        {
                            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                            if (b.size.y > .35f || b.size.x > .6f || b.size.z > .6f)
                            { var c = root.AddComponent<BoxCollider>(); c.center = root.transform.InverseTransformPoint(b.center); c.size = b.size * (dir == "Meshy" ? .8f : 1f); }
                        }
                    }
                    foreach (var t in root.GetComponentsInChildren<Transform>(true))
                        GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                    PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + name + ".prefab"); n++;
                }
                finally { UnityEngine.Object.DestroyImmediate(root); }
            }
            if (missing.Count > 0) Debug.LogWarning("Depot: unmapped materials: " + string.Join(", ", missing));
            return n;
        }

        /// Stripped worker-droid carcass (the rig's death pose baked to a static mesh) and a crashed drone shell,
        /// both in darker, sun-bleached material variants of the live robots.
        public static void BuildCarcassPrefabs(Dictionary<string, Material> mats)
        {
            const string worker = "Assets/AthenHill/Art/OuterBerms/WorkerDroid.glb";
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(worker);
            var clips = AssetDatabase.LoadAllAssetsAtPath(worker).OfType<AnimationClip>().ToDictionary(c => c.name);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            try
            {
                var anim = inst.GetComponentInChildren<Animation>();
                // legacy SampleAnimation leaves glTFast rigs in their bind pose in the Editor; AnimationMode samples correctly
                AnimationMode.StartAnimationMode();
                try { AnimationMode.BeginSampling(); AnimationMode.SampleAnimationClip(anim.gameObject, clips["death"], clips["death"].length); AnimationMode.EndSampling(); }
                finally { }
                var smr = inst.GetComponentInChildren<SkinnedMeshRenderer>();
                var baked = new Mesh { name = "DP_DeadWorker" }; smr.BakeMesh(baked, true);
                // express in the droid root's space (the skinned renderer sits under the armature)
                var toRoot = inst.transform.worldToLocalMatrix * smr.transform.localToWorldMatrix;
                var v = baked.vertices; var nn = baked.normals;
                for (int i = 0; i < v.Length; i++) { v[i] = toRoot.MultiplyPoint3x4(v[i]); nn[i] = toRoot.MultiplyVector(nn[i]).normalized; }
                float minY = v.Min(p => p.y); for (int i = 0; i < v.Length; i++) v[i].y -= minY + .03f;
                baked.vertices = v; baked.normals = nn; baked.RecalculateBounds(); baked.RecalculateTangents();
                AnimationMode.StopAnimationMode();
                var meshPath = Root + "Structures/DP_DeadWorker.asset";
                var old = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath); if (old) AssetDatabase.DeleteAsset(meshPath);
                AssetDatabase.CreateAsset(baked, meshPath);
                // sun-bleached, dust-caked variant of the live droid's URP set (27 Sep: the live material now has
                // normal + metal/roughness maps; the carcass's optics are dead, so no emission)
                var dead = NewOrLoad("DP_DeadWorkerPaint", out _);
                var workerMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/OuterBerms/Materials/RB_WorkerDroid.mat");
                if (workerMat) DeadVariant(dead, workerMat, new Color(.66f, .58f, .5f), .6f);
                var root = new GameObject("DP_DeadWorker");
                var go = new GameObject("DP_DeadWorker mesh", typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(root.transform, false);
                go.GetComponent<MeshFilter>().sharedMesh = baked; go.GetComponent<MeshRenderer>().sharedMaterial = dead;
                var b = baked.bounds; var col = root.AddComponent<BoxCollider>(); col.center = b.center; col.size = b.size * .85f;
                PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + "DP_DeadWorker.prefab"); UnityEngine.Object.DestroyImmediate(root);
            }
            finally { if (AnimationMode.InAnimationMode()) AnimationMode.StopAnimationMode(); UnityEngine.Object.DestroyImmediate(inst); }
            // crashed drone shell: the original drone model with a scorched, dust-dulled variant of its material
            const string drone = "Assets/AthenHill/Art/OuterBerms/ScrapDrone.glb";
            var dm = AssetDatabase.LoadAssetAtPath<GameObject>(drone);
            var droot = new GameObject("DP_CrashedDrone");
            try
            {
                var d = (GameObject)PrefabUtility.InstantiatePrefab(dm); d.transform.SetParent(droot.transform, false);
                var rs = d.GetComponentsInChildren<Renderer>(); var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds);
                float s = 1.25f / Mathf.Max(bb.size.x, bb.size.z); d.transform.localScale = Vector3.one * s; d.transform.localPosition = new Vector3(-bb.center.x * s, -bb.min.y * s, -bb.center.z * s);
                var dead = NewOrLoad("DP_CrashedDronePaint", out _);
                var droneMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/OuterBerms/Materials/RB_ScrapDrone.mat");
                if (droneMat) DeadVariant(dead, droneMat, new Color(.52f, .46f, .4f), .55f);
                foreach (var r in rs) r.sharedMaterials = r.sharedMaterials.Select(_ => dead).ToArray();
                var col = droot.AddComponent<BoxCollider>(); col.center = new Vector3(0, .3f, 0); col.size = new Vector3(1.1f, .6f, .7f);
                PrefabUtility.SaveAsPrefabAsset(droot, PrefabDir + "DP_CrashedDrone.prefab");
            }
            finally { UnityEngine.Object.DestroyImmediate(droot); }
        }

        // ------------------------------------------------------------------ review fixes (27 Sep, after the first captures)
        /// Fixes found in the post-install review: opaque chain-link (JPG base map had no alpha), blown-out white cradle
        /// cells, bright glossy concrete (sky-blue sheen on the plinth, clean jersey-barrier walls), stair-stepped apron
        /// edge and stray apron islands, the carcass standing upright (the worker's clips were static), and the missing
        /// cradle hum / arc crackle clips. Touches only this pass's materials, the apron mesh and its own audio objects.
        [MenuItem("Athen Hill/Outer Berms/Depot: review fixes")]
        public static void ReviewFixesMenu() => Debug.Log(ReviewFixes());
        public static string ReviewFixes()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) throw new Exception("Open the saved Athen Hill scene first");
            var log = new List<string>();
            // chain-link wire: base map with the Poly Haven opacity in alpha; keep coverage in the mips
            const string wirePng = Root + "Props/Textures/PH_modular_chainlink_fence_wire_BaseMap.png";
            AssetDatabase.ImportAsset(wirePng, ImportAssetOptions.ForceSynchronousImport);
            if (AssetImporter.GetAtPath(wirePng) is TextureImporter wi)
            {
                wi.alphaIsTransparency = true; wi.mipMapsPreserveCoverage = true; wi.alphaTestReferenceValue = .5f; wi.anisoLevel = 8; wi.streamingMipmaps = true;
                wi.textureCompression = TextureImporterCompression.CompressedHQ; wi.SaveAndReimport();
            }
            var wire = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "PH_modular_chainlink_fence_wire.mat");
            wire.SetTexture("_BaseMap", Tex(wirePng)); wire.SetColor("_BaseColor", new Color(.86f, .82f, .78f)); wire.SetFloat("_Cutoff", .5f);
            wire.SetFloat("_AlphaClip", 1); wire.EnableKeyword("_ALPHATEST_ON"); wire.renderQueue = (int)RenderQueue.AlphaTest; EditorUtility.SetDirty(wire); log.Add("fence wire alpha");
            // native review: the player sat at ~11.8 of 12 GB VRAM and paged (100 ms frames) facing the city from the
            // checkpoint. Small Poly Haven props do not need 2k maps on Linux: Standalone override 2048 -> 1024
            // (the overhead crane, seen large, keeps 2k).
            int shrunk = 0;
            foreach (var tp in Directory.GetFiles(Root + "Props/Textures").Where(f => (f.EndsWith(".jpg") || f.EndsWith(".png")) && !f.Contains("overhead_crane")).Select(f => f.Replace('\\', '/')))
            {
                if (AssetImporter.GetAtPath(tp) is not TextureImporter ti) continue;
                var ps = ti.GetPlatformTextureSettings("Standalone");
                if (ps.overridden && ps.maxTextureSize <= 1024 && ti.maxTextureSize <= 1024) continue;
                ps.overridden = true; ps.maxTextureSize = 1024; ti.SetPlatformTextureSettings(ps); ti.maxTextureSize = 1024; ti.SaveAndReimport(); shrunk++;
            }
            log.Add("props textures capped at 1k: " + shrunk);
            var cell = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "DP_CyanCell.mat");
            cell.SetColor("_BaseColor", new Color(.05f, .16f, .18f)); cell.SetColor("_EmissionColor", new Color(.3f, 1.45f, 1.75f)); EditorUtility.SetDirty(cell); log.Add("cyan cells toned to cyan");
            var concrete = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "DP_Concrete.mat");
            concrete.SetColor("_BaseColor", new Color(.84f, .75f, .64f)); concrete.SetFloat("_Smoothness", .45f); EditorUtility.SetDirty(concrete);
            var paint = CradlePaint();
            foreach (var pf in new[] { "DP_Cradle", "DP_CradleBroken" })
            {
                var root = PrefabUtility.LoadPrefabContents(PrefabDir + pf + ".prefab");
                try
                {
                    foreach (var r in root.GetComponentsInChildren<Renderer>(true))
                        r.sharedMaterials = r.sharedMaterials.Select(m => m && m.name == "WG_BonePaint" ? paint : m).ToArray();
                    PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + pf + ".prefab");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            log.Add("cradle housings in DP_CradlePaint");
            var apronMat = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "DP_ApronConcrete.mat");
            apronMat.SetColor("_BaseColor", new Color(.84f, .78f, .7f)); EditorUtility.SetDirty(apronMat); log.Add("concrete darker, less glossy");
            // apron: rebuild the mesh asset in place (the scene object keeps its reference)
            var layout = LoadDesign();
            groundCol = GameObject.Find("Outer Berms/Berms ground").GetComponent<MeshCollider>();
            Physics.SyncTransforms();
            var apron = GameObject.Find("Outer Berms/Machine depot/" + DepotName + "/Ground/Yard apron");
            var mesh = ApronMesh((JObject)layout["anchors"]["apron"], (JArray)layout["anchors"]["drifts"], out int tris);
            apron.GetComponent<MeshFilter>().sharedMesh = mesh; var mc = apron.GetComponent<MeshCollider>(); mc.sharedMesh = null; mc.sharedMesh = mesh;
            log.Add("apron " + tris + " triangles");
            // carcasses (the worker's clips now animate, so the death pose bakes)
            BuildCarcassPrefabs(BuildMaterials()); log.Add("carcass prefabs rebuilt");
            // audio
            AudioClip Clip(string n) => AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/AthenHill/Audio/ElevenLabs/Combat/" + n + ".wav");
            var fx = GameObject.Find("Outer Berms/Machine depot/" + DepotName + "/Power effects").transform;
            var hum = fx.Find("Cradle hum").GetComponent<AudioSource>(); hum.clip = Clip("cradle-hum"); hum.playOnAwake = hum.clip; hum.loop = true; hum.volume = .5f; EditorUtility.SetDirty(hum);
            foreach (var arc in fx.GetComponentsInChildren<ElectricArc>(true))
            {
                arc.clips = (arc.name == "Cradle arc" ? new[] { Clip("arc-crackle-1"), Clip("arc-crackle-2") } : new[] { Clip("arc-crackle-2") }).Where(c => c).ToArray();
                EditorUtility.SetDirty(arc);
            }
            log.Add("hum " + (hum.clip ? hum.clip.name : "missing") + ", arcs " + string.Join("/", fx.GetComponentsInChildren<ElectricArc>(true).Select(x => x.clips.Length)));
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Evidence + "review-fixes.json", JsonConvert.SerializeObject(log, Formatting.Indented));
            return string.Join("; ", log);
        }

        // ------------------------------------------------------------------ install
        static MeshCollider groundCol;
        static float GY(float x, float z) => groundCol.Raycast(new Ray(new Vector3(x, 80, z), Vector3.down), out var h, 200) ? h.point.y : 0;
        static float GroundMin(float x, float z, float r)
        {
            float m = GY(x, z);
            for (int i = 0; i < 12; i++) { float a = i * Mathf.PI / 6; m = Mathf.Min(m, GY(x + Mathf.Cos(a) * r, z + Mathf.Sin(a) * r)); }
            return m - .04f;
        }
        static float ResolveY(JToken y, float x, float z, float r)
        {
            if (y.Type == JTokenType.Float || y.Type == JTokenType.Integer) return (float)y;
            var s = (string)y;
            if (s == "ground-min") return GroundMin(x, z, Mathf.Max(r, .3f));
            if (s.StartsWith("ground")) return GY(x, z) + (s.Length > 6 ? float.Parse(s.Substring(6), System.Globalization.CultureInfo.InvariantCulture) : 0);
            throw new Exception("Bad y " + s);
        }

        [MenuItem("Athen Hill/Outer Berms/Depot: install")]
        public static void InstallMenu() => Install(false);
        /// Authoring iteration: removes only this pass's own root and re-installs from layout.json.
        public static string Reinstall() => Install(true);

        static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) throw new Exception("Open the saved Athen Hill scene first");
            var depot = GameObject.Find("Outer Berms/Machine depot").transform;
            var existing = depot.Find(DepotName);
            if (existing && !replace) throw new Exception("Depot rebuild already installed; edit the saved objects instead.");
            if (existing) UnityEngine.Object.DestroyImmediate(existing.gameObject);
            var layout = JObject.Parse(File.ReadAllText(ArtDir + "layout.json"));
            var record = new Dictionary<string, object>();
            record["ground"] = SculptGround();
            groundCol = GameObject.Find("Outer Berms/Berms ground").GetComponent<MeshCollider>();
            Physics.SyncTransforms();

            var root = new GameObject(DepotName).transform; root.SetParent(depot, false);
            var groups = new Dictionary<string, Transform>();
            Transform Group(string n) { if (!groups.TryGetValue(n, out var g)) { g = new GameObject(n).transform; g.SetParent(root, false); groups[n] = g; } return g; }

            BuildApron(Group("Ground"), (JObject)layout["anchors"]["apron"], (JArray)layout["anchors"]["drifts"], record);
            int placed = 0; var missingPrefabs = new List<string>();
            foreach (JObject it in layout["items"])
            {
                var spec = (string)it["prefab"]; var dir = spec.StartsWith("WG:") ? WgPrefabDir : PrefabDir;
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(dir + spec.Substring(3) + ".prefab");
                if (!prefab) { missingPrefabs.Add(spec); continue; }
                float x = (float)it["x"], z = (float)it["z"], r = (float)it["r"];
                float y = ResolveY(it["y"], x, z, r);
                var g = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                g.name = (string)it["name"]; g.transform.SetParent(Group((string)it["group"]), false);
                var rot = it["rot"] is JArray ra ? Quaternion.Euler((float)ra[0], (float)ra[1], (float)ra[2]) : Quaternion.Euler(0, (float)it["yaw"], 0);
                g.transform.SetPositionAndRotation(new Vector3(x, y, z), rot);
                g.transform.localScale = Vector3.one * (float)it["scale"];
                if (!(bool)it["collider"]) foreach (var c in g.GetComponentsInChildren<Collider>(true)) c.enabled = false;
                placed++;
            }
            record["placed"] = placed; record["missingPrefabs"] = missingPrefabs;
            RetireOldVisuals(depot, (JObject)layout["anchors"]["carcass"], record);
            MoveSpawns((JArray)layout["anchors"]["spawns"], record);
            AddPower(root, record);
            Decals(Group("Decals"), (JArray)layout["anchors"]["decals"], record);
            CamerasAndLandmarks(root, (JObject)layout["anchors"], record);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "install.json", JsonConvert.SerializeObject(record, Formatting.Indented));
            return JsonConvert.SerializeObject(record);
        }

        /// Yard apron: cracked concrete following the sculpted ground 5 cm proud, broken outline, cut where sand drifts
        /// have buried it (ground above cut_height or a designed drift) — the sand edge then overlaps the slab edge.
        /// 27 Sep review: the outline is traced with marching squares (interpolated crossings, no 25 cm stair-steps),
        /// the broken edge gets an 18 cm skirt so it reads as a slab at player height, and islands under 8 m² are dropped.
        static void BuildApron(Transform parent, JObject a, JArray drifts, Dictionary<string, object> record)
        {
            var mesh = ApronMesh(a, drifts, out int tris);
            var go = new GameObject("Yard apron", typeof(MeshFilter), typeof(MeshRenderer), typeof(MeshCollider));
            go.transform.SetParent(parent, false); go.isStatic = true;
            go.GetComponent<MeshFilter>().sharedMesh = mesh; go.GetComponent<MeshCollider>().sharedMesh = mesh;
            var r = go.GetComponent<MeshRenderer>(); r.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "DP_ApronConcrete.mat"); r.shadowCastingMode = ShadowCastingMode.Off;
            record["apronTriangles"] = tris;
        }

        static Mesh ApronMesh(JObject a, JArray drifts, out int triangleCount)
        {
            float x0 = (float)a["x0"], x1 = (float)a["x1"], z0 = (float)a["z0"], z1 = (float)a["z1"], cutH = (float)a["cut_height"];
            var design = new JObject { ["drifts"] = drifts };
            const float step = .25f; int nx = Mathf.CeilToInt((x1 - x0) / step) + 1, nz = Mathf.CeilToInt((z1 - z0) / step) + 1;
            float Field(float x, float z, float gy)
            {
                float edge = Mathf.Min(Mathf.Min(x - x0, x1 - x), Mathf.Min(z - z0, z1 - z));
                float n = Mathf.PerlinNoise(x * .55f + 11, z * .55f + 3) * 1.1f + Mathf.PerlinNoise(x * 2.1f, z * 2.1f) * .35f;
                return Mathf.Min(edge - n * .9f, Mathf.Min((cutH + (n - .7f) * .25f - gy) * 2f, (.07f - Drift(design, x, z)) * 4f));
            }
            float Heave(float x, float z)
            {
                int px = Mathf.FloorToInt((x + 200) / 3f), pz = Mathf.FloorToInt((z + 200) / 3f);
                float tx = (Mathf.PerlinNoise(px * 7.1f, pz * 3.3f) - .5f) * .018f, tz = (Mathf.PerlinNoise(px * 2.7f, pz * 9.1f) - .5f) * .018f;
                return tx * ((x + 200) % 3f - 1.5f) + tz * ((z + 200) % 3f - 1.5f);
            }
            var gx = new float[nx]; var gz = new float[nz]; var gh = new float[nx, nz]; var f = new float[nx, nz];
            for (int i = 0; i < nx; i++) gx[i] = Mathf.Min(x1, x0 + i * step);
            for (int j = 0; j < nz; j++) gz[j] = Mathf.Min(z1, z0 + j * step);
            for (int i = 0; i < nx; i++) for (int j = 0; j < nz; j++) { gh[i, j] = GY(gx[i], gz[j]); f[i, j] = Field(gx[i], gz[j], gh[i, j]); }
            // morphological opening (erode then dilate one cell): cuts thin bridges and slivers so they become islands
            bool In(int i, int j) => i >= 0 && j >= 0 && i < nx && j < nz && f[i, j] > 0;
            var er = new bool[nx, nz];
            for (int i = 0; i < nx; i++) for (int j = 0; j < nz; j++) er[i, j] = In(i, j) && In(i - 1, j) && In(i + 1, j) && In(i, j - 1) && In(i, j + 1);
            bool Er(int i, int j) => i >= 0 && j >= 0 && i < nx && j < nz && er[i, j];
            var cut = new List<(int, int)>();
            for (int i = 0; i < nx; i++) for (int j = 0; j < nz; j++)
                if (In(i, j) && !(Er(i, j) || Er(i - 1, j) || Er(i + 1, j) || Er(i, j - 1) || Er(i, j + 1))) cut.Add((i, j));
            foreach (var (i, j) in cut) f[i, j] = -.02f;
            var P = new List<Vector3>(); var ids = new Dictionary<long, int>(); var tri = new List<int>(); var rims = new List<(int, int)>();
            int Vert(long key, float x, float z)
            {
                if (ids.TryGetValue(key, out int k)) return k;
                k = P.Count; P.Add(new Vector3(x, GY(x, z) + .05f + Heave(x, z), z)); ids[key] = k; return k;
            }
            int Corner(int i, int j) => Vert(((long)i * 4096 + j) * 4, gx[i], gz[j]);
            int Cross(int i, int j, int i2, int j2)
            {
                float fa = f[i, j], fb = f[i2, j2], t = Mathf.Clamp(fa / (fa - fb), .02f, .98f);
                long key = (((long)Math.Min(i, i2) * 4096 + Math.Min(j, j2)) * 4) + (i != i2 ? 1 : 2);
                return Vert(key, Mathf.Lerp(gx[i], gx[i2], t), Mathf.Lerp(gz[j], gz[j2], t));
            }
            for (int i = 0; i < nx - 1; i++)
                for (int j = 0; j < nz - 1; j++)
                {
                    var c = new[] { (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1) };
                    int inside = c.Count(q => f[q.Item1, q.Item2] > 0);
                    if (inside == 0) continue;
                    var poly = new List<int>(); var isCross = new List<bool>();
                    for (int k = 0; k < 4; k++)
                    {
                        var (ai, aj) = c[k]; var (bi, bj) = c[(k + 1) % 4];
                        bool ain = f[ai, aj] > 0, bin = f[bi, bj] > 0;
                        if (ain) { poly.Add(Corner(ai, aj)); isCross.Add(false); }
                        if (ain != bin) { poly.Add(Cross(ai, aj, bi, bj)); isCross.Add(true); }
                    }
                    // winding: corners run +x then +z (counter-clockwise from above); Unity front faces are clockwise
                    for (int k = 1; k < poly.Count - 1; k++) tri.AddRange(new[] { poly[0], poly[k + 1], poly[k] });
                    for (int k = 0; k < poly.Count; k++)
                        if (isCross[k] && isCross[(k + 1) % poly.Count]) rims.Add((poly[k], poly[(k + 1) % poly.Count]));
                }
            // drop small islands (union-find over shared vertices, area in m²)
            var parent = Enumerable.Range(0, P.Count).ToArray();
            int Find(int x) { while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; }
            for (int t = 0; t < tri.Count; t += 3) { parent[Find(tri[t])] = Find(tri[t + 1]); parent[Find(tri[t + 1])] = Find(tri[t + 2]); }
            var area = new Dictionary<int, float>();
            for (int t = 0; t < tri.Count; t += 3)
            {
                var ar = Vector3.Cross(P[tri[t + 1]] - P[tri[t]], P[tri[t + 2]] - P[tri[t]]).magnitude * .5f; int r = Find(tri[t]);
                area[r] = (area.TryGetValue(r, out var s0) ? s0 : 0) + ar;
            }
            float mainArea = area.Count > 0 ? area.Values.Max() : 0;
            bool Keep(int v) => area.TryGetValue(Find(v), out var ar) && ar >= Mathf.Min(8f, mainArea);
            var top = new List<int>(); for (int t = 0; t < tri.Count; t += 3) if (Keep(tri[t])) top.AddRange(tri.GetRange(t, 3));
            // skirt: separate vertices (hard edge) dropping 13 cm below the slab rim into the ground
            var V = new List<Vector3>(P); var UV = P.Select(p => new Vector2(p.x, p.z)).ToList(); var all = new List<int>(top);
            foreach (var (va, vb) in rims)
            {
                if (!Keep(va)) continue;
                Vector3 pa = P[va], pb = P[vb]; float len = Vector3.Distance(pa, pb); if (len < 1e-4f) continue;
                int b0 = V.Count; float u0 = pa.x + pa.z;
                V.Add(pa); V.Add(pb); V.Add(pb + Vector3.down * .18f); V.Add(pa + Vector3.down * .18f);
                UV.Add(new Vector2(u0, 0)); UV.Add(new Vector2(u0 + len, 0)); UV.Add(new Vector2(u0 + len, -.13f)); UV.Add(new Vector2(u0, -.13f));
                // rim runs with the inside on its left when seen from above; the skirt faces outward
                all.AddRange(new[] { b0, b0 + 1, b0 + 2, b0, b0 + 2, b0 + 3 });
            }
            var mesh = new Mesh { name = "DP_YardApron", indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(V); mesh.SetUVs(0, UV); mesh.SetTriangles(all, 0);
            // top faces must face up; flip the whole set if the winding came out downward
            var nrm = Vector3.Cross(V[top[1]] - V[top[0]], V[top[2]] - V[top[0]]);
            if (nrm.y < 0) { for (int t = 0; t < all.Count; t += 3) (all[t + 1], all[t + 2]) = (all[t + 2], all[t + 1]); mesh.SetTriangles(all, 0); }
            mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
            var path = Root + "Structures/DP_YardApron.asset";
            var old = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (old) { old.Clear(); EditorUtility.CopySerialized(mesh, old); UnityEngine.Object.DestroyImmediate(mesh); mesh = old; } else AssetDatabase.CreateAsset(mesh, path);
            triangleCount = all.Count / 3;
            return mesh;
        }

        static void RetireOldVisuals(Transform depot, JObject carcass, Dictionary<string, object> record)
        {
            var off = new List<string>();
            foreach (Transform t in depot.Cast<Transform>().ToArray())
            {
                if (t.name == DepotName) continue;
                if (t.name == "Stripped mining droid carcass")
                {
                    float x = (float)carcass["x"], z = (float)carcass["z"]; var r = carcass["rot"].ToObject<float[]>();
                    t.SetPositionAndRotation(new Vector3(x, ResolveY(carcass["y"], x, z, 0), z), Quaternion.Euler(r[0], r[1], r[2]));
                    continue;
                }
                if (t.name == "Depot litter" && t.position.z > -25) { t.position = new Vector3(t.position.x, GY(t.position.x, t.position.z), t.position.z); continue; }
                if (t.gameObject.activeSelf) { t.gameObject.SetActive(false); off.Add(t.name); }
            }
            record["retired"] = off;
        }

        static void MoveSpawns(JArray spawns, Dictionary<string, object> record)
        {
            var enc = GameObject.Find("Outer Berms/Encounters/Machine depot nest").GetComponent<DroidEncounter>();
            var moved = new List<object>();
            for (int i = 0; i < enc.spawns.Length && i < spawns.Count; i++)
            {
                var s = (JObject)spawns[i]; float x = (float)s["x"], z = (float)s["z"]; var f = s["face"].ToObject<float[]>();
                var p = new Vector3(x, GY(x, z), z); var face = new Vector3(f[0], 0, f[1]) - p; face.y = 0;
                enc.spawns[i].point.SetPositionAndRotation(p, Quaternion.LookRotation(face.normalized));
                moved.Add(new { enc.spawns[i].point.name, pos = new[] { x, p.y, z } });
            }
            var avg = enc.spawns.Aggregate(Vector3.zero, (a, s) => a + s.point.position) / enc.spawns.Length;
            var kids = enc.spawns.Select(s => (s.point, s.point.position, s.point.rotation)).ToArray();
            enc.transform.position = avg;
            foreach (var (t, pos, rot) in kids) t.SetPositionAndRotation(pos, rot);
            EditorUtility.SetDirty(enc);
            record["spawns"] = moved;
        }

        static Light AddLight(Transform parent, string name, Vector3 pos, Color color, float intensity, float range)
        {
            var l = new GameObject(name, typeof(Light)).GetComponent<Light>();
            l.transform.SetParent(parent, true); l.transform.position = pos;
            l.type = LightType.Point; l.color = color; l.intensity = intensity; l.range = range; l.shadows = LightShadows.None;
            return l;
        }

        /// Cradle glow lights (night only), the broken cradle's intermittent arc (sparks, flash, crackle), a low
        /// transformer hum at the plinth, and a sparking lamp in the hall.
        static void AddPower(Transform root, Dictionary<string, object> record)
        {
            var fx = new GameObject("Power effects").transform; fx.SetParent(root, false);
            var cyan = new Color(.3f, .85f, .95f);
            var lights = new List<Light>();
            foreach (var c in root.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("LIGHT_cell")))
                lights.Add(AddLight(fx, "Cradle cell glow", c.position, cyan, 1.3f, 3.2f));
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>();
            var cityAudio = UnityEngine.Object.FindAnyObjectByType<CityAudio>();
            var sfx = cityAudio && cityAudio.confirmation ? cityAudio.confirmation.outputAudioMixerGroup : null;
            var sparksMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/OuterBerms/BermsSparks.mat");
            var arcs = new List<string>();
            foreach (var e in root.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("FX_arc") || t.name.StartsWith("LIGHT_hall_spark")))
            {
                var go = new GameObject(e.name.StartsWith("FX_arc") ? "Cradle arc" : "Hall lamp sparks"); go.transform.SetParent(fx, false); go.transform.position = e.position;
                var arc = go.AddComponent<ElectricArc>(); arc.session = session;
                arc.flash = AddLight(go.transform, "Arc flash", e.position, e.name.StartsWith("FX_arc") ? new Color(.55f, .9f, 1f) : new Color(1f, .8f, .5f), 0, 4.5f);
                arc.sparks = SparkSystem(go.transform, sparksMat);
                var src = go.AddComponent<AudioSource>(); src.playOnAwake = false; src.spatialBlend = 1; src.rolloffMode = AudioRolloffMode.Linear; src.minDistance = 2; src.maxDistance = 22; src.outputAudioMixerGroup = sfx; src.dopplerLevel = 0;
                arc.voice = src; arc.clips = new[] { "arc-crackle-1", "arc-crackle-2" }.Select(n => AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/AthenHill/Audio/ElevenLabs/Combat/" + n + ".wav")).Where(c => c).ToArray();
                if (!e.name.StartsWith("FX_arc")) { arc.minInterval = 5; arc.maxInterval = 11; arc.flashIntensity = 2.2f; }
                arcs.Add(go.name);
            }
            // transformer hum at the plinth
            var hum = new GameObject("Cradle hum", typeof(AudioSource)).GetComponent<AudioSource>(); hum.transform.SetParent(fx, false); hum.transform.position = new Vector3(-80.4f, 1.2f, -39.4f);
            hum.clip = AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/AthenHill/Audio/ElevenLabs/Combat/cradle-hum.wav"); hum.loop = true; hum.playOnAwake = hum.clip; hum.spatialBlend = 1;
            hum.rolloffMode = AudioRolloffMode.Linear; hum.minDistance = 2.5f; hum.maxDistance = 20; hum.volume = .55f; hum.outputAudioMixerGroup = sfx; hum.dopplerLevel = 0;
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            circuit.practicalLights = circuit.practicalLights.Where(l => l && !l.transform.IsChildOf(root)).Concat(lights).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !l.transform.IsChildOf(root)).Concat(lights).ToArray();
            EditorUtility.SetDirty(circuit);
            record["lights"] = lights.Count; record["arcs"] = arcs; record["humClip"] = hum.clip ? hum.clip.name : null;
        }

        static ParticleSystem SparkSystem(Transform parent, Material mat)
        {
            var go = new GameObject("Sparks", typeof(ParticleSystem)); go.transform.SetParent(parent, false);
            var ps = go.GetComponent<ParticleSystem>(); ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.playOnAwake = false; main.loop = false; main.duration = .5f; main.startLifetime = new ParticleSystem.MinMaxCurve(.25f, .7f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(1.5f, 5f); main.startSize = new ParticleSystem.MinMaxCurve(.02f, .05f); main.gravityModifier = 1.3f;
            main.simulationSpace = ParticleSystemSimulationSpace.World; main.maxParticles = 120; main.startColor = new Color(.8f, .95f, 1f);
            var em = ps.emission; em.enabled = false;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Sphere; shape.radius = .05f;
            var col = ps.colorOverLifetime; col.enabled = true; var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(new Color(.85f, .97f, 1f), 0), new GradientColorKey(new Color(1f, .6f, .2f), .5f), new GradientColorKey(new Color(1f, .3f, .1f), 1) }, new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0, 1) }); col.color = g;
            var coll = ps.collision; coll.enabled = true; coll.type = ParticleSystemCollisionType.World; coll.dampen = .5f; coll.bounce = .35f; coll.quality = ParticleSystemCollisionQuality.Low; coll.maxCollisionShapes = 8;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.renderMode = ParticleSystemRenderMode.Stretch; r.velocityScale = .05f; r.lengthScale = 1; r.sharedMaterial = mat; r.shadowCastingMode = ShadowCastingMode.Off;
            return ps;
        }

        static void Decals(Transform parent, JArray list, Dictionary<string, object> record)
        {
            var template = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat");
            if (!template || !template.HasProperty("Base_Map")) throw new Exception("Decal template material missing");
            var mats = new Dictionary<string, Material>(); int n = 0;
            foreach (JObject d in list)
            {
                var kind = (string)d["kind"];
                if (!mats.TryGetValue(kind, out var m))
                {
                    m = AssetDatabase.LoadAssetAtPath<Material>((kind.StartsWith("WG_") ? WgMatDir : MatDir) + kind + ".mat");
                    if (!m) { m = new Material(template) { name = kind }; m.SetTexture("Base_Map", Tex(Root + "Textures/" + kind + ".png")); if (m.HasProperty("Normal_Blend")) m.SetFloat("Normal_Blend", 0); AssetDatabase.CreateAsset(m, MatDir + kind + ".mat"); }
                    mats[kind] = m;
                }
                float x = (float)d["x"], z = (float)d["z"];
                var dir = new Vector3((float)d["dx"], 0, (float)d["dz"]).normalized;
                var go = new GameObject(kind.Replace("DP_Decal", "Decal ").Replace("WG_Decal", "Decal ") + " " + (++n)); go.transform.SetParent(parent, false);
                var p = go.AddComponent<UnityEngine.Rendering.Universal.DecalProjector>();
                if (d["proj"] == null)
                {
                    go.transform.SetPositionAndRotation(new Vector3(x, GY(x, z) + .4f, z), Quaternion.LookRotation(Vector3.down, dir));
                    p.size = new Vector3((float)d["w"], (float)d["l"], (float)d["depth"]); p.pivot = new Vector3(0, 0, (float)d["depth"] * .5f - .4f);
                    p.startAngleFade = 60; p.endAngleFade = 85;
                }
                else
                {
                    var f = d["proj"].ToObject<float[]>(); var fwd = new Vector3(f[0], f[1], f[2]).normalized;
                    go.transform.SetPositionAndRotation(new Vector3(x, GY(x, z) + (float)d["y"], z), Quaternion.LookRotation(fwd, Vector3.up));
                    p.size = new Vector3((float)d["w"], (float)d["l"], (float)d["depth"]); p.pivot = Vector3.zero;
                    p.startAngleFade = 50; p.endAngleFade = 75;
                }
                p.material = m; p.fadeFactor = (float)d["fade"]; p.drawDistance = 55; p.fadeScale = .85f;
            }
            record["decals"] = n;
        }

        static void CamerasAndLandmarks(Transform root, JObject a, Dictionary<string, object> record)
        {
            var cams = new GameObject("Depot review cameras").transform; cams.SetParent(root, false);
            foreach (var p in ((JObject)a["cameras"]).Properties())
            {
                var v = (JArray)p.Value; var pos = v[0].ToObject<float[]>(); var tgt = v[1].ToObject<float[]>();
                float y = pos[1] < 4 ? GY(pos[0], pos[2]) + pos[1] : pos[1];
                var existing = GameObject.Find(p.Name);
                var g = existing ? existing : new GameObject(p.Name, typeof(Camera));
                g.transform.SetParent(cams, true);
                g.transform.position = new Vector3(pos[0], y, pos[2]); g.transform.LookAt(new Vector3(tgt[0], tgt[1] < 4 ? GY(tgt[0], tgt[2]) + tgt[1] : tgt[1], tgt[2]));
                var c = g.GetComponent<Camera>(); c.enabled = false; c.fieldOfView = (float)v[2]; c.farClipPlane = 650; c.nearClipPlane = .05f;
            }
            var marks = GameObject.Find("Landmarks").transform;
            foreach (var p in ((JObject)a["landmarks"]).Properties())
            {
                var xz = p.Value.ToObject<float[]>(); var t = marks.Find(p.Name);
                if (!t) { t = new GameObject(p.Name).transform; t.SetParent(marks, true); }
                t.position = new Vector3(xz[0], GY(xz[0], xz[1]) + .1f, xz[1]);
            }
            record["landmarks"] = ((JObject)a["landmarks"]).Properties().Select(p => p.Name).ToArray();
        }
    }
}
