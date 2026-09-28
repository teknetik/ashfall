using System;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Editor
{
    /// 27 September 2026 (Carl, second pass): start the game late in the afternoon, just as it's getting dark.
    /// Adds an authored 17:00 "golden dusk" frame to the accepted Dustbowl profile and makes it the default hour.
    /// Idempotent: re-running replaces the 17:00 frame. Rollback: remove the 17:00 frame and set defaultHour back to 16.
    public static class DuskStartPass
    {
        const string ProfilePath = "Assets/AthenHill/Art/Atmosphere/Dustbowl/WardDustbowl.asset";
        public const float DuskHour = 17f;

        [MenuItem("Athen Hill/Atmosphere/Start at golden dusk (17:00)")]
        public static string Install()
        {
            var profile = AssetDatabase.LoadAssetAtPath<DayNightLightingProfile>(ProfilePath);
            if (!profile) throw new InvalidOperationException("Missing " + ProfilePath);
            var frames = profile.frames.Where(f => Mathf.Abs(f.hour - DuskHour) > .01f).ToList();
            var late = frames.First(f => Mathf.Abs(f.hour - 16f) < .01f);
            var dusk = late;
            dusk.hour = DuskHour;
            // Low sun (11° elevation), raking across the district; yaw sits between the 16:00 and 17:30 frames.
            dusk.keyEuler = new Vector3(11f, 230f, 0f);
            dusk.keyColor = new Color(1f, .6f, .33f); dusk.keyIntensity = .98f;
            // Cooler sky fill and a slightly bluer ambient so shade reads cool rather than crushed.
            dusk.fillColor = new Color(.62f, .72f, .95f); dusk.fillIntensity = .15f;
            dusk.ambientSky = new Color(.27f, .32f, .42f); dusk.ambientEquator = new Color(.34f, .27f, .21f);
            dusk.ambientGround = new Color(.19f, .15f, .11f);
            dusk.skyZenith = new Color(.13f, .21f, .37f); dusk.skyMiddle = new Color(.48f, .38f, .38f);
            dusk.skyHorizon = new Color(.86f, .45f, .2f);
            dusk.cloudLight = new Color(.96f, .56f, .3f); dusk.cloudShade = new Color(.34f, .29f, .33f);
            dusk.ridgeColor = new Color(.44f, .31f, .23f); dusk.fogColor = new Color(.52f, .37f, .26f);
            dusk.sunVisibility = 1f; dusk.lampStrength = .45f; // lamps warming up as the light goes
            dusk.postExposure = -.12f; dusk.skyExposure = .98f; dusk.reflectionStrength = .95f;
            frames.Add(dusk);
            profile.frames = frames.OrderBy(f => f.hour).ToArray();
            profile.defaultHour = DuskHour;
            if (!profile.IsValid(out var reason)) throw new InvalidOperationException(reason);
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();
            return $"frames={profile.frames.Length} default={profile.defaultHour}";
        }

        /// Edit-mode preview: applies a profile hour to the key/fill lights, ambient, fog, sky and exposure the way
        /// CityTimeOfDay does in Play Mode, renders 1920x1080 views, then restores everything. Nothing is saved.
        public static string Preview(float hour, string outDir, params string[] cameras)
        {
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var f = clock.profile.Evaluate(hour);
            var key = clock.keyLight; var fill = clock.skyFill;
            var kRot = key.transform.rotation; var kCol = key.color; var kI = key.intensity;
            Color fCol = fill ? fill.color : default; float fI = fill ? fill.intensity : 0;
            var aMode = RenderSettings.ambientMode; var aS = RenderSettings.ambientSkyColor; var aE = RenderSettings.ambientEquatorColor;
            var aG = RenderSettings.ambientGroundColor; var fog = RenderSettings.fogColor; var sky = RenderSettings.skybox; var sun = RenderSettings.sun;
            var tt = Shader.GetGlobalVector("_AthenTerrainTime"); var th = Shader.GetGlobalVector("_AthenTerrainHazeScale");
            var skyMat = new Material(clock.timeAwareSky);
            UnityEngine.Rendering.VolumeProfile tmp = null; UnityEngine.Rendering.VolumeProfile shared = clock.gradingVolume ? clock.gradingVolume.sharedProfile : null;
            try
            {
                key.transform.rotation = Quaternion.Euler(f.keyEuler); key.color = f.keyColor; key.intensity = f.keyIntensity;
                if (fill) { fill.color = f.fillColor; fill.intensity = f.fillIntensity; }
                RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
                RenderSettings.ambientSkyColor = f.ambientSky; RenderSettings.ambientEquatorColor = f.ambientEquator;
                RenderSettings.ambientGroundColor = f.ambientGround; RenderSettings.fogColor = f.fogColor;
                Shader.SetGlobalVector("_AthenTerrainTime", new Vector4(1, TerrainTimeLighting.AuthoredShadowWeight(kRot, key.transform.rotation, f.sunVisibility), 0, 0));
                Shader.SetGlobalVector("_AthenTerrainHazeScale", TerrainTimeLighting.HazeScale(fog, f.fogColor, QualitySettings.activeColorSpace == ColorSpace.Linear));
                skyMat.SetColor("_Zenith", f.skyZenith); skyMat.SetColor("_Middle", f.skyMiddle); skyMat.SetColor("_Horizon", f.skyHorizon);
                skyMat.SetColor("_CloudLight", f.cloudLight); skyMat.SetColor("_CloudShade", f.cloudShade); skyMat.SetColor("_RidgeColor", f.ridgeColor);
                skyMat.SetFloat("_Exposure", f.skyExposure); skyMat.SetFloat("_SunVisibility", f.sunVisibility); skyMat.SetVector("_SunDirection", -key.transform.forward);
                RenderSettings.skybox = skyMat; RenderSettings.sun = key;
                if (shared)
                {
                    tmp = ScriptableObject.CreateInstance<UnityEngine.Rendering.VolumeProfile>();
                    foreach (var comp in shared.components) tmp.components.Add(UnityEngine.Object.Instantiate(comp));
                    if (!tmp.TryGet(out UnityEngine.Rendering.Universal.ColorAdjustments ca)) ca = tmp.Add<UnityEngine.Rendering.Universal.ColorAdjustments>();
                    ca.postExposure.overrideState = true; ca.postExposure.value = f.postExposure; clock.gradingVolume.sharedProfile = tmp;
                }
                var main = GameObject.Find("MainCamera").GetComponent<Camera>();
                var go = new GameObject("__dusk") { hideFlags = HideFlags.DontSave }; var cam = go.AddComponent<Camera>(); cam.CopyFrom(main);
                var src = main.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
                var dst = go.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
                if (src) { dst.renderPostProcessing = src.renderPostProcessing; dst.antialiasing = src.antialiasing; dst.renderShadows = true; }
                cam.enabled = false; cam.nearClipPlane = .05f; cam.farClipPlane = 650;
                var rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 }; var tex = new Texture2D(1920, 1080, TextureFormat.RGB24, false);
                System.IO.Directory.CreateDirectory(outDir);
                var log = new System.Text.StringBuilder();
                foreach (var spec in cameras)
                {
                    string name;
                    if (spec.Contains(':'))
                    {
                        var p = spec.Split(':'); name = p[0];
                        Vector3 V(string s) { var a = s.Split(',').Select(float.Parse).ToArray(); return new Vector3(a[0], a[1], a[2]); }
                        go.transform.position = V(p[1]); go.transform.LookAt(V(p[2])); cam.fieldOfView = float.Parse(p[3]);
                    }
                    else
                    {
                        name = spec; var c = GameObject.Find(spec); if (!c) { log.AppendLine("missing " + spec); continue; }
                        go.transform.SetPositionAndRotation(c.transform.position, c.transform.rotation); cam.fieldOfView = c.GetComponent<Camera>().fieldOfView;
                    }
                    cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1920, 1080), 0, 0); tex.Apply();
                    System.IO.File.WriteAllBytes($"{outDir}/{name}_{hour:00.0}.png", tex.EncodeToPNG()); log.AppendLine(name);
                }
                RenderTexture.active = null; cam.targetTexture = null; UnityEngine.Object.DestroyImmediate(go); rt.Release();
                return log.ToString();
            }
            finally
            {
                key.transform.rotation = kRot; key.color = kCol; key.intensity = kI;
                if (fill) { fill.color = fCol; fill.intensity = fI; }
                RenderSettings.ambientMode = aMode; RenderSettings.ambientSkyColor = aS; RenderSettings.ambientEquatorColor = aE; RenderSettings.ambientGroundColor = aG;
                RenderSettings.fogColor = fog; RenderSettings.skybox = sky; RenderSettings.sun = sun;
                Shader.SetGlobalVector("_AthenTerrainTime", tt); Shader.SetGlobalVector("_AthenTerrainHazeScale", th);
                if (shared) clock.gradingVolume.sharedProfile = shared;
                if (tmp) { foreach (var comp in tmp.components) UnityEngine.Object.DestroyImmediate(comp); UnityEngine.Object.DestroyImmediate(tmp); }
                UnityEngine.Object.DestroyImmediate(skyMat);
            }
        }
    }
}
