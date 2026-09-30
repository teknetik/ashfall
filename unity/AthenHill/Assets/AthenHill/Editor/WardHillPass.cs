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
    /// 30 September 2026: hill and hero-tree base rebuild. Carl: "do a similar pass on the hero tree and hill ... circled
    /// in stone, stone like the walls of the other buildings so it matches", plus his two Meshy props: a floodlight for
    /// Vanguard Hall (replacing the box uplights) and a "Reclaim &amp; Save Point" terminal for the hill.
    ///
    /// Sources: art/hill_20260930 (author_ward_hill.py -> WardHill_LOD0/1.glb + ward-hill.json on the shared masonry kit;
    /// scatter_hill_plants.py -> HillPlants_LOD0/1.glb; prepare_meshy_props.py / prepare_prop_maps.py -> Art/HillProps;
    /// prepare_hill_textures.py -> plant and soil maps). Menu: Athen Hill → Ward hill → Build assets, Install (one time,
    /// refuses when the hill root exists), Add review cameras, Verify saved scene. Retired visuals stay in the scene
    /// inactive; the saved plinth, surface and stair colliders are untouched. The hill is not a render-chunk source.
    /// </summary>
    public static class WardHillPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/WardHill/";
        const string ModelDir = Root + "Models/";
        const string MatDir = Root + "Materials/";
        const string PlantTex = Root + "Plants/Textures/";
        const string SoilTex = Root + "Textures/";
        const string PropDir = "Assets/AthenHill/Art/HillProps/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/WardHill/";
        const string HillPrefab = PrefabDir + "WardHill.prefab";
        const string TerminalPrefab = PrefabDir + "WardSaveTerminal.prefab";
        public const string FloodlightPrefab = PrefabDir + "WardFloodlight.prefab";
        const string HallMats = "Assets/AthenHill/Art/VanguardHall/Materials/";
        const string Evidence = "../evidence/hill/20260930/";
        public const string HillRootName = "Ward hill";
        const float HillLod0 = .22f, PlantsLod0 = .8f, PlantsLod1 = .2f;   // plants: per-zone groups (5-13 m), PC lodBias 2

        // visuals replaced by the new hill (kept in the scene, inactive)
        static readonly string[] RetiredExact =
        {
            "AuthoredWorld/ENV_hill_plinth", "AuthoredWorld/ENV_hill_mound", "AuthoredWorld/ENV_hill_surface",
            "AuthoredWorld/ENV_hill_path", "AuthoredWorld/ENV_hill_path.001", "AuthoredWorld/ENV_hill_path.002",
            "City Atmosphere/Hill grass 1", "City Atmosphere/Hill grass 2", "City Atmosphere/Hill grass 3", "City Atmosphere/Hill grass 4",
            "Hill weathered stones", "Courtyard reference pass/North stairs", "Courtyard reference pass/South stairs",
            "Courtyard reference pass/West stairs",
        };
        static readonly string[] RetiredPrefixes =
        {
            "AuthoredWorld/ENV_hill_cap", "AuthoredWorld/ENV_hill_stair_", "AuthoredWorld/PROP_hill_market_",
            "Ward surface wear/ENV_hill_stair_", "Courtyard reference pass/Sand deposits/Stair deposit",
        };

        // ------------------------------------------------------------------ build
        [MenuItem("Athen Hill/Ward hill/Build assets")]
        public static string BuildAssets()
        {
            ConfigureTextures();
            foreach (var m in new[] { "WardHill_LOD0", "WardHill_LOD1", "HillPlants_LOD0", "HillPlants_LOD1" })
                AssetDatabase.ImportAsset(ModelDir + m + ".glb", ImportAssetOptions.ForceUpdate);
            foreach (var p in new[] { "Terminal", "Floodlight" })
                for (int i = 0; i < 3; i++) AssetDatabase.ImportAsset(PropDir + p + "/" + p + "_LOD" + i + ".glb", ImportAssetOptions.ForceUpdate);
            var mats = BuildMaterials();
            Directory.CreateDirectory(PrefabDir);
            BuildPropPrefab("Terminal", TerminalPrefab, mats["HP_Terminal"], new[] { .35f, .1f, .02f });
            BuildPropPrefab("Floodlight", FloodlightPrefab, mats["HP_Floodlight"], new[] { .3f, .08f, .02f });
            var missing = BuildHillPrefab(mats);
            AssetDatabase.SaveAssets();
            return "built; unmapped materials: " + (missing.Count == 0 ? "none" : string.Join(", ", missing));
        }

        static void ConfigureTextures()
        {
            var dirs = new[] { PlantTex.TrimEnd('/'), SoilTex.TrimEnd('/'), PropDir + "Terminal", PropDir + "Floodlight" };
            foreach (var g in AssetDatabase.FindAssets("t:Texture", dirs))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                var file = Path.GetFileNameWithoutExtension(path);
                bool normal = file.EndsWith("_Normal"), mask = file.EndsWith("_Mask");
                bool small = new[] { "celandine", "weed_plant", "crystalline", "namaqualand_stones", "dry_branches", "bark_debris" }.Any(file.StartsWith);
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !normal && !mask;
                bool alpha = (path.StartsWith(PlantTex) && file.EndsWith("_BaseMap") && path.EndsWith(".png")) || file == "Terminal_Screen";
                ti.alphaSource = mask || alpha ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                ti.alphaIsTransparency = alpha;
                ti.mipMapsPreserveCoverage = alpha;       // keep grass blades from thinning out in the distance
                if (alpha) ti.alphaTestReferenceValue = .45f;
                ti.maxTextureSize = small ? 1024 : 2048;
                ti.mipmapEnabled = true;
                ti.streamingMipmaps = true;
                ti.anisoLevel = 8;
                ti.wrapMode = TextureWrapMode.Repeat;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
            }
        }

        static Material Mat(Dictionary<string, Material> mats, string name, Shader shader)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
            else if (m.shader != shader) m.shader = shader;
            mats[name] = m;
            return m;
        }

        static Texture2D T(string path) => AssetDatabase.LoadAssetAtPath<Texture2D>(path);

        static void Maps(Material m, Texture2D baseMap, Texture2D normal, Texture2D mask, float smoothness, float tile = 1f)
        {
            m.SetTexture("_BaseMap", baseMap); m.SetColor("_BaseColor", Color.white);
            m.SetTextureScale("_BaseMap", Vector2.one / tile);
            if (normal) { m.SetTexture("_BumpMap", normal); m.SetFloat("_BumpScale", 1f); m.EnableKeyword("_NORMALMAP"); }
            if (mask)
            {
                m.SetTexture("_MetallicGlossMap", mask); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetTexture("_OcclusionMap", mask); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1f);
            }
            m.SetFloat("_Smoothness", smoothness);
            m.SetFloat("_SmoothnessTextureChannel", 0);
            m.enableInstancing = true;
        }

        static void Cutout(Material m, float cutoff = .45f)
        {
            m.SetFloat("_AlphaClip", 1); m.SetFloat("_Cutoff", cutoff); m.EnableKeyword("_ALPHATEST_ON");
            m.SetOverrideTag("RenderType", "TransparentCutout"); m.renderQueue = (int)RenderQueue.AlphaTest;
            m.SetFloat("_Cull", 0); m.doubleSidedGI = true;
        }

        static void Wind(Material m, float sway, float bend, float flutter, float transmission)
        {
            m.SetFloat("_WardWindStrength", sway); m.SetFloat("_WardBendHeight", bend); m.SetFloat("_WardLeafFlutter", flutter);
            m.SetFloat("_WardTranslucency", transmission); m.SetFloat("_WardIndirectTranslucency", transmission * .5f);
        }

        static Dictionary<string, Material> BuildMaterials()
        {
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var cover = Shader.Find("Athen Hill/Ward Ground Cover");
            if (!cover) throw new Exception("Athen Hill/Ward Ground Cover shader missing (Shaders/WardGroundCover)");
            var mats = new Dictionary<string, Material>();
            // soils (world-planar UVs in metres from the authoring script)
            var soil = Mat(mats, "WH_BedSoil", lit);
            Maps(soil, T(SoilTex + "WH_BedSoil_BaseMap.jpg"), T(SoilTex + "WH_BedSoil_Normal.jpg"), T(SoilTex + "WH_BedSoil_Mask.png"), .45f, 1.6f);
            soil.SetColor("_BaseColor", new Color(.92f, .9f, .84f));
            var litter = Mat(mats, "WH_RingLitter", lit);
            Maps(litter, T(SoilTex + "WH_RingLitter_BaseMap.jpg"), T(SoilTex + "WH_RingLitter_Normal.jpg"), T(SoilTex + "WH_RingLitter_Mask.png"), .5f, 1.6f);
            litter.SetColor("_BaseColor", new Color(.74f, .68f, .62f));
            // surface roots: the Phase 1 root bark maps, darkened to the trunk's brown
            var src = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Phase1/Tree/RootBark.mat");
            var roots = Mat(mats, "WH_RootBark", src ? src.shader : lit);
            if (src) roots.CopyPropertiesFromMaterial(src);
            roots.SetColor("_BaseColor", new Color(.46f, .37f, .3f));
            roots.SetTextureScale("_BaseMap", Vector2.one * 1.2f);
            EditorUtility.SetDirty(roots);
            // planting: foliage on the wind shader (cut-out, two-sided), hard parts on Lit
            void Plant(string name, string tex, bool cut, float sway, float bend, float flutter, float trans, float smooth, Color tint)
            {
                var m = Mat(mats, name, cover);
                Maps(m, T(PlantTex + tex + "_BaseMap.png"), T(PlantTex + tex + "_Normal.jpg"), T(PlantTex + tex + "_Mask.png"), smooth);
                m.SetColor("_BaseColor", tint);
                if (cut) Cutout(m); else { m.SetFloat("_Cull", 0); m.doubleSidedGI = true; }
                Wind(m, sway, bend, flutter, trans);
                EditorUtility.SetDirty(m);
            }
            Plant("grass_medium_01", "grass_medium_01", true, .07f, .32f, .012f, .22f, .55f, new Color(.97f, .94f, .88f));
            Plant("grass_medium_02", "grass_medium_02", true, .06f, .36f, .01f, .22f, .55f, new Color(.9f, .92f, .82f));
            Plant("cheiridopsis_succulent", "cheiridopsis_succulent", false, .006f, .3f, 0f, .1f, .6f, Color.white);
            Plant("cheiridopsis_succulent_flower", "cheiridopsis_succulent", true, .02f, .3f, .006f, .2f, .5f, Color.white);
            Plant("crystalline_iceplant", "crystalline_iceplant", true, .008f, .12f, .003f, .12f, .6f, Color.white);
            Plant("celandine_01", "celandine_01", true, .03f, .25f, .008f, .2f, .5f, Color.white);
            Plant("weed_plant_02", "weed_plant_02", true, .02f, .2f, .006f, .18f, .5f, Color.white);
            Plant("othonna_cerarioides", "othonna_cerarioides", false, .025f, 1.1f, 0f, 0f, .5f, Color.white);
            Plant("othonna_cerarioides_leaves", "othonna_cerarioides", true, .035f, 1.1f, .008f, .18f, .5f, Color.white);
            void Hard(string name, string tex, float smooth)
            {
                var m = Mat(mats, name, lit);
                Maps(m, T(PlantTex + tex + "_BaseMap.png"), T(PlantTex + tex + "_Normal.jpg"), T(PlantTex + tex + "_Mask.png"), smooth);
                EditorUtility.SetDirty(m);
            }
            Hard("namaqualand_stones_01", "namaqualand_stones_01", .6f);
            Hard("namaqualand_boulder_05", "namaqualand_boulder_05", .6f);
            Hard("bark_debris_01", "bark_debris_01", .5f);
            Hard("dry_branches_medium_01", "dry_branches_medium_01", .5f);
            mats["weed_plant_02.001"] = mats["weed_plant_02"];
            // Carl's Meshy props: full source maps, URP Lit, emission masks derived from the albedo
            void Prop(string name, string dir, float emission, float smooth)
            {
                var m = Mat(mats, name, lit);
                Maps(m, T(PropDir + dir + "/source_BaseColor.jpg"), T(PropDir + dir + "/source_Normal.jpg"), T(PropDir + dir + "/" + dir + "_Mask.png"), smooth);
                m.SetTexture("_OcclusionMap", null); m.DisableKeyword("_OCCLUSIONMAP");
                m.SetTexture("_EmissionMap", T(PropDir + dir + "/" + dir + "_Emission.png"));
                m.SetColor("_EmissionColor", Color.white * emission); m.EnableKeyword("_EMISSION");
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;   // URP keeps _EMISSION only with an emissive GI flag
                EditorUtility.SetDirty(m);
            }
            Prop("HP_Terminal", "Terminal", .9f, 1f);
            var screen = Mat(mats, "HP_TerminalScreen", lit);
            screen.SetTexture("_BaseMap", T(PropDir + "Terminal/Terminal_Screen.png")); screen.SetColor("_BaseColor", new Color(.06f, .08f, .08f));
            // a lit display: bright enough to read in full sun; no specular spot from the kiosk's own glow light
            screen.SetFloat("_Smoothness", .7f); screen.SetFloat("_Metallic", 0f);
            screen.SetFloat("_SpecularHighlights", 0f); screen.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
            screen.SetTexture("_EmissionMap", T(PropDir + "Terminal/Terminal_Screen.png")); screen.SetColor("_EmissionColor", Color.white * 2.2f);
            screen.EnableKeyword("_EMISSION"); screen.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            screen.SetFloat("_AlphaClip", 1); screen.SetFloat("_Cutoff", .5f); screen.EnableKeyword("_ALPHATEST_ON");
            screen.SetOverrideTag("RenderType", "TransparentCutout"); screen.renderQueue = (int)RenderQueue.AlphaTest;
            EditorUtility.SetDirty(screen);
            Prop("HP_Floodlight", "Floodlight", 3f, 1f);
            // shared stone and fittings
            foreach (var n in new[] { "VH_Ashlar", "VH_AshlarRough", "VH_Mortar", "VH_PodiumSlab", "VH_Sand", "VH_Steel", "VH_Dark", "VH_Bronze", "VH_LampLens" })
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(HallMats + n + ".mat");
                if (!m) throw new Exception("Hall material missing: " + n);
                mats[n] = m;
            }
            mats["RootBark"] = mats["WH_RootBark"];
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

        static List<Renderer> Instance(string glb, Transform parent, string name, Func<string, Material> map, HashSet<string> missing)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb);
            if (!model) throw new Exception("Model not imported: " + glb);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            inst.transform.SetParent(parent, false);
            inst.name = name;
            var rs = new List<Renderer>();
            foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
            {
                var slots = r.sharedMaterials;
                for (int i = 0; i < slots.Length; i++)
                {
                    var m = slots[i] ? map(slots[i].name) : null;
                    if (m) slots[i] = m; else missing?.Add(r.name + ":" + (slots[i] ? slots[i].name : "null"));
                }
                r.sharedMaterials = slots;
                r.receiveShadows = true;
                if (r is MeshRenderer mr) { mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; mr.receiveGI = ReceiveGI.LightProbes; }
                rs.Add(r);
            }
            return rs;
        }

        static void BuildPropPrefab(string prop, string path, Material mat, float[] cuts)
        {
            var root = new GameObject(Path.GetFileNameWithoutExtension(path));
            try
            {
                var levels = new List<LOD>();
                for (int i = 0; i < 3; i++)
                {
                    var rs = Instance(PropDir + prop + "/" + prop + "_LOD" + i + ".glb", root.transform, "LOD" + i, _ => mat, null);
                    foreach (var r in rs) r.shadowCastingMode = i == 2 ? ShadowCastingMode.Off : ShadowCastingMode.On;
                    levels.Add(new LOD(cuts[i], rs.ToArray()));
                }
                var g = root.AddComponent<LODGroup>(); g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                if (prop == "Terminal")
                {
                    // crisp screen art over both baked screens (the decimated Meshy atlas smears them up close)
                    var screenMat = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "HP_TerminalScreen.mat");
                    var quad = ScreenQuad(.566f, .376f);
                    var screens = new List<Renderer>();
                    foreach (var (sname, pos, yaw) in new[] { ("Screen front", new Vector3(.004f, 1.506f, .193f), 0f), ("Screen back", new Vector3(-.001f, 1.513f, -.2195f), 180f) })
                    {
                        var sgo = new GameObject(sname); sgo.transform.SetParent(root.transform, false);
                        sgo.transform.localPosition = pos; sgo.transform.localRotation = Quaternion.Euler(0, yaw, 0);
                        sgo.AddComponent<MeshFilter>().sharedMesh = quad;
                        var sr = sgo.AddComponent<MeshRenderer>(); sr.sharedMaterial = screenMat; sr.shadowCastingMode = ShadowCastingMode.Off;
                        screens.Add(sr);
                    }
                    for (int i = 0; i < levels.Count; i++) levels[i] = new LOD(levels[i].screenRelativeTransitionHeight, levels[i].renderers.Concat(screens).ToArray());
                    g.SetLODs(levels.ToArray());
                    // soft cyan spill from the screen onto the pad at night (bound to the city light circuit on install)
                    var go = new GameObject("Screen glow"); go.transform.SetParent(root.transform, false);
                    go.transform.localPosition = new Vector3(0, 1.42f, .62f);
                    var l = go.AddComponent<Light>(); l.type = LightType.Point; l.color = new Color(.4f, .88f, 1f); l.intensity = .7f; l.range = 2.4f; l.shadows = LightShadows.None;
                }
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (!t.GetComponent<Light>()) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                PrefabUtility.SaveAsPrefabAsset(root, path);
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        static JObject Record() => JObject.Parse(File.ReadAllText(ModelDir + "ward-hill.json"));
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);

        static HashSet<string> BuildHillPrefab(Dictionary<string, Material> mats)
        {
            var rec = Record();
            var missing = new HashSet<string>();
            var root = new GameObject("WardHill");
            try
            {
                // stone, soil, roots. Only walls, stairs and ring cast shadows; at LOD0 they cast through their LOD1 meshes
                // (shadow proxies, as on the hero tree): the ashlar margins and chips add nothing to a shadow map.
                var levels = new List<LOD>();
                var lodRenderers = new List<Renderer>[2];
                foreach (var (lod, cut) in new[] { (0, HillLod0), (1, .012f) })
                {
                    var rs = Instance(ModelDir + $"WardHill_LOD{lod}.glb", root.transform, "LOD" + lod, n => Lookup(mats, n), missing);
                    foreach (var r in rs)
                        r.shadowCastingMode = lod == 1 && Casts(r.name) ? ShadowCastingMode.On : ShadowCastingMode.Off;
                    lodRenderers[lod] = rs;
                    levels.Add(new LOD(cut, rs.ToArray()));
                }
                var proxyRoot = new GameObject("Shadow proxy (LOD1 meshes)"); proxyRoot.transform.SetParent(root.transform, false);
                var proxies = new List<Renderer>();
                foreach (var r1 in lodRenderers[1].Where(r => Casts(r.name)))
                {
                    var go = new GameObject(r1.name.Replace("_LOD1", "_Shadow"));
                    go.transform.SetParent(proxyRoot.transform, false);
                    go.transform.SetPositionAndRotation(r1.transform.position, r1.transform.rotation); go.transform.localScale = r1.transform.lossyScale;
                    go.AddComponent<MeshFilter>().sharedMesh = r1.GetComponent<MeshFilter>().sharedMesh;
                    var pr = go.AddComponent<MeshRenderer>(); pr.sharedMaterials = r1.sharedMaterials; pr.shadowCastingMode = ShadowCastingMode.ShadowsOnly;
                    proxies.Add(pr);
                }
                levels[0] = new LOD(levels[0].screenRelativeTransitionHeight, levels[0].renderers.Concat(proxies).ToArray());
                var group = root.AddComponent<LODGroup>(); group.SetLODs(levels.ToArray()); group.fadeMode = LODFadeMode.None; group.RecalculateBounds();

                // planting: one LOD group per bed / the ring (so beds out of view or far away drop detail on their own);
                // never static-batched, because the wind reads each vertex's height above its group's origin
                var planting = new GameObject("Planting"); planting.transform.SetParent(root.transform, false);
                var byZone = new SortedDictionary<string, List<Renderer>[]>();
                foreach (var lod in new[] { 0, 1 })
                {
                    var rs = Instance(ModelDir + $"HillPlants_LOD{lod}.glb", planting.transform, "LOD" + lod, n => Lookup(mats, n), missing);
                    foreach (var r in rs)
                    {
                        r.shadowCastingMode = r.name.Contains("_cast") && lod == 0 ? ShadowCastingMode.On : ShadowCastingMode.Off;
                        var zone = System.Text.RegularExpressions.Regex.Replace(r.name, @"^HillPlants_(.+?)_(cover|cast)_LOD\d$", "$1");
                        if (!byZone.TryGetValue(zone, out var lists)) byZone[zone] = lists = new[] { new List<Renderer>(), new List<Renderer>() };
                        lists[lod].Add(r);
                    }
                }
                foreach (Transform inst in planting.transform.Cast<Transform>().ToArray())
                    if (PrefabUtility.IsPartOfPrefabInstance(inst.gameObject)) PrefabUtility.UnpackPrefabInstance(inst.gameObject, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                foreach (var kv in byZone)
                {
                    var zgo = new GameObject("Zone " + kv.Key); zgo.transform.SetParent(planting.transform, false);
                    foreach (var r in kv.Value[0].Concat(kv.Value[1])) r.transform.SetParent(zgo.transform, true);
                    var zg = zgo.AddComponent<LODGroup>();
                    zg.SetLODs(new[] { new LOD(PlantsLod0, kv.Value[0].ToArray()), new LOD(PlantsLod1, kv.Value[1].ToArray()) });
                    zg.fadeMode = LODFadeMode.None; zg.RecalculateBounds();
                }
                foreach (Transform t in planting.transform.Cast<Transform>().ToArray()) if (t.childCount == 0 && !t.name.StartsWith("Zone")) UnityEngine.Object.DestroyImmediate(t.gameObject);

                // colliders: stair cheeks (boxes), ring wall (mesh), ring soil (convex cylinder)
                var cols = new GameObject("Colliders").transform; cols.SetParent(root.transform, false);
                foreach (var c in rec["colliders"])
                {
                    var go = new GameObject((string)c["name"]); go.transform.SetParent(cols, false);
                    var b = go.AddComponent<BoxCollider>(); b.center = V3(c["center"]); b.size = V3(c["size"]);
                }
                var ring = rec["ring"];
                var ringGo = new GameObject("COL_TreeRing"); ringGo.transform.SetParent(cols, false);
                ringGo.AddComponent<MeshCollider>().sharedMesh = RingMesh("TreeRingCollider", (float)ring["inner"], (float)ring["outer"], (float)ring["bottom"], (float)ring["top"], 48, true);
                var soilGo = new GameObject("COL_TreeRingSoil"); soilGo.transform.SetParent(cols, false);
                var soilCol = soilGo.AddComponent<MeshCollider>();
                soilCol.sharedMesh = RingMesh("TreeRingSoilCollider", 0f, (float)ring["inner"] + .02f, (float)ring["bottom"], (float)ring["soil_top"], 32, false);
                soilCol.convex = true;

                // terminals on their pads, facing the tree
                var terms = new GameObject("Terminals").transform; terms.SetParent(root.transform, false);
                var tprefab = AssetDatabase.LoadAssetAtPath<GameObject>(TerminalPrefab);
                foreach (var m in rec["mounts"])
                {
                    if ((string)m["prefab"] != "WardSaveTerminal") continue;
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(tprefab);
                    go.name = (string)m["name"];
                    go.transform.SetParent(terms, false);
                    go.transform.localPosition = V3(m["pos"]);
                    go.transform.localRotation = Quaternion.Euler(0, (float)m["yaw"], 0);
                }

                // tree uplights in the ring coping (bound to the city light circuit on install)
                var lights = new GameObject("Practical lights").transform; lights.SetParent(root.transform, false);
                foreach (var spec in rec["lights"])
                {
                    var go = new GameObject((string)spec["name"]); go.transform.SetParent(lights, false);
                    var pos = V3(spec["pos"]); go.transform.localPosition = pos;
                    go.transform.localRotation = Quaternion.LookRotation(V3(spec["target"]) - pos, Vector3.up);
                    var l = go.AddComponent<Light>(); var c = spec["color"];
                    l.type = LightType.Spot; l.color = new Color((float)c[0], (float)c[1], (float)c[2]);
                    l.intensity = (float)spec["intensity"]; l.range = (float)spec["range"]; l.spotAngle = (float)spec["angle"]; l.innerSpotAngle = (float)spec["inner"];
                    l.shadows = LightShadows.None;
                }

                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                {
                    if (t.GetComponent<Light>() || t.IsChildOf(terms)) continue;
                    var flags = StaticEditorFlags.OccludeeStatic;
                    if (!t.IsChildOf(planting.transform)) flags |= StaticEditorFlags.OccluderStatic | StaticEditorFlags.BatchingStatic;
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, flags);
                }
                PrefabUtility.SaveAsPrefabAsset(root, HillPrefab);
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
            if (missing.Count > 0) Debug.LogWarning("Ward hill: unmapped materials: " + string.Join(", ", missing));
            return missing;
        }

        static Mesh ScreenQuad(float w, float h)
        {
            Directory.CreateDirectory(PropDir + "Terminal");
            var path = PropDir + "Terminal/TerminalScreenQuad.asset";
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            bool create = !mesh;
            if (create) mesh = new Mesh { name = "TerminalScreenQuad" };
            mesh.Clear();
            mesh.vertices = new[] { new Vector3(-w / 2, -h / 2, 0), new Vector3(w / 2, -h / 2, 0), new Vector3(w / 2, h / 2, 0), new Vector3(-w / 2, h / 2, 0) };
            // faces +Z (the kiosk's front); texture reads left to right from the front
            mesh.uv = new[] { new Vector2(1, 0), new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1) };
            mesh.triangles = new[] { 0, 1, 2, 0, 2, 3 };   // clockwise seen from +Z (Unity front faces)
            mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
            if (create) AssetDatabase.CreateAsset(mesh, path); else EditorUtility.SetDirty(mesh);
            return mesh;
        }

        static bool Casts(string rendererName) => rendererName.StartsWith("WH_Walls") || rendererName.StartsWith("WH_Stairs") || rendererName.StartsWith("WH_Ring_");

        /// Annulus (inner > 0) or disc (inner = 0) prism saved as a mesh asset for collision.
        static Mesh RingMesh(string name, float inner, float outer, float y0, float y1, int seg, bool annulus)
        {
            Directory.CreateDirectory(Root + "Colliders");
            var path = Root + "Colliders/" + name + ".asset";
            var v = new List<Vector3>(); var t = new List<int>();
            for (int i = 0; i < seg; i++)
            {
                float a = Mathf.PI * 2 * i / seg; var d = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a));
                v.Add(d * outer + Vector3.up * y0); v.Add(d * outer + Vector3.up * y1);
                v.Add(d * inner + Vector3.up * y0); v.Add(d * inner + Vector3.up * y1);
            }
            for (int i = 0; i < seg; i++)
            {
                int a = i * 4, b = ((i + 1) % seg) * 4;
                t.AddRange(new[] { a, b + 1, b, a, a + 1, b + 1 });                  // outer wall
                t.AddRange(new[] { a + 1, a + 3, b + 3, a + 1, b + 3, b + 1 });      // top
                if (annulus) t.AddRange(new[] { a + 2, b + 2, b + 3, a + 2, b + 3, a + 3 });   // inner wall
                t.AddRange(new[] { a, b, b + 2, a, b + 2, a + 2 });                  // bottom
            }
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            bool create = !mesh;
            if (create) mesh = new Mesh { name = name };
            mesh.Clear(); mesh.SetVertices(v); mesh.SetTriangles(t, 0); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            if (create) AssetDatabase.CreateAsset(mesh, path); else EditorUtility.SetDirty(mesh);
            return mesh;
        }

        // ------------------------------------------------------------------ install
        static Transform FindPath(UnityEngine.SceneManagement.Scene scene, string path)
        {
            var parts = path.Split('/');
            var top = scene.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!top) return null;
            var t = top.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Cast<Transform>().FirstOrDefault(c => c.name == parts[i]);
            return t;
        }

        static IEnumerable<Transform> FindPrefixed(UnityEngine.SceneManagement.Scene scene, string prefixPath)
        {
            int slash = prefixPath.LastIndexOf('/');
            var parent = FindPath(scene, prefixPath.Substring(0, slash));
            var prefix = prefixPath.Substring(slash + 1);
            if (!parent) yield break;
            foreach (Transform c in parent) if (c.name.StartsWith(prefix) && !c.name.StartsWith("COL_")) yield return c;
        }

        public static List<Transform> RetireList(UnityEngine.SceneManagement.Scene scene)
        {
            var list = new List<Transform>();
            foreach (var p in RetiredExact) { var t = FindPath(scene, p); if (t) list.Add(t); }
            foreach (var p in RetiredPrefixes) list.AddRange(FindPrefixed(scene, p));
            // dressing on the hill top and the stairs (by position, so similarly named props elsewhere stay)
            bool OnHill(Vector3 p, float margin) => Mathf.Abs(p.x) < 7f + margin && Mathf.Abs(p.z) < 7f + margin;
            bool OnStairs(Vector3 p) => (Mathf.Abs(p.x) < 2.6f && Mathf.Abs(p.z) > 6.8f && Mathf.Abs(p.z) < 11f) || (Mathf.Abs(p.z) < 2.6f && p.x > 6.8f && p.x < 11f);
            var dressing = FindPath(scene, "AuthoredWorld/AAA Environment Dressing");
            if (dressing)
                foreach (Transform c in dressing)
                {
                    var r = c.GetComponent<Renderer>(); var p = r ? r.bounds.center : c.position;
                    if ((c.name == "Hill root stone" && (OnHill(p, .5f) || OnStairs(p) || p.magnitude < 11f)) || (c.name.StartsWith("Plaza bench") && OnHill(p, 0)))
                        list.Add(c);
                }
            foreach (var parentPath in new[] { "Courtyard reference pass/Vegetation", "Ward surface wear" })
            {
                var parent = FindPath(scene, parentPath);
                if (!parent) continue;
                foreach (Transform c in parent)
                {
                    var r = c.GetComponent<Renderer>(); var p = r ? r.bounds.center : c.position;
                    if ((c.name.StartsWith("Dry joint growth") || c.name == "Dusty joint weeds") && OnStairs(p)) list.Add(c);
                }
            }
            return list.Distinct().ToList();
        }

        [MenuItem("Athen Hill/Ward hill/Dry-run install")]
        public static string DryRun()
        {
            var scene = EditorSceneManager.GetActiveScene();
            return string.Join("\n", RetireList(scene).Select(t => PathOf(t) + " active=" + t.gameObject.activeSelf));
        }

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        [MenuItem("Athen Hill/Ward hill/Install rebuilt hill")]
        public static string Install() => Install(false);

        /// Authoring iteration only: replaces the installed hill root (retired objects stay retired).
        public static string Reinstall() => Install(true);

        static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath);
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == HillRootName);
            if (existing && !replace) throw new Exception("The Ward hill is already installed; edit it in place or use Reinstall during authoring.");
            Directory.CreateDirectory(Evidence + "rollback");
            if (!replace) File.Copy(ScenePath, Evidence + "rollback/before-hill-install.unity", true);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            if (existing)
            {
                circuit.practicalLights = circuit.practicalLights.Where(l => l && !l.transform.IsChildOf(existing.transform)).ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !l.transform.IsChildOf(existing.transform)).ToArray();
                UnityEngine.Object.DestroyImmediate(existing);
            }
            var record = new Dictionary<string, object>();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) chunks.ShowSources(true);
            var retired = new List<object>();
            foreach (var t in RetireList(scene))
            {
                retired.Add(new { path = PathOf(t), wasActive = t.gameObject.activeSelf });
                Undo.RecordObject(t.gameObject, "Retire hill visual");
                t.gameObject.SetActive(false);
                if (PrefabUtility.IsPartOfPrefabInstance(t.gameObject)) PrefabUtility.RecordPrefabInstancePropertyModifications(t.gameObject);
            }
            record["retired"] = retired;

            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(HillPrefab);
            var hill = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
            hill.name = HillRootName;
            hill.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);

            // the saved terminal colliders follow the new terminals (object ids kept): body over the kiosk, foot = stone pad
            var rec = Record();
            var fitted = new List<object>();
            int slot = 0;
            foreach (var m in rec["mounts"])
            {
                if ((string)m["prefab"] != "WardSaveTerminal") continue;
                var pos = V3(m["pos"]); var rot = Quaternion.Euler(0, (float)m["yaw"], 0);
                string prefix = "AuthoredWorld/COL_PROP_hill_market_" + slot.ToString("00") + "_";
                foreach (var (part, center, size) in new[] { ("body", new Vector3(0, .93f, 0), new Vector3(.98f, 1.86f, .76f)),
                                                            ("foot", new Vector3(0, -.08f, 0), new Vector3(1.55f, .2f, 1.25f)) })
                {
                    var t = FindPath(scene, prefix + part);
                    var b = t ? t.GetComponent<BoxCollider>() : null;
                    if (!b) { fitted.Add(new { collider = prefix + part, found = false }); continue; }
                    Undo.RecordObject(t, "Fit terminal collider"); Undo.RecordObject(b, "Fit terminal collider");
                    t.SetPositionAndRotation(pos, rot);
                    var s = t.lossyScale;
                    b.center = new Vector3(center.x / s.x, center.y / s.y, center.z / s.z);
                    b.size = new Vector3(size.x / Mathf.Abs(s.x), size.y / Mathf.Abs(s.y), size.z / Mathf.Abs(s.z));
                    if (PrefabUtility.IsPartOfPrefabInstance(t.gameObject)) { PrefabUtility.RecordPrefabInstancePropertyModifications(t); PrefabUtility.RecordPrefabInstancePropertyModifications(b); }
                    fitted.Add(new { collider = prefix + part, center = new[] { b.bounds.center.x, b.bounds.center.y, b.bounds.center.z }, size = new[] { b.bounds.size.x, b.bounds.size.y, b.bounds.size.z } });
                }
                slot++;
            }
            record["terminalColliders"] = fitted;

            // lights: uplights and terminal glows are practical, night-only lights on the city circuit
            var lamps = hill.GetComponentsInChildren<Light>(true);
            circuit.practicalLights = circuit.practicalLights.Where(l => l).Concat(lamps).Distinct().ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l).Concat(lamps).Distinct().ToArray();
            EditorUtility.SetDirty(circuit);
            record["lights"] = lamps.Select(l => PathOf(l.transform)).ToArray();

            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            record["chunksRebuilt"] = chunks != null;
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + (replace ? "reinstall.json" : "install.json"), json);
            return json;
        }

        // ------------------------------------------------------------------ Vanguard Hall floodlights
        /// Carl's Meshy floodlight replaces the hall's modelled box uplights. The hall source
        /// (art/vanguard_hall_20260930/author_vanguard_hall.py) no longer builds the boxes and records the floodlight
        /// mounts and re-aimed spots; this re-imports the hall models and edits the hall prefab in place (the existing
        /// "Facade uplight" lights keep their object ids, so their City Light Circuit bindings survive).
        [MenuItem("Athen Hill/Ward hill/Install Vanguard Hall floodlights")]
        public static string InstallHallFloodlights()
        {
            const string hallModels = "Assets/AthenHill/Art/VanguardHall/Models/";
            AssetDatabase.ImportAsset(hallModels + "VanguardHall_LOD0.glb", ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(hallModels + "VanguardHall_LOD1.glb", ImportAssetOptions.ForceUpdate);
            var rec = JObject.Parse(File.ReadAllText(hallModels + "vanguard-hall.json"));
            var flood = AssetDatabase.LoadAssetAtPath<GameObject>(FloodlightPrefab);
            if (!flood) throw new Exception("Build the Ward hill assets first (WardFloodlight prefab missing).");
            const string hallPrefab = "Assets/AthenHill/Prefabs/VanguardHall/VanguardHall.prefab";
            var root = PrefabUtility.LoadPrefabContents(hallPrefab);
            var log = new List<string>();
            try
            {
                var fit = root.transform.Find("Fittings");
                var lights = root.transform.Find("Practical lights");
                foreach (var m in rec["mounts"].Where(m => (string)m["prefab"] == "WardFloodlight"))
                {
                    var name = (string)m["name"];
                    var old = fit.Find(name);
                    if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(flood, fit);
                    go.name = name;
                    go.transform.localPosition = V3(m["pos"]);
                    go.transform.localRotation = Quaternion.Euler(0, (float)m["yaw"], 0);
                    log.Add(name + " at " + go.transform.localPosition);
                }
                foreach (var spec in rec["lights"])
                {
                    var t = lights.Find((string)spec["name"]);
                    if (!t) { log.Add("missing light " + spec["name"]); continue; }
                    var pos = V3(spec["pos"]);
                    t.localPosition = pos;
                    t.localRotation = Quaternion.LookRotation(V3(spec["target"]) - pos, Vector3.up);
                    var l = t.GetComponent<Light>(); var c = spec["color"];
                    l.color = new Color((float)c[0], (float)c[1], (float)c[2]);
                    l.intensity = (float)spec["intensity"]; l.range = (float)spec["range"];
                    l.spotAngle = (float)spec["angle"]; l.innerSpotAngle = (float)spec["inner"];
                    log.Add("aimed " + t.name);
                }
                PrefabUtility.SaveAsPrefabAsset(root, hallPrefab);
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            // the lamp lens glows at night with the rest of the city's practical lights
            var scene = EditorSceneManager.GetActiveScene();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var lens = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "HP_Floodlight.mat");
            if (circuit && lens && !circuit.emissiveMaterials.Contains(lens))
            {
                circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { lens }).ToArray();
                EditorUtility.SetDirty(circuit);
            }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            var json = JsonConvert.SerializeObject(log, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "hall-floodlights.json", json);
            return json;
        }

        // ------------------------------------------------------------------ review cameras (native lookbook / QA)
        static readonly (string name, Vector3 pos, Vector3 target, float fov)[] ReviewViews =
        {
            ("cam_hill_ring", new Vector3(1.4f, 3.15f, 6.4f), new Vector3(-0.2f, 1.85f, 0f), 60),
            ("cam_hill_heave", new Vector3(-4.1f, 3.1f, 3.9f), new Vector3(-2.45f, 1.9f, 1.65f), 50),
            ("cam_hill_roots", new Vector3(1.9f, 3.35f, 3.4f), new Vector3(-0.3f, 1.8f, -0.4f), 60),
            ("cam_hill_stair_north", new Vector3(2.2f, 1.65f, -14.5f), new Vector3(0f, 1.1f, -8.5f), 60),
            ("cam_hill_stair_west", new Vector3(14.5f, 1.65f, 2.4f), new Vector3(8.5f, 1.1f, 0f), 60),
            ("cam_hill_corner", new Vector3(-11.8f, 1.65f, -11.2f), new Vector3(-7f, 0.9f, -7f), 60),
            ("cam_hill_terminal", new Vector3(2.9f, 3.15f, -1.4f), new Vector3(5f, 2.4f, -4f), 55),
            ("cam_hill_beds", new Vector3(-1.1f, 3.15f, 6.0f), new Vector3(-5f, 1.6f, 1.8f), 60),
            ("cam_hill_east_wall", new Vector3(-12.5f, 1.65f, 2.6f), new Vector3(-7f, 0.9f, 0f), 60),
            ("cam_hill_overview", new Vector3(-15f, 13f, 16f), new Vector3(0f, 1f, 0f), 45),
        };

        [MenuItem("Athen Hill/Ward hill/Add review cameras")]
        public static void ReviewCameras()
        {
            var scene = EditorSceneManager.GetActiveScene();
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Ward hill review cameras");
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject("Ward hill review cameras");
            foreach (var (name, pos, target, fov) in ReviewViews)
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var c = go.AddComponent<Camera>(); c.enabled = false; c.fieldOfView = fov; c.nearClipPlane = .05f;
            }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
        }

        // ------------------------------------------------------------------ verify
        [MenuItem("Athen Hill/Ward hill/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var r = new Dictionary<string, object>();
            var hill = scene.GetRootGameObjects().FirstOrDefault(g => g.name == HillRootName);
            r["installed"] = hill != null;
            if (hill)
            {
                r["prefabLinked"] = PrefabUtility.IsPartOfPrefabInstance(hill);
                foreach (var lg in hill.GetComponentsInChildren<LODGroup>(true).Where(g => !g.transform.IsChildOf(hill.transform.Find("Terminals"))))
                    r["lods " + lg.name] = lg.GetLODs().Select(l => new { l.screenRelativeTransitionHeight, renderers = l.renderers.Length, triangles = l.renderers.Sum(x => x && x.GetComponent<MeshFilter>() ? (int)Enumerable.Range(0, x.GetComponent<MeshFilter>().sharedMesh.subMeshCount).Sum(s => x.GetComponent<MeshFilter>().sharedMesh.GetIndexCount(s) / 3) : 0) }).ToArray();
                r["colliders"] = hill.GetComponentsInChildren<Collider>(true).Count();
                r["materials"] = hill.GetComponentsInChildren<Renderer>(true).SelectMany(x => x.sharedMaterials).Where(m => m).Select(m => m.name + " (" + m.shader.name + ")").Distinct().OrderBy(x => x).ToArray();
                r["missingMaterials"] = hill.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(m => !m));
                r["terminals"] = hill.transform.Find("Terminals").Cast<Transform>().Select(t => new { t.name, pos = new[] { t.position.x, t.position.y, t.position.z }, yaw = t.eulerAngles.y }).ToArray();
            }
            r["retiredStillActive"] = RetireList(scene).Where(t => t.gameObject.activeSelf).Select(PathOf).ToArray();
            r["keptColliders"] = new[] { "AuthoredWorld/COL_ENV_hill_plinth", "AuthoredWorld/COL_ENV_hill_surface" }.Concat(
                new[] { "north", "south", "west" }.SelectMany(s => Enumerable.Range(0, 6).Select(i => $"AuthoredWorld/COL_ENV_hill_stair_{s}_{i}")))
                .Select(p => { var t = FindPath(scene, p); var c = t ? t.GetComponent<Collider>() : null; return new { p, active = t && t.gameObject.activeInHierarchy && c && c.enabled }; })
                .Where(x => !x.active).Select(x => x.p).ToArray();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            r["circuitLights"] = hill ? circuit.practicalLights.Count(l => l && l.transform.IsChildOf(hill.transform)) : 0;
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }
    }
}
