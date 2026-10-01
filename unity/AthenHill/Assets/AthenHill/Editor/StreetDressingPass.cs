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
    /// 30 September 2026: Ward street dressing. Carl: "A lot of the street trash and props looks very low quality can we
    /// rebuild them in blender and or meshy? I want the area to have a lived in look but not be too messy. I dont want a
    /// clean clinical ward. eventually we will introduce more NPC to make it look busy".
    ///
    /// Replaces the 8 Sep salvage scatter (58 copies of one 432-triangle trash mound, 21 crates, 10 scrap stacks, six
    /// generators) and the primitive-cube street dressing with a kit of individual props arranged as purposeful
    /// vignettes (stock by shop doors, refuse points with tied sacks, rest spots, water points, planters, a workshop yard
    /// and a scrap skip) along walls and in yards, with the avenue, stairs, doors and walker routes kept clear.
    ///
    /// Sources (art/street_dressing_20260930): prepare_ph_props.py (CC0 Poly Haven scans), prepare_meshy_props.py
    /// (meshy/street-dressing-20260930), author_street_props.py (Blender), prepare_textures.py (maps, materials.json),
    /// layout.py (layout.json). Menu: Athen Hill → Street dressing → Build assets, Audition kit (editor capture, not saved),
    /// Install (one time), Verify saved scene. Old props stay in the scene inactive; render chunks are rebuilt.
    /// </summary>
    public static class StreetDressingPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/StreetDressing/";
        const string PropDir = Root + "Props/";
        const string TexDir = Root + "Textures/";
        const string MatDir = Root + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/StreetDressing/";
        const string HillMats = "Assets/AthenHill/Art/WardHill/Materials/";
        const string Evidence = "../evidence/street-dressing/20260930/";
        const string LayoutPath = "../../art/street_dressing_20260930/layout.json";
        public const string RootName = "Ward street dressing";

        // ------------------------------------------------------------------ kit records
        public sealed class PropSpec
        {
            public string id, kind, notes;
            public float[] size;
            public int[] lods;
            public string[] materials;
            public bool collider = true;
            public float Max => size.Max();
            public bool Litter => kind == "authored" && size[1] < 0.13f && Max < 0.8f;
        }

        public static Dictionary<string, PropSpec> Specs()
        {
            var specs = new Dictionary<string, PropSpec>();
            void Read(string file, string kind)
            {
                if (!File.Exists(PropDir + file)) return;
                foreach (var p in JObject.Parse(File.ReadAllText(PropDir + file)).Properties())
                {
                    var o = (JObject)p.Value;
                    specs[p.Name] = new PropSpec
                    {
                        id = p.Name, kind = kind, notes = (string)o["notes"] ?? "",
                        size = o["size"].Select(x => (float)x).ToArray(),
                        lods = o["lods"].Select(x => (int)x).ToArray(),
                        materials = ((JObject)o["materials"]).Properties().Select(x => x.Name).ToArray(),
                        collider = o["collider"] == null || (bool)o["collider"],
                    };
                }
            }
            Read("ph-props.json", "polyhaven");
            Read("meshy-props.json", "meshy");
            Read("authored-props.json", "authored");
            return specs;
        }

        // ------------------------------------------------------------------ build
        [MenuItem("Athen Hill/Street dressing/Build assets")]
        public static string BuildAssets()
        {
            var specs = Specs();
            AssetDatabase.Refresh();
            ConfigureTextures(specs);
            foreach (var s in specs.Values)
                for (int i = 0; i < s.lods.Length; i++)
                    AssetDatabase.ImportAsset(PropDir + s.id + "/" + s.id + "_LOD" + i + ".glb", ImportAssetOptions.ForceUpdate);
            var mats = BuildMaterials();
            Directory.CreateDirectory(PrefabDir);
            var missing = new HashSet<string>();
            foreach (var s in specs.Values) BuildPrefab(s, mats, missing);
            AssetDatabase.SaveAssets();
            var report = new { props = specs.Count, materials = mats.Count, unmapped = missing.OrderBy(x => x).ToArray() };
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(report, Formatting.Indented);
            File.WriteAllText(Evidence + "build-assets.json", json);
            return json;
        }

        static void ConfigureTextures(Dictionary<string, PropSpec> specs)
        {
            // texture folder (Poly Haven model or prop id) -> the largest prop using it, for the import size
            var ph = JObject.Parse(File.ReadAllText(PropDir + "ph-props.json"));
            var modelSize = new Dictionary<string, float>();
            foreach (var p in ph.Properties())
            {
                var model = (string)p.Value["source"]; var max = p.Value["size"].Max(x => (float)x);
                modelSize[model] = Math.Max(modelSize.TryGetValue(model, out var m) ? m : 0, max);
            }
            foreach (var g in AssetDatabase.FindAssets("t:Texture", new[] { TexDir.TrimEnd('/'), PropDir.TrimEnd('/') }))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                var file = Path.GetFileNameWithoutExtension(path);
                var folder = Path.GetFileName(Path.GetDirectoryName(path));
                bool normal = file.Contains("nor_gl") || file.EndsWith("_Normal");
                bool mask = file.EndsWith("_Mask");
                bool alpha = file.EndsWith("_alpha");
                float size = modelSize.TryGetValue(folder, out var ms) ? ms : specs.TryGetValue(folder, out var sp) ? sp.Max : 1f;
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !normal && !mask;
                ti.alphaSource = mask || alpha ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                ti.alphaIsTransparency = alpha;
                ti.mipMapsPreserveCoverage = alpha;
                if (alpha) ti.alphaTestReferenceValue = .45f;
                // texel density from the closest view: small hand-sized props do not need 2k in the build
                ti.maxTextureSize = folder == "Authored" ? 1024 : size < 0.5f ? 1024 : 2048;
                ti.mipmapEnabled = true;
                ti.streamingMipmaps = true;
                ti.anisoLevel = 8;
                ti.wrapMode = TextureWrapMode.Repeat;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
            }
        }

        static Material Mat(Dictionary<string, Material> mats, string key, string assetName, Shader shader)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + assetName + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader) { name = assetName }; AssetDatabase.CreateAsset(m, path); }
            else if (m.shader != shader) m.shader = shader;
            mats[key] = m;
            return m;
        }

        static Texture2D T(string path) => string.IsNullOrEmpty(path) ? null : AssetDatabase.LoadAssetAtPath<Texture2D>(path);

        static Dictionary<string, Material> BuildMaterials()
        {
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var mats = new Dictionary<string, Material>();
            var specs = JObject.Parse(File.ReadAllText(TexDir + "materials.json"));
            foreach (var p in specs.Properties())
            {
                var s = (JObject)p.Value;
                if (s["shared"] != null) continue;
                var assetName = p.Name.StartsWith("SD_") ? p.Name : "SD_" + p.Name.Replace(".", "_");
                var m = Mat(mats, p.Name, assetName, lit);
                m.SetTexture("_BaseMap", T((string)s["base"]));
                var tint = s["tint"];
                m.SetColor("_BaseColor", tint != null ? new Color((float)tint[0], (float)tint[1], (float)tint[2]) : Color.white);
                var normal = T((string)s["normal"]);
                m.SetTexture("_BumpMap", normal); m.SetFloat("_BumpScale", 1f);
                if (normal) m.EnableKeyword("_NORMALMAP"); else m.DisableKeyword("_NORMALMAP");
                var mask = T((string)s["mask"]);
                if (mask)
                {
                    m.SetTexture("_MetallicGlossMap", mask); m.EnableKeyword("_METALLICSPECGLOSSMAP");
                    m.SetTexture("_OcclusionMap", mask); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1f);
                    // mask A is 1 - roughness; the slider scales it (scans read true at ~0.9, Meshy maps run glossy)
                    m.SetFloat("_Smoothness", (string)s["kind"] == "meshy" ? .8f : .9f);
                }
                else
                {
                    m.SetTexture("_MetallicGlossMap", null); m.DisableKeyword("_METALLICSPECGLOSSMAP");
                    m.SetFloat("_Metallic", s["metallic"] != null ? (float)s["metallic"] : 0f);
                    m.SetFloat("_Smoothness", s["smoothness"] != null ? Mathf.Clamp01((float)s["smoothness"]) : .3f);
                }
                m.SetFloat("_SmoothnessTextureChannel", 0);
                // tiling textures: metres per repeat from the authored UVs (already in metres / tile)
                m.SetTextureScale("_BaseMap", Vector2.one);
                bool two = s["doubleSided"] != null && (bool)s["doubleSided"];
                if (s["alphaClip"] != null && (bool)s["alphaClip"])
                {
                    m.SetFloat("_AlphaClip", 1); m.SetFloat("_Cutoff", s["cutoff"] != null ? (float)s["cutoff"] : .45f); m.EnableKeyword("_ALPHATEST_ON");
                    m.SetOverrideTag("RenderType", "TransparentCutout"); m.renderQueue = (int)RenderQueue.AlphaTest;
                    two = true;
                }
                m.SetFloat("_Cull", two ? 0 : 2); m.doubleSidedGI = two;
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
            }
            // shared hill materials: soil as is; potted plants get copies whose wind bend starts higher (their prefab
            // origin is the pot base, not the soil, and the ground-cover wind bends by height above the origin)
            mats["WH_BedSoil"] = AssetDatabase.LoadAssetAtPath<Material>(HillMats + "WH_BedSoil.mat");
            foreach (var n in new[] { "grass_medium_01", "grass_medium_02", "cheiridopsis_succulent", "cheiridopsis_succulent_flower",
                                      "crystalline_iceplant", "celandine_01", "weed_plant_02" })
            {
                var src = AssetDatabase.LoadAssetAtPath<Material>(HillMats + n + ".mat");
                if (!src) throw new Exception("Hill plant material missing: " + n);
                var m = Mat(mats, n, "SD_Potted_" + n, src.shader);
                m.CopyPropertiesFromMaterial(src);
                if (m.HasProperty("_WardBendHeight")) m.SetFloat("_WardBendHeight", src.GetFloat("_WardBendHeight") + .45f);
                EditorUtility.SetDirty(m);
            }
            AssetDatabase.SaveAssets();
            return mats;
        }

        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m) && m) return m;
            var trimmed = System.Text.RegularExpressions.Regex.Replace(name, @"\.\d+$", "");
            if (mats.TryGetValue(trimmed, out m) && m) return m;
            return mats.TryGetValue("SD_" + trimmed, out m) ? m : null;
        }

        static List<Renderer> Instance(string glb, Transform parent, string name, Dictionary<string, Material> mats, HashSet<string> missing)
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

        /// LOD switch heights by size (relative to the LODGroup's largest dimension; the PC preset's LOD bias is 2).
        static float[] Cuts(PropSpec s, int levels)
        {
            // tuned on the native A/B (evidence/street-dressing/20260930): earlier switches and culls cost nothing visible
            float[] c = s.Litter ? new[] { .08f, .025f } : s.Max < .5f ? new[] { .22f, .07f, .025f } : s.Max < 1.2f ? new[] { .3f, .08f, .02f } : new[] { .4f, .1f, .015f };
            return c.Take(levels).ToArray();
        }

        static readonly Dictionary<string, float> SeatHeights = new()
        {
            ["stool_folding"] = .44f, ["stool_wood"] = .44f, ["stool_painted"] = .58f, ["stool_metal"] = .46f, ["stool_low"] = .18f, ["bench_painted"] = .45f,
        };

        public static string PrefabPath(string id) => PrefabDir + "SD_" + id + ".prefab";

        static void BuildPrefab(PropSpec s, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var root = new GameObject("SD_" + s.id);
            try
            {
                var cuts = Cuts(s, s.lods.Length);
                var levels = new List<LOD>();
                for (int lod = 0; lod < cuts.Length; lod++)
                {
                    var rs = Instance(PropDir + s.id + "/" + s.id + "_LOD" + lod + ".glb", root.transform, "LOD" + lod, mats, missing);
                    // shadows: litter never; LOD0 always; LOD1 only for the big pieces whose shadow would visibly pop
                    bool cast = !s.Litter && (lod == 0 || (lod == 1 && s.Max >= 1.2f));
                    foreach (var r in rs) r.shadowCastingMode = cast ? ShadowCastingMode.On : ShadowCastingMode.Off;
                    levels.Add(new LOD(cuts[lod], rs.ToArray()));
                }
                var g = root.AddComponent<LODGroup>(); g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                // simple box collision for anything the player could walk into; litter and hand-sized things have none
                if (s.collider && !s.Litter && s.Max >= .3f && s.size[1] >= .15f)
                {
                    var b = root.AddComponent<BoxCollider>();
                    b.center = new Vector3(0, s.size[1] / 2, 0);
                    b.size = new Vector3(s.size[0] * .92f, s.size[1], s.size[2] * .92f);
                }
                // seats: markers for the future NPC pass (sit here, facing +Z)
                if (SeatHeights.TryGetValue(s.id, out var seat))
                {
                    var pts = s.id == "bench_painted" ? new[] { -.3f, .3f } : new[] { 0f };
                    foreach (var x in pts)
                    {
                        var sp = new GameObject("NPC sit point"); sp.transform.SetParent(root.transform, false);
                        sp.transform.localPosition = new Vector3(x, seat, s.id == "bench_painted" ? .05f : 0f);
                    }
                }
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(s.id));
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        // ------------------------------------------------------------------ audition (editor capture, scene not saved)
        /// Lays every prefab out in rows on open paving east of the hill and renders player-height views through a clone
        /// of MainCamera (post-processing on). Nothing is saved.
        public static string Audition(string outDir, string filter = "")
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var specs = Specs().Values.Where(s => filter == "" || filter.Split(',').Any(f => s.id.StartsWith(f))).OrderBy(s => s.id).ToList();
            var root = new GameObject("__audition");
            float x0 = 25f, z0 = -3.5f; int cols = 8; float dx = 1.8f, dz = 2.2f;
            for (int i = 0; i < specs.Count; i++)
            {
                var p = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(specs[i].id)), scene);
                p.transform.SetParent(root.transform, true);
                p.transform.position = new Vector3(x0 + (i % cols) * dx, 0f, z0 + (i / cols) * dz);
                p.transform.rotation = Quaternion.Euler(0, 200f, 0);   // front towards the cameras (south-west)
            }
            var views = new List<(string name, Vector3 pos, Vector3 target, float fov)>();
            int rows = (specs.Count + cols - 1) / cols;
            for (int r = 0; r < rows; r++)
                views.Add(($"row{r}", new Vector3(x0 + cols * dx / 2 - 1.6f, 1.62f, z0 + r * dz - 3.4f), new Vector3(x0 + cols * dx / 2 - 1.2f, .4f, z0 + r * dz), 62f));
            views.Add(("overview", new Vector3(x0 - 4f, 5.5f, z0 - 7f), new Vector3(x0 + 6f, 0f, z0 + rows * dz / 2), 55f));
            var shots = Capture(outDir, views);
            UnityEngine.Object.DestroyImmediate(root);
            return string.Join("\n", shots);
        }

        /// One prop at a time on open paving: a front-left and a back-right view at a distance fitted to its size.
        public static string AuditionSolo(string outDir, string filter, Vector3? at = null)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var specs = Specs().Values.Where(s => filter.Split(',').Any(f => s.id.StartsWith(f))).OrderBy(s => s.id).ToList();
            var spot = at ?? new Vector3(30f, 0f, 1.2f);
            var done = new List<string>();
            foreach (var s in specs)
            {
                var p = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(s.id)), scene);
                p.transform.SetPositionAndRotation(spot, Quaternion.Euler(0, 180f, 0));     // front faces -Z, towards the cameras
                var c = spot + Vector3.up * s.size[1] * .45f;
                float d = Mathf.Max(1.1f, s.Max * 1.9f);
                float h = Mathf.Clamp(s.size[1] + .6f, .8f, 1.62f);
                var views = new List<(string, Vector3, Vector3, float)>
                {
                    (s.id + "_front", spot + new Vector3(-.55f * d, h, -.85f * d), c, 50f),
                    (s.id + "_back", spot + new Vector3(.6f * d, h, .8f * d), c, 50f),
                };
                done.AddRange(Capture(outDir, views));
                UnityEngine.Object.DestroyImmediate(p);
            }
            return string.Join(",", done);
        }

        public static List<string> Capture(string outDir, List<(string name, Vector3 pos, Vector3 target, float fov)> views)
        {
            var main = GameObject.Find("MainCamera").GetComponent<Camera>();
            var go = new GameObject("__cap") { hideFlags = HideFlags.DontSave };
            var cam = go.AddComponent<Camera>(); cam.CopyFrom(main);
            var src = main.GetComponent<UniversalAdditionalCameraData>(); var dst = go.AddComponent<UniversalAdditionalCameraData>();
            if (src) { dst.renderPostProcessing = src.renderPostProcessing; dst.antialiasing = src.antialiasing; dst.antialiasingQuality = src.antialiasingQuality; dst.renderShadows = true; dst.requiresDepthTexture = src.requiresDepthTexture; }
            cam.enabled = false; cam.nearClipPlane = .05f; cam.farClipPlane = 650;
            var rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
            var tex = new Texture2D(1920, 1080, TextureFormat.RGB24, false);
            Directory.CreateDirectory(outDir);
            var done = new List<string>();
            foreach (var (name, pos, target, fov) in views)
            {
                go.transform.position = pos; go.transform.LookAt(target); cam.fieldOfView = fov;
                cam.targetTexture = rt;
                for (int k = 0; k < 3; k++) cam.Render();       // settle temporal effects / probe updates
                RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1920, 1080), 0, 0); tex.Apply();
                File.WriteAllBytes(Path.Combine(outDir, name + ".png"), tex.EncodeToPNG());
                done.Add(name);
            }
            RenderTexture.active = null; cam.targetTexture = null;
            UnityEngine.Object.DestroyImmediate(go); rt.Release();
            return done;
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.StreetDressingPass.RunBatch --steps build,audition[:filter] [--out dir]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "build").Split(',');
            var outDir = Arg("--out", Evidence + "audition");
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "build" => BuildAssets(),
                        "audition" => Audition(outDir, parts.Length > 1 ? parts[1].Replace('+', ',') : ""),
                        "solo" => AuditionSolo(outDir, parts[1].Replace('+', ','), parts.Length > 2 ? ParseV3(parts[2]) : null),
                        "install" => Install(),
                        "reinstall" => StreetDressingInstall.Reinstall(),
                        "toggle" => Toggle(parts[1] == "on"),
                        "capture" => StreetDressingInstall.CaptureViews(outDir),
                        "verify" => Verify(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("StreetDressingPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        /// Measurement only (A/B frame time): switches the whole dressing root off or on in the saved scene.
        static string Toggle(bool on)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            root.SetActive(on);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return RootName + (on ? " on" : " off");
        }

        static Vector3? ParseV3(string s) { var v = s.Split('/').Select(float.Parse).ToArray(); return new Vector3(v[0], v[1], v[2]); }

        // install / verify are defined with the layout (StreetDressingInstall.cs)
        public static string Install() => StreetDressingInstall.Install();
        public static string Verify() => StreetDressingInstall.Verify();
    }
}
