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
        UIDocument hud;
        StyleFloat hudOpacity;
        UniversalRenderPipelineAsset pipeline;
        float shadowDefault;
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
            var distance = (float?)request["shadowDistance"];
            // Epsilon keeps the current foliage backface-normal branch enabled.
            if (transmission.HasValue && (!float.IsFinite(transmission.Value) || transmission < .0001f || transmission > .5f))
                throw new ArgumentOutOfRangeException("transmission", "Use 0.0001–0.5; zero also disables the current backface-normal branch.");
            if (distance.HasValue && (!float.IsFinite(distance.Value) || distance < 1 || distance > 160))
                throw new ArgumentOutOfRangeException("shadowDistance");
            var tree = GameObject.Find("Ward oasis tree");
            if (!tree) throw new InvalidOperationException("No installed tree to audition.");
            if (transmission.HasValue)
            {
                var leaves = tree.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials)
                    .Where(m => m && m.HasProperty("_WardTranslucency") && m.GetFloat("_WardTranslucency") > 0).Distinct().ToArray();
                if (leaves.Length != 1) throw new InvalidOperationException("Expected one shared leaf material.");
                foreach (var material in leaves)
                {
                    if (!transmissionDefaults.ContainsKey(material)) transmissionDefaults.Add(material, material.GetFloat("_WardTranslucency"));
                    material.SetFloat("_WardTranslucency", transmission.Value);
                }
            }
            if (distance.HasValue)
            {
                if (!pipeline) { pipeline = session.Settings.Pipeline; shadowDefault = pipeline.shadowDistance; }
                pipeline.shadowDistance = distance.Value;
            }
        }

        public object Snapshot() => new
        {
            hudHidden = HudHidden,
            purpose = "Diagnostic companion/A-B view; not a normal-UI or performance acceptance frame",
            transmission = transmissionDefaults.Select(p => new { material = p.Key.name, original = p.Value, current = p.Key.GetFloat("_WardTranslucency") }).ToArray(),
            shadowDistance = pipeline ? (float?)pipeline.shadowDistance : null,
            originalShadowDistance = pipeline ? (float?)shadowDefault : null
        };

        public void Restore()
        {
            if (HudHidden && hud) hud.rootVisualElement.style.opacity = hudOpacity;
            HudHidden = false;
            foreach (var pair in transmissionDefaults) if (pair.Key) pair.Key.SetFloat("_WardTranslucency", pair.Value);
            transmissionDefaults.Clear();
            if (pipeline) pipeline.shadowDistance = shadowDefault;
            pipeline = null;
        }
    }
}
#endif
