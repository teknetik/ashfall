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
    /// 30 September 2026: read-only inventory of the saved scene for the street-dressing and courtyard-tree passes.
    /// Writes every renderer (path, active/enabled state, mesh, triangles, world bounds, prefab source, materials) and
    /// every scene root to JSON. Never saves the scene. Batch: -executeMethod AthenHill.Editor.StreetDressingAudit.DumpBatch
    /// --out &lt;file.json&gt;.
    /// </summary>
    public static class StreetDressingAudit
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";

        public static void DumpBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--out");
            var outPath = i >= 0 && i + 1 < args.Length ? args[i + 1] : "street-dressing-audit.json";
            try
            {
                Dump(outPath);
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                EditorApplication.Exit(1);
            }
        }

        [MenuItem("Athen Hill/Street dressing/Audit scene renderers (read-only)")]
        static void DumpMenu() => Dump("../evidence/street-dressing/20260930/audit.json");

        static void Dump(string outPath)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var rows = new List<object>();
            foreach (var root in scene.GetRootGameObjects())
            foreach (var r in root.GetComponentsInChildren<Renderer>(true))
            {
                var mesh = r is SkinnedMeshRenderer s ? s.sharedMesh : r.TryGetComponent<MeshFilter>(out var mf) ? mf.sharedMesh : null;
                long tris = 0;
                if (mesh != null)
                    for (int k = 0; k < mesh.subMeshCount; k++) tris += (long)mesh.GetIndexCount(k) / 3;
                var b = r.bounds;
                var prefabRoot = PrefabUtility.GetNearestPrefabInstanceRoot(r.gameObject);
                rows.Add(new
                {
                    path = PathOf(r.transform),
                    active = r.gameObject.activeInHierarchy,
                    enabled = r.enabled,
                    shadows = r.shadowCastingMode.ToString(),
                    mesh = mesh != null ? mesh.name : null,
                    meshAsset = mesh != null ? AssetDatabase.GetAssetPath(mesh) : null,
                    tris,
                    center = new[] { b.center.x, b.center.y, b.center.z },
                    size = new[] { b.size.x, b.size.y, b.size.z },
                    prefab = prefabRoot != null ? PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(prefabRoot) : null,
                    prefabRoot = prefabRoot != null ? PathOf(prefabRoot.transform) : null,
                    mats = r.sharedMaterials.Select(m => m != null ? m.name : null).ToArray(),
                    hasCollider = r.TryGetComponent<Collider>(out _),
                });
            }
            var roots = scene.GetRootGameObjects().Select(g => new
            {
                name = g.name,
                active = g.activeSelf,
                children = g.transform.childCount,
                pos = new[] { g.transform.position.x, g.transform.position.y, g.transform.position.z },
            }).ToArray();
            var colliders = new List<object>();
            foreach (var root in scene.GetRootGameObjects())
            foreach (var c in root.GetComponentsInChildren<Collider>(true))
            {
                if (!c.gameObject.activeInHierarchy || !c.enabled || c.isTrigger) continue;
                var b = c.bounds;
                colliders.Add(new
                {
                    path = PathOf(c.transform),
                    type = c.GetType().Name,
                    center = new[] { b.center.x, b.center.y, b.center.z },
                    size = new[] { b.size.x, b.size.y, b.size.z },
                    yaw = c.transform.eulerAngles.y,
                });
            }
            // actors, routes, landmarks and interaction markers (positions only)
            var markers = new List<object>();
            foreach (var root in scene.GetRootGameObjects())
            {
                var n = root.name;
                bool keep = n.EndsWith(" route") || n == "Landmarks" || n == "Colonists" || n.StartsWith("npc_") || n.Contains("interaction")
                            || n == "Hill visit area" || n == "Player" || n == "Mining droid route";
                if (!keep) continue;
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    markers.Add(new { path = PathOf(t), pos = new[] { t.position.x, t.position.y, t.position.z }, active = t.gameObject.activeInHierarchy });
            }
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outPath)));
            File.WriteAllText(outPath, JsonConvert.SerializeObject(new { scene = ScenePath, roots, renderers = rows, colliders, markers }, Formatting.Indented));
            Debug.Log($"StreetDressingAudit: {rows.Count} renderers -> {outPath}");
        }

        /// <summary>Trunk base of each courtyard tree: centroid/radius of LOD0 vertices within 0.6 m of the ground,
        /// plus the tree's colliders and LODGroup. Batch: -executeMethod AthenHill.Editor.StreetDressingAudit.TreeProbeBatch --out f.json</summary>
        public static void TreeProbeBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--out");
            var outPath = args[i + 1];
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var res = new List<object>();
            foreach (var g in scene.GetRootGameObjects())
            {
                if (!g.name.StartsWith("birch") && !g.name.StartsWith("maple") && !g.name.StartsWith("crimean")) continue;
                var bands = new List<object>();
                var mf = g.GetComponentsInChildren<MeshFilter>(true).FirstOrDefault(m => m.name.Contains("lod0"));
                if (mf != null)
                {
                    var vs = mf.sharedMesh.vertices.Select(v => mf.transform.TransformPoint(v)).ToArray();
                    foreach (var (y0, y1) in new[] { (-1f, .1f), (.1f, .3f), (.3f, .6f), (.6f, 1.2f), (1.2f, 2f) })
                    {
                        var band = vs.Where(v => v.y >= y0 && v.y < y1).ToArray();
                        if (band.Length == 0) continue;
                        var c = new Vector3(band.Average(v => v.x), band.Average(v => v.y), band.Average(v => v.z));
                        float r = band.Max(v => new Vector2(v.x - c.x, v.z - c.z).magnitude);
                        float rMed = band.Select(v => new Vector2(v.x - c.x, v.z - c.z).magnitude).OrderBy(x => x).ElementAt(band.Length / 2);
                        bands.Add(new { y0, y1, n = band.Length, c = new[] { c.x, c.y, c.z }, rMax = r, rMedian = rMed, minY = band.Min(v => v.y) });
                    }
                }
                res.Add(new
                {
                    name = g.name,
                    pos = new[] { g.transform.position.x, g.transform.position.y, g.transform.position.z },
                    scale = new[] { g.transform.lossyScale.x, g.transform.lossyScale.y, g.transform.lossyScale.z },
                    prefab = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(g),
                    lodGroup = g.GetComponentInChildren<LODGroup>(true) != null,
                    colliders = g.GetComponentsInChildren<Collider>(true).Select(c => c.GetType().Name + " " + c.bounds.center + " " + c.bounds.size).ToArray(),
                    components = g.GetComponents<Component>().Select(c => c.GetType().Name).ToArray(),
                    bands,
                });
            }
            File.WriteAllText(outPath, JsonConvert.SerializeObject(res, Formatting.Indented));
            EditorApplication.Exit(0);
        }

        static string PathOf(Transform t)
        {
            var parts = new List<string>();
            for (; t != null; t = t.parent) parts.Add(t.name);
            parts.Reverse();
            return string.Join("/", parts);
        }
    }
}
