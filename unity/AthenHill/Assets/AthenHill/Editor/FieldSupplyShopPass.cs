using System;
using System.Collections.Generic;
using System.Globalization;
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
    /// 5 October 2026: Field Supply opens as a walk-in outfitter's shop (Carl: "Open another shop - field supply. have a
    /// choice of low tech to mid tier packs for storage upgrades. a digital magazine shelf that are basically recipes for
    /// crafting upgrades and packs. also sell med kits and nano recharges."). Gameplay and data: art/field_supply_20261005
    /// (apply_data.py, PROGRESS.md); this pass is the building, the keeper and the shop dressing.
    ///
    /// Geometry: art/field_supply_20261005/field_supply_interior.py (called by the hall district authoring script) rolls
    /// the loading shutter up and fits out the ground floor; the record (Art/WardShops/Models/field_supply.json) carries the
    /// walk-in colliders, the lamp points, the pack hooks and the room bounds. Steps:
    ///  materials  FS_* materials (the magazine screens on the cover atlas, med and nano stock, felt, canvas, webbing).
    ///  models     re-imports the Field Supply models and patches Prefabs/WardShops/FieldSupply.prefab in place (material
    ///             slots re-mapped by name with later passes' substitutions kept, LODGroup rebuilt with the interior parts,
    ///             interior renderers unshadowed on the interior light layer, walk-in colliders from the record).
    ///  packs      Prefabs/FieldSupply/FS_pack_*.prefab: the five Meshy packs (art/field_supply_20261005/packs), three LODs,
    ///             origin at the hang point (top of the back).
    ///  tamsin     Tamsin's prefab through WardNpcInstall's import and prefab steps (Meshy rig, idle_248, Torr's talk_309).
    ///  install    scene root "Field Supply interior" (re-runnable: replaces itself): InteriorLighting, pendant lamps and
    ///             glows on the interior light layer, a night-only bay spill on the Ward lighting clock, Tamsin behind the
    ///             counter, packs on the wall and stand hooks, crates and stock, an interior reflection probe, review cameras
    ///             and landmarks; wires Tamsin into GameSession.npcs; street dressing or sand left in front of the opened
    ///             bay goes inactive (never deleted).
    ///  verify     saved-scene checks and walk-path clearance -> evidence/field-supply/20261005/verify.json.
    ///  bake       (graphics) bakes the interior reflection probe.  capture:HOUR:cam+cam (graphics, at most 6 cameras).
    /// Batch: -executeMethod AthenHill.Editor.FieldSupplyShopPass.RunBatch --steps materials,models,packs,tamsin,install,verify -nographics.
    /// Rollback: art/field_supply_20261005/previous/ holds the closed shop's models and record; re-copy them, run "models",
    /// then delete the "Field Supply interior" root (and take Tamsin out of GameSession.npcs) or run "uninstall".
    /// </summary>
    public static class FieldSupplyShopPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Evidence = "../evidence/field-supply/20261005/";
        const string ModelDir = "Assets/AthenHill/Art/WardShops/Models/";
        const string PrefabPath = "Assets/AthenHill/Prefabs/WardShops/FieldSupply.prefab";
        const string ArtDir = "Assets/AthenHill/Art/FieldSupply/";
        const string MatDir = ArtDir + "Materials/";
        const string PackArt = ArtDir + "Packs/";
        const string PackPrefabs = "Assets/AthenHill/Prefabs/FieldSupply/";
        const string AtlasSource = "../../art/field_supply_20261005/covers/magazine_atlas_8bit.png";
        const string AtlasPath = ArtDir + "FS_MagazineAtlas.png";
        const string TamsinPath = "Assets/AthenHill/Data/npc_tamsin.asset";
        const string TemplateMat = "Assets/AthenHill/Art/StreetDressing/Materials/SD_field_generator.mat";
        public const string RootName = "Field Supply interior";
        public const uint InteriorLayer = 1u << 7;
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;
        const float Floor = .5f;
        public static readonly string[] Packs = { "pack_field", "pack_rucksack", "pack_frame", "pack_carrier", "pack_rig" };

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] A(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static JObject Record() => JObject.Parse(File.ReadAllText(ModelDir + "field_supply.json"));

        /// The Field Supply prefab instance in the city scene (found by its source prefab, wherever it is parented).
        static Transform Shop(UnityEngine.SceneManagement.Scene scene)
        {
            foreach (var g in scene.GetRootGameObjects())
                foreach (var t in g.GetComponentsInChildren<Transform>(true))
                    if (PrefabUtility.IsAnyPrefabInstanceRoot(t.gameObject) && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(t.gameObject) == PrefabPath)
                        return t;
            throw new Exception("Field Supply prefab instance not found in the scene");
        }

        // ------------------------------------------------------------------ materials
        static Material Mat(string name, Func<Material> make, Action<Material> setup)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            bool created = !m;
            if (created) { m = make(); m.name = name; }
            setup(m);
            if (created) AssetDatabase.CreateAsset(m, path); else EditorUtility.SetDirty(m);
            return m;
        }
        static void Lit(Material m, Color c, float smooth, float metal = 0)
        {
            m.SetColor("_BaseColor", c); m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal); m.enableInstancing = true;
        }
        static void Glow(Material m, Color baseC, Color emission, float smooth)
        {
            Lit(m, baseC, smooth);
            m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", emission);
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;   // URP drops _EMISSION on save otherwise
        }
        static void Tex(string path, bool normal, bool srgb, int max = 2048)
        {
            var ti = (TextureImporter)AssetImporter.GetAtPath(path) ?? throw new Exception("No texture " + path);
            ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            ti.sRGBTexture = srgb; ti.mipmapEnabled = true; ti.streamingMipmaps = true; ti.maxTextureSize = max;
            ti.textureCompression = TextureImporterCompression.CompressedHQ; ti.anisoLevel = 4;
            ti.SaveAndReimport();
        }
        public static Dictionary<string, Material> Materials()
        {
            Directory.CreateDirectory(ArtDir);
            if (!File.Exists(AtlasSource)) throw new Exception("Cover atlas missing: " + AtlasSource + " (art/field_supply_20261005/covers/make_atlas.sh)");
            if (!File.Exists(AtlasPath) || !File.ReadAllBytes(AtlasPath).SequenceEqual(File.ReadAllBytes(AtlasSource))) { File.Copy(AtlasSource, AtlasPath, true); AssetDatabase.ImportAsset(AtlasPath); }
            Tex(AtlasPath, false, true);
            var atlas = AssetDatabase.LoadAssetAtPath<Texture2D>(AtlasPath);
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var d = new Dictionary<string, Material>
            {
                // field slates: the covers glow softly behind glass (emission on the same atlas, a darker base)
                ["FS_Screens"] = Mat("FS_Screens", () => new Material(lit), m =>
                {
                    Glow(m, new Color(.32f, .32f, .32f), Color.white * .95f, .88f);
                    m.SetTexture("_BaseMap", atlas); m.SetTexture("_EmissionMap", atlas);
                }),
                ["FS_MedRed"] = Mat("FS_MedRed", () => new Material(lit), m => Lit(m, new Color(.52f, .07f, .05f), .42f)),
                ["FS_MedOlive"] = Mat("FS_MedOlive", () => new Material(lit), m => Lit(m, new Color(.23f, .26f, .15f), .32f)),
                ["FS_MedWhite"] = Mat("FS_MedWhite", () => new Material(lit), m => Lit(m, new Color(.84f, .83f, .78f), .48f)),
                ["FS_NanoGlow"] = Mat("FS_NanoGlow", () => new Material(lit), m => Glow(m, new Color(.25f, .75f, .85f), new Color(.2f, .85f, 1.1f) * 2.4f, .9f)),
                ["FS_Amber"] = Mat("FS_Amber", () => new Material(lit), m => Glow(m, new Color(.78f, .48f, .1f), new Color(1f, .55f, .1f) * .35f, .55f)),
                ["FS_Felt"] = Mat("FS_Felt", () => new Material(lit), m => Lit(m, new Color(.05f, .13f, .14f), .08f)),
                ["FS_Canvas"] = Mat("FS_Canvas", () => new Material(lit), m => Lit(m, new Color(.5f, .41f, .28f), .18f)),
                ["FS_Webbing"] = Mat("FS_Webbing", () => new Material(lit), m => Lit(m, new Color(.38f, .35f, .24f), .22f)),
            };
            AssetDatabase.SaveAssets();
            return d;
        }

        // ------------------------------------------------------------------ models + prefab patch
        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m)) return m;
            var trimmed = System.Text.RegularExpressions.Regex.Replace(name, @"\.\d+$", "");
            return mats.TryGetValue(trimmed, out m) ? m : null;
        }

        public static string Models()
        {
            foreach (var lod in new[] { 0, 1 }) AssetDatabase.ImportAsset(ModelDir + $"FieldSupply_LOD{lod}.glb", ImportAssetOptions.ForceUpdate);
            var mats = WardShopsPass.BuildMaterials(false);
            foreach (var kv in SalvageShopPass.Materials()) mats[kv.Key] = kv.Value;
            foreach (var kv in Materials()) mats[kv.Key] = kv.Value;
            mats["FS_CaseGlass"] = mats["WS_ClearGlass"];
            var rec = Record();
            if (rec["interior"] == null) throw new Exception("field_supply.json has no interior record: re-run the Field Supply authoring");
            var log = new List<string>();
            var root = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                var levels = new List<LOD>();
                int interior = 0, kept = 0, unmapped = 0;
                foreach (var (lod, cut) in new[] { (0, WardShopsPass.Lod0ScreenHeight), (1, .01f) })
                {
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelDir + $"FieldSupply_LOD{lod}.glb");
                    var lodRoot = root.transform.Find("LOD" + lod) ?? throw new Exception("prefab has no LOD" + lod);
                    var rs = new List<Renderer>();
                    foreach (var r in lodRoot.GetComponentsInChildren<Renderer>(true))
                    {
                        var src = model.GetComponentsInChildren<Renderer>(true).FirstOrDefault(x => x.name == r.name);
                        if (!src) { log.Add("no source for " + r.name); continue; }
                        var want = src.sharedMaterials.Select(m => m ? Lookup(mats, m.name) : null).ToArray();
                        unmapped += want.Count(m => !m);
                        if (want.Any(m => !m)) log.Add("unmapped on " + r.name + ": " + string.Join(",", src.sharedMaterials.Where((m, i) => !want[i]).Select(m => m ? m.name : "null")));
                        // keep a later pass's 1:1 substitutions (the night facade's NF_Glass_HallEast for WS_Glass)
                        var current = r.sharedMaterials;
                        string modelPath = AssetDatabase.GetAssetPath(model);
                        var extra = current.Where(m => m && !want.Contains(m) && AssetDatabase.GetAssetPath(m) != modelPath).Distinct().ToList();
                        var missing = want.Where(m => m && !current.Contains(m)).Distinct().ToList();
                        var swap = new Dictionary<Material, Material>();
                        for (int i = 0; i < Math.Min(extra.Count, missing.Count); i++) swap[missing[i]] = extra[i];
                        var slots = want.Select((m, i) => m && swap.TryGetValue(m, out var s) ? s : m ?? (i < current.Length ? current[i] : null)).ToArray();
                        kept += swap.Count;
                        r.sharedMaterials = slots;
                        if (r.name.Contains("_Interior"))
                        {
                            interior++;
                            r.shadowCastingMode = ShadowCastingMode.Off;
                            r.renderingLayerMask |= InteriorLayer;
                            r.receiveShadows = true;
                            if (r is MeshRenderer mr) { mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; mr.receiveGI = ReceiveGI.LightProbes; }
                            // ReflectionProbeStatic: a baked probe renders only these, so without it the room's probe sees
                            // through its walls to the sky (5 Oct 2026; the Salvage probe has the same gap)
                            GameObjectUtility.SetStaticEditorFlags(r.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic | StaticEditorFlags.ReflectionProbeStatic);
                        }
                        rs.Add(r);
                    }
                    levels.Add(new LOD(cut, rs.ToArray()));
                }
                var group = root.GetComponent<LODGroup>();
                group.SetLODs(levels.ToArray());
                group.RecalculateBounds();
                var cols = root.transform.Find("Colliders") ?? throw new Exception("prefab has no Colliders");
                foreach (Transform c in cols.Cast<Transform>().ToArray()) UnityEngine.Object.DestroyImmediate(c.gameObject);
                foreach (var c in rec["colliders"])
                {
                    var go = new GameObject((string)c["name"]); go.transform.SetParent(cols, false);
                    var b = go.AddComponent<BoxCollider>(); b.center = V3(c["center"]); b.size = V3(c["size"]);
                    GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
                log.Add($"prefab patched: LOD0 {levels[0].renderers.Length} / LOD1 {levels[1].renderers.Length} renderers, interior {interior}, substitutions kept {kept}, unmapped slots {unmapped}, colliders {rec["colliders"].Count()}");
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            AssetDatabase.SaveAssets();
            return string.Join("; ", log);
        }

        // ------------------------------------------------------------------ packs
        static string Find(string dir, string prefix) => Directory.GetFiles(dir, prefix + ".*").Where(f => !f.EndsWith(".meta")).Select(f => f.Replace('\\', '/')).FirstOrDefault() ?? throw new Exception("Missing " + dir + prefix);

        static Material PackMaterial(string id)
        {
            var dir = PackArt + id + "/";
            string baseC = Find(dir, "source_BaseColor"), nrm = Find(dir, "source_Normal"), mask = dir + id + "_Mask.png";
            AssetDatabase.ImportAsset(mask, ImportAssetOptions.ForceUpdate);
            Tex(baseC, false, true); Tex(nrm, true, false); Tex(mask, false, false);
            var template = AssetDatabase.LoadAssetAtPath<Material>(TemplateMat) ?? throw new Exception("No template " + TemplateMat);
            var b = AssetDatabase.LoadAssetAtPath<Texture2D>(baseC); var n = AssetDatabase.LoadAssetAtPath<Texture2D>(nrm); var k = AssetDatabase.LoadAssetAtPath<Texture2D>(mask);
            return Mat("FS_" + id, () => new Material(template), m =>
            {
                m.CopyPropertiesFromMaterial(template);
                m.SetTexture("_BaseMap", b); m.SetTexture("_MainTex", b); m.SetColor("_BaseColor", Color.white); m.SetColor("_Color", Color.white);
                m.SetTexture("_BumpMap", n); m.SetFloat("_BumpScale", 1f);
                // canvas and webbing: Meshy's roughness map reads a little glossy under the room lamps, so smoothness x 0.75
                m.SetTexture("_MetallicGlossMap", k); m.SetTexture("_OcclusionMap", k); m.SetFloat("_Metallic", 1f); m.SetFloat("_Smoothness", .75f);
                m.SetFloat("_OcclusionStrength", 1f);
                m.EnableKeyword("_NORMALMAP"); m.EnableKeyword("_METALLICSPECGLOSSMAP"); m.EnableKeyword("_OCCLUSIONMAP");
                m.enableInstancing = true;
            });
        }

        public static string BuildPacks()
        {
            Directory.CreateDirectory(PackPrefabs);
            var log = new List<string>();
            foreach (var id in Packs)
            {
                var mat = PackMaterial(id);
                var path = PackPrefabs + "FS_" + id + ".prefab";
                var root = new GameObject("FS_" + id);
                try
                {
                    var levels = new List<LOD>();
                    float[] cuts = { .32f, .08f, .012f };   // packs are ~0.6 m: full detail inside ~3 m, LOD1 to ~12 m
                    for (int i = 0; i < 3; i++)
                    {
                        var glb = PackArt + id + "/" + id + "_LOD" + i + ".glb";
                        AssetDatabase.ImportAsset(glb, ImportAssetOptions.ForceUpdate);
                        var mesh = AssetDatabase.LoadAllAssetsAtPath(glb).OfType<Mesh>().FirstOrDefault() ?? throw new Exception("No mesh in " + glb);
                        var go = new GameObject("LOD" + i); go.transform.SetParent(root.transform, false);
                        go.AddComponent<MeshFilter>().sharedMesh = mesh;
                        var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = mat;
                        r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = true;
                        r.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
                        r.receiveGI = ReceiveGI.LightProbes; r.lightProbeUsage = LightProbeUsage.BlendProbes;
                        levels.Add(new LOD(cuts[i], new Renderer[] { r }));
                        if (i == 0) log.Add($"{id}: LOD0 {mesh.triangles.Length / 3} tris, bounds {mesh.bounds.size}");
                    }
                    var g = root.AddComponent<LODGroup>(); g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                }
                finally { UnityEngine.Object.DestroyImmediate(root); }
            }
            AssetDatabase.SaveAssets();
            return string.Join("; ", log);
        }

        // ------------------------------------------------------------------ Tamsin
        public static readonly WardNpcInstall.Spec Tamsin = new WardNpcInstall.Spec
        {
            key = "tamsin", title = "Tamsin", npcId = "npc_tamsin", height = 1.76f, idle = "idle_248", talk = "talk_309",
            record = "../../meshy/field-supply-20261005/",
        };
        public static string BuildTamsin()
        {
            var import = WardNpcInstall.Import(new[] { Tamsin });
            var prefab = WardNpcInstall.BuildPrefabs(new[] { Tamsin });
            return JsonConvert.SerializeObject(new { import, prefab });
        }

        // ------------------------------------------------------------------ install
        sealed class Prop { public string name, path; public Vector2 xz; public float yaw, support; }
        static Prop P(string name, string path, float x, float z, float yaw, float support = -1) => new Prop { name = name, path = path, xz = new Vector2(x, z), yaw = yaw, support = support };
        const string SD = "Assets/AthenHill/Prefabs/StreetDressing/";
        // shop-local layout (x along the facade, +x north; z out to the avenue; floor at y 0.5). support < 0 = floor.
        static Prop[] Layout(float counterTop) => new[]
        {
            P("Stock crate · pack wall corner", SD + "SD_crate_wood_deep.prefab", -2.95f, -5.85f, 4),
            P("Stock crate · stacked", SD + "SD_crate_wood.prefab", -2.95f, -5.85f, -8, 0),     // support 0: stacked on the crate (resolved below)
            P("Ammo crate (cell stock)", SD + "SD_ammo_crate_a.prefab", -2.85f, -4.9f, 88),
            P("Carton of dressings", SD + "SD_carton.prefab", -2.9f, -4.3f, 12),
            P("Tamsin's stool", SD + "SD_stool_wood.prefab", 2.75f, -1.25f, 15),
            P("Tote behind the counter", SD + "SD_tote_blue.prefab", 2.6f, -4.15f, 4),
            P("Rolled tarps", SD + "SD_tarp_stack.prefab", 2.55f, -5.95f, 90),
            P("Broom by the bay", SD + "SD_broom.prefab", 1.05f, -0.75f, 0),
            P("Toolbox on the counter", SD + "SD_toolbox.prefab", 1.42f, -1.85f, 12, counterTop),
            P("Rag on the counter", SD + "SD_rag.prefab", 1.38f, -2.45f, 30, counterTop),
        };

        static GameObject Instantiate(string path, Transform parent)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (!asset) return null;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, parent.gameObject.scene);
            go.transform.SetParent(parent, false);
            return go;
        }
        static Bounds WorldBounds(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>(true).Where(r => r.enabled && !(r is ParticleSystemRenderer)).ToArray();
            var b = rs.Length > 0 ? rs[0].bounds : new Bounds(go.transform.position, Vector3.zero);
            foreach (var r in rs) b.Encapsulate(r.bounds);
            return b;
        }
        static void Interior(GameObject go)
        {
            foreach (var r in go.GetComponentsInChildren<Renderer>(true)) { r.renderingLayerMask |= InteriorLayer; r.shadowCastingMode = ShadowCastingMode.Off; }
            foreach (var g in go.GetComponentsInChildren<LODGroup>(true))
            {
                var lods = g.GetLODs();
                if (lods.Length > 1 && lods[0].screenRelativeTransitionHeight < .6f && g.size > 1.2f) { lods[0].screenRelativeTransitionHeight = .6f; g.SetLODs(lods); }
            }
        }
        static GameObject Place(Transform root, Prop p, float stackOn, List<string> log)
        {
            var go = Instantiate(p.path, root);
            if (!go) { log.Add("missing " + p.path); return null; }
            go.name = p.name;
            go.transform.localRotation = Quaternion.Euler(0, p.yaw, 0);
            go.transform.localPosition = new Vector3(p.xz.x, 0, p.xz.y);
            float support = p.support < 0 ? Floor : p.support == 0 ? stackOn : p.support;
            var b = WorldBounds(go);
            go.transform.position += Vector3.up * (root.TransformPoint(new Vector3(0, support, 0)).y - b.min.y);
            Interior(go);
            return go;
        }

        static Light Lamp(Transform parent, string name, Vector3 local, Color c, float intensity, float range, LightType type = LightType.Point, float angle = 120)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.localPosition = local;
            if (type == LightType.Spot) go.transform.localRotation = Quaternion.LookRotation(Vector3.down, Vector3.forward);
            var l = go.AddComponent<Light>(); l.type = type; l.color = c; l.intensity = intensity; l.range = range; l.shadows = LightShadows.None;
            if (type == LightType.Spot) { l.spotAngle = angle; l.innerSpotAngle = angle * .55f; }
            l.renderingLayerMask = (int)InteriorLayer;
            return l;
        }

        // pack wall and stand hooks -> which pack hangs there (duplicates are stock)
        static readonly Dictionary<string, string> HookPacks = new Dictionary<string, string>
        {
            ["top_0"] = "pack_rucksack", ["top_1"] = "pack_frame", ["top_2"] = "pack_carrier", ["top_3"] = "pack_rig",
            ["low_0"] = "pack_field", ["low_2"] = "pack_field",
            ["stand_w0"] = "pack_frame", ["stand_w1"] = "pack_rucksack", ["stand_e0"] = "pack_rig", ["stand_e1"] = "pack_carrier",
        };

        public static readonly (string name, Vector3 pos, Vector3 target, float fov)[] Cameras =
        {
            // shop-local metres; y absolute (floor 0.5, eye 1.62 above it)
            ("cam_fs_street", new Vector3(-2.6f, 2.12f, 5.6f), new Vector3(-0.3f, 1.7f, -3.5f), 55),
            ("cam_fs_bay", new Vector3(-0.6f, 2.12f, 2.6f), new Vector3(-0.6f, 1.55f, -5.5f), 60),
            ("cam_fs_counter", new Vector3(-1.6f, 2.12f, -1.25f), new Vector3(2.4f, 1.7f, -2.9f), 60),
            ("cam_fs_tamsin", new Vector3(0.55f, 2.12f, -2.6f), new Vector3(2.35f, 2.05f, -2.7f), 45),
            ("cam_fs_packwall", new Vector3(0.35f, 2.12f, -2.6f), new Vector3(-1.3f, 1.65f, -6.4f), 60),
            ("cam_fs_shelf", new Vector3(-1.05f, 2.12f, -0.95f), new Vector3(-3.3f, 1.65f, -2.1f), 55),
            ("cam_fs_cabinet", new Vector3(0.6f, 2.12f, -1.6f), new Vector3(3.3f, 1.65f, -2.85f), 55),
            ("cam_fs_inside_out", new Vector3(1.6f, 2.12f, -5.6f), new Vector3(-0.8f, 1.9f, 0.6f), 60),
        };

        static void Unhook(GameSession session, CityLightCircuit circuit, GameObject old)
        {
            var oldNpcs = old.GetComponentsInChildren<NpcAgent>(true);
            session.npcs = session.npcs.Where(n => n && !oldNpcs.Contains(n)).ToArray();
            var oldLights = new HashSet<Light>(old.GetComponentsInChildren<Light>(true));
            circuit.practicalLights = circuit.practicalLights.Where(l => l && !oldLights.Contains(l)).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !oldLights.Contains(l)).ToArray();
        }

        public static string Install()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var log = new List<string>();
            var shop = Shop(scene);
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            var rec = Record();
            var interior = (JObject)rec["interior"] ?? throw new Exception("field_supply.json has no interior record: re-run the Field Supply authoring");
            float counterTop = (float)interior["counter"]["top"] + .055f;

            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (old) { Unhook(session, circuit, old); UnityEngine.Object.DestroyImmediate(old); log.Add("replaced previous install"); }
            var root = new GameObject(RootName).transform;
            root.SetPositionAndRotation(shop.position, shop.rotation);
            var b = interior["bounds"];
            var bmin = V3(b[0]); var bmax = V3(b[1]);

            // lamps: three pendants (shades in the shop model), a soft bounce, the shelf's and cabinet's cyan glows
            var lamps = new GameObject("Lamps").transform; lamps.SetParent(root, false);
            var warm = new Color(1f, .76f, .5f);
            var lights = new List<Light>();
            foreach (var l in interior["lamps"])
                lights.Add(Lamp(lamps, (string)l["name"] + " light", V3(l["pos"]) + Vector3.down * .07f, warm, 2.2f, 7f, LightType.Spot, 140));
            lights.Add(Lamp(lamps, "Room bounce", new Vector3(0f, 2.9f, -3.4f), new Color(1f, .82f, .62f), .45f, 6.5f));
            // in front of the tiers (at the lightbox it left a hot dot on the glossy band)
            var shelfZ = (float)interior["shelf"]["z"][0] / 2 + (float)interior["shelf"]["z"][1] / 2;
            lights.Add(Lamp(lamps, "Magazine shelf glow", new Vector3((float)interior["shelf"]["x"] + .75f, 1.6f, shelfZ), new Color(.35f, .85f, 1f), .3f, 2.4f));
            var cab = interior["cabinet"];
            lights.Add(Lamp(lamps, "Cabinet glow", new Vector3((float)cab["x"][0] - .45f, ((float)cab["y"][0] + (float)cab["y"][1]) / 2, ((float)cab["z"][0] + (float)cab["z"][1]) / 2), new Color(.35f, .85f, 1f), .25f, 2.0f));
            var spillGo = new GameObject("Bay spill"); spillGo.transform.SetParent(lamps, false);
            var bay = interior["bay"]; float bx0 = (float)bay["x"][0], bx1 = (float)bay["x"][1], btop = (float)bay["top"];
            spillGo.transform.localPosition = new Vector3((bx0 + bx1) / 2, 3.25f, -0.75f);
            spillGo.transform.localRotation = Quaternion.LookRotation(new Vector3(0, -2.6f, 3.2f).normalized, Vector3.up);
            var spill = spillGo.AddComponent<Light>(); spill.type = LightType.Spot; spill.color = warm; spill.intensity = 2.2f; spill.range = 7f;
            spill.spotAngle = 95; spill.innerSpotAngle = 50; spill.shadows = LightShadows.None;
            circuit.practicalLights = circuit.practicalLights.Concat(new[] { spill }).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Concat(new[] { spill }).ToArray();

            // packs on the hooks
            var stock = new GameObject("Packs").transform; stock.SetParent(root, false);
            int packs = 0;
            foreach (var h in interior["pack_hooks"])
            {
                string hook = (string)h["name"];
                if (!HookPacks.TryGetValue(hook, out var id)) continue;
                var go = Instantiate(PackPrefabs + "FS_" + id + ".prefab", stock);
                if (!go) { log.Add("missing pack prefab " + id); continue; }
                go.name = $"{id} · {hook}";
                var pos = V3(h["pos"]); var facing = V3(h["facing"]);
                bool wall = hook.StartsWith("top") || hook.StartsWith("low");
                // the hang point (top of the back) sits on the hook: wall packs with their backs to the rail, stand packs to the frame
                var at = wall ? new Vector3(pos.x, pos.y + .05f, -6.48f + .085f) : new Vector3(pos.x - facing.x * .13f, pos.y + .05f, pos.z);
                go.transform.localPosition = at; go.transform.localRotation = Quaternion.LookRotation(facing, Vector3.up);
                Interior(go);
                packs++;
            }
            // crates, stool and counter clutter
            var props = new GameObject("Props").transform; props.SetParent(root, false);
            int placed = 0; float stackOn = Floor;
            foreach (var p in Layout(counterTop))
            {
                var go = Place(props, p, stackOn, log);
                if (!go) continue;
                placed++;
                stackOn = root.InverseTransformPoint(WorldBounds(go).max).y;    // the next "stacked" prop rests on this one
            }

            // Tamsin behind the counter, facing the room
            var keeper = V3(interior["keeper"]);
            var npcRoot = new GameObject("npc_tamsin").transform; npcRoot.SetParent(root, false);
            npcRoot.localPosition = new Vector3(keeper.x, Floor, keeper.z); npcRoot.localRotation = Quaternion.Euler(0, -90, 0);
            var person = Instantiate(Tamsin.Prefab, npcRoot) ?? throw new Exception("Tamsin's prefab is missing: run the tamsin step");
            person.name = "WardNpc Tamsin"; person.transform.localPosition = Vector3.zero; person.transform.localRotation = Quaternion.identity;
            foreach (var r in person.GetComponentsInChildren<Renderer>(true)) r.renderingLayerMask |= InteriorLayer;
            foreach (var an in person.GetComponentsInChildren<Animation>(true)) an.cullingType = AnimationCullingType.BasedOnRenderers;
            var agent = npcRoot.gameObject.AddComponent<NpcAgent>();
            agent.definition = AssetDatabase.LoadAssetAtPath<NpcDefinition>(TamsinPath) ?? throw new Exception("npc_tamsin.asset missing (art/field_supply_20261005/apply_data.py)");
            agent.actor = person.GetComponent<ActorAnimation>(); agent.countsForCityVisit = false;
            session.npcs = session.npcs.Where(n => n).Concat(new[] { agent }).ToArray();

            // interior reflection, box projected over the room (baked by "bake")
            var probeGo = new GameObject("Interior reflection"); probeGo.transform.SetParent(root, false);
            probeGo.transform.localPosition = (bmin + bmax) / 2;
            var probe = probeGo.AddComponent<ReflectionProbe>(); probe.mode = ReflectionProbeMode.Baked; probe.boxProjection = true;
            probe.size = bmax - bmin; probe.blendDistance = .4f; probe.importance = 2;
            probe.intensity = .45f; probe.resolution = 128; probe.clearFlags = ReflectionProbeClearFlags.Skybox;
            var baked = AssetDatabase.LoadAssetAtPath<Cubemap>(ArtDir + "FieldSupplyInteriorReflection.exr");
            if (baked) { probe.customBakedTexture = baked; probe.mode = ReflectionProbeMode.Custom; }

            var il = root.gameObject.AddComponent<InteriorLighting>();
            il.localBounds = new Bounds((bmin + bmax) / 2, bmax - bmin);
            il.openingDirection = Vector3.forward;
            il.openingCorners = new[] { new Vector3(bx0, Floor, .05f), new Vector3(bx1, Floor, .05f), new Vector3(bx1, btop, .05f), new Vector3(bx0, btop, .05f) };
            il.interiorRoots = new[] { props, stock, npcRoot };
            il.renderers = shop.GetComponentsInChildren<Renderer>(true).Where(r => r.name.Contains("_Interior")).ToList();
            il.lamps = lights.ToArray();
            foreach (var r in il.renderers) r.renderingLayerMask |= InteriorLayer;

            // the opened bay: street dressing, sand banks or decals left on its approach go inactive (recorded, never deleted)
            var approach = new Bounds(shop.TransformPoint(new Vector3((bx0 + bx1) / 2, 1.2f, 1.1f)), Vector3.one);
            var corners = new[] { new Vector3(bx0 + .1f, Floor + .08f, -.3f), new Vector3(bx1 - .1f, 2.2f, 2.2f) }.Select(shop.TransformPoint).ToArray();
            approach = new Bounds((corners[0] + corners[1]) / 2, Vector3.zero); approach.Encapsulate(corners[0]); approach.Encapsulate(corners[1]);
            var retired = new List<string>();
            foreach (var g in scene.GetRootGameObjects())
            {
                if (g.name == RootName || g.transform == shop.root) continue;
                if (!g.name.StartsWith("Ward street dressing") && !g.name.StartsWith("Ward wall-foot drifts") && !g.name.StartsWith("Ward night life")) continue;
                foreach (Transform t in g.GetComponentsInChildren<Transform>(true))
                {
                    // single props (outermost prefab instances) and sand banks / decals (renderer leaves), never whole vignettes
                    if (t == g.transform || !t.gameObject.activeInHierarchy) continue;
                    bool prefabRoot = PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject);
                    bool leaf = !PrefabUtility.IsPartOfAnyPrefab(t.gameObject) && t.GetComponent<Renderer>() && t.childCount == 0;
                    bool decal = t.GetComponent<DecalProjector>() && t.childCount == 0;
                    if (!prefabRoot && !leaf && !decal) continue;
                    Bounds pb;
                    if (decal) { var dp = t.GetComponent<DecalProjector>(); pb = new Bounds(t.position, new Vector3(dp.size.x, 1f, dp.size.y)); }
                    else { var rs = t.GetComponentsInChildren<Renderer>(false); if (rs.Length == 0) continue; pb = rs[0].bounds; foreach (var r in rs) pb.Encapsulate(r.bounds); }
                    if (pb.size.magnitude > 4f || !approach.Contains(new Vector3(pb.center.x, approach.center.y, pb.center.z))) continue;
                    if (decal && !g.name.StartsWith("Ward wall-foot drifts")) continue;     // grime decals on the paving can stay
                    Undo.RecordObject(t.gameObject, "retire"); t.gameObject.SetActive(false);
                    retired.Add(PathOf(t));
                }
            }
            log.Add("retired on the bay approach: " + (retired.Count == 0 ? "none" : string.Join(", ", retired)));

            // landmarks (QA teleports) and review cameras
            var landmarks = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Landmarks");
            if (landmarks)
                foreach (var (n, local) in new[] { ("field_supply", new Vector3((bx0 + bx1) / 2, Floor, 2.2f)), ("field_supply_counter", new Vector3(.45f, Floor, -2.7f)),
                                                   ("field_supply_shelf", new Vector3(-2.3f, Floor, -1.95f)), ("field_supply_packs", new Vector3(-1.2f, Floor, -5.45f)) })
                {
                    var t = landmarks.transform.Find(n) ?? new GameObject(n).transform;
                    t.SetParent(landmarks.transform, true); t.position = root.TransformPoint(local);
                }
            var camRoot = new GameObject("Field Supply review cameras").transform; camRoot.SetParent(root, false);
            foreach (var (n, pos, target, fov) in Cameras)
            {
                var go = new GameObject(n); go.transform.SetParent(camRoot, false);
                go.transform.localPosition = pos; go.transform.localRotation = Quaternion.LookRotation(target - pos, Vector3.up);
                var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f; cam.farClipPlane = 650;
            }
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                if (!t.GetComponent<Light>() && !t.GetComponent<Camera>() && !t.GetComponentInParent<NpcAgent>())
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic | StaticEditorFlags.ReflectionProbeStatic);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            log.Add($"packs {packs}, props {placed}, lamps {lights.Count}+spill, interior renderers {il.renderers.Count}, npcs {session.npcs.Length}");
            return string.Join("; ", log);
        }

        public static string Uninstall()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (!old) return "not installed";
            Unhook(UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include), UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include), old);
            UnityEngine.Object.DestroyImmediate(old);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "uninstalled (re-copy art/field_supply_20261005/previous/ and run models to close the shutter again)";
        }

        // ------------------------------------------------------------------ verify
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var problems = new List<string>();
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            if (!root) problems.Add("not installed");
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            var tamsin = session.npcs.FirstOrDefault(n => n && n.definition && n.definition.id == "npc_tamsin");
            r["tamsinInSession"] = tamsin != null; if (!tamsin) problems.Add("Tamsin not in GameSession.npcs");
            if (tamsin)
            {
                if (!tamsin.actor) problems.Add("Tamsin has no ActorAnimation");
                if (tamsin.countsForCityVisit) problems.Add("Tamsin counts for the city visit");
                var shopDef = tamsin.definition.shop;
                r["shop"] = new { shopDef.title, shopDef.subtitle, shopDef.supplies, shopDef.parts, shopDef.salvage, shopDef.magazines, stockTags = shopDef.stockTags };
                if (!shopDef.magazines || shopDef.stockTags == null || !shopDef.stockTags.Contains("field_supply")) problems.Add("Tamsin's counter profile");
                // the counter front is inside her talk range; the bay mouth is not (no prompt from the street)
                var shopT = Shop(scene);
                float front = Vector3.Distance(shopT.TransformPoint(new Vector3(.45f, Floor, -2.7f)), tamsin.transform.position);
                float mouth = Vector3.Distance(shopT.TransformPoint(new Vector3(-.6f, Floor, .3f)), tamsin.transform.position);
                r["talkDistance"] = new { counterFront = Math.Round(front, 2), bayMouth = Math.Round(mouth, 2), range = session.interactionRange };
                if (front > session.interactionRange - .2f) problems.Add("counter front outside Tamsin's talk range");
                if (mouth < session.interactionRange + .3f) problems.Add("Tamsin's prompt reaches the street");
                // no other colonist's range overlaps hers
                foreach (var n in session.npcs.Where(x => x && x != tamsin))
                    if (Vector3.Distance(n.transform.position, tamsin.transform.position) < session.interactionRange * 2) problems.Add("Tamsin's talk range overlaps " + n.name);
            }
            foreach (var def in AssetDatabase.FindAssets("t:NpcDefinition").Select(g => AssetDatabase.LoadAssetAtPath<NpcDefinition>(AssetDatabase.GUIDToAssetPath(g))))
            {
                foreach (var e in def.entries ?? new DialogueEntry[0])
                {
                    foreach (var p in QuestConditions.Problems(e.requires)) problems.Add($"{def.id} entry {e.node}: {p}");
                    if (!def.nodes.Any(n => n.id == e.node)) problems.Add($"{def.id} entry node {e.node} missing");
                }
                foreach (var n in def.nodes)
                {
                    if ((n.choices?.Length ?? 0) > GameSession.MaxChoices) problems.Add($"{def.id}/{n.id} has more than {GameSession.MaxChoices} choices");
                    foreach (var c in n.choices ?? new DialogueChoice[0])
                    {
                        foreach (var p in QuestConditions.Problems(c.requires)) problems.Add($"{def.id}/{n.id} choice: {p}");
                        if (string.IsNullOrEmpty(c.action) && !def.nodes.Any(x => x.id == c.next)) problems.Add($"{def.id}/{n.id} '{c.label}' dead end");
                    }
                }
            }
            // walk paths: a 1.8 m capsule (r 0.3) clears porch -> bay -> counter front, -> shelf front, -> pack wall
            var shop = Shop(scene);
            Physics.SyncTransforms();
            var paths = new Dictionary<string, Vector3[]>
            {
                ["counter"] = new[] { new Vector3(-0.6f, 0, 2.6f), new Vector3(-0.6f, 0, .6f), new Vector3(-0.6f, 0, -.7f), new Vector3(0f, 0, -1.8f), new Vector3(.45f, 0, -2.7f), new Vector3(.45f, 0, -3.6f) },
                ["shelf"] = new[] { new Vector3(-0.6f, 0, -.7f), new Vector3(-1.6f, 0, -1.4f), new Vector3(-2.3f, 0, -1.95f) },
                ["packs"] = new[] { new Vector3(0f, 0, -1.8f), new Vector3(.25f, 0, -3.6f), new Vector3(0f, 0, -5.35f), new Vector3(-1.2f, 0, -5.45f), new Vector3(-2.2f, 0, -5.4f) },
                ["stand west"] = new[] { new Vector3(-1.6f, 0, -1.4f), new Vector3(-2.15f, 0, -3.0f), new Vector3(-2.15f, 0, -4.4f) },
            };
            var blocked = new List<string>();
            foreach (var kv in paths)
            {
                var path = kv.Value;
                for (int i = 0; i < path.Length; i++)
                {
                    var w = shop.TransformPoint(path[i] + Vector3.up * Floor);
                    foreach (var h in Physics.OverlapCapsule(w + Vector3.up * .36f, w + Vector3.up * 1.5f, .3f, ~(1 << 8), QueryTriggerInteraction.Ignore))
                        blocked.Add($"{kv.Key} point {i} {A(w)}: {PathOf(h.transform)}");
                    if (i > 0)
                    {
                        var a = shop.TransformPoint(path[i - 1] + Vector3.up * Floor);
                        if (Physics.CapsuleCast(a + Vector3.up * .36f, a + Vector3.up * 1.5f, .28f, (w - a).normalized, out var hit, (w - a).magnitude, ~(1 << 8), QueryTriggerInteraction.Ignore))
                            blocked.Add($"{kv.Key} leg {i - 1}->{i}: {PathOf(hit.transform)}");
                    }
                    if (!Physics.Raycast(w + Vector3.up * .5f, Vector3.down, out var g, 1f, ~(1 << 8), QueryTriggerInteraction.Ignore) || Mathf.Abs(g.point.y - w.y) > .06f)
                        blocked.Add($"{kv.Key} point {i}: no floor at {A(w)}");
                }
            }
            r["pathBlocked"] = blocked; problems.AddRange(blocked);
            if (root)
            {
                var il = root.GetComponent<InteriorLighting>();
                r["interiorRenderers"] = il ? il.renderers.Count : 0;
                r["lamps"] = il ? il.lamps.Length : 0;
                r["packs"] = root.transform.Find("Packs")?.childCount ?? 0;
                r["props"] = root.transform.Find("Props")?.childCount ?? 0;
                if ((int)r["packs"] < 8) problems.Add("packs missing on the hooks");
                r["missingMaterials"] = root.GetComponentsInChildren<Renderer>(true).Concat(shop.GetComponentsInChildren<Renderer>(true))
                    .Where(x => x.sharedMaterials.Any(m => !m)).Select(x => PathOf(x.transform)).ToArray();
                if (((string[])r["missingMaterials"]).Length > 0) problems.Add("missing materials");
                var screens = shop.GetComponentsInChildren<Renderer>(true).FirstOrDefault(x => x.name.Contains("_InteriorScreens_LOD0"));
                r["screensMaterial"] = screens ? screens.sharedMaterial?.name : null;
                if (!screens || !screens.sharedMaterial || !screens.sharedMaterial.GetTexture("_BaseMap")) problems.Add("magazine screens have no cover atlas");
            }
            var group = shop.GetComponent<LODGroup>();
            r["lodRenderers"] = group.GetLODs().Select(l => l.renderers.Length).ToArray();
            r["interiorInLods"] = group.GetLODs().SelectMany(l => l.renderers).Count(x => x && x.name.Contains("_Interior"));
            r["colliders"] = shop.Find("Colliders").Cast<Transform>().Select(t => t.name).ToArray();
            r["cameras"] = Cameras.Select(c => c.name).ToArray();
            r["problems"] = problems;
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", JsonConvert.SerializeObject(r, Formatting.Indented));
            return problems.Count == 0 ? "verify ok" : "verify problems: " + string.Join(" | ", problems.Take(14));
        }

        // ------------------------------------------------------------------ graphics steps
        static void ApplyRoom(GameObject root, float hour)
        {
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var f = clock.profile.Evaluate(hour);
            var (s0, e0, g0) = (RenderSettings.ambientSkyColor, RenderSettings.ambientEquatorColor, RenderSettings.ambientGroundColor);
            RenderSettings.ambientSkyColor = f.ambientSky; RenderSettings.ambientEquatorColor = f.ambientEquator; RenderSettings.ambientGroundColor = f.ambientGround;
            root.GetComponent<InteriorLighting>()?.ApplyInEditor();
            RenderSettings.ambientSkyColor = s0; RenderSettings.ambientEquatorColor = e0; RenderSettings.ambientGroundColor = g0;
        }
        public static string Bake()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            var probe = root.GetComponentInChildren<ReflectionProbe>(true);
            probe.mode = ReflectionProbeMode.Baked;
            ApplyRoom(root, 13f);
            Directory.CreateDirectory(ArtDir);
            var path = ArtDir + "FieldSupplyInteriorReflection.exr";
            if (!Lightmapping.BakeReflectionProbe(probe, path)) throw new Exception("interior reflection bake failed");
            // a few pixels of the street seen through the bay bake at the half-float maximum (65504); convolved into every
            // mip they turned all smooth surfaces in the room to chrome. Clamp them (ImageMagick, editor-only tooling).
            var clamp = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("magick", $"\"{Path.GetFullPath(path)}\" -fx \"min(u,6)\" \"{Path.GetFullPath(path)}\"") { UseShellExecute = false });
            clamp.WaitForExit();
            if (clamp.ExitCode != 0) throw new Exception("probe clamp failed (ImageMagick 'magick' on PATH?)");
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            probe.customBakedTexture = AssetDatabase.LoadAssetAtPath<Cubemap>(path); probe.mode = ReflectionProbeMode.Custom;
            EditorUtility.SetDirty(probe);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "baked " + path;
        }
        static int captured;
        public static string Capture(string hourText, string camList, string outDir)
        {
            var names = camList.Split('+');
            captured += names.Length;
            if (captured > 6) throw new Exception("at most 6 cameras per Unity run (VRAM rule)");
            float hour = float.Parse(hourText, Inv);
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (root) ApplyRoom(root, hour);
            foreach (var smr in UnityEngine.Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None)) smr.forceMatrixRecalculationPerRender = true;
            ShaderUtil.allowAsyncCompilation = false;
            DuskStartPass.Preview(hour, Path.Combine(outDir, "warmup"), names[0]);
            return DuskStartPass.Preview(hour, outDir, names);
        }

        /// -executeMethod AthenHill.Editor.FieldSupplyShopPass.RunBatch --steps materials,models,packs,tamsin,install,verify
        /// (graphics steps: bake, capture:HOUR:cam+cam [--out dir]).
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
                        "materials" => "materials " + Materials().Count,
                        "models" => Models(),
                        "packs" => BuildPacks(),
                        "tamsin" => BuildTamsin(),
                        "install" => Install(),
                        "uninstall" => Uninstall(),
                        "verify" => Verify(),
                        "bake" => Bake(),
                        "capture" => Capture(parts[1], parts[2], outDir),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("FieldSupplyShopPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
