using System;
using UnityEngine;

namespace AthenHill
{
    [Serializable]
    public struct DayNightFrame
    {
        [Range(0, 24)] public float hour;
        public Vector3 keyEuler;
        public Color keyColor;
        [Min(0)] public float keyIntensity;
        public Color fillColor;
        [Min(0)] public float fillIntensity;
        public Color ambientSky, ambientEquator, ambientGround;
        public Color skyZenith, skyMiddle, skyHorizon, cloudLight, cloudShade, ridgeColor;
        public Color fogColor;
        [Range(0, 1)] public float sunVisibility, lampStrength;
        public float postExposure;
        [Min(0)] public float skyExposure, reflectionStrength;

        public static DayNightFrame Blend(DayNightFrame a, DayNightFrame b, float t)
        {
            t = Mathf.SmoothStep(0, 1, Mathf.Clamp01(t));
            return new DayNightFrame
            {
                hour = Mathf.Lerp(a.hour, b.hour, t),
                keyEuler = Quaternion.Slerp(Quaternion.Euler(a.keyEuler), Quaternion.Euler(b.keyEuler), t).eulerAngles,
                keyColor = Color.Lerp(a.keyColor, b.keyColor, t), keyIntensity = Mathf.Lerp(a.keyIntensity, b.keyIntensity, t),
                fillColor = Color.Lerp(a.fillColor, b.fillColor, t), fillIntensity = Mathf.Lerp(a.fillIntensity, b.fillIntensity, t),
                ambientSky = Color.Lerp(a.ambientSky, b.ambientSky, t), ambientEquator = Color.Lerp(a.ambientEquator, b.ambientEquator, t),
                ambientGround = Color.Lerp(a.ambientGround, b.ambientGround, t), skyZenith = Color.Lerp(a.skyZenith, b.skyZenith, t),
                skyMiddle = Color.Lerp(a.skyMiddle, b.skyMiddle, t), skyHorizon = Color.Lerp(a.skyHorizon, b.skyHorizon, t),
                cloudLight = Color.Lerp(a.cloudLight, b.cloudLight, t), cloudShade = Color.Lerp(a.cloudShade, b.cloudShade, t),
                ridgeColor = Color.Lerp(a.ridgeColor, b.ridgeColor, t), fogColor = Color.Lerp(a.fogColor, b.fogColor, t),
                sunVisibility = Mathf.Lerp(a.sunVisibility, b.sunVisibility, t), lampStrength = Mathf.Lerp(a.lampStrength, b.lampStrength, t),
                postExposure = Mathf.Lerp(a.postExposure, b.postExposure, t), skyExposure = Mathf.Lerp(a.skyExposure, b.skyExposure, t),
                reflectionStrength = Mathf.Lerp(a.reflectionStrength, b.reflectionStrength, t)
            };
        }
    }

    [CreateAssetMenu(menuName = "Athen Hill/Day and night lighting", fileName = "WardDayNight")]
    public sealed class DayNightLightingProfile : ScriptableObject
    {
        [Tooltip("Tunable game presentation clock. This does not establish a planetary day length.")]
        [Min(1)] public float realMinutesPerCycle = 40;
        [Range(0, 24)] public float defaultHour = 12;
        public bool startPaused = true;
        public DayNightFrame[] frames;

        public bool IsValid(out string reason)
        {
            if (frames == null || frames.Length < 2) { reason = "At least two lighting frames are required."; return false; }
            for (int i = 0; i < frames.Length; i++)
            {
                if (!ClockMath.Finite(frames[i].hour) || frames[i].hour < 0 || frames[i].hour >= 24 || (i > 0 && frames[i].hour <= frames[i - 1].hour))
                { reason = "Frame hours must be finite, distinct, increasing and in [0, 24)."; return false; }
            }
            if (!ClockMath.Finite(realMinutesPerCycle) || realMinutesPerCycle < 1 || !ClockMath.Finite(defaultHour))
            { reason = "Clock configuration is invalid."; return false; }
            foreach (var frame in frames)
            {
                var values = new[] { frame.keyEuler.x, frame.keyEuler.y, frame.keyEuler.z, frame.keyIntensity, frame.fillIntensity,
                    frame.postExposure, frame.skyExposure, frame.reflectionStrength, frame.sunVisibility, frame.lampStrength };
                foreach (float value in values) if (!ClockMath.Finite(value)) { reason = "Lighting values must be finite."; return false; }
                if (frame.keyIntensity < 0 || frame.fillIntensity < 0 || frame.skyExposure < 0 || frame.reflectionStrength < 0 ||
                    frame.sunVisibility < 0 || frame.sunVisibility > 1 || frame.lampStrength < 0 || frame.lampStrength > 1)
                { reason = "Lighting intensity and blend values are outside their ranges."; return false; }
                var colors = new[] { frame.keyColor, frame.fillColor, frame.ambientSky, frame.ambientEquator, frame.ambientGround,
                    frame.skyZenith, frame.skyMiddle, frame.skyHorizon, frame.cloudLight, frame.cloudShade, frame.ridgeColor, frame.fogColor };
                foreach (var color in colors) if (!ClockMath.Finite(color.r) || !ClockMath.Finite(color.g) || !ClockMath.Finite(color.b) || color.r < 0 || color.g < 0 || color.b < 0)
                { reason = "Lighting colors must be finite and nonnegative."; return false; }
            }
            reason = ""; return true;
        }

        public DayNightFrame Evaluate(float hour)
        {
            hour = ClockMath.Wrap(hour);
            for (int i = 0; i < frames.Length; i++)
            {
                int next = (i + 1) % frames.Length;
                float a = frames[i].hour, b = frames[next].hour;
                float sample = hour;
                if (next == 0) { b += 24; if (sample < a) sample += 24; }
                if (sample >= a && sample <= b)
                {
                    var result = DayNightFrame.Blend(frames[i], frames[next], (sample - a) / (b - a));
                    result.hour = hour; return result;
                }
            }
            return frames[0];
        }
    }

    public static class ClockMath
    {
        public static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        public static float Wrap(float hour) => Finite(hour) ? Mathf.Repeat(hour, 24) : 0;
        public static float HourDistance(float a, float b) => Mathf.Abs(Mathf.DeltaAngle(Wrap(a) * 15, Wrap(b) * 15)) / 15;
        public static double Advance(double hour, float deltaSeconds, float cycleMinutes, float speed, bool paused, bool reducedMotion)
        {
            if (paused || !Finite(deltaSeconds) || deltaSeconds <= 0 || !Finite(cycleMinutes) || cycleMinutes < 1 || !Finite(speed)) return hour;
            speed = Mathf.Clamp(speed, 0, reducedMotion ? 1 : 120);
            return (hour + deltaSeconds * speed * 24.0 / (cycleMinutes * 60.0)) % 24.0;
        }
    }
}
