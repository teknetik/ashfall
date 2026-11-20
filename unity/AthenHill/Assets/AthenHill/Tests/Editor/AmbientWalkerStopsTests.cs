using System.Collections.Generic;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
    /// Residents pass (20 Nov 2026): AmbientWalker work stops. A walker with stops reaches each stop, stands there for its
    /// seconds turned to its facing, then walks on; walkers without stops keep the original constant-speed loop.
    public class AmbientWalkerStopsTests
    {
        static readonly MethodInfo StartM = typeof(AmbientWalker).GetMethod("Start", BindingFlags.NonPublic | BindingFlags.Instance);
        static readonly MethodInfo StepM = typeof(AmbientWalker).GetMethod("UpdateWithStops", BindingFlags.NonPublic | BindingFlags.Instance);
        readonly List<GameObject> made = new List<GameObject>();

        AmbientWalker Walker(params AmbientWalker.WorkStop[] stops)
        {
            var route = new GameObject("route"); made.Add(route);
            var pts = new[] { new Vector3(0, 0, 0), new Vector3(10, 0, 0), new Vector3(10, 0, 10), new Vector3(0, 0, 10) };
            var wps = new Transform[pts.Length];
            for (int i = 0; i < pts.Length; i++) { wps[i] = new GameObject("wp" + i).transform; wps[i].SetParent(route.transform); wps[i].position = pts[i]; }
            var go = new GameObject("walker"); made.Add(go);
            var w = go.AddComponent<AmbientWalker>();
            w.waypoints = wps; w.speed = 1; w.phase = 0; w.stops = stops;
            StartM.Invoke(w, null);
            return w;
        }
        static void Step(AmbientWalker w, float seconds, float dt = 1 / 30f) { for (float t = 0; t < seconds; t += dt) StepM.Invoke(w, new object[] { dt }); }

        [TearDown]
        public void Clean() { foreach (var g in made) if (g) Object.DestroyImmediate(g); made.Clear(); }

        [Test]
        public void StopsAtTheWaypointFacesTheStopAndWalksOn()
        {
            var w = Walker(new AmbientWalker.WorkStop { waypoint = 1, seconds = 5, facingYaw = 180, label = "desk" });
            for (int i = 0; i < 30 * 30 && !w.AtWork; i++) StepM.Invoke(w, new object[] { 1 / 30f });   // 10 m at <= 1 m/s with easing: well inside 30 s
            Assert.That(w.AtWork, Is.True, "at the stop");
            Assert.That(w.CurrentStop.label, Is.EqualTo("desk"));
            Assert.That(Vector3.Distance(w.transform.position, new Vector3(10, 0, 0)), Is.LessThan(.01f));
            Step(w, Mathf.Max(0, w.StopSecondsLeft - .3f));
            Assert.That(Mathf.Abs(Mathf.DeltaAngle(w.transform.eulerAngles.y, 180)), Is.LessThan(5), "turned to the stop's facing");
            Step(w, 2);
            Assert.That(w.AtWork, Is.False, "walks on after the stop");
            Assert.That(w.transform.position.z, Is.GreaterThan(.05f), "left along the next segment");
        }

        [Test]
        public void EasesIntoTheStopAndDoesNotStopTwiceInOnePass()
        {
            var w = Walker(new AmbientWalker.WorkStop { waypoint = 2, seconds = 1 });
            int entries = 0; bool was = false; float slowest = 9;
            Vector3 last = w.transform.position;
            for (float t = 0; t < 40; t += 1 / 30f)
            {
                StepM.Invoke(w, new object[] { 1 / 30f });
                if (w.AtWork && !was) entries++;
                if (!w.AtWork && !was) slowest = Mathf.Min(slowest, Vector3.Distance(last, w.transform.position) * 30);
                was = w.AtWork; last = w.transform.position;
            }
            Assert.That(entries, Is.EqualTo(1), "one stop per lap (the 40 m loop takes over 40 s)");
            Assert.That(slowest, Is.LessThan(.6f).And.GreaterThan(.3f), "eases to about the slow factor near the stop");
        }

        [Test]
        public void WalkerWithoutStopsHasNoWorkState()
        {
            var w = Walker();
            Assert.That(w.stops, Is.Empty);
            Assert.That(w.AtWork, Is.False);
        }
    }
}
