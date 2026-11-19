using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UIElements;

namespace AthenHill.Editor
{
    /// <summary>
    /// 19 November 2026, showcase camera (art/showcase_20261119/showcase_camera/README.md): conversation camera and photo
    /// mode. Runtime code is in Scripts/Camera; this pass only puts the two components on the main camera and wires them.
    /// Steps (all re-runnable, -nographics is fine):
    ///  install    adds ConversationCamera and PhotoMode to the GameObject that carries the scene's single FollowCamera
    ///             (only when missing), wires session/follow/clock/HUD and the UI/PhotoMode.uxml/.uss assets, and sets
    ///             FollowCamera.conversation/photo. Touches nothing else. Copies the scene to
    ///             evidence/showcase-camera/20261119/rollback/ before the first install.
    ///  verify     -> evidence/showcase-camera/20261119/verify.json: one FollowCamera, both components present, enabled and
    ///             wired, the panel assets load, Controls.inputactions has Gameplay/PhotoMode on P (and nothing else on P)
    ///             and the Photo map with every action the code reads. Never saves.
    ///  uninstall  removes the two components and clears FollowCamera's references (the code then does nothing).
    /// Batch: unity.sh LOG AthenHill.Editor.ShowcaseCameraInstall20261119.RunBatch --steps install,verify -nographics
    /// </summary>
    public static class ShowcaseCameraInstall20261119
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string PanelPath = "Assets/AthenHill/UI/PhotoMode.uxml";
        const string StylePath = "Assets/AthenHill/UI/PhotoMode.uss";
        const string InputPath = "Assets/AthenHill/Data/Controls.inputactions";
        const string Evidence = "../evidence/showcase-camera/20261119/";
        static readonly string[] PhotoActions = { "Exit", "Move", "Rise", "Fall", "Fast", "Slow", "Look", "Zoom", "Capture", "PanelUp", "PanelDown", "PanelLeft", "PanelRight", "PanelSubmit", "TogglePanel", "ResetView", "FreeCursor" };

        [MenuItem("Athen Hill/Showcase camera/Install")] static void InstallMenu() => Debug.Log("ShowcaseCamera install: " + Install());
        [MenuItem("Athen Hill/Showcase camera/Verify")] static void VerifyMenu() => Debug.Log("ShowcaseCamera verify: " + Verify());
        [MenuItem("Athen Hill/Showcase camera/Uninstall")] static void UninstallMenu() => Debug.Log("ShowcaseCamera uninstall: " + Uninstall());

        static FollowCamera TheFollowCamera()
        {
            var all = UnityEngine.Object.FindObjectsByType<FollowCamera>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            if (all.Length != 1) throw new Exception("expected exactly one FollowCamera, found " + all.Length);
            return all[0];
        }

        static T AddOnce<T>(GameObject go, List<string> log) where T : Component
        {
            var c = go.GetComponent<T>();
            if (c) return c;
            log.Add("added " + typeof(T).Name);
            return go.AddComponent<T>();
        }

        static void Dirty(UnityEngine.Object o)
        {
            EditorUtility.SetDirty(o);
            if (PrefabUtility.IsPartOfPrefabInstance(o)) PrefabUtility.RecordPrefabInstancePropertyModifications(o);
        }

        public static string Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            Directory.CreateDirectory(Evidence + "rollback");
            if (!File.Exists(Evidence + "rollback/scene-before-first-install.unity")) File.Copy(ScenePath, Evidence + "rollback/scene-before-first-install.unity");
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var log = new List<string>();
            var follow = TheFollowCamera();
            var go = follow.gameObject;
            if (!go.GetComponent<Camera>()) throw new Exception("FollowCamera's object has no Camera: " + go.name);
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include) ?? throw new Exception("no GameSession");
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var hud = UnityEngine.Object.FindAnyObjectByType<CityHud>(FindObjectsInactive.Include);
            var panel = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(PanelPath) ?? throw new Exception("missing " + PanelPath);
            var style = AssetDatabase.LoadAssetAtPath<StyleSheet>(StylePath) ?? throw new Exception("missing " + StylePath);

            var conversation = AddOnce<ConversationCamera>(go, log);
            conversation.session = session; conversation.follow = follow;
            Dirty(conversation);

            var photo = AddOnce<PhotoMode>(go, log);
            photo.session = session; photo.follow = follow; photo.clock = clock; photo.hud = hud;
            photo.panelTemplate = panel; photo.panelStyle = style;
            Dirty(photo);

            follow.conversation = conversation; follow.photo = photo;
            Dirty(follow);

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            log.Add($"wired on '{go.name}' (session {session.name}, clock {(clock ? clock.name : "none")}, hud {(hud ? hud.name : "none")})");
            return string.Join("; ", log);
        }

        public static string Uninstall()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var follow = TheFollowCamera();
            var log = new List<string>();
            follow.conversation = null; follow.photo = null; Dirty(follow);
            foreach (var c in follow.GetComponents<ConversationCamera>()) { UnityEngine.Object.DestroyImmediate(c, true); log.Add("removed ConversationCamera"); }
            foreach (var c in follow.GetComponents<PhotoMode>()) { UnityEngine.Object.DestroyImmediate(c, true); log.Add("removed PhotoMode"); }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return log.Count > 0 ? string.Join("; ", log) : "nothing installed";
        }

        public static string Verify()
        {
            var problems = new List<string>();
            var r = new JObject();
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            FollowCamera follow = null;
            try { follow = TheFollowCamera(); } catch (Exception e) { problems.Add(e.Message); }
            if (follow)
            {
                var conversation = follow.GetComponent<ConversationCamera>();
                var photo = follow.GetComponent<PhotoMode>();
                r["camera"] = follow.name;
                r["conversation"] = conversation ? new JObject { ["enabled"] = conversation.enabled, ["framingEnabled"] = conversation.framingEnabled, ["session"] = (bool)conversation.session, ["follow"] = conversation.follow == follow, ["depthOfField"] = conversation.depthOfField, ["fieldOfView"] = conversation.shot.fieldOfView } : null;
                r["photo"] = photo ? new JObject { ["enabled"] = photo.enabled, ["session"] = (bool)photo.session, ["follow"] = photo.follow == follow, ["clock"] = (bool)photo.clock, ["hud"] = (bool)photo.hud, ["panelTemplate"] = (bool)photo.panelTemplate, ["panelStyle"] = (bool)photo.panelStyle, ["supersample"] = photo.supersample, ["maxDistance"] = photo.maxDistance } : null;
                r["followReferences"] = new JObject { ["conversation"] = follow.conversation == conversation && conversation, ["photo"] = follow.photo == photo && photo };
                if (!conversation) problems.Add("ConversationCamera missing");
                else
                {
                    if (!conversation.enabled) problems.Add("ConversationCamera disabled");
                    if (!conversation.session || conversation.follow != follow) problems.Add("ConversationCamera not wired");
                }
                if (!photo) problems.Add("PhotoMode missing");
                else
                {
                    if (!photo.enabled) problems.Add("PhotoMode disabled");
                    if (!photo.session || photo.follow != follow || !photo.hud) problems.Add("PhotoMode not wired");
                    if (!photo.panelTemplate || !photo.panelStyle) problems.Add("PhotoMode panel assets not assigned");
                }
                if (follow.conversation != conversation || follow.photo != photo) problems.Add("FollowCamera references not set");
            }
            if (!AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(PanelPath)) problems.Add("panel UXML does not load");
            if (!AssetDatabase.LoadAssetAtPath<StyleSheet>(StylePath)) problems.Add("panel USS does not load");

            // Input: the photo key is P and only photo mode uses it; every action the code reads exists.
            var input = JObject.Parse(File.ReadAllText(InputPath));
            var maps = input["maps"].Children<JObject>().ToList();
            var gameplay = maps.FirstOrDefault(m => (string)m["name"] == "Gameplay");
            var photoMap = maps.FirstOrDefault(m => (string)m["name"] == "Photo");
            var onP = gameplay?["bindings"].Children<JObject>().Where(b => (string)b["path"] == "<Keyboard>/p").Select(b => (string)b["action"]).ToList() ?? new List<string>();
            r["gameplayOnP"] = new JArray(onP);
            if (onP.Count != 1 || onP[0] != "PhotoMode") problems.Add("Gameplay P binding is not exactly PhotoMode: " + string.Join(",", onP));
            if (photoMap == null) problems.Add("Photo action map missing");
            else
            {
                var names = photoMap["actions"].Children<JObject>().Select(a => (string)a["name"]).ToList();
                var missing = PhotoActions.Where(a => !names.Contains(a)).ToList();
                r["photoActions"] = new JArray(names);
                if (missing.Count > 0) problems.Add("Photo map lacks " + string.Join(",", missing));
            }
            var ids = maps.SelectMany(m => m["actions"].Children<JObject>()).Select(a => (string)a["id"]).ToList();
            if (ids.Count != ids.Distinct().Count()) problems.Add("duplicate action ids in Controls.inputactions");

            r["problems"] = new JArray(problems);
            r["pass"] = problems.Count == 0;
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", r.ToString(Formatting.Indented));
            if (problems.Count > 0) throw new Exception("verify failed: " + string.Join("; ", problems));
            return "PASS";
        }

        /// Native QA (19 Nov 2026): writes ConversationFraming.Shot.Default (the re-tuned shoulder shot) onto the scene's
        /// ConversationCamera. Idempotent; overwrites any Inspector tuning of the shot.
        public static string ApplyShot()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var conversation = TheFollowCamera().GetComponent<ConversationCamera>() ?? throw new Exception("ConversationCamera not installed");
            var before = conversation.shot;
            conversation.shot = ConversationFraming.Shot.Default;
            Dirty(conversation);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return $"shot back {before.back}->{conversation.shot.back}, shoulder {before.maxShoulder}->{conversation.shot.maxShoulder}, player x {before.playerViewportX}->{conversation.shot.playerViewportX}";
        }

        /// -executeMethod AthenHill.Editor.ShowcaseCameraInstall20261119.RunBatch --steps install,verify (or uninstall)
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
                        "shot" => ApplyShot(),
                        "verify" => Verify(),
                        "uninstall" => Uninstall(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("ShowcaseCameraInstall20261119 " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
