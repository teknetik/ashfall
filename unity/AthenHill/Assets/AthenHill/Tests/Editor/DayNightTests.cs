using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    public class DayNightTests
    {
        [TestCase(24, 0)] [TestCase(-1, 23)] [TestCase(49, 1)]
        public void ClockWrapsWithoutChangingTheDayLength(float input, float expected)
            => Assert.That(ClockMath.Wrap(input), Is.EqualTo(expected).Within(.00001));

        [Test] public void FullConfiguredCycleReturnsToStartingTime()
        {
            double hour = 12;
            for (int i = 0; i < 2400 * 60; i++) hour = ClockMath.Advance(hour, 1f / 60, 40, 1, false, false);
            Assert.That(ClockMath.HourDistance((float)hour, 12), Is.LessThan(.0001f));
        }
        [Test] public void PausedWorldAndPausedClockDoNotAdvance()
        {
            Assert.That(ClockMath.Advance(17.5, 5, 40, 60, true, false), Is.EqualTo(17.5));
            Assert.That(ClockMath.Advance(17.5, 0, 40, 60, false, false), Is.EqualTo(17.5));
        }
        [Test] public void ReducedMotionCapsTimelapseWithoutStoppingAnOrdinaryCycle()
        {
            double ordinary = ClockMath.Advance(12, 10, 40, 1, false, false);
            Assert.That(ClockMath.Advance(12, 10, 40, 60, false, true), Is.EqualTo(ordinary).Within(.000001));
            Assert.That(ordinary, Is.GreaterThan(12));
        }
        [Test] public void InvalidClockInputsCannotPoisonTheLightingState()
        {
            Assert.That(ClockMath.Advance(12, float.NaN, 40, 1, false, false), Is.EqualTo(12));
            Assert.That(ClockMath.Advance(12, 10, 0, 1, false, false), Is.EqualTo(12));
            Assert.That(ClockMath.Advance(12, 10, 40, float.PositiveInfinity, false, false), Is.EqualTo(12));
        }
        [Test] public void MidnightIsContinuousAndSamplesTheRequestedHour()
        {
            var profile = ScriptableObject.CreateInstance<DayNightLightingProfile>();
            try
            {
                profile.frames = new[] { Frame(3, .1f), Frame(12, 2), Frame(21, .1f) };
                var before = profile.Evaluate(23.999f); var after = profile.Evaluate(.001f);
                Assert.That(before.keyIntensity, Is.EqualTo(after.keyIntensity).Within(.00001));
                Assert.That(before.hour, Is.EqualTo(23.999f).Within(.00001));
                Assert.That(after.hour, Is.EqualTo(.001f).Within(.00001));
                Assert.That(profile.Evaluate(-1).keyIntensity, Is.EqualTo(profile.Evaluate(23).keyIntensity));
            }
            finally { Object.DestroyImmediate(profile); }
        }
        [Test] public void AuthoredKeyIsPreservedExactlyAndInterpolationDoesNotOvershoot()
        {
            var profile = ScriptableObject.CreateInstance<DayNightLightingProfile>();
            try
            {
                var authored = Frame(12, 1.73f); authored.keyEuler = new Vector3(42, 220.6f, 0); authored.ambientSky = new Color(.34f, .42f, .52f); authored.postExposure = -.38f;
                profile.frames = new[] { Frame(0, .07f), authored, Frame(19, .04f) };
                var sample = profile.Evaluate(12);
                Assert.That(sample.keyIntensity, Is.EqualTo(authored.keyIntensity));
                Assert.That(sample.ambientSky, Is.EqualTo(authored.ambientSky));
                Assert.That(sample.postExposure, Is.EqualTo(authored.postExposure));
                Assert.That(Quaternion.Angle(Quaternion.Euler(sample.keyEuler), Quaternion.Euler(authored.keyEuler)), Is.LessThan(.02f));
                for (int i = 0; i < 24 * 60; i++) Assert.That(profile.Evaluate(i / 60f).keyIntensity, Is.InRange(.0399f, 1.7301f));
            }
            finally { Object.DestroyImmediate(profile); }
        }
        [Test] public void DuplicateOrUnorderedKeysAreRejected()
        {
            var profile = ScriptableObject.CreateInstance<DayNightLightingProfile>();
            try
            {
                profile.frames = new[] { Frame(0, .1f), Frame(0, 1) }; Assert.That(profile.IsValid(out _), Is.False);
                profile.frames = new[] { Frame(12, .1f), Frame(0, 1) }; Assert.That(profile.IsValid(out _), Is.False);
                profile.frames = new[] { Frame(0, .1f), Frame(24, 1) }; Assert.That(profile.IsValid(out _), Is.False);
                profile.frames = new[] { Frame(0, .1f), Frame(12, 1) }; Assert.That(profile.IsValid(out _), Is.True);
            }
            finally { Object.DestroyImmediate(profile); }
        }
        [Test] public void NoonReflectionCannotSurviveAnInstantNightPreset()
        {
            Assert.That(CityTimeReflections.Confidence(12, 1), Is.Zero);
            Assert.That(CityTimeReflections.Confidence(0, 0), Is.EqualTo(1));
            Assert.That(CityTimeReflections.Confidence(.6f, .15f), Is.InRange(0, 1));
            Assert.That(ClockMath.HourDistance(23.9f, .1f), Is.EqualTo(.2f).Within(.001f));
        }
        [Test] public void TerrainPreservesAuthoredSunAndIgnoresItsRoll()
        {
            var authored = Quaternion.Euler(42, 220.6f, 0);
            Assert.That(TerrainTimeLighting.AuthoredShadowWeight(authored, authored, 1), Is.EqualTo(1));
            Assert.That(TerrainTimeLighting.AuthoredShadowWeight(authored, authored * Quaternion.AngleAxis(90, Vector3.forward), 1), Is.EqualTo(1));
        }
        [Test] public void TerrainCannotRetainNoonDirectionalShadowsAtDawnOrNight()
        {
            var authored = Quaternion.Euler(42, 220.6f, 0);
            Assert.That(TerrainTimeLighting.AuthoredShadowWeight(authored, Quaternion.Euler(7, 145, 0), 1), Is.Zero);
            Assert.That(TerrainTimeLighting.AuthoredShadowWeight(authored, authored, 0), Is.Zero);
            Assert.That(TerrainTimeLighting.AuthoredShadowWeight(authored, authored * Quaternion.AngleAxis(10, Vector3.up), 1), Is.InRange(.01f, .99f));
        }
        [Test] public void TerrainHazePreservesDefaultIncludingBlackChannels()
        {
            var authored = new Color(.69f, .59f, .45f);
            Assert.That(TerrainTimeLighting.HazeScale(authored, authored, true), Is.EqualTo(Vector4.one));
            Assert.That(TerrainTimeLighting.HazeScale(Color.black, Color.black, true), Is.EqualTo(Vector4.one));
            var bright = TerrainTimeLighting.HazeScale(Color.black, Color.white, true);
            Assert.That(float.IsNaN(bright.x) || float.IsInfinity(bright.x), Is.False);
        }
        [Test] public void TerrainNightHazeUsesLinearLightAndBecomesCoolerAndDarker()
        {
            var scale = TerrainTimeLighting.HazeScale(new Color(.69f, .59f, .45f), new Color(.03f, .044f, .075f), true);
            Assert.That(scale.x, Is.GreaterThan(0).And.LessThan(.01f));
            Assert.That(scale.y, Is.GreaterThan(scale.x).And.LessThan(.02f));
            Assert.That(scale.z, Is.GreaterThan(scale.y).And.LessThan(.05f));
        }
        static DayNightFrame Frame(float hour, float intensity) => new DayNightFrame { hour = hour, keyIntensity = intensity, skyExposure = 1, reflectionStrength = 1 };
    }
}
