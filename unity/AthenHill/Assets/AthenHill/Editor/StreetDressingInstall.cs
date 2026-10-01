using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>
    /// Ward street dressing (30 Sep 2026): installs art/street_dressing_20260930/layout.json into the saved scene.
    /// One time (refuses when the root exists). Retires the 8 Sep salvage scatter (trash, crates, scrap, generators) and
    /// the primitive-cube street dressing (inactive, kept for rollback; they are render-chunk sources, so the chunks are
    /// rebuilt), hides the four retrofit collider proxies that rendered as grey slabs (collision kept), and places the
    /// kit as prefab instances under "Ward street dressing/&lt;vignette&gt;". Move, add or delete instances in the Scene view;
    /// they are not render-chunk sources. See StreetDressingPass for the kit.
    /// </summary>
    public static class StreetDressingInstall
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string LayoutPath = "../../art/street_dressing_20260930/layout.json";
        const string Evidence = "../evidence/street-dressing/20260930/";
        const string CamRootName = "Street dressing review cameras";

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        static IEnumerable<Transform> All(UnityEngine.SceneManagement.Scene scene) =>
            scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true));

        /// Objects whose path starts with one of the prefixes; only the top-most match of each subtree.
        static List<Transform> Matching(UnityEngine.SceneManagement.Scene scene, IEnumerable<string> prefixes)
        {
            var list = new List<Transform>();
            foreach (var t in All(scene))
            {
                var p = PathOf(t);
                if (!prefixes.Any(pre => p.StartsWith(pre))) continue;
                if (t.parent && prefixes.Any(pre => PathOf(t.parent).StartsWith(pre))) continue;
                list.Add(t);
            }
            return list;
        }

        const string DecalMaterial = "Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat";
        // quadrants of the weathering atlas (uvScale .49): sand drift, foundation grime, footprint scuffs, runoff
        static readonly Dictionary<string, Vector2> DecalBias = new()
        {
            ["sand"] = new Vector2(.005f, .505f), ["grime"] = new Vector2(.505f, .505f), ["scuffs"] = new Vector2(.005f, .005f),
        };

        [MenuItem("Athen Hill/Street dressing/Install (one time)")]
        public static string Install() => Install(false);

        /// Authoring iteration only: replaces the installed dressing root (retired objects stay retired; the first rollback
        /// copy of the scene is kept).
        public static string Reinstall() => Install(true);

        static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath);
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == StreetDressingPass.RootName);
            if (existing && !replace)
                throw new Exception("The street dressing is already installed; edit the instances in place.");
            if (existing) UnityEngine.Object.DestroyImmediate(existing);
            var layout = JObject.Parse(File.ReadAllText(LayoutPath));
            Directory.CreateDirectory(Evidence + "rollback");
            if (!replace) File.Copy(ScenePath, Evidence + "rollback/before-street-dressing.unity", true);
            var record = new Dictionary<string, object>();

            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) chunks.ShowSources(true);

            // retire the old scatter (inactive, not deleted)
            var retired = new List<object>();
            foreach (var t in Matching(scene, layout["retirePrefixes"].Select(x => (string)x)))
            {
                retired.Add(new { path = PathOf(t), wasActive = t.gameObject.activeSelf });
                Undo.RecordObject(t.gameObject, "Retire street prop");
                t.gameObject.SetActive(false);
                if (PrefabUtility.IsPartOfPrefabInstance(t.gameObject)) PrefabUtility.RecordPrefabInstancePropertyModifications(t.gameObject);
            }
            record["retired"] = retired;

            // retrofit collider proxies that were left rendering: renderer off, collider kept
            var hidden = new List<string>();
            foreach (var path in layout["hideRenderers"].Select(x => (string)x))
            {
                var t = All(scene).FirstOrDefault(x => PathOf(x) == path);
                var r = t ? t.GetComponent<MeshRenderer>() : null;
                if (!r) continue;
                Undo.RecordObject(r, "Hide collider proxy");
                r.enabled = false;
                if (PrefabUtility.IsPartOfPrefabInstance(r)) PrefabUtility.RecordPrefabInstancePropertyModifications(r);
                hidden.Add(path);
            }
            record["hiddenRenderers"] = hidden;

            // the kit, grouped by vignette
            var root = new GameObject(StreetDressingPass.RootName);
            var groups = new Dictionary<string, Transform>();
            var placed = new Dictionary<string, int>();
            var missing = new HashSet<string>();
            int n = 0;
            foreach (var p in layout["placements"])
            {
                var vig = (string)p["vignette"]; var prop = (string)p["prop"];
                if (!groups.TryGetValue(vig, out var g))
                {
                    g = new GameObject(vig).transform; g.SetParent(root.transform, false); groups[vig] = g;
                }
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(StreetDressingPass.PrefabPath(prop));
                if (!prefab) { missing.Add(prop); continue; }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.transform.SetParent(g, false);
                var pos = p["pos"]; var e = p["euler"];
                go.transform.SetPositionAndRotation(new Vector3((float)pos[0], (float)pos[1], (float)pos[2]),
                                                    Quaternion.Euler((float)e[0], (float)e[1], (float)e[2]));
                var scale = p["scale"] != null ? (float)p["scale"] : 1f;
                if (Mathf.Abs(scale - 1f) > 1e-3) go.transform.localScale = Vector3.one * scale;     // uniform only
                go.name = prop;
                placed[prop] = placed.TryGetValue(prop, out var c) ? c + 1 : 1;
                n++;
            }
            // group origins at their props' centre so a vignette can be moved as one piece
            foreach (var g in groups.Values)
            {
                var kids = g.Cast<Transform>().ToArray();
                if (kids.Length == 0) continue;
                var centre = kids.Aggregate(Vector3.zero, (a, t) => a + t.position) / kids.Length; centre.y = 0;
                foreach (var k in kids) k.SetParent(null, true);
                g.position = centre;
                foreach (var k in kids) k.SetParent(g, true);
            }
            // ground decals: grime under working clusters, footprint scuffs where people stand (URP decal projectors)
            var decalMat = AssetDatabase.LoadAssetAtPath<Material>(DecalMaterial);
            int decals = 0;
            if (decalMat && layout["decals"] != null)
                foreach (var d in layout["decals"])
                {
                    if (!groups.TryGetValue((string)d["vignette"], out var g)) continue;
                    var pos = d["pos"]; var size = d["size"];
                    var go = new GameObject("Ground " + (string)d["kind"]); go.transform.SetParent(g, false);
                    var fwd = Quaternion.Euler(0, (float)d["yaw"], 0) * Vector3.forward;
                    go.transform.SetPositionAndRotation(new Vector3((float)pos[0], (float)pos[1] + .25f, (float)pos[2]), Quaternion.LookRotation(Vector3.down, fwd));
                    var proj = go.AddComponent<UnityEngine.Rendering.Universal.DecalProjector>();
                    proj.material = decalMat;
                    proj.size = new Vector3((float)size[0], (float)size[1], .5f);
                    proj.pivot = new Vector3(0, 0, .25f);                  // from 0.25 m above the surface to 0.25 m below
                    proj.uvScale = new Vector2(.49f, .49f); proj.uvBias = DecalBias[(string)d["kind"]];
                    proj.fadeFactor = (float)d["opacity"]; proj.drawDistance = 30; proj.fadeScale = .7f;
                    proj.startAngleFade = 60; proj.endAngleFade = 85;      // ground and tops only, not the sides of walls and props
                    decals++;
                }
            record["decals"] = decals;
            record["placed"] = n;
            record["byProp"] = placed.OrderBy(kv => kv.Key).ToDictionary(kv => kv.Key, kv => kv.Value);
            record["vignettes"] = groups.Keys.OrderBy(x => x).ToArray();
            record["missingPrefabs"] = missing.ToArray();

            AddReviewCameras(scene, layout);
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            record["chunksRebuilt"] = chunks != null;
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + "install.json", json);
            return json;
        }

        // ------------------------------------------------------------------ review cameras (player height, lookbook names)
        // vignette -> camera offset from its centre (metres) and look height
        static readonly (string cam, string vignette, Vector3 offset, float lookY)[] Views =
        {
            ("cam_sd_relay_frontage", "Relay Works frontage: parts stock", new Vector3(4.2f, 1.62f, 2.8f), 0.9f),
            ("cam_sd_air_water", "Air + Water frontage: water point", new Vector3(4.6f, 1.62f, -1.2f), 0.9f),
            ("cam_sd_tool_exchange", "Tool Exchange frontage: trolley", new Vector3(4.0f, 1.62f, -2.8f), 0.9f),
            ("cam_sd_salvage_frontage", "Salvage frontage: wheels", new Vector3(3.6f, 1.62f, -2.2f), 0.7f),
            ("cam_sd_finery", "Finery frontage: door planters and bench", new Vector3(-4.6f, 1.62f, 0.4f), 0.8f),
            ("cam_sd_field_supply", "Field Supply frontage: stock", new Vector3(-4.0f, 1.62f, 2.6f), 0.8f),
            ("cam_sd_repairs_tea", "Repairs frontage: tea break", new Vector3(-3.6f, 1.62f, -1.8f), 0.7f),
            ("cam_sd_thread_hide", "Thread + Hide frontage: sewing stool", new Vector3(-3.8f, 1.62f, -2.2f), 0.7f),
            ("cam_sd_bg_stock", "Basic General: stock by the east cheek", new Vector3(3.2f, 1.62f, -2.6f), 0.8f),
            ("cam_sd_bg_refuse", "Basic General: refuse point", new Vector3(-3.4f, 1.62f, -2.4f), 0.7f),
            ("cam_sd_hill_benches", "Hill foot benches", new Vector3(-5.0f, 1.62f, 1.0f), 0.6f),
            ("cam_sd_salvage_yard", "Salvage yard: scrap skip", new Vector3(-1.6f, 1.62f, -4.4f), 0.7f),
            ("cam_sd_east_yard", "East yard: generator and fuel", new Vector3(-3.6f, 1.62f, 3.4f), 0.7f),
            ("cam_sd_market_rest", "Market edge: rest spot", new Vector3(3.8f, 1.62f, 2.6f), 0.7f),
            ("cam_sd_west_gate", "West Gate approach: caravan goods waiting", new Vector3(-2.4f, 1.62f, -4.0f), 0.7f),
            ("cam_sd_hall_refuse", "Vanguard Hall: refuse point", new Vector3(3.6f, 1.62f, 2.2f), 0.7f),
            ("cam_sd_hydroponics", "Hydroponics door: planters", new Vector3(3.4f, 1.62f, -2.4f), 0.5f),
            ("cam_sd_finery_yard", "Finery yard: refuse point", new Vector3(3.2f, 1.62f, 2.4f), 0.6f),
            ("cam_sd_repairs_cart", "Repairs frontage: cart under repair", new Vector3(-4.2f, 1.62f, -1.2f), 0.7f),
            ("cam_sd_hill_stairs", "Hill stair feet: planted pots", new Vector3(13.5f, 1.62f, -9.5f), 0.6f),
        };

        static void AddReviewCameras(UnityEngine.SceneManagement.Scene scene, JObject layout)
        {
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            var centres = layout["placements"].GroupBy(p => (string)p["vignette"]).ToDictionary(
                g => g.Key, g => new Vector3(g.Average(p => (float)p["pos"][0]), g.Average(p => (float)p["pos"][1]), g.Average(p => (float)p["pos"][2])));
            foreach (var (cam, vig, offset, lookY) in Views)
            {
                if (!centres.TryGetValue(vig, out var c)) continue;
                var pos = new Vector3(c.x + offset.x, c.y + offset.y, c.z + offset.z);
                var target = new Vector3(c.x, c.y + lookY * .5f, c.z);
                var go = new GameObject(cam); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var k = go.AddComponent<Camera>(); k.enabled = false; k.fieldOfView = 60; k.nearClipPlane = .05f;
            }
            // two wide avenue views at player height (the same framing is used before and after)
            foreach (var (cam, pos, target) in new[] { ("cam_sd_avenue_west", new Vector3(-11f, 1.62f, -24f), new Vector3(-16f, 0.8f, 6f)),
                                                       ("cam_sd_avenue_east", new Vector3(11f, 1.62f, 24f), new Vector3(16f, 0.8f, -6f)) })
            {
                var go = new GameObject(cam); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var k = go.AddComponent<Camera>(); k.enabled = false; k.fieldOfView = 60; k.nearClipPlane = .05f;
            }
        }

        /// Editor capture of every review camera (added in memory if the scene has none; nothing is saved).
        public static string CaptureViews(string outDir)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var camRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (!camRoot) AddReviewCameras(scene, JObject.Parse(File.ReadAllText(LayoutPath)));
            camRoot = scene.GetRootGameObjects().First(g => g.name == CamRootName);
            var views = camRoot.GetComponentsInChildren<Camera>(true).Select(c => (c.name, c.transform.position, c.transform.position + c.transform.forward * 5f, c.fieldOfView)).ToList();
            return string.Join(",", StreetDressingPass.Capture(outDir, views));
        }

        /// Adds the review cameras to the saved scene without installing anything (for matched "before" captures).
        public static string CamerasOnly()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = JObject.Parse(File.ReadAllText(LayoutPath));
            AddReviewCameras(scene, layout);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return "review cameras: " + scene.GetRootGameObjects().First(g => g.name == CamRootName).transform.childCount;
        }

        // ------------------------------------------------------------------ verify
        [MenuItem("Athen Hill/Street dressing/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = JObject.Parse(File.ReadAllText(LayoutPath));
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == StreetDressingPass.RootName);
            r["installed"] = root != null;
            if (root)
            {
                var inst = root.GetComponentsInChildren<LODGroup>(true);
                r["instances"] = inst.Length;
                r["vignettes"] = root.transform.childCount;
                r["prefabLinked"] = inst.Count(g => PrefabUtility.IsPartOfPrefabInstance(g.gameObject));
                r["missingMaterials"] = root.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(m => !m));
                long lod0 = 0;
                foreach (var g in inst)
                    foreach (var rr in g.GetLODs()[0].renderers)
                        if (rr && rr.TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh)
                            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) lod0 += mf.sharedMesh.GetIndexCount(s) / 3;
                r["lod0Triangles"] = lod0;
                r["colliders"] = root.GetComponentsInChildren<Collider>(true).Length;
                r["sitPoints"] = root.GetComponentsInChildren<Transform>(true).Count(t => t.name == "NPC sit point");
            }
            r["retiredStillActive"] = Matching(scene, layout["retirePrefixes"].Select(x => (string)x)).Where(t => t.gameObject.activeSelf).Select(PathOf).ToArray();
            r["hiddenRenderersStillOn"] = layout["hideRenderers"].Select(x => (string)x).Where(p =>
            {
                var t = All(scene).FirstOrDefault(x => PathOf(x) == p); var mr = t ? t.GetComponent<MeshRenderer>() : null; return mr && mr.enabled;
            }).ToArray();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            r["reviewCameras"] = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName)?.transform.childCount ?? 0;
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }
    }
}
