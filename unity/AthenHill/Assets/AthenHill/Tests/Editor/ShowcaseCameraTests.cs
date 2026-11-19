using System;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
    /// Showcase camera (19 Nov 2026): conversation framing maths, obstruction pull-in, blend steps, photo-mode controls,
    /// file naming and state restore.
    public class ShowcaseCameraTests
    {
        readonly List<GameObject> made = new List<GameObject>();
        Camera MakeCamera(float fov, float aspect)
        {
            var go = new GameObject("showcase test camera"); made.Add(go);
            var c = go.AddComponent<Camera>(); c.fieldOfView = fov; c.aspect = aspect; c.nearClipPlane = .05f;
            return c;
        }
        [TearDown] public void Clean() { foreach (var g in made) if (g) UnityEngine.Object.DestroyImmediate(g); made.Clear(); }

        static Vector3 Viewport(Camera c, Vector3 from, Quaternion rotation, Vector3 point)
        {
            c.transform.SetPositionAndRotation(from, rotation);
            return c.WorldToViewportPoint(point);
        }

        // ---------------------------------------------------------------- framing
        [TestCase(0f, 0f, .667f, .64f)]
        [TestCase(30f, -1.2f, .333f, .64f)]
        [TestCase(-140f, .8f, .5f, .5f)]
        [TestCase(75f, 2.5f, .2f, .8f)]
        public void AimPutsTheTargetOnTheRequestedViewportPoint(float bearing, float rise, float vx, float vy)
        {
            var cam = MakeCamera(40, 16f / 9);
            var from = new Vector3(3, 1.6f, -2);
            var target = from + Quaternion.Euler(0, bearing, 0) * Vector3.forward * 2.4f + Vector3.up * rise;
            var rot = ConversationFraming.Aim(from, target, new Vector2(vx, vy), 40, 16f / 9);
            var v = Viewport(cam, from, rot, target);
            Assert.That(v.x, Is.EqualTo(vx).Within(.002f));
            Assert.That(v.y, Is.EqualTo(vy).Within(.002f));
            Assert.That(v.z, Is.GreaterThan(0));
            Assert.That(rot.eulerAngles.z, Is.EqualTo(0).Within(.01f).Or.EqualTo(360).Within(.01f), "no roll");
        }

        [TestCase(1f)]
        [TestCase(-1f)]
        public void ShoulderShotPutsTheNpcOnAThirdWithThePlayerInTheForeground(float side)
        {
            const float aspect = 16f / 9;
            var shot = ConversationFraming.Shot.Default;
            var cam = MakeCamera(shot.fieldOfView, aspect);
            var player = new Vector3(10, 1.58f, 4);
            var npc = player + new Vector3(1.2f, .05f, 1.4f);
            var pose = ConversationFraming.Solve(player, npc, side, shot, aspect);
            var n = Viewport(cam, pose.position, pose.rotation, npc);
            var p = Viewport(cam, pose.position, pose.rotation, player);
            Assert.That(n.x, Is.EqualTo(side > 0 ? shot.npcViewport.x : 1 - shot.npcViewport.x).Within(.002f));
            Assert.That(n.y, Is.EqualTo(shot.npcViewport.y).Within(.002f));
            Assert.That(p.z, Is.GreaterThan(0), "player head in front of the lens");
            Assert.That(p.x, Is.InRange(0f, 1f), "player head on screen");
            if (side > 0) Assert.That(p.x, Is.LessThan(n.x)); else Assert.That(p.x, Is.GreaterThan(n.x));
            Assert.That(Vector3.Distance(pose.position, player), Is.LessThan(1.6f));   // back 1.25 m since the native QA re-tune
            var toNpc = npc - player; toNpc.y = 0;
            Assert.That(Vector3.Dot(pose.position - player, toNpc), Is.LessThan(0), "camera stays behind the player");
            Assert.That(pose.shoulder, Is.InRange(0f, shot.maxShoulder + 1e-4f));
        }

        [Test]
        public void StandingRightAtTheNpcUsesTheEyeLine()
        {
            Assert.That(ConversationFraming.TooClose(new Vector3(8, 1.6f, 16), new Vector3(8, 1.7f, 15.2f), 1.2f), Is.True, "0.8 m across a counter");
            Assert.That(ConversationFraming.TooClose(new Vector3(8, 1.6f, 16), new Vector3(8, 1.7f, 14.2f), 1.2f), Is.False, "1.8 m away");
        }

        [Test]
        public void TheColonistTurnsToFaceTheNpc()
        {
            Assert.That(ConversationFraming.FaceYaw(Vector3.zero, new Vector3(0, 1, 5)).Value, Is.EqualTo(0).Within(1e-3f), "north");
            Assert.That(ConversationFraming.FaceYaw(Vector3.zero, new Vector3(3, 0, 0)).Value, Is.EqualTo(90).Within(1e-3f), "east");
            Assert.That(ConversationFraming.FaceYaw(new Vector3(2, 0, 2), new Vector3(1, 0, 1)).Value, Is.EqualTo(-135).Within(1e-3f), "south-west");
            Assert.That(ConversationFraming.FaceYaw(Vector3.zero, new Vector3(.01f, 2, .01f)), Is.Null, "same spot: no facing");
        }

        [Test]
        public void APulledInShoulderShotFallsBackToTheEyeLine()
        {
            // Native QA 19 Nov 2026: across Mira's counter the sweep pulled the lens in to about a third of the shot and the
            // player's own shoulder filled the frame. Full distance about 0.95 m.
            Assert.That(ConversationFraming.TooTight(.95f, .95f, .35f, .75f), Is.False, "nothing in the way");
            Assert.That(ConversationFraming.TooTight(.8f, .95f, .35f, .75f), Is.False, "a small pull-in keeps the shoulder shot");
            Assert.That(ConversationFraming.TooTight(.6f, .95f, .35f, .75f), Is.True, "pulled in past three quarters");
            Assert.That(ConversationFraming.TooTight(.3f, .95f, .35f, .75f), Is.True, "under the old minimum clearance");
            Assert.That(ConversationFraming.TooTight(.3f, .95f, .35f, 0f), Is.True, "minimum clearance still applies alone");
        }

        [Test]
        public void ShoulderOffsetReachesTheWantedSeparationOrStopsAtTheLimit()
        {
            float th = Mathf.Tan(20 * Mathf.Deg2Rad) * 16f / 9;
            float s = ConversationFraming.ShoulderOffset(.7f, 3f, .2f, -.2f, th, 2);
            float want = Mathf.Atan(.2f * th) - Mathf.Atan(-.2f * th);
            Assert.That(ConversationFraming.Separation(s, .7f, 3f), Is.EqualTo(want).Within(1e-3f));
            Assert.That(ConversationFraming.ShoulderOffset(.7f, 3f, .9f, -.9f, th, .4f), Is.EqualTo(.4f).Within(1e-5f), "clamped to max shoulder");
            Assert.That(ConversationFraming.ShoulderOffset(.7f, 3f, -.1f, .1f, th, 1), Is.EqualTo(0), "no separation wanted");
        }

        [Test]
        public void SideFollowsTheGameplayCamera()
        {
            var player = Vector3.zero; var npc = new Vector3(0, 0, 2);
            Assert.That(ConversationFraming.ChooseSide(player, npc, new Vector3(1, 1, -3)), Is.EqualTo(1));
            Assert.That(ConversationFraming.ChooseSide(player, npc, new Vector3(-1, 1, -3)), Is.EqualTo(-1));
        }

        [Test]
        public void PullInStopsShortOfTheHitAndNeverOvershoots()
        {
            var pivot = new Vector3(0, 1.6f, 0); var desired = pivot + new Vector3(.6f, 0, -.8f); // 1 m away
            var free = ConversationFraming.PullIn(pivot, desired, -1, .05f, out float d0);
            Assert.That(free, Is.EqualTo(desired)); Assert.That(d0, Is.EqualTo(1).Within(1e-5f));
            var pulled = ConversationFraming.PullIn(pivot, desired, .5f, .05f, out float d1);
            Assert.That(d1, Is.EqualTo(.45f).Within(1e-5f));
            Assert.That(Vector3.Distance(pivot, pulled), Is.EqualTo(.45f).Within(1e-5f));
            Assert.That(Vector3.Dot((pulled - pivot).normalized, (desired - pivot).normalized), Is.EqualTo(1).Within(1e-5f), "same line");
            ConversationFraming.PullIn(pivot, desired, .02f, .05f, out float d2);
            Assert.That(d2, Is.EqualTo(0), "a hit closer than the margin keeps the lens at the pivot");
            ConversationFraming.PullIn(pivot, desired, 4, .05f, out float d3);
            Assert.That(d3, Is.EqualTo(1).Within(1e-5f), "a hit beyond the target changes nothing");
        }

        [Test]
        public void BlendEasesOverTheSetTimeAndReducedMotionCuts()
        {
            float w = 0; int frames = 0;
            while (w < 1 && frames < 1000) { w = ConversationFraming.StepWeight(w, true, 1f / 60, .6f, false); frames++; }
            Assert.That(frames, Is.InRange(35, 37));
            Assert.That(ConversationFraming.StepWeight(.3f, true, .016f, .6f, true), Is.EqualTo(1));
            Assert.That(ConversationFraming.StepWeight(.7f, false, .016f, .6f, true), Is.EqualTo(0));
            Assert.That(ConversationFraming.StepWeight(.5f, true, 0, .6f, false), Is.EqualTo(.5f), "frozen time holds the blend");
            Assert.That(ConversationFraming.Ease(0), Is.EqualTo(0)); Assert.That(ConversationFraming.Ease(1), Is.EqualTo(1));
            Assert.That(ConversationFraming.Ease(.5f), Is.EqualTo(.5f).Within(1e-6f));
        }

        [Test]
        public void FocalLengthFollowsTheFieldOfView()
        {
            Assert.That(ConversationFraming.FocalLength(50), Is.EqualTo(25.73f).Within(.05f));
            Assert.That(ConversationFraming.FocalLength(20), Is.GreaterThan(ConversationFraming.FocalLength(50)));
        }

        // ---------------------------------------------------------------- photo controls
        [Test]
        public void PhotoControlsStepClampAndWrap()
        {
            var c = new PhotoControls { FieldOfView = 89 };
            Assert.That(c.Adjust(PhotoRow.FieldOfView, 1, true), Is.True); Assert.That(c.FieldOfView, Is.EqualTo(PhotoControls.MaxFieldOfView));
            Assert.That(c.Adjust(PhotoRow.FieldOfView, 1, false), Is.False, "already at the limit");
            c.Roll = 44; c.Adjust(PhotoRow.Roll, 1, true); Assert.That(c.Roll, Is.EqualTo(45));
            c.Hour = 23.9f; c.Adjust(PhotoRow.TimeOfDay, 1, false); Assert.That(c.Hour, Is.EqualTo(.15f).Within(1e-4f));
            c.Exposure = 2.9f; c.Adjust(PhotoRow.Exposure, 1, true); Assert.That(c.Exposure, Is.EqualTo(3));
            c.Aperture = 4; c.Adjust(PhotoRow.Aperture, 1, true); Assert.That(c.Aperture, Is.EqualTo(5.657f).Within(.01f), "one full stop");
            bool dof = c.DepthOfField; c.Adjust(PhotoRow.DepthOfField, -1, false); Assert.That(c.DepthOfField, Is.Not.EqualTo(dof));
            Assert.That(c.Adjust(PhotoRow.Capture, 1, false), Is.False);
            c.Selected = 0; c.MoveSelection(-1); Assert.That(c.SelectedRow, Is.EqualTo(PhotoRow.Exit));
            c.MoveSelection(1); Assert.That(c.SelectedRow, Is.EqualTo(PhotoRow.FieldOfView));
        }

        [Test]
        public void PhotoSlidersRoundTrip()
        {
            var c = new PhotoControls();
            foreach (var row in PhotoControls.Rows)
            {
                if (!PhotoControls.IsSlider(row)) continue;
                PhotoControls.SliderRange(row, out float min, out float max);
                float mid = (min + max) * .5f;
                c.SetFromSlider(row, mid);
                Assert.That(c.SliderValue(row), Is.EqualTo(mid).Within(.06f), row.ToString());
            }
            c.SetFromSlider(PhotoRow.FocusDistance, 100); Assert.That(c.FocusDistance, Is.EqualTo(PhotoControls.MaxFocus));
        }

        [Test]
        public void FreeCameraStaysNearTheColonistAndMovesAtTheSetSpeed()
        {
            var anchor = new Vector3(5, 1.5f, 5);
            Assert.That(PhotoFlight.ClampToAnchor(anchor, anchor + Vector3.right * 3, 15), Is.EqualTo(anchor + Vector3.right * 3));
            var far = PhotoFlight.ClampToAnchor(anchor, anchor + new Vector3(30, 40, 0), 15);
            Assert.That(Vector3.Distance(far, anchor), Is.EqualTo(15).Within(1e-4f));
            var step = PhotoFlight.Displacement(Quaternion.identity, new Vector2(1, 1), 1, 3, .5f);
            Assert.That(step.magnitude, Is.EqualTo(1.5f).Within(1e-4f), "diagonal input is not faster");
            Assert.That(PhotoFlight.Speed(3, true, false), Is.EqualTo(12)); Assert.That(PhotoFlight.Speed(3, false, true), Is.EqualTo(.75f));
            Assert.That(PhotoFlight.WrapPitch(350), Is.EqualTo(-10).Within(1e-4f));
        }

        [Test]
        public void CaptureNamesNeverOverwrite()
        {
            var taken = new HashSet<string>();
            var when = new DateTime(2026, 11, 19, 14, 3, 22);
            var a = PhotoFiles.Stem("/pics", when, 2, taken.Contains);
            Assert.That(a, Does.EndWith("Ashfall_20261119_140322"));
            taken.Add(PhotoFiles.SupersampledPath(a, 2));
            var b = PhotoFiles.Stem("/pics", when, 2, taken.Contains);
            Assert.That(b, Is.Not.EqualTo(a)); Assert.That(b, Does.EndWith("-2"));
            Assert.That(PhotoFiles.SupersampledPath(b, 2), Does.EndWith("-2_2x.png"));
            Assert.That(PhotoFiles.DefaultFolder(), Does.EndWith(System.IO.Path.Combine("Pictures", "Ashfall")));
            var px = new byte[] { 1, 2, 3, 0, 4, 5, 6, 7 }; PhotoFiles.ForceOpaque(px);
            Assert.That(px[3], Is.EqualTo(255)); Assert.That(px[7], Is.EqualTo(255)); Assert.That(px[4], Is.EqualTo(4));
        }

        // ---------------------------------------------------------------- state restore
        [Test]
        public void LedgerRestoresInReverseExactlyOnceAndSurvivesAFailingStep()
        {
            var order = new List<string>(); var ledger = new RestoreLedger();
            ledger.Add("a", () => order.Add("a"));
            ledger.Add("b", () => throw new InvalidOperationException("boom"));
            ledger.Add("c", () => order.Add("c"));
            string failed = null;
            Assert.That(ledger.RestoreAll((n, e) => failed = n), Is.EqualTo(2));
            Assert.That(order, Is.EqualTo(new[] { "c", "a" }));
            Assert.That(failed, Is.EqualTo("b"));
            Assert.That(ledger.Count, Is.Zero);
            Assert.That(ledger.RestoreAll(), Is.Zero, "nothing runs twice");
        }

        [Test]
        public void CameraStateRestoresPoseAndLens()
        {
            var cam = MakeCamera(52, 16f / 9);
            cam.transform.SetPositionAndRotation(new Vector3(1, 2, 3), Quaternion.Euler(12, 34, 0));
            var saved = CameraState.Capture(cam);
            cam.transform.SetPositionAndRotation(new Vector3(-7, 9, 0), Quaternion.Euler(-40, 200, 15)); cam.fieldOfView = 20;
            saved.Apply(cam);
            Assert.That(Vector3.Distance(cam.transform.position, new Vector3(1, 2, 3)), Is.LessThan(1e-5f));
            Assert.That(Quaternion.Angle(cam.transform.rotation, Quaternion.Euler(12, 34, 0)), Is.LessThan(1e-3f));
            Assert.That(cam.fieldOfView, Is.EqualTo(52).Within(1e-5f));
        }

        [Test]
        public void ConversationOverlayAtZeroWeightLeavesThePoseUntouched()
        {
            // At weight 0 Compose returns before touching the pose; the blend itself must also start exactly on the gameplay pose.
            var gameplay = new Vector3(3.25f, 2.1f, -7.5f); var gameplayRot = Quaternion.Euler(17, -90, 0);
            var pose = ConversationFraming.Solve(Vector3.up * 1.58f, new Vector3(0, 1.6f, 2), 1, ConversationFraming.Shot.Default, 16f / 9);
            float e = ConversationFraming.Ease(0);
            Assert.That(Vector3.Lerp(gameplay, pose.position, e), Is.EqualTo(gameplay));
            Assert.That(Quaternion.Angle(Quaternion.Slerp(gameplayRot, pose.rotation, e), gameplayRot), Is.LessThan(1e-3f));
        }
    }
}
