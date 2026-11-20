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
    /// <summary>
    /// Linn's voice, 20 Nov 2026 (Carl's playtest note "Linns voice does not match, should be more older and rough";
    /// art/linn_voice_20261120/README.md). The audio is made by art/linn_voice_20261120/linn_voice.py, which replaces the
    /// existing WAVs in place (same paths and GUIDs) and adds takes for the two housing nodes that were never voiced.
    /// This pass touches no scene object. Steps (each idempotent):
    ///   install   importer settings on Linn's four dialogue takes (as the 2 Oct NpcVoices imports: Vorbis 0.85,
    ///             decompress on load, mono, preload) and binds NpcVoices/npc_linn-housing.wav and -housing_leased.wav to
    ///             those nodes of Data/npc_linn.asset (only while the node has no clip or already has that clip).
    ///   verify    every Linn dialogue node and bark line has its take at the canonical path, each clip's imported length
    ///             matches the newly mastered WAV (art/linn_voice_20261120/installed.json, proves the re-import), writes
    ///             art/linn_voice_20261120/verify.json; throws on a problem.
    ///   rollback  clears the two housing takes again (only when they still hold this pass's clips). The other clips are
    ///             restored on disk by `python3 art/linn_voice_20261120/linn_voice.py --rollback`.
    /// -executeMethod AthenHill.Editor.LinnVoicePass20261120.RunBatch -nographics --steps install,verify
    /// </summary>
    public static class LinnVoicePass20261120
    {
        const string DefinitionPath = "Assets/AthenHill/Data/npc_linn.asset";
        const string BarkSetPath = "Assets/AthenHill/Data/Barks/barks_npc_linn.asset";
        const string VoiceAudio = "Assets/AthenHill/Audio/ElevenLabs/NpcVoices/";
        const string BarkAudio = "Assets/AthenHill/Audio/ElevenLabs/NpcBarks/";
        static readonly string[] NewNodes = { "housing", "housing_leased" };
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string ArtDir => Path.Combine(Repo, "art/linn_voice_20261120");
        static string Evidence => Path.Combine(Repo, "unity/evidence/showcase_phase2/20261120/linn_voice");
        static string VoicePath(string node) => VoiceAudio + "npc_linn-" + node + ".wav";

        static void Importer(string path)
        {
            var ai = AssetImporter.GetAtPath(path) as AudioImporter;
            if (!ai) throw new Exception("no AudioImporter at " + path);
            var s = ai.defaultSampleSettings;
            if (ai.forceToMono && !ai.loadInBackground && s.loadType == AudioClipLoadType.DecompressOnLoad &&
                s.compressionFormat == AudioCompressionFormat.Vorbis && Mathf.Approximately(s.quality, .85f) && s.preloadAudioData) return;
            s.loadType = AudioClipLoadType.DecompressOnLoad; s.compressionFormat = AudioCompressionFormat.Vorbis; s.quality = .85f; s.preloadAudioData = true;
            ai.defaultSampleSettings = s; ai.forceToMono = true; ai.loadInBackground = false;
            ai.SaveAndReimport();
        }

        static string Install()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var log = new List<string>();
            var def = AssetDatabase.LoadAssetAtPath<NpcDefinition>(DefinitionPath);
            if (!def) throw new Exception("missing " + DefinitionPath);
            foreach (var node in def.nodes)
                if (File.Exists(Path.Combine(Repo, "unity/AthenHill", VoicePath(node.id)))) Importer(VoicePath(node.id));
            var so = new SerializedObject(def);
            var nodes = so.FindProperty("nodes");
            bool changed = false;
            for (int i = 0; i < nodes.arraySize; i++)
            {
                var n = nodes.GetArrayElementAtIndex(i);
                var id = n.FindPropertyRelative("id").stringValue;
                if (!NewNodes.Contains(id)) continue;
                var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(VoicePath(id));
                if (!clip) throw new Exception("take not imported: " + VoicePath(id) + " (run linn_voice.py --generate first)");
                var voice = n.FindPropertyRelative("voice");
                if (voice.objectReferenceValue == clip) { log.Add(id + " already bound"); continue; }
                if (voice.objectReferenceValue) { log.Add(id + " keeps its other clip " + AssetDatabase.GetAssetPath(voice.objectReferenceValue)); continue; }
                voice.objectReferenceValue = clip; changed = true; log.Add(id + " bound to " + VoicePath(id));
            }
            if (changed) { so.ApplyModifiedPropertiesWithoutUndo(); EditorUtility.SetDirty(def); AssetDatabase.SaveAssets(); }
            Report("install", new { log });
            return string.Join("; ", log);
        }

        static string Rollback()
        {
            var log = new List<string>();
            var def = AssetDatabase.LoadAssetAtPath<NpcDefinition>(DefinitionPath);
            var so = new SerializedObject(def);
            var nodes = so.FindProperty("nodes");
            bool changed = false;
            for (int i = 0; i < nodes.arraySize; i++)
            {
                var n = nodes.GetArrayElementAtIndex(i);
                var id = n.FindPropertyRelative("id").stringValue;
                if (!NewNodes.Contains(id)) continue;
                var voice = n.FindPropertyRelative("voice");
                if (voice.objectReferenceValue && AssetDatabase.GetAssetPath(voice.objectReferenceValue) == VoicePath(id))
                { voice.objectReferenceValue = null; changed = true; log.Add(id + " unvoiced"); }
                else log.Add(id + " left as is");
            }
            if (changed) { so.ApplyModifiedPropertiesWithoutUndo(); EditorUtility.SetDirty(def); AssetDatabase.SaveAssets(); }
            Report("rollback", new { log });
            return string.Join("; ", log);
        }

        static string Verify()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var problems = new List<string>();
            var rows = new List<object>();
            var installedPath = Path.Combine(ArtDir, "installed.json");
            var installed = File.Exists(installedPath) ? JObject.Parse(File.ReadAllText(installedPath)) : null;
            void Check(string kind, string id, AudioClip clip, string expected)
            {
                var path = clip ? AssetDatabase.GetAssetPath(clip) : null;
                if (path != expected) problems.Add(kind + " " + id + ": clip " + (path ?? "none") + ", expected " + expected);
                double? wav = (double?)installed?["lines"]?[id]?["after"]?["seconds"];
                float len = clip ? clip.length : 0;
                if (clip && len < .5f) problems.Add(kind + " " + id + ": clip only " + len + " s");
                if (clip && wav.HasValue && Math.Abs(len - wav.Value) > .05) problems.Add(kind + " " + id + ": imported " + len.ToString("0.000") + " s but the mastered WAV is " + wav.Value + " s (not re-imported?)");
                var ai = path != null ? AssetImporter.GetAtPath(path) as AudioImporter : null;
                rows.Add(new { kind, id, path, seconds = Math.Round(len, 3), wavSeconds = wav, channels = clip ? clip.channels : 0,
                    frequency = clip ? clip.frequency : 0, mono = ai && ai.forceToMono, loadType = ai ? ai.defaultSampleSettings.loadType.ToString() : null });
            }
            var def = AssetDatabase.LoadAssetAtPath<NpcDefinition>(DefinitionPath);
            if (!def) problems.Add("missing " + DefinitionPath);
            else foreach (var n in def.nodes)
                {
                    if (string.IsNullOrWhiteSpace(n.text)) problems.Add("node " + n.id + " has no text");
                    Check("dialogue", n.id, n.voice, VoicePath(n.id));
                }
            var set = AssetDatabase.LoadAssetAtPath<BarkSet>(BarkSetPath);
            if (!set) problems.Add("missing " + BarkSetPath);
            else foreach (var l in set.lines) Check("bark", l.id, l.voice, BarkAudio + "npc_linn-" + l.id + ".wav");
            if (installed == null) problems.Add("no art/linn_voice_20261120/installed.json (lengths not compared)");
            var result = new { ok = problems.Count == 0, voice = (string)installed?["voice_name"], voiceId = (string)installed?["voice_id"],
                dialogueNodes = def ? def.nodes.Length : 0, barkLines = set ? set.lines.Length : 0, problems, clips = rows };
            Report("verify", result);
            Directory.CreateDirectory(Evidence);
            File.Copy(Path.Combine(ArtDir, "verify.json"), Path.Combine(Evidence, "verify.json"), true);
            if (problems.Count > 0) throw new Exception("LinnVoicePass20261120 verify: " + string.Join(" | ", problems));
            return "ok: " + rows.Count + " clips";
        }

        static void Report(string step, object body)
        {
            Directory.CreateDirectory(ArtDir);
            File.WriteAllText(Path.Combine(ArtDir, step + ".json"),
                JsonConvert.SerializeObject(new { step, utc = DateTime.UtcNow.ToString("u"), body }, Formatting.Indented));
        }

        /// -executeMethod AthenHill.Editor.LinnVoicePass20261120.RunBatch -nographics --steps install,verify | rollback
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
                        "install" => Install(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("LinnVoicePass20261120 " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
