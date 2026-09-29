using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// Palette v3 for the day/night profile the scene clock actually uses (read from CityTimeOfDay, not a path).
    /// Keeps the dust-bowl identity but gives shade a blue skylight, pales the distant haze, strengthens the sun
    /// against its exposure, and makes moonlight strong enough to read a street without lamps.
    /// Refuses to run twice (noon key above 2.0 means it has been applied). Before values go to the evidence log.
    public static class WardPalettePassV3
    {
        const string LogPath = "../evidence/rendering/20260929/palette-v3.json";

        [MenuItem("Athen Hill/Rendering/Apply palette v3 to the clock profile")]
        public static void Apply()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>();
            if (!clock || !clock.profile) throw new InvalidOperationException("Scene clock or its profile is missing.");
            var profile = clock.profile; var path = AssetDatabase.GetAssetPath(profile);
            var noon = profile.frames.FirstOrDefault(f => Mathf.Abs(f.hour - 12) < .01f);
            if (noon.keyIntensity > 2f) throw new InvalidOperationException("Palette v3 is already applied to " + path);
            var before = profile.frames.Select(Describe).ToArray();
            var moon = new Color(.55f, .68f, 1f);
            for (int i = 0; i < profile.frames.Length; i++)
            {
                ref var f = ref profile.frames[i];
                switch (Mathf.RoundToInt(f.hour * 10))
                {
                    case 0: case 53: case 190: Night(ref f, f.hour == 5.3f ? .3f : .42f, moon); break;
                    case 65: f.keyIntensity = .95f; f.ambientSky = new Color(.17f, .22f, .31f); break;
                    case 120: f.keyIntensity = 2.1f; f.keyColor = new Color(1f, .9f, .76f); f.ambientSky = new Color(.33f, .4f, .52f); f.fogColor = new Color(.7f, .62f, .5f); f.postExposure = -.5f; break;
                    case 160: f.keyIntensity = 1.8f; f.keyColor = new Color(1f, .78f, .55f); f.ambientSky = new Color(.28f, .33f, .44f); f.fogColor = new Color(.66f, .53f, .4f); f.postExposure = -.42f; break;
                    case 170: f.keyIntensity = 1.35f; f.ambientSky = new Color(.26f, .32f, .45f); f.postExposure = -.22f; break;
                    case 175: f.keyIntensity = .95f; break;
                }
            }
            if (!profile.IsValid(out var reason)) throw new InvalidOperationException(reason);
            EditorUtility.SetDirty(profile); AssetDatabase.SaveAssets();
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(LogPath)));
            File.WriteAllText(LogPath, JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), profile = path, before, after = profile.frames.Select(Describe) }, Formatting.Indented));
            Debug.Log("PALETTE_V3 applied to " + path);
        }

        public static void ApplyBatch() { Apply(); EditorApplication.Exit(0); }

        static void Night(ref DayNightFrame f, float key, Color moon)
        {
            f.keyIntensity = key; f.keyColor = moon; f.fillIntensity = .05f;
            f.ambientSky = new Color(.075f, .105f, .17f); f.ambientEquator = new Color(.06f, .072f, .1f); f.ambientGround = new Color(.04f, .042f, .05f);
            f.fogColor = new Color(.05f, .068f, .105f); f.postExposure = .55f; f.lampStrength = 1;
        }

        static object Describe(DayNightFrame f) => new { f.hour, f.keyIntensity, key = f.keyColor.ToString(), f.fillIntensity, sky = f.ambientSky.ToString(), equator = f.ambientEquator.ToString(), ground = f.ambientGround.ToString(), fog = f.fogColor.ToString(), f.postExposure, f.lampStrength };
    }
}
