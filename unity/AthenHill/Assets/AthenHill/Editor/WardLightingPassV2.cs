using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// Lighting v2 (29 Sep 2026): a readable sun/shade contrast by day, aerial perspective that starts at a
    /// street's length instead of 12 m, a moonlit night lit by real practical lamps, and render chunks that
    /// cull and stop casting shadows from flat ground. Run once; it refuses if the lamp circuit already reaches 150 m.
    /// Every value it replaces is written to the evidence log so it can be restored by hand.
    public static class WardLightingPassV2
    {
        const string ProfilePath = "Assets/AthenHill/Art/DayNight/WardDayNight.asset";
        const string LogPath = "../evidence/rendering/20260929/lighting-v2.json";
        const float LampReach = 150;

        [MenuItem("Athen Hill/Rendering/Apply lighting v2")]
        public static void Apply()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play first.");
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            if (!circuit) throw new InvalidOperationException("City light circuit is missing.");
            if (Mathf.Approximately(circuit.culledLightDistance, LampReach)) throw new InvalidOperationException("Lighting v2 is already applied.");
            var log = new List<object>();

            RenderingUpgradePass.Apply();

            // Day/night palette. Frames are matched by hour; anything not listed keeps its authored value.
            var profile = AssetDatabase.LoadAssetAtPath<DayNightLightingProfile>(ProfilePath);
            var moon = new Color(.55f, .68f, 1f);
            var targets = new Dictionary<float, Action<DayNightFrame[], int>>
            {
                [0f] = (f, i) => Night(ref f[i], .34f, moon, .075f, .5f),
                [5.3f] = (f, i) => Night(ref f[i], .16f, moon, .07f, .45f),
                [6.5f] = (f, i) => { f[i].keyIntensity = .95f; f[i].ambientSky = new Color(.17f, .22f, .31f); f[i].fogColor = new Color(.56f, .47f, .4f); f[i].postExposure = -.12f; },
                [12f] = (f, i) => { f[i].keyIntensity = 2.3f; f[i].keyColor = new Color(1f, .93f, .84f); f[i].ambientSky = new Color(.36f, .46f, .62f); f[i].ambientEquator = new Color(.42f, .4f, .36f); f[i].ambientGround = new Color(.3f, .25f, .2f); f[i].fogColor = new Color(.74f, .69f, .62f); f[i].postExposure = -.62f; },
                [17.5f] = (f, i) => { f[i].keyIntensity = 1.25f; f[i].keyColor = new Color(1f, .6f, .32f); f[i].ambientSky = new Color(.2f, .24f, .34f); f[i].fogColor = new Color(.66f, .5f, .38f); f[i].postExposure = -.25f; },
                [19f] = (f, i) => Night(ref f[i], .3f, moon, .08f, .5f),
            };
            var before = profile.frames.Select(x => x).ToArray();
            for (int i = 0; i < profile.frames.Length; i++)
                foreach (var t in targets) if (Mathf.Abs(profile.frames[i].hour - t.Key) < .01f) t.Value(profile.frames, i);
            if (!profile.IsValid(out var reason)) throw new InvalidOperationException("Profile invalid after edit: " + reason);
            log.Add(new { step = "day-night profile", asset = ProfilePath, before = before.Select(Describe), after = profile.frames.Select(Describe) });
            EditorUtility.SetDirty(profile);

            // Aerial perspective: fog starts past the width of a street and reaches the far ridges.
            log.Add(new { step = "fog", before = new { RenderSettings.fogMode, RenderSettings.fogStartDistance, RenderSettings.fogEndDistance }, after = new { start = 38, end = 420 } });
            RenderSettings.fogMode = FogMode.Linear; RenderSettings.fogStartDistance = 38; RenderSettings.fogEndDistance = 420;

            // Practical lamps: Forward+ lifts the per-object light limit, so lamps can reach and overlap like real ones.
            log.Add(new { step = "light circuit", before = new { circuit.fullLightDistance, circuit.culledLightDistance, circuit.shadowDistance }, after = new { full = 90, culled = LampReach, shadow = 32 } });
            circuit.fullLightDistance = 90; circuit.culledLightDistance = LampReach; circuit.shadowDistance = 32;
            foreach (var light in circuit.practicalLights.Where(l => l && l.type != LightType.Directional).Distinct())
            {
                var b = new { light.intensity, light.range };
                light.intensity = Mathf.Min(light.intensity * 2.4f, 24f); light.range = Mathf.Min(light.range * 1.6f, 26f);
                log.Add(new { step = "lamp", path = PathOf(light.transform), before = b, after = new { light.intensity, light.range } });
                EditorUtility.SetDirty(light);
            }
            EditorUtility.SetDirty(circuit);

            // Render chunks: flat ground receives shadows but does not cast them; ~24 m cells let the camera cull.
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks)
            {
                chunks.ShowSources(true);
                int flat = 0; long flatTris = 0;
                foreach (var r in chunks.sourceRoots.Where(t => t).SelectMany(t => t.GetComponentsInChildren<MeshRenderer>(true)).Distinct())
                {
                    if (r.name.StartsWith("COL_") || r.shadowCastingMode != ShadowCastingMode.On) continue;
                    var filter = r.GetComponent<MeshFilter>(); if (!filter || !filter.sharedMesh) continue;
                    var size = r.bounds.size;
                    if (size.y < .16f && size.x * size.z > .5f)
                    {
                        r.shadowCastingMode = ShadowCastingMode.Off; EditorUtility.SetDirty(r); flat++;
                        for (int s = 0; s < filter.sharedMesh.subMeshCount; s++) flatTris += filter.sharedMesh.GetIndexCount(s) / 3;
                    }
                }
                log.Add(new { step = "render chunks", flatGroundSourcesShadowOff = flat, flatTris, before = new { chunks.cellSize, chunks.cellDepth }, after = new { cellSize = 24, cellDepth = 24 } });
                chunks.cellSize = 24; chunks.cellDepth = 24; EditorUtility.SetDirty(chunks);
                StaticRenderChunksEditor.Rebuild(chunks);
            }

            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(LogPath)));
            File.WriteAllText(LogPath, JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), log }, Formatting.Indented, new JsonSerializerSettings { ReferenceLoopHandling = ReferenceLoopHandling.Ignore }));
            Debug.Log("LIGHTING_V2 applied; log " + LogPath);
        }

        public static void ApplyBatch() { Apply(); EditorApplication.Exit(0); }

        static void Night(ref DayNightFrame f, float moonIntensity, Color moon, float ambient, float exposure)
        {
            f.keyIntensity = moonIntensity; f.keyColor = moon; f.fillIntensity = .06f;
            f.ambientSky = new Color(ambient, ambient * 1.4f, ambient * 2.25f);
            f.ambientEquator = new Color(ambient * .8f, ambient * .95f, ambient * 1.35f);
            f.ambientGround = new Color(ambient * .55f, ambient * .55f, ambient * .65f);
            f.fogColor = new Color(.055f, .075f, .115f); f.postExposure = exposure; f.lampStrength = 1;
        }

        static object Describe(DayNightFrame f) => new { f.hour, f.keyIntensity, key = f.keyColor.ToString(), f.fillIntensity, sky = f.ambientSky.ToString(), equator = f.ambientEquator.ToString(), ground = f.ambientGround.ToString(), fog = f.fogColor.ToString(), f.postExposure, f.lampStrength };
        static string PathOf(Transform t) { var parts = new List<string>(); for (; t; t = t.parent) parts.Add(t.name); parts.Reverse(); return string.Join("/", parts); }
    }
}
