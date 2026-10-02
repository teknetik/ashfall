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
    /// 2 October 2026: visual prefabs for the two ranged Outer Berms enemies (Carl: "use meshy to create 2 more enemies a
    /// bit further out that use ranged weapons"). Sources, prompts, Meshy task ids, inspection renders and known defects:
    /// meshy/ranged-enemies-20261002 (README.md, record.json, handoff.json).
    ///
    /// Feral gunner droid: Meshy multi-image-to-3D biped (A-pose) rigged by Meshy, with a separately generated forearm
    /// rivet/arc gun strapped to the RightForeArm bone (make_gunner.py merges it into the rig GLB as a rigid child node with
    /// a 'Muzzle' child). Library clips (idle, walk, run, hit, death) and procedural ranged clips layered on library bases
    /// (aim, fire, fire_raise, strafe_left, strafe_right) come in as animation-only GLBs (Source/) and are derived here to
    /// legacy clips with bone rotations plus the Hips translation, each lifted so the lowest sole touches y = 0 (death: its
    /// first frame), loop seams eased on the looping clips. Uniform scale: standing idle = 2.0 m.
    /// Feral lancer drone: Meshy multi-image-to-3D, processed in Blender (process_lancer.py): authored rotors replace the
    /// fused Meshy blades ('Rotor A'..'Rotor D', pivots on the hubs, spin axis local Y), an emissive 'Lens cap' over the eye,
    /// 'Muzzle' at the lance tip. Rotor blur discs reuse the scrap drone's RB_RotorBlur material and RB_RotorDisc mesh.
    ///
    /// Materials are URP Lit on the exported Meshy maps (Art/OuterBerms/Ranged/Textures, make_textures.py); the gunner's
    /// emission map lights only its head optic and the lancer's lens cap carries its glow, so FeralDroid can drive the
    /// telegraph through _EmissionColor (RealtimeEmissive, or URP drops _EMISSION on save).
    ///
    /// Assets only: never opens, modifies or saves the city scene, and adds no gameplay components (the gameplay prefabs
    /// wrap these visuals). Batch: -executeMethod AthenHill.Editor.OuterBermsRangedEnemies.RunBatch -nographics
    /// --steps import,prefab,verify
    /// </summary>
    public static class OuterBermsRangedEnemies
    {
        const string Record = "../../meshy/ranged-enemies-20261002/";
        const string Art = "Assets/AthenHill/Art/OuterBerms/Ranged/";
        const string ModelDir = Art + "Models/", SourceDir = Art + "Source/", ClipDir = Art + "Clips/FeralGunner/", MatDir = Art + "Materials/", TexDir = Art + "Textures/";
        public const string GunnerModel = ModelDir + "FeralGunner.glb", LancerModel = ModelDir + "FeralLancer.glb";
        const string PrefabDir = "Assets/AthenHill/Prefabs/OuterBerms/Visuals/";
        public const string GunnerPrefab = PrefabDir + "FeralGunnerVisual.prefab", LancerPrefab = PrefabDir + "FeralLancerVisual.prefab";
        const string BlurMaterial = "Assets/AthenHill/Art/OuterBerms/Materials/RB_RotorBlur.mat", BlurDisc = "Assets/AthenHill/Art/OuterBerms/Meshes/RB_RotorDisc.asset";
        const string LensGlow = "Assets/AthenHill/Art/OuterBerms/Textures/RB_LensGlow.png";
        const string Evidence = "../evidence/ranged-enemies/20261002/";
        public const float GunnerHeight = 2.0f;
        static readonly Color GunnerGlow = new Color(1.1f, .45f, .1f), LancerGlow = new Color(1.2f, .32f, .07f);

        /// name, loops, lift rule (true = lowest sole over the clip; false = first frame), note
        static readonly (string name, bool loop, bool liftOverClip)[] Clips = {
            ("idle", true, true), ("walk", true, true), ("run", true, true), ("aim", true, true), ("strafe_left", true, true), ("strafe_right", true, true),
            ("fire", false, true), ("fire_raise", false, true), ("hit", false, true), ("death", false, false) };

        static float R(float v, int d = 4) => (float)Math.Round(v, d);
        static float[] V(Vector3 v, int d = 4) => new[] { R(v.x, d), R(v.y, d), R(v.z, d) };
        static float[] Q(Quaternion q) => new[] { R(q.x, 5), R(q.y, 5), R(q.z, 5), R(q.w, 5) };
        static string ClipAsset(string n) => ClipDir + n + ".anim";

        // ------------------------------------------------------------------ import
        public static object Import()
        {
            foreach (var d in new[] { ModelDir, SourceDir, ClipDir, MatDir, TexDir, PrefabDir }) Directory.CreateDirectory(d);
            var copied = new List<string>();
            void Copy(string from, string to)
            {
                if (!File.Exists(from)) throw new FileNotFoundException("Missing record file " + from);
                if (File.Exists(to) && File.ReadAllBytes(to).SequenceEqual(File.ReadAllBytes(from))) return;
                File.Copy(from, to, true); copied.Add(to);
            }
            Copy(Record + "gunner/build/FeralGunner_geo.glb", GunnerModel);
            Copy(Record + "lancer/proc/FeralLancer.glb", LancerModel);
            foreach (var c in Clips) Copy(Record + "gunner/build/anim/" + c.name + ".glb", SourceDir + "gunner_" + c.name + ".glb");
            AssetDatabase.Refresh();
            var report = new List<object>();
            foreach (var path in new[] { GunnerModel, LancerModel }.Concat(Clips.Select(c => SourceDir + "gunner_" + c.name + ".glb")))
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                var importer = AssetImporter.GetAtPath(path); if (!importer) throw new Exception("No importer for " + path);
                var so = new SerializedObject(importer);
                var method = so.FindProperty("importSettings.animationMethod") ?? throw new Exception("Expected glTFast import settings on " + path);
                int legacy = Array.IndexOf(method.enumNames, "Legacy"); bool changed = method.enumValueIndex != legacy;
                if (changed) { method.enumValueIndex = legacy; so.ApplyModifiedPropertiesWithoutUndo(); importer.SaveAndReimport(); }
                var clips = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().ToArray();
                if (path.StartsWith(SourceDir) && !clips.Any(c => c.legacy)) throw new Exception("No legacy clip in " + path);
                report.Add(new { path, legacyClips = clips.Select(c => new { c.name, length = R(c.length, 3), c.frameRate }).ToArray(), animationMethodChanged = changed });
            }
            // texture importers: sRGB base colour, normal maps, linear mask/emission, streamed mips, BC7
            var textures = new List<object>();
            foreach (var path in Directory.GetFiles(TexDir, "*.png").Select(p => p.Replace('\\', '/')))
            {
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                var file = Path.GetFileNameWithoutExtension(path);
                bool normal = file.EndsWith("_Normal"), linear = file.EndsWith("_Mask") || file.EndsWith("_Emission");
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !normal && !linear; ti.alphaSource = file.EndsWith("_Mask") ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                ti.maxTextureSize = file.EndsWith("_Emission") ? 1024 : 2048; ti.anisoLevel = 8; ti.mipmapEnabled = true; ti.streamingMipmaps = true;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
                var t = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                textures.Add(new { path, t.width, t.height, format = t.format.ToString(), srgb = ti.sRGBTexture, type = ti.textureType.ToString(), streaming = ti.streamingMipmaps });
            }
            var mats = BuildMaterials();
            return new { copied, report, textures, materials = mats, compressionAddon = GltfTextureCompression.Enabled };
        }

        static Material Lit(string name)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            var path = MatDir + name + ".mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
            m.shader = shader; return m;
        }

        static Material RobotMaterial(string name, string stem, Color? glow)
        {
            var m = Lit(name);
            Texture2D T(string s) { var x = AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + stem + "_" + s + ".png"); if (!x) throw new Exception("Missing texture " + stem + "_" + s); return x; }
            m.SetTexture("_BaseMap", T("BaseMap")); m.SetColor("_BaseColor", Color.white);
            m.SetTexture("_BumpMap", T("Normal")); m.SetFloat("_BumpScale", 1f); m.EnableKeyword("_NORMALMAP");
            m.SetTexture("_MetallicGlossMap", T("Mask")); m.EnableKeyword("_METALLICSPECGLOSSMAP"); m.SetFloat("_Smoothness", 1);
            if (glow.HasValue)
            {
                m.SetTexture("_EmissionMap", T("Emission")); m.SetColor("_EmissionColor", glow.Value); m.EnableKeyword("_EMISSION");
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
            else { m.SetTexture("_EmissionMap", null); m.SetColor("_EmissionColor", Color.black); m.DisableKeyword("_EMISSION"); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack; }
            m.SetFloat("_Cull", 2); m.doubleSidedGI = false; m.enableInstancing = true;
            EditorUtility.SetDirty(m); return m;
        }

        static object BuildMaterials()
        {
            var gunner = RobotMaterial("FR_FeralGunner", "FeralGunner", GunnerGlow);
            var gun = RobotMaterial("FR_FeralGunnerGun", "FeralGunnerGun", null);
            var lancer = RobotMaterial("FR_FeralLancer", "FeralLancer", null);
            var lens = Lit("FR_FeralLancerLens");
            lens.SetColor("_BaseColor", new Color(.2f, .035f, .02f)); lens.SetFloat("_Smoothness", .93f); lens.SetFloat("_Metallic", 0);
            var glowTex = AssetDatabase.LoadAssetAtPath<Texture2D>(LensGlow); if (!glowTex) throw new Exception("Missing " + LensGlow);
            lens.SetTexture("_EmissionMap", glowTex);
            lens.SetColor("_EmissionColor", LancerGlow); lens.EnableKeyword("_EMISSION");
            lens.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive; lens.enableInstancing = true; EditorUtility.SetDirty(lens);
            AssetDatabase.SaveAssets();
            return new[] { gunner, gun, lancer, lens }.Select(m => new { m.name, path = AssetDatabase.GetAssetPath(m), emission = m.IsKeywordEnabled("_EMISSION"), gi = m.globalIlluminationFlags.ToString() }).ToArray();
        }

        // ------------------------------------------------------------------ gunner helpers (as ImportSalvageDealer)
        /// Skinned vertex positions in the space of <paramref name="space"/> (bone matrices x bind poses).
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
            var clip = AssetDatabase.LoadAllAssetsAtPath(SourceDir + "gunner_" + name + ".glb").OfType<AnimationClip>().FirstOrDefault(c => c && c.legacy);
            return clip ? clip : throw new Exception("No legacy source clip " + name);
        }

        static Transform ResolveHost(GameObject rig, Transform wrapper, AnimationClip clip, List<string> log)
        {
            var paths = AnimationUtility.GetCurveBindings(clip).Select(b => b.path).Distinct().ToArray();
            bool All(Transform t) => paths.All(p => p.Length == 0 || t.Find(p) != null);
            foreach (var t in rig.GetComponentsInChildren<Transform>(true).Prepend(wrapper))
                if (All(t)) { log.Add("clip paths resolve from '" + t.name + "'"); return t; }
            var first = paths.Select(p => p.Split('/')[0]).Distinct().ToArray();
            if (first.Length == 1 && rig.name != first[0])
            {
                log.Add("instance root renamed '" + rig.name + "' -> '" + first[0] + "' so clip paths resolve from the wrapper");
                rig.name = first[0];
                if (All(wrapper)) return wrapper;
            }
            throw new Exception("Clip paths do not resolve on the gunner rig: " + string.Join(", ", paths.Take(5)));
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
                w = w * w * (3 - 2 * w); keys[i].value = Mathf.Lerp(keys[i].value, keys[0].value, w);
            }
            curve.keys = keys;
            for (int i = 0; i < curve.length; i++) { AnimationUtility.SetKeyLeftTangentMode(curve, i, AnimationUtility.TangentMode.ClampedAuto); AnimationUtility.SetKeyRightTangentMode(curve, i, AnimationUtility.TangentMode.ClampedAuto); }
            return seam;
        }

        static object DeriveClip(AnimationClip source, string name, Vector3 hipsOffset, bool loop)
        {
            var clip = new AnimationClip { name = name, legacy = true, frameRate = source.frameRate, wrapMode = loop ? WrapMode.Loop : name == "death" ? WrapMode.ClampForever : WrapMode.Once };
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
                if (loop && curve.length > 2) seam = Mathf.Max(seam, CloseLoop(curve, .3f));
                clip.SetCurve(binding.path, typeof(Transform), prop.Replace("m_LocalRotation", "localRotation").Replace("m_LocalPosition", "localPosition"), curve);
                kept++;
            }
            if (hips != 3) throw new Exception("Expected Hips x/y/z translation curves in " + source.name + ", found " + hips);
            clip.EnsureQuaternionContinuity();
            var target = ClipAsset(name);
            var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(target);
            if (existing) { EditorUtility.CopySerialized(clip, existing); existing.name = name; Object.DestroyImmediate(clip); EditorUtility.SetDirty(existing); }
            else AssetDatabase.CreateAsset(clip, target);
            return new { target, length = R(source.length, 3), source.frameRate, wrap = (loop ? WrapMode.Loop : name == "death" ? WrapMode.ClampForever : WrapMode.Once).ToString(), curvesKept = kept, curvesDropped = dropped, loopSeamCorrection = R(seam) };
        }

        // ------------------------------------------------------------------ prefabs
        public static object BuildPrefabs()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            // Work in a fresh unsaved scene: the city scene is never opened, modified or saved here.
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            Directory.CreateDirectory(PrefabDir);
            return new { gunner = BuildGunner(), lancer = BuildLancer() };
        }

        static object BuildGunner()
        {
            var log = new List<string>();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(GunnerModel); if (!model) throw new Exception("Run the import step first.");
            var root = new GameObject("FeralGunnerVisual");
            try
            {
                var visual = new GameObject("Visual").transform; visual.SetParent(root.transform, false);
                var rig = (GameObject)PrefabUtility.InstantiatePrefab(model); rig.transform.SetParent(visual, false);
                var smrs = rig.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                if (smrs.Length != 1 || !smrs[0].sharedMesh) throw new Exception("Gunner import must contain one skinned mesh, found " + smrs.Length);
                var smr = smrs[0];
                var sources = Clips.ToDictionary(c => c.name, c => SourceClip(c.name));
                var host = ResolveHost(rig, visual, sources["idle"], log);
                foreach (var c in Clips) if (ResolveHost(rig, visual, sources[c.name], new List<string>()) != host) throw new Exception(c.name + " binds to a different root");
                var anims = rig.GetComponentsInChildren<Animation>(true).Concat(visual.GetComponents<Animation>()).ToArray();
                var anim = host.GetComponent<Animation>();
                if (!anim) { anim = host.gameObject.AddComponent<Animation>(); log.Add("Animation added on '" + host.name + "'"); }
                foreach (var other in anims) if (other != anim) { Object.DestroyImmediate(other); log.Add("extra Animation removed from '" + other.name + "'"); }

                // uniform scale from the standing idle (frame 0)
                sources["idle"].SampleAnimation(host.gameObject, 0);
                var pts = Skin(smr, root.transform);
                float standing = pts.Max(p => p.y) - pts.Min(p => p.y), scale = GunnerHeight / standing;
                visual.localScale = Vector3.one * scale;
                log.Add($"standing idle height {standing:F4} m at import scale; uniform scale {scale:F4}");
                var bones = host.GetComponentsInChildren<Transform>(true);
                Transform Bone(string n) => bones.FirstOrDefault(t => t.name == n) ?? throw new Exception("Missing bone " + n);
                var head = Bone("Head"); var front = Bone("headfront");
                if ((root.transform.InverseTransformPoint(front.position) - root.transform.InverseTransformPoint(head.position)).z < 0)
                { visual.localRotation = Quaternion.Euler(0, 180, 0); log.Add("visual turned 180 degrees to face +Z"); }

                // derived clips: rotations + Hips translation, lifted to the ground
                var hipsT = Bone("Hips"); var derived = new Dictionary<string, object>();
                foreach (var c in Clips)
                {
                    var src = sources[c.name]; float low = float.MaxValue, high = float.MinValue; int n = Mathf.Max(8, Mathf.CeilToInt(src.length * 15));
                    for (int k = 0; k <= (c.liftOverClip ? n : 0); k++)
                    {
                        src.SampleAnimation(host.gameObject, src.length * k / n);
                        float y = Skin(smr, root.transform).Min(p => p.y); low = Mathf.Min(low, y); high = Mathf.Max(high, y);
                    }
                    var offset = hipsT.parent.InverseTransformVector(new Vector3(0, -low, 0));
                    derived[c.name] = new { liftMetres = R(-low), lowestPointBeforeLift = new[] { R(low), R(high) }, rule = c.liftOverClip ? "lowest point over the clip" : "first frame", clip = DeriveClip(src, c.name, offset, c.loop) };
                }
                AssetDatabase.SaveAssets();
                var clips = Clips.Select(c => AssetDatabase.LoadAssetAtPath<AnimationClip>(ClipAsset(c.name))).ToArray();
                var idle = clips[0];

                // materials
                smr.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "FR_FeralGunner.mat");
                smr.shadowCastingMode = ShadowCastingMode.On; smr.receiveShadows = true; smr.skinnedMotionVectors = true;
                var gun = bones.FirstOrDefault(t => t.name == "ForearmGun") ?? throw new Exception("ForearmGun node missing from the gunner model");
                var gunR = gun.GetComponent<MeshRenderer>(); if (!gunR) throw new Exception("ForearmGun has no MeshRenderer");
                gunR.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "FR_FeralGunnerGun.mat"); gunR.shadowCastingMode = ShadowCastingMode.On;
                var muzzle = gun.Find("Muzzle") ?? throw new Exception("Muzzle missing under ForearmGun");

                anim.playAutomatically = false; anim.clip = idle; anim.cullingType = AnimationCullingType.BasedOnRenderers;
                AnimationUtility.SetAnimationClips(anim, clips);

                // culling bounds: the skinned body over every clip, in the renderer's bounds space (root bone), +12 %
                var space = smr.rootBone ? smr.rootBone : smr.transform;
                var lo = Vector3.one * float.MaxValue; var hi = -lo;
                foreach (var clip in clips)
                {
                    int n = Mathf.Max(2, Mathf.CeilToInt(clip.length * 15));
                    for (int k = 0; k <= n; k++)
                    {
                        clip.SampleAnimation(host.gameObject, clip.length * k / n);
                        foreach (var p in Skin(smr, space)) { lo = Vector3.Min(lo, p); hi = Vector3.Max(hi, p); }
                    }
                }
                var env = new Bounds(); env.SetMinMax(lo, hi);
                smr.localBounds = new Bounds(env.center, env.size * 1.24f); smr.updateWhenOffscreen = false;
                idle.SampleAnimation(host.gameObject, 0);
                var prefab = PrefabUtility.SaveAsPrefabAsset(root, GunnerPrefab, out bool ok);
                if (!ok || !prefab) throw new Exception("Gunner prefab save failed");
                return new { prefab = GunnerPrefab, host = host.name, scale = R(scale), log, clips = derived, bounds = new { space = space.name, envelopeCenter = V(env.center, 2), envelopeSize = V(env.size, 2), fittedSize = V(smr.localBounds.size, 2) } };
            }
            finally { Object.DestroyImmediate(root); }
        }

        static object BuildLancer()
        {
            var log = new List<string>();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(LancerModel); if (!model) throw new Exception("Run the import step first.");
            var root = new GameObject("FeralLancerVisual");
            try
            {
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(model); inst.transform.SetParent(root.transform, false);
                inst.name = "Visual";
                Transform Find(string n) => inst.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == n) ?? throw new Exception("Lancer model is missing " + n);
                var body = Find("Body"); var cap = Find("Lens cap"); var muzzle = Find("Muzzle");
                var rotors = new[] { "Rotor A", "Rotor B", "Rotor C", "Rotor D" }.Select(Find).ToArray();
                // facing: the eye and the lance tip are in front (+Z)
                if (cap.localPosition.z < 0 || muzzle.localPosition.z < 0) { inst.transform.localRotation = Quaternion.Euler(0, 180, 0); log.Add("visual turned 180 degrees to face +Z"); }
                var bodyMat = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "FR_FeralLancer.mat");
                var lensMat = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "FR_FeralLancerLens.mat");
                var bodyR = body.GetComponent<MeshRenderer>(); bodyR.sharedMaterial = bodyMat; bodyR.shadowCastingMode = ShadowCastingMode.On;
                var capR = cap.GetComponent<MeshRenderer>(); capR.sharedMaterial = lensMat; capR.shadowCastingMode = ShadowCastingMode.Off;
                var disc = AssetDatabase.LoadAssetAtPath<Mesh>(BlurDisc); if (!disc) throw new Exception("Missing " + BlurDisc);
                var blur = AssetDatabase.LoadAssetAtPath<Material>(BlurMaterial); if (!blur) throw new Exception("Missing " + BlurMaterial);
                var rotorInfo = new List<object>();
                foreach (var r in rotors)
                {
                    var mr = r.GetComponent<MeshRenderer>(); mr.sharedMaterial = bodyMat; mr.shadowCastingMode = ShadowCastingMode.Off;
                    var mesh = r.GetComponent<MeshFilter>().sharedMesh;
                    float radius = mesh.vertices.Max(p => new Vector2(p.x, p.z).magnitude);
                    var old = r.Find("Blur disc"); if (old) Object.DestroyImmediate(old.gameObject);
                    var d = new GameObject("Blur disc", typeof(MeshFilter), typeof(MeshRenderer)).transform;
                    d.SetParent(r, false); d.localPosition = new Vector3(0, .005f, 0); d.localScale = Vector3.one * radius * 1.02f;
                    d.GetComponent<MeshFilter>().sharedMesh = disc;
                    var dr = d.GetComponent<MeshRenderer>(); dr.sharedMaterial = blur; dr.shadowCastingMode = ShadowCastingMode.Off; dr.receiveShadows = false;
                    rotorInfo.Add(new { r.name, pivot = V(root.transform.InverseTransformPoint(r.position)), bladeRadius = R(radius), up = V(root.transform.InverseTransformDirection(r.up), 3) });
                }
                var prefab = PrefabUtility.SaveAsPrefabAsset(root, LancerPrefab, out bool ok);
                if (!ok || !prefab) throw new Exception("Lancer prefab save failed");
                return new { prefab = LancerPrefab, log, rotors = rotorInfo };
            }
            finally { Object.DestroyImmediate(root); }
        }

        // ------------------------------------------------------------------ verify
        static string PathOf(Transform t, Transform root) => AnimationUtility.CalculateTransformPath(t, root);

        static object TexReport(Material m) => m.GetTexturePropertyNames().Select(n => (n, tex: m.GetTexture(n) as Texture2D)).Where(x => x.tex)
            .Select(x => new { property = x.n, x.tex.name, x.tex.width, x.tex.height, format = x.tex.format.ToString(), asset = AssetDatabase.GetAssetPath(x.tex) }).ToArray();

        public static object Verify()
        {
            var failures = new List<string>();
            var g = VerifyGunner(failures); var l = VerifyLancer(failures);
            var result = new { gunner = g, lancer = l, failures };
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", JsonConvert.SerializeObject(result, Formatting.Indented));
            if (failures.Count > 0) throw new Exception("Verify failed: " + string.Join("; ", failures));
            return new { written = Evidence + "verify.json", failures = failures.Count };
        }

        static object VerifyGunner(List<string> failures)
        {
            var root = PrefabUtility.LoadPrefabContents(GunnerPrefab);
            try
            {
                var t = root.transform;
                var anim = root.GetComponentInChildren<Animation>(true); if (!anim) throw new Exception("No Animation in the gunner prefab");
                var host = anim.gameObject;
                var smr = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single(); var mesh = smr.sharedMesh;
                var bones = root.GetComponentsInChildren<Transform>(true);
                Transform Bone(string n) => bones.First(b => b.name == n);
                var gun = Bone("ForearmGun"); var muzzle = Bone("Muzzle"); var fore = Bone("RightForeArm"); var hand = Bone("RightHand");
                var clips = AnimationUtility.GetAnimationClips(host);
                var expected = Clips.Select(c => c.name).ToArray();
                if (!expected.All(n => clips.Any(c => c && c.name == n))) failures.Add("gunner Animation is missing clips: " + string.Join(",", expected.Where(n => !clips.Any(c => c && c.name == n))));
                var reports = new Dictionary<string, object>(); float idleHeight = 0;
                var lb = smr.localBounds; var space = smr.rootBone ? smr.rootBone : smr.transform; bool covered = true;
                foreach (var clip in clips)
                {
                    var bindings = AnimationUtility.GetCurveBindings(clip);
                    int unresolved = bindings.Count(b => b.path.Length > 0 && !anim.transform.Find(b.path));
                    clip.SampleAnimation(host, 0);
                    var rest = smr.bones.ToDictionary(b => b.name, b => b.rotation);
                    var p0 = Skin(smr, t); float h0 = p0.Max(v => v.y) - p0.Min(v => v.y);
                    float soleLo = float.MaxValue, soleHi = float.MinValue, maxMove = 0; int moved = 0; var motion = smr.bones.ToDictionary(b => b.name, b => 0f);
                    var muz = new List<object>();
                    int N = Mathf.Max(6, Mathf.CeilToInt(clip.length * 10));
                    for (int k = 0; k <= N; k++)
                    {
                        float time = clip.length * k / N; clip.SampleAnimation(host, time);
                        foreach (var b in smr.bones) motion[b.name] = Mathf.Max(motion[b.name], Quaternion.Angle(rest[b.name], b.rotation));
                        var p = Skin(smr, t); float low = p.Min(v => v.y); soleLo = Mathf.Min(soleLo, low); soleHi = Mathf.Max(soleHi, low);
                        foreach (var q in Skin(smr, space)) if (!lb.Contains(q)) covered = false;
                        var mp = t.InverseTransformPoint(muzzle.position); var md = t.InverseTransformDirection(muzzle.forward);
                        if (k % Mathf.Max(1, N / 6) == 0) muz.Add(new { time = R(time, 2), position = V(mp, 3), forward = V(md, 3), elevationDeg = R(Mathf.Asin(Mathf.Clamp(md.y, -1, 1)) * Mathf.Rad2Deg, 1) });
                    }
                    moved = motion.Count(kv => kv.Value > 1); maxMove = motion.Values.Max();
                    reports[clip.name] = new { length = R(clip.length, 3), clip.frameRate, wrap = clip.wrapMode.ToString(), clip.legacy, curves = bindings.Length, unresolvedPaths = unresolved,
                        heightAtFrame0 = R(h0), soleAtFrame0 = R(p0.Min(v => v.y)), soleRangeOverClip = new[] { R(soleLo), R(soleHi) }, bonesMovedOver1Degree = moved, muzzle = muz };
                    if (unresolved != 0) failures.Add(clip.name + " has " + unresolved + " unresolved bone paths");
                    if (moved < 5) failures.Add(clip.name + " barely moves");
                    if (clip.name != "death" && Mathf.Abs(soleLo) > .03f) failures.Add(clip.name + " lowest sole " + soleLo);
                    if (clip.name == "idle") idleHeight = h0;
                }
                // muzzle checks in the aim pose and at the fire recoil peak (prefab space, faces +Z)
                var aim = clips.First(c => c.name == "aim"); aim.SampleAnimation(host, 0);
                var aimPos = t.InverseTransformPoint(muzzle.position); var aimDir = t.InverseTransformDirection(muzzle.forward);
                var wristToMuzzle = Vector3.Dot(muzzle.position - hand.position, aimDir);
                if (aimDir.z < .97f) failures.Add("aim: muzzle not pointing forward " + aimDir);
                if (aimPos.z < .6f) failures.Add("aim: muzzle not in front of the body " + aimPos);
                var fire = clips.First(c => c.name == "fire"); fire.SampleAnimation(host, .1f);
                var fireDir = t.InverseTransformDirection(muzzle.forward);
                // muzzle at the barrel end: the gun mesh's farthest vertex along +Z (gun space) vs the muzzle
                var gmesh = gun.GetComponent<MeshFilter>().sharedMesh; float tip = gmesh.vertices.Max(v => v.z);
                var muzzleInGun = gun.InverseTransformPoint(muzzle.position);
                aim.SampleAnimation(host, 0);
                var faceDir = t.InverseTransformPoint(Bone("headfront").position) - t.InverseTransformPoint(Bone("Head").position);
                if (faceDir.z <= 0) failures.Add("gunner does not face +Z");
                clips.First(c => c.name == "idle").SampleAnimation(host, 0);
                if (Mathf.Abs(idleHeight - GunnerHeight) > .03f) failures.Add("gunner standing height " + idleHeight);
                if (!covered) failures.Add("gunner localBounds do not cover every clip");
                if (Mathf.Abs(muzzleInGun.z - (tip + .01f)) > .02f) failures.Add("muzzle is not 1 cm ahead of the barrel tip: " + muzzleInGun.z + " vs tip " + tip);
                var mat = smr.sharedMaterial; var gmat = gun.GetComponent<MeshRenderer>().sharedMaterial;
                return new
                {
                    prefab = GunnerPrefab, guid = AssetDatabase.AssetPathToGUID(GunnerPrefab), model = GunnerModel,
                    animationHostPath = PathOf(host.transform, t), animation = new { anim.playAutomatically, clip = anim.clip ? anim.clip.name : null, culling = anim.cullingType.ToString(), clips = clips.Select(c => c.name).ToArray() },
                    visualScale = V(t.Find("Visual").localScale), facesPlusZ = faceDir.z > 0, standingHeight = R(idleHeight),
                    body = new { path = PathOf(smr.transform, t), triangles = Enumerable.Range(0, mesh.subMeshCount).Sum(s => (long)mesh.GetIndexCount(s)) / 3, vertices = mesh.vertexCount, bones = smr.bones.Length,
                        rootBone = smr.rootBone ? smr.rootBone.name : null, localBounds = new { center = V(lb.center, 2), size = V(lb.size, 2) }, boundsCoverAllClips = covered, smr.updateWhenOffscreen,
                        shadows = smr.shadowCastingMode.ToString(), material = new { mat.name, shader = mat.shader.name, keywords = mat.shaderKeywords, gi = mat.globalIlluminationFlags.ToString(), emissionColor = mat.GetColor("_EmissionColor").ToString(), textures = TexReport(mat) } },
                    opticRenderer = PathOf(smr.transform, t), opticNote = "the body material's emission map lights only the head optic; drive _EmissionColor on this renderer",
                    gun = new { path = PathOf(gun, t), parent = gun.parent.name, triangles = gmesh.triangles.Length / 3, localPosition = V(gun.localPosition), localRotation = Q(gun.localRotation), localScale = V(gun.localScale),
                        material = new { gmat.name, textures = TexReport(gmat) } },
                    muzzle = new { path = PathOf(muzzle, t), parent = muzzle.parent.name, localPosition = V(muzzle.localPosition), localRotation = Q(muzzle.localRotation),
                        relativeToRightForeArm = new { position = V(fore.InverseTransformPoint(muzzle.position)), rotation = Q(Quaternion.Inverse(fore.rotation) * muzzle.rotation) },
                        inGunSpaceZ = R(muzzleInGun.z), gunMeshTipZ = R(tip), aimPose = new { position = V(aimPos, 3), forward = V(aimDir, 3), aheadOfWrist = R(wristToMuzzle, 3) },
                        fireRecoilPeak = new { forward = V(fireDir, 3), elevationDeg = R(Mathf.Asin(fireDir.y) * Mathf.Rad2Deg, 1) } },
                    toeBones = new[] { Bone("LeftToeBase"), Bone("RightToeBase") }.Select(b => PathOf(b, t)).ToArray(),
                    headBone = PathOf(Bone("Head"), t),
                    clips = reports,
                };
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }

        static object VerifyLancer(List<string> failures)
        {
            var root = PrefabUtility.LoadPrefabContents(LancerPrefab);
            try
            {
                var t = root.transform;
                Transform Find(string n) => root.GetComponentsInChildren<Transform>(true).First(x => x.name == n);
                var body = Find("Body"); var cap = Find("Lens cap"); var muzzle = Find("Muzzle");
                var rotors = new[] { "Rotor A", "Rotor B", "Rotor C", "Rotor D" }.Select(Find).ToArray();
                var rends = root.GetComponentsInChildren<MeshRenderer>(true).Where(r => r.name != "Blur disc").ToArray();
                var b = rends[0].bounds; foreach (var r in rends) b.Encapsulate(r.bounds);
                var size = t.InverseTransformVector(b.size);
                if (t.InverseTransformPoint(cap.position).z <= 0 || t.InverseTransformPoint(muzzle.position).z <= 0) failures.Add("lancer does not face +Z");
                if (t.InverseTransformDirection(muzzle.forward).z < .97f) failures.Add("lancer muzzle not pointing +Z");
                foreach (var r in rotors) if (Vector3.Dot(r.up, t.up) < .99f) failures.Add(r.name + " spin axis is not up");
                if (Mathf.Abs(Mathf.Abs(size.x) - 1.8f) > .1f) failures.Add("lancer span " + size.x);
                int Tris(Transform x) { var f = x.GetComponent<MeshFilter>(); if (!f || !f.sharedMesh) return 0; var m = f.sharedMesh; return (int)(Enumerable.Range(0, m.subMeshCount).Sum(s => (long)m.GetIndexCount(s)) / 3); }
                var bm = body.GetComponent<MeshRenderer>().sharedMaterial; var lm = cap.GetComponent<MeshRenderer>().sharedMaterial;
                return new
                {
                    prefab = LancerPrefab, guid = AssetDatabase.AssetPathToGUID(LancerPrefab), model = LancerModel,
                    span = new { x = R(Mathf.Abs(size.x), 3), y = R(Mathf.Abs(size.y), 3), z = R(Mathf.Abs(size.z), 3), boundsCenter = V(t.InverseTransformPoint(b.center), 3) },
                    body = new { path = PathOf(body, t), triangles = Tris(body), material = new { bm.name, textures = TexReport(bm) } },
                    rotors = rotors.Select(r => new { path = PathOf(r, t), pivot = V(t.InverseTransformPoint(r.position)), spinAxisLocal = "Y", triangles = Tris(r),
                        blurDisc = r.Find("Blur disc") ? PathOf(r.Find("Blur disc"), t) : null, bladeRadius = R(r.GetComponent<MeshFilter>().sharedMesh.vertices.Max(p => new Vector2(p.x, p.z).magnitude)) }).ToArray(),
                    lensCap = new { path = PathOf(cap, t), position = V(t.InverseTransformPoint(cap.position)), triangles = Tris(cap), material = new { lm.name, emission = lm.IsKeywordEnabled("_EMISSION"), gi = lm.globalIlluminationFlags.ToString(), emissionColor = lm.GetColor("_EmissionColor").ToString() } },
                    muzzle = new { path = PathOf(muzzle, t), localPosition = V(muzzle.localPosition), localRotation = Q(muzzle.localRotation), prefabPosition = V(t.InverseTransformPoint(muzzle.position)), forward = V(t.InverseTransformDirection(muzzle.forward), 3) },
                    totalTriangles = rends.Sum(r => Tris(r.transform)),
                };
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
                    object result = st switch { "import" => Import(), "prefab" => BuildPrefabs(), "verify" => Verify(), _ => throw new Exception("unknown step " + st) };
                    results[st] = result;
                    Debug.Log("OuterBermsRangedEnemies " + st + ": " + JsonConvert.SerializeObject(result));
                }
                Directory.CreateDirectory(Evidence);
                string file = Evidence + "import.json";
                var all = File.Exists(file) ? Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(file)) : new Newtonsoft.Json.Linq.JObject();
                foreach (var kv in results) all[kv.Key] = Newtonsoft.Json.Linq.JToken.FromObject(kv.Value);
                File.WriteAllText(file, all.ToString(Formatting.Indented));
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); Debug.Log("OuterBermsRangedEnemies FAILED: " + e.Message); EditorApplication.Exit(1); }
        }
    }
}
