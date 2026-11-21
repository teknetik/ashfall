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
        [Header("Outer Berms Wasteland Atmosphere")]
        [Tooltip("World X boundary where Ward ends and the Outer Berms begin.")]
        public float bermsCityEdgeX = WastelandAtmosphere.DefaultCityEdgeX;
        [Tooltip("Distance in metres west of the wall over which the wasteland atmosphere blends in.")]
        [Min(0f)] public float bermsBlendMetres = WastelandAtmosphere.DefaultBlendMetres;
        public float Hour => (float)hour;
        public float BermsWeight => bermsWeight;
        public bool Paused { get; set; }
        public float Speed { get; private set; } = 1;
        public bool PreviewWhilePaused { get; set; }
        public float LampStrength => current.lampStrength;
        public float ReflectionStrength => current.reflectionStrength;
        public float SunVisibility => current.sunVisibility;
        public bool ReducedMotionSpeedLimited => session && session.reducedMotion && Speed > 1;
        public DayNightFrame CurrentFrame => current;
        public event Action TimeChanged;
        /// Weather (Scripts/Weather) scales and blends the evaluated frame; the profile stays the base and is never replaced.
        public Func<DayNightFrame, DayNightFrame> FrameModifier { get; set; }
        /// Re-applies the current hour, so a modifier change shows while the clock is paused.
        public void Refresh() { if (initialized) Apply(); }
        double hour;
        DayNightFrame current;
        Material previousSky, runtimeSky;
        VolumeProfile previousProfile, runtimeProfile;
        ColorAdjustments exposure;
        Light previousSun;
        AmbientMode previousAmbientMode;
        Color previousAmbientSky, previousAmbientEquator, previousAmbientGround, previousFog;
        float previousAmbientIntensity, previousFogStart, previousFogEnd, previousFogDensity, previousWeatherHaze;
        float baseSkyHorizonHaze, baseSkyHorizonDustGlow, bermsWeight, appliedBermsWeight;
        LightSnapshot originalKey, originalFill;
        bool initialized, bermsFogApplied;
        static readonly int TerrainTimeId = Shader.PropertyToID("_AthenTerrainTime");
        static readonly int TerrainHazeId = Shader.PropertyToID("_AthenTerrainHazeScale");
        static readonly int WeatherHazeId = Shader.PropertyToID("_AthenWeatherHaze");
        static readonly int HorizonHazeId = Shader.PropertyToID("_HorizonHaze");
        static readonly int HorizonDustGlowId = Shader.PropertyToID("_HorizonDustGlow");
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
            previousFogStart = RenderSettings.fogStartDistance; previousFogEnd = RenderSettings.fogEndDistance;
            previousFogDensity = RenderSettings.fogDensity; previousWeatherHaze = Shader.GetGlobalFloat(WeatherHazeId);
            baseSkyHorizonHaze = timeAwareSky.HasProperty(HorizonHazeId) ? timeAwareSky.GetFloat(HorizonHazeId) : .5f;
            baseSkyHorizonDustGlow = timeAwareSky.HasProperty(HorizonDustGlowId) ? timeAwareSky.GetFloat(HorizonDustGlowId) : .6f;
            bermsWeight = 0f; appliedBermsWeight = 0f; bermsFogApplied = false;
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
            bool reduced = session && session.reducedMotion;
            float dt = PreviewWhilePaused ? Time.unscaledDeltaTime : Time.deltaTime;
            double next = ClockMath.Advance(hour, dt, profile.realMinutesPerCycle, Speed, Paused, reduced);
            bool timeChanged = Math.Abs(next - hour) >= .00000001;
            if (timeChanged) hour = next;
            float targetBerms = session && session.player
                ? WastelandAtmosphere.BermsWeight(session.player.transform.position.x, bermsCityEdgeX, bermsBlendMetres)
                : 0f;
            bermsWeight = WastelandAtmosphere.SmoothWeight(bermsWeight, targetBerms, dt, reduced);
            if (timeChanged || Mathf.Abs(bermsWeight - appliedBermsWeight) > .002f) Apply();
        }

        void LateUpdate()
        {
            if (!initialized) return;
            ApplyBermsHaze();
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
            if (FrameModifier != null) current = FrameModifier(current);
            if (bermsWeight > .0001f) current = WastelandAtmosphere.ApplyToFrame(current, bermsWeight);
            appliedBermsWeight = bermsWeight;
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
            if (runtimeSky.HasProperty(HorizonHazeId))
                runtimeSky.SetFloat(HorizonHazeId, Mathf.Clamp01(baseSkyHorizonHaze + .16f * bermsWeight));
            if (runtimeSky.HasProperty(HorizonDustGlowId))
                runtimeSky.SetFloat(HorizonDustGlowId, Mathf.Clamp01(baseSkyHorizonDustGlow + .12f * bermsWeight));
            if (exposure) exposure.postExposure.value = current.postExposure;
            TimeChanged?.Invoke();
        }

        void ApplyBermsHaze()
        {
            float bh = WastelandAtmosphere.HazeMultiplier(bermsWeight);
            bool hasWeather = WeatherDirector.Active != null;
            if (bh <= 1.0001f)
            {
                if (bermsFogApplied && !hasWeather)
                {
                    RenderSettings.fogStartDistance = previousFogStart;
                    RenderSettings.fogEndDistance = previousFogEnd;
                    RenderSettings.fogDensity = previousFogDensity;
                    Shader.SetGlobalFloat(WeatherHazeId, previousWeatherHaze);
                }
                bermsFogApplied = false;
                return;
            }
            if (hasWeather)
            {
                // WeatherDirector.Update() already wrote baseFog / wh and _AthenWeatherHaze this frame.
                RenderSettings.fogStartDistance /= bh;
                RenderSettings.fogEndDistance /= bh;
                RenderSettings.fogDensity *= bh;
                Shader.SetGlobalFloat(WeatherHazeId, Shader.GetGlobalFloat(WeatherHazeId) + (bh - 1f));
            }
            else
            {
                RenderSettings.fogStartDistance = previousFogStart / bh;
                RenderSettings.fogEndDistance = previousFogEnd / bh;
                RenderSettings.fogDensity = previousFogDensity * bh;
                Shader.SetGlobalFloat(WeatherHazeId, previousWeatherHaze + (bh - 1f));
            }
            bermsFogApplied = true;
        }

        void OnDisable()
        {
            if (!initialized) return;
            initialized = false; PreviewWhilePaused = false;
            if (bermsFogApplied && WeatherDirector.Active == null)
            {
                RenderSettings.fogStartDistance = previousFogStart;
                RenderSettings.fogEndDistance = previousFogEnd;
                RenderSettings.fogDensity = previousFogDensity;
                Shader.SetGlobalFloat(WeatherHazeId, previousWeatherHaze);
            }
            bermsWeight = 0f; appliedBermsWeight = 0f; bermsFogApplied = false;
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

    /// Pure, testable Outer Berms wasteland atmosphere math. At or east of cityEdgeX (-58.3 m)
    /// BermsWeight returns 0, leaving Ward's authored city lighting 100 % untouched.
    public static class WastelandAtmosphere
    {
        public const float DefaultCityEdgeX = -58.3f;
        public const float DefaultBlendMetres = 28f;

        public static float BermsWeight(float playerX, float cityEdgeX = DefaultCityEdgeX, float blendMetres = DefaultBlendMetres)
        {
            if (!ClockMath.Finite(playerX) || !ClockMath.Finite(cityEdgeX)) return 0f;
            if (playerX >= cityEdgeX) return 0f;
            if (!ClockMath.Finite(blendMetres) || blendMetres <= .0001f) return 1f;
            float t = Mathf.Clamp01((cityEdgeX - playerX) / blendMetres);
            return Mathf.SmoothStep(0f, 1f, t);
        }

        /// Exponentially eases the blend weight; Reduced Motion eases 2.5x more gently.
        public static float SmoothWeight(float current, float target, float dt, bool reducedMotion)
        {
            current = ClockMath.Finite(current) ? Mathf.Clamp01(current) : 0f;
            target = ClockMath.Finite(target) ? Mathf.Clamp01(target) : 0f;
            if (!ClockMath.Finite(dt) || dt <= 0f) return current;
            float easeSeconds = reducedMotion ? 2.5f : .9f;
            float k = 1f - Mathf.Exp(-3f * dt / easeSeconds);
            return Mathf.Lerp(current, target, k);
        }

        /// Blowing ground dust multiplier in the Outer Berms. Reduced-Motion-safe (returns 1 when reducedMotion is on).
        public static float DustEmissionMultiplier(float bermsWeight, bool reducedMotion)
        {
            if (reducedMotion || !ClockMath.Finite(bermsWeight) || bermsWeight <= 0f) return 1f;
            return Mathf.Lerp(1f, 2.15f, Mathf.Clamp01(bermsWeight));
        }

        /// Wind clock multiplier in the Outer Berms. Reduced-Motion-safe (returns 1 when reducedMotion is on).
        public static float WindRateMultiplier(float bermsWeight, bool reducedMotion)
        {
            if (reducedMotion || !ClockMath.Finite(bermsWeight) || bermsWeight <= 0f) return 1f;
            return Mathf.Lerp(1f, 1.35f, Mathf.Clamp01(bermsWeight));
        }

        /// Horizon haze & fog tightening multiplier (1 inside Ward, up to 1.42 in full Outer Berms).
        public static float HazeMultiplier(float bermsWeight)
        {
            if (!ClockMath.Finite(bermsWeight) || bermsWeight <= 0f) return 1f;
            return Mathf.Lerp(1f, 1.42f, Mathf.Clamp01(bermsWeight));
        }

        /// Shifts ambient tone, shadow contrast, and horizon haze subtly bleaker/harsher in the Outer Berms.
        /// Exact identity when bermsWeight <= 0 so Ward's authored city lighting stays 100 % untouched.
        public static DayNightFrame ApplyToFrame(DayNightFrame frame, float bermsWeight)
        {
            if (!ClockMath.Finite(bermsWeight) || bermsWeight <= .0001f) return frame;
            float w = Mathf.Clamp01(bermsWeight);
            frame.ambientSky = BleachAndDarken(frame.ambientSky, .22f, .88f, w);
            frame.ambientEquator = BleachAndDarken(frame.ambientEquator, .18f, .90f, w);
            frame.ambientGround = BleachAndDarken(frame.ambientGround, .25f, .82f, w);
            frame.keyIntensity *= Mathf.Lerp(1f, 1.08f, w * Mathf.Clamp01(frame.sunVisibility));
            frame.fillIntensity *= Mathf.Lerp(1f, .82f, w);
            frame.fogColor = BleachAndDarken(frame.fogColor, .20f, .94f, w);
            frame.skyHorizon = BleachAndDarken(frame.skyHorizon, .16f, .95f, w);
            frame.skyMiddle = BleachAndDarken(frame.skyMiddle, .20f, .93f, w);
            frame.postExposure -= .05f * w;
            return frame;
        }

        static Color BleachAndDarken(Color c, float desaturate, float scale, float weight)
        {
            float lum = c.r * .299f + c.g * .587f + c.b * .114f;
            var target = new Color(
                Mathf.Max(0f, Mathf.Lerp(c.r, lum, desaturate) * scale),
                Mathf.Max(0f, Mathf.Lerp(c.g, lum, desaturate) * scale),
                Mathf.Max(0f, Mathf.Lerp(c.b, lum, desaturate) * scale),
                c.a);
            return Color.Lerp(c, target, weight);
        }
    }
}
