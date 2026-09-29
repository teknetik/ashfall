using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// Read-only geometry cost report for the saved city scene: which active renderers submit the most
    /// triangles, whether they have LODs, and whether they cast shadows (shadow cascades resubmit them).
    public static class SceneCostAudit
    {
        [MenuItem("Athen Hill/Rendering/Write scene cost audit")]
        public static void Write() => Write("../evidence/rendering/20260929/scene-cost-audit.json");

        public static void WriteBatch()
        {
            var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, "--audit-out");
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            Write(i >= 0 && i + 1 < args.Length ? args[i + 1] : "../evidence/rendering/20260929/scene-cost-audit.json");
            EditorApplication.Exit(0);
        }

        static void Write(string path)
        {
            var rows = new List<Row>();
            var lodMembers = new HashSet<Renderer>();
            var lodCull = new Dictionary<Renderer, string>();
            foreach (var group in UnityEngine.Object.FindObjectsByType<LODGroup>(FindObjectsInactive.Exclude))
            {
                var lods = group.GetLODs();
                for (int l = 0; l < lods.Length; l++) foreach (var r in lods[l].renderers) if (r) { lodMembers.Add(r); lodCull[r] = "LOD" + l + "/" + lods.Length; }
            }
            foreach (var r in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude))
            {
                if (!r.enabled) continue;
                var filter = r.GetComponent<MeshFilter>();
                Mesh mesh = r is SkinnedMeshRenderer s ? s.sharedMesh : filter ? filter.sharedMesh : null;
                if (!mesh) continue;
                long tris = 0; for (int sub = 0; sub < mesh.subMeshCount; sub++) tris += mesh.GetIndexCount(sub) / 3;
                rows.Add(new Row
                {
                    path = PathOf(r.transform), mesh = mesh.name, meshAsset = AssetDatabase.GetAssetPath(mesh), tris = tris,
                    materials = r.sharedMaterials.Length, shadows = r.shadowCastingMode.ToString(), lod = lodCull.TryGetValue(r, out var tag) ? tag : null,
                    skinned = r is SkinnedMeshRenderer, bounds = r.bounds.size.magnitude, center = r.bounds.center, isStatic = r.gameObject.isStatic
                });
            }
            var byMesh = rows.GroupBy(x => x.meshAsset + "|" + x.mesh).Select(g => new { mesh = g.Key, instances = g.Count(), trisEach = g.First().tris, trisTotal = g.Sum(x => x.tris), withLod = g.Count(x => x.lod != null), castShadows = g.Count(x => x.shadows != "Off"), example = g.First().path })
                .OrderByDescending(x => x.trisTotal).Take(60).ToList();
            var byRoot = rows.GroupBy(x => x.path.Split('/')[0]).Select(g => new { root = g.Key, renderers = g.Count(), tris = g.Sum(x => x.tris), noLodTris = g.Where(x => x.lod == null).Sum(x => x.tris) }).OrderByDescending(x => x.tris).ToList();
            var report = new
            {
                utc = DateTime.UtcNow.ToString("O"), renderers = rows.Count, totalTris = rows.Sum(x => x.tris),
                trisWithoutLod = rows.Where(x => x.lod == null).Sum(x => x.tris), shadowCastingTris = rows.Where(x => x.shadows != "Off").Sum(x => x.tris),
                lodGroups = UnityEngine.Object.FindObjectsByType<LODGroup>(FindObjectsInactive.Exclude).Length,
                byRoot, topMeshes = byMesh, topRenderers = rows.OrderByDescending(x => x.tris).Take(80)
            };
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));
            File.WriteAllText(path, JsonConvert.SerializeObject(report, Formatting.Indented, new JsonSerializerSettings { ReferenceLoopHandling = ReferenceLoopHandling.Ignore }));
            Debug.Log("SCENE_COST_AUDIT " + rows.Count + " renderers, " + report.totalTris + " tris -> " + path);
        }

        static string PathOf(Transform t) { var parts = new List<string>(); for (; t; t = t.parent) parts.Add(t.name); parts.Reverse(); return string.Join("/", parts); }

        class Row
        {
            public string path, mesh, meshAsset, shadows, lod; public long tris; public int materials; public bool skinned, isStatic; public float bounds;
            [JsonIgnore] public Vector3 center; public float[] centerXYZ => new[] { center.x, center.y, center.z };
        }
    }
}
