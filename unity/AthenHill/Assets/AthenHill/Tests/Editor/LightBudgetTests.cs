using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    /// Light budget pass (20 Nov 2026): ranking, hard cap, hysteresis, hold and cross-fade of LightBudgetMath.
    public sealed class LightBudgetTests
    {
        static LampBudgetState[] Lamps(int n, float firstScore = 100, float step = 1)
        {
            var s = new LampBudgetState[n];
            for (int i = 0; i < n; i++) s[i] = new LampBudgetState { wanted = true, inView = true, inWide = true, score = firstScore - i * step, real = true, fade = 1, sinceChange = 10 };
            return s;
        }

        static LightBudgetStats Run(LampBudgetState[] s, LightBudgetSettings cfg, int unmanaged, float seconds, float dt = 1f / 60)
        {
            var order = new int[s.Length]; var keys = new float[s.Length]; LightBudgetStats st = default;
            for (float t = 0; t < seconds; t += dt) st = LightBudgetMath.Step(s, s.Length, cfg, unmanaged, dt, order, keys);
            return st;
        }

        static int EnabledInView(LampBudgetState[] s) { int n = 0; foreach (var x in s) if (x.wanted && x.inView && x.fade > 0) n++; return n; }

        [Test]
        public void NeverExceedsHardCapAfterAnyStep()
        {
            var cfg = LightBudgetSettings.Default; var s = Lamps(120);
            var order = new int[s.Length]; var keys = new float[s.Length];
            for (int f = 0; f < 600; f++)
            {
                LightBudgetMath.Step(s, s.Length, cfg, 3, 1f / 60, order, keys);
                Assert.LessOrEqual(EnabledInView(s) + 3, cfg.hardCap, "frame " + f);
            }
        }

        [Test]
        public void KeepsTheHighestScoresReal()
        {
            var cfg = LightBudgetSettings.Default; var s = Lamps(60);
            Run(s, cfg, 0, 3);
            int soft = cfg.hardCap - cfg.fadeMargin;
            for (int i = 0; i < soft; i++) Assert.IsTrue(s[i].real && s[i].fade >= 1, "lamp " + i + " should be real");
            for (int i = soft; i < s.Length; i++) Assert.IsFalse(s[i].real, "lamp " + i + " should be a pool");
        }

        [Test]
        public void UnmanagedLightsShrinkTheBudget()
        {
            var cfg = LightBudgetSettings.Default; var s = Lamps(60);
            var st = Run(s, cfg, 10, 3);
            Assert.AreEqual(cfg.hardCap - 10 - cfg.fadeMargin, st.realInView);
            Assert.LessOrEqual(st.enabledInView + 10, cfg.hardCap);
        }

        [Test]
        public void HysteresisStopsSwappingNearEqualLamps()
        {
            var cfg = LightBudgetSettings.Default; var s = Lamps(40, 100, 0);   // all equal
            Run(s, cfg, 0, 3);
            var realBefore = new bool[s.Length]; for (int i = 0; i < s.Length; i++) realBefore[i] = s[i].real;
            // the scores wobble by up to 10 % (a camera turning slightly): nobody should change state
            var order = new int[s.Length]; var keys = new float[s.Length]; int changes = 0;
            for (int f = 0; f < 600; f++)
            {
                for (int i = 0; i < s.Length; i++) s[i].score = 100 * (1 + .1f * Mathf.Sin(f * .05f + i));
                var st = LightBudgetMath.Step(s, s.Length, cfg, 0, 1f / 60, order, keys);
                changes += st.promotions + st.demotions;
            }
            Assert.AreEqual(0, changes, "near-equal lamps swapped");
            for (int i = 0; i < s.Length; i++) Assert.AreEqual(realBefore[i], s[i].real);
        }

        [Test]
        public void ClearlyBetterLampIsPromotedAndCrossFades()
        {
            var cfg = LightBudgetSettings.Default; var s = Lamps(40);
            Run(s, cfg, 0, 3);
            int last = s.Length - 1; Assert.IsFalse(s[last].real);
            s[last].score = 1000;   // walked up to it
            var order = new int[s.Length]; var keys = new float[s.Length];
            LightBudgetMath.Step(s, s.Length, cfg, 0, 1f / 60, order, keys);
            Assert.IsTrue(s[last].real, "promoted");
            Assert.Less(s[last].fade, .1f, "fades in, does not pop");
            Run(s, cfg, 0, cfg.fadeSeconds + .1f);
            Assert.AreEqual(1, s[last].fade, 1e-4f);
            Assert.LessOrEqual(EnabledInView(s), cfg.hardCap);
        }

        [Test]
        public void DemotionInViewFadesOutButOffScreenIsInstant()
        {
            var cfg = LightBudgetSettings.Default; var s = Lamps(40);
            Run(s, cfg, 0, 3);
            var order = new int[s.Length]; var keys = new float[s.Length];
            // lamp 0 drops to the bottom while in view: it fades
            s[0].score = .001f;
            LightBudgetMath.Step(s, s.Length, cfg, 0, 1f / 60, order, keys);
            Assert.IsFalse(s[0].real); Assert.Greater(s[0].fade, .9f);
            // lamp 1 leaves the widened view and is beyond offscreenKeep: instant
            cfg.offscreenKeep = 0; s[1].inView = s[1].inWide = false;
            LightBudgetMath.Step(s, s.Length, cfg, 0, 1f / 60, order, keys);
            Assert.IsFalse(s[1].real); Assert.AreEqual(0, s[1].fade);
        }

        [Test]
        public void FreshPromotionIsHeld()
        {
            var cfg = LightBudgetSettings.Default; cfg.hysteresis = 1; var s = Lamps(40);
            Run(s, cfg, 0, 3);
            int last = s.Length - 1; var order = new int[s.Length]; var keys = new float[s.Length];
            s[last].score = 1000; LightBudgetMath.Step(s, s.Length, cfg, 0, 1f / 60, order, keys);
            s[last].score = .001f;  // immediately unimportant again
            Run(s, cfg, 0, cfg.minHoldSeconds * .5f);
            Assert.IsTrue(s[last].real, "held for minHoldSeconds");
            Run(s, cfg, 0, cfg.minHoldSeconds);
            Assert.IsFalse(s[last].real, "released after the hold");
        }

        [Test]
        public void OwnerOffMeansDarkAndOutOfTheCount()
        {
            var cfg = LightBudgetSettings.Default; var s = Lamps(10);
            for (int i = 0; i < s.Length; i++) s[i].wanted = false;
            var st = Run(s, cfg, 0, 1);
            Assert.AreEqual(0, st.enabledInView); Assert.AreEqual(0, st.poolsInView);
            foreach (var x in s) { Assert.IsFalse(x.real); Assert.AreEqual(0, x.fade); }
        }

        [Test]
        public void TurningRoundNeverBreaksTheCap()
        {
            // 80 lamps in a ring; the view covers 20 at a time and sweeps round quickly
            var cfg = LightBudgetSettings.Default; var s = Lamps(80, 50, 0);
            var order = new int[s.Length]; var keys = new float[s.Length];
            for (int f = 0; f < 1200; f++)
            {
                int start = (f * 2) % 80;
                for (int i = 0; i < 80; i++)
                {
                    int rel = (i - start + 80) % 80;
                    s[i].inView = rel < 30; s[i].inWide = rel < 36;
                    s[i].score = 50 + 30 * Mathf.Sin(i * 1.7f);
                }
                LightBudgetMath.Step(s, s.Length, cfg, 2, 1f / 60, order, keys);
                Assert.LessOrEqual(EnabledInView(s) + 2, cfg.hardCap, "frame " + f);
            }
        }

        [Test]
        public void CrossFadeWeightsSumToOne()
        {
            for (float f = 0; f <= 1; f += .05f) Assert.AreEqual(1, LightBudgetMath.LightWeight(f) + LightBudgetMath.PoolWeight(f), 1e-5f);
            Assert.AreEqual(0, LightBudgetMath.LightWeight(0)); Assert.AreEqual(1, LightBudgetMath.LightWeight(1));
        }

        [Test]
        public void ScoreFallsWithDistanceAndRisesWithBrightness()
        {
            float near = LightBudgetMath.Score(5, 8, .8f, 1, 5), far = LightBudgetMath.Score(5, 8, .8f, 1, 50);
            Assert.Greater(near, far);
            Assert.Greater(LightBudgetMath.Score(10, 8, .8f, 1, 20), LightBudgetMath.Score(5, 8, .8f, 1, 20));
            Assert.Greater(LightBudgetMath.Score(5, 8, .8f, 2, 20), LightBudgetMath.Score(5, 8, .8f, 1, 20));
        }

        [Test]
        public void NearWallLampOutranksFarFloodWithNearPreference()
        {
            // a 5.46 / 7.5 m wall lamp 5 m away against a 60 / 16 m tree uplight 30 m away (20 Nov walk)
            float wall = LightBudgetMath.Score(5.46f, 7.5f, .8f, 1, 5, 15), flood = LightBudgetMath.Score(60, 16, .85f, 1.3f, 30, 15);
            Assert.Greater(wall, flood);
            Assert.Less(LightBudgetMath.Score(5.46f, 7.5f, .8f, 1, 5), LightBudgetMath.Score(60, 16, .85f, 1.3f, 30), "without the preference the flood wins");
        }

        [Test]
        public void PoolCapKeepsBrightestAndNeverDropsAFadingPool()
        {
            var key = new float[] { 5, 1, 9, float.PositiveInfinity, 3, 7 };
            var cand = new bool[] { true, true, true, true, false, true };
            var show = new bool[6]; var order = new int[6]; var scratch = new float[6];
            int shown = LightBudgetMath.SelectPools(key, cand, 6, 2, show, order, scratch);
            Assert.IsTrue(show[3], "fading pool kept");
            Assert.IsTrue(show[2], "brightest kept");
            Assert.IsFalse(show[0] || show[1] || show[4] || show[5]);
            Assert.AreEqual(2, shown);
            // a far bright facade lamp outranks a near small dim one (no near preference for pools)
            Assert.Greater(LightBudgetMath.PoolKey(5.46f, 6.4f, .8f, 60), LightBudgetMath.PoolKey(.7f, 2f, .5f, 20));
        }
    }
}
