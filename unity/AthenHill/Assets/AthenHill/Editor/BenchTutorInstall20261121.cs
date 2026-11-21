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
using UnityEngine.UIElements;

namespace AthenHill.Editor
{
    /// <summary>
    /// 21 November 2026, Steady Hands bench programme, tutor agent: Brann walks the player through the first hand-made job.
    /// Record: art/steady_hands_bench_20261120/audio/tutor/README.md.
    ///
    /// lines    : audio/tutor/lines.json -> Audio/ElevenLabs/Bench/Tutor/BenchTutorLines.asset (clips by path; a missing clip
    ///            is a verify failure, not an install failure)
    /// scene    : scene root "Steady Hands bench tutor" with BenchTutor (lines, stylesheet). Its own root, so the bench's
    ///            installer can rebuild its root without touching it. Idempotent.
    /// install  : lines, scene.
    /// verify   : on the saved scene, -nographics: the root and its references; every line's clip; the asset matches lines.json;
    ///            every step of the bench recipe voiced or deliberately silent; every kind of action the recipe uses has a
    ///            how-line and a prompt; the whole job walked on paper through BenchTutorScript. Writes
    ///            unity/evidence/steady_hands/20261120/tutor/verify.json; throws (rc 1) on a failure.
    /// rollback : removes the scene root (the asset, clips and code stay; Settings keeps its switch).
    ///
    /// -executeMethod AthenHill.Editor.BenchTutorInstall20261121.RunBatch -nographics --steps install,verify | rollback
    /// </summary>
    public static class BenchTutorInstall20261121
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string RootName = "Steady Hands bench tutor";
        const string AssetPath = "Assets/AthenHill/Audio/ElevenLabs/Bench/Tutor/BenchTutorLines.asset";
        const string StylePath = "Assets/AthenHill/Scripts/Assembly/Tutor/BenchTutor.uss";
        const string RecipePath = "Assets/AthenHill/Data/Assembly/assembly_grip_stabilised_pistol.asset";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string LinesJson => Path.Combine(Repo, "art/steady_hands_bench_20261120/audio/tutor/lines.json");
        static string InstructionsJson => Path.Combine(Repo, "art/steady_hands_bench_20261120/audio/tutor/instructions.json");
        static BenchTutorLines.Pair[] Pairs(JObject doc, string name) => ((JObject)doc[name] ?? new JObject()).Properties().Select(p => new BenchTutorLines.Pair { key = p.Name, value = (string)p.Value }).OrderBy(p => p.key, StringComparer.Ordinal).ToArray();
        static string Evidence => Path.Combine(Repo, "unity/evidence/steady_hands/20261120/tutor");

        static string Sha1(string text) { using var sha = SHA1.Create(); return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-", "").ToLowerInvariant(); }

        // ------------------------------------------------------------------ lines
        static object Lines()
        {
            string text = File.ReadAllText(LinesJson); var doc = JObject.Parse(text);
            var asset = AssetDatabase.LoadAssetAtPath<BenchTutorLines>(AssetPath);
            bool created = !asset;
            if (created) { asset = ScriptableObject.CreateInstance<BenchTutorLines>(); AssetDatabase.CreateAsset(asset, AssetPath); }
            var list = new List<BenchTutorLines.Line>(); int clips = 0;
            foreach (JObject l in doc["lines"])
            {
                var clip = AssetDatabase.LoadAssetAtPath<AudioClip>((string)l["file"]); if (clip) clips++;
                list.Add(new BenchTutorLines.Line
                {
                    id = (string)l["id"], kind = (string)l["kind"], step = (string)l["step"] ?? "", verb = (string)l["verb"] ?? "", key = (string)l["key"] ?? "",
                    trigger = (string)l["trigger"], stage = (int?)l["stage"] ?? -1, text = (string)l["text"], clip = clip,
                });
            }
            asset.lines = list.ToArray();
            asset.silentSteps = ((JObject)doc["silent"] ?? new JObject()).Properties().Select(p => p.Name).OrderBy(x => x, StringComparer.Ordinal).ToArray();
            string itext = File.ReadAllText(InstructionsJson); var inst = JObject.Parse(itext);
            asset.actions = Pairs(inst, "actions"); asset.names = Pairs(inst, "names"); asset.tools = Pairs(inst, "tools");
            asset.shots = Pairs(inst, "shots"); asset.prefix = Pairs(inst, "prefix"); asset.refused = Pairs(inst, "refused");
            asset.sourceHash = Sha1(text + "\n" + itext);
            EditorUtility.SetDirty(asset); AssetDatabase.SaveAssets();
            return new { asset = AssetPath, created, lines = list.Count, clips, silent = asset.silentSteps.Length, instructions = asset.actions.Length, asset.sourceHash };
        }

        // ------------------------------------------------------------------ scene
        static object SceneStep()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            bool created = !root;
            if (created) { root = new GameObject(RootName); EditorSceneManager.MoveGameObjectToScene(root, scene); }
            var tutor = root.GetComponent<BenchTutor>() ?? root.AddComponent<BenchTutor>();
            tutor.lines = AssetDatabase.LoadAssetAtPath<BenchTutorLines>(AssetPath);
            tutor.style = AssetDatabase.LoadAssetAtPath<StyleSheet>(StylePath);
            root.SetActive(true);
            EditorUtility.SetDirty(tutor);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return new { root = RootName, created, lines = tutor.lines ? AssetPath : null, style = tutor.style ? StylePath : null };
        }

        static object Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var roots = scene.GetRootGameObjects().Where(g => g.name == RootName).ToList();
            foreach (var r in roots) UnityEngine.Object.DestroyImmediate(r);
            if (roots.Count > 0) { EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); }
            return new { removed = roots.Count };
        }

        // ------------------------------------------------------------------ verify
        static object Verify()
        {
            var problems = new List<string>(); var report = new JObject();
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            var tutor = root ? root.GetComponent<BenchTutor>() : null;
            if (!root) problems.Add("scene root missing: " + RootName);
            else if (!root.activeSelf) problems.Add("scene root inactive");
            if (root && !tutor) problems.Add("BenchTutor missing on the root");
            if (tutor && !tutor.lines) problems.Add("BenchTutor.lines not set");
            if (tutor && !tutor.style) problems.Add("BenchTutor.style not set");
            if (scene.GetRootGameObjects().Count(g => g.name == RootName) > 1) problems.Add("more than one tutor root");

            var asset = AssetDatabase.LoadAssetAtPath<BenchTutorLines>(AssetPath);
            if (!asset) { problems.Add("lines asset missing: " + AssetPath); Write(report, problems); throw new Exception("verify failed: " + string.Join("; ", problems)); }
            string text = File.ReadAllText(LinesJson); var doc = JObject.Parse(text);
            string itext = File.ReadAllText(InstructionsJson);
            if (asset.sourceHash != Sha1(text + "\n" + itext)) problems.Add("lines asset is older than lines.json or instructions.json (run the lines step)");
            foreach (var k in new[] { "take_tool", "put_back", "pick_up", "view", "view_now", "view_back" }) if (string.IsNullOrEmpty(asset.Text("prefix", k))) problems.Add("instruction prefix missing: " + k);
            foreach (var k in new[] { "blocked", "not_yet", "needs_tool", "wrong_tool", "wrong_place" }) if (string.IsNullOrEmpty(asset.Text("refused", k))) problems.Add("refusal caption missing: " + k);
            foreach (var k in new[] { "blocked", "not_yet", "needs_tool", "wrong_tool" }) if (!asset.Has("tutor.refused:" + k)) problems.Add("refusal line missing: " + k);
            var jsonLines = doc["lines"].Cast<JObject>().ToList();
            if (jsonLines.Count != asset.lines.Length) problems.Add($"asset has {asset.lines.Length} lines, lines.json {jsonLines.Count}");
            var noClip = asset.lines.Where(l => !l.clip).Select(l => l.id).ToList();
            foreach (var id in noClip) problems.Add("no clip: " + id);
            foreach (var l in jsonLines)
            {
                var a = asset.lines.FirstOrDefault(x => x.id == (string)l["id"]);
                if (a == null) { problems.Add("not in the asset: " + l["id"]); continue; }
                if (a.clip && AssetDatabase.GetAssetPath(a.clip) != (string)l["file"]) problems.Add($"{a.id}: clip is {AssetDatabase.GetAssetPath(a.clip)}, lines.json names {l["file"]}");
                if (a.clip && a.clip.length < .4f) problems.Add($"{a.id}: clip only {a.clip.length:0.00} s");
                if (a.text != (string)l["text"]) problems.Add(a.id + ": text differs from lines.json");
            }
            foreach (var g in asset.lines.GroupBy(l => l.trigger).Where(g => g.Count() > 1)) problems.Add("trigger used twice: " + g.Key);

            var recipe = AssetDatabase.LoadAssetAtPath<AssemblyRecipe>(RecipePath);
            var coverage = new JArray(); var teachUsed = new HashSet<string>();
            if (!recipe) problems.Add("bench recipe missing: " + RecipePath);
            else
            {
                var silent = new HashSet<string>(asset.silentSteps);
                for (int s = 0; s < recipe.data.stages.Length; s++)
                    foreach (var step in recipe.data.stages[s].steps)
                    {
                        string trig = (step.recovery ? "tutor.recovery:" : "tutor.step:") + step.id;
                        bool voiced = asset.Has(trig), quiet = silent.Contains(step.id);
                        var extras = step.actions.Where(a => asset.Has($"tutor.action:{step.id}:{a.key}")).Select(a => a.key).ToArray();
                        if (!voiced && !quiet) problems.Add("step neither voiced nor silent: " + step.id);
                        if (voiced && quiet) problems.Add("step both voiced and listed silent: " + step.id);
                        if (extras.Length > 1) problems.Add($"{step.id}: more than one extra line inside the row");
                        foreach (var a in step.actions)
                        {
                            var k = BenchTutorScript.TeachKey(a); if (k != null) teachUsed.Add(k);
                            if (string.IsNullOrEmpty(a.line) && string.IsNullOrEmpty(asset.Text("actions", step.id + ":" + a.key))) problems.Add($"no instruction for {step.id}:{a.key}");
                            if (!string.IsNullOrEmpty(a.part) && asset.Text("names", a.part) == null) problems.Add("no name for part " + a.part);
                            if (!string.IsNullOrEmpty(a.tool) && a.tool != "*" && asset.Text("tools", a.tool) == null) problems.Add("no name for tool " + a.tool);
                            if (!string.IsNullOrEmpty(a.shot) && asset.Text("shots", a.shot) == null) problems.Add("no name for shot " + a.shot);
                        }
                        coverage.Add(new JObject { ["step"] = step.id, ["stage"] = s, ["recovery"] = step.recovery, ["voiced"] = voiced, ["silent"] = quiet, ["extra"] = new JArray(extras) });
                    }
                foreach (var l in asset.lines.Where(l => l.kind == "action"))
                {
                    var st = recipe.data.Steps.FirstOrDefault(x => x.id == l.step);
                    if (st == null || st.actions.All(a => a.key != l.key)) problems.Add($"{l.id}: no action {l.step}:{l.key} in the recipe");
                }
                foreach (var l in asset.lines.Where(l => l.kind == "step" || l.kind == "recovery")) if (recipe.data.Steps.All(x => x.id != l.step)) problems.Add($"{l.id}: no step {l.step} in the recipe");
                foreach (var k in teachUsed)
                {
                    if (!asset.Has("tutor.verb:" + k)) problems.Add("no how-line for " + k);
                    if (BenchTutorScript.PromptText(k).mouse == null) problems.Add("no prompt for " + k);
                }
                // the source table too (the recipe asset is the bench's, installed on its own schedule)
                var src = JObject.Parse(File.ReadAllText(Path.Combine(Repo, "art/steady_hands_bench_20261120/data/steps.json")));
                foreach (var st in src["stages"].SelectMany(x => x["steps"])) foreach (var ac in st["actions"])
                    if (string.IsNullOrEmpty((string)ac["line"]) && string.IsNullOrEmpty(asset.Text("actions", st["id"] + ":" + ac["key"]))) problems.Add($"no instruction for {st["id"]}:{ac["key"]} (steps.json)");
                var spoken = BenchTutorScript.WalkOnPaper(recipe.data, asset.Has, out var prompts);
                var shouldSpeak = recipe.data.stages.Take(5).SelectMany(st => st.steps).Where(st => !st.recovery && !st.optional && asset.Has("tutor.step:" + st.id)).Select(st => "tutor.step:" + st.id).ToList();
                foreach (var t in shouldSpeak) if (!spoken.Contains(t)) problems.Add("walk on paper did not speak " + t);
                foreach (var k in teachUsed) if (!spoken.Contains("tutor.verb:" + k)) problems.Add("walk on paper did not teach " + k);
                if (spoken.Any(t => t.StartsWith("tutor.step:s5") || t.StartsWith("tutor.step:s6") || t.StartsWith("tutor.step:s7"))) problems.Add("walk on paper spoke in a quiet stage without a stall or a mistake");
                report["walkOnPaper"] = new JObject { ["spoken"] = spoken.Count, ["order"] = new JArray(spoken), ["prompts"] = new JArray(prompts) };
            }
            report["lines"] = asset.lines.Length; report["clips"] = asset.lines.Length - noClip.Count;
            report["seconds"] = Math.Round(asset.lines.Where(l => l.clip).Sum(l => l.clip.length), 1);
            report["byKind"] = JObject.FromObject(asset.lines.GroupBy(l => l.kind).ToDictionary(g => g.Key, g => g.Count()));
            report["silent"] = new JArray(asset.silentSteps); report["teachKeys"] = new JArray(teachUsed.OrderBy(x => x));
            report["coverage"] = coverage; report["instructions"] = asset.actions.Length;
            Write(report, problems);
            if (problems.Count > 0) throw new Exception("verify failed: " + string.Join("; ", problems.Take(20)));
            return new { pass = true, lines = asset.lines.Length, steps = coverage.Count, teach = teachUsed.Count };
        }
        static void Write(JObject report, List<string> problems)
        {
            report["pass"] = problems.Count == 0; report["problems"] = new JArray(problems); report["utc"] = DateTime.UtcNow.ToString("o");
            Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "verify.json"), report.ToString(Formatting.Indented));
        }

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            string steps = i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify";
            try
            {
                foreach (var name in steps.Split(',').SelectMany(s => s == "install" ? new[] { "lines", "scene" } : new[] { s }))
                {
                    object result = name switch
                    {
                        "lines" => Lines(),
                        "scene" => SceneStep(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + name),
                    };
                    Debug.Log("BenchTutorInstall20261121 " + name + ": " + JsonConvert.SerializeObject(result));
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        [MenuItem("Athen Hill/Steady Hands bench (20 Nov 2026)/Tutor: install")] public static void MenuInstall() { Debug.Log(JsonConvert.SerializeObject(Lines())); Debug.Log(JsonConvert.SerializeObject(SceneStep())); }
        [MenuItem("Athen Hill/Steady Hands bench (20 Nov 2026)/Tutor: verify")] public static void MenuVerify() => Debug.Log(JsonConvert.SerializeObject(Verify()));
    }
}
