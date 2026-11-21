using UnityEngine;

namespace AthenHill
{
    /// Dynamic weather layered on the day/night clock: wind that rises and falls, gusts, and dust fronts that build,
    /// peak and clear on a seeded schedule. Everything it drives is a multiplier or blend on the clock's own values
    /// (CityTimeOfDay.FrameModifier), on the authored fog distances, and on new shader globals whose unset value (0)
    /// is the accepted look. Runs on scaled time, so pause, photo mode and conversation cameras freeze it.
    /// Weather is not saved: New Game and Continue both start calm, with a grace period before anything happens.
    [DefaultExecutionOrder(-40)]
    public sealed class WeatherDirector : MonoBehaviour
    {
        public static WeatherDirector Active { get; private set; }

        [Header("Bindings")]
        public GameSession session;
        public CityTimeOfDay clock;
        [Tooltip("The Berms primer; while one of its steps is active no dust front starts.")]
        public BermsTutorial tutorial;
        [Tooltip("The blowing-sand layer follows this (the player), upwind of it.")]
        public Transform viewer;
        [Tooltip("Viewer-centred blowing sand, only during a dust front. Ordinary saved ParticleSystem (WeatherInstall20261119).")]
        public ParticleSystem blowingSand;
        public WeatherAudio weatherAudio;

        [Header("Schedule")]
        public WeatherScheduleSettings schedule = new WeatherScheduleSettings();
        [Tooltip("Treat the not-yet-started primer (Approach) as active too, so no front reaches the arrival or the range.")]
        public bool holdFrontsBeforePrimer = true;

        [Header("Wind")]
        [Tooltip("World direction the wind blows towards (XZ). Default matches the windborne grit and the wall-foot sand banks (from the west-south-west).")]
        public Vector3 windDirection = new Vector3(.95f, 0, .31f);
        [Tooltip("Wind speed in metres per second at strength 1 (gameplay vector and blowing sand).")]
        [Min(0)] public float baseWindSpeed = 5;
        [Tooltip("Gust swell frequency (cycles per game second, roughly).")]
        [Min(.01f)] public float gustFrequency = .12f;
        [Tooltip("Share of gust strength sent to shaders as a travelling gust wave across the vegetation.")]
        [Range(0, 1)] public float shaderGustShare = .35f;

        [Header("Look")]
        public WeatherLook look = new WeatherLook();
        [Tooltip("Under Reduced Motion the fog and light changes ease this many times more slowly.")]
        [Range(1, 6)] public float reducedMotionEaseScale = 2.5f;

        [Header("Blowing sand")]
        [Tooltip("Particles per second at a front's peak (capped by the system's Max Particles).")]
        [Min(0)] public float sandRate = 28;
        [Tooltip("The emitter sits this far upwind of the viewer so sand streams past.")]
        [Min(0)] public float sandUpwind = 9;
        [Tooltip("Sand colour is the current fog colour times this (keeps it right at night).")]
        public Color sandTint = new Color(1.12f, 1.02f, .9f, .16f);

        [Header("Radio (once per front)")]
        public string radioSpeaker = "Warden Ossa";
        [TextArea] public string frontLine = "Dust front rolling in off the berms. Visibility's dropping. Keep your bearings and stay near cover.";
        [TextArea] public string clearLine = "Front's passing. Air's clearing over the berms.";
        [Min(0)] public float radioGap = 1.5f;

        static readonly int WindBoostId = Shader.PropertyToID("_AthenWindBoost");
        static readonly int WindGustId = Shader.PropertyToID("_AthenWindGust");
        static readonly int HazeId = Shader.PropertyToID("_AthenWeatherHaze");
        static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");

        WeatherSchedule sched;
        WeatherMix mix, appliedLight;
        float gustTime, gustSeed, amplitude, envelope, fogStart, fogEnd, fogDensity, lastSandSpeed = -1;
        bool started, fogCaptured, instant, sandPlaying, reduced;
        string pendingFrontTag;
        MaterialPropertyBlock block;
        ParticleSystemRenderer sandRenderer;

        public WeatherKind State => sched != null ? sched.Current : WeatherKind.Calm;
        public bool Held => sched != null && sched.Held;
        public WeatherMix Mix => mix;
        public float Amplitude => amplitude;
        public WeatherSchedule Schedule => sched;

        void OnEnable()
        {
            Active = this;
            block ??= new MaterialPropertyBlock();
            sandRenderer = blowingSand ? blowingSand.GetComponent<ParticleSystemRenderer>() : null;
            sched = new WeatherSchedule(schedule, NewSeed());
            gustSeed = (sched.Seed & 1023) * .37f;
            mix = Target(); appliedLight = WeatherMix.Neutral; amplitude = mix.windStrength;
            fogStart = RenderSettings.fogStartDistance; fogEnd = RenderSettings.fogEndDistance; fogDensity = RenderSettings.fogDensity; fogCaptured = true;
            if (blowingSand) { blowingSand.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear); sandPlaying = false; }
            if (clock) { clock.FrameModifier = ModifyFrame; clock.Refresh(); appliedLight = mix; }
            started = session && session.HasStarted;
            Publish();
        }

        void OnDisable()
        {
            if (Active == this) Active = null;
            Shader.SetGlobalFloat(WindBoostId, 0); Shader.SetGlobalFloat(WindGustId, 0); Shader.SetGlobalFloat(HazeId, 0);
            if (fogCaptured) { RenderSettings.fogStartDistance = fogStart; RenderSettings.fogEndDistance = fogEnd; RenderSettings.fogDensity = fogDensity; }
            // Native QA fix (19 Nov 2026): on quit the scene tears down in any order; refreshing a clock whose key light is already
            // destroyed threw a NullReferenceException in CityTimeOfDay.Apply. Only re-apply a live clock.
            if (clock && clock.FrameModifier == (System.Func<DayNightFrame, DayNightFrame>)ModifyFrame) { clock.FrameModifier = null; if (clock.isActiveAndEnabled && clock.keyLight) clock.Refresh(); }
            if (blowingSand) blowingSand.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            if (sandRenderer) sandRenderer.SetPropertyBlock(null);
            if (weatherAudio) weatherAudio.Silence();
            WeatherConditions.Clear();
        }

        int NewSeed() => schedule != null && schedule.seed != 0 ? schedule.seed : System.Environment.TickCount;

        WeatherMix Target() { var s = schedule?.For(State); return s != null ? s.mix : WeatherMix.Neutral; }
        float EaseSeconds() { var s = schedule?.For(State); return s != null ? s.easeSeconds : 25; }

        bool FrontAllowed()
        {
            if (!tutorial) return true;
            return WeatherRules.FrontAllowed(true, tutorial.Step, holdFrontsBeforePrimer);
        }

        void Update()
        {
            reduced = session && session.reducedMotion;
            bool nowStarted = session && session.HasStarted;
            // New Game and Continue both begin calm, with the grace period counted from that moment.
            if (nowStarted && !started) ResetToCalm(true);
            started = nowStarted;
            float dt = Time.deltaTime;
            if (started && dt > 0)
            {
                var before = State;
                if (sched.Tick(dt, FrontAllowed())) Transition(before, State);
            }
            var target = Target();
            if (instant) { mix = target; instant = false; }
            else
            {
                float ease = EaseSeconds();
                mix = WeatherMix.Ease(mix, target, dt, ease, ease * (reduced ? reducedMotionEaseScale : 1));
            }
            gustTime += dt;
            envelope = reduced ? 0 : WeatherRules.GustEnvelope(gustTime * gustFrequency, gustSeed);
            amplitude = WeatherRules.WindAmplitude(mix, envelope);
            Publish();
        }

        void LateUpdate() => DriveSand();

        void Publish()
        {
            // Reduced Motion: the wind clock is frozen, so a changing bend would itself be motion; hold the authored pose.
            Shader.SetGlobalFloat(WindBoostId, reduced ? 0 : amplitude - 1);
            Shader.SetGlobalFloat(WindGustId, reduced ? 0 : mix.gust * shaderGustShare);
            Shader.SetGlobalFloat(HazeId, Mathf.Max(0, mix.haze - 1));
            if (fogCaptured)
            {
                float h = Mathf.Max(1, mix.haze);
                RenderSettings.fogStartDistance = fogStart / h; RenderSettings.fogEndDistance = fogEnd / h; RenderSettings.fogDensity = fogDensity * h;
            }
            if (clock && mix.LightDifference(appliedLight) > .002f) { appliedLight = mix; clock.Refresh(); }
            var dir = new Vector3(windDirection.x, 0, windDirection.z);
            dir = dir.sqrMagnitude > 1e-6f ? dir.normalized : Vector3.right;
            WeatherConditions.Publish(State, WeatherRules.Visibility(mix), dir * baseWindSpeed * amplitude, amplitude, mix.windRate, mix.dust);
            if (weatherAudio) weatherAudio.Drive(amplitude, mix.sand, started);
        }

        DayNightFrame ModifyFrame(DayNightFrame frame) => WeatherLighting.Apply(frame, mix, look);

        void DriveSand()
        {
            if (!blowingSand) return;
            float level = reduced || !started ? 0 : mix.sand;
            var dir = new Vector3(windDirection.x, 0, windDirection.z);
            dir = dir.sqrMagnitude > 1e-6f ? dir.normalized : Vector3.right;
            if (viewer) blowingSand.transform.position = viewer.position - dir * sandUpwind;
            if (level <= .01f)
            {
                if (sandPlaying) { sandPlaying = false; blowingSand.Stop(true, reduced ? ParticleSystemStopBehavior.StopEmittingAndClear : ParticleSystemStopBehavior.StopEmitting); }
                return;
            }
            var em = blowingSand.emission; em.rateOverTimeMultiplier = sandRate * level;
            float speed = baseWindSpeed * amplitude;
            if (Mathf.Abs(speed - lastSandSpeed) > .1f)
            {
                lastSandSpeed = speed;
                var v = blowingSand.velocityOverLifetime;
                v.x = new ParticleSystem.MinMaxCurve(dir.x * speed * .8f, dir.x * speed * 1.25f);
                v.y = new ParticleSystem.MinMaxCurve(-.1f, .35f);
                v.z = new ParticleSystem.MinMaxCurve(dir.z * speed * .8f, dir.z * speed * 1.25f);
            }
            if (sandRenderer)
            {
                var fog = RenderSettings.fogColor;
                sandRenderer.GetPropertyBlock(block);
                block.SetColor(BaseColorId, new Color(fog.r * sandTint.r, fog.g * sandTint.g, fog.b * sandTint.b, sandTint.a * level));
                sandRenderer.SetPropertyBlock(block);
            }
            if (!sandPlaying) { sandPlaying = true; blowingSand.Play(true); }
        }

        void Transition(WeatherKind from, WeatherKind to)
        {
            if (!session || sched.Held) return;
            if (to == WeatherKind.FrontBuildUp && !WeatherSchedule.IsFront(from))
            {
                pendingFrontTag = "weather:front:" + sched.Fronts;
                if (!string.IsNullOrWhiteSpace(frontLine)) session.Radio(frontLine, radioSpeaker, radioGap, pendingFrontTag);
            }
            else if (to == WeatherKind.FrontClearing && from != WeatherKind.FrontClearing)
            {
                // A warning still queued (the player was in a menu or conversation) is stale once the front clears.
                if (pendingFrontTag != null) { var tag = pendingFrontTag; session.RadioLine?.Drop(t => t == tag); }
                if (!string.IsNullOrWhiteSpace(clearLine)) session.Radio(clearLine, radioSpeaker, radioGap, "weather:clear:" + sched.Fronts);
                pendingFrontTag = null;
            }
        }

        void EnsureSchedule()
        {
            if (sched != null) return;
            schedule ??= new WeatherScheduleSettings();
            sched = new WeatherSchedule(schedule, NewSeed());
        }

        public void ResetToCalm(bool snap)
        {
            schedule ??= new WeatherScheduleSettings();
            sched = new WeatherSchedule(schedule, NewSeed());
            gustTime = 0; pendingFrontTag = null; instant = snap;
        }

        /// Dev bridge / native QA: force a state. "front" runs a whole front on its normal timings (with its radio
        /// lines); every other name holds until Resume. instant snaps the look instead of easing (captures).
        public bool DevSet(string name, bool snap, out string error)
        {
            error = null;
            if (!WeatherRules.TryParse(name, out var kind, out bool front)) { error = "State must be calm, breezy, gusting, buildup, peak, clearing or front."; return false; }
            EnsureSchedule();
            var before = State;
            sched.Force(kind, !front);
            if (front) Transition(before, kind);
            instant = snap;
            return true;
        }

        public object DevState() => new
        {
            available = true, state = WeatherRules.Name(State), held = sched != null && sched.Held, forcedRun = sched != null && sched.ForcedRun, remaining = sched != null ? sched.Remaining : 0f,
            elapsed = sched != null ? sched.Elapsed : 0f, grace = sched != null && sched.InGrace, fronts = sched != null ? sched.Fronts : 0, sinceFront = sched != null ? sched.SinceFront : 0f, frontAllowed = FrontAllowed(),
            windStrength = WeatherConditions.WindStrength, windRate = mix.windRate, gust = mix.gust, gustEnvelope = envelope,
            visibility = WeatherConditions.Visibility, wind = new[] { WeatherConditions.Wind.x, WeatherConditions.Wind.y, WeatherConditions.Wind.z },
            haze = mix.haze, dust = mix.dust, sand = mix.sand, sunDim = mix.sunDim, warmth = mix.warmth, reducedMotion = reduced,
            sandParticles = blowingSand ? blowingSand.particleCount : 0, sandPlaying,
            fogStart = RenderSettings.fogStartDistance, fogEnd = RenderSettings.fogEndDistance,
            audio = weatherAudio ? weatherAudio.State() : null
        };

        /// Compact keys for NativeQa's snapshot.json.
        public static object QaSnapshot()
        {
            var w = Active;
            if (!w) return new { available = false, state = (string)null, windStrength = 1f, visibility = 1f };
            return new { available = true, state = WeatherRules.Name(w.State), held = w.Held, windStrength = WeatherConditions.WindStrength, visibility = WeatherConditions.Visibility, sand = w.mix.sand };
        }
    }
}
