using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// Showcase phase 2, residents (20 Nov 2026, art/ward_residents_20261120, meshy/ward-residents-20261120): three Ward
    /// residents who fill places built to show how Ward lives and had nobody in them:
    ///  * Nadje, a Karaveen produce and pottery trader: the caravan market by the West Gate (stock crates, pottery stall,
    ///    behind the produce counter);
    ///  * Pell, the Node 07 goods dock tally clerk: tally desk, platform scale, bays 1 and 2, porters' handcart;
    ///  * Oren, an old water carrier: from his door in the stacked south wall homes to the Wardens' ration taps and back.
    /// Each is an AmbientWalker with work stops (AmbientWalker.stops, added by this pass: walkers without stops are unchanged)
    /// plus an NpcBarker with voiced Passing/Idle/Weapon lines (BarkDirector lets a walker at a work stop make Idle remarks).
    /// All three live under one scene root, "Ward residents", so the A/B can switch them off together.
    ///
    /// Steps (RunBatch --steps a,b,c; each idempotent):
    ///   barks     Data/Barks/barks_resident_*.asset from art/ward_residents_20261120/barks.json (takes bound by path while
    ///             the line's text matches; Inspector-edited text stays caption-only), audio importer settings as NpcLife.
    ///   simulate  (-nographics, scene NOT saved) builds the three routes in the opened city with no visual and runs each
    ///             walker for two laps at 30 fps: stops reached, facing, physics clearance of the body capsule every frame,
    ///             distance to the talking colonists. Writes simulate.json. Needs no Meshy model.
    ///   import    copies each resident's rigged_fixed.glb and clip GLBs from the Meshy record into Art/Imported/Meshy/WardResidents.
    ///   prefab    Prefabs/WardResidents/WardResident_&lt;Title&gt;.prefab: in-place walk (stride measured), idle/talk work clips
    ///             (in place, feet on the ground), LODGroup LOD0 ~20k / LOD1 ~6k, sampled bounds, skinning and Animation
    ///             culled off-screen.
    ///   install   scene root "Ward residents": walker roots, routes, stops, visuals, NpcBarker (added to BarkDirector.speakers),
    ///             ActorLookAt; review cameras under "Ward residents review cameras". Records install_record.json.
    ///   verify    (-nographics) checks all of the above, the existing walkers against before.json, writes verify.json; throws on a problem.
    ///   rollback  deactivates "Ward residents" and its cameras and removes its barkers from BarkDirector.speakers. Prefabs and
    ///             assets stay; install again to restore.
    ///   capture   (graphics) Editor captures of up to six review cameras: --hour 13|17|20.5 --cams a,b,c.
    /// -executeMethod AthenHill.Editor.WardResidentsInstall20261120.RunBatch -nographics --steps import,prefab,install,verify
    /// </summary>
    public static class WardResidentsInstall20261120
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Record = "../../meshy/ward-residents-20261120/";
        const string MeshyRoot = "../../meshy/";
        const string ArtRoot = "Assets/AthenHill/Art/Imported/Meshy/WardResidents";
        const string PrefabRoot = "Assets/AthenHill/Prefabs/WardResidents";
        const string BarksDir = "Assets/AthenHill/Data/Barks";
        const string BarkAudio = "Assets/AthenHill/Audio/ElevenLabs/NpcBarks/";
        const string Evidence = "../evidence/showcase_phase2/20261120/residents/";
        const string SceneRoot = "Ward residents";
        const string CameraRoot = "Ward residents review cameras";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string ArtDir => Path.Combine(Repo, "art/ward_residents_20261120");

        public class Spec
        {
            public string key, title, root, route; public float height, phase;
            /// clip sources relative to meshy/: walk (own rig), idle and talk (work motions, own rig or reused from another Meshy rig)
            public string walk, idle, talk;
            public string Prefab => PrefabRoot + "/WardResident_" + title + ".prefab";
            public string Instance => "WardResident " + title;
            public string Folder => ArtRoot + "/" + title;
            public string Model => Folder + "/" + title + ".glb";
            public string Material => Folder + "/" + title + ".mat";
            public string Speaker => "resident_" + title.ToLowerInvariant();
            public string Source(string role) => Folder + "/Source/" + role + "_" + Path.GetFileNameWithoutExtension(role == "walk" ? walk : role == "idle" ? idle : talk) + ".glb";
            public string ClipPath(string role) => Folder + "/Clips/" + key + "_" + role + ".anim";
        }
        public static readonly Spec[] Specs = {
            new Spec{ key = "trader", title = "Nadje", root = "npc_resident_nadje", route = "market", height = 1.74f, phase = .1f,
                walk = "ward-residents-20261120/trader/anim_only/walk_566.glb", idle = "ward-residents-20261120/trader/anim_only/inspect_281.glb",
                talk = "ward-residents-20261120/clerk/anim_only/checkout_34.glb" },   // 20 Nov: Meshy 7.1 rigs are "SmartRigArmature" rigs; reuse only clips from this generation
            new Spec{ key = "clerk", title = "Pell", root = "npc_resident_pell", route = "dock", height = 1.86f, phase = .35f,
                walk = "ward-residents-20261120/clerk/anim_only/walk_566.glb", idle = "ward-residents-20261120/trader/anim_only/inspect_281.glb",
                talk = "ward-residents-20261120/clerk/anim_only/checkout_34.glb" },
            new Spec{ key = "carrier", title = "Oren", root = "npc_resident_oren", route = "water", height = 1.66f, phase = .6f,
                walk = "ward-residents-20261120/clerk/anim_only/walk_566.glb",   // Elderly Shaky Walk (553, bought) shuffles at 0.17 m/s: unusable on a 62 m route
                idle = "ward-residents-20261120/trader/anim_only/inspect_281.glb",
                talk = "ward-residents-20261120/carrier/anim_only/drink_342.glb" },
        };
        public static float LodSwitch0 = .14f, LodCull = .012f;
        static readonly string[] Roles = { "walk", "idle", "talk" };

        static float R(float v, int d = 4) => (float)Math.Round(v, d);
        static float[] V(Vector3 v) => new[] { R(v.x), R(v.y), R(v.z) };
        static string PathOf(Transform t) { var s = t.name; while (t.parent) { t = t.parent; s = t.name + "/" + s; } return s; }
        static Transform Bone(Component root, string name) => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == name) ?? throw new Exception("No bone " + name + " under " + root.name);
        static IEnumerable<Spec> Selected()
        {
            var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, "--only");
            return i < 0 ? Specs : Specs.Where(s => a[i + 1].Split(',').Contains(s.key));
        }

        // ------------------------------------------------------------------ routes (art/ward_residents_20261120/routes.json)
        public class Stop { public int waypoint; public float seconds, yaw; public string clip, label; }
        public class Route { public float speed; public float[][] points; public Stop[] stops; }
        static Dictionary<string, Route> Routes() => JObject.Parse(File.ReadAllText(Path.Combine(ArtDir, "routes.json"))).Properties()
            .Where(p => !p.Name.StartsWith("_")).ToDictionary(p => p.Name, p => p.Value.ToObject<Route>());
        static Vector3 P(float[] xz) => new Vector3(xz[0], 0, xz[1]);

        // ------------------------------------------------------------------ barks
        static void AudioImport(string path)
        {
            var ai = AssetImporter.GetAtPath(path) as AudioImporter; if (!ai) return;
            var s = ai.defaultSampleSettings;
            if (ai.forceToMono && !ai.loadInBackground && s.loadType == AudioClipLoadType.CompressedInMemory && s.compressionFormat == AudioCompressionFormat.Vorbis && Mathf.Approximately(s.quality, .85f) && s.preloadAudioData) return;
            s.loadType = AudioClipLoadType.CompressedInMemory; s.compressionFormat = AudioCompressionFormat.Vorbis; s.quality = .85f; s.preloadAudioData = true;
            ai.defaultSampleSettings = s; ai.forceToMono = true; ai.loadInBackground = false; ai.SaveAndReimport();
        }
        static JObject BarkSource => JObject.Parse(File.ReadAllText(Path.Combine(ArtDir, "barks.json")));
        static string BarkSetPath(string speaker) => BarksDir + "/barks_" + speaker + ".asset";
        static Vector2 Hours(JToken t) => t is JArray a && a.Count == 2 ? new Vector2((float)a[0], (float)a[1]) : new Vector2(0, 24);

        public static object Barks()
        {
            AssetDatabase.Refresh();
            if (!AssetDatabase.IsValidFolder(BarksDir)) throw new Exception("Missing " + BarksDir + " (NPC life pass)");
            var log = new List<string>(); int voiced = 0;
            foreach (JObject sp in BarkSource["speakers"])
            {
                string id = (string)sp["id"]; var path = BarkSetPath(id);
                var set = AssetDatabase.LoadAssetAtPath<BarkSet>(path);
                if (!set) { set = ScriptableObject.CreateInstance<BarkSet>(); set.lines = new BarkLine[0]; AssetDatabase.CreateAsset(set, path); log.Add("created " + path); }
                set.speakerId = id; if (string.IsNullOrEmpty(set.displayName)) set.displayName = (string)sp["name"];
                var lines = (set.lines ?? new BarkLine[0]).Where(l => l != null).ToList();
                foreach (JObject j in sp["lines"])
                {
                    string lid = (string)j["id"], text = (string)j["text"];
                    var line = lines.FirstOrDefault(l => l.id == lid);
                    if (line == null)
                    {
                        line = new BarkLine { id = lid, trigger = (BarkTrigger)Enum.Parse(typeof(BarkTrigger), (string)j["trigger"]), text = text, requires = (string)j["requires"] ?? "", hours = Hours(j["hours"]), once = false, weight = 1 };
                        lines.Add(line);
                    }
                    var clipPath = BarkAudio + id + "-" + lid + ".wav"; AudioImport(clipPath);
                    var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(clipPath);
                    var want = clip && line.text == text ? clip : null;   // an Inspector-edited line stays caption-only
                    if (line.voice != want) line.voice = want;
                    if (want) voiced++; else log.Add($"caption-only {id}/{lid}" + (clip ? " (text edited)" : " (no take)"));
                }
                set.lines = lines.ToArray(); EditorUtility.SetDirty(set);
            }
            AssetDatabase.SaveAssets();
            return new { voiced, log };
        }

        // ------------------------------------------------------------------ simulate (no visuals, scene not saved)
        static readonly MethodInfo StartM = typeof(AmbientWalker).GetMethod("Start", BindingFlags.NonPublic | BindingFlags.Instance);
        static readonly MethodInfo StepM = typeof(AmbientWalker).GetMethod("UpdateWithStops", BindingFlags.NonPublic | BindingFlags.Instance);

        /// Non-trigger colliders the body capsule (r 0.25, 0.3-1.6 m) touches at a walker position, ignoring the ground and actors.
        static string[] Touching(Vector3 at)
        {
            return Physics.OverlapCapsule(at + Vector3.up * .55f, at + Vector3.up * 1.35f, .25f, ~0, QueryTriggerInteraction.Ignore)
                .Where(c => c && !c.GetComponentInParent<AmbientWalker>() && !c.GetComponentInParent<NpcAgent>() && !c.GetComponentInParent<PlayerMotor>() && c.bounds.max.y > .3f && c.bounds.size.x < 60 && c.bounds.size.z < 60)
                .Select(c => PathOf(c.transform)).Distinct().ToArray();
        }

        public static object Simulate()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); Physics.SyncTransforms();
            var routes = Routes(); var report = new Dictionary<string, object>(); var failures = new List<string>();
            var npcs = Object.FindObjectsByType<NpcAgent>(FindObjectsSortMode.None).Where(n => n.gameObject.activeInHierarchy).ToArray();
            foreach (var s in Specs)
            {
                var r = routes[s.route];
                var go = new GameObject("__sim_" + s.key); var wps = new List<Transform>();
                foreach (var p in r.points) { var w = new GameObject("wp").transform; w.SetParent(go.transform); w.position = P(p); wps.Add(w); }
                var walker = new GameObject("__walker_" + s.key).AddComponent<AmbientWalker>();
                walker.waypoints = wps.ToArray(); walker.speed = r.speed; walker.phase = 0;
                walker.stops = r.stops.Select(x => new AmbientWalker.WorkStop { waypoint = x.waypoint, seconds = x.seconds, facingYaw = x.yaw, talkClip = x.clip == "talk", label = x.label }).ToArray();
                StartM.Invoke(walker, null);
                float dt = 1 / 30f, t = 0, lap = r.points.Select((p, i) => Vector3.Distance(P(p), P(r.points[(i + 1) % r.points.Length]))).Sum() / r.speed + r.stops.Sum(x => x.seconds);
                var entered = new List<object>(); var touching = new Dictionary<string, int>(); float npcMin = 99, minSpeedRatio = 1; bool wasAtWork = false;
                Vector3 last = walker.transform.position; var facingErr = new List<float>(); AmbientWalker.WorkStop lastStop = null;
                while (t < lap * 2 + 5)
                {
                    StepM.Invoke(walker, new object[] { dt }); t += dt;
                    var pos = walker.transform.position;
                    if (walker.AtWork && (!wasAtWork || walker.CurrentStop != lastStop)) entered.Add(new { t = R(t, 1), stop = walker.CurrentStop.label, pos = V(pos) });
                    if (walker.AtWork && walker.StopSecondsLeft < dt * 1.5f) facingErr.Add(Mathf.Abs(Mathf.DeltaAngle(walker.transform.eulerAngles.y, walker.CurrentStop.facingYaw)));
                    if (!walker.AtWork && !wasAtWork && t > dt) minSpeedRatio = Mathf.Min(minSpeedRatio, Vector3.Distance(pos, last) / dt / r.speed);
                    wasAtWork = walker.AtWork; lastStop = walker.CurrentStop; last = pos;
                    foreach (var c in Touching(pos)) touching[c] = touching.TryGetValue(c, out var n) ? n + 1 : 1;
                    foreach (var n in npcs) npcMin = Mathf.Min(npcMin, Vector3.Distance(new Vector3(pos.x, 0, pos.z), new Vector3(n.transform.position.x, 0, n.transform.position.z)));
                }
                int expected = r.stops.Length * 2;
                if (entered.Count < expected) failures.Add($"{s.key}: {entered.Count} stops entered in two laps, expected {expected}");
                if (touching.Count > 0) failures.Add($"{s.key}: body capsule touches {string.Join(", ", touching.Keys.Take(4))}");
                if (npcMin < 3) failures.Add($"{s.key}: passes within {npcMin:F2} m of a talking colonist");
                float worstFacing = facingErr.Count > 0 ? facingErr.Max() : 0;
                if (worstFacing > 12) failures.Add($"{s.key}: facing at the end of a stop off by {worstFacing:F1} degrees");
                report[s.key] = new { route = s.route, lapSeconds = R(lap, 1), simulatedSeconds = R(t, 1), stopsEntered = entered, touching, nearestTalkingColonist = R(npcMin, 2), worstFacingErrorAtStopEnd = R(worstFacing, 1), slowestWalkingSpeedRatio = R(minSpeedRatio, 2) };
                Object.DestroyImmediate(walker.gameObject); Object.DestroyImmediate(go);
            }
            var result = new { ok = failures.Count == 0, failures, residents = report };
            Directory.CreateDirectory(Evidence); File.WriteAllText(Evidence + "simulate.json", JsonConvert.SerializeObject(result, Formatting.Indented));
            if (failures.Count > 0) throw new Exception("Simulate: " + string.Join("; ", failures));
            return result;
        }

        // ------------------------------------------------------------------ import
        public static object Import()
        {
            var report = new List<object>();
            foreach (var s in Selected())
            {
                Directory.CreateDirectory(s.Folder + "/Source"); Directory.CreateDirectory(s.Folder + "/Clips");
                var copied = new List<string>();
                void Copy(string from, string to)
                {
                    if (!File.Exists(from)) throw new FileNotFoundException("Missing Meshy record file " + from);
                    if (File.Exists(to) && File.ReadAllBytes(to).SequenceEqual(File.ReadAllBytes(from))) return;
                    File.Copy(from, to, true); copied.Add(to);
                }
                Copy(Record + s.key + "/rigged_fixed.glb", s.Model);
                foreach (var role in Roles) Copy(MeshyRoot + (role == "walk" ? s.walk : role == "idle" ? s.idle : s.talk), s.Source(role));
                AssetDatabase.Refresh();
                foreach (var path in Roles.Select(s.Source).Prepend(s.Model))
                {
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                    var importer = AssetImporter.GetAtPath(path) ?? throw new Exception("No importer for " + path);
                    var so = new SerializedObject(importer);
                    var method = so.FindProperty("importSettings.animationMethod") ?? throw new Exception("Expected glTFast import settings on " + path);
                    int legacy = Array.IndexOf(method.enumNames, "Legacy");
                    if (method.enumValueIndex != legacy) { method.enumValueIndex = legacy; so.ApplyModifiedPropertiesWithoutUndo(); importer.SaveAndReimport(); }
                    if (path != s.Model && !AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Any(c => c.legacy)) throw new Exception("No legacy clip in " + path);
                }
                if (!AssetDatabase.LoadAssetAtPath<GameObject>(s.Model)) throw new Exception("Model failed to import: " + s.Model);
                var tex = AssetDatabase.LoadAllAssetsAtPath(s.Model).OfType<Texture2D>().Select(t => new { t.name, t.width, t.height, format = t.format.ToString() }).ToArray();
                report.Add(new { s.key, copied, tex });
            }
            return report;
        }

        // ------------------------------------------------------------------ clips
        static bool IsHipsPos(EditorCurveBinding b) => (b.propertyName.StartsWith("m_LocalPosition") || b.propertyName.StartsWith("localPosition")) && (b.path == "Hips" || b.path.EndsWith("/Hips"));
        static float CloseLoop(AnimationCurve curve, float seconds, float share)
        {
            var keys = curve.keys; float end = keys[keys.Length - 1].time, start = keys[0].time;
            float seam = Mathf.Abs(keys[keys.Length - 1].value - keys[0].value);
            if (seam < 1e-4f) return seam;
            seconds = Mathf.Min(seconds, (end - start) * share);
            for (int i = 0; i < keys.Length; i++)
            {
                float w = Mathf.InverseLerp(end - seconds, end, keys[i].time); if (w <= 0) continue;
                w = w * w * (3 - 2 * w); keys[i].value = Mathf.Lerp(keys[i].value, keys[0].value, w);
            }
            curve.keys = keys; return seam;
        }
        static void Save(AnimationClip clip, string target)
        {
            var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(target);
            if (existing) { EditorUtility.CopySerialized(clip, existing); Object.DestroyImmediate(clip); EditorUtility.SetDirty(existing); }
            else AssetDatabase.CreateAsset(clip, target);
        }
        static void ShiftHips(AnimationClip clip, Vector3 add)
        {
            foreach (var b in AnimationUtility.GetCurveBindings(clip).Where(IsHipsPos))
            {
                var c = AnimationUtility.GetEditorCurve(clip, b); float a = b.propertyName.EndsWith(".x") ? add.x : b.propertyName.EndsWith(".y") ? add.y : add.z;
                var keys = c.keys; for (int i = 0; i < keys.Length; i++) keys[i].value += a; c.keys = keys;
                AnimationUtility.SetEditorCurve(clip, b, c);
            }
        }

        /// In-place walk (as WardWalkerInstall): Hips drift over the cycle removed, soles on y = 0, small loop seams closed.
        static object DeriveWalk(AnimationClip source, string target, GameObject host, SkinnedMeshRenderer smr, Transform root, Transform hips, out float rootSpeed)
        {
            var bindings = AnimationUtility.GetCurveBindings(source);
            var drift = Vector3.zero; float len = source.length;
            foreach (var b in bindings.Where(IsHipsPos))
            {
                var c = AnimationUtility.GetEditorCurve(source, b); float d = c.Evaluate(len) - c.Evaluate(0);
                if (b.propertyName.EndsWith(".x")) drift.x = d; else if (b.propertyName.EndsWith(".y")) drift.y = d; else drift.z = d;
            }
            var driftRoot = root.InverseTransformVector(hips.parent.TransformVector(drift));
            rootSpeed = new Vector2(driftRoot.x, driftRoot.z).magnitude / Mathf.Max(.001f, len);
            var clip = new AnimationClip { name = Path.GetFileNameWithoutExtension(target), legacy = true, frameRate = source.frameRate, wrapMode = WrapMode.Loop };
            int kept = 0, hipsCurves = 0; float seam = 0;
            foreach (var b in bindings)
            {
                bool rotation = b.propertyName.StartsWith("m_LocalRotation") || b.propertyName.StartsWith("localRotation"); bool hp = IsHipsPos(b);
                if (!rotation && !hp) continue;
                var curve = AnimationUtility.GetEditorCurve(source, b);
                if (hp)
                {
                    float d = b.propertyName.EndsWith(".x") ? drift.x : b.propertyName.EndsWith(".y") ? drift.y : drift.z;
                    var keys = curve.keys; for (int i = 0; i < keys.Length; i++) keys[i].value -= d * (keys[i].time / Mathf.Max(.001f, len)); curve.keys = keys; hipsCurves++;
                }
                if (curve.length > 2 && Mathf.Abs(curve.keys[curve.length - 1].value - curve.keys[0].value) < .3f) seam = Mathf.Max(seam, CloseLoop(curve, .12f, .15f));
                clip.SetCurve(b.path, typeof(Transform), b.propertyName.Replace("m_LocalRotation", "localRotation").Replace("m_LocalPosition", "localPosition"), curve); kept++;
            }
            if (hipsCurves != 3) throw new Exception("Expected Hips x/y/z translation curves in " + source.name + ", found " + hipsCurves);
            clip.EnsureQuaternionContinuity();
            float low = float.MaxValue;
            for (int k = 0; k < 24; k++) { clip.SampleAnimation(host, clip.length * k / 24f); low = Mathf.Min(low, WardNpcInstall.Skin(smr, root).Min(p => p.y)); }
            ShiftHips(clip, hips.parent.InverseTransformVector(root.TransformVector(new Vector3(0, -low, 0))));
            Save(clip, target);
            return new { target, length = R(source.length, 3), curvesKept = kept, maxLoopSeam = R(seam), hipsDriftRoot = V(driftRoot), soleLift = R(-low) };
        }

        /// In-place work motion (idle/talk, possibly from another Meshy rig with the same bone names): rotations + Hips
        /// translation, Hips drift removed, the lower foot bone kept at its bind height above the soles (so a bend or a
        /// crouch does not lift the body to put a hand on the ground), loop seam blended over 0.3 s.
        static object DeriveWork(AnimationClip source, string target, GameObject host, Transform root, Transform hips, float restFootAboveSole)
        {
            var clip = new AnimationClip { name = Path.GetFileNameWithoutExtension(target), legacy = true, frameRate = source.frameRate, wrapMode = WrapMode.Loop };
            float len = source.length; int kept = 0, hipsCurves = 0; float seam = 0;
            foreach (var b in AnimationUtility.GetCurveBindings(source))
            {
                bool rotation = b.propertyName.StartsWith("m_LocalRotation") || b.propertyName.StartsWith("localRotation"); bool hp = IsHipsPos(b);
                if (!rotation && !hp) continue;
                if (b.path.Length > 0 && !host.transform.Find(b.path)) continue;   // a bone this rig lacks (e.g. fingers)
                var curve = AnimationUtility.GetEditorCurve(source, b);
                if (hp)
                {
                    float d = curve.Evaluate(len) - curve.Evaluate(0);
                    if (!b.propertyName.EndsWith(".y")) { var keys = curve.keys; for (int i = 0; i < keys.Length; i++) keys[i].value -= d * (keys[i].time / Mathf.Max(.001f, len)); curve.keys = keys; }
                    hipsCurves++;
                }
                if (curve.length > 2 && Mathf.Abs(curve.keys[curve.length - 1].value - curve.keys[0].value) < .3f) seam = Mathf.Max(seam, CloseLoop(curve, .3f, .25f));
                clip.SetCurve(b.path, typeof(Transform), b.propertyName.Replace("m_LocalRotation", "localRotation").Replace("m_LocalPosition", "localPosition"), curve); kept++;
            }
            if (hipsCurves != 3) throw new Exception("Expected Hips x/y/z translation curves in " + source.name + ", found " + hipsCurves);
            clip.EnsureQuaternionContinuity();
            var feet = new[] { Bone(host.transform, "LeftFoot"), Bone(host.transform, "RightFoot") };
            float low = float.MaxValue;
            for (int k = 0; k < 24; k++) { clip.SampleAnimation(host, clip.length * k / 24f); low = Mathf.Min(low, feet.Min(f => root.InverseTransformPoint(f.position).y)); }
            ShiftHips(clip, hips.parent.InverseTransformVector(root.TransformVector(new Vector3(0, restFootAboveSole - low, 0))));
            Save(clip, target);
            return new { target, source = source.name, length = R(len, 3), curvesKept = kept, loopSeam = R(seam), footLift = R(restFootAboveSole - low) };
        }

        static Bounds PoseBounds(SkinnedMeshRenderer r, GameObject host, IEnumerable<AnimationClip> clips)
        {
            var space = r.rootBone ? r.rootBone : r.transform; bool any = false; var b = new Bounds();
            foreach (var clip in clips)
                for (int k = 0; k < 16; k++)
                {
                    clip.SampleAnimation(host, clip.length * k / 16f);
                    foreach (var p in WardNpcInstall.Skin(r, space)) { if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p); }
                }
            b.Expand(b.size * .12f);
            return b;
        }

        // ------------------------------------------------------------------ prefab
        public static object BuildPrefabs()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);   // the city scene is not touched here
            Directory.CreateDirectory(PrefabRoot);
            var all = new Dictionary<string, object>();
            foreach (var s in Selected())
            {
                var log = new List<string>();
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(s.Model) ?? throw new Exception("Run the import step first: " + s.Model);
                var root = new GameObject("WardResident_" + s.title);
                try
                {
                    var visual = new GameObject("Visual").transform; visual.SetParent(root.transform, false);
                    var rig = (GameObject)PrefabUtility.InstantiatePrefab(model); rig.transform.SetParent(visual, false);
                    var smrs = rig.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                    // LOD0 is the rig's own mesh node (char1 on 2026 rigs, Mesh_0 on Meshy 7.1 rigs); glb_lod.py adds char1_lod1
                    var smr = smrs.FirstOrDefault(r => r.name != "char1_lod1") ?? throw new Exception(s.key + ": no LOD0 renderer");
                    var lod1 = smrs.FirstOrDefault(r => r.name == "char1_lod1") ?? throw new Exception(s.key + ": no char1_lod1 (LOD1) renderer");
                    if (smrs.Length != 2) throw new Exception(s.key + ": expected LOD0 + LOD1, found " + smrs.Length);
                    AnimationClip SourceClip(string role) => AssetDatabase.LoadAllAssetsAtPath(s.Source(role)).OfType<AnimationClip>().FirstOrDefault(c => c && c.legacy) ?? throw new Exception("No legacy " + role + " clip " + s.key);
                    var srcWalk = SourceClip("walk");
                    var paths = AnimationUtility.GetCurveBindings(srcWalk).Select(b => b.path).Distinct().ToArray();
                    bool All(Transform t) => paths.All(p => p.Length == 0 || t.Find(p) != null);
                    Transform host = rig.GetComponentsInChildren<Transform>(true).Prepend(visual).FirstOrDefault(All);
                    if (!host)
                    {
                        var first = paths.Select(p => p.Split('/')[0]).Distinct().ToArray();
                        if (first.Length == 1) { log.Add("instance root renamed '" + rig.name + "' -> '" + first[0] + "'"); rig.name = first[0]; }
                        host = All(visual) ? visual : throw new Exception("Walk clip paths do not resolve: " + string.Join(", ", paths.Take(4)));
                    }
                    var anim = host.GetComponent<Animation>(); if (!anim) anim = host.gameObject.AddComponent<Animation>();
                    foreach (var other in rig.GetComponentsInChildren<Animation>(true).Concat(visual.GetComponents<Animation>()).ToArray()) if (other != anim) Object.DestroyImmediate(other);

                    var rest = WardNpcInstall.Skin(smr, root.transform);
                    float standing = rest.Max(p => p.y) - rest.Min(p => p.y), scale = s.height / standing;
                    visual.localScale = Vector3.one * scale;
                    log.Add($"rest height {standing:F4}; uniform scale {scale:F4} -> {s.height} m");
                    var head = Bone(host, "Head"); var front = host.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "headfront");
                    if (front && (root.transform.InverseTransformPoint(front.position) - root.transform.InverseTransformPoint(head.position)).z < 0) { visual.localRotation = Quaternion.Euler(0, 180, 0); log.Add("visual turned 180 degrees to face +Z"); }
                    // bind pose: the lower foot bone's height above the soles (work clips keep it)
                    rest = WardNpcInstall.Skin(smr, root.transform);
                    float restLow = rest.Min(p => p.y);
                    float restFoot = new[] { "LeftFoot", "RightFoot" }.Min(f => root.transform.InverseTransformPoint(Bone(host, f).position).y) - restLow;
                    var hips = Bone(host, "Hips");
                    var walkInfo = DeriveWalk(srcWalk, s.ClipPath("walk"), host.gameObject, smr, root.transform, hips, out float rootSpeed);
                    var idleInfo = DeriveWork(SourceClip("idle"), s.ClipPath("idle"), host.gameObject, root.transform, hips, restFoot);
                    var talkInfo = DeriveWork(SourceClip("talk"), s.ClipPath("talk"), host.gameObject, root.transform, hips, restFoot);
                    AssetDatabase.SaveAssets();
                    var walk = AssetDatabase.LoadAssetAtPath<AnimationClip>(s.ClipPath("walk"));
                    var idle = AssetDatabase.LoadAssetAtPath<AnimationClip>(s.ClipPath("idle"));
                    var talk = AssetDatabase.LoadAssetAtPath<AnimationClip>(s.ClipPath("talk"));
                    var (planted, strideInfo) = WardWalkerInstall.StrideSpeed(walk, host.gameObject, root.transform);
                    // 20 Nov: on the Meshy 7.1 (SmartRig) Walking 2 the root-motion speed is 17-28 % above what the in-place
                    // clip's planted foot actually does; the planted foot is what has to match the route speed (no sliding).
                    float stride = planted;
                    if (stride < .3f || stride > 2.2f) throw new Exception(s.key + ": implausible stride speed " + stride);

                    var src = smr.sharedMaterial;
                    if (!src || !src.shader || src.shader.name.Contains("Error")) throw new Exception(s.key + ": material failed to import");
                    var mat = AssetDatabase.LoadAssetAtPath<Material>(s.Material);
                    if (!mat) { mat = new Material(src) { name = s.title }; AssetDatabase.CreateAsset(mat, s.Material); log.Add("material created from " + src.shader.name); }
                    var boundsInfo = new List<object>();
                    foreach (var r in new[] { smr, lod1 })
                    {
                        r.sharedMaterial = mat; r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true; r.updateWhenOffscreen = false;
                        r.localBounds = PoseBounds(r, host.gameObject, new[] { walk, idle, talk });
                        boundsInfo.Add(new { r.name, centre = V(r.localBounds.center), size = V(r.localBounds.size) });
                    }
                    var lodGroup = visual.gameObject.AddComponent<LODGroup>();
                    lodGroup.SetLODs(new[] { new LOD(LodSwitch0, new Renderer[] { smr }), new LOD(LodCull, new Renderer[] { lod1 }) });
                    lodGroup.RecalculateBounds();
                    anim.playAutomatically = false; anim.clip = walk; anim.cullingType = AnimationCullingType.BasedOnRenderers;
                    AnimationUtility.SetAnimationClips(anim, new[] { walk, idle, talk });
                    var actor = root.AddComponent<ActorAnimation>();
                    actor.animationSource = anim; actor.idle = idle; actor.walk = walk; actor.run = walk; actor.talk = talk;
                    actor.walkStrideSpeed = actor.runStrideSpeed = stride;
                    actor.randomIdlePhase = true; actor.idleSpeedJitter = .05f;
                    walk.SampleAnimation(host.gameObject, 0);
                    var prefab = PrefabUtility.SaveAsPrefabAsset(root, s.Prefab, out bool ok);
                    if (!ok || !prefab) throw new Exception("Prefab save failed: " + s.Prefab);
                    all[s.key] = new { prefab = s.Prefab, scale = R(scale), host = host.name, log, walk = walkInfo, idle = idleInfo, talk = talkInfo, stride = strideInfo, walkStrideSpeed = R(stride, 3), strideSource = "planted foot", rootMotionSpeed = R(rootSpeed, 3), restFootAboveSole = R(restFoot), triangles = smr.sharedMesh.triangles.Length / 3, lod1Triangles = lod1.sharedMesh.triangles.Length / 3, bones = smr.bones.Length, bounds = boundsInfo };
                }
                finally { Object.DestroyImmediate(root); }
            }
            AssetDatabase.SaveAssets();
            return all;
        }

        // ------------------------------------------------------------------ install
        class InstallRecord { public bool sceneRootCreated; public List<string> speakersAdded = new List<string>(); public List<string> log = new List<string>(); }
        static string RecordFile => Path.Combine(ArtDir, "install_record.json");
        static InstallRecord LoadRecord() => File.Exists(RecordFile) ? JsonConvert.DeserializeObject<InstallRecord>(File.ReadAllText(RecordFile)) : new InstallRecord();
        static void SaveRecord(InstallRecord r) => File.WriteAllText(RecordFile, JsonConvert.SerializeObject(r, Formatting.Indented));

        static IEnumerable<AmbientWalker> OtherWalkers(GameObject residentsRoot) => Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None)
            .Where(w => !residentsRoot || !w.transform.IsChildOf(residentsRoot.transform));
        static object Snapshot(GameObject residentsRoot) => OtherWalkers(residentsRoot).OrderBy(w => PathOf(w.transform), StringComparer.Ordinal).Select(w => new
        {
            path = PathOf(w.transform), active = w.gameObject.activeSelf, w.speed, w.phase, w.turnLookAhead, w.turnSharpness, stops = w.stops == null ? 0 : w.stops.Length,
            position = V(w.transform.position), rotation = V(w.transform.eulerAngles),
            waypoints = w.waypoints.Select(p => p ? PathOf(p) + "@" + string.Join(",", V(p.position)) : "null").ToArray(),
            actor = w.actor ? PathOf(w.actor.transform) : null,
        }).ToArray();
        static GameObject FindRoot(string name) => EditorSceneManager.GetActiveScene().GetRootGameObjects().FirstOrDefault(g => g.name == name);

        public static object Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Directory.CreateDirectory(Evidence);
            var rec = LoadRecord(); var routes = Routes();
            var top = FindRoot(SceneRoot);
            string beforeFile = Evidence + "before.json";
            if (!File.Exists(beforeFile)) File.WriteAllText(beforeFile, JsonConvert.SerializeObject(Snapshot(top), Formatting.Indented));
            if (!top) { top = new GameObject(SceneRoot); rec.sceneRootCreated = true; rec.log.Add(DateTime.UtcNow.ToString("u") + " created " + SceneRoot); }
            top.SetActive(true);
            var routeRoot = top.transform.Find("Routes") ?? new GameObject("Routes").transform; routeRoot.SetParent(top.transform, false);
            var session = Object.FindAnyObjectByType<GameSession>() ?? throw new Exception("Saved city has no GameSession");
            var director = session.GetComponent<BarkDirector>() ?? throw new Exception("No BarkDirector (run the NPC life pass first)");
            var report = new Dictionary<string, object>();
            foreach (var s in Specs)
            {
                var r = routes[s.route];
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(s.Prefab) ?? throw new Exception("Run the prefab step first: " + s.Prefab);
                // route waypoints (rebuilt from routes.json each install)
                var rt = routeRoot.Find(s.root + " route"); if (rt) Object.DestroyImmediate(rt.gameObject);
                rt = new GameObject(s.root + " route").transform; rt.SetParent(routeRoot, false);
                var wps = r.points.Select((p, i) => { var w = new GameObject("wp_" + i.ToString("00")).transform; w.SetParent(rt, false); w.position = P(p); return w; }).ToArray();
                // walker root
                var wt = top.transform.Find(s.root); if (!wt) { wt = new GameObject(s.root).transform; wt.SetParent(top.transform, false); }
                wt.position = wps[0].position; wt.rotation = Quaternion.LookRotation(Vector3.ProjectOnPlane(wps[1].position - wps[0].position, Vector3.up).normalized + Vector3.forward * 1e-4f);
                var walker = wt.GetComponent<AmbientWalker>() ?? wt.gameObject.AddComponent<AmbientWalker>();
                walker.waypoints = wps; walker.speed = r.speed; walker.phase = s.phase;
                walker.stops = r.stops.Select(x => new AmbientWalker.WorkStop { waypoint = x.waypoint, seconds = x.seconds, facingYaw = x.yaw, talkClip = x.clip == "talk", label = x.label }).ToArray();
                // visual
                var inst = wt.Find(s.Instance)?.gameObject;
                if (inst && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst) != s.Prefab) { Object.DestroyImmediate(inst); inst = null; }
                if (!inst) { inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene); inst.name = s.Instance; inst.transform.SetParent(wt, false); }
                inst.SetActive(true); inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity; inst.transform.localScale = Vector3.one;
                walker.actor = inst.GetComponent<ActorAnimation>();
                walker.actor.walk.SampleAnimation(walker.actor.animationSource.gameObject, 0);
                EditorUtility.SetDirty(walker);
                // voice
                var set = AssetDatabase.LoadAssetAtPath<BarkSet>(BarkSetPath(s.Speaker)) ?? throw new Exception("Run the barks step first");
                var barker = wt.GetComponent<NpcBarker>() ?? wt.gameObject.AddComponent<NpcBarker>();
                barker.agent = null; barker.barks = set; barker.voiceHeight = s.height * .9f; EditorUtility.SetDirty(barker);
                if (!director.speakers.Contains(barker)) { director.speakers = director.speakers.Where(x => x).Append(barker).ToArray(); EditorUtility.SetDirty(director); if (!rec.speakersAdded.Contains(PathOf(wt))) rec.speakersAdded.Add(PathOf(wt)); }
                var look = inst.GetComponent<ActorLookAt>();
                if (!look)
                {
                    look = inst.AddComponent<ActorLookAt>();
                    look.actor = walker.actor; look.focusRadius = 4.5f; look.maxYaw = 55; look.maxPitch = 10; look.restWeight = 0; look.focusWeight = .8f;
                    look.glanceYaw = 0; look.settleSeconds = .45f; look.activeDistance = 30;
                }
                report[s.key] = new { walker = PathOf(wt), visual = PathOf(inst.transform), r.speed, stride = walker.actor.walkStrideSpeed, playbackRate = R(r.speed / walker.actor.walkStrideSpeed, 3), stops = r.stops.Length, speaker = s.Speaker };
            }
            report["cameras"] = Cameras(top);
            report["landmarks"] = Landmarks(true);
            rec.log.Add(DateTime.UtcNow.ToString("u") + " install"); SaveRecord(rec);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            return report;
        }

        static string Slug(string label) => new string(label.ToLowerInvariant().Select(c => char.IsLetterOrDigit(c) ? c : '_').ToArray()).Trim('_').Replace("__", "_");
        public static string StopCamera(Spec s, Stop stop) => "cam_res_" + s.title.ToLowerInvariant() + "_" + Slug(stop.label).Split('_').Take(3).Aggregate((a, b) => a + "_" + b);

        static string Cameras(GameObject residents)
        {
            var scene = EditorSceneManager.GetActiveScene(); Physics.SyncTransforms();
            var root = FindRoot(CameraRoot); if (!root) root = new GameObject(CameraRoot);
            root.SetActive(true);
            foreach (Transform c in root.transform.Cast<Transform>().ToArray()) Object.DestroyImmediate(c.gameObject);
            var template = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(c => c.name == "cam_checkpoint_player");
            var names = new List<string>(); var routes = Routes();
            Camera Cam(string name, Vector3 pos, Vector3 look, float fov)
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                var cam = go.AddComponent<Camera>(); if (template) cam.CopyFrom(template); cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f;
                var dir = pos - look;
                foreach (var hit in Physics.RaycastAll(look, dir.normalized, dir.magnitude, ~0, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance))
                {
                    if (hit.transform.IsChildOf(residents.transform)) continue;
                    pos = look + dir.normalized * Mathf.Max(.45f, hit.distance - .15f); break;
                }
                go.transform.position = pos; go.transform.LookAt(look); names.Add(name);
                return cam;
            }
            foreach (var s in Specs)
            {
                var r = routes[s.route]; var main = MainStop(r); var feet = P(r.points[main.waypoint]);
                var f = Quaternion.Euler(0, main.yaw, 0) * Vector3.forward; var right = Vector3.Cross(Vector3.up, f); float h = s.height;
                string n = s.title.ToLowerInvariant();
                // face, body and beside follow the resident at run time (ResidentReviewCamera); the initial pose is the main stop
                var walkerRoot = residents.transform.Find(s.root);
                void Follow(Camera c, ResidentReviewCamera.Framing framing) { var rc = c.gameObject.AddComponent<ResidentReviewCamera>(); rc.target = walkerRoot; rc.framing = framing; rc.height = h; }
                Follow(Cam("cam_res_" + n + "_face", feet + f * .9f + right * .15f + Vector3.up * (h * .93f), feet + Vector3.up * (h * .925f), 30), ResidentReviewCamera.Framing.Face);
                Follow(Cam("cam_res_" + n + "_body", feet + f * 2.8f + right * 1.0f + Vector3.up * 1.5f, feet + Vector3.up * (h * .5f), 42), ResidentReviewCamera.Framing.Body);
                Follow(Cam("cam_res_" + n + "_beside", feet + Quaternion.Euler(0, 30, 0) * f * 1.4f + Vector3.up * 1.62f, feet + Vector3.up * (h * .92f), 50), ResidentReviewCamera.Framing.Beside);
                foreach (var st in r.stops.Where(x => x != main))
                {
                    var at = P(r.points[st.waypoint]); var g = Quaternion.Euler(0, st.yaw + 35, 0) * Vector3.forward;
                    Cam(StopCamera(s, st), at + g * 3.6f + Vector3.up * 1.6f, at + Vector3.up * 1.0f, 50);
                }
            }
            return string.Join(", ", names);
        }
        static Stop MainStop(Route r) => r.stops.OrderByDescending(x => x.seconds).First();

        // QA landmarks (AthenDebugBridge "goto"): where the player stands to talk beside each resident at a work stop.
        public static string LandmarkName(Spec s) => "res_" + s.title.ToLowerInvariant();
        static readonly Dictionary<string, Vector3> LandmarkSpots = new Dictionary<string, Vector3>
        {
            { "trader", new Vector3(-37.6f, .5f, 12.2f) },   // customer side of the produce counter, Nadje behind it
            { "clerk", new Vector3(11.15f, .5f, 30.3f) },    // beside the Node 07 tally desk, Pell at it
            { "carrier", new Vector3(3.3f, .5f, -26.9f) },   // north of the ration taps, Oren at the tap
        };
        static Transform LandmarksRoot() => FindRoot("Landmarks")?.transform;
        static Transform QaLandmark(Spec s) => LandmarksRoot()?.Find(LandmarkName(s));
        static List<string> Landmarks(bool active)
        {
            var root = LandmarksRoot() ?? throw new Exception("No Landmarks root"); var log = new List<string>();
            foreach (var s in Specs)
            {
                var t = root.Find(LandmarkName(s));
                if (!t) { t = new GameObject(LandmarkName(s)).transform; t.SetParent(root, false); log.Add("landmark " + t.name); }
                t.position = LandmarkSpots[s.key]; t.gameObject.SetActive(active);
            }
            return log;
        }

        // ------------------------------------------------------------------ verify
        public static object Verify()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); Physics.SyncTransforms();
            var failures = new List<string>(); var report = new Dictionary<string, object>(); var routes = Routes();
            var top = FindRoot(SceneRoot);
            if (!top) throw new Exception("No scene root " + SceneRoot);
            if (!top.activeSelf) failures.Add(SceneRoot + " inactive");
            var director = Object.FindAnyObjectByType<GameSession>()?.GetComponent<BarkDirector>();
            if (!director) failures.Add("no BarkDirector");
            var npcs = Object.FindObjectsByType<NpcAgent>(FindObjectsSortMode.None).Where(n => n.gameObject.activeInHierarchy).ToArray();
            var nightLighting = Object.FindFirstObjectByType<NightActorLighting>(FindObjectsInactive.Include);
            if (!nightLighting) failures.Add("no NightActorLighting in the scene (residents would not get the night actor probe)");
            foreach (var s in Specs)
            {
                var r = routes[s.route];
                var wt = top.transform.Find(s.root); if (!wt) { failures.Add(s.key + ": walker root missing"); continue; }
                var walker = wt.GetComponent<AmbientWalker>(); var inst = wt.Find(s.Instance);
                if (!walker || !inst) { failures.Add(s.key + ": walker or visual missing"); continue; }
                bool linked = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst.gameObject) == s.Prefab && PrefabUtility.IsAnyPrefabInstanceRoot(inst.gameObject);
                if (!linked) failures.Add(s.key + ": prefab link broken");
                if (!inst.gameObject.activeInHierarchy) failures.Add(s.key + ": visual inactive");
                var actor = inst.GetComponent<ActorAnimation>();
                if (walker.actor != actor) failures.Add(s.key + ": AmbientWalker.actor is not the visual");
                var smr = inst.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(x => x.sharedMesh.triangles.Length).ToArray();
                if (smr.Any(x => x.updateWhenOffscreen)) failures.Add(s.key + ": updateWhenOffscreen on");
                if (!inst.GetComponentInChildren<LODGroup>()) failures.Add(s.key + ": no LODGroup");
                var anim = actor.animationSource;
                if (anim.cullingType != AnimationCullingType.BasedOnRenderers) failures.Add(s.key + ": Animation culling not BasedOnRenderers");
                foreach (var rr in inst.GetComponentsInChildren<Renderer>(true)) foreach (var m in rr.sharedMaterials)
                    if (!m || !m.shader || m.shader.name.Contains("Error")) failures.Add(s.key + ": missing/broken material on " + rr.name);
                int missing = wt.GetComponentsInChildren<Component>(true).Count(c => c == null); if (missing > 0) failures.Add(s.key + ": " + missing + " missing scripts");
                if (inst.GetComponentsInChildren<Collider>(true).Length > 0) failures.Add(s.key + ": colliders on the moving visual");
                foreach (var clip in new[] { actor.walk, actor.idle, actor.talk })
                {
                    if (!clip) { failures.Add(s.key + ": clip missing"); continue; }
                    int unresolved = AnimationUtility.GetCurveBindings(clip).Count(b => b.path.Length > 0 && !anim.transform.Find(b.path));
                    if (unresolved > 0) failures.Add(s.key + ": " + unresolved + " unresolved paths in " + clip.name);
                }
                int tris = smr[0].sharedMesh.triangles.Length / 3; if (tris > 21000) failures.Add(s.key + ": LOD0 " + tris + " triangles");
                float hMax = 0, soleMin = 1, soleMax = -1;
                for (int k = 0; k < 12; k++)
                {
                    actor.walk.SampleAnimation(anim.gameObject, actor.walk.length * k / 12f);
                    var pts = WardNpcInstall.Skin(smr[0], inst); float lo = pts.Min(p => p.y);
                    hMax = Mathf.Max(hMax, pts.Max(p => p.y) - lo); soleMin = Mathf.Min(soleMin, lo); soleMax = Mathf.Max(soleMax, lo);
                }
                if (Mathf.Abs(soleMin) > .02f) failures.Add(s.key + ": lowest sole off the ground " + soleMin);
                if (hMax > s.height + .12f || hMax < s.height - .3f) failures.Add(s.key + ": walking height " + hMax);
                var workSoles = new Dictionary<string, float[]>();
                foreach (var clip in new[] { actor.idle, actor.talk })
                {
                    float lo = 1, hi = -1;
                    for (int k = 0; k < 12; k++) { clip.SampleAnimation(anim.gameObject, clip.length * k / 12f); float l = WardNpcInstall.Skin(smr[0], inst).Min(p => p.y); lo = Mathf.Min(lo, l); hi = Mathf.Max(hi, l); }
                    workSoles[clip.name] = new[] { R(lo), R(hi) };
                    if (lo < -.05f || lo > .06f) failures.Add(s.key + $": {clip.name} lowest point {lo:F3} (feet sink or float)");
                }
                var (stride, strideInfo) = WardWalkerInstall.StrideSpeed(actor.walk, anim.gameObject, inst);
                if (Mathf.Abs(stride - actor.walkStrideSpeed) > actor.walkStrideSpeed * .12f) failures.Add(s.key + $": planted-foot speed {stride} differs from walkStrideSpeed {actor.walkStrideSpeed}");
                float rate = walker.speed / actor.walkStrideSpeed;
                if (rate < .6f || rate > 1.45f) failures.Add(s.key + ": playback rate " + rate + " outside 0.6-1.45");
                actor.walk.SampleAnimation(anim.gameObject, 0);
                // route data
                if (walker.waypoints.Length != r.points.Length || walker.waypoints.Select((w, i) => Vector3.Distance(w.position, P(r.points[i]))).Any(d => d > .01f)) failures.Add(s.key + ": waypoints differ from routes.json");
                if (walker.stops.Length != r.stops.Length || walker.stops.Any(x => x.waypoint < 0 || x.waypoint >= walker.waypoints.Length)) failures.Add(s.key + ": stops differ from routes.json or point outside the route");
                var clash = new HashSet<string>(); float npcMin = 99, groundMax = 0;
                for (int i = 0; i < walker.waypoints.Length; i++)
                {
                    Vector3 a = walker.waypoints[i].position, b = walker.waypoints[(i + 1) % walker.waypoints.Length].position;
                    int n = Mathf.Max(2, Mathf.CeilToInt(Vector3.Distance(a, b) / .2f));
                    for (int k = 0; k <= n; k++)
                    {
                        var p = Vector3.Lerp(a, b, k / (float)n);
                        foreach (var c in Touching(p)) clash.Add(c);
                        foreach (var npc in npcs) npcMin = Mathf.Min(npcMin, Vector2.Distance(new Vector2(p.x, p.z), new Vector2(npc.transform.position.x, npc.transform.position.z)));
                        if (Physics.Raycast(p + Vector3.up * 2, Vector3.down, out var hit, 4, ~0, QueryTriggerInteraction.Ignore) && !hit.transform.IsChildOf(top.transform)) groundMax = Mathf.Max(groundMax, Mathf.Abs(hit.point.y - p.y));
                    }
                }
                if (clash.Count > 0) failures.Add(s.key + ": route body capsule touches " + string.Join(", ", clash.Take(4)));
                if (npcMin < 3) failures.Add(s.key + $": route within {npcMin:F2} m of a talking colonist");
                // voice and glance
                var barker = wt.GetComponent<NpcBarker>();
                if (!barker || !barker.barks || barker.barks.speakerId != s.Speaker) failures.Add(s.key + ": NpcBarker missing or wrong set");
                else
                {
                    if (director && !director.speakers.Contains(barker)) failures.Add(s.key + ": barker not in BarkDirector.speakers");
                    if (barker.barks.lines.Any(l => !l.voice)) failures.Add(s.key + ": " + barker.barks.lines.Count(l => !l.voice) + " lines without a take");
                }
                var la = inst.GetComponent<ActorLookAt>(); if (!la) failures.Add(s.key + ": no ActorLookAt");
                if (!inst.GetComponentsInChildren<Transform>(true).Any(t => t.name == "Head")) failures.Add(s.key + ": rig has no Head bone");
                report[s.key] = new
                {
                    visual = PathOf(inst), linked, triangles = tris, lod1Triangles = smr.Length > 1 ? smr[1].sharedMesh.triangles.Length / 3 : 0, bones = smr[0].bones.Length,
                    clips = new { walk = actor.walk.name, idle = actor.idle.name, talk = actor.talk.name }, walkingHeight = R(hMax), soleRange = new[] { R(soleMin), R(soleMax) }, workClipLowest = workSoles,
                    walkStrideSpeed = R(actor.walkStrideSpeed, 3), measured = strideInfo, routeSpeed = walker.speed, playbackRate = R(rate, 3), playbackRateEasing = R(rate * walker.slowFactor, 3),
                    stops = walker.stops.Select(x => new { x.label, x.waypoint, x.seconds, x.facingYaw, x.talkClip }), routeClearance = clash.ToArray(), nearestTalkingColonist = R(npcMin, 2), groundOffsetMax = R(groundMax, 3),
                    barks = barker && barker.barks ? barker.barks.lines.Length : 0,
                };
            }
            var before = File.Exists(Evidence + "before.json") ? JToken.Parse(File.ReadAllText(Evidence + "before.json")) : null;
            var now = JToken.Parse(JsonConvert.SerializeObject(Snapshot(top)));
            File.WriteAllText(Evidence + "after.json", now.ToString(Formatting.Indented));
            bool same = before != null && JToken.DeepEquals(before, now);
            if (!same) failures.Add("existing walker snapshot differs from before.json (roots, routes, speeds, phases, turn settings, actors)");
            var cams = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(c => c.name.StartsWith("cam_res_")).Select(c => c.name).OrderBy(x => x).ToArray();
            int expectedCams = Specs.Sum(s => 3 + routes[s.route].stops.Length - 1);
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(c => c.name.StartsWith("cam_res_") && (c.name.EndsWith("_face") || c.name.EndsWith("_body") || c.name.EndsWith("_beside"))))
                if (!c.GetComponent<ResidentReviewCamera>() || !c.GetComponent<ResidentReviewCamera>().target) failures.Add(c.name + ": not following its resident");
            foreach (var s in Specs) if (!QaLandmark(s)) failures.Add("QA landmark " + LandmarkName(s) + " missing");
            if (cams.Length != expectedCams) failures.Add($"review cameras: {cams.Length}, expected {expectedCams}");
            var roster = new
            {
                actorAnimationsActive = Object.FindObjectsByType<ActorAnimation>(FindObjectsSortMode.None).Length,
                ambientWalkersActive = Object.FindObjectsByType<AmbientWalker>(FindObjectsSortMode.None).Length,
                talkingColonists = npcs.Length,
                barkSpeakers = director ? director.speakers.Count(x => x) : 0,
            };
            var result = new { ok = failures.Count == 0, failures, residents = report, existingWalkersUnchanged = same, cameras = cams, roster };
            File.WriteAllText(Evidence + "verify.json", JsonConvert.SerializeObject(result, Formatting.Indented));
            if (failures.Count > 0) throw new Exception("Verify failed: " + string.Join("; ", failures));
            return result;
        }

        // ------------------------------------------------------------------ rollback
        public static object Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var log = new List<string>(); var rec = LoadRecord();
            var top = FindRoot(SceneRoot);
            var director = Object.FindAnyObjectByType<GameSession>()?.GetComponent<BarkDirector>();
            if (top && director)
            {
                var ours = director.speakers.Where(x => x && x.transform.IsChildOf(top.transform)).ToArray();
                director.speakers = director.speakers.Where(x => x && !ours.Contains(x)).ToArray(); EditorUtility.SetDirty(director);
                log.Add("removed " + ours.Length + " resident barkers from BarkDirector.speakers");
            }
            if (top) { top.SetActive(false); log.Add(SceneRoot + " inactive"); }
            var cams = FindRoot(CameraRoot); if (cams) { cams.SetActive(false); log.Add(CameraRoot + " inactive"); }
            foreach (var s in Specs) { var l = QaLandmark(s); if (l) { l.gameObject.SetActive(false); log.Add(l.name + " inactive"); } }
            rec.log.Add(DateTime.UtcNow.ToString("u") + " rollback"); SaveRecord(rec);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return log;
        }

        // ------------------------------------------------------------------ editor captures (graphics, scene not saved)
        static void Light(float hour)
        {
            var clock = Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            if (!clock || !clock.profile) return;
            var f = clock.profile.Evaluate(hour);
            clock.keyLight.transform.rotation = Quaternion.Euler(f.keyEuler); clock.keyLight.color = f.keyColor; clock.keyLight.intensity = f.keyIntensity;
            if (clock.skyFill) { clock.skyFill.color = f.fillColor; clock.skyFill.intensity = f.fillIntensity; }
            RenderSettings.ambientMode = AmbientMode.Trilight; RenderSettings.ambientSkyColor = f.ambientSky; RenderSettings.ambientEquatorColor = f.ambientEquator; RenderSettings.ambientGroundColor = f.ambientGround; RenderSettings.fogColor = f.fogColor;
            var sky = new Material(clock.timeAwareSky);
            sky.SetColor("_Zenith", f.skyZenith); sky.SetColor("_Middle", f.skyMiddle); sky.SetColor("_Horizon", f.skyHorizon); sky.SetColor("_CloudLight", f.cloudLight); sky.SetColor("_CloudShade", f.cloudShade);
            sky.SetFloat("_Exposure", f.skyExposure); sky.SetFloat("_SunVisibility", f.sunVisibility); sky.SetVector("_SunDirection", -clock.keyLight.transform.forward);
            RenderSettings.skybox = sky; RenderSettings.sun = clock.keyLight;
            if (clock.gradingVolume && clock.gradingVolume.sharedProfile.TryGet<ColorAdjustments>(out var ca)) ca.postExposure.value = f.postExposure;
        }

        public static object Capture()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var argv = Environment.GetCommandLineArgs(); int hi = Array.IndexOf(argv, "--hour"), ci = Array.IndexOf(argv, "--cams");
            float hour = hi >= 0 ? float.Parse(argv[hi + 1], System.Globalization.CultureInfo.InvariantCulture) : 13;
            var routes = Routes();
            var wanted = ci >= 0 ? argv[ci + 1].Split(',') : Specs.SelectMany(s => new[] { "cam_res_" + s.title.ToLowerInvariant() + "_face", "cam_res_" + s.title.ToLowerInvariant() + "_body" }).ToArray();
            if (wanted.Length > 6) throw new Exception("At most six cameras per capture run");
            var outDir = Evidence + "captures/h" + hour.ToString("00.0", System.Globalization.CultureInfo.InvariantCulture).Replace(".", ""); Directory.CreateDirectory(outDir);
            Light(hour);
            var top = FindRoot(SceneRoot) ?? throw new Exception("Install first");
            var cams = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).GroupBy(c => c.name).ToDictionary(g => g.Key, g => g.First());
            var rt = new RenderTexture(1280, 960, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1 }; var tex = new Texture2D(1280, 960, TextureFormat.RGB24, false);
            var log = new List<string>();
            foreach (var name in wanted)
            {
                // pose the resident the camera concerns at that stop (face/body: the main stop), in its work clip
                var s = Specs.FirstOrDefault(x => name.StartsWith("cam_res_" + x.title.ToLowerInvariant() + "_")); if (s == null) { log.Add("not a resident camera " + name); continue; }
                var r = routes[s.route]; var stop = r.stops.FirstOrDefault(x => StopCamera(s, x) == name) ?? MainStop(r);
                var wt = top.transform.Find(s.root); var actor = wt.Find(s.Instance).GetComponent<ActorAnimation>();
                wt.SetPositionAndRotation(P(r.points[stop.waypoint]), Quaternion.Euler(0, stop.yaw, 0));
                foreach (var x in wt.GetComponentsInChildren<SkinnedMeshRenderer>(true)) x.forceMatrixRecalculationPerRender = true;
                var clip = stop.clip == "talk" ? actor.talk : actor.idle; clip.SampleAnimation(actor.animationSource.gameObject, clip.length * .35f);
                if (!cams.TryGetValue(name, out var src)) { log.Add("missing camera " + name); continue; }
                var go = new GameObject("__cap"); var cam = go.AddComponent<Camera>(); cam.CopyFrom(src); cam.enabled = false; cam.nearClipPlane = .05f; cam.farClipPlane = 650;
                var d = go.AddComponent<UniversalAdditionalCameraData>(); d.renderPostProcessing = true; d.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing; d.renderShadows = true; d.volumeLayerMask = ~0; d.volumeTrigger = go.transform;
                go.transform.SetPositionAndRotation(src.transform.position, src.transform.rotation);
                cam.targetTexture = rt; for (int i = 0; i < 3; i++) cam.Render();
                RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1280, 960), 0, 0); tex.Apply(); File.WriteAllBytes(Path.Combine(outDir, name + ".png"), tex.EncodeToPNG());
                RenderTexture.active = null; cam.targetTexture = null; Object.DestroyImmediate(go);
                log.Add($"{name} at {hour}: {s.title} at '{stop.label}' in {clip.name}");
            }
            rt.Release(); Object.DestroyImmediate(tex);
            File.WriteAllText(outDir + "/captures.txt", string.Join("\n", log) + "\n");
            return log;
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 ? args[i + 1].Split(',') : new[] { "verify" };
            try
            {
                var results = new Dictionary<string, object>();
                foreach (var st in steps)
                {
                    object result = st switch
                    {
                        "barks" => Barks(),
                        "simulate" => Simulate(),
                        "import" => Import(),
                        "prefab" => BuildPrefabs(),
                        "install" => Install(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        "capture" => Capture(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    results[st] = result;
                    Debug.Log("WardResidentsInstall20261120 " + st + ": " + JsonConvert.SerializeObject(result));
                }
                Directory.CreateDirectory(Evidence);
                string file = Evidence + "install-log.json";
                var all = File.Exists(file) ? JObject.Parse(File.ReadAllText(file)) : new JObject();
                foreach (var kv in results) all[kv.Key] = JToken.FromObject(kv.Value);
                File.WriteAllText(file, all.ToString(Formatting.Indented));
                Debug.Log("WardResidentsInstall20261120 OK");
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); Debug.Log("WardResidentsInstall20261120 FAILED: " + e.Message); EditorApplication.Exit(1); }
        }
    }
}
