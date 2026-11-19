using System;
using UnityEngine;

namespace AthenHill
{
    /// Weather states, in the order a dust front passes through them (build-up, peak, clearing).
    public enum WeatherKind { Calm, Breezy, Gusting, FrontBuildUp, FrontPeak, FrontClearing }

    /// What weather drives. Every channel is a multiplier or blend on top of the day/night clock's own value, so the
    /// clock stays the base; Neutral leaves the authored look untouched.
    [Serializable]
    public struct WeatherMix
    {
        [Tooltip("× the authored vegetation and cloth bend (1 = the accepted look).")]
        [Min(0)] public float windStrength;
        [Tooltip("× the speed of the shared wind clock (_AthenAtmosphereTime): faster sway and cloud drift.")]
        [Min(0)] public float windRate;
        [Tooltip("How strongly gusts swell the wind above its strength (0 = steady).")]
        [Range(0, 1)] public float gust;
        [Tooltip("Divides fog and terrain-haze distances (1 = authored, 2 = everything hazes twice as close).")]
        [Min(1)] public float haze;
        [Tooltip("× the emission of the existing windborne and drifting dust systems.")]
        [Min(0)] public float dust;
        [Tooltip("Blowing-sand layer and heavy wind sound (0 = off, 1 = full front).")]
        [Range(0, 1)] public float sand;
        [Tooltip("Fraction of sun (key light) intensity lost to suspended dust.")]
        [Range(0, 1)] public float sunDim;
        [Tooltip("How far the sun, fog and sky shift towards the dust colour (0 = authored).")]
        [Range(0, 1)] public float warmth;

        public static WeatherMix Neutral => new WeatherMix { windStrength = 1, windRate = 1, gust = 0, haze = 1, dust = 1, sand = 0, sunDim = 0, warmth = 0 };

        public static WeatherMix Lerp(WeatherMix a, WeatherMix b, float t)
        {
            t = Mathf.Clamp01(t);
            return new WeatherMix
            {
                windStrength = Mathf.Lerp(a.windStrength, b.windStrength, t), windRate = Mathf.Lerp(a.windRate, b.windRate, t),
                gust = Mathf.Lerp(a.gust, b.gust, t), haze = Mathf.Lerp(a.haze, b.haze, t), dust = Mathf.Lerp(a.dust, b.dust, t),
                sand = Mathf.Lerp(a.sand, b.sand, t), sunDim = Mathf.Lerp(a.sunDim, b.sunDim, t), warmth = Mathf.Lerp(a.warmth, b.warmth, t)
            };
        }

        /// Exponential approach: about 95 % of the way in easeSeconds, never overshooting, frame-rate independent.
        /// Light and haze channels have their own (slower under Reduced Motion) time.
        public static WeatherMix Ease(WeatherMix current, WeatherMix target, float dt, float motionSeconds, float lightSeconds)
        {
            if (!ClockMath.Finite(dt) || dt <= 0) return current;
            float km = EaseFactor(dt, motionSeconds), kl = EaseFactor(dt, lightSeconds);
            return new WeatherMix
            {
                windStrength = Mathf.Lerp(current.windStrength, target.windStrength, km), windRate = Mathf.Lerp(current.windRate, target.windRate, km),
                gust = Mathf.Lerp(current.gust, target.gust, km), dust = Mathf.Lerp(current.dust, target.dust, km),
                sand = Mathf.Lerp(current.sand, target.sand, km),
                haze = Mathf.Lerp(current.haze, target.haze, kl), sunDim = Mathf.Lerp(current.sunDim, target.sunDim, kl),
                warmth = Mathf.Lerp(current.warmth, target.warmth, kl)
            };
        }

        public static float EaseFactor(float dt, float easeSeconds)
        {
            if (!ClockMath.Finite(easeSeconds) || easeSeconds <= .0001f) return 1;
            return 1 - Mathf.Exp(-3f * dt / easeSeconds);
        }

        public float LightDifference(WeatherMix o) => Mathf.Max(Mathf.Abs(haze - o.haze), Mathf.Max(Mathf.Abs(sunDim - o.sunDim), Mathf.Abs(warmth - o.warmth)));

        public float MaxDifference(WeatherMix o) => Mathf.Max(LightDifference(o), Mathf.Max(Mathf.Abs(windStrength - o.windStrength),
            Mathf.Max(Mathf.Abs(windRate - o.windRate), Mathf.Max(Mathf.Abs(gust - o.gust), Mathf.Max(Mathf.Abs(dust - o.dust), Mathf.Abs(sand - o.sand))))));
    }

    [Serializable]
    public sealed class WeatherStateSettings
    {
        public WeatherKind kind;
        [Tooltip("How long this state lasts once chosen (seconds of game time, a random value in the range).")]
        [Min(1)] public float minSeconds = 120, maxSeconds = 300;
        [Tooltip("Relative chance of being chosen next. Only Calm, Breezy, Gusting and Front Build Up are chosen; peak and clearing follow a build-up.")]
        [Min(0)] public float weight = 1;
        [Tooltip("Seconds for the look to reach about 95 % of this state's values.")]
        [Min(.1f)] public float easeSeconds = 25;
        public WeatherMix mix = WeatherMix.Neutral;
    }

    [Serializable]
    public sealed class WeatherScheduleSettings
    {
        [Tooltip("0 = a new random schedule every session; any other value repeats the same sequence (tests, captures).")]
        public int seed;
        [Tooltip("Game seconds after New Game or Continue in which the weather stays calm (the arrival and the range).")]
        [Min(0)] public float startGraceSeconds = 480;
        [Tooltip("Earliest game second after the start at which a dust front may begin.")]
        [Min(0)] public float firstFrontEarliestSeconds = 900;
        [Tooltip("Minimum game seconds from the end of one dust front to the start of the next.")]
        [Min(0)] public float minSecondsBetweenFronts = 1200;
        public WeatherStateSettings[] states = CreateDefaultStates();

        static WeatherStateSettings S(WeatherKind k, float min, float max, float weight, float ease, float strength, float rate, float gust,
            float haze, float dust, float sand, float sunDim, float warmth) => new WeatherStateSettings
            {
                kind = k, minSeconds = min, maxSeconds = max, weight = weight, easeSeconds = ease,
                mix = new WeatherMix { windStrength = strength, windRate = rate, gust = gust, haze = haze, dust = dust, sand = sand, sunDim = sunDim, warmth = warmth }
            };

        // Breezy is the accepted (pre-weather) look; the others stay restrained until they are judged in the native player.
        public static WeatherStateSettings[] CreateDefaultStates() => new[]
        {
            //                                   min  max  weight ease  wind  rate  gust  haze  dust  sand  sun   warm
            S(WeatherKind.Calm,                  150, 360, 1f,    25,   .85f, .9f,  .05f, 1f,   .75f, 0f,   0f,   0f),
            S(WeatherKind.Breezy,                150, 360, 1.4f,  25,   1f,   1f,   .2f,  1f,   1f,   0f,   0f,   0f),
            S(WeatherKind.Gusting,               90,  210, .9f,   20,   1.3f, 1.15f,.55f, 1.08f,1.4f, 0f,   0f,   .05f),
            S(WeatherKind.FrontBuildUp,          70,  100, .45f,  60,   1.45f,1.25f,.5f,  1.5f, 1.7f, .35f, .2f,  .35f),
            S(WeatherKind.FrontPeak,             100, 180, 0f,    30,   1.7f, 1.35f,.4f,  2.2f, 2f,   1f,   .4f,  .8f),
            S(WeatherKind.FrontClearing,         70,  110, 0f,    60,   1.15f,1.1f, .3f,  1.3f, 1.3f, .2f,  .1f,  .25f),
        };

        public WeatherStateSettings For(WeatherKind kind)
        {
            if (states != null) foreach (var s in states) if (s != null && s.kind == kind) return s;
            foreach (var s in CreateDefaultStates()) if (s.kind == kind) return s;
            return null;
        }
    }

    /// Seeded weather schedule. Pure C#: the director supplies scaled game time, so pause, photo mode and conversation
    /// cameras (timeScale 0) freeze it.
    public sealed class WeatherSchedule
    {
        static readonly WeatherKind[] Choosable = { WeatherKind.Calm, WeatherKind.Breezy, WeatherKind.Gusting, WeatherKind.FrontBuildUp };
        readonly WeatherScheduleSettings settings;
        System.Random rng;
        public WeatherKind Current { get; private set; } = WeatherKind.Calm;
        public float Remaining { get; private set; }
        public float Elapsed { get; private set; }
        public float SinceFront { get; private set; }
        public int Fronts { get; private set; }
        /// A forced state holds until Resume or Reset (dev bridge and captures).
        public bool Held { get; private set; }
        public int Seed { get; private set; }

        public WeatherSchedule(WeatherScheduleSettings settings, int seed)
        {
            this.settings = settings ?? new WeatherScheduleSettings();
            Reset(seed);
        }

        public static bool IsFront(WeatherKind k) => k == WeatherKind.FrontBuildUp || k == WeatherKind.FrontPeak || k == WeatherKind.FrontClearing;
        public bool InGrace => Elapsed < settings.startGraceSeconds;

        public void Reset(int seed)
        {
            Seed = seed; rng = new System.Random(seed);
            Elapsed = 0; SinceFront = 0; Fronts = 0; Held = false; ForcedRun = false;
            Enter(WeatherKind.Calm);
        }

        public bool FrontEligible(bool frontAllowed) => frontAllowed && !InGrace && Elapsed >= settings.firstFrontEarliestSeconds &&
            (Fronts == 0 || SinceFront >= settings.minSecondsBetweenFronts);

        /// Advances by dt game seconds. Returns true when the state changed.
        public bool Tick(float dt, bool frontAllowed)
        {
            if (!ClockMath.Finite(dt) || dt <= 0) return false;
            Elapsed += dt;
            if (!IsFront(Current)) SinceFront += dt;
            if (Held) return false;
            // A tutorial step began (or the grace window applies) mid-front: let it clear instead of cutting it off.
            if (!frontAllowed && !ForcedRun && (Current == WeatherKind.FrontBuildUp || Current == WeatherKind.FrontPeak)) { Enter(WeatherKind.FrontClearing); return true; }
            Remaining -= dt;
            if (Remaining > 0) return false;
            var before = Current;
            switch (Current)
            {
                case WeatherKind.FrontBuildUp: Enter(WeatherKind.FrontPeak); break;
                case WeatherKind.FrontPeak: Enter(WeatherKind.FrontClearing); break;
                case WeatherKind.FrontClearing: SinceFront = 0; ForcedRun = false; Enter(Choose(frontAllowed)); break;
                default: ForcedRun = false; Enter(Choose(frontAllowed)); break;
            }
            return Current != before;
        }

        /// Forces a state. hold keeps it until Resume/Reset; otherwise it runs its normal course (a forced build-up
        /// still goes through peak and clearing).
        public void Force(WeatherKind kind, bool hold)
        {
            Held = hold; ForcedRun = !hold; Enter(kind);
        }

        public void Resume() { Held = false; ForcedRun = false; }

        /// A forced, unheld state is running its course; front suppression does not cut it short.
        public bool ForcedRun { get; private set; }

        WeatherKind Choose(bool frontAllowed)
        {
            if (InGrace) return WeatherKind.Calm;
            bool front = FrontEligible(frontAllowed);
            float total = 0;
            foreach (var k in Choosable) if (Candidate(k, front)) total += Weight(k);
            if (total <= 0) return Current == WeatherKind.Calm ? WeatherKind.Breezy : WeatherKind.Calm;
            double pick = rng.NextDouble() * total;
            foreach (var k in Choosable)
            {
                if (!Candidate(k, front)) continue;
                pick -= Weight(k);
                if (pick <= 0) return k;
            }
            foreach (var k in Choosable) if (Candidate(k, front)) return k;
            return WeatherKind.Calm;
        }

        bool Candidate(WeatherKind k, bool front) => k != Current && Weight(k) > 0 && (k != WeatherKind.FrontBuildUp || front);
        float Weight(WeatherKind k) { var s = settings.For(k); return s != null ? Mathf.Max(0, s.weight) : 0; }

        void Enter(WeatherKind kind)
        {
            if (kind == WeatherKind.FrontBuildUp && !IsFront(Current) && !Held) Fronts++;
            Current = kind;
            var s = settings.For(kind);
            float min = s != null ? Mathf.Max(1, s.minSeconds) : 120, max = s != null ? Mathf.Max(min, s.maxSeconds) : min;
            Remaining = Mathf.Lerp(min, max, (float)rng.NextDouble());
        }
    }

    /// Visual, haze and colour response to weather, applied to the clock's evaluated frame. Multiplies and blends the
    /// clock's own values; lamp strength and the hour are left to the clock.
    [Serializable]
    public sealed class WeatherLook
    {
        [Tooltip("Multiplies the clock's fog colour at full warmth (dusty ochre).")]
        public Color fogTint = new Color(1.06f, .93f, .76f, 1);
        [Tooltip("Multiplies the clock's sun colour at full warmth.")]
        public Color sunTint = new Color(1f, .84f, .64f, 1);
        [Tooltip("How far the horizon (and less so the zenith, clouds and ridges) takes the fog colour at full warmth.")]
        [Range(0, 1)] public float skyVeil = .7f;
        [Tooltip("Extra sky fill at full sun dim (dust scatters light into the shade).")]
        [Range(0, 1)] public float fillLift = .2f;
        [Tooltip("Fraction of the sky's sun disc lost at full sun dim.")]
        [Range(0, 1)] public float sunDiscDim = .6f;
        [Tooltip("How far the ambient horizon colour takes the fog colour at full warmth.")]
        [Range(0, 1)] public float ambientVeil = .25f;
    }

    public static class WeatherLighting
    {
        static Color Mul(Color c, Color tint) => new Color(c.r * tint.r, c.g * tint.g, c.b * tint.b, c.a);

        public static DayNightFrame Apply(DayNightFrame f, WeatherMix m, WeatherLook look)
        {
            if (look == null) return f;
            float w = Mathf.Clamp01(m.warmth), d = Mathf.Clamp01(m.sunDim);
            if (w <= 0 && d <= 0) return f;
            f.keyIntensity *= 1 - d;
            f.keyColor = Mul(f.keyColor, Color.Lerp(Color.white, look.sunTint, w));
            f.fillIntensity *= 1 + look.fillLift * d;
            f.sunVisibility = Mathf.Clamp01(f.sunVisibility * (1 - look.sunDiscDim * d));
            var fog = Mul(f.fogColor, Color.Lerp(Color.white, look.fogTint, w));
            f.fogColor = fog;
            float veil = look.skyVeil * w;
            f.skyHorizon = Color.Lerp(f.skyHorizon, fog, veil);
            f.skyMiddle = Color.Lerp(f.skyMiddle, fog, veil * .7f);
            f.skyZenith = Color.Lerp(f.skyZenith, fog, veil * .4f);
            f.cloudLight = Color.Lerp(f.cloudLight, fog, veil * .5f);
            f.cloudShade = Color.Lerp(f.cloudShade, fog, veil * .5f);
            f.ridgeColor = Color.Lerp(f.ridgeColor, fog, veil);
            f.ambientEquator = Color.Lerp(f.ambientEquator, fog, look.ambientVeil * w);
            return f;
        }
    }

    public static class WeatherRules
    {
        /// No dust front while a primer step is active; with holdBeforePrimer the not-yet-started primer (Approach)
        /// counts too, so the arrival and the range stay clear. A scene without the primer has no restriction.
        public static bool FrontAllowed(bool hasTutorial, BermsStep step, bool holdBeforePrimer) =>
            !hasTutorial || step == BermsStep.Complete || (!holdBeforePrimer && step == BermsStep.Approach);

        /// 1 = clear air, falling as fog and haze close in (the haze multiplier divides visibility distance).
        public static float Visibility(WeatherMix m) => Mathf.Clamp01(1f / Mathf.Max(1f, m.haze));

        /// Slow gust swells, 0 most of the time with occasional peaks towards 1.
        public static float GustEnvelope(float t, float seed)
        {
            float raw = Mathf.PerlinNoise(t, seed) * .7f + Mathf.PerlinNoise(t * 3.1f + 17f, seed + 7f) * .3f;
            return Mathf.SmoothStep(0, 1, Mathf.InverseLerp(.42f, .82f, raw));
        }

        public static float WindAmplitude(WeatherMix m, float gustEnvelope) => Mathf.Max(0, m.windStrength) * (1 + Mathf.Clamp01(m.gust) * Mathf.Clamp01(gustEnvelope));

        public static bool TryParse(string name, out WeatherKind kind, out bool front)
        {
            front = false; kind = WeatherKind.Calm;
            switch (name)
            {
                case "calm": kind = WeatherKind.Calm; return true;
                case "breezy": kind = WeatherKind.Breezy; return true;
                case "gusting": kind = WeatherKind.Gusting; return true;
                case "buildup": kind = WeatherKind.FrontBuildUp; return true;
                case "peak": kind = WeatherKind.FrontPeak; return true;
                case "clearing": kind = WeatherKind.FrontClearing; return true;
                case "front": kind = WeatherKind.FrontBuildUp; front = true; return true;
                default: return false;
            }
        }

        public static string Name(WeatherKind kind) => kind switch
        {
            WeatherKind.Calm => "calm", WeatherKind.Breezy => "breezy", WeatherKind.Gusting => "gusting",
            WeatherKind.FrontBuildUp => "buildup", WeatherKind.FrontPeak => "peak", _ => "clearing"
        };
    }

    /// Read-only weather for gameplay (droid detection, weapon handling). Without a weather director the values are
    /// clear air and no wind, so systems that read them behave as before.
    public static class WeatherConditions
    {
        /// 0–1: 1 = clear air; at a dust front's peak about 0.45 with the default settings.
        public static float Visibility { get; private set; } = 1;
        /// Current wind in world space (XZ, metres per second, gusts included). Zero without weather.
        public static Vector3 Wind { get; private set; }
        /// Current wind as a multiple of the authored sway (gusts included); 1 without weather.
        public static float WindStrength { get; private set; } = 1;
        /// Speed multiplier of the shared wind clock (CityAtmosphere); 1 without weather.
        public static float WindRate { get; private set; } = 1;
        /// Emission multiplier for the windborne dust systems; 1 without weather.
        public static float DustEmission { get; private set; } = 1;
        public static WeatherKind State { get; private set; } = WeatherKind.Breezy;
        public static bool Active { get; private set; }

        internal static void Publish(WeatherKind state, float visibility, Vector3 wind, float strength, float rate, float dust)
        {
            Active = true; State = state; Visibility = Mathf.Clamp01(visibility); Wind = wind;
            WindStrength = Mathf.Max(0, strength); WindRate = Mathf.Max(0, rate); DustEmission = Mathf.Max(0, dust);
        }

        internal static void Clear()
        {
            Active = false; State = WeatherKind.Breezy; Visibility = 1; Wind = Vector3.zero; WindStrength = 1; WindRate = 1; DustEmission = 1;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetOnLoad() => Clear();
    }
}
