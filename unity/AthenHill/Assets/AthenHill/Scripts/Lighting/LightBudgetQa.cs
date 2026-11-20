#if UNITY_EDITOR || DEBUG
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace AthenHill
{
    /// Light budget (20 Nov 2026) native QA, development players only, active with --athen-qa OUT:
    ///   OUT/light-budget.json        written every 0.25 s: budget on/off, camera, hour, local lights enabled in the
    ///                                rendering camera's view (every light, not only the budget's), lamps the owners want
    ///                                lit in view, real/pool counts, and running maxima since the last reset.
    ///   OUT/light-budget-cmd.json    {"id":"..","enabled":true|false,"reset":true,"dump":true} toggles the budget at
    ///                                runtime and resets the running stats; the id is echoed as lastCommand.
    ///   ATHEN_LB_TUNE=file           JSON applied after load: {"budget":{"hardCap":26,"poolGain":1.2,...},
    ///                                "aim":[{"path":"Root/child/light","aimAt":[x,y,z]} | {"path":..,"euler":[x,y,z]}],
    ///                                "lights":[{"path":..,"intensity":..,"range":..,"spotAngle":..,"innerSpotAngle":..}]}
    /// Nothing is saved; a release player never compiles this.
    [DefaultExecutionOrder(2100)]
    public sealed class LightBudgetQa : MonoBehaviour
    {
        string folder; float nextWrite; string lastCommand; object tuneLog;
        int frames, framesOver30, framesOverCap, maxInView, maxWantedInView, maxUnmanaged, hardCuts, promotions, demotions;
        float sumInView; DateTime since = DateTime.UtcNow;
        readonly List<Light> all = new List<Light>(); float nextScan;
        readonly Plane[] planes = new Plane[6];
        AthenDebugBridge bridge; CityTimeOfDay clock;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (!Debug.isDebugBuild && !Application.isEditor) return;
            var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, "--athen-qa");
            var tune = Environment.GetEnvironmentVariable("ATHEN_LB_TUNE");
            if ((i < 0 || i + 1 >= args.Length) && string.IsNullOrEmpty(tune)) return;
            var qa = new GameObject("Light budget QA").AddComponent<LightBudgetQa>();
            qa.folder = i >= 0 && i + 1 < args.Length ? Path.GetFullPath(args[i + 1]) : null;
            if (!string.IsNullOrEmpty(tune)) qa.ApplyTune(tune);
        }

        void Start() { bridge = FindAnyObjectByType<AthenDebugBridge>(); clock = FindAnyObjectByType<CityTimeOfDay>(); }

        static Transform FindPath(string path)
        {
            var parts = path.Split('/');
            foreach (var root in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
            {
                if (root.name != parts[0]) continue;
                var t = root.transform;
                for (int k = 1; k < parts.Length && t; k++) t = t.Cast<Transform>().FirstOrDefault(c => c.name == parts[k]);
                if (t) return t;
            }
            return null;
        }

        static Vector3 V(JToken a) => new Vector3((float)a[0], (float)a[1], (float)a[2]);

        void ApplyTune(string path)
        {
            var log = new List<string>();
            try
            {
                var j = JObject.Parse(File.ReadAllText(path));
                var budget = FindAnyObjectByType<LightBudget>(FindObjectsInactive.Include);
                var circuit = FindAnyObjectByType<CityLightCircuit>();
                if (j["budget"] is JObject b && budget)
                    foreach (var p in b.Properties())
                    {
                        var f = typeof(LightBudget).GetField(p.Name);
                        if (f == null) { log.Add("no field " + p.Name); continue; }
                        object v = f.FieldType == typeof(int) ? (object)(int)p.Value : f.FieldType == typeof(float) ? (float)p.Value
                            : f.FieldType == typeof(bool) ? (bool)p.Value : f.FieldType == typeof(Color) ? new Color((float)p.Value[0], (float)p.Value[1], (float)p.Value[2], 1) : null;
                        if (v == null) { log.Add("unsupported " + p.Name); continue; }
                        f.SetValue(budget, v); log.Add("budget." + p.Name);
                    }
                bool lightsChanged = false;
                bool wasOn = budget && budget.enabled;
                if (budget) budget.enabled = false;
                // the clock restores its cached values in OnDisable: switch it off before editing lights, on afterwards
                bool editLights = (j["aim"] is JArray aa && aa.Count > 0) || (j["lights"] is JArray ll && ll.Count > 0);
                if (editLights && circuit) circuit.enabled = false;
                foreach (JObject a in (JArray)j["aim"] ?? new JArray())
                {
                    var t = FindPath((string)a["path"]); if (!t) { log.Add("no " + a["path"]); continue; }
                    if (a["aimAt"] != null) t.rotation = Quaternion.LookRotation(V(a["aimAt"]) - t.position, Vector3.up);
                    if (a["euler"] != null) t.eulerAngles = V(a["euler"]);
                    if (a["localPosition"] != null) t.localPosition = V(a["localPosition"]);
                    log.Add("aim " + t.name); lightsChanged = true;
                }
                foreach (JObject a in (JArray)j["lights"] ?? new JArray())
                {
                    var t = FindPath((string)a["path"]); var l = t ? t.GetComponent<Light>() : null; if (!l) { log.Add("no light " + a["path"]); continue; }
                    if (a["intensity"] != null) l.intensity = (float)a["intensity"];
                    if (a["range"] != null) l.range = (float)a["range"];
                    if (a["spotAngle"] != null) l.spotAngle = (float)a["spotAngle"];
                    if (a["innerSpotAngle"] != null) l.innerSpotAngle = (float)a["innerSpotAngle"];
                    log.Add("light " + l.name); lightsChanged = true;
                }
                // The clock caches authored intensities at OnEnable, the budget its lamps and pools: restart both.
                if (editLights && circuit) circuit.enabled = true;
                if (budget && wasOn) { budget.enabled = true; budget.RefreshPools(); }
            }
            catch (Exception e) { log.Add("error: " + e.Message); Debug.LogError("Light budget tune failed: " + e); }
            tuneLog = log; Debug.Log("Light budget tune: " + string.Join(", ", log));
        }

        void Update()
        {
            if (folder == null) return;
            var cmdPath = Path.Combine(folder, "light-budget-cmd.json");
            if (File.Exists(cmdPath))
            {
                try
                {
                    var j = JObject.Parse(File.ReadAllText(cmdPath)); File.Delete(cmdPath);
                    var budget = FindAnyObjectByType<LightBudget>(FindObjectsInactive.Include);
                    if (j["enabled"] != null && budget) budget.enabled = (bool)j["enabled"];
                    if (j["reset"] != null && (bool)j["reset"]) ResetStats();
                    lastCommand = (string)j["id"];
                    Write(j["dump"] != null && (bool)j["dump"]);
                }
                catch (IOException) { }
                catch (Exception e) { Debug.LogError("Light budget command failed: " + e); }
            }
        }

        void ResetStats() { frames = framesOver30 = framesOverCap = maxInView = maxWantedInView = maxUnmanaged = hardCuts = promotions = demotions = 0; sumInView = 0; since = DateTime.UtcNow; }

        void LateUpdate()
        {
            if (folder == null) return;
            var cam = LightBudget.FindRenderingCamera(); if (!cam) return;
            if (Time.unscaledTime >= nextScan) { all.Clear(); all.AddRange(FindObjectsByType<Light>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).Where(l => l.type != LightType.Directional)); nextScan = Time.unscaledTime + 1; }
            GeometryUtility.CalculateFrustumPlanes(cam, planes);
            int inView = 0;
            foreach (var l in all) if (l && l.isActiveAndEnabled && l.intensity > 0 && GeometryUtility.TestPlanesAABB(planes, new Bounds(l.transform.position, Vector3.one * 2 * l.range))) inView++;
            var b = LightBudget.Active; bool on = b && b.isActiveAndEnabled;
            int wanted = on ? b.Stats.candidatesInView + b.UnmanagedInView : inView;
            frames++; sumInView += inView; if (inView > 30) framesOver30++;
            if (on && inView > b.hardCap) framesOverCap++;
            maxInView = Mathf.Max(maxInView, inView); maxWantedInView = Mathf.Max(maxWantedInView, wanted);
            if (on) { maxUnmanaged = Mathf.Max(maxUnmanaged, b.UnmanagedInView); hardCuts += b.Stats.hardCuts; promotions += b.Stats.promotions; demotions += b.Stats.demotions; }
            current = inView; currentWanted = wanted;
            if (Time.unscaledTime >= nextWrite) { nextWrite = Time.unscaledTime + .25f; Write(false); }
        }
        int current, currentWanted;

        void Write(bool dump)
        {
            var b = LightBudget.Active; bool on = b && b.isActiveAndEnabled;
            var circuit = FindAnyObjectByType<CityLightCircuit>();
            var o = new Dictionary<string, object>
            {
                ["frame"] = Time.frameCount, ["lastCommand"] = lastCommand, ["enabled"] = on, ["installed"] = FindAnyObjectByType<LightBudget>(FindObjectsInactive.Include) != null,
                ["camera"] = bridge ? bridge.selectedCamera : null, ["hour"] = clock ? Math.Round(clock.Hour, 2) : -1,
                ["lampStrength"] = clock ? Math.Round(clock.LampStrength, 3) : -1,
                ["circuit"] = circuit ? new { circuit.ActiveLights, circuit.ActiveShadowLights, strength = Math.Round(circuit.CurrentStrength, 3), circuit.enabled } : null,
                ["inView"] = current, ["wantedInView"] = currentWanted,
                ["budget"] = on ? new { b.hardCap, b.ManagedLamps, b.UnmanagedInView, b.LightsInView, b.Stats.candidatesInView, b.Stats.enabledInView, b.Stats.realInView, b.Stats.poolsInView, b.Stats.waiting, b.PoolsActive, b.PoolsDrawn, b.maxPools } : null,
                ["running"] = new { frames, seconds = Math.Round((DateTime.UtcNow - since).TotalSeconds, 1), meanInView = frames > 0 ? Math.Round(sumInView / frames, 2) : 0, maxInView, maxWantedInView, framesOver30, framesOverCap, maxUnmanaged, hardCuts, promotions, demotions },
                ["tune"] = tuneLog,
            };
            if (dump && on) o["lamps"] = b.Lamps().Where(x => x.wanted).Select(x => new { x.name, x.real, fade = Math.Round(x.fade, 2), x.inView, score = Math.Round(x.score, 3) }).ToArray();
            try
            {
                var path = Path.Combine(folder, "light-budget.json");
                File.WriteAllText(path + ".tmp", JsonConvert.SerializeObject(o, Formatting.Indented));
                File.Copy(path + ".tmp", path, true); File.Delete(path + ".tmp");
            }
            catch (IOException) { }
        }
    }
}
#endif
