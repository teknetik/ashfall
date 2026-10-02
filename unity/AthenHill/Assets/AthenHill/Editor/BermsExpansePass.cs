using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>
    /// 2 October 2026: Outer Berms expansion. Carl: "expand the outer berms, push back the mountains if required ...
    /// spread [loot] and enemies out a little, make them more challenging, use meshy to create 2 more enemies a bit further
    /// out that use ranged weapons". Sources and run order: art/berms_expanse_20261002/README.md.
    /// Batch: -executeMethod AthenHill.Editor.BermsExpansePass.RunBatch -nographics -quit --steps survey|...
    /// </summary>
    public static class BermsExpansePass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        public const string ArtSrc = "../../art/berms_expanse_20261002/";
        public const string Evidence = "../evidence/berms-expanse/20261002/";
        public const string GroundPath = "Outer Berms/Berms ground";

        // survey window (world metres): the old Berms footprint (x -104..-60, z -54..48) and everything the expansion may reach
        const float X0 = -290f, X1 = -40f, Z0 = -180f, Z1 = 170f;
        static bool InWindow(Bounds b) => b.max.x >= X0 && b.min.x <= X1 && b.max.z >= Z0 && b.min.z <= Z1;
        static bool InWindow(Vector3 p) => p.x >= X0 && p.x <= X1 && p.z >= Z0 && p.z <= Z1;
        public static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] V(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };

        // ------------------------------------------------------------------ survey (read-only)
        public static string Survey()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Physics.SyncTransforms();
            var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).ToList();
            var groundT = all.First(t => PathOf(t) == GroundPath);
            var groundMf = groundT.GetComponent<MeshFilter>(); var groundCol = groundT.GetComponent<MeshCollider>();
            var mesh = groundMf.sharedMesh; var verts = mesh.vertices; var cols = mesh.colors;
            var gv = new List<float[]>(verts.Length);
            for (int i = 0; i < verts.Length; i++)
            {
                var w = groundT.TransformPoint(verts[i]); var c = cols.Length == verts.Length ? cols[i] : Color.clear;
                gv.Add(new[] { (float)Math.Round(w.x, 4), (float)Math.Round(w.y, 5), (float)Math.Round(w.z, 4), c.r, c.g, c.b, c.a });
            }
            var gr = groundT.GetComponent<MeshRenderer>();
            var ground = new
            {
                path = GroundPath, position = V(groundT.position), rotation = V(groundT.eulerAngles), scale = V(groundT.lossyScale),
                mesh = mesh.name, meshAsset = AssetDatabase.GetAssetPath(mesh), colliderSameMesh = groundCol && groundCol.sharedMesh == mesh,
                vertexCount = verts.Length, triangles = mesh.triangles.Length / 3, indexFormat = mesh.indexFormat.ToString(),
                uvChannels = Enumerable.Range(0, 4).Where(k => mesh.HasVertexAttribute((UnityEngine.Rendering.VertexAttribute)((int)UnityEngine.Rendering.VertexAttribute.TexCoord0 + k))).ToArray(),
                material = gr.sharedMaterials.Select(m => m ? AssetDatabase.GetAssetPath(m) : null).ToArray(),
                shadows = gr.shadowCastingMode.ToString(), layer = groundT.gameObject.layer,
                staticFlags = GameObjectUtility.GetStaticEditorFlags(groundT.gameObject).ToString(),
                bounds = new { min = V(gr.bounds.min), max = V(gr.bounds.max) },
                vertices = gv,
            };
            var colliders = new List<object>();
            foreach (var c in all.SelectMany(t => t.GetComponents<Collider>()))
            {
                if (!c.gameObject.activeInHierarchy || !c.enabled || c == groundCol) continue;
                var b = c.bounds; if (!InWindow(b)) continue;
                colliders.Add(new { path = PathOf(c.transform), type = c.GetType().Name, trigger = c.isTrigger, layer = c.gameObject.layer, min = V(b.min), max = V(b.max) });
            }
            var markers = new List<object>();
            void Mark(string kind, Transform t, object extra = null) { if (t && InWindow(t.position)) markers.Add(new { kind, path = PathOf(t), pos = V(t.position), yaw = t.eulerAngles.y, active = t.gameObject.activeInHierarchy, extra }); }
            foreach (var n in UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Include)) Mark("npc", n.transform);
            foreach (var w in UnityEngine.Object.FindObjectsByType<WorldInteractable>(FindObjectsInactive.Include)) Mark("interactable", w.transform, new { w.prompt, w.range });
            foreach (var r in UnityEngine.Object.FindObjectsByType<RangeTarget>(FindObjectsInactive.Include)) Mark("target", r.transform);
            foreach (var e in UnityEngine.Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Include))
            {
                Mark("encounter", e.transform, new { e.displayName, e.respawnSeconds, e.respawnClearance, e.awaySeconds });
                foreach (var s in e.spawns) if (s.point) Mark("spawn", s.point, new { prefab = s.prefab ? s.prefab.name : null });
            }
            foreach (var s in UnityEngine.Object.FindObjectsByType<SalvageNode>(FindObjectsInactive.Include)) Mark("salvage", s.transform, new { s.displayName });
            var landmarks = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Landmarks");
            if (landmarks) foreach (Transform t in landmarks.transform) Mark("landmark", t);
            foreach (var t in all.Where(t => t.name.Contains("Respawn") || t.name.StartsWith("Boundary") || t.name.Contains("Gate marker"))) Mark("misc", t);
            var lights = all.Select(t => t.GetComponent<Light>()).Where(l => l && InWindow(l.transform.position))
                .Select(l => new { path = PathOf(l.transform), pos = V(l.transform.position), type = l.type.ToString(), l.range, l.intensity, shadows = l.shadows.ToString(), active = l.gameObject.activeInHierarchy }).ToArray();
            var cams = all.Select(t => t.GetComponent<Camera>()).Where(c => c && InWindow(c.transform.position))
                .Select(c => new { name = c.name, path = PathOf(c.transform), pos = V(c.transform.position), fwd = V(c.transform.forward), c.fieldOfView }).ToArray();
            var renderers = new List<object>();
            foreach (var r in all.Select(t => t.GetComponent<Renderer>()).Where(r => r && r.gameObject.activeInHierarchy && r.enabled && InWindow(r.bounds)))
            {
                if (r is ParticleSystemRenderer || r is LineRenderer || r is TrailRenderer) continue;
                var pr = PrefabUtility.GetNearestPrefabInstanceRoot(r.gameObject);
                renderers.Add(new { path = PathOf(r.transform), min = V(r.bounds.min), max = V(r.bounds.max), prefab = pr ? PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(pr) : null });
            }
            var berms = scene.GetRootGameObjects().First(g => g.name == "Outer Berms").transform;
            var groups = berms.Cast<Transform>().Select(t => new { name = t.name, active = t.gameObject.activeSelf, children = t.childCount, renderers = t.GetComponentsInChildren<Renderer>(true).Length }).ToArray();
            var comps = berms.GetComponents<Component>().Select(c => c.GetType().Name).ToArray();
            var fa = UnityEngine.Object.FindAnyObjectByType<FootstepAudio>();
            var tut = UnityEngine.Object.FindAnyObjectByType<BermsTutorial>();
            var prefabs = new Dictionary<string, object>();
            foreach (var p in Directory.GetFiles("Assets/AthenHill/Prefabs/OuterBerms", "*.prefab"))
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(p); var d = go.GetComponent<FeralDroid>(); var h = go.GetComponent<Health>();
                if (!d) continue;
                prefabs[Path.GetFileNameWithoutExtension(p)] = new { kind = d.kind.ToString(), health = h ? h.max : 0, d.wanderSpeed, d.chaseSpeed, d.aggroRadius, d.leashRadius, d.attackRange, d.windupSeconds, d.recoverSeconds, d.strikeDamage, d.repairPerSecond, d.staggerThreshold, d.slamEvery, d.idleThrottleDistance, loot = go.GetComponent<LootSource>() ? go.GetComponent<LootSource>().lootTableId : null };
            }
            var result = new
            {
                scene = ScenePath, utc = DateTime.UtcNow.ToString("O"), window = new[] { X0, X1, Z0, Z1 },
                ground, colliders, markers, lights, cameras = cams, renderers, bermsGroups = groups, bermsComponents = comps,
                footsteps = fa ? new { rect = new[] { fa.bermsRect.x, fa.bermsRect.y, fa.bermsRect.z, fa.bermsRect.w }, fa.bermsWidth, fa.bermsHeight, cells = fa.bermsSurfaces.Length } : null,
                tutorial = tut ? new { tut.startRadius, tut.showObjectiveWestOf, tut.depotRespawnSeconds, firstContact = tut.firstContact ? tut.firstContact.name : null, depot = tut.depot ? tut.depot.name : null } : null,
                prefabs,
                roots = scene.GetRootGameObjects().Select(g => g.name).ToArray(),
            };
            Directory.CreateDirectory(ArtSrc);
            File.WriteAllText(ArtSrc + "survey.json", JsonConvert.SerializeObject(result));
            return $"survey: {gv.Count} ground vertices, {colliders.Count} colliders, {markers.Count} markers, {renderers.Count} renderers";
        }

        // ------------------------------------------------------------------ prefab survey (read-only): kit footprints for layout
        public static string PrefabSurvey()
        {
            var dirs = new[] { "StreetDressing", "OuterBermsDepot", "TrainingRange", "WestGate", "PerimeterWalls", "Rooftops", "Salvage", "OuterBerms", "Hydroponics", "NightLife", "WallFootDrifts" };
            var files = dirs.SelectMany(d => Directory.GetFiles("Assets/AthenHill/Prefabs/" + d, "*.prefab")).Concat(new[] { "Assets/AthenHill/Prefabs/KaraveenTruck.prefab", "Assets/AthenHill/Prefabs/WardMiningDroid.prefab" });
            var outp = new Dictionary<string, object>();
            foreach (var f in files)
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(f); if (!go) continue;
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(go); inst.transform.position = Vector3.zero; inst.transform.rotation = Quaternion.identity;
                var rs = inst.GetComponentsInChildren<Renderer>().Where(r => r.enabled && !(r is ParticleSystemRenderer) && !(r is LineRenderer) && !(r is TrailRenderer)).ToArray();
                if (rs.Length == 0) { UnityEngine.Object.DestroyImmediate(inst); continue; }
                var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                long tris = 0; foreach (var mf in inst.GetComponentsInChildren<MeshFilter>()) if (mf.sharedMesh) tris += mf.sharedMesh.triangles.Length / 3;
                outp[f.Replace("Assets/AthenHill/Prefabs/", "")] = new { size = V(b.size), center = V(b.center), min = V(b.min), colliders = inst.GetComponentsInChildren<Collider>().Length, lod = inst.GetComponentsInChildren<LODGroup>().Length, lights = inst.GetComponentsInChildren<Light>().Length, tris };
                UnityEngine.Object.DestroyImmediate(inst);
            }
            Directory.CreateDirectory(ArtSrc);
            File.WriteAllText(ArtSrc + "prefabs.json", JsonConvert.SerializeObject(outp, Formatting.Indented));
            return $"prefab survey: {outp.Count} prefabs";
        }

        /// Editor captures of review cameras (graphics run, at most six per run): capture:&lt;out dir&gt;:cam_a+cam_b
        public static string Capture(string outDir, string views)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var camsByName = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true)).GroupBy(c => c.name).ToDictionary(g => g.Key, g => g.First());
            var list = new List<(string name, Vector3 pos, Vector3 target, float fov)>();
            foreach (var n in views.Split('+'))
            {
                if (!camsByName.TryGetValue(n, out var c)) throw new Exception("camera not found: " + n);
                list.Add((n, c.transform.position, c.transform.position + c.transform.forward * 5f, c.fieldOfView));
            }
            if (list.Count > 6) throw new Exception($"{list.Count} views in one run; capture at most 6 per Unity run");
            return string.Join(",", StreetDressingPass.Capture(outDir, list));
        }

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 ? args[i + 1].Split(',') : new[] { "survey" };
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "survey" => Survey(),
                        "prefabs" => PrefabSurvey(),
                        "loot" => BermsExpanseInstall.Loot(),
                        "droids" => BermsExpanseInstall.Droids(),
                        "install" => BermsExpanseInstall.Install(),
                        "verify" => BermsExpanseInstall.Verify(),
                        "capture" => Capture(parts[1], parts[2]),
                        "abbuild" => BermsExpanseInstall.AbBuild(parts[1]),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("BermsExpansePass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
