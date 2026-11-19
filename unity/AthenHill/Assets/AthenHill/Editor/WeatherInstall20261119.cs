using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Rendering.Universal.ShaderGUI;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Audio;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// <summary>
    /// 19 November 2026 showcase: dynamic weather (art/showcase_20261119/weather/README.md).
    /// Adds one scene root, "Ward weather" (WeatherDirector, WeatherAudio with two looping 2D sources on the city's
    /// Ambience mixer group, and the viewer-centred "Blowing sand" ParticleSystem on a soft-particle Unlit material),
    /// and switches Follow Weather on for the viewer-following "Windborne dust" emitters. Touches nothing else; it does
    /// not call any older pass. Idempotent: re-running reuses and re-binds the same objects.
    /// Batch (Editor closed, -nographics):
    ///   Unity -batchmode -nographics -projectPath unity/AthenHill
    ///     -executeMethod AthenHill.Editor.WeatherInstall20261119.RunBatch --steps install,verify
    /// Rollback: --steps rollback (removes the root, Follow Weather off; the material and audio assets stay).
    /// </summary>
    public static class WeatherInstall20261119
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string RootName = "Ward weather";
        const string ArtDir = "Assets/AthenHill/Art/Weather/";
        const string MaterialPath = ArtDir + "BlowingSand.mat";
        const string PuffPath = "Assets/AthenHill/Art/Atmosphere/Dustbowl/SoftPuff.png";
        const string AudioDir = "Assets/AthenHill/Audio/Weather/";
        const string BedClip = AudioDir + "weather_wind_bed.wav";
        const string FrontClip = AudioDir + "weather_dust_front.wav";
        static string RecordPath => Path.GetFullPath(Path.Combine(Application.dataPath, "../../../art/showcase_20261119/weather/install-record.json"));

        static GameObject Root() => EditorSceneManager.GetActiveScene().GetRootGameObjects().FirstOrDefault(g => g.name == RootName);

        static Transform Child(Transform parent, string name)
        {
            var t = parent.Find(name);
            if (t) return t;
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            return go.transform;
        }

        static T Ensure<T>(GameObject go) where T : Component => go.GetComponent<T>() ? go.GetComponent<T>() : go.AddComponent<T>();

        static AudioClip ImportClip(string path)
        {
            var importer = AssetImporter.GetAtPath(path) as AudioImporter;
            if (!importer) throw new InvalidOperationException("Missing weather audio (run art/showcase_20261119/weather/generate_weather_audio.py): " + path);
            var s = importer.defaultSampleSettings;
            if (!importer.forceToMono || s.loadType != AudioClipLoadType.CompressedInMemory || s.compressionFormat != AudioCompressionFormat.Vorbis)
            {
                importer.forceToMono = true; importer.loadInBackground = true;
                s.loadType = AudioClipLoadType.CompressedInMemory; s.compressionFormat = AudioCompressionFormat.Vorbis;
                s.quality = .7f; s.sampleRateSetting = AudioSampleRateSetting.PreserveSampleRate;
                importer.defaultSampleSettings = s;
                importer.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<AudioClip>(path);
        }

        static Material SandMaterial()
        {
            Directory.CreateDirectory(ArtDir);
            var shader = Shader.Find("Universal Render Pipeline/Particles/Unlit");
            if (!shader) throw new InvalidOperationException("URP Particles/Unlit shader not found.");
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
            if (!mat) { mat = new Material(shader) { name = "BlowingSand" }; AssetDatabase.CreateAsset(mat, MaterialPath); }
            mat.shader = shader;
            var puff = AssetDatabase.LoadAssetAtPath<Texture2D>(PuffPath);
            if (puff) mat.SetTexture("_BaseMap", puff);
            mat.SetColor("_BaseColor", new Color(.82f, .7f, .54f, .16f));
            // Alpha blended, soft against the ground (the PC pipeline asset keeps the depth texture) and faded near the
            // camera, so sheets never cut hard lines into walls or fill the screen up close.
            mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", 0);
            mat.SetFloat("_SoftParticlesEnabled", 1); mat.SetFloat("_SoftParticlesNearFadeDistance", 0); mat.SetFloat("_SoftParticlesFarFadeDistance", 1.5f);
            mat.SetFloat("_CameraFadingEnabled", 1); mat.SetFloat("_CameraNearFadeDistance", .8f); mat.SetFloat("_CameraFarFadeDistance", 3.5f);
            mat.enableInstancing = true;
            BaseShaderGUI.SetMaterialKeywords(mat, null, ParticleGUI.SetMaterialKeywords);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static Gradient Fade()
        {
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, .25f), new GradientAlphaKey(1, .65f), new GradientAlphaKey(0, 1) });
            return g;
        }

        static ParticleSystem BuildSand(Transform root, Material mat)
        {
            var go = Child(root, "Blowing sand").gameObject;
            var ps = Ensure<ParticleSystem>(go);
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.loop = true; main.playOnAwake = false; main.prewarm = false; main.duration = 5;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.startLifetime = new ParticleSystem.MinMaxCurve(2.5f, 4f); main.startSpeed = 0;
            main.startSize = new ParticleSystem.MinMaxCurve(2.5f, 6f); main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
            main.startColor = Color.white; main.maxParticles = 80; main.cullingMode = ParticleSystemCullingMode.PauseAndCatchup;
            var em = ps.emission; em.enabled = true; em.rateOverTime = 1;   // WeatherDirector sets the multiplier (0 outside a front)
            var shape = ps.shape; shape.enabled = true; shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(34, 2.2f, 34); shape.position = new Vector3(0, 1.1f, 0);
            var vel = ps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(4f, 6.25f); vel.y = new ParticleSystem.MinMaxCurve(-.1f, .35f); vel.z = new ParticleSystem.MinMaxCurve(1.3f, 2f);
            var size = ps.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .7f, 1, 1.3f));
            var col = ps.colorOverLifetime; col.enabled = true; col.color = Fade();
            var rot = ps.rotationOverLifetime; rot.enabled = true; rot.z = new ParticleSystem.MinMaxCurve(-.15f, .15f);
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = mat; r.renderMode = ParticleSystemRenderMode.Billboard;
            r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
            r.lightProbeUsage = LightProbeUsage.Off; r.reflectionProbeUsage = ReflectionProbeUsage.Off;
            // Overdraw cap: no sheet may cover more than a third of the screen however close it drifts.
            r.maxParticleSize = .33f;
            r.sortingFudge = 10;
            return ps;
        }

        static AudioSource BuildSource(Transform root, string name, AudioClip clip, AudioMixerGroup group)
        {
            var source = Ensure<AudioSource>(Child(root, name).gameObject);
            source.clip = clip; source.outputAudioMixerGroup = group;
            source.loop = true; source.playOnAwake = false; source.spatialBlend = 0; source.volume = 0; source.priority = 96;
            source.dopplerLevel = 0;
            return source;
        }

        static AudioMixerGroup AmbienceGroup(GameSession session)
        {
            var city = UnityEngine.Object.FindFirstObjectByType<CityAudio>(FindObjectsInactive.Include);
            if (city && city.ambience && city.ambience.outputAudioMixerGroup) return city.ambience.outputAudioMixerGroup;
            var mixer = AssetDatabase.LoadAssetAtPath<AudioMixer>("Assets/AthenHill/Audio/City.mixer");
            return mixer ? mixer.FindMatchingGroups("Ambience").FirstOrDefault() : null;
        }

        static IEnumerable<WindborneDust> ViewerDust() =>
            UnityEngine.Object.FindObjectsByType<WindborneDust>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(d => d.gameObject.name == "Windborne dust" && d.viewer);

        public static string Install()
        {
            var session = UnityEngine.Object.FindFirstObjectByType<GameSession>(FindObjectsInactive.Include);
            var clock = UnityEngine.Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var tutorial = UnityEngine.Object.FindFirstObjectByType<BermsTutorial>(FindObjectsInactive.Include);
            if (!session || !session.player) throw new InvalidOperationException("GameSession with a player is required.");
            if (!clock) throw new InvalidOperationException("CityTimeOfDay is required.");
            var group = AmbienceGroup(session);
            if (!group) throw new InvalidOperationException("City Ambience mixer group not found.");
            var bed = ImportClip(BedClip); var front = ImportClip(FrontClip);
            var mat = SandMaterial();

            var root = Root();
            bool created = !root;
            if (created) { root = new GameObject(RootName); SceneManager_Move(root); }
            var director = Ensure<WeatherDirector>(root);
            var audio = Ensure<WeatherAudio>(root);
            director.session = session; director.clock = clock; director.tutorial = tutorial;
            director.viewer = session.player.transform;
            director.blowingSand = BuildSand(root.transform, mat);
            director.weatherAudio = audio;
            audio.session = session;
            audio.windBed = BuildSource(root.transform, "Weather wind bed", bed, group);
            audio.frontLayer = BuildSource(root.transform, "Weather dust front", front, group);
            EditorUtility.SetDirty(director); EditorUtility.SetDirty(audio);

            var dust = ViewerDust().ToList();
            foreach (var d in dust) { d.followWeather = true; EditorUtility.SetDirty(d); }
            WriteRecord("install", new { created, dustFollowing = dust.Count, group = group.name, tutorial = tutorial != null });
            return (created ? "created " : "re-bound ") + RootName + "; windborne dust following weather: " + dust.Count + "; audio group " + group.name;
        }

        static void SceneManager_Move(GameObject go) => UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(go, EditorSceneManager.GetActiveScene());

        public static string Verify()
        {
            var problems = new List<string>();
            var root = Root();
            if (!root) problems.Add("no " + RootName + " root");
            var director = root ? root.GetComponent<WeatherDirector>() : null;
            var audio = root ? root.GetComponent<WeatherAudio>() : null;
            if (!director) problems.Add("WeatherDirector missing");
            else
            {
                if (!director.session) problems.Add("director.session unbound");
                if (!director.clock) problems.Add("director.clock unbound");
                if (!director.viewer) problems.Add("director.viewer unbound");
                if (!director.tutorial) problems.Add("director.tutorial unbound (fronts would be unrestricted)");
                if (!director.blowingSand) problems.Add("blowing sand missing");
                else
                {
                    var r = director.blowingSand.GetComponent<ParticleSystemRenderer>();
                    if (!r || !r.sharedMaterial || r.sharedMaterial.shader.name != "Universal Render Pipeline/Particles/Unlit") problems.Add("blowing sand material wrong");
                    if (director.blowingSand.main.playOnAwake) problems.Add("blowing sand plays on awake");
                    if (director.blowingSand.main.maxParticles > 120) problems.Add("blowing sand max particles above 120");
                }
                if (director.weatherAudio != audio) problems.Add("director.weatherAudio unbound");
                if (director.schedule == null || director.schedule.states == null || director.schedule.states.Length < 6) problems.Add("schedule states incomplete");
            }
            if (audio)
            {
                foreach (var s in new[] { audio.windBed, audio.frontLayer })
                {
                    if (!s) { problems.Add("weather audio source missing"); continue; }
                    if (!s.clip) problems.Add(s.name + " has no clip");
                    if (!s.outputAudioMixerGroup) problems.Add(s.name + " has no mixer group");
                    if (s.playOnAwake) problems.Add(s.name + " plays on awake");
                }
            }
            else problems.Add("WeatherAudio missing");
            if (!ViewerDust().Any(d => d.followWeather)) problems.Add("no windborne dust follows the weather");
            if (UnityEngine.Object.FindObjectsByType<WeatherDirector>(FindObjectsInactive.Include, FindObjectsSortMode.None).Length > 1) problems.Add("more than one WeatherDirector");
            WriteRecord("verify", new { problems });
            if (problems.Count > 0) throw new InvalidOperationException("Weather verify failed: " + string.Join("; ", problems));
            return "PASS";
        }

        public static string Rollback()
        {
            var root = Root();
            if (root) UnityEngine.Object.DestroyImmediate(root);
            int n = 0;
            foreach (var d in UnityEngine.Object.FindObjectsByType<WindborneDust>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (d.followWeather) { d.followWeather = false; EditorUtility.SetDirty(d); n++; }
            WriteRecord("rollback", new { removedRoot = root != null, dustReset = n });
            return "removed " + RootName + (root ? "" : " (was absent)") + "; follow weather off on " + n;
        }

        static void WriteRecord(string step, object data)
        {
            var path = RecordPath;
            var log = File.Exists(path) ? JsonConvert.DeserializeObject<List<object>>(File.ReadAllText(path)) ?? new List<object>() : new List<object>();
            log.Add(new { utc = DateTime.UtcNow.ToString("u"), step, data });
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, JsonConvert.SerializeObject(log, Formatting.Indented));
        }

        [MenuItem("Athen Hill/Weather/Install weather (19 Nov 2026)")]
        static void InstallMenu() { Debug.Log(Install()); EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene()); }

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = (i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify").Split(',');
            try
            {
                EditorSceneManager.OpenScene(ScenePath);
                bool dirty = false;
                foreach (var st in steps)
                {
                    string r = st switch { "install" => Install(), "verify" => Verify(), "rollback" => Rollback(), _ => throw new Exception("unknown step " + st) };
                    if (st == "install" || st == "rollback") dirty = true;
                    Debug.Log("WeatherInstall20261119 " + st + ": " + r);
                }
                if (dirty) { var scene = EditorSceneManager.GetActiveScene(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); }
                AssetDatabase.SaveAssets();
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }   // scene not saved on failure
        }
    }
}
