using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// Rendering baseline for the PC quality level: long, cascaded sun shadows, Forward+ so every practical
    /// lamp reaches every surface at night, HDR grading, and screen-space AO tuned for a sunlit desert town.
    /// Re-running re-applies the same values; each change is logged with its previous value.
    public static class RenderingUpgradePass
    {
        const string PipelinePath = "Assets/Settings/PC_RPAsset.asset";
        const string RendererPath = "Assets/Settings/PC_Renderer.asset";
        const string ReportPath = "../evidence/rendering/20260929/rendering-upgrade.json";

        [MenuItem("Athen Hill/Rendering/Apply PC rendering baseline")]
        public static void Apply()
        {
            var changes = new System.Collections.Generic.List<object>();
            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(PipelinePath);
            var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererPath);
            if (!pipeline || !renderer) throw new InvalidOperationException("PC pipeline or renderer asset is missing.");

            var p = new SerializedObject(pipeline);
            Set(p, "m_ShadowDistance", 150f, changes);
            Set(p, "m_ShadowCascadeCount", 4, changes);
            Set(p, "m_Cascade4Split", new Vector3(.04f, .12f, .34f), changes);
            Set(p, "m_Cascade3Split", new Vector2(.1f, .35f), changes);
            Set(p, "m_Cascade2Split", .25f, changes);
            Set(p, "m_CascadeBorder", .15f, changes);
            Set(p, "m_MainLightShadowmapResolution", 4096, changes);
            Set(p, "m_ShadowDepthBias", .6f, changes);
            Set(p, "m_ShadowNormalBias", .6f, changes);
            Set(p, "m_SoftShadowQuality", 3, changes);
            Set(p, "m_SoftShadowsSupported", true, changes);
            Set(p, "m_AdditionalLightShadowsSupported", true, changes);
            Set(p, "m_AdditionalLightsShadowmapResolution", 4096, changes);
            Set(p, "m_AdditionalLightsPerObjectLimit", 8, changes);
            Set(p, "m_SupportsHDR", true, changes);
            Set(p, "m_ColorGradingMode", (int)ColorGradingMode.HighDynamicRange, changes);
            Set(p, "m_ColorGradingLutSize", 32, changes);
            p.ApplyModifiedPropertiesWithoutUndo();

            var r = new SerializedObject(renderer);
            Set(r, "m_RenderingMode", (int)RenderingMode.ForwardPlus, changes);
            r.ApplyModifiedPropertiesWithoutUndo();

            var ssao = renderer.rendererFeatures.FirstOrDefault(f => f && f.GetType().Name == "ScreenSpaceAmbientOcclusion");
            if (ssao)
            {
                var s = new SerializedObject(ssao);
                Set(s, "m_Settings.Intensity", .85f, changes);
                Set(s, "m_Settings.Radius", .5f, changes);
                Set(s, "m_Settings.DirectLightingStrength", .35f, changes);
                Set(s, "m_Settings.Falloff", 60f, changes);
                Set(s, "m_Settings.Samples", 1, changes);
                Set(s, "m_Settings.BlurQuality", 0, changes);
                Set(s, "m_Settings.AOMethod", 0, changes);
                s.ApplyModifiedPropertiesWithoutUndo();
            }
            else changes.Add(new { property = "ScreenSpaceAmbientOcclusion", note = "feature not found" });

            EditorUtility.SetDirty(pipeline); EditorUtility.SetDirty(renderer); if (ssao) EditorUtility.SetDirty(ssao);
            AssetDatabase.SaveAssets();
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(ReportPath)));
            File.WriteAllText(ReportPath, JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), pipeline = PipelinePath, renderer = RendererPath, changes }, Formatting.Indented));
            Debug.Log("RENDERING_UPGRADE applied " + changes.Count + " settings");
        }

        public static void ApplyBatch() { Apply(); EditorApplication.Exit(0); }

        static void Set(SerializedObject o, string path, object value, System.Collections.Generic.List<object> log)
        {
            var sp = o.FindProperty(path);
            if (sp == null) { log.Add(new { asset = o.targetObject.name, property = path, note = "missing" }); return; }
            object before;
            switch (sp.propertyType)
            {
                case SerializedPropertyType.Float: before = sp.floatValue; sp.floatValue = Convert.ToSingle(value); break;
                case SerializedPropertyType.Integer: before = sp.intValue; sp.intValue = Convert.ToInt32(value); break;
                case SerializedPropertyType.Enum: before = sp.intValue; sp.intValue = Convert.ToInt32(value); break;
                case SerializedPropertyType.Boolean: before = sp.boolValue; sp.boolValue = (bool)value; break;
                case SerializedPropertyType.Vector2: before = sp.vector2Value.ToString(); sp.vector2Value = (Vector2)value; break;
                case SerializedPropertyType.Vector3: before = sp.vector3Value.ToString(); sp.vector3Value = (Vector3)value; break;
                default: log.Add(new { asset = o.targetObject.name, property = path, note = "unsupported type " + sp.propertyType }); return;
            }
            log.Add(new { asset = o.targetObject.name, property = path, before, after = value is Vector2 || value is Vector3 ? value.ToString() : value });
        }
    }
}
