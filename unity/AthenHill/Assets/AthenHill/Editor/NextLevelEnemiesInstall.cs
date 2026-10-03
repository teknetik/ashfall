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
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// 2 October 2026, "next level" programme, enemies pass. Three higher-level Outer Berms enemies from Carl's delivered
    /// Meshy models (meshy/incoming-20261002, prepared by meshy/next-level-enemies-20261002/prep_models.py: geometry GLBs,
    /// URP Lit texture sets, walk/run from the delivered clips and procedural idle/attack/hit/death; handoff.json):
    ///  * Scrap Reaper      (FeralScrapReaper)    level 3: fast melee walker, double-arm slash, 420 HP, armour 16;
    ///  * Ironclad Warden   (FeralIroncladWarden) RETIRED to Prefabs/OuterBerms/Retired on 2 Oct (evening): the delivered model is a
    ///                      bearded human, Carl's new Brann; the `brann` step rebuilds Prefabs/SalvageDealer.prefab on it (backup kept);
    ///  * Post Sentinel     (FeralPostSentinel)   level 3: a one-wheeled rolling ranged sentry (FeralDroid kind Wheeled, Carl's
    ///                      correction: "supposed to have a wheel to move around"), 520 HP, armour 14, 4-bolt bursts.
    /// Plus: DroidThreat levels/experience on every droid prefab, three rare loot items (apply_data.py adds them to the
    /// catalog), five loot tables, loot crates (SalvageHeapNode searches on kit crates), four POIs in the outer third of the
    /// expanse (art/next_level_20261002/enemies/sites.json from layout_nextlevel.py) under "Outer Berms/Next level sites" with
    /// encounters, QA landmarks (nextlevel_*), compass points and cam_nextlevel_* review cameras; and a fix for the ranged
    /// droid prefabs that carried a whole nested FeralWorkerDroid (their voice source was copied with its root).
    /// Idempotent: re-running replaces everything it made. Batch:
    ///   -executeMethod AthenHill.Editor.NextLevelEnemiesInstall.InstallAll -nographics -quit   (import, visuals, droids, loot, install, verify)
    ///   -executeMethod AthenHill.Editor.NextLevelEnemiesInstall.VerifyAll  -nographics -quit
    ///   -executeMethod AthenHill.Editor.NextLevelEnemiesInstall.RunBatch   --steps capture:<dir>:cam+cam  (graphics, at most 6)
    /// </summary>
    public static class NextLevelEnemiesInstall
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Record = "../../meshy/next-level-enemies-20261002/";
        const string ArtSrc = "../../art/next_level_20261002/enemies/";
        public const string Evidence = "../evidence/next-level/20261002/enemies/";
        const string Art = "Assets/AthenHill/Art/OuterBerms/NextLevel/";
        const string ModelDir = Art + "Models/", SourceDir = Art + "Source/", ClipDir = Art + "Clips/", MatDir = Art + "Materials/", TexDir = Art + "Textures/";
        const string OB = "Assets/AthenHill/Prefabs/OuterBerms/", VisualDir = OB + "Visuals/";
        const string Crafting = "Assets/AthenHill/Data/Crafting/WardCrafting.asset", City = "Assets/AthenHill/Data/CityCatalog.asset";
        public const string RootName = "Next level sites";
        static readonly string[] Keys = { "warden", "reaper" };
        static readonly Dictionary<string, string> Names = new Dictionary<string, string> { ["warden"] = "IroncladWarden", ["reaper"] = "ScrapReaper", ["sentinel"] = "PostSentinel" };
        static readonly Dictionary<string, float> Heights = new Dictionary<string, float> { ["warden"] = 1.9f, ["reaper"] = 2.05f };
        /// name, loops, lift rule (true = lowest sole over the clip; false = first frame)
        static readonly (string name, bool loop, bool liftOverClip)[] Clips = { ("idle", true, true), ("walk", true, true), ("run", true, true), ("attack", false, true), ("hit", false, true), ("death", false, false) };
        static readonly (string name, bool loop, bool liftOverClip)[] BrannClips = { ("idle", true, true), ("talk", true, true), ("walk", true, true), ("run", true, true) };
        const string DealerPrefab = "Assets/AthenHill/Prefabs/SalvageDealer.prefab", DealerBackup = "Assets/AthenHill/Prefabs/Retired/SalvageDealer_hauler_20261001.prefab", RetiredDir = OB + "Retired/";
        static JObject Handoff => JObject.Parse(File.ReadAllText(Record + "handoff.json"));
        static float R(float v, int d = 4) => (float)Math.Round(v, d);
        static float[] V(Vector3 v, int d = 3) => new[] { R(v.x, d), R(v.y, d), R(v.z, d) };
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static AudioClip Clip(string n) => AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/AthenHill/Audio/ElevenLabs/Combat/" + n + ".wav");

        // ------------------------------------------------------------------ import
        public static string Import()
        {
            foreach (var d in new[] { ModelDir, SourceDir, MatDir, TexDir, VisualDir }) Directory.CreateDirectory(d);
            foreach (var k in Keys) Directory.CreateDirectory(ClipDir + Names[k]);
            var copied = new List<string>();
            void Copy(string from, string to)
            {
                if (!File.Exists(from)) throw new FileNotFoundException("Missing record file " + from);
                if (File.Exists(to) && new FileInfo(to).Length == new FileInfo(from).Length && File.ReadAllBytes(to).SequenceEqual(File.ReadAllBytes(from))) return;
                File.Copy(from, to, true); copied.Add(to);
            }
            foreach (var k in Keys)
            {
                Copy(Record + k + "/build/" + Names[k] + "_geo.glb", ModelDir + Names[k] + ".glb");
                foreach (var c in Clips) Copy(Record + k + "/build/anim/" + c.name + ".glb", SourceDir + k + "_" + c.name + ".glb");
                if (k == "warden") Copy(Record + k + "/build/anim/talk.glb", SourceDir + k + "_talk.glb");
                foreach (var t in new[] { "BaseMap", "Normal", "Mask" }) Copy(Record + k + "/textures/" + Names[k] + "_" + t + ".png", TexDir + Names[k] + "_" + t + ".png");
            }
            Copy(Record + "sentinel/build/PostSentinel_geo.glb", ModelDir + "PostSentinel.glb");
            foreach (var t in new[] { "BaseMap", "Normal", "Mask" }) Copy(Record + "sentinel/textures/PostSentinel_" + t + ".png", TexDir + "PostSentinel_" + t + ".png");
            AssetDatabase.Refresh();
            var report = new List<object>();
            foreach (var path in Directory.GetFiles(ModelDir, "*.glb").Concat(Directory.GetFiles(SourceDir, "*.glb")).Select(p => p.Replace('\\', '/')))
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                var importer = AssetImporter.GetAtPath(path); if (!importer) throw new Exception("No importer for " + path);
                var so = new SerializedObject(importer);
                var method = so.FindProperty("importSettings.animationMethod") ?? throw new Exception("Expected glTFast import settings on " + path);
                int legacy = Array.IndexOf(method.enumNames, "Legacy"); bool changed = method.enumValueIndex != legacy;
                if (changed) { method.enumValueIndex = legacy; so.ApplyModifiedPropertiesWithoutUndo(); importer.SaveAndReimport(); }
                var clips = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().ToArray();
                if (path.StartsWith(SourceDir) && !clips.Any(c => c.legacy)) throw new Exception("No legacy clip in " + path);
                report.Add(new { path, clips = clips.Select(c => new { c.name, length = R(c.length, 3) }).ToArray(), animationMethodChanged = changed });
            }
            var textures = new List<object>();
            foreach (var path in Directory.GetFiles(TexDir, "*.png").Select(p => p.Replace('\\', '/')))
            {
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                var file = Path.GetFileNameWithoutExtension(path); bool normal = file.EndsWith("_Normal"), linear = file.EndsWith("_Mask");
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !normal && !linear; ti.alphaSource = file.EndsWith("_Mask") ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                ti.maxTextureSize = 2048; ti.anisoLevel = 8; ti.mipmapEnabled = true; ti.streamingMipmaps = true; ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
                var t = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                textures.Add(new { path, t.width, t.height, format = t.format.ToString() });
            }
            var mats = new[] { "IroncladWarden", "ScrapReaper", "PostSentinel" }.Select(n => RobotMaterial("NL_" + n, n)).Select(m => AssetDatabase.GetAssetPath(m)).ToArray();
            AssetDatabase.SaveAssets();
            Write("import.json", new { copied, report, textures, materials = mats });
            return $"import: {copied.Count} files copied, {report.Count} glTF assets, {textures.Count} textures, {mats.Length} materials";
        }

        static Material RobotMaterial(string name, string stem)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            var path = MatDir + name + ".mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
            m.shader = shader;
            Texture2D T(string s) { var x = AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + stem + "_" + s + ".png"); if (!x) throw new Exception("Missing texture " + stem + "_" + s); return x; }
            m.SetTexture("_BaseMap", T("BaseMap")); m.SetColor("_BaseColor", Color.white);
            m.SetTexture("_BumpMap", T("Normal")); m.SetFloat("_BumpScale", 1f); m.EnableKeyword("_NORMALMAP");
            m.SetTexture("_MetallicGlossMap", T("Mask")); m.EnableKeyword("_METALLICSPECGLOSSMAP"); m.SetFloat("_Smoothness", 1);
            m.SetTexture("_EmissionMap", null); m.SetColor("_EmissionColor", Color.black); m.DisableKeyword("_EMISSION"); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack;
            m.SetFloat("_Cull", 2); m.doubleSidedGI = false; m.enableInstancing = true;
            EditorUtility.SetDirty(m); return m;
        }

        // ------------------------------------------------------------------ visual prefabs (as OuterBermsRangedEnemies)
        static Vector3[] Skin(SkinnedMeshRenderer r, Transform space)
        {
            var mesh = r.sharedMesh; var bones = r.bones; var bind = mesh.bindposes;
            var m = new Matrix4x4[bones.Length];
            for (int i = 0; i < m.Length; i++) m[i] = space.worldToLocalMatrix * bones[i].localToWorldMatrix * bind[i];
            var v = mesh.vertices; var w = mesh.boneWeights; var p = new Vector3[v.Length];
            for (int i = 0; i < v.Length; i++)
            {
                var b = w[i];
                p[i] = m[b.boneIndex0].MultiplyPoint3x4(v[i]) * b.weight0 + m[b.boneIndex1].MultiplyPoint3x4(v[i]) * b.weight1 + m[b.boneIndex2].MultiplyPoint3x4(v[i]) * b.weight2 + m[b.boneIndex3].MultiplyPoint3x4(v[i]) * b.weight3;
            }
            return p;
        }

        static AnimationClip SourceClip(string key, string name)
        {
            var clip = AssetDatabase.LoadAllAssetsAtPath(SourceDir + key + "_" + name + ".glb").OfType<AnimationClip>().FirstOrDefault(c => c && c.legacy);
            return clip ? clip : throw new Exception("No legacy source clip " + key + "_" + name);
        }

        static Transform ResolveHost(GameObject rig, Transform wrapper, AnimationClip clip, List<string> log)
        {
            var paths = AnimationUtility.GetCurveBindings(clip).Select(b => b.path).Distinct().ToArray();
            bool All(Transform t) => paths.All(p => p.Length == 0 || t.Find(p) != null);
            foreach (var t in rig.GetComponentsInChildren<Transform>(true).Prepend(wrapper)) if (All(t)) { log.Add("clip paths resolve from '" + t.name + "'"); return t; }
            var first = paths.Select(p => p.Split('/')[0]).Distinct().ToArray();
            if (first.Length == 1 && rig.name != first[0]) { log.Add("instance root renamed '" + rig.name + "' -> '" + first[0] + "'"); rig.name = first[0]; if (All(wrapper)) return wrapper; }
            throw new Exception("Clip paths do not resolve on the rig: " + string.Join(", ", paths.Take(5)));
        }

        static float CloseLoop(AnimationCurve curve, float seconds)
        {
            var keys = curve.keys; float end = keys[keys.Length - 1].time, start = keys[0].time; float seam = Mathf.Abs(keys[keys.Length - 1].value - keys[0].value);
            seconds = Mathf.Min(seconds, (end - start) * .25f);
            for (int i = 0; i < keys.Length; i++) { float w = Mathf.InverseLerp(end - seconds, end, keys[i].time); if (w <= 0) continue; w = w * w * (3 - 2 * w); keys[i].value = Mathf.Lerp(keys[i].value, keys[0].value, w); }
            curve.keys = keys;
            for (int i = 0; i < curve.length; i++) { AnimationUtility.SetKeyLeftTangentMode(curve, i, AnimationUtility.TangentMode.ClampedAuto); AnimationUtility.SetKeyRightTangentMode(curve, i, AnimationUtility.TangentMode.ClampedAuto); }
            return seam;
        }

        static object DeriveClip(AnimationClip source, string target, string name, Vector3 rootOffset, bool loop, string rootBone)
        {
            var wrap = loop ? WrapMode.Loop : name == "death" ? WrapMode.ClampForever : WrapMode.Once;
            var clip = new AnimationClip { name = name, legacy = true, frameRate = source.frameRate, wrapMode = wrap };
            int kept = 0, dropped = 0, root = 0; float seam = 0;
            foreach (var binding in AnimationUtility.GetCurveBindings(source))
            {
                string prop = binding.propertyName;
                bool rotation = prop.StartsWith("m_LocalRotation") || prop.StartsWith("localRotation");
                bool rootPos = (prop.StartsWith("m_LocalPosition") || prop.StartsWith("localPosition")) && (binding.path == rootBone || binding.path.EndsWith("/" + rootBone));
                if (!rotation && !rootPos) { dropped++; continue; }
                var curve = AnimationUtility.GetEditorCurve(source, binding);
                if (rootPos) { float add = prop.EndsWith(".x") ? rootOffset.x : prop.EndsWith(".y") ? rootOffset.y : rootOffset.z; var keys = curve.keys; for (int i = 0; i < keys.Length; i++) keys[i].value += add; curve.keys = keys; root++; }
                if (loop && curve.length > 2) seam = Mathf.Max(seam, CloseLoop(curve, .3f));
                clip.SetCurve(binding.path, typeof(Transform), prop.Replace("m_LocalRotation", "localRotation").Replace("m_LocalPosition", "localPosition"), curve);
                kept++;
            }
            if (root != 3) throw new Exception("Expected " + rootBone + " x/y/z translation curves in " + source.name + ", found " + root);
            clip.EnsureQuaternionContinuity();
            var existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(target);
            if (existing) { EditorUtility.CopySerialized(clip, existing); existing.name = name; Object.DestroyImmediate(clip); EditorUtility.SetDirty(existing); }
            else AssetDatabase.CreateAsset(clip, target);
            return new { target, length = R(source.length, 3), wrap = wrap.ToString(), curvesKept = kept, curvesDropped = dropped, loopSeamCorrection = R(seam) };
        }

        public static string Visuals()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var results = new Dictionary<string, object>();
            results["reaper"] = BuildBiped("reaper");   // the warden model is Brann now (brann step)
            results["sentinel"] = BuildSentinelVisual();
            AssetDatabase.SaveAssets();
            Write("visuals.json", results);
            return "visuals: " + string.Join(", ", results.Keys);
        }

        static object BuildBiped(string key)
        {
            var log = new List<string>(); string name = Names[key];
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelDir + name + ".glb"); if (!model) throw new Exception("Run the import step first: " + name);
            var root = new GameObject(name + "Visual");
            try
            {
                var visual = new GameObject("Visual").transform; visual.SetParent(root.transform, false);
                var rig = (GameObject)PrefabUtility.InstantiatePrefab(model); rig.transform.SetParent(visual, false);
                var smrs = rig.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                if (smrs.Length != 1 || !smrs[0].sharedMesh) throw new Exception(name + " import must contain one skinned mesh, found " + smrs.Length);
                var smr = smrs[0];
                var sources = Clips.ToDictionary(c => c.name, c => SourceClip(key, c.name));
                var host = ResolveHost(rig, visual, sources["idle"], log);
                foreach (var c in Clips) if (ResolveHost(rig, visual, sources[c.name], new List<string>()) != host) throw new Exception(c.name + " binds to a different root");
                var anims = rig.GetComponentsInChildren<Animation>(true).Concat(visual.GetComponents<Animation>()).ToArray();
                var anim = host.GetComponent<Animation>();
                if (!anim) { anim = host.gameObject.AddComponent<Animation>(); log.Add("Animation added on '" + host.name + "'"); }
                foreach (var other in anims) if (other != anim) { Object.DestroyImmediate(other); log.Add("extra Animation removed from '" + other.name + "'"); }
                sources["idle"].SampleAnimation(host.gameObject, 0);
                var pts = Skin(smr, root.transform);
                float standing = pts.Max(p => p.y) - pts.Min(p => p.y), scale = Heights[key] / standing;
                visual.localScale = Vector3.one * scale; log.Add($"standing idle height {standing:F4} m at import scale; uniform scale {scale:F4} -> {Heights[key]} m");
                var bones = host.GetComponentsInChildren<Transform>(true);
                Transform Bone(string n) => bones.FirstOrDefault(t => t.name == n) ?? throw new Exception("Missing bone " + n);
                var head = Bone("head"); var front = Bone("headfront");
                if ((root.transform.InverseTransformPoint(front.position) - root.transform.InverseTransformPoint(head.position)).z < 0) { visual.localRotation = Quaternion.Euler(0, 180, 0); log.Add("visual turned 180 degrees to face +Z"); }
                var pelvis = Bone("pelvis"); var derived = new Dictionary<string, object>();
                foreach (var c in Clips)
                {
                    var src = sources[c.name]; float low = float.MaxValue; int n = Mathf.Max(8, Mathf.CeilToInt(src.length * 15));
                    for (int k = 0; k <= (c.liftOverClip ? n : 0); k++) { src.SampleAnimation(host.gameObject, src.length * k / n); low = Mathf.Min(low, Skin(smr, root.transform).Min(p => p.y)); }
                    var offset = pelvis.parent.InverseTransformVector(new Vector3(0, -low, 0));
                    derived[c.name] = new { liftMetres = R(-low), rule = c.liftOverClip ? "lowest point over the clip" : "first frame", clip = DeriveClip(src, ClipDir + name + "/" + c.name + ".anim", c.name, offset, c.loop, "pelvis") };
                }
                AssetDatabase.SaveAssets();
                var clips = Clips.Select(c => AssetDatabase.LoadAssetAtPath<AnimationClip>(ClipDir + name + "/" + c.name + ".anim")).ToArray();
                smr.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "NL_" + name + ".mat");
                smr.shadowCastingMode = ShadowCastingMode.On; smr.receiveShadows = true; smr.skinnedMotionVectors = true;
                anim.playAutomatically = false; anim.clip = clips[0]; anim.cullingType = AnimationCullingType.BasedOnRenderers;
                AnimationUtility.SetAnimationClips(anim, clips);
                var space = smr.rootBone ? smr.rootBone : smr.transform; var lo = Vector3.one * float.MaxValue; var hi = -lo;
                foreach (var clip in clips)
                {
                    int n = Mathf.Max(2, Mathf.CeilToInt(clip.length * 15));
                    for (int k = 0; k <= n; k++) { clip.SampleAnimation(host.gameObject, clip.length * k / n); foreach (var p in Skin(smr, space)) { lo = Vector3.Min(lo, p); hi = Vector3.Max(hi, p); } }
                }
                var env = new Bounds(); env.SetMinMax(lo, hi); smr.localBounds = new Bounds(env.center, env.size * 1.24f); smr.updateWhenOffscreen = false;
                clips[0].SampleAnimation(host.gameObject, 0);
                var prefab = PrefabUtility.SaveAsPrefabAsset(root, VisualDir + name + "Visual.prefab", out bool ok);
                if (!ok || !prefab) throw new Exception(name + " visual prefab save failed");
                return new { prefab = VisualDir + name + "Visual.prefab", host = host.name, scale = R(scale), log, clips = derived, triangles = smr.sharedMesh.triangles.Length / 3, bones = smr.bones.Length, envelopeSize = V(env.size, 2) };
            }
            finally { Object.DestroyImmediate(root); }
        }

        static object BuildSentinelVisual()
        {
            var log = new List<string>();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelDir + "PostSentinel.glb"); if (!model) throw new Exception("Run the import step first: PostSentinel");
            var root = new GameObject("PostSentinelVisual");
            try
            {
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(model); inst.transform.SetParent(root.transform, false); inst.name = "Visual";
                // glTFast folds a single scene root node into the prefab root, so 'Body' may be the instance itself: find it by its mesh
                var all = inst.GetComponentsInChildren<Transform>(true);
                Transform Find(string n) => all.FirstOrDefault(t => t.name == n) ?? all.FirstOrDefault(t => t.GetComponent<MeshFilter>() && t.GetComponent<MeshFilter>().sharedMesh && t.GetComponent<MeshFilter>().sharedMesh.name == n)
                    ?? throw new Exception("Sentinel model is missing " + n + " (hierarchy: " + string.Join(", ", all.Select(t => t.name)) + ")");
                var body = Find("Body"); var wheel = Find("Wheel"); var muzzle = Find("Muzzle"); var head = Find("Head"); var hat = Find("Hat");
                log.Add("hierarchy: " + string.Join(" / ", all.Select(t => t.name)));
                if (inst.transform.InverseTransformPoint(muzzle.position).z < 0) { inst.transform.localRotation = Quaternion.Euler(0, 180, 0); log.Add("visual turned 180 degrees to face +Z"); }
                var mat = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "NL_PostSentinel.mat");
                foreach (var r in new[] { body, wheel }.Select(t => t.GetComponent<MeshRenderer>())) { if (!r) throw new Exception("Body/Wheel without a MeshRenderer"); r.sharedMaterial = mat; r.shadowCastingMode = ShadowCastingMode.On; }
                var prefab = PrefabUtility.SaveAsPrefabAsset(root, VisualDir + "PostSentinelVisual.prefab", out bool ok);
                if (!ok || !prefab) throw new Exception("Sentinel visual prefab save failed");
                var rends = root.GetComponentsInChildren<MeshRenderer>(); var b = rends[0].bounds; foreach (var r in rends) b.Encapsulate(r.bounds);
                return new { prefab = VisualDir + "PostSentinelVisual.prefab", log, height = R(b.size.y), wheelPivot = V(root.transform.InverseTransformPoint(wheel.position)), muzzle = V(root.transform.InverseTransformPoint(muzzle.position)), head = V(root.transform.InverseTransformPoint(head.position)), hatTop = R(b.max.y) };
            }
            finally { Object.DestroyImmediate(root); }
        }

        // ------------------------------------------------------------------ gameplay prefabs
        class DroidSpec
        {
            public string key, prefab, visual, display, loot; public DroidKind kind; public DroidAttack attack; public float health, armour, aimY, capRadius, capHeight;
            public int level, experience; public bool glow, eye; public Action<FeralDroid> tune;
        }

        public static string Droids()
        {
            var log = new List<string>();
            var worker = AssetDatabase.LoadAssetAtPath<GameObject>(OB + "FeralWorkerDroid.prefab");
            var h = Handoff;
            float Speed(string k, string c) => (float)h[k]["clips"][c]["native_speed_mps"];
            float Impact(string k) => (float)h[k]["clips"]["attack"]["impact_normalized"];
            var specs = new[]
            {
                // Scrap Reaper (retuned after the first native batch, nl1: three took 112 rifle shots and 5 knock-downs). 400 HP behind 14
                // armour: the precision-barrel rifle (pen 16) lands its full 28 a shot -> 14-15 hits; the starter pistol lands 20 -> 20 shots
                // under its nano cap while three of them close at 4.6 m/s. Strikes 18 (7 on the full kit), 0.6 s tell, staggers at 60.
                new DroidSpec { key = "reaper", prefab = "FeralScrapReaper", visual = "ScrapReaperVisual", display = "Scrap Reaper", loot = "loot_scrap_reaper", kind = DroidKind.Walker, attack = DroidAttack.Melee,
                    health = 400, armour = 14, aimY = 1.35f, capRadius = .45f, capHeight = 2.05f, level = 3, experience = 60, glow = true, eye = true,
                    tune = d => { d.wanderSpeed = 1.3f; d.chaseSpeed = 4.6f; d.turnSpeed = 9; d.aggroRadius = 30; d.leashRadius = 60; d.attackRange = 2.0f; d.wanderRadius = 4; d.alertSeconds = .5f; d.windupSeconds = .6f; d.recoverSeconds = .9f;
                        d.staggerSeconds = .3f; d.staggerImmunity = 1.4f; d.staggerThreshold = 60; d.strikeDamage = 18; d.repairPerSecond = 10; d.flank = .5f; d.separation = 1.8f; d.idleThrottleDistance = 70; d.walkStrideSpeed = Speed("reaper", "walk"); d.runStrideSpeed = Speed("reaper", "run"); d.attackImpact = Impact("reaper"); } },
                // Post Sentinel: rolling ranged sentry (kind Wheeled). Retuned after nl1 (its bursts put the kitted player down in seconds):
                // 560 HP / armour 14 -> 20 rifle hits; 3-bolt bursts of 16 at 0.25 s after a 1.2 s laser tell, less lead and more spread
                // (strafing beats it), longer pauses. On the full kit a volley costs ~16, on the bare starter 37.
                new DroidSpec { key = "sentinel", prefab = "FeralPostSentinel", visual = "PostSentinelVisual", display = "Post Sentinel", loot = "loot_post_sentinel", kind = DroidKind.Wheeled, attack = DroidAttack.Ranged,
                    health = 560, armour = 14, aimY = 1.2f, capRadius = .34f, capHeight = 1.9f, level = 3, experience = 70, glow = true, eye = true,
                    tune = d => { d.wanderSpeed = 2.0f; d.wanderRadius = 9; d.chaseSpeed = 5.0f; d.strafeSpeed = 3.2f; d.turnSpeed = 5; d.aggroRadius = 36; d.leashRadius = 70; d.fireRange = 40; d.preferredRange = 22; d.retreatRange = 9;
                        d.burstCount = 3; d.burstInterval = .25f; d.boltSpeed = 34; d.boltDamage = 16; d.aimSpread = 2.0f; d.leadFactor = .35f; d.windupSeconds = 1.2f; d.volleyPause = new Vector2(2.0f, 3.2f); d.repairPerSecond = 6; d.separation = 2.4f; d.idleThrottleDistance = 90;
                        d.windupClip = Clip("gunner-aim"); d.fireClip = Clip("gunner-fire"); d.wheelRadius = (float)h["sentinel"]["wheel"]["radius"]; d.leanPerTurnRate = .05f; d.pitchPerAccel = 1.5f; d.maxLean = 12; d.wreckMaxTravel = 2f; } },
            };
            foreach (var s in specs) log.Add(BuildDroid(s, worker));
            log.Add(RetireWarden());
            log.Add(ThreatOnExistingPrefabs());
            log.Add(FixNestedDroids());
            AssetDatabase.SaveAssets();
            Write("droids.json", new { log });
            return string.Join("; ", log);
        }

        static string BuildDroid(DroidSpec s, GameObject template)
        {
            var visual = AssetDatabase.LoadAssetAtPath<GameObject>(VisualDir + s.visual + ".prefab") ?? throw new Exception("Run the visuals step first: " + s.visual);
            var t = template.GetComponent<FeralDroid>();
            var root = new GameObject(s.prefab);
            try
            {
                var vis = (GameObject)PrefabUtility.InstantiatePrefab(visual); vis.transform.SetParent(root.transform, false); vis.name = "Visual"; vis.transform.SetAsFirstSibling();
                var h = root.AddComponent<Health>(); h.max = s.health; h.aimOffset = new Vector3(0, s.aimY, 0);
                var d = root.AddComponent<FeralDroid>();
                d.kind = s.kind; d.attackMode = s.attack; d.displayName = s.display; d.armour = s.armour; d.armourMinFraction = .25f;
                s.tune(d);
                var all = vis.GetComponentsInChildren<Transform>(true);
                Transform Find(string n) => all.FirstOrDefault(x => x.name == n);
                var anim = vis.GetComponentInChildren<Animation>(true);
                if (anim)
                {
                    anim.playAutomatically = false; d.animationSource = anim;
                    AnimationClip C(string n) => AnimationUtility.GetAnimationClips(anim.gameObject).FirstOrDefault(c => c && c.name == n);
                    d.idle = C("idle"); d.walk = C("walk"); d.run = C("run"); d.attack = C("attack"); d.hit = C("hit"); d.death = C("death");
                    d.feet = new[] { Find("ball_l"), Find("ball_r") }.Where(x => x).ToArray();
                }
                var head = Find("head") ?? Find("Head");
                if (s.attack == DroidAttack.Ranged)
                {
                    d.muzzle = Find("Muzzle") ?? throw new Exception(s.prefab + ": no Muzzle in the visual");
                    var boltPath = OB + "DroidBolt_Sentinel.prefab";
                    if (!AssetDatabase.LoadAssetAtPath<DroidBolt>(boltPath)) { if (!AssetDatabase.CopyAsset("Assets/AthenHill/Prefabs/BermsExpanse/DroidBolt_Gunner.prefab", boltPath)) throw new Exception("could not copy the gunner bolt"); }
                    d.boltPrefab = AssetDatabase.LoadAssetAtPath<DroidBolt>(boltPath); d.fireClipPerShot = false;
                    var laserMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/BermsExpanse/Materials/DroidAimLaser.mat") ?? throw new Exception("DroidAimLaser.mat missing (expansion droids step)");
                    var laser = new GameObject("Aim laser", typeof(LineRenderer)).GetComponent<LineRenderer>(); laser.transform.SetParent(root.transform, false);
                    laser.useWorldSpace = true; laser.positionCount = 2; laser.sharedMaterial = laserMat; laser.widthMultiplier = .02f; laser.numCapVertices = 2;
                    laser.shadowCastingMode = ShadowCastingMode.Off; laser.receiveShadows = false; laser.enabled = false;
                    laser.colorGradient = new Gradient { colorKeys = new[] { new GradientColorKey(new Color(1, .35f, .12f), 0), new GradientColorKey(new Color(1, .2f, .08f), 1) }, alphaKeys = new[] { new GradientAlphaKey(.9f, 0), new GradientAlphaKey(.35f, 1) } };
                    d.aimLaser = laser;
                }
                if (s.kind == DroidKind.Wheeled) d.wheel = Find("Wheel") ?? throw new Exception("no Wheel node");
                // presentation from the worker template: clips by reference, FX objects as copies; the voice source is rebuilt on
                // its own child (the template's lives on the worker root; instantiating that root is how the gunner got a whole
                // worker droid nested inside it)
                d.alertClip = t.alertClip; d.strikeClip = t.strikeClip; d.hitClip = t.hitClip; d.deathClip = t.deathClip; d.footstepClips = t.footstepClips; d.footstepVolume = t.footstepVolume;
                if (s.attack == DroidAttack.Melee) d.windupClip = t.windupClip;   // ranged: the tune set its own aim clip
                d.glowCalm = t.glowCalm; d.glowHostile = t.glowHostile; d.glowWindup = t.glowWindup;
                Transform CopyChild(Component c, string name = null)
                {
                    if (!c || c.transform == template.transform) return null;
                    var g = Object.Instantiate(c.gameObject, root.transform); g.name = name ?? c.gameObject.name; g.transform.localPosition = c.transform.localPosition; g.transform.localRotation = c.transform.localRotation; return g.transform;
                }
                var voice = new GameObject("Voice", typeof(AudioSource)).GetComponent<AudioSource>(); voice.transform.SetParent(root.transform, false); voice.transform.localPosition = new Vector3(0, s.aimY, 0);
                if (t.voice) EditorUtility.CopySerialized(t.voice, voice);
                voice.playOnAwake = false; voice.clip = null; voice.loop = false; d.voice = voice;
                var sp = CopyChild(t.sparks); d.sparks = sp ? sp.GetComponent<ParticleSystem>() : null;
                var sm = CopyChild(t.smoke); d.smoke = sm ? sm.GetComponent<ParticleSystem>() : null; if (sm) sm.localPosition = new Vector3(0, s.aimY, 0);
                if (s.kind == DroidKind.Walker && t.footDust) { var fd = CopyChild(t.footDust); d.footDust = fd.GetComponent<ParticleSystem>(); }
                if (s.glow && head)
                {
                    // the worker's own glow renderer is its skinned body (emission map), so the new droids get a small emissive lens
                    // sphere at the head front that FeralDroid tints through _EmissionColor
                    var g = GameObject.CreatePrimitive(PrimitiveType.Sphere); g.name = "Optic glow"; Object.DestroyImmediate(g.GetComponent<Collider>());
                    g.transform.SetParent(head, false); var front = Find("headfront");
                    g.transform.position = front ? front.position + (front.position - head.position).normalized * .015f : head.position + root.transform.forward * .16f;
                    g.transform.localScale = Vector3.one * (s.kind == DroidKind.Wheeled ? .07f : .08f) / Mathf.Max(.01f, head.lossyScale.x);
                    var gr = g.GetComponent<MeshRenderer>(); gr.sharedMaterial = GlowMaterial(); gr.shadowCastingMode = ShadowCastingMode.Off; gr.receiveShadows = false;
                    d.glowRenderers = new Renderer[] { gr };
                }
                else d.glowRenderers = new Renderer[0];
                if (s.eye && t.eyeLight)
                {
                    var eye = Object.Instantiate(t.eyeLight.gameObject, root.transform); eye.name = "Optic light"; d.eyeLight = eye.GetComponent<Light>();
                    if (head) { eye.transform.SetParent(head, true); eye.transform.position = head.position + root.transform.forward * .18f; } else eye.transform.localPosition = new Vector3(0, s.aimY + .4f, .2f);
                }
                var cap = root.AddComponent<CapsuleCollider>(); cap.center = new Vector3(0, s.capHeight / 2, 0); cap.height = s.capHeight; cap.radius = s.capRadius;
                var rb = root.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false; rb.mass = s.kind == DroidKind.Wheeled ? 60 : 120; rb.angularDamping = .5f;
                var loot = root.AddComponent<LootSource>(); loot.lootTableId = s.loot;
                var threat = root.AddComponent<DroidThreat>(); threat.level = s.level; threat.experience = s.experience;
                PrefabUtility.SaveAsPrefabAsset(root, OB + s.prefab + ".prefab");
                return s.prefab + (anim ? " (clips " + AnimationUtility.GetAnimationClips(anim.gameObject).Length + ")" : " (wheeled)");
            }
            finally { Object.DestroyImmediate(root); }
        }

        static Material GlowMaterial()
        {
            var path = MatDir + "NL_OpticGlow.mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "NL_OpticGlow" }; AssetDatabase.CreateAsset(m, path); }
            m.SetColor("_BaseColor", new Color(.25f, .05f, .02f)); m.SetFloat("_Smoothness", .9f); m.SetFloat("_Metallic", 0);
            m.SetColor("_EmissionColor", new Color(1.1f, .45f, .1f)); m.EnableKeyword("_EMISSION"); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive; m.enableInstancing = true;
            EditorUtility.SetDirty(m); return m;
        }

        /// The hostile Ironclad Warden is retired (its model is Brann): the gameplay prefab and its visual move to Retired/
        /// folders, keeping their GUIDs and setup, so they can be put back by moving them.
        static string RetireWarden()
        {
            Directory.CreateDirectory(RetiredDir); Directory.CreateDirectory(VisualDir + "Retired/"); AssetDatabase.Refresh();
            var moved = new List<string>();
            foreach (var (from, to) in new[] { (OB + "FeralIroncladWarden.prefab", RetiredDir + "FeralIroncladWarden.prefab"), (VisualDir + "IroncladWardenVisual.prefab", VisualDir + "Retired/IroncladWardenVisual.prefab") })
            {
                if (!AssetDatabase.LoadAssetAtPath<GameObject>(from)) continue;
                if (AssetDatabase.LoadAssetAtPath<GameObject>(to)) AssetDatabase.DeleteAsset(to);
                var err = AssetDatabase.MoveAsset(from, to); if (!string.IsNullOrEmpty(err)) throw new Exception("retire: " + err);
                moved.Add(Path.GetFileName(to));
            }
            return "retired: " + (moved.Count > 0 ? string.Join(", ", moved) : "already retired");
        }

        // ------------------------------------------------------------------ Brann on the delivered human rig
        /// Rebuilds Prefabs/SalvageDealer.prefab in place (same GUID and root objects, so the scene instance, NPC root, dialogue,
        /// counter position, routes and ActorLookAt wiring stay): the Visual child becomes the delivered rig at 1.8 m, with the
        /// delivered walk/run and the procedural idle/talk, legacy Animation driven by ActorAnimation. The previous Meshy hauler
        /// is copied once to Prefabs/Retired/SalvageDealer_hauler_20261001.prefab.
        public static string Brann()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            Directory.CreateDirectory("Assets/AthenHill/Prefabs/Retired"); Directory.CreateDirectory(ClipDir + "Brann"); AssetDatabase.Refresh();
            if (!AssetDatabase.LoadAssetAtPath<GameObject>(DealerBackup) && !AssetDatabase.CopyAsset(DealerPrefab, DealerBackup)) throw new Exception("could not back up " + DealerPrefab);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelDir + "IroncladWarden.glb") ?? throw new Exception("Run the import step first");
            var h = Handoff; var log = new List<string>();
            var root = PrefabUtility.LoadPrefabContents(DealerPrefab);
            try
            {
                var old = root.transform.Find("Visual"); if (old) { Object.DestroyImmediate(old.gameObject); log.Add("previous Visual removed (hauler kept in " + DealerBackup + ")"); }
                var visual = new GameObject("Visual").transform; visual.SetParent(root.transform, false); visual.SetAsFirstSibling();
                var rig = (GameObject)PrefabUtility.InstantiatePrefab(model, root.scene); rig.transform.SetParent(visual, false);
                var smr = rig.GetComponentsInChildren<SkinnedMeshRenderer>(true).Single();
                var sources = BrannClips.ToDictionary(c => c.name, c => SourceClip("warden", c.name));
                var host = ResolveHost(rig, visual, sources["idle"], log);
                foreach (var c in BrannClips) if (ResolveHost(rig, visual, sources[c.name], new List<string>()) != host) throw new Exception(c.name + " binds to a different root");
                var anim = host.GetComponent<Animation>(); if (!anim) anim = host.gameObject.AddComponent<Animation>();   // Editor GetComponent returns a fake null
                foreach (var other in rig.GetComponentsInChildren<Animation>(true).Concat(visual.GetComponents<Animation>())) if (other != anim) Object.DestroyImmediate(other);
                sources["idle"].SampleAnimation(host.gameObject, 0);
                var pts = Skin(smr, root.transform); float standing = pts.Max(q => q.y) - pts.Min(q => q.y), scale = 1.8f / standing;
                visual.localScale = Vector3.one * scale; log.Add($"standing idle {standing:F4} m at import scale; uniform scale {scale:F4} -> 1.80 m");
                var bones = host.GetComponentsInChildren<Transform>(true);
                Transform Bone(string n) => bones.FirstOrDefault(t => t.name == n) ?? throw new Exception("Missing bone " + n);
                var head = Bone("head"); var neck = Bone("neck_01"); var front = Bone("headfront"); var pelvis = Bone("pelvis");
                if ((root.transform.InverseTransformPoint(front.position) - root.transform.InverseTransformPoint(head.position)).z < 0) { visual.localRotation = Quaternion.Euler(0, 180, 0); log.Add("visual turned 180 degrees to face +Z"); }
                var derived = new Dictionary<string, object>();
                foreach (var c in BrannClips)
                {
                    var src = sources[c.name]; float low = float.MaxValue; int n = Mathf.Max(8, Mathf.CeilToInt(src.length * 15));
                    for (int k = 0; k <= n; k++) { src.SampleAnimation(host.gameObject, src.length * k / n); low = Mathf.Min(low, Skin(smr, root.transform).Min(q => q.y)); }
                    var offset = pelvis.parent.InverseTransformVector(new Vector3(0, -low, 0));
                    derived[c.name] = new { liftMetres = R(-low), clip = DeriveClip(src, ClipDir + "Brann/" + c.name + ".anim", c.name, offset, c.loop, "pelvis") };
                }
                AssetDatabase.SaveAssets();
                var clips = BrannClips.ToDictionary(c => c.name, c => AssetDatabase.LoadAssetAtPath<AnimationClip>(ClipDir + "Brann/" + c.name + ".anim"));
                smr.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "NL_IroncladWarden.mat");
                smr.shadowCastingMode = ShadowCastingMode.On; smr.receiveShadows = true; smr.skinnedMotionVectors = true;
                smr.renderingLayerMask = 129;   // default + InteriorLighting (7): the scene instance carried this as an override on the old renderer
                anim.playAutomatically = false; anim.clip = clips["idle"]; anim.cullingType = AnimationCullingType.AlwaysAnimate;
                AnimationUtility.SetAnimationClips(anim, BrannClips.Select(c => clips[c.name]).ToArray());
                var space = smr.rootBone ? smr.rootBone : smr.transform; var lo = Vector3.one * float.MaxValue; var hi = -lo;
                foreach (var clip in clips.Values) { int n = Mathf.Max(2, Mathf.CeilToInt(clip.length * 15)); for (int k = 0; k <= n; k++) { clip.SampleAnimation(host.gameObject, clip.length * k / n); foreach (var q in Skin(smr, space)) { lo = Vector3.Min(lo, q); hi = Vector3.Max(hi, q); } } }
                var env = new Bounds(); env.SetMinMax(lo, hi); smr.localBounds = new Bounds(env.center, env.size * 1.24f); smr.updateWhenOffscreen = false;
                var actor = root.GetComponent<ActorAnimation>(); if (!actor) actor = root.AddComponent<ActorAnimation>();
                actor.animationSource = anim; actor.idle = clips["idle"]; actor.talk = clips["talk"]; actor.walk = clips["walk"]; actor.run = clips["run"];
                actor.walkStrideSpeed = (float)h["warden"]["clips"]["walk"]["native_speed_mps"]; actor.runStrideSpeed = (float)h["warden"]["clips"]["run"]["native_speed_mps"];
                actor.randomIdlePhase = true; actor.idleSpeedJitter = .08f;
                var look = root.GetComponent<ActorLookAt>(); if (!look) look = root.AddComponent<ActorLookAt>();
                look.actor = actor; look.head = head; look.neck = neck;
                clips["idle"].SampleAnimation(host.gameObject, 0);
                PrefabUtility.SaveAsPrefabAsset(root, DealerPrefab);
                Write("brann.json", new { prefab = DealerPrefab, backup = DealerBackup, scale = R(scale), log, clips = derived, triangles = smr.sharedMesh.triangles.Length / 3, bones = smr.bones.Length, look = new { head = head.name, neck = neck.name }, strides = new { actor.walkStrideSpeed, actor.runStrideSpeed } });
                return $"brann: SalvageDealer rebuilt on the delivered rig (scale {scale:F3}, {BrannClips.Length} clips), hauler backed up to {DealerBackup}";
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }

        /// DroidThreat on the five earlier prefabs (level 1 depot droids, 2 ranged, 3 Foreman); armour stays 0 there.
        static string ThreatOnExistingPrefabs()
        {
            var values = new (string file, int level, int xp)[] { ("FeralWorkerDroid", 1, 12), ("FeralScrapDrone", 1, 8), ("FeralGunnerDroid", 2, 25), ("FeralLancerDrone", 2, 30), ("FeralDepotForeman", 3, 150) };
            var done = new List<string>();
            foreach (var (file, level, xp) in values)
            {
                var path = OB + file + ".prefab"; if (!AssetDatabase.LoadAssetAtPath<GameObject>(path)) { done.Add(file + ": missing"); continue; }
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var th = root.GetComponent<DroidThreat>(); if (!th) th = root.AddComponent<DroidThreat>();
                    th.level = level; th.experience = xp;
                    var fd = root.GetComponent<FeralDroid>(); if (fd && fd.attackMode == DroidAttack.Ranged) fd.separation = 2.4f;   // gunner/lancer stacking fix (nl1)
                    PrefabUtility.SaveAsPrefabAsset(root, path); done.Add($"{file} L{level}/{xp}xp");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            return "threat: " + string.Join(", ", done);
        }

        /// The gunner/lancer prefabs (BermsExpanseInstall.Droids, 2 Oct) copied their template's voice/motor AudioSources by
        /// instantiating the component's GameObject, which was the whole worker/drone prefab root: a complete second FeralDroid
        /// nested inside each ranged droid (Carl: "the feral gunners seem to be attached to the other droids"). Moves the audio
        /// sources the outer droid references onto fresh children and removes the nested droid. Idempotent.
        static string FixNestedDroids()
        {
            var fixedList = new List<string>();
            foreach (var file in new[] { "FeralGunnerDroid", "FeralLancerDrone" })
            {
                var path = OB + file + ".prefab"; if (!AssetDatabase.LoadAssetAtPath<GameObject>(path)) continue;
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var outer = root.GetComponent<FeralDroid>();
                    var nested = root.GetComponentsInChildren<FeralDroid>(true).Where(x => x != outer).Select(x => x.gameObject).Distinct().ToArray();
                    if (nested.Length == 0) { fixedList.Add(file + ": clean"); continue; }
                    AudioSource Move(AudioSource src, string name)
                    {
                        if (!src || !nested.Any(n => src.transform == n.transform || src.transform.IsChildOf(n.transform))) return src;
                        var go = new GameObject(name, typeof(AudioSource)); go.transform.SetParent(root.transform, false); go.transform.position = src.transform.position;
                        var dst = go.GetComponent<AudioSource>(); EditorUtility.CopySerialized(src, dst); return dst;
                    }
                    outer.voice = Move(outer.voice, "Voice"); outer.motorLoop = Move(outer.motorLoop, "Motor loop");
                    // FX objects that live inside the nested root move up a level (keeping world position)
                    void Lift(Component c) { if (c && nested.Any(n => c.transform.IsChildOf(n.transform))) c.transform.SetParent(root.transform, true); }
                    Lift(outer.sparks); Lift(outer.smoke); Lift(outer.footDust); Lift(outer.downwash); Lift(outer.eyeLight);
                    foreach (var r in outer.glowRenderers ?? new Renderer[0]) Lift(r);
                    foreach (var n in nested) Object.DestroyImmediate(n);
                    PrefabUtility.SaveAsPrefabAsset(root, path); fixedList.Add(file + ": removed " + nested.Length + " nested droid root(s)");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            return "nested: " + string.Join(", ", fixedList);
        }

        // ------------------------------------------------------------------ loot tables
        public static readonly string[] NewItems = { "reaper_blade", "sentinel_optic" };
        static readonly string[] RetiredTables = { "loot_ironclad_warden" };
        public static string Loot()
        {
            var cat = AssetDatabase.LoadAssetAtPath<CraftingCatalog>(Crafting); var city = AssetDatabase.LoadAssetAtPath<CityCatalog>(City);
            var known = new HashSet<string>(city.items.Select(i => i.id));
            var missing = NewItems.Where(i => !known.Contains(i)).ToArray();
            if (missing.Length > 0) throw new Exception("CityCatalog lacks " + string.Join(",", missing) + ": run art/next_level_20261002/enemies/apply_data.py first");
            LootEntry E(string id, int lo, int hi, float chance, int pity = 0, bool guarantee = false) => new LootEntry { itemId = id, minQuantity = lo, maxQuantity = hi, chance = chance, pityAfter = pity, guaranteeUntilCollected = guarantee };
            var tables = new[]
            {
                new LootTable { id = "loot_scrap_reaper", entries = new[] { E("reaper_blade", 1, 1, .45f, 2), E("droid_servo_damaged", 1, 1, .8f, 2), E("scrap_alloy", 2, 4, 1), E("nanite_residue", 2, 4, 1), E("copper_filament", 1, 2, .6f, 2), E("actuator_intact", 1, 1, .25f, 4), E("lattice_shard", 1, 1, .15f, 6) } },
                new LootTable { id = "loot_post_sentinel", entries = new[] { E("sentinel_optic", 1, 1, .55f, 2), E("optic_lens_cracked", 1, 1, .8f), E("micro_capacitor", 1, 2, .75f, 2), E("copper_filament", 1, 2, 1), E("charge_cell_core", 1, 1, .25f, 4), E("lattice_shard", 1, 1, .25f, 4), E("nanite_residue", 2, 3, 1) } },
                new LootTable { id = "loot_nextlevel_crate", entries = new[] { E("scrap_alloy", 4, 6, 1), E("nanite_residue", 3, 5, 1), E("micro_capacitor", 1, 2, 1), E("actuator_intact", 1, 1, .6f, 2), E("lattice_shard", 1, 2, .6f, 2), E("medkit", 1, 1, .5f, 2), E("wound_coil", 1, 1, .4f, 3) } },
                new LootTable { id = "loot_nextlevel_strongbox", entries = new[] { E("reaper_blade", 1, 1, .5f, 3, true), E("sentinel_optic", 1, 1, .5f, 3, true), E("lattice_shard", 2, 3, 1), E("actuator_intact", 1, 2, 1), E("charge_cell_core", 1, 1, .6f, 2), E("medkit", 1, 2, 1), E("micro_capacitor", 2, 3, 1) } },
            };
            foreach (var t in tables) foreach (var e in t.entries) if (!known.Contains(e.itemId)) throw new Exception("unknown item " + e.itemId);
            var list = cat.lootTables.Where(t => !tables.Any(n => n.id == t.id) && !RetiredTables.Contains(t.id)).ToList(); list.AddRange(tables); cat.lootTables = list.ToArray();
            EditorUtility.SetDirty(cat); AssetDatabase.SaveAssets();
            return "loot tables: " + string.Join(", ", tables.Select(t => t.id)) + $" ({cat.lootTables.Length} in all)";
        }

        // ------------------------------------------------------------------ scene install
        static JObject Sites => JObject.Parse(File.ReadAllText(ArtSrc + "sites.json"));

        public static string Install()
        {
            AssetDatabase.Refresh();
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks && (chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))) throw new Exception("Rebuild and save existing render-chunk source edits before this install.");
            Directory.CreateDirectory(Evidence);
            var rec = new Dictionary<string, object> { ["utc"] = DateTime.UtcNow.ToString("O") };
            var roots = scene.GetRootGameObjects();
            var berms = roots.First(g => g.name == "Outer Berms").transform;
            var expanse = berms.Find("Berms expanse") ?? throw new Exception("Berms expanse is not installed");
            var session = Object.FindAnyObjectByType<GameSession>(); var combat = Object.FindAnyObjectByType<PlayerCombat>(); var crafting = Object.FindAnyObjectByType<CraftingSession>();
            var landmarks = roots.First(g => g.name == "Landmarks").transform;
            var sites = Sites;
            // ---- undo a previous run: our root, our landmarks, our parked scatter
            var old = berms.Find(RootName); if (old) Object.DestroyImmediate(old.gameObject);
            foreach (JObject s in sites["sites"]) { var l = landmarks.Find((string)s["landmark"]); if (l) Object.DestroyImmediate(l.gameObject); }
            // parked scatter is recorded by path and by position (re-enable by either), so a re-run never loses a rock
            var parkedFile = Evidence + "parked-scatter.json";
            var scatterAll = (expanse.Find("Scatter") ? expanse.Find("Scatter").GetComponentsInChildren<Transform>(true) : new Transform[0]).Where(t => PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject)).ToArray();
            if (File.Exists(parkedFile))
                foreach (var p in JArray.Parse(File.ReadAllText(parkedFile)))
                {
                    string path = p.Type == JTokenType.String ? (string)p : (string)p["path"]; var t = expanse.Find(path ?? "~");
                    if (!t && p.Type == JTokenType.Object) { float px = (float)p["x"], pz = (float)p["z"]; t = scatterAll.FirstOrDefault(x => Mathf.Abs(x.position.x - px) < .05f && Mathf.Abs(x.position.z - pz) < .05f); }
                    if (t) t.gameObject.SetActive(true);
                }
            var root = new GameObject(RootName).transform; root.SetParent(berms, false);
            // ---- ground
            var groundCols = expanse.Find("Ground").GetComponentsInChildren<MeshCollider>().Cast<Collider>().Append(berms.Find("Berms ground").GetComponent<MeshCollider>()).ToList();
            float GroundY(float x, float z, float fallback = float.NaN)
            {
                var ray = new Ray(new Vector3(x, 300, z), Vector3.down); float best = float.NegativeInfinity;
                foreach (var c in groundCols) if (c && c.Raycast(ray, out var hit, 600) && hit.point.y > best) best = hit.point.y;
                return float.IsNegativeInfinity(best) ? fallback : best;
            }
            Physics.SyncTransforms();
            var scatterRoots = scatterAll;
            var parked = new List<object>(); var parkedPaths = new HashSet<string>();
            void Park(Vector3 at, float radius)
            {
                foreach (var t in scatterRoots)
                {
                    var p = t.position; if (new Vector2(p.x - at.x, p.z - at.z).magnitude > radius + .8f * t.localScale.x + .3f) continue;
                    t.gameObject.SetActive(false); var rel = PathOf(t).Substring(PathOf(expanse).Length + 1);
                    if (parkedPaths.Add(rel)) parked.Add(new { path = rel, x = R(t.position.x, 3), z = R(t.position.z, 3), name = t.name });
                }
            }
            var nodePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(OB + "SalvageHeapNode.prefab");
            var droidPrefabs = new Dictionary<string, FeralDroid> { ["reaper"] = AssetDatabase.LoadAssetAtPath<FeralDroid>(OB + "FeralScrapReaper.prefab"), ["sentinel"] = AssetDatabase.LoadAssetAtPath<FeralDroid>(OB + "FeralPostSentinel.prefab") };
            foreach (var kv in droidPrefabs) if (!kv.Value) throw new Exception("droid prefab missing: " + kv.Key + " (run the droids step)");
            var siteRoot = new GameObject("Sites").transform; siteRoot.SetParent(root, false);
            var siteRec = new List<object>(); var missingProps = new List<string>(); int props = 0, crates = 0, spawns = 0, nodes = 0;
            foreach (JObject s in sites["sites"])
            {
                var c = s["centre"].Select(v => (float)v).ToArray();
                var site = new GameObject((string)s["name"]).transform; site.SetParent(siteRoot, false); site.position = new Vector3(c[0], GroundY(c[0], c[1], 0), c[1]);
                var propRoot = new GameObject("Props").transform; propRoot.SetParent(site, true);
                foreach (JObject p in s["props"])
                {
                    var w = p["world"].Select(v => (float)v).ToArray(); float fp = (float)(p["footprint"] ?? 1.5f);
                    Park(new Vector3(w[0], 0, w[1]), fp);
                    var go = Place((string)p["prefab"], propRoot, w[0], w[1], (float)p["yaw"], 1, GroundY, (bool?)p["main"] == true ? -.25f : -.04f);
                    if (!go) { missingProps.Add((string)p["prefab"]); continue; }
                    EnsureCollider(go); props++;
                }
                // loot crates: a kit crate with a salvage-node search on its lid
                var crateRoot = new GameObject("Loot crates").transform; crateRoot.SetParent(site, true);
                foreach (JObject cr in s["crates"])
                {
                    var w = cr["world"].Select(v => (float)v).ToArray(); Park(new Vector3(w[0], 0, w[1]), (float)(cr["footprint"] ?? 1f));
                    var go = Place((string)cr["prefab"], crateRoot, w[0], w[1], (float)cr["yaw"], 1, GroundY, -.02f);
                    if (!go) { missingProps.Add((string)cr["prefab"]); continue; }
                    go.name = "Crate · " + (string)cr["name"]; EnsureCollider(go);
                    var b = Bounds(go);
                    var node = (GameObject)PrefabUtility.InstantiatePrefab(nodePrefab, scene); node.name = "Loot crate · " + (string)cr["name"];
                    node.transform.SetParent(go.transform, true); node.transform.position = new Vector3(b.center.x, b.max.y + .03f, b.center.z);
                    var sn = node.GetComponent<SalvageNode>(); sn.crafting = crafting; sn.lootTableId = (string)cr["loot"]; sn.displayName = (string)cr["name"];
                    sn.readyPrompt = (string)cr["prompt"]; sn.progressLabel = (string)cr["progress"]; sn.searchingPrompt = (string)cr["progress"] + " hold still"; sn.searchSeconds = 2.0f; sn.respawnSeconds = 600;
                    sn.depletedPrompt = "Emptied · more in {0}";
                    node.GetComponent<WorldInteractable>().range = (float)cr["range"]; crates++;
                }
                foreach (JObject n in s["salvage"])
                {
                    var w = n["world"].Select(v => (float)v).ToArray();
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(nodePrefab, scene); go.name = "Salvage node · " + (string)n["name"];
                    go.transform.SetParent(site, true); go.transform.position = new Vector3(w[0], GroundY(w[0], w[1], site.position.y), w[1]);
                    var node = go.GetComponent<SalvageNode>(); node.crafting = crafting; node.lootTableId = (string)n["loot"]; node.displayName = (string)n["name"];
                    node.readyPrompt = (string)n["prompt"]; node.progressLabel = (string)n["progress"]; node.searchingPrompt = (string)n["progress"] + " hold still"; node.respawnSeconds = 420;
                    go.GetComponent<WorldInteractable>().range = (float)n["range"]; nodes++;
                }
                var enc = (JObject)s["encounter"];
                var eg = new GameObject("Encounter · " + (string)enc["name"]).transform; eg.SetParent(site, false); eg.position = site.position;
                var e = eg.gameObject.AddComponent<DroidEncounter>();
                e.displayName = (string)enc["name"]; e.player = combat; e.session = session;
                e.activateWithin = 75; e.requirePistol = true; e.packRadius = 22; e.parkBeyond = 170; e.respawnSeconds = 600; e.respawnClearance = 90; e.awaySeconds = 30;
                var list = new List<DroidEncounter.Spawn>(); int k = 0;
                foreach (JObject sp in enc["spawns"])
                {
                    var pf = droidPrefabs[(string)sp["kind"]]; var w = sp["world"].Select(v => (float)v).ToArray();
                    var pt = new GameObject($"Spawn {++k} · {pf.name}").transform; pt.SetParent(eg, false);
                    pt.SetPositionAndRotation(FreeSpot(new Vector2(w[0], w[1]), GroundY, site.position.y), Quaternion.Euler(0, (float)sp["yaw"], 0));
                    list.Add(new DroidEncounter.Spawn { prefab = pf, point = pt }); spawns++;
                }
                e.spawns = list.ToArray();
                var cp = site.gameObject.AddComponent<BermsCompassPoint>(); cp.displayName = (string)s["name"]; cp.kind = BermsCompassPoint.Kind.Site; cp.encounter = e;
                var ap = s["approach"].Select(v => (float)v).ToArray();
                var l = new GameObject((string)s["landmark"]).transform; l.SetParent(landmarks, false); l.position = FreeSpot(new Vector2(ap[0], ap[1]), GroundY, site.position.y);
                siteRec.Add(new { id = (string)s["id"], centre = V(site.position), props = propRoot.childCount, crates = crateRoot.childCount, spawns = e.spawns.Length, landmark = V(l.position) });
            }
            // ---- review cameras (player height above the ground)
            var cams = new GameObject("Next level review cameras").transform; cams.SetParent(root, false);
            foreach (JObject cdef in sites["cameras"])
            {
                var p = cdef["pos"].Select(v => (float)v).ToArray(); var t = cdef["target"].Select(v => (float)v).ToArray();
                var pos = new Vector3(p[0], GroundY(p[0], p[2], 0) + p[1], p[2]); var tgt = new Vector3(t[0], GroundY(t[0], t[2], 0) + t[1], t[2]);
                var go = new GameObject((string)cdef["name"]); go.transform.SetParent(cams, false); go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(tgt - pos, Vector3.up));
                var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = (float)(cdef["fov"] ?? 58); cam.nearClipPlane = .05f; cam.farClipPlane = 1600;
            }
            // Brann at his counter: a player-height camera 2.3 m in front of the SalvageDealer instance, looking at his face
            var brann = roots.SelectMany(g => g.GetComponentsInChildren<ActorLookAt>(true)).Select(l => l.transform).FirstOrDefault(t => PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(t.gameObject) == DealerPrefab);
            if (brann)
            {
                var go = new GameObject("cam_nextlevel_brann"); go.transform.SetParent(cams, false);
                var pos = brann.position + brann.forward * 2.3f + brann.right * .5f + Vector3.up * 1.6f; var tgt = brann.position + Vector3.up * 1.45f;
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(tgt - pos, Vector3.up));
                var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = 40; cam.nearClipPlane = .05f; cam.farClipPlane = 1600;
                rec["brannCamera"] = new { at = V(pos), brann = V(brann.position) };
            }
            else rec["brannCamera"] = "SalvageDealer instance not found";
            File.WriteAllText(parkedFile, JsonConvert.SerializeObject(parked, Formatting.Indented));
            rec["sites"] = siteRec; rec["props"] = props; rec["crates"] = crates; rec["salvageNodes"] = nodes; rec["spawns"] = spawns; rec["cameras"] = cams.childCount; rec["parkedScatter"] = parked.Count; rec["missingProps"] = missingProps.Distinct().ToArray();
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Write("install.json", rec);
            return $"installed: {siteRec.Count} sites, {props} props, {crates} loot crates, {nodes} salvage nodes, {spawns} spawns, {cams.childCount} cameras, {parked.Count} scatter parked, {missingProps.Count} missing props";
        }

        static Vector3 FreeSpot(Vector2 want, Func<float, float, float, float> groundY, float fallback)
        {
            Physics.SyncTransforms();
            bool Free(Vector3 p) => !Physics.CheckCapsule(p + Vector3.up * .6f, p + Vector3.up * 1.7f, .45f, ~(1 << 8), QueryTriggerInteraction.Ignore);
            var first = new Vector3(want.x, groundY(want.x, want.y, fallback), want.y);
            if (Free(first)) return first;
            for (float r = .75f; r <= 6f; r += .75f) for (int a = 0; a < 12; a++) { float ang = a * Mathf.PI / 6; float x = want.x + Mathf.Cos(ang) * r, z = want.y + Mathf.Sin(ang) * r; var p = new Vector3(x, groundY(x, z, fallback), z); if (Free(p)) return p; }
            return first;
        }

        static Bounds Bounds(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>().Where(r => r.enabled && !(r is ParticleSystemRenderer) && !(r is LineRenderer) && !(r is TrailRenderer)).ToArray();
            if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.one * .1f);
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); return b;
        }

        static GameObject Place(string prefab, Transform parent, float x, float z, float yaw, float scale, Func<float, float, float, float> groundY, float sink)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/" + prefab + ".prefab"); if (!asset) return null;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, parent.gameObject.scene); go.transform.SetParent(parent, false);
            go.transform.localScale = Vector3.one * scale; go.transform.SetPositionAndRotation(new Vector3(x, 0, z), Quaternion.Euler(0, yaw, 0));
            var b = Bounds(go); var ext = b.extents; float minY = float.PositiveInfinity, sumY = 0; int n = 0;
            foreach (var (dx, dz) in new[] { (0f, 0f), (-1f, -1f), (1f, -1f), (-1f, 1f), (1f, 1f) })
            {
                float y = groundY(b.center.x + dx * ext.x * .85f, b.center.z + dz * ext.z * .85f, float.NaN);
                if (float.IsNaN(y)) continue; minY = Mathf.Min(minY, y); sumY += y; n++;
            }
            if (n == 0) { Object.DestroyImmediate(go); return null; }
            float baseY = Mathf.Max(ext.x, ext.z) > 3 ? Mathf.Lerp(minY, sumY / n, .4f) : minY; float bottom = b.min.y - go.transform.position.y;
            go.transform.position = new Vector3(x, baseY - bottom + sink * Mathf.Max(1, scale), z);
            return go;
        }

        static void EnsureCollider(GameObject go)
        {
            if (go.GetComponentsInChildren<Collider>(true).Length > 0) return;
            var b = Bounds(go); if (Mathf.Max(b.size.x, b.size.z) < 1.2f || b.size.y < .8f) return;
            var box = go.AddComponent<BoxCollider>(); var inv = go.transform.worldToLocalMatrix;
            var locals = go.GetComponentsInChildren<MeshFilter>().Where(f => f.sharedMesh).SelectMany(f => { var m = inv * f.transform.localToWorldMatrix; var bb = f.sharedMesh.bounds; return new[] { m.MultiplyPoint3x4(bb.min), m.MultiplyPoint3x4(bb.max), m.MultiplyPoint3x4(new Vector3(bb.min.x, bb.min.y, bb.max.z)), m.MultiplyPoint3x4(new Vector3(bb.max.x, bb.min.y, bb.min.z)) }; }).ToArray();
            if (locals.Length > 0) { var lo = locals.Aggregate(Vector3.Min); var hi = locals.Aggregate(Vector3.Max); box.center = (lo + hi) / 2; box.size = (hi - lo) * .92f; }
            else { box.center = inv.MultiplyPoint3x4(b.center); box.size = b.size; }
        }

        // ------------------------------------------------------------------ verify (-nographics)
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); Physics.SyncTransforms();
            var r = new Dictionary<string, object>(); var problems = new List<string>();
            var roots = scene.GetRootGameObjects(); var berms = roots.First(g => g.name == "Outer Berms").transform;
            var root = berms.Find(RootName); if (!root) throw new Exception("not installed");
            var expanse = berms.Find("Berms expanse");
            var cols = expanse.Find("Ground").GetComponentsInChildren<MeshCollider>().Cast<Collider>().Append(berms.Find("Berms ground").GetComponent<MeshCollider>()).ToList();
            float G(Vector3 p) { var ray = new Ray(new Vector3(p.x, 300, p.z), Vector3.down); float best = float.NegativeInfinity; foreach (var c in cols) if (c.Raycast(ray, out var h, 600)) best = Mathf.Max(best, h.point.y); return best; }
            var inst = root.GetComponentsInChildren<Transform>(true).Where(t => PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject)).ToArray();
            r["prefabInstances"] = inst.Length; r["brokenPrefabLinks"] = inst.Count(t => !PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject));
            r["missingMaterials"] = root.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(q => !q));
            var combat = Object.FindAnyObjectByType<PlayerCombat>(); var session = Object.FindAnyObjectByType<GameSession>();
            var encs = root.GetComponentsInChildren<DroidEncounter>(true); r["encounters"] = encs.Length; if (encs.Length != 4) problems.Add("expected 4 encounters, found " + encs.Length);
            foreach (var e in encs)
            {
                if (e.player != combat || e.session != session) problems.Add(e.name + ": not wired to the player/session");
                foreach (var s in e.spawns)
                {
                    if (!s.prefab || !s.point) { problems.Add(e.name + ": empty spawn"); continue; }
                    float gy = G(s.point.position);
                    if (float.IsNegativeInfinity(gy)) problems.Add(PathOf(s.point) + ": no ground"); else if (Mathf.Abs(gy - s.point.position.y) > .6f) problems.Add(PathOf(s.point) + $": spawn {s.point.position.y:0.00} vs ground {gy:0.00}");
                    if (Physics.CheckCapsule(s.point.position + Vector3.up * .6f, s.point.position + Vector3.up * 1.7f, .35f, ~(1 << 8), QueryTriggerInteraction.Ignore)) problems.Add(PathOf(s.point) + ": spawn overlaps a collider");
                    if (!s.prefab.GetComponent<DroidThreat>()) problems.Add(s.prefab.name + ": no DroidThreat");
                }
            }
            var cat = AssetDatabase.LoadAssetAtPath<CraftingCatalog>(Crafting); var city = AssetDatabase.LoadAssetAtPath<CityCatalog>(City);
            var nodesAll = root.GetComponentsInChildren<SalvageNode>(true); r["salvageNodes"] = nodesAll.Length; r["lootCrates"] = nodesAll.Count(n => n.name.StartsWith("Loot crate"));
            foreach (var n in nodesAll) { if (!cat.lootTables.Any(t => t.id == n.lootTableId)) problems.Add(n.name + ": unknown loot table " + n.lootTableId); if (!n.crafting) problems.Add(n.name + ": no crafting session"); }
            foreach (var id in new[] { "loot_scrap_reaper", "loot_post_sentinel", "loot_nextlevel_crate", "loot_nextlevel_strongbox" })
            {
                var t = cat.lootTables.FirstOrDefault(x => x.id == id); if (t == null) { problems.Add("missing loot table " + id); continue; }
                foreach (var e in t.entries) if (!city.items.Any(i => i.id == e.itemId)) problems.Add(id + ": unknown item " + e.itemId);
            }
            foreach (var id in NewItems) if (!city.items.Any(i => i.id == id)) problems.Add("catalog item missing: " + id);
            var landmarks = roots.First(g => g.name == "Landmarks").transform;
            var lm = Sites["sites"].Select(s => (string)s["landmark"]).ToArray();
            foreach (var n in lm) if (!landmarks.Find(n)) problems.Add("landmark missing: " + n);
            r["landmarks"] = lm; r["cameras"] = root.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray();
            if (root.GetComponentsInChildren<Camera>(true).Length < 4) problems.Add("review cameras missing");
            // prefabs
            var prefabs = new Dictionary<string, object>();
            foreach (var file in new[] { "FeralScrapReaper", "FeralPostSentinel", "FeralWorkerDroid", "FeralScrapDrone", "FeralGunnerDroid", "FeralLancerDrone", "FeralDepotForeman" })
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(OB + file + ".prefab"); if (!go) { problems.Add("prefab missing " + file); continue; }
                var d = go.GetComponent<FeralDroid>(); var th = go.GetComponent<DroidThreat>(); var h = go.GetComponent<Health>(); var ls = go.GetComponent<LootSource>();
                int nested = go.GetComponentsInChildren<FeralDroid>(true).Count(x => x != d);
                if (nested > 0) problems.Add(file + ": nested FeralDroid x" + nested);
                if (!th) problems.Add(file + ": no DroidThreat");
                long tris = go.GetComponentsInChildren<SkinnedMeshRenderer>(true).Sum(s => s.sharedMesh ? s.sharedMesh.triangles.Length / 3 : 0) + go.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh && f.GetComponent<MeshRenderer>() && f.name != "Blur disc").Sum(f => f.sharedMesh.triangles.Length / 3);
                prefabs[file] = new { kind = d.kind.ToString(), attack = d.attackMode.ToString(), health = h.max, d.armour, level = th ? th.level : 0, experience = th ? th.experience : 0, loot = ls ? ls.lootTableId : null, clips = d.animationSource ? AnimationUtility.GetAnimationClips(d.animationSource.gameObject).Length : 0, triangles = tris, wheel = d.wheel ? d.wheel.name : null, muzzle = d.muzzle ? d.muzzle.name : null };
                if (new[] { "FeralScrapReaper", "FeralPostSentinel" }.Contains(file))
                {
                    if (!ls || !cat.lootTables.Any(t => t.id == ls.lootTableId)) problems.Add(file + ": loot table");
                    if (d.kind == DroidKind.Walker && !(d.idle && d.walk && d.run && d.attack && d.hit && d.death)) problems.Add(file + ": clips missing");
                    if (d.kind == DroidKind.Walker) foreach (var clip in new[] { d.idle, d.walk, d.run, d.attack, d.hit, d.death }) { int unresolved = AnimationUtility.GetCurveBindings(clip).Count(b => b.path.Length > 0 && !d.animationSource.transform.Find(b.path)); if (unresolved > 0) problems.Add(file + "/" + clip.name + ": " + unresolved + " unresolved paths"); }
                    if (d.kind == DroidKind.Wheeled && (!d.wheel || !d.muzzle || !d.boltPrefab || !d.aimLaser)) problems.Add(file + ": wheeled wiring");
                    if (d.armour <= 0) problems.Add(file + ": no armour");
                }
            }
            r["prefabs"] = prefabs;
            if (AssetDatabase.LoadAssetAtPath<GameObject>(OB + "FeralIroncladWarden.prefab")) problems.Add("the Ironclad Warden prefab is still live");
            if (!AssetDatabase.LoadAssetAtPath<GameObject>(RetiredDir + "FeralIroncladWarden.prefab")) problems.Add("retired Ironclad Warden prefab missing");
            if (cat.lootTables.Any(t => t.id == "loot_ironclad_warden")) problems.Add("loot_ironclad_warden still in the catalog");
            if (city.items.Any(i => i.id == "ironclad_plate")) problems.Add("ironclad_plate still in the catalog");
            // Brann on the delivered rig
            var dealer = AssetDatabase.LoadAssetAtPath<GameObject>(DealerPrefab); var actor = dealer ? dealer.GetComponent<ActorAnimation>() : null; var look = dealer ? dealer.GetComponent<ActorLookAt>() : null;
            if (!actor || !look) problems.Add("SalvageDealer prefab lacks ActorAnimation/ActorLookAt");
            else
            {
                var dsmr = dealer.GetComponentInChildren<SkinnedMeshRenderer>(true);
                r["brann"] = new { triangles = dsmr ? dsmr.sharedMesh.triangles.Length / 3 : 0, idle = actor.idle ? actor.idle.name : null, talk = actor.talk ? actor.talk.name : null, walk = actor.walk ? actor.walk.name : null, run = actor.run ? actor.run.name : null, head = look.head ? look.head.name : null, neck = look.neck ? look.neck.name : null, renderingLayerMask = dsmr ? dsmr.renderingLayerMask : 0, backup = AssetDatabase.LoadAssetAtPath<GameObject>(DealerBackup) != null };
                if (!(actor.idle && actor.talk && actor.walk && actor.run) || actor.walk == actor.idle) problems.Add("Brann clips not wired");
                if (!look.head || !look.neck || look.actor != actor) problems.Add("Brann look-at not wired");
                if (!dsmr || dsmr.sharedMesh.triangles.Length / 3 != 11358) problems.Add("Brann is not on the delivered rig");
                if (!AssetDatabase.LoadAssetAtPath<GameObject>(DealerBackup)) problems.Add("previous Brann backup missing");
                foreach (var clip in new[] { actor.idle, actor.talk, actor.walk, actor.run }) if (clip) { int unresolved = AnimationUtility.GetCurveBindings(clip).Count(b => b.path.Length > 0 && !actor.animationSource.transform.Find(b.path)); if (unresolved > 0) problems.Add("Brann/" + clip.name + ": " + unresolved + " unresolved paths"); }
                var dealerInst = roots.SelectMany(g => g.GetComponentsInChildren<ActorLookAt>(true)).FirstOrDefault(l => PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(l.gameObject) == DealerPrefab);
                if (!dealerInst) problems.Add("no SalvageDealer instance in the scene"); else r["brannInScene"] = new { position = V(dealerInst.transform.position), parent = dealerInst.transform.parent ? dealerInst.transform.parent.name : null };
            }
            var parkedFile = Evidence + "parked-scatter.json"; r["parkedScatter"] = File.Exists(parkedFile) ? JArray.Parse(File.ReadAllText(parkedFile)).Count : 0;
            r["problems"] = problems;
            Write("verify.json", r);
            return $"verify: {problems.Count} problems; " + string.Join(" | ", problems.Take(12));
        }

        // ------------------------------------------------------------------ capture (graphics; droid visuals stood at their spawns, never saved)
        public static string Capture(string outDir, string views)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var camsByName = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true)).GroupBy(c => c.name).ToDictionary(g => g.Key, g => g.First());
            var list = new List<(string name, Vector3 pos, Vector3 target, float fov)>();
            foreach (var n in views.Split('+')) { if (!camsByName.TryGetValue(n, out var c)) throw new Exception("camera not found: " + n); list.Add((n, c.transform.position, c.transform.position + c.transform.forward * 5f, c.fieldOfView)); }
            if (list.Count > 6) throw new Exception($"{list.Count} views in one run; capture at most 6 per Unity run");
            var berms = scene.GetRootGameObjects().First(g => g.name == "Outer Berms").transform; var root = berms.Find(RootName) ?? throw new Exception("not installed");
            var temp = new List<GameObject>();
            foreach (var e in root.GetComponentsInChildren<DroidEncounter>(true))
                foreach (var s in e.spawns)
                {
                    if (!s.prefab || !s.point) continue;
                    var vis = s.prefab.transform.Find("Visual"); if (!vis) continue;
                    var src = PrefabUtility.GetCorrespondingObjectFromSource(vis.gameObject) ?? vis.gameObject;
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(src, scene); go.transform.SetPositionAndRotation(s.point.position, s.point.rotation); go.transform.localScale = vis.localScale; go.name = "__cap " + s.prefab.name;
                    var anim = go.GetComponentInChildren<Animation>(true); if (anim && anim.clip) anim.clip.SampleAnimation(anim.gameObject, 0);
                    temp.Add(go);
                }
            try { return string.Join(",", StreetDressingPass.Capture(outDir, list)); }
            finally { foreach (var g in temp) Object.DestroyImmediate(g); }
        }

        // ------------------------------------------------------------------ batch entry points
        static void Write(string file, object o) { Directory.CreateDirectory(Evidence); File.WriteAllText(Evidence + file, JsonConvert.SerializeObject(o, Formatting.Indented)); }

        public static void InstallAll() => Run(new[] { "import", "visuals", "droids", "loot", "brann", "install", "verify" });
        public static void VerifyAll() => Run(new[] { "verify" });
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, "--steps");
            Run(i >= 0 ? args[i + 1].Split(',') : new[] { "verify" });
        }
        static void Run(string[] steps)
        {
            var log = new List<string>();
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "import" => Import(), "visuals" => Visuals(), "droids" => Droids(), "loot" => Loot(), "brann" => Brann(), "install" => Install(), "verify" => Verify(),
                        "capture" => Capture(parts[1], parts[2]), _ => throw new Exception("unknown step " + st),
                    };
                    log.Add(st + ": " + result); Debug.Log("NextLevelEnemiesInstall " + st + ": " + result);
                }
                Directory.CreateDirectory(Evidence); File.AppendAllText(Evidence + "run.log", DateTime.UtcNow.ToString("O") + "\n" + string.Join("\n", log) + "\n");
                bool bad = log.Any(l => l.StartsWith("verify: verify: ") && !l.Contains(" 0 problems"));   // exit 2 when verify lists problems
                EditorApplication.Exit(bad ? 2 : 0);
            }
            catch (Exception e) { Debug.LogException(e); Debug.Log("NextLevelEnemiesInstall FAILED: " + e.Message); Directory.CreateDirectory(Evidence); File.AppendAllText(Evidence + "run.log", DateTime.UtcNow.ToString("O") + " FAILED " + e + "\n"); EditorApplication.Exit(1); }
        }
    }
}
