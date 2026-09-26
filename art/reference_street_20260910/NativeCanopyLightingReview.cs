#if UNITY_EDITOR || DEBUG
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill
{
    // Transient opt-in diagnostic views. No source assets or preferences are written.
    internal sealed class NativeCanopyLightingReview
    {
        const string LampName = "Lamp warm Finery entrance light";
        readonly Dictionary<Material, Vector2> normalDefaults = new Dictionary<Material, Vector2>();
        readonly Dictionary<Renderer, ShadowCastingMode> shadowDefaults = new Dictionary<Renderer, ShadowCastingMode>();
        Light lamp;
        string mode = "baseline";
        Camera overriddenCamera;
        bool originalEnabled;
        LightShadows originalShadows;
        object lastRenderedLight;
        Material[] observedMaterials = Array.Empty<Material>();
        Renderer[] observedRenderers = Array.Empty<Renderer>();

        public void SetMode(string value)
        {
            if (!new[] { "baseline", "lampOff", "lampShadowsOff", "clothNormalsOff", "canopyShadowsOff" }.Contains(value))
                throw new ArgumentException("Unknown bounded canopy lighting diagnostic.", nameof(value));
            Restore();
            var lights = UnityEngine.Object.FindObjectsByType<Light>()
                .Where(l => l.name == LampName && l.type == LightType.Point).ToArray();
            if (lights.Length != 1) throw new InvalidOperationException("Expected the single authored Finery point light.");
            lamp = lights[0];
            var names = new[] { "Membrane", "Valance", "Seam", "Repair" }
                .Select(f => "Finery weathered canvas " + f + " v2").ToArray();
            var renderers = UnityEngine.Object.FindObjectsByType<Renderer>()
                .Where(r => r.enabled && r.sharedMaterials.Any(m => m && names.Contains(m.name))).ToArray();
            var materials = renderers.SelectMany(r => r.sharedMaterials)
                .Where(m => m && names.Contains(m.name)).Distinct().ToArray();
            if (materials.Length != 4 || materials.Any(m => m.shader.name != "Universal Render Pipeline/Lit"))
                throw new InvalidOperationException("Expected the four current canvas Lit materials on active renderers.");
            observedMaterials = materials; observedRenderers = renderers;
            if (value == "clothNormalsOff")
            {
                foreach (var material in materials)
                {
                    normalDefaults.Add(material, new Vector2(material.GetFloat("_BumpScale"), material.GetFloat("_DetailNormalMapScale")));
                    material.SetFloat("_BumpScale", 0); material.SetFloat("_DetailNormalMapScale", 0);
                }
            }
            if (value == "canopyShadowsOff")
            {
                // A combined renderer must contain only the selected cloth family.
                if (renderers.Any(r => r.sharedMaterials.Any(m => !m || !names.Contains(m.name))))
                    throw new InvalidOperationException("A cloth renderer also contains unrelated material slots.");
                foreach (var renderer in renderers)
                {
                    shadowDefaults.Add(renderer, renderer.shadowCastingMode);
                    renderer.shadowCastingMode = ShadowCastingMode.Off;
                }
            }
            mode = value;
            // This callback runs after the normal lamp circuit refresh and before
            // URP culling/shadows. End-camera restores its exact instantaneous state.
            RenderPipelineManager.beginCameraRendering += BeginCamera;
            RenderPipelineManager.endCameraRendering += EndCamera;
        }

        void BeginCamera(ScriptableRenderContext context, Camera camera)
        {
            if (!lamp || !camera.CompareTag("MainCamera")) return;
            if (overriddenCamera) RestoreLight();
            originalEnabled = lamp.enabled; originalShadows = lamp.shadows;
            overriddenCamera = camera;
            if (mode == "lampOff") lamp.enabled = false;
            if (mode == "lampShadowsOff") lamp.shadows = LightShadows.None;
            lastRenderedLight = new { frame = Time.frameCount, camera = camera.name,
                circuitEnabled = originalEnabled, circuitShadows = originalShadows.ToString(),
                renderedEnabled = lamp.enabled, renderedShadows = lamp.shadows.ToString(), intensity = lamp.intensity,
                shadowStrength = lamp.shadowStrength, bias = lamp.shadowBias, normalBias = lamp.shadowNormalBias,
                nearPlane = lamp.shadowNearPlane, range = lamp.range,
                position = new[] { lamp.transform.position.x, lamp.transform.position.y, lamp.transform.position.z } };
        }

        void EndCamera(ScriptableRenderContext context, Camera camera)
        {
            if (camera == overriddenCamera) RestoreLight();
        }

        void RestoreLight()
        {
            if (lamp && overriddenCamera) { lamp.enabled = originalEnabled; lamp.shadows = originalShadows; }
            overriddenCamera = null;
        }

        public object Snapshot() => new { mode, diagnosticOnly = true,
            scope = "Main-camera lamp and canvas A/B diagnosis; reflections retain normal lighting. Not an art or performance acceptance frame.",
            lastRenderedLight,
            materials = observedMaterials.Where(m => m).OrderBy(m => m.name).Select(m => new { material = m.name,
                baseNormalScale = m.GetFloat("_BumpScale"), detailNormalScale = m.GetFloat("_DetailNormalMapScale"),
                shaderKeywords = m.shaderKeywords.OrderBy(k => k).ToArray() }).ToArray(),
            renderers = observedRenderers.Where(r => r).OrderBy(r => r.name).Select(r => new { renderer = r.name,
                shadowCastingMode = r.shadowCastingMode.ToString() }).ToArray(),
            normals = normalDefaults.Select(p => new { material = p.Key.name, originalBase = p.Value.x,
                originalDetail = p.Value.y, currentBase = p.Key.GetFloat("_BumpScale"), currentDetail = p.Key.GetFloat("_DetailNormalMapScale") }).ToArray(),
            shadowRenderers = shadowDefaults.Select(p => new { renderer = p.Key.name, original = p.Value.ToString(), current = p.Key.shadowCastingMode.ToString() }).ToArray() };

        public void Restore()
        {
            RenderPipelineManager.beginCameraRendering -= BeginCamera;
            RenderPipelineManager.endCameraRendering -= EndCamera;
            RestoreLight();
            foreach (var pair in normalDefaults) if (pair.Key)
            { pair.Key.SetFloat("_BumpScale", pair.Value.x); pair.Key.SetFloat("_DetailNormalMapScale", pair.Value.y); }
            normalDefaults.Clear();
            foreach (var pair in shadowDefaults) if (pair.Key) pair.Key.shadowCastingMode = pair.Value;
            shadowDefaults.Clear(); lamp = null; mode = "baseline"; lastRenderedLight = null;
        }
    }
}
#endif
