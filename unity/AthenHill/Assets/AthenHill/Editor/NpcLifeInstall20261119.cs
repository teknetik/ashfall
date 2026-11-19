using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// NPC life pass, 19 Nov 2026 (art/showcase_20261119/npc_life/README.md): ambient barks, captions and the missing voices.
    /// Source of truth: art/showcase_20261119/npc_life/barks.json (lines, voices, dialogue takes); audio made by
    /// generate_voices.py in the same folder. Steps (each idempotent, none calls an older pass):
    ///   assets    importer settings for the new takes; Data/Barks/barks_&lt;speaker&gt;.asset (BarkSet) per speaker: missing lines
    ///             are added, voices bound by asset path when the line's text still matches the take (an Inspector-edited
    ///             line keeps its text and becomes caption-only). --force resets every JSON line to the JSON.
    ///   dialogue  Tamsin's five nodes and Ossa's locker/range nodes get their takes (by path); Tamsin's "supplies" node
    ///             loses its stale hotbar keys (only when it still reads the old text). A take is bound only to matching text.
    ///   scene     BarkDirector on the GameSession object; NpcBarker on every NpcAgent root and the three ambient walkers;
    ///             ActorLookAt (focus only, no idle glances or rest levelling) on each walker's visual, so they glance at
    ///             the player as they pass. Existing components are kept (Inspector tuning survives a re-run).
    ///   verify    checks all of the above and writes verify.json; throws on a problem.
    ///   rollback  removes the components this pass added, restores Tamsin's old supplies text and clears the takes it
    ///             bound (Tamsin, Ossa locker/range/long_arm) and the old Ossa long_arm and catalog texts. BarkSet assets and audio files stay on disk.
    ///   text      CityCatalog descriptions of the trauma kit, nano cell and surge pack lose their fixed hotbar keys (only
    ///             while they still read the old text).
    /// -executeMethod AthenHill.Editor.NpcLifeInstall20261119.RunBatch -nographics --steps assets,dialogue,text,scene,verify
    /// </summary>
    public static class NpcLifeInstall20261119
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string DataDir = "Assets/AthenHill/Data/";
        const string BarksDir = "Assets/AthenHill/Data/Barks";
        const string BarkAudio = "Assets/AthenHill/Audio/ElevenLabs/NpcBarks/";
        const string VoiceAudio = "Assets/AthenHill/Audio/ElevenLabs/NpcVoices/";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string ArtDir => Path.Combine(Repo, "art/showcase_20261119/npc_life");
        static string RecordPath => Path.Combine(ArtDir, "install_record.json");
        static JObject Source => JObject.Parse(File.ReadAllText(Path.Combine(ArtDir, "barks.json")));

        class Rec { public List<string> lookAtAdded = new List<string>(); public List<string> log = new List<string>(); }
        static Rec LoadRec() => File.Exists(RecordPath) ? JsonConvert.DeserializeObject<Rec>(File.ReadAllText(RecordPath)) : new Rec();
        static void SaveRec(Rec r) { Directory.CreateDirectory(ArtDir); File.WriteAllText(RecordPath, JsonConvert.SerializeObject(r, Formatting.Indented)); }
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static string BarkSetPath(string speaker) => BarksDir + "/barks_" + speaker + ".asset";
        static string BarkClipPath(string speaker, string line) => BarkAudio + speaker + "-" + line + ".wav";
        static string VoiceClipPath(string npc, string node) => VoiceAudio + npc + "-" + node + ".wav";
        static bool Force => Environment.GetCommandLineArgs().Contains("--force");

        // ------------------------------------------------------------------ assets
        static void Importer(string path, bool bark)
        {
            var ai = AssetImporter.GetAtPath(path) as AudioImporter;
            if (!ai) return;
            var s = ai.defaultSampleSettings;
            // Barks are short and many: Vorbis kept compressed in memory (one voice plays at a time). Dialogue takes
            // match the 2 Oct NpcVoices imports (decompressed on load).
            var load = bark ? AudioClipLoadType.CompressedInMemory : AudioClipLoadType.DecompressOnLoad;
            if (ai.forceToMono && !ai.loadInBackground && s.loadType == load && s.compressionFormat == AudioCompressionFormat.Vorbis && Mathf.Approximately(s.quality, .85f) && s.preloadAudioData) return;
            s.loadType = load; s.compressionFormat = AudioCompressionFormat.Vorbis; s.quality = .85f; s.preloadAudioData = true;
            ai.defaultSampleSettings = s; ai.forceToMono = true; ai.loadInBackground = false;
            ai.SaveAndReimport();
        }
        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            var parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }
        static Vector2 Hours(JToken t) => t is JArray a && a.Count == 2 ? new Vector2((float)a[0], (float)a[1]) : new Vector2(0, 24);

        public static string Assets()
        {
            AssetDatabase.Refresh();
            var src = Source; var log = new List<string>(); int added = 0, voiced = 0, captionOnly = 0;
            foreach (var d in src["dialogue"]) Importer(VoiceClipPath((string)d["npc"], (string)d["node"]), false);
            EnsureFolder(BarksDir);
            foreach (JObject sp in src["speakers"])
            {
                string id = (string)sp["id"];
                var path = BarkSetPath(id);
                var set = AssetDatabase.LoadAssetAtPath<BarkSet>(path);
                if (!set) { set = ScriptableObject.CreateInstance<BarkSet>(); set.lines = new BarkLine[0]; AssetDatabase.CreateAsset(set, path); log.Add("created " + path); }
                set.speakerId = id;
                if (string.IsNullOrEmpty(set.displayName) || Force) set.displayName = (string)sp["name"];
                var lines = (set.lines ?? new BarkLine[0]).Where(l => l != null).ToList();
                foreach (JObject j in sp["lines"])
                {
                    string lid = (string)j["id"], text = (string)j["text"], requires = (string)j["requires"] ?? "";
                    foreach (var problem in QuestConditions.Problems(requires)) throw new Exception($"{id}/{lid}: unknown condition term '{problem}'");
                    var line = lines.FirstOrDefault(l => l.id == lid);
                    bool fresh = line == null;
                    if (fresh) { line = new BarkLine { id = lid }; lines.Add(line); added++; }
                    if (fresh || Force)
                    {
                        line.trigger = (BarkTrigger)Enum.Parse(typeof(BarkTrigger), (string)j["trigger"]);
                        line.text = text; line.requires = requires; line.hours = Hours(j["hours"]);
                        line.once = (bool?)j["once"] ?? false; line.weight = (float?)j["weight"] ?? 1;
                    }
                    var clipPath = BarkClipPath(id, lid);
                    Importer(clipPath, true);
                    var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(clipPath);
                    // A take speaks the JSON text; a line whose text was edited in the Inspector stays caption-only.
                    var want = clip && line.text == text ? clip : null;
                    if (line.voice != want) line.voice = want;
                    if (want) voiced++; else { captionOnly++; log.Add($"caption-only {id}/{lid}" + (clip ? " (text edited)" : " (no take)")); }
                }
                set.lines = lines.ToArray();
                EditorUtility.SetDirty(set);
            }
            AssetDatabase.SaveAssets();
            Report("assets", new { added, voiced, captionOnly, log });
            return $"{added} lines added, {voiced} voiced, {captionOnly} caption-only";
        }

        // ------------------------------------------------------------------ dialogue
        public static string Dialogue()
        {
            var src = Source; var log = new List<string>(); var touched = new HashSet<NpcDefinition>();
            foreach (JObject d in src["dialogue"])
            {
                string npc = (string)d["npc"], nodeId = (string)d["node"], text = (string)d["text"], old = (string)d["oldText"];
                var def = AssetDatabase.LoadAssetAtPath<NpcDefinition>(DataDir + npc + ".asset") ?? throw new Exception("Missing " + npc + ".asset");
                var node = def.nodes?.FirstOrDefault(n => n != null && n.id == nodeId) ?? throw new Exception($"{npc} has no node {nodeId}");
                if (old != null && node.text == old) { node.text = text; touched.Add(def); log.Add($"{npc}/{nodeId}: text updated (stale hotbar keys)"); }
                var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(VoiceClipPath(npc, nodeId));
                var want = clip && node.text == text ? clip : null;
                if (!want) log.Add($"{npc}/{nodeId}: " + (clip ? "text differs from the take, left unvoiced" : "no take"));
                if (node.voice != want && (want || node.voice == clip)) { node.voice = want; touched.Add(def); }
            }
            foreach (var def in touched) EditorUtility.SetDirty(def);
            AssetDatabase.SaveAssets();
            Report("dialogue", new { touched = touched.Select(t => t.name).ToArray(), log });
            return string.Join("; ", log.DefaultIfEmpty("no change"));
        }

        // ------------------------------------------------------------------ text (catalog descriptions)
        const string CatalogPath = "Assets/AthenHill/Data/CityCatalog.asset";
        /// CityCatalog item descriptions that named fixed hotbar keys ("Use with 9.") before the hotbar became configurable
        /// (5 Oct 2026). Changed only while an item still reads the old text, so later edits are never overwritten.
        public static string Text()
        {
            var log = new List<string>();
            var catalog = AssetDatabase.LoadAssetAtPath<CityCatalog>(CatalogPath) ?? throw new Exception("Missing " + CatalogPath);
            foreach (JObject c in Source["catalog"] ?? new JArray())
            {
                var item = catalog.items.FirstOrDefault(i => i != null && i.id == (string)c["item"]);
                if (item == null) { log.Add("no item " + c["item"]); continue; }
                if (item.description == (string)c["oldText"]) { item.description = (string)c["text"]; log.Add(item.id + " description updated"); }
                else if (item.description != (string)c["text"]) log.Add(item.id + ": description was edited since, left alone");
            }
            if (log.Any(l => l.EndsWith("updated"))) { EditorUtility.SetDirty(catalog); AssetDatabase.SaveAssets(); }
            Report("text", new { log });
            return string.Join("; ", log.DefaultIfEmpty("no change"));
        }

        // ------------------------------------------------------------------ scene
        static IEnumerable<T> SceneAll<T>() where T : Component => Object.FindObjectsByType<T>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(c => c && c.gameObject.scene.IsValid());
        /// Per-speaker NpcBarker tuning from barks.json ("barker": {"weaponRadius": 25}); applied only when the component is
        /// added (or with --force), so Inspector tuning survives a re-run.
        static void Overrides(NpcBarker b, JObject speaker)
        {
            if (!(speaker["barker"] is JObject o)) return;
            foreach (var p in o.Properties())
            {
                var f = typeof(NpcBarker).GetField(p.Name) ?? throw new Exception("NpcBarker has no field " + p.Name);
                f.SetValue(b, p.Value.ToObject(f.FieldType));
            }
        }
        public static string Scene()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var src = Source; var rec = LoadRec(); var log = new List<string>();
            var session = Object.FindAnyObjectByType<GameSession>() ?? throw new Exception("Saved city has no GameSession");
            var director = session.GetComponent<BarkDirector>();
            if (!director) { director = session.gameObject.AddComponent<BarkDirector>(); log.Add("BarkDirector added on " + session.name); }
            var barkers = new List<NpcBarker>();
            var speakers = src["speakers"].Cast<JObject>().ToDictionary(s => (string)s["id"]);
            foreach (var agent in SceneAll<NpcAgent>())
            {
                if (!agent.gameObject.activeInHierarchy) { log.Add("skipped inactive " + PathOf(agent.transform)); continue; }
                if (!agent.definition || !speakers.ContainsKey(agent.definition.id)) { log.Add("no bark set for " + PathOf(agent.transform)); continue; }
                var b = agent.GetComponent<NpcBarker>();
                if (!b || Force) { if (!b) { b = agent.gameObject.AddComponent<NpcBarker>(); log.Add("NpcBarker on " + PathOf(agent.transform)); } Overrides(b, speakers[agent.definition.id]); }
                b.agent = agent; b.barks = AssetDatabase.LoadAssetAtPath<BarkSet>(BarkSetPath(agent.definition.id)) ?? throw new Exception("Run the assets step first");
                EditorUtility.SetDirty(b); barkers.Add(b);
            }
            var walkers = SceneAll<AmbientWalker>().ToList();
            foreach (var sp in speakers.Values.Where(s => (string)s["kind"] == "walker"))
            {
                string id = (string)sp["id"], name = (string)sp["walker"];
                var w = walkers.FirstOrDefault(x => x.name == name) ?? throw new Exception("No ambient walker " + name);
                var b = w.GetComponent<NpcBarker>();
                if (!b || Force) { if (!b) { b = w.gameObject.AddComponent<NpcBarker>(); log.Add("NpcBarker on " + PathOf(w.transform)); } Overrides(b, sp); }
                b.agent = null; b.barks = AssetDatabase.LoadAssetAtPath<BarkSet>(BarkSetPath(id)) ?? throw new Exception("Run the assets step first");
                EditorUtility.SetDirty(b); barkers.Add(b);
                if (!w.actor) throw new Exception(name + " has no actor (WardWalkerInstall)");
                var look = w.actor.GetComponent<ActorLookAt>();
                if (!look)
                {
                    look = w.actor.gameObject.AddComponent<ActorLookAt>();
                    // A glance while passing: no rest levelling or idle glances, so the walk clip's own head motion stays.
                    look.actor = w.actor; look.focusRadius = 4.5f; look.maxYaw = 55; look.maxPitch = 10; look.restWeight = 0; look.focusWeight = .8f;
                    look.glanceYaw = 0; look.settleSeconds = .45f; look.activeDistance = 30;
                    var p = PathOf(look.transform); if (!rec.lookAtAdded.Contains(p)) rec.lookAtAdded.Add(p);
                    log.Add("ActorLookAt on " + p);
                }
            }
            director.speakers = barkers.ToArray(); EditorUtility.SetDirty(director);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            rec.log.Add(DateTime.UtcNow.ToString("u") + " scene: " + string.Join("; ", log.DefaultIfEmpty("no change"))); SaveRec(rec);
            Report("scene", new { speakers = barkers.Count, log });
            return $"{barkers.Count} speakers; " + string.Join("; ", log.DefaultIfEmpty("no change"));
        }

        // ------------------------------------------------------------------ verify
        public static string Verify()
        {
            EditorSceneManager.OpenScene(ScenePath);
            var src = Source; var problems = new List<string>(); var rows = new List<object>();
            var session = Object.FindAnyObjectByType<GameSession>();
            var director = session ? session.GetComponent<BarkDirector>() : null;
            if (!director) problems.Add("no BarkDirector on the GameSession");
            var barkers = SceneAll<NpcBarker>().ToList();
            foreach (JObject sp in src["speakers"])
            {
                string id = (string)sp["id"];
                var set = AssetDatabase.LoadAssetAtPath<BarkSet>(BarkSetPath(id));
                if (!set) { problems.Add("missing " + BarkSetPath(id)); continue; }
                var b = barkers.Where(x => x.barks == set).OrderByDescending(x => x.gameObject.activeInHierarchy).FirstOrDefault();
                if (!b) problems.Add("no NpcBarker uses " + id);
                else if (director && !director.speakers.Contains(b)) problems.Add(id + " is not in BarkDirector.speakers");
                if (b && (string)sp["kind"] == "npc" && (!b.agent || !b.agent.definition || b.agent.definition.id != id)) problems.Add(id + ": barker not on its NpcAgent");
                foreach (JObject j in sp["lines"])
                {
                    var line = set.lines.FirstOrDefault(l => l != null && l.id == (string)j["id"]);
                    if (line == null) { problems.Add($"{id}/{j["id"]} missing"); continue; }
                    foreach (var problem in QuestConditions.Problems(line.requires)) problems.Add($"{id}/{line.id}: bad condition {problem}");
                    if (!line.voice) problems.Add($"{id}/{line.id}: no voice");
                    else if (AssetDatabase.GetAssetPath(line.voice) != BarkClipPath(id, line.id) || line.voice.length < .5f) problems.Add($"{id}/{line.id}: wrong take");
                }
                object look = null;
                if (b && b.Walker)
                {
                    var walker = b.GetComponent<AmbientWalker>(); var la = walker && walker.actor ? walker.actor.GetComponent<ActorLookAt>() : null;
                    var bones = walker && walker.actor ? walker.actor.GetComponentsInChildren<Transform>(true).Select(t => t.name).ToList() : new List<string>();
                    if (!la) problems.Add(id + ": walker has no ActorLookAt");
                    if (!bones.Contains("Head")) problems.Add(id + ": walker rig has no Head bone (ActorLookAt would disable itself)");
                    look = new { lookAt = (bool)la, head = bones.Contains("Head"), neck = bones.Contains("neck") };
                }
                rows.Add(new { id, lines = set.lines.Length, voiced = set.lines.Count(l => l != null && l.voice), barker = b ? PathOf(b.transform) : null, look });
            }
            foreach (JObject d in src["dialogue"])
            {
                string npc = (string)d["npc"], nodeId = (string)d["node"];
                var def = AssetDatabase.LoadAssetAtPath<NpcDefinition>(DataDir + npc + ".asset");
                var node = def ? def.nodes.FirstOrDefault(n => n.id == nodeId) : null;
                if (node == null) { problems.Add($"{npc}/{nodeId} missing"); continue; }
                if (node.text != (string)d["text"]) problems.Add($"{npc}/{nodeId}: text differs from the voiced take");
                if (!node.voice || AssetDatabase.GetAssetPath(node.voice) != VoiceClipPath(npc, nodeId)) problems.Add($"{npc}/{nodeId}: take not bound");
            }
            var catalog = AssetDatabase.LoadAssetAtPath<CityCatalog>(CatalogPath);
            foreach (JObject c in Source["catalog"] ?? new JArray())
                if (catalog && catalog.items.FirstOrDefault(i => i != null && i.id == (string)c["item"])?.description == (string)c["oldText"]) problems.Add(c["item"] + ": stale hotbar key in its description");
            var uxml = File.ReadAllText(Path.Combine(Application.dataPath, "AthenHill/UI/CityHUD.uxml"));
            if (!uxml.Contains("name=\"bark-caption\"")) problems.Add("CityHUD.uxml has no bark-caption element (BarkCaptionView builds one at runtime)");
            Report("verify", new { problems, speakers = rows });
            if (problems.Count > 0) throw new Exception("NPC life verify: " + string.Join("; ", problems));
            return rows.Count + " speakers, dialogue takes bound, no problems";
        }

        // ------------------------------------------------------------------ rollback
        public static string Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var rec = LoadRec(); var log = new List<string>();
            foreach (var b in SceneAll<NpcBarker>().ToList()) { log.Add("removed NpcBarker " + PathOf(b.transform)); Object.DestroyImmediate(b); }
            foreach (var d in SceneAll<BarkDirector>().ToList()) { log.Add("removed BarkDirector"); Object.DestroyImmediate(d); }
            foreach (var la in SceneAll<ActorLookAt>().ToList()) if (rec.lookAtAdded.Contains(PathOf(la.transform))) { log.Add("removed ActorLookAt " + PathOf(la.transform)); Object.DestroyImmediate(la); }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            foreach (JObject d in Source["dialogue"])
            {
                string npc = (string)d["npc"], nodeId = (string)d["node"], old = (string)d["oldText"];
                var def = AssetDatabase.LoadAssetAtPath<NpcDefinition>(DataDir + npc + ".asset"); var node = def ? def.nodes.FirstOrDefault(n => n.id == nodeId) : null;
                if (node == null) continue;
                if (AssetDatabase.GetAssetPath(node.voice) == VoiceClipPath(npc, nodeId)) node.voice = null;
                if (old != null && node.text == (string)d["text"]) node.text = old;
                EditorUtility.SetDirty(def); log.Add($"{npc}/{nodeId} restored");
            }
            var cat = AssetDatabase.LoadAssetAtPath<CityCatalog>(CatalogPath);
            foreach (JObject c in Source["catalog"] ?? new JArray())
            {
                var item = cat ? cat.items.FirstOrDefault(i => i != null && i.id == (string)c["item"]) : null;
                if (item != null && item.description == (string)c["text"]) { item.description = (string)c["oldText"]; EditorUtility.SetDirty(cat); log.Add(item.id + " description restored"); }
            }
            AssetDatabase.SaveAssets();
            rec.lookAtAdded.Clear(); rec.log.Add(DateTime.UtcNow.ToString("u") + " rollback"); SaveRec(rec);
            Report("rollback", new { log });
            return string.Join("; ", log);
        }

        static void Report(string step, object body)
        {
            Directory.CreateDirectory(ArtDir);
            File.WriteAllText(Path.Combine(ArtDir, step + ".json"), JsonConvert.SerializeObject(new { step, utc = DateTime.UtcNow.ToString("u"), body }, Formatting.Indented));
        }

        [MenuItem("Athen Hill/NPC life/Install barks and voices (19 Nov 2026)")]
        static void InstallMenu()
        {
            if (EditorApplication.isPlaying) { Debug.LogError("Exit Play first."); return; }
            Debug.Log("NpcLife assets: " + Assets()); Debug.Log("NpcLife dialogue: " + Dialogue()); Debug.Log("NpcLife text: " + Text()); Debug.Log("NpcLife scene: " + Scene()); Debug.Log("NpcLife verify: " + Verify());
        }

        /// -executeMethod AthenHill.Editor.NpcLifeInstall20261119.RunBatch -nographics --steps assets,dialogue,text,scene,verify [--force]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = (i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify").Split(',');
            try
            {
                foreach (var st in steps)
                {
                    string result = st switch
                    {
                        "assets" => Assets(),
                        "dialogue" => Dialogue(),
                        "text" => Text(),
                        "scene" => Scene(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("NpcLifeInstall20261119 " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
