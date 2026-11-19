using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
    /// NPC life pass (19 Nov 2026): bark line choice, hour windows, once-only lines, no-repeat, cooldowns and the
    /// approach edge trigger. Pure logic only (BarkRules, BarkMemory, ApproachGate).
    public class NpcBarkTests
    {
        static BarkLine L(string id, BarkTrigger t, float from = 0, float to = 24, string requires = null, bool once = false, float weight = 1)
            => new BarkLine { id = id, trigger = t, text = "Line " + id + ".", hours = new Vector2(from, to), requires = requires, once = once, weight = weight };
        static readonly List<string> None = new List<string>();

        [Test]
        public void HoursWrapPastMidnightAndFullDayMeansAny()
        {
            Assert.That(BarkRules.InHours(new Vector2(0, 24), 3.5f));
            Assert.That(BarkRules.InHours(new Vector2(5, 5), 17));
            Assert.That(BarkRules.InHours(new Vector2(5, 11), 5), "from is inclusive");
            Assert.That(BarkRules.InHours(new Vector2(5, 11), 11), Is.False, "to is exclusive");
            Assert.That(BarkRules.InHours(new Vector2(21, 5), 23.5f));
            Assert.That(BarkRules.InHours(new Vector2(21, 5), 2));
            Assert.That(BarkRules.InHours(new Vector2(21, 5), 12), Is.False);
            Assert.That(BarkRules.InHours(new Vector2(18, 2), 24.5f), "hours past 24 wrap");
        }

        [Test]
        public void PickFiltersTriggerHoursConditionAndOnce()
        {
            var lines = new[] {
                L("greet", BarkTrigger.Greeting), L("idle", BarkTrigger.Idle),
                L("night", BarkTrigger.Greeting, 21, 5), L("primer", BarkTrigger.Acknowledge, requires: "primer", once: true),
                new BarkLine { id = "blank", trigger = BarkTrigger.Greeting, text = "  " } };
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Greeting, 12, null, null, None, 0).id, Is.EqualTo("greet"), "daytime: the night line is out of hours; blank text is never spoken");
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Greeting, 23, null, null, None, 0).id, Is.EqualTo("night"), "a line for this hour beats an any-hour line");
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Acknowledge, 12, e => false, null, None, 0), Is.Null, "condition fails");
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Acknowledge, 12, e => e == "primer", null, None, 0).id, Is.EqualTo("primer"));
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Acknowledge, 12, e => true, l => l.id == "primer", None, 0), Is.Null, "a once-only line already spoken is gone");
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Weapon, 12, null, null, None, 0), Is.Null, "no line for that trigger");
        }

        [Test]
        public void PickAvoidsRecentLinesAndFallsBackToTheStalest()
        {
            var lines = new[] { L("a", BarkTrigger.Idle), L("b", BarkTrigger.Idle), L("c", BarkTrigger.Idle) };
            for (int i = 0; i < 20; i++)
                Assert.That(BarkRules.Pick(lines, BarkTrigger.Idle, 12, null, null, new List<string> { "a", "b" }, i / 20.0).id, Is.EqualTo("c"));
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Idle, 12, null, null, new List<string> { "b", "c", "a" }, .5).id, Is.EqualTo("b"), "all recent: the one heard longest ago");
        }

        [Test]
        public void PickHonoursWeights()
        {
            var lines = new[] { L("rare", BarkTrigger.Idle, weight: 1), L("common", BarkTrigger.Idle, weight: 3), L("off", BarkTrigger.Idle, weight: 0) };
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Idle, 12, null, null, None, .1).id, Is.EqualTo("rare"));
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Idle, 12, null, null, None, .3).id, Is.EqualTo("common"));
            Assert.That(BarkRules.Pick(lines, BarkTrigger.Idle, 12, null, null, None, .999).id, Is.EqualTo("common"));
            var picked = Enumerable.Range(0, 100).Select(i => BarkRules.Pick(lines, BarkTrigger.Idle, 12, null, null, None, i / 100.0).id).ToList();
            Assert.That(picked, Has.No.Member("off"), "weight 0 is never spoken");
        }

        [Test]
        public void ARunOfPicksNeverRepeatsWithinTheRecentWindow()
        {
            var lines = new[] { L("a", BarkTrigger.Greeting), L("b", BarkTrigger.Greeting), L("c", BarkTrigger.Greeting), L("d", BarkTrigger.Greeting) };
            var memory = new BarkMemory { recentCapacity = 3 }; var rng = new System.Random(7); var said = new List<string>();
            for (int i = 0; i < 40; i++)
            {
                var line = BarkRules.Pick(lines, BarkTrigger.Greeting, 12, null, null, memory.Recent("mira"), rng.NextDouble());
                said.Add(line.id); memory.Spoke("mira", line.id, BarkTrigger.Greeting, i * 200, 0, 0);
            }
            for (int i = 3; i < said.Count; i++) Assert.That(said.Skip(i - 3).Take(3), Has.No.Member(said[i]), "line " + i);
        }

        [Test]
        public void CooldownsAreGlobalAndPerSpeakerTrigger()
        {
            var m = new BarkMemory();
            Assert.That(m.Ready("mira", BarkTrigger.Greeting, 0));
            m.Spoke("mira", "greet", BarkTrigger.Greeting, 10, cooldown: 150, globalGap: 9);
            Assert.That(m.Ready("torr", BarkTrigger.Greeting, 15), Is.False, "nobody barks inside the global gap");
            Assert.That(m.Ready("torr", BarkTrigger.Greeting, 19));
            Assert.That(m.Ready("mira", BarkTrigger.Idle, 19), "another trigger of the same speaker is free");
            Assert.That(m.Ready("mira", BarkTrigger.Greeting, 100), Is.False, "her greeting cools down");
            Assert.That(m.Ready("mira", BarkTrigger.Greeting, 160));
            m.Hold("mira", BarkTrigger.Greeting, 400); m.Hold("mira", BarkTrigger.Greeting, 200);
            Assert.That(m.Ready("mira", BarkTrigger.Greeting, 300), Is.False, "a hold never shortens an earlier one");
            m.HoldAll(500);
            Assert.That(m.Ready("vex", BarkTrigger.Passing, 450), Is.False, "window grace holds everyone");
            m.Clear();
            Assert.That(m.Ready("mira", BarkTrigger.Greeting, 0));
        }

        [Test]
        public void RecentKeepsTheLatestLinesOldestFirst()
        {
            var m = new BarkMemory { recentCapacity = 2 };
            m.Spoke("s", "a", BarkTrigger.Idle, 0, 0, 0); m.Spoke("s", "b", BarkTrigger.Idle, 0, 0, 0); m.Spoke("s", "a", BarkTrigger.Idle, 0, 0, 0); m.Spoke("s", "c", BarkTrigger.Idle, 0, 0, 0);
            Assert.That(m.Recent("s"), Is.EqualTo(new[] { "a", "c" }));
            Assert.That(m.Recent("other"), Is.Empty);
        }

        [Test]
        public void ApproachFiresOnceAndRearmsBeyondTheMargin()
        {
            var g = new ApproachGate();
            Assert.That(g.Enter(8, 5, 3), Is.False);
            Assert.That(g.Enter(4.9f, 5, 3), Is.True);
            Assert.That(g.Enter(4, 5, 3), Is.False, "still inside");
            Assert.That(g.Enter(7, 5, 3), Is.False, "between radius and margin: not re-armed");
            Assert.That(g.Enter(4, 5, 3), Is.False, "came back without leaving far enough");
            Assert.That(g.Enter(8.5f, 5, 3), Is.False);
            Assert.That(g.Enter(5, 5, 3), Is.True, "re-armed after stepping beyond 8 m");
            g = new ApproachGate(); g.Occupy();
            Assert.That(g.Enter(2, 5, 3), Is.False, "the player was already here (in conversation)");
        }

        [Test]
        public void ApproachOrderPutsMilestonesBeforeTheGreeting()
        {
            var o = BarkRules.ApproachOrder.ToList();
            Assert.That(o.IndexOf(BarkTrigger.Acknowledge), Is.LessThan(o.IndexOf(BarkTrigger.OrderDone)));
            Assert.That(o.IndexOf(BarkTrigger.OrderDone), Is.LessThan(o.IndexOf(BarkTrigger.Greeting)));
            Assert.That(o, Has.No.Member(BarkTrigger.Idle).And.No.Member(BarkTrigger.Weapon), "idle and weapon lines have their own moments");
        }

        [Test]
        public void CaptionTimeCoversTheTakeAndTheReadingTime()
        {
            Assert.That(BarkRules.CaptionSeconds("Through you go.", 0), Is.EqualTo(2.2f).Within(.001f), "short text-only lines get the minimum");
            Assert.That(BarkRules.CaptionSeconds("Through you go.", 3), Is.EqualTo(3.5f).Within(.001f), "voiced: the take plus a beat");
            Assert.That(BarkRules.CaptionSeconds(string.Join(" ", Enumerable.Repeat("word", 40)), 0), Is.EqualTo(8).Within(.001f), "clamped");
            Assert.That(BarkRules.OnceFlag("npc_mira", "ack_primer"), Is.EqualTo("bark.npc_mira.ack_primer"));
            Assert.That(QuestConditions.Problems("flag:" + BarkRules.OnceFlag("npc_mira", "ack_primer")), Is.Empty, "once flags are valid flag terms");
        }

        [Test]
        public void BarkSetHasIgnoresBlankLines()
        {
            var set = ScriptableObject.CreateInstance<BarkSet>();
            try
            {
                set.lines = new[] { new BarkLine { id = "x", trigger = BarkTrigger.Weapon, text = "" }, L("g", BarkTrigger.Greeting) };
                Assert.That(set.Has(BarkTrigger.Greeting)); Assert.That(set.Has(BarkTrigger.Weapon), Is.False);
            }
            finally { Object.DestroyImmediate(set); }
        }
    }
}
