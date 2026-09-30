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
    /// 30 September 2026: Vanguard Hall rebuild. Replaces the 6,856-triangle Meshy hall (and its retrofit banners,
    /// plinth and step) with an authored civic hall: modelled ashlar with per-block tint (Athen Hill/Masonry Lit),
    /// battered piers, riveted portal doors, barred windows, entablature and cornice, parapet, steel repairs, conduit,
    /// comms mast and a woven banner. Accepted reference: art/vanguard_hall_20260930/concept (Carl, 30 Sep 2026).
    ///
    /// Sources: art/vanguard_hall_20260930 (author_vanguard_hall.py -> Models/*.glb + vanguard-hall.json,
    /// prepare_textures.py -> Textures). Menu: Athen Hill → Vanguard Hall → Build assets (textures, materials,
    /// prefab; existing materials keep Inspector edits unless Rebuild materials is used), Install (refuses when the
    /// hall root exists), Verify saved scene. Replaced visuals stay in the scene, inactive, for rollback.
    /// The hall is not a render-chunk source: it keeps its own LODGroup and vertex-colour masonry.
    /// </summary>
    public static class VanguardHallPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/VanguardHall/";
        const string MatDir = Root + "Materials/";
        const string TexDir = Root + "Textures/";
        const string ModelDir = Root + "Models/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/VanguardHall/";
        const string PrefabPath = PrefabDir + "VanguardHall.prefab";
        const string Evidence = "../evidence/vanguard-hall/20260930/";
        public const string HallRootName = "Vanguard Hall";
        public static readonly Vector3 Pose = new Vector3(-10f, 0f, -26.55f);

        static readonly string[] Retired =
        {
            "Post-war salvage/Vanguard Hall repaired", "Ward district retrofit/Hall banners",
            "AuthoredWorld/BLD_hall_plinth", "AuthoredWorld/BLD_hall_step", "AuthoredWorld/COL_BLD_hall_plinth", "AuthoredWorld/COL_BLD_hall_step",
        };

        // salvage dressing that sat inside the new footprint moves to the west side of the podium (base pivots)
        static readonly (string path, Vector3 pos)[] Moved =
        {
            ("Post-war salvage/crate scatter 57", new Vector3(-17.35f, 0.01f, -26.4f)),
            ("Post-war salvage/scrap scatter 56", new Vector3(-17.6f, 0.01f, -32.2f)),
            ("Post-war salvage/trash scatter 59", new Vector3(-16.9f, 0.01f, -34.4f)),
        };

        // ------------------------------------------------------------------ assets
        [MenuItem("Athen Hill/Vanguard Hall/Build assets")]
        public static void BuildAssets() => Build(false);

        [MenuItem("Athen Hill/Vanguard Hall/Build assets (rebuild materials)")]
        public static void BuildAssetsRebuildMaterials() => Build(true);

        static void Build(bool rebuildMaterials)
        {
            ConfigureTextures();
            ConfigureStreakMap();
            ConfigureModels();
            var mats = BuildMaterials(rebuildMaterials);
            BuildPrefab(mats);
            AssetDatabase.SaveAssets();
        }

        static void ConfigureTextures()
        {
            var guids = AssetDatabase.FindAssets("t:Texture", new[] { TexDir.TrimEnd('/') });
            try
            {
                AssetDatabase.StartAssetEditing();
                foreach (var g in guids)
                {
                    var path = AssetDatabase.GUIDToAssetPath(g);
                    if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                    var file = Path.GetFileNameWithoutExtension(path);
                    bool normal = file.EndsWith("_Normal"), mask = file.EndsWith("_Mask"), banner = file.StartsWith("VH_Banner");
                    bool big = file.StartsWith("VH_Ashlar") || file.StartsWith("VH_Sandstone");
                    ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                    ti.sRGBTexture = !normal && !mask;
                    ti.alphaIsTransparency = banner && file.EndsWith("_BaseMap");
                    ti.alphaSource = banner && file.EndsWith("_BaseMap") ? TextureImporterAlphaSource.FromInput : (mask ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None);
                    ti.maxTextureSize = mask ? 2048 : big ? 4096 : 2048;
                    ti.mipmapEnabled = true;
                    ti.streamingMipmaps = true;
                    ti.anisoLevel = 8;
                    ti.wrapMode = banner ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
                    ti.textureCompression = TextureImporterCompression.CompressedHQ;
                    ti.SaveAndReimport();
                }
            }
            finally { AssetDatabase.StopAssetEditing(); }
            AssetDatabase.Refresh();
        }

        static void ConfigureModels()
        {
            // glTFast importer: keep defaults (imported meshes keep vertex colours and exported tangents)
            AssetDatabase.ImportAsset(ModelDir + "VanguardHall_LOD0.glb", ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(ModelDir + "VanguardHall_LOD1.glb", ImportAssetOptions.ForceUpdate);
        }

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

        static Texture2D Tex(string set, string kind) => AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + set + "_" + kind + (kind == "Mask" || set == "VH_Banner" && kind == "BaseMap" ? ".png" : ".jpg"));

        static void SetupLit(Material m, string set, Color color, float tileMetres, float smoothness = 1f, float bump = 1f)
        {
            m.SetTexture("_BaseMap", set != null ? Tex(set, "BaseMap") : null);
            m.SetColor("_BaseColor", color);
            var scale = Vector2.one / tileMetres;
            m.SetTextureScale("_BaseMap", scale);
            if (set != null)
            {
                m.SetTexture("_BumpMap", Tex(set, "Normal")); m.EnableKeyword("_NORMALMAP"); m.SetFloat("_BumpScale", bump);
                m.SetTexture("_MetallicGlossMap", Tex(set, "Mask")); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetTexture("_OcclusionMap", Tex(set, "Mask")); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1);
            }
            m.SetFloat("_Smoothness", smoothness);
            m.SetFloat("_SmoothnessTextureChannel", 0);
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
        }

        static void Detail(Material m, string set, float normalScale, float tileMetres)
        {
            m.SetTexture("_DetailNormalMap", Tex(set, "Normal")); m.SetFloat("_DetailNormalMapScale", normalScale);
            m.SetTextureScale("_DetailAlbedoMap", Vector2.one * (2f / tileMetres)); // relative to the base tiling
            m.EnableKeyword("_DETAIL_MULX2");
        }

        static void Masonry(Material m, float wear, float baseWear)
        {
            m.SetFloat("_BlockTint", 1f); m.SetFloat("_BlockAO", 1f);
            m.SetFloat("_WearStrength", wear); m.SetFloat("_WearScale", .22f); m.SetFloat("_BaseWear", baseWear);
            m.SetColor("_WearTint", new Color(.62f, .55f, .45f));
            MasonryWeathering(m, 1f, 1f);
        }

        public const string StreakMapPath = TexDir + "WardRunoff_Streaks.png";

        /// 30 Sep 2026 weathering pass (Carl: flat shade, clean edges, faint rain stains): runoff streaks (mesh UV1.x),
        /// worn arrises (UV1.y), rust trails (UV2.x), dust on upward faces, ray-traced vertex sky occlusion.
        public static void MasonryWeathering(Material m, float edgeWear, float streaks)
        {
            m.SetTexture("_StreakMap", AssetDatabase.LoadAssetAtPath<Texture2D>(StreakMapPath));
            m.SetVector("_StreakScale", new Vector4(.45f, .125f, 0, 0));
            m.SetFloat("_StreakStrength", streaks); m.SetColor("_StreakTint", new Color(.44f, .40f, .35f));
            m.SetColor("_DepositTint", new Color(1.12f, 1.1f, 1.05f));
            m.SetFloat("_RustStrength", 1f); m.SetColor("_RustTint", new Color(.6f, .37f, .23f));
            m.SetFloat("_EdgeWear", edgeWear); m.SetColor("_EdgeTint", new Color(1.2f, 1.16f, 1.08f)); m.SetFloat("_EdgeNoiseScale", 24f);
            m.SetFloat("_TopDust", .5f); m.SetColor("_DustTint", new Color(.8f, .68f, .52f));
            m.SetFloat("_CavityAlbedo", .6f);
            BattleGrime(m, edgeWear > 0 ? 1f : .5f);
            EditorUtility.SetDirty(m);
        }

        /// 30 Sep 2026 (Carl: "everything needs a little more weathering, dirt, grime and general 'this place saw a battle
        /// take place long ago'", West Gate arches as the reference): old pitting, shrapnel scars in the baked impact
        /// clusters, grime packed on the arrises, heavier broad dirt and wall-foot soiling, darker runoff.
        public static void BattleGrime(Material m, float amount)
        {
            m.SetFloat("_Pitting", .45f * amount); m.SetFloat("_PitScale", 7f);
            m.SetFloat("_BattleDamage", 1.15f * amount); m.SetFloat("_ScarScale", 1.7f);
            m.SetFloat("_EdgeGrime", .65f * amount);
            m.SetFloat("_WearStrength", .5f); m.SetColor("_WearTint", new Color(.52f, .45f, .36f)); m.SetFloat("_BaseWear", .6f);
            m.SetFloat("_StreakStrength", Mathf.Max(m.GetFloat("_StreakStrength"), 1.4f * amount));
            m.SetColor("_StreakTint", new Color(.36f, .32f, .28f));
            EditorUtility.SetDirty(m);
        }

        static void ConfigureStreakMap()
        {
            AssetDatabase.ImportAsset(StreakMapPath, ImportAssetOptions.ForceUpdate);
            if (AssetImporter.GetAtPath(StreakMapPath) is not TextureImporter ti) throw new Exception("Streak map missing: " + StreakMapPath);
            ti.textureType = TextureImporterType.Default; ti.sRGBTexture = false; ti.alphaSource = TextureImporterAlphaSource.None;
            ti.mipmapEnabled = true; ti.streamingMipmaps = true; ti.anisoLevel = 8; ti.wrapMode = TextureWrapMode.Repeat;
            ti.maxTextureSize = 2048; ti.textureCompression = TextureImporterCompression.CompressedHQ;
            ti.SaveAndReimport();
        }

        public const float Lod0ScreenHeight = .40f;

        /// Applies the weathering pass to the installed hall without rebuilding the prefab (keeps its light bindings):
        /// streak map import, re-imported GLBs (new UV1/UV2 wear channels and vertex AO), masonry material
        /// properties, LOD0 cut and probe-only GI on the renderers (UV1 carries wear data, never lightmap UVs).
        [MenuItem("Athen Hill/Vanguard Hall/Apply weathering pass")]
        public static string ApplyWeathering()
        {
            ConfigureStreakMap();
            ConfigureModels();
            foreach (var (name, edge, streak) in new[] { ("VH_Ashlar", 1f, 1.4f), ("VH_AshlarRough", 1.15f, 1.4f), ("VH_Mortar", 0f, 1f), ("VH_PodiumSlab", .9f, .5f) })
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(MatDir + name + ".mat");
                if (!m) continue;
                MasonryWeathering(m, edge, streak);
                if (name == "VH_Ashlar") m.SetFloat("_BumpScale", 1f);
                if (name == "VH_Mortar") m.SetColor("_BaseColor", new Color(.56f, .51f, .44f));   // grime-packed joints (West Gate)
                if (name == "VH_PodiumSlab") { m.SetFloat("_Pitting", .2f); m.SetFloat("_BaseWear", 0f); }
            }
            var root = PrefabUtility.LoadPrefabContents(PrefabPath);
            int renderers = 0;
            try
            {
                var group = root.GetComponent<LODGroup>();
                var lods = group.GetLODs();
                lods[0].screenRelativeTransitionHeight = Lod0ScreenHeight;
                group.SetLODs(lods);
                foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
                {
                    r.receiveGI = ReceiveGI.LightProbes;
                    GameObjectUtility.SetStaticEditorFlags(r.gameObject, GameObjectUtility.GetStaticEditorFlags(r.gameObject) & ~StaticEditorFlags.ContributeGI);
                    renderers++;
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            AssetDatabase.SaveAssets();
            return "weathering applied; renderers " + renderers;
        }

        public static Dictionary<string, Material> BuildMaterials(bool rebuild)
        {
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var masonry = Shader.Find("Athen Hill/Masonry Lit");
            var window = Shader.Find("Athen Hill/Ward Window Interior");
            if (!masonry) throw new Exception("Athen Hill/Masonry Lit shader missing (Art/VanguardHall/Shaders)");
            var mats = new Dictionary<string, Material>();
            void Make(string name, Shader shader, Action<Material> setup) { var m = NewOrLoad(name, shader, rebuild, out bool s); mats[name] = m; if (s) setup(m); }

            Make("VH_Ashlar", masonry, m => { SetupLit(m, "VH_Ashlar", Color.white, 2f, 1f, .7f); Masonry(m, .3f, .35f); });
            Make("VH_AshlarRough", masonry, m => { SetupLit(m, "VH_Sandstone", new Color(.94f, .92f, .88f), 2f); Masonry(m, .3f, .45f); });
            Make("VH_Mortar", masonry, m => { SetupLit(m, "VH_Sandstone", new Color(.86f, .82f, .75f), 1.5f, .8f); Masonry(m, .2f, .3f); m.SetFloat("_BlockTint", 0); });
            Make("VH_PodiumSlab", masonry, m => { SetupLit(m, "VH_Sandstone", new Color(.98f, .95f, .9f), 2f); Masonry(m, .35f, 0f); });
            Make("VH_Roof", lit, m => SetupLit(m, "VH_Sandstone", new Color(.66f, .62f, .56f), 2f, .8f));
            Make("VH_Sand", lit, m => SetupLit(m, "VH_Sand", new Color(1f, .95f, .88f), 1.8f));
            Make("VH_DoorSteel", lit, m => SetupLit(m, "VH_Rust", new Color(.62f, .55f, .52f), 2.2f));
            Make("VH_Steel", lit, m => SetupLit(m, "VH_SheetSteel", new Color(.72f, .67f, .63f), 2f));
            Make("VH_PaintedSteel", lit, m => SetupLit(m, "VH_Paint", new Color(.44f, .47f, .40f), 2f));
            Make("VH_Bronze", lit, m =>
            {
                SetupLit(m, "VH_Rust", new Color(.78f, .66f, .5f), 1.2f, .55f, .6f);
                m.SetTexture("_MetallicGlossMap", null); m.DisableKeyword("_METALLICSPECGLOSSMAP");
                m.SetFloat("_Metallic", .7f); m.SetFloat("_Smoothness", .4f);
            });
            Make("VH_PlateBronze", lit, m =>
            {
                SetupLit(m, "VH_Rust", new Color(.26f, .24f, .22f), 1.0f, .5f, .7f);
                m.SetTexture("_MetallicGlossMap", null); m.DisableKeyword("_METALLICSPECGLOSSMAP");
                m.SetFloat("_Metallic", .55f); m.SetFloat("_Smoothness", .32f);
            });
            Make("VH_Brass", lit, m =>
            {
                SetupLit(m, null, new Color(.86f, .66f, .36f), 1f, .62f);
                m.SetFloat("_Metallic", 1f);
            });
            Make("VH_Dark", lit, m => SetupLit(m, null, new Color(.03f, .03f, .028f), 1f, .2f));
            Make("VH_LampLens", lit, m =>
            {
                SetupLit(m, null, new Color(.9f, .82f, .7f), 1f, .85f);
                m.SetColor("_EmissionColor", new Color(1f, .8f, .55f) * 6f); m.EnableKeyword("_EMISSION");
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            });
            Make("VH_Rubber", lit, m => SetupLit(m, null, new Color(.035f, .035f, .035f), 1f, .3f));
            Make("VH_BeaconRed", lit, m =>
            {
                SetupLit(m, null, new Color(.5f, .05f, .03f), 1f, .7f);
                m.SetColor("_EmissionColor", new Color(1f, .06f, .03f) * 3f); m.EnableKeyword("_EMISSION");
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            });
            Make("VH_Banner", lit, m =>
            {
                m.SetTexture("_BaseMap", Tex("VH_Banner", "BaseMap")); m.SetColor("_BaseColor", Color.white);
                m.SetTextureScale("_BaseMap", Vector2.one);
                m.SetTexture("_MetallicGlossMap", Tex("VH_Banner", "Mask")); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetFloat("_Smoothness", 1f);
                m.SetTexture("_DetailNormalMap", Tex("VH_Linen", "Normal")); m.SetFloat("_DetailNormalMapScale", 1f);
                m.SetTextureScale("_DetailAlbedoMap", new Vector2(4.1f, 12.5f)); m.EnableKeyword("_DETAIL_MULX2");
                m.SetFloat("_AlphaClip", 1); m.SetFloat("_Cutoff", .5f); m.EnableKeyword("_ALPHATEST_ON"); m.renderQueue = (int)RenderQueue.AlphaTest;
                m.SetFloat("_Cull", 0); m.doubleSidedGI = true; m.enableInstancing = true;
                EditorUtility.SetDirty(m);
            });
            Make("VH_Glass", window, m =>
            {
                var src = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Quality/RelayArchitecture/Revision02/Materials/WardGlass.mat");
                if (src) m.CopyPropertiesFromMaterial(src);
                // hall rooms: ground floor 0.5-6.4, upper floor 6.4-12.3 (windows at 2.0-3.4 and 6.8-9.5), 4.5 m deep
                m.SetVector("_RoomSize", new Vector4(5.2f, 5.9f, 4.5f, 0));
                m.SetVector("_RoomOffset", new Vector4(Pose.x - 2.6f, .5f, Pose.z, 0));
                m.SetFloat("_RoomSeed", 17); m.SetFloat("_BlindAmount", .55f); m.SetFloat("_FurnitureAmount", .7f);
                m.SetFloat("_LitFraction", .6f); m.SetFloat("_CoolFraction", 0f); m.SetFloat("_DirtAmount", .45f);
                EditorUtility.SetDirty(m);
            });
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

        static JObject Record() => JObject.Parse(File.ReadAllText(ModelDir + "vanguard-hall.json"));

        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);

        public static void BuildPrefab(Dictionary<string, Material> mats)
        {
            Directory.CreateDirectory(PrefabDir);
            var rec = Record();
            var root = new GameObject("VanguardHall");
            var missing = new HashSet<string>();
            try
            {
                var levels = new List<LOD>();
                foreach (var (lod, cut) in new[] { (0, Lod0ScreenHeight), (1, .012f) })
                {
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelDir + $"VanguardHall_LOD{lod}.glb");
                    if (!model) throw new Exception("Model not imported: LOD" + lod);
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
                        bool glass = r.name.StartsWith("VH_Glass"), sand = r.name.StartsWith("VH_Sand");
                        r.shadowCastingMode = glass || sand ? ShadowCastingMode.Off : ShadowCastingMode.On;
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

                // collision proxies
                var cols = new GameObject("Colliders").transform; cols.SetParent(root.transform, false);
                foreach (var c in rec["colliders"])
                {
                    var go = new GameObject((string)c["name"]); go.transform.SetParent(cols, false);
                    var b = go.AddComponent<BoxCollider>(); b.center = V3(c["center"]); b.size = V3(c["size"]);
                }

                // fittings (Poly Haven CC0 props from the West Gate library)
                var fit = new GameObject("Fittings").transform; fit.SetParent(root.transform, false);
                var lampHeads = new List<Transform>();
                foreach (var mnt in rec["mounts"])
                {
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/WestGate/" + (string)mnt["prefab"] + ".prefab");
                    if (!prefab) { Debug.LogWarning("Vanguard Hall: missing prefab " + mnt["prefab"]); continue; }
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    go.name = (string)mnt["name"];
                    go.transform.SetParent(fit, false);
                    go.transform.localPosition = V3(mnt["pos"]);
                    go.transform.localRotation = Quaternion.Euler(0, (float)mnt["yaw"], 0);
                    foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                    if (((string)mnt["prefab"]) == "PH_WallLamp")
                    {
                        lampHeads.Add(go.transform);
                        // glowing bulb inside the caged glass (follows the city light circuit through VH_LampLens)
                        var bulb = GameObject.CreatePrimitive(PrimitiveType.Sphere); bulb.name = "Bulb";
                        UnityEngine.Object.DestroyImmediate(bulb.GetComponent<Collider>());
                        bulb.transform.SetParent(go.transform, false); bulb.transform.localPosition = new Vector3(0, .215f, .015f); bulb.transform.localScale = Vector3.one * .07f;
                        var br = bulb.GetComponent<MeshRenderer>(); br.sharedMaterial = mats["VH_LampLens"]; br.shadowCastingMode = ShadowCastingMode.Off;
                    }
                }

                // practical lights (bound to the city light circuit on install)
                var lights = new GameObject("Practical lights").transform; lights.SetParent(root.transform, false);
                foreach (var head in lampHeads)
                {
                    var go = new GameObject(head.name + " light"); go.transform.SetParent(lights, false);
                    // warm point light at the caged bulb, in the range of the city's other wall lamps
                    var fwd = head.localRotation * Vector3.forward;
                    go.transform.localPosition = head.localPosition + Vector3.up * .215f + fwd * .2f;
                    var l = go.AddComponent<Light>();
                    bool recess = head.name.Contains("recess");
                    l.type = LightType.Point; l.color = new Color(1f, .78f, .52f); l.intensity = recess ? 3.2f : 4.6f; l.range = recess ? 5.5f : 8f;
                    l.shadows = LightShadows.None;
                }
                foreach (var spec in rec["lights"] ?? new JArray())
                {
                    var go = new GameObject((string)spec["name"]); go.transform.SetParent(lights, false);
                    var pos = V3(spec["pos"]); go.transform.localPosition = pos;
                    go.transform.localRotation = Quaternion.LookRotation(V3(spec["target"]) - pos, Vector3.up);
                    var l = go.AddComponent<Light>();
                    l.type = LightType.Spot; var c = spec["color"]; l.color = new Color((float)c[0], (float)c[1], (float)c[2]);
                    l.intensity = (float)spec["intensity"]; l.range = (float)spec["range"]; l.spotAngle = (float)spec["angle"]; l.innerSpotAngle = (float)spec["inner"];
                    l.shadows = LightShadows.None;
                }
                var beacon = new GameObject("Mast beacon light"); beacon.transform.SetParent(lights, false);
                beacon.transform.localPosition = V3(rec["beacon"]);
                var bl = beacon.AddComponent<Light>(); bl.type = LightType.Point; bl.color = new Color(1f, .1f, .05f); bl.intensity = .8f; bl.range = 2.5f; bl.shadows = LightShadows.None;

                BuildDecals(root.transform);

                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (!t.GetComponent<Light>() && !t.GetComponent<UnityEngine.Rendering.Universal.DecalProjector>())
                        GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
            if (missing.Count > 0) Debug.LogWarning("Vanguard Hall: unmapped materials: " + string.Join(", ", missing));
        }

        // weathering decals: sill and scupper runoff, pier grime and sheltered wall-foot sediment, using the accepted
        // Ward weathering atlases (runoff quadrant of "Sand grime scuffs and runoff", LocalizedSedimentV1 WallFoot)
        static void BuildDecals(Transform root)
        {
            var runoff = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat");
            var foot = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/ReferenceStreet/20260910/LocalizedSedimentV1/WallFoot.mat");
            if (!runoff || !foot) { Debug.LogWarning("Vanguard Hall: weathering decal materials missing"); return; }
            var parent = new GameObject("Weathering decals").transform; parent.SetParent(root, false);
            int n = 0;
            // face: 0 front (+Z), 1 east (+X), 2 rear (-Z), 3 west (-X); u along the face, y height, planeOffset = face plane
            void Add(Material mat, Vector2 bias, int face, float plane, float u, float y, float w, float h, float fade, float depth = .5f)
            {
                var go = new GameObject((mat == foot ? "Wall foot sediment " : "Runoff ") + (++n)); go.transform.SetParent(parent, false);
                Vector3 nrm = face switch { 0 => Vector3.forward, 1 => Vector3.right, 2 => Vector3.back, _ => Vector3.left };
                Vector3 pos = face switch { 0 => new Vector3(u, y, plane), 1 => new Vector3(plane, y, u), 2 => new Vector3(u, y, plane), _ => new Vector3(plane, y, u) };
                go.transform.localPosition = pos + nrm * (depth * .5f - .12f);
                go.transform.localRotation = Quaternion.LookRotation(-nrm, Vector3.up);
                var d = go.AddComponent<UnityEngine.Rendering.Universal.DecalProjector>();
                d.material = mat; d.pivot = Vector3.zero; d.size = new Vector3(w, h, depth);
                d.uvScale = new Vector2(.49f, .49f); d.uvBias = bias; d.fadeFactor = fade; d.drawDistance = 45f;
            }
            var run = new Vector2(.51f, .01f); var sed = new Vector2(.51f, .51f);
            foreach (var x in new[] { -2.9f, -1.3f, 1.3f, 2.9f }) Add(runoff, run, 0, 0f, x, 6.05f, .95f, 1.1f, .55f);
            foreach (var x in new[] { -3.2f, 3.2f }) Add(runoff, run, 0, .5f, x, 10.72f, .55f, .8f, .6f, .4f);
            foreach (var x in new[] { -4.75f, 4.75f }) Add(runoff, run, 0, .5f, x, 9.55f, 1.3f, 1.7f, .35f, .7f);
            foreach (var x in new[] { -3.15f, 3.15f }) Add(runoff, run, 0, 0f, x, 1.45f, .7f, .8f, .4f);
            foreach (var z in new[] { -3.05f, -5.45f }) { Add(runoff, run, 1, 5f, z, 6.05f, .85f, 1.1f, .5f); Add(runoff, run, 3, -5f, z, 6.05f, .85f, 1.1f, .5f); }
            foreach (var z in new[] { -3.0f, -6.4f }) Add(runoff, run, 1, 5.5f, z, 10.72f, .55f, .8f, .6f, .4f);
            Add(runoff, run, 3, -5.5f, -5.6f, 10.72f, .55f, .8f, .6f, .4f);
            Add(runoff, run, 2, -8.5f, 1.5f, 6.05f, .95f, 1.1f, .55f);
            foreach (var x in new[] { -2.6f, 2.8f }) Add(runoff, run, 2, -9f, x, 10.72f, .55f, .8f, .6f, .4f);
            Add(runoff, run, 2, -8.5f, 1.75f, 2.9f, 1.6f, .9f, .45f);
            foreach (var x in new[] { -3.0f, 3.0f }) Add(foot, sed, 0, 0f, x, .72f, 1.35f, .42f, .4f);
            Add(foot, sed, 1, 5f, -4.2f, .72f, 4.6f, .42f, .35f); Add(foot, sed, 3, -5f, -4.2f, .72f, 4.6f, .42f, .4f);
            Add(foot, sed, 2, -8.5f, -1.2f, .72f, 4.6f, .42f, .4f);
        }

        // ------------------------------------------------------------------ install
        [MenuItem("Athen Hill/Vanguard Hall/Install rebuilt hall")]
        public static void Install() => Install(false);

        /// Authoring iteration only: removes the installed hall root (and restores nothing else) before installing again.
        public static void Reinstall() => Install(true);

        static Transform FindPath(string path)
        {
            var parts = path.Split('/');
            var top = SceneManager().GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!top) return null;
            var t = top.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Cast<Transform>().FirstOrDefault(c => c.name == parts[i]);
            return t;
        }

        static UnityEngine.SceneManagement.Scene SceneManager() => EditorSceneManager.GetActiveScene();

        static void Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = SceneManager();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath);
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == HallRootName);
            if (existing && !replace) throw new Exception("Vanguard Hall is already installed; edit it in place or use Reinstall during authoring.");
            if (existing) UnityEngine.Object.DestroyImmediate(existing);
            Directory.CreateDirectory(Evidence + "rollback");
            if (!replace) File.Copy(ScenePath, Evidence + "rollback/before-install-saved-by-pass.unity", true);

            var record = new Dictionary<string, object>();
            var retired = new List<object>();
            foreach (var p in Retired)
            {
                var t = FindPath(p);
                if (!t) { retired.Add(new { path = p, found = false }); continue; }
                retired.Add(new { path = p, found = true, wasActive = t.gameObject.activeSelf });
                Undo.RecordObject(t.gameObject, "Retire hall visual");
                t.gameObject.SetActive(false);
            }
            record["retired"] = retired;
            var moved = new List<object>();
            foreach (var (p, pos) in Moved)
            {
                var t = FindPath(p);
                if (!t) { moved.Add(new { path = p, found = false }); continue; }
                moved.Add(new { path = p, from = new[] { t.position.x, t.position.y, t.position.z }, to = new[] { pos.x, pos.y, pos.z } });
                Undo.RecordObject(t, "Move salvage");
                t.position = pos;
            }
            record["moved"] = moved;

            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            var hall = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
            hall.name = HallRootName;
            hall.transform.SetPositionAndRotation(Pose, Quaternion.identity);
            record["pose"] = new[] { Pose.x, Pose.y, Pose.z };

            // lights: warm lamps are night lights on the city circuit; the glass joins the circuit's emissive set
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var lamps = hall.GetComponentsInChildren<Light>(true).Where(l => !l.name.StartsWith("Mast")).ToArray();
            circuit.practicalLights = circuit.practicalLights.Where(l => l && !l.transform.IsChildOf(hall.transform)).Concat(lamps).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !l.transform.IsChildOf(hall.transform)).Concat(lamps).ToArray();
            foreach (var em in new[] { "VH_Glass", "VH_LampLens" })
            {
                var mat = AssetDatabase.LoadAssetAtPath<Material>(MatDir + em + ".mat");
                if (mat && !circuit.emissiveMaterials.Contains(mat)) circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { mat }).ToArray();
            }
            EditorUtility.SetDirty(circuit);
            record["lights"] = lamps.Select(l => l.name).ToArray();

            // render chunks: the retired plinth/step and Meshy hall were chunk sources
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            record["chunksRebuilt"] = chunks != null;

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + (replace ? "reinstall.json" : "install.json"), JsonConvert.SerializeObject(record, Formatting.Indented));
            Debug.Log("Vanguard Hall installed: " + JsonConvert.SerializeObject(record));
        }

        // ------------------------------------------------------------------ review cameras (native lookbook / QA)
        static readonly (string name, Vector3 pos, Vector3 target, float fov)[] ReviewViews =
        {
            ("cam_vh_plaza", new Vector3(-3.5f, 1.65f, -12f), new Vector3(-10f, 6.5f, -27f), 60),
            ("cam_vh_front", new Vector3(-10f, 1.65f, -14.5f), new Vector3(-10f, 7f, -27f), 60),
            ("cam_vh_portal", new Vector3(-9f, 1.65f, -22.2f), new Vector3(-10f, 2.7f, -27.5f), 60),
            ("cam_vh_pier", new Vector3(-2.9f, 1.65f, -22.9f), new Vector3(-5.3f, 2.3f, -26.5f), 60),
            ("cam_vh_upper", new Vector3(-8.4f, 1.65f, -19.5f), new Vector3(-9.4f, 9.2f, -27f), 55),
            ("cam_vh_nameplate", new Vector3(-10f, 1.65f, -21.5f), new Vector3(-10f, 5.7f, -26.5f), 40),
            ("cam_vh_west", new Vector3(-21.5f, 1.65f, -27.5f), new Vector3(-12f, 5.5f, -31f), 60),
            ("cam_vh_rear", new Vector3(-4.5f, 1.65f, -41f), new Vector3(-10f, 5f, -35f), 60),
            ("cam_vh_lattice", new Vector3(1.8f, 1.65f, -31f), new Vector3(-8f, 5f, -31f), 60),
        };

        [MenuItem("Athen Hill/Vanguard Hall/Add review cameras")]
        public static void ReviewCameras()
        {
            var scene = SceneManager();
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Vanguard Hall review cameras");
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject("Vanguard Hall review cameras");
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
        [MenuItem("Athen Hill/Vanguard Hall/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var r = new Dictionary<string, object>();
            var hall = scene.GetRootGameObjects().FirstOrDefault(g => g.name == HallRootName);
            r["installed"] = hall != null;
            if (hall)
            {
                r["prefabLinked"] = PrefabUtility.IsPartOfPrefabInstance(hall);
                r["position"] = new[] { hall.transform.position.x, hall.transform.position.y, hall.transform.position.z };
                r["lossyScale"] = new[] { hall.transform.lossyScale.x, hall.transform.lossyScale.y, hall.transform.lossyScale.z };
                var lg = hall.GetComponent<LODGroup>();
                r["lods"] = lg ? lg.GetLODs().Select(l => new { l.screenRelativeTransitionHeight, renderers = l.renderers.Length, triangles = l.renderers.Sum(x => x.GetComponent<MeshFilter>() ? x.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3 : 0) }).ToArray() : null;
                r["colliders"] = hall.GetComponentsInChildren<Collider>(true).Select(c => new { c.name, c.bounds.center.x, c.bounds.center.y, c.bounds.center.z, sx = c.bounds.size.x, sy = c.bounds.size.y, sz = c.bounds.size.z }).ToArray();
                r["materials"] = hall.GetComponentsInChildren<Renderer>(true).SelectMany(x => x.sharedMaterials).Where(m => m).Select(m => m.name + " (" + m.shader.name + ")").Distinct().OrderBy(x => x).ToArray();
                r["missingMaterials"] = hall.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(m => !m));
                var mesh0 = hall.transform.Find("LOD0").GetComponentsInChildren<MeshFilter>(true).Select(f => new { f.name, verts = f.sharedMesh.vertexCount, colors = f.sharedMesh.colors32.Length, tangents = f.sharedMesh.tangents.Length }).ToArray();
                r["lod0Meshes"] = mesh0;
            }
            r["retired"] = Retired.Select(p => { var t = FindPath(p); return new { path = p, found = t != null, activeSelf = t && t.gameObject.activeSelf }; }).ToArray();
            r["moved"] = Moved.Select(m => { var t = FindPath(m.path); return new { m.path, pos = t ? new[] { t.position.x, t.position.y, t.position.z } : null }; }).ToArray();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            r["circuitLights"] = circuit.practicalLights.Count(l => l && hall && l.transform.IsChildOf(hall.transform));
            r["circuitGlass"] = circuit.emissiveMaterials.Any(m => m && m.name == "VH_Glass");
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }
    }
}
