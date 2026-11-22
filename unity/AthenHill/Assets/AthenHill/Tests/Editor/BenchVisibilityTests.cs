using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
    /// Carl's second Steady Hands playtest of 22 Nov 2026: scrap hidden under thicker things, no obvious way to change the
    /// driver's bit, and a housing pin that was hard to find. All on the installed bench, with its real meshes.
    public class BenchVisibilityTests
    {
        GameObject go; AssemblySession session; AssemblyBench bench; AssemblyBot bot;
        const float Dt = 1f / 60;

        [SetUp] public void SetUp()
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Data/Assembly/SteadyHandsBench.prefab");
            Assert.That(prefab, Is.Not.Null);
            go = Object.Instantiate(prefab); session = go.GetComponent<AssemblySession>(); bench = go.GetComponent<AssemblyBench>();
            AssemblyCraftLink.ForgetDetached();
            Assert.That(session.Open(true), Is.True);
            bot = new AssemblyBot(session, false);
        }
        [TearDown] public void TearDown() { session.Close(false); Object.DestroyImmediate(go); AssemblyCraftLink.ForgetDetached(); }

        void Reach(string action) => Assert.That(bot.PlayUntil(action), Is.True, bot.Error);
        static readonly string[] Salvage = { "materials.sheet_a", "materials.sheet_b", "materials.vial", "servo.case_body" };

        // ---- "The alloy scraps on the bench build get hidden under anything thicker than them. the tool roll, the tray."
        [Test] public void TheOpenRollCoversNoneOfTheSalvage()
        {
            Reach("s0.salvage:servo");
            Assert.That(bench.Param("tools.roll_unroll").Value, Is.EqualTo(1).Within(.01f));
            foreach (var id in Salvage) Assert.That(bench.Support.Covered(bench.Part(id)), Is.LessThan(.1f), id + " is under something");
            foreach (var id in new[] { "materials.sheet_a", "materials.sheet_b", "materials.vial" })
                Assert.That(bench.Part(id).place, Does.StartWith("place.entry."), id + " had to be moved out from under the roll");
        }

        [Test] public void BothSheetsShowInTheTray()
        {
            Reach("s0.card_before:pulses");
            Assert.That(bench.Part("materials.sheet_b").place, Is.EqualTo("fixtures.tray/seat_alloy#b"));
            Assert.That(bench.Support.Covered(bench.Part("materials.sheet_b")), Is.LessThan(.05f), "the second sheet is under the tray's floor");
            Assert.That(bench.Support.Covered(bench.Part("materials.sheet_a")), Is.LessThan(.6f), "the first sheet is under the second");   // a staggered pile: about half of it shows
        }

        static readonly string[] On = { "tools.roll", "fixtures.tray", "fixtures.workmat", "fixtures.partsmat", "fixtures.pad", "fixtures.cradle", "fixtures.dish", "fixtures.vise", "tools.mallet", "tools.file_flat" };

        [Test] public void AThinSheetPutDownOnAnythingStaysInSight([ValueSource(nameof(On))] string on, [Values(-.6f, 0f, .6f)] float along)
        {
            Reach("s0.salvage:servo");
            var sheet = bench.Part("materials.sheet_a"); var under = bench.Part(on);
            var at = under.transform.TransformPoint(under.localBounds.center + Vector3.right * (under.localBounds.extents.x * along));
            if (on == "tools.roll") at = bench.Part("tools.punch").transform.position + bench.surface.right * (along * .3f + .15f);
            sheet.transform.position = at + bench.Up * .085f;
            bench.Support.Rest(sheet);
            Assert.That(bench.Support.Covered(sheet), Is.LessThan(.02f), "hidden by or in " + on);
            Assert.That(bench.HeightAbove(sheet.transform.position), Is.InRange(-.01f, .05f), "left in the air, or under the bench");
        }

        [Test] public void LooseScrapComesOutFromUnderWhatCoversIt()
        {
            Reach("s0.salvage:servo");
            var sheet = bench.Part("materials.sheet_a");
            var buried = bench.surface.TransformPoint(new Vector3(.75f, -.0105f, .3f));
            bench.Drop(sheet, new Pose(buried, sheet.transform.rotation));
            Assert.That(bench.Support.Covered(sheet), Is.GreaterThan(.5f), "the set-up did not bury it");
            bench.Support.Uncover();
            Assert.That(bench.Support.Covered(sheet), Is.LessThan(.05f));
        }

        // ---- "I cant see an obvious way to change the screw driver head for the servo part?"
        [Test] public void TheWrongBitSaysHowToChangeItUntilItIsChanged()
        {
            Reach("s2.screws:a_turn"); bot.FreeHands();
            Assert.That(bot.Take("tool:screwdriver"), Is.True, bot.Error);
            if (session.HeldTool.Mode == "cross") bot.Flip();
            bot.Wait(Dt);
            Assert.That(session.BitWanted(), Is.EqualTo("cross"));
            Assert.That(session.ActionLine, Does.Contain("press R").And.Contain("cross"));
            bot.Flip(); bot.Wait(Dt);
            Assert.That(session.BitWanted(), Is.Null);
            Assert.That(session.ActionLine, Does.Not.Contain("press R"));
        }

        [TestCase(true), TestCase(false)]
        public void ClickingTheSpareBitFitsItAndNeverCarriesItOff(bool driverInHand)
        {
            Reach("s2.screws:a_turn"); bot.FreeHands();
            var driver = bench.Tool("tool:screwdriver");
            if (driverInHand) Assert.That(bot.Take("tool:screwdriver"), Is.True, bot.Error);
            for (int i = 0; i < 2; i++)
            {
                var spare = bench.Parts.First(p => p.IsBit && p.transform.parent == bench.Part("tools.bitblock").transform);
                string kind = spare.BitKind;
                Assert.That(bot.Press(spare.id), Is.True, bot.Error);
                Assert.That(session.HeldPart, Is.Null, "the bit was carried off");
                Assert.That(session.HeldTool, Is.EqualTo(driver));
                Assert.That(driver.Mode, Is.EqualTo(kind));
            }
        }

        // ---- "The pin on the handle that need knocking out with mallet and punch was hard to find."
        [Test] public void WithThePunchInHandThePinIsRingedAndInItsOwnShot()
        {
            Reach("s1.pin:punch"); bot.FreeHands(); bot.Wait(Dt);
            Assert.That(session.SmallTarget(out var at, out var label), Is.True);
            Assert.That(label, Does.StartWith("TAKE THE"));
            Assert.That(bot.Take("tools.punch"), Is.True, bot.Error); bot.Wait(Dt);
            Assert.That(session.SmallTarget(out at, out label), Is.True);
            Assert.That(Vector3.Distance(at, bench.Marker("pistol.housing_pin/punch").transform.position), Is.LessThan(.001f));
            Assert.That(session.WantedShotName, Is.EqualTo("pin"));
        }

        [Test] public void TheLineNeverSaysToPutThePunchBackBeforeItIsSet()
        {
            var lines = AssetDatabase.LoadAssetAtPath<BenchTutorLines>("Assets/AthenHill/Audio/ElevenLabs/Bench/Tutor/BenchTutorLines.asset");
            var host = new GameObject("tutor under test"); bool was = BenchTutor.Enabled;
            try
            {
                var tutor = host.AddComponent<BenchTutor>(); tutor.lines = lines;
                BenchTutor.Enabled = true;
                Reach("s1.pin:punch"); bot.FreeHands();
                Assert.That(bot.Take("tools.punch"), Is.True, bot.Error);
                tutor.Drive(session, Dt);
                string line = tutor.LineFor(session.Next.Value);
                Assert.That(line, Does.Not.Contain("back first").And.Contain("ringed pin"));
            }
            finally { BenchTutor.Enabled = was; Object.DestroyImmediate(host); }
        }

        [Test] public void OneClickOnThePinStandsThePunchOnIt()
        {
            Reach("s1.pin:punch"); bot.FreeHands();
            Assert.That(bot.Take("tools.punch"), Is.True, bot.Error);
            Assert.That(bot.Press("pistol.housing_pin/punch"), Is.True, bot.Error);
            bot.Wait(.5f);
            Assert.That(bench.Part("tools.punch").place, Is.EqualTo("pistol.housing_pin/punch"));
        }
    }
}
