using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    /// Phase 1 polish tests: Reduced-Motion-safe camera FOV feel, music ducking and equal-power crossfades,
    /// footstep null-safety, stash edge cases, and world-map zoom/math safety.
    public class WorldAtmospherePolishTests
    {
        // ------------------------------------------------------------------ camera FOV feel
        [Test]
        public void FollowCameraFeelRespectsReducedMotionAndAiming()
        {
            Assert.That(FollowCameraFeel.TargetFovOffset(true, false, false, false, 3.5f, 5.5f), Is.EqualTo(3.5f).Within(1e-4f));
            Assert.That(FollowCameraFeel.TargetFovOffset(true, true, false, false, 3.5f, 5.5f), Is.EqualTo(5.5f).Within(1e-4f), "dodge overrides sprint");
            Assert.That(FollowCameraFeel.TargetFovOffset(true, true, true, false, 3.5f, 5.5f), Is.Zero, "aiming suppresses kinetic kick");
            Assert.That(FollowCameraFeel.TargetFovOffset(true, true, false, true, 3.5f, 5.5f), Is.Zero, "reduced motion suppresses kinetic kick");
            Assert.That(FollowCameraFeel.TargetFovOffset(true, false, false, false, float.NaN, 5.5f), Is.Zero);
        }

        [Test]
        public void FollowCameraFeelStepsSmoothlyAndSnapsCleanlyToZero()
        {
            float v = 0f;
            for (int i = 0; i < 30; i++) v = FollowCameraFeel.StepFovOffset(v, 5.5f, 1f / 60f, 12f, 7f, false);
            Assert.That(v, Is.GreaterThan(5f).And.LessThanOrEqualTo(5.5f));

            // Reduced motion clears immediately with no drift
            Assert.That(FollowCameraFeel.StepFovOffset(v, 5.5f, 1f / 60f, 12f, 7f, true), Is.Zero);

            // Returning to idle snaps to exact 0 so FollowCamera releases lensTouched
            for (int i = 0; i < 120; i++) v = FollowCameraFeel.StepFovOffset(v, 0f, 1f / 60f, 12f, 7f, false);
            Assert.That(v, Is.Zero);
        }

        [Test]
        public void FollowCameraFeelComposesAndClampsLensFov()
        {
            Assert.That(FollowCameraFeel.ComposeLensFov(60f, 48f, 0f, 3.5f), Is.EqualTo(63.5f).Within(1e-4f));
            Assert.That(FollowCameraFeel.ComposeLensFov(60f, 48f, 1f, 5.5f), Is.EqualTo(48f).Within(1e-4f));
            Assert.That(FollowCameraFeel.ComposeLensFov(115f, 48f, 0f, 20f), Is.EqualTo(120f).Within(1e-4f));
            Assert.That(FollowCameraFeel.ComposeLensFov(5f, 48f, 0f, 0f), Is.EqualTo(10f).Within(1e-4f));
        }

        // ------------------------------------------------------------------ audio mix
        [Test]
        public void CityAudioMixDucksForDialogueMenusAndTravel()
        {
            Assert.That(CityAudioMix.TargetMusicDuck(CityState.Play, .65f, .4f), Is.EqualTo(1f));
            Assert.That(CityAudioMix.TargetMusicDuck(CityState.Dialogue, .65f, .4f), Is.EqualTo(.65f).Within(1e-4f));
            Assert.That(CityAudioMix.TargetMusicDuck(CityState.Stash, .65f, .4f), Is.EqualTo(.65f).Within(1e-4f));
            Assert.That(CityAudioMix.TargetMusicDuck(CityState.Rest, .65f, .4f), Is.EqualTo(.65f).Within(1e-4f));
            Assert.That(CityAudioMix.TargetMusicDuck(CityState.Map, .65f, .4f), Is.EqualTo(.65f).Within(1e-4f));
            Assert.That(CityAudioMix.TargetMusicDuck(CityState.Grid, .65f, .4f), Is.EqualTo(.4f).Within(1e-4f));
        }

        [Test]
        public void CityAudioMixDucksFasterThanItRecoversAndUsesEqualPowerCrossfade()
        {
            float afterAttack = CityAudioMix.StepDuck(1f, .5f, .2f, .45f, 1.6f);
            float afterRelease = CityAudioMix.StepDuck(.5f, 1f, .2f, .45f, 1.6f);
            Assert.That(1f - afterAttack, Is.GreaterThan(afterRelease - .5f), "attack is faster than release");

            foreach (float t in new[] { 0f, .25f, .5f, .75f, 1f })
            {
                CityAudioMix.EqualPowerCrossfade(t, out float outGain, out float inGain);
                Assert.That(outGain * outGain + inGain * inGain, Is.EqualTo(1f).Within(1e-4f), $"constant power at t={t}");
            }
        }

        [Test]
        public void CityAudioMixSkipsNullPlaylistEntries()
        {
            var a = AudioClip.Create("track_a", 64, 1, 44100, false);
            var b = AudioClip.Create("track_b", 64, 1, 44100, false);
            try
            {
                var list = new[] { a, null, b, null };
                Assert.That(CityAudioMix.NextPlayableTrack(list, 0), Is.EqualTo(2));
                Assert.That(CityAudioMix.NextPlayableTrack(list, 2), Is.EqualTo(0));
                Assert.That(CityAudioMix.NextPlayableTrack(new AudioClip[] { null, null }, 0), Is.EqualTo(-1));
                Assert.That(CityAudioMix.NextPlayableTrack(null, 0), Is.EqualTo(-1));
            }
            finally
            {
                Object.DestroyImmediate(a);
                Object.DestroyImmediate(b);
            }
        }

        // ------------------------------------------------------------------ footstep null-safety
        [Test]
        public void FootstepAudioHandlesMissingMotorAndEmptyMapsSafely()
        {
            var go = new GameObject("footstep safety test");
            try
            {
                var foot = go.AddComponent<FootstepAudio>();
                foot.defaultSurface = FootSurface.Concrete;
                Assert.That(foot.Surface(), Is.EqualTo(FootSurface.Concrete));
                Assert.That(foot.SurfaceAt(null, Vector3.zero), Is.EqualTo(FootSurface.Concrete));
                Assert.That(foot.VarietySurface(Vector3.zero), Is.EqualTo(FootSurface.Concrete));
                Assert.That(foot.BermsSurface(Vector3.zero), Is.EqualTo(FootSurface.Sand));
            }
            finally
            {
                Object.DestroyImmediate(go);
            }
        }

        // ------------------------------------------------------------------ stash edge cases
        [Test]
        public void StashModelRejectsEmptyIdsAndGuardsRestoreOverflow()
        {
            var stash = new StashModel(4);
            Assert.That(stash.Quantity(""), Is.Zero);
            Assert.That(stash.Consume("", 1), Is.False);
            Assert.That(stash.Store(null, "", 1, out var reason), Is.False);
            Assert.That(reason, Is.EqualTo("bad_count"));

            stash.Restore(new[]
            {
                new ItemStack("scrap_coil", int.MaxValue - 5),
                new ItemStack("scrap_coil", 20),
            }, null);
            Assert.That(stash.Quantity("scrap_coil"), Is.EqualTo(int.MaxValue), "duplicate stacks saturate instead of overflowing negative");
        }

        // ------------------------------------------------------------------ world map math safety & wheel zoom
        [Test]
        public void MapViewHandlesDegenerateScaleAndNonFiniteZoomFactors()
        {
            var zero = new MapView(new Vector2(10, 20), 0f, new Vector2(800, 600));
            var world = zero.PanelToWorld(new Vector2(400, 300));
            Assert.That(ClockMath.Finite(world.x) && ClockMath.Finite(world.y), Is.True);
            Assert.That(zero.Pan(new Vector2(50, -30)).centre, Is.EqualTo(zero.centre));
            Assert.That(zero.ZoomAt(new Vector2(400, 300), 1.5f, .5f, 14f).scale, Is.Zero);

            var valid = new MapView(new Vector2(10, 20), 2f, new Vector2(800, 600));
            Assert.That(valid.ZoomAt(new Vector2(400, 300), float.NaN, .5f, 14f).scale, Is.EqualTo(2f));
            Assert.That(valid.ZoomAt(new Vector2(400, 300), -2f, .5f, 14f).scale, Is.EqualTo(2f));
        }

        [Test]
        public void WorldMapMathHandlesNullDeclutterInfinityAndProportionalWheelZoom()
        {
            Assert.That(WorldMapMath.Declutter(null), Is.Empty);
            Assert.That(WorldMapMath.TrackedMarker(new Vector3(float.PositiveInfinity, 0, 0), false, null).shown, Is.False);
            Assert.That(WorldMapDiscovery.Downed(new MapState { downed = true, downedX = float.NegativeInfinity, downedZ = 0 }), Is.Null);

            Assert.That(WorldMapMath.WheelZoomFactor(0f), Is.EqualTo(1f));
            Assert.That(WorldMapMath.WheelZoomFactor(float.NaN), Is.EqualTo(1f));
            Assert.That(WorldMapMath.WheelZoomFactor(-3f), Is.EqualTo(1.25f).Within(1e-4f), "standard wheel up notch");
            Assert.That(WorldMapMath.WheelZoomFactor(3f), Is.EqualTo(0.8f).Within(1e-4f), "standard wheel down notch");
            Assert.That(WorldMapMath.WheelZoomFactor(-1f), Is.GreaterThan(1f).And.LessThan(1.25f), "fine trackpad scroll");
            Assert.That(WorldMapMath.WheelZoomFactor(-999f), Is.EqualTo(1.25f * 1.25f).Within(1e-4f), "clamped spike");
        }
    }
}
