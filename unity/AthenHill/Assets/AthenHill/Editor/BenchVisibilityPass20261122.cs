using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Editor
{
    /// 22 Nov 2026, Carl's second bench playtest round: small parts stay in sight. Brings the installed bench prefab up to
    /// art/steady_hands_bench_20261120/data/layout.json for the few things that changed, without a rebuild of the prefab
    /// (the scene holds an instance, so the scene is not written):
    ///   the second sheet's seat in the tray, where the sheets and the vial start, and the close shot of the housing pin.
    ///
    ///   -executeMethod AthenHill.Editor.BenchVisibilityPass20261122.RunBatch --steps install,verify | rollback
    public static class BenchVisibilityPass20261122
    {
        const string PrefabPath = "Assets/AthenHill/Data/Assembly/SteadyHandsBench.prefab";
        const string TrayB = "fixtures.tray/seat_alloy#b", Pin = "cam_bench_pin";
        static readonly string[] Parts = { "materials.sheet_a", "materials.sheet_b", "materials.vial" };
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string LayoutPath => Path.Combine(Repo, "art/steady_hands_bench_20261120/data/layout.json");
        static string OriginalsPath => Path.Combine(Repo, "art/bench_visibility_20261122/originals.json");
        static Vector3 V(JToken a) => new Vector3((float)a[0], (float)a[1], (float)a[2]);
        static JObject ById(JObject layout, string list, string id) => ((JArray)layout[list]).Cast<JObject>().First(p => (string)p["id"] == id);

        static Dictionary<string, Vector3> Wanted(AssemblyBench bench)
        {
            var layout = JObject.Parse(File.ReadAllText(LayoutPath)); var wanted = new Dictionary<string, Vector3>();
            var b = bench.Marker(TrayB);
            var shift = V(ById(layout, "places", TrayB)["pos"]) - V(ById(layout, "places", "fixtures.tray/seat_alloy")["pos"]);
            wanted[TrayB] = b.transform.parent.position + b.frame.TransformVector(shift);
            foreach (var part in Parts)
            {
                string place = bench.Part(part).homePlace;
                wanted[place] = bench.surface.TransformPoint(V(ById(layout, "places", place)["at"]));
            }
            return wanted;
        }

        static object Install()
        {
            var root = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                var bench = root.GetComponent<AssemblyBench>(); bench.Index(true);
                var wanted = Wanted(bench);
                if (!File.Exists(OriginalsPath))
                {
                    var originals = new JObject();
                    foreach (var id in wanted.Keys) { var p = bench.Marker(id).transform.localPosition; originals[id] = new JArray(p.x, p.y, p.z); }
                    File.WriteAllText(OriginalsPath, originals.ToString());
                }
                foreach (var pair in wanted) bench.Marker(pair.Key).transform.position = pair.Value;
                foreach (var part in Parts) bench.Put(bench.Part(part), bench.Part(part).homePlace);
                var sh = ById(JObject.Parse(File.ReadAllText(LayoutPath)), "shots", "pin");
                var t = bench.cameraRoot.Find(Pin);
                if (!t) { t = new GameObject(Pin).transform; t.SetParent(bench.cameraRoot, false); }
                t.localPosition = V(sh["pos"]); t.localRotation = Quaternion.LookRotation(V(sh["look"]) - V(sh["pos"]), Vector3.up);
                var cam = t.GetComponent<Camera>(); if (!cam) cam = t.gameObject.AddComponent<Camera>();
                cam.enabled = false; cam.fieldOfView = (float)sh["fov"]; cam.nearClipPlane = .03f;
                Save(root);
                return new { places = wanted.Count, shot = Pin };
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }

        static void Save(GameObject root)
        {
            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath, out bool ok);
            if (!ok) throw new Exception("could not save " + PrefabPath);
        }

        static object Verify()
        {
            var root = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                var bench = root.GetComponent<AssemblyBench>(); bench.Index(true);
                var problems = new List<string>();
                foreach (var pair in Wanted(bench))
                    if (Vector3.Distance(bench.Marker(pair.Key).transform.position, pair.Value) > 1e-4f) problems.Add(pair.Key + " is not where the layout has it");
                if (!bench.cameraRoot.Find(Pin)) problems.Add(Pin + " is missing");
                foreach (var p in bench.Parts)
                    foreach (var r in p.renderers)
                    {
                        var filter = r ? r.GetComponent<MeshFilter>() : null;
                        if (filter && filter.sharedMesh && !filter.sharedMesh.isReadable) problems.Add(p.id + ": mesh cannot be read, so nothing can be rested on it");
                    }
                if (problems.Count > 0) throw new Exception("verify failed: " + string.Join("; ", problems));
                return new { pass = true };
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }

        static object Rollback()
        {
            var originals = JObject.Parse(File.ReadAllText(OriginalsPath));
            var root = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                var bench = root.GetComponent<AssemblyBench>(); bench.Index(true);
                foreach (var pair in originals) bench.Marker(pair.Key).transform.localPosition = V(pair.Value);
                foreach (var part in Parts) bench.Put(bench.Part(part), bench.Part(part).homePlace);
                var cam = bench.cameraRoot.Find(Pin); if (cam) UnityEngine.Object.DestroyImmediate(cam.gameObject);
                Save(root);
                return new { restored = originals.Count };
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            string steps = i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify";
            try
            {
                foreach (var name in steps.Split(','))
                {
                    object result = name switch { "install" => Install(), "verify" => Verify(), "rollback" => Rollback(), _ => throw new Exception("unknown step " + name) };
                    Debug.Log("BenchVisibilityPass20261122 " + name + ": " + JsonConvert.SerializeObject(result));
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
