using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
    /// Brann's guided first job (tutor agent, 21 Nov 2026): the trigger logic of BenchTutorScript by hand (first use of each
    /// kind of action, the taper by stage, priority and never talking over Brann, no repeats across leaving and coming back,
    /// off by the Settings switch or on a later hand-made job), the whole job walked on paper against the installed lines,
    /// and BenchTutor driven on the stand-in bench through a detached sitting, including leave and resume through the blob.
    public class BenchTutorTests
    {
        const string LinesPath = "Assets/AthenHill/Audio/ElevenLabs/Bench/Tutor/BenchTutorLines.asset";
        const string RecipePath = "Assets/AthenHill/Data/Assembly/assembly_grip_stabilised_pistol.asset";
        const string PrefabPath = "Assets/AthenHill/Data/Assembly/SteadyHandsBenchStandIns.prefab";

        static BenchTutorScript.Next N(int stage, string step, string key, string teach, bool recovery = false) => new BenchTutorScript.Next { stage = stage, step = step, key = key, teach = teach, recovery = recovery };
        /// Lets time pass with Brann silent and returns what the tutor speaks (marking it spoken), in order.
        static string[] Speak(BenchTutorScript s, int max = 8)
        {
            var said = new System.Collections.Generic.List<string>();
            for (int i = 0; i < max; i++) { var c = s.Candidate(1, false); if (c == null) break; s.Spoken(c); said.Add(c); }
            return said.ToArray();
        }

        [Test] public void FirstUseOfAKindOfActionTeachesItOnceWithPromptAndGhost()
        {
            var s = new BenchTutorScript(_ => true); s.Begin(true, null, true);
            s.Observe(N(0, "s0.pistol", "lay", "seat"));
            Assert.That(s.Prompt, Is.EqualTo("seat"), "the prompt shows the first time a seat comes up");
            Assert.That(s.TakeGhost(), Is.True, "the ghost is asked for at once"); Assert.That(s.TakeGhost(), Is.False, "once");
            Assert.That(Speak(s), Is.EqualTo(new[] { "tutor.step:s0.pistol", "tutor.action:s0.pistol:lay", "tutor.verb:seat" }), "what, then how");
            Assert.That(s.Prompt, Is.EqualTo("seat"), "the prompt stays until a seat has been done");
            s.ActionDone("seat");
            Assert.That(s.Prompt, Is.Null);
            s.Observe(N(0, "s0.salvage", "servo", "seat"));
            Assert.That(s.TakeGhost(), Is.False); Assert.That(Speak(s), Is.EqualTo(new[] { "tutor.step:s0.salvage", "tutor.action:s0.salvage:servo" }), "no second how-line for a seat");
            // a how-line not yet spoken is dropped when the player does that kind of action first
            s.Observe(N(0, "s0.roll", "untie", "turn")); s.ActionDone("turn");
            Assert.That(s.Waiting.Any(t => t.StartsWith("tutor.verb")), Is.False);
        }

        [Test] public void TaperFullEarlyQuietInFiveAndSixSilentInSeven()
        {
            var s = new BenchTutorScript(_ => true); s.Begin(true, null, true);
            s.Observe(N(3, "s3.bath", "dip", "seat")); s.ActionDone("seat");
            Assert.That(Speak(s), Does.Contain("tutor.step:s3.bath"), "stages up to 4 voice each step");
            s.Observe(N(5, "s5.strap", "strap", "seat"));
            Assert.That(Speak(s), Is.Empty, "stage 5 is quiet");
            s.Idle(14); Assert.That(Speak(s), Is.Empty);
            s.Idle(15); Assert.That(Speak(s), Is.EqualTo(new[] { "tutor.step:s5.strap" }), "unless the player stalls");
            s.Idle(60); Assert.That(Speak(s), Is.Empty, "once per step");
            s.Observe(N(6, "s6.pin", "start", "seat"));
            s.Fault("s6.pin", 6); Assert.That(Speak(s), Is.EqualTo(new[] { "tutor.step:s6.pin" }), "or makes a mistake");
            s.Observe(N(7, "s7.shake", "shake", "flick"));
            s.Idle(100); s.Fault("s7.shake", 7);
            Assert.That(Speak(s), Is.Empty, "stage 7 keeps Brann's own lines");
            // a stall in a voiced stage repeats the step's line once
            s.Observe(N(2, "s2.gears", "top", "seat")); Speak(s);
            s.Idle(20); Assert.That(Speak(s), Is.EqualTo(new[] { "tutor.step:s2.gears" }));
        }

        [Test] public void NeverTalksOverBrannAndFaultsBeatStepLines()
        {
            var s = new BenchTutorScript(_ => true); s.Begin(true, null, false);
            s.Observe(N(1, "s1.clamp", "set", "seat"));
            Assert.That(s.Candidate(5, true), Is.Null, "Brann is speaking or has a line queued: nothing");
            Assert.That(s.Candidate(.2f, false), Is.Null, "a short silence first");
            Assert.That(s.Candidate(1, false), Is.EqualTo("tutor.welcome"), "then the welcome before the step");
            s.Spoken("tutor.welcome");
            s.Fault("s1.clamp", 1);
            Assert.That(s.Waiting.Any(t => t.StartsWith("tutor.step") || t.StartsWith("tutor.action")), Is.False, "a mistake drops waiting step lines (Brann's fault line speaks)");
            Assert.That(s.Waiting, Does.Contain("tutor.verb:seat"), "the how-line stays");
            // a recovery step takes the stage, ahead of anything else
            s.Observe(N(1, "s1.screw_b.r", "pliers", "turn", true));
            Assert.That(Speak(s).First(), Is.EqualTo("tutor.recovery:s1.screw_b.r"));
            // a quick player is not talked over: the next thing must settle
            s.Observe(N(1, "s1.scales", "left", "seat")); Assert.That(s.Candidate(.1f, false), Is.Null);
            s.Observe(N(1, "s1.lead", "unplug", "seat")); Assert.That(s.Waiting.Contains("tutor.step:s1.scales"), Is.False, "the line of a step that is no longer next goes");
        }

        [Test] public void LeavingAndComingBackDoesNotRepeat()
        {
            var s = new BenchTutorScript(_ => true); s.Begin(true, null, false);
            s.Observe(N(0, "s0.pistol", "lay", "seat")); Speak(s); s.ActionDone("seat");
            s.Observe(N(0, "s0.roll", "untie", "turn")); Speak(s);
            string note = s.Save();
            Assert.That(note, Does.Contain("tutor.step:s0.roll")); Assert.That(note, Does.Contain("done=seat"));
            var back = new BenchTutorScript(_ => true); back.Begin(true, note, true);
            back.Observe(N(0, "s0.roll", "untie", "turn"));
            Assert.That(Speak(back), Is.Empty, "nothing said before is said again, and no welcome on a resume");
            Assert.That(back.Prompt, Is.EqualTo("turn"), "a kind of action not yet done keeps its prompt");
            back.Observe(N(0, "s0.salvage", "servo", "seat")); Assert.That(back.Prompt, Is.Null, "a kind already done has none");
        }

        [Test] public void OffBySettingAndOnLaterHandMadeJobs()
        {
            var s = new BenchTutorScript(_ => true); s.Begin(true, null, false);
            s.SetEnabled(false);
            s.Observe(N(0, "s0.pistol", "lay", "seat"));
            Assert.That(s.Prompt, Is.Null); Assert.That(Speak(s), Is.Empty); Assert.That(s.TakeGhost(), Is.False);
            s.SetEnabled(true);
            Assert.That(s.Prompt, Is.EqualTo("seat"), "switched back on, it picks up where the job is");
            Assert.That(Speak(s), Does.Contain("tutor.step:s0.pistol"));
            var later = new BenchTutorScript(_ => true); later.Begin(false, null, false);
            later.Observe(N(0, "s0.pistol", "lay", "seat")); later.Idle(100); later.Fault("s0.pistol", 0);
            Assert.That(later.Prompt, Is.Null); Assert.That(Speak(later), Is.Empty, "not the first hand-made job: silent");
            Assert.That(later.Save(), Is.EqualTo("said=;done="));
        }

        [Test] public void HRepeatsTheStepAndItsHowLineAtOnce()
        {
            var s = new BenchTutorScript(_ => true); s.Begin(true, null, true);
            s.Observe(N(5, "s5.strap", "strap", "seat")); s.ActionDone("seat");
            Assert.That(Speak(s), Is.Empty, "a quiet stage");
            Assert.That(s.Repeat(), Is.True);
            Assert.That(s.Candidate(.01f, false), Is.EqualTo("tutor.step:s5.strap"), "H: at once, in any stage");
            s.Spoken("tutor.step:s5.strap"); s.Repeat(); Assert.That(Speak(s), Is.EqualTo(new[] { "tutor.step:s5.strap" }), "and again");
            s.Observe(N(1, "s1.tape", "peel", "path")); Speak(s); s.Repeat();
            Assert.That(Speak(s), Is.EqualTo(new[] { "tutor.step:s1.tape", "tutor.verb:path" }), "the how-line too while that kind is not yet done");
            s.SetEnabled(false); Assert.That(s.Repeat(), Is.False);
            Assert.That(BenchTutor.GuidedFor(null, "recipe_grip_stabilised_pistol"), Is.True, "no crafting model (QA): guided");
        }

        [Test] public void TheBeforeCardIsNotKeptWaiting()
        {
            var s = new BenchTutorScript(_ => true); s.Begin(true, null, true);
            s.Observe(N(0, "s0.card_before", "pulses", "point_aim"));
            Assert.That(s.Candidate(.01f, false), Is.EqualTo("tutor.step:s0.card_before"), "no settle and no gap before the camera moves");
            s.Spoken("tutor.step:s0.card_before"); s.Spoken(s.Candidate(.01f, false));
            Assert.That(s.Candidate(.01f, false), Is.EqualTo("tutor.verb:point_aim"));
            Assert.That(s.Candidate(.01f, true), Is.Null, "but never over Brann");
        }

        [Test] public void AHowLineNotYetSpokenOutlivesItsStep()
        {
            var s = new BenchTutorScript(_ => true); s.Begin(true, null, true);
            s.Observe(N(0, "s0.shake_before", "shake", "flick", false));
            s.Observe(N(0, "s0.cell", "latch", "turn"));   // shaken at once (optional: not counted as done), on to the cell
            var said = Speak(s);
            Assert.That(said, Does.Contain("tutor.verb:flick"), "the Flick how-line still plays");
            s.Observe(N(3, "s3.spin", "flick", "flick"));
            Assert.That(s.Prompt, Is.EqualTo("flick"), "and the prompt comes back at the first required flick");
            Assert.That(Speak(s), Does.Not.Contain("tutor.verb:flick"), "without saying the how-line twice");
        }

        [Test] public void ThePromptNeverCoversItsTarget()
        {
            var safe = Rect.MinMaxRect(BenchTutorPrompt.SafeSide, BenchTutorPrompt.SafeTop, 1920 - BenchTutorPrompt.SafeSide, 1080 - BenchTutorPrompt.SafeBottom);
            var size = new Vector2(460, 84);
            // sh-real9 frame 19: the wrap in the close vise shot, the box used to sit on it
            var wrap = Rect.MinMaxRect(600, 170, 900, 470);
            var at = BenchTutorPrompt.Place(wrap, size, safe, BenchTutorPrompt.Gap);
            Assert.That(BenchTutorPrompt.Covered(new Rect(at, size), wrap), Is.Zero, "beside the wrap, not on it");
            Assert.That(at.x, Is.GreaterThanOrEqualTo(wrap.xMax), "on the roomier side (right)");
            // a sweep of targets over the whole picture: never on the target when there is room, always inside the safe area
            for (float x = 0; x < 1900; x += 95) for (float y = 0; y < 1060; y += 85) foreach (var tw in new[] { 40f, 260f, 700f })
            {
                var t = new Rect(x, y, tw, tw * .6f);
                var p = BenchTutorPrompt.Place(t, size, safe, BenchTutorPrompt.Gap); var box = new Rect(p, size);
                Assert.That(box.xMin >= safe.xMin - .01f && box.xMax <= safe.xMax + .01f && box.yMin >= safe.yMin - .01f && box.yMax <= safe.yMax + .01f, $"inside the safe area for {t}");
                bool room = tw < 700;
                if (room) Assert.That(BenchTutorPrompt.Covered(box, t), Is.Zero, $"clear of {t}");
            }
            // a target filling the picture: the least it can cover
            var all = Rect.MinMaxRect(0, 0, 1920, 1080);
            Assert.That(BenchTutorPrompt.Covered(new Rect(BenchTutorPrompt.Place(all, size, safe, 28), size), all), Is.EqualTo(size.x * size.y));
        }

        [Test] public void LinesWithoutATakeAreNeverOffered()
        {
            var s = new BenchTutorScript(t => t != "tutor.action:s0.pistol:lay"); s.Begin(true, null, true);
            s.Observe(N(0, "s0.pistol", "lay", "seat"));
            Assert.That(Speak(s), Is.EqualTo(new[] { "tutor.step:s0.pistol", "tutor.verb:seat" }));
        }

        [Test] public void TheWholeJobOnPaperVoicesEveryEarlyStepAndTeachesEveryKind()
        {
            var lines = AssetDatabase.LoadAssetAtPath<BenchTutorLines>(LinesPath); var recipe = AssetDatabase.LoadAssetAtPath<AssemblyRecipe>(RecipePath);
            if (!lines || !recipe) Assert.Ignore("Run BenchTutorInstall20261121 install (and the bench's recipe step) first.");
            Assert.That(lines.lines.All(l => l.clip), Is.True, "every line has its take");
            var spoken = BenchTutorScript.WalkOnPaper(recipe.data, lines.Has, out var prompts);
            var teach = recipe.data.Steps.SelectMany(st => st.actions).Select(BenchTutorScript.TeachKey).Where(k => k != null).Distinct().ToList();
            foreach (var k in teach) { Assert.That(spoken, Does.Contain("tutor.verb:" + k)); Assert.That(prompts, Does.Contain(k)); }
            foreach (var st in recipe.data.stages.Take(5).SelectMany(x => x.steps).Where(x => !x.recovery && !x.optional)) Assert.That(spoken, Does.Contain("tutor.step:" + st.id), st.id);
            Assert.That(spoken.Count(t => t.StartsWith("tutor.step:s5") || t.StartsWith("tutor.step:s6") || t.StartsWith("tutor.step:s7")), Is.Zero);
            Assert.That(spoken.First(), Is.EqualTo("tutor.welcome"));
        }

        [Test] public void OnTheBenchItSpeaksThroughBrannAndResumesWithoutRepeating()
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath); var lines = AssetDatabase.LoadAssetAtPath<BenchTutorLines>(LinesPath);
            if (!prefab || !lines) Assert.Ignore("The bench prefab or the tutor lines are not installed.");
            bool was = BenchTutor.Enabled; BenchTutor.Enabled = true;
            var go = Object.Instantiate(prefab); var host = new GameObject("tutor test");
            try
            {
                var session = go.GetComponent<AssemblySession>();
                AssemblyCraftLink.ForgetDetached();
                Assert.That(session.Open(true), Is.True);
                var tutor = host.AddComponent<BenchTutor>(); tutor.lines = lines;
                void Run(float seconds) { for (float t = 0; t < seconds; t += .1f) { session.Step(.1f, default); tutor.Drive(session, .1f); } }
                Run(14);
                var spoken = session.Voice.Spoken.ToList();
                Assert.That(spoken.First(), Is.EqualTo("take_bench"), "the bench's own line first");
                Assert.That(spoken, Does.Contain("tutor_welcome")); Assert.That(spoken, Does.Contain("tutor_s0_pistol"));
                Assert.That(spoken.IndexOf("tutor_s0_pistol"), Is.GreaterThan(spoken.IndexOf("take_bench")));
                Assert.That(tutor.PromptKey, Is.EqualTo("seat"));
                Assert.That(session.ActionLine, Does.StartWith("Drag the pistol onto the black work mat"), "the action line carries a plain instruction for every action");
                tutor.Refusal("not_yet", session.bench.Part("servo.case_body"), null);
                Assert.That(tutor.CaptionFlash, Does.StartWith("Not the servo yet.").And.Contain("Drag the pistol"), "a wrong click says what is wrong and what to do");
                Assert.That(tutor.CaptionText, Is.Null, "and it is not put in Brann's caption band: they are not his words");
                Assert.That(session.DevComplete("s0.pistol", "lay", 1), Is.True);
                Run(.2f);
                Assert.That(tutor.PromptKey, Is.EqualTo("turn"), "a seat has been done: its prompt goes, the next kind (the strap) has its own");
                Assert.That(session.Job.Notes[BenchTutor.NoteKey], Does.Contain("done=seat").And.Contain("tutor.step:s0.pistol"));
                session.Close(true);
                tutor.Drive(session, .1f); Assert.That(tutor.Bound, Is.False);
                Assert.That(session.Open(true), Is.True, "back at the bench");
                Run(14);
                var again = session.Voice.Spoken.ToList();
                Assert.That(again, Does.Not.Contain("tutor_welcome")); Assert.That(again, Does.Not.Contain("tutor_s0_pistol"));
                Assert.That(again, Does.Contain("tutor_s0_roll"), "it carries on from the next step");
                // the before card: its line starts the moment Brann is silent (no settle, no gap), the how-line right behind it, and
                // the caption stays until the first pulse
                session.DevComplete("s0.roll", null, 1); session.DevComplete("s0.salvage", null, 1);
                for (int i = 0; i < 400 && (session.Voice.Busy || tutor.Script.Waiting.Any()) ; i++) { session.Step(.1f, default); tutor.Drive(session, .1f); if (session.Voice.LineId == "tutor_s0_card_before") break; }
                if (session.Voice.LineId != "tutor_s0_card_before") { session.Step(.05f, default); tutor.Drive(session, .05f); }
                Assert.That(session.Voice.LineId, Is.EqualTo("tutor_s0_card_before"), "spoken as soon as Brann is free");
                Assert.That(tutor.CaptionHeld, Does.StartWith("Pistol up."));
                for (int i = 0; i < 200 && session.Voice.LineId != "tutor_point_aim_verb"; i++) { session.Step(.1f, default); tutor.Drive(session, .1f); }
                Assert.That(session.Voice.LineId, Is.EqualTo("tutor_point_aim_verb"));
                Assert.That(tutor.CaptionHeld, Does.Contain("It wanders"), "the how-line joins the held caption");
                session.Job.Notes["card:s0.card_before"] = "0,0"; tutor.Drive(session, .1f);
                Assert.That(tutor.CaptionHeld, Is.Null, "the first pulse lets the caption go");
                // switched off in Settings: silent, and no instruction line
                BenchTutor.Enabled = false; int before = session.Voice.Spoken.Count(x => x.StartsWith("tutor_"));
                Run(14);
                Assert.That(session.Voice.Spoken.Count(x => x.StartsWith("tutor_")), Is.EqualTo(before)); Assert.That(tutor.PromptKey, Is.Null);
                Assert.That(session.ActionLine, Is.Not.StartWith("Drag").And.Not.StartWith("Hold"), "the guided instruction goes with the switch");
                session.Close(false);
            }
            finally
            {
                BenchTutor.Enabled = was; AssemblyCraftLink.ForgetDetached();
                Object.DestroyImmediate(host); Object.DestroyImmediate(go);
            }
        }
    }
}
