using System;
using UnityEngine;

namespace AthenHill
{
    /// One budgeted lamp's per-frame inputs and persistent selection state (light budget pass, 20 Nov 2026).
    public struct LampBudgetState
    {
        // inputs, written by LightBudget every frame
        /// The lamp's owner (light clock, or nobody for a static lamp) wants it lit this frame.
        public bool wanted;
        /// Its range box meets the rendering camera's frustum (the test URP's culling makes).
        public bool inView;
        /// Its range box meets the widened frustum used for ranking (a superset of inView).
        public bool inWide;
        /// Apparent importance for the rendering camera (brighter, bigger and nearer is higher).
        public float score;
        /// The player stands in its light: keep it real if any slot allows.
        public bool pinned;
        // persistent state
        /// Selected as a real light (fading towards 1) rather than a pool (fading towards 0).
        public bool real;
        /// 1 = real light at full strength, 0 = only the pool; the two cross-fade.
        public float fade;
        /// Seconds since `real` last changed.
        public float sinceChange;
    }

    public struct LightBudgetSettings
    {
        /// Local lights allowed in view in total (managed + unmanaged), e.g. 30 URP slots minus combat-FX headroom.
        public int hardCap;
        /// Slots below hardCap kept free for cross-fades (a demoted lamp still burns while it fades out).
        public int fadeMargin;
        /// Score multiplier for a lamp that is already real (so two near-equal lamps do not swap back and forth).
        public float hysteresis;
        /// A freshly promoted lamp stays real at least this long while it is in view.
        public float minHoldSeconds;
        public float fadeSeconds;
        /// Real lamps outside the widened frustum kept real (best scores), so turning round does not demote everything.
        public int offscreenKeep;
        public float pinBoost;

        public static LightBudgetSettings Default => new LightBudgetSettings
        { hardCap = 28, fadeMargin = 2, hysteresis = 1.35f, minHoldSeconds = 1f, fadeSeconds = .6f, offscreenKeep = 12, pinBoost = 4f };
    }

    public struct LightBudgetStats
    {
        public int candidatesInView, enabledInView, realInView, poolsInView, promotions, demotions, hardCuts, waiting;
    }

    /// Pure selection logic of the light budget, kept free of scene access so Edit Mode tests can drive it.
    /// Contract: after Step, the number of lamps with `wanted && inView && fade > 0` plus `unmanagedInView` never exceeds
    /// settings.hardCap (unless unmanaged lights alone exceed it, in which case every managed lamp in view is off).
    public static class LightBudgetMath
    {
        public static float Effective(in LampBudgetState s, in LightBudgetSettings cfg)
        {
            if (!s.wanted) return -1;
            float e = Mathf.Max(0, s.score);
            if (s.real) e *= cfg.hysteresis;
            if (s.pinned) e *= cfg.pinBoost;
            return e;
        }

        /// Advances selection and fades by dt. `order` and `keys` are scratch buffers at least `count` long.
        public static LightBudgetStats Step(LampBudgetState[] s, int count, in LightBudgetSettings cfg, int unmanagedInView, float dt, int[] order, float[] keys)
        {
            var stats = new LightBudgetStats();
            int hardManaged = Mathf.Max(0, cfg.hardCap - unmanagedInView);
            int soft = Mathf.Max(0, hardManaged - cfg.fadeMargin);
            float fadeStep = cfg.fadeSeconds > 0 ? dt / cfg.fadeSeconds : 1;
            for (int i = 0; i < count; i++)
            {
                s[i].sinceChange += dt;
                if (!s[i].wanted)
                {
                    // The owner switched it off (day, dust front, far away): nothing to fade, the light is dark anyway.
                    if (s[i].real) { s[i].real = false; s[i].sinceChange = 0; }
                    s[i].fade = 0;
                }
                if (s[i].wanted && s[i].inView) stats.candidatesInView++;
            }

            // 1. Desired set among lamps in the widened view: recent promotions first (hold), then by effective score.
            int n = 0;
            for (int i = 0; i < count; i++) if (s[i].wanted && s[i].inWide) { order[n] = i; keys[n] = -Effective(s[i], cfg); n++; }
            Array.Sort(keys, order, 0, n);
            var desired = Desired(count);
            int slots = soft;
            for (int k = 0; k < n && slots > 0; k++)
            {
                int i = order[k];
                if (s[i].real && s[i].sinceChange < cfg.minHoldSeconds) { desired[i] = true; slots--; }
            }
            for (int k = 0; k < n && slots > 0; k++)
            {
                int i = order[k];
                if (!desired[i]) { desired[i] = true; slots--; }
            }
            // 2. Off-screen real lamps: keep the best few real so a quick turn finds them already lit.
            int m = 0;
            for (int i = 0; i < count; i++) if (s[i].wanted && !s[i].inWide && s[i].real) { order[m] = i; keys[m] = -Effective(s[i], cfg); m++; }
            Array.Sort(keys, order, 0, m);
            for (int k = 0; k < m && k < cfg.offscreenKeep; k++) desired[order[k]] = true;

            // 3. Demotions. Out of the widened view nothing it lights is on screen, so it switches at once.
            for (int i = 0; i < count; i++)
            {
                if (!s[i].real || desired[i]) continue;
                s[i].real = false; s[i].sinceChange = 0; stats.demotions++;
                if (!s[i].inWide) s[i].fade = 0;
            }
            // 4. Promotions in score order while the hard cap has room (a fading-out lamp still holds its slot).
            int enabledInView = 0;
            for (int i = 0; i < count; i++) if (s[i].wanted && s[i].inView && s[i].fade > 0) enabledInView++;
            n = 0;
            for (int i = 0; i < count; i++) if (desired[i] && !s[i].real) { order[n] = i; keys[n] = -Effective(s[i], cfg); n++; }
            Array.Sort(keys, order, 0, n);
            for (int k = 0; k < n; k++)
            {
                int i = order[k];
                if (!s[i].inView) { s[i].real = true; s[i].sinceChange = 0; s[i].fade = 1; stats.promotions++; continue; }
                bool counted = s[i].fade > 0;
                if (!counted && enabledInView >= hardManaged) { stats.waiting++; continue; }
                s[i].real = true; s[i].sinceChange = 0; stats.promotions++;
                if (!counted) enabledInView++;
            }
            // 5. Fades.
            for (int i = 0; i < count; i++)
            {
                if (!s[i].wanted) continue;
                s[i].fade = Mathf.MoveTowards(s[i].fade, s[i].real ? 1 : 0, fadeStep);
                if (s[i].real && s[i].fade <= 0) s[i].fade = Mathf.Min(1, fadeStep);
            }
            // 6. Hard cap: if anything still exceeds it (camera cut, a burst of unmanaged lights), cut the weakest at once.
            n = 0;
            for (int i = 0; i < count; i++) if (s[i].wanted && s[i].inView && s[i].fade > 0) { order[n] = i; keys[n] = Effective(s[i], cfg); n++; }
            if (n > hardManaged)
            {
                Array.Sort(keys, order, 0, n);
                for (int k = 0; k < n - hardManaged; k++) { int i = order[k]; s[i].fade = 0; if (s[i].real) { s[i].real = false; s[i].sinceChange = 0; } stats.hardCuts++; }
            }
            for (int i = 0; i < count; i++)
            {
                if (!s[i].wanted || !s[i].inView) continue;
                if (s[i].fade > 0) stats.enabledInView++;
                if (s[i].real) stats.realInView++;
                if (s[i].fade < 1) stats.poolsInView++;
            }
            return stats;
        }

        [ThreadStatic] static bool[] desiredBuffer;
        static bool[] Desired(int count)
        {
            if (desiredBuffer == null || desiredBuffer.Length < count) desiredBuffer = new bool[Mathf.Max(count, 64)];
            Array.Clear(desiredBuffer, 0, count);
            return desiredBuffer;
        }

        /// Apparent importance of a lamp seen from `eye`: brightness times pool area over distance squared, softened near,
        /// times a near preference 1 / (1 + (d / nearMetres)^2): a pool stands in well for a far lamp but not for a near one
        /// (no specular, no light on characters), so a big far floodlight should not take a slot from the wall lamp beside you.
        public static float Score(float intensity, float range, float luminance, float priority, float distance, float nearMetres = 0)
        {
            float r = Mathf.Max(.5f, range);
            float near = nearMetres > 0 ? 1f / (1 + distance * distance / (nearMetres * nearMetres)) : 1;
            return Mathf.Max(0, priority) * Mathf.Max(0, intensity) * Mathf.Max(.05f, luminance) * r * r / (distance * distance + .25f * r * r + 1) * near;
        }

        /// Pool cap: marks the `max` best candidates (highest key) in `show`. Keys of float.PositiveInfinity (a lamp in the
        /// middle of a cross-fade) always win so a swap never loses its pool half-way. Returns how many are shown.
        public static int SelectPools(float[] key, bool[] candidate, int count, int max, bool[] show, int[] order, float[] scratch)
        {
            int n = 0;
            for (int i = 0; i < count; i++) { show[i] = false; if (candidate[i]) { order[n] = i; scratch[n] = -key[i]; n++; } }
            Array.Sort(scratch, order, 0, n);
            int shown = 0;
            for (int k = 0; k < n; k++)
            {
                int i = order[k];
                if (shown < max || float.IsPositiveInfinity(key[i])) { show[i] = true; shown++; }
            }
            return shown;
        }

        /// Pool importance on screen: brightness times the pool's apparent size (no near preference, so far facades keep
        /// their pools ahead of small dim lamps).
        public static float PoolKey(float intensity, float reach, float luminance, float distance) =>
            Mathf.Max(0, intensity) * Mathf.Max(.05f, luminance) * reach * reach / (distance * distance + 1);

        /// Cross-fade weights. The real light uses smoothstep(fade); the pool the remainder, so the two sum to one.
        public static float LightWeight(float fade) => fade <= 0 ? 0 : fade >= 1 ? 1 : fade * fade * (3 - 2 * fade);
        public static float PoolWeight(float fade) => 1 - LightWeight(fade);
    }
}
