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
    /// 1 October 2026: Ward perimeter walls. Carl: "walls look too clean, maybe some parts of the wall have fallen."
    /// Replaces the flat 44-triangle boxes of the north/south boundary walls, the +X (legacy "west") rampart by the
    /// District gate, the strip wall beyond it and the -X Outer Berms walls with a modular kit on the shared Ward masonry
    /// (art/perimeter_walls_20261001: author_perimeter_walls.py builds every module at LOD0-2 plus a shadow mesh,
    /// pw_layout.py writes layout.json). Old, battle-scarred, repaired stone: weathered and repaired bays, broken merlons,
    /// shell damage, two collapsed tops and the old siege breach by the West Gate portal closed with HESCO, sandbags and a
    /// welded sheet screen.
    ///
    /// Menu: Athen Hill → Perimeter walls → Build assets (materials + one prefab per module: LODGroup, a ShadowsOnly
    /// massing mesh, convex rubble-cone colliders), Install (one time, refuses when the root exists; rollback copy of the
    /// scene, old wall visuals retired inactive, render chunks rebuilt), Verify saved scene, review cameras. The saved
    /// wall colliders are untouched, so the visual breaches stay blocked. The new walls are not render-chunk sources:
    /// move or swap module instances under "Ward perimeter walls" in the Scene view (uniform transforms only).
    /// </summary>
    public static class PerimeterWallsPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/PerimeterWalls/";
        const string ModelDir = Root + "Models/";
        const string MatDir = Root + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/PerimeterWalls/";
        const string HallMats = "Assets/AthenHill/Art/VanguardHall/Materials/";
        const string HillMats = "Assets/AthenHill/Art/WardHill/Materials/";
        const string StreetMats = "Assets/AthenHill/Art/StreetDressing/Materials/";
        const string RetrofitGlb = "Assets/AthenHill/Art/WardRetrofit/WardRetrofit.glb";
        const string LayoutPath = "../../art/perimeter_walls_20261001/layout.json";
        const string Evidence = "../evidence/perimeter-walls/20261001/";
        public const string RootName = "Ward perimeter walls";
        public const string CamRootName = "Perimeter wall review cameras";
        static readonly string[] Kinds = { "NS", "EX", "BW" };

        // LOD switch distances (metres at 60° FOV, PC lodBias 2 applied): bevelled, chipped LOD0 within ~16 m,
        // single-bevel LOD1 to ~45 m, flat-block LOD2 beyond. Each prefab converts these with its own LODGroup size.
        const float Lod0Distance = 16f, Lod1Distance = 45f, CullDistance = 900f, LodBias = 2f;

        static JObject Layout() => JObject.Parse(File.ReadAllText(LayoutPath));
        static string PrefabPath(string id) => PrefabDir + id + ".prefab";

        // ------------------------------------------------------------------ build assets
        [MenuItem("Athen Hill/Perimeter walls/Build assets")]
        public static string BuildAssets()
        {
            AssetDatabase.Refresh();
            foreach (var k in Kinds)
                for (int lod = 0; lod < 4; lod++)
                    AssetDatabase.ImportAsset(ModelDir + $"PW_{k}_LOD{lod}.glb", ImportAssetOptions.ForceUpdate);
            var mats = BuildMaterials();
            Directory.CreateDirectory(PrefabDir);
            var layout = Layout();
            var missing = new HashSet<string>();
            var report = new Dictionary<string, object>();
            // every node of every LOD file, by name (one load per file)
            var nodes = new Dictionary<string, Transform>();
            var models = new List<GameObject>();
            foreach (var k in Kinds)
                for (int lod = 0; lod < 4; lod++)
                {
                    var path = ModelDir + $"PW_{k}_LOD{lod}.glb";
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                    if (!model) throw new Exception("Model not imported: " + path);
                    foreach (var t in model.GetComponentsInChildren<Transform>(true)) nodes[t.name] = t;
                }
            foreach (var p in ((JObject)layout["modules"]).Properties())
                report[p.Name] = BuildPrefab(p.Name, (string)p.Value["kind"], nodes, mats, missing);
            AssetDatabase.SaveAssets();
            var json = JsonConvert.SerializeObject(new { modules = report, unmapped = missing.OrderBy(x => x).ToArray() }, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "build-assets.json", json);
            return "prefabs " + report.Count + ", unmapped: " + (missing.Count == 0 ? "none" : string.Join(", ", missing));
        }

        static Material Load(string path)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) throw new Exception("Material missing: " + path);
            return m;
        }

        static Dictionary<string, Material> BuildMaterials()
        {
            var mats = new Dictionary<string, Material>();
            // the shared Ward masonry (Masonry Lit) and the hall's fittings
            foreach (var n in new[] { "VH_Ashlar", "VH_AshlarRough", "VH_Mortar", "VH_PodiumSlab", "VH_Sand", "VH_Steel", "VH_PaintedSteel", "VH_Dark" })
                mats[n] = Load(HallMats + n + ".mat");
            // field repairs: the street-dressing sacks and scrap sheet, the retrofit HESCO (same baskets as the gate defences)
            mats["SD_Sack"] = Load(StreetMats + "SD_Sack.mat");
            mats["SD_ScrapSheet"] = Load(StreetMats + "SD_ScrapSheet.mat");
            var retro = AssetDatabase.LoadAllAssetsAtPath(RetrofitGlb).OfType<Material>().ToList();
            Material Retro(string n) => retro.FirstOrDefault(m => m.name == n || m.name.StartsWith(n + "."))
                                        ?? throw new Exception(n + " not found in " + RetrofitGlb);
            mats["PW_Hesco"] = Retro("Retro_Hesco");
            mats["PW_RustSheet"] = Retro("Retro_RustSheet");
            mats["PW_Corrugated"] = Retro("Retro_CorrugatedWorn");
            // rubble cones: the retrofit's concrete-debris rubble, warmed to the Ward sandstone (a copy; the retrofit keeps its own)
            Directory.CreateDirectory(MatDir);
            var rubblePath = MatDir + "PW_Rubble.mat";
            var rubble = AssetDatabase.LoadAssetAtPath<Material>(rubblePath);
            var src = Retro("Retro_Rubble");
            if (!rubble) { rubble = new Material(src) { name = "PW_Rubble" }; AssetDatabase.CreateAsset(rubble, rubblePath); }
            else { rubble.shader = src.shader; rubble.CopyPropertiesFromMaterial(src); }
            var warm = new Color(1.0f, .84f, .66f, 1f);
            foreach (var prop in new[] { "baseColorFactor", "_BaseColor", "_Color" })
                if (rubble.HasProperty(prop)) rubble.SetColor(prop, rubble.GetColor(prop) * warm);
            EditorUtility.SetDirty(rubble);
            mats["PW_Rubble"] = rubble;
            // dry grass and weeds at the wall feet: the hill's Poly Haven plants on the Ward Ground Cover wind shader
            mats["grass_medium_01"] = Load(HillMats + "grass_medium_01.mat");
            mats["weed_plant_02"] = Load(HillMats + "weed_plant_02.mat");
            // shadow massing: a plain opaque Lit material (only its ShadowCaster pass runs)
            Directory.CreateDirectory(MatDir);
            var shadowPath = MatDir + "PW_ShadowCaster.mat";
            var sh = AssetDatabase.LoadAssetAtPath<Material>(shadowPath);
            if (!sh)
            {
                sh = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "PW_ShadowCaster" };
                AssetDatabase.CreateAsset(sh, shadowPath);
            }
            sh.enableInstancing = true;
            EditorUtility.SetDirty(sh);
            mats["PW_Shadow"] = sh;
            return mats;
        }

        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m)) return m;
            var trimmed = System.Text.RegularExpressions.Regex.Replace(name, @"\.\d+$", "");
            return mats.TryGetValue(trimmed, out m) ? m : null;
        }

        static Renderer Part(Transform src, Transform parent, Dictionary<string, Material> mats, HashSet<string> missing, ShadowCastingMode shadows)
        {
            var mf = src.GetComponent<MeshFilter>();
            var mr = src.GetComponent<MeshRenderer>();
            if (!mf || !mr) return null;
            var go = new GameObject(src.name);
            go.transform.SetParent(parent, false);
            // node transforms are identity (modules are authored at their origin); keep any the importer added
            var root = src.root;
            go.transform.localPosition = root.InverseTransformPoint(src.position);
            go.transform.localRotation = Quaternion.Inverse(root.rotation) * src.rotation;
            go.AddComponent<MeshFilter>().sharedMesh = mf.sharedMesh;
            var r = go.AddComponent<MeshRenderer>();
            var slots = mr.sharedMaterials;
            for (int i = 0; i < slots.Length; i++)
            {
                var m = slots[i] ? Lookup(mats, slots[i].name) : null;
                if (m) slots[i] = m; else missing.Add(src.name + ":" + (slots[i] ? slots[i].name : "null"));
            }
            r.sharedMaterials = slots;
            r.shadowCastingMode = shadows;
            r.receiveShadows = shadows != ShadowCastingMode.ShadowsOnly;
            r.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
            r.receiveGI = ReceiveGI.LightProbes;
            r.lightProbeUsage = LightProbeUsage.BlendProbes;
            return r;
        }

        static int Tris(Renderer r)
        {
            var mf = r ? r.GetComponent<MeshFilter>() : null;
            if (!mf || !mf.sharedMesh) return 0;
            var m = mf.sharedMesh;
            int n = 0;
            for (int s = 0; s < m.subMeshCount; s++) n += (int)m.GetIndexCount(s) / 3;
            return n;
        }

        static object BuildPrefab(string id, string kind, Dictionary<string, Transform> nodes, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var root = new GameObject(id);
            var rec = new Dictionary<string, object>();
            try
            {
                var levels = new List<LOD>();
                var lodRenderers = new List<Renderer>[3];
                for (int lod = 0; lod < 3; lod++)
                {
                    var holder = new GameObject("LOD" + lod).transform; holder.SetParent(root.transform, false);
                    var rs = new List<Renderer>();
                    // stone: the ShadowsOnly massing casts for it; fittings, repairs and rubble cast their own (thin
                    // sheets and baskets would self-shadow against a coincident proxy); weeds never
                    foreach (var part in new[] { "Stone", "Kit", "Weeds" })
                        if (nodes.TryGetValue($"{id}_{part}_LOD{lod}", out var src))
                        {
                            var r = Part(src, holder, mats, missing, part == "Kit" ? ShadowCastingMode.On : ShadowCastingMode.Off);
                            if (r) rs.Add(r);
                        }
                    if (rs.Count == 0) throw new Exception("No LOD" + lod + " meshes for " + id);
                    lodRenderers[lod] = rs;
                    rec["LOD" + lod] = rs.Sum(Tris);
                }
                // one ShadowsOnly massing mesh for every LOD level: shadows never pop between LODs and the bevelled
                // ashlar never reaches the shadow maps (the walls frame most views, inside all four cascades)
                Renderer shadow = null;
                if (nodes.TryGetValue(id + "_Shadow", out var ssrc))
                {
                    var holder = new GameObject("Shadow caster").transform; holder.SetParent(root.transform, false);
                    shadow = Part(ssrc, holder, mats, missing, ShadowCastingMode.ShadowsOnly);
                    rec["shadow"] = Tris(shadow);
                }
                else missing.Add(id + "_Shadow (no shadow mesh)");
                for (int lod = 0; lod < 3; lod++)
                {
                    var rs = lodRenderers[lod].ToList();
                    if (shadow) rs.Add(shadow);
                    levels.Add(new LOD(new[] { .5f, .2f, .01f }[lod], rs.ToArray()));   // placeholders until the size is known
                }
                var g = root.AddComponent<LODGroup>();
                g.SetLODs(levels.ToArray());
                g.fadeMode = LODFadeMode.None;
                g.RecalculateBounds();
                float H(float d) => Mathf.Clamp(g.size * LodBias / (2f * d * Mathf.Tan(30f * Mathf.Deg2Rad)), .004f, .98f);
                var cuts = new[] { H(Lod0Distance), H(Lod1Distance), H(CullDistance) };
                for (int i = 0; i < levels.Count; i++) levels[i] = new LOD(cuts[i], levels[i].renderers);
                g.SetLODs(levels.ToArray());
                g.RecalculateBounds();
                rec["lodCuts"] = cuts.Select(c => Math.Round(c, 4)).ToArray();
                rec["size"] = Math.Round(g.size, 2);
                // rubble cones: low convex colliders (the wall colliders themselves stay in the scene, untouched)
                var cones = nodes.Keys.Where(n => n.StartsWith(id + "_ColCone")).OrderBy(n => n).ToList();
                if (cones.Count > 0)
                {
                    var cols = new GameObject("Rubble colliders").transform; cols.SetParent(root.transform, false);
                    foreach (var n in cones)
                    {
                        var go = new GameObject(n.Replace(id + "_", "")); go.transform.SetParent(cols, false);
                        var mc = go.AddComponent<MeshCollider>();
                        mc.sharedMesh = nodes[n].GetComponent<MeshFilter>().sharedMesh;
                        mc.convex = true;
                    }
                    rec["coneColliders"] = cones.Count;
                }
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, t.name.Contains("_Weeds_")
                        ? StaticEditorFlags.OccludeeStatic : StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(id));
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
            return rec;
        }

        // ------------------------------------------------------------------ scene helpers
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        static Transform FindPath(UnityEngine.SceneManagement.Scene scene, string path)
        {
            var parts = path.Split('/');
            var top = scene.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!top) return null;
            var t = top.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Cast<Transform>().FirstOrDefault(c => c.name == parts[i]);
            return t;
        }

        public static List<Transform> RetireList(UnityEngine.SceneManagement.Scene scene, JObject layout)
        {
            var list = new List<Transform>();
            foreach (var p in layout["retire"].Select(x => (string)x)) { var t = FindPath(scene, p); if (t) list.Add(t); }
            foreach (var pre in layout["retirePrefixes"].Select(x => (string)x))
            {
                int slash = pre.LastIndexOf('/');
                var parent = FindPath(scene, pre.Substring(0, slash));
                var prefix = pre.Substring(slash + 1);
                if (!parent) continue;
                foreach (Transform c in parent) if (c.name.StartsWith(prefix) && !c.name.StartsWith("COL_")) list.Add(c);
            }
            return list.Distinct().ToList();
        }

        // ------------------------------------------------------------------ install
        [MenuItem("Athen Hill/Perimeter walls/Install (one time)")]
        public static string Install() => Install(false);

        /// Authoring iteration only: replaces the installed walls root (retired objects stay retired; the first rollback
        /// copy of the scene is kept).
        public static string Reinstall() => Install(true);

        static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (existing && !replace) throw new Exception("The perimeter walls are already installed; edit the module instances in place.");
            if (existing) UnityEngine.Object.DestroyImmediate(existing);
            var layout = Layout();
            Directory.CreateDirectory(Evidence + "rollback");
            if (!replace) File.Copy(ScenePath, Evidence + "rollback/before-perimeter-walls.unity", true);
            var record = new Dictionary<string, object>();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) chunks.ShowSources(true);

            var retired = new List<object>();
            foreach (var t in RetireList(scene, layout))
            {
                retired.Add(new { path = PathOf(t), wasActive = t.gameObject.activeSelf });
                if (!t.gameObject.activeSelf) continue;
                Undo.RecordObject(t.gameObject, "Retire wall visual");
                t.gameObject.SetActive(false);
                if (PrefabUtility.IsPartOfPrefabInstance(t.gameObject)) PrefabUtility.RecordPrefabInstancePropertyModifications(t.gameObject);
            }
            record["retired"] = retired;

            var root = new GameObject(RootName);
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
            var walls = new Dictionary<string, Transform>();
            var placed = new Dictionary<string, int>();
            var missing = new HashSet<string>();
            foreach (var p in layout["placements"])
            {
                var wall = (string)p["wall"]; var id = (string)p["module"];
                if (!walls.TryGetValue(wall, out var w)) { w = new GameObject(wall).transform; w.SetParent(root.transform, false); walls[wall] = w; }
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(id));
                if (!prefab) { missing.Add(id); continue; }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.transform.SetParent(w, false);
                var pos = p["pos"];
                go.transform.SetPositionAndRotation(new Vector3((float)pos[0], (float)pos[1], (float)pos[2]), Quaternion.Euler(0, (float)p["yaw"], 0));
                go.name = $"{(int)p["slot"]:00} {id}";
                placed[id] = placed.TryGetValue(id, out var c) ? c + 1 : 1;
            }
            record["placed"] = placed.Values.Sum();
            record["byModule"] = placed.OrderBy(kv => kv.Key).ToDictionary(kv => kv.Key, kv => kv.Value);
            record["missingPrefabs"] = missing.ToArray();
            record["walls"] = walls.Keys.ToArray();

            AddCameras(scene);
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            record["chunksRebuilt"] = chunks != null;
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + (replace ? "reinstall.json" : "install.json"), json);
            return json;
        }

        /// Measurement only (A/B frame time): switches the new walls root off or on in the saved scene (the old visuals
        /// stay retired either way; they were 44-triangle boxes, so "off" is the walls' whole cost).
        static string Toggle(bool on)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            root.SetActive(on);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return RootName + (on ? " on" : " off");
        }

        /// A/B timing builds (development, OpenGL), one build per Editor run (memory caps). Other passes toggle their own
        /// roots in the shared scene for their A/B runs, so both arms come from ONE snapshot of the saved scene:
        /// "on" writes two scene copies (walls root on / off) and builds the on copy to Builds/pw-ab-on; "off" builds the
        /// off copy to Builds/pw-ab-off and deletes both copies. The saved scene itself is never toggled.
        const string AbOnCopy = "Assets/AthenHill/Scenes/__pw_ab_on.unity", AbOffCopy = "Assets/AthenHill/Scenes/__pw_ab_off.unity";

        static string AbBuild(string arm)
        {
            string src;
            if (arm == "on")
            {
                var scene = EditorSceneManager.OpenScene(ScenePath);
                var root = scene.GetRootGameObjects().First(g => g.name == RootName);
                root.SetActive(true);
                if (!EditorSceneManager.SaveScene(scene, AbOnCopy, true)) throw new Exception("could not write " + AbOnCopy);
                root.SetActive(false);
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
                    scenes = new[] { src }, locationPathName = "Builds/pw-ab-" + arm + "/AthenHill.x86_64",
                    target = BuildTarget.StandaloneLinux64, options = BuildOptions.Development,
                });
                if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("A/B build failed: " + arm);
                return "pw-ab-" + arm + " " + report.summary.totalTime.TotalSeconds.ToString("0") + " s";
            }
            finally
            {
                if (arm == "off") { AssetDatabase.DeleteAsset(AbOnCopy); AssetDatabase.DeleteAsset(AbOffCopy); }
            }
        }

        // ------------------------------------------------------------------ review cameras
        // player-height views of every wall (eye 1.65 m), close-ups of the story beats and two raised views
        public static readonly (string name, Vector3 pos, Vector3 target, float fov)[] ReviewViews =
        {
            ("cam_pw_north_west", new Vector3(-12f, 1.65f, 31f), new Vector3(-24f, 2.6f, 43.5f), 60),
            ("cam_pw_north_east", new Vector3(14f, 1.65f, 31f), new Vector3(24f, 2.6f, 43.5f), 60),
            ("cam_pw_north_foot", new Vector3(-5f, 1.65f, 39.8f), new Vector3(-1f, 1.8f, 44f), 60),
            ("cam_pw_south_lane", new Vector3(-21f, 1.65f, -38.5f), new Vector3(-8f, 2.2f, -43.5f), 60),
            ("cam_pw_south_east", new Vector3(8f, 1.65f, -33f), new Vector3(20f, 2.6f, -43.5f), 60),
            ("cam_pw_south_foot", new Vector3(10f, 1.65f, -39.5f), new Vector3(13f, 1.5f, -44f), 60),
            ("cam_pw_east_gate", new Vector3(36f, 1.65f, 6f), new Vector3(47f, 3.8f, 6f), 60),
            ("cam_pw_east_south", new Vector3(39f, 1.65f, -16f), new Vector3(46.5f, 3.2f, -28f), 60),
            ("cam_pw_east_north", new Vector3(39f, 1.65f, 20f), new Vector3(46.5f, 3.4f, 27f), 60),
            ("cam_pw_east_foot", new Vector3(42.8f, 1.65f, -19f), new Vector3(46.5f, 1.8f, -22.5f), 60),
            ("cam_pw_west_gap", new Vector3(-46f, 1.65f, -14f), new Vector3(-58.5f, 1.8f, -3f), 60),
            ("cam_pw_west_north", new Vector3(-47f, 1.65f, 18f), new Vector3(-58f, 1.5f, 30f), 60),
            ("cam_pw_west_south", new Vector3(-47f, 1.65f, -12f), new Vector3(-58f, 1.5f, -26f), 60),
            ("cam_pw_outer_west", new Vector3(-65.5f, .45f, -10f), new Vector3(-60f, 1.2f, -22f), 60),
            ("cam_pw_corner_nw_high", new Vector3(-30f, 9f, 20f), new Vector3(-55f, 2f, 44f), 55),
            ("cam_pw_south_high", new Vector3(0f, 11f, -12f), new Vector3(10f, 2f, -44f), 55),
            // 1 Oct restart: the story beats up close
            ("cam_pw_south_collapse", new Vector3(13.5f, 1.65f, -37.5f), new Vector3(10.2f, 2.3f, -44f), 60),
            ("cam_pw_north_collapse", new Vector3(-49.5f, 1.65f, 39.0f), new Vector3(-45.6f, 2.6f, 44f), 60),
            ("cam_pw_berms_breach", new Vector3(-52.5f, 1.65f, -10.5f), new Vector3(-58f, 1.4f, -15f), 60),
            ("cam_pw_berms_breach_out", new Vector3(-65.5f, .3f, -18.5f), new Vector3(-60f, 1.2f, -14.5f), 60),
            ("cam_pw_gate_siege", new Vector3(41.5f, 1.65f, -11.5f), new Vector3(46.5f, 4.2f, -6.8f), 60),
            ("cam_pw_rampart_close", new Vector3(44.0f, 1.65f, -20.5f), new Vector3(46.5f, 2.0f, -18.2f), 60),
        };

        static void AddCameras(UnityEngine.SceneManagement.Scene scene)
        {
            // keep the existing cameras (their ids are saved in the scene); add the missing ones
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (!root)
            {
                root = new GameObject(CamRootName);
                UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
            }
            foreach (var (name, pos, target, fov) in ReviewViews)
            {
                var t = root.transform.Find(name);
                if (!t) { t = new GameObject(name).transform; t.SetParent(root.transform, false); }
                t.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var c = t.GetComponent<Camera>();
                if (!c) c = t.gameObject.AddComponent<Camera>();
                c.enabled = false; c.fieldOfView = fov; c.nearClipPlane = .05f;
            }
        }

        [MenuItem("Athen Hill/Perimeter walls/Add review cameras")]
        public static string ReviewCameras()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            AddCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return "review cameras: " + ReviewViews.Length;
        }

        // existing scene cameras that frame the walls (lookbook names)
        public static readonly string[] SceneViews = { "cam_gate", "cam_hill", "cam_hero", "cam_avenue", "cam_grid", "cam_market",
                                                       "cam_berms_overview", "cam_westgate_mouth", "cam_wear_wall" };

        /// Editor captures (MainCamera clone, post-processing on) of the review cameras and the scene cameras; not saved.
        /// filter: '+'-separated name prefixes. withCameras: add the review cameras first (in memory only).
        public static string CaptureViews(string outDir, string filter)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            AddCameras(scene);
            var cams = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true))
                .Where(c => c.name.StartsWith("cam_pw_") || SceneViews.Contains(c.name))
                .Where(c => string.IsNullOrEmpty(filter) || filter.Split('+').Any(f => c.name.StartsWith(f)))
                .GroupBy(c => c.name).Select(g => g.First()).OrderBy(c => c.name).ToList();
            var views = cams.Select(c => (c.name, c.transform.position, c.transform.position + c.transform.forward * 10f, c.fieldOfView)).ToList();
            return string.Join(",", StreetDressingPass.Capture(outDir, views));
        }

        /// Editor audition: the kit laid out in a row on the open paving east of the hill (in memory, not saved).
        public static string Audition(string outDir, string filter)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var ids = ((JObject)layout["modules"]).Properties().Select(p => p.Name)
                .Where(n => string.IsNullOrEmpty(filter) || filter.Split('+').Any(f => n.Contains(f))).OrderBy(n => n).ToList();
            var root = new GameObject("__audition");
            float x = 0f; var views = new List<(string, Vector3, Vector3, float)>();
            foreach (var id in ids)
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(id)), scene);
                go.transform.SetParent(root.transform, true);
                float L = (float)layout["modules"][id]["length"];
                go.transform.SetPositionAndRotation(new Vector3(18f + x, 0f, 12f), Quaternion.identity);
                views.Add((id, new Vector3(18f + x + L * .5f + 1.5f, 1.65f, 12f + 7f), new Vector3(18f + x + L * .5f, 2.2f, 12f), 60f));
                x += L + 1.5f;
            }
            var shots = StreetDressingPass.Capture(outDir, views);
            UnityEngine.Object.DestroyImmediate(root);
            return string.Join(",", shots);
        }

        // ------------------------------------------------------------------ verify
        [MenuItem("Athen Hill/Perimeter walls/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            if (root)
            {
                var mods = root.GetComponentsInChildren<LODGroup>(true);
                r["active"] = root.activeSelf;
                r["modules"] = mods.Length;
                r["expectedModules"] = layout["placements"].Count();
                r["prefabLinked"] = mods.Count(m => PrefabUtility.IsPartOfPrefabInstance(m.gameObject));
                r["nonUniformScale"] = mods.Where(m => (m.transform.lossyScale - Vector3.one).sqrMagnitude > 1e-6).Select(m => PathOf(m.transform)).ToArray();
                var rends = root.GetComponentsInChildren<Renderer>(true);
                r["renderers"] = rends.Length;
                r["missingMaterials"] = rends.Count(x => x.sharedMaterials.Any(m => !m));
                r["materials"] = rends.SelectMany(x => x.sharedMaterials).Where(m => m).Select(m => m.name + " (" + m.shader.name + ")").Distinct().OrderBy(x => x).ToArray();
                long[] tri = new long[4];
                foreach (var g in mods)
                {
                    var lods = g.GetLODs();
                    for (int i = 0; i < lods.Length && i < 3; i++) tri[i] += lods[i].renderers.Where(x => x && x.shadowCastingMode != ShadowCastingMode.ShadowsOnly).Sum(Tris);
                    tri[3] += lods[0].renderers.Where(x => x && x.shadowCastingMode == ShadowCastingMode.ShadowsOnly).Sum(Tris);
                }
                r["trianglesAllModules"] = new { LOD0 = tri[0], LOD1 = tri[1], LOD2 = tri[2], shadow = tri[3] };
                r["coneColliders"] = root.GetComponentsInChildren<MeshCollider>(true).Length;
            }
            r["retiredStillActive"] = RetireList(scene, layout).Where(t => t.gameObject.activeSelf).Select(PathOf).ToArray();
            r["keptColliders"] = layout["keptColliders"].Select(x => (string)x)
                .Select(p => { var t = FindPath(scene, p); var c = t ? t.GetComponent<Collider>() : null; return new { p, ok = t && t.gameObject.activeInHierarchy && c && c.enabled }; })
                .Where(x => !x.ok).Select(x => x.p).ToArray();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            var cams = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            r["reviewCameras"] = cams ? cams.GetComponentsInChildren<Camera>(true).Length : 0;
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.PerimeterWallsPass.RunBatch --steps build,install,verify,capture[:filter] [--out dir]
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
                        "build" => BuildAssets(),
                        "install" => Install(),
                        "reinstall" => Reinstall(),
                        "cameras" => ReviewCameras(),
                        "toggle" => Toggle(parts[1] == "on"),
                        "abbuild" => AbBuild(parts[1]),
                        "capture" => CaptureViews(outDir, parts.Length > 1 ? parts[1] : ""),
                        "audition" => Audition(outDir, parts.Length > 1 ? parts[1] : ""),
                        "verify" => Verify(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("PerimeterWallsPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
