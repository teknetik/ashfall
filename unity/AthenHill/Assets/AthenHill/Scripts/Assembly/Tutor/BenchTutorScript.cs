using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
    /// What Brann says to walk the player through the first hand-made job, and when (tutor agent, 21 Nov 2026). Pure C#, no
    /// scene: BenchTutor feeds it from the bench session and speaks what it offers; Edit Mode tests feed it by hand.
    ///
    /// - When a step becomes the next useful thing (the session's HintAction) its line is offered, and one extra line for a
    ///   repeated action inside the row when that action is next. Stages 0 to 4 (`voicedStages`) only; stages 0 and 1 have
    ///   the full lines and 2 to 4 shorter ones (the text decides that, not this class).
    /// - The first time each teach key (input archetype, Point and Window in two forms) is next: its "how" line, the on-screen
    ///   prompt (Prompt) until an action of that kind has been done once, and the ghost at once (TakeGhost).
    /// - A recovery step that becomes next: its line, in every stage up to `lastGuidedStage`.
    /// - A stall (idle past `stallSeconds`, or `quietStallSeconds` in the quiet stages 5 and 6) repeats the step's line once
    ///   per sitting; a mistake in a quiet stage does too. Stage 7 is left to Brann's existing lines.
    /// - It never interrupts: the host asks for a line only while Brann is silent with nothing of the bench's queued, so the
    ///   bench's fault and stage lines always win. A fault drops the tutor's queued step lines.
    /// - Save()/Load(): what was said and which kinds of action have been done, kept in the job's notes so a job resumed
    ///   after leaving does not repeat itself. Reminders are not kept.
    public sealed class BenchTutorScript
    {
        [Serializable] public class Tuning
        {
            [Tooltip("Step lines are offered in stages up to this index (0-4); later stages speak only on a stall or a mistake.")] public int voicedStages = 4;
            [Tooltip("Nothing at all past this stage (stage 7 keeps Brann's existing lines).")] public int lastGuidedStage = 6;
            [Tooltip("Idle seconds before the step's line is said again (stages 0-4), once per step and sitting.")] public float stallSeconds = 20;
            [Tooltip("Idle seconds before a quiet stage (5, 6) speaks the step's line.")] public float quietStallSeconds = 15;
            [Tooltip("The next thing must stay the same this long before its line starts (a quick player is not talked over).")] public float settleSeconds = .6f;
            [Tooltip("Silence after Brann stops before the tutor speaks.")] public float gapSeconds = .5f;
            [Tooltip("At most this many lines waiting.")] public int maxPending = 4;
            [Tooltip("Steps whose line (and the how-line after it) starts the moment Brann is silent, without the settle and the gap: the camera moves on the next click there (Carl's playtest, 21 Nov: s0.card_before).")] public string[] urgentSteps = { "s0.card_before" };
            [Tooltip("How-lines that start at once in the same way.")] public string[] urgentTeach = { "point_aim" };
            [Tooltip("Steps whose line stays as a caption until the job notes record a result (BenchTutor: the first pulse through the card).")] public string[] holdCaptionSteps = { "s0.card_before" };
        }
        public enum Kind { Welcome = 0, Recovery = 1, Step = 2, Action = 3, Verb = 4 }
        /// The next useful action as the tutor sees it.
        public struct Next
        {
            public int stage; public string step, key, teach; public bool recovery, optional;
            public bool Valid => !string.IsNullOrEmpty(step);
            public bool Same(Next o) => step == o.step && key == o.key && teach == o.teach && stage == o.stage;
        }
        sealed class Pending { public string trigger, step, key, teach; public Kind kind; public bool reminder, urgent; }

        public readonly Tuning tuning;
        readonly Func<string, bool> has;
        readonly HashSet<string> said = new HashSet<string>(), done = new HashSet<string>(), reminded = new HashSet<string>(), ghosted = new HashSet<string>();
        readonly List<Pending> pending = new List<Pending>();
        Next next; float stable, quiet; bool ghost, enabled = true;
        /// Every trigger the host has spoken, in order (tests, QA).
        public readonly List<string> Log = new List<string>();

        /// has: does a line exist for this trigger (lines without one are never offered).
        public BenchTutorScript(Func<string, bool> has, Tuning tuning = null) { this.has = has ?? (_ => true); this.tuning = tuning ?? new Tuning(); }

        /// The job is guided (the first hand-made job). Off for a later hand-made job; Auto-assemble never opens the bench.
        public bool Guided { get; private set; }
        public bool On => Guided && enabled;
        public Next Current => next;
        public IEnumerable<string> Said => said;
        public IEnumerable<string> Done => done;
        public IEnumerable<string> Waiting => pending.Select(p => p.trigger);
        /// The teach key whose on-screen prompt shows now, or null.
        public string Prompt => On && next.Valid && !string.IsNullOrEmpty(next.teach) && next.stage <= tuning.lastGuidedStage && !done.Contains(next.teach) ? next.teach : null;

        /// Starts a sitting. persisted: the job's tutor note (Save()); resumed: the job had been worked before.
        public void Begin(bool guided, string persisted, bool resumed)
        {
            said.Clear(); done.Clear(); reminded.Clear(); ghosted.Clear(); pending.Clear(); Log.Clear();
            next = default; stable = quiet = 0; ghost = false;
            Guided = guided; Load(persisted);
            if (On && !resumed && !said.Contains("tutor.welcome")) Enqueue("tutor.welcome", Kind.Welcome, null, null, null, false);
        }
        /// The Settings switch ("Brann's guidance"). Off drops everything waiting and hides the prompt; on picks up again.
        public void SetEnabled(bool on)
        {
            if (enabled == on) return;
            enabled = on; pending.Clear();
            if (on) { var n = next; next = default; Observe(n); }
        }

        /// Called every frame with the session's next useful action (default when there is none).
        public void Observe(Next n)
        {
            if (n.Same(next)) return;
            next = n; stable = 0;
            pending.RemoveAll(Stale);
            if (!On || !n.Valid || n.stage > tuning.lastGuidedStage) return;
            if (n.recovery) Enqueue("tutor.recovery:" + n.step, Kind.Recovery, n.step, null, null, false);
            else if (n.stage <= tuning.voicedStages)
            {
                Enqueue("tutor.step:" + n.step, Kind.Step, n.step, null, null, false);
                Enqueue("tutor.action:" + n.step + ":" + n.key, Kind.Action, n.step, n.key, null, false);
            }
            if (!string.IsNullOrEmpty(n.teach) && !done.Contains(n.teach))
            {
                Enqueue("tutor.verb:" + n.teach, Kind.Verb, null, null, n.teach, false);
                if (ghosted.Add(n.teach)) ghost = true;
            }
        }
        /// The host shows the ghost of the part or the tool's path now (once per teach key and sitting). True once per request.
        public bool TakeGhost() { bool g = ghost; ghost = false; return g; }

        /// An action of this teach key has been done: its prompt goes and its how-line is no longer needed.
        public void ActionDone(string teach)
        {
            if (string.IsNullOrEmpty(teach) || !done.Add(teach)) return;
            pending.RemoveAll(p => p.kind == Kind.Verb && p.teach == teach);
        }
        /// A mistake: Brann's own fault line speaks, so the tutor's waiting step lines go. In the quiet stages (past
        /// voicedStages) the step's line is said once, unless a recovery step takes over (its own line).
        public void Fault(string stepId, int stage)
        {
            pending.RemoveAll(p => p.kind == Kind.Step || p.kind == Kind.Action);
            quiet = 0;
            if (On && stage > tuning.voicedStages && stage <= tuning.lastGuidedStage && !string.IsNullOrEmpty(stepId) && reminded.Add(stepId))
                Enqueue("tutor.step:" + stepId, Kind.Step, stepId, null, null, true);
        }
        /// Seconds since the player last made progress (the session's Idle).
        public void Idle(float seconds)
        {
            if (!On || !next.Valid || next.stage > tuning.lastGuidedStage || reminded.Contains(next.step)) return;
            float wait = next.stage <= tuning.voicedStages ? tuning.stallSeconds : tuning.quietStallSeconds;
            if (seconds < wait) return;
            reminded.Add(next.step);
            Enqueue(next.recovery ? "tutor.recovery:" + next.step : "tutor.step:" + next.step, next.recovery ? Kind.Recovery : Kind.Step, next.step, null, null, true);
        }

        /// H (Carl, 21 Nov: "H always repeats the current instruction"): the step's (or recovery's) line again, and the how-line
        /// while that kind of action has not been done, in any stage that has one, at once. False when there is nothing to say.
        public bool Repeat()
        {
            if (!On || !next.Valid) return false;
            int before = pending.Count;
            pending.RemoveAll(p => p.step == next.step && (p.kind == Kind.Step || p.kind == Kind.Recovery));
            Enqueue(next.recovery ? "tutor.recovery:" + next.step : "tutor.step:" + next.step, next.recovery ? Kind.Recovery : Kind.Step, next.step, null, null, true);
            if (!string.IsNullOrEmpty(next.teach) && !done.Contains(next.teach)) { pending.RemoveAll(p => p.kind == Kind.Verb && p.teach == next.teach); Enqueue("tutor.verb:" + next.teach, Kind.Verb, null, null, next.teach, true); }
            foreach (var p in pending) if (p.reminder && (p.step == next.step || p.teach == next.teach)) p.urgent = true;
            return pending.Count > 0 && pending.Count >= before;
        }

        /// The line to speak now, or null. busy: Brann is speaking or has a line of the bench's queued.
        public string Candidate(float dt, bool busy)
        {
            stable += dt;
            if (busy) { quiet = 0; return null; }
            quiet += dt;
            if (!On || pending.Count == 0) return null;
            var best = Best();
            if (!Urgent(best) && (quiet < tuning.gapSeconds || stable < tuning.settleSeconds)) return null;
            return best.trigger;
        }
        /// The host spoke it.
        public void Spoken(string trigger)
        {
            var p = pending.FirstOrDefault(x => x.trigger == trigger); if (p == null) return;
            pending.Remove(p); said.Add(trigger); Log.Add(trigger); quiet = 0;
        }
        /// The host could not find a line for it: forget it.
        public void Drop(string trigger) => pending.RemoveAll(p => p.trigger == trigger);

        bool Urgent(Pending p) => p.urgent || p.kind == Kind.Verb ? Array.IndexOf(tuning.urgentTeach ?? new string[0], p.teach) >= 0
                                  : (p.kind == Kind.Step || p.kind == Kind.Action) && Array.IndexOf(tuning.urgentSteps ?? new string[0], p.step) >= 0;
        Pending Best() { Pending best = null; foreach (var p in pending) if (best == null || (int)p.kind < (int)best.kind) best = p; return best; }
        bool Stale(Pending p)
        {
            switch (p.kind)
            {
                case Kind.Welcome: return false;
                case Kind.Verb: return done.Contains(p.teach);
                case Kind.Action: return p.step != next.step || p.key != next.key;
                default: return p.step != next.step;
            }
        }
        void Enqueue(string trigger, Kind kind, string step, string key, string teach, bool reminder)
        {
            if (!reminder && said.Contains(trigger)) return;
            if (pending.Any(p => p.trigger == trigger) || !has(trigger)) return;
            if (pending.Count >= tuning.maxPending)
            {
                // drop by priority: the latest of the lowest (a step line before a verb line, never the one being added if it ranks higher)
                var worst = pending.Where(p => p.kind != Kind.Verb).OrderByDescending(p => (int)p.kind).FirstOrDefault() ?? pending[0];
                pending.Remove(worst);
            }
            pending.Add(new Pending { trigger = trigger, kind = kind, step = step, key = key, teach = teach, reminder = reminder });
        }

        // ------------------------------------------------------------------ the job note
        /// "said=T|T|T;done=K,K": compact, kept in AssemblyJob.Notes["tutor"] inside the bench blob.
        public string Save() => "said=" + string.Join("|", said.OrderBy(x => x, StringComparer.Ordinal)) + ";done=" + string.Join(",", done.OrderBy(x => x, StringComparer.Ordinal));
        void Load(string note)
        {
            if (string.IsNullOrEmpty(note)) return;
            foreach (var part in note.Split(';'))
            {
                int eq = part.IndexOf('='); if (eq < 0) continue;
                string name = part.Substring(0, eq), value = part.Substring(eq + 1);
                if (name == "said") foreach (var t in value.Split('|')) { if (t.Length > 0) said.Add(t); }
                else if (name == "done") foreach (var t in value.Split(',')) { if (t.Length > 0) done.Add(t); }
            }
        }

        /// The job walked on paper (installer verify, tests): every non-optional, non-recovery action in table order is "next",
        /// lines are spoken as soon as they are offered with Brann otherwise silent, and each action is done at once.
        /// Returns the triggers spoken, in order; prompts: the teach keys whose prompt showed.
        public static List<string> WalkOnPaper(AssemblyRecipeData recipe, Func<string, bool> has, out List<string> prompts)
        {
            var script = new BenchTutorScript(has); script.Begin(true, null, false);
            prompts = new List<string>();
            for (int s = 0; s < recipe.stages.Length; s++)
                foreach (var step in recipe.stages[s].steps)
                {
                    if (step.recovery || step.optional) continue;
                    foreach (var a in step.actions)
                    {
                        string teach = TeachKey(a);
                        script.Observe(new Next { stage = s, step = step.id, key = a.key, teach = teach });
                        if (script.Prompt != null && !prompts.Contains(script.Prompt)) prompts.Add(script.Prompt);
                        for (int i = 0; i < 12; i++) { var c = script.Candidate(1, false); if (c == null) break; script.Spoken(c); }
                        script.ActionDone(teach);
                    }
                }
            return script.Log.ToList();
        }

        // ------------------------------------------------------------------ verbs
        /// The teach key of an action: its archetype, with Point and Window split by form. Null for forms the step lines
        /// already explain (the press held in its band, the cure's wait).
        public static string TeachKey(AssemblyActionDef a)
        {
            if (a == null) return null;
            switch (a.verb)
            {
                case AssemblyVerbKind.Seat: return "seat";
                case AssemblyVerbKind.Turn: return "turn";
                case AssemblyVerbKind.Path: return "path";
                case AssemblyVerbKind.Wipe: return "wipe";
                case AssemblyVerbKind.Flick: return "flick";
                case AssemblyVerbKind.Point: return a.mode == "aim" ? "point_aim" : "point";
                case AssemblyVerbKind.Window: return a.mode == "strike" ? "window_strike" : a.mode == "hold" ? "window_hold" : null;
            }
            return null;
        }
        public static readonly string[] TeachKeys = { "seat", "turn", "point_aim", "point", "flick", "path", "window_strike", "window_hold", "wipe" };
        /// The on-screen prompt for a teach key: the mouse form and the keyboard form (DESIGN.md section 5).
        public static (string mouse, string keys) PromptText(string teach)
        {
            switch (teach)
            {
                case "seat": return ("<b>Drag</b> it with the left button to where it goes  ·  <b>wheel</b> turns it", "<b>Space</b> takes  ·  <b>arrows</b> or <b>Tab</b> to its place  ·  <b>Space</b> sets  ·  <b>Q</b>, <b>Shift+Q</b> turn");
                case "turn": return ("<b>Hold left</b> on it and <b>circle</b> the mouse slowly (or roll the <b>wheel</b>)", "<b>Hold Space</b>");
                case "point_aim": return ("Hold the pistol on the card  ·  <b>left click</b> fires", "<b>Space</b> fires");
                case "point": return ("With the tool in hand, <b>click</b> the lit mark", "<b>Arrows</b> or <b>Tab</b> to the mark  ·  <b>Space</b>");
                case "flick": return ("Hold it and <b>shake</b> the mouse side to side", "<b>Hold Space</b>");
                case "path": return ("<b>Hold left</b> and <b>follow</b> the lit line, steady", "<b>Hold Space</b>  ·  <b>A D</b> steer");
                case "window_strike": return ("<b>Hold left</b> to lift, <b>let go</b> to strike", "<b>Hold Space</b>, let go to strike");
                case "window_hold": return ("<b>Hold left</b>, <b>let go</b> when it looks and sounds right", "<b>Hold Space</b>, let go in time");
                case "wipe": return ("<b>Hold left</b> and <b>scrub</b> over it until it is clean", "<b>Hold Space</b>");
            }
            return (null, null);
        }
    }
}
