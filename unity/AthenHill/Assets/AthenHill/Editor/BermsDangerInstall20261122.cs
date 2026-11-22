using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// 22 Nov 2026 (Gemini merge, fix round): installs the Outer Berms danger atmosphere on its own. Gemini's
    /// BermsDensityPass20261121 created it under the density root, and the density props were not accepted, so their
    /// rollback took the controller with them. This puts back only the controller (tier-3 zone radio warnings, ash
    /// wisps that follow the player, distant crackles): no props, no hazard arcs (hazardRoot stays empty, so a
    /// crackle is sound only), no lights, no colliders.
    /// Batch: -executeMethod AthenHill.Editor.BermsDangerInstall20261122.RunBatch -nographics --steps install,verify|rollback
    public static class BermsDangerInstall20261122
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string RootName = "Berms danger atmosphere";
        const string Evidence = "../evidence/gemini_merge/20261121/berms_danger/";

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 && i + 1 < args.Length ? args[i + 1].Split(',') : new[] { "verify" };
            try
            {
                foreach (var st in steps)
                {
                    string r = st == "install" ? Install() : st == "verify" ? Verify() : st == "rollback" ? Rollback() : throw new Exception("unknown step " + st);
                    Debug.Log("BermsDangerInstall20261122 " + st + ": " + r);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        static Transform Berms(UnityEngine.SceneManagement.Scene scene)
        {
            var b = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Outer Berms");
            if (!b) throw new Exception("Outer Berms root not found");
            return b.transform;
        }

        /// Idempotent: deletes its own root and builds it again.
        public static string Install()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var berms = Berms(scene);
            var old = berms.Find(RootName); if (old) Object.DestroyImmediate(old.gameObject);
            var root = new GameObject(RootName).transform; root.SetParent(berms, false);
            var session = Object.FindAnyObjectByType<GameSession>();
            var player = Object.FindAnyObjectByType<PlayerCombat>();
            var cityAudio = Object.FindAnyObjectByType<CityAudio>();
            var sfx = cityAudio && cityAudio.confirmation ? cityAudio.confirmation.outputAudioMixerGroup : null;
            var smoke = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/FX/Materials/FX_Smoke.mat");
            if (!smoke) throw new Exception("FX_Smoke.mat missing");
            var clips = new[] { "arc-crackle-1", "arc-crackle-2" }
                .Select(n => AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/AthenHill/Audio/ElevenLabs/Combat/" + n + ".wav")).Where(c => c).ToArray();
            BermsDensityPass20261121.WireDangerAtmosphere(root, null, session, player, smoke, clips, sfx);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return $"installed under Outer Berms/{RootName} (crackle clips {clips.Length})";
        }

        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var root = Berms(scene).Find(RootName);
            var problems = new JArray();
            if (!root) throw new Exception("not installed: Outer Berms/" + RootName + " missing");
            var all = Object.FindObjectsByType<BermsDangerAtmosphere>(FindObjectsInactive.Include);
            if (all.Length != 1) problems.Add($"{all.Length} BermsDangerAtmosphere in the scene (want 1)");
            var atmo = root.GetComponentInChildren<BermsDangerAtmosphere>(true);
            if (!atmo) problems.Add("controller missing under the root");
            else
            {
                if (!atmo.session || !atmo.player || !atmo.ashWisps || !atmo.crackleSource) problems.Add("controller reference missing (session/player/ashWisps/crackleSource)");
                if (atmo.dangerZones == null || atmo.dangerZones.Length != 4) problems.Add("want 4 tier-3 zones");
                if (atmo.hazardRoot) problems.Add("hazardRoot should be empty (no density hazards)");
            }
            if (root.GetComponentsInChildren<Light>(true).Length > 0) problems.Add("lights under the root");
            if (root.GetComponentsInChildren<Collider>(true).Length > 0) problems.Add("colliders under the root");
            if (root.GetComponentsInChildren<MeshRenderer>(true).Length > 0) problems.Add("mesh renderers under the root");
            bool densityPresent = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).Any(t => t.name == "Berms density");
            if (densityPresent) problems.Add("the unaccepted Berms density root is in the scene");
            var report = new JObject { ["utc"] = DateTime.UtcNow.ToString("o"), ["pass"] = problems.Count == 0, ["problems"] = problems,
                ["zones"] = atmo && atmo.dangerZones != null ? atmo.dangerZones.Length : 0, ["crackleClips"] = atmo ? atmo.crackleClips.Length : 0, ["densityPresent"] = densityPresent };
            Directory.CreateDirectory(Evidence); File.WriteAllText(Evidence + "verify.json", report.ToString());
            if (problems.Count > 0) throw new Exception("verify FAIL: " + string.Join("; ", problems));
            return "verify PASS";
        }

        public static string Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var root = Berms(scene).Find(RootName);
            if (!root) return "already absent";
            Object.DestroyImmediate(root.gameObject);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "removed Outer Berms/" + RootName;
        }
    }
}
