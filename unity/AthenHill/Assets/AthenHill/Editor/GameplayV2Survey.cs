using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>Read-only batch survey of the Outer Berms gameplay layout for Gameplay v2 placement. Never saves.</summary>
    public static class GameplayV2Survey
    {
        public static void Run()
        {
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var outDir = System.Environment.GetEnvironmentVariable("SURVEY_DIR") ?? "Captures";
            Directory.CreateDirectory(outDir);
            var report = new Dictionary<string, object>();
            var roots = scene.GetRootGameObjects();
            report["roots"] = roots.Select(r => r.name).ToArray();
            var berms = roots.First(r => r.name == "Outer Berms").transform;
            var list = new List<object>();
            void Walk(Transform t, int depth, string path)
            {
                string p = path + "/" + t.name;
                var prefab = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(t.gameObject);
                bool isRoot = PrefabUtility.IsAnyPrefabInstanceRoot(t.gameObject);
                var comps = t.GetComponents<Component>().Where(c => c && !(c is Transform)).Select(c => c.GetType().Name).ToArray();
                var rend = t.GetComponentsInChildren<Renderer>(true);
                Bounds b = default; bool first = true;
                foreach (var r in rend) { if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
                if (depth <= 3 || isRoot || comps.Length > 0)
                    list.Add(new { path = p, pos = V(t.position), rot = V(t.eulerAngles), scale = V(t.lossyScale), active = t.gameObject.activeInHierarchy, prefab = isRoot ? prefab : null, comps, size = first ? null : V(b.size) });
                if (isRoot && depth > 2) return;
                foreach (Transform c in t) Walk(c, depth + 1, p);
            }
            Walk(berms, 0, "");
            report["berms"] = list;
            var encounters = Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            report["encounters"] = encounters.Select(e => new { e.name, e.displayName, pos = V(e.transform.position), e.respawnSeconds, e.respawnClearance, spawns = e.spawns.Select(s => new { prefab = s.prefab ? AssetDatabase.GetAssetPath(s.prefab) : null, point = s.point ? s.point.name : null, pos = s.point ? V(s.point.position) : null }) }).ToArray();
            var session = Object.FindAnyObjectByType<GameSession>();
            report["citySession"] = new { session.name, comps = session.GetComponents<Component>().Select(c => c.GetType().Name).ToArray(), children = session.transform.Cast<Transform>().Select(t => t.name).ToArray() };
            var crafting = session.GetComponent<CraftingSession>();
            report["fabricator"] = crafting && crafting.fabricator ? V(crafting.fabricator.position) : null;
            var tutorial = Object.FindAnyObjectByType<BermsTutorial>();
            report["tutorial"] = new { tutorial.name, tutorial.lineComplete, tutorial.rewardCredits, tutorial.rewardItem, tutorial.rewardScrap, first = tutorial.firstContact ? tutorial.firstContact.name : null, depot = tutorial.depot ? tutorial.depot.name : null };
            var combat = Object.FindAnyObjectByType<PlayerCombat>();
            report["combat"] = new { combat.damage, combat.range, combat.fireInterval, combat.nanoMax, combat.nanoPerShot, combat.nanoRegen, combat.nanoRegenDelay, combat.aimAssistDegrees, combat.recoilDegreesPerPoint, combat.cityEdgeX };
            var hud = Object.FindAnyObjectByType<CityHud>();
            report["hud"] = new { hud.name, comps = hud.GetComponents<Component>().Select(c => c.GetType().Name).ToArray() };
            report["interactables"] = Object.FindObjectsByType<WorldInteractable>(FindObjectsInactive.Include, FindObjectsSortMode.None).Select(w => new { w.name, pos = V(w.transform.position), w.prompt, w.range }).ToArray();
            report["npcs"] = session.npcs.Where(n => n).Select(n => new { n.name, pos = V(n.transform.position) }).ToArray();
            var sizes = new Dictionary<string, object>();
            foreach (var p in new[] { "Assets/AthenHill/Prefabs/Salvage/crate.prefab", "Assets/AthenHill/Prefabs/Salvage/trash.prefab", "Assets/AthenHill/Prefabs/Salvage/scrap.prefab", "Assets/AthenHill/Prefabs/WestGate/PH_AmmoBox.prefab", "Assets/AthenHill/Prefabs/OuterBermsDepot/PHD_ToolChest.prefab", "Assets/AthenHill/Prefabs/OuterBermsDepot/MX_ScrapHeapA.prefab", "Assets/AthenHill/Prefabs/OuterBermsDepot/MX_ScrapHeapB.prefab", "Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab" })
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(p); if (!go) { sizes[p] = "missing"; continue; }
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(go); inst.transform.position = Vector3.zero;
                var rs = inst.GetComponentsInChildren<Renderer>(true);
                Bounds b = default; bool first = true;
                foreach (var r in rs) { if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
                sizes[p] = new { size = V(b.size), center = V(b.center), renderers = rs.Select(r => new { r.name, type = r.GetType().Name, mats = r.sharedMaterials.Where(m => m).Select(m => m.name + " | " + m.shader.name + " | " + AssetDatabase.GetAssetPath(m)).ToArray() }).ToArray(), lights = inst.GetComponentsInChildren<Light>(true).Select(l => new { l.name, color = l.color.ToString(), l.intensity, l.range }).ToArray(), tris = inst.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh).Sum(f => f.sharedMesh.triangles.Length / 3) };
                Object.DestroyImmediate(inst);
            }
            report["prefabs"] = sizes;
            File.WriteAllText(Path.Combine(outDir, "gameplay-v2-survey.json"), JsonConvert.SerializeObject(report, Formatting.Indented, new JsonSerializerSettings { ReferenceLoopHandling = ReferenceLoopHandling.Ignore }));
            Debug.Log("GAMEPLAY_V2_SURVEY written to " + outDir);
        }
        static float[] V(Vector3 v) => new[] { (float)System.Math.Round(v.x, 2), (float)System.Math.Round(v.y, 2), (float)System.Math.Round(v.z, 2) };
    }
}
