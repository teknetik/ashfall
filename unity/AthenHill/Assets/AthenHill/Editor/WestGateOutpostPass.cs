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
    /// 26 September 2026: West Gate / Warden outpost rebuild (replaces the first-pass booth, floating TextMesh
    /// signs and box props). Sources: art/west_gate_20260926 (Blender-authored structures, Poly Haven CC0 props
    /// and textures, OFL stencil fonts, generated sign/paper textures). Placement comes from layout.json.
    ///
    /// Menu: Athen Hill → Outer Berms → West Gate: build assets (textures, URP materials, prefabs; existing
    /// materials are kept so Inspector edits survive) and West Gate: install outpost (refuses when the outpost root
    /// exists). Gameplay objects (Wardens, locker, briefing board, range control, respawn, landmarks) keep their
    /// components, IDs and references and are only moved; replaced visuals stay in the scene, inactive.
    /// </summary>
    public static class WestGateOutpostPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/WestGate/";
        const string MatDir = Root + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/WestGate/";
        const string Layout = "../../art/west_gate_20260926/layout.json";
        const string Evidence = "../evidence/west-gate/20260926/";
        const string OutpostName = "West Gate outpost";

        // metres per texture repeat for the tiling WG materials (Blender UVs are in metres)
        static readonly Dictionary<string, float> Tile = new()
        {
            ["WG_OlivePaint"] = 1.5f, ["WG_BonePaint"] = 2.2f, ["WG_SandPaint"] = 2.2f, ["WG_RustSteel"] = 1.2f, ["WG_PlateSteel"] = 2.0f,
            ["WG_ShutterPaint"] = 2.0f, ["WG_Concrete"] = 4.0f, ["WG_Plywood"] = 1.0f, ["WG_Hessian"] = .38f, ["WG_ShadeCloth"] = .7f, ["WG_Hazard"] = 1.8f,
        };
        static readonly string[] BigProps = { "PH_concrete_road_barrier", "PH_concrete_road_barrier_02", "PH_boulder_02", "PH_boulder_03", "PH_boulder_04", "PH_portable_generator", "PH_exterior_aircon_unit_rusted" };

        // ------------------------------------------------------------------ assets
        [MenuItem("Athen Hill/Outer Berms/West Gate: build assets")]
        public static void BuildAssets()
        {
            ConfigureTextures();
            var mats = BuildMaterials();
            BuildPrefabs(mats);
            AssetDatabase.SaveAssets();
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
                    bool normal = file.EndsWith("_Normal"), mask = file.EndsWith("_Mask");
                    bool changed = false;
                    void Set<T>(T current, T value, Action<T> apply) { if (!EqualityComparer<T>.Default.Equals(current, value)) { apply(value); changed = true; } }
                    if (file.StartsWith("BermsGroundLayers_"))
                    {
                        Set(ti.textureShape, TextureImporterShape.Texture2DArray, v => ti.textureShape = v);
                        var s = new TextureImporterSettings(); ti.ReadTextureSettings(s);
                        if (s.flipbookColumns != 1 || s.flipbookRows != 4) { s.flipbookColumns = 1; s.flipbookRows = 4; ti.SetTextureSettings(s); changed = true; }
                        Set(ti.sRGBTexture, file.EndsWith("_AH"), v => ti.sRGBTexture = v);
                        Set(ti.maxTextureSize, 8192, v => ti.maxTextureSize = v);
                        Set(ti.alphaIsTransparency, false, v => ti.alphaIsTransparency = v);
                    }
                    else if (file == "BermsGroundSplat")
                    {
                        Set(ti.sRGBTexture, false, v => ti.sRGBTexture = v); Set(ti.wrapMode, TextureWrapMode.Clamp, v => ti.wrapMode = v);
                        Set(ti.maxTextureSize, 2048, v => ti.maxTextureSize = v);
                    }
                    else
                    {
                        Set(ti.textureType, normal ? TextureImporterType.NormalMap : TextureImporterType.Default, v => ti.textureType = v);
                        Set(ti.sRGBTexture, !normal && !mask, v => ti.sRGBTexture = v);
                        bool big = path.Contains("/Textures/WG_") || BigProps.Any(p => file.StartsWith(p + "_"));
                        Set(ti.maxTextureSize, big ? 2048 : 1024, v => ti.maxTextureSize = v);
                        Set(ti.alphaIsTransparency, (file.EndsWith("_BaseMap") || file.StartsWith("WG_Decal")) && path.EndsWith(".png"), v => ti.alphaIsTransparency = v);
                        if (file.StartsWith("WG_Decal")) Set(ti.wrapMode, TextureWrapMode.Clamp, v => ti.wrapMode = v);
                    }
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

        static void SetupLit(Material m, Texture2D baseMap, Texture2D normal, Texture2D mask, Color color, float smoothness, float metallic, float tile, bool clip = false, bool twoSided = false)
        {
            m.SetTexture("_BaseMap", baseMap); m.SetColor("_BaseColor", color);
            m.SetTextureScale("_BaseMap", Vector2.one * tile);
            if (normal) { m.SetTexture("_BumpMap", normal); m.EnableKeyword("_NORMALMAP"); m.SetFloat("_BumpScale", 1); }
            if (mask)
            {
                m.SetTexture("_MetallicGlossMap", mask); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetTexture("_OcclusionMap", mask); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1);
                m.SetFloat("_Smoothness", smoothness); // multiplier on mask alpha
            }
            else { m.SetFloat("_Smoothness", smoothness); m.SetFloat("_Metallic", metallic); }
            if (clip) { m.SetFloat("_AlphaClip", 1); m.SetFloat("_Cutoff", .45f); m.EnableKeyword("_ALPHATEST_ON"); m.renderQueue = (int)RenderQueue.AlphaTest; }
            if (twoSided) { m.SetFloat("_Cull", 0); m.doubleSidedGI = true; }
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
        }

        static void SetupEmissive(Material m, Color color, float intensity)
        {
            m.SetColor("_BaseColor", color * .3f); m.SetFloat("_Smoothness", .8f);
            m.SetColor("_EmissionColor", color * intensity); m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive; m.enableInstancing = true;
            EditorUtility.SetDirty(m);
        }

        static void SetupTransparent(Material m, Color color)
        {
            m.SetFloat("_Surface", 1); m.SetFloat("_Blend", 0); m.SetFloat("_ZWrite", 0);
            m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.renderQueue = (int)RenderQueue.Transparent;
            m.SetColor("_BaseColor", color); m.SetFloat("_Smoothness", .92f); m.SetFloat("_Metallic", 0);
            EditorUtility.SetDirty(m);
        }

        public static Dictionary<string, Material> BuildMaterials()
        {
            var mats = new Dictionary<string, Material>();
            // tiling / sign / paper sets generated by make_textures.py
            foreach (var bm in Directory.GetFiles(Root + "Textures", "WG_*_BaseMap.*").Where(f => !f.EndsWith(".meta")))
            {
                var name = Path.GetFileName(bm); name = name.Substring(0, name.IndexOf("_BaseMap", StringComparison.Ordinal));
                var m = NewOrLoad(name, out bool created); mats[name] = m;
                if (!created) continue;
                float tile = Tile.TryGetValue(name, out var t) ? 1f / t : 1f;
                bool cloth = name is "WG_Banner" or "WG_ShadeCloth", paper = name.StartsWith("WG_Paper");
                SetupLit(m, Tex(bm.Replace('\\', '/')), Tex(Root + "Textures/" + name + "_Normal.jpg"), Tex(Root + "Textures/" + name + "_Mask.png"),
                    Color.white, paper ? .5f : 1f, 0, tile, clip: name == "WG_Banner", twoSided: cloth || paper);
            }
            // simple authored materials
            void Simple(string name, Action<Material> setup) { var m = NewOrLoad(name, out bool created); mats[name] = m; if (created) setup(m); }
            Simple("WG_Rubber", m => SetupLit(m, null, null, null, new Color(.045f, .045f, .045f), .32f, 0, 1));
            Simple("WG_InteriorDark", m => SetupLit(m, null, null, null, new Color(.035f, .036f, .03f), .15f, 0, 1));
            Simple("WG_Solar", m => SetupLit(m, null, null, null, new Color(.05f, .07f, .12f), .88f, .3f, 1));
            Simple("WG_FlagRed", m => SetupLit(m, null, null, null, new Color(.52f, .09f, .06f), .2f, 0, 1, twoSided: true));
            Simple("WG_Collider", m => SetupLit(m, null, null, null, Color.magenta, 0, 0, 1));
            Simple("WG_CyanGlow", m => SetupEmissive(m, new Color(.30f, .85f, .88f), 3.2f));
            Simple("WG_AmberLens", m => SetupEmissive(m, new Color(1f, .55f, .12f), 4f));
            Simple("WG_LampLens", m => SetupEmissive(m, new Color(1f, .9f, .75f), 5f));
            // Poly Haven props
            var recs = JObject.Parse(File.ReadAllText(Root + "Props/Textures/materials.json"));
            foreach (var p in recs.Properties())
            {
                var m = NewOrLoad(p.Name, out bool created); mats[p.Name] = m;
                if (!created) continue;
                var r = (JObject)p.Value; string T(string k) => r[k] != null ? Root + "Props/Textures/" + (string)r[k] : null;
                var f = r["baseColorFactor"].ToObject<float[]>();
                bool glass = p.Name.Contains("glass") || (bool)r["transmission"];
                if (glass) { SetupTransparent(m, new Color(.6f, .65f, .62f, .35f)); continue; }
                bool bulb = p.Name.Contains("bulb");
                SetupLit(m, T("baseMap") != null ? Tex(T("baseMap")) : null, T("normalMap") != null ? Tex(T("normalMap")) : null, T("maskMap") != null ? Tex(T("maskMap")) : null,
                    new Color(f[0], f[1], f[2], f[3]), 1, (float)r["metallicFactor"], 1, clip: (string)r["alphaMode"] == "MASK", twoSided: (bool)r["doubleSided"]);
                if (bulb) SetupEmissive(m, new Color(1f, .88f, .7f), 4f);
            }
            AssetDatabase.SaveAssets();
            return mats;
        }

        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m)) return m;
            var trimmed = System.Text.RegularExpressions.Regex.Replace(name, @"\.\d+$", "");
            return mats.TryGetValue(trimmed, out m) ? m : null;
        }

        public static void BuildPrefabs(Dictionary<string, Material> mats)
        {
            Directory.CreateDirectory(PrefabDir);
            var missing = new HashSet<string>();
            foreach (var dir in new[] { "Structures", "Props" })
            foreach (var glb in Directory.GetFiles(Root + dir, "*.glb"))
            {
                var path = glb.Replace('\\', '/'); var name = Path.GetFileNameWithoutExtension(path);
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (!model) { Debug.LogWarning("West Gate: not imported " + path); continue; }
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
                        r.sharedMaterials = slots;
                        var mt = System.Text.RegularExpressions.Regex.Match(r.name, @"_LOD(\d)$");
                        if (mt.Success) { int k = int.Parse(mt.Groups[1].Value); if (!lod.ContainsKey(k)) lod[k] = new List<Renderer>(); lod[k].Add(r); }
                        var size = r.bounds.size.magnitude;
                        r.shadowCastingMode = size < .45f ? ShadowCastingMode.Off : ShadowCastingMode.On;
                    }
                    if (lod.Count > 1)
                    {
                        var group = root.AddComponent<LODGroup>();
                        var size = lod[0].Select(r => r.bounds.size.magnitude).Max();
                        float[] cut = size > 3 ? new[] { .30f, .10f, .02f } : size > 1 ? new[] { .22f, .06f, .012f } : new[] { .12f, .035f, .008f };
                        var levels = lod.Values.Select((rs, i) => new LOD(cut[Math.Min(i, cut.Length - 1)] * (i == lod.Count - 1 ? .5f : 1), rs.ToArray())).ToArray();
                        group.SetLODs(levels); group.RecalculateBounds(); group.fadeMode = LODFadeMode.None;
                    }
                    bool hasCol = root.GetComponentsInChildren<Collider>(true).Any();
                    if (!hasCol && dir == "Props")
                    {
                        var rs = (lod.Count > 0 ? lod[0].ToArray() : inst.GetComponentsInChildren<Renderer>()).Where(r => r.enabled).ToArray();
                        if (rs.Length > 0)
                        {
                            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                            if (b.size.y > .35f || b.size.x > .6f || b.size.z > .6f)
                            { var c = root.AddComponent<BoxCollider>(); c.center = root.transform.InverseTransformPoint(b.center); c.size = b.size; }
                        }
                    }
                    foreach (var t in root.GetComponentsInChildren<Transform>(true))
                        GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                    PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + name + ".prefab");
                }
                finally { UnityEngine.Object.DestroyImmediate(root); }
            }
            if (missing.Count > 0) Debug.LogWarning("West Gate: unmapped materials: " + string.Join(", ", missing));
        }

        // ------------------------------------------------------------------ inside approach: wreck gantry
        static readonly string[] WreckVisuals = { "PROP_wreck_beam_a", "PROP_wreck_beam_b", "PROP_wreck_crossbeam", "PROP_wreck_severed_foot", "PROP_wreck_severed_foot.001",
            "PROP_wreck_bolt_plate", "PROP_wreck_bolt_plate.001", "PROP_wreck_bolt_plate.002", "PROP_wreck_bolt_plate.003" };

        /// The collapsed gantry framing the gate from inside Ward was flat-coloured boxes. Its beams become riveted
        /// I-sections in the textured rust material at the same transforms; colliders (COL_*) are untouched and the
        /// original visuals stay in AuthoredWorld, inactive, for rollback. Render chunks are rebuilt through the
        /// normal source-edit workflow.
        [MenuItem("Athen Hill/Outer Berms/West Gate: upgrade wreck gantry")]
        public static void UpgradeWreckGantry()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (EditorApplication.isPlaying || scene.path != ScenePath) throw new Exception("Open the saved scene in Edit mode");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks)) throw new Exception("Rebuild and save existing source edits first.");
            var root = GameObject.Find("Outer Berms/" + OutpostName + "/Gate").transform;
            if (root.Find("Wreck gantry")) throw new Exception("Wreck gantry already upgraded; edit the saved objects.");
            var world = GameObject.Find("AuthoredWorld").transform;
            var mat = NewOrLoad("WG_WreckRust", out bool created);
            if (created) SetupLit(mat, Tex(Root + "Textures/WG_RustSteel_BaseMap.jpg"), Tex(Root + "Textures/WG_RustSteel_Normal.jpg"), Tex(Root + "Textures/WG_RustSteel_Mask.png"), new Color(.86f, .74f, .66f), 1, 0, 1f / 1.4f);
            var parent = new GameObject("Wreck gantry").transform; parent.SetParent(root, false);
            chunks.ShowSources(true);
            var made = new List<string>();
            foreach (var n in WreckVisuals)
            {
                var src = world.Find(n); if (!src) continue;
                var mf = src.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh) continue;
                var b = mf.sharedMesh.bounds;
                bool beam = n.Contains("beam");
                var mesh = beam ? IBeamMesh(b) : BoxMesh(b);
                mesh.name = "Wreck " + n.Replace("PROP_wreck_", "");
                var path = Root + "Structures/Wreck_" + n.Replace("PROP_wreck_", "").Replace(".", "_") + ".asset";
                var old = AssetDatabase.LoadAssetAtPath<Mesh>(path); if (old) AssetDatabase.DeleteAsset(path);
                AssetDatabase.CreateAsset(mesh, path);
                var go = new GameObject(n.Replace("PROP_wreck_", "Wreck "), typeof(MeshFilter), typeof(MeshRenderer));
                go.transform.SetParent(parent, false); go.transform.SetPositionAndRotation(src.position, src.rotation); go.transform.localScale = src.lossyScale;
                go.GetComponent<MeshFilter>().sharedMesh = mesh; go.GetComponent<MeshRenderer>().sharedMaterial = mat; go.isStatic = true;
                src.gameObject.SetActive(false); made.Add(n);
            }
            StaticRenderChunksEditor.Rebuild(chunks);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            File.WriteAllText(Evidence + "wreck-gantry.json", JsonConvert.SerializeObject(new { replacedVisuals = made, collidersUntouched = true, material = MatDir + "WG_WreckRust.mat" }, Formatting.Indented));
        }

        static void AddBox(List<Vector3> P, List<Vector3> N, List<Vector2> UV, List<int> I, Vector3 c, Vector3 s)
        {
            var h = s / 2;
            foreach (var (n, u, v) in new[] { (Vector3.right, Vector3.forward, Vector3.up), (Vector3.left, Vector3.back, Vector3.up), (Vector3.up, Vector3.right, Vector3.forward), (Vector3.down, Vector3.right, Vector3.back), (Vector3.forward, Vector3.left, Vector3.up), (Vector3.back, Vector3.right, Vector3.up) })
            {
                int i0 = P.Count; var fc = c + Vector3.Scale(n, h); var hu = Vector3.Scale(u, h).magnitude; var hv = Vector3.Scale(v, h).magnitude;
                foreach (var (a, bb) in new[] { (-1, -1), (1, -1), (1, 1), (-1, 1) })
                {
                    var p = fc + u * hu * a + v * hv * bb; P.Add(p); N.Add(n);
                    UV.Add(new Vector2(Vector3.Dot(p, u), Vector3.Dot(p, v)));
                }
                I.AddRange(new[] { i0, i0 + 2, i0 + 1, i0, i0 + 3, i0 + 2 });
            }
        }

        static Mesh FromLists(List<Vector3> P, List<Vector3> N, List<Vector2> UV, List<int> I)
        {
            var m = new Mesh(); m.SetVertices(P); m.SetNormals(N); m.SetUVs(0, UV); m.SetTriangles(I, 0); m.RecalculateTangents(); m.RecalculateBounds(); return m;
        }

        static Mesh BoxMesh(Bounds b)
        {
            var P = new List<Vector3>(); var N = new List<Vector3>(); var UV = new List<Vector2>(); var I = new List<int>();
            AddBox(P, N, UV, I, b.center, b.size); return FromLists(P, N, UV, I);
        }

        /// I-section filling the source box: length on its longest axis, flanges across the next axis, a torn web
        /// stub and bolted splice plates every 2.5 m.
        static Mesh IBeamMesh(Bounds b)
        {
            var P = new List<Vector3>(); var N = new List<Vector3>(); var UV = new List<Vector2>(); var I = new List<int>();
            var s = b.size; int L = s.x >= s.y && s.x >= s.z ? 0 : s.y >= s.z ? 1 : 2;
            int D = L == 0 ? (s.y >= s.z ? 1 : 2) : L == 1 ? (s.x >= s.z ? 0 : 2) : (s.x >= s.y ? 0 : 1);
            int W = 3 - L - D;
            Vector3 Ax(int k) => k == 0 ? Vector3.right : k == 1 ? Vector3.up : Vector3.forward;
            float len = s[L], depth = s[D], width = s[W] * .92f, tf = Mathf.Min(.06f, depth * .08f), tw = Mathf.Min(.04f, width * .06f);
            Vector3 Size(float l, float d, float w) { var v = Vector3.zero; v[L] = l; v[D] = d; v[W] = w; return v; }
            foreach (var sign in new[] { -1, 1 })
                AddBox(P, N, UV, I, b.center + Ax(D) * sign * (depth / 2 - tf / 2) - Ax(L) * .12f * (sign > 0 ? 1 : 0), Size(len - (sign > 0 ? .24f : 0), tf, width));
            AddBox(P, N, UV, I, b.center, Size(len, depth - 2 * tf, tw));
            for (float t = -len / 2 + 1.25f; t < len / 2 - .5f; t += 2.5f)
                foreach (var sign in new[] { -1, 1 })
                    AddBox(P, N, UV, I, b.center + Ax(L) * t + Ax(W) * sign * (tw / 2 + .012f), Size(.34f, depth - 2 * tf - .04f, .024f));
            return FromLists(P, N, UV, I);
        }

        // ------------------------------------------------------------------ scene
        static MeshCollider ground;
        static float GroundY(float x, float z)
        {
            if (x > -60.02f) return 0;
            return ground.Raycast(new Ray(new Vector3(x, 60, z), Vector3.down), out var h, 200) ? h.point.y : 0;
        }
        static float GroundMin(float x, float z, float r)
        {
            float m = GroundY(x, z);
            for (int i = 0; i < 12; i++) { float a = i * Mathf.PI / 6; m = Mathf.Min(m, GroundY(x + Mathf.Cos(a) * r, z + Mathf.Sin(a) * r)); }
            return m - .04f;
        }
        static float ResolveY(JToken y, float x, float z, float r)
        {
            if (y.Type == JTokenType.Float || y.Type == JTokenType.Integer) return (float)y;
            var s = (string)y;
            if (s == "ground-min") return GroundMin(x, z, Mathf.Max(r, .3f));
            if (s.StartsWith("ground")) return GroundY(x, z) + (s.Length > 6 ? float.Parse(s.Substring(6), System.Globalization.CultureInfo.InvariantCulture) : 0);
            throw new Exception("Bad y " + s);
        }

        [MenuItem("Athen Hill/Outer Berms/West Gate: install outpost")]
        public static void InstallMenu() => Install(false);

        /// Authoring iteration: removes only this pass's own root and re-installs from layout.json.
        public static void Reinstall() => Install(true);

        static void Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) throw new Exception("Open the saved Athen Hill scene first");
            var berms = GameObject.Find("Outer Berms").transform;
            var existing = berms.Find(OutpostName);
            if (existing && !replace) throw new Exception("West Gate outpost already installed; edit the saved objects instead.");
            Directory.CreateDirectory(Evidence);
            if (!existing) File.Copy(ScenePath, Evidence + "scene-before-west-gate.unity", true);
            Transform keptWreck = null;
            if (existing)
            {
                keptWreck = existing.Find("Gate/Wreck gantry");               // chunk-coupled; survives a reinstall
                if (keptWreck) keptWreck.SetParent(null, true);
                UnityEngine.Object.DestroyImmediate(existing.gameObject);
                var oldVis = GameObject.Find("Outer Berms/Warden post/Warden arms locker/Arms locker visual");
                if (oldVis) UnityEngine.Object.DestroyImmediate(oldVis);
            }
            var layout = JObject.Parse(File.ReadAllText(Layout));
            ground = GameObject.Find("Outer Berms/Berms ground").GetComponent<MeshCollider>();
            var record = new Dictionary<string, object>();

            GroundPad(record);
            Physics.SyncTransforms();
            var root = new GameObject(OutpostName).transform; root.SetParent(berms, false);
            var groups = new Dictionary<string, Transform>();
            Transform Group(string n) { if (!groups.TryGetValue(n, out var g)) { g = new GameObject(n).transform; g.SetParent(root, false); groups[n] = g; } return g; }

            int placed = 0; var missingPrefabs = new List<string>();
            foreach (JObject it in layout["items"])
            {
                var prefabName = Path.GetFileName((string)it["prefab"]);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabDir + prefabName + ".prefab");
                if (!prefab) { missingPrefabs.Add(prefabName); continue; }
                float x = (float)it["x"], z = (float)it["z"], r = (float)it["r"];
                float y = ResolveY(it["y"], x, z, r);
                var g = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                g.name = (string)it["name"]; g.transform.SetParent(Group((string)it["group"]), false);
                g.transform.SetPositionAndRotation(new Vector3(x, y, z), Quaternion.Euler(0, (float)it["yaw"], 0));
                g.transform.localScale = Vector3.one * (float)it["scale"];
                if (!(bool)it["collider"]) foreach (var c in g.GetComponentsInChildren<Collider>(true)) c.enabled = false;
                placed++;
            }
            record["placed"] = placed; record["missingPrefabs"] = missingPrefabs;
            if (keptWreck) keptWreck.SetParent(Group("Gate"), true);

            BuildApron(Group("Gate"), (JObject)layout["anchors"]["apron"], record);
            MoveGameplay((JObject)layout["anchors"], record);
            RetireOldVisuals(record);
            AddLights(root, record);
            Decals(root, (JArray)layout["anchors"]["decals"], record);
            GroundMaterial(record);
            WardenKit(record);
            Cameras(root);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            File.WriteAllText(Evidence + "install.json", JsonConvert.SerializeObject(record, Formatting.Indented));
            Debug.Log("West Gate outpost installed: " + JsonConvert.SerializeObject(record));
        }

        /// Lower the berm mound under the container footprint so the post sits level (vertex edit on the pass's own ground mesh).
        static void GroundPad(Dictionary<string, object> record)
        {
            var mf = ground.GetComponent<MeshFilter>(); var mesh = mf.sharedMesh;
            var v = mesh.vertices; int changed = 0;
            for (int i = 0; i < v.Length; i++)
            {
                var w = ground.transform.TransformPoint(v[i]);
                if (w.x < -68.0f && w.x > -75.4f && w.z < -4.2f && w.z > -7.6f && w.y > -1.52f)
                { w.y = -1.52f; v[i] = ground.transform.InverseTransformPoint(w); changed++; }
            }
            if (changed > 0)
            {
                var backup = Evidence + "BermsGround-before-pad.asset";
                if (!File.Exists(backup)) File.Copy(AssetDatabase.GetAssetPath(mesh), backup);
                mesh.vertices = v; mesh.RecalculateNormals(); mesh.RecalculateBounds(); EditorUtility.SetDirty(mesh);
                ground.sharedMesh = null; ground.sharedMesh = mesh;
            }
            record["groundPadVertices"] = changed;
        }

        /// Concrete ramp apron from the gate threshold down to the basin floor, 6 cm proud of the ground,
        /// with a chamfered skirt and a broken, eroded outer (west) edge.
        static void BuildApron(Transform parent, JObject a, Dictionary<string, object> record)
        {
            float x0 = (float)a["x0"], x1 = (float)a["x1"], z0 = (float)a["z0"], z1 = (float)a["z1"];
            const float step = .25f; int nx = Mathf.CeilToInt((x1 - x0) / step) + 1, nz = Mathf.CeilToInt((z1 - z0) / step) + 1;
            var P = new List<Vector3>(); var UV = new List<Vector2>(); var I = new List<int>(); var C = new List<Color>();
            var idx = new int[nx, nz];
            float Edge(float z) => x0 + .9f * Mathf.PerlinNoise(z * .45f, 3.1f) + .35f * Mathf.PerlinNoise(z * 1.7f, 7.7f); // eroded west edge
            for (int i = 0; i < nx; i++)
            for (int j = 0; j < nz; j++)
            {
                float x = Mathf.Min(x1, x0 + i * step), z = Mathf.Min(z1, z0 + j * step);
                bool inside = x >= Edge(z);
                float edgeD = Mathf.Min(Mathf.Min(z - z0, z1 - z), x - Edge(z));
                float lift = inside ? Mathf.Lerp(-.06f, .06f, Mathf.Clamp01(edgeD / .18f)) : -.08f;
                float y = GroundY(x, z) + lift;
                idx[i, j] = P.Count; P.Add(new Vector3(x, y, z)); UV.Add(new Vector2(x, z)); C.Add(inside ? Color.white : new Color(1, 1, 1, 0));
            }
            for (int i = 0; i < nx - 1; i++)
            for (int j = 0; j < nz - 1; j++)
            {
                int p00 = idx[i, j], p10 = idx[i + 1, j], p01 = idx[i, j + 1], p11 = idx[i + 1, j + 1];
                if (C[p00].a + C[p10].a + C[p01].a + C[p11].a < 2) continue; // drop quads beyond the broken edge
                I.AddRange(new[] { p00, p01, p10, p10, p01, p11 });
            }
            var mesh = new Mesh { name = "WestGateApron", indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(P); mesh.SetUVs(0, UV); mesh.SetTriangles(I, 0); mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
            var path = Root + "Structures/WestGateApron.asset";
            var old = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (old) { old.Clear(); EditorUtility.CopySerialized(mesh, old); mesh = old; } else AssetDatabase.CreateAsset(mesh, path);
            var go = new GameObject("Concrete apron", typeof(MeshFilter), typeof(MeshRenderer), typeof(MeshCollider));
            go.transform.SetParent(parent, false); go.isStatic = true;
            go.GetComponent<MeshFilter>().sharedMesh = mesh; go.GetComponent<MeshCollider>().sharedMesh = mesh;
            var apronMat = NewOrLoad("WG_ApronConcrete", out bool created);
            if (created) SetupLit(apronMat, Tex(Root + "Textures/WG_Concrete_BaseMap.jpg"), Tex(Root + "Textures/WG_Concrete_Normal.jpg"), Tex(Root + "Textures/WG_Concrete_Mask.png"), new Color(.96f, .93f, .88f), .9f, 0, 1f / 4.5f);
            go.GetComponent<MeshRenderer>().sharedMaterial = apronMat;
            record["apronTriangles"] = I.Count / 3;
        }

        static void MoveGameplay(JObject a, Dictionary<string, object> record)
        {
            Vector3 At(JObject o) => new Vector3((float)o["x"], GroundY((float)o["x"], (float)o["z"]), (float)o["z"]);
            Quaternion Yaw(JObject o) => Quaternion.Euler(0, (float)o["yaw"], 0);
            var ossa = GameObject.Find("Outer Berms/Warden post/Warden Ossa").transform;
            ossa.SetPositionAndRotation(At((JObject)a["ossa"]), Yaw((JObject)a["ossa"]));
            var rell = GameObject.Find("Outer Berms/Warden post/West Gate checkpoint/Warden Rell").transform;
            rell.SetPositionAndRotation(At((JObject)a["rell"]), Yaw((JObject)a["rell"]));
            var locker = GameObject.Find("Outer Berms/Warden post/Warden arms locker").transform;
            locker.SetPositionAndRotation(At((JObject)a["locker"]), Yaw((JObject)a["locker"]));
            var lamp = locker.GetComponentInChildren<Light>(true);
            if (lamp) { lamp.transform.localPosition = new Vector3(-.32f, 2.25f, .1f); lamp.range = 2.6f; lamp.intensity = .9f; }
            var board = GameObject.Find("Outer Berms/Warden post/West Gate checkpoint/Checkpoint field briefing").transform;
            board.SetPositionAndRotation(At((JObject)a["board"]), Yaw((JObject)a["board"]));
            var reset = GameObject.Find("Outer Berms/Warden post/West Gate checkpoint/Range reset control").transform;
            reset.SetPositionAndRotation(At((JObject)a["range_reset"]), Yaw((JObject)a["range_reset"]));
            var respawn = GameObject.Find("Outer Berms/Warden post/Respawn point").transform;
            respawn.SetPositionAndRotation(At((JObject)a["respawn"]), Yaw((JObject)a["respawn"]));
            var marks = GameObject.Find("Landmarks").transform;
            foreach (var p in ((JObject)a["landmarks"]).Properties())
            {
                var xz = p.Value.ToObject<float[]>(); var t = marks.Find(p.Name);
                if (!t) { t = new GameObject(p.Name).transform; t.SetParent(marks, true); }
                t.position = new Vector3(xz[0], GroundY(xz[0], xz[1]) + .1f, xz[1]);
            }
            // Dialogue: point the player at the new post (IDs and branches unchanged).
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>();
            var od = ossa.GetComponent<NpcAgent>().definition;
            foreach (var n in od.nodes)
            {
                if (n.id == "greeting") n.text = "Ossa. West Gate watch. Nobody walks the Berms unarmed. The ARMS LOCKER is under the canopy at the post, left of my issue window; the cyan light on top marks it. Rell keeps the return lane clear.";
                if (n.id == "locker") n.text = "The green steel cabinet under the shade canopy, next to the crates, with ARMS stencilled on the door and a cyan beacon on top. Walk up to it and press E. Press 7 to draw the pistol outside the walls; it runs on nano charge. The range is across the lane, past the barriers.";
            }
            EditorUtility.SetDirty(od);
            var rd = rell.GetComponent<NpcAgent>().definition;
            foreach (var n in rd.nodes)
                if (n.id == "greeting") n.text = "Rell. I'm watching the return lane. Check in with Ossa at the post down the ramp, collect your pistol from the marked locker under the canopy, then try the range across the lane. Keep this gap clear; it is your way back to Ward.";
            EditorUtility.SetDirty(rd);
            var tutorial = UnityEngine.Object.FindAnyObjectByType<BermsTutorial>();
            tutorial.lineStart = "New scavenger? Nobody walks the Berms unarmed. I'm Ossa, on West Gate watch. Take the scrap pistol from the ARMS LOCKER under the canopy at my post; the cyan light marks it. Then use the range across the lane.";
            tutorial.briefingWarden = ossa; EditorUtility.SetDirty(tutorial);
            var notice = board.GetComponent<CheckpointNotice>();
            notice.message = "WEST GATE FIELD BRIEFING: Check in with Warden Ossa at the post. Draw the scrap pistol from the ARMS LOCKER under the canopy (cyan light), then knock down the three range plates across the lane. Feral cargo droids and inspection drones patrol the old service road; their cluster nests at the machine depot to the south. The aquifer machine inside Ward is friendly. Keep the return lane clear.";
            EditorUtility.SetDirty(notice);
            record["moved"] = new[] { "Warden Ossa", "Warden Rell", "Warden arms locker", "Checkpoint field briefing", "Range reset control", "Respawn point" };
        }

        static void RetireOldVisuals(Dictionary<string, object> record)
        {
            var off = new List<string>();
            void Off(string path) { var g = GameObject.Find(path); if (g && g.activeSelf) { g.SetActive(false); off.Add(path); } }
            const string cp = "Outer Berms/Warden post/West Gate checkpoint/";
            Off(cp + "Warden watch booth"); Off(cp + "Checkpoint groundcover"); Off(cp + "Warden training range sign");
            foreach (var b in GameObject.Find(cp.TrimEnd('/')).transform.Cast<Transform>().Where(t => t.name == "Checkpoint barrier").ToArray())
                if (b.gameObject.activeSelf) { b.gameObject.SetActive(false); off.Add(cp + "Checkpoint barrier"); }
            Off(cp + "Checkpoint field briefing/Field briefing text"); Off(cp + "Checkpoint field briefing/Field briefing backing");
            Off(cp + "Range reset control/Range control pedestal"); Off(cp + "Range reset control/Range reset lettering");
            foreach (var n in new[] { 1, 2, 4, 5, 9, 10 }) Off(cp + "Checkpoint foliage/Drought shrub " + n);
            Off("Outer Berms/Warden post/Warden arms locker/Arms issue cabinet");
            Off("Outer Berms/Warden post/Post generator"); Off("Outer Berms/Warden post/Post litter"); Off("Outer Berms/Warden post/Post crate");
            Off("Outer Berms/Service road");
            // the new cabinet visual lives under the interaction root so its prompt/collider stay together
            var locker = GameObject.Find("Outer Berms/Warden post/Warden arms locker").transform;
            var vis = GameObject.Find("Outer Berms/" + OutpostName + "/Outpost/Arms locker visual");
            if (vis) { vis.transform.SetParent(locker, true); vis.transform.localPosition = Vector3.zero; vis.transform.localRotation = Quaternion.identity; }
            record["retired"] = off;
        }

        static Light AddLight(Transform parent, string name, Vector3 pos, Vector3 target, LightType type, Color color, float intensity, float range, float angle, bool shadows)
        {
            var l = new GameObject(name, typeof(Light)).GetComponent<Light>();
            l.transform.SetParent(parent, true); l.transform.position = pos;
            if (target != Vector3.zero) l.transform.rotation = Quaternion.LookRotation(target - pos);
            l.type = type; l.color = color; l.intensity = intensity; l.range = range;
            if (type == LightType.Spot) { l.spotAngle = angle; l.innerSpotAngle = angle * .55f; }
            l.shadows = shadows ? LightShadows.Soft : LightShadows.None; l.shadowStrength = .85f; l.shadowBias = .04f; l.shadowNormalBias = .3f;
            return l;
        }

        static void AddLights(Transform root, Dictionary<string, object> record)
        {
            var lights = new GameObject("Practical lights").transform; lights.SetParent(root, false);
            var warm = new Color(1f, .82f, .62f); var sodium = new Color(1f, .74f, .45f);
            var list = new List<Light>
            {
                AddLight(lights, "Gate flood west (apron)", new Vector3(-60.4f, 6.45f, 1f), new Vector3(-64.5f, -.8f, 1f), LightType.Spot, warm, 9f, 22, 95, true),
                AddLight(lights, "Gate flood east (threshold)", new Vector3(-57.6f, 6.45f, 1f), new Vector3(-55f, 0, 1f), LightType.Spot, warm, 5f, 14, 85, false),
                AddLight(lights, "Gate beacon", new Vector3(-59f, 7.05f, 4.9f), Vector3.zero, LightType.Point, new Color(1f, .55f, .12f), 1.4f, 4, 0, false),
                AddLight(lights, "Light tower flood", new Vector3(-68.2f, 7.1f, 5.25f), new Vector3(-71f, -1.6f, -2.2f), LightType.Spot, new Color(.92f, .95f, 1f), 14f, 30, 78, true),
                AddLight(lights, "Issue window lamp", new Vector3(-70.53f, .75f, -4.35f), new Vector3(-70.53f, -1.6f, -3.1f), LightType.Spot, sodium, 4.5f, 8, 110, false),
                AddLight(lights, "Post interior", new Vector3(-69.9f, .95f, -5.9f), Vector3.zero, LightType.Point, warm, 1.6f, 4.5f, 0, false),
                AddLight(lights, "Post door lamp", new Vector3(-68.3f, .75f, -6.6f), new Vector3(-67.4f, -1.6f, -5.6f), LightType.Spot, sodium, 3.2f, 7, 100, false),
                AddLight(lights, "Briefing board lamp", new Vector3(-63.9f, 1.3f, -4.0f), new Vector3(-64.3f, -.2f, -4.4f), LightType.Spot, warm, 1.4f, 4, 80, false),
            };
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            circuit.practicalLights = circuit.practicalLights.Where(l => l && !l.transform.IsChildOf(root)).Concat(list).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !l.transform.IsChildOf(root)).Concat(list).ToArray();
            var emissive = new[] { "WG_AmberLens", "WG_LampLens" }.Select(n => AssetDatabase.LoadAssetAtPath<Material>(MatDir + n + ".mat")).Where(m => m).ToArray();
            circuit.emissiveMaterials = circuit.emissiveMaterials.Where(m => m && !emissive.Contains(m)).Concat(emissive).ToArray();
            EditorUtility.SetDirty(circuit);
            record["lights"] = list.Select(l => l.name).ToArray();
        }

        /// Screen-space decals (the accepted "Ward weathering decals" feature): tyre tracks, oil, drifted sand, grime.
        static void Decals(Transform root, JArray list, Dictionary<string, object> record)
        {
            var template = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat");
            if (!template || !template.HasProperty("Base_Map")) throw new Exception("Decal template material missing");
            var parent = new GameObject("Decals").transform; parent.SetParent(root, false);
            var mats = new Dictionary<string, Material>(); int n = 0;
            foreach (JObject d in list)
            {
                var kind = (string)d["kind"];
                if (!mats.TryGetValue(kind, out var m))
                {
                    var path = MatDir + kind + ".mat";
                    m = AssetDatabase.LoadAssetAtPath<Material>(path);
                    if (!m) { m = new Material(template) { name = kind }; m.SetTexture("Base_Map", Tex(Root + "Textures/" + kind + ".png")); if (m.HasProperty("Normal_Blend")) m.SetFloat("Normal_Blend", 0); AssetDatabase.CreateAsset(m, path); }
                    mats[kind] = m;
                }
                float x = (float)d["x"], z = (float)d["z"];
                var dir = new Vector3((float)d["dx"], 0, (float)d["dz"]).normalized;
                var go = new GameObject(kind.Replace("WG_Decal", "Decal ") + " " + (++n));
                go.transform.SetParent(parent, false);
                var proj = d["proj"];
                var p = go.AddComponent<UnityEngine.Rendering.Universal.DecalProjector>();
                if (proj.Type == JTokenType.String)
                {
                    float gy = GroundY(x, z);
                    go.transform.SetPositionAndRotation(new Vector3(x, gy + .2f, z), Quaternion.LookRotation(Vector3.down, dir));
                    p.size = new Vector3((float)d["w"], (float)d["l"], (float)d["depth"]); p.pivot = new Vector3(0, 0, (float)d["depth"] * .5f - .2f);
                    p.startAngleFade = 60; p.endAngleFade = 85;
                }
                else
                {
                    var f = proj.ToObject<float[]>(); var fwd = new Vector3(f[0], f[1], f[2]).normalized;
                    float y = d["y"].Type == JTokenType.String ? GroundY(x, z) : (float)d["y"];
                    go.transform.SetPositionAndRotation(new Vector3(x, y, z), Quaternion.LookRotation(fwd, Vector3.up));
                    p.size = new Vector3((float)d["w"], (float)d["l"], (float)d["depth"]); p.pivot = Vector3.zero;
                    p.startAngleFade = 50; p.endAngleFade = 75;
                }
                p.material = m; p.fadeFactor = (float)d["fade"]; p.drawDistance = 60; p.fadeScale = .85f;
            }
            record["decals"] = n;
        }

        static void GroundMaterial(Dictionary<string, object> record)
        {
            var r = ground.GetComponent<MeshRenderer>();
            var basin = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/Terrain/SandstoneBasin.mat");
            var path = Root + "Ground/BermsGround.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m)
            {
                m = new Material(Shader.Find("Athen Hill/Berms Ground")) { name = "BermsGround" };
                m.SetTexture("_Splat", Tex(Root + "Ground/BermsGroundSplat.png"));
                m.SetTexture("_AlbedoHeight", AssetDatabase.LoadAssetAtPath<Texture2DArray>(Root + "Ground/BermsGroundLayers_AH.png"));
                m.SetTexture("_NormalRoughAO", AssetDatabase.LoadAssetAtPath<Texture2DArray>(Root + "Ground/BermsGroundLayers_NRA.png"));
                m.SetVector("_SplatRect", new Vector4(-104, -54, 1f / 44, 1f / 102));
                m.SetVector("_LayerSize", new Vector4(4, 1.8f, 2.5f, 4));
                m.SetColor("_Tint0", new Color(1.0f, .95f, .9f)); m.SetColor("_Tint1", new Color(1.05f, .98f, .9f));
                m.SetColor("_Tint2", new Color(.95f, .92f, .88f)); m.SetColor("_Tint3", new Color(1.05f, 1.0f, .92f));
                m.SetFloat("_Saturation", .72f);
                if (basin)
                {
                    m.SetTexture("_Geology", basin.GetTexture("_Geology")); m.SetTexture("_RockTex", basin.GetTexture("_RockTex"));
                    m.SetColor("_RockTint", basin.GetColor("_RockTint")); m.SetColor("_Haze", basin.GetColor("_Haze")); m.SetFloat("_HazeDensity", basin.GetFloat("_HazeDensity"));
                    m.SetFloat("_RockScale", basin.GetFloat("_DetailScale"));
                }
                AssetDatabase.CreateAsset(m, path);
            }
            record["groundMaterialBefore"] = r.sharedMaterial ? AssetDatabase.GetAssetPath(r.sharedMaterial) : null;
            r.sharedMaterial = m; r.receiveShadows = true;
            record["groundMaterial"] = path;
        }

        /// Wardens on the gate get a field-worn, sand-dusted armour variant (city guards keep the original).
        static void WardenKit(Dictionary<string, object> record)
        {
            var made = new List<string>();
            foreach (var path in new[] { "Outer Berms/Warden post/Warden Ossa", "Outer Berms/Warden post/West Gate checkpoint/Warden Rell" })
            {
                var g = GameObject.Find(path); if (!g) continue;
                foreach (var r in g.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                {
                    var slots = r.sharedMaterials;
                    for (int i = 0; i < slots.Length; i++)
                    {
                        var src = slots[i]; if (!src || src.name.StartsWith("WG_Warden")) continue;
                        var vpath = MatDir + "WG_Warden_" + src.name.Replace(" ", "_") + ".mat";
                        var v = AssetDatabase.LoadAssetAtPath<Material>(vpath);
                        if (!v)
                        {
                            v = new Material(src) { name = "WG_Warden_" + src.name };
                            ApplyWardenKit(v);
                            AssetDatabase.CreateAsset(v, vpath); made.Add(vpath);
                        }
                        slots[i] = v;
                    }
                    r.sharedMaterials = slots;
                }
            }
            record["wardenMaterials"] = made;
        }

        /// The supplied guard material re-uses its albedo as a full-strength emissive map and is fully metallic,
        /// so it glows white in any light. The Warden variant is lit normally: no self-emission, painted
        /// (dielectric) plate, field-worn khaki tint. The four city guards keep the original material.
        static void ApplyWardenKit(Material v)
        {
            if (v.HasProperty("baseColorFactor")) v.SetColor("baseColorFactor", new Color(.74f, .68f, .56f, 1));
            else if (v.HasProperty("_BaseColor")) v.SetColor("_BaseColor", new Color(.74f, .68f, .56f, 1));
            if (v.HasProperty("emissiveFactor")) v.SetColor("emissiveFactor", Color.black);
            if (v.HasProperty("metallicFactor")) v.SetFloat("metallicFactor", .12f);
            if (v.HasProperty("roughnessFactor")) v.SetFloat("roughnessFactor", .62f);
            EditorUtility.SetDirty(v);
        }

        static void Cameras(Transform root)
        {
            var cams = new GameObject("West Gate review cameras").transform; cams.SetParent(root, false);
            void Cam(string name, Vector3 pos, Vector3 target, float fov)
            {
                var existing = GameObject.Find(name);
                var g = existing && !existing.transform.IsChildOf(root) ? existing : new GameObject(name, typeof(Camera));
                if (!existing || existing.transform.IsChildOf(root)) g.transform.SetParent(cams, true);
                g.transform.position = pos; g.transform.LookAt(target);
                var c = g.GetComponent<Camera>(); c.enabled = false; c.fieldOfView = fov; c.farClipPlane = 650; c.nearClipPlane = .05f;
            }
            Cam("cam_westgate_inside", new Vector3(-45.5f, 1.7f, 5.2f), new Vector3(-60, 2.2f, 1), 62);
            Cam("cam_westgate_mouth", new Vector3(-56.5f, 1.65f, 1.2f), new Vector3(-68, -.4f, -.5f), 62);
            Cam("cam_westgate_post", new Vector3(-65.2f, .1f, 1.2f), new Vector3(-71.5f, -.6f, -4.6f), 60);
            Cam("cam_westgate_issue", new Vector3(-70.2f, .05f, -1.6f), new Vector3(-71.9f, -.5f, -4.5f), 58);
            Cam("cam_westgate_range", new Vector3(-63.6f, .35f, 2.6f), new Vector3(-72f, -.9f, 10.5f), 62);
            Cam("cam_westgate_return", new Vector3(-74.5f, .2f, 1.8f), new Vector3(-59, 2.4f, 1), 60);
            Cam("cam_westgate_aerial", new Vector3(-52f, 13f, -9f), new Vector3(-67, -1, 1), 55);
            // existing checkpoint cameras reframed on the new post (names kept for the native checks)
            Cam("cam_checkpoint_player", new Vector3(-57.2f, 1.7f, 3.4f), new Vector3(-68.5f, -.8f, -2.5f), 62);
            Cam("cam_checkpoint_locker", new Vector3(-71.0f, -.05f, -2.3f), new Vector3(-72.3f, -.5f, -4.4f), 60);
        }
    }
}
