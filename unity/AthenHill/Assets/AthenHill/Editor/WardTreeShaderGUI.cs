#if UNITY_EDITOR
using System;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Editor
{
    // URP 17.6's LitShader is internal. Delegate its complete standard inspector
    // through ShaderGUI rather than duplicating keyword/blend/detail behavior.
    public sealed class WardTreeShaderGUI : ShaderGUI
    {
        const string LitTypeName = "UnityEditor.Rendering.Universal.ShaderGUI.LitShader";
        ShaderGUI litGUI;
        ShaderGUI Lit
        {
            get
            {
                if (litGUI == null)
                {
                    var type = typeof(BaseShaderGUI).Assembly.GetType(LitTypeName, true);
                    litGUI = Activator.CreateInstance(type, true) as ShaderGUI;
                    if (litGUI == null) throw new InvalidOperationException("Ward tree Inspector requires the pinned URP Lit ShaderGUI.");
                }
                return litGUI;
            }
        }

        static readonly GUIContent Wind = new GUIContent("Crown sway (metres)",
            "World-space crown sway amplitude, 0–0.3 metres. Uses the same reduced-motion-aware wind clock in visible and shadow passes.");
        static readonly GUIContent Flutter = new GUIContent("Leaf flutter (metres)",
            "Small leaf movement amplitude, 0–0.04 metres. Keep zero on trunk and branch materials.");
        static readonly GUIContent Direct = new GUIContent("Leaf sun transmission",
            "Leaf-tinted light from the main sun on backlit faces, 0–0.5. Either positive transmission control also enables the shader's two-sided leaf normal convention.");
        static readonly GUIContent Ambient = new GUIContent("Leaf ambient transmission",
            "Approximate light through a thin leaf from the opposite ambient/probe hemisphere, 0–0.5. Forward rendering with legacy probes only. Zero adds no ambient transmission; keep zero on bark.");

        public override void OnGUI(MaterialEditor materialEditor, MaterialProperty[] properties)
        {
            Lit.OnGUI(materialEditor, properties);
            EditorGUILayout.Space();
            EditorGUILayout.LabelField("Ward Tree", EditorStyles.boldLabel);
            EditorGUI.BeginChangeCheck();
            // ShaderProperty respects each shader Range, multi-material values,
            // Undo and property drawers without changing a value just by opening UI.
            materialEditor.ShaderProperty(FindProperty("_WardWindStrength", properties), Wind);
            materialEditor.ShaderProperty(FindProperty("_WardLeafFlutter", properties), Flutter);
            materialEditor.ShaderProperty(FindProperty("_WardTranslucency", properties), Direct);
            materialEditor.ShaderProperty(FindProperty("_WardIndirectTranslucency", properties), Ambient);
            if (EditorGUI.EndChangeCheck()) materialEditor.PropertiesChanged();
        }

        public override void ValidateMaterial(Material material) => Lit.ValidateMaterial(material);
        public override void AssignNewShaderToMaterial(Material material, Shader oldShader, Shader newShader)
            => Lit.AssignNewShaderToMaterial(material, oldShader, newShader);
        public override void OnClosed(Material material) => Lit.OnClosed(material);
        public override void OnMaterialPreviewGUI(MaterialEditor materialEditor, Rect rect, GUIStyle background)
            => Lit.OnMaterialPreviewGUI(materialEditor, rect, background);
        public override void OnMaterialPreviewSettingsGUI(MaterialEditor materialEditor)
            => Lit.OnMaterialPreviewSettingsGUI(materialEditor);
    }
}
#endif
