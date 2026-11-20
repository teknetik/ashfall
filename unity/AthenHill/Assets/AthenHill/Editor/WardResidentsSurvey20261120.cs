using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// Showcase phase 2, residents (20 Nov 2026, art/ward_residents_20261120): read-only survey of the saved city for
    /// choosing where new residents live and walk. Writes unity/evidence/showcase_phase2/20261120/residents/survey.json.
    /// -executeMethod AthenHill.Editor.WardResidentsSurvey20261120.Run -nographics
    public static class WardResidentsSurvey20261120
    {
        const string Out = "../evidence/showcase_phase2/20261120/residents/";
        static string PathOf(Transform t) { var s = t.name; while (t.parent) { t = t.parent; s = t.name + "/" + s; } return s; }
        static float[] V(Vector3 v) => new[] { (float)Math.Round(v.x, 2), (float)Math.Round(v.y, 2), (float)Math.Round(v.z, 2) };

        static readonly string[] Keys = {
            "sit point", "WL_", "tally", "scale", "water", "dock", "market", "stall", "karaveen", "food", "hydro", "greenhouse",
            "quonset", "home", "container", "door", "stair", "step", "terminal", "lattice", "ring", "portal", "west gate", "counter",
            "bench", "board", "cart", "crate", "vignette", "kiosk", "booth", "trough", "tap", "shop", "porch",
        };

        public static void Run()
        {
            try
            {
                EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity", OpenSceneMode.Single);
                var scene = EditorSceneManager.GetActiveScene();
                var all = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Transform>(true)).ToArray();
                var report = new Dictionary<string, object>();
                report["roots"] = scene.GetRootGameObjects().Select(g =>
                {
                    var rs = g.GetComponentsInChildren<Renderer>(false); var b = rs.Length > 0 ? rs[0].bounds : new Bounds(g.transform.position, Vector3.zero);
                    foreach (var r in rs) b.Encapsulate(r.bounds);
                    return new { name = g.name, active = g.activeSelf, children = g.transform.childCount, centre = V(b.center), size = V(b.size) };
                }).ToArray();
                report["walkers"] = Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None).Select(w => new
                {
                    path = PathOf(w.transform), active = w.gameObject.activeInHierarchy, w.speed, w.phase,
                    waypoints = w.waypoints.Select(p => p ? V(p.position) : null).ToArray(),
                    actor = w.actor ? PathOf(w.actor.transform) : null,
                }).ToArray();
                report["npcs"] = Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Include, FindObjectsSortMode.None).Select(n => new
                {
                    path = PathOf(n.transform), active = n.gameObject.activeInHierarchy, id = n.definition ? n.definition.id : null,
                    pos = V(n.transform.position), yaw = Math.Round(n.transform.eulerAngles.y, 1),
                }).ToArray();
                report["named"] = all.Where(t => t.gameObject.activeInHierarchy && Keys.Any(k => t.name.ToLowerInvariant().Contains(k.ToLowerInvariant())))
                    .Where(t => t.parent == null || t.parent.name != t.name)
                    .Select(t =>
                    {
                        var r = t.GetComponentInChildren<Renderer>(); var c = t.GetComponent<Collider>();
                        return new { path = PathOf(t), pos = V(t.position), yaw = Math.Round(t.eulerAngles.y, 0), size = r ? V(r.bounds.size) : null, collider = c ? c.GetType().Name : null };
                    }).Take(4000).ToArray();
                report["cameras"] = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(c => c.name.StartsWith("cam_")).Select(c => c.name + " " + string.Join(",", V(c.transform.position))).OrderBy(x => x).ToArray();
                // colliders: compact list of static colliders' world bounds (for route clearance planning offline)
                report["colliders"] = Object.FindObjectsByType<Collider>(FindObjectsSortMode.None).Where(c => c.enabled && c.gameObject.activeInHierarchy && !c.isTrigger)
                    .Select(c => new { p = PathOf(c.transform), min = V(c.bounds.min), max = V(c.bounds.max) })
                    .Where(c => c.max[1] > .15f && c.min[1] < 2f && (c.max[0] - c.min[0]) < 80 && (c.max[2] - c.min[2]) < 80).ToArray();
                Directory.CreateDirectory(Out);
                File.WriteAllText(Out + "survey.json", JsonConvert.SerializeObject(report, Formatting.Indented));
                Debug.Log("WardResidentsSurvey OK");
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); Debug.Log("WardResidentsSurvey FAILED"); EditorApplication.Exit(1); }
        }
    }
}
