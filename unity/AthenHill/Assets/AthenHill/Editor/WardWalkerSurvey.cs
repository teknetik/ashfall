using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// 3 Oct 2026 (art/ward_walkers_20261003): read-only survey of the ambient walkers (routes, speeds, actors, nearby landmarks).
    public static class WardWalkerSurvey
    {
        static string PathOf(Transform t) { var s = t.name; while (t.parent) { t = t.parent; s = t.name + "/" + s; } return s; }
        public static void Run()
        {
            try
            {
                EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity", OpenSceneMode.Single);
                var roots = EditorSceneManager.GetActiveScene().GetRootGameObjects();
                var named = roots.SelectMany(r => r.GetComponentsInChildren<Transform>(true)).Where(t => t.parent && t.parent.parent == null && t.gameObject.activeInHierarchy).ToArray();
                var outp = new List<object>();
                foreach (var w in Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                {
                    var pts = w.waypoints.Where(p => p).Select(p => p.position).ToArray();
                    float len = 0; for (int i = 0; i < pts.Length; i++) len += Vector3.Distance(pts[i], pts[(i + 1) % pts.Length]);
                    var smr = w.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                    var near = pts.SelectMany(p => named.OrderBy(t => Vector3.Distance(t.position, p)).Take(2).Select(t => PathOf(t))).Distinct().Take(10).ToArray();
                    outp.Add(new
                    {
                        path = PathOf(w.transform), active = w.gameObject.activeInHierarchy, w.speed, w.phase, w.turnLookAhead, routeLength = len, lapSeconds = len / Mathf.Max(.01f, w.speed),
                        waypoints = w.waypoints.Select(p => p ? PathOf(p) + " " + p.position.ToString("F1") : "null").ToArray(),
                        actor = w.actor ? PathOf(w.actor.transform) : null,
                        actorPrefab = w.actor ? PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(w.actor.gameObject) : null,
                        walkStride = w.actor ? w.actor.walkStrideSpeed : 0, humanoid = w.actor && w.actor.humanoidAnimator,
                        renderers = smr.Select(r => r.name + " tris=" + (r.sharedMesh ? r.sharedMesh.triangles.Length / 3 : 0) + " mats=" + string.Join("|", r.sharedMaterials.Select(m => m ? m.name : "null")) + " offscreen=" + r.updateWhenOffscreen).ToArray(),
                        near,
                    });
                }
                Directory.CreateDirectory("../evidence/ward-walkers/20261003");
                File.WriteAllText("../evidence/ward-walkers/20261003/survey.json", JsonConvert.SerializeObject(outp, Formatting.Indented));
                EditorApplication.Exit(0);
            }
            catch (System.Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
