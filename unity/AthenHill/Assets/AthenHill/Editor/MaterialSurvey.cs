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
    /// Read-only: for every material used by enabled renderers under the given scene roots (or render-chunk sources),
    /// record shader, main/normal/mask textures with their pixel size and tiling, and how many triangles and how much
    /// world area use it. Used to plan facade material upgrades. Batch: -executeMethod ...MaterialSurvey.WriteBatch --survey-out PATH
    public static class MaterialSurvey
    {
        public static void WriteBatch()
        {
            var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, "--survey-out");
            string output = i >= 0 && i + 1 < args.Length ? args[i + 1] : "../evidence/rendering/20260929/material-survey.json";
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) chunks.ShowSources(true);
            var usage = new Dictionary<Material, Usage>();
            foreach (var r in UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude))
            {
                if (!r.enabled || r.transform.IsChildOf(chunks ? chunks.generatedRoot : null)) continue;
                var filter = r.GetComponent<MeshFilter>(); if (!filter || !filter.sharedMesh) continue;
                var mesh = filter.sharedMesh; var root = r.transform.root.name; var mid = r.transform.parent ? r.transform.parent.name : "";
                for (int s = 0; s < r.sharedMaterials.Length && s < mesh.subMeshCount; s++)
                {
                    var m = r.sharedMaterials[s]; if (!m) continue;
                    if (!usage.TryGetValue(m, out var u)) usage[m] = u = new Usage();
                    u.renderers++; u.tris += mesh.GetIndexCount(s) / 3; u.area += r.bounds.size.x * r.bounds.size.y + r.bounds.size.z * r.bounds.size.y;
                    u.roots.Add(root + "/" + mid);
                }
            }
            var rows = usage.OrderByDescending(kv => kv.Value.area).Select(kv => new
            {
                material = kv.Key.name, path = AssetDatabase.GetAssetPath(kv.Key), shader = kv.Key.shader.name, kv.Value.renderers, kv.Value.tris,
                boundsArea = Mathf.Round(kv.Value.area), roots = kv.Value.roots.Take(6),
                textures = kv.Key.GetTexturePropertyNames().Select(p => new { p, t = kv.Key.GetTexture(p) }).Where(x => x.t)
                    .Select(x => new { prop = x.p, name = x.t.name, size = x.t.width + "x" + x.t.height, tiling = kv.Key.GetTextureScale(x.p).ToString() })
            }).ToList();
            File.WriteAllText(output, JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), materials = rows.Count, rows }, Formatting.Indented));
            Debug.Log("MATERIAL_SURVEY " + rows.Count + " materials -> " + output);
            EditorApplication.Exit(0);
        }

        class Usage { public int renderers; public long tris; public float area; public HashSet<string> roots = new HashSet<string>(); }
    }
}
