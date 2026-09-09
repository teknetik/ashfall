using System;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill
{
    [DefaultExecutionOrder(-50)]
    public sealed class CityTimeOfDay : MonoBehaviour
    {
        public DayNightLightingProfile profile;
        public GameSession session;
        public Light keyLight, skyFill;
        public Material timeAwareSky;
        public Volume gradingVolume;
        public CityTimeReflections reflections;
        public float Hour => (float)hour;
        public bool Paused { get; set; }
        public float Speed { get; private set; } = 1;
        public bool PreviewWhilePaused { get; set; }
        public float LampStrength => current.lampStrength;
        public float ReflectionStrength => current.reflectionStrength;
        public float SunVisibility => current.sunVisibility;
        public bool ReducedMotionSpeedLimited => session && session.reducedMotion && Speed > 1;
        public DayNightFrame CurrentFrame => current;
        public event Action TimeChanged;
        double hour;
        DayNightFrame current;
        Material previousSky, runtimeSky;
        VolumeProfile previousProfile, runtimeProfile;
        ColorAdjustments exposure;
        Light previousSun;
        AmbientMode previousAmbientMode;
        Color previousAmbientSky, previousAmbientEquator, previousAmbientGround, previousFog;
        float previousAmbientIntensity;
        LightSnapshot originalKey, originalFill;
        bool initialized;
        static readonly int TerrainTimeId = Shader.PropertyToID("_AthenTerrainTime");
        static readonly int TerrainHazeId = Shader.PropertyToID("_AthenTerrainHazeScale");
        Vector4 previousTerrainTime, previousTerrainHaze;
        struct LightSnapshot
        {
            public Light light; public Quaternion rotation; public float intensity; public Color color; public bool enabled;
            public static LightSnapshot Read(Light light) => light ? new LightSnapshot { light = light, rotation = light.transform.rotation, intensity = light.intensity, color = light.color, enabled = light.enabled } : default;
            public void Restore() { if (!light) return; light.transform.rotation = rotation; light.intensity = intensity; light.color = color; light.enabled = enabled; }
        }

        void OnEnable()
        {
            if (!Application.isPlaying) return;
            if (!profile || !profile.IsValid(out _) || !keyLight || !timeAwareSky)
            { Debug.LogError("City time needs a valid profile, authored key light and time-aware sky material.", this); enabled = false; return; }
            previousSky = RenderSettings.skybox; previousSun = RenderSettings.sun;
            previousTerrainTime = Shader.GetGlobalVector(TerrainTimeId); previousTerrainHaze = Shader.GetGlobalVector(TerrainHazeId);
            previousAmbientMode = RenderSettings.ambientMode; previousAmbientIntensity = RenderSettings.ambientIntensity;
            previousAmbientSky = RenderSettings.ambientSkyColor; previousAmbientEquator = RenderSettings.ambientEquatorColor;
            previousAmbientGround = RenderSettings.ambientGroundColor; previousFog = RenderSettings.fogColor;
            originalKey = LightSnapshot.Read(keyLight); originalFill = LightSnapshot.Read(skyFill);
            runtimeSky = new Material(timeAwareSky) { name = timeAwareSky.name + " (runtime clock)" };
            RenderSettings.skybox = runtimeSky; RenderSettings.sun = keyLight;
            if (gradingVolume && gradingVolume.sharedProfile)
            {
                previousProfile = gradingVolume.HasInstantiatedProfile() ? gradingVolume.profile : null;
                var source = previousProfile ? previousProfile : gradingVolume.sharedProfile;
                runtimeProfile = ScriptableObject.CreateInstance<VolumeProfile>(); runtimeProfile.name = source.name + " (runtime clock)";
                foreach (var component in source.components) runtimeProfile.components.Add(Instantiate(component));
                if (!runtimeProfile.TryGet(out exposure)) exposure = runtimeProfile.Add<ColorAdjustments>();
                exposure.postExposure.overrideState = true;
                gradingVolume.profile = runtimeProfile;
            }
            initialized = true; ResetToAuthoredDefault();
        }

        void Update()
        {
            if (!initialized) return;
            float dt = PreviewWhilePaused ? Time.unscaledDeltaTime : Time.deltaTime;
            double next = ClockMath.Advance(hour, dt, profile.realMinutesPerCycle, Speed, Paused, session && session.reducedMotion);
            if (Math.Abs(next - hour) < .00000001) return;
            hour = next; Apply();
        }

        public void SetHour(float value)
        {
            if (!ClockMath.Finite(value)) throw new ArgumentOutOfRangeException(nameof(value), "Time must be finite.");
            hour = ClockMath.Wrap(value); if (initialized) Apply();
        }
        public void SetSpeed(float value)
        {
            if (!ClockMath.Finite(value)) throw new ArgumentOutOfRangeException(nameof(value), "Clock speed must be finite.");
            Speed = Mathf.Clamp(value, .1f, 120);
        }
        public void ResetToAuthoredDefault()
        {
            if (!profile) return;
            Paused = profile.startPaused; Speed = 1; SetHour(profile.defaultHour);
        }
        void Apply()
        {
            current = profile.Evaluate(Hour);
            keyLight.transform.rotation = Quaternion.Euler(current.keyEuler); keyLight.color = current.keyColor;
            keyLight.intensity = current.keyIntensity; keyLight.enabled = current.keyIntensity > .0001f;
            if (skyFill) { skyFill.color = current.fillColor; skyFill.intensity = current.fillIntensity; }
            RenderSettings.ambientMode = AmbientMode.Trilight; RenderSettings.ambientIntensity = previousAmbientIntensity;
            RenderSettings.ambientSkyColor = current.ambientSky; RenderSettings.ambientEquatorColor = current.ambientEquator;
            RenderSettings.ambientGroundColor = current.ambientGround; RenderSettings.fogColor = current.fogColor;
            float authoredShadowWeight = TerrainTimeLighting.AuthoredShadowWeight(originalKey.rotation, keyLight.transform.rotation, current.sunVisibility);
            Shader.SetGlobalVector(TerrainTimeId, new Vector4(1, authoredShadowWeight, 0, 0));
            Shader.SetGlobalVector(TerrainHazeId, TerrainTimeLighting.HazeScale(previousFog, current.fogColor, QualitySettings.activeColorSpace == ColorSpace.Linear));
            runtimeSky.SetColor("_Zenith", current.skyZenith); runtimeSky.SetColor("_Middle", current.skyMiddle);
            runtimeSky.SetColor("_Horizon", current.skyHorizon); runtimeSky.SetColor("_CloudLight", current.cloudLight);
            runtimeSky.SetColor("_CloudShade", current.cloudShade); runtimeSky.SetColor("_RidgeColor", current.ridgeColor);
            runtimeSky.SetFloat("_Exposure", current.skyExposure); runtimeSky.SetFloat("_SunVisibility", current.sunVisibility);
            runtimeSky.SetVector("_SunDirection", -keyLight.transform.forward);
            if (exposure) exposure.postExposure.value = current.postExposure;
            TimeChanged?.Invoke();
        }

        void OnDisable()
        {
            if (!initialized) return;
            initialized = false; PreviewWhilePaused = false;
            originalKey.Restore(); originalFill.Restore();
            RenderSettings.sun = previousSun; RenderSettings.skybox = previousSky;
            Shader.SetGlobalVector(TerrainTimeId, previousTerrainTime); Shader.SetGlobalVector(TerrainHazeId, previousTerrainHaze);
            RenderSettings.ambientMode = previousAmbientMode; RenderSettings.ambientIntensity = previousAmbientIntensity;
            RenderSettings.ambientSkyColor = previousAmbientSky; RenderSettings.ambientEquatorColor = previousAmbientEquator;
            RenderSettings.ambientGroundColor = previousAmbientGround; RenderSettings.fogColor = previousFog;
            if (gradingVolume && runtimeProfile && gradingVolume.profile == runtimeProfile) gradingVolume.profile = previousProfile;
            if (runtimeProfile)
            {
                foreach (var component in runtimeProfile.components) Destroy(component);
                Destroy(runtimeProfile);
            }
            if (runtimeSky) Destroy(runtimeSky);
        }
    }

    // Shared small calculations are kept testable without a live scene or GPU.
    public static class TerrainTimeLighting
    {
        public static float AuthoredShadowWeight(Quaternion authored, Quaternion current, float sunVisibility)
        {
            // Roll has no effect on light direction, so compare the directional vectors.
            float angle = Vector3.Angle(authored * Vector3.forward, current * Vector3.forward);
            return (1 - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(3, 18, angle))) * Mathf.Clamp01(sunVisibility);
        }
        public static Vector4 HazeScale(Color authoredFog, Color currentFog, bool linearSpace)
        {
            if (linearSpace) { authoredFog = authoredFog.linear; currentFog = currentFog.linear; }
            return new Vector4(Ratio(authoredFog.r, currentFog.r), Ratio(authoredFog.g, currentFog.g), Ratio(authoredFog.b, currentFog.b), 1);
        }
        static float Ratio(float authored, float current)
        {
            if (!ClockMath.Finite(authored) || !ClockMath.Finite(current)) return 1;
            if (Mathf.Approximately(authored, current)) return 1;
            return Mathf.Clamp(current / Mathf.Max(.0001f, authored), 0, 16);
        }
    }
}
