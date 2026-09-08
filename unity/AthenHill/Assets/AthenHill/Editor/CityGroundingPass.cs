using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    public static class CityGroundingPass
    {
        const string Evidence = "../evidence/grounding/20260908";
        static float[] V(Vector3 v) => new[] { v.x, v.y, v.z };
        static Transform[] All() => UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include);
        static readonly List<Collider> surfaceProbes = new List<Collider>();
        static readonly string[] Cameras = { "cam_grounding_stairs", "cam_grounding_bench", "cam_grounding_hill_bench", "cam_grounding_shop_back", "cam_grounding_shop_side", "cam_grounding_general_back", "cam_grounding_hall_back", "cam_ring_front", "cam_hill", "cam_avenue", "cam_gate" };

        // Reuse saved authored geometry; retain the ordinary editable scene and prefabs.
        [MenuItem("Athen Hill/Repairs/Ground props and extend foundations")]
        public static void Apply()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play first.");
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            Directory.CreateDirectory(Evidence);
            string gameplay = Gameplay();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            chunks.ShowSources(true);
            var changes = new List<object>();
            AddSurfaceProbes();
            try
            {
                foreach (var stone in All().Where(t => t.name == "Hill root stone" && t.gameObject.activeInHierarchy))
                {
                    var renderer = stone.GetComponent<Renderer>();
                    var before = stone.position;
                    // Embed the rounded underside slightly so its visible edge contacts the tread/soil.
                    stone.position += Vector3.up * (Ground(renderer.bounds.center) - .035f - renderer.bounds.min.y);
                    Record(stone);
                    changes.Add(new { stone.name, before = V(before), after = V(stone.position), gap = renderer.bounds.min.y - Ground(renderer.bounds.center) });
                }
                var legs = All().Where(t => t.name == "Plaza bench leg" && t.gameObject.activeInHierarchy).ToArray();
                foreach (var seat in All().Where(t => t.name == "Plaza bench seat" && t.gameObject.activeInHierarchy))
                {
                    var pair = legs.Where(t => Mathf.Abs(t.position.z - seat.position.z) < .01f && Mathf.Abs(t.position.x - seat.position.x) < 1).ToArray();
                    if (pair.Length != 2) throw new Exception("Expected two legs per plaza bench.");
                    var shifts = pair.Select(t => Ground(t.GetComponent<Renderer>().bounds.center) - .005f - t.GetComponent<Renderer>().bounds.min.y).ToArray();
                    if (Mathf.Abs(shifts[0] - shifts[1]) > .015f) throw new Exception("Bench feet need a level surface.");
                    var before = seat.position;
                    foreach (var part in pair.Concat(new[] { seat })) { part.position += Vector3.up * shifts.Max(); Record(part); }
                    changes.Add(new { seat.name, before = V(before), after = V(seat.position), feet = pair.Select(t => t.GetComponent<Renderer>().bounds.min.y - Ground(t.position)).ToArray() });
                }
            }
            finally { RemoveSurfaceProbes(); }

            var foundations = new List<object>();
            var world = GameObject.Find("AuthoredWorld").GetComponentsInChildren<Transform>(true);
            foreach (var building in GameObject.Find("Post-war salvage").transform.Cast<Transform>().Where(t => t.gameObject.activeInHierarchy && t.name.EndsWith(" repaired")))
            {
                string prefix = building.name.StartsWith("BLD_shop_") ? building.name.Replace(" repaired", "")
                    : building.name == "Basic General repaired" ? "BLD_general" : building.name == "Vanguard Hall repaired" ? "BLD_hall" : null;
                if (prefix == null) continue;
                string baseName = prefix + (prefix == "BLD_hall" ? "_plinth" : "_porch");
                var slab = world.Single(t => t.name == baseName);
                var renderer = slab.GetComponent<Renderer>();
                var before = renderer.bounds;
                var shell = building.Find("Meshy visual").GetComponent<Renderer>().bounds;
                var min = Vector3.Min(before.min, shell.min - new Vector3(.08f, 0, .08f));
                var max = Vector3.Max(before.max, shell.max + new Vector3(.08f, 0, .08f));
                // The entrance and its step keep their original edge and top elevation.
                if (prefix.StartsWith("BLD_shop_"))
                {
                    if (building.position.x > 0) min.x = before.min.x; else max.x = before.max.x;
                }
                else max.z = before.max.z;
                min.y = -.08f; max.y = before.max.y;
                var target = new Bounds((min + max) * .5f, max - min);
                Fit(renderer, target);
                var proxy = world.Single(t => t.name == "COL_" + baseName);
                Fit(proxy.GetComponent<BoxCollider>(), target);
                // The extended slab includes the old small interior tile. Avoid coplanar top faces.
                var interior = world.FirstOrDefault(t => t.name == prefix + "_interior_floor");
                if (interior) { interior.GetComponent<Renderer>().enabled = false; Record(interior.GetComponent<Renderer>()); }
                foundations.Add(new { building = building.name, foundation = baseName, beforeMin = V(before.min), beforeMax = V(before.max), min = V(target.min), max = V(target.max), shellMin = V(shell.min), shellMax = V(shell.max) });
            }
            if (foundations.Count != 10) throw new Exception("Expected foundations for eight shops, Basic General and Vanguard Hall.");
            VerifyPortal();
            AddCameras();
            StaticRenderChunksEditor.Rebuild(chunks);
            if (gameplay != Gameplay()) throw new Exception("Gameplay roots or routes changed during grounding repairs.");
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            File.WriteAllText(Evidence + "/repairs.json", JsonConvert.SerializeObject(new { gameplayPreserved = true, props = changes, foundations, portal = "Accepted 12,009-triangle Meshy model present at south Ring Gate. North Lattice Jack is a separate landmark." }, Formatting.Indented));
            Capture();
        }

        static void Record(UnityEngine.Object obj)
        {
            EditorUtility.SetDirty(obj);
            if (PrefabUtility.IsPartOfPrefabInstance(obj)) PrefabUtility.RecordPrefabInstancePropertyModifications(obj);
        }
        static string Gameplay() => DistrictCityPass.GameplaySignature() + JsonConvert.SerializeObject(new {
            walkers = UnityEngine.Object.FindObjectsByType<AmbientWalker>().OrderBy(w => w.name).Select(w => new { w.name, position = V(w.transform.position), w.speed, w.phase, waypoints = w.waypoints.Select(t => V(t.position)) }),
            ring = V(UnityEngine.Object.FindAnyObjectByType<GameSession>().ringPoint.position),
            lattice = V(UnityEngine.Object.FindAnyObjectByType<GameSession>().latticePoint.position)
        });
        static void Fit(Renderer renderer, Bounds target)
        {
            var size = renderer.bounds.size;
            renderer.transform.localScale = Vector3.Scale(renderer.transform.localScale, new Vector3(target.size.x / size.x, target.size.y / size.y, target.size.z / size.z));
            renderer.transform.position += target.center - renderer.bounds.center;
            Record(renderer.transform);
        }
        static void Fit(BoxCollider collider, Bounds target)
        {
            // Collision proxies use identity-aligned world axes in the imported city.
            if (Quaternion.Angle(collider.transform.rotation, Quaternion.identity) > .01f) throw new Exception("Unexpected rotated foundation proxy.");
            collider.center = collider.transform.InverseTransformPoint(target.center);
            var scale = collider.transform.lossyScale;
            collider.size = new Vector3(target.size.x / scale.x, target.size.y / scale.y, target.size.z / scale.z);
            Record(collider);
        }
        static void AddSurfaceProbes()
        {
            // The broad gameplay hill collider omits the mound and coping; sample visible surfaces too.
            var world = GameObject.Find("AuthoredWorld");
            foreach (var f in world.GetComponentsInChildren<MeshFilter>().Where(f => f.name.StartsWith("ENV_hill_") && f.GetComponent<Renderer>() && f.GetComponent<Renderer>().enabled))
            {
                var c = f.gameObject.AddComponent<MeshCollider>(); c.sharedMesh = f.sharedMesh; surfaceProbes.Add(c);
            }
            Physics.SyncTransforms();
        }
        static void RemoveSurfaceProbes()
        {
            foreach (var c in surfaceProbes) UnityEngine.Object.DestroyImmediate(c);
            surfaceProbes.Clear(); Physics.SyncTransforms();
        }
        static float Ground(Vector3 p)
        {
            var hits = Physics.RaycastAll(new Vector3(p.x, 5, p.z), Vector3.down, 6, ~0, QueryTriggerInteraction.Ignore)
                .Where(h => h.normal.y > .65f && (h.collider.name == "COL_Ground" || h.collider.name.StartsWith("COL_ENV_hill_") || surfaceProbes.Contains(h.collider))).ToArray();
            if (hits.Length == 0) throw new Exception("No support under " + p);
            return hits.Max(h => h.point.y);
        }
        static void VerifyPortal()
        {
            var gate = GameObject.Find("Meshy Ring Gate");
            if (!gate || PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(gate) != "Assets/AthenHill/Prefabs/RingGate.prefab") throw new Exception("Accepted RingGate prefab is missing.");
            var visual = gate.transform.Find("Meshy ring gate visual");
            var filter = visual.GetComponent<MeshFilter>();
            if (!visual.gameObject.activeInHierarchy || !visual.GetComponent<Renderer>().enabled || filter.sharedMesh.triangles.Length / 3 != 12009) throw new Exception("Accepted portal geometry is not visible.");
            if (GameObject.Find("AuthoredWorld").GetComponentsInChildren<Transform>().Any(t => t.name.StartsWith("ENV_ring_") || t.name.StartsWith("PROP_ring_"))) throw new Exception("Legacy ring geometry is still active.");
            Physics.SyncTransforms();
            if (Physics.RaycastAll(new Vector3(0, 3.7f, gate.transform.position.z - 4), Vector3.forward, 8).Any(h => h.collider.transform.IsChildOf(gate.transform))) throw new Exception("Portal aperture is blocked.");
        }
        static void AddCameras()
        {
            DistrictCityPass.Camera("cam_grounding_stairs", new Vector3(12.8f, 2.2f, 5.5f), new Vector3(7.8f, .9f, .8f), 55);
            DistrictCityPass.Camera("cam_grounding_bench", new Vector3(13.4f, 1.25f, 9.5f), new Vector3(11.5f, .35f, 5.7f), 50);
            DistrictCityPass.Camera("cam_grounding_hill_bench", new Vector3(-1.1f, 2.5f, -2.4f), new Vector3(-3.4f, 1.65f, -5.8f), 52);
            DistrictCityPass.Camera("cam_grounding_shop_back", new Vector3(27.2f, 1.45f, -24.8f), new Vector3(23.1f, 1.9f, -18), 65);
            DistrictCityPass.Camera("cam_grounding_shop_side", new Vector3(21.5f, 1.45f, -26.2f), new Vector3(21.2f, 2.2f, -18), 67);
            DistrictCityPass.Camera("cam_grounding_general_back", new Vector3(13, 1.25f, 10.1f), new Vector3(8, 1.15f, 14.2f), 58);
            DistrictCityPass.Camera("cam_grounding_hall_back", new Vector3(-19, 1.55f, -41.4f), new Vector3(-10, 2.5f, -34), 64);
        }
        public static void Capture()
        {
            ShaderUtil.allowAsyncCompilation = false;
            Directory.CreateDirectory(Evidence + "/editor");
            foreach (var name in Cameras)
            {
                PortDiagnostics.Capture(name); PortDiagnostics.Capture(name);
                File.Copy("Captures/Fixed/" + name + ".png", Evidence + "/editor/" + name + ".png", true);
            }
        }
        public static void Build()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            VerifyPortal();
            LinuxBuild.Development(); File.Copy("Captures/linux-build.json", Evidence + "/development-build.json", true);
            LinuxBuild.Release(); File.Copy("Captures/linux-build.json", Evidence + "/release-build.json", true);
        }
        public static void Survey()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            Directory.CreateDirectory(Evidence);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            chunks.ShowSources(true);
            Physics.SyncTransforms();
            var renderers = UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include);
            File.WriteAllText(Evidence + "/survey.json", JsonConvert.SerializeObject(new {
                roots = chunks.sourceRoots.Select(t => t.name),
                renderers = renderers.Where(r => r.name.Contains("stone") || r.name.Contains("bench") || r.name.Contains("ring") || r.name.Contains("Ring") || r.name.Contains("porch") || r.name.Contains("plinth") || r.transform.root.name == "Post-war salvage").Select(r => new {
                    r.name, parent = r.transform.parent ? r.transform.parent.name : null, root = r.transform.root.name,
                    active = r.gameObject.activeInHierarchy, r.enabled, position = V(r.transform.position), min = V(r.bounds.min), max = V(r.bounds.max),
                    mesh = AssetDatabase.GetAssetPath(r.GetComponent<MeshFilter>().sharedMesh),
                    hits = Physics.RaycastAll(r.bounds.center + Vector3.up * 20, Vector3.down, 50, ~0, QueryTriggerInteraction.Ignore).OrderBy(h => h.point.y).Select(h => new { h.collider.name, p = V(h.point), n = V(h.normal) })
                }),
                colliders = UnityEngine.Object.FindObjectsByType<Collider>().Select(c => new { c.name, min = V(c.bounds.min), max = V(c.bounds.max) })
            }, Formatting.Indented));
            chunks.ShowSources(false);
            ShaderUtil.allowAsyncCompilation = false;
            foreach (var name in new[] { "cam_ring_front", "cam_hill" })
            {
                PortDiagnostics.Capture(name); PortDiagnostics.Capture(name);
                File.Copy("Captures/Fixed/" + name + ".png", Evidence + "/before-" + name + ".png", true);
            }
        }
    }
}
