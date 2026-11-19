using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Rendering.Universal.ShaderGUI;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// <summary>
    /// Combat feel pass, 19 Nov 2026 (art/showcase_20261119/combat_feel/README.md). Idempotent; touches only its own
    /// objects and components and never calls an older install pass.
    ///
    /// Steps (comma separated, in this order for a first install):
    ///   audio   import the synthesised hit ticks (Audio/UI/hit-*.wav, make_hit_ticks.py) as small PCM clips
    ///   assets  FX_BoltStreak texture, FX_BoltGlow / FX_BoltStreak materials, Prefabs/FX/CriticalFlash.prefab (no light)
    ///   droids  a DroidWeakPoint on every live FeralDroid prefab (anchored to the optic, following the skeleton)
    ///   bolts   glow halo + hot core, impact flash and a softer, shorter trail on every droid bolt prefab (no lights)
    ///   scene   CameraImpulse on the follow camera; CombatHud tick source and clips; CombatFx critical flash + impulse
    ///   verify  checks everything above and prints the weak-point balance table
    ///   rollback removes what this pass added and restores the bolt trails from the record
    ///
    /// -executeMethod AthenHill.Editor.CombatFeelPass20261119.RunBatch --steps audio,assets,droids,bolts,scene,verify
    /// </summary>
    public static class CombatFeelPass20261119
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string DroidDir = "Assets/AthenHill/Prefabs/OuterBerms";
        const string FxTex = "Assets/AthenHill/Art/FX/Textures/";
        const string FxMat = "Assets/AthenHill/Art/FX/Materials/";
        const string StreakTexture = FxTex + "FX_BoltStreak.png";
        const string BoltGlowMat = FxMat + "FX_BoltGlow.mat";
        const string BoltStreakMat = FxMat + "FX_BoltStreak.mat";
        const string CriticalPrefab = "Assets/AthenHill/Prefabs/FX/CriticalFlash.prefab";
        const string AudioDir = "Assets/AthenHill/Audio/UI/";
        static readonly string[] Ticks = { "hit-tick.wav", "hit-critical.wav", "hit-kill.wav" };
        const string HaloName = "Bolt glow halo", CoreName = "Bolt glow core", FlashName = "Bolt impact flash", AudioName = "Hit feedback audio";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string ArtDir => Path.Combine(Repo, "art/showcase_20261119/combat_feel");
        static string RecordPath => Path.Combine(ArtDir, "record.json");

        // Level-3 droids get the smaller multiplier so the starter pistol still cannot take them (DroidWeakPoint, README).
        const float MultiplierLevel3 = DroidWeakPoint.Level3Multiplier;
        static float RadiusFor(DroidKind kind) => DroidWeakPoint.RadiusFor(kind);
        static float MultiplierFor(int level) => DroidWeakPoint.MultiplierFor(level);

        // ------------------------------------------------------------------ record
        class Key { public float t, r, g, b, a; }
        class TrailRecord { public float time; public List<Key> width = new List<Key>(); public List<Key> colors = new List<Key>(); public List<Key> alphas = new List<Key>(); public string material; public int textureMode; }
        class Rec
        {
            public List<string> weakPoints = new List<string>();
            public Dictionary<string, TrailRecord> trails = new Dictionary<string, TrailRecord>();
            public List<string> scene = new List<string>();
            public List<string> log = new List<string>();
        }
        static Rec rec;
        static Rec Load() => File.Exists(RecordPath) ? JsonConvert.DeserializeObject<Rec>(File.ReadAllText(RecordPath)) ?? new Rec() : new Rec();
        static void Save() { Directory.CreateDirectory(ArtDir); File.WriteAllText(RecordPath, JsonConvert.SerializeObject(rec, Formatting.Indented)); }
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        // ------------------------------------------------------------------ audio
        static string Audio()
        {
            var lines = new List<string>();
            foreach (var name in Ticks)
            {
                string path = AudioDir + name;
                if (!File.Exists(Path.Combine(Repo, "unity/AthenHill", path))) throw new Exception(path + " missing: run art/showcase_20261119/combat_feel/make_hit_ticks.py");
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                var imp = (AudioImporter)AssetImporter.GetAtPath(path);
                var s = imp.defaultSampleSettings;
                // tiny, latency-critical clips: keep them decompressed and preloaded
                s.loadType = AudioClipLoadType.DecompressOnLoad; s.compressionFormat = AudioCompressionFormat.PCM; s.preloadAudioData = true;
                imp.defaultSampleSettings = s; imp.forceToMono = true; imp.loadInBackground = false;
                imp.SaveAndReimport();
                var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(path);
                lines.Add($"{name} {(clip ? clip.length * 1000 : -1):0} ms");
            }
            return string.Join("; ", lines);
        }

        // ------------------------------------------------------------------ assets
        static string Assets()
        {
            if (!File.Exists(Path.Combine(Repo, "unity/AthenHill", StreakTexture)))
            {
                // across the trail (V) a soft core; along it (U) constant, so the trail's own gradient shapes the length
                var tex = new Texture2D(64, 32, TextureFormat.RGBA32, false, true);
                for (int y = 0; y < 32; y++)
                {
                    float v = Mathf.Abs((y + .5f) / 32f * 2 - 1);
                    float a = Mathf.Pow(Mathf.Clamp01(1 - v), 1.8f);
                    for (int x = 0; x < 64; x++) tex.SetPixel(x, y, new Color(1, 1, 1, a));
                }
                tex.Apply();
                File.WriteAllBytes(Path.Combine(Repo, "unity/AthenHill", StreakTexture), tex.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(tex);
            }
            var streak = Texture(StreakTexture);
            var glowTex = Texture(FxTex + "FX_Glow.png");
            AdditiveMaterial(BoltGlowMat, glowTex, new Color(3.2f, 3.2f, 3.2f), true);
            AdditiveMaterial(BoltStreakMat, streak, new Color(2.6f, 2.6f, 2.6f), false);
            BuildCriticalFlash();
            AssetDatabase.SaveAssets();
            return $"{StreakTexture}, {BoltGlowMat}, {BoltStreakMat}, {CriticalPrefab}";
        }

        static Texture2D Texture(string path)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var imp = (TextureImporter)AssetImporter.GetAtPath(path);
            if (imp == null) throw new Exception("Missing texture " + path);
            if (path == StreakTexture)
            {
                imp.textureType = TextureImporterType.Default; imp.sRGBTexture = false; imp.alphaSource = TextureImporterAlphaSource.FromInput; imp.alphaIsTransparency = true;
                imp.mipmapEnabled = true; imp.wrapMode = TextureWrapMode.Clamp; imp.maxTextureSize = 64; imp.textureCompression = TextureImporterCompression.CompressedHQ;
                imp.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        /// Same set-up as CombatFxBuilder's additive particle materials (URP Particles/Unlit), tinted by vertex colour.
        static Material AdditiveMaterial(string path, Texture2D tex, Color baseColor, bool soft)
        {
            var shader = Shader.Find("Universal Render Pipeline/Particles/Unlit");
            if (!shader) throw new Exception("Missing URP Particles/Unlit shader");
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!mat) { mat = new Material(shader) { name = Path.GetFileNameWithoutExtension(path) }; AssetDatabase.CreateAsset(mat, path); }
            mat.shader = shader;
            mat.SetTexture("_BaseMap", tex); mat.SetColor("_BaseColor", baseColor);
            mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", 2); mat.SetFloat("_FlipbookBlending", 0);
            mat.SetFloat("_SoftParticlesEnabled", soft ? 1 : 0); mat.SetFloat("_SoftParticlesNearFadeDistance", 0); mat.SetFloat("_SoftParticlesFarFadeDistance", .3f);
            mat.SetFloat("_CameraFadingEnabled", 1); mat.SetFloat("_CameraNearFadeDistance", .25f); mat.SetFloat("_CameraFarFadeDistance", .8f);
            if (mat.HasProperty("_BlendModePreserveSpecular")) mat.SetFloat("_BlendModePreserveSpecular", 0);
            BaseShaderGUI.SetMaterialKeywords(mat, null, ParticleGUI.SetMaterialKeywords);
            EditorUtility.SetDirty(mat); return mat;
        }

        static void BuildCriticalFlash()
        {
            var glowMat = AssetDatabase.LoadAssetAtPath<Material>(FxMat + "FX_Glow.mat");
            var sparkMat = AssetDatabase.LoadAssetAtPath<Material>(FxMat + "FX_Spark.mat");
            if (!glowMat || !sparkMat) throw new Exception("FX_Glow / FX_Spark materials missing (CombatFxBuilder)");
            var root = new GameObject("CriticalFlash"); var fx = root.AddComponent<FxBurst>();
            // no light: the hit flash already carries one, and the OpenGL player draws at most 32 per camera
            fx.flash = null; fx.lifetime = .6f;
            var g = Ps(root, "Glow", glowMat, .07f, .1f, 0, 0, .5f, .65f, 1);
            var gm = g.main; gm.startColor = new Color(1f, .86f, .55f);
            Fade(g);
            var s = Ps(root, "Sparks", sparkMat, .15f, .35f, 4.5f, 9.5f, .02f, .04f, 16);
            var sm = s.main; sm.gravityModifier = 1.1f; sm.startColor = new Color(1f, .9f, .6f);
            var sh = s.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = .04f;
            var r = s.GetComponent<ParticleSystemRenderer>(); r.renderMode = ParticleSystemRenderMode.Stretch; r.velocityScale = .045f; r.lengthScale = 1.4f;
            Fade(s);
            fx.systems = new[] { g, s }; fx.optional = new[] { s };
            Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(Repo, "unity/AthenHill", CriticalPrefab)));
            PrefabUtility.SaveAsPrefabAsset(root, CriticalPrefab, out bool ok); UnityEngine.Object.DestroyImmediate(root);
            if (!ok) throw new Exception("Could not save " + CriticalPrefab);
        }

        static ParticleSystem Ps(GameObject root, string name, Material mat, float life0, float life1, float speed0, float speed1, float size0, float size1, int burst, bool world = true)
        {
            var go = new GameObject(name); go.transform.SetParent(root.transform, false);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var m = ps.main; m.duration = Mathf.Max(.1f, life1); m.loop = false; m.playOnAwake = false;
            m.simulationSpace = world ? ParticleSystemSimulationSpace.World : ParticleSystemSimulationSpace.Local;
            m.startLifetime = new ParticleSystem.MinMaxCurve(life0, life1); m.startSpeed = new ParticleSystem.MinMaxCurve(speed0, speed1);
            m.startSize = new ParticleSystem.MinMaxCurve(size0, size1); m.scalingMode = ParticleSystemScalingMode.Hierarchy; m.maxParticles = Mathf.Max(1, burst * 2);
            var e = ps.emission; e.enabled = true; e.rateOverTime = 0;
            if (burst > 0) e.SetBursts(new[] { new ParticleSystem.Burst(0, (short)burst) }); else e.SetBursts(new ParticleSystem.Burst[0]);
            var sh = ps.shape; sh.enabled = false;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.sharedMaterial = mat; r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false; r.renderMode = ParticleSystemRenderMode.Billboard;
            r.minParticleSize = 0; r.maxParticleSize = 2;
            return ps;
        }

        static void Fade(ParticleSystem ps)
        {
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) }, new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0, 1) });
            var c = ps.colorOverLifetime; c.enabled = true; c.color = new ParticleSystem.MinMaxGradient(g);
        }

        // ------------------------------------------------------------------ droids
        static IEnumerable<string> DroidPrefabs()
        {
            var paths = AssetDatabase.FindAssets("t:Prefab", new[] { DroidDir }).Select(AssetDatabase.GUIDToAssetPath)
                .Where(p => Path.GetDirectoryName(p).Replace('\\', '/') == DroidDir)
                .Where(p => { var go = AssetDatabase.LoadAssetAtPath<GameObject>(p); return go && go.GetComponent<FeralDroid>(); }).ToList();
            // bases first, so a variant (the Foreman) inherits the component and only overrides its numbers
            return paths.OrderBy(p => PrefabUtility.GetPrefabAssetType(AssetDatabase.LoadAssetAtPath<GameObject>(p)) == PrefabAssetType.Variant ? 1 : 0).ThenBy(p => p);
        }

        static string Droids()
        {
            var lines = new List<string>();
            foreach (var path in DroidPrefabs())
            {
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var droid = root.GetComponent<FeralDroid>();
                    var threat = root.GetComponent<DroidThreat>();
                    int level = threat ? threat.level : DroidThreat.DefaultLevel;
                    if (rec.weakPoints.Contains(path)) { lines.Add(Path.GetFileNameWithoutExtension(path) + " already configured"); continue; }
                    var weak = root.GetComponent<DroidWeakPoint>();
                    bool inherited = weak && PrefabUtility.GetPrefabAssetType(AssetDatabase.LoadAssetAtPath<GameObject>(path)) == PrefabAssetType.Variant;
                    if (weak && !inherited) { lines.Add(Path.GetFileNameWithoutExtension(path) + " has its own weak point: left alone"); continue; }
                    if (!weak) weak = root.AddComponent<DroidWeakPoint>();
                    if (!inherited) Anchor(root, droid, weak);
                    weak.radius = RadiusFor(droid.kind);
                    weak.damageMultiplier = MultiplierFor(level);
                    weak.label = "optic";
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    rec.weakPoints.Add(path);
                    float s = Mathf.Abs(root.transform.lossyScale.x);
                    lines.Add($"{Path.GetFileNameWithoutExtension(path)} L{level}: ×{weak.damageMultiplier} r {weak.radius} anchor {(weak.anchor ? PathOf(weak.anchor) : "root")} at {root.transform.InverseTransformPoint(weak.Centre)}{(inherited ? " (variant override)" : "")}");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            return string.Join(" | ", lines);
        }

        /// The optic light marks the optic. When it is not inside the skeleton (it would then ignore the head's
        /// animation), the zone hangs from the nearest bone instead, at the same rest position.
        static void Anchor(GameObject root, FeralDroid droid, DroidWeakPoint weak)
        {
            var skinned = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.bones != null && r.bones.Length > 0).ToArray();
            var bones = new HashSet<Transform>(skinned.SelectMany(r => r.bones).Where(b => b));
            Transform target = droid.eyeLight ? droid.eyeLight.transform : null;
            Vector3 at;
            if (target) at = target.position;
            else if (bones.Count > 0) { var top = bones.OrderByDescending(b => b.position.y).First(); at = top.position + Vector3.down * .12f * Mathf.Abs(root.transform.lossyScale.x); }
            else { var h = root.GetComponent<Health>(); at = h ? h.AimPoint + Vector3.up * .3f : root.transform.position + Vector3.up * 1.5f; }
            bool underSkeleton = target && bones.Any(b => target.IsChildOf(b));
            Transform anchor = target;
            if (bones.Count > 0 && !underSkeleton) anchor = bones.OrderBy(b => (b.position - at).sqrMagnitude).First();
            if (!anchor) anchor = root.transform;
            weak.anchor = anchor == root.transform ? null : anchor;
            var a = weak.anchor ? weak.anchor : root.transform;
            float scale = Mathf.Max(.01f, Mathf.Abs(root.transform.lossyScale.x));
            weak.offset = Quaternion.Inverse(a.rotation) * (at - a.position) / scale;
        }

        // ------------------------------------------------------------------ bolts
        static IEnumerable<string> BoltPrefabs()
            => DroidPrefabs().Select(p => AssetDatabase.LoadAssetAtPath<GameObject>(p).GetComponent<FeralDroid>().boltPrefab)
                .Where(b => b).Select(b => AssetDatabase.GetAssetPath(b)).Where(p => !string.IsNullOrEmpty(p)).Distinct();

        static string Bolts()
        {
            var glowMat = AssetDatabase.LoadAssetAtPath<Material>(BoltGlowMat);
            var streakMat = AssetDatabase.LoadAssetAtPath<Material>(BoltStreakMat);
            if (!glowMat || !streakMat) throw new Exception("Run the assets step first.");
            var lines = new List<string>();
            foreach (var path in BoltPrefabs())
            {
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var bolt = root.GetComponent<DroidBolt>();
                    if (root.GetComponentsInChildren<Light>(true).Length > 0) lines.Add(Path.GetFileNameWithoutExtension(path) + " carries a Light (left as it was)");
                    Color tint = Tint(bolt);
                    var halo = Child(root, HaloName) ?? GlowSystem(root, HaloName, glowMat, .46f, new Color(tint.r, tint.g, tint.b, .55f));
                    var core = Child(root, CoreName) ?? GlowSystem(root, CoreName, glowMat, .14f, Color.Lerp(tint, Color.white, .65f));
                    bolt.glow = new[] { halo, core };
                    if (!(bolt.impactFlash = Child(root, FlashName)))
                    {
                        var f = Ps(root, FlashName, glowMat, .09f, .11f, 0, 0, .75f, .9f, 0);
                        var m = f.main; m.startColor = Color.Lerp(tint, Color.white, .4f); m.maxParticles = 4;
                        Fade(f); bolt.impactFlash = f;
                    }
                    var trail = bolt.trail;
                    if (trail && trail.sharedMaterial != streakMat)
                    {
                        if (!rec.trails.ContainsKey(path)) rec.trails[path] = Capture(trail);
                        trail.sharedMaterial = streakMat; trail.textureMode = LineTextureMode.Stretch;
                        trail.time = .06f; trail.widthMultiplier = 1;
                        trail.widthCurve = new AnimationCurve(new Keyframe(0, .13f), new Keyframe(1, .02f));
                        var g = new Gradient();
                        g.SetKeys(new[] { new GradientColorKey(Color.Lerp(tint, Color.white, .55f), 0), new GradientColorKey(tint, .3f), new GradientColorKey(tint, 1) },
                                  new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(.8f, .3f), new GradientAlphaKey(0, 1) });
                        trail.colorGradient = g;
                        trail.shadowCastingMode = ShadowCastingMode.Off; trail.receiveShadows = false;
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    lines.Add($"{Path.GetFileNameWithoutExtension(path)} tint {tint}");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            return string.Join(" | ", lines);
        }

        static Color Tint(DroidBolt bolt)
        {
            if (rec.trails.TryGetValue(AssetDatabase.GetAssetPath(bolt), out var t) && t.colors.Count > 0) return new Color(t.colors[0].r, t.colors[0].g, t.colors[0].b);
            if (bolt.trail) { var k = bolt.trail.colorGradient.colorKeys; if (k.Length > 0) return k[0].color; }
            return new Color(1f, .5f, .2f);
        }

        static ParticleSystem Child(GameObject root, string name)
        {
            var t = root.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == name);
            return t ? t.GetComponent<ParticleSystem>() : null;
        }

        /// One long-lived billboard in local space: the bolt carries it; DroidBolt restarts it on launch and clears it
        /// on impact.
        static ParticleSystem GlowSystem(GameObject root, string name, Material mat, float size, Color color)
        {
            var ps = Ps(root, name, mat, 6, 6, 0, 0, size, size, 1, false);
            var m = ps.main; m.startColor = color; m.maxParticles = 1;
            return ps;
        }

        static TrailRecord Capture(TrailRenderer trail)
        {
            var r = new TrailRecord { time = trail.time, material = AssetDatabase.GetAssetPath(trail.sharedMaterial), textureMode = (int)trail.textureMode };
            foreach (var k in trail.widthCurve.keys) r.width.Add(new Key { t = k.time, a = k.value });
            r.width.ForEach(k => k.r = trail.widthMultiplier);
            foreach (var k in trail.colorGradient.colorKeys) r.colors.Add(new Key { t = k.time, r = k.color.r, g = k.color.g, b = k.color.b });
            foreach (var k in trail.colorGradient.alphaKeys) r.alphas.Add(new Key { t = k.time, a = k.alpha });
            return r;
        }

        static void Restore(TrailRenderer trail, TrailRecord r)
        {
            trail.time = r.time; trail.textureMode = (LineTextureMode)r.textureMode;
            trail.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(r.material);
            trail.widthMultiplier = r.width.Count > 0 ? r.width[0].r : 1;
            trail.widthCurve = new AnimationCurve(r.width.Select(k => new Keyframe(k.t, k.a)).ToArray());
            var g = new Gradient();
            g.SetKeys(r.colors.Select(k => new GradientColorKey(new Color(k.r, k.g, k.b), k.t)).ToArray(), r.alphas.Select(k => new GradientAlphaKey(k.a, k.t)).ToArray());
            trail.colorGradient = g;
        }

        // ------------------------------------------------------------------ scene
        static string SceneWiring()
        {
            var lines = new List<string>();
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            var player = UnityEngine.Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);
            var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>(FindObjectsInactive.Include);
            var hud = UnityEngine.Object.FindAnyObjectByType<CombatHud>(FindObjectsInactive.Include);
            var fx = UnityEngine.Object.FindAnyObjectByType<CombatFx>(FindObjectsInactive.Include);
            if (!session || !player || !follow || !hud) throw new Exception("Scene is missing GameSession, PlayerCombat, FollowCamera or CombatHud.");

            var impulse = follow.GetComponent<CameraImpulse>();
            if (!impulse) { impulse = Undo.AddComponent<CameraImpulse>(follow.gameObject); Note("impulse:" + PathOf(follow.transform)); lines.Add("CameraImpulse added on " + PathOf(follow.transform)); }
            impulse.session = session; impulse.player = player; impulse.view = follow.GetComponent<Camera>();
            EditorUtility.SetDirty(impulse);

            var audioT = hud.transform.Find(AudioName);
            if (!audioT)
            {
                var go = new GameObject(AudioName); go.transform.SetParent(hud.transform, false);
                var src = go.AddComponent<AudioSource>(); src.playOnAwake = false; src.spatialBlend = 0; src.priority = 40; src.loop = false;
                if (player.audioSource) src.outputAudioMixerGroup = player.audioSource.outputAudioMixerGroup;
                audioT = go.transform; Note("audio:" + PathOf(audioT)); lines.Add("tick source added");
            }
            hud.feedbackAudio = audioT.GetComponent<AudioSource>();
            hud.hitTick = AssetDatabase.LoadAssetAtPath<AudioClip>(AudioDir + Ticks[0]);
            hud.criticalTick = AssetDatabase.LoadAssetAtPath<AudioClip>(AudioDir + Ticks[1]);
            hud.killTick = AssetDatabase.LoadAssetAtPath<AudioClip>(AudioDir + Ticks[2]);
            EditorUtility.SetDirty(hud);

            if (fx)
            {
                fx.criticalFlash = AssetDatabase.LoadAssetAtPath<FxBurst>(CriticalPrefab);
                fx.impulse = impulse;
                EditorUtility.SetDirty(fx); lines.Add("CombatFx wired");
            }
            else lines.Add("no CombatFx in the scene: critical flash skipped");
            return string.Join("; ", lines);
        }
        static void Note(string s) { if (!rec.scene.Contains(s)) rec.scene.Add(s); }

        // ------------------------------------------------------------------ verify
        static string Verify()
        {
            var problems = new List<string>(); var lines = new List<string>();
            foreach (var name in Ticks) if (!AssetDatabase.LoadAssetAtPath<AudioClip>(AudioDir + name)) problems.Add("clip " + name);
            if (!AssetDatabase.LoadAssetAtPath<FxBurst>(CriticalPrefab)) problems.Add("CriticalFlash prefab");
            else if (AssetDatabase.LoadAssetAtPath<GameObject>(CriticalPrefab).GetComponentsInChildren<Light>(true).Length > 0) problems.Add("CriticalFlash has a light");
            foreach (var path in DroidPrefabs())
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                var weak = go.GetComponent<DroidWeakPoint>(); var threat = go.GetComponent<DroidThreat>();
                if (!weak) { problems.Add("no weak point on " + path); continue; }
                int level = threat ? threat.level : 1;
                if (level >= 3 && weak.damageMultiplier > MultiplierLevel3 + 1e-4f) problems.Add($"{path}: level {level} multiplier {weak.damageMultiplier} above {MultiplierLevel3}");
                if (weak.anchor && !weak.anchor.IsChildOf(go.transform)) problems.Add(path + ": anchor outside the prefab");
            }
            foreach (var path in BoltPrefabs())
            {
                var bolt = AssetDatabase.LoadAssetAtPath<GameObject>(path).GetComponent<DroidBolt>();
                if (bolt.glow == null || bolt.glow.Length < 2 || bolt.glow.Any(g => !g)) problems.Add(path + ": glow");
                if (!bolt.impactFlash) problems.Add(path + ": impact flash");
                if (bolt.glow != null && bolt.glow.Any(g => g && g.main.playOnAwake)) problems.Add(path + ": glow plays on awake");
            }
            var hud = UnityEngine.Object.FindAnyObjectByType<CombatHud>(FindObjectsInactive.Include);
            if (!hud || !hud.feedbackAudio || !hud.hitTick || !hud.criticalTick || !hud.killTick) problems.Add("CombatHud tick wiring");
            var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>(FindObjectsInactive.Include);
            var impulse = follow ? follow.GetComponent<CameraImpulse>() : null;
            if (!impulse || !impulse.player || !impulse.session || !impulse.view) problems.Add("CameraImpulse wiring");
            var fx = UnityEngine.Object.FindAnyObjectByType<CombatFx>(FindObjectsInactive.Include);
            if (fx && (!fx.criticalFlash || fx.impulse != impulse)) problems.Add("CombatFx wiring");
            lines.Add(Balance());
            return (problems.Count == 0 ? "PASS" : "FAIL: " + string.Join("; ", problems)) + " | " + string.Join(" | ", lines);
        }

        /// The weak-point balance table: a full starter-pistol charge against every level-3 droid with a quarter of the
        /// hits on the optic (expected) and with every hit on it (ceiling).
        static string Balance()
        {
            var catalog = AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
            if (!catalog) return "balance: crafting catalog missing";
            var pistol = catalog.weapons.FirstOrDefault(w => w.id == "weapon_scrap_pistol");
            if (pistol == null) return "balance: no scrap pistol";
            int shots = Mathf.FloorToInt(pistol.stats.nanoMax / Mathf.Max(1, pistol.stats.nanoPerShot));
            var rows = new List<string>();
            foreach (var path in DroidPrefabs())
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                var d = go.GetComponent<FeralDroid>(); var t = go.GetComponent<DroidThreat>(); var w = go.GetComponent<DroidWeakPoint>(); var h = go.GetComponent<Health>();
                if (!t || t.level < 3 || !w || !h) continue;
                float perHit = FeralDroid.MitigatedDamage(WeaponBallistics.ArmourReduced(pistol.stats.damage, t.armour, pistol.stats.armourPenetration), d.armour, pistol.stats.armourPenetration, d.armourMinFraction);
                float expected = WeakPointMath.ChargeDamage(shots, perHit, w.damageMultiplier, DroidWeakPoint.ExpectedWeakShare), ceiling = WeakPointMath.ChargeDamage(shots, perHit, w.damageMultiplier, 1);
                rows.Add($"{go.name} {h.max} hp: pistol charge {shots}×{perHit:0.#} expected {expected:0} ({expected / h.max:P0}), all optic {ceiling:0} ({ceiling / h.max:P0})");
            }
            return "balance: " + string.Join("; ", rows);
        }

        // ------------------------------------------------------------------ rollback
        static string Rollback()
        {
            var lines = new List<string>();
            foreach (var path in rec.weakPoints.ToList())
            {
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    bool variant = PrefabUtility.GetPrefabAssetType(AssetDatabase.LoadAssetAtPath<GameObject>(path)) == PrefabAssetType.Variant;
                    var weak = root.GetComponent<DroidWeakPoint>();
                    if (weak && variant) PrefabUtility.RevertObjectOverride(weak, InteractionMode.AutomatedAction);
                    else if (weak) UnityEngine.Object.DestroyImmediate(weak);
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
                lines.Add("weak point off " + Path.GetFileNameWithoutExtension(path));
            }
            rec.weakPoints.Clear();
            foreach (var path in BoltPrefabs())
            {
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var bolt = root.GetComponent<DroidBolt>();
                    foreach (var n in new[] { HaloName, CoreName, FlashName }) { var c = Child(root, n); if (c) UnityEngine.Object.DestroyImmediate(c.gameObject); }
                    bolt.glow = new ParticleSystem[0]; bolt.impactFlash = null;
                    if (bolt.trail && rec.trails.TryGetValue(path, out var t)) Restore(bolt.trail, t);
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
                rec.trails.Remove(path);
                lines.Add("bolt restored " + Path.GetFileNameWithoutExtension(path));
            }
            var follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>(FindObjectsInactive.Include);
            var impulse = follow ? follow.GetComponent<CameraImpulse>() : null;
            if (impulse && rec.scene.Any(s => s.StartsWith("impulse:"))) UnityEngine.Object.DestroyImmediate(impulse);
            var hud = UnityEngine.Object.FindAnyObjectByType<CombatHud>(FindObjectsInactive.Include);
            if (hud)
            {
                var a = hud.transform.Find(AudioName);
                if (a && rec.scene.Any(s => s.StartsWith("audio:"))) UnityEngine.Object.DestroyImmediate(a.gameObject);
                hud.feedbackAudio = null; hud.hitTick = hud.criticalTick = hud.killTick = null; EditorUtility.SetDirty(hud);
            }
            var fx = UnityEngine.Object.FindAnyObjectByType<CombatFx>(FindObjectsInactive.Include);
            if (fx) { fx.criticalFlash = null; fx.impulse = null; EditorUtility.SetDirty(fx); }
            rec.scene.Clear();
            lines.Add("scene unwired (assets under Art/FX, Prefabs/FX/CriticalFlash and Audio/UI/hit-*.wav are kept)");
            return string.Join("; ", lines);
        }

        // ------------------------------------------------------------------ batch entry
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = (i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify").Split(',');
            try
            {
                EditorSceneManager.OpenScene(ScenePath);
                rec = Load();
                bool dirty = false, failed = false;
                foreach (var st in steps)
                {
                    string r = st switch
                    {
                        "audio" => Audio(), "assets" => Assets(), "droids" => Droids(), "bolts" => Bolts(),
                        "scene" => SceneWiring(), "verify" => Verify(), "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st)
                    };
                    if (st == "scene" || st == "rollback") dirty = true;
                    if (st == "verify" && !r.StartsWith("PASS")) failed = true;
                    rec.log.Add(DateTime.UtcNow.ToString("u") + " " + st + ": " + r);
                    Debug.Log("CombatFeelPass20261119 " + st + ": " + r);
                    Save();
                }
                if (dirty) { var scene = EditorSceneManager.GetActiveScene(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); }
                AssetDatabase.SaveAssets();
                Save();
                EditorApplication.Exit(failed ? 2 : 0);
            }
            catch (Exception e)
            {
                Debug.LogError("CombatFeelPass20261119 failed: " + e);
                if (rec != null) { rec.log.Add(DateTime.UtcNow.ToString("u") + " ERROR " + e.Message); Save(); }
                EditorApplication.Exit(1);
            }
        }

        [MenuItem("Athen Hill/Combat/Combat feel pass (19 Nov 2026): install")]
        static void MenuInstall() { rec = Load(); Debug.Log(Audio() + "\n" + Assets() + "\n" + Droids() + "\n" + Bolts() + "\n" + SceneWiring() + "\n" + Verify()); EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene()); Save(); }
    }
}
