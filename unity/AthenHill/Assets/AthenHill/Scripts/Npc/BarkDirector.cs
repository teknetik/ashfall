using System;
using System.Linq;
using UnityEngine;
using UnityEngine.Audio;
using UnityEngine.UIElements;
namespace AthenHill
{
    /// Ambient barks (NPC life pass, 19 Nov 2026): short lines outside dialogue, one speaker at a time, only during play.
    ///  Greeting     the player walks up to a colonist (edge-triggered, per-speaker cooldown)
    ///  Acknowledge  replaces the greeting once per save after a milestone (primer complete, home leased: the line's condition)
    ///  OrderDone    replaces the greeting while a completed field order is news (once per speaker and order)
    ///  Idle         now and then while the player lingers close and in sight (lines may be tied to the hour)
    ///  Weapon       the player came back through the gate with a weapon out, or reached for one inside the walls
    ///  Passing      ambient walkers, when the player comes close
    /// Every line is captioned (BarkCaptionView) unless captions are off; lines without a voice take are then skipped.
    /// Nothing is saved except once-only lines (story flags), so the save format is unchanged.
    [DisallowMultipleComponent]
    [RequireComponent(typeof(GameSession))]
    public class BarkDirector : MonoBehaviour
    {
        /// Same PlayerPrefs prefix as GameSettings, so a Settings toggle can own this value later.
        public const string CaptionsKey = "AthenHill.Settings.v1.BarkCaptions";
        [Header("Cooldowns (seconds)")]
        [Tooltip("Silence after any bark ends before anyone else barks.")]
        [Min(0)] public float globalGap = 7;
        [Min(0)] public float greetingCooldown = 150, passingCooldown = 90, weaponCooldown = 25;
        [Tooltip("Random interval between one colonist's idle remarks while the player lingers.")]
        public Vector2 idleInterval = new Vector2(70, 150);
        [Tooltip("No barks for this long after a window, dialogue or the pause menu closes.")]
        [Min(0)] public float afterWindowGrace = 3;
        [Tooltip("A colonist does not greet again for this long after a conversation with them.")]
        [Min(0)] public float afterTalkHold = 60;
        [Tooltip("A completed field order stays news for this long.")]
        [Min(0)] public float orderNewsSeconds = 900;
        [Tooltip("Seconds a weapon event waits for someone in range to react.")]
        [Min(0)] public float weaponEventSeconds = 1.5f;
        [Header("Captions")]
        [Min(.5f)] public float captionMinSeconds = 2.2f;
        [Min(.5f)] public float captionMaxSeconds = 8;
        [Header("Scan")]
        [Tooltip("Seconds between proximity scans.")]
        [Min(.02f)] public float scanInterval = .2f;
        [Tooltip("Speakers. Every NpcBarker in the scene when empty.")]
        public NpcBarker[] speakers = new NpcBarker[0];

        static int captions = -1;
        /// Bark subtitles on/off (default on), saved locally. Dialogue text is unaffected.
        public static bool CaptionsEnabled
        {
            get { if (captions < 0) captions = PlayerPrefs.GetInt(CaptionsKey, 1) != 0 ? 1 : 0; return captions == 1; }
            set { captions = value ? 1 : 0; PlayerPrefs.SetInt(CaptionsKey, captions); PlayerPrefs.Save(); }
        }
        // ---- QA state (dev bridge / NativeQa snapshot)
        public string LastSpeaker { get; private set; }
        public string LastSpeakerId { get; private set; }
        public string LastLineId { get; private set; }
        public string LastText { get; private set; }
        public string LastTrigger { get; private set; }
        public bool LastVoiced { get; private set; }
        public float LastTime { get; private set; } = -1;
        public int Count { get; private set; }
        public NpcBarker Active => active;

        GameSession session; PlayerCombat combat; FieldOrders orders; CityTimeOfDay clock; AudioMixerGroup group;
        BarkCaptionView caption; readonly BarkMemory memory = new BarkMemory(); System.Random rng;
        NpcBarker active; BarkLine activeLine; float captionLeft; bool activeVoiced, captionShown;
        bool wasArmed, bound; CityState lastState = CityState.Boot; float nextScan, weaponUntil = -1;
        string orderNews; float orderNewsAt = -1;
        static readonly RaycastHit[] hits = new RaycastHit[8];

        void Start()
        {
            session = GetComponent<GameSession>();
            combat = session.player ? session.player.GetComponent<PlayerCombat>() : null;
            orders = GetComponent<FieldOrders>();
            clock = FindAnyObjectByType<CityTimeOfDay>();
            var audio = FindAnyObjectByType<CityAudio>();
            group = audio && audio.steps ? audio.steps.outputAudioMixerGroup : null;
            if (speakers == null || speakers.Length == 0) speakers = FindObjectsByType<NpcBarker>(FindObjectsSortMode.None);
            speakers = speakers.Where(s => s).ToArray();
            rng = new System.Random(Environment.TickCount);
            if (orders) orders.Completed += OnOrderCompleted;
            session.Talked += OnTalked;
            if (session.Settings) session.Settings.Changed += OnSettings;
            bound = true;
        }
        void OnDestroy()
        {
            if (!bound) return;
            if (orders) orders.Completed -= OnOrderCompleted;
            if (session) { session.Talked -= OnTalked; if (session.Settings) session.Settings.Changed -= OnSettings; }
        }
        void OnSettings() { if (active) active.SetLevel(session.Settings.Sound.effects); }
        void OnOrderCompleted(FieldOrder order) { orderNews = order != null && !string.IsNullOrEmpty(order.id) ? order.id : "order" + Time.frameCount; orderNewsAt = Time.time; }
        void OnTalked(NpcAgent npc)
        {
            var s = Array.Find(speakers, x => x && x.agent == npc);
            if (!s) return;
            if (active == s) Cancel();
            memory.Hold(s.SpeakerId, BarkTrigger.Greeting, Time.time + afterTalkHold);
            s.approach.Occupy();
        }

        void Update()
        {
            if (!session) return;
            float now = Time.time; var state = session.State;
            if (state != lastState) { if (state == CityState.Play) memory.HoldAll(now + afterWindowGrace); lastState = state; }
            if (active) Tick(state);
            if (state != CityState.Play || !session.HasStarted) return;
            if (caption == null) BindCaption();
            WatchWeapon(now);
            if (now < nextScan) return;
            nextScan = now + scanInterval;
            Scan(now);
        }

        /// Captions and voices only run during play: a dialogue or window cancels the bark (the colonist's dialogue voice
        /// takes over); pause and Settings freeze it (the audio listener pauses with the game).
        void Tick(CityState state)
        {
            if (!active.isActiveAndEnabled) { Cancel(); return; }
            if (state != CityState.Play)
            {
                if (state != CityState.Paused && state != CityState.Settings) Cancel();
                else if (captionShown) { caption?.Hide(); captionShown = false; }
                return;
            }
            captionLeft -= Time.deltaTime;
            bool speaking = active.Speaking;
            if (captionLeft <= 0 && !speaking) { Finish(); return; }
            if (!captionShown && captionLeft > 0 && CaptionsEnabled && caption != null) { caption.Show(active.DisplayName, activeLine.text); captionShown = true; }
            if (captionShown && (captionLeft <= 0 || !CaptionsEnabled)) { caption.Hide(); captionShown = false; }
            if (active.agent) active.agent.barking = speaking || !activeVoiced && captionLeft > 0;
        }
        void Finish()
        {
            if (active && active.agent) active.agent.barking = false;
            caption?.Hide(); captionShown = false; active = null; activeLine = null;
        }
        void Cancel() { if (active) active.Stop(); Finish(); }

        void BindCaption()
        {
            if (Time.frameCount % 15 != 0) return;
            var hud = FindAnyObjectByType<CityHud>();
            var doc = hud ? hud.GetComponent<UIDocument>() : null;
            if (doc && doc.rootVisualElement?.panel != null) caption = BarkCaptionView.Bind(doc.rootVisualElement);
        }

        /// Weapons are holstered automatically inside the walls (PlayerCombat), so the city reacts to the moment it
        /// happens: coming back through the gate with one out, or pressing a weapon key inside the walls.
        void WatchWeapon(float now)
        {
            if (!combat) return;
            bool armed = combat.Armed, inside = !combat.InBerms;
            bool reached = false;
            if (inside && combat.hasPistol && session.Character != null)
                for (int i = 1; i <= 2; i++) { var slot = HotbarModel.WeaponSlot(i); if (session.input.Pressed("Slot" + HotbarModel.Key(i)) && session.Character.Equipped(slot) != null) reached = true; }
            if (inside && (wasArmed && !armed || armed || reached)) weaponUntil = now + weaponEventSeconds;
            wasArmed = armed;
        }

        void Scan(float now)
        {
            var p = session.player ? session.player.transform.position : transform.position;
            if (weaponUntil >= now && !active)
            {
                NpcBarker nearest = null; float best = float.MaxValue;
                foreach (var s in speakers)
                {
                    if (!Available(s) || !s.barks.Has(BarkTrigger.Weapon)) continue;
                    float d = Vector3.Distance(s.transform.position, p);
                    if (d <= s.weaponRadius && d < best && memory.Ready(s.SpeakerId, BarkTrigger.Weapon, now) && InSight(s, p)) { best = d; nearest = s; }
                }
                if (nearest && TrySpeak(nearest, BarkTrigger.Weapon, now, false)) weaponUntil = -1;
            }
            foreach (var s in speakers)
            {
                if (!Available(s)) continue;
                float d = Vector3.Distance(s.transform.position, p);
                bool entered = s.approach.Enter(d, s.Walker ? s.passRadius : s.greetRadius, s.rearmMargin);
                // A walker standing at a work stop (residents pass, 20 Nov 2026) may also make idle remarks.
                if (s.Walker && !s.AtWork || active) { if (entered && !active) Approach(s, now, p); continue; }
                if (entered) { Approach(s, now, p); continue; }
                if (d <= s.idleRadius)
                {
                    if (s.nextIdle < 0) s.nextIdle = now + Range(idleInterval);
                    else if (now >= s.nextIdle) { s.nextIdle = now + Range(idleInterval); TrySpeak(s, BarkTrigger.Idle, now, true, p); }
                }
            }
        }
        float Range(Vector2 r) => Mathf.Lerp(Mathf.Min(r.x, r.y), Mathf.Max(r.x, r.y), (float)rng.NextDouble());
        bool Available(NpcBarker s) => s && s.isActiveAndEnabled && s.barks && s.barks.lines != null && !(s.agent && (s.agent.talking || s.agent == session.ActiveNpc));

        void Approach(NpcBarker s, float now, Vector3 p)
        {
            if (!InSight(s, p)) return;
            foreach (var t in BarkRules.ApproachOrder)
            {
                if (s.Walker ? t == BarkTrigger.Greeting : t == BarkTrigger.Passing) continue;
                if (t == BarkTrigger.OrderDone && (orderNews == null || now - orderNewsAt > orderNewsSeconds || s.orderAcknowledged == orderNews)) continue;
                if (TrySpeak(s, t, now, false)) return;
            }
        }

        bool TrySpeak(NpcBarker s, BarkTrigger trigger, float now, bool checkSight, Vector3 player = default)
        {
            string id = s.SpeakerId;
            if (active || !memory.Ready(id, trigger, now)) return false;
            if (checkSight && !InSight(s, player)) return false;
            bool captions = CaptionsEnabled;
            var line = BarkRules.Pick(s.barks.lines, trigger, clock ? clock.Hour : 12, Holds, l => session.HasFlag(BarkRules.OnceFlag(id, l.id)), memory.Recent(id), rng.NextDouble());
            if (line == null || !line.voice && !captions) return false;
            Speak(s, line, trigger, now);
            return true;
        }
        bool Holds(string expression) => QuestConditions.Evaluate(expression, session);

        void Speak(NpcBarker s, BarkLine line, BarkTrigger trigger, float now)
        {
            string id = s.SpeakerId; var clip = line.voice;
            active = s; activeLine = line; activeVoiced = clip; captionShown = false;
            if (clip) s.Play(clip, session.Settings ? session.Settings.Sound.effects : 1, group);
            captionLeft = BarkRules.CaptionSeconds(line.text, clip ? clip.length : 0, captionMinSeconds, captionMaxSeconds);
            float cooldown = trigger switch { BarkTrigger.Greeting => greetingCooldown, BarkTrigger.Passing => passingCooldown, BarkTrigger.Weapon => weaponCooldown, _ => 0 };
            memory.Spoke(id, line.id, trigger, now, cooldown, globalGap + Mathf.Max(captionLeft, clip ? clip.length : 0));
            if (trigger == BarkTrigger.Acknowledge || trigger == BarkTrigger.OrderDone) memory.Hold(id, BarkTrigger.Greeting, now + greetingCooldown);
            if (trigger == BarkTrigger.OrderDone) s.orderAcknowledged = orderNews;
            if (line.once) session.SetFlag(BarkRules.OnceFlag(id, line.id));
            if (s.agent) s.agent.barking = true;
            LastSpeaker = s.DisplayName; LastSpeakerId = id; LastLineId = line.id; LastText = line.text; LastTrigger = trigger.ToString();
            LastVoiced = clip; LastTime = now; Count++;
        }

        /// The player can hear and see the speaker: no wall between their heads (Brann works behind the Salvage shop wall).
        bool InSight(NpcBarker s, Vector3 player)
        {
            var from = player + Vector3.up * 1.6f; var to = s.Mouth; var d = to - from; float len = d.magnitude;
            if (len < .05f) return true;
            var mask = session.follow ? session.follow.worldMask : (LayerMask)~(1 << 8);
            int n = Physics.RaycastNonAlloc(from, d / len, hits, len - .05f, mask, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < n; i++)
            {
                var t = hits[i].collider.transform;
                if (session.player && t.IsChildOf(session.player.transform) || t.IsChildOf(s.transform)) continue;
                return false;
            }
            return true;
        }

        // ---- QA (NativeQa snapshot "barks", dev bridge)
        public object QaState() => new
        {
            captions = CaptionsEnabled,
            speakers = speakers.Count(s => s),
            count = Count,
            active = active ? active.SpeakerId : null,
            caption = caption?.Text,
            captionBound = caption != null,
            last = new { speaker = LastSpeaker, speakerId = LastSpeakerId, line = LastLineId, text = LastText, trigger = LastTrigger, voiced = LastVoiced, time = LastTime },
            globalReadyIn = Mathf.Max(0, memory.GlobalReadyAt - Time.time),
            orderNews,
            roster = speakers.Where(s => s).Select(s => new { id = s.SpeakerId, name = s.DisplayName, walker = s.Walker, lines = s.barks ? s.barks.lines.Length : 0, voiced = s.barks ? s.barks.lines.Count(l => l != null && l.voice) : 0, inside = s.approach.Inside }).ToArray(),
        };
        public static object Qa(GameSession s) { var d = s ? s.GetComponent<BarkDirector>() : null; return d ? d.QaState() : null; }
        /// QA: forget cooldowns and approach state so a scripted walk-up greets deterministically.
        /// QA (barkReset): clears cooldowns, holds and the bark in progress. Each approach gate is re-armed to where the
        /// player stands now, so a speaker the player is already beside is not "walked up to" by the reset itself: a
        /// reset used to fire an instant Passing line from a walker who happened to be next to the player, which took the
        /// one-bark slot and the 7 s gap and swallowed the greeting the check was walking up for (Gemini merge, 21 Nov
        /// 2026: Daro's slower night pace put him beside the player at the 23:00 reset).
        public void QaReset()
        {
            Cancel(); memory.Clear();
            var p = session && session.player ? session.player.transform.position : transform.position;
            foreach (var s in speakers) if (s)
            {
                s.approach = default;
                if (Vector3.Distance(s.transform.position, p) <= (s.Walker ? s.passRadius : s.greetRadius)) s.approach.Occupy();
                s.nextIdle = -1; s.orderAcknowledged = null;
            }
        }
    }
}
