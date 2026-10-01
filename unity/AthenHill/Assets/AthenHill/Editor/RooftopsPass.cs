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
    /// 1 October 2026: Ward rooftops and service cables (art-direction review item 8: "From the street every roofline is an
    /// unbroken cornice against the sky ... At 1.6 m eye height, the skyline is what the player sees above every shop. It is
    /// also where Ward's survival story (water, power, air) can be told cheaply.").
    ///
    /// A kit of single roof objects (water tanks, a dew/condensate net, PV panels, cowls and turbine vents, a whip antenna and
    /// a dish, service-line masts, guard rails, a shade frame, caged ladders, wall hooks and junction boxes) placed one or
    /// two per building where the avenue sees them, plus service lines between masts across the two cross streets, short
    /// lines across the alleys and conduit drops down the side walls. Everything sits under one scene root, "Ward rooftops",
    /// in world space: one child per shop roof whose transform equals that shop's root (so its children use the shop's own
    /// frame), and "Service lines" for the spans and drops. The shops' meshes, the night-life emitters and other passes'
    /// roots are not touched; nothing is retired and no render-chunk source changes.
    ///
    /// Sources (art/rooftops_20261001): author_roof_kit.py and author_cables.py (Blender), make_textures.py, layout.py
    /// (layout.json + validation), review_cams.py (review-cameras.json). Menu: Athen Hill → Rooftops → Build assets,
    /// Install (one time), Verify saved scene, Add review cameras; batch RunBatch --steps build,install,verify,capture.
    /// </summary>
    public static class RooftopsPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/Rooftops/";
        const string ModelDir = Root + "Models/";
        const string TexDir = Root + "Textures/";
        const string MatDir = Root + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/Rooftops/";
        const string Evidence = "../evidence/rooftops/20261001/";
        const string ArtDir = "../../art/rooftops_20261001/";
        public const string RootName = "Ward rooftops";
        const string LinesName = "Service lines";
        const string CamRootName = "Rooftops review cameras";
        static readonly string[] SharedMaterialDirs =
        {
            "Assets/AthenHill/Art/VanguardHall/Materials", "Assets/AthenHill/Art/WardShops/Materials",
            "Assets/AthenHill/Art/StreetDressing/Materials", "Assets/AthenHill/Art/Rooftops/Materials",
        };

        static JObject Kit() => JObject.Parse(File.ReadAllText(ModelDir + "kit.json"));
        static JObject Lines() => JObject.Parse(File.ReadAllText(ModelDir + "lines.json"));
        static JObject Layout() => JObject.Parse(File.ReadAllText(ArtDir + "layout.json"));
        static JObject Cams() => JObject.Parse(File.ReadAllText(ArtDir + "review-cameras.json"));
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        public static string PrefabPath(string id) => PrefabDir + "RT_" + id + ".prefab";
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        // ------------------------------------------------------------------ build
        [MenuItem("Athen Hill/Rooftops/Build assets")]
        public static string BuildAssets()
        {
            AssetDatabase.Refresh();
            ConfigureTextures();
            var mats = BuildMaterials();
            var kit = Kit();
            var lines = Lines();
            foreach (var p in kit.Properties())
                for (int lod = 0; lod < 2; lod++) AssetDatabase.ImportAsset(ModelDir + $"RT_{p.Name}_LOD{lod}.glb", ImportAssetOptions.ForceUpdate);
            foreach (var p in lines.Properties())
                for (int lod = 0; lod < 2; lod++) AssetDatabase.ImportAsset(ModelDir + $"RT_{p.Name}_LOD{lod}.glb", ImportAssetOptions.ForceUpdate);
            Directory.CreateDirectory(PrefabDir);
            var missing = new HashSet<string>();
            var report = new Dictionary<string, object>();
            foreach (var p in kit.Properties()) report[p.Name] = BuildPrefab(p.Name, (JObject)p.Value, mats, missing, false);
            foreach (var p in lines.Properties()) report[p.Name] = BuildPrefab(p.Name, (JObject)p.Value, mats, missing, true);
            AssetDatabase.SaveAssets();
            var json = JsonConvert.SerializeObject(new { prefabs = report, unmappedMaterials = missing.OrderBy(x => x).ToArray() }, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "build-assets.json", json);
            return json;
        }

        static void ConfigureTextures()
        {
            foreach (var g in AssetDatabase.FindAssets("t:Texture", new[] { TexDir.TrimEnd('/') }))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                bool net = path.Contains("DewNet");
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = true;
                ti.alphaSource = net ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                ti.alphaIsTransparency = net;
                ti.mipMapsPreserveCoverage = net;
                if (net) ti.alphaTestReferenceValue = .5f;
                ti.mipmapEnabled = true;
                ti.streamingMipmaps = true;
                ti.anisoLevel = 8;
                ti.wrapMode = TextureWrapMode.Repeat;
                ti.maxTextureSize = 512;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
            }
        }

        static Material NewOrLoad(string name, Shader shader)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
            else if (m.shader != shader) m.shader = shader;
            return m;
        }

        /// The four new materials (existing ones keep Inspector edits except the values set here) + every shared material.
        static Dictionary<string, Material> BuildMaterials()
        {
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var net = NewOrLoad("RT_DewNet", lit);
            net.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + "RT_DewNet_Base.png"));
            net.SetTextureScale("_BaseMap", new Vector2(4f, 4f));               // one tile = 0.25 m of net
            net.SetColor("_BaseColor", new Color(.92f, .92f, .9f));
            net.SetFloat("_AlphaClip", 1); net.SetFloat("_Cutoff", .5f); net.EnableKeyword("_ALPHATEST_ON");
            net.SetOverrideTag("RenderType", "TransparentCutout"); net.renderQueue = (int)RenderQueue.AlphaTest;
            net.SetFloat("_Cull", 0); net.doubleSidedGI = true;
            net.SetFloat("_Smoothness", .18f); net.SetFloat("_Metallic", 0);
            var pv = NewOrLoad("RT_SolarCell", lit);
            pv.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + "RT_SolarCell_Base.png"));
            pv.SetTextureScale("_BaseMap", new Vector2(1.068f, 1.068f));       // 6 x 6 cells of 156 mm per tile
            pv.SetColor("_BaseColor", Color.white);
            pv.SetFloat("_Smoothness", .9f); pv.SetFloat("_Metallic", 0);
            var cer = NewOrLoad("RT_Ceramic", lit);
            cer.SetTexture("_BaseMap", null);
            cer.SetColor("_BaseColor", new Color(.78f, .75f, .69f));
            cer.SetFloat("_Smoothness", .72f); cer.SetFloat("_Metallic", 0);
            foreach (var m in new[] { net, pv, cer }) { m.enableInstancing = true; EditorUtility.SetDirty(m); }
            AssetDatabase.SaveAssets();
            var mats = new Dictionary<string, Material>();
            foreach (var dir in SharedMaterialDirs)
                foreach (var g in AssetDatabase.FindAssets("t:Material", new[] { dir }))
                {
                    var p = AssetDatabase.GUIDToAssetPath(g);
                    if (Path.GetDirectoryName(p).Replace('\\', '/') != dir) continue;
                    var m = AssetDatabase.LoadAssetAtPath<Material>(p);
                    if (m && !mats.ContainsKey(m.name)) mats[m.name] = m;
                }
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

        /// LOD switch heights (screen-relative height of the group's largest extent; the PC preset's LOD bias is 2).
        static float[] Cuts(string id, float size)
        {
            if (id.StartsWith("Lines_")) return new[] { .14f, .0015f };           // spans and drops: thin, long, keep them far
            if (id == "Whip" || id.StartsWith("CableMast")) return new[] { .3f, .004f };
            if (id.StartsWith("Ladder")) return new[] { .35f, .01f };
            if (id == "JunctionBox" || id == "WallHook") return new[] { .07f, .015f };
            if (id.StartsWith("Tank")) return new[] { .3f, .008f };
            return size > 2f ? new[] { .28f, .008f } : new[] { .22f, .012f };
        }

        static object BuildPrefab(string id, JObject rec, Dictionary<string, Material> mats, HashSet<string> missing, bool line)
        {
            var root = new GameObject("RT_" + id);
            try
            {
                float size = line ? 10f : rec["size"].Max(x => (float)x);
                bool shadows = !line && rec["shadows"] != null && (bool)rec["shadows"];
                var cuts = Cuts(id, size);
                var levels = new List<LOD>();
                long[] tris = new long[2];
                for (int lod = 0; lod < 2; lod++)
                {
                    var rs = Instance(ModelDir + $"RT_{id}_LOD{lod}.glb", root.transform, "LOD" + lod, mats, missing);
                    foreach (var r in rs)
                    {
                        r.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
                        if (r.TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh)
                            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) tris[lod] += mf.sharedMesh.GetIndexCount(s) / 3;
                    }
                    levels.Add(new LOD(cuts[lod], rs.ToArray()));
                }
                var g = root.AddComponent<LODGroup>(); g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                // ladders: a box from the wall to the rails over the bottom 2.2 m, so nobody walks into the cage's foot
                if (!line && rec["collider"] != null && rec["collider"].Type == JTokenType.Object)
                {
                    var b = root.AddComponent<BoxCollider>();
                    b.center = V3(rec["collider"]["center"]); b.size = V3(rec["collider"]["size"]);
                }
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(id));
                return new { lod0 = tris[0], lod1 = tris[1], cuts, shadows };
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        // ------------------------------------------------------------------ install (one time)
        [MenuItem("Athen Hill/Rooftops/Install (one time)")]
        public static string Install() => Install(false);

        /// Authoring iteration only: replaces the installed root (the first rollback copy of the scene is kept).
        public static string Reinstall() => Install(true);

        static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath);
            if (scene.isDirty) throw new Exception("Save or discard scene changes before installing.");
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (existing && !replace) throw new Exception("Ward rooftops are already installed; edit the instances in place (or Reinstall while authoring).");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>(FindObjectsInactive.Include);
            string fpBefore = chunks ? StaticRenderChunksEditor.Fingerprint(chunks) : null;
            Directory.CreateDirectory(Evidence + "rollback");
            var rollback = Evidence + "rollback/before-rooftops-install.unity";
            if (!replace || !File.Exists(rollback)) File.Copy(ScenePath, rollback, true);
            if (existing) UnityEngine.Object.DestroyImmediate(existing);

            var layout = Layout();
            var lines = Lines();
            var root = new GameObject(RootName);
            var placed = new Dictionary<string, int>();
            var missing = new HashSet<string>();
            var groups = new List<object>();
            foreach (var g in layout["groups"])
            {
                var go = new GameObject((string)g["name"]);
                go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(V3(g["root"]), Quaternion.Euler(0, (float)g["yaw"], 0));
                int n = 0;
                foreach (var it in g["items"])
                {
                    var id = (string)it["id"];
                    bool sd = (bool)it["sd"];
                    var path = sd ? StreetDressingPass.PrefabPath(id) : PrefabPath(id);
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                    if (!prefab) { missing.Add(path); continue; }
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                    inst.transform.SetParent(go.transform, false);
                    inst.transform.localPosition = V3(it["local"]);
                    inst.transform.localRotation = Quaternion.Euler(0, (float)it["localYaw"], 0);
                    inst.name = id;
                    if (sd)          // street-kit seats and crate on a roof: nobody sees their shadow from the street
                        foreach (var rr in inst.GetComponentsInChildren<Renderer>(true))
                        {
                            rr.shadowCastingMode = ShadowCastingMode.Off;
                            PrefabUtility.RecordPrefabInstancePropertyModifications(rr);
                        }
                    placed[id] = placed.TryGetValue(id, out var c) ? c + 1 : 1;
                    n++;
                }
                groups.Add(new { name = go.name, items = n });
            }
            var linesRoot = new GameObject(LinesName);
            linesRoot.transform.SetParent(root.transform, false);
            foreach (var p in lines.Properties())
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(p.Name));
                if (!prefab) { missing.Add(PrefabPath(p.Name)); continue; }
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                inst.transform.SetParent(linesRoot.transform, false);
                inst.transform.position = V3(p.Value["origin"]);
                inst.name = (string)p.Value["group"];
                placed[p.Name] = 1;
            }
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            var record = new
            {
                utc = DateTime.UtcNow, rollback, groups, lines = lines.Properties().Count(), placed = placed.OrderBy(kv => kv.Key).ToDictionary(kv => kv.Key, kv => kv.Value),
                missingPrefabs = missing.ToArray(), retired = new string[0], lights = 0,
                chunkFingerprintBefore = fpBefore, chunkFingerprintAfter = chunks ? StaticRenderChunksEditor.Fingerprint(chunks) : null,
                reviewCameras = Cams().Properties().Select(x => x.Name).ToArray(), replace,
            };
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + (replace ? "reinstall.json" : "install.json"), json);
            return json;
        }

        // ------------------------------------------------------------------ review cameras
        static void AddReviewCameras(UnityEngine.SceneManagement.Scene scene)
        {
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            foreach (var p in Cams().Properties())
            {
                var pos = V3(p.Value["pos"]); var target = V3(p.Value["target"]);
                var go = new GameObject(p.Name); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var k = go.AddComponent<Camera>(); k.enabled = false; k.fieldOfView = (float)p.Value["fov"]; k.nearClipPlane = .05f; k.farClipPlane = 1200f;
            }
        }

        [MenuItem("Athen Hill/Rooftops/Add review cameras")]
        public static string CamerasOnly()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return "review cameras: " + scene.GetRootGameObjects().First(g => g.name == CamRootName).transform.childCount;
        }

        // ------------------------------------------------------------------ verify
        [MenuItem("Athen Hill/Rooftops/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            int expected = layout["groups"].Sum(g => g["items"].Count()) + Lines().Properties().Count();
            r["expectedInstances"] = expected;
            if (root)
            {
                var inst = root.GetComponentsInChildren<LODGroup>(true);
                r["instances"] = inst.Length;
                r["prefabLinked"] = inst.Count(g => PrefabUtility.IsPartOfPrefabInstance(g.gameObject) && !PrefabUtility.IsPrefabAssetMissing(g.gameObject));
                r["groups"] = root.transform.Cast<Transform>().Select(t => t.name + " (" + t.childCount + ")").ToArray();
                var rends = root.GetComponentsInChildren<Renderer>(true);
                r["missingMaterials"] = rends.Count(x => x.sharedMaterials.Any(m => !m));
                r["errorShaderMaterials"] = rends.SelectMany(x => x.sharedMaterials).Where(m => m && (m.shader == null || m.shader.name.Contains("Error"))).Select(m => m.name).Distinct().ToArray();
                long lod0 = 0, lod1 = 0, shadowLod0 = 0;
                foreach (var g in inst)
                {
                    var lods = g.GetLODs();
                    foreach (var (level, i) in lods.Select((l, i) => (l, i)))
                        foreach (var rr in level.renderers)
                            if (rr && rr.TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh)
                            {
                                long t = 0;
                                for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) t += mf.sharedMesh.GetIndexCount(s) / 3;
                                if (i == 0) { lod0 += t; if (rr.shadowCastingMode != ShadowCastingMode.Off) shadowLod0 += t; } else lod1 += t;
                            }
                }
                r["lod0Triangles"] = lod0; r["lod1Triangles"] = lod1; r["lod0ShadowCasterTriangles"] = shadowLod0;
                r["renderers"] = rends.Length;
                r["shadowCasters"] = rends.Count(x => x.shadowCastingMode != ShadowCastingMode.Off);
                r["lights"] = root.GetComponentsInChildren<Light>(true).Length;
                r["colliders"] = root.GetComponentsInChildren<Collider>(true).Select(c => PathOf(c.transform)).ToArray();
                r["nonUniformScale"] = root.GetComponentsInChildren<Transform>(true).Where(t => Mathf.Abs(t.localScale.x - t.localScale.y) > 1e-4 || Mathf.Abs(t.localScale.y - t.localScale.z) > 1e-4).Select(PathOf).ToArray();
                // each shop group must still sit exactly on its shop's root
                var off = new List<string>();
                foreach (var g in layout["groups"])
                {
                    var t = root.transform.Find((string)g["name"]);
                    if (!t) { off.Add("missing " + g["name"]); continue; }
                    if ((t.position - V3(g["root"])).magnitude > 1e-3 || Mathf.Abs(Mathf.DeltaAngle(t.eulerAngles.y, (float)g["yaw"])) > .01f) off.Add((string)g["name"]);
                }
                r["groupsOffTheirShop"] = off.ToArray();
            }
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>(FindObjectsInactive.Include);
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            var cams = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            r["reviewCameras"] = cams ? cams.GetComponentsInChildren<Camera>(true).Select(c => c.name + (c.enabled ? " (ENABLED)" : "")).ToArray() : new string[0];
            r["retiredStillActive"] = new string[0];          // this pass retires nothing
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        // ------------------------------------------------------------------ editor captures (scene not saved)
        /// Renders the named review cameras (at most six per run, see BRIEF memory safety) through a MainCamera clone.
        /// mode "off" deactivates the rooftops root in memory first (matched before/after; nothing is saved).
        public static string Capture(string outDir, string camList, string mode)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (mode == "off" && root) root.SetActive(false);
            var cams = Cams();
            var names = string.IsNullOrEmpty(camList) ? cams.Properties().Select(p => p.Name).ToList() : camList.Split('+').ToList();
            if (names.Count > 6) throw new Exception("At most six cameras per capture run (VRAM).");
            var views = new List<(string, Vector3, Vector3, float)>();
            foreach (var n in names)
            {
                var c = cams[n];
                if (c != null) { views.Add((n + (mode == "off" ? "-off" : ""), V3(c["pos"]), V3(c["target"]), (float)c["fov"])); continue; }
                var cam = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true)).FirstOrDefault(k => k.name == n);
                if (!cam) throw new Exception("No camera " + n);
                views.Add((n + (mode == "off" ? "-off" : ""), cam.transform.position, cam.transform.position + cam.transform.forward * 10f, cam.fieldOfView));
            }
            return string.Join(",", StreetDressingPass.Capture(outDir, views));
        }

        /// Measurement only (A/B): switches the whole rooftops root off or on in the saved scene.
        static string Toggle(bool on)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            root.SetActive(on);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return RootName + (on ? " on" : " off");
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.RooftopsPass.RunBatch --steps build,install,verify,capture[:out[:cam+cam[:off]]]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "build").Split(',');
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "build" => BuildAssets(),
                        "install" => Install(),
                        "reinstall" => Reinstall(),
                        "verify" => Verify(),
                        "cams" => CamerasOnly(),
                        "capture" => Capture(parts.Length > 1 && parts[1] != "" ? parts[1] : Evidence + "editor", parts.Length > 2 ? parts[2] : "", parts.Length > 3 ? parts[3] : ""),
                        "toggle" => Toggle(parts[1] == "on"),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("RooftopsPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
