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
    /// 1 October 2026: Ward hydroponics greenhouses. Carl: "green houses look bare." The two retrofit quonsets
    /// ("Ward district retrofit/Hydroponics bays", art/ward_retrofit_20260926) held bare trays with a sparse scatter of
    /// desert succulents under flat pink slabs, behind a polycarbonate skin that cast a full opaque shadow over the
    /// interior. This pass makes them the working heart of Ward's food supply (lore.md):
    ///
    ///  * interior fit-out per bay (rack legs, NFT channels, feed manifolds and returns, slim LED bars on the light clock
    ///    and always-on propagation lights, vine gutters with rockwool slabs, strings and top wires, fans, misting line,
    ///    floor, duckboards, a harvest trolley) and twelve crop sections (lettuces, chard, herbs, seedlings, microgreens,
    ///    cordon tomatoes and runner beans), each a three-level LODGroup, placed at their authored pivots;
    ///  * the skin: a copy of the polycarbonate with a dust/condensation film and no shadow pass, so sun reaches the crops;
    ///  * the working yard (layout.json): harvest by the doors, potting bench, nursery under shade cloth with drying herbs,
    ///    growers' rest bench (stools and bench carry NPC sit points), nutrient totes and dosing trolley, compost, herbs in
    ///    the planters between the bays; grime/scuff decals; four night-only grow-glow lights on the city light circuit.
    ///
    /// Retired (inactive, kept for rollback): "Hydroponics bays Detail" (replaced by a filtered copy without the 93k
    /// triangles of succulents: planters and tank fittings kept) and "Hydroponics bays Glow". Collision is unchanged: the
    /// quonsets stay solid. Sources: art/hydroponics_20261001 (author_hydroponics.py, hyprops.py, prepare_textures.py,
    /// layout.py). Menu: Athen Hill → Hydroponics → Build assets, Install (one time), Verify saved scene.
    /// </summary>
    public static class HydroponicsPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/Hydroponics/";
        const string TexDir = Root + "Textures/";
        const string MatDir = Root + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/Hydroponics/";
        const string SdPrefabDir = "Assets/AthenHill/Prefabs/StreetDressing/";
        const string RetrofitGlb = "Assets/AthenHill/Art/WardRetrofit/WardRetrofit.glb";
        const string Evidence = "../evidence/hydroponics/20261001/";
        const string LayoutPath = "../../art/hydroponics_20261001/layout.json";
        const string DecalMaterial = "Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat";
        public const string RootName = "Ward hydroponics";
        const string CamRootName = "Hydroponics review cameras";
        const string BaysPath = "Ward district retrofit/Hydroponics bays";
        const string DetailPath = BaysPath + "/Hydroponics bays Detail";
        const string GlowPath = BaysPath + "/Hydroponics bays Glow";
        const string StructurePath = BaysPath + "/Hydroponics bays Structure";
        const string SkinSource = "Retro_Polycarbonate";
        static readonly string[] RetiredSubmeshMaterials = { "crystalline_iceplant", "cheiridopsis_succulent" };

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        static Transform Find(UnityEngine.SceneManagement.Scene scene, string path) =>
            scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).FirstOrDefault(t => PathOf(t) == path);

        static JObject Manifest() => JObject.Parse(File.ReadAllText(Root + "hy-manifest.json"));
        static JObject Layout() => JObject.Parse(File.ReadAllText(LayoutPath));

        // ================================================================== build
        [MenuItem("Athen Hill/Hydroponics/Build assets")]
        public static string BuildAssets()
        {
            AssetDatabase.Refresh();
            ConfigureTextures();
            var man = Manifest();
            foreach (var s in man["sections"]) foreach (var g in s["glb"]) AssetDatabase.ImportAsset(Root + (string)g, ImportAssetOptions.ForceUpdate);
            foreach (var p in ((JObject)man["props"]).Properties()) foreach (var g in p.Value["glb"]) AssetDatabase.ImportAsset(Root + (string)g, ImportAssetOptions.ForceUpdate);
            var mats = BuildMaterials();
            Directory.CreateDirectory(PrefabDir); Directory.CreateDirectory(PrefabDir + "Interior");
            var missing = new HashSet<string>();
            int interior = 0, props = 0, composites = 0;
            foreach (var s in man["sections"]) { BuildSectionPrefab((JObject)s, mats, missing); interior++; }
            foreach (var p in ((JObject)man["props"]).Properties())
                if (!p.Name.StartsWith("fill_")) { BuildPropPrefab(p.Name, (JObject)p.Value, mats, missing); props++; }
            foreach (var c in ((JObject)Layout()["composites"]).Properties())
            { BuildComposite(c.Name, (string)c.Value[0], (string)c.Value[1], (JObject)man["props"][(string)c.Value[1]], mats, missing); composites++; }
            AssetDatabase.SaveAssets();
            var report = new { interior, props, composites, materials = mats.Count, unmapped = missing.OrderBy(x => x).ToArray() };
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(report, Formatting.Indented);
            File.WriteAllText(Evidence + "build-assets.json", json);
            return json;
        }

        static void ConfigureTextures()
        {
            foreach (var g in AssetDatabase.FindAssets("t:Texture", new[] { TexDir.TrimEnd('/') }))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                var file = Path.GetFileNameWithoutExtension(path);
                bool normal = file.Contains("nor_gl") || file.EndsWith("_Normal");
                bool mask = file.EndsWith("_mask");
                bool alpha = file == "HY_CropAtlas" || file == "HY_ShadeCloth" || file == "HY_PolyFilm";
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !normal && !mask;
                ti.alphaSource = mask || alpha ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                ti.alphaIsTransparency = alpha && file != "HY_PolyFilm";
                ti.mipMapsPreserveCoverage = file == "HY_CropAtlas" || file == "HY_ShadeCloth";
                if (ti.mipMapsPreserveCoverage) ti.alphaTestReferenceValue = .45f;
                ti.maxTextureSize = 2048;
                ti.mipmapEnabled = true;
                ti.streamingMipmaps = true;
                ti.anisoLevel = 8;
                ti.wrapMode = file.StartsWith("HY_Crop") ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
            }
        }

        static Texture2D T(JToken t) => t == null ? null : AssetDatabase.LoadAssetAtPath<Texture2D>((string)t);
        static Color C(JToken t, Color d) => t == null ? d : new Color((float)t[0], (float)t[1], (float)t[2]);

        static Dictionary<string, Material> BuildMaterials()
        {
            Directory.CreateDirectory(MatDir);
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var cover = Shader.Find("Athen Hill/Ward Ground Cover") ?? throw new Exception("Ward Ground Cover shader missing");
            var mats = new Dictionary<string, Material>();
            foreach (var p in JObject.Parse(File.ReadAllText(TexDir + "materials.json")).Properties())
            {
                var s = (JObject)p.Value;
                var kind = (string)s["shader"] ?? "lit";
                var shader = kind == "groundcover" ? cover : lit;
                var assetName = p.Name.StartsWith("HY_") ? p.Name : "HY_" + p.Name;
                var path = MatDir + assetName + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!m) { m = new Material(shader) { name = assetName }; AssetDatabase.CreateAsset(m, path); }
                else if (m.shader != shader) m.shader = shader;
                var baseMap = T(s["base"]);
                m.SetTexture("_BaseMap", baseMap);
                var col = C(s["tint"] ?? s["color"], Color.white);
                m.SetColor("_BaseColor", col);
                var normal = T(s["normal"]);
                m.SetTexture("_BumpMap", normal); m.SetFloat("_BumpScale", s["normalScale"] != null ? (float)s["normalScale"] : 1f);
                if (normal) m.EnableKeyword("_NORMALMAP"); else m.DisableKeyword("_NORMALMAP");
                var mask = T(s["mask"]);
                if (mask)
                {
                    m.SetTexture("_MetallicGlossMap", mask); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                    m.SetTexture("_OcclusionMap", mask); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1f);
                }
                else
                {
                    m.SetTexture("_MetallicGlossMap", null); m.DisableKeyword("_METALLICSPECGLOSSMAP");
                    m.SetTexture("_OcclusionMap", null); m.DisableKeyword("_OCCLUSIONMAP");
                    m.SetFloat("_Metallic", s["metallic"] != null ? (float)s["metallic"] : 0f);
                }
                m.SetFloat("_Smoothness", s["smoothness"] != null ? (float)s["smoothness"] : .3f);
                m.SetFloat("_SmoothnessTextureChannel", 0);
                m.SetTextureScale("_BaseMap", Vector2.one);
                bool two = s["doubleSided"] != null && (bool)s["doubleSided"];
                bool clip = s["alphaClip"] != null && (bool)s["alphaClip"];
                // reset blend state, then apply the surface type
                m.SetFloat("_Surface", 0); m.SetFloat("_Blend", 0); m.SetFloat("_ZWrite", 1);
                m.SetFloat("_SrcBlend", 1); m.SetFloat("_DstBlend", 0); m.SetFloat("_SrcBlendAlpha", 1); m.SetFloat("_DstBlendAlpha", 0);
                m.DisableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.DisableKeyword("_ALPHAPREMULTIPLY_ON"); m.SetShaderPassEnabled("ShadowCaster", true);
                m.SetOverrideTag("RenderType", "Opaque"); m.renderQueue = (int)RenderQueue.Geometry;
                m.SetFloat("_AlphaClip", 0); m.DisableKeyword("_ALPHATEST_ON");
                if (clip)
                {
                    m.SetFloat("_AlphaClip", 1); m.SetFloat("_Cutoff", s["cutoff"] != null ? (float)s["cutoff"] : .45f); m.EnableKeyword("_ALPHATEST_ON");
                    m.SetOverrideTag("RenderType", "TransparentCutout"); m.renderQueue = (int)RenderQueue.AlphaTest;
                    two = true;
                }
                if (kind == "transparent")
                {
                    // alpha blend as URP's material GUI sets it: preserve-specular lifts the alpha multiply into the shader
                    bool keepSpec = s["preserveSpecular"] != null && (bool)s["preserveSpecular"];
                    m.SetFloat("_Surface", 1); m.SetFloat("_Blend", 0); m.SetFloat("_ZWrite", 0);
                    m.SetFloat("_SrcBlend", (float)(keepSpec ? BlendMode.One : BlendMode.SrcAlpha)); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                    m.SetFloat("_SrcBlendAlpha", 1); m.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
                    m.SetFloat("_BlendModePreserveSpecular", keepSpec ? 1 : 0); m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    if (keepSpec) m.EnableKeyword("_ALPHAPREMULTIPLY_ON"); else m.DisableKeyword("_ALPHAPREMULTIPLY_ON");
                    // the moon and sun put a hard hotspot on the curved skin (native review, 1 Oct): no direct specular
                    // highlights, sky reflections kept
                    bool highlights = s["specularHighlights"] == null || (bool)s["specularHighlights"];
                    m.SetFloat("_SpecularHighlights", highlights ? 1 : 0);
                    if (highlights) m.DisableKeyword("_SPECULARHIGHLIGHTS_OFF"); else m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
                    m.SetOverrideTag("RenderType", "Transparent"); m.renderQueue = (int)RenderQueue.Transparent;
                    // polycarbonate passes most of the light: no opaque shadow over the crops
                    if (s["castShadows"] != null && !(bool)s["castShadows"]) m.SetShaderPassEnabled("ShadowCaster", false);
                }
                if (kind == "groundcover")
                {   // still air under the skin: no sway (the fans are slow); leaves transmit light
                    m.SetFloat("_WardWindStrength", 0); m.SetFloat("_WardLeafFlutter", 0);
                    m.SetFloat("_WardTranslucency", s["translucency"] != null ? (float)s["translucency"] : .25f);
                    m.SetFloat("_WardIndirectTranslucency", s["indirectTranslucency"] != null ? (float)s["indirectTranslucency"] : .1f);
                }
                if (s["emission"] != null)
                {
                    float k = s["emissionIntensity"] != null ? (float)s["emissionIntensity"] : 1f;
                    m.SetColor("_EmissionColor", C(s["emission"], Color.black) * k); m.EnableKeyword("_EMISSION");
                    m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                }
                else { m.SetColor("_EmissionColor", Color.black); m.DisableKeyword("_EMISSION"); }
                m.SetFloat("_Cull", two ? 0 : 2); m.doubleSidedGI = two;
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
                mats[p.Name] = m;
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

        static List<Renderer> Instance(string glb, Transform parent, string name, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb) ?? throw new Exception("Model not imported: " + glb);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            inst.transform.SetParent(parent, false);
            inst.name = name;
            var rs = new List<Renderer>();
            foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
            {
                var slots = r.sharedMaterials;
                for (int i = 0; i < slots.Length; i++)
                {
                    var m = slots[i] ? Lookup(mats, slots[i].name) : null;
                    if (m) slots[i] = m; else missing.Add(Path.GetFileNameWithoutExtension(glb) + ":" + (slots[i] ? slots[i].name : "null"));
                }
                r.sharedMaterials = slots;
                r.receiveShadows = true;
                if (r is MeshRenderer mr) { mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; mr.receiveGI = ReceiveGI.LightProbes; }
                rs.Add(r);
            }
            return rs;
        }

        static void SetStatic(GameObject root)
        {
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
        }

        /// LOD switch heights. Crop sections are 4.6 m long: full plants within ~9 m, reduced heads to ~25 m, one cross
        /// card per plant beyond (PC preset LOD bias 2). The fit-outs (15 m) keep their small parts within ~30 m.
        internal static float[] SectionCuts = { .85f, .3f, .06f };
        internal static float[] FitoutCuts = { .8f, .03f };

        static float[] PropCuts(float max, int levels)
        {
            float[] c = max < .5f ? new[] { .22f, .07f, .025f } : max < 1.2f ? new[] { .3f, .08f, .02f } : new[] { .4f, .1f, .015f };
            return c.Take(levels).ToArray();
        }

        public static string SectionPrefabPath(string name) => PrefabDir + "Interior/" + name + ".prefab";
        public static string PrefabPath(string id) => id.StartsWith("SD_") ? SdPrefabDir + id + ".prefab" : PrefabDir + id + ".prefab";

        static void BuildSectionPrefab(JObject s, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var name = (string)s["name"];
            var root = new GameObject(name);
            try
            {
                var glbs = s["glb"].Select(x => (string)x).ToArray();
                bool crops = (string)s["kind"] == "crops";
                var cuts = crops ? SectionCuts : FitoutCuts;
                var levels = new List<LOD>();
                var lodRenderers = new List<List<Renderer>>();
                for (int lod = 0; lod < glbs.Length; lod++)
                {
                    var rs = Instance(Root + glbs[lod], root.transform, "LOD" + lod, mats, missing);
                    // crops: sun reaches the trays through the skin, so close up the plants shade them -- through a
                    // shadow-only copy of the reduced (LOD1) heads in the LOD0 level; the LOD1 and LOD2 levels cast none.
                    // The fit-out casts from its LOD0 only (legs, channels, bars within ~30 m).
                    // (measured 1 Oct: shadow-casting LOD1 crops cost ~1 ms at the yard's wide view; within ~9 m only)
                    foreach (var r in rs)
                        r.shadowCastingMode = crops ? ShadowCastingMode.Off : (lod == 0 ? ShadowCastingMode.On : ShadowCastingMode.Off);
                    lodRenderers.Add(rs);
                }
                if (crops && lodRenderers.Count > 1)
                {
                    var proxyRoot = new GameObject("Shadow proxy (LOD1 crops)"); proxyRoot.transform.SetParent(root.transform, false);
                    foreach (var r1 in lodRenderers[1])
                    {
                        var go = new GameObject(r1.name + " shadow");
                        go.transform.SetParent(proxyRoot.transform, false);
                        go.transform.SetPositionAndRotation(r1.transform.position, r1.transform.rotation); go.transform.localScale = r1.transform.lossyScale;
                        go.AddComponent<MeshFilter>().sharedMesh = r1.GetComponent<MeshFilter>().sharedMesh;
                        var pr = go.AddComponent<MeshRenderer>(); pr.sharedMaterials = r1.sharedMaterials;
                        pr.shadowCastingMode = ShadowCastingMode.ShadowsOnly; pr.receiveShadows = false;
                        lodRenderers[0].Add(pr);
                    }
                }
                for (int lod = 0; lod < lodRenderers.Count; lod++)
                    levels.Add(new LOD(cuts[Math.Min(lod, cuts.Length - 1)], lodRenderers[lod].ToArray()));
                var g = root.AddComponent<LODGroup>(); g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                SetStatic(root);
                PrefabUtility.SaveAsPrefabAsset(root, SectionPrefabPath(name));
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        static void BuildPropPrefab(string id, JObject rec, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var root = new GameObject("HY_" + id);
            try
            {
                var glbs = rec["glb"].Select(x => (string)x).ToArray();
                var size = rec["size"].Select(x => (float)x).ToArray();
                var cuts = PropCuts(size.Max(), glbs.Length);
                int shadowLods = rec["shadowLods"] != null ? (int)rec["shadowLods"] : 1;
                var levels = new List<LOD>();
                for (int lod = 0; lod < glbs.Length; lod++)
                {
                    var rs = Instance(Root + glbs[lod], root.transform, "LOD" + lod, mats, missing);
                    bool small = size.Max() < .3f;
                    foreach (var r in rs) r.shadowCastingMode = !small && lod < shadowLods ? ShadowCastingMode.On : ShadowCastingMode.Off;
                    levels.Add(new LOD(cuts[lod], rs.ToArray()));
                }
                var g = root.AddComponent<LODGroup>(); g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                foreach (var c in rec["colliders"] ?? new JArray())
                {
                    var b = root.AddComponent<BoxCollider>();
                    b.center = new Vector3((float)c["center"][0], (float)c["center"][1], (float)c["center"][2]);
                    b.size = new Vector3((float)c["size"][0], (float)c["size"][1], (float)c["size"][2]);
                }
                foreach (var sp in rec["sitPoints"] ?? new JArray())
                {
                    var go = new GameObject("NPC sit point"); go.transform.SetParent(root.transform, false);
                    go.transform.localPosition = new Vector3((float)sp[0], (float)sp[1], (float)sp[2]);
                }
                SetStatic(root);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath("HY_" + id));
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        /// A street-kit container (nested prefab: its scan, LODs and collider) with a produce fill in its own LODGroup.
        static void BuildComposite(string id, string container, string fill, JObject rec, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var root = new GameObject(id);
            try
            {
                var c = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(container)) ?? throw new Exception("Street kit prefab missing: " + container);
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(c);
                inst.transform.SetParent(root.transform, false); inst.name = container;
                var f = new GameObject("Produce"); f.transform.SetParent(root.transform, false);
                var glbs = rec["glb"].Select(x => (string)x).ToArray();
                var cuts = new[] { .2f, .07f, .025f };
                var levels = new List<LOD>();
                for (int lod = 0; lod < glbs.Length; lod++)
                {
                    var rs = Instance(Root + glbs[lod], f.transform, "LOD" + lod, mats, missing);
                    foreach (var r in rs) r.shadowCastingMode = ShadowCastingMode.Off;
                    levels.Add(new LOD(cuts[lod], rs.ToArray()));
                }
                var g = f.AddComponent<LODGroup>(); g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                SetStatic(root);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(id));
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        // ================================================================== install
        [MenuItem("Athen Hill/Hydroponics/Install (one time)")]
        public static string Install() => Install(false);

        /// Authoring iteration only: replaces the installed root (retired objects stay retired; the first rollback copy of
        /// the scene is kept).
        public static string Reinstall() => Install(true);

        static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (existing && !replace) throw new Exception("The hydroponics pass is already installed; edit the instances in place.");
            var circuit = UnityEngine.Object.FindFirstObjectByType<CityLightCircuit>();
            if (existing) UnityEngine.Object.DestroyImmediate(existing);
            if (circuit) PruneCircuit(circuit);
            Directory.CreateDirectory(Evidence + "rollback");
            var rollback = Evidence + "rollback/before-hydroponics.unity";
            if (!File.Exists(rollback)) File.Copy(ScenePath, rollback, true);
            var record = new Dictionary<string, object>();
            var layout = Layout(); var man = Manifest();

            var detail = Find(scene, DetailPath) ?? throw new Exception(DetailPath + " missing");
            var glow = Find(scene, GlowPath) ?? throw new Exception(GlowPath + " missing");
            var structure = Find(scene, StructurePath) ?? throw new Exception(StructurePath + " missing");

            var root = new GameObject(RootName);
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);

            // ---- retrofit detail: a filtered copy (planters, tank bands, ladders) replaces the succulent-filled original
            var kept = KeptDetail(detail, root.transform, out var keptInfo);
            record["detailKept"] = keptInfo;
            foreach (var t in new[] { detail, glow })
            {
                Undo.RecordObject(t.gameObject, "Retire retrofit hydroponics part");
                t.gameObject.SetActive(false);
                PrefabUtility.RecordPrefabInstancePropertyModifications(t.gameObject);
            }
            record["retired"] = new[] { DetailPath, GlowPath };

            // ---- skin: polycarbonate copy with film and no shadow pass
            record["skin"] = SetSkin(structure.GetComponent<MeshRenderer>(), true);

            // ---- interior
            var interior = new GameObject("Interior").transform; interior.SetParent(root.transform, false);
            int sections = 0;
            foreach (var s in man["sections"])
            {
                var name = (string)s["name"];
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(SectionPrefabPath(name)) ?? throw new Exception("Build assets first: " + name);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.transform.SetParent(interior, false);
                go.transform.position = new Vector3((float)s["pivot"][0], (float)s["pivot"][1], (float)s["pivot"][2]);
                sections++;
            }
            record["interiorSections"] = sections;

            // ---- yard
            var yard = new GameObject("Yard").transform; yard.SetParent(root.transform, false);
            var groups = new Dictionary<string, Transform>();
            var placed = new Dictionary<string, int>(); var missing = new HashSet<string>();
            foreach (var p in layout["placements"])
            {
                var vig = (string)p["vignette"]; var prop = (string)p["prop"];
                if (!groups.TryGetValue(vig, out var g)) { g = new GameObject(vig).transform; g.SetParent(yard, false); groups[vig] = g; }
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(prop));
                if (!prefab) { missing.Add(prop); continue; }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.transform.SetParent(g, false);
                var pos = p["pos"]; var e = p["euler"];
                go.transform.SetPositionAndRotation(new Vector3((float)pos[0], (float)pos[1], (float)pos[2]), Quaternion.Euler((float)e[0], (float)e[1], (float)e[2]));
                var sc = p["scale"] != null ? (float)p["scale"] : 1f;
                if (Mathf.Abs(sc - 1f) > 1e-3) go.transform.localScale = Vector3.one * sc;
                go.name = prop.Substring(3);
                placed[prop] = placed.TryGetValue(prop, out var n) ? n + 1 : 1;
            }
            foreach (var g in groups.Values)
            {
                var kids = g.Cast<Transform>().ToArray(); if (kids.Length == 0) continue;
                var centre = kids.Aggregate(Vector3.zero, (a, t) => a + t.position) / kids.Length; centre.y = 0;
                foreach (var k in kids) k.SetParent(null, true);
                g.position = centre;
                foreach (var k in kids) k.SetParent(g, true);
            }
            record["placed"] = placed.Values.Sum();
            record["byProp"] = placed.OrderBy(kv => kv.Key).ToDictionary(kv => kv.Key, kv => kv.Value);
            record["missingPrefabs"] = missing.ToArray();
            record["decals"] = AddDecals(layout, groups);

            // ---- night grow glow and the LED material on the light clock
            var lights = new List<Light>();
            var lroot = new GameObject("Grow glow lights").transform; lroot.SetParent(root.transform, false);
            foreach (var l in layout["lights"])
            {
                var go = new GameObject((string)l["name"]); go.transform.SetParent(lroot, false);
                go.transform.position = new Vector3((float)l["pos"][0], (float)l["pos"][1], (float)l["pos"][2]);
                var light = go.AddComponent<Light>();
                light.type = LightType.Point; light.shadows = LightShadows.None;
                light.color = C(l["color"], Color.white); light.intensity = (float)l["intensity"]; light.range = (float)l["range"];
                light.renderMode = LightRenderMode.Auto;
                lights.Add(light);
            }
            if (circuit)
            {
                circuit.practicalLights = circuit.practicalLights.Concat(lights).ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Concat(lights).ToArray();
                var led = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "HY_LED.mat");
                if (led && !circuit.emissiveMaterials.Contains(led)) circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { led }).ToArray();
                EditorUtility.SetDirty(circuit);
            }
            record["lights"] = lights.Count;
            record["circuit"] = circuit ? circuit.name : null;

            AddReviewCameras(scene);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) record["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + (replace ? "reinstall.json" : "install.json"), json);
            return json;
        }

        static void PruneCircuit(CityLightCircuit circuit)
        {
            circuit.practicalLights = circuit.practicalLights.Where(l => l).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l).ToArray();
            EditorUtility.SetDirty(circuit);
        }

        /// The retrofit's merged detail mesh without the succulent/ice-plant submeshes (tray scatter and planter fill),
        /// as a 32-bit mesh asset with the unused vertices dropped, drawn at the original's transform and cull distance.
        static object KeptDetail(Transform detail, Transform parent, out object info)
        {
            var mf = detail.GetComponent<MeshFilter>(); var mr = detail.GetComponent<MeshRenderer>();
            var src = mf.sharedMesh;
            var mats = mr.sharedMaterials;
            var keep = Enumerable.Range(0, src.subMeshCount).Where(i => !RetiredSubmeshMaterials.Any(n => mats[i] && mats[i].name.StartsWith(n))).ToArray();
            var vs = src.vertices; var ns = src.normals; var ts = src.tangents;
            var uvs = new List<Vector4>[8];
            for (int ch = 0; ch < 8; ch++) { uvs[ch] = new List<Vector4>(); src.GetUVs(ch, uvs[ch]); }
            var map = new Dictionary<int, int>(); var subs = new List<int[]>();
            foreach (var i in keep)
            {
                var tri = src.GetTriangles(i, true);
                for (int k = 0; k < tri.Length; k++) { if (!map.TryGetValue(tri[k], out var v)) { v = map.Count; map[tri[k]] = v; } tri[k] = v; }
                subs.Add(tri);
            }
            var order = map.OrderBy(kv => kv.Value).Select(kv => kv.Key).ToArray();
            var m = new Mesh { name = "Hydroponics bays Detail (planters and tank fittings)", indexFormat = IndexFormat.UInt32 };
            m.SetVertices(order.Select(i => vs[i]).ToArray());
            if (ns.Length == vs.Length) m.SetNormals(order.Select(i => ns[i]).ToArray());
            if (ts.Length == vs.Length) m.SetTangents(order.Select(i => ts[i]).ToArray());
            for (int ch = 0; ch < 8; ch++) if (uvs[ch].Count == vs.Length) m.SetUVs(ch, order.Select(i => uvs[ch][i]).ToList());
            m.subMeshCount = subs.Count;
            for (int s = 0; s < subs.Count; s++) m.SetTriangles(subs[s], s, false);
            m.RecalculateBounds();
            Directory.CreateDirectory(Root + "Retrofit");
            var path = Root + "Retrofit/Hydroponics_bays_Detail_kept.asset";
            if (AssetDatabase.LoadAssetAtPath<Mesh>(path)) AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(m, path);
            var go = new GameObject("Retrofit planters and tank fittings (kept from Hydroponics bays Detail)");
            go.transform.SetParent(parent, false);
            go.transform.SetPositionAndRotation(detail.position, detail.rotation); go.transform.localScale = detail.lossyScale;
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var r = go.AddComponent<MeshRenderer>(); r.sharedMaterials = keep.Select(i => mats[i]).ToArray();
            r.shadowCastingMode = mr.shadowCastingMode; r.receiveShadows = true;
            var srcLod = detail.GetComponent<LODGroup>();
            var lod = go.AddComponent<LODGroup>();
            lod.SetLODs(new[] { new LOD(srcLod ? srcLod.GetLODs()[0].screenRelativeTransitionHeight : .03f, new Renderer[] { r }) });
            lod.fadeMode = LODFadeMode.None; lod.RecalculateBounds();
            int srcTris = Enumerable.Range(0, src.subMeshCount).Sum(i => (int)src.GetIndexCount(i) / 3);
            int keptTris = subs.Sum(t => t.Length / 3);
            info = new { asset = path, sourceTriangles = srcTris, keptTriangles = keptTris, keptMaterials = keep.Select(i => mats[i].name).ToArray(), vertices = order.Length };
            return info;
        }

        /// Swaps the structure renderer's polycarbonate slot (prefab-instance override) to the pass's skin, or back.
        static object SetSkin(MeshRenderer structure, bool on)
        {
            var mine = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "HY_Polycarbonate.mat") ?? throw new Exception("Build assets first (HY_Polycarbonate)");
            var original = AssetDatabase.LoadAllAssetsAtPath(RetrofitGlb).OfType<Material>().FirstOrDefault(m => m.name.StartsWith(SkinSource));
            var slots = structure.sharedMaterials;
            int slot = Array.FindIndex(slots, m => m && (m == mine || m.name.StartsWith(SkinSource)));
            if (slot < 0) throw new Exception("No polycarbonate slot on " + structure.name);
            if (on && original)
            {   // keep the retrofit's faces: one-sided or double-sided as authored
                var cull = original.HasProperty("_CullMode") ? original.GetFloat("_CullMode") : original.HasProperty("_Cull") ? original.GetFloat("_Cull") : 2f;
                mine.SetFloat("_Cull", cull); mine.doubleSidedGI = cull == 0; EditorUtility.SetDirty(mine);
            }
            var before = slots[slot] ? slots[slot].name : null;
            slots[slot] = on ? mine : original;
            Undo.RecordObject(structure, "Hydroponics skin");
            structure.sharedMaterials = slots;
            PrefabUtility.RecordPrefabInstancePropertyModifications(structure);
            return new { slot, before, after = slots[slot] ? slots[slot].name : null, cull = mine.GetFloat("_Cull") };
        }

        static readonly Dictionary<string, Vector2> DecalBias = new()
        {
            ["sand"] = new Vector2(.005f, .505f), ["grime"] = new Vector2(.505f, .505f), ["scuffs"] = new Vector2(.005f, .005f),
        };

        static int AddDecals(JObject layout, Dictionary<string, Transform> groups)
        {
            var decalMat = AssetDatabase.LoadAssetAtPath<Material>(DecalMaterial);
            if (!decalMat || layout["decals"] == null) return 0;
            int n = 0;
            foreach (var d in layout["decals"])
            {
                if (!groups.TryGetValue((string)d["vignette"], out var g)) continue;
                var pos = d["pos"]; var size = d["size"];
                var go = new GameObject("Ground " + (string)d["kind"]); go.transform.SetParent(g, false);
                var fwd = Quaternion.Euler(0, (float)d["yaw"], 0) * Vector3.forward;
                go.transform.SetPositionAndRotation(new Vector3((float)pos[0], (float)pos[1] + .25f, (float)pos[2]), Quaternion.LookRotation(Vector3.down, fwd));
                var proj = go.AddComponent<DecalProjector>();
                proj.material = decalMat;
                proj.size = new Vector3((float)size[0], (float)size[1], .5f);
                proj.pivot = new Vector3(0, 0, .25f);
                proj.uvScale = new Vector2(.49f, .49f); proj.uvBias = DecalBias[(string)d["kind"]];
                proj.fadeFactor = (float)d["opacity"]; proj.drawDistance = 30; proj.fadeScale = .7f;
                proj.startAngleFade = 60; proj.endAngleFade = 85;
                n++;
            }
            return n;
        }

        // ================================================================== review cameras (player height, lookbook names)
        internal static readonly (string name, Vector3 eye, Vector3 target)[] Shots =
        {
            ("cam_hy_east_yard", new Vector3(-17.4f, 1.62f, 30.6f), new Vector3(-24.5f, 1.0f, 36.2f)),
            ("cam_hy_harvest", new Vector3(-22.9f, 1.62f, 32.9f), new Vector3(-25.4f, .55f, 34.6f)),
            ("cam_hy_nursery", new Vector3(-18.2f, 1.62f, 32.6f), new Vector3(-21.8f, .85f, 35.4f)),
            ("cam_hy_potting", new Vector3(-23.3f, 1.62f, 24.4f), new Vector3(-26.0f, .9f, 26.6f)),
            ("cam_hy_south_lane", new Vector3(-27.6f, 1.62f, 22.6f), new Vector3(-38.0f, 1.0f, 25.3f)),
            ("cam_hy_skin_close", new Vector3(-32.9f, 1.62f, 23.3f), new Vector3(-34.7f, 1.0f, 27.2f)),
            ("cam_hy_gap", new Vector3(-24.9f, 1.62f, 32.5f), new Vector3(-36.0f, 1.0f, 32.5f)),
            ("cam_hy_compost", new Vector3(-36.0f, 1.62f, 40.7f), new Vector3(-41.6f, .55f, 41.3f)),
            ("cam_hy_pump", new Vector3(-48.6f, 1.62f, 28.2f), new Vector3(-43.6f, .9f, 33.0f)),
            ("cam_hy_wide", new Vector3(-15.2f, 2.6f, 38.6f), new Vector3(-30.0f, 1.0f, 30.8f)),
        };

        static void AddReviewCameras(UnityEngine.SceneManagement.Scene scene)
        {
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
            foreach (var (name, eye, target) in Shots)
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(eye, Quaternion.LookRotation(target - eye, Vector3.up));
                var k = go.AddComponent<Camera>(); k.enabled = false; k.fieldOfView = 60; k.nearClipPlane = .05f;
            }
        }

        /// Adds only the review cameras to the saved scene (for matched native "before" captures).
        public static string CamerasOnly()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "review cameras: " + Shots.Length;
        }

        // ================================================================== verify / toggle / probe / capture
        [MenuItem("Athen Hill/Hydroponics/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            if (root)
            {
                var groups = root.GetComponentsInChildren<LODGroup>(true);
                r["lodGroups"] = groups.Length;
                var interior = root.transform.Find("Interior");
                var yard = root.transform.Find("Yard");
                r["interiorSections"] = interior ? interior.childCount : 0;
                r["interiorPrefabLinked"] = interior ? interior.Cast<Transform>().Count(t => PrefabUtility.IsPartOfPrefabInstance(t.gameObject)) : 0;
                r["yardInstances"] = yard ? yard.Cast<Transform>().Sum(g => g.Cast<Transform>().Count(t => PrefabUtility.IsPartOfPrefabInstance(t.gameObject))) : 0;
                r["missingMaterials"] = root.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(m => !m));
                long lod0 = 0, all = 0;
                foreach (var g in groups)
                {
                    var lods = g.GetLODs();
                    for (int i = 0; i < lods.Length; i++)
                        foreach (var rr in lods[i].renderers)
                            if (rr && rr.shadowCastingMode != ShadowCastingMode.ShadowsOnly && rr.TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh)
                                for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) { var t = mf.sharedMesh.GetIndexCount(s) / 3; all += t; if (i == 0) lod0 += t; }
                }
                r["lod0Triangles"] = lod0; r["allLodTriangles"] = all;
                r["interiorLod0Triangles"] = interior ? interior.GetComponentsInChildren<LODGroup>(true).Sum(g => g.GetLODs()[0].renderers.Where(x => x && x.shadowCastingMode != ShadowCastingMode.ShadowsOnly && x.GetComponent<MeshFilter>()).Sum(x => (long)x.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3)) : 0;
                r["colliders"] = root.GetComponentsInChildren<Collider>(true).Length;
                r["sitPoints"] = root.GetComponentsInChildren<Transform>(true).Count(t => t.name == "NPC sit point");
                r["decals"] = root.GetComponentsInChildren<DecalProjector>(true).Length;
                r["lights"] = root.GetComponentsInChildren<Light>(true).Length;
                r["shadowProxies"] = root.GetComponentsInChildren<MeshRenderer>(true).Count(x => x.shadowCastingMode == ShadowCastingMode.ShadowsOnly);
            }
            r["retiredStillActive"] = new[] { DetailPath, GlowPath }.Where(p => { var t = Find(scene, p); return t && t.gameObject.activeSelf; }).ToArray();
            var structure = Find(scene, StructurePath);
            r["skin"] = structure ? structure.GetComponent<MeshRenderer>().sharedMaterials.Select(m => m ? m.name : "null").FirstOrDefault(n => n.Contains("Polycarbonate")) : null;
            var circuit = UnityEngine.Object.FindFirstObjectByType<CityLightCircuit>();
            if (circuit && root)
            {
                var mine = root.GetComponentsInChildren<Light>(true);
                r["circuitLights"] = mine.Count(l => circuit.practicalLights.Contains(l));
                r["circuitNightOnly"] = mine.Count(l => circuit.nightOnlyLights.Contains(l));
                r["circuitLed"] = circuit.emissiveMaterials.Any(m => m && m.name == "HY_LED");
                r["circuitNullLights"] = circuit.practicalLights.Count(l => !l);
            }
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            r["reviewCameras"] = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName)?.transform.childCount ?? 0;
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        /// Measurement only (A/B frame time): the whole pass off (root inactive, retrofit detail, glow and skin restored)
        /// or on, in the saved scene.
        public static string Toggle(bool on)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            root.SetActive(on);
            foreach (var p in new[] { DetailPath, GlowPath })
            {
                var t = Find(scene, p); t.gameObject.SetActive(!on); PrefabUtility.RecordPrefabInstancePropertyModifications(t.gameObject);
            }
            SetSkin(Find(scene, StructurePath).GetComponent<MeshRenderer>(), on);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "hydroponics pass " + (on ? "on" : "off");
        }

        /// A/B timing builds (development, OpenGL), one build per Editor run (memory caps). The three October workstreams
        /// share the saved scene and the default build folder, so both arms come from ONE snapshot of the saved scene:
        /// "on" writes two scene copies (pass on / pass off with the retrofit Detail, Glow and skin restored) and builds the
        /// on copy to Builds/hy-ab-on; "off" builds the off copy to Builds/hy-ab-off and deletes both copies. The saved scene
        /// itself is not changed (same pattern as PerimeterWallsPass).
        const string AbOnCopy = "Assets/AthenHill/Scenes/__hy_ab_on.unity", AbOffCopy = "Assets/AthenHill/Scenes/__hy_ab_off.unity";

        static string AbBuild(string arm)
        {
            string src;
            if (arm == "noyard" || arm == "nointerior")
            {   // attribution arm from the same snapshot pattern (its own copy, built and deleted in one run)
                var scene = EditorSceneManager.OpenScene(ScenePath);
                var root = scene.GetRootGameObjects().First(g => g.name == RootName);
                root.transform.Find(arm == "noyard" ? "Yard" : "Interior").gameObject.SetActive(false);
                src = "Assets/AthenHill/Scenes/__hy_ab_" + arm + ".unity";
                if (!EditorSceneManager.SaveScene(scene, src, true)) throw new Exception("could not write " + src);
                try
                {
                    PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneLinux64, false);
                    PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneLinux64, new[] { GraphicsDeviceType.OpenGLCore });
                    var rep = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                    {
                        scenes = new[] { src }, locationPathName = "Builds/hy-ab-" + arm + "/AthenHill.x86_64",
                        target = BuildTarget.StandaloneLinux64, options = BuildOptions.Development,
                    });
                    if (rep.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("A/B build failed: " + arm);
                    return "hy-ab-" + arm + " " + rep.summary.totalTime.TotalSeconds.ToString("0") + " s";
                }
                finally { AssetDatabase.DeleteAsset(src); }
            }
            if (arm == "on")
            {
                var scene = EditorSceneManager.OpenScene(ScenePath);
                var root = scene.GetRootGameObjects().First(g => g.name == RootName);
                var detail = Find(scene, DetailPath); var glow = Find(scene, GlowPath);
                var structure = Find(scene, StructurePath).GetComponent<MeshRenderer>();
                root.SetActive(true); detail.gameObject.SetActive(false); glow.gameObject.SetActive(false); SetSkin(structure, true);
                if (!EditorSceneManager.SaveScene(scene, AbOnCopy, true)) throw new Exception("could not write " + AbOnCopy);
                root.SetActive(false); detail.gameObject.SetActive(true); glow.gameObject.SetActive(true); SetSkin(structure, false);
                if (!EditorSceneManager.SaveScene(scene, AbOffCopy, true)) throw new Exception("could not write " + AbOffCopy);
                src = AbOnCopy;
            }
            else
            {
                if (!File.Exists(AbOffCopy)) throw new Exception("Run abbuild:on first (it writes the scene snapshot for both arms).");
                src = AbOffCopy;
            }
            try
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneLinux64, false);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneLinux64, new[] { GraphicsDeviceType.OpenGLCore });
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = new[] { src }, locationPathName = "Builds/hy-ab-" + arm + "/AthenHill.x86_64",
                    target = BuildTarget.StandaloneLinux64, options = BuildOptions.Development,
                });
                if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("A/B build failed: " + arm);
                return "hy-ab-" + arm + " " + report.summary.totalTime.TotalSeconds.ToString("0") + " s";
            }
            finally
            {
                if (arm == "off") { AssetDatabase.DeleteAsset(AbOnCopy); AssetDatabase.DeleteAsset(AbOffCopy); }
            }
        }

        /// Read-only: materials, shaders, shadow modes of the retrofit bays.
        public static string Probe()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var bays = Find(scene, BaysPath) ?? throw new Exception(BaysPath + " missing");
            var rows = new List<object>();
            foreach (var r in bays.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials.Select(m => m == null ? null : (object)new
                {
                    m.name, shader = m.shader.name, m.renderQueue, keywords = m.shaderKeywords,
                    cull = m.HasProperty("_CullMode") ? m.GetFloat("_CullMode") : m.HasProperty("_Cull") ? m.GetFloat("_Cull") : -1,
                    shadowPass = m.GetShaderPassEnabled("ShadowCaster"),
                }).ToArray();
                rows.Add(new { path = PathOf(r.transform), active = r.gameObject.activeInHierarchy, r.enabled, shadows = r.shadowCastingMode.ToString(), mats });
            }
            var json = JsonConvert.SerializeObject(new { lodBias = QualitySettings.lodBias, rows }, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "probe-retrofit-bays.json", json);
            return "probe: " + rows.Count + " renderers";
        }

        internal static readonly (string name, Vector3 eye, Vector3 target, float fov)[] CloseViews =
        {
            ("close_rack_b", new Vector3(-31.2f, 1.45f, 24.3f), new Vector3(-31.6f, 1.0f, 27.0f), 55f),
            ("close_vines_a_gap", new Vector3(-30.5f, 1.55f, 32.0f), new Vector3(-31.6f, 1.3f, 34.6f), 55f),
            ("close_crates", new Vector3(-24.0f, 1.62f, 33.4f), new Vector3(-25.3f, .45f, 34.4f), 50f),
            ("close_potting", new Vector3(-24.4f, 1.62f, 25.3f), new Vector3(-25.9f, .85f, 26.2f), 50f),
            ("close_nursery", new Vector3(-20.0f, 1.62f, 33.2f), new Vector3(-21.6f, .8f, 34.6f), 55f),
            ("inside_b", new Vector3(-27.4f, 1.55f, 28.3f), new Vector3(-36f, 1.0f, 28.3f), 70f),
            ("plan_overview", new Vector3(-17f, 15f, 14f), new Vector3(-33f, 0f, 33f), 55f),
        };

        /// Editor captures through a MainCamera clone: 1920x1080, no MSAA, at most six views per run (GPU memory rule,
        /// 1 Oct: batch captures must not starve the desktop's VRAM). The native lookbook is the evidence of record.
        public static string CaptureViews(string outDir, string filter = "")
        {
            EditorSceneManager.OpenScene(ScenePath);
            var views = Shots.Select(s => (s.name, s.eye, s.target, 60f)).Concat(CloseViews.Select(v => (v.name, v.eye, v.target, v.fov)))
                .Where(v => filter == "" || filter.Split('+').Any(f => v.name.Contains(f))).Take(6).ToList();
            var main = GameObject.Find("MainCamera").GetComponent<Camera>();
            var go = new GameObject("__cap") { hideFlags = HideFlags.DontSave };
            var cam = go.AddComponent<Camera>(); cam.CopyFrom(main);
            var src = main.GetComponent<UniversalAdditionalCameraData>(); var dst = go.AddComponent<UniversalAdditionalCameraData>();
            if (src) { dst.renderPostProcessing = src.renderPostProcessing; dst.antialiasing = src.antialiasing; dst.antialiasingQuality = src.antialiasingQuality; dst.renderShadows = true; dst.requiresDepthTexture = src.requiresDepthTexture; }
            cam.enabled = false; cam.nearClipPlane = .05f; cam.farClipPlane = 650;
            var rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1 };
            var tex = new Texture2D(1920, 1080, TextureFormat.RGB24, false);
            Directory.CreateDirectory(outDir);
            var done = new List<string>();
            foreach (var (name, pos, target, fov) in views)
            {
                go.transform.position = pos; go.transform.LookAt(target); cam.fieldOfView = fov; cam.targetTexture = rt;
                for (int k = 0; k < 3; k++) cam.Render();
                RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1920, 1080), 0, 0); tex.Apply();
                File.WriteAllBytes(Path.Combine(outDir, name + ".png"), tex.EncodeToPNG());
                done.Add(name);
            }
            RenderTexture.active = null; cam.targetTexture = null;
            UnityEngine.Object.DestroyImmediate(go); rt.Release(); UnityEngine.Object.DestroyImmediate(rt); UnityEngine.Object.DestroyImmediate(tex);
            return string.Join(",", done);
        }

        // ================================================================== batch
        /// -executeMethod AthenHill.Editor.HydroponicsPass.RunBatch --steps build,cameras,install,reinstall,verify,capture[:filter],toggle:on|off,probe [--out dir]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "build").Split(',');
            var outDir = Arg("--out", Evidence + "editor");
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "build" => BuildAssets(),
                        "cameras" => CamerasOnly(),
                        "install" => Install(),
                        "reinstall" => Reinstall(),
                        "verify" => Verify(),
                        "capture" => CaptureViews(outDir, parts.Length > 1 ? parts[1] : ""),
                        "toggle" => Toggle(parts[1] == "on"),
                        "probe" => Probe(),
                        "abbuild" => AbBuild(parts[1]),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("HydroponicsPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
