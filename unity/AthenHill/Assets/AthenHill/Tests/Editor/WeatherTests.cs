using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    public class WeatherTests
    {
        static WeatherScheduleSettings Defaults(int seed = 11) => new WeatherScheduleSettings { seed = seed };

        static List<(float t, WeatherKind k)> Run(WeatherSchedule s, float seconds, bool frontAllowed, float step = 1)
        {
            var log = new List<(float, WeatherKind)> { (0, s.Current) };
            for (float t = 0; t < seconds; t += step)
                if (s.Tick(step, frontAllowed)) log.Add((s.Elapsed, s.Current));
            return log;
        }

        [Test] public void NewGameStaysCalmThroughTheGracePeriod()
        {
            var settings = Defaults();
            for (int seed = 1; seed <= 20; seed++)
            {
                var s = new WeatherSchedule(settings, seed);
                Assert.That(s.Current, Is.EqualTo(WeatherKind.Calm));
                for (float t = 0; t < settings.startGraceSeconds - 1; t += 1)
                {
                    s.Tick(1, true);
                    Assert.That(s.Current, Is.EqualTo(WeatherKind.Calm), $"seed {seed} at {s.Elapsed}s");
                }
            }
        }

        [Test] public void NoFrontWhileFrontsAreNotAllowed()
        {
            var s = new WeatherSchedule(Defaults(), 5);
            var log = Run(s, 6 * 3600, false);
            Assert.That(log.Exists(e => WeatherSchedule.IsFront(e.k)), Is.False);
            Assert.That(log.Exists(e => e.k == WeatherKind.Gusting), Is.True, "wind still rises and falls");
            Assert.That(log.Exists(e => e.k == WeatherKind.Breezy), Is.True);
        }

        [Test] public void FrontsRespectFirstStartAndMinimumGap()
        {
            var settings = Defaults();
            int fronts = 0;
            for (int seed = 1; seed <= 10; seed++)
            {
                var s = new WeatherSchedule(settings, seed);
                float lastEnd = -1; var prev = s.Current;
                for (float t = 0; t < 8 * 3600; t += 1)
                {
                    s.Tick(1, true);
                    if (s.Current == prev) continue;
                    if (s.Current == WeatherKind.FrontBuildUp)
                    {
                        fronts++;
                        Assert.That(s.Elapsed, Is.GreaterThanOrEqualTo(settings.firstFrontEarliestSeconds));
                        if (lastEnd >= 0) Assert.That(s.Elapsed - lastEnd, Is.GreaterThanOrEqualTo(settings.minSecondsBetweenFronts - 1));
                    }
                    if (prev == WeatherKind.FrontClearing) lastEnd = s.Elapsed;
                    // Phases only follow one another; peak and clearing are never chosen directly.
                    if (s.Current == WeatherKind.FrontPeak) Assert.That(prev, Is.EqualTo(WeatherKind.FrontBuildUp));
                    if (s.Current == WeatherKind.FrontClearing) Assert.That(prev, Is.EqualTo(WeatherKind.FrontPeak));
                    prev = s.Current;
                }
            }
            Assert.That(fronts, Is.GreaterThan(0), "eight hours of play should see a front");
        }

        [Test] public void SameSeedSameSequence()
        {
            var a = Run(new WeatherSchedule(Defaults(), 42), 3 * 3600, true);
            var b = Run(new WeatherSchedule(Defaults(), 42), 3 * 3600, true);
            Assert.That(a, Is.EqualTo(b));
        }

        static WeatherScheduleSettings FrontOnly()
        {
            var settings = new WeatherScheduleSettings { startGraceSeconds = 0, firstFrontEarliestSeconds = 0, minSecondsBetweenFronts = 0 };
            foreach (var st in settings.states) st.weight = st.kind == WeatherKind.FrontBuildUp ? 1 : 0;
            return settings;
        }

        [Test] public void TutorialStartingMidFrontClearsItInsteadOfCuttingIt()
        {
            var s = new WeatherSchedule(FrontOnly(), 3);
            for (int i = 0; i < 1000 && s.Current != WeatherKind.FrontBuildUp; i++) s.Tick(1, true);
            Assert.That(s.Current, Is.EqualTo(WeatherKind.FrontBuildUp));
            Assert.That(s.Tick(.1f, false), Is.True);
            Assert.That(s.Current, Is.EqualTo(WeatherKind.FrontClearing));
            for (int i = 0; i < 400; i++) s.Tick(1, false);
            Assert.That(WeatherSchedule.IsFront(s.Current), Is.False);
        }

        [Test] public void ForcedStatesHoldAndResetReturnsCalm()
        {
            var s = new WeatherSchedule(Defaults(), 9);
            s.Force(WeatherKind.FrontPeak, true);
            for (int i = 0; i < 3600; i++) s.Tick(1, false);
            Assert.That(s.Current, Is.EqualTo(WeatherKind.FrontPeak));
            Assert.That(s.Held, Is.True);
            s.Reset(9);
            Assert.That(s.Current, Is.EqualTo(WeatherKind.Calm));
            Assert.That(s.Held, Is.False);
            Assert.That(s.Elapsed, Is.Zero);
        }

        [Test] public void ForcedFrontRunsItsCourseOnce()
        {
            var s = new WeatherSchedule(Defaults(), 9);
            s.Force(WeatherKind.FrontBuildUp, false);
            Assert.That(s.Fronts, Is.EqualTo(1));
            var seen = new List<WeatherKind> { s.Current };
            for (int i = 0; i < 600; i++) if (s.Tick(1, false)) seen.Add(s.Current);
            Assert.That(seen.GetRange(0, 4), Is.EqualTo(new[] { WeatherKind.FrontBuildUp, WeatherKind.FrontPeak, WeatherKind.FrontClearing, WeatherKind.Calm }));
            Assert.That(s.Fronts, Is.EqualTo(1));
        }

        [Test] public void EasingApproachesWithoutOvershoot()
        {
            var a = WeatherMix.Neutral;
            var b = new WeatherMix { windStrength = 2, windRate = 1.5f, gust = 1, haze = 3, dust = 2, sand = 1, sunDim = .5f, warmth = 1 };
            Assert.That(WeatherMix.Ease(a, b, 0, 10, 10).MaxDifference(a), Is.Zero);
            Assert.That(WeatherMix.Ease(a, b, float.NaN, 10, 10).MaxDifference(a), Is.Zero);
            var m = a; float last = float.MaxValue;
            for (int i = 0; i < 100; i++)
            {
                m = WeatherMix.Ease(m, b, .1f, 10, 10);
                float d = m.MaxDifference(b);
                Assert.That(d, Is.LessThanOrEqualTo(last));
                Assert.That(m.haze, Is.InRange(1f, 3f));
                last = d;
            }
            // 10 s at 10 s ease: about 95 % of the way
            Assert.That((m.haze - 1) / 2, Is.InRange(.94f, .96f));
            Assert.That(WeatherMix.Ease(a, b, 1e6f, 10, 10).MaxDifference(b), Is.LessThan(1e-4f));
            // Slower light easing (Reduced Motion) lags the motion channels.
            var r = WeatherMix.Ease(a, b, 1, 10, 25);
            Assert.That(r.haze - 1, Is.LessThan(r.windStrength - 1));
        }

        static DayNightFrame Frame(float hour, float key, Color fog) => new DayNightFrame
        {
            hour = hour, keyEuler = new Vector3(40, 30, 0), keyColor = new Color(1, .9f, .8f), keyIntensity = key, fillColor = Color.gray, fillIntensity = .4f,
            ambientSky = Color.gray, ambientEquator = Color.gray, ambientGround = Color.gray, skyZenith = new Color(.3f, .5f, .9f), skyMiddle = new Color(.5f, .6f, .8f),
            skyHorizon = new Color(.8f, .75f, .7f), cloudLight = Color.white, cloudShade = Color.gray, ridgeColor = Color.gray, fogColor = fog,
            sunVisibility = .9f, lampStrength = .3f, postExposure = .2f, skyExposure = 1, reflectionStrength = 1
        };

        [Test] public void NeutralWeatherLeavesTheClockFrameUntouched()
        {
            var f = Frame(13, 2.2f, new Color(.64f, .47f, .31f));
            var g = WeatherLighting.Apply(f, WeatherMix.Neutral, new WeatherLook());
            Assert.That(g, Is.EqualTo(f));
            var defaults = new WeatherScheduleSettings();
            Assert.That(WeatherLighting.Apply(f, defaults.For(WeatherKind.Breezy).mix, new WeatherLook()), Is.EqualTo(f), "breezy is the accepted look");
            Assert.That(WeatherLighting.Apply(f, defaults.For(WeatherKind.Calm).mix, new WeatherLook()), Is.EqualTo(f));
        }

        [Test] public void FrontScalesTheClockValuesInsteadOfReplacingThem()
        {
            var peak = new WeatherScheduleSettings().For(WeatherKind.FrontPeak).mix;
            var look = new WeatherLook();
            foreach (var (hour, key) in new[] { (13f, 2.4f), (20.5f, .15f), (2f, 0f) })
            {
                var f = Frame(hour, key, new Color(.6f, .45f, .3f) * (key > 1 ? 1 : .2f));
                var g = WeatherLighting.Apply(f, peak, look);
                Assert.That(g.keyIntensity, Is.EqualTo(key * (1 - peak.sunDim)).Within(1e-5f));
                Assert.That(g.hour, Is.EqualTo(f.hour));
                Assert.That(g.lampStrength, Is.EqualTo(f.lampStrength));
                Assert.That(g.keyEuler, Is.EqualTo(f.keyEuler));
                Assert.That(g.postExposure, Is.EqualTo(f.postExposure));
                Assert.That(g.sunVisibility, Is.LessThan(f.sunVisibility));
                foreach (var c in new[] { g.fogColor, g.skyHorizon, g.skyZenith, g.keyColor, g.ambientEquator })
                    Assert.That(c.r >= 0 && c.g >= 0 && c.b >= 0, Is.True);
                // Warmer: the fog keeps its brightness order but leans red over blue.
                Assert.That(g.fogColor.r / Mathf.Max(1e-4f, g.fogColor.b), Is.GreaterThan(f.fogColor.r / f.fogColor.b));
            }
        }

        [Test] public void FrontsWaitForThePrimer()
        {
            Assert.That(WeatherRules.FrontAllowed(false, BermsStep.Approach, true), Is.True, "no primer in the scene");
            Assert.That(WeatherRules.FrontAllowed(true, BermsStep.Approach, true), Is.False);
            Assert.That(WeatherRules.FrontAllowed(true, BermsStep.Approach, false), Is.True);
            foreach (var step in new[] { BermsStep.TakePistol, BermsStep.Draw, BermsStep.Targets, BermsStep.FirstContact, BermsStep.Depot })
            {
                Assert.That(WeatherRules.FrontAllowed(true, step, true), Is.False, step.ToString());
                Assert.That(WeatherRules.FrontAllowed(true, step, false), Is.False, step.ToString());
            }
            Assert.That(WeatherRules.FrontAllowed(true, BermsStep.Complete, true), Is.True);
        }

        [Test] public void VisibilityWindAndNames()
        {
            Assert.That(WeatherRules.Visibility(WeatherMix.Neutral), Is.EqualTo(1));
            var peak = new WeatherScheduleSettings().For(WeatherKind.FrontPeak).mix;
            Assert.That(WeatherRules.Visibility(peak), Is.InRange(.3f, .6f));
            Assert.That(WeatherRules.WindAmplitude(WeatherMix.Neutral, 1), Is.EqualTo(1));
            Assert.That(WeatherRules.WindAmplitude(peak, 0), Is.EqualTo(peak.windStrength));
            Assert.That(WeatherRules.WindAmplitude(peak, 1), Is.EqualTo(peak.windStrength * (1 + peak.gust)).Within(1e-5f));
            for (float t = 0; t < 200; t += .37f) Assert.That(WeatherRules.GustEnvelope(t, 3), Is.InRange(0f, 1f));
            foreach (var k in new[] { WeatherKind.Calm, WeatherKind.Breezy, WeatherKind.Gusting, WeatherKind.FrontBuildUp, WeatherKind.FrontPeak, WeatherKind.FrontClearing })
            {
                Assert.That(WeatherRules.TryParse(WeatherRules.Name(k), out var parsed, out bool front), Is.True);
                Assert.That(parsed, Is.EqualTo(k)); Assert.That(front, Is.False);
            }
            Assert.That(WeatherRules.TryParse("front", out var f, out bool run) && f == WeatherKind.FrontBuildUp && run, Is.True);
            Assert.That(WeatherRules.TryParse("storm", out _, out _), Is.False);
            Assert.That(WeatherRules.TryParse(null, out _, out _), Is.False);
        }

        [Test] public void WithoutWeatherGameplaySeesClearStillAir()
        {
            Assert.That(WeatherConditions.Active, Is.False);
            Assert.That(WeatherConditions.Visibility, Is.EqualTo(1));
            Assert.That(WeatherConditions.Wind, Is.EqualTo(Vector3.zero));
            Assert.That(WeatherConditions.WindRate, Is.EqualTo(1));
            Assert.That(WeatherConditions.DustEmission, Is.EqualTo(1));
        }
    }
}
