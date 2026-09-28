using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>Read-only batch survey for the Outer Berms tutorial zone west of the market gate.</summary>
    public static class OuterBermsSurvey
    {
        public static void Run()
        {
            var scene = EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity", OpenSceneMode.Single);
            var outDir = System.Environment.GetEnvironmentVariable("SURVEY_DIR");
            var report = new Dictionary<string, object>();
            var roots = scene.GetRootGameObjects();
            Transform Find(string path) => roots.Select(r => path.StartsWith(r.name + "/") ? r.transform.Find(path.Substring(r.name.Length + 1)) : r.name == path ? r.transform : null).FirstOrDefault(t => t);

            foreach (var name in new[] { "AuthoredWorld/BLD_boundary_side.001", "AuthoredWorld/COL_BLD_boundary_side.001", "AuthoredWorld/BLD_boundary_side" })
            {
                var t = Find(name); if (!t) { report[name] = "missing"; continue; }
                var f = t.GetComponent<MeshFilter>(); var r = t.GetComponent<Renderer>(); var c = t.GetComponent<Collider>();
                report[name] = new
                {
                    pos = V(t.position), rot = V(t.eulerAngles), scale = V(t.lossyScale), active = t.gameObject.activeInHierarchy,
                    mesh = f && f.sharedMesh ? new { f.sharedMesh.name, path = AssetDatabase.GetAssetPath(f.sharedMesh), verts = f.sharedMesh.vertexCount, tris = f.sharedMesh.triangles.Length / 3, b = V(f.sharedMesh.bounds.size), bc = V(f.sharedMesh.bounds.center), uvs = f.sharedMesh.uv.Take(24).Select(u => new[] { u.x, u.y }), verts24 = f.sharedMesh.vertices.Take(24).Select(V) } : null,
                    renderer = r ? new { r.enabled, mats = r.sharedMaterials.Select(m => m ? m.name + " | " + m.shader.name + " | " + AssetDatabase.GetAssetPath(m) : "null") } : null,
                    collider = c ? c.GetType().Name : null,
                    prefab = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(t.gameObject)
                };
            }
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            report["chunks"] = chunks ? new { roots = chunks.sourceRoots.Select(s => s ? s.name : "null"), stale = chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks), chunks.editingSources } : null;

            // District gate prefab dimensions, salvage prefabs, ground/terrain materials
            foreach (var p in Directory.GetFiles("Assets/AthenHill/Prefabs/District", "*.prefab").Concat(Directory.GetFiles("Assets/AthenHill/Prefabs/Salvage", "*.prefab")).Concat(new[] { "Assets/AthenHill/Prefabs/WardGuard.prefab", "Assets/AthenHill/Prefabs/WardMiningDroid.prefab", "Assets/AthenHill/Prefabs/KaraveenTruck.prefab" }))
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(p);
                var rs = go.GetComponentsInChildren<Renderer>(true);
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(go); inst.transform.position = Vector3.zero;
                var b = new Bounds(); bool first = true;
                foreach (var r in inst.GetComponentsInChildren<Renderer>()) { if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
                report["prefab " + p] = new { size = V(b.size), center = V(b.center), renderers = rs.Length, colliders = go.GetComponentsInChildren<Collider>(true).Length, comps = go.GetComponents<Component>().Select(c => c.GetType().Name), mats = rs.SelectMany(r => r.sharedMaterials).Where(m => m).Select(m => m.name).Distinct().Take(6) };
                Object.DestroyImmediate(inst);
            }
            report["gate instances"] = roots.SelectMany(r => r.GetComponentsInChildren<Transform>(true)).Where(t => PrefabUtility.IsAnyPrefabInstanceRoot(t.gameObject) && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(t.gameObject).Contains("District/gate")).Select(t => new { path = t.name, pos = V(t.position), rot = V(t.eulerAngles), s = V(t.lossyScale), active = t.gameObject.activeInHierarchy }).ToArray();
            var basin = Find("Desert Landscape");
            report["basin mats"] = basin.GetComponentsInChildren<Renderer>().SelectMany(r => r.sharedMaterials).Where(m => m).Select(m => m.name + " | " + m.shader.name + " | " + AssetDatabase.GetAssetPath(m)).Distinct();
            report["materials"] = AssetDatabase.FindAssets("t:Material", new[] { "Assets/AthenHill" }).Select(AssetDatabase.GUIDToAssetPath).Where(p => p.ToLower().Contains("concrete") || p.ToLower().Contains("asphalt") || p.ToLower().Contains("paving") || p.ToLower().Contains("sand") || p.ToLower().Contains("road") || p.ToLower().Contains("rust")).ToArray();

            // Basin top-surface heights west of the wall (2 m grid) using temporary mesh colliders
            var temp = new List<GameObject>();
            foreach (var r in basin.GetComponentsInChildren<MeshRenderer>())
            {
                var f = r.GetComponent<MeshFilter>(); var go = new GameObject("hm"); go.layer = 31;
                go.transform.SetPositionAndRotation(r.transform.position, r.transform.rotation); go.transform.localScale = r.transform.lossyScale;
                go.AddComponent<MeshCollider>().sharedMesh = f.sharedMesh; temp.Add(go);
            }
            Physics.SyncTransforms();
            float x0 = -220, z0 = -100, step = 2; int nx = 86, nz = 101;
            var h = new float[nx * nz];
            for (int j = 0; j < nz; j++) for (int i = 0; i < nx; i++)
                h[j * nx + i] = Physics.Raycast(new Vector3(x0 + i * step, 200, z0 + j * step), Vector3.down, out var hit, 400, 1 << 31) ? hit.point.y : -99;
            foreach (var g in temp) Object.DestroyImmediate(g);
            File.WriteAllText(outDir + "/basin.json", JsonConvert.SerializeObject(new { x0, z0, step, nx, nz, h }));

            // Player-capsule clearance around the truck toward the wall (world colliders only)
            var clear = new List<object>();
            for (float z = -12; z <= 12; z += .5f) for (float x = -58f; x <= -44; x += .5f)
                if (!Physics.CheckCapsule(new Vector3(x, .45f, z), new Vector3(x, 1.5f, z), .4f, ~(1 << 8), QueryTriggerInteraction.Ignore)) clear.Add(new[] { x, z });
            report["clear"] = clear;
            File.WriteAllText(outDir + "/report.json", JsonConvert.SerializeObject(report, Formatting.Indented));
        }
        static float[] V(Vector3 v) => new[] { (float)System.Math.Round(v.x, 3), (float)System.Math.Round(v.y, 3), (float)System.Math.Round(v.z, 3) };
    }
}
