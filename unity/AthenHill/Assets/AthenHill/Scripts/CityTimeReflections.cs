using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill
{
    [Serializable]
    public sealed class TimeReflectionBinding
    {
        public ReflectionProbe probe;
        [Range(32, 512)] public int runtimeResolution = 128;
        [Tooltip("The sky-only probe also supplies the fallback outside local boxes.")]
        public bool globalSky;
    }

    // One time-sliced capture in flight for the entire district. No DynamicGI sky readback is required.
    [DefaultExecutionOrder(40)]
    public sealed class CityTimeReflections : MonoBehaviour
    {
        public CityTimeOfDay clock;
        public Transform viewer;
        public TimeReflectionBinding[] probes = Array.Empty<TimeReflectionBinding>();
        [Min(1)] public float minimumSecondsBetweenUpdates = 8;
        [Range(.05f, 2)] public float refreshAfterHours = .3f;
        [Min(0)] public float localCapturePadding = 12;
        public bool CapturePending => inFlight >= 0;
        public int CompletedCaptures { get; private set; }
        public int FailedCaptures { get; private set; }
        public float LastCaptureLatencyMilliseconds { get; private set; }
        public string Status { get; private set; } = "Authored reflections";
        sealed class ProbeState
        {
            public TimeReflectionBinding binding;
            public ReflectionProbeMode mode;
            public ReflectionProbeRefreshMode refresh;
            public ReflectionProbeTimeSlicingMode slicing;
            public int resolution;
            public float intensity, shadowDistance, capturedHour, capturedSun, lastStarted = -100, validSince = -100;
            public bool dynamicObjects, runtime;
            public Texture customTexture;
        }
        ProbeState[] states;
        int inFlight = -1, renderId, nextIndex;
        float startedAt, requestedHour, requestedSun;
        DefaultReflectionMode originalDefaultMode;
        Texture originalDefaultTexture;
        float originalDefaultIntensity;
        bool initialized;

        void OnEnable()
        {
            if (!Application.isPlaying || !clock || !clock.profile || !clock.profile.IsValid(out _)) return;
            states = new ProbeState[probes.Length];
            originalDefaultMode = RenderSettings.defaultReflectionMode;
            originalDefaultTexture = RenderSettings.customReflectionTexture;
            originalDefaultIntensity = RenderSettings.reflectionIntensity;
            for (int i = 0; i < probes.Length; i++)
            {
                var binding = probes[i]; var p = binding?.probe; if (!p) continue;
                states[i] = new ProbeState { binding = binding, mode = p.mode, refresh = p.refreshMode, slicing = p.timeSlicingMode,
                    resolution = p.resolution, intensity = p.intensity, shadowDistance = p.shadowDistance, dynamicObjects = p.renderDynamicObjects,
                    customTexture = p.customBakedTexture, capturedHour = clock.profile.defaultHour, capturedSun = clock.profile.Evaluate(clock.profile.defaultHour).sunVisibility };
            }
            initialized = true;
        }

        void LateUpdate()
        {
            if (!initialized) return;
            if (inFlight >= 0)
            {
                var state = states[inFlight];
                if (!state.binding.probe) { inFlight = -1; Status = "Probe removed"; }
                else if (state.binding.probe.IsFinishedRendering(renderId))
                {
                    state.capturedHour = requestedHour; state.capturedSun = requestedSun; state.validSince = Time.realtimeSinceStartup;
                    LastCaptureLatencyMilliseconds = (Time.realtimeSinceStartup - startedAt) * 1000;
                    CompletedCaptures++; inFlight = -1;
                    if (state.binding.globalSky)
                    {
                        RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom;
                        RenderSettings.customReflectionTexture = state.binding.probe.realtimeTexture;
                    }
                    Status = "Reflections current";
                }
                else if (Time.realtimeSinceStartup - startedAt > 10)
                {
                    inFlight = -1; FailedCaptures++; Status = "Reflection capture timed out; awaiting retry";
                    if (FailedCaptures == 1) Debug.LogWarning(Status, this);
                }
            }
            for (int i = 0; i < states.Length; i++)
            {
                var state = states[i]; if (state == null || !state.binding.probe) continue;
                // A large preset jump must never display the previous bright noon cubemap at night.
                float hourError = ClockMath.HourDistance(clock.Hour, state.capturedHour);
                float sunError = Mathf.Abs(clock.SunVisibility - state.capturedSun);
                float confidence = Confidence(hourError, sunError);
                if (state.runtime) confidence *= Mathf.SmoothStep(0, 1, Mathf.Clamp01((Time.realtimeSinceStartup - state.validSince) / .35f));
                state.binding.probe.intensity = state.intensity * clock.ReflectionStrength * confidence;
                if (state.binding.globalSky) RenderSettings.reflectionIntensity = originalDefaultIntensity * clock.ReflectionStrength * confidence;
            }
            if (inFlight >= 0 || states.Length == 0) return;
            for (int offset = 0; offset < states.Length; offset++)
            {
                int index = (nextIndex + offset) % states.Length; var state = states[index];
                if (state == null || !state.binding.probe || !state.binding.probe.isActiveAndEnabled) continue;
                if (ClockMath.HourDistance(clock.Hour, state.capturedHour) < refreshAfterHours && Mathf.Abs(clock.SunVisibility - state.capturedSun) < .08f) continue;
                float interval = clock.Paused || clock.Speed <= 1 || clock.ReducedMotionSpeedLimited ? minimumSecondsBetweenUpdates : Mathf.Max(1, minimumSecondsBetweenUpdates / Mathf.Sqrt(clock.Speed));
                if (Time.realtimeSinceStartup - state.lastStarted < interval) continue;
                if (!state.binding.globalSky && viewer && Vector3.Distance(viewer.position, state.binding.probe.bounds.ClosestPoint(viewer.position)) > localCapturePadding) continue;
                var p = state.binding.probe;
                if (!state.runtime)
                {
                    p.mode = ReflectionProbeMode.Realtime; p.refreshMode = ReflectionProbeRefreshMode.ViaScripting;
                    p.timeSlicingMode = ReflectionProbeTimeSlicingMode.IndividualFaces;
                    p.resolution = Mathf.ClosestPowerOfTwo(Mathf.Clamp(state.binding.runtimeResolution, 32, 512));
                    p.renderDynamicObjects = false; p.shadowDistance = Mathf.Min(state.shadowDistance, 18);
                    state.runtime = true; state.validSince = float.PositiveInfinity; p.intensity = 0;
                }
                startedAt = Time.realtimeSinceStartup; state.lastStarted = startedAt;
                requestedHour = clock.Hour; requestedSun = clock.SunVisibility;
                renderId = p.RenderProbe();
                if (renderId < 0) { FailedCaptures++; Status = "Reflection capture rejected"; if (FailedCaptures == 1) Debug.LogWarning(Status, this); break; }
                inFlight = index; nextIndex = (index + 1) % states.Length;
                Status = "Updating " + p.name; break;
            }
        }

        public static float Confidence(float hourError, float sunError) => 1 - Mathf.Max(Mathf.InverseLerp(.4f, 1.2f, hourError), Mathf.InverseLerp(.10f, .3f, sunError));

        void OnDisable()
        {
            if (!initialized) return;
            initialized = false;
            foreach (var state in states)
            {
                var p = state?.binding.probe; if (!p) continue;
                p.mode = state.mode; p.refreshMode = state.refresh; p.timeSlicingMode = state.slicing; p.resolution = state.resolution;
                p.intensity = state.intensity; p.shadowDistance = state.shadowDistance; p.renderDynamicObjects = state.dynamicObjects;
                p.customBakedTexture = state.customTexture;
            }
            RenderSettings.defaultReflectionMode = originalDefaultMode; RenderSettings.customReflectionTexture = originalDefaultTexture;
            RenderSettings.reflectionIntensity = originalDefaultIntensity; inFlight = -1; states = null;
        }
    }
}
