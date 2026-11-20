using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// 20 November 2026: the hero base, a new player body (Carl: "recreate our main character as burley sci-fi action
    /// hero ... a base character we can add armour etc on later"). Rodin 2.5 mesh from a new concept on its own Meshy
    /// rig, shaped to the contract the player installers already expect (art/hero_base_20261120/README.md):
    /// armature `Armature`, mesh `char1`, 54 joints with the finger bones named and rolled as on the previous rig, one
    /// material `PlayerSkin`, legacy clips idle/walk/run in the file. The 12 source clips were fetched on this rig, so
    /// the retarget in CharacterFeelPass is an identity transfer and no rest-pose matching is involved.
    ///
    /// This pass only moves files and audits. The scene, prefab and clips are rebuilt by the existing installers, run
    /// one Unity job each by art/hero_base_20261120/unity/install.sh:
    ///   RifleHandsPass20261120 rollback -> HeroBasePass20261120 files -> MainCharacterInstall.InstallBatch ->
    ///   CharacterArmsPass20261120 install -> RifleHandsPass20261120 install,rebaseline -> HeroBasePass20261120 cameras,verify
    ///
    /// Batch: -executeMethod AthenHill.Editor.HeroBasePass20261120.RunBatch --steps files|cameras|verify|restore
    ///   files     [--armour placeholder] copies the pass outputs over colonist.glb, the TS_*.glb pieces and Source/Player/Player_*.glb (same
    ///             paths and GUIDs). The files they replace are kept once in art/hero_base_20261120/rollback/assets.
    ///   cameras   review cameras cam_hero_* round the saved spawn (root "Hero base review cameras")
    ///   verify    -nographics audit of the saved scene: unity/evidence/hero_base/20261120/verify.json
    ///   restore   copies the kept files back (then re-run the installers: install.sh rollback does both)
    /// While installed (rollback/installed.json exists) the earlier passes that copy the previous body's files
    /// (ColonistBackPass20261120 install/rollback, PlayerFace20261003 rollback) refuse to run: see Guard.
    /// </summary>
    public static class HeroBasePass20261120
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string CamRoot = "Hero base review cameras";
        const string BodyAsset = "Assets/AthenHill/Art/Imported/Meshy/colonist.glb";
        const string ArmourDir = "Assets/AthenHill/Art/Armour/TutorialSet";
        const string SourceDir = "Assets/AthenHill/Art/CharacterMotion/Source/Player";
        static string ArtDir => Path.GetFullPath("../../art/hero_base_20261120");
        static string Evidence => Path.GetFullPath("../evidence/hero_base/20261120");
        static string Marker => Path.Combine(ArtDir, "rollback", "installed.json");
        static readonly string[] Armour = { "TS_Helmet", "TS_FieldVest", "TS_WardenCarrier", "TS_ArmGuards", "TS_Gloves", "TS_LegArmour", "TS_Boots" };
        static readonly string[] Clips = { "aim_95", "aimturn_585", "back_233", "draw_222", "fwd_234", "idle_243", "idle_252", "left_528", "lower_334", "rifleturn_573", "turnl_576", "turnr_586" };

        /// True while the hero base files are in the project.
        public static bool Installed => File.Exists(Marker);

        /// Called first by passes that would copy the previous (MPFB) body's files over the hero base.
        public static void Guard(string what)
        {
            if (Installed) throw new InvalidOperationException(what + " would put the previous player body's files back over the hero base (art/hero_base_20261120). Run art/hero_base_20261120/unity/install.sh rollback first if that is intended.");
        }

        /// Where the armour pieces come from: armour/out (the re-fit), or with `--armour placeholder` the stand-ins in
        /// armour_placeholder/out (the old meshes bound to the new skeleton, unfitted; only for exercising the installers).
        static string ArmourSrc => Path.Combine(ArtDir, Environment.GetCommandLineArgs().Contains("placeholder") ? "armour_placeholder" : "armour", "out");

        static IEnumerable<(string src, string asset)> Files()
        {
            yield return (Path.Combine(ArtDir, "build", "out", "colonist.glb"), BodyAsset);
            yield return (Path.Combine(ArtDir, "build", "out", "TS_FPArms.glb"), ArmourDir + "/TS_FPArms.glb");
            foreach (var a in Armour) yield return (Path.Combine(ArmourSrc, a + ".glb"), ArmourDir + "/" + a + ".glb");
            foreach (var c in Clips) yield return (Path.Combine(ArtDir, "build", "out", "source", "Player_" + c + ".glb"), SourceDir + "/Player_" + c + ".glb");
        }

        static string Sha(string path) { using var s = File.OpenRead(path); using var h = SHA256.Create(); return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant(); }
        static string Full(string asset) => Path.GetFullPath(asset);
        static string Keep(string asset) => Path.Combine(ArtDir, "rollback", "assets", asset.Substring("Assets/AthenHill/".Length).Replace('/', Path.DirectorySeparatorChar));
        static void OpenScene() { if (EditorSceneManager.GetActiveScene().path != ScenePath) EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); }
        static void SaveScene() { var s = EditorSceneManager.GetActiveScene(); EditorSceneManager.MarkSceneDirty(s); EditorSceneManager.SaveScene(s); }
        static PlayerMotor Motor() { var m = Object.FindAnyObjectByType<PlayerMotor>(FindObjectsInactive.Include); if (!m) throw new InvalidOperationException("No PlayerMotor"); return m; }
        static PlayerCombat Combat() { var c = Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include); if (!c) throw new InvalidOperationException("No PlayerCombat"); return c; }
        static string F(Vector3 v) => string.Format(CultureInfo.InvariantCulture, "{0:0.###},{1:0.###},{2:0.###}", v.x, v.y, v.z);

        // ------------------------------------------------------------------ files
        static string CopyFiles()
        {
            var missing = Files().Where(f => !File.Exists(f.src)).Select(f => f.src).ToArray();
            if (missing.Length > 0) throw new FileNotFoundException("missing pass outputs: " + string.Join(", ", missing.Select(Path.GetFileName)));
            var kept = new List<string>(); var copied = new List<string>();
            var shaFile = Path.Combine(ArtDir, "rollback", "sha256.json");
            Directory.CreateDirectory(Path.GetDirectoryName(shaFile));
            var previous = File.Exists(shaFile) ? JsonConvert.DeserializeObject<Dictionary<string, string>>(File.ReadAllText(shaFile)) : new Dictionary<string, string>();
            foreach (var (src, asset) in Files())
            {
                var keep = Keep(asset);
                if (!File.Exists(keep) && File.Exists(Full(asset))) { Directory.CreateDirectory(Path.GetDirectoryName(keep)); File.Copy(Full(asset), keep); previous[asset] = Sha(keep); kept.Add(Path.GetFileName(asset)); }   // first run only: the file being replaced
                if (!File.Exists(Full(asset)) || Sha(src) != Sha(Full(asset))) { File.Copy(src, Full(asset), true); copied.Add(Path.GetFileName(asset)); }
            }
            File.WriteAllText(shaFile, JsonConvert.SerializeObject(previous, Formatting.Indented));
            File.WriteAllText(Marker, JsonConvert.SerializeObject(new { installed = DateTime.Now.ToString("s"), files = Files().ToDictionary(f => f.asset, f => Sha(f.src)) }, Formatting.Indented));
            foreach (var (_, asset) in Files()) AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceUpdate);
            AssetDatabase.SaveAssets();
            return "copied " + copied.Count + " (" + string.Join(", ", copied) + "); kept previous " + kept.Count;
        }

        static string Restore()
        {
            var restored = new List<string>();
            foreach (var (_, asset) in Files())
            {
                var keep = Keep(asset); if (!File.Exists(keep)) continue;
                if (Sha(keep) != Sha(Full(asset))) { File.Copy(keep, Full(asset), true); restored.Add(Path.GetFileName(asset)); }
                AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceUpdate);
            }
            if (File.Exists(Marker)) File.Delete(Marker);
            OpenScene(); var s = EditorSceneManager.GetActiveScene(); int removed = 0;
            foreach (var g in s.GetRootGameObjects().Where(g => g.name == CamRoot).ToArray()) { Object.DestroyImmediate(g); removed++; }
            SaveScene(); AssetDatabase.SaveAssets();
            return "restored " + restored.Count + " (" + string.Join(", ", restored) + "); camera roots removed " + removed + ". Re-run the installers.";
        }

        // ------------------------------------------------------------------ cameras
        static string Cameras()
        {
            OpenScene();
            var scene = EditorSceneManager.GetActiveScene();
            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == CamRoot).ToArray()) Object.DestroyImmediate(old);
            var motor = Motor(); var root = new GameObject(CamRoot);
            var feet = motor.transform.position;
            var fwd = Vector3.ProjectOnPlane(motor.visual ? motor.visual.forward : motor.transform.forward, Vector3.up).normalized;
            if (fwd.sqrMagnitude < .5f) fwd = Vector3.forward;
            var right = Vector3.Cross(Vector3.up, fwd);
            var shots = new (string name, Vector3 pos, Vector3 look, float fov)[]
            {
                ("cam_hero_front", feet + fwd * 3.0f + Vector3.up * 1.3f, feet + Vector3.up * .95f, 40f),                          // whole body from the front
                ("cam_hero_quarter", feet + fwd * 2.4f + right * 1.6f + Vector3.up * 1.4f, feet + Vector3.up * .95f, 40f),         // front three-quarter
                ("cam_hero_side", feet + right * 3.0f + Vector3.up * 1.3f, feet + Vector3.up * .95f, 40f),                         // profile
                ("cam_hero_back", feet - fwd * 3.0f + Vector3.up * 1.5f, feet + Vector3.up * .95f, 40f),                           // whole body from behind
                ("cam_hero_follow", feet - fwd * 3.2f + right * .35f + Vector3.up * 2.05f, feet + fwd * 2f + Vector3.up * 1.5f, 50f), // the follow camera's view
                ("cam_hero_face", feet + fwd * .75f + right * .12f + Vector3.up * 1.62f, feet + Vector3.up * 1.62f, 32f),          // face close-up
                ("cam_hero_bust", feet + fwd * 1.25f - right * .55f + Vector3.up * 1.5f, feet + Vector3.up * 1.4f, 36f),           // head and shoulders, other side
                ("cam_hero_hands", feet + fwd * .8f + right * .75f + Vector3.up * .95f, feet + right * .3f + Vector3.up * .85f, 36f), // right hand and forearm
            };
            var made = new List<string>();
            foreach (var (name, pos, look, fov) in shots)
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f;
                go.transform.position = pos; go.transform.LookAt(look); made.Add(name + " @ " + F(pos));
            }
            SaveScene();
            return string.Join("; ", made);
        }

        // ------------------------------------------------------------------ verify (-nographics)
        static string Verify()
        {
            OpenScene();
            var fails = new List<string>(); var info = new Dictionary<string, object>();
            void Must(bool ok, string what) { if (!ok) fails.Add(what); }
            var files = new Dictionary<string, object>();
            foreach (var (src, asset) in Files())
            {
                bool inst = File.Exists(src) && File.Exists(Full(asset)) && Sha(src) == Sha(Full(asset));
                files[asset] = new { installed = inst, guid = AssetDatabase.AssetPathToGUID(asset) }; Must(inst, "not installed: " + asset);
            }
            info["files"] = files; Must(Installed, "marker rollback/installed.json missing");
            var motor = Motor(); var combat = Combat();
            var skins = motor.visual.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.sharedMesh).ToArray();
            var body = skins.Where(r => !r.name.StartsWith("Armour ")).OrderByDescending(r => r.sharedMesh.vertexCount).First();
            int tris = body.sharedMesh.triangles.Length / 3;
            var boneNames = body.bones.Where(b => b).Select(b => b.name).ToArray();
            info["body"] = new
            {
                mesh = body.sharedMesh.name, asset = AssetDatabase.GetAssetPath(body.sharedMesh), triangles = tris, vertices = body.sharedMesh.vertexCount, bones = body.bones.Length,
                materials = body.sharedMaterials.Select(m => m ? m.name : "MISSING").ToArray(),
                textures = body.sharedMaterials.Where(m => m).SelectMany(m => m.GetTexturePropertyNames().Select(p => m.GetTexture(p)).Where(t => t).Select(t => t.name + " " + t.width + "x" + t.height)).Distinct().ToArray(),
                shadows = body.shadowCastingMode.ToString(), layer = body.gameObject.layer,
            };
            Must(AssetDatabase.GetAssetPath(body.sharedMesh) == BodyAsset, "body mesh is not from colonist.glb");
            Must(body.bones.Length == 54 && body.bones.All(b => b), "body has " + body.bones.Length + " bones (54 expected)");
            Must(tris >= 40000 && tris <= 90000, "body triangles " + tris);
            Must(body.sharedMaterials.Length == 1 && body.sharedMaterials[0] && body.sharedMaterials[0].name.StartsWith("PlayerSkin"), "body material is not the single PlayerSkin");
            foreach (var n in new[] { "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "LeftHand", "RightHand", "LeftFoot", "RightFoot", "index_01_r", "thumb_03_l", "pinky_03_r" })
                Must(boneNames.Contains(n), "bone missing: " + n);
            // height in the sampled idle: the top of the head bone chain against the soles (bone positions, not a bake)
            var actor = motor.actor;
            Must(actor && actor.idle && actor.walk && actor.run, "actor clips missing");
            if (actor)
            {
                info["clips"] = new { idle = actor.idle ? actor.idle.name : null, walk = actor.walk ? actor.walk.name + " @ " + AssetDatabase.GetAssetPath(actor.walk) : null, run = actor.run ? actor.run.name + " @ " + AssetDatabase.GetAssetPath(actor.run) : null };
                Must(actor.walk && AssetDatabase.GetAssetPath(actor.walk) == BodyAsset, "walk is not the clip inside colonist.glb");
                Must(actor.run && AssetDatabase.GetAssetPath(actor.run) == BodyAsset, "run is not the clip inside colonist.glb");
                if (actor.idle && actor.animationSource)
                {
                    actor.idle.SampleAnimation(actor.animationSource.gameObject, 0);
                    var all = motor.visual.GetComponentsInChildren<Transform>(true);
                    var headEnd = all.FirstOrDefault(t => t.name == "head_end"); var lf = all.FirstOrDefault(t => t.name == "LeftToeBase");
                    if (headEnd && lf) { float h = headEnd.position.y - motor.transform.position.y; info["headEndHeight"] = h; Must(h > 1.6f && h < 1.9f, "head_end height " + h.ToString("0.000", CultureInfo.InvariantCulture)); }
                }
            }
            // armour: every installed piece shares the body's bones and bind poses
            var bodyBind = new Dictionary<string, Matrix4x4>();
            for (int i = 0; i < body.bones.Length; i++) if (body.bones[i]) bodyBind[body.bones[i].name] = body.sharedMesh.bindposes[i];
            var pieces = new List<object>();
            foreach (var r in skins.Where(r => r.name.StartsWith("Armour ")))
            {
                float worst = 0; var miss = new List<string>();
                for (int i = 0; i < r.bones.Length; i++)
                {
                    var b = r.bones[i]; if (!b) { miss.Add("null " + i); continue; }
                    if (!bodyBind.TryGetValue(b.name, out var bb)) { miss.Add(b.name); continue; }
                    var a = r.sharedMesh.bindposes[i]; for (int k = 0; k < 16; k++) worst = Mathf.Max(worst, Mathf.Abs(a[k] - bb[k]));
                }
                pieces.Add(new { r.name, asset = AssetDatabase.GetAssetPath(r.sharedMesh), triangles = r.sharedMesh.triangles.Length / 3, bindDiff = worst, missing = miss });
                Must(miss.Count == 0, r.name + " bones not on the body: " + string.Join(",", miss)); Must(worst < 1e-3f, r.name + " bind pose differs by " + worst);
            }
            info["armour"] = pieces; Must(pieces.Count >= 7, "armour pieces under the visual: " + pieces.Count);
            // hands: 15 finger joints a side on the body and on both view models, solved grips sized to match
            var grips = Object.FindObjectsByType<PlayerHandGrip>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            var gripInfo = new List<object>();
            foreach (var g in grips)
            {
                bool ok = g.rightFingers.Length == 15 && g.leftFingers.Length == 15 && g.rightFingers.All(t => t) && g.leftFingers.All(t => t);
                gripInfo.Add(new { path = PathOf(g.transform), right = g.rightFingers.Length, left = g.leftFingers.Length, pistolRight = g.pistolRight.Length, pistolLeft = g.pistolLeft.Length, rifleRight = g.rifleRight.Length, rifleLeft = g.rifleLeft.Length });
                Must(ok, "finger arrays incomplete on " + PathOf(g.transform));
            }
            info["handGrips"] = gripInfo; Must(grips.Length >= 3, "PlayerHandGrip components: " + grips.Length + " (body + two view models expected)");
            foreach (var (label, vm) in new[] { ("pistol", combat.viewModel), ("rifle", combat.rifleViewModel) })
            {
                Must(vm, label + " view model missing"); if (!vm) continue;
                var arms = vm.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.sharedMesh && AssetDatabase.GetAssetPath(r.sharedMesh).EndsWith("TS_FPArms.glb")).ToArray();
                Must(arms.Length > 0, label + " view model has no arms from TS_FPArms.glb");
                Must(vm.GetComponentInChildren<ViewModelArmsRig>(true), label + " view model has no ViewModelArmsRig");
            }
            Must(motor.visual.GetComponentInChildren<ArmPoseCorrector>(true), "no ArmPoseCorrector on the player (run CharacterArmsPass20261120 install)");
            var camRoot = EditorSceneManager.GetActiveScene().GetRootGameObjects().FirstOrDefault(g => g.name == CamRoot);
            info["cameras"] = camRoot ? camRoot.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray() : new string[0];
            Must(camRoot, "review cameras missing");
            info["fails"] = fails; info["result"] = fails.Count == 0 ? "PASS" : "FAIL";
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(info, Formatting.Indented); File.WriteAllText(Path.Combine(Evidence, "verify.json"), json);
            if (fails.Count > 0) throw new InvalidOperationException("verify FAILED: " + string.Join("; ", fails));
            return "PASS (" + tris + " triangles, " + pieces.Count + " armour pieces, " + grips.Length + " hand grips)";
        }

        static string PathOf(Transform t) { var parts = new List<string>(); for (int i = 0; t && i < 4; i++, t = t.parent) parts.Add(t.name); parts.Reverse(); return string.Join("/", parts); }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            int code = 0; var log = new List<string>(); var steps = Arg("--steps", "verify").Split(',');
            try
            {
                foreach (var st in steps)
                {
                    string result = st switch
                    {
                        "files" => CopyFiles(),
                        "cameras" => Cameras(),
                        "verify" => Verify(),
                        "restore" => Restore(),
                        _ => throw new ArgumentException("unknown step " + st),
                    };
                    log.Add("[" + st + "] " + result); Debug.Log("HeroBasePass20261120 " + st + ": " + result);
                }
            }
            catch (Exception e) { Debug.LogException(e); log.Add("FAILED " + e); code = 1; }
            try { Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, string.Join("_", steps) + "-result.txt"), string.Join("\n", log) + "\n"); } catch (Exception e) { Debug.LogException(e); }
            EditorApplication.Exit(code);
        }
    }
}
