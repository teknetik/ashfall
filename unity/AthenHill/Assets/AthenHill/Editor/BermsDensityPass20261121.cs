using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// 21 November 2026 (Phase 4 / Outer Berms density): additive worldbuilding pass that fills the sparse corridors
    /// between Outer Berms POIs with collapsed conveyor spines, fallen Quantum Tube pylons, Warden sandbag cover posts,
    /// Karaveen skirmish wrecks and desert boulder/scrub clusters from art/berms_density_20261121/placements.json.
    /// Never moves or modifies existing sites, encounters, spawns, loot, colliders or ground tiles.
    ///
    /// Menu: Athen Hill -> Outer Berms -> Install / Verify / Rollback Berms Density (2026-11-21)
    /// Batch: -executeMethod AthenHill.Editor.BermsDensityPass20261121.RunBatch --steps install,verify
    /// </summary>
    public static class BermsDensityPass20261121
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string PlacementsPath = "../../art/berms_density_20261121/placements.json";
        const string PrefabRoot = "Assets/AthenHill/Prefabs/";
        const string RootName = "Berms density";
        const string TilesPath = "Outer Berms/Berms expanse/Ground";

        [MenuItem("Athen Hill/Outer Berms/Install Berms Density (2026-11-21)")]
        public static void MenuInstall() => Debug.Log(Install());

        [MenuItem("Athen Hill/Outer Berms/Verify Berms Density (2026-11-21)")]
        public static void MenuVerify() => Debug.Log(Verify());

        [MenuItem("Athen Hill/Outer Berms/Rollback Berms Density (2026-11-21)")]
        public static void MenuRollback() => Debug.Log(Rollback());

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string stepsArg = "install,verify";
            for (int i = 0; i < args.Length - 1; i++)
                if (args[i] == "--steps") stepsArg = args[i + 1];
            foreach (var raw in stepsArg.Split(','))
            {
                var step = raw.Trim().ToLowerInvariant();
                if (step == "install") Debug.Log(Install());
                else if (step == "verify") Debug.Log(Verify());
                else if (step == "rollback") Debug.Log(Rollback());
                else throw new ArgumentException("Unknown BermsDensityPass step: " + step);
            }
        }

        static Scene OpenScene() => EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);

        static Transform Find(Scene s, string path)
        {
            var parts = path.Split('/');
            var r = s.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!r) return null;
            var t = r.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Find(parts[i]);
            return t;
        }

        public static string Install()
        {
            var scene = OpenScene();
            var berms = Find(scene, "Outer Berms");
            var tiles = Find(scene, TilesPath);
            if (!berms || !tiles) throw new Exception("Outer Berms or expanse ground not found");

            var old = berms.Find(RootName);
            if (old) Object.DestroyImmediate(old.gameObject);

            var root = new GameObject(RootName).transform;
            root.SetParent(berms, false);

            var groundGo = Find(scene, "Outer Berms/Berms ground");
            var varietyGo = Find(scene, "Outer Berms/Berms variety");
            var groundCols = tiles.GetComponentsInChildren<MeshCollider>(true).Cast<Collider>().ToList();
            if (groundGo && groundGo.GetComponent<MeshCollider>()) groundCols.Add(groundGo.GetComponent<MeshCollider>());
            if (varietyGo) groundCols.AddRange(varietyGo.GetComponentsInChildren<MeshCollider>(true));
            Physics.SyncTransforms();

            float GroundY(float x, float z)
            {
                var ray = new Ray(new Vector3(x, 300f, z), Vector3.down);
                float best = float.NegativeInfinity;
                foreach (var c in groundCols)
                    if (c && c.Raycast(ray, out var hit, 600f) && hit.point.y > best) best = hit.point.y;
                return best;
            }

            var doc = JObject.Parse(File.ReadAllText(PlacementsPath));
            var prefabs = (JArray)doc["prefabs"];
            var groups = new Dictionary<string, Transform>();
            var cache = new Dictionary<string, GameObject>();
            var missing = new List<string>();
            int placed = 0, skippedGround = 0;

            Transform Group(string name)
            {
                if (!groups.TryGetValue(name, out var g))
                {
                    g = new GameObject(name).transform;
                    g.SetParent(root, false);
                    groups[name] = g;
                }
                return g;
            }

            foreach (JObject p in prefabs)
            {
                var rel = (string)p["prefab"];
                if (!cache.TryGetValue(rel, out var asset))
                {
                    asset = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabRoot + rel + ".prefab");
                    cache[rel] = asset;
                }
                if (!asset) { if (!missing.Contains(rel)) missing.Add(rel); continue; }

                float x = (float)p["x"], z = (float)p["z"];
                float y = GroundY(x, z);
                if (float.IsNegativeInfinity(y)) { skippedGround++; continue; }

                float sink = p["sink"] != null ? (float)p["sink"] : 0.08f;
                float yaw = p["yaw"] != null ? (float)p["yaw"] : 0f;
                float scale = p["scale"] != null ? (float)p["scale"] : 1f;
                bool shadows = p["shadows"] == null || (bool)p["shadows"];
                string colMode = p["collider"] != null ? (string)p["collider"] : "keep";
                string group = p["group"] != null ? (string)p["group"] : "Props";

                var inst = (GameObject)PrefabUtility.InstantiatePrefab(asset, scene);
                inst.name = $"{Path.GetFileNameWithoutExtension(rel)}_{placed + 1:000}";
                inst.transform.SetParent(Group(group), false);
                inst.transform.position = new Vector3(x, y - sink, z);
                inst.transform.rotation = Quaternion.Euler(0, yaw, 0);
                inst.transform.localScale = Vector3.one * scale;
                GameObjectUtility.SetStaticEditorFlags(inst, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);

                foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                {
                    r.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
                    r.receiveShadows = true;
                }
                if (colMode == "remove")
                    foreach (var c in inst.GetComponentsInChildren<Collider>(true))
                        Object.DestroyImmediate(c);

                placed++;
            }

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return $"BERMS_DENSITY install OK: placed={placed}, skippedGround={skippedGround}, missingPrefabs={missing.Count} ({string.Join(", ", missing)})";
        }

        public static string Verify()
        {
            var scene = OpenScene();
            var root = Find(scene, "Outer Berms/" + RootName);
            if (!root) throw new Exception("Berms density root not found");
            int renderers = root.GetComponentsInChildren<Renderer>(false).Length;
            int missingMats = root.GetComponentsInChildren<Renderer>(false)
                .Count(r => r.sharedMaterials == null || r.sharedMaterials.Any(m => !m));
            if (renderers == 0) throw new Exception("Berms density has 0 active renderers");
            if (missingMats > 0) throw new Exception($"Berms density has {missingMats} renderers with missing materials");
            return $"BERMS_DENSITY verify PASS: groups={root.childCount}, renderers={renderers}, missingMaterials=0";
        }

        public static string Rollback()
        {
            var scene = OpenScene();
            var root = Find(scene, "Outer Berms/" + RootName);
            if (!root) return "BERMS_DENSITY rollback: root already absent";
            Object.DestroyImmediate(root.gameObject);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return "BERMS_DENSITY rollback OK: removed " + RootName;
        }
    }
}
