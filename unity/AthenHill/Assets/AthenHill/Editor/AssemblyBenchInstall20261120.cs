using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Audio;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>
    /// 20 November 2026, Steady Hands bench programme, bench agent: the hands-on assembly system's installer.
    /// Record: art/steady_hands_bench_20261120/bench/README.md.
    ///
    /// recipe   : art/steady_hands_bench_20261120/data/steps.json -> Data/Assembly/assembly_grip_stabilised_pistol.asset
    /// audio    : audio/manifest.json + audio/lines.json -> Data/Assembly/AssemblyAudioTable.asset (missing clips stay silent)
    /// settings : creates Data/Assembly/AssemblySettings.asset when there is none (never overwrites tuned numbers)
    /// prefab   : builds the bench (greybox families laid out per data/layout.json) -> Data/Assembly/SteadyHandsBench.prefab
    /// scene    : scene root "Steady Hands bench" (an instance of that prefab) placed from the Salvage workbench's
    ///            transform, registered with the shop's InteriorLighting, QA landmark bench_steady_hands. Idempotent.
    /// install  : recipe, audio, settings, prefab, scene.
    /// verify   : on the saved scene, -nographics. Writes unity/evidence/steady_hands/20261120/bench/verify.json.
    /// selfteststandins : the same on the stand-in bench (SteadyHandsBenchStandIns.prefab, which `prefab` saves beside the installed one
    ///            whatever data/sources.json says): bench/selftest-standins.json. The bench's own Edit Mode tests play that prefab too.
    /// selftest : plays the whole job and the slice with the bot (mouse and keyboard forms, faults, leaving) on a copy of the prefab. Saves nothing.
    /// bindcheck: binds each real family found under Art/Bench (or --family NAME) on a scratch object through BindFamily and
    ///            reports what does not resolve (bench/bind-FAMILY.json). Installs nothing, saves nothing.
    /// sight    : walks the whole job on a scratch bench and tests that the player can see what every action needs, from the shot
    ///            the session will use (AssemblySightCheck): bench/sight-LABEL.json. `verify` runs the same on the installed prefab
    ///            (bench/sight.json) and `bindcheck` on the whole bench with each real family (bench/sight-bind-FAMILY.json).
    /// Which families are real: art/steady_hands_bench_20261120/data/sources.json; --real a,b and --greybox a,b|all change it for one run.
    /// rollback : removes the scene root, its InteriorLighting entry and the landmark (assets stay).
    /// -executeMethod AthenHill.Editor.AssemblyBenchInstall20261120.RunBatch --steps install,verify | rollback
    /// </summary>
    public static class AssemblyBenchInstall20261120
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        public const string RootName = "Steady Hands bench";
        public const string PrefabPath = AssemblyKitBuilder.DataDir + "SteadyHandsBench.prefab";
        /// The same bench built from the stand-ins alone, whatever data/sources.json says: what the bench's own Edit Mode tests
        /// and `selftest --standins` play, so that they do not change with the art. No scene uses it; it is not in a build.
        public const string StandInPrefabPath = AssemblyKitBuilder.DataDir + "SteadyHandsBenchStandIns.prefab";
        public const string RecipePath = AssemblyKitBuilder.DataDir + "assembly_grip_stabilised_pistol.asset";
        public const string SettingsPath = AssemblyKitBuilder.DataDir + "AssemblySettings.asset";
        public const string AudioPath = AssemblyKitBuilder.DataDir + "AssemblyAudioTable.asset";
        const string StylePath = AssemblyKitBuilder.DataDir + "AssemblyHud.uss";
        const string InputPath = "Assets/AthenHill/Data/Controls.inputactions";
        const string MixerPath = "Assets/AthenHill/Audio/City.mixer";
        const string Landmark = "bench_steady_hands";
        /// When true a point the player cannot see fails `verify`. The stand-in bench is held to it.
        const bool SightIsStrict = false;
        const string ShopRoot = "Salvage shop interior";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string ArtDir => Path.Combine(Repo, "art/steady_hands_bench_20261120");
        static string StepsPath => Path.Combine(ArtDir, "data/steps.json");
        static string LayoutPath => Path.Combine(ArtDir, "data/layout.json");
        static string RecordPath => Path.Combine(ArtDir, "bench/record.json");
        static string Evidence => Path.Combine(Repo, "unity/evidence/steady_hands/20261120/bench");

        static string Sha1(string text) { using (var sha = SHA1.Create()) return string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(text)).Select(b => b.ToString("x2"))); }
        static IEnumerable<Transform> All(Scene s) => s.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Transform>(true));
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static void WriteEvidence(string name, object value) { Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(value, Formatting.Indented)); }
        static T LoadOrCreate<T>(string path) where T : ScriptableObject
        {
            var a = AssetDatabase.LoadAssetAtPath<T>(path);
            if (!a) { Directory.CreateDirectory(Path.GetDirectoryName(path)); a = ScriptableObject.CreateInstance<T>(); AssetDatabase.CreateAsset(a, path); }
            return a;
        }

        // ------------------------------------------------------------------ assets
        static object Recipe()
        {
            string text = File.ReadAllText(StepsPath);
            var data = AssemblyRecipeData.FromJson(text);
            var problems = data.Validate();
            if (problems.Count > 0) throw new Exception("steps.json: " + string.Join("; ", problems));
            var asset = LoadOrCreate<AssemblyRecipe>(RecipePath);
            asset.data = data; asset.sourceHash = Sha1(text);
            EditorUtility.SetDirty(asset); AssetDatabase.SaveAssets();
            return new { asset = RecipePath, stages = data.stages.Length, steps = data.Steps.Count(), actions = data.Steps.Sum(s => s.actions.Length), asset.sourceHash };
        }

        static object Audio()
        {
            var table = LoadOrCreate<AssemblyAudioTable>(AudioPath);
            string manifestPath = Path.Combine(ArtDir, "audio/manifest.json"), linesPath = Path.Combine(ArtDir, "audio/lines.json");
            var events = new List<AssemblyAudioTable.Event>(); var lines = new List<AssemblyAudioTable.Line>(); var contacts = new List<AssemblyAudioTable.Contact>();
            var missing = new List<string>(); string hash = "";
            if (File.Exists(manifestPath))
            {
                string text = File.ReadAllText(manifestPath); hash += Sha1(text);
                var manifest = JObject.Parse(text);
                foreach (JObject e in (JArray)manifest["events"])
                {
                    string id = (string)e["id"]; var files = ((JArray)e["files"]).Select(f => (string)f).ToList();
                    // the audio agent's note: the first take of the screw loop pulses, use the second
                    if (id == "asm.screw.turn" && files.Any(f => f.Contains("-02"))) files = files.Where(f => f.Contains("-02")).ToList();
                    var clips = new List<AudioClip>();
                    foreach (var f in files) { var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(f); if (clip) clips.Add(clip); else missing.Add(f); }
                    var range = e["pitch_range"] as JArray;
                    events.Add(new AssemblyAudioTable.Event { id = id, clips = clips.ToArray(), loop = e["loop"] != null && e["loop"].Type == JTokenType.Boolean && (bool)e["loop"], volume = 1,
                        pitchRange = range != null && range.Count == 2 ? new Vector2((float)range[0], (float)range[1]) : new Vector2(.97f, 1.03f) });
                }
                if (manifest["contact_matrix"] is JObject matrix)
                    foreach (var cell in matrix) { var key = cell.Key.Split('|'); if (key.Length == 2 && cell.Value.Type == JTokenType.String) contacts.Add(new AssemblyAudioTable.Contact { part = key[0], surface = key[1], eventId = (string)cell.Value }); }
            }
            if (File.Exists(linesPath))
            {
                string text = File.ReadAllText(linesPath); hash += Sha1(text);
                foreach (JObject l in (JArray)JObject.Parse(text)["lines"])
                {
                    string file = (string)l["file"]; var clip = string.IsNullOrEmpty(file) ? null : AssetDatabase.LoadAssetAtPath<AudioClip>(file);
                    if (!clip && !string.IsNullOrEmpty(file)) missing.Add(file);
                    lines.Add(new AssemblyAudioTable.Line { id = (string)l["id"], speaker = (string)l["speaker"] ?? "npc_brann", trigger = (string)l["trigger"] ?? "", text = (string)l["text"] ?? "", clip = clip });
                }
            }
            table.events = events.ToArray(); table.lines = lines.ToArray(); table.contacts = contacts.ToArray(); table.sourceHash = hash;
            EditorUtility.SetDirty(table); AssetDatabase.SaveAssets();
            return new { asset = AudioPath, events = events.Count, withClips = events.Count(e => e.clips.Length > 0), clips = events.Sum(e => e.clips.Length), lines = lines.Count, voiced = lines.Count(l => l.clip), contacts = contacts.Count, missingFiles = missing.Count, firstMissing = missing.Take(5) };
        }

        static object Settings()
        {
            bool had = AssetDatabase.LoadAssetAtPath<AssemblySettings>(SettingsPath);
            LoadOrCreate<AssemblySettings>(SettingsPath); AssetDatabase.SaveAssets();
            return new { asset = SettingsPath, created = !had };
        }

        static string SourcesPath => Path.Combine(ArtDir, "data/sources.json");
        static string Glb(string family) => AssemblyKitBuilder.ArtDir + char.ToUpperInvariant(family[0]) + family.Substring(1) + "/" + family + ".glb";
        static string[] Arg(string name) { var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, name); return i >= 0 && i + 1 < args.Length ? args[i + 1].Split(',') : new string[0]; }
        /// Which families are bound from their art and which are stand-ins: art/steady_hands_bench_20261120/data/sources.json
        /// ({"sources": {"pistol": "real", "fixtures": "greybox", ...}}; the integration pass owns what it says, a family it does not name
        /// is a stand-in). For one run, `--real a,b` makes those real as well and `--greybox a,b` (or `all`) makes those stand-ins
        /// whatever the file says. So a re-install keeps the real families without anyone remembering a flag.
        static Dictionary<string, string> Sources(out JObject how)
        {
            var real = new HashSet<string>(Arg("--real")); var grey = new HashSet<string>(Arg("--greybox"));
            var file = File.Exists(SourcesPath) ? JObject.Parse(File.ReadAllText(SourcesPath)) : new JObject();
            if (file["sources"] is JObject inner) file = inner;   // {"about": "...", "sources": {family: "real" | "greybox"}} or the families at the top
            var sources = new Dictionary<string, string>(); how = new JObject();
            foreach (var family in AssemblyKitBuilder.Families)
            {
                string said = file[family] != null && file[family].Type == JTokenType.String ? (string)file[family] : "greybox", why = file[family] != null ? "data/sources.json" : "not named in data/sources.json";
                if (real.Contains(family)) { said = "real"; why = "--real"; }
                if (grey.Contains(family) || grey.Contains("all")) { said = "greybox"; why = "--greybox"; }
                if (said != "real" && said != "greybox") throw new Exception($"data/sources.json: {family} is \"{said}\"; it must be \"real\" or \"greybox\"");
                if (said == "real" && !File.Exists(Glb(family))) throw new Exception($"{family} is to be real ({why}) but there is no model at {Glb(family)}");
                sources[family] = said == "real" ? Glb(family) : "greybox"; how[family] = said + " (" + why + ")";
            }
            foreach (var name in real.Concat(grey)) if (name != "all" && Array.IndexOf(AssemblyKitBuilder.Families, name) < 0) throw new Exception("no such family: " + name);
            return sources;
        }
        static AssemblyKitBuilder.BenchSpec Spec(Dictionary<string, string> sources, bool scratch)
        {
            var spec = new AssemblyKitBuilder.BenchSpec
            {
                layout = JObject.Parse(File.ReadAllText(LayoutPath)), scratch = scratch,
                recipe = AssetDatabase.LoadAssetAtPath<AssemblyRecipe>(RecipePath), settings = AssetDatabase.LoadAssetAtPath<AssemblySettings>(SettingsPath),
                audio = AssetDatabase.LoadAssetAtPath<AssemblyAudioTable>(AudioPath), hudStyle = AssetDatabase.LoadAssetAtPath<UnityEngine.UIElements.StyleSheet>(StylePath),
                mixer = AssetDatabase.LoadAssetAtPath<AudioMixer>(MixerPath)?.FindMatchingGroups("SFX").FirstOrDefault(),
            };
            if (!spec.recipe || !spec.settings || !spec.audio) throw new Exception("Run the recipe, audio and settings steps first.");
            foreach (var pair in sources) spec.sources[pair.Key] = pair.Value;
            return spec;
        }

        static object Prefab()
        {
            var spec = Spec(Sources(out var how), false);
            bool anyReal = spec.sources.Values.Any(x => x != "greybox");
            var go = AssemblyKitBuilder.BuildBench(spec);
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(PrefabPath));
                PrefabUtility.SaveAsPrefabAsset(go, PrefabPath, out bool ok);
                if (!ok) throw new Exception("Could not save " + PrefabPath);
                if (!anyReal) { PrefabUtility.SaveAsPrefabAsset(go, StandInPrefabPath, out ok); if (!ok) throw new Exception("Could not save " + StandInPrefabPath); }
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }
            var bindOfInstalled = AssemblyKitBuilder.LastReport;
            if (anyReal)
            {
                // the stand-in bench beside it (the bench's own tests play this one)
                var grey = Spec(AssemblyKitBuilder.Families.ToDictionary(f => f, f => "greybox"), false); var standIn = AssemblyKitBuilder.BuildBench(grey);
                try { PrefabUtility.SaveAsPrefabAsset(standIn, StandInPrefabPath, out bool ok2); if (!ok2) throw new Exception("Could not save " + StandInPrefabPath); }
                finally { UnityEngine.Object.DestroyImmediate(standIn); }
                var greyProblems = grey.log.Where(l => l.Contains("not found") || l.Contains("missing") || l.Contains("no ") || l.Contains("unknown")).ToList();
                if (greyProblems.Count > 0) throw new Exception("stand-in bench build: " + string.Join("; ", greyProblems));
            }
            AssetDatabase.SaveAssets();
            var problems = spec.log.Where(l => l.Contains("not found") || l.Contains("missing") || l.Contains("no ") || l.Contains("unknown")).ToList();
            if (problems.Count > 0) throw new Exception("bench build: " + string.Join("; ", problems));
            var bind = bindOfInstalled;
            return new { prefab = PrefabPath, standInPrefab = StandInPrefabPath, spec.sources, sourcesFrom = how, spec.log, hudStyle = (bool)spec.hudStyle, mixer = spec.mixer ? spec.mixer.name : null,
                placesOnMarks = bind.boundPlaces, placesOnPoseMarks = bind.posePlaces, placesFromLayout = bind.fallbackPlaces.Count, bind.notes, bind.problems, bind.clips, bind.shots, bind.standIns };
        }

        // ------------------------------------------------------------------ scene
        class Rec { public bool interiorRootAdded; public string interiorLighting; public bool landmarkAdded; public string installed; }
        static Rec LoadRec() => File.Exists(RecordPath) ? JsonConvert.DeserializeObject<Rec>(File.ReadAllText(RecordPath)) : new Rec();
        static void SaveRec(Rec r) { Directory.CreateDirectory(Path.GetDirectoryName(RecordPath)); File.WriteAllText(RecordPath, JsonConvert.SerializeObject(r, Formatting.Indented)); }

        static Transform Workbench(Scene scene)
        {
            var shop = scene.GetRootGameObjects().FirstOrDefault(g => g.name == ShopRoot) ?? throw new Exception("No scene root " + ShopRoot);
            var station = shop.GetComponentsInChildren<CraftingStationMarker>(true).FirstOrDefault(m => m.stationId == "station_field_fabricator");
            // the instance is named "Workbench" in the scene: find it by the prefab it comes from
            var benches = shop.GetComponentsInChildren<Transform>(true).Where(t => t.gameObject.activeInHierarchy && PrefabUtility.IsAnyPrefabInstanceRoot(t.gameObject)
                && (AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject)) ?? "").EndsWith("/SS_Workbench.prefab")).ToList();
            if (benches.Count == 0) benches = shop.GetComponentsInChildren<Transform>(true).Where(t => (t.name == "Workbench" || t.name.StartsWith("SS_Workbench")) && t.gameObject.activeInHierarchy).ToList();
            if (benches.Count == 0) throw new Exception("No SS_Workbench instance under " + ShopRoot);
            return station ? benches.OrderBy(t => Vector3.Distance(t.position, station.transform.position)).First() : benches[0];
        }

        static object SceneStep()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath) ?? throw new Exception("Build the prefab first: " + PrefabPath);
            var rec = LoadRec();
            var workbench = Workbench(scene);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (root && PrefabUtility.GetCorrespondingObjectFromSource(root) != prefab) { UnityEngine.Object.DestroyImmediate(root); root = null; }
            if (!root) { root = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene); root.name = RootName; }
            root.transform.SetPositionAndRotation(workbench.position, workbench.rotation);
            root.transform.localScale = Vector3.one;
            // the shop's interior ambient and its lamps (rendering layer 7): every renderer under one of the interior roots
            var shop = scene.GetRootGameObjects().First(g => g.name == ShopRoot);
            var il = shop.GetComponentInChildren<InteriorLighting>(true);
            if (il && !il.interiorRoots.Contains(root.transform))
            {
                il.interiorRoots = il.interiorRoots.Where(t => t).Append(root.transform).ToArray();
                rec.interiorRootAdded = true; rec.interiorLighting = PathOf(il.transform); EditorUtility.SetDirty(il);
            }
            var bridge = UnityEngine.Object.FindAnyObjectByType<AthenDebugBridge>(FindObjectsInactive.Include);
            if (bridge && bridge.landmarks)
            {
                var lm = bridge.landmarks.Find(Landmark);
                if (!lm) { lm = new GameObject(Landmark).transform; lm.SetParent(bridge.landmarks, false); rec.landmarkAdded = true; }
                var use = workbench.Find("Use point");
                lm.position = use ? use.position : workbench.TransformPoint(new Vector3(0, 0, 1.083f));
                EditorUtility.SetDirty(bridge.landmarks);
            }
            rec.installed = DateTime.Now.ToString("yyyy-MM-dd HH:mm");
            SaveRec(rec);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return new { root = RootName, at = new[] { root.transform.position.x, root.transform.position.y, root.transform.position.z }, yaw = root.transform.eulerAngles.y, workbench = PathOf(workbench), interiorLighting = il ? PathOf(il.transform) : null, landmark = Landmark };
        }

        static object Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath); var rec = LoadRec(); var log = new List<string>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            foreach (var il in UnityEngine.Object.FindObjectsByType<InteriorLighting>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (root && il.interiorRoots.Contains(root.transform)) { il.interiorRoots = il.interiorRoots.Where(t => t && t != root.transform).ToArray(); EditorUtility.SetDirty(il); log.Add("interior root removed from " + PathOf(il.transform)); }
            if (root) { UnityEngine.Object.DestroyImmediate(root); log.Add("root " + RootName); }
            var bridge = UnityEngine.Object.FindAnyObjectByType<AthenDebugBridge>(FindObjectsInactive.Include);
            if (rec.landmarkAdded && bridge && bridge.landmarks) { var lm = bridge.landmarks.Find(Landmark); if (lm) { UnityEngine.Object.DestroyImmediate(lm.gameObject); EditorUtility.SetDirty(bridge.landmarks); log.Add("landmark " + Landmark); } }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            if (File.Exists(RecordPath)) File.Move(RecordPath, RecordPath.Replace(".json", "-rolledback-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".json"));
            var r = new { restored = log, note = "Assets under Data/Assembly stay; the Bench input map and the code are untouched." };
            WriteEvidence("rollback.json", r);
            return r;
        }

        // ------------------------------------------------------------------ verify
        /// The Bench action map of DESIGN.md section 5: action -> binding paths.
        static readonly Dictionary<string, string[]> BenchBindings = new Dictionary<string, string[]>
        {
            { "Pointer", new[] { "<Mouse>/position" } }, { "Delta", new[] { "<Mouse>/delta" } },
            { "Navigate", new[] { "<Keyboard>/w", "<Keyboard>/s", "<Keyboard>/a", "<Keyboard>/d", "<Keyboard>/upArrow", "<Keyboard>/downArrow", "<Keyboard>/leftArrow", "<Keyboard>/rightArrow" } },
            { "Next", new[] { "<Keyboard>/tab" } }, { "Primary", new[] { "<Mouse>/leftButton" } }, { "PrimaryKey", new[] { "<Keyboard>/space", "<Keyboard>/enter", "<Keyboard>/numpadEnter" } },
            { "Scroll", new[] { "<Mouse>/scroll/y" } }, { "Rotate", new[] { "<Keyboard>/q", "<Keyboard>/e" } }, { "Flip", new[] { "<Mouse>/middleButton", "<Keyboard>/r" } },
            { "PutBack", new[] { "<Keyboard>/x" } }, { "Look", new[] { "<Mouse>/rightButton" } }, { "LookKey", new[] { "<Keyboard>/leftShift" } },
            { "Zoom", new[] { "<Keyboard>/c", "<Keyboard>/z" } }, { "Hint", new[] { "<Keyboard>/h" } }, { "Abandon", new[] { "<Keyboard>/backspace" } },
        };

        static void VerifyInput(List<string> problems, JObject report)
        {
            var input = JObject.Parse(File.ReadAllText(InputPath));
            var maps = input["maps"].Children<JObject>().ToList();
            var bench = maps.FirstOrDefault(m => (string)m["name"] == "Bench");
            if (bench == null) { problems.Add("Controls.inputactions has no Bench map (run art/steady_hands_bench_20261120/bench/apply_input.py)"); return; }
            var ids = maps.Select(m => (string)m["id"]).Concat(maps.SelectMany(m => m["actions"].Children<JObject>()).Select(a => (string)a["id"])).Concat(maps.SelectMany(m => m["bindings"].Children<JObject>()).Select(b => (string)b["id"])).ToList();
            var repeated = ids.GroupBy(x => x).Where(g => g.Count() > 1).Select(g => g.Key).ToList();
            if (repeated.Count > 0) problems.Add("duplicate ids in Controls.inputactions: " + string.Join(", ", repeated.Take(4)));
            var actions = bench["actions"].Children<JObject>().Select(a => (string)a["name"]).ToList();
            foreach (var want in BenchBindings.Keys) if (!actions.Contains(want)) problems.Add("Bench map lacks action " + want);
            foreach (var extra in actions.Where(a => !BenchBindings.ContainsKey(a))) problems.Add("Bench map has an unexpected action " + extra);
            var bound = bench["bindings"].Children<JObject>().Where(b => !((bool?)b["isComposite"] ?? false)).Select(b => ((string)b["action"], (string)b["path"])).ToList();
            foreach (var pair in BenchBindings) foreach (var path in pair.Value) if (!bound.Contains((pair.Key, path))) problems.Add($"Bench/{pair.Key} is not bound to {path}");
            // one key, one meaning at the bench
            foreach (var g in bound.GroupBy(b => b.Item2).Where(g => g.Select(x => x.Item1).Distinct().Count() > 1)) problems.Add($"{g.Key} is bound to more than one Bench action: {string.Join(", ", g.Select(x => x.Item1).Distinct())}");
            // Esc steps back through the always-on UI map; nothing at the bench may sit on Esc or M
            foreach (var b in bound.Where(b => b.Item2 == "<Keyboard>/escape" || b.Item2 == "<Keyboard>/m")) problems.Add($"Bench/{b.Item1} is bound to {b.Item2}, which the UI map owns");
            report["benchActions"] = new JArray(actions); report["benchBindings"] = bound.Count;
        }

        /// Plays the job on paper: first open action, done, until complete. Also every fault that starts a recovery.
        static void VerifyGraph(AssemblyRecipeData data, List<string> problems, JObject report)
        {
            foreach (var p in data.Validate()) problems.Add("recipe: " + p);
            bool Finish(AssemblyJob job, out int actions)
            {
                actions = 0;
                for (int guard = 0; guard < 2000 && !job.Complete; guard++)
                {
                    var open = job.OpenActions.ToList();
                    if (open.Count > 0) { job.CompleteAction(open[0].step.id, open[0].action.key, 1); actions++; continue; }
                    var empty = job.OpenSteps.FirstOrDefault(s => s.actions.Length == 0);
                    if (empty == null) return false;
                    job.CompleteStep(empty.id);
                }
                return job.Complete;
            }
            var plain = new AssemblyJob(data);
            if (!Finish(plain, out int count)) problems.Add("the job cannot be completed: stuck at stage " + plain.StageIndex + " with open steps " + string.Join(",", plain.OpenSteps.Select(s => s.id)));
            report["actionsToComplete"] = count; report["scoreOfPerfectRun"] = plain.Score;
            int recoveries = 0;
            foreach (var step in data.Steps) foreach (var a in step.actions) foreach (var f in a.faults.Where(f => !string.IsNullOrEmpty(f.recovery)))
            {
                var job = new AssemblyJob(data);
                for (int guard = 0; guard < 2000 && job.State(step.id) != AssemblyStepState.Available && job.State(step.id) != AssemblyStepState.Active; guard++)
                {
                    var open = job.OpenActions.ToList(); if (open.Count > 0) { job.CompleteAction(open[0].step.id, open[0].action.key, 1); continue; }
                    var empty = job.OpenSteps.FirstOrDefault(s => s.actions.Length == 0); if (empty == null) break; job.CompleteStep(empty.id);
                }
                string started = null; for (int i = 0; i < Mathf.Max(1, f.after); i++) started = job.Fault(step.id, a.key, f.kind).recoveryStarted ?? started;
                if (started != f.recovery) { problems.Add($"{step.id}:{a.key} fault {f.kind} did not start {f.recovery}"); continue; }
                if (!Finish(job, out _)) problems.Add($"after fault {f.kind} on {step.id}:{a.key} the job cannot be completed");
                else if (!job.IsDone(f.recovery)) problems.Add($"recovery {f.recovery} was not needed to finish after {f.kind}");
                recoveries++;
            }
            report["recoveriesChecked"] = recoveries;
        }

        /// SEAM.md section 4: each part of an exported family lists the design steps that touch it. Where the step table and
        /// that list disagree it is a warning for whoever owns the row, never a failure.
        static JArray CrossCheck(AssemblyRecipeData data, AssemblyBench bench)
        {
            var mine = new Dictionary<string, HashSet<string>>();   // part id -> steps of the table that refer to it
            void Touch(string step, string id) { if (string.IsNullOrEmpty(id)) return; if (!mine.TryGetValue(id, out var set)) mine[id] = set = new HashSet<string>(); set.Add(step); }
            void Target(string step, string t)
            {
                if (string.IsNullOrEmpty(t) || t == "seat" || t == "start" || t == "clear" || t == "gone") return;
                var m = bench.Marker(t); if (m) Touch(step, m.ownerPart); else if (bench.Part(t)) Touch(step, t);
            }
            void Effect(string step, string e)
            {
                e = AssemblyBench.EffectBody(e); int at = e.IndexOf('>');
                if (e.StartsWith("~")) { int eq = e.IndexOf('='); Target(step, eq > 0 ? e.Substring(1, eq - 1) : e.Substring(1)); return; }
                if (at > 0) { Touch(step, e.Substring(0, at)); Target(step, e.Substring(at + 1)); return; }
                at = e.IndexOf('='); if (at > 0 && bench.Part(e.Substring(0, at))) Touch(step, e.Substring(0, at));   // a lamp
            }
            foreach (var step in data.Steps)
            {
                string id = step.recovery && step.id.EndsWith(".r") ? step.id.Substring(0, step.id.Length - 2) : step.id;
                foreach (var e in step.effects) Effect(id, e);
                foreach (var a in step.actions)
                {
                    Touch(id, a.part); Target(id, a.target); foreach (var t in a.targets) Target(id, t);
                    if (!string.IsNullOrEmpty(a.tool) && a.tool != "*") { var tool = bench.Tool(a.tool); if (tool) Touch(id, tool.id); }
                    foreach (var e in a.effects) Effect(id, e); foreach (var f in a.faults) foreach (var e in f.effects) Effect(id, e);
                }
            }
            var warnings = new JArray();
            foreach (var family in AssemblyKitBuilder.Families)
            {
                string path = Path.Combine(ArtDir, family, "export/parts.json"); if (!File.Exists(path)) continue;
                foreach (JObject e in (JArray)JObject.Parse(File.ReadAllText(path))["parts"])
                {
                    string id = (string)e["id"]; if (!(e["steps"] is JArray listed)) continue;
                    var theirs = new HashSet<string>(listed.Select(x => (string)x)); mine.TryGetValue(id, out var ours); ours = ours ?? new HashSet<string>();
                    var onlyTable = ours.Where(x => !theirs.Contains(x)).OrderBy(x => x).ToList(); var onlyArt = theirs.Where(x => !ours.Contains(x)).OrderBy(x => x).ToList();
                    if (onlyTable.Count > 0) warnings.Add($"{id}: the table handles it in {string.Join(", ", onlyTable)}, which its parts.json does not list");
                    if (onlyArt.Count > 0) warnings.Add($"{id}: its parts.json lists {string.Join(", ", onlyArt)}, where the table does not handle it");
                }
            }
            return warnings;
        }

        static object Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var problems = new List<string>(); var report = new JObject();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            var recipe = AssetDatabase.LoadAssetAtPath<AssemblyRecipe>(RecipePath);
            if (!prefab) problems.Add("missing " + PrefabPath);
            if (!recipe) problems.Add("missing " + RecipePath);
            if (!root) problems.Add("no scene root " + RootName);
            if (recipe)
            {
                string text = File.Exists(StepsPath) ? File.ReadAllText(StepsPath) : "";
                if (recipe.sourceHash != Sha1(text)) problems.Add("the recipe asset is not generated from the current steps.json (run the recipe step)");
                VerifyGraph(recipe.data, problems, report);
                report["steps"] = recipe.data.Steps.Count(); report["designRows"] = recipe.data.Steps.Count(s => !s.recovery); report["actions"] = recipe.data.Steps.Sum(s => s.actions.Length);
                report["stagesWithActions"] = new JArray(recipe.data.stages.Where(s => s.steps.Any(st => st.actions.Length > 0)).Select(s => s.id));
            }
            VerifyInput(problems, report);
            if (root && recipe)
            {
                if (PrefabUtility.GetCorrespondingObjectFromSource(root) != prefab) problems.Add("the scene root is not an instance of " + PrefabPath);
                if (PrefabUtility.IsPrefabAssetMissing(root)) problems.Add("the scene root's prefab is missing");
                var bench = root.GetComponent<AssemblyBench>(); var session = root.GetComponent<AssemblySession>();
                if (!bench || !session) problems.Add("the root lacks AssemblyBench or AssemblySession");
                else
                {
                    bench.Index(true);
                    if (bench.recipe != recipe) problems.Add("the bench does not use " + RecipePath);
                    if (!bench.settings) problems.Add("the bench has no settings asset");
                    if (!bench.audioTable) problems.Add("the bench has no audio table");
                    if (!bench.hudStyle) problems.Add("the bench has no HUD stylesheet");
                    if (!bench.mixerGroup) problems.Add("the bench has no mixer group");
                    if (!bench.ghostMaterial || !bench.lineMaterial) problems.Add("the bench lacks its hint materials");
                    if (!bench.surface || !bench.loose || !bench.cameraRoot) problems.Add("the bench lacks its surface, loose container or camera root");
                    if (!root.transform.Find("Aim dot")) problems.Add("no Aim dot");
                    // every reference of every action resolves on the bench
                    int refs = 0;
                    void Effect(string where, string e)
                    {
                        if (e.StartsWith("@")) { int c = e.IndexOf(':'); string mark = c > 1 ? e.Substring(1, c - 1) : ""; if (!bench.Marker(mark)) problems.Add($"{where}: effect tied to an unknown mark: {e}"); }
                        e = AssemblyBench.EffectBody(e);
                        refs++; int at = e.IndexOf('>');
                        if (e.StartsWith("~")) { int eq = e.IndexOf('='); string wipe = eq > 0 ? e.Substring(1, eq - 1) : e.Substring(1); if (Array.IndexOf(bench.wipeIds, wipe) < 0) problems.Add($"{where}: effect reveals a wipe the bench does not have: {e}"); return; }
                        if (at > 0) { if (!bench.Part(e.Substring(0, at))) problems.Add($"{where}: effect part missing: {e}"); string to = e.Substring(at + 1); if (to != "gone" && to != "seat" && to != "clear" && to != "start" && !bench.Marker(to)) problems.Add($"{where}: effect place missing: {e}"); }
                        else { at = e.IndexOf('='); if (at <= 0 || !bench.Param(e.Substring(0, at)) && !bench.lamps.Any(l => l.part == e.Substring(0, at) && bench.Part(l.part))) problems.Add($"{where}: effect mechanism or lamp missing: {e}"); }
                    }
                    foreach (var step in recipe.data.Steps)
                    {
                        foreach (var e in step.effects) Effect(step.id, e);
                        foreach (var a in step.actions)
                        {
                            string where = step.id + ":" + a.key; refs++;
                            var part = bench.Part(a.part);
                            if (!string.IsNullOrEmpty(a.part) && !part) problems.Add($"{where}: part {a.part} missing");
                            if (!string.IsNullOrEmpty(a.tool) && a.tool != "*" && !bench.Tool(a.tool)) problems.Add($"{where}: no tool {a.tool}");
                            if (!string.IsNullOrEmpty(a.toolMode) && bench.Tool(a.tool) && !bench.Tool(a.tool).modes.Contains(a.toolMode) && !bench.Parts.Any(b => b.BitKind == a.toolMode)) problems.Add($"{where}: tool {a.tool} has no mode or bit {a.toolMode}");
                            if (!string.IsNullOrEmpty(a.target) && a.target != "seat" && a.target != "start" && a.target != "clear" && !bench.Marker(a.target) && !bench.Part(a.target)) problems.Add($"{where}: target {a.target} missing");
                            foreach (var t in a.targets) if (!bench.Marker(t)) problems.Add($"{where}: mark {t} missing");
                            if (!string.IsNullOrEmpty(a.drive) && !bench.Param(a.drive) && !(a.mode == "sustain" && bench.lamps.Any(l => l.part == a.drive))) problems.Add($"{where}: mechanism {a.drive} missing");
                            if (a.verb == AssemblyVerbKind.Wipe && (!bench.Marker(a.target) || bench.Marker(a.target).kind != AssemblyMarkerKind.Zone)) problems.Add($"{where}: {a.target} is not a wipe zone");
                            foreach (var f in a.faults) if (f.when != null && f.when.StartsWith("poor:") && recipe.data.Steps.All(s => s.id != f.when.Substring(5))) problems.Add($"{where}: fault {f.kind} checks an unknown step {f.when}");
                            foreach (var f in a.faults) if (f.when != null && f.when.StartsWith("wrong:") && !bench.Part(f.when.Substring(6))) problems.Add($"{where}: fault {f.kind} names an unknown part {f.when}");
                            if (a.verb == AssemblyVerbKind.Seat && part && (a.target == "seat" || a.target == "start" || a.target == "clear") && !part.hasClear) problems.Add($"{where}: {a.part} has no clear pose");
                            if (a.verb == AssemblyVerbKind.Seat && part && bench.Marker(a.target) && bench.Marker(a.target).kind == AssemblyMarkerKind.Place && !bench.Marker(a.target).Accepts(a.part)) problems.Add($"{where}: {a.target} does not accept {a.part}");
                            if (a.verb == AssemblyVerbKind.Path && (!bench.Marker(a.target) || bench.Marker(a.target).points.Length < 2)) problems.Add($"{where}: path {a.target} has fewer than two points");
                            if (!string.IsNullOrEmpty(a.shot) && !bench.cameraRoot.Find("cam_bench_" + a.shot)) problems.Add($"{where}: no shot {a.shot}");
                            foreach (var e in a.effects) Effect(where, e);
                            foreach (var f in a.faults) foreach (var e in f.effects) Effect(where, e);
                        }
                    }
                    foreach (var stage in recipe.data.stages) if (!bench.cameraRoot.Find("cam_bench_" + stage.shot)) problems.Add($"stage {stage.id}: no shot {stage.shot}");
                    foreach (var p in bench.Parts)
                    {
                        if (!string.IsNullOrEmpty(p.homePlace) && p.homePlace != "gone" && !bench.Marker(p.homePlace)) problems.Add($"{p.id}: home place {p.homePlace} missing");
                        if (!p.restParent) problems.Add($"{p.id}: no rest parent recorded");
                        foreach (var h in p.heldBy) if (!bench.Part(h) && !bench.Param(h)) problems.Add($"{p.id}: held by unknown {h}");
                        if (p.IsTool && !p.tip) problems.Add($"{p.id}: tool without a tip");
                    }
                    // (laying a job onto the bench is checked on a plain copy by selftest and the Edit Mode tests: in the Editor a prefab
                    // instance's children cannot be reparented, so it cannot be done on the scene's own instance here)
                    report["parts"] = bench.Parts.Count(); report["markers"] = bench.Markers.Count(); report["places"] = bench.Markers.Count(m => m.kind == AssemblyMarkerKind.Place);
                    report["mechanisms"] = bench.Params.Count(); report["references"] = refs;
                    report["families"] = new JArray(bench.Parts.Select(p => p.id.Split('.')[0]).Distinct().OrderBy(x => x));
                    report["placesWithNoMark"] = new JArray(bench.Markers.Where(m => m.kind == AssemblyMarkerKind.Place && !m.id.Contains("/")).Select(m => m.id).OrderBy(x => x));
                    report["stepCrossCheck"] = CrossCheck(recipe.data, bench);
                    // sound: which events the job asks for have clips, which lines can be said
                    // the events each action can ask for: its loop and done sounds; a strike's .strike and .miss, a hold's .seat; else its own
                    var asked = recipe.data.Steps.SelectMany(s => s.actions).SelectMany(a => a.audio.Length == 0 ? new[] { a.loop, a.done }
                            : a.verb == AssemblyVerbKind.Window ? (a.mode == "strike" ? new[] { a.loop, a.done, a.audio + ".strike", a.audio + ".miss" } : new[] { a.loop, a.done, a.audio + ".seat" })
                            : new[] { a.loop, a.done, a.audio })
                        .Where(x => !string.IsNullOrEmpty(x)).Distinct().OrderBy(x => x).ToList();
                    report["eventsAsked"] = asked.Count; report["eventsSilent"] = new JArray(asked.Where(id => { var e = bench.audioTable.Find(id); return e == null || e.clips.Length == 0; }));
                    report["audioEvents"] = bench.audioTable.events.Length; report["audioClips"] = bench.audioTable.events.Sum(e => e.clips.Length);
                    report["lines"] = bench.audioTable.lines.Length; report["linesVoiced"] = bench.audioTable.lines.Count(l => l.clip);
                }
                var cams = root.GetComponentsInChildren<Camera>(true);
                if (cams.Any(c => c.enabled)) problems.Add("a review camera is enabled");
                if (cams.Any(c => !c.name.StartsWith("cam_bench_"))) problems.Add("a camera under the root is not named cam_bench_*");
                report["cameras"] = new JArray(cams.Select(c => c.name));
                var renderers = root.GetComponentsInChildren<Renderer>(true);
                int noMaterial = renderers.Count(r => r.sharedMaterials.Any(m => !m)), offLayer = renderers.Count(r => (r.renderingLayerMask & (1u << 7)) == 0);
                if (noMaterial > 0) problems.Add(noMaterial + " renderers under the root lack a material");
                if (offLayer > 0) problems.Add(offLayer + " renderers under the root are not on rendering layer 7 (the shop's lamps)");
                report["renderers"] = renderers.Length;
                report["triangles"] = renderers.Select(r => r.GetComponent<MeshFilter>()).Where(f => f && f.sharedMesh).Sum(f => f.sharedMesh.triangles.Length / 3);
                var il = UnityEngine.Object.FindObjectsByType<InteriorLighting>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(i => i.interiorRoots.Contains(root.transform));
                if (!il) problems.Add("the root is not one of an InteriorLighting's interior roots");
                var workbench = Workbench(scene);
                if (Vector3.Distance(root.transform.position, workbench.position) > .001f || Quaternion.Angle(root.transform.rotation, workbench.rotation) > .01f) problems.Add("the root is not at the workbench's transform");
                report["at"] = new JArray(root.transform.position.x, root.transform.position.y, root.transform.position.z);
                var mods = PrefabUtility.GetPropertyModifications(root) ?? new PropertyModification[0];
                report["instanceOverrides"] = mods.Count(m => m.target && !(m.target is Transform) && m.propertyPath != "m_Name");
            }
            var bridge = UnityEngine.Object.FindAnyObjectByType<AthenDebugBridge>(FindObjectsInactive.Include);
            if (!bridge || !bridge.landmarks || !bridge.landmarks.Find(Landmark)) problems.Add("landmark missing " + Landmark);
            int missingScripts = All(scene).SelectMany(t => t.GetComponents<Component>()).Count(c => c == null);
            if (missingScripts > 0) problems.Add(missingScripts + " missing scripts in the scene");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            bool fingerprint = !chunks || chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            if (!fingerprint) problems.Add("render chunk fingerprint stale");
            if (!scene.GetRootGameObjects().Any(g => g.GetComponentsInChildren<CraftingStationMarker>(true).Any(m => m.stationId == "station_field_fabricator"))) problems.Add("no workbench station station_field_fabricator");
            report["missingScripts"] = missingScripts; report["chunkFingerprintMatches"] = fingerprint;
            // sounds held under a Turn, a Window or a Path: an event the audio package did not make as a loop is struck again and
            // again while the hold lasts (AssemblyAudio.Loop), never looped; an id the package does not have at all is a mistake
            var table = AssetDatabase.LoadAssetAtPath<AssemblyAudioTable>(AudioPath); var recipeAsset = AssetDatabase.LoadAssetAtPath<AssemblyRecipe>(RecipePath);
            if (table && recipeAsset)
            {
                var strokes = new JArray();
                foreach (var st in recipeAsset.data.Steps) foreach (var a in st.actions)
                {
                    if (string.IsNullOrEmpty(a.loop)) continue; var ev = table.Find(a.loop);
                    if (ev == null) problems.Add($"{st.id}:{a.key}: its held sound {a.loop} is not an event of the audio package");
                    else if (!ev.loop) strokes.Add($"{st.id}:{a.key} {a.loop}");
                }
                report["heldSoundsStruckNotLooped"] = strokes;
            }
            // can the player see what every action needs? On a plain copy of the prefab in an empty scene (the walk moves every part)
            var prefabAsset = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefabAsset)
            {
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                prefabAsset = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
                var copy = UnityEngine.Object.Instantiate(prefabAsset); JObject sight;
                try { sight = AssemblySightCheck.Run(copy.GetComponent<AssemblyBench>(), JObject.Parse(File.ReadAllText(LayoutPath)), "the installed prefab"); }
                finally { UnityEngine.Object.DestroyImmediate(copy); }
                Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "sight.json"), sight.ToString(Formatting.Indented));
                report["sight"] = SightSummary(sight, "sight.json");
                if (sight["error"] != null) problems.Add("sight check: " + (string)sight["error"]);
                if (sight["stopped"] != null) problems.Add("sight check: the walk stopped at " + (string)sight["stopped"]);
                if (SightIsStrict) foreach (var f in ((JArray)sight["failures"] ?? new JArray()).GroupBy(x => (string)x["action"])) problems.Add($"sight: {f.Key}: {string.Join("; ", f.Select(x => $"{(string)x["what"]} {(string)x["why"]} in {(string)x["shot"]}"))}");
            }
            report["problems"] = new JArray(problems); report["pass"] = problems.Count == 0;
            Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "verify.json"), report.ToString(Formatting.Indented));
            if (problems.Count > 0) throw new Exception("AssemblyBenchInstall20261120 verify: " + string.Join("; ", problems));
            return new { ok = true, steps = (int)report["steps"], parts = (int?)report["parts"], places = (int?)report["places"] };
        }

        // ------------------------------------------------------------------ selftest
        /// Plays the slice on a copy of the bench in an empty scene with the bot (mouse form, keyboard form, leaving and
        /// returning, the faults and their recoveries). No camera, no player, nothing saved: it proves the session logic
        /// and the data together in about a minute, without the Edit Mode suite. Writes selftest.json.
        static object SelfTest(bool onStandIns = false)
        {
            // --standins plays the stand-in bench (SteadyHandsBenchStandIns.prefab) whatever is installed, and writes selftest-standins.json
            bool standIns = onStandIns || Environment.GetCommandLineArgs().Contains("--standins"); string prefabPath = standIns ? StandInPrefabPath : PrefabPath;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath) ?? throw new Exception("Build the prefab first.");
            var results = new JArray(); int failed = 0;
            // --only TEXT runs just the scenarios whose name contains it (and writes selftest-partial.json)
            string only = Environment.GetCommandLineArgs().SkipWhile(a => a != "--only").Skip(1).FirstOrDefault();
            void Run(string name, Func<AssemblySession, JObject, string> body)
            {
                if (!string.IsNullOrEmpty(only) && !name.Contains(only)) return;
                // a plain copy, not a prefab instance: in the Editor a prefab instance's children cannot be reparented, and the bench moves parts between parents
                var go = UnityEngine.Object.Instantiate(prefab); var session = go.GetComponent<AssemblySession>();
                var o = new JObject { ["name"] = name }; string error; AssemblyBot.Reaims.Clear();
                try { AssemblyCraftLink.ForgetDetached(); error = session.Open(true) ? body(session, o) : "the bench did not open"; }
                catch (Exception e) { error = e.GetType().Name + ": " + e.Message + " @ " + (e.StackTrace ?? "").Split('\n').FirstOrDefault(); }
                o["ok"] = error == null; if (error != null) { o["error"] = error; failed++; }
                if (AssemblyBot.Reaims.Count > 0) o["reaims"] = new JArray(AssemblyBot.Reaims);
                if (session.LastResult != null) o["result"] = new JObject { ["quality"] = session.LastResult.quality.ToString(), ["score"] = session.LastResult.score, ["faults"] = session.LastResult.faults, ["seconds"] = session.LastResult.seconds };
                results.Add(o);
                session.Close(false); UnityEngine.Object.DestroyImmediate(go);
            }
            string Slice(AssemblySession session, JObject o, bool keys)
            {
                var bot = new AssemblyBot(session, keys); bool ok = bot.PlaySlice();
                o["frames"] = bot.Frames; o["actions"] = bot.Log.Count; o["log"] = new JArray(ok ? bot.Log.Skip(Math.Max(0, bot.Log.Count - 4)) : bot.Log);
                o["events"] = session.Audio != null ? session.Audio.Log.Distinct().Count() : 0; o["lines"] = session.Voice != null ? new JArray(session.Voice.Spoken) : null;
                return ok ? null : bot.Error;
            }
            string Whole(AssemblySession session, JObject o, bool keys)
            {
                var viseBase = session.bench.Part("fixtures.vise_base"); var baseAt = viseBase ? new Pose(viseBase.transform.position, viseBase.transform.rotation) : default;
                var bot = new AssemblyBot(session, keys); bool ok = bot.PlayJob();
                // the vise's base stays where it is through the whole job (Carl, 21 Nov: only the body swivels)
                if (viseBase) { float moved = Vector3.Distance(viseBase.transform.position, baseAt.position) * 1000, turned = Quaternion.Angle(viseBase.transform.rotation, baseAt.rotation); o["viseBaseMovedMm"] = Math.Round(moved, 2); o["viseBaseTurnedDeg"] = Math.Round(turned, 2); if (ok && (moved > .5f || turned > .2f)) return $"the vise's base moved {moved:0.0} mm, turned {turned:0.0} degrees"; }
                var crank = session.bench.Param("tools.drill_crank"); if (crank && crank.continuous) o["drillCrankTurns"] = Math.Round(crank.Turns, 2);
                o["frames"] = bot.Frames; o["actions"] = bot.Log.Count; o["log"] = new JArray(bot.Log.Skip(Math.Max(0, bot.Log.Count - (ok ? 4 : 14))));
                o["events"] = session.Audio != null ? session.Audio.Log.Distinct().Count() : 0; o["lines"] = session.Voice != null ? new JArray(session.Voice.Spoken) : null;
                o["asked"] = new JArray(session.VoiceAsked.Where(x => x.StartsWith("stage.start") || x.StartsWith("step.start:s4.press") || x.StartsWith("step.done:s3.spin") || x.StartsWith("step.done:s5.damp")).Distinct());
                if (session.Job != null) o["stepsDoneBelow085"] = new JArray(session.Job.Recipe.Steps.Where(st => session.Job.ActionsDone(st.id) > 0 && session.Job.StepPrecision(st.id) < .85f).Select(st => $"{st.id} {session.Job.StepPrecision(st.id):0.00}"));
                o["faultLog"] = new JArray(bot.Log.Where(l => l.Contains("put off") || l.Contains("instead")));
                return ok ? null : bot.Error;
            }
            Run("whole job, mouse", (s, o) => Whole(s, o, false));
            Run("whole job, keyboard", (s, o) => Whole(s, o, true));
            Run("slice, mouse", (s, o) => Slice(s, o, false));
            Run("slice, keyboard", (s, o) => Slice(s, o, true));
            Run("leave and return", (s, o) =>
            {
                var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s1.screw_a:turn")) return bot.Error;
                int done = s.Job.Recipe.Steps.Count(st => s.Job.IsDone(st.id));
                s.Close(true);
                if (!s.Open(true)) return "the bench did not reopen";
                if (s.Job.Recipe.Steps.Count(st => s.Job.IsDone(st.id)) != done) return "finished steps were lost on returning";
                if (s.bench.Part("pistol.wrap").place != "fixtures.partsmat/seat_pistol_wrap" || s.bench.Part("pistol.frame").place != "fixtures.vise/seat_work") return "the bench was not rebuilt as it was left";
                o["doneSteps"] = done;
                bot = new AssemblyBot(s, false); return bot.PlaySlice() ? null : bot.Error;
            });
            Run("leave and return after the grant", (s, o) =>
            {
                var bot = new AssemblyBot(s, false);
                if (!bot.PlayThrough(1)) return bot.Error;
                s.DevGrant(new[] { "s2", "s3", "s4", "s5" }, .9f);
                if (s.Job.StageIndex != 6) return "the grant did not reach the fit";
                s.Close(true);
                if (!s.Open(true)) return "the bench did not reopen";
                if (s.Job.StageIndex != 6) return "steps that have nothing to do were lost on returning (stage " + s.Job.StageIndex + ")";
                if (s.bench.Part("grip.core").place != "fixtures.workmat/seat_grip" || s.bench.Part("pistol.frame").place != "fixtures.cradle/seat_frame") return "the bench was not rebuilt as it was left";
                bot = new AssemblyBot(s, true); return bot.PlayThrough() && s.LastResult != null ? null : bot.Error ?? "the job did not finish";
            });
            Run("wrong bit cams out", (s, o) =>
            {
                var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s1.screw_a:turn") || !bot.Take("tool:screwdriver")) return bot.Error;
                bot.Flip(); if (!bot.Press("pistol.screw_grip_a")) return bot.Error;
                if (s.Job.FaultsOn("s1.screw_a", "camout") != 1) return "no cam-out was recorded with the cross bit";
                if (s.Job.ActionDone("s1.screw_a", "turn")) return "the screw came out with the wrong bit";
                bot.Flip(); return bot.PlaySlice() ? (s.LastResult.faults >= 1 ? null : "the fault was not in the result") : bot.Error;
            });
            Run("forcing the seized screw", (s, o) =>
            {
                var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s1.screw_b:oil") || !bot.Take("tool:screwdriver")) return bot.Error;
                if (!bot.Press("pistol.screw_grip_b")) return bot.Error;
                if (s.Job.FaultsOn("s1.screw_b", "slip") != 1 || s.Job.State("s1.screw_b.r") != AssemblyStepState.Dormant) return "the first slip should cost quality only";
                if (!bot.Press("pistol.screw_grip_b")) return bot.Error;
                if (s.Job.State("s1.screw_b.r") != AssemblyStepState.Available) return "the second slip did not round the slot (recovery " + s.Job.State("s1.screw_b.r") + ")";
                if (s.Job.CanDo("s1.screw_b", "turn")) return "the screwdriver can still turn a rounded screw";
                if (!bot.PlaySlice()) return bot.Error;
                return s.Job == null || s.LastResult == null ? "no result" : null;
            });
            Run("letting go of the housing", (s, o) =>
            {
                var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s1.housing:slide")) return bot.Error;
                if (!bot.PullAndLetGo("pistol.housing")) return bot.Error;
                if (s.Job.FaultsOn("s1.housing", "flew_off") != 1) return "letting go did not lose the spring";
                if (s.bench.Part("pistol.housing_spring").place != "place.bench.stray") return "the spring is not on the bench";
                if (s.bench.Part("pistol.housing").place != "seat") return "the housing did not stay on its rail";
                return bot.PlaySlice() ? (s.bench.Part("pistol.housing_spring") ? null : null) : bot.Error;
            });
            Run("a part rolls off", (s, o) =>
            {
                var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s0.card_before:pulses")) return bot.Error;
                // the test card says what to do (21 Nov, Carl lost at the card): the action line names it and counts the pulses
                if (s.ActionLine == null || !s.ActionLine.StartsWith("Fire three test pulses") || !s.ActionLine.EndsWith("3 left")) return "no action line at the test card: '" + s.ActionLine + "'";
                if (!s.DevFault("s0.salvage", "rolled_off")) return "the fault was refused";
                if (s.bench.Part("materials.vial").place != "place.bench.stray") return "the vial is not where it rolled";
                return bot.PlaySlice() ? null : bot.Error;
            });
            // ---- the later stages' mistakes and their ways back (DESIGN section 7), and the four of the slice built on 20 Nov
            const AssemblyStepState Av = AssemblyStepState.Available;
            Run("stage 2: the circlip flies, a lead is cut short", (s, o) =>
            {
                s.DevGrant(new[] { "s0", "s1" }, .95f); var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s2.leads:snip")) return bot.Error;
                s.DevFault("s2.leads", "short_lead");
                if (s.Job.State("s3.loop.r") != AssemblyStepState.Locked) return "the splice should wait for stage 3 (it is " + s.Job.State("s3.loop.r") + ")";
                if (!s.VoiceAsked.Contains("fault.first:short_lead")) return "Brann was not asked for fault_short_lead";
                if (!bot.PlayUntil("s2.circlip:spring")) return bot.Error;
                s.DevFault("s2.circlip", "flew_off");
                if (s.Job.State("s2.circlip.r") != Av || s.Job.CanDo("s2.circlip", "spring")) return "the circlip's recovery did not take over";
                if (s.bench.Part("servo.circlip").place != "place.bench.stray") return "the circlip is not on the bench";
                if (!bot.PlayThrough(2)) return bot.Error;
                if (!s.Job.IsDone("s2.circlip") || s.bench.Part("servo.circlip").place != "fixtures.partsmat/seat_servo_circlip") return "the circlip was not found and set down";
                if (!bot.PlayUntil("s3.loop:clip")) return bot.Error;
                return s.Job.IsDone("s3.loop.r") ? null : "the short lead was never spliced";
            });
            Run("stage 3: a careless brush grinds, a cold joint shows at the tester", (s, o) =>
            {
                s.DevGrant(new[] { "s0", "s1", "s2" }, .95f); var bot = new AssemblyBot(s, true);
                if (!bot.PlayUntil("s3.brush:race")) return bot.Error;
                s.DevComplete("s3.brush", null, .55f);
                if (s.bench.Wipe("servo.gimbal_race/race").Coverage < 1) return "a finished wipe did not leave its mask clean";
                if (!bot.PlayUntil("s3.spin:flick") || !bot.PlayNext()) return bot.Error;
                if (s.Job.FaultsOn("s3.spin", "grind") != 1 || s.Job.State("s3.spin.r") != Av || s.Job.CanDo("s3.spin", "flick")) return "the rotor did not grind";
                if (!s.VoiceAsked.Contains("step.fault:s3.spin") || !s.AudioHeard.Contains("asm.spin.grind")) return "no spin_bad line or grind sound";
                if (!bot.PlayUntil("s3.trim:trim")) return bot.Error;
                if (!s.Job.IsDone("s3.spin.r") || !s.Job.IsDone("s3.spin") || !s.VoiceAsked.Contains("step.done:s3.spin")) return "brushing again did not put the spin right";
                if (!bot.PlayUntil("s3.loop:clip")) return bot.Error;
                s.DevComplete("s3.loop", null, .5f);
                if (!bot.PlayUntil("s3.test:probe") || !bot.PlayNext()) return bot.Error;
                if (s.Job.FaultsOn("s3.test", "cold_joint") != 1 || s.Job.State("s3.test.r") != Av) return "the tester did not show the cold joint";
                if (!s.VoiceAsked.Contains("fault.first:cold_joint")) return "Brann was not asked for fault_cold_joint";
                if (!bot.PlayUntil("s3.scribe:sheet")) return bot.Error;
                return s.Job.IsDone("s3.test.r") && s.Job.IsDone("s3.test") ? null : "the joint was not reflowed and tested again";
            });
            Run("stage 3: the strip cracks on the second over-bend", (s, o) =>
            {
                s.DevGrant(new[] { "s0", "s1", "s2" }, .95f); var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s3.strap:bend_1")) return bot.Error;
                s.DevFault("s3.strap", "over_bend");
                if (s.Job.State("s3.strap.r") != AssemblyStepState.Dormant) return "one over-bend should only cost quality";
                s.DevFault("s3.strap", "over_bend");
                if (s.Job.State("s3.strap.r") != Av) return "the second over-bend did not crack the strip";
                if (!s.VoiceAsked.Contains("fault.first:over_bend")) return "Brann was not asked for fault_overbend";
                if (s.bench.Part("materials.sheet_a_strap").place != "fixtures.bin/seat_scrap" || s.bench.Part("materials.sheet_b_strap").place != "fixtures.vise/seat_work#strap") return "the spare strip is not in the vise";
                if (!bot.PlayThrough(3)) return bot.Error;
                return s.Job.IsDone("s3.strap") && s.bench.Part("materials.strap_bent").place == "place.mat.strap" && s.bench.Part("materials.sheet_b_strap").Gone ? null : "the spare did not become the strap";
            });
            Run("stage 5: a stripped head, a soft seam, a pinched lead", (s, o) =>
            {
                s.DevGrant(new[] { "s0", "s1", "s2", "s3", "s4" }, .95f); var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s5.loop:tuck")) return bot.Error;
                s.DevComplete("s5.loop", null, .5f);
                if (!bot.PlayUntil("s5.torque:l_c_torque")) return bot.Error;
                s.DevFault("s5.torque", "stripped");
                if (!s.VoiceAsked.Contains("fault.first:stripped")) return "Brann was not asked for fault_stripped";
                if (!bot.PlayUntil("s5.cure:wait")) return bot.Error;
                bot.Wait(2); if (!bot.Press("grip.core")) return bot.Error; bot.Wait(.2f);
                if (s.Job.FaultsOn("s5.cure", "soft_seam") != 1) return "lifting the grip under the lamp cost nothing (held " + (s.HeldPart ? s.HeldPart.id : "-") + ", focus " + s.Focus.Id + ", refusals " + s.Refusals + ", core at " + s.bench.Part("grip.core").place + ", next " + (s.Next.HasValue ? s.Next.Value.Id : "-") + ", shot " + s.WantedShotName + ")";
                bot.FreeHands();
                if (!bot.PlayUntil("s5.damp:tilt") || !bot.PlayNext()) return bot.Error;
                if (s.Job.FaultsOn("s5.damp", "pinched") != 1 || s.Job.State("s5.damp.r") != Av || !s.VoiceAsked.Contains("step.fault:s5.damp")) return "the damper did not show the pinched lead";
                if (!bot.PlayUntil("s6.slide:clamp")) return bot.Error;
                if (!s.Job.IsDone("s5.damp") || !s.VoiceAsked.Contains("step.done:s5.damp")) return "the damper was not put right";
                return bot.PlayJob() ? (s.LastResult.faults >= 3 ? null : "the faults are not in the result") : bot.Error;
            });
            Run("stage 1: the lead pulled by its wire, a bent pin", (s, o) =>
            {
                var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s1.lead:unplug")) return bot.Error;
                bot.FreeHands(); if (!bot.Press("pistol.lead")) return bot.Error;
                // on the real pistol the wire runs under the backstrap housing and the pin at this point, and only its plug can be
                // reached (21 Nov: no point of the lead comes under the pointer from the shot): the mistake is raised by the dev path
                // there, and the scenario says so
                if (s.Job.FaultsOn("s1.lead", "frayed") == 0 && AssemblyBot.Reaims.Any(x => x.StartsWith("pistol.lead never")))
                {
                    o["note"] = "the lead cannot be reached by its wire on this art; fault raised by the dev path";
                    if (!s.DevFault("s1.lead", "frayed")) return "the frayed fault was refused";
                    if (!s.Job.ActionDone("s1.lead", "unplug") && !bot.PlayNext()) return bot.Error;
                }
                if (s.Job.FaultsOn("s1.lead", "frayed") != 1 || !s.Job.ActionDone("s1.lead", "unplug")) return "pulling the wire did not fray the lead (focus " + s.Focus.Id + ")";
                if (s.Job.State("s3.lead.r") != AssemblyStepState.Locked) return "the re-strip should wait for stage 3";
                if (!bot.PlayUntil("s1.pin:taps")) return bot.Error;
                s.DevFault("s1.pin", "miss"); if (s.Job.State("s1.pin.r") != AssemblyStepState.Dormant) return "one miss should only dent the frame";
                s.DevFault("s1.pin", "miss"); if (s.Job.State("s1.pin.r") == AssemblyStepState.Dormant) return "the second miss did not bend the pin";
                if (!bot.PlayUntil("s1.housing:slide")) return bot.Error;
                if (!s.Job.IsDone("s1.pin.r") || s.bench.Part("pistol.housing_pin").place != "fixtures.partsmat/seat_pistol_pin") return "the pin was not straightened on the anvil and set down";
                if (!bot.PlaySlice()) return bot.Error;
                return s.LastResult.faults >= 3 ? null : "the faults are not in the result";
            });
            Run("stage 6: the plug upside down, a proud pin", (s, o) =>
            {
                s.DevGrant(new[] { "s0", "s1", "s2", "s3", "s4", "s5" }, .95f); var bot = new AssemblyBot(s, false);
                if (!bot.PlayUntil("s6.plug:plug")) return bot.Error;
                if (!bot.Press("pistol.lead_plug")) return bot.Error;
                if (!s.CarryFlipped) return "the plug did not come to the hand the wrong way up (held " + (s.HeldPart ? s.HeldPart.id : "-") + ")";
                bot.Hover(2.5f);
                if (s.Job.FaultsOn("s6.plug", "upside_down") < 1 || s.Job.ActionDone("s6.plug", "plug")) return "the plug seated upside down, or was not refused";
                if (!bot.PlayNext() || !s.Job.ActionDone("s6.plug", "plug")) return bot.Error ?? "the plug did not seat once turned over";
                if (!bot.PlayUntil("s6.pin:taps")) return bot.Error;
                s.DevComplete("s6.pin", "taps", .4f);
                if (!bot.PlayUntil("s6.screws:a_start") || !bot.PlayNext()) return bot.Error;
                if (s.Job.FaultsOn("s6.screws", "proud") != 1 || s.Job.State("s6.pin.r") != Av || s.Job.CanDo("s6.screws", "b_start")) return "the proud pin did not block the screws";
                return bot.PlayJob() ? (s.LastResult.faults >= 2 ? null : "the faults are not in the result") : bot.Error;
            });
            Run("hints", (s, o) =>
            {
                var bot = new AssemblyBot(s, false); var set = s.bench.settings;
                bot.Wait(set.hintGlint + .5f); if (s.HintLevel != 1 || !s.Fx.Log.Any(x => x.StartsWith("glint:"))) return "no glint after " + set.hintGlint + " s";
                bot.Wait(set.hintVoice - set.hintGlint); if (s.HintLevel != 2 || !s.Voice.Log.Any(x => x.StartsWith("hint.idle25:"))) return "no line from Brann after " + set.hintVoice + " s";
                bot.Wait(set.hintGhost - set.hintVoice); if (!s.Fx.Log.Any(x => x.StartsWith("ghost:"))) return "no ghost after " + set.hintGhost + " s";
                o["feedback"] = new JArray(s.Fx.Log); return null;
            });
            var report = new JObject { ["pass"] = failed == 0, ["failed"] = failed, ["only"] = only, ["scenarios"] = results };
            Directory.CreateDirectory(Evidence); report["prefab"] = prefabPath; File.WriteAllText(Path.Combine(Evidence, !string.IsNullOrEmpty(only) ? "selftest-partial.json" : standIns ? "selftest-standins.json" : "selftest.json"), report.ToString(Formatting.Indented));
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            if (failed > 0) throw new Exception("selftest: " + string.Join(" | ", results.Where(r => !(bool)r["ok"]).Select(r => (string)r["name"] + ": " + (string)r["error"])));
            return new { ok = true, scenarios = results.Count };
        }

        // ------------------------------------------------------------------ sight (can the player see what every action needs?)
        /// The sight check on a bench built for the purpose in an empty scene: the families as data/sources.json has them, or as
        /// --real / --greybox say for this run (`sight --greybox all` is the stand-in bench). Writes bench/sight-LABEL.json.
        static object SightStep()
        {
            var sources = Sources(out var how);
            var realOnes = sources.Where(x => x.Value != "greybox").Select(x => x.Key).OrderBy(x => x, StringComparer.Ordinal).ToArray();
            string label = realOnes.Length == 0 ? "standins" : "real-" + string.Join("-", realOnes);
            var report = SightOn(sources, label); report["sources"] = how;
            Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "sight-" + label + ".json"), report.ToString(Formatting.Indented));
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            return SightSummary(report, "sight-" + label + ".json");
        }
        static JObject SightOn(Dictionary<string, string> sources, string label)
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var spec = Spec(sources, true); GameObject go = null;
            try { go = AssemblyKitBuilder.BuildBench(spec); return AssemblySightCheck.Run(go.GetComponent<AssemblyBench>(), spec.layout, label); }
            finally { if (go) UnityEngine.Object.DestroyImmediate(go); }
        }
        static JObject SightSummary(JObject report, string file) => new JObject
        {
            ["ok"] = report["ok"], ["actionsChecked"] = report["actionsChecked"], ["pointsChecked"] = report["pointsChecked"], ["actionsThatFail"] = report["failed"], ["byWhy"] = report["byWhy"],
            ["shotsUsed"] = report["shotsUsed"], ["notWalked"] = report["notWalked"], ["stopped"] = report["stopped"], ["error"] = report["error"], ["file"] = "unity/evidence/steady_hands/20261120/bench/" + file,
        };

        // ------------------------------------------------------------------ probe (where is a part, and what does the pointer find there?)
        /// `probe --part a,b [--shot NAME]`: on a copy of the installed prefab as found, each part's pose, box, hold point and surface
        /// points, and what a pointer aimed at its hold point from the shot picks. Writes bench/probe.json. For finding out why a
        /// press misses on real art.
        static object Probe()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath) ?? throw new Exception("Build the prefab first.");
            var go = UnityEngine.Object.Instantiate(prefab); var bench = go.GetComponent<AssemblyBench>(); var rows = new JArray();
            try
            {
                bench.Index(true); bench.ResetAsFound();
                foreach (var e in Arg("--effects")) bench.ApplyEffect(e);   // e.g. --effects tools.roll>place.roll,tools.roll_unroll=1
                string shot = Arg("--shot").FirstOrDefault() ?? "work"; var cam = bench.cameraRoot.Find("cam_bench_" + shot);
                JArray V3(Vector3 v) => new JArray(Math.Round(v.x, 4), Math.Round(v.y, 4), Math.Round(v.z, 4));
                foreach (var id in Arg("--part"))
                {
                    var p = bench.Part(id); if (!p) { rows.Add(new JObject { ["id"] = id, ["error"] = "no such part" }); continue; }
                    var t = p.transform; var b = p.localBounds; var lo = Vector3.positiveInfinity; var hi = Vector3.negativeInfinity;
                    for (int i = 0; i < 8; i++) { var c = t.TransformPoint(b.center + Vector3.Scale(b.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1))); lo = Vector3.Min(lo, c); hi = Vector3.Max(hi, c); }
                    var row = new JObject
                    {
                        ["id"] = id, ["node"] = t.name, ["active"] = p.gameObject.activeInHierarchy, ["place"] = p.place, ["parent"] = t.parent ? t.parent.name : null,
                        ["position"] = V3(t.position), ["euler"] = V3(t.eulerAngles), ["boxMin"] = V3(lo), ["boxMax"] = V3(hi),
                        ["hold"] = V3(p.GrabPoint), ["holdIs"] = p.grab ? "grab empty " + p.grab.name : p.hasHandle ? "a surface point" : "the middle of the box",
                        ["surfacePoints"] = p.surface.Length, ["surfaceRadiusMm"] = Math.Round(p.surfaceRadius * Mathf.Abs(t.lossyScale.x) * 1000, 2),
                        ["renderers"] = new JArray(p.renderers.Select(r => r.GetType().Name + " " + r.name + " at " + V3(r.bounds.center).ToString(Formatting.None) + " size " + V3(r.bounds.size).ToString(Formatting.None))),
                    };
                    if (cam)
                    {
                        var eye = cam.position; var ray = new Ray(eye, (p.GrabPoint - eye).normalized);
                        row["fromShot"] = shot; row["ownHitMm"] = Math.Round(p.Raycast(ray, .006f) * 1000, 1); row["holdAtMm"] = Math.Round(Vector3.Distance(eye, p.GrabPoint) * 1000, 1);
                        var hit = bench.Pick(ray); row["pointerFinds"] = hit.part ? hit.part.id : hit.marker ? hit.marker.id : null; row["pointerFindsAtMm"] = Math.Round(hit.distance * 1000, 1);
                    }
                    rows.Add(row);
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }
            Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "probe.json"), rows.ToString(Formatting.Indented));
            return new { parts = rows.Count, file = "unity/evidence/steady_hands/20261120/bench/probe.json" };
        }

        // ------------------------------------------------------------------ bindcheck (SEAM.md: the integration seam, tried early)
        /// Binds a real family as the integration pass will (`prefab --real FAMILY`), alone, on a scratch object in an
        /// empty scene, and writes what it found: nodes and empties that do not resolve, clips and whether they move
        /// anything once re-bound to their rig, places that found their marks, sizes against the family's own numbers.
        static object BindCheck()
        {
            var args = Environment.GetCommandLineArgs(); int fi = Array.IndexOf(args, "--family");
            var wanted = fi >= 0 && fi + 1 < args.Length ? args[fi + 1].Split(',') : AssemblyKitBuilder.Families;
            var layout = JObject.Parse(File.ReadAllText(LayoutPath)); var summary = new JObject();
            var sightDone = new Dictionary<string, string>(); var sightSummaries = new Dictionary<string, JObject>();
            foreach (var family in wanted)
            {
                string glb = Glb(family);
                if (!File.Exists(glb)) { summary[family] = "no model at " + glb; continue; }
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                var recipe = AssetDatabase.LoadAssetAtPath<AssemblyRecipe>(RecipePath);   // (a new scene unloads what nothing holds)
                var spec = new AssemblyKitBuilder.BenchSpec { layout = layout, families = new[] { family }, scratch = true, recipe = recipe };
                spec.sources[family] = glb;
                var o = new JObject { ["family"] = family, ["model"] = glb };
                GameObject go = null;
                try
                {
                    go = AssemblyKitBuilder.BuildBench(spec); var bench = go.GetComponent<AssemblyBench>(); var bind = AssemblyKitBuilder.LastReport;
                    var file = JObject.Parse(File.ReadAllText(AssemblyKitBuilder.PartsPath(family, glb)));
                    var listed = ((JArray)file["parts"]).Cast<JObject>().ToList();
                    o["partsListed"] = listed.Count; o["partsBound"] = bench.Parts.Count();
                    // a parent in another family is expected to be missing when one family is bound alone
                    var external = bind.problems.Where(x => x.Contains("is not on the bench")).ToList();
                    o["problems"] = new JArray(bind.problems.Except(external)); o["parentsInOtherFamilies"] = new JArray(external); o["notes"] = new JArray(bind.notes);
                    o["standInsForWhatTheModelLacks"] = new JArray(bind.standIns.TryGetValue(family, out var filled) ? filled : new string[0]);
                    // empties the file names that the model does not have
                    var names = new HashSet<string>(go.GetComponentsInChildren<Transform>(true).Select(t => t.name)); var lost = new JArray();
                    foreach (var e in listed)
                        foreach (var kind in new[] { "marks", "zones" })
                            foreach (var m in (e[kind] as JArray ?? new JArray()).OfType<JObject>()) { string n = (string)m["node"]; if (!string.IsNullOrEmpty(n) && !names.Contains(n)) lost.Add($"{(string)e["id"]}: {kind} empty {n}"); }
                    o["emptiesNotInModel"] = lost;
                    o["marks"] = bench.Markers.Count(m => m.kind == AssemblyMarkerKind.Mark); o["paths"] = new JArray(bench.Markers.Where(m => m.kind == AssemblyMarkerKind.Path).Select(m => $"{m.id} ({m.points.Length} points)"));
                    o["zones"] = new JArray(bench.Markers.Where(m => m.kind == AssemblyMarkerKind.Zone).Select(m => { AssemblyWipeMask.Axes(m.size, out int u, out int v, out int n); return $"{m.id}: {m.size.x * 1000:0.#} x {m.size.y * 1000:0.#} x {m.size.z * 1000:0.#} mm, wiped across {"xyz"[u]}{"xyz"[v]}"; }));
                    o["placesOnMarks"] = new JArray(bind.boundPlaces); o["placesOnPoseMarks"] = new JArray(bind.posePlaces);
                    o["shots"] = JObject.FromObject(bind.shots);
                    o["placesWhoseMarkIsNotInTheModel"] = new JArray(bind.fallbackPlaces.Where(id => id.StartsWith(family + ".")));
                    // sizes: the part's own box against the family's size_mm (sorted, so the axis convention does not matter)
                    var sizes = new JArray();
                    foreach (var e in listed)
                    {
                        var p = bench.Part((string)e["id"]); if (!p || !(e["size_mm"] is JArray sm) || sm.Count != 3) continue;
                        var want = sm.Select(x => (float)x).OrderBy(x => x).ToArray(); var b = Vector3.Scale(p.localBounds.size, p.transform.lossyScale) * 1000; var got = new[] { Mathf.Abs(b.x), Mathf.Abs(b.y), Mathf.Abs(b.z) }.OrderBy(x => x).ToArray();
                        if (Enumerable.Range(0, 3).Any(k => Mathf.Abs(got[k] - want[k]) > Mathf.Max(1.5f, want[k] * .25f))) sizes.Add($"{p.id}: bound box {got[0]:0.#} x {got[1]:0.#} x {got[2]:0.#} mm, the family says {want[0]:0.#} x {want[1]:0.#} x {want[2]:0.#}");
                    }
                    o["sizesThatDisagree"] = sizes;
                    o["partsWithoutRenderers"] = new JArray(bench.Parts.Where(p => p.renderers.Length == 0).Select(p => p.id));
                    o["kinds"] = new JObject(bench.Parts.GroupBy(p => p.kind).OrderBy(g => g.Key).Select(g => new JProperty(g.Key, g.Count())));
                    // mechanisms: does the re-bound clip move anything between 0 and 1?
                    var mech = new JArray();
                    foreach (var m in bench.Params.OrderBy(x => x.id, StringComparer.Ordinal))
                    {
                        var row = new JObject { ["id"] = m.id, ["asFound"] = m.asFound, ["clip"] = bind.clips.TryGetValue(m.id, out var how) ? how : "none (the bench moves it)" };
                        if (m.clip && m.clipRoot)
                        {
                            var ts = m.clipRoot.GetComponentsInChildren<Transform>(true);
                            m.Set(0); var p0 = ts.Select(t => t.position).ToArray(); var r0 = ts.Select(t => t.rotation).ToArray(); var s0 = ts.Select(t => t.localScale).ToArray();
                            m.Set(1); float move = 0, turn = 0, scale = 0; string mover = "";
                            for (int k = 0; k < ts.Length; k++) { float d = Vector3.Distance(ts[k].position, p0[k]) * 1000, a = Quaternion.Angle(ts[k].rotation, r0[k]); if (d > move) { move = d; mover = ts[k].name; } turn = Mathf.Max(turn, a); scale = Mathf.Max(scale, (ts[k].localScale - s0[k]).magnitude); }
                            row["movesMm"] = Mathf.Round(move * 10) / 10; row["turnsDeg"] = Mathf.Round(turn * 10) / 10; row["scales"] = Mathf.Round(scale * 100) / 100; row["mostMoved"] = mover; row["length"] = m.clip.length; row["legacy"] = m.clip.legacy;
                            if (move < .05f && turn < .2f && scale < .01f) ((JArray)o["problems"]).Add($"{m.id}: its clip moves nothing when sampled from {m.clipRoot.name}");
                            m.Set(m.asFound);
                        }
                        mech.Add(row);
                    }
                    o["mechanisms"] = mech;
                    // the as-found poses: seated parts whose clear pose is the same as their rest
                    o["clearSameAsRest"] = new JArray(bench.Parts.Where(p => p.hasClear && p.Travel < 1e-4f).Select(p => p.id));
                    // the step table against this family: ids the table uses that the model does not have
                    if (recipe)
                    {
                        var missing = new SortedSet<string>(StringComparer.Ordinal);
                        void Need(string id) { if (string.IsNullOrEmpty(id) || !id.StartsWith(family + ".")) return; if (!bench.Part(id) && !bench.Marker(id) && !bench.Param(id)) missing.Add(id); }
                        foreach (var st in recipe.data.Steps) foreach (var a in st.actions)
                        {
                            Need(a.part); Need(a.target); Need(a.drive); foreach (var t in a.targets) Need(t);
                            foreach (var e in a.effects.Concat(a.faults.SelectMany(f => f.effects)).Concat(st.effects)) { var body = AssemblyBench.EffectBody(e); int at = body.IndexOf('>'); if (body.StartsWith("~")) { int eq = body.IndexOf('='); Need(eq > 0 ? body.Substring(1, eq - 1) : body.Substring(1)); } else if (at > 0) { Need(body.Substring(0, at)); Need(body.Substring(at + 1)); } else { at = body.IndexOf('='); if (at > 0) Need(body.Substring(0, at)); } }
                        }
                        o["idsTheStepTableUsesThatNeitherTheModelNorAStandInHas"] = new JArray(missing);
                    }
                    o["ok"] = ((JArray)o["problems"]).Count == 0 && lost.Count == 0;
                }
                catch (Exception e) { o["ok"] = false; o["exception"] = e.GetType().Name + ": " + e.Message + " @ " + (e.StackTrace ?? "").Split('\n').FirstOrDefault(); }
                finally { if (go) UnityEngine.Object.DestroyImmediate(go); }
                // the same family on the whole bench (the others as data/sources.json has them): can every action still be seen?
                try
                {
                    var sources = Sources(out var how); bool already = sources[family] == glb; sources[family] = glb; how[family] = already ? how[family] : "real (bindcheck)";
                    // (when data/sources.json already has every family as this run would, the walk is the same for each: made once)
                    string key = string.Join(",", sources.OrderBy(x => x.Key, StringComparer.Ordinal).Select(x => x.Key + "=" + x.Value));
                    if (!sightDone.TryGetValue(key, out var file))
                    {
                        var sight = SightOn(sources, already ? "whole bench as data/sources.json has it" : "whole bench with the real " + family); sight["sources"] = how;
                        file = already ? "sight-bind-as-sources.json" : "sight-bind-" + family + ".json";
                        File.WriteAllText(Path.Combine(Evidence, file), sight.ToString(Formatting.Indented));
                        sightDone[key] = file; sightSummaries[file] = SightSummary(sight, file);
                    }
                    o["sight"] = sightSummaries[file];
                }
                catch (Exception e) { o["sight"] = new JObject { ["ok"] = false, ["error"] = e.GetType().Name + ": " + e.Message + " @ " + (e.StackTrace ?? "").Split('\n').FirstOrDefault() }; }
                Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "bind-" + family + ".json"), o.ToString(Formatting.Indented));
                summary[family] = new JObject { ["ok"] = o["ok"], ["problems"] = (o["problems"] as JArray)?.Count ?? -1, ["parts"] = o["partsBound"], ["exception"] = o["exception"], ["sightOk"] = o["sight"]?["ok"], ["sightFails"] = o["sight"]?["actionsThatFail"] };
            }
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            return summary;
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            string steps = i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify";
            try
            {
                foreach (var name in steps.Split(',').SelectMany(s => s == "install" ? new[] { "recipe", "audio", "settings", "prefab", "scene" } : new[] { s }))
                {
                    object result = name switch
                    {
                        "recipe" => Recipe(),
                        "audio" => Audio(),
                        "settings" => Settings(),
                        "prefab" => Prefab(),
                        "scene" => SceneStep(),
                        "verify" => Verify(),
                        "selftest" => SelfTest(),
                        "selfteststandins" => SelfTest(true),
                        "bindcheck" => BindCheck(),
                        "sight" => SightStep(),
                        "probe" => Probe(),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + name),
                    };
                    Debug.Log("AssemblyBenchInstall20261120 " + name + ": " + JsonConvert.SerializeObject(result));
                    if (name != "verify" && name != "selftest" && name != "selfteststandins" && name != "rollback" && name != "bindcheck" && name != "sight" && name != "probe") WriteEvidence(name + ".json", result);   // those three write their own full report
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        [MenuItem("Athen Hill/Steady Hands bench (20 Nov 2026)/Install")] public static void MenuInstall() { foreach (Func<object> step in new Func<object>[] { Recipe, Audio, Settings, Prefab, SceneStep }) Debug.Log(JsonConvert.SerializeObject(step())); }
        [MenuItem("Athen Hill/Steady Hands bench (20 Nov 2026)/Verify")] public static void MenuVerify() => Debug.Log(JsonConvert.SerializeObject(Verify()));
        [MenuItem("Athen Hill/Steady Hands bench (20 Nov 2026)/Rollback")] public static void MenuRollback() => Debug.Log(JsonConvert.SerializeObject(Rollback()));
    }
}
