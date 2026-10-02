using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: Brann, the salvage dealer behind the Salvage shop trade counter (Carl: "an npc to trade with").
    /// Source: the unused roster model meshy/npc-roster-20260927/salvage_hauler, re-rigged in Meshy with library idles and
    /// talk clips (meshy/salvage-dealer-20261001: rig_dealer.py, record.json, README.md, inspection renders).
    ///
    /// Assets only: builds Prefabs/SalvageDealer.prefab without opening or saving the city scene. Follows the Ward Guard
    /// pattern (glTFast import with legacy animation, an Animation component driving legacy clips, ActorAnimation on the
    /// prefab root, ActorLookAt with Head/neck). The clip GLBs in Source/ are animation-only copies of the Meshy clips
    /// (strip_clip.py: same rig task, identical skeleton and keyframe bytes, no duplicate mesh/textures). Each clip is
    /// derived to Clips/dealer_*.anim keeping bone rotations plus the Hips translation, lifted by a constant so the lowest
    /// sole touches y = 0 over the loop (Meshy's library poses stand 9-12 cm below the wide-legged A-pose rig origin), with
    /// the loop seam eased like CharacterFeelPass. Uniform scale only: the standing idle is scaled to 1.82 m.
    ///
    /// Batch: -executeMethod AthenHill.Editor.ImportSalvageDealer.RunBatch -nographics --steps import,prefab,verify
    /// </summary>
    public static class ImportSalvageDealer
    {
        const string Record = "../../meshy/salvage-dealer-20261001/";
        public const string Folder = "Assets/AthenHill/Art/Imported/Meshy/SalvageDealer";
        public const string ModelPath = Folder + "/SalvageDealer.glb";
        const string SourceFolder = Folder + "/Source";
        const string ClipFolder = Folder + "/Clips";
        public const string MaterialPath = Folder + "/SalvageDealer.mat";
        public const string PrefabPath = "Assets/AthenHill/Prefabs/SalvageDealer.prefab";
        const string Evidence = "../evidence/salvage-shop/20261001/";
        public const float TargetHeight = 1.82f;
        /// Meshy library clips on rig task 01a0f911 (record.json). The first idle and talk are installed on the prefab;
        /// the others are kept as derived alternates.
        static readonly (string name, int action, string title)[] Clips = {
            ("idle_246", 246, "Idle 6 (weight on one hip)"), ("idle_252", 252, "Idle 12 (calm, palms out)"),
            ("talk_309", 309, "Talk with Left Hand on Hip"), ("talk_313", 313, "Talk with Hands Open"),
            ("talk_314", 314, "Talk with Right Hand Open")};
        public const string IdleClip = "idle_246", TalkClip = "talk_309";

        static string ClipAsset(string name) => ClipFolder + "/dealer_" + name + ".anim";
        static float R(float v, int d = 4) => (float)Math.Round(v, d);
        static float[] V(Vector3 v) => new[] { R(v.x), R(v.y), R(v.z) };

        // ------------------------------------------------------------------ import
        public static object Import()
        {
            Directory.CreateDirectory(SourceFolder); Directory.CreateDirectory(ClipFolder);
            var copied = new List<string>();
            void Copy(string from, string to)
            {
                if (!File.Exists(from)) throw new FileNotFoundException("Missing Meshy record file " + from);
                if (File.Exists(to) && File.ReadAllBytes(to).SequenceEqual(File.ReadAllBytes(from))) return;
                File.Copy(from, to, true); copied.Add(to);
            }
            Copy(Record + "rigged.glb", ModelPath);
            foreach (var c in Clips) Copy(Record + "anim_only/" + c.name + ".glb", SourceFolder + "/" + c.name + ".glb");
            AssetDatabase.Refresh();
            var report = new List<object>();
            foreach (var path in new[] { ModelPath }.Concat(Clips.Select(c => SourceFolder + "/" + c.name + ".glb")))
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                var importer = AssetImporter.GetAtPath(path); if (!importer) throw new Exception("No importer for " + path);
                var settings = new SerializedObject(importer);
                var method = settings.FindProperty("importSettings.animationMethod") ?? throw new Exception("Expected glTFast import settings on " + path);
                int legacy = Array.IndexOf(method.enumNames, "Legacy");
                bool changed = method.enumValueIndex != legacy;
                if (changed) { method.enumValueIndex = legacy; settings.ApplyModifiedPropertiesWithoutUndo(); importer.SaveAndReimport(); }
                var clips = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().ToArray();
                if (path != ModelPath && !clips.Any(c => c.legacy)) throw new Exception("No legacy clip in " + path);
                report.Add(new { path, legacyClips = clips.Select(c => new { c.name, c.legacy, length = R(c.length), c.frameRate }).ToArray(), animationMethodChanged = changed });
            }
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath); if (!model) throw new Exception("Model failed to import");
            var textures = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Texture2D>()
                .Select(t => new { t.name, t.width, t.height, format = t.format.ToString(), srgb = t.isDataSRGB, mips = t.mipmapCount }).ToArray();
            return new { copied, report, modelRoot = model.name, textures, compressionAddon = GltfTextureCompression.Enabled };
        }

        // ------------------------------------------------------------------ prefab
        /// Skinned vertex positions in the space of <paramref name="space"/> (bone matrices x bind poses, as ImportWardGuard:
        /// glTF skins ignore the mesh node's own scale, and BakeMesh is ambiguous with Meshy's centimetre armature).
        static Vector3[] Skin(SkinnedMeshRenderer r, Transform space)
        {
            var mesh = r.sharedMesh; var bones = r.bones; var bind = mesh.bindposes;
            var m = new Matrix4x4[bones.Length];
            for (int i = 0; i < m.Length; i++) m[i] = space.worldToLocalMatrix * bones[i].localToWorldMatrix * bind[i];
            var v = mesh.vertices; var w = mesh.boneWeights; var p = new Vector3[v.Length];
            for (int i = 0; i < v.Length; i++)
            {
                var b = w[i];
                p[i] = m[b.boneIndex0].MultiplyPoint3x4(v[i]) * b.weight0 + m[b.boneIndex1].MultiplyPoint3x4(v[i]) * b.weight1
                     + m[b.boneIndex2].MultiplyPoint3x4(v[i]) * b.weight2 + m[b.boneIndex3].MultiplyPoint3x4(v[i]) * b.weight3;
            }
            return p;
        }

        static AnimationClip SourceClip(string name)
        {
            var clip = AssetDatabase.LoadAllAssetsAtPath(SourceFolder + "/" + name + ".glb").OfType<AnimationClip>().FirstOrDefault(c => c && c.legacy);
            if (!clip) throw new Exception("No legacy source clip " + name);
            return clip;
        }

        /// The transform the clip binding paths are relative to. glTFast makes either the single root node (Armature) or a
        /// scene object the instance root; choose the object that resolves every bone path, renaming the instance root
        /// when the clips address it by its glTF node name.
        static Transform ResolveHost(GameObject rig, Transform wrapper, AnimationClip clip, List<string> log)
        {
            var paths = AnimationUtility.GetCurveBindings(clip).Select(b => b.path).Distinct().ToArray();
            bool All(Transform t) => paths.All(p => p.Length == 0 || t.Find(p) != null);
            foreach (var t in rig.GetComponentsInChildren<Transform>(true).Prepend(wrapper))
                if (All(t)) { log.Add("clip paths resolve from '" + t.name + "' (e.g. " + paths.FirstOrDefault(p => p.EndsWith("Hips")) + ")"); return t; }
            var first = paths.Select(p => p.Split('/')[0]).Distinct().ToArray();
            if (first.Length == 1 && rig.name != first[0])
            {
                log.Add("instance root renamed '" + rig.name + "' -> '" + first[0] + "' so clip paths resolve from the wrapper");
                rig.name = first[0];
                if (All(wrapper)) return wrapper;
            }
            throw new Exception("Clip paths do not resolve on the dealer rig: " + string.Join(", ", paths.Take(5)));
        }

        static float CloseLoop(AnimationCurve curve, float seconds)
        {
            var keys = curve.keys; float end = keys[keys.Length - 1].time, start = keys[0].time;
            float seam = Mathf.Abs(keys[keys.Length - 1].value - keys[0].value);
            seconds = Mathf.Min(seconds, (end - start) * .25f);
            for (int i = 0; i < keys.Length; i++)
            {
                float w = Mathf.InverseLerp(end - seconds, end, keys[i].time);
                if (w <= 0) continue;
                w = w * w * (3 - 2 * w);
                keys[i].value = Mathf.Lerp(keys[i].value, keys[0].value, w);
            }
            curve.keys = keys;
            for (int i = 0; i < curve.length; i++) AnimationUtility.SetKeyLeftTangentMode(curve, i, AnimationUtility.TangentMode.ClampedAuto);
            for (int i = 0; i < curve.length; i++) AnimationUtility.SetKeyRightTangentMode(curve, i, AnimationUtility.TangentMode.ClampedAuto);
            return seam;
        }

        static float LowestSole(AnimationClip clip, GameObject host, SkinnedMeshRenderer smr, Transform space, int samples, out float highestSole)
        {
            float low = float.MaxValue; highestSole = float.MinValue;
            for (int k = 0; k < samples; k++)
            {
                clip.SampleAnimation(host, clip.length * k / samples);
                float y = Skin(smr, space).Min(p => p.y);
                low = Mathf.Min(low, y); highestSole = Mathf.Max(highestSole, y);
            }
            return low;
        }

        /// Rotations of every bone plus the Hips translation (raised by <paramref name="hipsOffset"/>, in the Hips parent's
        /// local units), loop seam eased over 0.3 s.
        static object DeriveClip(AnimationClip source, string target, Vector3 hipsOffset)
        {
            var clip = new AnimationClip { name = Path.GetFileNameWithoutExtension(target), legacy = true, frameRate = source.frameRate, wrapMode = WrapMode.Loop };
            int kept = 0, dropped = 0, hips = 0; float seam = 0;
            foreach (var binding in AnimationUtility.GetCurveBindings(source))
            {
                string prop = binding.propertyName;
                bool rotation = prop.StartsWith("m_LocalRotation") || prop.StartsWith("localRotation");
                bool hipsPosition = (prop.StartsWith("m_LocalPosition") || prop.StartsWith("localPosition")) && (binding.path == "Hips" || binding.path.EndsWith("/Hips"));
                if (!rotation && !hipsPosition) { dropped++; continue; }
                var curve = AnimationUtility.GetEditorCurve(source, binding);
                if (hipsPosition)
                {
                    float add = prop.EndsWith(".x") ? hipsOffset.x : prop.EndsWith(".y") ? hipsOffset.y : hipsOffset.z;
                    var keys = curve.keys; for (int i = 0; i < keys.Length; i++) keys[i].value += add; curve.keys = keys; hips++;
                }
                if (curve.length > 2) seam = Mathf.Max(seam, CloseLoop(curve, .3f));
                clip.SetCurve(binding.path, typeof(Transform), prop.Replace("m_LocalRotation", "localRotation").Replace("m_LocalPosition", "localPosition"), curve);
                kept++;
            }
            if (hips != 3) throw new Exception("Expected Hips x/y/z translation curves in " + source.name + ", found " + hips);
            clip.EnsureQuaternionContinuity();
            var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(target);
            if (existing) { EditorUtility.CopySerialized(clip, existing); Object.DestroyImmediate(clip); EditorUtility.SetDirty(existing); }
            else AssetDatabase.CreateAsset(clip, target);
            return new { target, length = R(source.length, 3), source.frameRate, curvesKept = kept, curvesDropped = dropped, loopSeamCorrection = R(seam) };
        }

        public static object BuildPrefab()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            // Work in a fresh unsaved scene: the city scene is never opened, modified or saved here.
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var log = new List<string>();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath); if (!model) throw new Exception("Run the import step first.");
            var root = new GameObject("SalvageDealer");
            try
            {
                var visual = new GameObject("Visual").transform; visual.SetParent(root.transform, false);
                var rig = (GameObject)PrefabUtility.InstantiatePrefab(model);
                rig.transform.SetParent(visual, false);
                var renderers = rig.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                if (renderers.Length != 1 || !renderers[0].sharedMesh) throw new Exception("Dealer import must contain one skinned mesh, found " + renderers.Length);
                var smr = renderers[0];
                var sources = Clips.ToDictionary(c => c.name, c => SourceClip(c.name));
                var host = ResolveHost(rig, visual, sources[IdleClip], log);
                foreach (var c in Clips) if (ResolveHost(rig, visual, sources[c.name], new List<string>()) != host) throw new Exception(c.name + " binds to a different root");
                var anims = rig.GetComponentsInChildren<Animation>(true).Concat(visual.GetComponents<Animation>()).ToArray();
                var anim = host.GetComponent<Animation>();
                if (!anim) { anim = host.gameObject.AddComponent<Animation>(); log.Add("Animation added on '" + host.name + "'"); }
                foreach (var other in anims) if (other != anim) { Object.DestroyImmediate(other); log.Add("extra Animation removed from '" + other.name + "'"); }

                // Uniform scale from the standing idle (frame 0), not the wide-legged A-pose rest.
                sources[IdleClip].SampleAnimation(host.gameObject, 0);
                var pts = Skin(smr, root.transform);
                float standing = pts.Max(p => p.y) - pts.Min(p => p.y);
                float scale = TargetHeight / standing;
                visual.localScale = Vector3.one * scale;
                log.Add($"standing idle height {standing:F4} m at import scale; uniform scale {scale:F4}");
                // Facing: the rig's headfront bone sits in front of the face.
                var head = host.GetComponentsInChildren<Transform>(true).First(t => t.name == "Head");
                var neck = host.GetComponentsInChildren<Transform>(true).First(t => t.name == "neck");
                var front = host.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "headfront");
                if (front)
                {
                    var d = root.transform.InverseTransformPoint(front.position) - root.transform.InverseTransformPoint(head.position);
                    if (d.z < 0) { visual.localRotation = Quaternion.Euler(0, 180, 0); log.Add("visual turned 180 degrees to face +Z"); }
                }

                // Derive each clip with its own sole height lifted to y = 0.
                var hipsT = host.GetComponentsInChildren<Transform>(true).First(t => t.name == "Hips");
                var derived = new Dictionary<string, object>();
                foreach (var c in Clips)
                {
                    float low = LowestSole(sources[c.name], host.gameObject, smr, root.transform, 24, out float high);
                    var offset = hipsT.parent.InverseTransformVector(new Vector3(0, -low, 0));
                    derived[c.name] = new { action = c.action, c.title, soleBeforeLift = new[] { R(low), R(high) }, liftMetres = R(-low), hipsLocalOffset = V(offset),
                        clip = DeriveClip(sources[c.name], ClipAsset(c.name), offset) };
                }
                AssetDatabase.SaveAssets();
                var idle = AssetDatabase.LoadAssetAtPath<AnimationClip>(ClipAsset(IdleClip));
                var talk = AssetDatabase.LoadAssetAtPath<AnimationClip>(ClipAsset(TalkClip));

                // Editable material asset on the glTFast shader (same family as the Ward Guard's MAT_cloth); edits survive reruns.
                var source = smr.sharedMaterial;
                if (!source || !source.shader || source.shader.name.Contains("Error")) throw new Exception("Dealer material failed to import.");
                var mat = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
                if (!mat)
                {
                    mat = new Material(source) { name = "SalvageDealer" };
                    AssetDatabase.CreateAsset(mat, MaterialPath); log.Add("material created from imported " + source.name + " (" + source.shader.name + ")");
                }
                else log.Add("existing material kept: " + MaterialPath);
                smr.sharedMaterial = mat;
                smr.shadowCastingMode = ShadowCastingMode.On; smr.receiveShadows = true; smr.updateWhenOffscreen = true;

                anim.playAutomatically = false; anim.clip = idle;
                AnimationUtility.SetAnimationClips(anim, new[] { idle, talk });
                var actor = root.AddComponent<ActorAnimation>();
                actor.animationSource = anim;
                actor.idle = idle; actor.walk = idle; actor.run = idle; actor.talk = talk;   // Brann never walks
                actor.randomIdlePhase = true; actor.idleSpeedJitter = .08f;
                var look = root.AddComponent<ActorLookAt>();
                look.actor = actor; look.head = head; look.neck = neck;
                idle.SampleAnimation(host.gameObject, 0);
                var prefab = PrefabUtility.SaveAsPrefabAsset(root, PrefabPath, out bool ok);
                if (!ok || !prefab) throw new Exception("Prefab save failed");
                AssetDatabase.SaveAssets();
                return new { prefab = PrefabPath, host = host.name, scale = R(scale), log, clips = derived, idle = idle.name, talk = talk.name };
            }
            finally { Object.DestroyImmediate(root); }
        }

        // ------------------------------------------------------------------ verify
        public static object Verify()
        {
            var root = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                var actor = root.GetComponent<ActorAnimation>(); if (!actor) throw new Exception("No ActorAnimation on the prefab root");
                var look = root.GetComponent<ActorLookAt>(); if (!look) throw new Exception("No ActorLookAt on the prefab root");
                var smr = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
                var anim = actor.animationSource; if (!anim) throw new Exception("ActorAnimation has no Animation source");
                var host = anim.gameObject; var mesh = smr.sharedMesh; var t = root.transform;
                var clipReports = new Dictionary<string, object>();
                var failures = new List<string>(); float idleHeight = 0;
                var counterTops = new[] { .90f, .95f, 1.00f, 1.05f };
                foreach (var clip in new[] { actor.idle, actor.talk })
                {
                    var bindings = AnimationUtility.GetCurveBindings(clip);
                    int unresolved = bindings.Count(b => b.path.Length > 0 && !anim.transform.Find(b.path));
                    clip.SampleAnimation(host, 0);
                    var rest = smr.bones.ToDictionary(b => b.name, b => b.rotation);
                    var p0 = Skin(smr, t);
                    var hips0 = smr.bones.First(b => b.name == "Hips").position;
                    var motion = smr.bones.ToDictionary(b => b.name, b => 0f);
                    float soleLow = float.MaxValue, soleHigh = float.MinValue, hipsTravel = 0;
                    var reach = counterTops.Select(_ => -9f).ToArray();
                    float handForward = -9, handLow = 9;
                    var bodyFront = counterTops.Select(_ => -9f).ToArray();
                    float minX = 9, maxX = -9, minZ = 9, maxZ = -9;
                    var weights = mesh.boneWeights; var bones = smr.bones;
                    var handBone = bones.Select(b => b.name is "LeftHand" or "RightHand" or "LeftForeArm" or "RightForeArm").ToArray();
                    const int N = 30;
                    for (int k = 0; k < N; k++)
                    {
                        clip.SampleAnimation(host, clip.length * k / N);
                        foreach (var b in bones) motion[b.name] = Mathf.Max(motion[b.name], Quaternion.Angle(rest[b.name], b.rotation));
                        hipsTravel = Mathf.Max(hipsTravel, (bones.First(b => b.name == "Hips").position - hips0).magnitude);
                        var p = Skin(smr, t);
                        float low = p.Min(v => v.y); soleLow = Mathf.Min(soleLow, low); soleHigh = Mathf.Max(soleHigh, low);
                        for (int i = 0; i < p.Length; i++)
                        {
                            minX = Mathf.Min(minX, p[i].x); maxX = Mathf.Max(maxX, p[i].x); minZ = Mathf.Min(minZ, p[i].z); maxZ = Mathf.Max(maxZ, p[i].z);
                            for (int c = 0; c < counterTops.Length; c++)
                                if (p[i].y < counterTops[c]) bodyFront[c] = Mathf.Max(bodyFront[c], p[i].z);
                            if (!handBone[weights[i].boneIndex0] || weights[i].weight0 < .5f) continue;
                            handForward = Mathf.Max(handForward, p[i].z); handLow = Mathf.Min(handLow, p[i].y);
                            for (int c = 0; c < counterTops.Length; c++)
                                if (p[i].y < counterTops[c]) reach[c] = Mathf.Max(reach[c], p[i].z);
                        }
                    }
                    clipReports[clip.name] = new
                    {
                        length = R(clip.length, 3), clip.frameRate, wrap = clip.wrapMode.ToString(), clip.legacy, curves = bindings.Length, unresolvedPaths = unresolved,
                        heightAtFrame0 = R(p0.Max(v => v.y) - p0.Min(v => v.y)), soleHeightAtFrame0 = R(p0.Min(v => v.y)),
                        soleHeightRangeOverLoop = new[] { R(soleLow), R(soleHigh) },
                        bonesMovedOver1Degree = motion.Count(kv => kv.Value > 1), bonesMovedOver5Degrees = motion.Count(kv => kv.Value > 5),
                        largestBoneMotionDegrees = motion.OrderByDescending(kv => kv.Value).Take(6).ToDictionary(kv => kv.Key, kv => R(kv.Value, 1)),
                        hipsTravelMetres = R(hipsTravel),
                        handVerticesMaxForwardZ = R(handForward), handVerticesLowestY = R(handLow),
                        footprintOverLoop = new { minX = R(minX), maxX = R(maxX), minZ = R(minZ), maxZ = R(maxZ) },
                        bodyForwardZBelowCounterTop = counterTops.Select((h, c) => new { counterTop = h, maxZ = R(bodyFront[c]) }).ToArray(),
                        handForwardZBelowCounterTop = counterTops.Select((h, c) => new { counterTop = h, maxHandZ = reach[c] < -8 ? (float?)null : R(reach[c]) }).ToArray(),
                    };
                    if (unresolved != 0) failures.Add(clip.name + " has " + unresolved + " unresolved bone paths");
                    if (motion.Count(kv => kv.Value > 1) < 5) failures.Add(clip.name + " barely moves (frozen pose?)");
                    if (Mathf.Abs(p0.Min(v => v.y)) > .02f) failures.Add(clip.name + " sole is off the ground at frame 0: " + p0.Min(v => v.y));
                    if (clip == actor.idle) idleHeight = p0.Max(v => v.y) - p0.Min(v => v.y);
                }
                actor.idle.SampleAnimation(host, 0);
                var front = smr.bones.FirstOrDefault(b => b.name == "headfront");
                var faceDir = front ? t.InverseTransformPoint(front.position) - t.InverseTransformPoint(look.head.position) : Vector3.zero;
                var mat = smr.sharedMaterial;
                var textures = mat.GetTexturePropertyNames().Select(n => (n, tex: mat.GetTexture(n) as Texture2D)).Where(x => x.tex)
                    .Select(x => new { property = x.n, x.tex.name, x.tex.width, x.tex.height, format = x.tex.format.ToString(), graphicsFormat = x.tex.graphicsFormat.ToString(),
                        srgb = x.tex.isDataSRGB, mips = x.tex.mipmapCount, asset = AssetDatabase.GetAssetPath(x.tex), x.tex.anisoLevel, filter = x.tex.filterMode.ToString() }).ToArray();
                var floats = mat.shader ? Enumerable.Range(0, mat.shader.GetPropertyCount()).Where(i => mat.shader.GetPropertyType(i) is ShaderPropertyType.Float or ShaderPropertyType.Range)
                    .Select(i => mat.shader.GetPropertyName(i)).Where(n => n.Contains("metallic") || n.Contains("roughness") || n.Contains("normalTexture_scale") || n.Contains("Cull") || n.Contains("occlusion"))
                    .ToDictionary(n => n, n => R(mat.GetFloat(n))) : null;
                var result = new
                {
                    prefab = PrefabPath, prefabGuid = AssetDatabase.AssetPathToGUID(PrefabPath), model = ModelPath,
                    hierarchy = smr.transform.GetComponentsInParent<Transform>(true).Reverse().Select(x => x.name).ToArray(),
                    animationHost = host.name, animationHostPath = AnimationUtility.CalculateTransformPath(host.transform, t),
                    visualScale = V(t.Find("Visual").localScale), visualRotationY = R(t.Find("Visual").localEulerAngles.y, 1),
                    faceDirectionInPrefab = V(faceDir.normalized), facesPlusZ = faceDir.z > 0 && Mathf.Abs(faceDir.z) > Mathf.Abs(faceDir.x),
                    actor = new { idle = actor.idle.name, talk = actor.talk.name, walk = actor.walk.name, run = actor.run.name, actor.randomIdlePhase, actor.idleSpeedJitter },
                    animation = new { anim.playAutomatically, clip = anim.clip ? anim.clip.name : null, clips = AnimationUtility.GetAnimationClips(anim.gameObject).Select(c => c.name).ToArray(), culling = anim.cullingType.ToString() },
                    lookAt = new { head = look.head ? look.head.name : null, neck = look.neck ? look.neck.name : null, actorWired = look.actor == actor },
                    renderer = new { name = smr.name, shadows = smr.shadowCastingMode.ToString(), smr.receiveShadows, smr.updateWhenOffscreen, smr.skinnedMotionVectors, quality = smr.quality.ToString(),
                        triangles = Enumerable.Range(0, mesh.subMeshCount).Sum(s => (long)mesh.GetIndexCount(s)) / 3, vertices = mesh.vertexCount, submeshes = mesh.subMeshCount,
                        bones = smr.bones.Length, boneNames = smr.bones.Select(b => b.name).ToArray(), blendShapes = mesh.blendShapeCount, maxBonesPerVertex = mesh.GetBonesPerVertex().Max() },
                    material = new { asset = AssetDatabase.GetAssetPath(mat), mat.name, shader = mat.shader.name, keywords = mat.shaderKeywords, mat.renderQueue, floats, textures },
                    clips = clipReports,
                };
                var json = JsonConvert.SerializeObject(result, Formatting.Indented);
                Directory.CreateDirectory(Evidence); File.WriteAllText(Evidence + "dealer-verify.json", json);
                if (!result.facesPlusZ) failures.Add("prefab does not face +Z");
                if (Mathf.Abs(idleHeight - TargetHeight) > .03f) failures.Add("standing height " + idleHeight);
                if (failures.Count > 0) throw new Exception("Verify failed: " + string.Join("; ", failures));
                return new { written = Evidence + "dealer-verify.json", result.facesPlusZ, triangles = result.renderer.triangles, result.renderer.bones, height = R(idleHeight) };
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 ? args[i + 1].Split(',') : new[] { "import", "prefab", "verify" };
            try
            {
                var results = new Dictionary<string, object>();
                foreach (var st in steps)
                {
                    object result = st switch
                    {
                        "import" => Import(),
                        "prefab" => BuildPrefab(),
                        "verify" => Verify(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    results[st] = result;
                    Debug.Log("ImportSalvageDealer " + st + ": " + JsonConvert.SerializeObject(result));
                }
                Directory.CreateDirectory(Evidence);
                string file = Evidence + "dealer-import.json";
                var all = File.Exists(file) ? Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(file)) : new Newtonsoft.Json.Linq.JObject();
                foreach (var kv in results) all[kv.Key] = Newtonsoft.Json.Linq.JToken.FromObject(kv.Value);
                File.WriteAllText(file, all.ToString(Formatting.Indented));
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); Debug.Log("ImportSalvageDealer FAILED: " + e.Message); EditorApplication.Exit(1); }
        }
    }
}
