using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
    /// One sitting at the bench (DESIGN.md section 9). While the game is in CityState.Assembly at this bench's station it
    /// owns the bench camera, the hand (what is held, what the pointer or focus ring is on, the verb in progress), the
    /// idle hints, the sound events, Brann's lines and the hand-off to the crafting system.
    ///
    ///   Closed -> Working -> Closed                 (Esc steps back: the job is kept, a step in progress resets)
    ///             Working -> Completing -> Closed   (the last step: the crafting system grants and fits the grip)
    ///   Working: Idle -> Hover -> Carry(part) -> Seating -> Idle
    ///            Idle -> Hover -> ToolInHand -> Engaged(verb) -> ToolInHand, with Fault -> recovery step
    ///
    /// All of it runs through Step(dt, frame), which needs no camera and no player loop, so Edit Mode tests play the
    /// job with made-up frames exactly as the mouse or the keyboard would.
    [DisallowMultipleComponent]
    public class AssemblySession : MonoBehaviour
    {
        public enum Phase { Closed, Working, Completing }
        public static AssemblySession Current { get; private set; }
        /// QA: the next sitting may run without a crafting ticket (nothing reserved, nothing granted).
        public static bool AllowDetached;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)] static void ResetStatics() { Current = null; AllowDetached = false; }

        public AssemblyBench bench;
        [Tooltip("Found in the scene when empty.")] public GameSession session;

        public Phase State { get; private set; }
        public AssemblyJob Job { get; private set; }
        public AssemblyCraftLink Link { get; private set; }
        public AssemblyAudio Audio { get; private set; }
        public AssemblyFeedback Fx { get; private set; }
        public BenchVoice Voice { get; private set; }
        public AssemblyCameraRig Rig { get; private set; }
        public AssemblyHud Hud { get; private set; }
        AssemblyInput input; AssemblyInputFrame last;
        AssemblySettings S => bench.settings;
        AssemblyRecipeData Recipe => bench.recipe.data;

        // ---- the hand
        public AssemblyPart HeldPart { get; private set; }
        public AssemblyPart HeldTool { get; private set; }
        SeatVerb carry; AssemblyActionRef carryRef; bool carryHasRef;
        AssemblyVerb verb; AssemblyActionRef verbRef;
        FlickVerb flick; AssemblyActionRef flickRef; PointVerb aim; AssemblyActionRef aimRef; bool aiming; float aimPose;
        AssemblyActionRef inspectRef; bool inspecting; float inspectFrom;
        public AssemblyHit Focus { get; private set; }
        public AssemblyVerb Verb => verb;
        public AssemblyVerbStatus VerbStatus { get; private set; }
        readonly Dictionary<string, float> partial = new Dictionary<string, float>();
        readonly Dictionary<string, List<float>> marks = new Dictionary<string, List<float>>();
        readonly Dictionary<string, HashSet<string>> marksHit = new Dictionary<string, HashSet<string>>();
        float clock, idle, pressTime, abandonHeld, toolSpin; Vector2 pressScreen; bool pressPicked, keyTapPending, resumed; int hintLevel, hintVoice;
        Vector3 toolTip; string shotNow = "";
        public float Idle => idle; public int HintLevel => hintLevel;
        /// Every sound event and every voice trigger asked for in this sitting (QA and tests; the logs keep only the last few).
        public HashSet<string> AudioHeard => Audio != null ? Audio.Heard : new HashSet<string>();
        public HashSet<string> VoiceAsked => Voice != null ? Voice.Asked : new HashSet<string>();
        public bool Detached => Link != null && Link.Detached;
        public string LastNotice { get; private set; } = "";
        /// Raised with (step id, action key) when an action is done, and with (step id, fault kind) on a mistake.
        public event Action<string, string> ActionDone, Faulted;

        void OnEnable() { Current = this; }
        void OnDisable() { if (State != Phase.Closed) Shut(false); if (Current == this) Current = null; }
        void Awake() { if (!bench) bench = GetComponent<AssemblyBench>(); if (!session) session = FindAnyObjectByType<GameSession>(); }
        /// The crafting system opens the bench job through this (E at the bench, Brann's "Use the bench", Build by hand).
        void Start()
        {
            var craft = session ? session.GetComponent<CraftingSession>() : null;
            if (craft) craft.AssemblyOpener = (station, recipeId) =>
            {
                if (!station || station.stationId != bench.stationId || !bench.recipe || recipeId != Recipe.craftRecipeId) return false;
                session.OpenAssembly(station, recipeId);
                return session.State == CityState.Assembly;
            };
        }

        // ------------------------------------------------------------------ the player loop
        void Update()
        {
            if (!session || !bench) return;
            // Brann finishes what he was saying (and the line queued behind it) after the player has stepped back
            if (State == Phase.Closed && Voice != null) Voice.Tick(Time.deltaTime);
            bool want = session.State == CityState.Assembly && session.ActiveStationId == bench.stationId;
            if (want && State == Phase.Closed) Open(AllowDetached);
            else if (!want && State != Phase.Closed) Shut(State == Phase.Working);
            if (State != Phase.Working) return;
            var camera = Rig != null && Rig.Lens ? Rig.Lens : Camera.main;
            last = input != null ? input.Read(camera, S.tapSeconds, S.tapPixels) : default;
            if (Hud != null && last.primaryDown && last.pointer && Hud.PointerOnControl(last.screen)) { last.primaryDown = false; last.primaryHeld = false; }
            last.abandonHeld |= Hud != null && Hud.AbandonPressed;
            Step(Time.deltaTime, last, camera ? camera.transform.position : (Vector3?)null);
        }
        void LateUpdate()
        {
            if (State == Phase.Closed || Rig == null) return;
            Rig.Focus(FocusOfWork());
            Rig.Tick(Time.deltaTime, last, HeldPart == null && HeldTool == null && verb == null, session && session.reducedMotion);
            Hud?.Tick(Time.deltaTime);
        }

        // ------------------------------------------------------------------ opening and closing
        /// Starts a sitting. With a GameSession this is driven by CityState.Assembly; tests call it directly.
        public bool Open(bool allowDetached)
        {
            if (State != Phase.Closed || !bench || !bench.recipe || !bench.settings) return false;
            bench.Index(true);
            Link = new AssemblyCraftLink(session);
            var ticket = Link.Begin(Recipe.craftRecipeId, allowDetached || !session, out string reason);
            if (ticket == null)
            {
                Note("You cannot start that here. " + Link.ReasonText(Recipe.craftRecipeId, reason));
                if (session) { session.Cue(CitySoundCue.Unavailable); session.Close(); }
                return false;
            }
            AllowDetached = false;
            string blob = Link.Blob; resumed = !string.IsNullOrEmpty(blob);
            Job = AssemblyJob.FromBlob(Recipe, blob);
            Audio = new AssemblyAudio(bench, S) { Clock = () => clock, effectsLevel = session && session.Settings ? session.Settings.Sound.effects : 1 };
            Voice?.Stop();
            Fx = new AssemblyFeedback(bench); Voice = new BenchVoice(bench, session); Rig = new AssemblyCameraRig(bench, S);
            partial.Clear(); marks.Clear(); marksHit.Clear(); waitDisturbed.Clear(); waitSpoiled.Clear(); HeldPart = HeldTool = null; carry = null; verb = null; flick = null; aim = null; aiming = false; aimPose = 0;
            idle = 0; hintLevel = 0; abandonHeld = 0; Focus = default; shotNow = "";
            bench.Rebuild(Job); RestoreCards(); UpdateSchematic();
            State = Phase.Working;
            if (session)
            {
                input = new AssemblyInput(session.input); session.input.SetBench(true);
                var lens = session.follow ? session.follow.GetComponent<Camera>() : Camera.main;
                if (lens && Application.isPlaying) Rig.Enter(lens, session.reducedMotion, WantedShot());
                var doc = FindAnyObjectByType<CityHud>() is CityHud hud ? hud.GetComponent<UIDocument>() : null;
                if (doc && doc.rootVisualElement != null)
                {
                    Hud = new AssemblyHud(doc.rootVisualElement, bench.hudStyle);
                    bool first = PlayerPrefs.GetInt(AssemblyHud.SeenKey, 0) == 0;
                    Hud.Show(true, first); if (first) { PlayerPrefs.SetInt(AssemblyHud.SeenKey, 1); PlayerPrefs.Save(); }
                }
            }
            Audio.Loop("amb", "asm.amb.bed", bench.SurfacePoint, true);
            Voice.Say(resumed ? "session.enter.resume" : "session.enter.first");
            ReportStage(); RefreshWatchers();
            return true;
        }

        /// Ends the sitting. keep = the job is unfinished and stays on the bench (saved through the crafting system).
        void Shut(bool keep)
        {
            DropEverything();
            // holster and step back: when leaving is all that is left, leaving finishes the job
            var leave = keep && Job != null ? Job.LeaveStep : null;
            if (leave != null)
            {
                Job.CompleteStep(leave.id, 1); Link.Blob = Job.ToBlob();
                Voice?.Say("step.done:" + leave.id, true);
                keep = false; State = Phase.Completing; HandOver();
            }
            if (keep && Job != null && Link != null)
            {
                Job.Leave(); Link.Blob = Job.ToBlob(); bench.Rebuild(Job); RestoreCards();
                Voice?.Say("session.leave.unfinished", true);
            }
            if (session && session.input) session.input.SetBench(false);
            Rig?.Exit(session && session.reducedMotion); Audio?.Dispose(); Fx?.Clear(); Hud?.Dispose(); Hud = null;
            // Brann finishes the line he has begun; nothing queued follows it
            State = Phase.Closed; input = null;
        }
        /// Tests and the editor: closes a sitting that was opened without a GameSession.
        public void Close(bool keep = true) { if (State != Phase.Closed) Shut(keep && State == Phase.Working); Voice?.Stop(); }

        void Note(string text) { LastNotice = text; if (session) session.Notify(text, "Workbench"); }

        void ReportStage()
        {
            var stage = Job.Stage; if (stage == null) return;
            Link.ReportStage(stage.id, stage.label);
            Hud?.SetStage(Detached ? $"{stage.label.ToUpperInvariant()}  ·  {Job.StageIndex + 1} / {Recipe.stages.Length}" : "");
            UpdateSchematic();
        }
        /// The schematic on the backboard: the region of the stage in hand is lit, finished ones carry Brann's tick.
        void UpdateSchematic()
        {
            int now = Job.StageIndex;
            for (int i = 0; i < Recipe.stages.Length; i++) { var m = bench.Param("fixtures.schematic_" + Recipe.stages[i].id); if (!m) m = bench.Param("fixtures.schematic." + Recipe.stages[i].id); if (m) m.Set(i < now ? 1 : i == now ? .5f : 0); }
        }

        // ------------------------------------------------------------------ one frame of work
        public void Step(float dt, AssemblyInputFrame f, Vector3? eye = null)
        {
            if (State != Phase.Working) return;
            clock += dt; Job.Seconds += dt; idle += dt; pulsed = false;
            Vector3 eyePoint = eye ?? f.ray.origin;
            Fx.reducedMotion = session && session.reducedMotion;
            Voice.Tick(dt);
            if (Abandoning(dt, f)) return;
            UpdateFocus(f);
            if (verb != null) TickVerb(dt, f, eyePoint);
            if (State == Phase.Working) TickWaits(dt);
            if (verb == null && State == Phase.Working)
            {
                if (carry != null) TickCarry(dt, f, eyePoint);
                else if (HeldTool) TickTool(dt, f);
                if (State == Phase.Working) { HandlePrimary(f, eyePoint); HandleOther(f); }
            }
            if (State != Phase.Working) return;
            var usable = Focus.part && Usable(Focus) ? Focus.part : Focus.marker && Usable(Focus) ? bench.Part(Focus.marker.ownerPart) : null;
            Fx.Hover(usable); Fx.Tick(dt);
            Hints(dt, f);
            // (without a live camera, in tests and the selftest, the shot is still tracked: the bot looks through it)
            string shot = pinnedShot ?? WantedShot(); if (shot != shotNow) { float blendFor = aim != null && shot == aimRef.action.shot ? S.shotSeconds * 1.5f : -1; if (Rig == null || !Rig.Active || Rig.SetShot(shot, session && session.reducedMotion, blendFor)) shotNow = shot; }
            if (aimDot) aimDot.gameObject.SetActive(aiming);
            ClearViewToCard(); UpdateActionLine(); ShowCardPrints();
        }

        /// Work that goes on by itself once it is set up (the seam curing under the lamp): time passes while the action is
        /// open and nobody lifts the part. Lifting it early is the action's fault, and the wait starts again.
        readonly HashSet<string> waitDisturbed = new HashSet<string>(), waitSpoiled = new HashSet<string>();
        void TickWaits(float dt)
        {
            foreach (var r in Open().ToList())
            {
                var a = r.action; if (a.verb != AssemblyVerbKind.Window || a.mode != "wait") continue;
                var p = bench.Part(a.part); float need = Mathf.Max(.1f, a.seconds); partial.TryGetValue(r.Id, out float t);
                if (p && HeldPart == p)
                {
                    if (t > 0 && waitDisturbed.Add(r.Id)) { waitSpoiled.Add(r.Id); Audio.StopLoop("wait:" + r.Id); RaiseFault(r, a.faults.Length > 0 ? a.faults[0].kind : "disturbed"); }
                    partial[r.Id] = 0; continue;
                }
                waitDisturbed.Remove(r.Id);
                if (t <= 0 && !string.IsNullOrEmpty(a.loop)) Audio.Loop("wait:" + r.Id, a.loop, p ? p.GrabPoint : bench.SurfacePoint);
                t += dt; partial[r.Id] = t;
                if (t >= need) { Audio.StopLoop("wait:" + r.Id); bool spoiled = waitSpoiled.Remove(r.Id); Complete(r, spoiled ? .6f : 1); return; }
            }
        }
        /// Seconds an open wait has run (QA, the bot).
        public bool Waiting(out AssemblyActionRef wait) { foreach (var r in Open()) if (r.action.verb == AssemblyVerbKind.Window && r.action.mode == "wait") { wait = r; return true; } wait = default; return false; }
        public bool CarryFlipped => carry != null && carry.Flipped;

        Transform aimDot => bench.transform.Find("Aim dot");

        // ------------------------------------------------------------------ the test card made readable (21 Nov)
        readonly List<Renderer> clearedForCard = new List<Renderer>();
        /// While the pistol is held for the test card, anything standing between the card shot's eye and the card is not drawn
        /// (a jar or the bin in front of the board); everything comes back when the pulses are done or the pistol is put down.
        void ClearViewToCard()
        {
            bool want = aim != null && aim.c.marker && State == Phase.Working;
            if (!want) { if (clearedForCard.Count > 0) { foreach (var r in clearedForCard) if (r) r.forceRenderingOff = false; clearedForCard.Clear(); } return; }
            if (clearedForCard.Count > 0) return;
            var cam = ShotCamera(string.IsNullOrEmpty(aimRef.action.shot) ? shotNow : aimRef.action.shot); if (!cam) return;
            var card = aim.c.marker.transform; var eye = cam.transform.position; var to = card.position - eye; float far = to.magnitude; if (far < .05f) return;
            var ray = new Ray(eye, to / far); var cardPart = bench.Part(aim.c.marker.ownerPart);
            var planes = GeometryUtility.CalculateFrustumPlanes(Matrix4x4.Perspective(cam.fieldOfView, 16f / 9f, .05f, far - .06f) * Matrix4x4.Scale(new Vector3(1, 1, -1)) * cam.transform.worldToLocalMatrix);
            foreach (var p in bench.Parts)
            {
                if (!p || p == HeldPart || p == cardPart || p.Gone || !p.gameObject.activeInHierarchy || HeldPart && p.transform.IsChildOf(HeldPart.transform)) continue;
                if (cardPart && (cardPart.transform.IsChildOf(p.transform) || p.transform.IsChildOf(cardPart.transform))) continue;   // the board the card is clipped to
                foreach (var r in p.renderers)
                {
                    if (!r || !r.enabled || r.forceRenderingOff) continue;
                    var b = r.bounds; b.Expand(.04f);
                    // on the line to the card, or anywhere in the picture between the eye and the card (21 Nov: the stand-in jar and
                    // bin stood low in front of the shot, off the line)
                    bool onLine = b.IntersectRay(ray, out float t) && t < far - .04f;
                    // (not the worktop and the mats, which are under everything: big and flat)
                    bool flatBig = r.bounds.size.y < .03f && Mathf.Max(r.bounds.size.x, r.bounds.size.z) > .3f;
                    bool before = !flatBig && Vector3.Dot(b.center - eye, to / far) < far - .08f && GeometryUtility.TestPlanesAABB(planes, b);
                    if (onLine || before) { r.forceRenderingOff = true; clearedForCard.Add(r); }
                }
            }
        }
        List<(AssemblyPart card, Renderer[] prints)> cardPrints;
        /// The rings printed on a test card show only once it is clipped to the board (21 Nov: they floated over the bench in
        /// other shots).
        void ShowCardPrints()
        {
            cardPrints ??= bench.Parts.Select(p => (p, p.GetComponentsInChildren<Renderer>(true).Where(r => r.name.StartsWith("print_ring_")).ToArray())).Where(x => x.Item2.Length > 0).ToList();
            foreach (var (card, prints) in cardPrints)
            {
                bool on = card && !card.Gone && card.gameObject.activeInHierarchy && card.place != null && card.place.StartsWith("fixtures.board/");
                foreach (var r in prints) if (r && r.enabled != on) r.enabled = on;
            }
        }
        string actionLine = "";
        /// The action line for an action that names one, with what is left of a counted one (the three test pulses).
        void UpdateActionLine()
        {
            string text = "";
            var next = aim != null ? aimRef : NextAction();
            if (next.HasValue && (!string.IsNullOrEmpty(next.Value.action.line) || LineFor != null))
            {
                text = !string.IsNullOrEmpty(next.Value.action.line) ? next.Value.action.line : LineFor?.Invoke(next.Value) ?? "";
                if (text != "" && next.Value.action.count > 1)
                {
                    int done = aim != null && aimRef.Id == next.Value.Id ? aim.Hits.Count + Mathf.RoundToInt(aim.c.carried) : partial.TryGetValue(next.Value.Id, out var pc) ? Mathf.RoundToInt(pc) : 0;
                    int left = Mathf.Max(0, next.Value.action.count - done);
                    text += left == 1 ? "  ·  1 left" : $"  ·  {left} left";
                }
            }
            if (text != actionLine) { actionLine = text; Hud?.SetAction(text); }
        }
        /// The action line as it stands (QA).
        public string ActionLine => actionLine;
        bool pulsed;

        bool Abandoning(float dt, in AssemblyInputFrame f)
        {
            abandonHeld = f.abandonHeld ? abandonHeld + dt : 0;
            Hud?.SetAbandon(abandonHeld / Mathf.Max(.1f, S.abandonHoldSeconds));
            if (abandonHeld < S.abandonHoldSeconds) return false;
            Abandon(); return true;
        }

        /// Packs the job in: the weapon and what was not spent go back to the pack; what was cut or fused is lost.
        public void Abandon()
        {
            if (State != Phase.Working) return;
            DropEverything();
            if (!Link.Abandon(Job.SpentInputs(), out string reason))
            {
                // the pack cannot take the parts back: say why, and the job stays as it is
                Note("You cannot pack the job in yet. " + Link.ReasonText(Recipe.craftRecipeId, reason));
                if (session) session.Cue(CitySoundCue.Unavailable);
                abandonHeld = -1.5f; return;
            }
            Link.Blob = null; Voice.Say("session.abandon", true);
            Note("You pack the job in. Your pistol and what you had not used are back in your pack.");
            Job = new AssemblyJob(Recipe); bench.ResetAsFound();
            State = Phase.Completing;
            if (session) session.Close(); else Shut(false);
        }

        // ------------------------------------------------------------------ what is open, what matches
        IEnumerable<AssemblyActionRef> Open() => Job.OpenActions;
        static bool ToolFits(string wanted, AssemblyPart tool) => wanted == "*" || (string.IsNullOrEmpty(wanted) ? !tool : tool && tool.HasTag(wanted));
        bool Matches(AssemblyActionDef a, AssemblyHit hit)
        {
            if (hit.part)
            {
                if (a.part == hit.part.id || a.target == hit.part.id || WrongFor(a, hit.part) != null) return true;
                if (a.verb == AssemblyVerbKind.Turn && a.mode == "reveal") { var root = bench.Part(a.part); return root && hit.part.transform.IsChildOf(root.transform); }
                if (a.verb == AssemblyVerbKind.Seat && (a.target == "seat" || a.target == "start")) { var p = bench.Part(a.part); return p && p.parentId == hit.part.id; }
                return false;
            }
            if (!hit.marker) return false;
            if (a.target == hit.marker.id || Array.IndexOf(a.targets, hit.marker.id) >= 0) return true;
            // a mark sits on its part: turning or striking the part can start from the mark (the oil point on the screw head)
            return (a.verb == AssemblyVerbKind.Turn || a.verb == AssemblyVerbKind.Window) && a.mode != "reveal" && a.mode != "wait" && !string.IsNullOrEmpty(a.part) && a.part == hit.marker.ownerPart;
        }
        /// The fault an action has for being done by the wrong thing (the lead pulled by its wire): "wrong:PART".
        static AssemblyFaultDef WrongFor(AssemblyActionDef a, AssemblyPart p) => p ? Array.Find(a.faults, fd => fd.when == "wrong:" + p.id) : null;
        AssemblyActionRef? FindOpen(Func<AssemblyActionDef, bool> test)
        {
            foreach (var r in Open()) if (test(r.action)) return r;
            return null;
        }
        /// An action of an open step that is waiting for earlier actions of the same step.
        AssemblyActionRef? FindWaiting(Func<AssemblyActionDef, bool> test)
        {
            foreach (var step in Job.OpenSteps) foreach (var a in step.actions) { var why = Job.Blocked(step.id, a.key); if (why != null && why.StartsWith("after:") && test(a)) return new AssemblyActionRef { step = step, action = a }; }
            return null;
        }
        AssemblyActionRef? OpenSeatFor(AssemblyPart p, AssemblyPart tool) => p ? FindOpen(a => a.verb == AssemblyVerbKind.Seat && a.mode != "inspect" && a.part == p.id && ToolFits(a.tool, tool)) : null;

        /// What a part is on: the part it is seated on, or the part that owns the place it has been put (the gimbal pressed into
        /// the core, a screw started in a plate, a sheet stacked on the other). Null when it lies free or on a fixture.
        AssemblyPart Carrier(AssemblyPart p)
        {
            if (!p) return null;
            if (p.place == "seat") return bench.Part(p.parentId);
            var at = bench.Marker(p.place); var owner = at && at.kind == AssemblyMarkerKind.Place ? bench.Part(at.ownerPart) : null;
            return owner && !owner.IsFixture ? owner : null;
        }
        /// Fitted to something else, so it is handled with it unless the job has work for the part itself.
        bool Installed(AssemblyPart p) => p && (p.place == "seat" || Carrier(p));

        /// The stage in hand still has a step that handles this part (it is not its turn yet).
        bool DueThisStage(AssemblyPart p)
        {
            var stage = Job.Stage; if (stage == null) return false;
            foreach (var step in stage.steps) { if (Job.IsDone(step.id) || step.recovery && Job.State(step.id) == AssemblyStepState.Dormant) continue; foreach (var a in step.actions) if (a.part == p.id && !Job.ActionDone(step.id, a.key)) return true; }
            return false;
        }

        /// Can the thing under the pointer be used now? Decides what may be picked and what gets the affordance rim.
        bool Usable(AssemblyHit hit)
        {
            if (hit.marker)
            {
                var m = hit.marker; if (!m.gameObject.activeInHierarchy) return false;
                if (m.kind == AssemblyMarkerKind.Place)
                {
                    if (HeldTool && !HeldPart) return IsPocket(m, HeldTool) || FindOpen(a => a.verb == AssemblyVerbKind.Seat && a.part == HeldTool.id && a.target == m.id) != null;
                    var held = HeldPart ? HeldPart : null; if (!held) return false;
                    return m.Accepts(held.id) || carryHasRef && carryRef.action.target == m.id || aim != null && aimRef.action.target == m.id;
                }
                // one mark of several is used up once it has been hit
                foreach (var r in Open()) if (Matches(r.action, hit) && !(marksHit.TryGetValue(r.Id, out var hitAlready) && hitAlready.Contains(m.id))) return true;
                // work that is not ready yet answers only a tool brought to it too soon (the seized screw); a bare hand passes
                // through to the part the mark is on
                return HeldTool && FindWaiting(a => ToolFits(a.tool, HeldTool) && Matches(a, hit)) != null;
            }
            var p = hit.part; if (!p || p.Gone || p == HeldPart || p == HeldTool) return false;
            if (HeldPart) return carryHasRef && Matches(carryRef.action, hit) || aim != null && Matches(aimRef.action, hit);
            if (FindOpen(a => a.verb != AssemblyVerbKind.Flick && ToolFits(a.tool, HeldTool) && Matches(a, hit)) != null) return true;
            if (p.IsTool) return p.gameObject.activeInHierarchy;   // a tool can always be taken, also in exchange for the one in hand
            if (HeldTool) return FindWaiting(a => ToolFits(a.tool, HeldTool) && Matches(a, hit)) != null || FindOpen(a => Matches(a, hit) && a.verb != AssemblyVerbKind.Flick) != null;
            if (p.IsFixture || p.IsConsumable) return false;
            // a loose part can always be picked up, unless it is clamped; a seated one answers only when this stage has work
            // for it (it comes off, or it refuses and shows what holds it). Otherwise the press goes through to what it is part of.
            if (!Installed(p)) return !bench.ClampOn(p) || FindOpen(a => a.part == p.id) != null || FindWaiting(a => a.part == p.id) != null;
            return FindOpen(a => a.part == p.id) != null || FindWaiting(a => a.part == p.id) != null || DueThisStage(p);
        }

        /// A part fitted in the one under the pointer that the job wants now, and the job has nothing for the carrier itself (the
        /// rotor to be lifted out of the cradle lying on the mat): where the pointer passes over both, within 3 cm of depth, the
        /// hand goes for the fitted part. The rim of what it is fitted in stands proud of it, so from most shots the carrier's
        /// surface is met first.
        AssemblyHit FittedChildUnder(Ray ray, AssemblyHit hit)
        {
            var carrier = hit.part; if (!carrier || HeldPart || Job == null) return hit;
            // the other way round: a part fitted on what the job wants handled now, with nothing of its own open yet (the servo's lid
            // still clipped on while the servo is to be turned round in the vise): the hand takes what it is fitted to
            if (FindOpen(a => a.part == carrier.id && ToolFits(a.tool, HeldTool)) == null)
            {
                var up = bench.Part(carrier.parentId);
                for (int guard = 0; guard < 4 && up && carrier.OnParent; guard++)
                {
                    if (FindOpen(a => a.part == up.id && a.verb == AssemblyVerbKind.Seat && ToolFits(a.tool, HeldTool)) != null)
                    { var h = new AssemblyHit { part = up, distance = hit.distance, point = hit.point }; if (Usable(h)) return h; break; }
                    if (!up.OnParent) break; up = bench.Part(up.parentId);
                }
            }
            if (FindOpen(a => a.part == carrier.id && ToolFits(a.tool, HeldTool)) != null) return hit;
            var best = hit; float bestT = float.MaxValue;
            foreach (var c in bench.Parts)
            {
                if (!c || c == carrier || c.place != "seat" || c.parentId != carrier.id || c.Gone || !c.gameObject.activeInHierarchy) continue;
                if (FindOpen(a => a.part == c.id && a.verb != AssemblyVerbKind.Flick && ToolFits(a.tool, HeldTool)) == null) continue;
                float t = c.Raycast(ray, .006f); if (t < 0 || t - hit.distance > .03f || t >= bestT) continue;
                var h = new AssemblyHit { part = c, distance = t, point = ray.GetPoint(t) };
                if (!Usable(h)) continue;
                best = h; bestT = t;
            }
            if (best.part != carrier) return best;
            // two loose parts lying together (the strip and its spare side by side on the mat): of what the pointer is on within
            // 8 mm of depth, the hand goes for the one the job wants now (21 Nov, sh-real1: the press for the strap took the spare)
            foreach (var c in bench.Parts)
            {
                if (!c || c == carrier || c.Gone || !c.gameObject.activeInHierarchy || c.IsFixture || c.IsTool) continue;
                if (FindOpen(a => a.part == c.id && a.verb != AssemblyVerbKind.Flick && ToolFits(a.tool, HeldTool)) == null) continue;
                float t = c.Raycast(ray, .006f); if (t < 0 || Mathf.Abs(t - hit.distance) > .008f || t >= bestT) continue;
                var h = new AssemblyHit { part = c, distance = t, point = ray.GetPoint(t) };
                if (!Usable(h)) continue;
                best = h; bestT = t;
            }
            return best;
        }

        // ------------------------------------------------------------------ focus: the pointer, or the keyboard ring
        void UpdateFocus(in AssemblyInputFrame f)
        {
            if (verb != null && !(VerbStatus.waiting)) return;
            if (f.pointer) { Focus = FittedChildUnder(f.ray, bench.Pick(f.ray, Usable)); return; }
            if (Focus.Valid && !(Focus.part ? Focus.part.gameObject.activeInHierarchy : Focus.marker.gameObject.activeInHierarchy)) Focus = default;
            if (f.next || f.previous || !Focus.Valid && (f.navStep != Vector2Int.zero || f.primaryDown)) { CycleFocus(f.previous ? -1 : 1); return; }
            if (f.navStep == Vector2Int.zero || f.lookKey) return;
            var frame = bench.surface ? bench.surface : bench.transform;
            var dir = (frame.right * f.navStep.x - frame.forward * f.navStep.y).normalized; var from = Focus.Position;
            AssemblyHit best = default; float bestScore = float.MaxValue;
            foreach (var hit in Candidates())
            {
                var d = Vector3.ProjectOnPlane(hit.Position - from, bench.Up); float len = d.magnitude; if (len < .004f) continue;
                float along = Vector3.Dot(d / len, dir); if (along < .35f) continue;
                float score = len * (2.2f - along);
                if (score < bestScore) { bestScore = score; best = hit; }
            }
            if (best.Valid) Focus = best;
        }
        IEnumerable<AssemblyHit> Candidates()
        {
            foreach (var p in bench.Parts) if (p && p.gameObject.activeInHierarchy) { var hit = AssemblyHit.Of(p); if (Usable(hit)) yield return hit; }
            foreach (var m in bench.Markers) if (m && m.gameObject.activeInHierarchy) { var hit = AssemblyHit.Of(m); if (Usable(hit)) yield return hit; }
        }
        /// The things the open actions involve, in table order: the tool to take, the part to handle, where it goes.
        public List<AssemblyHit> UsefulObjects()
        {
            var list = new List<AssemblyHit>(); var seen = new HashSet<string>();
            void Add(AssemblyHit h) { if (h.Valid && seen.Add(h.Id)) list.Add(h); }
            foreach (var r in Open())
            {
                var a = r.action;
                if (!string.IsNullOrEmpty(a.tool) && !ToolFits(a.tool, HeldTool)) { var t = bench.Tool(a.tool); if (t) Add(AssemblyHit.Of(t)); }
                var p = bench.Part(a.part);
                if (p && p != HeldPart && p != HeldTool && !p.Gone && p.gameObject.activeInHierarchy) Add(AssemblyHit.Of(p));
                marksHit.TryGetValue(r.Id, out var hitAlready);
                foreach (var id in a.targets.Length > 0 ? a.targets : new[] { a.target })
                {
                    var m = bench.Marker(id);
                    if (m) { if (m.gameObject.activeInHierarchy && (hitAlready == null || !hitAlready.Contains(id))) Add(AssemblyHit.Of(m)); continue; }
                    var tp = bench.Part(id); if (tp) { Add(AssemblyHit.Of(tp)); continue; }
                    if ((id == "seat" || id == "start") && p) { var parent = bench.Part(p.parentId); if (parent) Add(AssemblyHit.Of(parent)); }
                }
            }
            return list;
        }
        void CycleFocus(int step)
        {
            var list = UsefulObjects().Where(Usable).ToList(); if (list.Count == 0) { Focus = default; return; }
            int i = list.FindIndex(h => h.Id == Focus.Id);
            Focus = list[((i < 0 ? (step > 0 ? 0 : list.Count - 1) : i + step) % list.Count + list.Count) % list.Count];
        }
        /// Where the hand should be for the thing in focus: the socket's approach for the part in hand, else the thing.
        Vector3 FocusPoint()
        {
            if (!Focus.Valid) return HeldPart ? HeldPart.GrabPoint : HeldTool ? HeldTool.TipPoint : bench.SurfacePoint;
            if (HeldPart && carryHasRef && Matches(carryRef.action, Focus) && bench.TargetPose(HeldPart, carryRef.action.target, out _, out _, out var approach, out _)) return approach.position + HeldPart.GrabOffsetAt(approach.rotation);
            return Focus.Position;
        }

        // ------------------------------------------------------------------ the hand
        AssemblyVerbContext Context(AssemblyActionRef? r, AssemblyPart part, AssemblyPart tool, AssemblyMarker marker)
        {
            var c = new AssemblyVerbContext { bench = bench, settings = S, audio = Audio, fx = Fx, camera = Rig, part = part, tool = tool, marker = marker };
            if (r.HasValue) { c.step = r.Value.step; c.action = r.Value.action; partial.TryGetValue(r.Value.Id, out c.carried); }
            return c;
        }
        void Feed(AssemblyVerbContext c, in AssemblyInputFrame f, Vector3 eye)
        {
            c.clock = clock; c.eye = eye; c.reducedMotion = session && session.reducedMotion;
            c.hasFocusPoint = !f.pointer; c.focusPoint = FocusPoint();
        }

        void StartCarry(AssemblyPart p, AssemblyActionRef? seat)
        {
            carry = new SeatVerb { c = Context(seat, p, HeldTool, null) }; carryHasRef = seat.HasValue; if (seat.HasValue) carryRef = seat.Value;
            HeldPart = p; carry.Begin(); idle = Mathf.Min(idle, S.hintGlint * .5f);
            RefreshWatchers();
        }
        void StopCarry() { carry = null; HeldPart = null; carryHasRef = false; flick = null; aim = null; aiming = false; aimPose = 0; inspecting = false; }

        /// Watchers ride along with a carry: a shake of the thing in hand, or its test pulses at the card.
        void RefreshWatchers()
        {
            flick = null; aim = null; bool wasInspecting = inspecting; inspecting = false;
            if (!HeldPart || Job == null) return;
            // looking a part over: turning it round in the hand
            var look = FindOpen(a => a.verb == AssemblyVerbKind.Seat && a.mode == "inspect" && a.part == HeldPart.id);
            if (look.HasValue && carry != null) { if (!wasInspecting || inspectRef.Id != look.Value.Id) inspectFrom = carry.Turned; inspectRef = look.Value; inspecting = true; }
            if (carry != null)
            {
                var seat = OpenSeatFor(HeldPart, HeldTool);
                if (seat.HasValue && (!carryHasRef || carryRef.Id != seat.Value.Id)) { carryRef = seat.Value; carryHasRef = true; carry.c.step = seat.Value.step; carry.c.action = seat.Value.action; }
                else if (!seat.HasValue && carryHasRef) { carryHasRef = false; carry.c.step = null; carry.c.action = null; }
            }
            var fl = FindOpen(a => a.verb == AssemblyVerbKind.Flick && a.part == HeldPart.id);
            if (fl.HasValue) { flickRef = fl.Value; flick = new FlickVerb { c = Context(fl, HeldPart, null, null) }; flick.Begin(); }
            var am = FindOpen(a => a.verb == AssemblyVerbKind.Point && a.mode == "aim" && a.part == HeldPart.id);
            if (am.HasValue)
            {
                aimRef = am.Value; aim = new PointVerb { c = Context(am, HeldPart, null, bench.Marker(am.Value.action.target)) };
                bool after = Job.StageIndex >= Recipe.stages.Length - 1;
                aim.c.handling = Link.Handling(Recipe.modItemId, Job.Quality, after); aim.Begin();
            }
        }

        void TickCarry(float dt, in AssemblyInputFrame f, Vector3 eye)
        {
            Feed(carry.c, f, eye);
            var part = HeldPart;
            var st = carry.Tick(dt, f);
            if (HeldTool && part) AssemblyVerb.PlaceTool(HeldTool, part.GrabPoint, -bench.Up);
            if (st.done)
            {
                // seated: the action counts first, then a fumble on the way in (the vial rolls off the tray after it was set down)
                var done = carryRef; bool had = carryHasRef;
                StopCarry();
                if (had) Complete(done, st.precision);
                if (had && st.fault != null && State == Phase.Working) RaiseFault(done, st.fault);
                return;
            }
            if (st.fault != null && carryHasRef) RaiseFault(carryRef, st.fault);
            if (inspecting && carry.Turned - inspectFrom >= Mathf.Max(90, inspectRef.action.turns * 360)) { var r = inspectRef; inspecting = false; Complete(r, 1); if (carry == null) return; }
            if (st.ended) { StopCarry(); return; }
            if (flick != null) { Feed(flick.c, f, eye); var fs = flick.Tick(dt, f); if (fs.done) { var r = flickRef; flick = null; Complete(r, 1); } }
            aiming = false;
            if (aim != null && aim.c.marker)
            {
                // (21 Nov, Carl at sh-real2b: picking the pistol up moved to the card and nothing showed until the pointer happened to
                // be within a few cm of its middle; now anywhere within 30 cm of the card's middle raises the pistol and shows the dot)
                var card = aim.c.marker; float reach = Mathf.Max(.30f, Mathf.Max(.03f, card.size.x) * 1.8f);
                aiming = f.pointer ? AssemblyVerb.DistanceToRay(f.ray, card.transform.position, out _) < reach : Focus.marker == card;
                if (aiming)
                {
                    pulsed |= f.primaryDown;   // this press is a test pulse, whatever it finishes
                    Feed(aim.c, f, eye); int before = aim.Hits.Count;
                    var ast = aim.Tick(dt, f);
                    PoseAtCard(dt, part, eye);
                    // on the face the eye sees
                    var dot = aimDot; float toEye = Vector3.Dot(card.transform.forward, eye - card.transform.position) >= 0 ? 1 : -1;
                    if (dot) dot.SetPositionAndRotation(aim.AimPoint + card.transform.forward * (.0012f * toEye), card.transform.rotation);
                    for (int i = before; i < aim.Hits.Count; i++) AddHole(aimRef, aim.Hits[i]);
                    partial[aimRef.Id] = ast.carry;
                    if (ast.done) { var r = aimRef; aim = null; aiming = false; Complete(r, 1); }
                }
            }
            if (!aiming && aimPose > 0 && carry != null) PoseAtCard(dt, part, eye);
        }

        /// The pistol at the card. While the hand is on the card the pistol comes up in front of the eye, low in the picture
        /// and seen from behind, its muzzle on the wandering aim point (so what sways is the handling numbers); off the card it
        /// goes back to the carry.
        void PoseAtCard(float dt, AssemblyPart part, Vector3 eye)
        {
            bool cut = session && session.reducedMotion;
            aimPose = cut ? (aiming ? 1 : 0) : Mathf.MoveTowards(aimPose, aiming ? 1 : 0, dt / Mathf.Max(.01f, S.aimRaiseSeconds));
            if (aimPose <= 0 || !part) return;
            var live = Rig != null && Rig.Active && Rig.Lens ? Rig.Lens : ShotCamera(shotNow);
            if (!live) return;
            if (aiming && aim != null) aimAt = aim.AimPoint;
            var pose = AimPose(part, live.transform.position, live.transform.rotation, live.fieldOfView, aimAt, S);
            float k = aimPose * aimPose * (3 - 2 * aimPose);
            part.transform.SetPositionAndRotation(Vector3.Lerp(part.transform.position, pose.position, k), Quaternion.Slerp(part.transform.rotation, pose.rotation, k));
        }
        Vector3 aimAt;
        /// Where a held pistol is while it is aimed from an eye: its grip low in the picture under the point it aims at, top
        /// up, muzzle on the aim point. (The muzzle is the part's tip: +Z out of the bore, +Y the top of the pistol.)
        public static Pose AimPose(AssemblyPart part, Vector3 eye, Quaternion view, float fov, Vector3 aimPoint, AssemblySettings s)
        {
            Vector3 forward = view * Vector3.forward, up = view * Vector3.up, right = view * Vector3.right;
            float reach = s ? s.aimReach : .42f, low = s ? s.aimLow : .42f;
            float half = Mathf.Tan(fov * .5f * Mathf.Deg2Rad) * reach;
            var seen = Quaternion.Inverse(view) * (aimPoint - eye);
            float across = seen.z > .05f ? Mathf.Clamp(seen.x / seen.z * reach, -half, half) * .55f : 0;
            // (21 Nov: low in the picture it was seen from above and read as pointing up; now nearer eye height and a little to the
            // right, so the eye looks along the barrel at the card)
            Vector3 hold = eye + forward * reach - up * (half * low) + right * (across + half * (s ? s.aimSide : .32f));
            var t = part.transform;
            var tipTurn = part.tip ? Quaternion.Inverse(t.rotation) * part.tip.rotation : Quaternion.LookRotation(Vector3.right, Vector3.up);
            var tipAt = part.tip ? Vector3.Scale(t.InverseTransformPoint(part.tip.position), t.lossyScale) : Vector3.Scale(part.localBounds.center, t.lossyScale);
            var rotation = t.rotation; Vector3 muzzle = hold;
            for (int i = 0; i < 3; i++)
            {
                var along = aimPoint - muzzle; if (along.sqrMagnitude < 1e-8f) break;
                rotation = Quaternion.LookRotation(along.normalized, up) * Quaternion.Inverse(tipTurn);
                muzzle = hold - part.GrabOffsetAt(rotation) + rotation * tipAt;
            }
            return new Pose(hold - part.GrabOffsetAt(rotation), rotation);
        }

        void TickTool(float dt, in AssemblyInputFrame f)
        {
            var tool = HeldTool;
            Vector3 want = !f.pointer ? FocusPoint() : Focus.Valid && Usable(Focus) ? Focus.Position : bench.OnSurface(f.ray, .03f);
            toolTip = Vector3.Lerp(toolTip, want + bench.Up * .012f, 1 - Mathf.Exp(-S.Spring(tool.mass) * dt));
            var frame = bench.surface ? bench.surface : bench.transform;
            AssemblyVerb.PlaceTool(tool, toolTip, (-bench.Up * .8f - frame.forward * .6f).normalized);
        }

        /// Where a tool lives: its home place, or the pocket on what it is kept in (a place there that takes only it).
        static bool IsPocket(AssemblyMarker m, AssemblyPart tool) =>
            m && tool && m.kind == AssemblyMarkerKind.Place && (m.id == tool.homePlace || !string.IsNullOrEmpty(tool.parentId) && m.ownerPart == tool.parentId && m.accepts.Length == 1 && m.accepts[0] == tool.id);

        void TakeTool(AssemblyPart tool)
        {
            if (HeldTool) PutToolBack();
            HeldTool = tool; tool.place = "held"; Fx.Settle(tool);
            tool.transform.SetParent(bench.loose ? bench.loose : bench.transform, true); toolTip = tool.TipPoint;
            Audio.Play("asm.kit.tool", tool.GrabPoint);
        }
        void PutToolBack()
        {
            var tool = HeldTool; if (!tool) return;
            HeldTool = null;
            if (!string.IsNullOrEmpty(tool.homePlace)) bench.Put(tool, tool.homePlace); else bench.Put(tool, "seat");
            Audio.Play("asm.kit.tool", tool.GrabPoint, .8f);
        }

        void DropEverything()
        {
            if (verb != null) { verb.End(); verb = null; }
            if (carry != null) { carry.Return(); StopCarry(); }
            if (HeldTool) PutToolBack();
            aiming = false; var dot = aimDot; if (dot) dot.gameObject.SetActive(false); foreach (var cr in clearedForCard) if (cr) cr.forceRenderingOff = false; clearedForCard.Clear();
        }

        // ------------------------------------------------------------------ presses
        void HandlePrimary(in AssemblyInputFrame f, Vector3 eye)
        {
            if (f.primaryDown)
            {
                pressTime = clock; pressScreen = f.screen; pressPicked = false; keyTapPending = false;
                if (carry != null)
                {
                    if (aiming || pulsed) return;                                   // the click is a test pulse (also the last one)
                    if (flick != null && f.keyboard) { keyTapPending = true; return; } // a held key shakes; a tap puts down
                    PutDownOrRefuse(f);
                }
                else if (HeldTool) UseTool(f, eye);
                else PickOrEngage(f, eye);
                return;
            }
            if (!f.primaryUp || carry == null) return;
            bool tap = clock - pressTime < S.tapSeconds && (f.keyboard || (f.screen - pressScreen).magnitude < S.tapPixels);
            if (keyTapPending) { keyTapPending = false; if (tap) PutDownOrRefuse(f); return; }
            if (pressPicked) { pressPicked = false; if (!tap && !carry.Leaving) PutDownOrRefuse(f); }
        }

        void PutDownOrRefuse(in AssemblyInputFrame f)
        {
            if (carry == null) return;
            // onto a place that takes this kind of part but is not where this one goes: swapped plates, the wrong outline
            if (Focus.marker && Focus.marker.kind == AssemblyMarkerKind.Place && !(carryHasRef && carryRef.action.target == Focus.marker.id) && !Focus.marker.Accepts(HeldPart.id))
            { Refuse(HeldPart, null, null, "wrong_place"); return; }
            carry.PutDown(); StopCarry();
        }

        void PickOrEngage(in AssemblyInputFrame f, Vector3 eye)
        {
            var hit = Focus; if (!hit.Valid) return;
            // the wrong thing to pull on: it does the job, badly (the trigger lead pulled by its wire comes off frayed)
            var wrong = hit.part ? FindOpen(a => WrongFor(a, hit.part) != null) : null;
            if (wrong.HasValue)
            {
                var fd = WrongFor(wrong.Value.action, hit.part);
                Fx.Shudder(hit.part, S.shudderMm * .0008f, S.shudderSeconds); Complete(wrong.Value, .4f); RaiseFault(wrong.Value, fd.kind); return;
            }
            var act = FindOpen(a => string.IsNullOrEmpty(a.tool) && a.verb != AssemblyVerbKind.Seat && a.verb != AssemblyVerbKind.Flick && a.mode != "aim" && a.mode != "wait" && Matches(a, hit));
            if (act.HasValue) { Engage(act.Value, hit, null, f, eye); return; }
            if (hit.marker)
            {
                // a mark that wants a tool: show which
                var needs = FindOpen(a => Matches(a, hit) && !string.IsNullOrEmpty(a.tool));
                if (needs.HasValue) { Fx.Glint(bench.Tool(needs.Value.action.tool)); Audio.Play("asm.ui.glint", hit.Position, .6f); }
                return;
            }
            var p = hit.part;
            if (p.IsTool) { TakeTool(p); return; }
            if (p.IsFixture || p.IsConsumable) return;
            var clamp = bench.ClampOn(p);
            if (clamp) { Refuse(p, clamp.target ? clamp.target.GetComponentInParent<AssemblyPart>() : null, null, "blocked"); return; }
            var seat = OpenSeatFor(p, null);
            if (!seat.HasValue)
            {
                // it is this part's turn, but not for a bare hand (the core fresh from the press is lifted with pliers)
                var toolOnly = FindOpen(a => a.verb == AssemblyVerbKind.Seat && a.mode != "inspect" && a.part == p.id && !string.IsNullOrEmpty(a.tool) && a.tool != "*");
                if (toolOnly.HasValue) { Fx.Glint(bench.Tool(toolOnly.Value.action.tool)); Refuse(p, null, null, "needs_tool", bench.Tool(toolOnly.Value.action.tool)); return; }
            }
            if (Installed(p) && !seat.HasValue && FindWaiting(a => a.part == p.id) == null)
            {
                // not this part's turn: when the job wants the thing it belongs to handled, the press takes that (the pistol
                // is picked up by wherever it is grasped); otherwise the part refuses below and shows what holds it
                var whole = p;
                for (int guard = 0; guard < 8 && Carrier(whole); guard++) whole = Carrier(whole);
                if (whole && whole != p && !whole.IsFixture && !Installed(whole) && !bench.ClampOn(whole))
                {
                    var wholeSeat = OpenSeatFor(whole, null);
                    if (wholeSeat.HasValue || FindOpen(a => a.part == whole.id && (a.verb == AssemblyVerbKind.Flick || a.mode == "aim" || a.mode == "inspect")) != null) { StartCarry(whole, wholeSeat); pressPicked = true; return; }
                }
            }
            if (p.place == "seat")
            {
                if (bench.HeldInPlace(p, out var blocker, out var latch)) { Refuse(p, blocker, latch); return; }
                if (!seat.HasValue)
                {
                    var needsTool = FindOpen(a => a.part == p.id && !string.IsNullOrEmpty(a.tool));
                    if (needsTool.HasValue) { Fx.Glint(bench.Tool(needsTool.Value.action.tool)); Refuse(p, null, null, "needs_tool", bench.Tool(needsTool.Value.action.tool)); return; }
                    if (p.parentId != "" && bench.Part(p.parentId)) { Refuse(p, null, null, "not_yet"); return; }   // not its turn: it stays where it is
                }
            }
            else if (Installed(p) && !seat.HasValue && FindOpen(a => a.part == p.id) == null) { Refuse(p, null, null, "not_yet"); return; }   // fitted to something and not its turn
            StartCarry(p, seat); pressPicked = true;
        }

        /// A part that will not move: it shudders, and what holds it glints.
        /// A press the bench turned down, for the tutor's captions (21 Nov): kind is blocked (other = what holds it), not_yet,
        /// needs_tool (other = the tool to take), wrong_tool (other = the tool in the hand) or wrong_place.
        public event Action<string, AssemblyPart, AssemblyPart> Refused;
        /// The tutor's plain instruction for an action that has no `line` of its own (null or empty: no line).
        public Func<AssemblyActionRef, string> LineFor;
        void Refuse(AssemblyPart p, AssemblyPart blocker, AssemblyParam latch = null, string kind = null, AssemblyPart other = null)
        {
            var latchOwner = latch ? (latch.target ? latch.target.GetComponentInParent<AssemblyPart>() : bench.Part(latch.id)) : null;
            try { Refused?.Invoke(blocker || latch ? "blocked" : kind ?? "not_yet", p, blocker ? blocker : latchOwner ? latchOwner : other); } catch (Exception e) { Debug.LogException(e); }
            Fx.Shudder(p, S.shudderMm * .001f, S.shudderSeconds);
            if (blocker) Fx.Glint(blocker);
            if (latch) { Audio.Play("asm.latch.stuck", p.GrabPoint); var owner = latch.target ? latch.target.GetComponentInParent<AssemblyPart>() : bench.Part(latch.id); if (owner) Fx.Glint(owner); }
            else Audio.Play("asm.seat.blocked", p.GrabPoint, .7f);
            Refusals++;
        }
        public int Refusals { get; private set; }

        void UseTool(in AssemblyInputFrame f, Vector3 eye)
        {
            var hit = Focus; var tool = HeldTool; if (!hit.Valid) return;
            if (hit.marker && IsPocket(hit.marker, tool)) { PutToolBack(); return; }
            // the tool itself is stood on the work (the punch on the pin)
            var stand = FindOpen(a => a.verb == AssemblyVerbKind.Seat && a.part == tool.id && Matches(a, hit));
            if (stand.HasValue) { HeldTool = null; StartCarry(tool, stand); pressPicked = false; return; }
            var act = FindOpen(a => ToolFits(a.tool, tool) && a.verb != AssemblyVerbKind.Flick && a.mode != "wait" && a.mode != "aim" && WrongFor(a, hit.part) == null && Matches(a, hit));
            if (!act.HasValue)
            {
                // forcing something that is not ready (the seized screw before oil and taps)
                var waiting = FindWaiting(a => ToolFits(a.tool, tool) && Matches(a, hit) && Array.Exists(a.faults, x => x.when == "blocked")) ?? FindWaiting(a => ToolFits(a.tool, tool) && Matches(a, hit));
                if (waiting.HasValue)
                {
                    var fd = Array.Find(waiting.Value.action.faults, x => x.when == "blocked");
                    if (hit.part) Fx.Shudder(hit.part, S.shudderMm * .0006f, S.shudderSeconds);
                    if (fd != null) RaiseFault(waiting.Value, fd.kind); else Audio.Play("asm.seat.blocked", hit.Position, .7f);
                    return;
                }
                var other = FindOpen(a => Matches(a, hit) && !string.IsNullOrEmpty(a.tool));
                if (other.HasValue) { Fx.Glint(bench.Tool(other.Value.action.tool)); Audio.Play("asm.seat.blocked", hit.Position, .5f); try { Refused?.Invoke("wrong_tool", hit.part, HeldTool); } catch (Exception e) { Debug.LogException(e); } }
                else if (hit.part && hit.part.IsTool) TakeTool(hit.part);
                return;
            }
            var a = act.Value.action;
            if (!string.IsNullOrEmpty(a.toolMode) && tool.Mode != a.toolMode)
            {
                var fd = Array.Find(a.faults, x => x.when == "mode");
                AssemblyVerb.PlaceTool(tool, hit.Position, -bench.Up);
                if (hit.part) Fx.Shudder(hit.part, S.shudderMm * .0005f, S.shudderSeconds);
                RaiseFault(act.Value, fd != null ? fd.kind : "camout");
                return;
            }
            if (a.verb == AssemblyVerbKind.Seat)
            {
                var p = bench.Part(a.part); if (!p) return;
                if (hit.part != p) return;
                if (bench.HeldInPlace(p, out var blocker, out var latch)) { Refuse(p, blocker, latch); return; }
                StartCarry(p, act); pressPicked = true; return;
            }
            Engage(act.Value, hit, tool, f, eye);
        }

        void HandleOther(in AssemblyInputFrame f)
        {
            if (f.putBack)
            {
                if (carry != null) { carry.Return(); StopCarry(); }
                else if (HeldTool) PutToolBack();
            }
            if (f.flip && carry == null && HeldTool)
            {
                // the quick swap: the bit in the tool changes places with the one in the block (or the tool's own modes cycle)
                var bit = HeldTool.SeatedBit; AssemblyPart other = null;
                if (bit) foreach (var p in bench.Parts) if (p.IsBit && p != bit && p.gameObject.activeInHierarchy && p.BitKind != bit.BitKind) { other = p; break; }
                if (bit && other) { bench.Swap(bit, other); Audio.Play("asm.kit.tool", HeldTool.GrabPoint, .7f); }
                else if (HeldTool.modes.Length > 1) { HeldTool.modeIndex++; Audio.Play("asm.kit.tool", HeldTool.GrabPoint, .7f); }
            }
        }

        // ------------------------------------------------------------------ engaged verbs
        void Engage(AssemblyActionRef r, AssemblyHit hit, AssemblyPart tool, in AssemblyInputFrame f, Vector3 eye)
        {
            var a = r.action;
            var marker = hit.marker && (a.target == hit.marker.id || Array.IndexOf(a.targets, hit.marker.id) >= 0) ? hit.marker : bench.Marker(a.target);
            if (a.verb == AssemblyVerbKind.Point && a.targets.Length > 0 && marksHit.TryGetValue(r.Id, out var hitSet) && marker && hitSet.Contains(marker.id)) return;
            verb = AssemblyVerb.Create(a.verb); verbRef = r;
            verb.c = Context(r, bench.Part(a.part), tool, marker);
            Feed(verb.c, f, eye); verb.Begin(); idle = Mathf.Min(idle, S.hintGlint * .5f);
            TickVerb(0, f, eye);
        }

        void TickVerb(float dt, in AssemblyInputFrame f, Vector3 eye)
        {
            Feed(verb.c, f, eye);
            var st = verb.Tick(dt, f); VerbStatus = st;
            var r = verbRef; var a = r.action;
            if (st.carry > 0) partial[r.Id] = st.carry;
            if (st.fault != null) RaiseFault(r, st.fault);
            if (verb == null) return;
            if (st.done)
            {
                var done = verb; EndVerb();
                if (a.verb == AssemblyVerbKind.Point && a.targets.Length > 1 && done.c.marker)
                {
                    // one mark of several: the action is done when each has been hit
                    if (!marksHit.TryGetValue(r.Id, out var set)) { marksHit[r.Id] = set = new HashSet<string>(); marks[r.Id] = new List<float>(); }
                    if (set.Add(done.c.marker.id)) marks[r.Id].Add(st.precision);
                    foreach (var e in a.effects) if (e.StartsWith("@" + done.c.marker.id + ":") || e.StartsWith(done.c.marker.ownerPart + ">")) bench.ApplyEffect(e);
                    idle = 0; hintLevel = 0;
                    if (set.Count < a.targets.Length) return;
                    Complete(r, marks[r.Id].Average()); return;
                }
                bool rides = a.verb == AssemblyVerbKind.Turn && a.turns < 0 && done.c.part && done.c.part.IsFastener;
                Complete(r, st.precision);
                // a screw that has come out rides the bit to wherever it is put
                if (rides && State == Phase.Working && HeldTool) { var seat = OpenSeatFor(done.c.part, HeldTool); if (seat.HasValue) { StartCarry(done.c.part, seat); pressPicked = false; } }
                return;
            }
            if (st.ended) { EndVerb(); return; }
            if (st.waiting && (f.putBack || f.primaryDown && !(Focus.Valid && Matches(a, Focus)))) EndVerb();
        }
        void EndVerb() { if (verb == null) return; verb.End(); verb = null; VerbStatus = default; }

        // ------------------------------------------------------------------ progress, faults, the end
        void Complete(AssemblyActionRef r, float precision)
        {
            int stageBefore = Job.StageIndex;
            if (Job.Blocked(r.step.id, r.action.key) != null) return;
            // work that shows what an earlier step left undone: it fails here instead of finishing (the rotor grinds, the
            // tester's lamp stays dark, the damper keeps swinging), and its recovery puts it right
            foreach (var fd in r.action.faults)
            {
                if (fd.when == null || !fd.when.StartsWith("poor:")) continue;
                bool mended = !string.IsNullOrEmpty(fd.recovery) ? Job.IsDone(fd.recovery) : Job.FaultsOn(r.step.id, fd.kind) > 0;
                if (mended || Job.StepPrecision(fd.when.Substring(5)) >= S.poorPrecision) continue;
                partial.Remove(r.Id); marks.Remove(r.Id); marksHit.Remove(r.Id);
                RaiseFault(r, fd.kind); return;
            }
            var prog = Job.CompleteAction(r.step.id, r.action.key, precision);
            if (!prog.ok) return;
            bench.ApplyAction(r.action);
            partial.Remove(r.Id); marks.Remove(r.Id); marksHit.Remove(r.Id); idle = 0; hintLevel = 0; pinnedShot = null; Hud?.HideLegend();
            if (r.action.verb != AssemblyVerbKind.Seat && !string.IsNullOrEmpty(r.action.done)) Audio.Play(r.action.done, bench.Part(r.action.part) ? bench.Part(r.action.part).GrabPoint : bench.SurfacePoint);
            Link.Blob = Job.ToBlob();
            ActionDone?.Invoke(r.step.id, r.action.key);
            if (prog.stepDone)
            {
                foreach (var e in r.step.effects) bench.ApplyEffect(e);
                if (!Voice.Say($"step.done:{r.step.id}:{Job.Quality}")) Voice.Say("step.done:" + r.step.id);
            }
            if (prog.stageDone)
            {
                Audio.Play("asm.ui.stage", bench.SurfacePoint);
                if (!prog.jobDone) { ReportStage(); Voice.Say("stage.start:" + Job.StageIndex); }
            }
            foreach (var id in prog.unlocked) Voice.Say("step.start:" + id);
            if (prog.jobDone) { Finish(); return; }
            RefreshWatchers();
        }

        static readonly Dictionary<string, string> FaultSounds = new Dictionary<string, string>
        {
            { "camout", "asm.screw.camout" }, { "slip", "asm.screw.camout" }, { "stripped", "asm.screw.strip" }, { "rounded", "asm.screw.strip" }, { "overtight", "asm.vise.creak" },
            { "miss", "asm.tap.miss" }, { "flew_off", "asm.part.spring_jump" }, { "rolled_off", "asm.part.floor" }, { "tear", "asm.peel.tear" }, { "frayed", "asm.part.connector" },
            { "cold_joint", "asm.solder.cold" }, { "short_lead", "asm.cut.snip" }, { "over_bend", "asm.bend.crack" },
            { "grind", "asm.spin.grind" }, { "pinched", "asm.damper.tick" }, { "snapped", "asm.pry.break" }, { "wire_snapped", "asm.wind.snap" }, { "scorched", "asm.solder.scorch" },
            { "nicked", "asm.strip.squeeze" }, { "past_line", "asm.file.stroke" }, { "over_pour", "asm.press.pour" }, { "void", "asm.press.hiss" }, { "loose_pocket", "asm.file.round" },
            { "cracked_lug", "asm.pry.break" }, { "soft_seam", "asm.cure.switch" }, { "bind", "asm.drill.bind" }, { "short_leg", "asm.cut.snip" }, { "spill", "asm.oil.wipe" },
            { "off_centre", "asm.punch.dimple" }, { "upside_down", "asm.seat.blocked" }, { "proud", "asm.tap.miss" }, { "bent_pin", "asm.tap.miss" },
        };
        void RaiseFault(AssemblyActionRef r, string kind)
        {
            var result = Job.Fault(r.step.id, r.action.key, kind);
            if (!result.ok) return;
            idle = 0; hintLevel = 0;
            var p = bench.Part(r.action.part);
            Audio.Play(FaultSounds.TryGetValue(kind, out var sound) ? sound : "asm.seat.blocked", p ? p.GrabPoint : bench.SurfacePoint);
            if (result.recoveryStarted != null && result.def != null) foreach (var e in result.def.effects) bench.ApplyEffect(e);
            bool said = result.count == 1 && Voice.Say("step.fault_first:" + r.step.id);
            if (!said && result.first) said = Voice.Say("fault.first:" + kind);
            if (!said) Voice.Say("step.fault:" + r.step.id);
            Link.Blob = Job.ToBlob();
            Faulted?.Invoke(r.step.id, kind);
        }

        void Finish()
        {
            State = Phase.Completing;
            DropEverything();
            HandOver();
            if (session) session.Close(); else Shut(false);
        }
        /// The job is complete: the crafting system consumes the inputs, grants and fits the grip at its quality.
        void HandOver()
        {
            var result = new AssemblyResult { recipeId = Recipe.craftRecipeId, quality = Job.Quality, score = Job.Score, faults = Job.Faults, seconds = Job.Seconds, byproducts = Recipe.byproducts.Select(b => new ItemStack(b.itemId, b.quantity)).ToArray() };
            LastResult = result;
            Audio.Play("asm.ui.job", bench.SurfacePoint);
            bool ok = Link.Complete(result, out string reason);
            if (!ok) Note(Detached ? $"Bench job finished ({result.quality}, score {result.score:0.00}). Detached QA job: nothing was granted." : "The bench job is finished, but the grip could not be handed over: " + reason);
            Link.Blob = null;
        }
        public AssemblyResult LastResult { get; private set; }

        // ------------------------------------------------------------------ hints (DESIGN.md section 8)
        AssemblyActionRef? NextAction()
        {
            // what is in the hand says what comes next (the sheet that was picked up, not the one the table lists first)
            if (HeldPart) { var mine = FindOpen(a => a.part == HeldPart.id && (a.verb == AssemblyVerbKind.Seat || a.verb == AssemblyVerbKind.Flick || a.mode == "aim") && ToolFits(a.tool, HeldTool)); if (mine.HasValue) return mine; }
            AssemblyActionRef? first = null;
            foreach (var r in Open())
            {
                if (Job.State(r.step.id) == AssemblyStepState.Active && !r.step.optional) return r;
                if (!first.HasValue && !r.step.optional) first = r;
            }
            return first ?? Open().Cast<AssemblyActionRef?>().FirstOrDefault();
        }
        /// What a hint points at: the next thing the job needs. Steps that may be skipped (a shake, a look over) are never
        /// hinted, so with the pistol in the hand the glint is where it has to go, not what else could be done with it.
        public AssemblyActionRef? HintAction()
        {
            if (Job == null) return null;
            if (HeldPart)
            {
                var mine = FindOpenRef(r => !r.step.optional && r.action.part == HeldPart.id && (r.action.verb == AssemblyVerbKind.Seat || r.action.verb == AssemblyVerbKind.Flick || r.action.mode == "aim") && ToolFits(r.action.tool, HeldTool));
                if (mine.HasValue) return mine;
            }
            AssemblyActionRef? first = null;
            foreach (var r in Open())
            {
                if (r.step.optional) continue;
                if (Job.State(r.step.id) == AssemblyStepState.Active) return r;
                if (!first.HasValue) first = r;
            }
            return first;
        }
        AssemblyActionRef? FindOpenRef(Func<AssemblyActionRef, bool> test) { foreach (var r in Open()) if (test(r)) return r; return null; }
        void Hints(float dt, in AssemblyInputFrame f)
        {
            if (verb != null && !VerbStatus.waiting) { idle = 0; return; }
            if (f.hint) { Hint(3); Hud?.ShowLegend(6); return; }
            if (hintLevel < 1 && idle >= S.hintGlint) Hint(1);
            else if (hintLevel < 2 && idle >= S.hintVoice) Hint(2);
            else if (hintLevel < 3 && idle >= S.hintGhost) { Hint(3); idle = 0; hintLevel = 0; }
        }
        /// 1: the next useful thing glints. 2: Brann says a short line. 3: a ghost of the part at its socket, or the path.
        public void Hint(int level)
        {
            var next = HintAction(); if (!next.HasValue) return;
            var a = next.Value.action; var part = bench.Part(a.part); var tool = string.IsNullOrEmpty(a.tool) ? null : bench.Tool(a.tool);
            hintLevel = Mathf.Max(hintLevel, level);
            if (level == 1)
            {
                Fx.Glint(tool && tool != HeldTool ? tool : part && part != HeldPart ? part : bench.Part(bench.Marker(a.target) ? bench.Marker(a.target).ownerPart : a.part));
                Audio.Play("asm.ui.glint", part ? part.GrabPoint : bench.SurfacePoint, .6f);
            }
            else if (level == 2) { Voice.Say("hint.idle25:" + "abc"[hintVoice++ % 3]); }
            else
            {
                if (a.verb == AssemblyVerbKind.Seat && part && bench.TargetPose(part, a.target, out _, out var seated, out _, out _)) Fx.Ghost(part, seated, S.ghostSeconds);
                else
                {
                    var marker = bench.Marker(a.targets.Length > 0 ? a.targets[0] : a.target); var points = new List<Vector3>();
                    if (marker && marker.kind == AssemblyMarkerKind.Path) { foreach (var t in marker.points) if (t) points.Add(t.position); }
                    else
                    {
                        var from = tool ? tool.GrabPoint : part ? part.GrabPoint + bench.Up * .08f : bench.SurfacePoint; var to = marker ? marker.transform.position : part ? part.GrabPoint : from;
                        for (int i = 0; i <= 8; i++) points.Add(Vector3.Lerp(from, to, i / 8f) + bench.Up * (Mathf.Sin(i / 8f * Mathf.PI) * .04f));
                    }
                    Fx.Path(points, S.ghostSeconds, a.part + ">" + a.target);
                    if (tool && tool != HeldTool) Fx.Glint(tool);
                }
            }
        }

        // ------------------------------------------------------------------ camera and cards
        /// The shot the work in hand wants (the camera goes there; the bot looks from there).
        public string WantedShotName => Job != null ? WantedShot() : "work";
        string WantedShot()
        {
            // work in progress keeps the shot it began in
            if (verb != null) return !string.IsNullOrEmpty(shotNow) ? shotNow : "work";
            if (aiming && !string.IsNullOrEmpty(aimRef.action.shot)) return aimRef.action.shot;
            var next = NextAction();
            if (!next.HasValue) { var stage = Job != null ? Job.Stage : null; return stage != null && !string.IsNullOrEmpty(stage.shot) ? stage.shot : "work"; }
            return ShotFor(next.Value, HeldTool, HeldPart);
        }
        /// The shot an action is worked from with a given hand: its own, its step's or its stage's, unless that does not show
        /// what the hand needs next (the tool still to be taken, the part still to be picked up, where the work is done); then
        /// the work surface, then the whole bench. The camera and the sight check (AssemblySightCheck) ask the same question.
        public string ShotFor(AssemblyActionRef r, AssemblyPart heldTool, AssemblyPart heldPart)
        {
            var stage = Job != null ? Job.Stage : null; string fallback = stage != null && !string.IsNullOrEmpty(stage.shot) ? stage.shot : "work";
            var a = r.action; string preferred = !string.IsNullOrEmpty(a.shot) ? a.shot : !string.IsNullOrEmpty(r.step.shot) ? r.step.shot : fallback;
            see.Clear();
            if (!string.IsNullOrEmpty(a.tool) && a.tool != "*" && !ToolFits(a.tool, heldTool))
            {
                var tool = bench.Tool(a.tool);
                // (21 Nov) a tool to be taken from the open toolkit: the hand goes to it in the shot over the roll, whatever the work
                // shot shows (a tool tucked in its pocket can sit behind the canvas from the side); back to the work once it is in hand
                if (tool && tool.gameObject.activeInHierarchy && tool.parentId == "tools.roll" && (tool.OnParent || (tool.place ?? "").StartsWith("place.rest.")) && ShotCamera("roll") && Sees(ShotCamera("roll"), tool.GrabPoint)) return "roll";
                if (tool && tool.gameObject.activeInHierarchy) see.Add(tool.GrabPoint);
            }
            var p = bench.Part(a.part);
            // the same for a tool that is itself set somewhere (the punch stood on the pin): taken from the roll in the roll shot
            if (p && p.IsTool && p != heldTool && p != heldPart && p.parentId == "tools.roll" && (p.OnParent || (p.place ?? "").StartsWith("place.rest.")) && ShotCamera("roll") && Sees(ShotCamera("roll"), p.GrabPoint)) return "roll";
            if (p && !p.Gone && p != heldPart && p != heldTool && p.gameObject.activeInHierarchy && (a.verb == AssemblyVerbKind.Seat || a.verb == AssemblyVerbKind.Flick || a.mode == "aim")) see.Add(p.GrabPoint);
            see.Add(ActPointFor(r, heldTool, heldPart));
            foreach (var name in new[] { preferred, "work", "wide" }) { var cam = ShotCamera(name); if (cam && see.TrueForAll(point => Sees(cam, point))) return name; }
            return ShotCamera("wide") ? "wide" : preferred;
        }
        readonly List<Vector3> see = new List<Vector3>();
        public Camera ShotCamera(string name) { var t = bench.cameraRoot ? bench.cameraRoot.Find("cam_bench_" + name) : null; return t ? t.GetComponent<Camera>() : null; }
        /// Is a point inside a shot's picture, with a little to spare, and clear of the bench's own interface (16:9 unless
        /// the live lens says otherwise)?
        bool Sees(Camera cam, Vector3 world)
        {
            var l = cam.transform.InverseTransformPoint(world); if (l.z < .05f) return false;
            float tv = Mathf.Tan(cam.fieldOfView * .5f * Mathf.Deg2Rad), aspect = Rig != null && Rig.Lens ? Rig.Lens.aspect : 16f / 9f;
            if (Mathf.Abs(l.x) > l.z * tv * aspect * .93f || Mathf.Abs(l.y) > l.z * tv * .9f) return false;
            return AssemblyHud.CoveredBy(new Vector2((l.x / (l.z * tv * aspect) * .5f + .5f) * AssemblyHud.Reference.x, (.5f - l.y / (l.z * tv) * .5f) * AssemblyHud.Reference.y)) == null;
        }
        Vector3 FocusOfWork()
        {
            if (verb != null) return verb.ActPoint;
            if (HeldPart) return HeldPart.GrabPoint;
            if (HeldTool) return HeldTool.TipPoint;
            var next = NextAction(); if (!next.HasValue) return bench.SurfacePoint;
            var p = bench.Part(next.Value.action.part); return p && !p.Gone ? p.GrabPoint : bench.SurfacePoint;
        }

        /// A pulse through the card: one of the decals on the card's centre mark moves to the hole, and the job remembers where
        /// (in the mark's own plane, so the holes stay with the card wherever it goes).
        void AddHole(AssemblyActionRef r, Vector3 world)
        {
            var card = bench.Marker(r.action.target); if (!card) return;
            var local = card.transform.InverseTransformPoint(world);
            string key = "card:" + r.step.id; Job.Notes.TryGetValue(key, out var text);
            Job.Notes[key] = (string.IsNullOrEmpty(text) ? "" : text + ";") + FormattableString.Invariant($"{local.x:0.####},{local.y:0.####}");
            RestoreCards();
        }
        /// Shows the holes of every card the job has shot at (cards are the parts lying on the notes' target places).
        void RestoreCards()
        {
            foreach (var step in Recipe.Steps) foreach (var a in step.actions)
            {
                if (a.mode != "aim") continue;
                var target = bench.Marker(a.target); if (!target) continue;
                Job.Notes.TryGetValue("card:" + step.id, out var text); var holes = string.IsNullOrEmpty(text) ? new string[0] : text.Split(';');
                // the decals are on the card's centre mark; a bench built before 20 Nov 18:00 has them on the card named by the action's effect
                var holder = target.transform;
                if (!holder.Find("decal_0")) foreach (var e in a.effects) { int at = e.IndexOf('>'); var cp = at > 0 ? bench.Part(e.Substring(0, at)) : null; if (cp && cp.transform.Find("decal_0")) { holder = cp.transform; break; } }
                for (int i = 0; ; i++)
                {
                    var decal = holder.Find("decal_" + i); if (!decal) break;
                    bool on = i < holes.Length; decal.gameObject.SetActive(on); if (!on) continue;
                    var xy = holes[i].Split(',');
                    if (xy.Length == 2 && float.TryParse(xy[0], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float x) && float.TryParse(xy[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float y))
                        decal.localPosition = new Vector3(x, y, decal.localPosition.z);
                }
            }
        }

        // ------------------------------------------------------------------ QA and tests
        /// Completes an open action as if it had been done by hand (QA): effects, sounds, lines and the save all follow.
        public bool DevComplete(string stepId, string key, float precision)
        {
            if (State != Phase.Working || Job == null) return false;
            var step = Job.Step(stepId); if (step == null) return false;
            bool any = false;
            foreach (var a in step.actions)
            {
                if (!string.IsNullOrEmpty(key) && a.key != key) continue;
                if (State != Phase.Working || Job.Blocked(stepId, a.key) != null) continue;
                DropEverything(); Complete(new AssemblyActionRef { step = step, action = a }, precision); any = true;
            }
            return any;
        }
        public bool DevFault(string stepId, string kind)
        {
            if (State != Phase.Working || Job == null) return false;
            var step = Job.Step(stepId); if (step == null || step.actions.Length == 0) return false;
            var action = step.actions.FirstOrDefault(a => a.faults.Any(x => x.kind == kind)) ?? step.actions[0];
            RaiseFault(new AssemblyActionRef { step = step, action = action }, kind); return true;
        }
        /// The slice: every step of the named stages done at one precision, as if the grip had been made.
        public int DevGrant(IEnumerable<string> stageIds, float precision)
        {
            if (State != Phase.Working || Job == null) return 0;
            DropEverything();
            int before = Job.StageIndex;
            var granted = Job.Grant(stageIds, precision);
            bench.Rebuild(Job); RestoreCards(); Link.Blob = Job.ToBlob();
            if (Job.Complete) { Finish(); return granted.Count; }
            if (Job.StageIndex != before) { ReportStage(); Voice.Say("stage.start:" + Job.StageIndex); }
            RefreshWatchers();
            return granted.Count;
        }
        /// Finishes the whole job at a score (every remaining step done at that precision).
        public bool DevFinish(float score)
        {
            if (State != Phase.Working || Job == null) return false;
            DropEverything();
            foreach (var step in Recipe.Steps) if (!step.recovery && !Job.IsDone(step.id)) Job.CompleteStep(step.id, score, true);
            bench.Rebuild(Job);
            if (Job.Complete) Finish();
            return State != Phase.Working;
        }
        /// QA: holds a shot by name until an action is finished or it is released with "auto" (a look at every shot per run).
        public bool DevShot(string shot)
        {
            if (Rig == null || !Rig.Active) return false;
            if (string.IsNullOrEmpty(shot) || shot == "auto") { pinnedShot = null; return true; }
            bool ok = Rig.SetShot(shot, true); if (ok) { shotNow = shot; pinnedShot = shot; } return ok;
        }
        string pinnedShot;
        public string PinnedShot => pinnedShot;
        public IEnumerable<string> ShotNames { get { if (bench.cameraRoot) foreach (Transform t in bench.cameraRoot) if (t.name.StartsWith("cam_bench_")) yield return t.name.Substring(10); } }
        public string ShotNow => shotNow;
        public bool Aiming => aiming;
        public bool CarryLeaving => carry != null && carry.Leaving;
        public float CarryDistanceMm => carry != null ? carry.DistanceMm : -1;
        public float CarryYawError => carry != null ? carry.YawError : 0;
        public AssemblyActionRef? CarryAction => carryHasRef ? carryRef : (AssemblyActionRef?)null;
        public AssemblyActionRef? VerbAction => verb != null ? verbRef : (AssemblyActionRef?)null;
        public AssemblyActionRef? Next => State == Phase.Working ? NextAction() : null;
        public float Partial(string actionId) => partial.TryGetValue(actionId, out float v) ? v : 0;
        public Vector3 ActPoint(AssemblyActionRef r) => ActPointFor(r, HeldTool, HeldPart);
        /// Where the hand works for an action, given what it holds.
        public Vector3 ActPointFor(AssemblyActionRef r, AssemblyPart heldTool, AssemblyPart heldPart)
        {
            var a = r.action; var p = bench.Part(a.part);
            // a carried part: where the hand must be for it to go in (its grab point at the way in); a tool to stand: the place
            if (a.verb == AssemblyVerbKind.Seat && a.mode != "inspect" && p && heldPart == p && bench.TargetPose(p, a.target, out _, out _, out var approach, out _)) return approach.position + p.GrabOffsetAt(approach.rotation);
            if (a.verb == AssemblyVerbKind.Seat && p && a.part == (heldTool ? heldTool.id : "") && bench.TargetPose(p, a.target, out _, out var stood, out _, out _)) return stood.position;
            if (a.verb == AssemblyVerbKind.Seat || a.verb == AssemblyVerbKind.Flick || a.verb == AssemblyVerbKind.Turn) return p ? p.GrabPoint : bench.SurfacePoint;
            if (a.verb == AssemblyVerbKind.Point && a.mode == "aim" && heldPart != p) return p ? p.GrabPoint : bench.SurfacePoint;
            string id = a.target;
            if (a.targets.Length > 0) { marksHit.TryGetValue(r.Id, out var set); id = a.targets.FirstOrDefault(t => set == null || !set.Contains(t)) ?? a.targets[0]; }
            var m = bench.Marker(id); if (m) return m.kind == AssemblyMarkerKind.Path && m.points.Length > 0 && m.points[0] ? m.points[0].position : m.transform.position;
            var tp = bench.Part(id); return tp ? tp.GrabPoint : p ? p.GrabPoint : bench.SurfacePoint;
        }
    }
}
