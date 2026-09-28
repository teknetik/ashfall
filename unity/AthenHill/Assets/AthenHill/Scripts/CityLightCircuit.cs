using System;
using System.Collections.Generic;
using UnityEngine;

namespace AthenHill
{
    // Ordinary authored fixtures supply lights and emissive materials; no geometry is built here.
    public sealed class CityLightCircuit : MonoBehaviour
    {
        public CityTimeOfDay clock;
        public Transform viewer;
        public Light[] practicalLights = Array.Empty<Light>();
        public Material[] emissiveMaterials = Array.Empty<Material>();
        [Range(0, 1)] public float daytimeStrength = .04f;
        [Min(0)] public float fullLightDistance = 28;
        [Min(1)] public float culledLightDistance = 42;
        [Min(0)] public float shadowDistance = 18;
        /// Fixtures listed here switch off entirely below this circuit strength (daylight), instead of running
        /// at daytimeStrength; floodlights whose light is invisible in sun should not cost lighting or shadows.
        public Light[] nightOnlyLights = Array.Empty<Light>();
        [Range(0, 1)] public float nightOnlyThreshold = .2f;
        /// Practical shadows are dropped while the circuit is dimmer than this (a 4% lamp casts no visible shadow).
        [Range(0, 1)] public float shadowStrengthThreshold = .25f;
        readonly HashSet<Light> nightOnly = new HashSet<Light>();
        public float CurrentStrength { get; private set; }
        public int ActiveLights { get; private set; }
        public int ActiveShadowLights { get; private set; }
        struct LightState { public Light light; public float intensity, shadowStrength; public bool enabled; public LightShadows shadows; }
        struct MaterialState { public Material source, runtime; public Color emission; }
        struct Binding { public Renderer renderer; public int slot; public Material source, runtime; }
        LightState[] lightStates;
        readonly List<MaterialState> materialStates = new List<MaterialState>();
        readonly List<Binding> bindings = new List<Binding>();
        static readonly int EmissionId = Shader.PropertyToID("_EmissionColor");

        void OnEnable()
        {
            if (!Application.isPlaying) return;
            nightOnly.Clear(); foreach (var l in nightOnlyLights) if (l) nightOnly.Add(l);
            lightStates = new LightState[practicalLights.Length];
            for (int i = 0; i < practicalLights.Length; i++)
            {
                var light = practicalLights[i]; if (!light) continue;
                lightStates[i] = new LightState { light = light, intensity = light.intensity, enabled = light.enabled, shadows = light.shadows, shadowStrength = light.shadowStrength };
            }
            // Resolve once by serialized material identity, including freshly rebuilt render chunks.
            // Shared runtime clones preserve batching and do not dirty the authored material assets.
            foreach (var source in emissiveMaterials)
            {
                if (!source || !source.HasProperty(EmissionId) || materialStates.Exists(m => m.source == source)) continue;
                var runtime = new Material(source) { name = source.name + " (time of day)" };
                runtime.EnableKeyword("_EMISSION");
                materialStates.Add(new MaterialState { source = source, runtime = runtime, emission = source.GetColor(EmissionId) });
            }
            foreach (var renderer in FindObjectsByType<Renderer>(FindObjectsInactive.Exclude))
            {
                var slots = renderer.sharedMaterials; bool changed = false;
                for (int i = 0; i < slots.Length; i++)
                {
                    foreach (var material in materialStates)
                    {
                        if (slots[i] != material.source) continue;
                        bindings.Add(new Binding { renderer = renderer, slot = i, source = material.source, runtime = material.runtime });
                        slots[i] = material.runtime; changed = true; break;
                    }
                }
                if (changed) renderer.sharedMaterials = slots;
            }
            Refresh();
        }

        void LateUpdate() => Refresh();
        public void Refresh()
        {
            CurrentStrength = Mathf.Lerp(daytimeStrength, 1, clock ? clock.LampStrength : 1);
            foreach (var state in materialStates) state.runtime.SetColor(EmissionId, state.emission * CurrentStrength);
            ActiveLights = ActiveShadowLights = 0;
            if (lightStates == null) return;
            foreach (var state in lightStates)
            {
                var light = state.light; if (!light) continue;
                float distance = viewer ? Vector3.Distance(viewer.position, light.transform.position) : 0;
                float distanceWeight = 1 - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(fullLightDistance, Mathf.Max(fullLightDistance + 1, culledLightDistance), distance));
                light.intensity = state.intensity * CurrentStrength * distanceWeight;
                light.enabled = state.enabled && light.intensity > .002f && (CurrentStrength >= nightOnlyThreshold || !nightOnly.Contains(light));
                float shadowWeight = 1 - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(shadowDistance * .75f, Mathf.Max(1, shadowDistance), distance));
                light.shadowStrength = state.shadowStrength * shadowWeight;
                light.shadows = shadowWeight > .001f && CurrentStrength >= shadowStrengthThreshold ? state.shadows : LightShadows.None;
                if (light.enabled) { ActiveLights++; if (light.shadows != LightShadows.None) ActiveShadowLights++; }
            }
        }

        void OnDisable()
        {
            if (lightStates != null) foreach (var state in lightStates) if (state.light)
            { state.light.intensity = state.intensity; state.light.enabled = state.enabled; state.light.shadows = state.shadows; state.light.shadowStrength = state.shadowStrength; }
            foreach (var binding in bindings)
            {
                if (!binding.renderer) continue;
                var slots = binding.renderer.sharedMaterials;
                if (binding.slot < slots.Length && slots[binding.slot] == binding.runtime)
                { slots[binding.slot] = binding.source; binding.renderer.sharedMaterials = slots; }
            }
            foreach (var state in materialStates) if (state.runtime) Destroy(state.runtime);
            bindings.Clear(); materialStates.Clear(); lightStates = null;
        }
    }
}
