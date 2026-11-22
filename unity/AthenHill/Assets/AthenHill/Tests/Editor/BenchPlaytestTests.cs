using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
    /// Carl's Steady Hands playtest of 22 Nov 2026, one test or more for each note. They play the INSTALLED bench: the
    /// stand-in bench's empties point another way, which is how the crack and tool faults passed every earlier test.
    public class BenchPlaytestTests
    {
        GameObject go; AssemblySession session; AssemblyBench bench; AssemblyBot bot;
        const float Dt = 1f / 60;

        [SetUp] public void SetUp()
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Data/Assembly/SteadyHandsBench.prefab");
            Assert.That(prefab, Is.Not.Null);
            go = UnityEngine.Object.Instantiate(prefab); session = go.GetComponent<AssemblySession>(); bench = go.GetComponent<AssemblyBench>();
            AssemblyCraftLink.ForgetDetached();
            Assert.That(session.Open(true), Is.True);
            bot = new AssemblyBot(session, false);
        }
        [TearDown] public void TearDown()
        {
            session.Close(false); UnityEngine.Object.DestroyImmediate(go); AssemblyCraftLink.ForgetDetached();
        }

        Camera Shot(string name) => session.ShotCamera(name);
        void Reach(string action) => Assert.That(bot.PlayUntil(action), Is.True, bot.Error);
        AssemblyInputFrame Aim(Camera cam, Vector3 at) => new AssemblyInputFrame { pointer = true, ray = new Ray(cam.transform.position, (at - cam.transform.position).normalized) };
        void Step(Camera cam, AssemblyInputFrame f) => session.Step(Dt, f, cam.transform.position);
        Vector3 OnBench(float x, float y, float z) => bench.surface.TransformPoint(new Vector3(x, y, z));

        // ---- "Getting the charge cell onto the pad was a bit tricky, anywhere in its vicinity should have been ok"
        [TestCase(0f, 0f), TestCase(.11f, 0f), TestCase(-.11f, 0f), TestCase(0f, .1f), TestCase(0f, -.1f), TestCase(.1f, .09f)]
        public void TheChargeCellSeatsFromAnywhereNearThePad(float dx, float dz)
        {
            Reach("s0.cell:cell");
            var cam = Shot("mat"); var cell = bench.Part("pistol.cell");
            var pad = bench.Marker("fixtures.pad/seat_cell").transform.position;
            CarryTo(cam, cell, pad + bench.surface.right * dx + bench.surface.forward * dz, 90);
            Assert.That(cell.place, Is.EqualTo("fixtures.pad/seat_cell"), $"{dx}, {dz} from the pad's mark");
        }

        // ---- "Placing things on the mat is hard, it should snap into place when over the mat"
        [TestCase(-.19f), TestCase(0f), TestCase(.19f)]
        public void APartDropsIntoPlaceFromAnywhereOverTheMat(float dx)
        {
            Reach("s1.scales:left");
            var scale = bench.Part("pistol.scale_l");
            CarryTo(Shot("vise"), scale, bench.Part("fixtures.partsmat").transform.position + bench.surface.right * dx, 90);
            Assert.That(scale.place, Is.EqualTo("fixtures.partsmat/seat_pistol_scale_l"));
        }

        [Test] public void LettingGoWhileItPullsInDoesNotDropIt()
        {
            Reach("s0.cell:cell");
            var cam = Shot("mat"); var cell = bench.Part("pistol.cell"); var pad = bench.Marker("fixtures.pad/seat_cell").transform.position;
            CarryTo(cam, cell, pad, 1);   // released on the frame it reaches the pad
            for (int i = 0; i < 60; i++) Step(cam, Aim(cam, pad));
            Assert.That(cell.place, Is.EqualTo("fixtures.pad/seat_cell"));
        }

        void CarryTo(Camera cam, AssemblyPart part, Vector3 to, int framesThere)
        {
            bot.FreeHands();
            Assert.That(bot.Press(part.id), Is.True, bot.Error);
            for (int i = 1; i < 240 && session.CarryLeaving; i++) { var up = Aim(cam, part.RestWorld.position + bench.Up * (.003f * i)); up.primaryHeld = true; Step(cam, up); }
            Assert.That(session.HeldPart, Is.EqualTo(part), part.id + " was not picked up");
            for (int i = 0; i < framesThere && session.HeldPart; i++) { var f = Aim(cam, to); f.primaryHeld = true; Step(cam, f); }
            var release = Aim(cam, to); release.primaryUp = true; release.screen = new Vector2(400, 400); Step(cam, release);
        }

        // ---- "Tools like the mallet when straightening the pin are at odd angle for the work involved"
        [Test] public void EveryToolMeetsItsWorkAlongItsWorkingAxis()
        {
            Assert.That(bench.ArtAxes, Is.True, "the installed art works along the empties' +Y");
            foreach (var id in new[] { "tools.screwdriver", "tools.drill", "tools.punch", "tools.pliers", "tools.mallet", "tools.wirebrush" })
            {
                var tool = bench.Part(id);
                foreach (var into in new[] { -bench.Up, -bench.surface.forward, bench.surface.right, (bench.surface.forward - bench.Up).normalized })
                {
                    var at = OnBench(.1f, .2f, .1f);
                    AssemblyToolPose.Place(bench, tool, at, into);
                    Assert.That(Vector3.Angle(AssemblyToolPose.WorkAxis(bench, tool), into), Is.LessThan(.5f), id);
                    Assert.That(Vector3.Distance(tool.TipPoint, at), Is.LessThan(.001f), id + " is not on the work");
                }
            }
        }

        [Test] public void PenLikeToolsKeepTheirHandlesOutOfTheBench()
        {
            foreach (var id in new[] { "tools.iron", "tools.scribe", "tools.pick", "tools.cutters", "tools.strippers", "tools.applicator", "tools.oil_dropper", "tools.file_flat", "tools.file_round" })
            {
                var tool = bench.Part(id); var at = OnBench(0, .02f, .1f);
                AssemblyToolPose.Place(bench, tool, at, -bench.Up);
                Assert.That(bench.HeightAbove(tool.GrabPoint), Is.GreaterThan(bench.HeightAbove(at)), id + " has its handle under the work");
                Assert.That(Vector3.Dot(tool.GrabPoint - at, bench.surface.forward), Is.GreaterThan(-.005f), id + " points away from the hand");
            }
        }

        [Test] public void ThePunchStandsInLineWithThePinAndTheMalletHitsAlongIt()
        {
            Reach("s1.pin:taps");
            var pin = bench.Part("pistol.housing_pin"); var punch = bench.Part("tools.punch");
            var driven = pin.RemovalAxis;
            Assert.That(Vector3.Angle(AssemblyToolPose.WorkAxis(bench, punch), driven), Is.LessThan(1), "the punch lies across the pin");
            Assert.That(Vector3.Distance(punch.TipPoint, bench.Marker("pistol.housing_pin/punch").transform.position), Is.LessThan(.002f));
            var mallet = bench.Part("tools.mallet");
            var a = session.Job.Action("s1.pin", "taps");
            var blow = AssemblyToolPose.Work(bench, a, pin, null, mallet);
            Assert.That(Vector3.Angle(blow.into, driven), Is.LessThan(1));
            AssemblyToolPose.Place(bench, mallet, blow.at, blow.into);
            Assert.That(Vector3.Angle(AssemblyToolPose.WorkAxis(bench, mallet), driven), Is.LessThan(1), "the mallet's face is not square to the punch");
            Assert.That(Vector3.Dot((mallet.TipPoint - punch.TipPoint).normalized, -driven), Is.GreaterThan(.97f), "the mallet is not at the punch's end");
        }

        [Test] public void SpinningMechanismsTurnAboutTheirBones([Values("tools.drill_crank", "servo.rotor")] string id)
        {
            var param = bench.Param(id);
            Assert.That(param.continuous, Is.True);
            Assert.That(Vector3.Angle(param.spinAxis, Vector3.up), Is.LessThan(1), id + " tumbles: a Blender bone lies along +Y");
        }

        [Test] public void StraighteningThePinOnTheAnvilIsABlowStraightDown()
        {
            var pin = bench.Part("pistol.housing_pin"); bench.Put(pin, "fixtures.vise/anvil");
            var mallet = bench.Part("tools.mallet");
            var blow = AssemblyToolPose.Work(bench, session.Job.Action("s1.pin.r", "straighten"), pin, null, mallet);
            AssemblyToolPose.Place(bench, mallet, blow.at, blow.into);
            Assert.That(Vector3.Angle(AssemblyToolPose.WorkAxis(bench, mallet), -bench.Up), Is.LessThan(.5f), "the face is not flat on the pin");
            var handle = (mallet.GrabPoint - mallet.TipPoint).normalized;
            Assert.That(Mathf.Abs(Vector3.Dot(handle, bench.Up)), Is.LessThan(.45f), "the handle is not across the blow");
            Assert.That(Vector3.Dot(handle, bench.surface.forward), Is.GreaterThan(.3f), "the handle is not to the hand");
        }

        // ---- "I turn the vise and can see the crack but it's not moving the game forward"
        [Test] public void TurningTheViseWithVUntilTheCrackShowsFinishesTheStep()
        {
            Reach("s1.inspect:find");
            var cam = Shot("vise"); var at = bench.Marker("pistol.frame/crack").transform.position;
            for (int i = 0; i < 90 && !session.Job.IsDone("s1.inspect"); i++)
            {
                var f = Aim(cam, at);
                if (i < 12) { f.swivelHeld = true; f.delta = new Vector2(4, 0); }
                Step(cam, f);
            }
            Assert.That(session.Job.IsDone("s1.inspect"), Is.True);
            for (int i = 0; i < 90; i++) Step(cam, Aim(cam, at));
            Assert.That(Mathf.Abs(session.Vise.Yaw), Is.LessThan(.6f), "it did not come back square for the next step");
        }

        [Test] public void ClickingTheVisibleCrackFinishesTheStep()
        {
            Reach("s1.inspect:find");
            var cam = Shot("vise"); var f = Aim(cam, bench.Marker("pistol.frame/crack").transform.position);
            f.primaryDown = f.primaryHeld = true; Step(cam, f);
            Assert.That(session.Job.IsDone("s1.inspect"), Is.True);
        }

        [Test] public void ACrackTurnedAwayIsNotFoundUntilItComesBackRound()
        {
            Reach("s1.inspect:find");
            var cam = Shot("vise"); session.Vise.Turn(180);
            var at = bench.Marker("pistol.frame/crack").transform.position;
            for (int i = 0; i < 60; i++) Step(cam, Aim(cam, at));
            Assert.That(session.Job.IsDone("s1.inspect"), Is.False, "found with its back to the player");
            session.Vise.Turn(160);
            for (int i = 0; i < 60 && !session.Job.IsDone("s1.inspect"); i++) Step(cam, Aim(cam, at));
            Assert.That(session.Job.IsDone("s1.inspect"), Is.True);
        }

        [Test] public void TurningTooFarIsTightAndTheStepGoesOn()
        {
            Reach("s2.swap:snug");
            bot.FreeHands();
            var cam = Shot("vise"); var screw = bench.Part("fixtures.vise_screw");
            var press = Aim(cam, screw.GrabPoint); press.primaryDown = press.primaryHeld = true; Step(cam, press);
            Assert.That(session.Verb, Is.InstanceOf<TurnVerb>(), "pressing the handle did not start the turn");
            for (int i = 0; i < 200 && !session.Job.ActionDone("s2.swap", "snug"); i++)
            {
                var f = Aim(cam, screw.GrabPoint); f.primaryHeld = true; f.scroll = 2; Step(cam, f);
            }
            Assert.That(session.Job.ActionDone("s2.swap", "snug"), Is.True, "over-tightening blocked the job");
            Assert.That(session.Job.FaultsOn("s2.swap", "overtight"), Is.EqualTo(1));
        }

        [Test] public void AViseOpensWhicheverWayItIsTurned([Values(1, -1)] int way)
        {
            Reach("s2.swap:open");
            bot.FreeHands();
            var cam = Shot("vise"); var screw = bench.Part("fixtures.vise_screw");
            var press = Aim(cam, screw.GrabPoint); press.primaryDown = press.primaryHeld = true; Step(cam, press);
            for (int i = 0; i < 200 && !session.Job.ActionDone("s2.swap", "open"); i++)
            {
                var f = Aim(cam, screw.GrabPoint); f.primaryHeld = true; f.scroll = way; Step(cam, f);
            }
            Assert.That(session.Job.ActionDone("s2.swap", "open"), Is.True);
        }

        [Test] public void TheHandleWorksWithAToolStillInTheHand()
        {
            Reach("s2.pry:open_turn");
            var cam = Shot("vise"); var screw = bench.Part("fixtures.vise_screw");
            Assert.That(session.HeldTool, Is.Not.Null, "the pick is still in the hand after the first clip");
            var press = Aim(cam, screw.GrabPoint); press.primaryDown = press.primaryHeld = true; Step(cam, press);
            Assert.That(session.Verb, Is.InstanceOf<TurnVerb>(), "the handle did not answer");
            Assert.That(session.Vise.Grabbed, Is.False, "the press spun the vise instead");
        }

        // ---- "Should be able to spin the vise at all times"
        [TestCase("s0.cell:latch"), TestCase("s1.bind:snip_a"), TestCase("s1.pin:taps"), TestCase("s2.dust:lid")]
        public void TheViseTurnsAtAnyStep(string action)
        {
            Reach(action);
            var cam = Shot("vise"); float before = session.Vise.Yaw;
            var baseAt = bench.Part("fixtures.vise_base").transform.position;
            var f = Aim(cam, bench.SurfacePoint); f.swivelHeld = true; f.delta = new Vector2(10, 0);
            for (int i = 0; i < 10; i++) Step(cam, f);
            Assert.That(Mathf.Abs(Mathf.DeltaAngle(before, session.Vise.Yaw)), Is.GreaterThan(30));
            Assert.That(Vector3.Distance(baseAt, bench.Part("fixtures.vise_base").transform.position), Is.LessThan(1e-5f), "the base moved");
        }

        [Test] public void TheViseTurnsWithAPartInTheHand()
        {
            Reach("s1.scales:left");
            bot.FreeHands(); Assert.That(bot.Press("pistol.scale_l"), Is.True, bot.Error);
            Assert.That(session.HeldPart, Is.Not.Null);
            var cam = Shot("vise"); float before = session.Vise.Yaw;
            var f = Aim(cam, bench.SurfacePoint); f.swivelHeld = true; f.scroll = 1;
            for (int i = 0; i < 3; i++) Step(cam, f);
            Assert.That(Mathf.Abs(Mathf.DeltaAngle(before, session.Vise.Yaw)), Is.GreaterThan(30));
            Assert.That(session.HeldPart, Is.Not.Null, "turning the vise dropped the part");
        }

        // ---- "Often the camera can get out of view" and "A & E should move the character sideways"
        [Test] public void TheWorkStaysInThePictureWhereverTheViewIsTaken()
        {
            var lensObject = new GameObject("test lens", typeof(Camera));
            var rig = new AssemblyCameraRig(bench, bench.settings);
            try
            {
                var lens = lensObject.GetComponent<Camera>(); lens.aspect = 16f / 9;
                rig.Enter(lens, true, "vise");
                var work = bench.Marker("fixtures.vise/seat_work").transform.position;
                foreach (float sideways in new[] { -1f, 0, 1 })
                    foreach (float zoom in new[] { 0f, 1 })
                        foreach (float look in new[] { -500f, 0, 500 })
                        {
                            rig.ResetView(true); rig.ZoomTo(zoom); rig.Focus(work);
                            var f = new AssemblyInputFrame { shimmy = sideways, lookHeld = true, delta = new Vector2(look, look) };
                            for (int i = 0; i < 90; i++) rig.Tick(Dt, f, false, true);
                            var v = lens.WorldToViewportPoint(work);
                            Assert.That(v.z, Is.GreaterThan(0));
                            Assert.That(v.x, Is.InRange(.02f, .98f), $"side {sideways}, zoom {zoom}, look {look}");
                            Assert.That(v.y, Is.InRange(.03f, .97f), $"side {sideways}, zoom {zoom}, look {look}");
                        }
            }
            finally { rig.Exit(true); UnityEngine.Object.DestroyImmediate(lensObject); }
        }

        [Test] public void AAndEStepSidewaysAndANewShotIsNotLeftZoomedIn()
        {
            var lensObject = new GameObject("test lens", typeof(Camera));
            var rig = new AssemblyCameraRig(bench, bench.settings);
            try
            {
                var lens = lensObject.GetComponent<Camera>(); rig.Enter(lens, true, "vise");
                var none = new AssemblyInputFrame(); rig.Tick(Dt, none, false, true);
                var start = lens.transform.position; var right = lens.transform.right;
                var f = new AssemblyInputFrame { shimmy = 1 };
                for (int i = 0; i < 30; i++) rig.Tick(Dt, f, false, true);
                Assert.That(Vector3.Dot(lens.transform.position - start, right), Is.GreaterThan(.2f), "E steps right");
                f.shimmy = -1;
                for (int i = 0; i < 60; i++) rig.Tick(Dt, f, false, true);
                Assert.That(Vector3.Dot(lens.transform.position - start, right), Is.LessThan(-.2f), "A steps left");
                rig.ZoomTo(1); rig.Tick(Dt, none, false, true); Assert.That(rig.Zoom, Is.EqualTo(1));
                rig.SetShot("mat", true); Assert.That(rig.Zoom, Is.EqualTo(0));
            }
            finally { rig.Exit(true); UnityEngine.Object.DestroyImmediate(lensObject); }
        }

        [Test] public void TheKeysAreBoundAndDoNotClash()
        {
            var maps = (JArray)JObject.Parse(File.ReadAllText(Path.Combine(Application.dataPath, "AthenHill/Data/Controls.inputactions")))["maps"];
            var bindings = (JArray)maps.First(m => (string)m["name"] == "Bench")["bindings"];
            string[] Uses(string key) => bindings.Where(b => (string)b["path"] == "<Keyboard>/" + key).Select(b => (string)b["action"]).ToArray();
            foreach (var key in new[] { "a", "e", "d" }) Assert.That(Uses(key), Is.EqualTo(new[] { "Shimmy" }), key);
            Assert.That(Uses("v"), Is.EqualTo(new[] { "Swivel" }));
            Assert.That(Uses("g"), Is.EqualTo(new[] { "ResetView" }));
        }

        // ---- "it should say to go back to Ossa where she will talk to you about the scrap and then say go to Brann"
        [Test] public void AClearedDepotSendsThePlayerToOssaThenOnToBrann()
        {
            var order = AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset").orders[0];
            Assert.That(order.identifyGuidance, Is.EqualTo("ossa"));
            var ossa = AssetDatabase.LoadAssetAtPath<NpcDefinition>("Assets/AthenHill/Data/npc_ossa.asset");
            Assert.That(ossa.nodes.First(n => n.id == "servo_look").text, Does.Contain("Brann"), "Ossa is the one who sends the player on");
            string scene = File.ReadAllText(Path.Combine(Application.dataPath, "AthenHill/Scenes/AthenHill.unity"));
            Assert.That(scene, Does.Contain("Bring that salvage back to me at the post"));
            Assert.That(scene, Does.Not.Contain("Take that salvage to Brann"));
            Assert.That(scene, Does.Contain("- key: ossa"), "her marker");
        }
    }
}
