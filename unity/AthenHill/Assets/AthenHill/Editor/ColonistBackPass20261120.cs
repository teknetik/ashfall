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
    /// 20 November 2026 (showcase phase 2): the player colonist seen from behind. The conversation camera puts his back,
    /// shoulder and helmet across a third of the frame, and three asset faults made it read as speckle and rags:
    ///   - the flight suit's base colour (a Meshy retexture) is a patchwork of unrelated fragments (knit/moire weaves,
    ///     white cross-stitches, pink skin-coloured pieces): replaced by a synthesised olive twill in the same UVs
    ///     (art/colonist_back_20261120/make_suit.py); the fold normal map is kept with seams/patch hems/stitches added;
    ///   - the chest rig, plate carrier and helmet were fitted with fitlib.strip_inner (deleted a third of the
    ///     double-walled shells: holes, one-sided rims) and a Blender COLLAPSE decimation on meshes still split at
    ///     every UV seam (each seam tore into flaky jagged borders); the side panels also took upper-arm weights and
    ///     were pushed out against the arms (saw-tooth flaps under the armpits): re-fitted from the full Meshy sources
    ///     (art/colonist_back_20261120/blender/fit_piece.py, decimate.py).
    /// Only the four GLB files change (same paths, GUIDs, rig, joint order, inverse bind matrices, mesh and material
    /// names), so the player prefab, scene, PlayerArmourVisuals, ViewModelArmourMirror and the first-person view models
    /// inherit them with no reinstall. MainCharacterInstall / TutorialSetInstall / RifleArmourInstall /
    /// PlayerFace20261003 install are NOT run.
    ///
    /// Batch: -executeMethod AthenHill.Editor.ColonistBackPass20261120.RunBatch --steps install,verify
    ///   install   copies art/colonist_back_20261120/out/*.glb over the assets (previous files kept once in
    ///             art/colonist_back_20261120/rollback/), reimports them, audits the integration, adds cam_cb_* cameras
    ///   verify    -nographics audit of the saved scene: verify.json in unity/evidence/showcase_phase2/20261120/colonist_back
    ///   capture   graphics mode: --shots kit|light|carrier|suit (at most six cameras each) --state before|after
    ///   rollback  copies rollback/*.glb back, reimports, removes the review cameras
    /// Record: art/colonist_back_20261120/README.md.
    /// </summary>
    public static class ColonistBackPass20261120
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string CamRoot = "Colonist back review cameras";
        static string ArtDir => Path.GetFullPath("../../art/colonist_back_20261120");
        static string Evidence => Path.GetFullPath("../evidence/showcase_phase2/20261120/colonist_back");

        static readonly (string file, string asset)[] Files =
        {
            ("colonist.glb", "Assets/AthenHill/Art/Imported/Meshy/colonist.glb"),
            ("TS_FieldVest.glb", "Assets/AthenHill/Art/Armour/TutorialSet/TS_FieldVest.glb"),
            ("TS_Helmet.glb", "Assets/AthenHill/Art/Armour/TutorialSet/TS_Helmet.glb"),
            ("TS_WardenCarrier.glb", "Assets/AthenHill/Art/Armour/TutorialSet/TS_WardenCarrier.glb"),
        };
        const string FPArmsAsset = "Assets/AthenHill/Art/Armour/TutorialSet/TS_FPArms.glb";

        // ------------------------------------------------------------------ helpers
        static string Sha(string path) { using var s = File.OpenRead(path); using var h = SHA256.Create(); return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant(); }
        static string Full(string asset) => Path.GetFullPath(asset);
        static PlayerMotor Motor() { var m = Object.FindAnyObjectByType<PlayerMotor>(FindObjectsInactive.Include); if (!m) throw new InvalidOperationException("No PlayerMotor"); return m; }
        static PlayerCombat Combat() { var c = Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include); if (!c) throw new InvalidOperationException("No PlayerCombat"); return c; }
        static PlayerArmourVisuals Visuals(PlayerMotor m) { var v = m.GetComponent<PlayerArmourVisuals>(); if (!v) v = Object.FindAnyObjectByType<PlayerArmourVisuals>(FindObjectsInactive.Include); return v; }   // no ?? on Unity objects (fake null)
        static SkinnedMeshRenderer Body(PlayerMotor m) => m.visual.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.sharedMesh).OrderByDescending(r => r.sharedMesh.vertexCount).First();
        static string F(Vector3 v) => string.Format(CultureInfo.InvariantCulture, "{0:0.###},{1:0.###},{2:0.###}", v.x, v.y, v.z);
        static void OpenScene() { if (EditorSceneManager.GetActiveScene().path != ScenePath) EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); }

        /// Estimated GPU size of a texture with its mip chain (block formats from GraphicsFormatUtility).
        static long TexBytes(Texture t)
        {
            if (t is not Texture2D t2) return 0;
            var fmt = t2.graphicsFormat; long total = 0; int w = t2.width, h = t2.height;
            for (int i = 0; i < t2.mipmapCount; i++) { total += (long)UnityEngine.Experimental.Rendering.GraphicsFormatUtility.ComputeMipmapSize(Math.Max(1, w >> i), Math.Max(1, h >> i), fmt); }
            return total;
        }

        static object Describe(SkinnedMeshRenderer r)
        {
            var tex = new List<object>(); long bytes = 0; var seen = new HashSet<Texture>();
            foreach (var m in r.sharedMaterials.Where(m => m))
                foreach (var p in m.GetTexturePropertyNames())
                {
                    var t = m.GetTexture(p); if (!t || !seen.Add(t)) continue;
                    long b = TexBytes(t); bytes += b;
                    tex.Add(new { material = m.name, property = p, t.name, t.width, t.height, format = (t as Texture2D)?.graphicsFormat.ToString(), mips = (t as Texture2D)?.mipmapCount, mb = Math.Round(b / 1048576.0, 2) });
                }
            return new
            {
                mesh = r.sharedMesh ? r.sharedMesh.name : null,
                triangles = r.sharedMesh ? r.sharedMesh.triangles.Length / 3 : 0,
                vertices = r.sharedMesh ? r.sharedMesh.vertexCount : 0,
                bones = r.bones.Length,
                materials = r.sharedMaterials.Select(m => m ? m.name + " (" + m.shader.name + ")" : "MISSING").ToArray(),
                textureMB = Math.Round(bytes / 1048576.0, 2),
                textures = tex,
            };
        }

        /// The installer's own bind check (TutorialSetInstall.Attach): each piece bone's bind pose against the body's.
        static float BindDiff(SkinnedMeshRenderer body, SkinnedMeshRenderer piece, List<string> missing)
        {
            var bodyBind = new Dictionary<string, Matrix4x4>();
            for (int i = 0; i < body.bones.Length; i++) if (body.bones[i]) bodyBind[body.bones[i].name] = body.sharedMesh.bindposes[i];
            float worst = 0;
            for (int i = 0; i < piece.bones.Length; i++)
            {
                var b = piece.bones[i]; if (!b) { missing.Add("null bone " + i); continue; }
                if (!bodyBind.TryGetValue(b.name, out var bb)) { missing.Add(b.name); continue; }
                var a = piece.sharedMesh.bindposes[i];
                for (int k = 0; k < 16; k++) worst = Mathf.Max(worst, Mathf.Abs(a[k] - bb[k]));
            }
            return worst;
        }

        // ------------------------------------------------------------------ install
        static string Install()
        {
            var rb = Path.Combine(ArtDir, "rollback"); Directory.CreateDirectory(rb);
            var record = new Dictionary<string, object>(); var copied = new List<string>();
            var shaFile = Path.Combine(rb, "sha256.json");
            var previous = File.Exists(shaFile) ? JsonConvert.DeserializeObject<Dictionary<string, string>>(File.ReadAllText(shaFile)) : new Dictionary<string, string>();
            foreach (var (file, asset) in Files)
            {
                var src = Path.Combine(ArtDir, "out", file); if (!File.Exists(src)) throw new FileNotFoundException("missing pass output (see README)", src);
                var keep = Path.Combine(rb, file);
                if (!File.Exists(keep)) { File.Copy(Full(asset), keep); previous[file] = Sha(keep); }   // first install only: the shipped file
                if (Sha(src) != Sha(Full(asset))) { File.Copy(src, Full(asset), true); copied.Add(file); }
            }
            File.WriteAllText(shaFile, JsonConvert.SerializeObject(previous, Formatting.Indented));
            foreach (var (_, asset) in Files) AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceUpdate);
            OpenScene();
            record["copied"] = copied;
            record["cameras"] = Cameras();
            var s = EditorSceneManager.GetActiveScene(); EditorSceneManager.MarkSceneDirty(s); EditorSceneManager.SaveScene(s);
            record["audit"] = JsonConvert.DeserializeObject(Verify());
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Path.Combine(Evidence, "install.json"), json);
            return "copied " + string.Join(", ", copied) + "; cameras and verify in install.json";
        }

        /// Review cameras round the player's saved spawn (the native lookbook leaves him there), at the conversation
        /// distance and the follow camera's, plus helmet and vest close-ups; all at about player height.
        static string Cameras()
        {
            var scene = EditorSceneManager.GetActiveScene();
            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == CamRoot).ToArray()) Object.DestroyImmediate(old);
            var motor = Motor(); var root = new GameObject(CamRoot);
            var feet = motor.transform.position;
            var fwd = Vector3.ProjectOnPlane(motor.visual ? motor.visual.forward : motor.transform.forward, Vector3.up).normalized;
            if (fwd.sqrMagnitude < .5f) fwd = Vector3.forward;
            var made = new List<string>();
            foreach (var (name, pos, look, fov) in Shots(feet, fwd))
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f;
                go.transform.position = pos; go.transform.LookAt(look); made.Add(name + " @ " + F(pos));
            }
            return string.Join("; ", made);
        }

        /// Camera specs relative to the colonist's feet and facing. cam_cb_conv is the game's own conversation shot
        /// (ConversationFraming.Solve with Shot.Default, an NPC head 1.9 m ahead, right shoulder, 16:9).
        /// Note (fix round): at ordinary talking distances the game's own solve cannot reach playerViewportX 0.27: the
        /// wanted head separation (0.50 rad) needs a shoulder offset past maxShoulder 0.75 m, which gives 0.31 rad, so
        /// the colonist's head lands at about 0.43 of the width (0.42 at 2.2 m). This camera reproduces that, as the
        /// native frames of phase 1 show; the 0.27 target is a ConversationFraming tuning question, not this camera.
        static (string name, Vector3 pos, Vector3 look, float fov)[] Shots(Vector3 feet, Vector3 fwd)
        {
            var right = Vector3.Cross(Vector3.up, fwd); var head = feet + Vector3.up * 1.58f;
            var npc = feet + fwd * 1.9f + Vector3.up * 1.62f;
            var shot = ConversationFraming.Shot.Default;
            var pose = ConversationFraming.Solve(head, npc, 1, shot, 16f / 9);
            var convLook = pose.position + pose.rotation * Vector3.forward * 3;
            return new[]
            {
                ("cam_cb_conv", pose.position, convLook, shot.fieldOfView),                                        // the conversation shot
                ("cam_cb_follow", feet - fwd * 3.2f + right * .35f + Vector3.up * 2.05f, feet + fwd * 2f + Vector3.up * 1.5f, 50f),   // follow camera
                ("cam_cb_back", feet - fwd * 1.5f + Vector3.up * 1.55f, feet + Vector3.up * 1.25f, 40f),            // straight behind at 1.5 m
                ("cam_cb_quarter", feet - fwd * 1.2f + right * .9f + Vector3.up * 1.55f, feet + Vector3.up * 1.25f, 40f), // three-quarter back
                ("cam_cb_helmet", feet - fwd * .62f + right * .32f + Vector3.up * 1.72f, feet + Vector3.up * 1.65f, 40f), // helmet close-up
                ("cam_cb_vest", feet - fwd * .85f + right * .25f + Vector3.up * 1.35f, feet + Vector3.up * 1.2f, 40f),  // vest close-up
            };
        }

        // ------------------------------------------------------------------ verify (-nographics)
        static string Verify()
        {
            OpenScene();
            var fails = new List<string>(); var info = new Dictionary<string, object>();
            void Must(bool ok, string what) { if (!ok) fails.Add(what); }
            // files: installed = pass outputs
            var files = new Dictionary<string, object>();
            foreach (var (file, asset) in Files)
            {
                var src = Path.Combine(ArtDir, "out", file); var a = Sha(Full(asset));
                bool inst = File.Exists(src) && Sha(src) == a;
                files[file] = new { asset, sha256 = a, installed = inst, guid = AssetDatabase.AssetPathToGUID(asset) };
                Must(inst, "not installed: " + file);
            }
            info["files"] = files;
            var motor = Motor(); var combat = Combat();
            var body = Body(motor);
            Must(body.bones.Length == 54 && body.bones.All(b => b), "body bones " + body.bones.Length);
            Must(body.sharedMaterials.Length == body.sharedMesh.subMeshCount && body.sharedMaterials.All(m => m), "body materials missing");
            Must(body.sharedMesh.bindposes.Length == 54, "body bindposes " + body.sharedMesh.bindposes.Length);
            info["body"] = Describe(body);
            var actor = motor.actor;
            Must(actor && actor.idle && actor.walk && actor.run, "player clips missing");
            info["clips"] = actor ? new[] { actor.idle, actor.walk, actor.run }.Select(c => c ? c.name + " " + AssetDatabase.GetAssetPath(c) : "MISSING").ToArray() : null;
            // armour pieces
            var vis = Visuals(motor);
            Must(vis, "no PlayerArmourVisuals");
            var pieces = new List<object>(); int armourTris = 0;
            if (vis)
                foreach (var p in vis.pieces)
                {
                    if (p == null) continue;
                    var smr = p.model ? p.model.GetComponentsInChildren<SkinnedMeshRenderer>(true).FirstOrDefault() : null;
                    Must(smr && smr.sharedMesh, "piece without mesh: " + p.itemId);
                    if (!smr || !smr.sharedMesh) continue;
                    var missing = new List<string>(); float diff = BindDiff(body, smr, missing);
                    Must(missing.Count == 0, p.itemId + " unbound bones " + string.Join(",", missing));
                    Must(diff < 1e-4f, p.itemId + " bind diff " + diff);
                    Must(smr.sharedMaterials.All(m => m) && smr.sharedMaterials.Length == smr.sharedMesh.subMeshCount, p.itemId + " material missing");
                    Must(smr.bones.All(b => b && b.IsChildOf(motor.visual)), p.itemId + " bone outside the player rig");
                    armourTris += smr.sharedMesh.triangles.Length / 3;
                    pieces.Add(new { p.itemId, p.slot, model = p.model.name, active = p.model.activeSelf, asset = AssetDatabase.GetAssetPath(smr.sharedMesh), bindMaxDiff = diff, detail = Describe(smr) });
                }
            info["pieces"] = pieces; info["armourTrianglesAllPieces"] = armourTris;
            // first-person view models and the armour mirror are not touched by this pass
            var mirrors = Object.FindObjectsByType<ViewModelArmourMirror>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            Must(mirrors.Length > 0, "no ViewModelArmourMirror");
            info["armourMirrors"] = mirrors.Select(m => new { m.name, sources = m.sources.Count(s => s), mirrors = m.mirrors.Count(s => s), total = m.mirrors.Length }).ToArray();
            foreach (var m in mirrors) Must(m.sources.Length == m.mirrors.Length && m.sources.All(s => s), m.name + " mirror sources broken");
            var fpArms = Object.FindObjectsByType<SkinnedMeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None)
                .Where(r => r.sharedMesh && AssetDatabase.GetAssetPath(r.sharedMesh) == FPArmsAsset).ToArray();
            info["fpArmsRenderers"] = fpArms.Length; Must(fpArms.Length > 0, "first-person arms renderers missing");
            info["fpArmsSha256"] = Sha(Full(FPArmsAsset));
            // cameras
            var cams = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(c => c.name.StartsWith("cam_cb_")).Select(c => c.name).OrderBy(n => n).ToArray();
            info["reviewCameras"] = cams; Must(cams.Length == 6, "review cameras " + cams.Length);
            // scripts
            int missingScripts = motor.visual.GetComponentsInChildren<Transform>(true).Sum(t => GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject));
            info["missingScriptsUnderPlayer"] = missingScripts; Must(missingScripts == 0, "missing scripts under the player");
            info["pass"] = fails.Count == 0; info["fails"] = fails;
            var json = JsonConvert.SerializeObject(info, Formatting.Indented);
            Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "verify.json"), json);
            if (fails.Count > 0) throw new InvalidOperationException("verify failed: " + string.Join("; ", fails));
            return json;
        }

        // ------------------------------------------------------------------ rollback
        static string Rollback()
        {
            var rb = Path.Combine(ArtDir, "rollback"); var restored = new List<string>();
            foreach (var (file, asset) in Files)
            {
                var keep = Path.Combine(rb, file); if (!File.Exists(keep)) continue;
                if (Sha(keep) != Sha(Full(asset))) { File.Copy(keep, Full(asset), true); restored.Add(file); }
                AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceUpdate);
            }
            OpenScene(); var s = EditorSceneManager.GetActiveScene(); int removed = 0;
            foreach (var g in s.GetRootGameObjects().Where(g => g.name == CamRoot).ToArray()) { Object.DestroyImmediate(g); removed++; }
            EditorSceneManager.MarkSceneDirty(s); EditorSceneManager.SaveScene(s);
            return "restored " + string.Join(", ", restored) + "; camera roots removed " + removed;
        }

        // ------------------------------------------------------------------ capture (graphics mode)
        /// Renders review frames of the colonist at the rifle review stand (open ground) through DuskStartPass.Preview.
        /// --shots kit|light|carrier|suit picks one set (each at most six cameras), --state before|after names the folder.
        /// Nothing is saved: piece visibility and pose are changed in memory only.
        static string Capture()
        {
            var a = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(a, k); return i >= 0 && i + 1 < a.Length ? a[i + 1] : d; }
            var set = Arg("--shots", "kit"); var state = Arg("--state", "after");
            var outDir = Path.Combine(Evidence, "captures", state); Directory.CreateDirectory(outDir);
            OpenScene();
            var motor = Motor(); var combat = Combat(); var actor = motor.actor; var body = motor.visual;
            var vis = Visuals(motor);
            if (combat.muzzleLight) combat.muzzleLight.enabled = false;
            if (combat.heldPistol) combat.heldPistol.SetActive(false); if (combat.heldRifle) combat.heldRifle.SetActive(false);
            foreach (var r in body.GetComponentsInChildren<SkinnedMeshRenderer>(true)) r.forceMatrixRecalculationPerRender = true;
            string[] kit = set switch
            {
                "carrier" => new[] { "warden_plate_carrier", "field_boots", "field_helmet", "field_armguards", "field_gloves" },
                "suit" => new string[0],
                _ => new[] { "field_vest", "field_boots", "field_helmet" },
            };
            foreach (var p in vis.pieces) if (p != null && p.model) p.model.SetActive(kit.Contains(p.itemId));
            var clock = Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var sunFwd = Quaternion.Euler(clock.profile.Evaluate(13f).keyEuler) * Vector3.forward;
            var toSun = -Vector3.ProjectOnPlane(sunFwd, Vector3.up).normalized;
            var feet = RifleArmourInstall.Stand;
            if (Physics.Raycast(feet + Vector3.up * 6, Vector3.down, out var hit, 30, ~(1 << 8), QueryTriggerInteraction.Ignore)) feet.y = hit.point.y;
            motor.transform.position = feet + Vector3.up * .015f;
            // "sun": his back to the sun (the worst case for speckle); "shade": he faces the sun, back in his own shadow
            void Face(Vector3 dir) { body.rotation = Quaternion.LookRotation(dir, Vector3.up); if (actor.idle) actor.idle.SampleAnimation(actor.animationSource.gameObject, .4f); }
            string Spec(string n, (string name, Vector3 pos, Vector3 look, float fov) s) => string.Format(CultureInfo.InvariantCulture, "{0}:{1},{2},{3}:{4},{5},{6}:{7}", n, s.pos.x, s.pos.y, s.pos.z, s.look.x, s.look.y, s.look.z, s.fov);
            var log = new List<string>();
            (string, Vector3, Vector3, float) S(Vector3 fwd, string n) => Shots(feet, fwd).First(x => x.name == n);
            Face(-toSun); DuskStartPass.Preview(13, Path.Combine(outDir, "warmup"), Spec("warm", S(-toSun, "cam_cb_back")));
            switch (set)
            {
                case "kit":
                    Face(-toSun); var f = -toSun;
                    log.Add(DuskStartPass.Preview(13, outDir, new[] { "cam_cb_conv", "cam_cb_follow", "cam_cb_back", "cam_cb_quarter", "cam_cb_helmet", "cam_cb_vest" }.Select(n => Spec("kit_sun_" + n.Substring(7), S(f, n))).ToArray()));
                    break;
                case "light":
                    Face(toSun);
                    log.Add(DuskStartPass.Preview(13, outDir, new[] { "cam_cb_conv", "cam_cb_back", "cam_cb_helmet" }.Select(n => Spec("kit_shade_" + n.Substring(7), S(toSun, n))).ToArray()));
                    Face(-toSun);
                    log.Add(DuskStartPass.Preview(20.5f, outDir, new[] { "cam_cb_conv", "cam_cb_back", "cam_cb_vest" }.Select(n => Spec("kit_night_" + n.Substring(7), S(-toSun, n))).ToArray()));
                    break;
                case "carrier":
                case "suit":
                    Face(-toSun);
                    log.Add(DuskStartPass.Preview(13, outDir, new[] { "cam_cb_conv", "cam_cb_back", "cam_cb_quarter" }.Select(n => Spec(set + "_sun_" + n.Substring(7), S(-toSun, n))).ToArray()));
                    Face(toSun);
                    log.Add(DuskStartPass.Preview(13, outDir, new[] { "cam_cb_conv", "cam_cb_back", "cam_cb_vest" }.Select(n => Spec(set + "_shade_" + n.Substring(7), S(toSun, n))).ToArray()));
                    break;
                default: throw new ArgumentException("unknown shot set " + set);
            }
            return string.Join("\n", log);
        }

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
                        "install" => Install(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        "capture" => Capture(),
                        "cameras" => CamerasStep(),
                        _ => throw new ArgumentException("unknown step " + st),
                    };
                    log.Add("[" + st + "] " + result); Debug.Log("ColonistBackPass20261120 " + st + ": " + result);
                }
            }
            catch (Exception e) { Debug.LogException(e); log.Add("FAILED " + e); code = 1; }
            try { Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, string.Join("_", steps) + "-result.txt"), string.Join("\n", log) + "\n"); } catch (Exception e) { Debug.LogException(e); }
            EditorApplication.Exit(code);
        }

        static string CamerasStep() { OpenScene(); var r = Cameras(); var s = EditorSceneManager.GetActiveScene(); EditorSceneManager.MarkSceneDirty(s); EditorSceneManager.SaveScene(s); return r; }
    }
}
