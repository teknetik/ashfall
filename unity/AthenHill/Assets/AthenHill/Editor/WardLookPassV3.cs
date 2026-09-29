using System;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// Look v3 (29 Sep 2026): the dust-bowl grade stacked seven warm shifts (white balance, colour filter, lift/gamma/gain,
    /// midtones, highlights, bloom tint, vignette), which turned every surface the same orange. This keeps its character
    /// but splits it: neutral base, slightly cool shadows, warm highlights, restrained grain. It also lifts moonlight so a
    /// street without lamps still reads at night. Values it replaces are logged for manual restore.
    public static class WardLookPassV3
    {
        const string GradePath = "Assets/AthenHill/Art/Atmosphere/Dustbowl/WardDustbowlGrade.asset";
        const string ProfilePath = "Assets/AthenHill/Art/DayNight/WardDayNight.asset";
        const string LogPath = "../evidence/rendering/20260929/look-v3.json";

        [MenuItem("Athen Hill/Rendering/Apply look v3 grade")]
        public static void Apply()
        {
            var log = new List<object>();
            var grade = AssetDatabase.LoadAssetAtPath<VolumeProfile>(GradePath);
            if (!grade) throw new InvalidOperationException("Grade profile missing: " + GradePath);
            if (grade.TryGet<WhiteBalance>(out var wb)) { log.Add(new { wb = new { wb.temperature.value, tint = wb.tint.value } }); wb.temperature.Override(1.5f); wb.tint.Override(0f); }
            if (grade.TryGet<ColorAdjustments>(out var ca))
            {
                log.Add(new { colorAdjustments = new { contrast = ca.contrast.value, filter = ca.colorFilter.value.ToString(), saturation = ca.saturation.value } });
                ca.contrast.Override(16f); ca.colorFilter.Override(new Color(1f, .99f, .975f)); ca.saturation.Override(4f);
            }
            if (grade.TryGet<LiftGammaGain>(out var lgg))
            {
                log.Add(new { lgg = new { lift = lgg.lift.value.ToString(), gamma = lgg.gamma.value.ToString(), gain = lgg.gain.value.ToString() } });
                lgg.lift.Override(new Vector4(.99f, 1f, 1.03f, -.01f)); lgg.gamma.Override(new Vector4(1f, 1f, 1f, 0f)); lgg.gain.Override(new Vector4(1.02f, 1f, .97f, 0f));
            }
            if (grade.TryGet<ShadowsMidtonesHighlights>(out var smh))
            {
                log.Add(new { smh = new { shadows = smh.shadows.value.ToString(), midtones = smh.midtones.value.ToString(), highlights = smh.highlights.value.ToString() } });
                smh.shadows.Override(new Vector4(.95f, .98f, 1.06f, 0f)); smh.midtones.Override(new Vector4(1f, 1f, .99f, 0f)); smh.highlights.Override(new Vector4(1.03f, 1f, .95f, 0f));
            }
            if (grade.TryGet<Bloom>(out var bloom))
            {
                log.Add(new { bloom = new { bloom.threshold.value, intensity = bloom.intensity.value, tint = bloom.tint.value.ToString() } });
                bloom.threshold.Override(1.1f); bloom.intensity.Override(.38f); bloom.tint.Override(new Color(1f, .95f, .88f));
            }
            if (grade.TryGet<Vignette>(out var vig))
            {
                log.Add(new { vignette = new { color = vig.color.value.ToString(), vig.intensity.value } });
                vig.color.Override(new Color(.05f, .05f, .06f)); vig.intensity.Override(.24f);
            }
            if (grade.TryGet<FilmGrain>(out var grain)) { log.Add(new { grain = grain.intensity.value }); grain.intensity.Override(.12f); }
            EditorUtility.SetDirty(grade);

            var profile = AssetDatabase.LoadAssetAtPath<DayNightLightingProfile>(ProfilePath);
            for (int i = 0; i < profile.frames.Length; i++)
            {
                ref var f = ref profile.frames[i];
                if (f.sunVisibility > .01f) continue;
                log.Add(new { nightFrame = f.hour, before = new { f.keyIntensity, sky = f.ambientSky.ToString(), f.postExposure } });
                float boost = 1.35f;
                f.keyIntensity = Mathf.Max(f.keyIntensity, .2f) * 1.6f;
                f.ambientSky *= boost; f.ambientEquator *= boost; f.ambientGround *= boost;
                f.postExposure += .15f;
            }
            if (!profile.IsValid(out var reason)) throw new InvalidOperationException(reason);
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(LogPath)));
            File.WriteAllText(LogPath, JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), log }, Formatting.Indented));
            Debug.Log("LOOK_V3 applied");
        }

        public static void ApplyBatch() { Apply(); EditorApplication.Exit(0); }
    }
}
