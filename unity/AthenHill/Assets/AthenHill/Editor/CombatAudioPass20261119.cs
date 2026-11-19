using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Audio;

namespace AthenHill.Editor
{
    /// <summary>
    /// Combat audio pass, 19 Nov 2026 (art/showcase_20261119/combat_audio/README.md): the field rifle's own layered set
    /// and sound identity for the Scrap Reaper, Post Sentinel, Feral Gunner, Feral Lancer and Depot Foreman, plus bolt
    /// fly-bys and impacts. Idempotent; touches only the fields listed here and never calls another install pass.
    ///
    /// Steps (comma separated, in this order for a first install):
    ///   audio    import the clips under Audio/ElevenLabs/Combat/Rifle and /Droids (PCM, decompress on load, preloaded)
    ///   weapon   PlayerCombat.weaponSounds: the weapon_field_rifle set (gains from the generator's manifest)
    ///   droids   per-kind variant arrays, voice source on SFX with a desert rolloff, the Sentinel's roll loop child
    ///   bolts    fly-by / impact clip arrays and their source's rolloff and mixer group on the three bolt prefabs
    ///   verify   checks everything above and prints the distances and gains
    ///   rollback restores every recorded value, removes the roll loop child and the rifle set
    ///   sfxall   optional, not part of the install: moves the untouched droids' (worker, scrap drone) voices from the UI
    ///            group to SFX as well (recorded, undone by rollback)
    ///
    /// -executeMethod AthenHill.Editor.CombatAudioPass20261119.RunBatch --steps audio,weapon,droids,bolts,verify
    /// </summary>
    public static class CombatAudioPass20261119
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string DroidDir = "Assets/AthenHill/Prefabs/OuterBerms/";
        const string RifleDir = "Assets/AthenHill/Audio/ElevenLabs/Combat/Rifle/";
        const string ClipDir = "Assets/AthenHill/Audio/ElevenLabs/Combat/Droids/";
        const string MixerPath = "Assets/AthenHill/Audio/City.mixer";
        const string RifleId = "weapon_field_rifle";
        const string RollName = "Roll loop audio";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string ArtDir => Path.Combine(Repo, "art/showcase_20261119/combat_audio");
        static string RecordPath => Path.Combine(ArtDir, "record.json");

        // ------------------------------------------------------------------ what goes where
        class Kind
        {
            public string prefab; public float min, max;
            public string[] alert = { }, windup = { }, strike = { }, slam = { }, fire = { }, death = { }, step = { };
            public bool roll;
        }
        // Distances (metres): heard well before the 30-36 m aggro radii and the ~40 m far-idle line, silent beyond Max
        // (CombatAudio.DesertRolloff). The bowl is ~500 m across, so nothing carries more than a fifth of it.
        static readonly Kind[] Kinds =
        {
            new Kind { prefab = "FeralScrapReaper", min = 3, max = 70, alert = new[] { "reaper-alert" }, windup = new[] { "reaper-windup" },
                strike = new[] { "reaper-strike-1", "reaper-strike-2" }, death = new[] { "reaper-death" }, step = new[] { "reaper-step-1", "reaper-step-2" } },
            new Kind { prefab = "FeralPostSentinel", min = 3, max = 90, alert = new[] { "sentinel-alert" }, windup = new[] { "sentinel-aim" },
                fire = new[] { "sentinel-fire-1", "sentinel-fire-2" }, death = new[] { "sentinel-death" }, roll = true },
            new Kind { prefab = "FeralGunnerDroid", min = 2.5f, max = 75, alert = new[] { "gunner-alert" }, windup = new[] { "gunner-tell" },
                fire = new[] { "gunner-shot-1", "gunner-shot-2" }, death = new[] { "gunner-death" } },
            new Kind { prefab = "FeralLancerDrone", min = 2.5f, max = 80, alert = new[] { "lancer-alert" }, windup = new[] { "lancer-tell" },
                fire = new[] { "lancer-launch-1", "lancer-launch-2" }, death = new[] { "lancer-death" } },
            new Kind { prefab = "FeralDepotForeman", min = 4, max = 90, alert = new[] { "foreman-alert" }, windup = new[] { "foreman-windup" },
                strike = new[] { "foreman-strike" }, slam = new[] { "foreman-slam" }, death = new[] { "foreman-death" }, step = new[] { "reaper-step-1", "reaper-step-2" } },
        };
        // The roll loop's wider Min Distance keeps it about -15 dB at 60 m, where an idle or patrolling Sentinel is still a dot.
        const float RollMin = 12, RollMax = 120, BoltMin = 1.5f, BoltMax = 50;
        static readonly Dictionary<string, (string[] flyby, string[] impact)> BoltClips = new Dictionary<string, (string[], string[])>
        {
            ["FeralGunnerDroid"] = (new[] { "bolt-flyby-1", "bolt-flyby-2", "bolt-flyby-4" }, new[] { "bolt-impact-1", "bolt-impact-2" }),
            ["FeralPostSentinel"] = (new[] { "bolt-flyby-1", "bolt-flyby-2", "bolt-flyby-4" }, new[] { "bolt-impact-1", "bolt-impact-2" }),
            ["FeralLancerDrone"] = (new[] { "bolt-flyby-1", "bolt-flyby-2", "bolt-flyby-4" }, new[] { "lancer-impact" }),
        };
        static readonly string[] DroidFields = { "alertVariants", "windupVariants", "strikeVariants", "slamVariants", "fireVariants", "deathVariants", "stepVariants", "rollLoop" };
        static readonly string[] SourceProps = { "OutputAudioMixerGroup", "MinDistance", "MaxDistance", "rolloffMode", "rolloffCustomCurve", "Priority", "DopplerLevel", "panLevelCustomCurve" };

        // ------------------------------------------------------------------ record
        class Key { public float t, v, i, o; }
        class SourceRec
        {
            public string group; public float min, max, doppler, blend; public int mode, priority; public List<Key> curve = new List<Key>();
            public List<string> overridden = new List<string>();
        }
        class BoltRec { public List<string> flyby = new List<string>(), impact = new List<string>(); public SourceRec source; }
        class Rec
        {
            public Dictionary<string, SourceRec> voices = new Dictionary<string, SourceRec>();
            public List<string> droids = new List<string>(), rollLoops = new List<string>();
            public Dictionary<string, BoltRec> bolts = new Dictionary<string, BoltRec>();
            public bool weaponSet;
            public List<string> log = new List<string>();
        }
        static Rec rec;
        static Rec Load() => File.Exists(RecordPath) ? JsonConvert.DeserializeObject<Rec>(File.ReadAllText(RecordPath)) ?? new Rec() : new Rec();
        static void Save() { Directory.CreateDirectory(ArtDir); File.WriteAllText(RecordPath, JsonConvert.SerializeObject(rec, Formatting.Indented)); }

        static string GroupKey(AudioMixerGroup g) => g ? AssetDatabase.GetAssetPath(g) + "#" + g.name : null;
        static AudioMixerGroup GroupFrom(string key)
        {
            if (string.IsNullOrEmpty(key)) return null;
            var parts = key.Split('#');
            return AssetDatabase.LoadAllAssetsAtPath(parts[0]).OfType<AudioMixerGroup>().FirstOrDefault(g => g.name == parts[1]);
        }
        static AudioMixerGroup Sfx()
        {
            var g = AssetDatabase.LoadAllAssetsAtPath(MixerPath).OfType<AudioMixerGroup>().FirstOrDefault(x => x.name == "SFX");
            if (!g) throw new Exception("No SFX group in " + MixerPath);
            return g;
        }

        static SourceRec Capture(AudioSource s, bool variant)
        {
            var r = new SourceRec { group = GroupKey(s.outputAudioMixerGroup), min = s.minDistance, max = s.maxDistance, doppler = s.dopplerLevel, blend = s.spatialBlend, mode = (int)s.rolloffMode, priority = s.priority };
            var c = s.GetCustomCurve(AudioSourceCurveType.CustomRolloff);
            if (c != null) r.curve = c.keys.Select(k => new Key { t = k.time, v = k.value, i = k.inTangent, o = k.outTangent }).ToList();
            if (variant)
            {
                var so = new SerializedObject(s);
                foreach (var p in SourceProps) { var sp = so.FindProperty(p); if (sp != null && sp.prefabOverride) r.overridden.Add(p); }
            }
            return r;
        }
        static void Restore(AudioSource s, SourceRec r, bool variant)
        {
            s.outputAudioMixerGroup = GroupFrom(r.group); s.minDistance = r.min; s.maxDistance = r.max; s.dopplerLevel = r.doppler; s.priority = r.priority; s.spatialBlend = r.blend;
            s.rolloffMode = (AudioRolloffMode)r.mode;
            if (r.curve.Count > 0) s.SetCustomCurve(AudioSourceCurveType.CustomRolloff, new AnimationCurve(r.curve.Select(k => new Keyframe(k.t, k.v, k.i, k.o)).ToArray()));
            if (!variant) return;
            // properties the variant did not override before this pass go back to inheriting from the base
            var so = new SerializedObject(s);
            foreach (var p in SourceProps)
            {
                if (r.overridden.Contains(p)) continue;
                var sp = so.FindProperty(p);
                if (sp != null && sp.prefabOverride) PrefabUtility.RevertPropertyOverride(sp, InteractionMode.AutomatedAction);
            }
        }
        static void Desert(AudioSource s, float min, float max, AudioMixerGroup sfx)
        {
            s.outputAudioMixerGroup = sfx; s.spatialBlend = 1; s.dopplerLevel = 0;
            s.minDistance = min; s.maxDistance = max; s.rolloffMode = AudioRolloffMode.Custom;
            s.SetCustomCurve(AudioSourceCurveType.CustomRolloff, CombatAudio.DesertRolloff(min, max));
        }

        static AudioClip Clip(string dir, string name)
        {
            var c = AssetDatabase.LoadAssetAtPath<AudioClip>(dir + name + ".wav");
            if (!c) throw new Exception($"Missing {dir}{name}.wav: run unity/tools/generate_combat_audio_20261119.py and the audio step");
            return c;
        }
        static AudioClip[] Clips(string[] names) => names.Select(n => Clip(ClipDir, n)).ToArray();
        static AudioClip[] RifleClips(string layer) => Directory.GetFiles(Path.Combine(Repo, "unity/AthenHill", RifleDir), "rifle-" + layer + "-*.wav").OrderBy(f => f)
            .Select(f => Clip(RifleDir, Path.GetFileNameWithoutExtension(f))).ToArray();
        static bool IsVariant(string path) => PrefabUtility.GetPrefabAssetType(AssetDatabase.LoadAssetAtPath<GameObject>(path)) == PrefabAssetType.Variant;

        // ------------------------------------------------------------------ audio
        static string Audio()
        {
            int n = 0;
            foreach (var dir in new[] { RifleDir, ClipDir })
                foreach (var file in Directory.GetFiles(Path.Combine(Repo, "unity/AthenHill", dir), "*.wav").OrderBy(f => f))
                {
                    string path = dir + Path.GetFileName(file);
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                    var imp = (AudioImporter)AssetImporter.GetAtPath(path);
                    var s = imp.defaultSampleSettings;
                    bool loop = path.EndsWith("-loop.wav");
                    // one-shots fire on the frame of the event: decompressed and preloaded; the 4 s roll loop is small too
                    s.loadType = AudioClipLoadType.DecompressOnLoad; s.compressionFormat = loop ? AudioCompressionFormat.Vorbis : AudioCompressionFormat.PCM;
                    s.quality = .7f; s.preloadAudioData = true;
                    imp.defaultSampleSettings = s; imp.forceToMono = false; imp.loadInBackground = false;
                    imp.SaveAndReimport(); n++;
                }
            return n + " clips imported";
        }

        // ------------------------------------------------------------------ weapon
        static (float mech, float body, float tail) Gains()
        {
            var path = Path.Combine(ArtDir, "manifest.json");
            try
            {
                var g = JObject.Parse(File.ReadAllText(path))["balance"]["rifle_runtime_layer_gains"];
                return ((float)g["mech"], (float)g["body"], (float)g["tail"]);
            }
            catch { return (.512f, .699f, .354f); }   // the 19 Nov 2026 measurement
        }

        static string Weapon()
        {
            var combat = UnityEngine.Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);
            if (!combat) throw new Exception("No PlayerCombat in the scene");
            var (mech, body, tail) = Gains();
            var set = new WeaponSoundSet
            {
                weaponId = RifleId, mech = RifleClips("mech"), body = RifleClips("body"), tail = RifleClips("tail"),
                empty = RifleClips("empty"), draw = RifleClips("draw"), holster = RifleClips("holster"),
                mechGain = mech, bodyGain = body, tailGain = tail, pitch = new Vector2(.98f, 1.02f), burstTailScale = .75f,
            };
            if (set.body.Length == 0) throw new Exception("Rifle body layer missing");
            Undo.RecordObject(combat, "Rifle sound set");
            var list = (combat.weaponSounds ?? new WeaponSoundSet[0]).Where(s => s != null && s.weaponId != RifleId).ToList();
            list.Add(set); combat.weaponSounds = list.ToArray();
            EditorUtility.SetDirty(combat); rec.weaponSet = true;
            return $"{RifleId}: mech {set.mech.Length} body {set.body.Length} tail {set.tail.Length} empty {set.empty.Length} draw {set.draw.Length} holster {set.holster.Length}; gains {mech}/{body}/{tail}, burst tail ×{set.burstTailScale}";
        }

        // ------------------------------------------------------------------ droids
        static string Droids()
        {
            var sfx = Sfx(); var lines = new List<string>();
            foreach (var k in Kinds)
            {
                string path = DroidDir + k.prefab + ".prefab";
                if (!AssetDatabase.LoadAssetAtPath<GameObject>(path)) { lines.Add(k.prefab + " missing: skipped"); continue; }
                bool variant = IsVariant(path);
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var d = root.GetComponent<FeralDroid>();
                    if (!d.voice) { lines.Add(k.prefab + " has no voice source: skipped"); continue; }
                    d.alertVariants = Clips(k.alert); d.windupVariants = Clips(k.windup); d.strikeVariants = Clips(k.strike); d.slamVariants = Clips(k.slam);
                    d.fireVariants = Clips(k.fire); d.deathVariants = Clips(k.death); d.stepVariants = Clips(k.step); d.limitVoices = true;
                    if (!rec.voices.ContainsKey(path)) rec.voices[path] = Capture(d.voice, variant);
                    Desert(d.voice, k.min, k.max, sfx);
                    d.voice.priority = 96;   // tells and deaths outrank ambience when the 32 real voices run out
                    if (k.roll)
                    {
                        var t = root.transform.Find(RollName);
                        var src = t ? t.GetComponent<AudioSource>() : null;
                        if (!src) { var go = new GameObject(RollName); go.transform.SetParent(root.transform, false); go.transform.localPosition = Vector3.up * .4f; src = go.AddComponent<AudioSource>(); if (!rec.rollLoops.Contains(path)) rec.rollLoops.Add(path); }
                        src.clip = Clip(ClipDir, "sentinel-roll-loop"); src.loop = true; src.playOnAwake = false; src.volume = 0; src.priority = 140;
                        Desert(src, RollMin, RollMax, sfx);
                        d.rollLoop = src; d.rollFullSpeed = Mathf.Max(.5f, d.chaseSpeed);
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    if (!rec.droids.Contains(path)) rec.droids.Add(path);
                    lines.Add($"{k.prefab}{(variant ? " (variant)" : "")}: voice {k.min}-{k.max} m SFX{(k.roll ? $", roll loop {RollMin}-{RollMax} m full at {d.rollFullSpeed} m/s" : "")}");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            return string.Join(" | ", lines);
        }

        static string SfxAll()
        {
            var sfx = Sfx(); var lines = new List<string>();
            foreach (var path in AssetDatabase.FindAssets("t:Prefab", new[] { DroidDir.TrimEnd('/') }).Select(AssetDatabase.GUIDToAssetPath).Where(p => Path.GetDirectoryName(p).Replace('\\', '/') + "/" == DroidDir))
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (!go || !go.GetComponent<FeralDroid>() || rec.voices.ContainsKey(path)) continue;
                bool variant = IsVariant(path);
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var d = root.GetComponent<FeralDroid>();
                    if (!d.voice || d.voice.outputAudioMixerGroup == sfx) continue;
                    rec.voices[path] = Capture(d.voice, variant);
                    d.voice.outputAudioMixerGroup = sfx;
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    lines.Add(Path.GetFileNameWithoutExtension(path) + " voice -> SFX");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            return lines.Count > 0 ? string.Join("; ", lines) : "nothing to move";
        }

        // ------------------------------------------------------------------ bolts
        static string Bolts()
        {
            var sfx = Sfx(); var lines = new List<string>();
            foreach (var kv in BoltClips)
            {
                var droid = AssetDatabase.LoadAssetAtPath<GameObject>(DroidDir + kv.Key + ".prefab");
                var boltPrefab = droid ? droid.GetComponent<FeralDroid>().boltPrefab : null;
                if (!boltPrefab) { lines.Add(kv.Key + " has no bolt prefab: skipped"); continue; }
                string path = AssetDatabase.GetAssetPath(boltPrefab);
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var bolt = root.GetComponent<DroidBolt>();
                    if (!bolt.impactAudio) { lines.Add(Path.GetFileNameWithoutExtension(path) + " has no audio source: skipped"); continue; }
                    if (!rec.bolts.ContainsKey(path))
                        rec.bolts[path] = new BoltRec
                        {
                            flyby = bolt.flybyClips.Select(c => c ? AssetDatabase.GetAssetPath(c) : null).ToList(),
                            impact = bolt.impactClips.Select(c => c ? AssetDatabase.GetAssetPath(c) : null).ToList(),
                            source = Capture(bolt.impactAudio, IsVariant(path)),
                        };
                    bolt.flybyClips = Clips(kv.Value.flyby); bolt.impactClips = Clips(kv.Value.impact);
                    Desert(bolt.impactAudio, BoltMin, BoltMax, sfx);   // the fly-by already carries its own doppler sweep
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    lines.Add($"{Path.GetFileNameWithoutExtension(path)}: flyby {bolt.flybyClips.Length}, impact {bolt.impactClips.Length}, {BoltMin}-{BoltMax} m SFX");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            return string.Join(" | ", lines);
        }

        // ------------------------------------------------------------------ verify
        static string Verify()
        {
            var problems = new List<string>(); var lines = new List<string>();
            var sfx = Sfx();
            var combat = UnityEngine.Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);
            var set = combat ? CombatAudio.SelectSet(combat.weaponSounds, RifleId) : null;
            if (set == null) problems.Add("no usable rifle set on PlayerCombat");
            else
            {
                if (set.mech.Length < 6 || set.body.Length < 8 || set.tail.Length < 6) problems.Add($"rifle set short: {set.mech.Length}/{set.body.Length}/{set.tail.Length}");
                if (set.mech.Concat(set.body).Concat(set.tail).Concat(set.empty).Concat(set.draw).Concat(set.holster).Any(c => !c)) problems.Add("rifle set has a missing clip");
                lines.Add($"rifle gains {set.mechGain}/{set.bodyGain}/{set.tailGain}");
            }
            if (combat && CombatAudio.SelectSet(combat.weaponSounds, "weapon_scrap_pistol") != null) problems.Add("a pistol set exists: the pistol must keep its legacy arrays");
            foreach (var k in Kinds)
            {
                string path = DroidDir + k.prefab + ".prefab";
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (!go) { problems.Add(path + " missing"); continue; }
                var d = go.GetComponent<FeralDroid>();
                if (d.alertVariants.Length == 0 || d.deathVariants.Length == 0 || d.windupVariants.Length == 0) problems.Add(k.prefab + ": variants");
                if (d.alertVariants.Concat(d.windupVariants).Concat(d.strikeVariants).Concat(d.slamVariants).Concat(d.fireVariants).Concat(d.deathVariants).Concat(d.stepVariants).Any(c => !c)) problems.Add(k.prefab + ": missing clip");
                CheckSource(d.voice, k.prefab + " voice", k.max, sfx, problems);
                if (k.roll) { if (!d.rollLoop || !d.rollLoop.clip || !d.rollLoop.loop || d.rollLoop.playOnAwake) problems.Add(k.prefab + ": roll loop"); else CheckSource(d.rollLoop, k.prefab + " roll", RollMax, sfx, problems); }
                lines.Add($"{k.prefab} {d.voice.minDistance}-{d.voice.maxDistance} m");
            }
            foreach (var kv in BoltClips)
            {
                var droid = AssetDatabase.LoadAssetAtPath<GameObject>(DroidDir + kv.Key + ".prefab");
                var bolt = droid ? droid.GetComponent<FeralDroid>().boltPrefab : null;
                if (!bolt) continue;
                if (bolt.flybyClips.Length != kv.Value.flyby.Length || bolt.impactClips.Length != kv.Value.impact.Length || bolt.flybyClips.Concat(bolt.impactClips).Any(c => !c)) problems.Add(bolt.name + ": clips");
                CheckSource(bolt.impactAudio, bolt.name, BoltMax, sfx, problems);
            }
            return (problems.Count == 0 ? "PASS" : "FAIL: " + string.Join("; ", problems)) + " | " + string.Join(" | ", lines);
        }
        static void CheckSource(AudioSource s, string label, float max, AudioMixerGroup sfx, List<string> problems)
        {
            if (!s) { problems.Add(label + ": no source"); return; }
            if (s.outputAudioMixerGroup != sfx) problems.Add(label + ": not on SFX");
            if (s.rolloffMode != AudioRolloffMode.Custom || Mathf.Abs(s.maxDistance - max) > .01f) problems.Add(label + ": rolloff");
            var c = s.GetCustomCurve(AudioSourceCurveType.CustomRolloff);
            if (c == null || c.length < 3 || c.Evaluate(1) > .001f || c.Evaluate(0) < .99f) problems.Add(label + ": curve does not fall from 1 to 0");
            if (s.spatialBlend < .99f) problems.Add(label + ": not 3D");
        }

        // ------------------------------------------------------------------ rollback
        static string Rollback()
        {
            var lines = new List<string>();
            var combat = UnityEngine.Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);
            if (combat && rec.weaponSet)
            {
                Undo.RecordObject(combat, "Rifle sound set rollback");
                combat.weaponSounds = (combat.weaponSounds ?? new WeaponSoundSet[0]).Where(s => s != null && s.weaponId != RifleId).ToArray();
                EditorUtility.SetDirty(combat); rec.weaponSet = false; lines.Add("rifle set removed");
            }
            foreach (var path in rec.voices.Keys.Union(rec.droids).ToList())
            {
                if (!AssetDatabase.LoadAssetAtPath<GameObject>(path)) continue;
                bool variant = IsVariant(path);
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var d = root.GetComponent<FeralDroid>();
                    if (rec.droids.Contains(path))
                    {
                        if (variant)
                        {
                            var so = new SerializedObject(d);
                            foreach (var f in DroidFields) { var sp = so.FindProperty(f); if (sp != null && sp.prefabOverride) PrefabUtility.RevertPropertyOverride(sp, InteractionMode.AutomatedAction); }
                        }
                        else
                        {
                            d.alertVariants = d.windupVariants = d.strikeVariants = d.slamVariants = new AudioClip[0];
                            d.fireVariants = d.hitVariants = d.deathVariants = d.stepVariants = new AudioClip[0]; d.rollLoop = null;
                        }
                        var t = root.transform.Find(RollName);
                        if (t && rec.rollLoops.Contains(path)) UnityEngine.Object.DestroyImmediate(t.gameObject);
                    }
                    if (d.voice && rec.voices.TryGetValue(path, out var r)) Restore(d.voice, r, variant);
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    lines.Add("restored " + Path.GetFileNameWithoutExtension(path));
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            rec.voices.Clear(); rec.droids.Clear(); rec.rollLoops.Clear();
            foreach (var kv in rec.bolts.ToList())
            {
                if (!AssetDatabase.LoadAssetAtPath<GameObject>(kv.Key)) continue;
                var root = PrefabUtility.LoadPrefabContents(kv.Key);
                try
                {
                    var bolt = root.GetComponent<DroidBolt>();
                    bolt.flybyClips = kv.Value.flyby.Select(p => string.IsNullOrEmpty(p) ? null : AssetDatabase.LoadAssetAtPath<AudioClip>(p)).ToArray();
                    bolt.impactClips = kv.Value.impact.Select(p => string.IsNullOrEmpty(p) ? null : AssetDatabase.LoadAssetAtPath<AudioClip>(p)).ToArray();
                    if (bolt.impactAudio && kv.Value.source != null) Restore(bolt.impactAudio, kv.Value.source, IsVariant(kv.Key));
                    PrefabUtility.SaveAsPrefabAsset(root, kv.Key);
                    lines.Add("restored " + Path.GetFileNameWithoutExtension(kv.Key));
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            rec.bolts.Clear();
            lines.Add("clips under Combat/Rifle and Combat/Droids are kept, unused");
            return string.Join("; ", lines);
        }

        // ------------------------------------------------------------------ batch entry
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = (i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify").Split(',');
            try
            {
                EditorSceneManager.OpenScene(ScenePath);
                rec = Load();
                bool dirty = false, failed = false;
                foreach (var st in steps)
                {
                    string r = st switch
                    {
                        "audio" => Audio(), "weapon" => Weapon(), "droids" => Droids(), "bolts" => Bolts(), "sfxall" => SfxAll(),
                        "verify" => Verify(), "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st)
                    };
                    if (st == "weapon" || st == "rollback") dirty = true;
                    if (st == "verify" && !r.StartsWith("PASS")) failed = true;
                    rec.log.Add(DateTime.UtcNow.ToString("u") + " " + st + ": " + r);
                    Debug.Log("CombatAudioPass20261119 " + st + ": " + r);
                    Save();
                }
                if (dirty) { var scene = EditorSceneManager.GetActiveScene(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); }
                AssetDatabase.SaveAssets();
                Save();
                EditorApplication.Exit(failed ? 2 : 0);
            }
            catch (Exception e)
            {
                Debug.LogError("CombatAudioPass20261119 failed: " + e);
                if (rec != null) { rec.log.Add(DateTime.UtcNow.ToString("u") + " ERROR " + e.Message); Save(); }
                EditorApplication.Exit(1);
            }
        }

        [MenuItem("Athen Hill/Combat/Combat audio pass (19 Nov 2026): install")]
        static void MenuInstall() { rec = Load(); Debug.Log(Audio() + "\n" + Weapon() + "\n" + Droids() + "\n" + Bolts() + "\n" + Verify()); EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene()); Save(); }
    }
}
