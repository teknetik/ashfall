#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.UIElements;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    public static class DayNightPass
    {
        const string AssetRoot = "Assets/AthenHill/Art/DayNight";
        static string Evidence => Path.GetFullPath(Path.Combine(Application.dataPath, "../../evidence/quality/20260908/day-night"));

        [MenuItem("Athen Hill/Day and night/Install clock and developer controls")]
        public static void Install()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Install in Edit Mode.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != "Assets/AthenHill/Scenes/AthenHill.unity") throw new InvalidOperationException("Open the saved AthenHill scene first.");
            if (Object.FindAnyObjectByType<CityTimeOfDay>()) throw new InvalidOperationException("The clock is already installed. Edit its saved profile and references in the Inspector.");
            if (scene.isDirty) throw new InvalidOperationException("Save the current authored scene before installing so the baseline is recoverable.");
            var session = Object.FindAnyObjectByType<GameSession>(); var hud = Object.FindAnyObjectByType<CityHud>();
            var key = RenderSettings.sun;
            var fill = GameObject.Find("Sky fill")?.GetComponent<Light>();
            var volume = Object.FindObjectsByType<Volume>().Where(v => v.isGlobal && v.sharedProfile && v.sharedProfile.TryGet<ColorAdjustments>(out _)).OrderByDescending(v => v.priority).FirstOrDefault();
            var shader = Shader.Find("Athen Hill/Ward Day Night Sky");
            var layout = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/DeveloperTimeMenu.uxml");
            if (!session || !hud || !key || !fill || !volume || !RenderSettings.skybox || !shader || !layout)
                throw new InvalidOperationException("Clock needs the existing session, HUD, sun, sky fill, grading volume, sky, compiled shader and menu layout.");
            if (LightmapSettings.lightmaps.Length > 0)
                throw new InvalidOperationException("The saved scene contains lightmaps. Audit their sun contribution before enabling a moving light clock.");
            Directory.CreateDirectory(Evidence);
            if (!AssetDatabase.IsValidFolder(AssetRoot)) AssetDatabase.CreateFolder("Assets/AthenHill/Art", "DayNight");
            EditorSceneManager.SaveScene(scene, Path.Combine(Evidence, "before-clock.unity"), true);
            var profilePath = AssetRoot + "/WardDayNight.asset"; var skyPath = AssetRoot + "/WardTimeSky.mat";
            if (File.Exists(profilePath) || File.Exists(skyPath)) throw new InvalidOperationException("Day/night assets already exist; recover the existing installation instead of replacing its tuning.");
            var noon = CaptureAuthored(key, fill, volume);
            var profile = ScriptableObject.CreateInstance<DayNightLightingProfile>(); profile.defaultHour = noon.hour; profile.startPaused = true;
            profile.frames = CreateFrames(noon);
            if (!profile.IsValid(out string reason)) throw new InvalidOperationException(reason);
            AssetDatabase.CreateAsset(profile, profilePath);
            var sky = new Material(RenderSettings.skybox) { name = "Ward time sky", shader = shader };
            sky.SetFloat("_SunVisibility", 1); sky.SetVector("_SunDirection", -key.transform.forward);
            AssetDatabase.CreateAsset(sky, skyPath);
            var go = new GameObject("Ward lighting clock"); Undo.RegisterCreatedObjectUndo(go, "Install Ward time of day");
            var clock = Undo.AddComponent<CityTimeOfDay>(go); var reflections = Undo.AddComponent<CityTimeReflections>(go);
            var circuit = Undo.AddComponent<CityLightCircuit>(go); var menu = Undo.AddComponent<DeveloperTimeMenu>(go);
            clock.profile = profile; clock.session = session; clock.keyLight = key; clock.skyFill = fill;
            clock.gradingVolume = volume; clock.timeAwareSky = sky; clock.reflections = reflections;
            reflections.clock = clock; reflections.viewer = hud.worldCamera.transform;
            reflections.probes = Object.FindObjectsByType<ReflectionProbe>()
                .OrderBy(p => p.cullingMask == 0 ? 0 : 1).Select(p => new TimeReflectionBinding { probe = p, globalSky = p.cullingMask == 0, runtimeResolution = p.cullingMask == 0 ? 128 : Mathf.Min(256, p.resolution) }).ToArray();
            circuit.clock = clock; circuit.viewer = hud.worldCamera.transform;
            circuit.practicalLights = Object.FindObjectsByType<Light>()
                .Where(l => l.type != LightType.Directional && l.name.IndexOf("lamp", StringComparison.OrdinalIgnoreCase) >= 0).ToArray();
            circuit.emissiveMaterials = AssetDatabase.FindAssets("t:Material LampEmission", new[] { "Assets/AthenHill" })
                .Select(g => AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(g))).Where(m => m && m.HasProperty("_EmissionColor")).ToArray();
            menu.clock = clock; menu.hud = hud; menu.layout = layout;
            foreach (var component in new Object[] { clock, reflections, circuit, menu }) EditorUtility.SetDirty(component);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene);
            WriteInstalledReport(clock, "installation");
            Selection.activeGameObject = go;
            Debug.Log("Ward clock installed at the captured authored default and paused. Save the scene and bind any new fixture lights/materials before native review.");
        }

        [MenuItem("Athen Hill/Day and night/Write installed clock report")]
        public static void ExportInstalledReport()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Export the saved configuration in Edit Mode.");
            var clock = Object.FindAnyObjectByType<CityTimeOfDay>();
            WriteInstalledReport(clock, "existing installation report export");
            Debug.Log("Existing Ward clock validated and installation.json written; scene and assets were not changed.");
        }

        static void WriteInstalledReport(CityTimeOfDay clock, string reportKind)
        {
            if (!clock || !clock.profile || !clock.profile.IsValid(out _) || !clock.keyLight || !clock.skyFill ||
                !clock.timeAwareSky || !clock.gradingVolume || !clock.session || !clock.reflections)
                throw new InvalidOperationException("The existing clock is missing a valid profile or required scene references.");
            var scene = clock.gameObject.scene;
            if (scene.path != "Assets/AthenHill/Scenes/AthenHill.unity") throw new InvalidOperationException("The clock is not in the authored AthenHill scene.");
            var reflections = clock.reflections; var circuit = clock.GetComponent<CityLightCircuit>(); var menu = clock.GetComponent<DeveloperTimeMenu>();
            if (!circuit || !menu || !menu.hud || !menu.layout) throw new InvalidOperationException("The existing light circuit or developer menu references are incomplete.");
            if (reflections.probes == null || reflections.probes.Any(p => p == null || !p.probe)) throw new InvalidOperationException("A serialized reflection binding is missing its probe.");
            // Unity's serializer writes only Vector3/Color fields. Passing these structs
            // straight to Newtonsoft also visits normalized/linear/gamma getters recursively.
            var authored = JToken.Parse(JsonUtility.ToJson(clock.profile.Evaluate(clock.profile.defaultHour)));
            var report = new
            {
                reportExportedUtc = DateTime.UtcNow.ToString("o"), reportKind, scene = scene.path, sceneHasUnsavedChanges = scene.isDirty,
                authored, profile = AssetDatabase.GetAssetPath(clock.profile), sky = AssetDatabase.GetAssetPath(clock.timeAwareSky),
                clock.profile.startPaused, clock.profile.realMinutesPerCycle,
                pipeline = GraphicsSettings.currentRenderPipeline ? GraphicsSettings.currentRenderPipeline.name : "unavailable",
                probes = reflections.probes.Select(p => new { p.probe.name, p.globalSky, p.runtimeResolution, configuredMode = p.probe.mode.ToString() }).ToArray(),
                practicalLights = (circuit.practicalLights ?? Array.Empty<Light>()).Where(l => l).Select(l => l.name).ToArray(),
                emissionMaterials = (circuit.emissiveMaterials ?? Array.Empty<Material>()).Where(m => m).Select(m => AssetDatabase.GetAssetPath(m)).ToArray(),
                lightmaps = LightmapSettings.lightmaps.Length,
                reviewRequired = "Save and reopen the scene, bind all new fixture lights/materials, run Edit Mode tests, then capture native dawn/noon/dusk/night and menu/release tests. This report does not build or accept visuals."
            };
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Path.Combine(Evidence, "installation.json"), JsonConvert.SerializeObject(report, Formatting.Indented));
        }

        public static DayNightFrame CaptureAuthored(Light key, Light fill, Volume volume)
        {
            var sky = RenderSettings.skybox; volume.sharedProfile.TryGet<ColorAdjustments>(out var adjustments);
            Color Read(string property, Color fallback) => sky.HasProperty(property) ? sky.GetColor(property) : fallback;
            return new DayNightFrame
            {
                hour = 12, keyEuler = key.transform.eulerAngles, keyColor = key.color, keyIntensity = key.intensity,
                fillColor = fill.color, fillIntensity = fill.intensity,
                ambientSky = RenderSettings.ambientSkyColor, ambientEquator = RenderSettings.ambientEquatorColor, ambientGround = RenderSettings.ambientGroundColor,
                skyZenith = Read("_Zenith", new Color(.24f, .39f, .57f)), skyMiddle = Read("_Middle", new Color(.54f, .64f, .68f)),
                skyHorizon = Read("_Horizon", RenderSettings.fogColor), cloudLight = Read("_CloudLight", Color.white), cloudShade = Read("_CloudShade", Color.gray),
                ridgeColor = Read("_RidgeColor", RenderSettings.fogColor), fogColor = RenderSettings.fogColor,
                sunVisibility = 1, lampStrength = 0, postExposure = adjustments ? adjustments.postExposure.value : 0,
                skyExposure = sky.HasProperty("_Exposure") ? sky.GetFloat("_Exposure") : 1, reflectionStrength = 1
            };
        }

        public static DayNightFrame[] CreateFrames(DayNightFrame noon)
        {
            var night = noon; night.hour = 0; night.keyEuler = new Vector3(32, 40, 0); night.keyColor = new Color(.48f, .63f, 1);
            night.keyIntensity = .07f; night.fillColor = new Color(.39f, .50f, .75f); night.fillIntensity = .025f;
            night.ambientSky = new Color(.032f, .055f, .09f); night.ambientEquator = new Color(.025f, .034f, .055f); night.ambientGround = new Color(.012f, .017f, .026f);
            night.skyZenith = new Color(.009f, .018f, .047f); night.skyMiddle = new Color(.018f, .032f, .070f); night.skyHorizon = new Color(.048f, .065f, .103f);
            night.cloudLight = new Color(.045f, .067f, .11f); night.cloudShade = new Color(.015f, .024f, .05f); night.ridgeColor = new Color(.025f, .036f, .058f);
            night.fogColor = new Color(.030f, .044f, .075f); night.sunVisibility = 0; night.lampStrength = 1; night.postExposure = .25f;
            var predawn = night; predawn.hour = 5.3f; predawn.keyEuler = new Vector3(0, 140, 0); predawn.keyIntensity = .008f;
            predawn.skyHorizon = new Color(.20f, .12f, .14f); predawn.skyMiddle = new Color(.09f, .12f, .20f); predawn.postExposure = .12f;
            var dawn = noon; dawn.hour = 6.5f; dawn.keyEuler = new Vector3(7, 145, 0); dawn.keyColor = new Color(1, .66f, .40f); dawn.keyIntensity = .68f;
            dawn.fillIntensity = .07f; dawn.ambientSky = new Color(.14f, .19f, .27f); dawn.ambientEquator = new Color(.18f, .135f, .11f); dawn.ambientGround = new Color(.07f, .055f, .045f);
            dawn.skyZenith = new Color(.12f, .22f, .40f); dawn.skyMiddle = new Color(.38f, .36f, .43f); dawn.skyHorizon = new Color(.75f, .39f, .23f);
            dawn.cloudLight = new Color(.80f, .48f, .30f); dawn.cloudShade = new Color(.22f, .22f, .30f); dawn.ridgeColor = new Color(.30f, .22f, .20f);
            dawn.fogColor = new Color(.39f, .28f, .24f); dawn.lampStrength = .72f; dawn.postExposure = -.15f;
            var dusk = dawn; dusk.hour = 17.5f; dusk.keyEuler = new Vector3(8, 295, 0); dusk.keyColor = new Color(1, .58f, .30f); dusk.keyIntensity = .64f;
            dusk.skyZenith = new Color(.095f, .16f, .30f); dusk.skyMiddle = new Color(.35f, .27f, .32f); dusk.skyHorizon = new Color(.76f, .32f, .14f);
            dusk.ambientSky = new Color(.13f, .16f, .24f); dusk.cloudLight = new Color(.85f, .38f, .18f); dusk.lampStrength = .78f;
            var blueHour = night; blueHour.hour = 19; blueHour.keyEuler = new Vector3(20, 30, 0); blueHour.keyIntensity = .04f;
            blueHour.skyHorizon = new Color(.12f, .12f, .19f); blueHour.skyMiddle = new Color(.045f, .06f, .13f); blueHour.ambientSky = new Color(.055f, .068f, .12f);
            return new[] { night, predawn, dawn, noon, dusk, blueHour };
        }
    }
}
#endif
