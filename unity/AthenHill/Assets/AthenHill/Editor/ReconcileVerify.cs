using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>Read-only reopen check for the crafting + developer-UI reconciliation (t_c7c1e1ca). Never saves the scene.</summary>
    public static class ReconcileVerify
    {
        public static void Run()
        {
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            var session = UnityEngine.Object.FindAnyObjectByType<CraftingSession>();
            var marker = UnityEngine.Object.FindAnyObjectByType<CraftingStationMarker>();
            string[] roots = { "Player", "MainCamera", "CitySession", "Landmarks", "AuthoredWorld", "Post-war salvage", "Colonists", "Outer Berms", "City Render Chunks" };
            var report = new
            {
                utc = DateTime.UtcNow, scene = scene.path,
                chunksPresent = chunks != null, chunkSourcesShown = chunks ? chunks.editingSources : (bool?)null,
                storedFingerprint = chunks ? chunks.sourceFingerprint : null,
                recomputedFingerprint = chunks ? StaticRenderChunksEditor.Fingerprint(chunks) : null,
                fingerprintMatches = chunks && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks),
                generatedChunkRenderers = chunks && chunks.generatedRoot ? chunks.generatedRoot.GetComponentsInChildren<MeshRenderer>(true).Length : -1,
                colliders = UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsInactive.Include).Length,
                craftingSessionPresent = session != null, craftingData = session && session.data ? AssetDatabase.GetAssetPath(session.data) : null,
                fabricatorPresent = session && session.fabricator, stationId = marker ? marker.stationId : null,
                fabricatorParent = session && session.fabricator && session.fabricator.parent ? session.fabricator.parent.name : null,
                checkpointFabricator = GameObject.Find("checkpoint_fabricator") != null,
                rootsPresent = roots.ToDictionary(n => n, n => GameObject.Find(n) != null),
                sceneSha256 = Sha(Path.GetFullPath(Path.Combine(Application.dataPath, "..", ImportBaseline.ScenePath)))
            };
            var text = JsonConvert.SerializeObject(report, Formatting.Indented);
            File.WriteAllText(Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "evidence", "reconcile", "20260929", "reopen-verify.json")), text);
            Debug.Log("ReconcileVerify " + text);
        }

        static string Sha(string path)
        {
            using (var sha = System.Security.Cryptography.SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
        }
    }
}
