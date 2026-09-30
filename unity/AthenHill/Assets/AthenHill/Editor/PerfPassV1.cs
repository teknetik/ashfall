using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// GPU-time pass from the 30 Sep native profiles (the player is GPU-bound: Gfx.PresentFrame 7–9 ms):
    /// half-resolution SSAO with high-quality blur, screen-space decals drawn to 45 m instead of 70 m, and the hero tree's
    /// 3.7 M-triangle LOD0 limited to ~23 m (LODGroup size halved; LOD1 1.8 M beyond). Logs before/after; re-running
    /// re-applies the same values.
    public static class PerfPassV1
    {
        const string RendererPath = "Assets/Settings/PC_Renderer.asset";

        public static void ApplyBatch()
        {
            int code = 0;
            try { Apply(); } catch (Exception e) { Debug.LogException(e); code = 1; }
            EditorApplication.Exit(code);
        }

        public static void Apply()
        {
            var log = new System.Collections.Generic.List<object>();
            var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererPath);
            foreach (var f in renderer.rendererFeatures.Where(f => f))
            {
                var so = new SerializedObject(f);
                if (f.GetType().Name == "ScreenSpaceAmbientOcclusion")
                {
                    var d = so.FindProperty("m_Settings.Downsample"); var b = so.FindProperty("m_Settings.BlurQuality");
                    log.Add(new { ssao = new { downsampleBefore = d.boolValue, blurBefore = b.intValue } });
                    d.boolValue = true; b.intValue = 0; // 0 = High
                }
                else if (f.GetType().Name == "DecalRendererFeature")
                {
                    var m = so.FindProperty("m_Settings.maxDrawDistance");
                    log.Add(new { decals = f.name, maxDrawDistanceBefore = m.floatValue }); m.floatValue = 45;
                }
                so.ApplyModifiedPropertiesWithoutUndo(); EditorUtility.SetDirty(f);
            }
            AssetDatabase.SaveAssets();

            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var tree = GameObject.Find("Ward oasis tree");
            var lod = tree ? tree.GetComponentInChildren<LODGroup>() : null;
            if (!lod) throw new InvalidOperationException("Hero tree LODGroup not found.");
            const float TargetSize = 10.75f;
            log.Add(new { tree = lod.name, sizeBefore = lod.size, sizeAfter = TargetSize });
            if (!Mathf.Approximately(lod.size, TargetSize)) { lod.size = TargetSize; EditorUtility.SetDirty(lod); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); }
            var path = Path.GetFullPath(Path.Combine(Application.dataPath, "../../evidence/rendering/20260930/perf-pass-v1.json"));
            File.WriteAllText(path, JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), log }, Formatting.Indented));
            Debug.Log("PERF_PASS_V1 " + JsonConvert.SerializeObject(log));
        }
    }
}
