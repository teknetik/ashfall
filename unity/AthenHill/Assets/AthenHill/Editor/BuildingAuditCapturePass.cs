using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>Authored diagnostic cameras only; never edits geometry, materials, colliders or existing cameras.</summary>
    public static class BuildingAuditCapturePass
    {
        const string CameraRoot = "Quality building audit cameras";
        const string Evidence = "../evidence/quality/20260908/building-captures";
        static string PlanPath => Path.Combine(Evidence, "building-capture-plan.json");
        static string FullPath(Transform t) => t.parent ? FullPath(t.parent) + "/" + t.name : t.name;
        static float[] V(Vector3 v) => new[] { v.x, v.y, v.z };
        static Vector3 V(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static string Hash(string path)
        {
            if (!File.Exists(path)) return null;
            using var stream = File.OpenRead(path);
            using var hash = SHA256.Create();
            return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
        static Scene CheckedScene()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play Mode before camera authoring/export.");
            var scene = SceneManager.GetActiveScene();
            if (scene.path != ImportBaseline.ScenePath) throw new InvalidOperationException("Open the saved AthenHill scene first.");
            return scene;
        }
        static Transform[] Transforms(Scene scene) => scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).ToArray();
        static Transform Unique(Transform[] all, string path)
        {
            var found = all.Where(t => FullPath(t) == path).ToArray();
            if (found.Length != 1) throw new InvalidOperationException($"Expected exactly one '{path}'; found {found.Length}. Update the capture plan after intentional replacements.");
            return found[0];
        }

        [MenuItem("Athen Hill/Quality audit/Prepare building capture cameras")]
        public static void Prepare()
        {
            var scene = CheckedScene();
            var plan = JObject.Parse(File.ReadAllText(PlanPath));
            var all = Transforms(scene);
            // Validate every source selector and camera name before making any scene change.
            var viewNames = new HashSet<string>();
            foreach (var building in plan["buildings"])
            {
                Unique(all, (string)building["primaryPath"]);
                foreach (var source in building["sourceInstances"]) Unique(all, (string)source["path"]);
                foreach (var view in building["views"])
                {
                    var name = (string)view["name"];
                    if (!viewNames.Add(name)) throw new InvalidOperationException("Duplicate planned camera " + name);
                    var matches = all.Where(t => t.name == name).ToArray();
                    if (matches.Length > 1 || (matches.Length == 1 && (!matches[0].GetComponent<Camera>() || FullPath(matches[0]) != CameraRoot + "/" + name)))
                        throw new InvalidOperationException("Existing camera/object name conflicts: " + name);
                }
            }
            var roots = scene.GetRootGameObjects().Where(g => g.name == CameraRoot).ToArray();
            if (roots.Length > 1) throw new InvalidOperationException("Duplicate audit camera root.");
            var root = roots.FirstOrDefault();
            int added = 0;
            if (!root)
            {
                root = new GameObject(CameraRoot);
                Undo.RegisterCreatedObjectUndo(root, "Prepare building audit cameras");
            }
            if (!root.activeInHierarchy) throw new InvalidOperationException("Enable the existing audit camera root before capture.");
            foreach (var view in plan["buildings"].SelectMany(b => b["views"]))
            {
                var name = (string)view["name"];
                if (all.Any(t => t.name == name)) continue; // Preserve adjusted camera poses on repeat.
                var camera = ImportBaseline.Camera(name, V(view["position"]), V(view["target"]), (float)view["fov"]);
                camera.transform.SetParent(root.transform, true);
                Undo.RegisterCreatedObjectUndo(camera.gameObject, "Prepare building audit cameras");
                added++;
            }
            if (added > 0) EditorSceneManager.MarkSceneDirty(scene);
            Debug.Log($"Prepared {added} new building audit cameras; existing camera poses preserved. Review framing, save normally, then ExportSavedManifest. No capture, build, source visibility or chunk changes performed.");
        }

        static Bounds WorldBounds(Renderer r, Mesh mesh)
        {
            if (r is SkinnedMeshRenderer) return r.bounds;
            var local = mesh.bounds;
            var matrix = r.localToWorldMatrix;
            var first = matrix.MultiplyPoint3x4(local.min);
            var result = new Bounds(first, Vector3.zero);
            for (int i = 0; i < 8; i++)
                result.Encapsulate(matrix.MultiplyPoint3x4(local.center + Vector3.Scale(local.extents,
                    new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1))));
            return result;
        }

        [MenuItem("Athen Hill/Quality audit/Export saved building capture manifest")]
        public static void ExportSavedManifest()
        {
            var scene = CheckedScene();
            if (scene.isDirty) throw new InvalidOperationException("Save the reviewed scene first; the capture manifest must identify serialized camera poses and sources.");
            var plan = JObject.Parse(File.ReadAllText(PlanPath));
            var all = Transforms(scene);
            var exported = new List<object>();
            var hashCache = new Dictionary<string, string>();
            string AssetHash(string path)
            {
                if (!hashCache.TryGetValue(path, out var hash)) hashCache[path] = hash = Hash(path);
                return hash;
            }
            foreach (var building in plan["buildings"])
            {
                var sourceRows = new List<object>();
                foreach (var source in building["sourceInstances"])
                {
                    var t = Unique(all, (string)source["path"]);
                    var renderer = t.GetComponent<Renderer>();
                    var mesh = renderer is SkinnedMeshRenderer skin ? skin.sharedMesh : t.GetComponent<MeshFilter>()?.sharedMesh;
                    if (!renderer || !mesh || !t.gameObject.activeInHierarchy) throw new InvalidOperationException("Planned source is no longer an active renderer: " + FullPath(t));
                    var asset = AssetDatabase.GetAssetPath(mesh);
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mesh, out string guid, out long localId);
                    var bounds = WorldBounds(renderer, mesh);
                    long triangles = 0;
                    for (int s = 0; s < mesh.subMeshCount; s++)
                        if (mesh.GetTopology(s) == MeshTopology.Triangles) triangles += (long)mesh.GetIndexCount(s) / 3;
                    sourceRows.Add(new { path = FullPath(t), globalObjectId = GlobalObjectId.GetGlobalObjectIdSlow(renderer).ToString(),
                        mesh = mesh.name, asset, guid, localId, assetSha256 = AssetHash(asset), vertices = mesh.vertexCount, triangles,
                        position = V(t.position), rotationEuler = V(t.eulerAngles), lossyScale = V(t.lossyScale),
                        center = V(bounds.center), size = V(bounds.size), rendererEnabled = renderer.enabled,
                        sourceAssetChangedSincePlan = asset != (string)source["meshPath"],
                        materials = renderer.sharedMaterials.Select(m => m ? new { name = m.name, asset = AssetDatabase.GetAssetPath(m),
                            shader = m.shader ? m.shader.name : null, assetSha256 = AssetHash(AssetDatabase.GetAssetPath(m)) } : null).ToArray() });
                }
                var cameras = new List<object>();
                foreach (var proposal in building["views"])
                {
                    var name = (string)proposal["name"];
                    var t = Unique(all, CameraRoot + "/" + name);
                    var camera = t.GetComponent<Camera>();
                    if (!camera || camera.enabled || !t.gameObject.activeInHierarchy) throw new InvalidOperationException("Audit camera must be disabled on an active GameObject: " + name);
                    var q = t.rotation;
                    var overlaps = Physics.OverlapSphere(t.position, .12f, ~0, QueryTriggerInteraction.Ignore).Select(c => FullPath(c.transform)).OrderBy(s => s).ToArray();
                    var target = V(proposal["target"]);
                    var delta = target - t.position;
                    var hits = Physics.RaycastAll(t.position, delta.normalized, delta.magnitude, ~0, QueryTriggerInteraction.Ignore)
                        .OrderBy(h => h.distance).Select(h => new { path = FullPath(h.collider.transform), distance = h.distance }).ToArray();
                    cameras.Add(new { name, kind = (string)proposal["kind"], position = V(t.position), rotationEuler = V(t.eulerAngles),
                        rotationQuaternion = new[] { q.x, q.y, q.z, q.w }, forward = V(t.forward), fov = camera.fieldOfView,
                        aspect = camera.aspect, near = camera.nearClipPlane, far = camera.farClipPlane,
                        originalProposedTarget = V(V(proposal["target"])), plannedPosition = V(V(proposal["position"])),
                        overlaps, rayToOriginalProposedTarget = hits, reviewStatus = "unreviewed; collision diagnostics do not prove framing or visual coverage" });
                }
                exported.Add(new { id = (string)building["id"], name = (string)building["name"], primaryPath = (string)building["primaryPath"],
                    sourceInstances = sourceRows, views = cameras, visualReview = "pending" });
            }
            var output = new { schema = 1, exportedUtc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion,
                scene = scene.path, sceneSha256 = Hash(scene.path), sceneDirty = scene.isDirty, planSha256 = Hash(PlanPath),
                buildQualification = "Unbuilt manifest. Root must build this saved scene and attach actual build identity to native captures.",
                captureContract = plan["captureContract"], buildings = exported,
                architectureOutsidePrimaryBuildingSet = plan["architectureOutsidePrimaryBuildingSet"] };
            Directory.CreateDirectory(Evidence);
            var file = Path.Combine(Evidence, "saved-camera-manifest.json");
            File.WriteAllText(file, JsonConvert.SerializeObject(output, Formatting.Indented) + "\n");
            Debug.Log("Saved building capture manifest: " + Path.GetFullPath(file));
        }
    }
}
