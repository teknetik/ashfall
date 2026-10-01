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
    /// 30 September 2026: stone rebuild of the five shops round the Vanguard Hall plaza (Relay Works, Air + Water,
    /// Tool Exchange, Finery, Field Supply) to the hall's standard (Carl: "modelled stone, proper doorways, lamps on the
    /// city's day/night timing"; Tool Exchange: "sci-fi not woodworking shop from the 90s").
    ///
    /// Sources: art/hall_district_20260930/author_ward_shops.py (Blender, shared kit art/ward_masonry_kit) writes
    /// Art/WardShops/Models/<Shop>_LOD0/1.glb and <shop>.json (colliders, fittings, lamps, sign and display mounts).
    /// Menu Athen Hill → Ward shops: Build assets (materials keep Inspector edits unless rebuilt), Dry-run install
    /// (writes what would be retired), Install (one-time; refuses when a shop root exists), Verify saved scene.
    /// Replaced shop layers stay in the scene inactive; the combined district retrofit meshes get filtered copies
    /// (originals untouched) so rollback is a re-activation plus a mesh reassignment recorded in the install report.
    /// The shops are not render-chunk sources: each keeps its own LODGroup and vertex-colour masonry.
    ///
    /// North avenue (30 Sep 2026, Carl: "we still need to rebuild. general, salvage, thread and repairs. same stone work,
    /// same signage, same weathering"): NorthSites (Salvage, Repairs, Thread + Hide from art/north_avenue_20260930/
    /// author_north_shops.py; the Basic General booth from author_basic_general.py) go through the same build / plan /
    /// install / signs / verify path under their own group and evidence folder (menu Athen Hill → Ward shops → North avenue).
    /// The booth is retired by an explicit list only (no parcel sweep), so Mira, the counter dressing, the Stock panels,
    /// the back panel and the family sign are never touched.
    /// </summary>
    public static class WardShopsPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/WardShops/";
        const string MatDir = Root + "Materials/";
        const string ModelDir = Root + "Models/";
        const string RetrofitDir = Root + "Retrofit/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/WardShops/";
        const string HallMatDir = "Assets/AthenHill/Art/VanguardHall/Materials/";
        const string HallTexDir = "Assets/AthenHill/Art/VanguardHall/Textures/";
        const string BoothDir = Root + "Booth/";
        const string Evidence = "../evidence/hall-district/20260930/";
        const string NorthEvidence = "../evidence/north-avenue/20260930/";
        public const string GroupName = "Ward shops (hall district)";
        public const string NorthGroupName = "Ward shops (north avenue)";
        public const float Lod0ScreenHeight = .45f;

        public sealed class Site
        {
            public string key, model, name; public Vector3 pos; public float yaw; public string[] retire;
            /// booth: an open stall with its own footprint (Basic General); no parcel sweep, explicit retire list only
            public bool booth;
            public Site(string key, string model, string name, Vector3 pos, float yaw, params string[] retire)
            { this.key = key; this.model = model; this.name = name; this.pos = pos; this.yaw = yaw; this.retire = retire; }
            public string ModelPath(int lod) => (booth ? BoothDir : ModelDir) + $"{model}_LOD{lod}.glb";
            public string RecordPath => (booth ? BoothDir : ModelDir) + key + ".json";
        }

        static string[] Porch(string id) => new[] { $"AuthoredWorld/BLD_shop_{id}_porch", $"AuthoredWorld/BLD_shop_{id}_first_step", $"AuthoredWorld/BLD_shop_{id}_interior_floor" };

        public static readonly Site[] Sites =
        {
            new Site("relay_works", "RelayWorks", "Relay Works", new Vector3(-18.1f, 0, -18f), 90f,
                new[] { "Ward shop architecture/relay_works", "Post-war salvage/BLD_shop_e_01 repaired", "Relay and Air Water surface wear/relay_works" }.Concat(Porch("e_01")).ToArray()),
            new Site("air_water", "AirWater", "Air + Water", new Vector3(-18.1f, 0, -9f), 90f,
                new[] { "Ward shop architecture/air_water", "Post-war salvage/BLD_shop_e_02 repaired", "Relay and Air Water surface wear/air_water" }.Concat(Porch("e_02")).ToArray()),
            new Site("tool_exchange", "ToolExchange", "Tool Exchange", new Vector3(-18.1f, 0, 9f), 90f,
                new[] { "Ward shop architecture/tool_exchange", "Post-war salvage/BLD_shop_e_03 repaired", "Tool Exchange display and shutter" }.Concat(Porch("e_03")).ToArray()),
            new Site("finery", "Finery", "Finery", new Vector3(18.1f, 0, -18f), -90f,
                new[] { "Phase 1 Finery frontage", "Post-war salvage/BLD_shop_w_01 repaired", "Field Supply and Finery weathering/finery",
                        "Courtyard reference pass/Canopy", "Courtyard reference pass/Awning hardware" }.Concat(Porch("w_01")).ToArray()),
            new Site("field_supply", "FieldSupply", "Field Supply", new Vector3(18.1f, 0, -9f), -90f,
                new[] { "Ward shop architecture/field_supply", "Post-war salvage/BLD_shop_w_02 repaired", "Field Supply and Finery weathering/field_supply" }.Concat(Porch("w_02")).ToArray()),
        };

        const string BG = "Basic General authored frontage/";
        public static readonly Site[] NorthSites =
        {
            new Site("salvage", "Salvage", "Salvage", new Vector3(-18.1f, 0, 18f), 90f,
                new[] { "Ward shop architecture/salvage", "Post-war salvage/BLD_shop_e_04 repaired" }.Concat(Porch("e_04")).ToArray()),
            new Site("repairs", "Repairs", "Repairs", new Vector3(18.1f, 0, 9f), -90f,
                new[] { "Ward shop architecture/repairs", "Post-war salvage/BLD_shop_w_03 repaired" }.Concat(Porch("w_03")).ToArray()),
            new Site("thread_hide", "ThreadHide", "Thread + Hide", new Vector3(18.1f, 0, 18f), -90f,
                new[] { "Ward shop architecture/thread_hide", "Post-war salvage/BLD_shop_w_04 repaired" }.Concat(Porch("w_04")).ToArray()),
            // the booth's structure only: Stock, counter rivets, counter wear, the counter dressing, back panel, sign and Mira stay
            new Site("basic_general", "BasicGeneral", "Basic General", new Vector3(8f, 0, 15.1f), 0f,
                BG + "Masonry", BG + "Walls", BG + "Rear services", BG + "Structure", BG + "Canopy", BG + "Signs", BG + "Lights", BG + "Threshold",
                BG + "Hardware/Bearer_anchor*", BG + "Hardware/Rear_panel_fixing*", BG + "Hardware/Service_lid_screw*", BG + "Hardware/Sign_mounting_screw*",
                BG + "Localized wear/Sign_plate_corner_contact_wear*", "AuthoredWorld/BLD_general_porch", "AuthoredWorld/BLD_general_first_step",
                "Post-war salvage/Basic General repaired") { booth = true },
        };

        // roots whose contents are never swept by the parcel rules (gameplay, actors, other passes' accepted assets)
        static readonly string[] Protected =
        {
            "Colonists", "Landmarks", "CitySession", "Player", "MainCamera", "Vanguard Hall", "City Render Chunks", "Paving",
            "Paving Joints", "Desert Landscape", "Ward oasis tree", "Outer Berms", "Karaveen", "Ward mining droid", "Mining droid route",
            "Ward shop architecture/Air + Water filter fittings", "Ward lighting clock", "Character preview", "First-person view model",
            GroupName, NorthGroupName, "Basic General counter dressing", "Basic General back panel", "Basic General sign (hall district family)",
            "City Audio",
        };

        static readonly string[] RetrofitMeshes =
        {
            "Ward district retrofit/Shop retrofits/Shop retrofits Structure", "Ward district retrofit/Shop retrofits/Shop retrofits Detail",
            "Ward district retrofit/Shop retrofits/Shop retrofits Glow", "Ward district retrofit/Shop retrofits/Shop retrofits Decals",
        };

        // ------------------------------------------------------------------ parcel geometry (local to a site root)
        static Matrix4x4 SiteMatrix(Site s) => Matrix4x4.TRS(s.pos, Quaternion.Euler(0, s.yaw, 0), Vector3.one);

        /// building volume, facade band (things mounted on the old facade) and porch surface layer
        static bool InParcel(Site s, Vector3 world, Bounds wb, out string zone)
        {
            zone = null;
            if (s.booth) return false;
            var p = SiteMatrix(s).inverse.MultiplyPoint3x4(world);
            if (p.x > -4.05f && p.x < 4.05f && p.z > -7.35f && p.z < 0.3f && p.y > 0.45f && p.y < 16f) { zone = "building"; return true; }
            if (p.x > -4.3f && p.x < 4.3f && p.z >= 0.3f && p.z < 1.9f && p.y > 1.0f && p.y < 13f) { zone = "facade"; return true; }
            if (p.x > -4.0f && p.x < 4.0f && p.z >= 0.3f && p.z < 4.6f && wb.max.y < 0.66f && wb.size.y < 0.4f) { zone = "porch"; return true; }
            return false;
        }

        static string PathOf(Transform t) { var s = t.name; while (t.parent) { t = t.parent; s = t.name + "/" + s; } return s; }
        static bool IsProtected(string path) => Protected.Any(p => path == p || path.StartsWith(p + "/")) || path.StartsWith("AuthoredWorld/COL_");

        static Transform FindPath(string path)
        {
            var parts = path.Split('/');
            var top = EditorSceneManager.GetActiveScene().GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!top) return null;
            var t = top.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Cast<Transform>().FirstOrDefault(c => c.name == parts[i]);
            return t;
        }

        /// A retire entry is a path, or "parent/prefix*" for every child of parent whose name starts with prefix.
        static IEnumerable<Transform> FindRetire(string path)
        {
            if (!path.EndsWith("*")) { var t = FindPath(path); if (t) yield return t; yield break; }
            var cut = path.LastIndexOf('/');
            var parent = FindPath(path.Substring(0, cut));
            var prefix = path.Substring(cut + 1).TrimEnd('*');
            if (!parent) yield break;
            foreach (Transform c in parent) if (c.name.StartsWith(prefix)) yield return c;
        }

        // ------------------------------------------------------------------ materials
        static Texture2D Tex(string set, string kind) => AssetDatabase.LoadAssetAtPath<Texture2D>(HallTexDir + set + "_" + kind + (kind == "Mask" ? ".png" : ".jpg"));

        static Material NewOrLoad(string name, Shader shader, bool rebuild, out bool setup)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            setup = !m || rebuild;
            if (!m) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
            else if (rebuild && m.shader != shader) m.shader = shader;
            return m;
        }

        static void SetupLit(Material m, string set, Color color, float tileMetres, float smoothness = 1f, float bump = 1f)
        {
            m.SetTexture("_BaseMap", set != null ? Tex(set, "BaseMap") : null);
            m.SetColor("_BaseColor", color);
            m.SetTextureScale("_BaseMap", Vector2.one / tileMetres);
            if (set != null)
            {
                m.SetTexture("_BumpMap", Tex(set, "Normal")); m.EnableKeyword("_NORMALMAP"); m.SetFloat("_BumpScale", bump);
                m.SetTexture("_MetallicGlossMap", Tex(set, "Mask")); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetTexture("_OcclusionMap", Tex(set, "Mask")); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1);
            }
            m.SetFloat("_Smoothness", smoothness);
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
        }

        static void Emissive(Material m, Color baseColor, Color emission)
        {
            SetupLit(m, null, baseColor, 1f, .8f);
            m.SetColor("_EmissionColor", emission); m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            EditorUtility.SetDirty(m);
        }

        public static Dictionary<string, Material> BuildMaterials(bool rebuild)
        {
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var window = Shader.Find("Athen Hill/Ward Window Interior");
            var mats = new Dictionary<string, Material>();
            // the hall's materials are shared (same stone, steel and lamp glass standard)
            foreach (var n in new[] { "VH_Ashlar", "VH_AshlarRough", "VH_Mortar", "VH_PodiumSlab", "VH_Roof", "VH_Sand", "VH_DoorSteel", "VH_Steel",
                                      "VH_PaintedSteel", "VH_Bronze", "VH_PlateBronze", "VH_Brass", "VH_Dark", "VH_LampLens", "VH_Rubber" })
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(HallMatDir + n + ".mat");
                if (!m) throw new Exception("Hall material missing: " + n);
                mats[n] = m;
            }
            void Make(string name, Shader shader, Action<Material> setup) { var m = NewOrLoad(name, shader, rebuild, out bool s); mats[name] = m; if (s) setup(m); }
            Make("WS_Glass", window, m =>
            {
                var src = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Quality/RelayArchitecture/Revision02/Materials/WardGlass.mat");
                if (src) m.CopyPropertiesFromMaterial(src);
                m.SetVector("_RoomSize", new Vector4(3.6f, 4.3f, 3.4f, 0)); m.SetVector("_RoomOffset", new Vector4(0f, .5f, 0f, 0));
                m.SetFloat("_RoomSeed", 29); m.SetFloat("_BlindAmount", .5f); m.SetFloat("_FurnitureAmount", .75f);
                m.SetFloat("_LitFraction", .55f); m.SetFloat("_CoolFraction", .1f); m.SetFloat("_DirtAmount", .5f);
                EditorUtility.SetDirty(m);
            });
            Make("WS_ClearGlass", lit, m =>
            {
                SetupLit(m, null, new Color(.55f, .66f, .68f, .14f), 1f, .93f);
                m.SetFloat("_Surface", 1); m.SetFloat("_Blend", 0); m.SetFloat("_ZWrite", 0);
                m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One); m.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
                m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.SetOverrideTag("RenderType", "Transparent");
                m.renderQueue = (int)RenderQueue.Transparent; m.SetShaderPassEnabled("DepthOnly", false); m.SetShaderPassEnabled("ShadowCaster", false);
                EditorUtility.SetDirty(m);
            });
            Make("WS_LedCyan", lit, m => Emissive(m, new Color(.1f, .2f, .22f), new Color(.25f, .95f, 1.1f) * 2.6f));
            Make("WS_ScreenCyan", lit, m => Emissive(m, new Color(.02f, .05f, .06f), new Color(.2f, .8f, 1f) * 1.6f));
            Make("WS_PanelDark", lit, m => SetupLit(m, "VH_SheetSteel", new Color(.22f, .23f, .245f), 1.2f, .9f));
            Make("WS_Deck", lit, m => SetupLit(m, "VH_SheetSteel", new Color(.32f, .31f, .3f), .8f, .7f));
            Make("WS_Canvas", lit, m =>
            {
                SetupLit(m, "VH_Linen", new Color(.62f, .3f, .2f), .9f, .55f, .8f);
                m.SetFloat("_Cull", 0); m.doubleSidedGI = true; EditorUtility.SetDirty(m);
            });
            Make("WS_Shutter", lit, m => SetupLit(m, "VH_Paint", new Color(.4f, .44f, .46f), 1.6f, .9f));
            Make("WS_Corrugated", lit, m => SetupLit(m, "VH_Rust", new Color(.56f, .47f, .42f), 2f, .8f));
            Make("WS_PaintTeal", lit, m => SetupLit(m, "VH_Paint", new Color(.24f, .42f, .44f), 1.4f, .9f));
            Make("WS_PaintRed", lit, m => SetupLit(m, "VH_Paint", new Color(.52f, .2f, .14f), 1.4f, .9f));
            Make("WS_CladTeal", lit, m => SetupLit(m, "VH_Paint", new Color(.3f, .45f, .46f), 1.6f, .9f));
            // sign family (30 Sep): worn dark steel box, graphite panel, amber channel letters, cyan status, red OPEN
            Make("WS_SignFrame", lit, m => SetupLit(m, "VH_Paint", new Color(.15f, .155f, .165f), .9f, .9f));
            Make("WS_SignPanel", lit, m => SetupLit(m, "VH_SheetSteel", new Color(.075f, .08f, .088f), .7f, .75f, .6f));
            Make("WS_SignRivet", lit, m => SetupLit(m, "VH_SheetSteel", new Color(.42f, .4f, .38f), .5f, 1f));
            Make("WS_SignReturn", lit, m => SetupLit(m, "VH_SheetSteel", new Color(.09f, .09f, .095f), .5f, .8f));
            Make("WS_SignDark", lit, m => SetupLit(m, null, new Color(.018f, .018f, .02f), 1f, .8f));
            Make("WS_SignLetter", lit, m => Emissive(m, new Color(.93f, .6f, .26f), new Color(1f, .56f, .19f) * 2.6f));
            Make("WS_SignRed", lit, m => Emissive(m, new Color(.45f, .07f, .05f), new Color(1f, .1f, .06f) * 3.2f));
            Make("WS_SignCyan", lit, m => Emissive(m, new Color(.1f, .2f, .22f), new Color(.25f, .95f, 1.1f) * 2.4f));
            // north avenue (30 Sep): door and trim paints, safety yellow, container rust, dyed cloth, hides, warm display LEDs
            Make("WS_PaintOlive", lit, m => SetupLit(m, "VH_Paint", new Color(.27f, .29f, .19f), 1.4f, .9f));
            Make("WS_PaintOchre", lit, m => SetupLit(m, "VH_Paint", new Color(.5f, .34f, .13f), 1.4f, .9f));
            Make("WS_PaintYellow", lit, m => SetupLit(m, "VH_Paint", new Color(.58f, .44f, .1f), 1.2f, .9f));
            Make("WS_ContainerRust", lit, m => SetupLit(m, "VH_Rust", new Color(.5f, .27f, .18f), 1.6f, .85f));
            void Cloth(string n, Color c, float smooth = .5f, float bump = .8f) => Make(n, lit, m =>
            {
                SetupLit(m, "VH_Linen", c, .7f, smooth, bump);
                m.SetFloat("_Cull", 0); m.doubleSidedGI = true; EditorUtility.SetDirty(m);
            });
            Cloth("WS_ClothIndigo", new Color(.13f, .17f, .33f));
            Cloth("WS_ClothOchre", new Color(.64f, .43f, .17f));
            Cloth("WS_ClothMadder", new Color(.5f, .15f, .1f));
            Cloth("WS_ClothBone", new Color(.76f, .7f, .58f));
            Cloth("WS_Hide", new Color(.44f, .29f, .18f), .35f, .45f);
            Make("WS_LedWarm", lit, m => Emissive(m, new Color(.3f, .22f, .15f), new Color(1f, .7f, .42f) * 2.2f));
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

        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static JObject Record(string key) => JObject.Parse(File.ReadAllText(ModelDir + key + ".json"));
        static JObject Record(Site s) => JObject.Parse(File.ReadAllText(s.RecordPath));

        // ------------------------------------------------------------------ prefabs
        [MenuItem("Athen Hill/Ward shops/Build assets")]
        public static void BuildAssets() => Build(false);

        [MenuItem("Athen Hill/Ward shops/Build assets (rebuild materials)")]
        public static void BuildAssetsRebuildMaterials() => Build(true);

        public static string Build(bool rebuildMaterials) => Build(rebuildMaterials, Sites);

        [MenuItem("Athen Hill/Ward shops/North avenue: build assets")]
        public static string BuildNorth() => Build(false, NorthSites);

        public static string Build(bool rebuildMaterials, Site[] sites)
        {
            foreach (var s in sites)
                foreach (var lod in new[] { 0, 1 })
                    AssetDatabase.ImportAsset(s.ModelPath(lod), ImportAssetOptions.ForceUpdate);
            var mats = BuildMaterials(rebuildMaterials);
            var log = new List<string>();
            foreach (var s in sites) log.Add(BuildPrefab(s, mats));
            AssetDatabase.SaveAssets();
            return string.Join("\n", log);
        }

        static string BuildPrefab(Site s, Dictionary<string, Material> mats)
        {
            Directory.CreateDirectory(PrefabDir);
            var rec = Record(s);
            var root = new GameObject(s.model);
            var missing = new HashSet<string>();
            int lamps = 0;
            try
            {
                var levels = new List<LOD>();
                foreach (var (lod, cut) in new[] { (0, Lod0ScreenHeight), (1, .01f) })
                {
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(s.ModelPath(lod));
                    if (!model) throw new Exception($"Model not imported: {s.model} LOD{lod}");
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
                    inst.transform.SetParent(root.transform, false);
                    inst.name = "LOD" + lod;
                    var rs = new List<Renderer>();
                    foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                    {
                        var slots = r.sharedMaterials;
                        for (int i = 0; i < slots.Length; i++)
                        {
                            var m = slots[i] ? Lookup(mats, slots[i].name) : null;
                            if (m) slots[i] = m; else missing.Add(r.name + ":" + (slots[i] ? slots[i].name : "null"));
                        }
                        r.sharedMaterials = slots;
                        bool noShadow = r.name.Contains("_Glass_") || r.name.Contains("_Sand_") || r.name.Contains("_Glow_") || r.name.Contains("_Display_");
                        r.shadowCastingMode = noShadow ? ShadowCastingMode.Off : ShadowCastingMode.On;
                        r.receiveShadows = true;
                        if (r is MeshRenderer mr) { mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; mr.receiveGI = ReceiveGI.LightProbes; }
                        rs.Add(r);
                    }
                    levels.Add(new LOD(cut, rs.ToArray()));
                }
                var group = root.AddComponent<LODGroup>();
                group.SetLODs(levels.ToArray());
                group.fadeMode = LODFadeMode.None;
                group.RecalculateBounds();

                var cols = new GameObject("Colliders").transform; cols.SetParent(root.transform, false);
                foreach (var c in rec["colliders"])
                {
                    var go = new GameObject((string)c["name"]); go.transform.SetParent(cols, false);
                    var b = go.AddComponent<BoxCollider>(); b.center = V3(c["center"]); b.size = V3(c["size"]);
                }

                var fit = new GameObject("Fittings").transform; fit.SetParent(root.transform, false);
                var lights = new GameObject("Practical lights").transform; lights.SetParent(root.transform, false);
                foreach (var mnt in rec["mounts"] ?? new JArray())
                {
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/WestGate/" + (string)mnt["prefab"] + ".prefab");
                    if (!prefab) { Debug.LogWarning("Ward shops: missing prefab " + mnt["prefab"]); continue; }
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    go.name = (string)mnt["name"];
                    go.transform.SetParent(fit, false);
                    go.transform.localPosition = V3(mnt["pos"]);
                    go.transform.localRotation = Quaternion.Euler(0, (float)mnt["yaw"], 0);
                    foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                    if ((string)mnt["prefab"] != "PH_WallLamp") continue;
                    var bulb = GameObject.CreatePrimitive(PrimitiveType.Sphere); bulb.name = "Bulb";
                    UnityEngine.Object.DestroyImmediate(bulb.GetComponent<Collider>());
                    bulb.transform.SetParent(go.transform, false); bulb.transform.localPosition = new Vector3(0, .215f, .015f); bulb.transform.localScale = Vector3.one * .07f;
                    var br = bulb.GetComponent<MeshRenderer>(); br.sharedMaterial = mats["VH_LampLens"]; br.shadowCastingMode = ShadowCastingMode.Off;
                    var lg = new GameObject(go.name + " light"); lg.transform.SetParent(lights, false);
                    var fwd = go.transform.localRotation * Vector3.forward;
                    lg.transform.localPosition = go.transform.localPosition + Vector3.up * .215f + fwd * .2f;
                    var l = lg.AddComponent<Light>(); l.type = LightType.Point; l.color = new Color(1f, .78f, .52f); l.intensity = 4.2f; l.range = 7.5f; l.shadows = LightShadows.None;
                    lamps++;
                }

                // sign mounts (filled by the sign pass) and the Tool Exchange display
                var signs = new GameObject("Sign mounts").transform; signs.SetParent(root.transform, false);
                foreach (var sg in rec["signs"] ?? new JArray())
                {
                    var go = new GameObject("Sign mount: " + (string)sg["text"]); go.transform.SetParent(signs, false);
                    go.transform.localPosition = V3(sg["centre"]);
                }
                if (rec["display"] is JObject disp && disp.HasValues)
                {
                    var d = new GameObject("Display").transform; d.SetParent(root.transform, false);
                    foreach (var p in disp["props"])
                    {
                        var go = new GameObject("Prop mount: " + (string)p["name"]); go.transform.SetParent(d, false);
                        go.transform.localPosition = V3(p["pos"]); go.transform.localRotation = Quaternion.Euler(0, (float)p["yaw"], 0);
                    }
                    var lgo = new GameObject("Display light"); lgo.transform.SetParent(lights, false);
                    var lp = V3(disp["light"]["pos"]); lgo.transform.localPosition = lp;
                    lgo.transform.localRotation = Quaternion.LookRotation(V3(disp["light"]["target"]) - lp, Vector3.forward);
                    var l = lgo.AddComponent<Light>(); l.type = LightType.Spot; l.color = new Color(.78f, .92f, 1f); l.intensity = 5f; l.range = 3.2f;
                    if (disp["light"]["color"] is JArray lc) l.color = new Color((float)lc[0], (float)lc[1], (float)lc[2]);
                    if (disp["light"]["intensity"] != null) l.intensity = (float)disp["light"]["intensity"];
                    if (disp["light"]["range"] != null) l.range = (float)disp["light"]["range"];
                    l.spotAngle = 115f; l.innerSpotAngle = 70f; l.shadows = LightShadows.None;
                }

                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (!t.GetComponent<Light>())
                        GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + s.model + ".prefab");
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
            if (missing.Count > 0) Debug.LogWarning($"Ward shops {s.model}: unmapped materials: " + string.Join(", ", missing));
            return $"{s.model}: prefab saved, lamps {lamps}, unmapped {missing.Count} {string.Join(",", missing.Take(6))}";
        }

        // ------------------------------------------------------------------ install
        public sealed class Plan
        {
            public List<(Site site, string path, string why)> retire = new List<(Site, string, string)>();
            public List<(Site site, string path, string why)> keep = new List<(Site, string, string)>();
        }

        public static Plan MakePlan() => MakePlan(Sites);

        public static Plan MakePlan(Site[] sites)
        {
            var Sites = sites;      // the parcel sweep below runs over the given sites only
            var plan = new Plan();
            var seen = new HashSet<GameObject>();
            foreach (var s in Sites)
                foreach (var p in s.retire)
                    foreach (var t in FindRetire(p))
                        if (t && t.gameObject.activeSelf && seen.Add(t.gameObject)) plan.retire.Add((s, PathOf(t), "root"));
            bool UnderRetired(Transform t) { for (; t; t = t.parent) if (seen.Contains(t.gameObject)) return true; return false; }
            void Consider(Component c, Vector3 world, Bounds wb, string kind)
            {
                var go = c.gameObject;
                if (!go.activeInHierarchy || UnderRetired(go.transform)) return;
                var path = PathOf(go.transform);
                bool retrofitLight = path.StartsWith("Ward district retrofit/") && kind == "light";
                if (IsProtected(path) || (path.StartsWith("Ward district retrofit/") && !retrofitLight)) return;
                foreach (var s in Sites)
                {
                    if (!InParcel(s, world, wb, out var zone)) continue;
                    if (zone == "porch" && (path.Contains("props") || path.StartsWith("Post-war salvage/"))) return;   // loose props stay whole
                    if (go.GetComponent<Camera>() || path.StartsWith("cam_")) return;
                    if (seen.Add(go)) plan.retire.Add((s, path, zone + " " + kind));
                    return;
                }
            }
            foreach (var r in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
                if (!(r is ParticleSystemRenderer)) Consider(r, r.bounds.center, r.bounds, "renderer");
            foreach (var l in UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
                if (l.type != LightType.Directional) Consider(l, l.transform.position, new Bounds(l.transform.position, Vector3.one * .1f), "light");
            foreach (var d in UnityEngine.Object.FindObjectsByType<DecalProjector>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
                Consider(d, d.transform.position, new Bounds(d.transform.position, d.size), "decal");
            foreach (var a in UnityEngine.Object.FindObjectsByType<AudioSource>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var path = PathOf(a.transform);
                foreach (var s in Sites) if (InParcel(s, a.transform.position, new Bounds(a.transform.position, Vector3.one * .1f), out var z)) plan.keep.Add((s, path, "audio " + z));
            }
            foreach (var c in UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (UnderRetired(c.transform)) continue;
                var path = PathOf(c.transform);
                foreach (var s in Sites) if (InParcel(s, c.bounds.center, c.bounds, out var z)) plan.keep.Add((s, path, "collider " + z + " " + c.GetType().Name));
            }
            return plan;
        }

        [MenuItem("Athen Hill/Ward shops/Dry-run install")]
        public static string DryRun() => DryRun(Sites, Evidence);

        [MenuItem("Athen Hill/Ward shops/North avenue: dry-run install")]
        public static string DryRunNorth() => DryRun(NorthSites, NorthEvidence);

        static string DryRun(Site[] sites, string evidence)
        {
            var plan = MakePlan(sites);
            Directory.CreateDirectory(evidence);
            var lines = plan.retire.Select(r => $"RETIRE [{r.site.key}] {r.why} :: {r.path}").Concat(plan.keep.Select(k => $"KEEP   [{k.site.key}] {k.why} :: {k.path}"));
            File.WriteAllLines(evidence + "shops-install-dryrun.txt", lines);
            return $"retire {plan.retire.Count}, keep-report {plan.keep.Count} -> {evidence}shops-install-dryrun.txt";
        }

        static Mesh FilteredRetrofit(MeshFilter mf, out int removed) => FilteredRetrofit(mf.sharedMesh, mf.transform, out removed);
        static Mesh FilteredRetrofit(Mesh src, Transform tr, out int removed) => FilteredRetrofit(src, tr, Sites, out removed);

        /// Copy of a combined mesh without the triangles inside the shop parcels. The retrofit meshes use 16-bit
        /// indices with a base vertex per submesh, so indices are read and written relative to that base.
        static Mesh FilteredRetrofit(Mesh src, Transform tr, Site[] Sites, out int removed)
        {
            // fresh 32-bit mesh with every vertex channel copied and absolute indices (the glTF originals are 16-bit
            // with a base vertex per submesh; rewriting those in place produced wrapped/garbled triangles)
            var vs = src.vertices;
            var m = new Mesh { name = src.name + (Sites == WardShopsPass.Sites ? " (hall district shops removed)" : " (north avenue shops removed)"), indexFormat = IndexFormat.UInt32 };
            m.SetVertices(vs);
            if (src.normals.Length == vs.Length) m.SetNormals(src.normals);
            if (src.tangents.Length == vs.Length) m.SetTangents(src.tangents);
            if (src.colors32.Length == vs.Length) m.SetColors(src.colors32);
            for (int ch = 0; ch < 8; ch++)
            {
                var uv = new List<Vector4>(); src.GetUVs(ch, uv);
                if (uv.Count == vs.Length) m.SetUVs(ch, uv);
            }
            m.subMeshCount = src.subMeshCount;
            removed = 0;
            // connected pieces (vertices welded by position, across submeshes): a piece goes when a quarter of its
            // triangles, or its centre, lies in a parcel, so struts and posts do not leave slivers behind
            var parent = new int[vs.Length];
            for (int i = 0; i < parent.Length; i++) parent[i] = i;
            int Find(int a) { while (parent[a] != a) { parent[a] = parent[parent[a]]; a = parent[a]; } return a; }
            void Union(int a, int b) { a = Find(a); b = Find(b); if (a != b) parent[b] = a; }
            var weld = new Dictionary<Vector3Int, int>();
            for (int i = 0; i < vs.Length; i++)
            {
                var k = Vector3Int.RoundToInt(vs[i] * 1000f);
                if (weld.TryGetValue(k, out int j)) Union(j, i); else weld[k] = i;
            }
            var subTris = new List<int[]>();
            for (int sub = 0; sub < src.subMeshCount; sub++)
            {
                var tris = src.GetTriangles(sub, true);
                subTris.Add(tris);
                for (int i = 0; i < tris.Length; i += 3) { Union(tris[i], tris[i + 1]); Union(tris[i], tris[i + 2]); }
            }
            var inside = new Dictionary<int, int>(); var total = new Dictionary<int, int>(); var boxes = new Dictionary<int, Bounds>();
            foreach (var tris in subTris)
                for (int i = 0; i < tris.Length; i += 3)
                {
                    int r = Find(tris[i]);
                    var c = tr.TransformPoint((vs[tris[i]] + vs[tris[i + 1]] + vs[tris[i + 2]]) / 3f);
                    total[r] = total.TryGetValue(r, out int t0) ? t0 + 1 : 1;
                    if (Sites.Any(s => InParcel(s, c, new Bounds(c, Vector3.one * .01f), out _))) inside[r] = inside.TryGetValue(r, out int n0) ? n0 + 1 : 1;
                    if (boxes.TryGetValue(r, out var bb)) { bb.Encapsulate(c); boxes[r] = bb; } else boxes[r] = new Bounds(c, Vector3.zero);
                }
            var drop = new HashSet<int>();
            foreach (var kv in total)
            {
                inside.TryGetValue(kv.Key, out int n);
                var bc = boxes[kv.Key].center;
                if (n >= Mathf.Max(1, kv.Value / 4) || Sites.Any(s => InParcel(s, bc, boxes[kv.Key], out _))) drop.Add(kv.Key);
            }
            for (int sub = 0; sub < src.subMeshCount; sub++)
            {
                var tris = subTris[sub];
                var keep = new List<int>(tris.Length);
                for (int i = 0; i < tris.Length; i += 3)
                {
                    if (drop.Contains(Find(tris[i]))) { removed++; continue; }
                    keep.Add(tris[i]); keep.Add(tris[i + 1]); keep.Add(tris[i + 2]);
                }
                m.SetTriangles(keep, sub, false, 0);
            }
            m.RecalculateBounds();
            return m;
        }

        [MenuItem("Athen Hill/Ward shops/Install rebuilt shops")]
        public static string Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath);
            if (scene.GetRootGameObjects().Any(g => g.name == GroupName)) throw new Exception("Ward shops are already installed; edit them in place.");
            if (scene.isDirty) throw new Exception("Save or discard scene changes before installing.");
            Directory.CreateDirectory(Evidence + "rollback");
            File.Copy(ScenePath, Evidence + "rollback/before-shops-install.unity", true);

            var plan = MakePlan();
            var report = new Dictionary<string, object>();
            var retired = new List<object>();
            foreach (var (site, path, why) in plan.retire)
            {
                var t = FindPath(path);
                if (!t) continue;
                Undo.RecordObject(t.gameObject, "Retire shop layer");
                t.gameObject.SetActive(false);
                retired.Add(new { site = site.key, path, why });
            }
            report["retired"] = retired;

            // district retrofit: filtered copies of the combined meshes (originals kept as assets)
            Directory.CreateDirectory(RetrofitDir);
            var retro = new List<object>();
            foreach (var p in RetrofitMeshes)
            {
                var t = FindPath(p);
                var mf = t ? t.GetComponent<MeshFilter>() : null;
                if (!mf || !mf.sharedMesh) { retro.Add(new { path = p, found = false }); continue; }
                var original = mf.sharedMesh;
                var copy = FilteredRetrofit(mf, out int removed);
                var assetPath = RetrofitDir + t.name.Replace(' ', '_') + "_hall_district.asset";
                AssetDatabase.CreateAsset(copy, assetPath);
                Undo.RecordObject(mf, "Filter retrofit mesh");
                mf.sharedMesh = copy;
                var mc = t.GetComponent<MeshCollider>();
                if (mc && mc.sharedMesh == original) mc.sharedMesh = copy;
                retro.Add(new { path = p, removedTriangles = removed, original = AssetDatabase.GetAssetPath(original) + "#" + original.name, filtered = assetPath });
            }
            report["retrofit"] = retro;

            var group = new GameObject(GroupName);
            SceneManagerMove(group, scene);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var installed = new List<object>();
            foreach (var s in Sites)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabDir + s.model + ".prefab");
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.name = s.name;
                go.transform.SetParent(group.transform, false);
                go.transform.SetPositionAndRotation(s.pos, Quaternion.Euler(0, s.yaw, 0));
                var ls = go.GetComponentsInChildren<Light>(true);
                var lamps = ls.Where(l => l.name != "Display light").ToArray();
                circuit.practicalLights = circuit.practicalLights.Where(l => l && !l.transform.IsChildOf(go.transform)).Concat(ls).ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !l.transform.IsChildOf(go.transform)).Concat(lamps).ToArray();
                installed.Add(new { site = s.key, s.name, pos = new[] { s.pos.x, s.pos.y, s.pos.z }, s.yaw, lights = ls.Length });
            }
            foreach (var em in new[] { "WS_Glass" })
            {
                var mat = AssetDatabase.LoadAssetAtPath<Material>(MatDir + em + ".mat");
                if (mat && !circuit.emissiveMaterials.Contains(mat)) circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { mat }).ToArray();
            }
            EditorUtility.SetDirty(circuit);
            report["installed"] = installed;

            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            report["chunksRebuilt"] = chunks != null;

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Evidence + "shops-install.json", JsonConvert.SerializeObject(report, Formatting.Indented));
            return $"installed {installed.Count} shops, retired {retired.Count} objects, retrofit meshes {retro.Count}";
        }

        /// Rebuilds the filtered retrofit meshes from the original GLB sub-assets (fixes the first install, which
        /// flattened the 16-bit per-submesh indices) and retires retrofit bin colliders inside the parcels.
        public static string RepairRetrofit()
        {
            var log = new List<string>();
            var originals = AssetDatabase.LoadAllAssetsAtPath("Assets/AthenHill/Art/WardRetrofit/WardRetrofit.glb").OfType<Mesh>().ToList();
            foreach (var p in RetrofitMeshes)
            {
                var t = FindPath(p);
                var mf = t ? t.GetComponent<MeshFilter>() : null;
                var src = originals.FirstOrDefault(m => m.name == t.name);
                if (!mf || !src) { log.Add(p + ": missing"); continue; }
                var fixedMesh = FilteredRetrofit(src, t, out int removed);
                var assetPath = RetrofitDir + t.name.Replace(' ', '_') + "_hall_district.asset";
                if (AssetDatabase.LoadAssetAtPath<Mesh>(assetPath)) AssetDatabase.DeleteAsset(assetPath);
                AssetDatabase.CreateAsset(fixedMesh, assetPath);
                mf.sharedMesh = fixedMesh;
                int keptTris = 0; for (int sub = 0; sub < fixedMesh.subMeshCount; sub++) keptTris += (int)fixedMesh.GetIndexCount(sub) / 3;
                int srcTris = 0; for (int sub = 0; sub < src.subMeshCount; sub++) srcTris += (int)src.GetIndexCount(sub) / 3;
                log.Add($"{p}: source {srcTris} tris, removed {removed}, kept {keptTris}, sub {fixedMesh.subMeshCount}, fmt {fixedMesh.indexFormat}, bounds {fixedMesh.bounds.size}");
            }
            var retro = FindPath("Ward district retrofit/Shop retrofits");
            foreach (Transform c in retro)
            {
                if (!c.name.StartsWith("COL_") || !c.gameObject.activeSelf) continue;
                var col = c.GetComponent<Collider>();
                var center = col ? col.bounds.center : c.position;
                if (Sites.Any(s => InParcel(s, center, new Bounds(center, Vector3.one * .1f), out _)))
                { Undo.RecordObject(c.gameObject, "Retire retrofit collider"); c.gameObject.SetActive(false); log.Add("retired collider " + c.name); }
            }
            AssetDatabase.SaveAssets();
            var scene = EditorSceneManager.GetActiveScene();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.AppendAllText(Evidence + "shops-install-repair.txt", string.Join("\n", log) + "\n");
            return string.Join("\n", log);
        }


        // ------------------------------------------------------------------ kept Air + Water filter bank
        static bool KeptStoragePart(string n) => n.Contains("Feed masonry anchor") || n.Contains("Feed stand-off") ||
                                                  n.Contains("Feed retaining clamp") || n.Contains("Filter manifold inlet");

        /// The accepted 29 Sep filter fittings mount on vessels, retainers and riser anchors that live inside the air_water
        /// shop prefab instance (children of a prefab instance cannot be reparented). The instance is re-activated with
        /// every child switched off except the filter bank and the riser anchors, as instance overrides.
        [MenuItem("Athen Hill/Ward shops/Keep Air + Water filter bank")]
        public static string KeepAirWaterFilterBank()
        {
            var arch = FindPath("Ward shop architecture");
            var aw = FindPath("Ward shop architecture/air_water");
            if (!arch || !aw) throw new Exception("Ward shop architecture/air_water missing");
            var empty = arch.Find("Air + Water filter bank (kept from air_water)");
            if (empty && empty.childCount == 0) UnityEngine.Object.DestroyImmediate(empty.gameObject);
            var kept = new List<string>();
            aw.gameObject.SetActive(true);
            foreach (Transform c in aw)
            {
                bool keep = c.name == "Front filter bank" || c.name == "Water storage and filtration";
                c.gameObject.SetActive(keep);
                if (c.name == "Water storage and filtration")
                    foreach (Transform g in c) { g.gameObject.SetActive(KeptStoragePart(g.name)); if (KeptStoragePart(g.name)) kept.Add(g.name); }
                if (c.name == "Front filter bank") kept.Add(c.name);
                PrefabUtility.RecordPrefabInstancePropertyModifications(c.gameObject);
            }
            PrefabUtility.RecordPrefabInstancePropertyModifications(aw.gameObject);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            var scene = EditorSceneManager.GetActiveScene();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Evidence + "shops-kept-filter-bank.json", JsonConvert.SerializeObject(kept, Formatting.Indented));
            return "kept " + kept.Count;
        }

        // ------------------------------------------------------------------ Tool Exchange display props (Meshy)
        const string PropDir = Root + "ToolExchangeProps/";

        /// Fits the Meshy props (meshy/tool-exchange-scifi-20260930) into the Tool Exchange prefab's display mounts:
        /// uniform scale to the planned size, base (or centre for the wall set) on the mount, shadows on, no colliders.
        [MenuItem("Athen Hill/Ward shops/Fit Tool Exchange display props")]
        public static string FitDisplayProps()
        {
            var rec = Record("tool_exchange");
            var path = PrefabDir + "ToolExchange.prefab";
            var root = PrefabUtility.LoadPrefabContents(path);
            var log = new List<string>();
            try
            {
                var display = root.transform.Find("Display");
                foreach (var p in rec["display"]["props"])
                {
                    var name = (string)p["name"];
                    var mount = display.Find("Prop mount: " + name);
                    mount.localPosition = V3(p["pos"]); mount.localRotation = Quaternion.Euler(0, (float)p["yaw"], 0);
                    foreach (Transform c in mount.Cast<Transform>().ToArray()) UnityEngine.Object.DestroyImmediate(c.gameObject);
                    AssetDatabase.ImportAsset(PropDir + $"TE_{name}.glb", ImportAssetOptions.ForceUpdate);
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(PropDir + $"TE_{name}.glb");
                    if (!model) { log.Add(name + ": model missing"); continue; }
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
                    inst.name = "TE " + name;
                    inst.transform.SetParent(mount, false);
                    inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity; inst.transform.localScale = Vector3.one;
                    var rs = inst.GetComponentsInChildren<Renderer>(true);
                    // measure with the mount unrotated so the box is the prop's own (a yawed AABB inflates it)
                    var mountRot = mount.localRotation; mount.localRotation = Quaternion.identity;
                    Bounds Measure() { var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds); return bb; }
                    var b = Measure();
                    var target = V3(p["size"]);
                    // fit by the dimension that defines each prop (bench/wall/drone/cutter width, arm height)
                    float k = name == "servo_arm" ? target.y / b.size.y : target.x / b.size.x;
                    inst.transform.localScale = Vector3.one * k;
                    b = Measure();
                    var lc = mount.InverseTransformPoint(b.center);
                    var shift = name == "tool_wall" ? -lc : new Vector3(-lc.x, -(lc.y - b.extents.y), -lc.z);
                    inst.transform.localPosition = shift;
                    mount.localRotation = mountRot;
                    foreach (var r in rs) { r.shadowCastingMode = ShadowCastingMode.On; if (r is MeshRenderer mr) mr.receiveGI = ReceiveGI.LightProbes; }
                    foreach (var c in inst.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                    b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                    log.Add($"{name}: scale {k:F3}, size {b.size:F2}");
                }
                // steel backboard for the loose tool set
                var wall = display.Find("Prop mount: tool_wall");
                var board = GameObject.CreatePrimitive(PrimitiveType.Cube); board.name = "Tool wall backboard";
                UnityEngine.Object.DestroyImmediate(board.GetComponent<Collider>());
                board.transform.SetParent(wall, false); board.transform.localPosition = new Vector3(0, 0, -.08f); board.transform.localScale = new Vector3(1.3f, .95f, .03f);
                board.GetComponent<MeshRenderer>().sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "WS_PanelDark.mat");
                var strip = GameObject.CreatePrimitive(PrimitiveType.Cube); strip.name = "Charging rail light";
                UnityEngine.Object.DestroyImmediate(strip.GetComponent<Collider>());
                strip.transform.SetParent(wall, false); strip.transform.localPosition = new Vector3(0, -.44f, -.05f); strip.transform.localScale = new Vector3(1.2f, .015f, .02f);
                strip.GetComponent<MeshRenderer>().sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "WS_LedCyan.mat");
                PrefabUtility.SaveAsPrefabAsset(root, path);
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            File.WriteAllText(Evidence + "tool-exchange-props.txt", string.Join("\n", log));
            return string.Join("\n", log);
        }


        // ------------------------------------------------------------------ signs
        const string SignDir = Root + "Signs/";
        const string SignPrefabDir = PrefabDir + "Signs/";
        public const string BasicGeneralSignName = "Basic General sign (hall district family)";
        static readonly Dictionary<string, string> SignText = new Dictionary<string, string>
        {
            ["relay_works"] = "RELAY WORKS", ["air_water"] = "AIR + WATER", ["tool_exchange"] = "TOOL EXCHANGE",
            ["finery"] = "FINERY", ["field_supply"] = "FIELD SUPPLY",
            ["salvage"] = "SALVAGE", ["repairs"] = "REPAIRS", ["thread_hide"] = "THREAD + HIDE",
        };

        static GameObject BuildSignPrefab(string key, Dictionary<string, Material> mats)
        {
            Directory.CreateDirectory(SignPrefabDir);
            AssetDatabase.ImportAsset(SignDir + $"Sign_{key}.glb", ImportAssetOptions.ForceUpdate);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(SignDir + $"Sign_{key}.glb");
            if (!model) throw new Exception("Sign model missing: " + key);
            var root = new GameObject("Sign " + key);
            try
            {
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
                inst.transform.SetParent(root.transform, false);
                var rs = new List<Renderer>();
                foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                {
                    var slots = r.sharedMaterials;
                    for (int i = 0; i < slots.Length; i++) { var m = slots[i] ? Lookup(mats, slots[i].name) : null; if (m) slots[i] = m; }
                    r.sharedMaterials = slots;
                    r.shadowCastingMode = r.name.Contains("_Glow") ? ShadowCastingMode.Off : ShadowCastingMode.On;
                    if (r is MeshRenderer mr) mr.receiveGI = ReceiveGI.LightProbes;
                    rs.Add(r);
                }
                var g = root.AddComponent<LODGroup>();
                g.SetLODs(new[] { new LOD(.012f, rs.ToArray()) }); g.RecalculateBounds();
                return PrefabUtility.SaveAsPrefabAsset(root, SignPrefabDir + $"Sign_{key}.prefab");
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        /// Builds the sign prefabs, mounts one on each shop prefab's sign mount (prefab contents edit, so the installed
        /// instances keep their light bindings), swaps the Basic General sign (the 29 Sep baked plate stays inactive)
        /// and puts the emissive sign materials on the city light clock.
        [MenuItem("Athen Hill/Ward shops/Install signs")]
        public static string InstallSigns()
        {
            var mats = BuildMaterials(false);
            var log = new List<string>();
            foreach (var kv in SignText)
            {
                var prefab = BuildSignPrefab(kv.Key, mats);
                var site = Sites.Concat(NorthSites).First(x => x.key == kv.Key);
                var path = PrefabDir + site.model + ".prefab";
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var mount = root.transform.Find("Sign mounts/Sign mount: " + kv.Value);
                    if (!mount) { log.Add(kv.Key + ": mount missing"); continue; }
                    foreach (Transform c in mount.Cast<Transform>().ToArray()) UnityEngine.Object.DestroyImmediate(c.gameObject);
                    var s = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    s.transform.SetParent(mount, false); s.transform.localPosition = Vector3.zero; s.transform.localRotation = Quaternion.identity;
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    log.Add(kv.Key + ": sign mounted");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            var bgPrefab = BuildSignPrefab("basic_general", mats);
            var scene = EditorSceneManager.GetActiveScene();
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Basic General neon sign");
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == BasicGeneralSignName);
            if (existing) UnityEngine.Object.DestroyImmediate(existing);
            var bg = (GameObject)PrefabUtility.InstantiatePrefab(bgPrefab, scene);
            bg.name = BasicGeneralSignName;
            // the baked plate was centred at z 16.942 with 0.158 thickness: its back (the booth fascia) is at 16.863
            bg.transform.SetPositionAndRotation(new Vector3(8.0f, 2.72f, 16.863f), Quaternion.identity);
            if (old) old.SetActive(false);
            log.Add("basic general: sign swapped, old plate " + (old ? "inactive" : "missing"));
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            foreach (var em in new[] { "WS_SignLetter", "WS_SignRed", "WS_SignCyan" })
                if (mats.TryGetValue(em, out var mat) && !circuit.emissiveMaterials.Contains(mat)) circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { mat }).ToArray();
            EditorUtility.SetDirty(circuit);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            File.WriteAllText(Evidence + "signs-install.txt", string.Join("\n", log));
            return string.Join("\n", log);
        }


        // ------------------------------------------------------------------ refresh after source changes
        /// Re-imports the shop and sign GLBs (the installed prefab instances pick up the new meshes; the prefabs are not
        /// rebuilt, so their light bindings stay) and applies the grime / sign / glass material tuning.
        [MenuItem("Athen Hill/Ward shops/Refresh models and materials")]
        public static string RefreshModels()
        {
            foreach (var s in Sites.Concat(NorthSites))
                foreach (var lod in new[] { 0, 1 }) AssetDatabase.ImportAsset(s.ModelPath(lod), ImportAssetOptions.ForceUpdate);
            foreach (var g in AssetDatabase.FindAssets("Sign_", new[] { SignDir.TrimEnd('/') }))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                if (path.EndsWith(".glb")) AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            }
            var mats = BuildMaterials(false);
            // letters keep their amber at night (the first pass blew out to white), OPEN reads red, cyan stays an accent
            mats["WS_SignLetter"].SetColor("_BaseColor", new Color(.86f, .5f, .17f));
            mats["WS_SignLetter"].SetColor("_EmissionColor", new Color(1f, .4f, .07f) * 1.35f);
            mats["WS_SignRed"].SetColor("_EmissionColor", new Color(1f, .07f, .035f) * 2.4f);
            mats["WS_SignCyan"].SetColor("_EmissionColor", new Color(.25f, .95f, 1.1f) * 1.6f);
            mats["WS_SignFrame"].SetColor("_BaseColor", new Color(.14f, .13f, .12f));
            mats["WS_ClearGlass"].SetColor("_BaseColor", new Color(.6f, .7f, .72f, .05f)); mats["WS_ClearGlass"].SetFloat("_Smoothness", .86f);
            // steel and paint a little grimier, as the West Gate's blackened bands
            foreach (var (n, c) in new[] { ("WS_Shutter", new Color(.34f, .36f, .36f)), ("WS_PaintTeal", new Color(.2f, .34f, .35f)),
                                           ("WS_PaintRed", new Color(.42f, .17f, .12f)), ("WS_Corrugated", new Color(.46f, .38f, .33f)),
                                           ("WS_Canvas", new Color(.54f, .27f, .18f)) })
                mats[n].SetColor("_BaseColor", c);
            foreach (var m in mats.Values) EditorUtility.SetDirty(m);
            AssetDatabase.SaveAssets();
            var remapped = Sites.Concat(NorthSites).Select(x => x.model + " " + RemapPrefabMaterials(x, mats)).ToArray();
            return "refreshed " + (Sites.Length + NorthSites.Length) + " shops and signs; material slots re-mapped: " + string.Join(", ", remapped);
        }

        /// The prefab stores one material per sub-mesh slot. When a re-authored model gains or loses a material (the Repairs gas
        /// cage, 30 Sep: WS_PaintYellow/Teal/Red), the imported sub-mesh order shifts under the stored slots and surfaces pick up
        /// the wrong material (its roller shutter rendered in yellow paint). Re-map every slot from the model's own names.
        public static int RemapPrefabMaterials(Site s, Dictionary<string, Material> mats)
        {
            var path = PrefabDir + s.model + ".prefab";
            if (!File.Exists(path)) return -1;
            var root = PrefabUtility.LoadPrefabContents(path);
            int changed = 0;
            try
            {
                foreach (var lod in new[] { 0, 1 })
                {
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(s.ModelPath(lod));
                    var lodRoot = root.transform.Find("LOD" + lod);
                    if (!model || !lodRoot) continue;
                    var dsts = lodRoot.GetComponentsInChildren<Renderer>(true);
                    foreach (var src in model.GetComponentsInChildren<Renderer>(true))
                    {
                        var dst = dsts.FirstOrDefault(r => r.name == src.name);
                        if (!dst) continue;
                        var slots = src.sharedMaterials.Select(m => m ? (Lookup(mats, m.name) ?? m) : null).ToArray();
                        if (!slots.SequenceEqual(dst.sharedMaterials)) { dst.sharedMaterials = slots; changed++; }
                    }
                }
                if (changed > 0) PrefabUtility.SaveAsPrefabAsset(root, path);
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            return changed;
        }

        /// Finery's old ochre street canopy (Courtyard reference pass) hung off the old frontage; retire it by name
        /// wherever it sits in the hierarchy.
        public static string RetireFineryCanopy()
        {
            var log = new List<string>();
            foreach (var t in UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (t.name == "Ochre red courtyard awning" || t.name.StartsWith("Canopy side spar") || t.name.StartsWith("Canopy diagonal brace") ||
                    t.name.StartsWith("Awning edge rope") || t.name.StartsWith("Stitched panel seam") || t.name.StartsWith("Frayed canvas fibre") ||
                    t.name.StartsWith("Finery canopy"))
                {
                    var g = t.parent && (t.parent.name == "Canopy" || t.parent.name == "Awning hardware" || t.parent.name.StartsWith("Canopy revision")) ? t.parent : t;
                    if (!g.gameObject.activeSelf) continue;
                    log.Add(PathOf(g)); g.gameObject.SetActive(false);
                    if (PrefabUtility.IsPartOfPrefabInstance(g)) PrefabUtility.RecordPrefabInstancePropertyModifications(g.gameObject);
                }
            }
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            var scene = EditorSceneManager.GetActiveScene();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Evidence + "shops-finery-canopy-retired.txt", string.Join("\n", log.Distinct()));
            return string.Join("\n", log.Distinct());
        }

        // ------------------------------------------------------------------ north avenue (30 Sep 2026)
        static void Retire(Transform t)
        {
            Undo.RecordObject(t.gameObject, "Retire north avenue layer");
            t.gameObject.SetActive(false);
            if (PrefabUtility.IsPartOfPrefabInstance(t.gameObject)) PrefabUtility.RecordPrefabInstancePropertyModifications(t.gameObject);
        }

        /// One-time install of Salvage, Repairs, Thread + Hide and the Basic General booth: retires the replaced layers
        /// (inactive, not deleted), filters the combined retrofit meshes again for the three shop parcels (new copies; the
        /// hall-district copies stay as assets), retires retrofit colliders in those parcels, instantiates the prefabs under
        /// their own group, puts their lamps on the Ward lighting clock and rebuilds the render chunks.
        [MenuItem("Athen Hill/Ward shops/North avenue: install (one-time)")]
        public static string InstallNorth()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath);
            if (scene.GetRootGameObjects().Any(g => g.name == NorthGroupName)) throw new Exception("North avenue shops are already installed; edit them in place.");
            if (scene.isDirty) throw new Exception("Save or discard scene changes before installing.");
            Directory.CreateDirectory(NorthEvidence + "rollback");
            File.Copy(ScenePath, NorthEvidence + "rollback/before-north-install.unity", true);

            var plan = MakePlan(NorthSites);
            var report = new Dictionary<string, object>();
            var retired = new List<object>();
            foreach (var (site, path, why) in plan.retire)
            {
                var t = FindPath(path);
                if (!t) continue;
                Retire(t);
                retired.Add(new { site = site.key, path, why });
            }
            report["retired"] = retired;

            Directory.CreateDirectory(RetrofitDir);
            var retro = new List<object>();
            foreach (var p in RetrofitMeshes)
            {
                var t = FindPath(p);
                var mf = t ? t.GetComponent<MeshFilter>() : null;
                if (!mf || !mf.sharedMesh) { retro.Add(new { path = p, found = false }); continue; }
                var before = mf.sharedMesh;
                var copy = FilteredRetrofit(before, t, NorthSites, out int removed);
                var assetPath = RetrofitDir + t.name.Replace(' ', '_') + "_north_avenue.asset";
                if (AssetDatabase.LoadAssetAtPath<Mesh>(assetPath)) AssetDatabase.DeleteAsset(assetPath);
                AssetDatabase.CreateAsset(copy, assetPath);
                Undo.RecordObject(mf, "Filter retrofit mesh");
                mf.sharedMesh = copy;
                var mc = t.GetComponent<MeshCollider>();
                if (mc && mc.sharedMesh == before) mc.sharedMesh = copy;
                retro.Add(new { path = p, removedTriangles = removed, before = AssetDatabase.GetAssetPath(before), filtered = assetPath });
            }
            var shopRetro = FindPath("Ward district retrofit/Shop retrofits");
            if (shopRetro)
                foreach (Transform c in shopRetro)
                {
                    if (!c.name.StartsWith("COL_") || !c.gameObject.activeSelf) continue;
                    var col = c.GetComponent<Collider>();
                    var center = col ? col.bounds.center : c.position;
                    if (NorthSites.Any(x => InParcel(x, center, new Bounds(center, Vector3.one * .1f), out _)))
                    { Retire(c); retro.Add(new { retiredCollider = PathOf(c) }); }
                }
            report["retrofit"] = retro;

            var group = new GameObject(NorthGroupName);
            SceneManagerMove(group, scene);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var installed = new List<object>();
            foreach (var s in NorthSites)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabDir + s.model + ".prefab");
                if (!prefab) throw new Exception("Prefab missing (run North avenue: build assets): " + s.model);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.name = s.name;
                go.transform.SetParent(group.transform, false);
                go.transform.SetPositionAndRotation(s.pos, Quaternion.Euler(0, s.yaw, 0));
                var ls = go.GetComponentsInChildren<Light>(true);
                var lamps = ls.Where(l => l.name != "Display light").ToArray();
                circuit.practicalLights = circuit.practicalLights.Where(l => l && !l.transform.IsChildOf(go.transform)).Concat(ls).ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !l.transform.IsChildOf(go.transform)).Concat(lamps).ToArray();
                installed.Add(new { site = s.key, s.name, pos = new[] { s.pos.x, s.pos.y, s.pos.z }, s.yaw, lights = ls.Length });
            }
            foreach (var em in new[] { "WS_Glass", "WS_LedWarm" })
            {
                var mat = AssetDatabase.LoadAssetAtPath<Material>(MatDir + em + ".mat");
                if (mat && !circuit.emissiveMaterials.Contains(mat)) circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { mat }).ToArray();
            }
            EditorUtility.SetDirty(circuit);
            report["installed"] = installed;

            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            report["chunksRebuilt"] = chunks != null;

            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            File.WriteAllText(NorthEvidence + "north-install.json", JsonConvert.SerializeObject(report, Formatting.Indented));
            return $"installed {installed.Count} buildings, retired {retired.Count} objects, retrofit {retro.Count} entries";
        }

        /// Mounts the family signs for Salvage, Repairs and Thread + Hide on their prefabs' sign mounts. (Basic General
        /// keeps the family sign already in the scene; the new lintel is built to carry it where it hangs.)
        [MenuItem("Athen Hill/Ward shops/North avenue: install signs")]
        public static string InstallNorthSigns()
        {
            var mats = BuildMaterials(false);
            var log = new List<string>();
            foreach (var key in new[] { "salvage", "repairs", "thread_hide" })
            {
                var prefab = BuildSignPrefab(key, mats);
                var site = NorthSites.First(x => x.key == key);
                var path = PrefabDir + site.model + ".prefab";
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var mount = root.transform.Find("Sign mounts/Sign mount: " + SignText[key]);
                    if (!mount) { log.Add(key + ": mount missing"); continue; }
                    foreach (Transform c in mount.Cast<Transform>().ToArray()) UnityEngine.Object.DestroyImmediate(c.gameObject);
                    var sg = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    sg.transform.SetParent(mount, false); sg.transform.localPosition = Vector3.zero; sg.transform.localRotation = Quaternion.identity;
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    log.Add(key + ": sign mounted");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            AssetDatabase.SaveAssets();
            var scene = EditorSceneManager.GetActiveScene();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Directory.CreateDirectory(NorthEvidence);
            File.WriteAllText(NorthEvidence + "north-signs-install.txt", string.Join("\n", log));
            return string.Join("\n", log);
        }

        [MenuItem("Athen Hill/Ward shops/North avenue: verify saved scene")]
        public static string VerifyNorth()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var group = scene.GetRootGameObjects().FirstOrDefault(g => g.name == NorthGroupName);
            var r = new Dictionary<string, object> { ["group"] = group != null };
            if (group)
            {
                var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
                r["buildings"] = group.transform.Cast<Transform>().Select(t => new
                {
                    t.name, pos = t.position.ToString("F2"), yaw = t.eulerAngles.y,
                    lods = t.GetComponent<LODGroup>()?.lodCount, colliders = t.GetComponentsInChildren<Collider>(true).Length,
                    lights = t.GetComponentsInChildren<Light>(true).Length,
                    lightsOnCircuit = t.GetComponentsInChildren<Light>(true).Count(l => circuit.practicalLights.Contains(l)),
                    signs = t.Find("Sign mounts") ? t.Find("Sign mounts").GetComponentsInChildren<Renderer>(true).Length : 0,
                }).ToArray();
            }
            foreach (var s in NorthSites)
                foreach (var p in s.retire)
                    foreach (var t in FindRetire(p)) r["retired " + PathOf(t)] = !t.gameObject.activeSelf;
            foreach (var n in new[] { "COL_BLD_shop_e_04_porch", "COL_BLD_shop_w_03_porch", "COL_BLD_shop_w_04_porch", "COL_BLD_shop_e_04_first_step",
                                      "COL_BLD_shop_w_03_first_step", "COL_BLD_shop_w_04_first_step", "COL_BLD_general_back", "COL_BLD_general_porch",
                                      "COL_BLD_general_awning", "COL_BLD_general_side_e", "COL_BLD_general_side_w", "COL_BLD_general_first_step" })
            { var t = FindPath("AuthoredWorld/" + n); r["kept " + n] = t && t.gameObject.activeInHierarchy && t.GetComponent<Collider>() && t.GetComponent<Collider>().enabled; }
            foreach (var n in new[] { "Colonists/npc_mira", "Basic General counter dressing", "Basic General back panel", "Basic General sign (hall district family)",
                                      BG + "Stock", BG + "Hardware/Counter_plate_rivet_hex" })
            { var t = FindPath(n); r["kept " + n] = t && t.gameObject.activeInHierarchy; }
            Directory.CreateDirectory(NorthEvidence);
            File.WriteAllText(NorthEvidence + "north-verify-saved-scene.json", JsonConvert.SerializeObject(r, Formatting.Indented));
            return JsonConvert.SerializeObject(r);
        }

        static void SceneManagerMove(GameObject go, UnityEngine.SceneManagement.Scene scene) =>
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(go, scene);

        [MenuItem("Athen Hill/Ward shops/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var group = scene.GetRootGameObjects().FirstOrDefault(g => g.name == GroupName);
            var r = new Dictionary<string, object> { ["group"] = group != null };
            if (group)
            {
                var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
                r["shops"] = group.transform.Cast<Transform>().Select(t => new
                {
                    t.name, pos = t.position.ToString("F2"), yaw = t.eulerAngles.y,
                    lods = t.GetComponent<LODGroup>()?.lodCount, colliders = t.GetComponentsInChildren<Collider>(true).Length,
                    lights = t.GetComponentsInChildren<Light>(true).Length,
                    lightsOnCircuit = t.GetComponentsInChildren<Light>(true).Count(l => circuit.practicalLights.Contains(l)),
                }).ToArray();
            }
            foreach (var s in Sites)
                foreach (var p in s.retire) { var t = FindPath(p); r["retired " + p] = t ? (object)(!t.gameObject.activeSelf) : "missing"; }
            foreach (var n in new[] { "COL_BLD_shop_e_01_porch", "COL_BLD_shop_e_02_porch", "COL_BLD_shop_e_03_porch", "COL_BLD_shop_w_01_porch", "COL_BLD_shop_w_02_porch" })
            { var t = FindPath("AuthoredWorld/" + n); r["kept " + n] = t && t.gameObject.activeInHierarchy && t.GetComponent<Collider>() && t.GetComponent<Collider>().enabled; }
            var fit = FindPath("Ward shop architecture/Air + Water filter fittings");
            r["air water filter fittings active"] = fit && fit.gameObject.activeInHierarchy;
            File.WriteAllText(Evidence + "shops-verify-saved-scene.json", JsonConvert.SerializeObject(r, Formatting.Indented));
            return JsonConvert.SerializeObject(r);
        }
    }
}
