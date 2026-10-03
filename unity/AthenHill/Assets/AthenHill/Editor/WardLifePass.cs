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
    /// 3 October 2026: Ward life pass (art/ward_life_20261003, README.md). Three weak spots made to explain how Ward
    /// survives: the West Gate bastions rebuilt as real filled gabions (Carl's open item "gabion bastions read as tiled
    /// boxes"), the empty court behind Vanguard Hall (old Lattice Jack site) as the Wardens' water ration point, and the
    /// empty paving east of the Meshy ring as the Node 07 goods dock. Blender sources: bake_gabion.py, bake_marks.py,
    /// author_life.py → Art/WardLife/{Textures,Models}; placements: layout.py → layout.json (validated there).
    ///
    /// Steps (batch: RunBatch --steps a,b:arg,... [--out dir]):
    ///   survey               — read-only dump of colliders/renderers/lights/markers/cameras round the three spots
    ///   build                — texture import settings, WL_* materials, Prefabs/WardLife/&lt;Model&gt;.prefab (LODs, colliders,
    ///                          mounts, wall lamps) for every model in layout.models
    ///   install / reinstall  — one scene root per spot ("Ward life: …"), retire the replaced root (deactivated, kept),
    ///                          lamps onto the Ward lighting clock, decals, review cameras cam_wl_*; rollback copy of the
    ///                          scene on the first install
    ///   verify               — saved-scene checks (installed, prefab links, materials, lights, retired inactive, chunk
    ///                          fingerprint, collider clearance against routes/NPC/landmark markers, overlaps)
    ///   budget               — per review camera: local lights in view and this pass's triangles at the selected LOD
    ///   capture[:prefix]     — editor captures of the review cameras (≤ 6 per run), never saves
    ///   rollback             — deactivate the Ward life roots and re-activate what they retired (saves)
    /// Nothing is deleted: the round-two bastions stay in the scene inactive.
    /// </summary>
    public static class WardLifePass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/WardLife/";
        const string TexDir = Root + "Textures/";
        const string ModelDir = Root + "Models/";
        const string MatDir = Root + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/WardLife/";
        const string LayoutPath = "../../art/ward_life_20261003/layout.json";
        const string Evidence = "../evidence/ward-life/20261003/";
        const string NightMats = "Assets/AthenHill/Art/NightFacade/";
        const string PhGlassPath = "Assets/AthenHill/Art/WestGate/Materials/PH_industrial_wall_lamp_glass.mat";
        static readonly string[] MatSearch =
        {
            MatDir, "Assets/AthenHill/Art/WardBuildings/Materials/", "Assets/AthenHill/Art/VanguardHall/Materials/",
            "Assets/AthenHill/Art/WardShops/Materials/", "Assets/AthenHill/Art/WestGate/Materials/",
            "Assets/AthenHill/Art/TrainingRange/Materials/", "Assets/AthenHill/Art/WestGateArches/Materials/",
            "Assets/AthenHill/Art/NightFacade/Materials/", "Assets/AthenHill/Art/StreetDressing/Materials/",
            "Assets/AthenHill/Art/Weathering/",
        };
        const float LodBias = 2f;

        static JObject Layout() => JObject.Parse(File.ReadAllText(LayoutPath));
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] F3(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };

        static Transform FindPath(UnityEngine.SceneManagement.Scene scene, string path)
        {
            var parts = path.Split('/');
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!root) return null;
            var t = root.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Cast<Transform>().FirstOrDefault(c => c.name == parts[i]);
            return t;
        }

        static int Tris(Renderer r)
        {
            var mf = r ? r.GetComponent<MeshFilter>() : null;
            if (!mf || !mf.sharedMesh) return 0;
            int n = 0;
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) n += (int)mf.sharedMesh.GetIndexCount(s) / 3;
            return n;
        }

        // ------------------------------------------------------------------ survey (read-only)
        static readonly (string name, Rect r)[] Regions =
        {
            ("gate", Rect.MinMaxRect(26f, -24f, 54f, 32f)),
            ("court", Rect.MinMaxRect(-18f, -50f, 16f, -16f)),
            ("plaza", Rect.MinMaxRect(-22f, 10f, 22f, 44f)),
        };

        static string RegionOf(Bounds b)
        {
            foreach (var (n, r) in Regions)
                if (b.max.x >= r.xMin && b.min.x <= r.xMax && b.max.z >= r.yMin && b.min.z <= r.yMax) return n;
            return null;
        }

        public static string Survey(string outDir)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var cols = new List<object>(); var rends = new List<object>(); var lights = new List<object>();
            var markers = new List<object>(); var cams = new List<object>();
            foreach (var root in scene.GetRootGameObjects())
            {
                bool route = root.name.EndsWith(" route") || root.name == "Landmarks" || root.name == "Colonists";
                if (route) foreach (Transform c in root.transform) markers.Add(new { path = PathOf(c), pos = F3(c.position) });
                if (root.name == "Player" || root.name.EndsWith(" interaction") || root.name.StartsWith("npc_"))
                    markers.Add(new { path = root.name, pos = F3(root.transform.position) });
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (t.name == "NPC sit point")
                        markers.Add(new { path = PathOf(t), pos = F3(t.position), active = t.gameObject.activeInHierarchy });
                foreach (var c in root.GetComponentsInChildren<Collider>(true))
                {
                    if (!c.gameObject.activeInHierarchy || !c.enabled || c is TerrainCollider) continue;
                    var reg = RegionOf(c.bounds);
                    if (reg == null || c.bounds.size.x > 80 || c.bounds.size.z > 80) continue;
                    cols.Add(new { reg, path = PathOf(c.transform), center = F3(c.bounds.center), size = F3(c.bounds.size), trigger = c.isTrigger });
                }
                foreach (var r in root.GetComponentsInChildren<Renderer>(true))
                {
                    if (!r.gameObject.activeInHierarchy || !r.enabled) continue;
                    var reg = RegionOf(r.bounds);
                    if (reg == null || r.bounds.size.x > 80 || r.bounds.size.z > 80) continue;
                    var lg = r.GetComponentInParent<LODGroup>();
                    if (lg && lg.GetLODs().Length > 0 && !lg.GetLODs()[0].renderers.Contains(r)) continue;
                    var pr = PrefabUtility.GetNearestPrefabInstanceRoot(r.gameObject);
                    rends.Add(new { reg, path = PathOf(r.transform), prefab = pr ? PathOf(pr.transform) : null, min = F3(r.bounds.min), max = F3(r.bounds.max) });
                }
                foreach (var l in root.GetComponentsInChildren<Light>(true))
                {
                    if (l.type == LightType.Directional) continue;
                    var reg = RegionOf(new Bounds(l.transform.position, Vector3.one));
                    if (reg == null) continue;
                    lights.Add(new { reg, path = PathOf(l.transform), pos = F3(l.transform.position), range = l.range, active = l.gameObject.activeInHierarchy && l.enabled });
                }
                foreach (var c in root.GetComponentsInChildren<Camera>(true))
                    if (c.name.StartsWith("cam_")) cams.Add(new { name = c.name, pos = F3(c.transform.position), fwd = F3(c.transform.forward), fov = c.fieldOfView });
            }
            var rootsInfo = scene.GetRootGameObjects().Select(g => new { g.name, active = g.activeSelf }).ToArray();
            Directory.CreateDirectory(outDir);
            File.WriteAllText(Path.Combine(outDir, "survey.json"), JsonConvert.SerializeObject(new { colliders = cols, renderers = rends, lights, markers, cameras = cams, roots = rootsInfo }, Formatting.Indented));
            return "survey: " + cols.Count + " colliders, " + rends.Count + " renderers, " + lights.Count + " lights, " + markers.Count + " markers, " + cams.Count + " cameras";
        }

        // ------------------------------------------------------------------ textures and materials
        static void ImportTextures(List<string> log)
        {
            AssetDatabase.Refresh();
            foreach (var file in Directory.GetFiles(TexDir, "*.png"))
            {
                var path = file.Replace('\\', '/');
                var name = Path.GetFileNameWithoutExtension(path);
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                if (!ti) { log.Add("no importer " + path); continue; }
                ti.textureType = name.EndsWith("_Normal") ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !(name.EndsWith("_Normal") || name.EndsWith("_Mask") || name.EndsWith("_Height"));
                ti.mipmapEnabled = true;
                ti.streamingMipmaps = true;
                ti.anisoLevel = 4;
                ti.maxTextureSize = 2048;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                bool alpha = name.Contains("Wire") && name.EndsWith("_BaseMap") || name.StartsWith("WL_Decal");
                ti.alphaIsTransparency = alpha;
                ti.alphaSource = alpha || name.EndsWith("_Mask") ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                if (name.Contains("Wire") && name.EndsWith("_BaseMap")) { ti.mipMapsPreserveCoverage = true; ti.alphaTestReferenceValue = .5f; }
                ti.wrapMode = name.StartsWith("WL_Decal") ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
                ti.SaveAndReimport();
                log.Add("texture " + name);
            }
        }

        static Texture2D Tex(string name) => AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + name + ".png");

        static Material MakeMat(string name, Material template, Shader shader = null)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m)
            {
                m = template ? new Material(template) : new Material(shader);
                m.name = name;
                AssetDatabase.CreateAsset(m, path);
            }
            else if (template) { m.shader = template.shader; m.CopyPropertiesFromMaterial(template); }
            else if (shader) m.shader = shader;
            return m;
        }

        static void BuildMaterials(List<string> log)
        {
            var ashlar = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/VanguardHall/Materials/VH_AshlarRough.mat");
            var hessian = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/WestGate/Materials/WG_Hessian.mat");
            var decal = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/WallFootDrifts/Materials/WFD_DecalSheet.mat");
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            if (!ashlar || !hessian || !decal || !lit) throw new Exception("template material missing (VH_AshlarRough / WG_Hessian / WFD_DecalSheet / URP Lit)");
            var scale = Vector2.one / 1.5f;     // the fill bake covers 1.5 m
            foreach (var (n, wired) in new[] { ("WL_GabionFill", false), ("WL_GabionFillWired", true) })
            {
                var m = MakeMat(n, ashlar);
                m.SetTexture("_BaseMap", Tex(wired ? "WL_GabionFillWired_BaseMap" : "WL_GabionFill_BaseMap"));
                m.SetTextureScale("_BaseMap", scale); m.SetTextureOffset("_BaseMap", Vector2.zero);
                m.SetColor("_BaseColor", new Color(1.32f, 1.27f, 1.2f));   // the bake reads darker than Ward's sunlit stone
                m.SetTexture("_BumpMap", Tex(wired ? "WL_GabionFillWired_Normal" : "WL_GabionFill_Normal")); m.SetFloat("_BumpScale", 1f); m.EnableKeyword("_NORMALMAP");
                m.SetTexture("_MetallicGlossMap", Tex("WL_GabionFill_Mask")); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetTexture("_OcclusionMap", Tex("WL_GabionFill_Mask")); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1f);
                m.SetFloat("_Smoothness", 1f);
                if (!wired) { m.SetTexture("_ParallaxMap", Tex("WL_GabionFill_Height")); m.SetFloat("_Parallax", .025f); m.EnableKeyword("_PARALLAXMAP"); }
                else { m.SetTexture("_ParallaxMap", null); m.DisableKeyword("_PARALLAXMAP"); }
                // stone fill: rubble wear, less arris/edge treatment than dressed ashlar
                if (m.HasProperty("_EdgeWear")) m.SetFloat("_EdgeWear", .3f);
                if (m.HasProperty("_Pitting")) m.SetFloat("_Pitting", .25f);
                if (m.HasProperty("_TopDust")) m.SetFloat("_TopDust", .55f);
                if (m.HasProperty("_BattleDamage")) m.SetFloat("_BattleDamage", 1.2f);
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
                log.Add("material " + n);
            }
            foreach (var (n, fresh) in new[] { ("WL_GabionWire", false), ("WL_GabionWireFresh", true) })
            {
                var m = MakeMat(n, null, lit);
                m.SetTexture("_BaseMap", Tex(fresh ? "WL_GabionWireFresh_BaseMap" : "WL_GabionWire_BaseMap"));
                m.SetTextureScale("_BaseMap", Vector2.one);
                m.SetColor("_BaseColor", Color.white);
                m.SetTexture("_BumpMap", Tex("WL_GabionWire_Normal")); m.EnableKeyword("_NORMALMAP"); m.SetFloat("_BumpScale", 1f);
                m.SetTexture("_MetallicGlossMap", Tex(fresh ? "WL_GabionWireFresh_Mask" : "WL_GabionWire_Mask")); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetTexture("_OcclusionMap", Tex(fresh ? "WL_GabionWireFresh_Mask" : "WL_GabionWire_Mask")); m.EnableKeyword("_OCCLUSIONMAP");
                m.SetFloat("_Smoothness", 1f);
                m.SetFloat("_AlphaClip", 1f); m.SetFloat("_Cutoff", .5f); m.EnableKeyword("_ALPHATEST_ON");
                m.SetOverrideTag("RenderType", "TransparentCutout"); m.renderQueue = (int)RenderQueue.AlphaTest;
                m.SetFloat("_Cull", 0f); m.doubleSidedGI = true;
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
                log.Add("material " + n);
            }
            foreach (var (n, k) in new[] { ("WL_HessianOld", new Color(.74f, .7f, .64f)), ("WL_HessianPale", new Color(1.16f, 1.12f, 1.04f)) })
            {
                var m = MakeMat(n, hessian);
                m.SetColor("_BaseColor", k);
                EditorUtility.SetDirty(m);
                log.Add("material " + n);
            }
            foreach (var n in new[] { "WL_DecalMarks", "WL_DecalDamp" })
            {
                var m = MakeMat(n, decal);
                m.SetTexture("Base_Map", Tex(n));
                if (m.HasProperty("Normal_Blend")) m.SetFloat("Normal_Blend", 0);
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
                log.Add("material " + n);
            }
            AssetDatabase.SaveAssets();
        }

        static readonly Dictionary<string, Material> matCache = new Dictionary<string, Material>();

        static Material FindMat(string name)
        {
            name = System.Text.RegularExpressions.Regex.Replace(name.Replace(" (Instance)", ""), @"\.\d+$", "");
            if (matCache.TryGetValue(name, out var m) && m) return m;
            foreach (var d in MatSearch)
            {
                m = AssetDatabase.LoadAssetAtPath<Material>(d + name + ".mat");
                if (m) { matCache[name] = m; return m; }
            }
            return null;
        }

        // ------------------------------------------------------------------ prefabs
        static Dictionary<string, object> BuildModel(string key, string model, int nl, float[] dist)
        {
            for (int lod = 0; lod < nl; lod++) AssetDatabase.ImportAsset(ModelDir + model + "_LOD" + lod + ".glb", ImportAssetOptions.ForceUpdate);
            var rec = JObject.Parse(File.ReadAllText(ModelDir + key + ".json"));
            Directory.CreateDirectory(PrefabDir);
            var missing = new HashSet<string>();
            var root = new GameObject(model);
            var report = new Dictionary<string, object>();
            try
            {
                var levels = new List<LOD>();
                for (int lod = 0; lod < nl; lod++)
                {
                    var glb = ModelDir + model + "_LOD" + lod + ".glb";
                    var src = AssetDatabase.LoadAssetAtPath<GameObject>(glb);
                    if (!src) throw new Exception("Model not imported: " + glb);
                    var holder = new GameObject("LOD" + lod).transform; holder.SetParent(root.transform, false);
                    var rs = new List<Renderer>();
                    foreach (var mr in src.GetComponentsInChildren<MeshRenderer>(true))
                    {
                        var mf = mr.GetComponent<MeshFilter>();
                        if (!mf || !mf.sharedMesh) continue;
                        var go = new GameObject(mr.name); go.transform.SetParent(holder, false);
                        go.transform.localPosition = src.transform.InverseTransformPoint(mr.transform.position);
                        go.transform.localRotation = Quaternion.Inverse(src.transform.rotation) * mr.transform.rotation;
                        go.AddComponent<MeshFilter>().sharedMesh = mf.sharedMesh;
                        var r = go.AddComponent<MeshRenderer>();
                        var slots = mr.sharedMaterials;
                        for (int i = 0; i < slots.Length; i++)
                        {
                            var m = slots[i] ? FindMat(slots[i].name) : null;
                            if (m) slots[i] = m; else missing.Add(mr.name + ":" + (slots[i] ? slots[i].name : "null"));
                        }
                        r.sharedMaterials = slots;
                        var n = mr.name;
                        bool noShadow = n.Contains("_Glass_") || n.Contains("_Sand_") || n.Contains("_Glow_") || n.Contains("_Hardware_") || n.Contains("_Wire_");
                        r.shadowCastingMode = noShadow ? ShadowCastingMode.Off : ShadowCastingMode.On;
                        r.receiveShadows = true;
                        r.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
                        r.receiveGI = ReceiveGI.LightProbes; r.lightProbeUsage = LightProbeUsage.BlendProbes;
                        rs.Add(r);
                    }
                    if (rs.Count == 0) throw new Exception("no renderers in " + glb);
                    report["LOD" + lod] = rs.Sum(Tris);
                    levels.Add(new LOD(.5f / (lod + 1), rs.ToArray()));
                }
                var g = root.AddComponent<LODGroup>();
                g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                float H(float d) => Mathf.Clamp(g.size * LodBias / (2f * d * Mathf.Tan(30f * Mathf.Deg2Rad)), .003f, .98f);
                for (int i = 0; i < levels.Count; i++) levels[i] = new LOD(H(dist[Math.Min(i, dist.Length - 1)]), levels[i].renderers);
                for (int i = 1; i < levels.Count; i++) if (levels[i].screenRelativeTransitionHeight >= levels[i - 1].screenRelativeTransitionHeight)
                        levels[i] = new LOD(levels[i - 1].screenRelativeTransitionHeight * .5f, levels[i].renderers);
                g.SetLODs(levels.ToArray()); g.RecalculateBounds();
                report["lodCuts"] = levels.Select(l => Math.Round(l.screenRelativeTransitionHeight, 4)).ToArray();
                report["size"] = Math.Round(g.size, 2);

                var cols = new GameObject("Colliders").transform; cols.SetParent(root.transform, false);
                foreach (var c in rec["colliders"] ?? new JArray())
                {
                    var go = new GameObject((string)c["name"]); go.transform.SetParent(cols, false);
                    var bc = go.AddComponent<BoxCollider>();
                    bc.center = V3(c["center"]); bc.size = V3(c["size"]);
                }
                report["colliders"] = cols.childCount;

                var fit = new GameObject("Fittings").transform; fit.SetParent(root.transform, false);
                var lights = new GameObject("Practical lights").transform; lights.SetParent(root.transform, false);
                var bulbMat = AssetDatabase.LoadAssetAtPath<Material>(NightMats + "Materials/NF_WallLampBulb.mat");
                var glassMat = AssetDatabase.LoadAssetAtPath<Material>(NightMats + "Materials/NF_WallLampGlass.mat");
                var phGlass = AssetDatabase.LoadAssetAtPath<Material>(PhGlassPath);
                var cookie = AssetDatabase.LoadAssetAtPath<Texture2D>(NightMats + "Textures/NF_WallLampCookie.png");
                int lamps = 0;
                foreach (var mnt in rec["mounts"] ?? new JArray())
                {
                    var ppath = (string)mnt["path"] ?? "Assets/AthenHill/Prefabs/WestGate/" + (string)mnt["prefab"] + ".prefab";
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(ppath);
                    if (!prefab) { missing.Add("prefab " + ppath); continue; }
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    go.name = (string)mnt["name"];
                    go.transform.SetParent(fit, false);
                    go.transform.localPosition = V3(mnt["pos"]);
                    go.transform.localRotation = Quaternion.Euler(0, (float)mnt["yaw"], 0);
                    foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                    if ((string)mnt["prefab"] != "PH_WallLamp") continue;
                    foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                    {
                        r.shadowCastingMode = ShadowCastingMode.Off;
                        var ms = r.sharedMaterials;
                        for (int i = 0; i < ms.Length; i++) if (ms[i] == phGlass && glassMat) ms[i] = glassMat;
                        r.sharedMaterials = ms;
                    }
                    var bulb = GameObject.CreatePrimitive(PrimitiveType.Sphere); bulb.name = "Bulb";
                    UnityEngine.Object.DestroyImmediate(bulb.GetComponent<Collider>());
                    bulb.transform.SetParent(go.transform, false); bulb.transform.localPosition = new Vector3(0, .215f, .015f); bulb.transform.localScale = Vector3.one * .07f;
                    var br = bulb.GetComponent<MeshRenderer>(); br.sharedMaterial = bulbMat; br.shadowCastingMode = ShadowCastingMode.Off;
                    var lg = new GameObject(go.name + " light"); lg.transform.SetParent(lights, false);
                    var fwd = go.transform.localRotation * Vector3.forward;
                    lg.transform.localPosition = go.transform.localPosition + Vector3.up * .115f + fwd * .35f;
                    const float tilt = 10f;
                    var dir = (Vector3.down * Mathf.Cos(tilt * Mathf.Deg2Rad) + fwd * Mathf.Sin(tilt * Mathf.Deg2Rad)).normalized;
                    lg.transform.localRotation = Quaternion.LookRotation(dir, fwd);
                    var l = lg.AddComponent<Light>(); l.type = LightType.Spot; l.color = new Color(1f, .78f, .52f);
                    l.intensity = (float?)mnt["intensity"] ?? 5.46f; l.range = (float?)mnt["range"] ?? 7.5f;
                    l.spotAngle = 140f; l.innerSpotAngle = 95f; l.cookie = cookie; l.shadows = LightShadows.None;
                    lamps++;
                }
                report["lights"] = lamps;
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (!t.GetComponent<Light>())
                        GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + model + ".prefab");
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
            report["unmapped"] = missing.OrderBy(x => x).ToArray();
            return report;
        }

        public static string Build(string only)
        {
            var layout = Layout();
            var log = new List<string>();
            ImportTextures(log);
            BuildMaterials(log);
            var all = new Dictionary<string, object> { ["log"] = log };
            foreach (JObject m in layout["models"])
            {
                var key = (string)m["key"];
                if (!string.IsNullOrEmpty(only) && only != key) continue;
                all[key] = BuildModel(key, (string)m["model"], (int)m["lods"], m["lodDistances"].Select(x => (float)x).ToArray());
            }
            AssetDatabase.SaveAssets();
            var json = JsonConvert.SerializeObject(all, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "build-assets.json", json);
            return json;
        }

        // ------------------------------------------------------------------ install
        static Material DecalMat(string name)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(MatDir + name + ".mat");
            return m ? m : FindMat(name);
        }

        public static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            Directory.CreateDirectory(Evidence + "rollback");
            var rb = Evidence + "rollback/before-ward-life.unity";
            if (!File.Exists(rb)) File.Copy(ScenePath, rb, true);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            string fpBefore = chunks ? chunks.sourceFingerprint : null;
            var log = new List<string>();
            var record = new Dictionary<string, object>();
            foreach (JObject sp in layout["spots"])
            {
                var rootName = (string)sp["root"];
                var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == rootName);
                if (existing && !replace) throw new Exception(rootName + " is already installed; edit it in place (or reinstall during authoring).");
                if (existing)
                {
                    var old = existing.GetComponentsInChildren<Light>(true);
                    if (circuit)
                    {
                        circuit.practicalLights = circuit.practicalLights.Where(l => l && !old.Contains(l)).ToArray();
                        circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !old.Contains(l)).ToArray();
                    }
                    UnityEngine.Object.DestroyImmediate(existing);
                }
                foreach (var p in sp["retire"] ?? new JArray())
                {
                    var t = FindPath(scene, (string)p);
                    if (!t) throw new Exception("retire path not found: " + p);
                    if (!t.gameObject.activeSelf) { log.Add("already inactive: " + p); continue; }
                    t.gameObject.SetActive(false);
                    if (PrefabUtility.IsPartOfPrefabInstance(t.gameObject)) PrefabUtility.RecordPrefabInstancePropertyModifications(t.gameObject);
                    log.Add("retired: " + p);
                }
                var root = new GameObject(rootName);
                UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
                Transform kit = null, decals = null;
                var lamps = new List<Light>();
                int placed = 0;
                foreach (var inst in sp["instances"])
                {
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>((string)inst["prefab"]);
                    if (!prefab) throw new Exception("Prefab missing (build first): " + inst["prefab"]);
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                    Transform parent = root.transform;
                    if ((string)inst["kind"] == "kit")
                    {
                        if (!kit) { kit = new GameObject("Street dressing kit").transform; kit.SetParent(root.transform, false); }
                        parent = kit;
                    }
                    go.transform.SetParent(parent, false);
                    go.transform.SetPositionAndRotation(V3(inst["pos"]), Quaternion.Euler(0, (float)inst["yaw"], 0));
                    go.name = (string)inst["name"];
                    var pl = go.transform.Find("Practical lights");
                    if (pl) lamps.AddRange(pl.GetComponentsInChildren<Light>(true));
                    placed++;
                }
                int nd = 0;
                foreach (var d in sp["decals"] ?? new JArray())
                {
                    var mat = DecalMat((string)d["mat"]);
                    if (!mat) { log.Add("decal material missing: " + d["mat"]); continue; }
                    if (!decals) { decals = new GameObject("Decals").transform; decals.SetParent(root.transform, false); }
                    var go = new GameObject("Decal · " + (string)d["name"]); go.transform.SetParent(decals, false);
                    var pos = V3(d["pos"]);
                    var fwd = Quaternion.Euler(0, (float)d["yaw"], 0) * Vector3.forward;
                    go.transform.SetPositionAndRotation(pos + Vector3.up * .25f, Quaternion.LookRotation(Vector3.down, fwd));
                    var proj = go.AddComponent<DecalProjector>();
                    proj.material = mat;
                    var size = d["size"];
                    // projector x = the decal's width (texture u), y = its length along `fwd` (texture v)
                    proj.size = new Vector3((float)size[0], (float)size[1], .5f);
                    proj.pivot = new Vector3(0, 0, .25f);
                    var uv = d["uv"];
                    if (uv != null && uv.Type == JTokenType.Array) { proj.uvScale = new Vector2((float)uv[0], (float)uv[1]); proj.uvBias = new Vector2((float)uv[2], (float)uv[3]); }
                    proj.fadeFactor = (float)d["opacity"]; proj.drawDistance = 35; proj.fadeScale = .75f;
                    proj.startAngleFade = 60; proj.endAngleFade = 85;
                    nd++;
                }
                if (circuit && lamps.Count > 0)
                {
                    circuit.practicalLights = circuit.practicalLights.Where(l => l).Concat(lamps).Distinct().ToArray();
                    circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l).Concat(lamps).Distinct().ToArray();
                    EditorUtility.SetDirty(circuit);
                }
                record[rootName] = new { placed, decals = nd, lights = lamps.Select(l => PathOf(l.transform)).ToArray() };
            }
            AddCameras(scene, layout);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            record["log"] = log;
            record["lightCircuitFound"] = circuit != null;
            if (chunks) record["chunkFingerprintUnchanged"] = chunks.sourceFingerprint == fpBefore && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + (replace ? "reinstall.json" : "install.json"), json);
            return json;
        }

        static void AddCameras(UnityEngine.SceneManagement.Scene scene, JObject layout)
        {
            var camRoot = (string)layout["cameraRoot"];
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == camRoot);
            if (!root) { root = new GameObject(camRoot); UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene); }
            foreach (var c in layout["cameras"])
            {
                var name = (string)c["name"];
                var t = root.transform.Find(name);
                if (!t) { t = new GameObject(name).transform; t.SetParent(root.transform, false); }
                var pos = V3(c["pos"]);
                t.SetPositionAndRotation(pos, Quaternion.LookRotation(V3(c["target"]) - pos, Vector3.up));
                var cam = t.GetComponent<Camera>();
                if (!cam) cam = t.gameObject.AddComponent<Camera>();
                cam.enabled = false; cam.fieldOfView = (float)c["fov"]; cam.nearClipPlane = .05f;
            }
        }

        public static string Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var log = new List<string>();
            foreach (JObject sp in layout["spots"])
            {
                var r = scene.GetRootGameObjects().FirstOrDefault(g => g.name == (string)sp["root"]);
                if (r) { r.SetActive(false); log.Add("deactivated " + r.name); }
                foreach (var p in sp["retire"] ?? new JArray())
                {
                    var t = FindPath(scene, (string)p);
                    if (t) { t.gameObject.SetActive(true); log.Add("re-activated " + p); }
                }
            }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return string.Join("\n", log);
        }

        // ------------------------------------------------------------------ verify
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var all = new Dictionary<string, object>();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            var markers = new List<(string, Vector3)>();
            foreach (var g in scene.GetRootGameObjects())
            {
                bool route = g.name.EndsWith(" route") || g.name == "Landmarks" || g.name == "Colonists";
                if (route) foreach (Transform c in g.transform) markers.Add((g.name + "/" + c.name, c.position));
                if (g.name == "Player" || g.name.EndsWith(" interaction") || g.name.StartsWith("npc_")) markers.Add((g.name, g.transform.position));
            }
            var mineRoots = layout["spots"].Select(s => (string)s["root"]).ToArray();
            var retiredRoots = layout["spots"].SelectMany(s => s["retire"] ?? new JArray()).Select(x => ((string)x).Split('/')[0]).ToArray();
            foreach (JObject sp in layout["spots"])
            {
                var r = new Dictionary<string, object>();
                var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == (string)sp["root"]);
                r["installed"] = root != null;
                if (root)
                {
                    r["active"] = root.activeSelf;
                    var insts = root.GetComponentsInChildren<Transform>(true).Where(t => PrefabUtility.IsAnyPrefabInstanceRoot(t.gameObject)).ToArray();
                    r["instances"] = insts.Length;
                    r["expectedInstances"] = sp["instances"].Count();
                    r["missingPrefabs"] = root.GetComponentsInChildren<Transform>(true).Count(t => PrefabUtility.IsPrefabAssetMissing(t.gameObject));
                    var rends = root.GetComponentsInChildren<Renderer>(true);
                    r["renderers"] = rends.Length;
                    r["missingMaterials"] = rends.Where(x => x.sharedMaterials.Any(m => !m)).Select(x => PathOf(x.transform)).Take(20).ToArray();
                    var projs = root.GetComponentsInChildren<DecalProjector>(true);
                    r["decals"] = projs.Length;
                    r["decalsWithoutMaterial"] = projs.Count(p => !p.material);
                    var groups = root.GetComponentsInChildren<LODGroup>(true).Where(g => g.transform.parent == root.transform).ToArray();
                    r["modelTriangles"] = groups.GroupBy(gg => { var src = PrefabUtility.GetCorrespondingObjectFromSource(gg.gameObject); return src ? src.name : gg.name; })
                        .ToDictionary(grp => grp.Key + " ×" + grp.Count(), grp => grp.First().GetLODs().Select(l => l.renderers.Where(x => x).Sum(Tris)).ToArray());
                    var lamps = root.GetComponentsInChildren<Light>(true);
                    r["lights"] = lamps.Length;
                    r["lightsOnCircuit"] = circuit ? lamps.Count(l => circuit.practicalLights.Contains(l) && circuit.nightOnlyLights.Contains(l)) : -1;
                    var cols = root.GetComponentsInChildren<Collider>(true).Where(c => c.enabled && c.gameObject.activeInHierarchy).ToArray();
                    r["colliders"] = cols.Length;
                    var hits = new List<object>();
                    foreach (var (name, p) in markers)
                        foreach (var c in cols)
                        {
                            var q = new Vector3(p.x, c.bounds.center.y, p.z);
                            var d = Vector3.Distance(q, c.bounds.ClosestPoint(q));
                            if (d < .45f && p.y < c.bounds.max.y + .5f) hits.Add(new { marker = name, collider = PathOf(c.transform), dist = Math.Round(d, 2) });
                        }
                    r["markerConflicts"] = hits;
                    var segHits = new List<object>();
                    foreach (var g in scene.GetRootGameObjects().Where(g => g.name.EndsWith(" route")))
                    {
                        var wps = g.transform.Cast<Transform>().Select(t => t.position).ToList();
                        for (int i = 0; i < wps.Count && wps.Count > 1; i++)
                        {
                            var a = wps[i]; var b2 = wps[(i + 1) % wps.Count];
                            int n = Mathf.Max(1, Mathf.CeilToInt(Vector3.Distance(a, b2) / 0.4f));
                            for (int k = 0; k <= n; k++)
                            {
                                var p = Vector3.Lerp(a, b2, k / (float)n);
                                foreach (var c in cols)
                                {
                                    if (c.bounds.min.y > 1.9f) continue;
                                    var q = new Vector3(p.x, c.bounds.center.y, p.z);
                                    if (Vector3.Distance(q, c.bounds.ClosestPoint(q)) < .45f) { segHits.Add(new { route = g.name, seg = i, collider = c.name }); break; }
                                }
                            }
                        }
                    }
                    r["routeSegmentConflicts"] = segHits.Distinct().Take(40).ToArray();
                    var mine = new HashSet<Collider>(scene.GetRootGameObjects().Where(g => mineRoots.Contains(g.name)).SelectMany(g => g.GetComponentsInChildren<Collider>(true)));
                    var others = scene.GetRootGameObjects().Where(g => !retiredRoots.Contains(g.name)).SelectMany(g => g.GetComponentsInChildren<Collider>(false))
                        .Where(c => c.enabled && !mine.Contains(c) && !c.isTrigger && c.gameObject.name != "COL_Ground" && !(c is TerrainCollider) && c.bounds.size.x < 60 && c.bounds.size.z < 60).ToArray();
                    var overl = new List<object>();
                    foreach (var c in cols)
                    {
                        var b0 = c.bounds; b0.Expand(-0.1f);
                        foreach (var o in others)
                            if (b0.Intersects(o.bounds)) overl.Add(new { mine = PathOf(c.transform), other = PathOf(o.transform) });
                    }
                    r["colliderOverlaps"] = overl;
                }
                var retired = new List<object>();
                foreach (var p in sp["retire"] ?? new JArray())
                {
                    var t = FindPath(scene, (string)p);
                    retired.Add(new { path = (string)p, found = t != null, activeInHierarchy = t && t.gameObject.activeInHierarchy });
                }
                r["retired"] = retired;
                all[(string)sp["root"]] = r;
            }
            var camRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == (string)layout["cameraRoot"]);
            all["reviewCameras"] = camRoot ? camRoot.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray() : new string[0];
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { all["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); all["chunkEditing"] = chunks.editingSources; }
            var missingScripts = scene.GetRootGameObjects().Where(g => mineRoots.Contains(g.name))
                .SelectMany(g => g.GetComponentsInChildren<Transform>(true)).Sum(t => GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject));
            all["missingScripts"] = missingScripts;
            var json = JsonConvert.SerializeObject(all, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        // ------------------------------------------------------------------ view budget (planning estimate, never saves)
        public static string Budget()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var lights = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).Where(l => l.enabled && l.type != LightType.Directional).ToArray();
            var mineRoots = layout["spots"].Select(s => (string)s["root"]).ToArray();
            var ours = scene.GetRootGameObjects().Where(g => mineRoots.Contains(g.name) && g.activeInHierarchy).SelectMany(g => g.GetComponentsInChildren<LODGroup>(false)).ToArray();
            var views = layout["cameras"].Select(c => ((string)c["name"], V3(c["pos"]), Quaternion.LookRotation(V3(c["target"]) - V3(c["pos"]), Vector3.up), (float)c["fov"])).ToList();
            foreach (var sc in UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (new[] { "cam_hill", "cam_avenue", "cam_gate", "cam_grid", "cam_whompah", "cam_ring_front", "cam_ss_lattice_approach", "cam_wb2_gate_spawn", "cam_wb2_gate_apron" }.Contains(sc.name))
                    views.Add((sc.name, sc.transform.position, sc.transform.rotation, sc.fieldOfView));
            var res = new Dictionary<string, object>();
            foreach (var (name, pos, rot, fov) in views)
            {
                var go = new GameObject("tmp cam"); var cam = go.AddComponent<Camera>();
                go.transform.SetPositionAndRotation(pos, rot);
                cam.fieldOfView = fov; cam.aspect = 16f / 9f; cam.nearClipPlane = .05f; cam.farClipPlane = 1600f;
                var planes = GeometryUtility.CalculateFrustumPlanes(cam);
                var lit = lights.Where(l => GeometryUtility.TestPlanesAABB(planes, new Bounds(l.transform.position, Vector3.one * 2f * l.range))).ToArray();
                int tris = 0, casters = 0;
                foreach (var g in ours)
                {
                    var lods = g.GetLODs();
                    var wc = g.transform.TransformPoint(g.localReferencePoint);
                    float dist = Mathf.Max(.01f, Vector3.Distance(pos, wc));
                    float h = g.size / (2f * dist * Mathf.Tan(cam.fieldOfView * .5f * Mathf.Deg2Rad)) * LodBias;
                    int sel = -1;
                    for (int i = 0; i < lods.Length; i++) if (h >= lods[i].screenRelativeTransitionHeight) { sel = i; break; }
                    if (sel < 0) continue;
                    foreach (var r in lods[sel].renderers)
                        if (r && r.gameObject.activeInHierarchy && GeometryUtility.TestPlanesAABB(planes, r.bounds)) { tris += Tris(r); if (r.shadowCastingMode != ShadowCastingMode.Off) casters++; }
                }
                res[name] = new { localLightsInView = lit.Length, ofThisPass = lit.Count(l => mineRoots.Any(m => PathOf(l.transform).StartsWith(m))), passTrianglesAtSelectedLod = tris, passShadowCasters = casters };
                UnityEngine.Object.DestroyImmediate(go);
            }
            var json = JsonConvert.SerializeObject(res, Formatting.Indented);
            File.WriteAllText(Evidence + "view-budget.json", json);
            return json;
        }

        // ------------------------------------------------------------------ captures (never saves)
        public static string Capture(string outDir, string filter)
        {
            EditorSceneManager.OpenScene(ScenePath);
            var views = Layout()["cameras"].Where(c => string.IsNullOrEmpty(filter) || filter.Split('+').Any(f => ((string)c["name"]).StartsWith(f)))
                .Select(c => ((string)c["name"], V3(c["pos"]), V3(c["target"]), (float)c["fov"])).Take(6).ToList();
            return string.Join(",", StreetDressingPass.Capture(outDir, views));
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.WardLifePass.RunBatch --steps build,install,verify [--out dir]
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
                    var p = st.Split(':');
                    string a1 = p.Length > 1 ? p[1] : "";
                    string result = p[0] switch
                    {
                        "survey" => Survey(string.IsNullOrEmpty(a1) ? Evidence + "survey" : a1),
                        "build" => Build(a1),
                        "install" => Install(false),
                        "reinstall" => Install(true),
                        "verify" => Verify(),
                        "budget" => Budget(),
                        "capture" => Capture(outDir, a1),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("WardLifePass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
