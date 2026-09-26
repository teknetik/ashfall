#if UNITY_EDITOR || DEBUG
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using UnityEngine.UIElements;

namespace AthenHill
{
    // Transient opt-in QA auditions. Never writes source materials or user preferences.
    internal sealed class NativeVisualReview
    {
        readonly Dictionary<Material, float> transmissionDefaults = new Dictionary<Material, float>();
        readonly Dictionary<Material, float> ambientTransmissionDefaults = new Dictionary<Material, float>();
        readonly NativeTreeShadowReview treeShadowReview = new NativeTreeShadowReview();
        UIDocument hud;
        StyleFloat hudOpacity;
        UniversalRenderPipelineAsset pipeline;
        float shadowDefault;
        int cascadeDefault;
        public bool HudHidden { get; private set; }

        public void SetHudHidden(UIDocument document, GameSession session, bool hidden)
        {
            if (hidden && session.State != CityState.Dialogue)
                throw new InvalidOperationException("Unobstructed companion captures require an actual active dialogue.");
            if (hidden == HudHidden) return;
            if (hidden)
            {
                hud = document; hudOpacity = hud.rootVisualElement.style.opacity;
                hud.rootVisualElement.style.opacity = 0;
            }
            else if (hud) hud.rootVisualElement.style.opacity = hudOpacity;
            HudHidden = hidden;
        }

        public void Tree(GameSession session, JObject request)
        {
            var transmission = (float?)request["transmission"];
            var ambientTransmission = (float?)request["ambientTransmission"];
            var distance = (float?)request["shadowDistance"];
            var cascades = (int?)request["shadowCascades"];
            // Epsilon keeps the current foliage backface-normal branch enabled.
            if (transmission.HasValue && (!float.IsFinite(transmission.Value) || transmission < .0001f || transmission > .5f))
                throw new ArgumentOutOfRangeException("transmission", "Use 0.0001–0.5; zero also disables the current backface-normal branch.");
            if (ambientTransmission.HasValue && (!float.IsFinite(ambientTransmission.Value) || ambientTransmission < 0 || ambientTransmission > .5f))
                throw new ArgumentOutOfRangeException("ambientTransmission", "Use 0–0.5 for the independent ambient-transmission audition.");
            if (distance.HasValue && (!float.IsFinite(distance.Value) || distance < 1 || distance > 160))
                throw new ArgumentOutOfRangeException("shadowDistance");
            if (cascades.HasValue && cascades != 1 && cascades != 2 && cascades != 4)
                throw new ArgumentOutOfRangeException("shadowCascades", "Use 1, 2 or 4 cascades.");
            var tree = GameObject.Find("Ward oasis tree");
            if (!tree) throw new InvalidOperationException("No installed tree to audition.");
            if (transmission.HasValue || ambientTransmission.HasValue)
            {
                var leaves = tree.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials)
                    .Where(m => m && m.HasProperty("_WardTranslucency") && m.GetFloat("_WardTranslucency") > 0).Distinct().ToArray();
                if (leaves.Length != 1) throw new InvalidOperationException("Expected one shared leaf material.");
                if (ambientTransmission.HasValue && !leaves[0].HasProperty("_WardIndirectTranslucency"))
                    throw new InvalidOperationException("Leaf material does not support the ambient-transmission candidate.");
                foreach (var material in leaves)
                {
                    if (transmission.HasValue)
                    {
                        if (!transmissionDefaults.ContainsKey(material)) transmissionDefaults.Add(material, material.GetFloat("_WardTranslucency"));
                        material.SetFloat("_WardTranslucency", transmission.Value);
                    }
                    if (ambientTransmission.HasValue)
                    {
                        if (!ambientTransmissionDefaults.ContainsKey(material)) ambientTransmissionDefaults.Add(material, material.GetFloat("_WardIndirectTranslucency"));
                        material.SetFloat("_WardIndirectTranslucency", ambientTransmission.Value);
                    }
                }
            }
            if (distance.HasValue || cascades.HasValue)
            {
                if (!pipeline)
                {
                    pipeline = session.Settings.Pipeline;
                    shadowDefault = pipeline.shadowDistance;
                    cascadeDefault = pipeline.shadowCascadeCount;
                }
                if (distance.HasValue) pipeline.shadowDistance = distance.Value;
                if (cascades.HasValue) pipeline.shadowCascadeCount = cascades.Value;
            }
        }

        public void TreeShadow(JObject request)
        {
            var enabled = (bool?)request["enabled"];
            if (!enabled.HasValue) throw new ArgumentException("Tree shadow audition requires enabled: true or false.");
            if (enabled.Value) treeShadowReview.Begin(GameObject.Find("Ward oasis tree"));
            else treeShadowReview.Restore();
        }

        public object Snapshot() => new
        {
            hudHidden = HudHidden,
            treeShadow = treeShadowReview.Snapshot(),
            purpose = "Diagnostic companion/A-B view; not a normal-UI or performance acceptance frame",
            transmission = transmissionDefaults.Select(p => new { material = p.Key.name, original = p.Value, current = p.Key.GetFloat("_WardTranslucency") }).ToArray(),
            ambientTransmission = ambientTransmissionDefaults.Select(p => new
            {
                material = p.Key.name, original = p.Value, current = p.Key.GetFloat("_WardIndirectTranslucency"),
                leafTexture = LeafTextureSnapshot(p.Key)
            }).ToArray(),
            shadowDistance = pipeline ? (float?)pipeline.shadowDistance : null,
            originalShadowDistance = pipeline ? (float?)shadowDefault : null,
            shadowCascades = pipeline ? (int?)pipeline.shadowCascadeCount : null,
            originalShadowCascades = pipeline ? (int?)cascadeDefault : null
        };

        static object LeafTextureSnapshot(Material material)
        {
            var texture = material.GetTexture("_BaseMap") as Texture2D;
            if (!texture) return null;
            return new
            {
                name = texture.name,
                dimensions = new[] { texture.width, texture.height },
                streamingMipmaps = texture.streamingMipmaps,
                loadedMipmapLevel = texture.loadedMipmapLevel,
                desiredMipmapLevel = texture.desiredMipmapLevel
            };
        }

        public void Restore()
        {
            treeShadowReview.Restore();
            if (HudHidden && hud) hud.rootVisualElement.style.opacity = hudOpacity;
            HudHidden = false;
            foreach (var pair in transmissionDefaults) if (pair.Key) pair.Key.SetFloat("_WardTranslucency", pair.Value);
            transmissionDefaults.Clear();
            foreach (var pair in ambientTransmissionDefaults) if (pair.Key) pair.Key.SetFloat("_WardIndirectTranslucency", pair.Value);
            ambientTransmissionDefaults.Clear();
            if (pipeline)
            {
                pipeline.shadowDistance = shadowDefault;
                pipeline.shadowCascadeCount = cascadeDefault;
            }
            pipeline = null;
        }
    }
}
#endif
