using System.Reflection;
using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    public class PlayerRenderPoseTests
    {
        [TestCase(30)]
        [TestCase(60)]
        [TestCase(144)]
        public void ConstantMovementAdvancesEvenlyAcrossRenderAndPhysicsCadences(int frameRate)
        {
            const double step = .02;
            const float speed = 6;
            var pose = new PlayerRenderPose();
            pose.Reset(Vector3.zero, Quaternion.identity);
            int completedSteps = 0;
            float previous = 0;
            for (int frame = 1; frame <= frameRate * 3; frame++)
            {
                double time = (double)frame / frameRate;
                int steps = (int)System.Math.Floor(time / step + 1e-8);
                while (completedSteps < steps)
                {
                    completedSteps++;
                    pose.Record(Vector3.right * (float)(completedSteps * step * speed), Quaternion.identity);
                }
                float fraction = PlayerRenderPose.Fraction(time, completedSteps * step, (float)step);
                float actual = pose.Position(fraction).x;
                float expected = (float)System.Math.Max(0, (time - step) * speed);
                Assert.That(actual, Is.EqualTo(expected).Within(.00001f), "Render frame " + frame);
                // The initial partial interval has no earlier simulation sample.
                if ((double)(frame - 1) / frameRate >= step)
                    Assert.That(actual - previous, Is.EqualTo(speed / frameRate).Within(.00001f),
                        "Constant motion must not repeat poses or jump at the 50 Hz physics cadence.");
                previous = actual;
            }
        }

        [Test]
        public void CollisionStopNeverExtrapolatesPastLastCompletedPose()
        {
            var pose = new PlayerRenderPose();
            pose.Reset(Vector3.zero, Quaternion.identity);
            pose.Record(Vector3.right, Quaternion.identity);
            Assert.That(pose.Position(PlayerRenderPose.Fraction(5, 1, .02f)).x, Is.EqualTo(1));
            pose.Record(Vector3.right, Quaternion.identity);
            Assert.That(pose.Position(.5f).x, Is.EqualTo(1));
            Assert.That(PlayerRenderPose.Fraction(.99, 1, .02f), Is.Zero);
            Assert.That(PlayerRenderPose.Fraction(1, 1, 0), Is.EqualTo(1));
        }

        [Test]
        public void FacingCrossesTheYawSeamByTheShortArc()
        {
            var pose = new PlayerRenderPose();
            pose.Reset(Vector3.zero, Quaternion.Euler(0, 359, 0));
            pose.Record(Vector3.zero, Quaternion.Euler(0, 1, 0));
            Assert.That(Quaternion.Angle(pose.Rotation(.5f), Quaternion.identity), Is.LessThan(.01f));
        }

        [Test]
        public void TeleportClearsTheOldMotionInsteadOfSweepingThroughTheDistrict()
        {
            var pose = new PlayerRenderPose();
            pose.Reset(Vector3.zero, Quaternion.identity);
            pose.Record(Vector3.one, Quaternion.Euler(0, 90, 0));
            var destination = new Vector3(50, 8, -30);
            var rotation = Quaternion.Euler(0, 180, 0);
            pose.Reset(destination, rotation);
            foreach (float fraction in new[] { 0f, .5f, 1f })
            {
                Assert.That(Vector3.Distance(pose.Position(fraction), destination), Is.LessThan(.00001f));
                Assert.That(Quaternion.Angle(pose.Rotation(fraction), rotation), Is.LessThan(.01f));
            }
        }

        [Test]
        public void PresentationPreservesControllerRootAndRestoresAuthoredVisualOffset()
        {
            var root = new GameObject("render pose test");
            root.SetActive(false);
            try
            {
                var motor = root.AddComponent<PlayerMotor>();
                var visual = new GameObject("visual").transform;
                visual.SetParent(root.transform, false);
                var offset = new Vector3(.1f, -.03f, .02f);
                visual.localPosition = offset;
                motor.visual = visual;
                root.SetActive(true);
                InvokeLifecycle(motor, "OnEnable");
                // Supply two completed steps without inventing a second movement/input implementation.
                var pose = (PlayerRenderPose)typeof(PlayerMotor).GetField("renderPose",
                    BindingFlags.Instance | BindingFlags.NonPublic).GetValue(motor);
                root.transform.position = Vector3.right;
                pose.Record(root.transform.position, Quaternion.Euler(0, 90, 0));
                InvokeLifecycle(motor, "LateUpdate");
                Assert.That(root.transform.position, Is.EqualTo(Vector3.right), "Rendering must never move collision.");
                Assert.That(Vector3.Distance(visual.position, motor.RenderPosition + offset), Is.LessThan(.00001f));
                motor.enabled = false;
                InvokeLifecycle(motor, "OnDisable");
                Assert.That(Vector3.Distance(visual.localPosition, offset), Is.LessThan(.00001f));
                Assert.That(Quaternion.Angle(visual.rotation, Quaternion.Euler(0, 90, 0)), Is.LessThan(.01f));
                motor.enabled = true;
                InvokeLifecycle(motor, "OnEnable");
                motor.Teleport(new Vector3(10, 3, -4));
                Assert.That(Vector3.Distance(motor.RenderPosition, root.transform.position), Is.LessThan(.00001f));
                Assert.That(Vector3.Distance(visual.localPosition, offset), Is.LessThan(.00001f));
            }
            finally { Object.DestroyImmediate(root); }
        }

        // EditMode does not run this gameplay behaviour. Calling its methods directly
        // avoids asking Unity's runtime SendMessage dispatcher to execute it in EditMode.
        static void InvokeLifecycle(PlayerMotor motor, string method)
        {
            typeof(PlayerMotor).GetMethod(method, BindingFlags.Instance | BindingFlags.NonPublic).Invoke(motor, null);
        }
    }
}
