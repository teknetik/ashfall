using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>Checks imported dialogue clips and scene bindings before the native build.</summary>
    public static class NpcVoiceAudit
    {
        static readonly Dictionary<string, int> Expected = new Dictionary<string, int>
        {
            {"npc_mira", 1}, {"npc_torr", 2}, {"npc_vex", 2}, {"npc_linn", 2},
            {"npc_brann", 15}, {"npc_ossa", 6}, {"npc_rell", 2}
        };

        public static void VerifyAndBuild()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>();
            if (!session) throw new Exception("Saved city has no GameSession");
            var actors = session.npcs.Where(n => n && n.definition).ToDictionary(n => n.definition.id, n => n);
            if (actors.Count != Expected.Count || Expected.Keys.Any(id => !actors.ContainsKey(id)))
                throw new Exception("Saved city NPC roster does not match the voice roster");
            var lines = new List<object>();
            foreach (var pair in Expected)
            {
                var definition = actors[pair.Key].definition;
                if (definition.nodes == null || definition.nodes.Length != pair.Value)
                    throw new Exception(pair.Key + ": dialogue node count changed");
                foreach (var node in definition.nodes)
                {
                    if (node == null || !node.voice || string.IsNullOrWhiteSpace(node.text))
                        throw new Exception(pair.Key + ": missing text or voice clip");
                    var path = AssetDatabase.GetAssetPath(node.voice);
                    var expectedPath = "Assets/AthenHill/Audio/ElevenLabs/NpcVoices/" + pair.Key + "-" + node.id + ".wav";
                    if (path != expectedPath || node.voice.length < 1)
                        throw new Exception(pair.Key + "/" + node.id + ": invalid imported voice " + path);
                    lines.Add(new { npc = pair.Key, node = node.id, clip = node.voice.name,
                        seconds = node.voice.length, path });
                }
            }
            var root = Path.GetFullPath(Path.Combine(Application.dataPath, "../.."));
            var evidence = Path.Combine(root, "evidence/npc-voices/20261002");
            Directory.CreateDirectory(evidence);
            File.WriteAllText(Path.Combine(evidence, "editor-audit.json"),
                JsonConvert.SerializeObject(new { success = true, actorCount = actors.Count,
                    lineCount = lines.Count, lines }, Formatting.Indented));
            Debug.Log("NPC voice audit: " + actors.Count + " actors, " + lines.Count + " imported clips");
            LinuxBuild.Development();
        }
    }
}
