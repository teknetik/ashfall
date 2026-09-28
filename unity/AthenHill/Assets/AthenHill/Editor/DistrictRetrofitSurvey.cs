using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>Read-only batch survey of scene roots, their children and world bounds (district retrofit planning).</summary>
    public static class DistrictRetrofitSurvey
    {
        public static void Run()
        {
            var scene = EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity", OpenSceneMode.Single);
            var rows = new List<object>();
            void Walk(Transform t, int depth)
            {
                var rs = t.GetComponentsInChildren<Renderer>(true).Where(r => r.enabled && r.gameObject.activeInHierarchy).ToArray();
                var cs = t.GetComponentsInChildren<Collider>(true).Where(c => c.enabled && c.gameObject.activeInHierarchy).ToArray();
                Bounds? b = null;
                foreach (var r in rs) { if (b == null) b = r.bounds; else { var x = b.Value; x.Encapsulate(r.bounds); b = x; } }
                Bounds? cb = null;
                foreach (var c in cs) { if (cb == null) cb = c.bounds; else { var x = cb.Value; x.Encapsulate(c.bounds); cb = x; } }
                rows.Add(new
                {
                    path = Path(t), depth, active = t.gameObject.activeInHierarchy, children = t.childCount,
                    pos = V(t.position), rotY = t.eulerAngles.y, scale = V(t.lossyScale),
                    renderers = rs.Length, colliders = cs.Length,
                    center = b.HasValue ? V(b.Value.center) : null, size = b.HasValue ? V(b.Value.size) : null,
                    colCenter = cb.HasValue ? V(cb.Value.center) : null, colSize = cb.HasValue ? V(cb.Value.size) : null,
                });
                if (depth < 2) foreach (Transform c in t) Walk(c, depth + 1);
            }
            foreach (var g in scene.GetRootGameObjects()) Walk(g.transform, 0);
            File.WriteAllText(System.Environment.GetEnvironmentVariable("SURVEY_OUT") ?? "/tmp/survey.json", JsonConvert.SerializeObject(rows, Formatting.Indented));
        }
        /// Top-surface height of visible geometry and player-blocking colliders on a 0.25 m grid (little-endian float32 files).
        public static void Heightmap()
        {
            var scene = EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity", OpenSceneMode.Single);
            var outDir = System.Environment.GetEnvironmentVariable("SURVEY_DIR");
            var temp = new List<GameObject>();
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (!r.enabled) continue;
                var f = r.GetComponent<MeshFilter>(); if (!f || !f.sharedMesh) continue;
                if (r.GetComponentInParent<LODGroup>() && r.name.ToLower().Contains("lod") && !r.name.EndsWith("0")) continue;
                var go = new GameObject("hm"); go.layer = 31;
                go.transform.SetPositionAndRotation(r.transform.position, r.transform.rotation); go.transform.localScale = r.transform.lossyScale;
                var mc = go.AddComponent<MeshCollider>(); mc.sharedMesh = f.sharedMesh; temp.Add(go);
            }
            Physics.SyncTransforms();
            float x0 = -62, z0 = -47, step = .25f; int nx = 497, nz = 377;
            var top = new float[nx * nz]; var block = new float[nx * nz];
            for (int j = 0; j < nz; j++) for (int i = 0; i < nx; i++)
            {
                var o = new Vector3(x0 + i * step, 60, z0 + j * step);
                top[j * nx + i] = Physics.Raycast(o, Vector3.down, out var hit, 120, 1 << 31) ? hit.point.y : -99;
                // highest player-blocking collider surface between 0.15 m and 3 m above ground
                block[j * nx + i] = Physics.CheckBox(new Vector3(o.x, 1.6f, o.z), new Vector3(step / 2, 1.4f, step / 2), Quaternion.identity, ~(1 << 31), QueryTriggerInteraction.Ignore) ? 1 : 0;
            }
            foreach (var g in temp) Object.DestroyImmediate(g);
            File.WriteAllBytes(outDir + "/top.f32", ToBytes(top)); File.WriteAllBytes(outDir + "/block.f32", ToBytes(block));
            File.WriteAllText(outDir + "/grid.json", JsonConvert.SerializeObject(new { x0, z0, step, nx, nz }));
        }
        static byte[] ToBytes(float[] a) { var b = new byte[a.Length * 4]; System.Buffer.BlockCopy(a, 0, b, 0, b.Length); return b; }
        static float[] V(Vector3 v) => new[] { (float)System.Math.Round(v.x, 2), (float)System.Math.Round(v.y, 2), (float)System.Math.Round(v.z, 2) };
        static string Path(Transform t) => t.parent ? Path(t.parent) + "/" + t.name : t.name;
    }
}
