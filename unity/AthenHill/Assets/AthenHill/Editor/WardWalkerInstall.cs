using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
    /// 3 October 2026 (art/ward_walkers_20261003, meshy/ward-walkers-20261003): three distinct Ward residents for the three
    /// ambient walkers that all used the supplied "weathered traveler" (Traveler.prefab):
    ///  * npc_walker_01 (east avenue lane from the West Gate): Daro, a Karaveen caravan porter with a pack frame;
    ///  * npc_walker_02 (north loop by the Quantum Tube goods node): Sel, a nanofabrication technician in a patched work coat;
    ///  * npc_walker_03 (south loop in the hall district): Anso, a hydroponics grower in a straw hat with a harvest satchel
    ///    of greens (part of the mesh; the Meshy "carry" walks are a shoulder carry and a bucket pick-up, not usable here).
    /// Same pipeline as <see cref="WardNpcInstall"/>: Codex concept sheet, Meshy multi-image-to-3D, Meshy rig (24 bones),
    /// Meshy library walk clip on that rig, prepare_unity.sh (smooth normals + re-baked normal map + LOD0 ~20k / LOD1 ~6-9k).
    ///
    /// Visuals only: every AmbientWalker (waypoints, speed, phase, turn settings) and walker root is kept; the old Traveler
    /// child is deactivated (rollback: <see cref="Rollback"/>) and AmbientWalker.actor repointed. The walk clip is made
    /// in place and its stride speed measured from the planted foot, so ActorAnimation plays it at speed / stride
    /// (no foot sliding at the authored route speed). The yard mechanic is not touched.
    ///
    /// Batch: unity.sh LOG AthenHill.Editor.WardWalkerInstall.RunBatch -nographics --steps import,prefab,install,verify
    ///        unity.sh LOG AthenHill.Editor.WardWalkerInstall.RunBatch --steps capture   (graphics; 6 cameras)
    /// </summary>
    public static class WardWalkerInstall
    {
        const string Record = "../../meshy/ward-walkers-20261003/";
        const string ArtRoot = "Assets/AthenHill/Art/Imported/Meshy/WardWalkers";
        const string PrefabRoot = "Assets/AthenHill/Prefabs/WardWalkers";
        const string TravelerPrefab = "Assets/AthenHill/Prefabs/Traveler.prefab";
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Evidence = "../evidence/ward-walkers/20261003/";
        const string CameraRoot = "Ward walker review cameras";

        public class Spec
        {
            public string key, title, walker, walk; public float height;
            public string Instance => "WardWalker " + title;
            public string Prefab => PrefabRoot + "/WardWalker_" + title + ".prefab";
            public string Folder => ArtRoot + "/" + title;
            public string Model => Folder + "/" + title + ".glb";
            public string Material => Folder + "/" + title + ".mat";
        }
        public static readonly Spec[] Specs = {
            new Spec{key="porter",   title="Daro", walker="npc_walker_01", height=1.78f, walk="walk_566"},   // Walking 2: 0.954 m/s root motion vs route 0.95 (Casual Walk 30: 0.73, rate 1.30)
            new Spec{key="nanotech", title="Sel",  walker="npc_walker_02", height=1.68f, walk="walk_566"},   // Walking 2: 0.903 vs route 1.05 (Walking Woman 1: 1.32, rate 0.80)
            new Spec{key="grower",   title="Anso", walker="npc_walker_03", height=1.80f, walk="walk_115"},   // Quick Walk: 1.262 planted vs route 1.15 (Walking 2: 0.96, rate 1.20)
        };

        public static float LodSwitch0 = .14f, LodCull = .012f;
        /// import/prefab steps only: --only porter,nanotech limits them to those walkers (install/verify always take all three).
        static IEnumerable<Spec> Selected()
        {
            var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, "--only"), w = Array.IndexOf(a, "--walk");
            // audition: --walk porter=basic_walking overrides a walker's clip for this run (stride comparison; the prefab is rebuilt with it)
            if (w >= 0) foreach (var kv in a[w + 1].Split(',').Select(x => x.Split('='))) Specs.Single(s => s.key == kv[0]).walk = kv[1];
            return i < 0 ? Specs : Specs.Where(s => a[i + 1].Split(',').Contains(s.key));
        }

        static float R(float v, int d = 4) => (float)Math.Round(v, d);
        static float[] V(Vector3 v) => new[] { R(v.x), R(v.y), R(v.z) };
        static string PathOf(Transform t) { var s = t.name; while (t.parent) { t = t.parent; s = t.name + "/" + s; } return s; }
        static string ClipPath(Spec s, string clip) => s.Folder + "/Clips/" + s.key + "_" + clip + ".anim";
        static Transform Bone(Component root, string name) => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == name) ?? throw new Exception("No bone " + name + " under " + root.name);

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
                Copy(Record + s.key + "/anim_only/" + s.walk + ".glb", s.Folder + "/Source/" + s.walk + ".glb");
                AssetDatabase.Refresh();
                foreach (var path in new[] { s.Model, s.Folder + "/Source/" + s.walk + ".glb" })
                {
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                    var importer = AssetImporter.GetAtPath(path); if (!importer) throw new Exception("No importer for " + path);
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

        // ------------------------------------------------------------------ walk clip
        /// In-place walk: Hips translation drift over the cycle removed (linear ramp), soles on y = 0, loop seam measured.
        /// Returns the derived clip report; the clip is written to <paramref name="target"/>.
        static object DeriveWalk(AnimationClip source, string target, GameObject host, SkinnedMeshRenderer smr, Transform root, Transform hips, out float rootSpeed)
        {
            var bindings = AnimationUtility.GetCurveBindings(source);
            bool IsHipsPos(EditorCurveBinding b) => (b.propertyName.StartsWith("m_LocalPosition") || b.propertyName.StartsWith("localPosition")) && (b.path == "Hips" || b.path.EndsWith("/Hips"));
            // drift of the Hips over one cycle in its parent's space
            var drift = Vector3.zero; float len = source.length;
            foreach (var b in bindings.Where(IsHipsPos))
            {
                var c = AnimationUtility.GetEditorCurve(source, b); float d = c.Evaluate(len) - c.Evaluate(0);
                if (b.propertyName.EndsWith(".x")) drift.x = d; else if (b.propertyName.EndsWith(".y")) drift.y = d; else drift.z = d;
            }
            var driftRoot = root.InverseTransformVector(hips.parent.TransformVector(drift));
            rootSpeed = new Vector2(driftRoot.x, driftRoot.z).magnitude / Mathf.Max(.001f, len);
            var clip = new AnimationClip { name = Path.GetFileNameWithoutExtension(target), legacy = true, frameRate = source.frameRate, wrapMode = WrapMode.Loop };
            int kept = 0, dropped = 0, hipsCurves = 0; float seam = 0;
            foreach (var b in bindings)
            {
                string prop = b.propertyName;
                bool rotation = prop.StartsWith("m_LocalRotation") || prop.StartsWith("localRotation");
                bool hp = IsHipsPos(b);
                if (!rotation && !hp) { dropped++; continue; }
                var curve = AnimationUtility.GetEditorCurve(source, b);
                if (hp)
                {
                    // remove the linear drift (a looping cycle returns to its start height, so this only removes travel)
                    float d = prop.EndsWith(".x") ? drift.x : prop.EndsWith(".y") ? drift.y : drift.z;
                    var keys = curve.keys; for (int i = 0; i < keys.Length; i++) keys[i].value -= d * (keys[i].time / Mathf.Max(.001f, len)); curve.keys = keys;
                    hipsCurves++;
                }
                // close small seams only: a large jump on a rotation component is a quaternion sign flip (same rotation)
                if (curve.length > 2 && Mathf.Abs(curve.keys[curve.length - 1].value - curve.keys[0].value) < .3f) seam = Mathf.Max(seam, CloseLoop(curve, LoopBlendSeconds));
                clip.SetCurve(b.path, typeof(Transform), prop.Replace("m_LocalRotation", "localRotation").Replace("m_LocalPosition", "localPosition"), curve);
                kept++;
            }
            if (hipsCurves != 3) throw new Exception("Expected Hips x/y/z translation curves in " + source.name + ", found " + hipsCurves);
            clip.EnsureQuaternionContinuity();
            // soles: lowest skinned vertex over the cycle -> y 0 (shift the Hips curves)
            float low = float.MaxValue;
            for (int k = 0; k < 24; k++) { clip.SampleAnimation(host, clip.length * k / 24f); low = Mathf.Min(low, WardNpcInstall.Skin(smr, root).Min(p => p.y)); }
            var lift = hips.parent.InverseTransformVector(root.TransformVector(new Vector3(0, -low, 0)));
            foreach (var b in AnimationUtility.GetCurveBindings(clip).Where(IsHipsPos))
            {
                var c = AnimationUtility.GetEditorCurve(clip, b); float add = b.propertyName.EndsWith(".x") ? lift.x : b.propertyName.EndsWith(".y") ? lift.y : lift.z;
                var keys = c.keys; for (int i = 0; i < keys.Length; i++) keys[i].value += add; c.keys = keys;
                AnimationUtility.SetEditorCurve(clip, b, c);
            }
            var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(target);
            if (existing) { EditorUtility.CopySerialized(clip, existing); Object.DestroyImmediate(clip); EditorUtility.SetDirty(existing); }
            else AssetDatabase.CreateAsset(clip, target);
            return new { target, length = R(source.length, 3), frameRate = source.frameRate, curvesKept = kept, curvesDropped = dropped, maxLoopSeam = R(seam), hipsDriftRoot = V(driftRoot), rootMotionSpeed = R(driftRoot.magnitude / Mathf.Max(.001f, len), 3), soleLift = R(-low) };
        }

        /// Blends the last <paramref name="seconds"/> of a curve onto its first key so the loop has no pop; returns the seam it closed.
        static float CloseLoop(AnimationCurve curve, float seconds)
        {
            var keys = curve.keys; float end = keys[keys.Length - 1].time, start = keys[0].time;
            float seam = Mathf.Abs(keys[keys.Length - 1].value - keys[0].value);
            if (seam < 1e-4f) return seam;
            seconds = Mathf.Min(seconds, (end - start) * .15f);
            for (int i = 0; i < keys.Length; i++)
            {
                float w = Mathf.InverseLerp(end - seconds, end, keys[i].time); if (w <= 0) continue;
                w = w * w * (3 - 2 * w); keys[i].value = Mathf.Lerp(keys[i].value, keys[0].value, w);
            }
            curve.keys = keys;
            return seam;
        }
        public static float LoopBlendSeconds = .12f;

        /// Ground speed the in-place clip implies: the backward speed of each foot while it is planted (lowest 3 cm of its
        /// travel), median over the cycle, in prefab space (character faces +Z). Also the stride length and cadence.
        public static (float speed, object info) StrideSpeed(AnimationClip clip, GameObject host, Transform root)
        {
            int n = 90; float dt = clip.length / n;
            var feet = new[] { "LeftFoot", "RightFoot" }.Select(f => Bone(host.transform, f)).ToArray();
            var pos = feet.Select(_ => new Vector3[n + 1]).ToArray();
            for (int k = 0; k <= n; k++) { clip.SampleAnimation(host, dt * k); for (int f = 0; f < 2; f++) pos[f][k] = root.InverseTransformPoint(feet[f].position); }
            var v = new List<float>(); float strideMax = 0;
            for (int f = 0; f < 2; f++)
            {
                float lo = pos[f].Min(p => p.y);
                for (int k = 0; k < n; k++)
                    if (pos[f][k].y < lo + .03f && pos[f][k + 1].y < lo + .03f) v.Add(-(pos[f][k + 1].z - pos[f][k].z) / dt);
                strideMax = Mathf.Max(strideMax, pos[f].Max(p => p.z) - pos[f].Min(p => p.z));
            }
            if (v.Count < 6) throw new Exception("Too few planted-foot samples in " + clip.name + ": " + v.Count);
            v.Sort(); float median = v[v.Count / 2];
            return (median, new { plantedSamples = v.Count, medianSpeed = R(median, 3), p25 = R(v[v.Count / 4], 3), p75 = R(v[v.Count * 3 / 4], 3), footTravelZ = R(strideMax, 3), cycleSeconds = R(clip.length, 3) });
        }

        static AnimationClip StaticPose(AnimationClip walk, GameObject host, string target, float at)
        {
            var clip = new AnimationClip { name = Path.GetFileNameWithoutExtension(target), legacy = true, wrapMode = WrapMode.Loop };
            foreach (var b in AnimationUtility.GetCurveBindings(walk))
            {
                float value = AnimationUtility.GetEditorCurve(walk, b).Evaluate(walk.length * at);
                clip.SetCurve(b.path, typeof(Transform), b.propertyName, AnimationCurve.Constant(0, 1, value));
            }
            clip.EnsureQuaternionContinuity();
            var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(target);
            if (existing) { EditorUtility.CopySerialized(clip, existing); Object.DestroyImmediate(clip); EditorUtility.SetDirty(existing); return existing; }
            AssetDatabase.CreateAsset(clip, target); return clip;
        }

        static Bounds PoseBounds(SkinnedMeshRenderer r, GameObject host, AnimationClip clip)
        {
            var space = r.rootBone ? r.rootBone : r.transform; bool any = false; var b = new Bounds();
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
                var root = new GameObject("WardWalker_" + s.title);
                try
                {
                    var visual = new GameObject("Visual").transform; visual.SetParent(root.transform, false);
                    var rig = (GameObject)PrefabUtility.InstantiatePrefab(model); rig.transform.SetParent(visual, false);
                    var smrs = rig.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                    var smr = smrs.FirstOrDefault(r => r.name == "char1") ?? throw new Exception(s.key + ": no char1 (LOD0) renderer");
                    var lod1 = smrs.FirstOrDefault(r => r.name == "char1_lod1") ?? throw new Exception(s.key + ": no char1_lod1 (LOD1) renderer");
                    if (smrs.Length != 2) throw new Exception(s.key + ": expected LOD0 + LOD1, found " + smrs.Length);
                    var source = AssetDatabase.LoadAllAssetsAtPath(s.Folder + "/Source/" + s.walk + ".glb").OfType<AnimationClip>().FirstOrDefault(c => c && c.legacy) ?? throw new Exception("No legacy walk clip " + s.key);
                    // clip paths resolve from the rig root (glTFast makes the armature the instance root: rename it as needed)
                    var paths = AnimationUtility.GetCurveBindings(source).Select(b => b.path).Distinct().ToArray();
                    bool All(Transform t) => paths.All(p => p.Length == 0 || t.Find(p) != null);
                    Transform host = rig.GetComponentsInChildren<Transform>(true).Prepend(visual).FirstOrDefault(All);
                    if (!host)
                    {
                        var first = paths.Select(p => p.Split('/')[0]).Distinct().ToArray();
                        if (first.Length == 1) { log.Add("instance root renamed '" + rig.name + "' -> '" + first[0] + "'"); rig.name = first[0]; }
                        host = All(visual) ? visual : throw new Exception("Walk clip paths do not resolve: " + string.Join(", ", paths.Take(4)));
                    }
                    log.Add("clip paths resolve from '" + host.name + "'");
                    var anim = host.GetComponent<Animation>(); if (!anim) anim = host.gameObject.AddComponent<Animation>();
                    foreach (var other in rig.GetComponentsInChildren<Animation>(true).Concat(visual.GetComponents<Animation>()).ToArray()) if (other != anim) Object.DestroyImmediate(other);

                    // height from the bind (A-)pose, uniform scale
                    var rest = WardNpcInstall.Skin(smr, root.transform);
                    float standing = rest.Max(p => p.y) - rest.Min(p => p.y), scale = s.height / standing;
                    visual.localScale = Vector3.one * scale;
                    log.Add($"rest height {standing:F4} at import scale; uniform scale {scale:F4} -> {s.height} m");
                    var head = Bone(host, "Head");
                    var front = host.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "headfront");
                    if (front)
                    {
                        var d = root.transform.InverseTransformPoint(front.position) - root.transform.InverseTransformPoint(head.position);
                        if (d.z < 0) { visual.localRotation = Quaternion.Euler(0, 180, 0); log.Add("visual turned 180 degrees to face +Z"); }
                    }
                    var hips = Bone(host, "Hips");
                    var derived = DeriveWalk(source, ClipPath(s, s.walk), host.gameObject, smr, root.transform, hips, out float rootSpeed);
                    AssetDatabase.SaveAssets();
                    var walk = AssetDatabase.LoadAssetAtPath<AnimationClip>(ClipPath(s, s.walk));
                    var (planted, strideInfo) = StrideSpeed(walk, host.gameObject, root.transform);
                    // a clip authored with root motion states its own ground speed (the planted foot was fixed in the source);
                    // an in-place clip's speed is the planted foot's backward speed
                    float stride = rootSpeed > .3f ? rootSpeed : planted;
                    if (stride < .5f || stride > 2.2f) throw new Exception(s.key + ": implausible stride speed " + stride);
                    var idle = StaticPose(walk, host.gameObject, ClipPath(s, "pose"), 0);

                    var src = smr.sharedMaterial;
                    if (!src || !src.shader || src.shader.name.Contains("Error")) throw new Exception(s.key + ": material failed to import");
                    var mat = AssetDatabase.LoadAssetAtPath<Material>(s.Material);
                    if (!mat) { mat = new Material(src) { name = s.title }; AssetDatabase.CreateAsset(mat, s.Material); log.Add("material created from " + src.shader.name); }
                    var boundsInfo = new List<object>();
                    foreach (var r in new[] { smr, lod1 })
                    {
                        r.sharedMaterial = mat;
                        r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true; r.updateWhenOffscreen = false;
                        r.localBounds = PoseBounds(r, host.gameObject, walk);
                        boundsInfo.Add(new { r.name, centre = V(r.localBounds.center), size = V(r.localBounds.size), space = r.rootBone ? r.rootBone.name : r.name });
                    }
                    var lodGroup = visual.gameObject.AddComponent<LODGroup>();
                    lodGroup.SetLODs(new[] { new LOD(LodSwitch0, new Renderer[] { smr }), new LOD(LodCull, new Renderer[] { lod1 }) });
                    lodGroup.RecalculateBounds();
                    log.Add($"LODGroup: LOD0 {smr.sharedMesh.triangles.Length / 3} tris above {LodSwitch0}, LOD1 {lod1.sharedMesh.triangles.Length / 3} tris above {LodCull}, culled below");

                    anim.playAutomatically = false; anim.clip = walk; anim.cullingType = AnimationCullingType.BasedOnRenderers;
                    AnimationUtility.SetAnimationClips(anim, new[] { walk, idle });
                    var actor = root.AddComponent<ActorAnimation>();
                    actor.animationSource = anim; actor.idle = idle; actor.walk = walk; actor.run = walk; actor.talk = idle;   // ambient walkers never stop, run or talk
                    actor.walkStrideSpeed = actor.runStrideSpeed = stride;
                    actor.randomIdlePhase = true; actor.idleSpeedJitter = 0;
                    walk.SampleAnimation(host.gameObject, 0);
                    var prefab = PrefabUtility.SaveAsPrefabAsset(root, s.Prefab, out bool ok);
                    if (!ok || !prefab) throw new Exception("Prefab save failed: " + s.Prefab);
                    all[s.key] = new { prefab = s.Prefab, scale = R(scale), host = host.name, log, walk = derived, stride = strideInfo, walkStrideSpeed = R(stride, 3), strideSource = rootSpeed > .3f ? "root motion" : "planted foot", bounds = boundsInfo };
                }
                finally { Object.DestroyImmediate(root); }
            }
            AssetDatabase.SaveAssets();
            return all;
        }

        // ------------------------------------------------------------------ scene install
        static AmbientWalker Walker(Spec s) => Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None)
            .SingleOrDefault(w => w.name == s.walker) ?? throw new Exception("No AmbientWalker " + s.walker);

        static GameObject OldVisual(AmbientWalker w) => w.transform.Cast<Transform>().FirstOrDefault(t => t.name == "Traveler" && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(t.gameObject) == TravelerPrefab)?.gameObject
            ?? throw new Exception(w.name + ": no Traveler child visual");

        static object Snapshot() => Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None).OrderBy(w => PathOf(w.transform), StringComparer.Ordinal).Select(w => new
        {
            path = PathOf(w.transform), active = w.gameObject.activeSelf, w.speed, w.phase, w.turnLookAhead, w.turnSharpness,
            position = V(w.transform.position), rotation = V(w.transform.eulerAngles),
            waypoints = w.waypoints.Select(p => p ? PathOf(p) + "@" + string.Join(",", V(p.position)) : "null").ToArray(),
            colliders = w.GetComponentsInChildren<Collider>(true).Where(c => c.enabled && c.gameObject.activeInHierarchy).Select(c => c.GetType().Name + "@" + c.name).OrderBy(x => x).ToArray(),
        }).ToArray();

        public static object Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Directory.CreateDirectory(Evidence);
            string beforeFile = Evidence + "before.json";
            if (!File.Exists(beforeFile)) File.WriteAllText(beforeFile, JsonConvert.SerializeObject(Snapshot(), Formatting.Indented));
            var report = new Dictionary<string, object>();
            foreach (var s in Specs)
            {
                var w = Walker(s);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(s.Prefab) ?? throw new Exception("Run the prefab step first: " + s.Prefab);
                var old = OldVisual(w);
                if (old.activeSelf) { old.SetActive(false); EditorUtility.SetDirty(old); }
                var inst = w.transform.Cast<Transform>().FirstOrDefault(t => t.name == s.Instance)?.gameObject;
                if (inst && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst) != s.Prefab) { Object.DestroyImmediate(inst); inst = null; }
                bool created = !inst;
                if (!inst) { inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene); inst.name = s.Instance; inst.transform.SetParent(w.transform, false); }
                inst.SetActive(true);
                inst.transform.localPosition = old.transform.localPosition; inst.transform.localRotation = old.transform.localRotation;
                var ps = w.transform.lossyScale; inst.transform.localScale = new Vector3(1 / ps.x, 1 / ps.y, 1 / ps.z);
                Undo.RecordObject(w, "Ward walker visual"); w.actor = inst.GetComponent<ActorAnimation>(); EditorUtility.SetDirty(w);
                w.actor.walk.SampleAnimation(w.actor.animationSource.gameObject, 0);
                report[s.key] = new { walker = PathOf(w.transform), created, deactivated = PathOf(old.transform), visual = PathOf(inst.transform), localScale = V(inst.transform.localScale), w.speed, stride = w.actor.walkStrideSpeed, playbackRate = R(w.speed / w.actor.walkStrideSpeed, 3) };
            }
            report["cameras"] = Cameras();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            return report;
        }

        /// Review pose: the middle of the walker's longest route segment, facing along it.
        public static (Vector3 pos, Vector3 fwd) ReviewPose(AmbientWalker w)
        {
            var p = w.waypoints.Select(t => t.position).ToArray(); int best = 0; float bl = -1;
            for (int i = 0; i < p.Length; i++) { float l = Vector3.Distance(p[i], p[(i + 1) % p.Length]); if (l > bl) { bl = l; best = i; } }
            var a = p[best]; var b = p[(best + 1) % p.Length];
            return ((a + b) * .5f, Vector3.ProjectOnPlane(b - a, Vector3.up).normalized);
        }

        static string Cameras()
        {
            var scene = EditorSceneManager.GetActiveScene(); Physics.SyncTransforms();
            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == CameraRoot).ToArray()) Object.DestroyImmediate(old);
            var root = new GameObject(CameraRoot);
            var template = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(c => c.name == "cam_checkpoint_player");
            var names = new List<string>();
            var walkers = Specs.Select(Walker).Select(x => x.transform).ToArray();
            void Cam(string name, Vector3 pos, Vector3 look, float fov)
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                var cam = go.AddComponent<Camera>(); if (template) cam.CopyFrom(template); cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f;
                var dir = pos - look;
                foreach (var hit in Physics.RaycastAll(look, dir.normalized, dir.magnitude, ~0, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance))
                {
                    if (walkers.Any(r => hit.transform.IsChildOf(r))) continue;
                    pos = look + dir.normalized * Mathf.Max(.45f, hit.distance - .15f); break;
                }
                go.transform.position = pos; go.transform.LookAt(look); names.Add(name);
            }
            foreach (var s in Specs)
            {
                var (feet, f) = ReviewPose(Walker(s)); var right = Vector3.Cross(Vector3.up, f); float h = s.height;
                Cam("cam_walkers_" + s.key + "_face", feet + f * 1.15f + right * .2f + Vector3.up * (h * .93f), feet + Vector3.up * (h * .925f), 30);
                Cam("cam_walkers_" + s.key + "_body", feet + f * 3.4f + right * 1.1f + Vector3.up * 1.6f, feet + Vector3.up * (h * .5f), 42);
            }
            return string.Join(", ", names);
        }

        // ------------------------------------------------------------------ verify (-nographics)
        public static object Verify()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var failures = new List<string>(); var report = new Dictionary<string, object>();
            foreach (var s in Specs)
            {
                var w = Walker(s); var inst = w.transform.Find(s.Instance);
                if (!inst) { failures.Add(s.key + ": visual missing"); continue; }
                bool linked = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst.gameObject) == s.Prefab && PrefabUtility.IsAnyPrefabInstanceRoot(inst.gameObject);
                if (!linked) failures.Add(s.key + ": prefab link broken");
                if (!inst.gameObject.activeInHierarchy) failures.Add(s.key + ": visual inactive");
                var actor = inst.GetComponent<ActorAnimation>();
                if (w.actor != actor) failures.Add(s.key + ": AmbientWalker.actor is not the new visual");
                var old = OldVisual(w); if (old.activeSelf) failures.Add(s.key + ": old Traveler still active");
                var smr = inst.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(r => r.sharedMesh.triangles.Length).ToArray();
                if (smr.Any(r => r.updateWhenOffscreen)) failures.Add(s.key + ": updateWhenOffscreen on");
                if (!inst.GetComponentInChildren<LODGroup>()) failures.Add(s.key + ": no LODGroup");
                var anim = actor.animationSource;
                if (anim.cullingType != AnimationCullingType.BasedOnRenderers) failures.Add(s.key + ": Animation culling not BasedOnRenderers");
                foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                    foreach (var m in r.sharedMaterials)
                        if (!m || !m.shader || m.shader.name.Contains("Error") || m.shader.name == "Hidden/InternalErrorShader") failures.Add(s.key + ": missing/broken material on " + r.name);
                int missingScripts = inst.GetComponentsInChildren<Component>(true).Count(c => c == null);
                if (missingScripts > 0) failures.Add(s.key + ": " + missingScripts + " missing scripts");
                if (inst.GetComponentsInChildren<Collider>(true).Length > 0) failures.Add(s.key + ": colliders on the moving visual");
                int unresolved = AnimationUtility.GetCurveBindings(actor.walk).Count(b => b.path.Length > 0 && !anim.transform.Find(b.path));
                if (unresolved > 0) failures.Add(s.key + ": " + unresolved + " unresolved walk paths");
                if (smr[0].sharedMesh.triangles.Length / 3 > 21000) failures.Add(s.key + ": LOD0 over 21k triangles");
                // height / soles across the cycle, stride, playback rate
                float hMax = 0, soleMin = 1, soleMax = -1;
                for (int k = 0; k < 12; k++)
                {
                    actor.walk.SampleAnimation(anim.gameObject, actor.walk.length * k / 12f);
                    var pts = WardNpcInstall.Skin(smr[0], inst); float lo = pts.Min(p => p.y);
                    hMax = Mathf.Max(hMax, pts.Max(p => p.y) - lo); soleMin = Mathf.Min(soleMin, lo); soleMax = Mathf.Max(soleMax, lo);
                }
                if (Mathf.Abs(soleMin) > .02f) failures.Add(s.key + ": lowest sole off the ground " + soleMin);
                if (hMax > s.height + .12f || hMax < s.height - .25f) failures.Add(s.key + ": walking height " + hMax);
                var (stride, strideInfo) = StrideSpeed(actor.walk, anim.gameObject, inst);
                if (Mathf.Abs(stride - actor.walkStrideSpeed) > actor.walkStrideSpeed * .12f) failures.Add(s.key + $": planted-foot speed {stride} differs from walkStrideSpeed {actor.walkStrideSpeed} by more than 12 %");
                float rate = w.speed / actor.walkStrideSpeed;
                if (rate < .7f || rate > 1.45f) failures.Add(s.key + ": playback rate " + rate + " outside 0.7-1.45");
                actor.walk.SampleAnimation(anim.gameObject, 0);
                report[s.key] = new
                {
                    visual = PathOf(inst), linked, triangles = smr[0].sharedMesh.triangles.Length / 3, lod1Triangles = smr.Length > 1 ? smr[1].sharedMesh.triangles.Length / 3 : 0,
                    bones = smr[0].bones.Length, walk = actor.walk.name, walkingHeight = R(hMax), soleRange = new[] { R(soleMin), R(soleMax) },
                    walkStrideSpeed = R(actor.walkStrideSpeed, 3), measured = strideInfo, routeSpeed = w.speed, playbackRate = R(rate, 3),
                    material = smr[0].sharedMaterial.name + " / " + smr[0].sharedMaterial.shader.name,
                };
            }
            var before = File.Exists(Evidence + "before.json") ? JToken.Parse(File.ReadAllText(Evidence + "before.json")) : null;
            var now = JToken.Parse(JsonConvert.SerializeObject(Snapshot()));
            File.WriteAllText(Evidence + "after.json", now.ToString(Formatting.Indented));
            bool same = before != null && JToken.DeepEquals(before, now);
            if (!same) failures.Add("walker snapshot differs from before.json (roots, routes, speeds, phases, colliders)");
            // the yard mechanic and talking NPCs untouched
            var mech = Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None).Single(x => x.name == "npc_yard_mechanic");
            if (!mech.actor || PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(mech.actor.gameObject) != "Assets/AthenHill/Prefabs/YardMechanic.prefab") failures.Add("yard mechanic actor changed");
            var cams = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(c => c.name.StartsWith("cam_walkers_")).Select(c => c.name).OrderBy(x => x).ToArray();
            if (cams.Length != Specs.Length * 2) failures.Add("review cameras: " + cams.Length);
            var result = new { ok = failures.Count == 0, failures, walkers = report, walkerSnapshotUnchanged = same, cameras = cams };
            File.WriteAllText(Evidence + "verify.json", JsonConvert.SerializeObject(result, Formatting.Indented));
            if (failures.Count > 0) throw new Exception("Verify failed: " + string.Join("; ", failures));
            return result;
        }

        // ------------------------------------------------------------------ rollback
        /// Reactivates the Traveler visuals and repoints AmbientWalker.actor; the new instances go inactive, prefabs stay.
        public static object Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var log = new List<string>();
            foreach (var s in Specs)
            {
                var w = Walker(s); var old = OldVisual(w); old.SetActive(true);
                var inst = w.transform.Find(s.Instance); if (inst) inst.gameObject.SetActive(false);
                w.actor = old.GetComponent<ActorAnimation>(); EditorUtility.SetDirty(w);
                log.Add(s.walker + " -> " + PathOf(old.transform));
            }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return log;
        }

        // ------------------------------------------------------------------ editor captures (graphics, scene not saved)
        public static object Capture()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            // diagnostics: --forcelod N renders that LOD only (captures-lodN), --keys porter,grower limits the walkers
            var argv = Environment.GetCommandLineArgs(); int fl = Array.IndexOf(argv, "--forcelod"), ki = Array.IndexOf(argv, "--keys");
            int forceLod = fl >= 0 ? int.Parse(argv[fl + 1]) : -1; var keys = ki >= 0 ? argv[ki + 1].Split(',') : null;
            bool noNormal = argv.Contains("--nonormal"), restPose = argv.Contains("--rest"), noShadow = argv.Contains("--noshadow"), plainLit = argv.Contains("--plainlit"), noLod1 = argv.Contains("--nolod1"), bake = argv.Contains("--bake"); int mb = Array.IndexOf(argv, "--mipbias");
            if (mb >= 0) foreach (var sp in Specs) { var m = AssetDatabase.LoadAssetAtPath<Material>(sp.Material); foreach (var n in m.GetTexturePropertyNames()) { var t = m.GetTexture(n); if (t) t.mipMapBias = float.Parse(argv[mb + 1], System.Globalization.CultureInfo.InvariantCulture); } }   // diagnostics: normal map off / bind pose
            var outDir = Evidence + (forceLod >= 0 ? "captures-lod" + forceLod : noNormal ? "captures-nonormal" : noShadow ? "captures-noshadow" : plainLit ? "captures-plainlit" : noLod1 ? "captures-nolod1" : bake ? "captures-bake" : mb >= 0 ? "captures-mipbias" : restPose ? "captures-rest" : "captures"); Directory.CreateDirectory(outDir);
            var clock = Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            if (clock && clock.profile)
            {
                var f = clock.profile.Evaluate(13f);
                clock.keyLight.transform.rotation = Quaternion.Euler(f.keyEuler); clock.keyLight.color = f.keyColor; clock.keyLight.intensity = f.keyIntensity;
                if (clock.skyFill) { clock.skyFill.color = f.fillColor; clock.skyFill.intensity = f.fillIntensity; }
                RenderSettings.ambientMode = AmbientMode.Trilight; RenderSettings.ambientSkyColor = f.ambientSky; RenderSettings.ambientEquatorColor = f.ambientEquator; RenderSettings.ambientGroundColor = f.ambientGround; RenderSettings.fogColor = f.fogColor;
                var sky = new Material(clock.timeAwareSky);
                sky.SetColor("_Zenith", f.skyZenith); sky.SetColor("_Middle", f.skyMiddle); sky.SetColor("_Horizon", f.skyHorizon); sky.SetColor("_CloudLight", f.cloudLight); sky.SetColor("_CloudShade", f.cloudShade);
                sky.SetFloat("_Exposure", f.skyExposure); sky.SetFloat("_SunVisibility", f.sunVisibility); sky.SetVector("_SunDirection", -clock.keyLight.transform.forward);
                RenderSettings.skybox = sky; RenderSettings.sun = clock.keyLight;
                if (clock.gradingVolume && clock.gradingVolume.sharedProfile.TryGet<ColorAdjustments>(out var ca)) ca.postExposure.value = f.postExposure;
            }
            var cams = Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).GroupBy(c => c.name).ToDictionary(g => g.Key, g => g.First());
            var rt = new RenderTexture(1280, 960, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1 }; var tex = new Texture2D(1280, 960, TextureFormat.RGB24, false);
            var log = new List<string>();
            void Shot(string camName, string file)
            {
                if (!cams.TryGetValue(camName, out var src)) { log.Add("missing camera " + camName); return; }
                var go = new GameObject("__cap"); var cam = go.AddComponent<Camera>(); cam.CopyFrom(src); cam.enabled = false; cam.nearClipPlane = .05f; cam.farClipPlane = 650;
                var d = go.AddComponent<UniversalAdditionalCameraData>(); d.renderPostProcessing = true; d.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing; d.renderShadows = true; d.volumeLayerMask = ~0; d.volumeTrigger = go.transform;
                go.transform.SetPositionAndRotation(src.transform.position, src.transform.rotation);
                cam.targetTexture = rt; for (int i = 0; i < 3; i++) cam.Render();
                RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1280, 960), 0, 0); tex.Apply(); File.WriteAllBytes(Path.Combine(outDir, file + ".png"), tex.EncodeToPNG());
                RenderTexture.active = null; cam.targetTexture = null; Object.DestroyImmediate(go); log.Add(file + " from " + camName);
            }
            foreach (var s in Specs.Where(x => keys == null || keys.Contains(x.key)))
            {
                var w = Walker(s); var (pos, fwd) = ReviewPose(w);
                w.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(fwd, Vector3.up));
                var inst = w.transform.Find(s.Instance).gameObject; var actor = inst.GetComponent<ActorAnimation>();
                foreach (var x in inst.GetComponentsInChildren<SkinnedMeshRenderer>(true)) x.forceMatrixRecalculationPerRender = true;
                var lodGroup = inst.GetComponentInChildren<LODGroup>(); if (forceLod >= 0) lodGroup.ForceLOD(forceLod);
                if (noLod1) { foreach (var x in inst.GetComponentsInChildren<SkinnedMeshRenderer>(true)) if (x.name == "char1_lod1") x.gameObject.SetActive(false); lodGroup.enabled = false; }
                if (plainLit) foreach (var x in inst.GetComponentsInChildren<SkinnedMeshRenderer>(true)) { var c = new Material(Shader.Find("Universal Render Pipeline/Lit")); c.SetTexture("_BaseMap", x.sharedMaterial.GetTexture("baseColorTexture")); c.SetFloat("_Smoothness", .3f); c.SetFloat("_Metallic", 0); x.sharedMaterial = c; }
                if (noShadow) foreach (var x in inst.GetComponentsInChildren<SkinnedMeshRenderer>(true)) x.receiveShadows = false;
                if (noNormal) foreach (var x in inst.GetComponentsInChildren<SkinnedMeshRenderer>(true)) { var m = new Material(x.sharedMaterial); m.SetTexture("normalTexture", null); m.DisableKeyword("_NORMALMAP"); x.sharedMaterial = m; }
                log.Add($"{s.key}: lodBias {QualitySettings.lodBias}, quality level {QualitySettings.GetQualityLevel()} ({QualitySettings.names[QualitySettings.GetQualityLevel()]}), LODGroup size {lodGroup.size:F3}, forceLod {forceLod}");
                if (!restPose) actor.walk.SampleAnimation(actor.animationSource.gameObject, actor.walk.length * .3f);
                var baked = new List<GameObject>();
                if (bake) foreach (var x in inst.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.name == "char1"))
                {
                    var mesh = new Mesh(); x.BakeMesh(mesh, false); mesh.RecalculateTangents();
                    var g = new GameObject("__baked", typeof(MeshFilter), typeof(MeshRenderer)); g.transform.SetParent(x.transform, false);
                    g.GetComponent<MeshFilter>().sharedMesh = mesh; g.GetComponent<MeshRenderer>().sharedMaterials = x.sharedMaterials; baked.Add(g);
                    foreach (var y in inst.GetComponentsInChildren<SkinnedMeshRenderer>(true)) y.enabled = false;
                }
                Shot("cam_walkers_" + s.key + "_face", s.key + "_face");
                foreach (var g in baked) Object.DestroyImmediate(g);
                actor.walk.SampleAnimation(actor.animationSource.gameObject, actor.walk.length * .55f);
                Shot("cam_walkers_" + s.key + "_body", s.key + "_body");
            }
            rt.Release(); Object.DestroyImmediate(tex);
            File.WriteAllText(outDir + "/captures.txt", string.Join("\n", log) + "\n");
            return log;
        }

        /// Diagnostic (-nographics): the LOD0 skinned at walk 30 % baked to OBJ (positions, normals, UVs) for an offline render.
        public static object DumpMesh()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); var log = new List<string>();
            foreach (var s in Specs)
            {
                var inst = Walker(s).transform.Find(s.Instance); var actor = inst.GetComponent<ActorAnimation>();
                var smr = inst.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(r => r.name == "char1");
                actor.walk.SampleAnimation(actor.animationSource.gameObject, actor.walk.length * .3f);
                var m = new Mesh(); smr.BakeMesh(m, true);
                var sb = new System.Text.StringBuilder();
                foreach (var v in m.vertices) sb.AppendFormat(System.Globalization.CultureInfo.InvariantCulture, "v {0} {1} {2}\n", -v.x, v.y, v.z);
                foreach (var v in m.normals) sb.AppendFormat(System.Globalization.CultureInfo.InvariantCulture, "vn {0} {1} {2}\n", -v.x, v.y, v.z);
                foreach (var v in m.uv) sb.AppendFormat(System.Globalization.CultureInfo.InvariantCulture, "vt {0} {1}\n", v.x, v.y);
                var t = m.triangles; for (int i = 0; i < t.Length; i += 3) sb.AppendFormat("f {0}/{0}/{0} {2}/{2}/{2} {1}/{1}/{1}\n", t[i] + 1, t[i + 1] + 1, t[i + 2] + 1);
                File.WriteAllText(Evidence + "dump_" + s.key + ".obj", sb.ToString());
                log.Add($"{s.key}: {m.vertexCount} verts, {t.Length / 3} tris, uv {m.uv.Length}, normals {m.normals.Length}, tangents {m.tangents.Length}; source mesh verts {smr.sharedMesh.vertexCount}, index format {smr.sharedMesh.indexFormat}, submeshes {smr.sharedMesh.subMeshCount}");
            }
            return log;
        }

        /// Diagnostic (-nographics): how rigidly the face follows the Head bone during the walk. For vertices above the neck
        /// that are in front of the head bone, the spread (max - min over 12 samples) of their Head-local position, in metres.
        /// Also run on the WardNpc prefabs' idles for comparison.
        public static object FaceCheck()
        {
            var res = new Dictionary<string, object>();
            void Check(string name, GameObject prefab, Func<ActorAnimation, AnimationClip> pick)
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                try
                {
                    var actor = go.GetComponent<ActorAnimation>(); var clip = pick(actor); var host = actor.animationSource.gameObject;
                    var smr = go.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(r => r.name == "char1");
                    var head = Bone(host.transform, "Head");
                    clip.SampleAnimation(host, 0);
                    var p0 = WardNpcInstall.Skin(smr, head); var w = smr.sharedMesh.boneWeights; int hi = Array.IndexOf(smr.bones, head);
                    var idx = Enumerable.Range(0, p0.Length).Where(i => w[i].boneIndex0 == hi && w[i].weight0 > .5f).ToArray();
                    var mn = idx.Select(i => p0[i]).ToArray(); var mx = idx.Select(i => p0[i]).ToArray();
                    float maxSkinWeightsOnFace = 0;
                    for (int k = 1; k < 12; k++)
                    {
                        clip.SampleAnimation(host, clip.length * k / 12f); var p = WardNpcInstall.Skin(smr, head);
                        for (int n = 0; n < idx.Length; n++) { mn[n] = Vector3.Min(mn[n], p[idx[n]]); mx[n] = Vector3.Max(mx[n], p[idx[n]]); }
                    }
                    var spread = idx.Select((_, n) => (mx[n] - mn[n]).magnitude * head.lossyScale.x).OrderBy(x => x).ToArray();
                    var multi = idx.Count(i => w[i].weight1 > .05f);
                    res[name] = new { clip = clip.name, headVerts = idx.Length, spreadMedian = R(spread[spread.Length / 2]), spreadP95 = R(spread[spread.Length * 95 / 100]), spreadMax = R(spread.Last()), vertsWithSecondBone = multi,
                        secondBones = idx.Where(i => w[i].weight1 > .05f).GroupBy(i => smr.bones[w[i].boneIndex1].name).ToDictionary(g => g.Key, g => g.Count()) };
                }
                finally { Object.DestroyImmediate(go); }
            }
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            foreach (var s in Specs) Check(s.key, AssetDatabase.LoadAssetAtPath<GameObject>(s.Prefab), a => a.walk);
            foreach (var n in new[] { "Vex", "Mira" }) { var pf = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/WardNpcs/WardNpc_" + n + ".prefab"); if (pf) { Check(n + "_idle", pf, a => a.idle); Check(n + "_talk", pf, a => a.talk); } }
            return res;
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 ? args[i + 1].Split(',') : new[] { "import", "prefab", "install", "verify" };
            try
            {
                var results = new Dictionary<string, object>();
                foreach (var st in steps)
                {
                    object result = st switch
                    {
                        "import" => Import(),
                        "prefab" => BuildPrefabs(),
                        "install" => Install(),
                        "verify" => Verify(),
                        "capture" => Capture(),
                        "rollback" => Rollback(),
                        "dumpmesh" => DumpMesh(),
                        "facecheck" => FaceCheck(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    results[st] = result;
                    Debug.Log("WardWalkerInstall " + st + ": " + JsonConvert.SerializeObject(result));
                }
                Directory.CreateDirectory(Evidence);
                string file = Evidence + "install-log.json";
                var all = File.Exists(file) ? JObject.Parse(File.ReadAllText(file)) : new JObject();
                foreach (var kv in results) all[kv.Key] = JToken.FromObject(kv.Value);
                File.WriteAllText(file, all.ToString(Formatting.Indented));
                Debug.Log("WardWalkerInstall OK");
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); Debug.Log("WardWalkerInstall FAILED: " + e.Message); EditorApplication.Exit(1); }
        }
    }
}
